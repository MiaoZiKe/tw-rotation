"""多頻道每日成效收集（2026-11-09）：IG／Threads 帳號層＋每則已發貼文的成效，每天記一列。

Andy 要的是「每週檢討時看得到數字」，所以這支只做三件事：
  1. 帳號層：追蹤數、觸及／瀏覽（有權限才有）。
  2. 每則已發貼文（讀各頻道 state/posted.json 的 id）：觸及、瀏覽、讚、留言、分享、收藏、轉發、引用。
  3. 寫檔：docs/marketing/channels/<頻道>/state/insights/
       account_daily.csv   每天每平台一列（同一天重跑就覆蓋那一列，不重複）
       posts_daily.csv     每天每則貼文一列（看得出發文後的累積曲線）
       last_run.json       這一輪的狀態：每個平台是 ok／partial（缺指標）／no_token（沒設權杖）／
                           token_invalid／no_uid、缺哪些指標、哪個權限需要 Andy 重新授權、上次成功時間

設計原則（CLAUDE.md 紅線）：
  · 「沒權限」「沒設定」「真的壞了」分開記。權限不足只記缺哪個指標與需要哪個權限，不讓工作流紅燈。
  · 每個指標先試合併呼叫，失敗再逐一試；某指標不支援就略過，不影響其他指標。
  · 權杖只讀自己頻道的前綴（HP.tokens 只看 <前綴>IG_*／<前綴>THREADS_*），絕不碰頻道①的 IG_ACCESS_TOKEN。
  · 檔案裡不寫權杖，也不寫完整帳號編號（IG 使用者編號只在記憶體裡用，錯誤訊息的長數字一律遮掉）。
  · 共用 scripts/healing_post.py 的權杖讀取、IG 帳號探查（fb_ig_candidates／resolve_uid），只 import、不改它。

用法：
  python scripts/channel_insights.py --channel healing        # 單一頻道（工作流 matrix 用）
  python scripts/channel_insights.py --channel all
  python scripts/channel_insights.py --channel tech --dry-run  # 不連網、不寫檔，只印會抓什麼
工作流：.github/workflows/channel_insights.yml（台北 23:23 每天一次）。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import healing_post as HP  # noqa: E402  共用：tokens／resolve_uid／ig_host／channel／load_json（只 import，不改）
import social_publish as SP  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))
THREADS_API = "https://graph.threads.net/v1.0"
DEFAULT_POST_LIMIT = 30   # 每平台只抓最近 30 則，免得 CSV 與 API 呼叫無限長大

IG_ACCOUNT_METRICS = ["reach", "views", "profile_views", "accounts_engaged"]
IG_POST_METRICS = ["views", "reach", "saved", "shares", "total_interactions"]
TH_ACCOUNT_METRICS = ["views", "likes", "replies", "reposts", "quotes"]
TH_POST_METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]
# 需要哪個權限才拿得到洞察（缺權限時摘要照這個寫給 Andy）
NEEDS = {"ig": "instagram_manage_insights", "threads": "threads_manage_insights"}
# 合併呼叫時要帶的時間窗（total_value／views 類指標必填；followers_count 不吃）
TIME_METRICS = {"reach", "views", "profile_views", "accounts_engaged", "likes", "replies", "reposts", "quotes"}

ACCOUNT_FIELDS = ["date", "fetched_at", "platform", "status", "followers", "views", "reach", "profile_views",
                  "accounts_engaged", "likes", "replies", "reposts", "quotes", "missing", "need_permission"]
POST_FIELDS = ["date", "fetched_at", "platform", "folder", "post_id", "posted_at", "views", "reach", "likes",
               "comments", "replies", "reposts", "quotes", "shares", "saved", "total_interactions", "missing"]

Getter = Callable[[str, dict], tuple[bool, dict]]


# ---------- 呼叫與錯誤分類 ----------
def live_get(url: str, params: dict) -> tuple[bool, dict]:
    """單次 GET。成功回 (True, JSON)；失敗回 (False, error 物件)。權杖在 params 裡，絕不輸出。"""
    import requests
    try:
        r = requests.get(url, params=params, timeout=SP.HTTP_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        return False, {"message": f"連線失敗：{type(e).__name__}"}
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if r.status_code >= 400 or "error" in data:
        err = data.get("error") if isinstance(data.get("error"), dict) else {"message": f"HTTP {r.status_code}"}
        return False, err
    return True, data


def _clean(msg) -> str:
    """錯誤訊息：去掉權杖、遮掉 9 位以上的數字（可能是帳號編號），截短。"""
    s = SP.redact(str(msg or ""))
    s = re.sub(r"\d{9,}", "…", s)
    return s[:160]


def classify(err: dict) -> str:
    """Graph 錯誤 → 種類：token_invalid（權杖失效）／permission（缺權限）／unsupported（這個指標或欄位不適用）／rate_limit／error。"""
    try:
        code = int(err.get("code") or 0)
    except (TypeError, ValueError):
        code = 0
    msg = str(err.get("message") or "").lower()
    if code == 190 or "expired" in msg or "invalid oauth" in msg:
        return "token_invalid"
    if code in (10, 200, 294) or "permission" in msg:
        return "permission"
    if code == 100:
        return "unsupported"
    if code in (4, 17, 32, 613):
        return "rate_limit"
    return "error"


def vals(d: dict) -> dict:
    """Graph insights 回應 → {指標: 數值}。total_value 取 total_value.value；時間序列取最後一筆。"""
    out = {}
    for m in (d.get("data") or []) if isinstance(d, dict) else []:
        name = m.get("name")
        if not name:
            continue
        if "total_value" in m:
            v = (m.get("total_value") or {}).get("value")
        else:
            arr = m.get("values") or []
            v = arr[-1].get("value") if arr else None
        if v is not None:
            out[name] = v
    return out


def fetch_insights(get: Getter, url: str, token: str, metrics: list[str], extra: dict | None = None):
    """先合併呼叫；失敗（通常是其中一個指標不支援或缺權限）就逐一呼叫。回傳 (值, 缺的 {指標: {kind, message}})。"""
    extra = extra or {}
    ok, d = get(url, {"metric": ",".join(metrics), "access_token": token, **extra})
    if ok:
        return vals(d), {}
    got, missing = {}, {}
    for m in metrics:
        ok, d = get(url, {"metric": m, "access_token": token, **extra})
        if ok:
            got.update(vals(d))
        else:
            missing[m] = {"kind": classify(d), "message": _clean(d.get("message"))}
    return got, missing


def _window(now: datetime, metric_list: list[str]) -> dict:
    """需要時間窗的指標帶 since／until（最近 1 天）；只給 total_value／views 類，免得 followers_count 也被帶去出錯。"""
    if not any(m in TIME_METRICS for m in metric_list):
        return {}
    return {"since": int((now - timedelta(days=1)).timestamp()), "until": int(now.timestamp())}


# ---------- 單一平台 ----------
def collect_ig(get: Getter, token: str, uid: str, now: datetime, posts: list[dict]) -> dict:
    base = HP.ig_host(token)   # EAA（Facebook 登入）→ graph.facebook.com；IGAA → graph.instagram.com
    res = {"account": {}, "missing": {}, "posts": [], "errors": []}
    ok, d = get(f"{base}/{uid}", {"fields": "followers_count", "access_token": token})
    if ok:
        res["account"]["followers"] = d.get("followers_count")
    else:
        res["missing"]["followers"] = {"kind": classify(d), "message": _clean(d.get("message"))}
    acc_extra = {"period": "day", "metric_type": "total_value", **_window(now, IG_ACCOUNT_METRICS)}
    got, miss = fetch_insights(get, f"{base}/{uid}/insights", token, IG_ACCOUNT_METRICS, acc_extra)
    res["account"].update(got)
    res["missing"].update(miss)
    for p in posts:
        row = {"folder": p["folder"], "post_id": p["id"], "posted_at": p["posted_at"], "missing": {}}
        ok, d = get(f"{base}/{p['id']}", {"fields": "like_count,comments_count", "access_token": token})
        if ok:
            row["likes"] = d.get("like_count")
            row["comments"] = d.get("comments_count")
        else:
            row["missing"]["likes_comments"] = {"kind": classify(d), "message": _clean(d.get("message"))}
        got, miss = fetch_insights(get, f"{base}/{p['id']}/insights", token, IG_POST_METRICS)
        row.update(got)
        row["missing"].update(miss)
        res["posts"].append(row)
    return res


def collect_threads(get: Getter, token: str, now: datetime, posts: list[dict]) -> dict:
    res = {"account": {}, "missing": {}, "posts": [], "errors": []}
    ok, d = get(f"{THREADS_API}/me/threads_insights", {"metric": "followers_count", "access_token": token})
    if ok:
        res["account"]["followers"] = vals(d).get("followers_count")
    else:
        res["missing"]["followers"] = {"kind": classify(d), "message": _clean(d.get("message"))}
    got, miss = fetch_insights(get, f"{THREADS_API}/me/threads_insights", token, TH_ACCOUNT_METRICS,
                               _window(now, TH_ACCOUNT_METRICS))
    res["account"].update(got)
    res["missing"].update(miss)
    for p in posts:
        row = {"folder": p["folder"], "post_id": p["id"], "posted_at": p["posted_at"], "missing": {}}
        got, miss = fetch_insights(get, f"{THREADS_API}/{p['id']}/insights", token, TH_POST_METRICS)
        row.update(got)
        row["missing"].update(miss)
        res["posts"].append(row)
    return res


def posted_list(state: Path, plat: str, limit: int) -> list[dict]:
    """state/posted.json → 這個平台最近 limit 則（沒刪除、有 id）。只取 id 與發文時間，不取網址以外的東西。"""
    posted = HP.load_json(state / "posted.json", {})
    rows = []
    for folder, rec in (posted.items() if isinstance(posted, dict) else []):
        r = (rec or {}).get(plat) if isinstance(rec, dict) else None
        if isinstance(r, dict) and r.get("id") and not r.get("deleted"):
            rows.append({"folder": str(folder), "id": str(r["id"]), "posted_at": str(r.get("at") or "")})
    rows.sort(key=lambda x: x["posted_at"], reverse=True)
    return rows[:limit]


def _need(missing: dict) -> bool:
    return any(v.get("kind") == "permission" for v in missing.values())


def summarize_platform(plat: str, status: str, res: dict) -> dict:
    """平台結果 → 一列狀態（寫進 last_run.json 與摘要）。"""
    got_account = bool(res.get("account"))
    post_ok = sum(1 for r in res.get("posts", []) if any(k in r for k in ("views", "likes", "reach")))
    miss = dict(res.get("missing", {}))
    for r in res.get("posts", []):
        for k, v in (r.get("missing") or {}).items():
            miss.setdefault(f"{k}", v)
    kinds = {v.get("kind") for v in miss.values()}
    if status == "ok" and "token_invalid" in kinds:   # 權杖失效要蓋過「缺指標」，不然會被當成權限問題
        status = "token_invalid"
    elif status == "ok" and miss:
        status = "partial"
    if status == "ok" and not got_account and res.get("posts") and not post_ok:
        status = "error"
    return {"status": status, "missing": {k: v.get("kind") for k, v in miss.items()},
            "need_permission": NEEDS[plat] if _need(miss) else "",
            "posts_total": len(res.get("posts", [])), "posts_with_data": post_ok,
            "account_values": {k: v for k, v in res.get("account", {}).items() if v is not None}}


# ---------- 寫檔（同一天重跑只覆蓋當天那一列） ----------
def upsert_csv(path: Path, fields: list[str], rows: list[dict], key: Callable[[dict], tuple]) -> None:
    existing: dict[tuple, dict] = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                existing[key(r)] = r
    for r in rows:
        existing[key({k: str(v) for k, v in r.items()})] = {k: ("" if r.get(k) is None else r.get(k)) for k in fields}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])


# ---------- 一個頻道 ----------
def run_channel(code: str, env: dict, now: datetime, get: Getter = live_get,
                post_limit: int = DEFAULT_POST_LIMIT, write: bool = True) -> dict:
    c = HP.channel(code)
    prefix = c["prefix"]
    out_dir = c["state"] / "insights"
    today = now.astimezone(TAIPEI).strftime("%Y-%m-%d")
    fetched = now.astimezone(TAIPEI).isoformat(timespec="seconds")
    toks = HP.tokens(env, prefix)                       # 只讀 <前綴>*，權杖已遮蔽
    verify = HP.load_json(c["state"] / "verify.json", {})
    prev = HP.load_json(out_dir / "last_run.json", {}) if write else {}
    report = {"channel": code, "account": c["account"], "at": fetched, "platforms": {}}
    acc_rows, post_rows = [], []

    for plat in ("ig", "threads"):
        tok = toks.get(plat, "")
        pl = {"status": "no_token", "missing": {}, "need_permission": "", "posts_total": 0, "posts_with_data": 0,
              "account_values": {}, "last_success": (prev.get("platforms", {}).get(plat) or {}).get("last_success", "")}
        if not tok:
            report["platforms"][plat] = pl
            continue
        posts = posted_list(c["state"], plat, post_limit)
        try:
            if plat == "ig":
                via = (verify.get("ig") or {}).get("via", "")
                uid = HP.resolve_uid("ig", (env.get(f"{prefix}IG_USER_ID") or "").strip(), tok, prefix, via)
                if not uid:
                    report["platforms"][plat] = {**pl, "status": "no_uid"}
                    continue
                res = collect_ig(get, tok, uid, now, posts)
            else:
                res = collect_threads(get, tok, now, posts)
        except Exception as e:  # noqa: BLE001
            report["platforms"][plat] = {**pl, "status": "error", "note": _clean(e)}
            continue
        s = summarize_platform(plat, "ok", res)
        if s["account_values"] or s["posts_with_data"]:
            s["last_success"] = fetched
        s = {**pl, **s}
        report["platforms"][plat] = s
        acc_rows.append({"date": today, "fetched_at": fetched, "platform": plat, "status": s["status"],
                         **{k: s["account_values"].get(k) for k in ACCOUNT_FIELDS[4:13]},
                         "missing": ";".join(f"{k}={v}" for k, v in s["missing"].items()),
                         "need_permission": s["need_permission"]})
        for r in res["posts"]:
            post_rows.append({"date": today, "fetched_at": fetched, "platform": plat, "folder": r["folder"],
                              "post_id": r["post_id"], "posted_at": r["posted_at"],
                              **{k: r.get(k) for k in POST_FIELDS[6:16]},
                              "missing": ";".join(sorted(r.get("missing", {}))) })

    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        if acc_rows:
            upsert_csv(out_dir / "account_daily.csv", ACCOUNT_FIELDS, acc_rows, lambda r: (r["date"], r["platform"]))
        if post_rows:
            upsert_csv(out_dir / "posts_daily.csv", POST_FIELDS, post_rows,
                       lambda r: (r["date"], r["platform"], r["post_id"]))
        (out_dir / "last_run.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def render(report: dict) -> str:
    """給 Actions 摘要用的繁體中文表格（不含權杖與帳號編號）。"""
    label = {"ok": "✅ 全部拿到", "partial": "⚠️ 缺部分指標", "no_token": "🛠️ 等待設定權杖",
             "token_invalid": "⚠️ 權杖失效（要重新產生）", "no_uid": "⚠️ 查不到 IG 帳號編號", "error": "⚠️ 抓取失敗"}
    lines = [f"### {report['channel']}（{report['account']}）洞察收集 {report['at'][:16]}", "",
             "| 平台 | 狀態 | 貼文有數字 | 缺的指標 | 需要重新授權 |", "|---|---|---|---|---|"]
    for plat, name in (("ig", "IG"), ("threads", "Threads")):
        p = report["platforms"].get(plat, {})
        miss = ", ".join(sorted(p.get("missing", {}))) or "—"
        lines.append(f"| {name} | {label.get(p.get('status'), p.get('status'))} | "
                     f"{p.get('posts_with_data', 0)}／{p.get('posts_total', 0)} | {miss} | "
                     f"{p.get('need_permission') or '—'} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="多頻道每日成效收集")
    ap.add_argument("--channel", default="all", help="頻道代碼（healing／tech／caffaine）或 all")
    ap.add_argument("--post-limit", type=int, default=DEFAULT_POST_LIMIT)
    ap.add_argument("--dry-run", action="store_true", help="不連網、不寫檔，只印會抓哪些權杖與貼文數")
    a = ap.parse_args(argv)
    chs = list(HP.load_channels()) if a.channel == "all" else [a.channel]
    now = datetime.now(TAIPEI)
    env = dict(os.environ)
    failed = False
    md = []
    for code in chs:
        try:
            if a.dry_run:
                c = HP.channel(code)
                toks = HP.tokens(env, c["prefix"])
                print(f"[{code}] 空跑：權杖 IG={'有' if toks['ig'] else '沒有'} Threads={'有' if toks['threads'] else '沒有'}；"
                      f"貼文 IG={len(posted_list(c['state'], 'ig', a.post_limit))} "
                      f"Threads={len(posted_list(c['state'], 'threads', a.post_limit))}")
                continue
            rep = run_channel(code, env, now, post_limit=a.post_limit)
            md.append(render(rep))
            print(f"[{code}] " + "；".join(f"{k}={v['status']}" for k, v in rep["platforms"].items()))
            for k, v in rep["platforms"].items():
                if v.get("need_permission"):
                    print(f"::warning::{code} {k} 缺權限：需要重新授權 {v['need_permission']}（其餘能拿的已照拿）")
                if v.get("status") == "no_token":
                    print(f"::notice::{code} {k} 還沒設定權杖，這次不抓")
        except Exception as e:  # noqa: BLE001  真的壞了才紅燈：未預期的錯誤
            failed = True
            print(f"::error::{code} 洞察收集發生未預期錯誤：{_clean(e)}")
    summary = "\n".join(md)
    if summary:
        print(summary)
        sp = os.environ.get("GITHUB_STEP_SUMMARY")
        if sp:
            with open(sp, "a", encoding="utf-8") as f:
                f.write(summary + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
