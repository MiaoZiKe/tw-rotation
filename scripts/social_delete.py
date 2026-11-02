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
        time.sleep(sleep)
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
    a = ap.parse_args(argv)

    keep = load_keep(Path(a.keep_file) if a.keep_file else None, a.keep_id)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    th_tok = (env.get("THREADS_DELETE_TOKEN") or env.get("THREADS_ACCESS_TOKEN") or "").strip()
    ig_tok = (env.get("IG_ACCESS_TOKEN") or "").strip()

    # ---- 真刪：先擋 ----
    if a.execute:
        if a.platform == "ig":
            print("IG（Instagram 登入版 API）官方不支援刪除貼文，請用手動刪除清單在 App 內刪。", file=sys.stderr)
            return 2
        if a.confirm != CONFIRM:
            print(f"沒有確認字串：要加 --confirm {CONFIRM}（一字不差）。一則都沒刪。", file=sys.stderr)
            return 2
        if not a.ids_file or not Path(a.ids_file).exists():
            print("缺 --ids-file 或檔案不存在。一則都沒刪。", file=sys.stderr)
            return 2
        if not th_tok:
            print("沒有 Threads 權杖（環境變數 THREADS_DELETE_TOKEN 或 THREADS_ACCESS_TOKEN）。一則都沒刪。", file=sys.stderr)
            return 2
        ids = read_ids(Path(a.ids_file))
        c = Client(TH_API, th_tok, transport)
        q = delete_quota(c)
        if not q["ok"]:
            print(f"::error::查不到刪除額度，多半是權杖沒有 threads_delete 權限，停止（一則都沒刪）：{q['error']}")
            return 3
        remain = (q["total"] or DAILY_LIMIT) - (q["used"] or 0)
        cap = max(0, min(a.max, remain))
        print(f"刪除額度：24 小時內已用 {q['used']}／{q['total']}，本次最多刪 {cap} 則；ids 檔共 {len(ids)} 則")
        rows, _ = list_threads(c, keep["threads"], with_views=False, with_replies=not a.no_replies)
        known = {r["id"]: r for r in rows}
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
