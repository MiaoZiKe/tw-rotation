"""談晴說礙（頻道④）外部回覆：到別人的熱門串底下留有觀點的回覆（2026-11-25 Andy 核准④自己經營、不跨頻道導流）。

預設只產草稿、不送出：
  python scripts/healing_outreach.py --collect     取候選串寫進 outreach/drafts.json（draft 空白，待人工／總編輯補稿）
  python scripts/healing_outreach.py --probe       只讀：驗④權杖有沒有 threads_keyword_search（只印數量）
  python scripts/healing_outreach.py --send        只送 approved:true 且 lint 過的草稿；加 --live 才真的送（沒加＝只印會送什麼）
限制：每天 ≤5 則、兩則間隔 ≥10 分鐘、同一人一天 ≤1 則、同一則串只回一次、送前先查是否已回過。
重用 auto_reply／reply_lint／threads_search 的函式。送出紀錄 state/outreach_sent.json（只存雜湊與 id）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import auto_reply as AR  # noqa: E402
import reply_lint as RL  # noqa: E402
import threads_search as S  # noqa: E402

TAIPEI = timezone(timedelta(hours=8))
HEAL = ROOT / "docs" / "marketing" / "channels" / "healing"
OUT = HEAL / "outreach"
DRAFTS = OUT / "drafts.json"
TARGETS = OUT / "targets.txt"
SENT = HEAL / "state" / "outreach_sent.json"
DM_CFG = HEAL / "dm_config.json"
KEYWORDS = ("薪資", "租屋", "加班", "存款", "少子化", "房租", "低薪", "月薪")
DAILY_MAX = 5
GAP_MIN = 10
MIN_LEN, MAX_LEN = 30, 80
HARM_FALLBACK = ("自殺", "想死", "輕生", "不想活", "自殘", "割腕", "結束生命", "活不下去")
EXTRA_BAD = ("1925", "安心專線", "我們", "追蹤", "按讚")


def h(*p: str) -> str:
    return hashlib.sha1("|".join(p).encode()).hexdigest()[:12]


def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def harm_words() -> tuple:
    cfg = load_json(DM_CFG, {})
    return tuple(cfg.get("self_harm_keywords") or ()) or HARM_FALLBACK


def skip_reason(text: str) -> str:
    """對方的串該不該跳過：政治、謾罵、指控、帶網址（reply_lint）＋自傷相關。"""
    for w in harm_words():
        if w and w in (text or ""):
            return f"自傷相關（{w}）"
    return RL.skip_reason(text)


def lint(text: str, recent: list[str] | None = None) -> list[str]:
    """④版回覆檢查：30～80 字、不帶網址／導流、不預測漲跌、無黑名單與模板句、不帶標籤、不太像最近的回覆、不提自己帳號、不放 1925。
    不套 reply_lint 的個股／四碼代號規則（談晴回覆會引用薪資、租金等數字）。"""
    t = (text or "").strip()
    err: list[str] = []
    n = RL.clen(t)
    if not MIN_LEN <= n <= MAX_LEN:
        err.append(f"長度 {n} 字（要 {MIN_LEN}～{MAX_LEN}）")
    if RL.TL.has_url(t) or re.search(r"https?://|www\.|\.com|\.tw\b", t, re.I):
        err.append("帶網址")
    for w in RL.PROMO + EXTRA_BAD:
        if w.lower() in t.lower():
            err.append(f"導流／自稱／1925 字「{w}」")
    for w in RL.PREDICT:
        if w in t:
            err.append(f"預測字「{w}」")
    for w in RL.BLACK:
        if w in t:
            err.append(f"黑名單字「{w}」")
    for w in RL.TEMPLATE:
        if w in t:
            err.append(f"模板句「{w}」")
    for w in harm_words():
        if w and w in t:
            err.append(f"自傷字「{w}」")
    if re.search(r"[#＃@]", t) or "我" in t:
        err.append("不放標籤、@ 或自稱「我」")
    for r in (recent or [])[-50:]:
        if RL.similarity(t, r) >= RL.SIM_MAX:
            err.append(f"跟最近的回覆太像：{r[:20]}…")
            break
    return err


# ── 候選 ───────────────────────────────────────────────────────────────
def load_manual(path: Path = TARGETS) -> list[dict]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        try:
            mid = AR.shortcode_to_id(parts[0])
        except ValueError:
            continue
        rows.append({"target_id": mid, "permalink": parts[0], "context": (parts[1] if len(parts) > 1 else "")[:80],
                     "author": h("a", parts[2]) if len(parts) > 2 and parts[2] else h("t", mid), "source": "manual"})
    return rows


def search_candidates(token: str, me: str, keywords=KEYWORDS, search=S.search, per_kw: int = 10) -> tuple[list[dict], str]:
    """keyword_search 取熱門；權限沒過審（只搜得到自己的）回空清單與狀態。"""
    rows_all, state = [], "empty"
    for kw in keywords:
        rows, _ = search(token, kw, "TOP", per_kw)
        st = S.permission_state(rows, me)
        if st == "own_only":
            return [], st
        if st == "approved":
            state = st
        rows_all += rows
    out = []
    for r in rows_all:
        if r.get("username") == me or r.get("is_reply"):
            continue
        out.append({"target_id": str(r["id"]), "permalink": r.get("permalink", ""), "context": (r.get("text") or "")[:80],
                    "author": h("a", r.get("username") or r["id"]), "source": "search", "_text": r.get("text") or ""})
    return out, state


def collect(cands: list[dict], drafts: list[dict], sent: dict, now: datetime, cap: int = 20) -> int:
    have = {d["target_id"] for d in drafts} | {s["target_id"] for s in sent.get("sent", [])}
    n = 0
    for c in cands:
        if c["target_id"] in have or n >= cap:
            continue
        why = skip_reason(c.get("_text") or c.get("context") or "")
        if why:
            continue
        c = {k: v for k, v in c.items() if not k.startswith("_")}
        drafts.append({**c, "draft": "", "approved": False, "status": "pending", "added": now.isoformat(timespec="seconds")})
        have.add(c["target_id"])
        n += 1
    return n


# ── 送出前的限制 ────────────────────────────────────────────────────────
def day_key(t: datetime) -> str:
    return t.astimezone(TAIPEI).strftime("%Y-%m-%d")


def parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def can_send(d: dict, sent: dict, now: datetime) -> str:
    """回空字串＝可以送；否則回原因。"""
    rows = sent.get("sent", [])
    today = [r for r in rows if (parse_ts(r["ts"]) and day_key(parse_ts(r["ts"])) == day_key(now))]
    if len(today) >= DAILY_MAX:
        return f"今天已 {len(today)} 則（上限 {DAILY_MAX}）"
    last = max((parse_ts(r["ts"]) for r in rows if parse_ts(r["ts"])), default=None)
    if last and now - last < timedelta(minutes=GAP_MIN):
        return f"距上一則不到 {GAP_MIN} 分鐘"
    if any(r["author"] == d["author"] for r in today):
        return "同一個人今天已回過"
    if any(r["target_id"] == d["target_id"] for r in rows):
        return "這則串已回過"
    return ""


def _tcall(method, path, token, params=None):
    return AR.threads_call(method, path, token, params)


def post_one(d: dict, token: str, tcall=_tcall) -> str:
    return AR.post_reply({"platform": "threads", "draft": d["draft"], "target_id": d["target_id"]},
                         {"THREADS_ACCESS_TOKEN": token}, tcall=tcall)


def send(drafts: list[dict], sent: dict, now: datetime, live: bool = False, token: str = "",
         poster=post_one, checker=None, max_per_run: int = 1, sleeper=time.sleep) -> dict:
    """只處理 approved:true 的草稿。live=False（dry_run）只回「會送什麼」，不呼叫任何 API、不寫紀錄。"""
    res = {"sent": 0, "would": 0, "held": []}
    for d in drafts:
        if not d.get("approved") or d.get("status") == "sent":
            continue
        recent = [s.get("draft", "") for s in sent.get("sent", [])]
        errs = lint(d.get("draft", ""), recent)
        if errs:
            res["held"].append((d["target_id"], "; ".join(errs)))
            continue
        why = can_send(d, sent, now)
        if why:
            res["held"].append((d["target_id"], why))
            continue
        if not live:
            res["would"] += 1
            sent = {"sent": list(sent.get("sent", [])) + [{"ts": now.isoformat(), "target_id": d["target_id"], "author": d["author"]}]}
            continue
        if res["sent"] >= max_per_run:
            break
        if checker and checker(d, token):
            d["status"] = "already"
            res["held"].append((d["target_id"], "API 顯示已回過"))
            continue
        try:
            rid = poster(d, token)
        except Exception as e:  # noqa: BLE001  送不出去不重試，留給人看
            d["status"] = "failed"
            res["held"].append((d["target_id"], f"送出失敗：{str(e)[:80]}"))
            continue
        d["status"] = "sent"
        sent.setdefault("sent", []).append({"ts": now.isoformat(timespec="seconds"), "target_id": d["target_id"],
                                            "author": d["author"], "draft": d["draft"], "reply_id": rid})
        res["sent"] += 1
        now = datetime.now(timezone.utc)
    return res


def token_of(env=os.environ) -> str:
    return (env.get("HEALING_THREADS_ACCESS_TOKEN_AUTO") or env.get("HEALING_THREADS_ACCESS_TOKEN") or "").strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--live", action="store_true", help="與 --send 併用才真的送出；預設只印會送什麼")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    tok = token_of()
    drafts = load_json(DRAFTS, [])
    sent = load_json(SENT, {"sent": []})
    if a.probe or a.collect:
        if not tok:
            print("等待權杖（HEALING_THREADS_ACCESS_TOKEN），無法查")
            cands, st = [], "no_token"
        else:
            me = _tcall("GET", "/me", tok, {"fields": "id,username"}).get("username")
            try:
                cands, st = search_candidates(tok, me)
            except Exception as e:  # noqa: BLE001
                cands, st = [], "error:" + str(e)[:120]
        print(f"keyword_search 權限狀態：{st}（approved＝可用；own_only／error 403＝未過審）；候選 {len(cands)} 則")
        if a.probe and tok:
            # 2026-11-27：keyword_search 沒權限時，改驗 threads_profile_discovery（查公開帳號近期貼文），只讀只印數量
            for path, params in (("/profile_lookup", {"username": "zuck"}),
                                 ("/profile_posts", {"username": "zuck", "fields": "id,permalink", "limit": 3})):
                try:
                    r = _tcall("GET", path, tok, params)
                    n = len(r.get("data", [])) if isinstance(r, dict) and "data" in r else (1 if r else 0)
                    print(f"{path}：可用（回 {n} 筆）")
                except Exception as e:  # noqa: BLE001
                    print(f"{path}：不可用 {str(e)[:160]}")
        if a.collect:
            cands += load_manual() if not cands else []
            n = collect(cands, drafts, sent, now)
            save_json(DRAFTS, drafts)
            print(f"新增草稿位 {n} 則（draft 待補、approved=false）→ {DRAFTS}")
        return 0
    if a.send:
        res = send(drafts, sent, now, live=a.live, token=tok,
                   checker=lambda d, t: AR.already_replied({"platform": "threads", "target_id": d["target_id"]}, {"THREADS_ACCESS_TOKEN": t}))
        print(json.dumps(res, ensure_ascii=False))
        if a.live:
            save_json(DRAFTS, drafts)
            save_json(SENT, sent)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
