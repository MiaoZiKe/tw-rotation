"""社群貼文刪除工具（Threads 可用官方 API 刪；IG 只列清單＋產出手動刪除清單）。

2026-11-02 Andy：「因為可能要重新開始，IG Thread 文章會需要砍掉，你需要幫我看看你是否有砍掉的功能」。
能力查證與 Andy 要做的設定：docs/marketing/diagnosis_1102/delete_capability.md

用法：
  # 預設＝只列清單（dry-run），不會送出任何 DELETE
  python scripts/social_delete.py --out out/social_delete/list.json
  python scripts/social_delete.py --platform threads --no-views --out list.json

  # 真刪（只有 Threads）：三個條件缺一不可
  python scripts/social_delete.py --execute --ids-file ids.txt --confirm 我確定刪除

安全規則：
  · 沒有 --execute 一律只讀；有 --execute 也要 --ids-file 與 --confirm「我確定刪除」一字不差才動作。
  · 保留清單（social/delete_keep.json 與 --keep-id）裡的 id 永遠不刪，連同它們底下自己的串文回覆。
  · 只刪「清單裡查得到、屬於這個帳號」的貼文；ids 檔裡查不到的 id 一律跳過（--allow-unlisted 才放行）。
  · 逐則刪、每則結果寫進結果檔；遇到權限／權杖／頻率錯誤立刻停。
  · 每 24 小時官方上限 100 則；先查剩餘額度，再用 --max（預設 90）封頂。
  · 權杖只從環境變數讀（THREADS_ACCESS_TOKEN、IG_ACCESS_TOKEN），絕不印出、絕不寫檔；錯誤訊息一律遮蔽。
  · IG（Instagram 登入版 API）官方不支援刪除貼文，所以 IG 只輸出手動刪除清單（含 permalink）。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP_FILE = ROOT / "social" / "delete_keep.json"
TH_API = "https://graph.threads.net/v1.0"
IG_API = "https://graph.instagram.com/v24.0"
TAIPEI = timezone(timedelta(hours=8))
CONFIRM = "我確定刪除"
DAILY_LIMIT = 100           # 官方：每個帳號 24 小時滾動 100 則刪除
TH_FIELDS = "id,media_type,text,timestamp,permalink,is_quote_post"
TH_REPLY_FIELDS = "id,media_type,text,timestamp,permalink,root_post,replied_to,is_reply"
IG_FIELDS = "id,caption,media_type,media_product_type,timestamp,permalink"
# 遇到就整批停：190 權杖失效、10／200～299 權限不足、4／17／32／613 頻率上限
STOP_CODES = {190, 10, 4, 17, 32, 613} | set(range(200, 300))


class ApiError(Exception):
    def __init__(self, status: int, code, message: str):
        super().__init__(f"HTTP {status} code={code} {message}")
        self.status, self.code, self.message = status, code, message

    @property
    def fatal(self) -> bool:
        try:
            return int(self.code) in STOP_CODES
        except (TypeError, ValueError):
            return self.status in (401, 403)


# ---------- 連線（測試會換掉 transport） ----------

def _mask(s: str, secrets: list[str]) -> str:
    s = str(s)
    for v in secrets:
        if v:
            s = s.replace(v, "***")
    return re.sub(r"(access_token=)[^&\s\"']+", r"\1***", s)[:400]


def urllib_transport(method: str, url: str, params: dict) -> tuple[int, dict]:
    q = urllib.parse.urlencode(params)
    if method == "GET":
        req = urllib.request.Request(f"{url}?{q}")
    else:
        req = urllib.request.Request(f"{url}?{q}", method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {"error": {"message": "非 JSON 回應"}}
    except urllib.error.URLError as e:
        return 0, {"error": {"message": f"連線失敗：{type(e.reason).__name__}"}}


class Client:
    def __init__(self, base: str, token: str, transport=urllib_transport):
        self.base, self.token, self.transport = base, token, transport
        self.calls: list[tuple[str, str]] = []   # (method, path)，給測試與 log 用，不含權杖

    def req(self, method: str, path: str, **params) -> dict:
        params["access_token"] = self.token
        self.calls.append((method, path))
        st, body = self.transport(method, f"{self.base}{path}", params)
        if st == 200 and not (isinstance(body, dict) and body.get("error")):
            return body if isinstance(body, dict) else {}
        err = body.get("error", {}) if isinstance(body, dict) else {}
        raise ApiError(st, err.get("code"), _mask(err.get("message", ""), [self.token]))

    def pages(self, path: str, limit_pages: int = 50, **params) -> list[dict]:
        out, after = [], None
        for _ in range(limit_pages):
            p = dict(params, limit=100)
            if after:
                p["after"] = after
            b = self.req("GET", path, **p)
            out.extend(b.get("data") or [])
            after = ((b.get("paging") or {}).get("cursors") or {}).get("after")
            if not after or not (b.get("paging") or {}).get("next"):
                break
        return out


# ---------- 共用 ----------

def tw_time(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        d = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return ts
    return d.astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M")


def head40(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()[:40]


def norm_id(x) -> str:
    s = str(x).strip()
    return re.sub(r"^(th|threads|ig):", "", s)


def load_keep(path: Path | None, extra: list[str] | None = None) -> dict[str, set[str]]:
    keep = {"threads": set(), "ig": set()}
    if path and path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        for k in ("threads", "ig"):
            keep[k] |= {norm_id(i) for i in (d.get(k) or [])}
    for i in extra or []:
        s = str(i).strip()
        if s.startswith("ig:"):
            keep["ig"].add(norm_id(s))
        else:
            keep["threads"].add(norm_id(s))
    return keep


def read_ids(path: Path) -> list[str]:
    """ids 檔：一行一個（# 開頭是註解）、JSON 陣列、或本工具輸出的清單 json（取 threads 裡 keep=false 的）。"""
    txt = path.read_text(encoding="utf-8").strip()
    if txt.startswith("[") or txt.startswith("{"):
        d = json.loads(txt)
        if isinstance(d, dict):
            d = [x["id"] for x in d.get("threads", []) if not x.get("keep")]
        return [norm_id(x["id"] if isinstance(x, dict) else x) for x in d]
    out = []
    for line in txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(norm_id(line.split()[0]))
    return out


_SC = re.compile(r"/post/([A-Za-z0-9_-]+)")


def resolve_permalinks(ids: list[str], rows: list[dict]) -> tuple[list[str], list[str]]:
    """2026-11-04（期中選舉刪掉重發）：ids 檔可以直接貼貼文網址（threads.com／threads.net 的 /post/<代碼>），
    用清單裡每則的 permalink 對回數字 id。對不到的原樣保留（execute 會當成「不在清單」跳過），回傳 (ids, 註記)。"""
    by_sc = {}
    for r in rows:
        m = _SC.search(r.get("permalink") or "")
        if m:
            by_sc[m.group(1)] = r["id"]
    out, notes = [], []
    for x in ids:
        m = _SC.search(x)
        if not m:
            out.append(x)
            continue
        mid = by_sc.get(m.group(1))
        notes.append(f"{x} → {mid or '對不到（不在這個帳號的清單裡）'}")
        out.append(mid or x)
    return out, notes


def views_of(c: Client, mid: str) -> int | None:
    try:
        b = c.req("GET", f"/{mid}/insights", metric="views")
    except ApiError:
        return None
    for m in b.get("data") or []:
        if m.get("name") == "views":
            v = m.get("values") or []
            if v:
                return v[0].get("value")
            return (m.get("total_value") or {}).get("value")
    return None


# ---------- Threads ----------

def list_threads(c: Client, keep: set[str], with_views=True, with_replies=True) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    rows: list[dict] = []
    for p in c.pages("/me/threads", fields=TH_FIELDS):
        rows.append({"id": str(p["id"]), "kind": "貼文", "media_type": p.get("media_type"),
                     "time_tw": tw_time(p.get("timestamp")), "text40": head40(p.get("text")),
                     "permalink": p.get("permalink", ""), "root": None})
    if with_replies:
        try:
            for p in c.pages("/me/replies", fields=TH_REPLY_FIELDS):
                root = ((p.get("root_post") or {}).get("id"))
                rows.append({"id": str(p["id"]), "kind": "回覆", "media_type": p.get("media_type"),
                             "time_tw": tw_time(p.get("timestamp")), "text40": head40(p.get("text")),
                             "permalink": p.get("permalink", ""), "root": str(root) if root else None})
        except ApiError as e:
            notes.append(f"讀不到自己的回覆（多半是權杖沒有 threads_read_replies）：{e}")
    seen, uniq = set(), []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    for r in uniq:
        r["keep"] = r["id"] in keep or (r["root"] in keep if r["root"] else False)
        r["views"] = views_of(c, r["id"]) if with_views else None
    return uniq, notes


def delete_quota(c: Client) -> dict:
    """回 {'ok': bool, 'used': int|None, 'total': int|None, 'error': str|None}；權杖沒有 threads_delete 時 ok=False。"""
    try:
        b = c.req("GET", "/me/threads_publishing_limit", fields="delete_quota_usage,delete_config")
    except ApiError as e:
        return {"ok": False, "used": None, "total": None, "error": str(e), "fatal": e.fatal}
    d = (b.get("data") or [{}])[0]
    return {"ok": True, "used": d.get("delete_quota_usage"),
            "total": (d.get("delete_config") or {}).get("quota_total"), "error": None, "fatal": False}


def execute_threads(c: Client, ids: list[str], known: dict[str, dict], keep: set[str], *,
                    max_n: int, allow_unlisted: bool, result_path: Path | None, sleep=1.0) -> list[dict]:
    results: list[dict] = []

    def save():
        if result_path:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    done = 0
    for mid in ids:
        row = known.get(mid)
        if mid in keep or (row and row.get("keep")):
            results.append({"id": mid, "result": "保留（在保留清單，不刪）"})
            continue
        if row is None and not allow_unlisted:
            results.append({"id": mid, "result": "跳過（不在這個帳號的貼文清單裡）"})
            continue
        if done >= max_n:
            results.append({"id": mid, "result": f"未處理（本次上限 {max_n} 則已到，24 小時後再跑）"})
            continue
        try:
            b = c.req("DELETE", f"/{mid}")
            ok = bool(b.get("success", True))
            results.append({"id": mid, "result": "成功" if ok else "失敗（API 回 success=false）",
                            "deleted_id": b.get("deleted_id"), "text40": (row or {}).get("text40", "")})
            done += 1 if ok else 0
        except ApiError as e:
            results.append({"id": mid, "result": f"失敗：{e}", "text40": (row or {}).get("text40", "")})
            if e.fatal:
                results.append({"id": "-", "result": "權限／權杖／頻率錯誤，整批立即停止"})
                save()
                print(f"::error::權限／權杖／頻率錯誤，立即停止：{e}")
                break
        save()
        _sleep(sleep)
    save()
    return results


# ---------- IG（只列清單） ----------

def list_ig(c: Client, keep: set[str], with_views=True) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    rows = []
    for p in c.pages("/me/media", fields=IG_FIELDS):
        rows.append({"id": str(p["id"]), "kind": p.get("media_product_type") or "FEED",
                     "media_type": p.get("media_type"), "time_tw": tw_time(p.get("timestamp")),
                     "text40": head40(p.get("caption")), "permalink": p.get("permalink", "")})
    try:
        for p in c.pages("/me/stories", fields=IG_FIELDS):
            rows.append({"id": str(p["id"]), "kind": "STORY（限動，24 小時內）", "media_type": p.get("media_type"),
                         "time_tw": tw_time(p.get("timestamp")), "text40": "", "permalink": p.get("permalink", "")})
    except ApiError as e:
        notes.append(f"讀不到限動：{e}")
    for r in rows:
        r["keep"] = r["id"] in keep
        r["views"] = views_of(c, r["id"]) if with_views else None
    return rows, notes


def ig_manual_md(rows: list[dict]) -> str:
    out = ["# IG 手動刪除清單（Instagram 登入版 API 不支援刪除，只能在 App 內刪）", "",
           "做法：IG App → 個人檔案 → 右上 ☰ → 「你的活動」→「貼文」或「Reels」→ 右上「選取」→ 勾選 → 右下「刪除」。",
           "刪掉的會先進「最近刪除」30 天，30 天內可還原；超過就永久刪除。", "",
           "| 要刪 | 時間（台北） | 類型 | 前 40 字 | 觀看 | 連結 |", "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: x["time_tw"]):
        mark = "保留，不要刪" if r["keep"] else "刪"
        txt = r["text40"].replace("|", "／")
        out.append(f"| {mark} | {r['time_tw']} | {r['kind']} | {txt} | {r['views'] if r['views'] is not None else '-'} | {r['permalink']} |")
    return "\n".join(out) + "\n"


# ---------- 2026-11-09 重新開始：先備份全文＋圖片網址，再刪 ----------
# Andy 11-09：「因為重新開始，幫我將除了今天所有內容刪除 IG Thread」→ 刪之前把每則全文、圖片網址存檔（刪了救不回來）。

TH_TOKEN_ENVS = ("THREADS_DELETE_TOKEN", "THREADS_ACCESS_TOKEN_AUTO", "THREADS_ACCESS_TOKEN")
TH_FULL = "id,media_type,media_product_type,text,timestamp,permalink,shortcode,is_quote_post,media_url,thumbnail_url,alt_text,username"
TH_FULL_REPLY = TH_FULL + ",root_post,replied_to,is_reply"
TH_CHILD = "id,media_type,media_url,thumbnail_url,alt_text"
IG_FULL = "id,caption,media_type,media_product_type,timestamp,permalink,shortcode,media_url,thumbnail_url,username"
IG_CHILD = "id,media_type,media_url,thumbnail_url"


def th_token_candidates(env) -> list[tuple[str, str]]:
    out, seen = [], set()
    for k in TH_TOKEN_ENVS:
        v = (env.get(k) or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append((k, v))
    return out


def pick_delete_token(cands, transport) -> tuple[str | None, str | None, dict, list[str]]:
    """逐把權杖查刪除額度，回第一把有 threads_delete 的 (環境變數名, 權杖, 額度, 每把結果)。只印變數名，不印值。"""
    notes = []
    for name, tok in cands:
        q = delete_quota(Client(TH_API, tok, transport))
        notes.append(f"{name}：{'有刪除權限' if q['ok'] else '沒有刪除權限（' + str(q['error']) + '）'}")
        if q["ok"]:
            return name, tok, q, notes
    return None, None, {}, notes


def _safe_pages(c: Client, path: str, fields: str, fallback: str, notes: list[str]) -> list[dict]:
    try:
        return c.pages(path, fields=fields)
    except ApiError as e:
        notes.append(f"{path} 用完整欄位讀取失敗，改用基本欄位：{e}")
        return c.pages(path, fields=fallback)


def _children(c: Client, mid: str, fields: str, notes: list[str]) -> list[dict]:
    try:
        return c.req("GET", f"/{mid}/children", fields=fields).get("data") or []
    except ApiError as e:
        notes.append(f"{mid} 的輪播子圖讀不到：{e}")
        return []


def _media_urls(p: dict) -> list[str]:
    urls = [p.get("media_url"), p.get("thumbnail_url")]
    for ch in p.get("children") or []:
        urls += [ch.get("media_url"), ch.get("thumbnail_url")]
    return [u for u in urls if u]


def archive_threads(c: Client, notes: list[str]) -> list[dict]:
    rows = []
    for p in _safe_pages(c, "/me/threads", TH_FULL, TH_FIELDS, notes):
        p = dict(p, kind="主文")
        rows.append(p)
    try:
        for p in _safe_pages(c, "/me/replies", TH_FULL_REPLY, TH_REPLY_FIELDS, notes):
            rows.append(dict(p, kind="串文／回覆"))
    except ApiError as e:
        notes.append(f"讀不到自己的回覆（權杖多半缺 threads_read_replies）：{e}")
    seen, out = set(), []
    for r in rows:
        r["id"] = str(r["id"])
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        if r.get("media_type") == "CAROUSEL_ALBUM":
            r["children"] = _children(c, r["id"], TH_CHILD, notes)
        r["root"] = str((r.get("root_post") or {}).get("id") or "") or None
        r["time_tw"] = tw_time(r.get("timestamp"))
        r["text40"] = head40(r.get("text"))
        r["media_urls"] = _media_urls(r)
        out.append(r)
    return out


def archive_ig(c: Client, notes: list[str]) -> list[dict]:
    rows = []
    for p in _safe_pages(c, "/me/media", IG_FULL, IG_FIELDS, notes):
        p = dict(p, id=str(p["id"]), kind=p.get("media_product_type") or "FEED")
        if p.get("media_type") == "CAROUSEL_ALBUM":
            p["children"] = _children(c, p["id"], IG_CHILD, notes)
        try:
            p["comments"] = c.pages(f"/{p['id']}/comments", limit_pages=5,
                                    fields="id,text,timestamp,username,replies{id,text,timestamp,username}")
        except ApiError as e:
            p["comments"] = None
            notes.append(f"IG {p['id']} 留言讀不到：{e}")
        p["time_tw"] = tw_time(p.get("timestamp"))
        p["text40"] = head40(p.get("caption"))
        p["media_urls"] = _media_urls(p)
        rows.append(p)
    try:
        for p in c.pages("/me/stories", fields=IG_FULL):
            rows.append(dict(p, id=str(p["id"]), kind="STORY（限動，24 小時內）", time_tw=tw_time(p.get("timestamp")),
                             text40="", media_urls=_media_urls(p)))
    except ApiError as e:
        notes.append(f"讀不到限動：{e}")
    return rows


def mark_keep(rows: list[dict], keep_from_tw: str | None, keep_ids: set[str]) -> None:
    """keep_from_tw＝'2026-11-09'：台北時間這天（含）之後發的全部保留；串文跟著它的主文走。"""
    by = {r["id"]: r for r in rows}
    for r in rows:
        k = r["id"] in keep_ids or bool(keep_from_tw and r.get("time_tw", "")[:10] >= keep_from_tw)
        root = by.get(r.get("root") or "")
        if root is not None and (root["id"] in keep_ids or (keep_from_tw and root.get("time_tw", "")[:10] >= keep_from_tw)):
            k = True
        r["keep"] = k


def download_media(rows: list[dict], media_dir: Path, plat: str, cap_mb: int = 400) -> int:
    """把圖片／影片存下來（Meta CDN 網址幾天就失效）。超過總量上限或單檔 > 60MB 就只留網址。"""
    media_dir.mkdir(parents=True, exist_ok=True)
    total, n = 0, 0
    for r in rows:
        r["media_files"] = []
        for i, u in enumerate(r.get("media_urls") or []):
            if total > cap_mb * 1024 * 1024:
                r.setdefault("media_note", "總量上限已到，只留網址")
                break
            ext = ".mp4" if ".mp4" in u.split("?")[0] else ".jpg"
            fn = f"{plat}_{r.get('time_tw', '')[:10]}_{r['id']}_{i}{ext}"
            try:
                with urllib.request.urlopen(u, timeout=60) as resp:
                    data = resp.read(60 * 1024 * 1024 + 1)
                if len(data) > 60 * 1024 * 1024:
                    continue
                (media_dir / fn).write_bytes(data)
                total += len(data)
                n += 1
                r["media_files"].append(f"media/{fn}")
            except Exception as e:  # noqa: BLE001
                r.setdefault("media_errors", []).append(f"{i}：{type(e).__name__}")
    return n


def archive_md(report: dict) -> str:
    out = [f"# 重新開始前的社群備份（{report['generated_at_tw']} 台北）", "",
           "Andy 11-09：「因為重新開始，幫我將除了今天所有內容刪除 IG Thread」。刪之前的完整備份；全文與圖片網址在 archive.json，圖檔在 media/。",
           f"保留規則：台北時間 {report['keep_from_tw']}（含）之後發的全部保留（含它們的串文）。", "",
           f"- Threads 主文 {report['count']['threads_main']}、串文／回覆 {report['count']['threads_reply']}、IG {report['count']['ig']}",
           f"- 待刪：Threads {report['count']['threads_delete']}、IG {report['count']['ig_delete']}；保留：Threads {report['count']['threads_keep']}、IG {report['count']['ig_keep']}", ""]
    for plat, key in (("Threads", "threads"), ("IG", "ig")):
        out += [f"## {plat}", "", "| 處理 | 時間（台北） | 類型 | id | 前 40 字 | 圖 | 連結 |", "|---|---|---|---|---|---|---|"]
        for r in sorted(report[key], key=lambda x: x.get("time_tw", "")):
            t = (r.get("text40") or "").replace("|", "／")
            out.append(f"| {'保留' if r['keep'] else '刪'} | {r.get('time_tw', '')} | {r.get('kind', '')} | {r['id']} | {t} | "
                       f"{len(r.get('media_urls') or [])} | {r.get('permalink', '')} |")
        out.append("")
    if report["notes"]:
        out += ["## 讀取時的注意事項", ""] + [f"- {n}" for n in report["notes"]]
    return "\n".join(out) + "\n"


def run_archive(a, env, transport) -> int:
    d = Path(a.archive_dir)
    d.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    th_rows, ig_rows = [], []
    cands = th_token_candidates(env)
    if cands:
        th_rows = archive_threads(Client(TH_API, dict(cands).get("THREADS_ACCESS_TOKEN") or cands[0][1], transport), notes)
        for name, tok in cands:
            try:
                me = Client(TH_API, tok, transport).req("GET", "/me", fields="id,username")
                notes.append(f"Threads 權杖 {name} 的帳號：@{me.get('username')}")
            except ApiError as e:
                notes.append(f"Threads 權杖 {name} 查不到帳號：{e}")
        _, _, _, perm = pick_delete_token(cands, transport)
        notes += perm
    else:
        notes.append("沒有 Threads 權杖，略過 Threads")
    ig_tok = (env.get("IG_ACCESS_TOKEN") or "").strip()
    if ig_tok:
        try:
            ig_rows = archive_ig(Client(IG_API, ig_tok, transport), notes)
        except ApiError as e:
            notes.append(f"IG 清單讀取失敗：{e}")
    keep = load_keep(Path(a.keep_file) if a.keep_file else None, a.keep_id)
    mark_keep(th_rows, a.keep_from_tw, keep["threads"])
    mark_keep(ig_rows, a.keep_from_tw, keep["ig"])
    if a.download_media:
        n = download_media(th_rows, d / "media", "th") + download_media(ig_rows, d / "media", "ig")
        notes.append(f"圖檔／影片已下載 {n} 個到 media/")
    report = {"generated_at_tw": datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M"), "keep_from_tw": a.keep_from_tw,
              "threads": th_rows, "ig": ig_rows, "notes": notes,
              "count": {"threads_main": sum(r["kind"] == "主文" for r in th_rows),
                        "threads_reply": sum(r["kind"] != "主文" for r in th_rows), "ig": len(ig_rows),
                        "threads_delete": sum(not r["keep"] for r in th_rows), "threads_keep": sum(r["keep"] for r in th_rows),
                        "ig_delete": sum(not r["keep"] for r in ig_rows), "ig_keep": sum(r["keep"] for r in ig_rows)}}
    (d / "archive.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "archive.md").write_text(archive_md(report), encoding="utf-8")
    # 刪除順序：串文先、主文後（主文先刪，底下的串文可能變成查不到）
    dels = sorted([r for r in th_rows if not r["keep"]], key=lambda r: (r["kind"] == "主文", r.get("time_tw", "")))
    (d / "threads_delete_ids.txt").write_text(
        "# 2026-11-09 重新開始：要刪的 Threads（串文先、主文後）\n" +
        "".join(f"{r['id']}  # {r['kind']} {r.get('time_tw', '')} {r.get('text40', '')}\n" for r in dels), encoding="utf-8")
    (d / "ig_delete_ids.txt").write_text(
        "# 2026-11-09 重新開始：要刪的 IG\n" +
        "".join(f"{r['id']}  # {r['kind']} {r.get('time_tw', '')} {r.get('permalink', '')}\n" for r in ig_rows if not r["keep"]),
        encoding="utf-8")
    (d / "ig_manual.md").write_text(ig_manual_md([dict(r, views=None) for r in ig_rows]), encoding="utf-8")
    c = report["count"]
    print(f"[備份完成，沒有刪任何東西] Threads 主文 {c['threads_main']}、串文／回覆 {c['threads_reply']}、IG {c['ig']}；"
          f"待刪 Threads {c['threads_delete']}、IG {c['ig_delete']}")
    for n in notes:
        print("注意：", n)
    return 0


def execute_ig(c: Client, ids: list[str], known: dict[str, dict], *, max_n: int, result_path: Path | None,
               sleep=1.0) -> list[dict]:
    """IG 試刪（Meta 2025-12 新增刪除端點，官方寫 Facebook 登入版；Instagram 登入版沒寫，所以先試，第一則就權限錯誤就整批停）。"""
    results: list[dict] = []
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
    done = 0
    for mid in ids:
        row = known.get(mid)
        if row is None:
            results.append({"id": mid, "result": "跳過（不在這個帳號的貼文清單裡）"}); continue
        if row.get("keep"):
            results.append({"id": mid, "result": "保留（今天的，不刪）"}); continue
        if done >= max_n:
            results.append({"id": mid, "result": f"未處理（本次上限 {max_n} 則）"}); continue
        try:
            b = c.req("DELETE", f"/{mid}")
            ok = bool(b.get("success", True))
            results.append({"id": mid, "result": "成功" if ok else "失敗（API 回 success=false）"})
            done += ok
        except ApiError as e:
            results.append({"id": mid, "result": f"失敗：{e}"})
            if e.fatal or e.status in (400, 403) or done == 0:
                results.append({"id": "-", "result": "IG 權杖不能刪（或被擋），整批停止，改用手動刪除清單"})
                break
        if result_path:
            result_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        _sleep(sleep)
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    return results


def _sleep(spec) -> None:
    """sleep＝數字（秒）或 'a-b'（每則隨機 a～b 秒，Andy 11-09：每刪一則間隔 5～10 秒避免限流）。"""
    if isinstance(spec, str) and "-" in spec:
        lo, hi = (float(x) for x in spec.split("-", 1))
        time.sleep(random.uniform(lo, hi))
    else:
        time.sleep(float(spec))


# ---------- 主程式 ----------

def main(argv=None, transport=urllib_transport, env=None, sleep=1.0) -> int:
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description="社群貼文刪除工具（預設只列清單）")
    ap.add_argument("--platform", choices=["all", "threads", "ig"], default="all")
    ap.add_argument("--out", default="out/social_delete/list.json", help="清單 json 輸出路徑")
    ap.add_argument("--keep-file", default=str(KEEP_FILE))
    ap.add_argument("--keep-id", action="append", default=[], help="額外保留的 id（IG 請加 ig: 前綴）")
    ap.add_argument("--no-views", action="store_true", help="不抓觀看數（快很多）")
    ap.add_argument("--no-replies", action="store_true", help="Threads 不列自己的回覆")
    ap.add_argument("--execute", action="store_true", help="真的刪（只有 Threads）")
    ap.add_argument("--ids-file", help="要刪的 Threads id 清單檔")
    ap.add_argument("--confirm", default="", help=f"必須是「{CONFIRM}」")
    ap.add_argument("--max", type=int, default=90, help="本次最多刪幾則（官方 24 小時上限 100）")
    ap.add_argument("--allow-unlisted", action="store_true", help="允許刪清單裡查不到的 id（預設跳過）")
    ap.add_argument("--result", default="out/social_delete/result.json")
    ap.add_argument("--archive-dir", help="備份模式：把全部貼文全文、圖片網址（與圖檔）存到這個資料夾，不刪任何東西")
    ap.add_argument("--keep-from-tw", help="台北日期 YYYY-MM-DD：這天（含）之後發的全部保留")
    ap.add_argument("--download-media", action="store_true", help="備份模式：連圖檔／影片一起下載")
    ap.add_argument("--sleep", default=None, help="每刪一則間隔秒數，或 '5-10'（隨機）")
    ap.add_argument("--ig-try-delete", action="store_true", help="IG 試刪（第一則權限錯誤就停）")
    a = ap.parse_args(argv)
    if a.sleep is not None:
        sleep = a.sleep
    if a.archive_dir:
        return run_archive(a, env, transport)

    keep = load_keep(Path(a.keep_file) if a.keep_file else None, a.keep_id)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    th_tok = (env.get("THREADS_DELETE_TOKEN") or env.get("THREADS_ACCESS_TOKEN") or "").strip()
    ig_tok = (env.get("IG_ACCESS_TOKEN") or "").strip()

    # ---- 真刪：先擋 ----
    if a.execute:
        if a.platform == "ig" and not a.ig_try_delete:
            print("IG（Instagram 登入版 API）官方不支援刪除貼文，請用手動刪除清單在 App 內刪。", file=sys.stderr)
            return 2
        if a.platform == "ig":
            if a.confirm != CONFIRM or not a.ids_file or not Path(a.ids_file).exists() or not ig_tok:
                print("IG 試刪缺確認字串／ids 檔／IG 權杖。一則都沒刪。", file=sys.stderr)
                return 2
            ids = read_ids(Path(a.ids_file))
            c = Client(IG_API, ig_tok, transport)
            rows, _ = list_ig(c, keep["ig"], with_views=False)
            if a.keep_from_tw:
                mark_keep(rows, a.keep_from_tw, keep["ig"])
            res = execute_ig(c, ids, {r["id"]: r for r in rows}, max_n=a.max, result_path=Path(a.result), sleep=sleep)
            ok = sum(1 for r in res if r["result"] == "成功")
            bad = sum(1 for r in res if r["result"].startswith("失敗"))
            print(f"IG 完成：成功 {ok}、失敗 {bad}；結果檔 {a.result}")
            for r in res:
                print(f"  {r['id']}：{r['result']}")
            return 0 if bad == 0 else 1
        if a.confirm != CONFIRM:
            print(f"沒有確認字串：要加 --confirm {CONFIRM}（一字不差）。一則都沒刪。", file=sys.stderr)
            return 2
        if not a.ids_file or not Path(a.ids_file).exists():
            print("缺 --ids-file 或檔案不存在。一則都沒刪。", file=sys.stderr)
            return 2
        cands = th_token_candidates(env)
        if not cands:
            print("沒有 Threads 權杖（環境變數 THREADS_DELETE_TOKEN 或 THREADS_ACCESS_TOKEN）。一則都沒刪。", file=sys.stderr)
            return 2
        ids = read_ids(Path(a.ids_file))
        name, tok, q, perm = pick_delete_token(cands, transport)
        for n in perm:
            print(f"權杖檢查：{n}")
        if not tok and a.max <= 1:
            # 2026-11-11：額度查詢（threads_publishing_limit 的 delete 欄位）回 code=10 不一定代表不能刪；
            # 只刪 1 則時改用第一把權杖實際送一次 DELETE 測試，結果寫進 result.json。
            name, tok = cands[0]
            q = {"ok": False, "used": None, "total": None, "error": "額度查詢失敗"}
            print(f"額度查詢失敗，改用 {name} 實際刪 1 則測試權限")
        if not tok:
            print(f"::error::查不到刪除額度，所有權杖都沒有 threads_delete 權限，停止（一則都沒刪）：{perm}")
            return 3
        print(f"用 {name} 來刪")
        c = Client(TH_API, tok, transport)
        remain = (q["total"] or DAILY_LIMIT) - (q["used"] or 0)
        cap = max(0, min(a.max, remain))
        print(f"刪除額度：24 小時內已用 {q['used']}／{q['total']}，本次最多刪 {cap} 則；ids 檔共 {len(ids)} 則")
        rows, _ = list_threads(c, keep["threads"], with_views=False, with_replies=not a.no_replies)
        if a.keep_from_tw:
            mark_keep(rows, a.keep_from_tw, keep["threads"])
        known = {r["id"]: r for r in rows}
        ids, rn = resolve_permalinks(ids, rows)
        for n in rn:
            print(f"網址對 id：{n}")
        res = execute_threads(c, ids, known, keep["threads"], max_n=cap, allow_unlisted=a.allow_unlisted,
                              result_path=Path(a.result), sleep=sleep)
        ok = sum(1 for r in res if r["result"] == "成功")
        bad = sum(1 for r in res if r["result"].startswith("失敗"))
        print(f"完成：成功 {ok}、失敗 {bad}、其他 {len(res) - ok - bad}；結果檔 {a.result}")
        for r in res:
            print(f"  {r['id']}：{r['result']}")
        return 0 if bad == 0 else 1

    # ---- 預設：只列清單 ----
    report: dict = {"generated_at_tw": datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M"),
                    "mode": "list（dry-run，沒有刪任何東西）", "notes": [], "threads": [], "ig": [],
                    "threads_delete_permission": None}
    if a.platform in ("all", "threads"):
        if th_tok:
            c = Client(TH_API, th_tok, transport)
            try:
                rows, notes = list_threads(c, keep["threads"], not a.no_views, not a.no_replies)
                report["threads"], report["notes"] = rows, report["notes"] + notes
            except ApiError as e:
                report["notes"].append(f"Threads 清單讀取失敗：{e}")
            q = delete_quota(c)
            report["threads_delete_permission"] = (
                f"有（24 小時內已刪 {q['used']}／上限 {q['total']}）" if q["ok"]
                else f"沒有或無法確認（權杖多半缺 threads_delete）：{q['error']}")
        else:
            report["notes"].append("沒有 Threads 權杖，略過 Threads")
    if a.platform in ("all", "ig"):
        if ig_tok:
            c = Client(IG_API, ig_tok, transport)
            try:
                rows, notes = list_ig(c, keep["ig"], not a.no_views)
                report["ig"], report["notes"] = rows, report["notes"] + notes
            except ApiError as e:
                report["notes"].append(f"IG 清單讀取失敗：{e}")
        else:
            report["notes"].append("沒有 IG 權杖，略過 IG")

    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    ids_txt = out.with_name(out.stem + "_threads_ids.txt")
    ids_txt.write_text("# 要刪的 Threads id（已扣掉保留清單）；不想刪的整行刪掉或前面加 #\n" + "".join(
        f"{r['id']}  # {r['kind']} {r['time_tw']} {r['text40']}\n" for r in report["threads"] if not r["keep"]),
        encoding="utf-8")
    ig_md = out.with_name(out.stem + "_ig_manual.md")
    ig_md.write_text(ig_manual_md(report["ig"]), encoding="utf-8")

    th, ig = report["threads"], report["ig"]
    print(f"[只列清單，沒有刪任何東西] Threads {len(th)} 則（保留 {sum(r['keep'] for r in th)}）、"
          f"IG {len(ig)} 則（保留 {sum(r['keep'] for r in ig)}）")
    print(f"Threads 刪除權限：{report['threads_delete_permission']}")
    for n in report["notes"]:
        print("注意：", n)
    print(f"輸出：{out}、{ids_txt}、{ig_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
