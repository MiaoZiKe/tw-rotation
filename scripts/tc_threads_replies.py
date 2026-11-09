"""頻道②「科技透明圈」Threads 留言關鍵字 → 公開回覆（2026-11-08）。

Andy 原話：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。
Threads API 沒有私訊、也查不到對方有沒有追蹤，所以 Threads 這邊改成「公開回覆一句＋網站連結」；
私訊＋追蹤檢查只有 IG 做得到（workers/tc-dm）。

做法：輪詢（threads_read_replies，自己帳號 Standard Access 即可；Threads webhook 才需要 Advanced Access）。
  每 15 分鐘由 tc_post.yml 跑一次：讀自己最近 N 篇貼文的留言 → 含關鍵字（social/tc/dm_config.json）→
  用 threads_manage_replies 公開回覆（reply_to_id）。每人每篇 1 次、每輪上限 max_per_run。
紀錄：state/tc/threads_replied.json 只存 sha256 雜湊（留言 id、使用者＋貼文），不存留言內容與帳號名稱；保留 30 天。
法遵閘：dm_config.json 的 legal_reviewed 不是 true → 只記錄「會回什麼」，不送出。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tc_post as T  # noqa: E402

CONFIG = ROOT / "social" / "tc" / "dm_config.json"
STATE = ROOT / "state" / "tc" / "threads_replied.json"
KEEP_DAYS = 30


def norm(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s or "").lower().split())


def h(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def matched(text: str, keywords: list[str]) -> bool:
    t = norm(text)
    return any(norm(k) and norm(k) in t for k in keywords)


def run(env: dict, now: datetime, dry_run: bool, config_path: Path = CONFIG, state_path: Path = STATE) -> tuple[int, dict]:
    cfg = T.load_json(config_path, {})
    rcfg = cfg.get("threads_reply") or {}
    res = {"replied": 0, "would_reply": 0, "seen": 0}
    tok = T.tokens_from(env)["threads"]
    if not rcfg.get("enabled"):
        T.log("Threads 關鍵字回覆：設定關閉，略過")
        return 0, res
    if not tok:
        T.log("Threads 關鍵字回覆：沒有 TC 權杖 → 安靜跳過")
        return 0, res
    send = cfg.get("legal_reviewed") is True and not dry_run
    if cfg.get("legal_reviewed") is not True:
        T.log("Threads 關鍵字回覆：文案還沒過法遵（legal_reviewed=false）→ 只記錄、不送出")
    try:
        uid, me = T.preflight("threads", tok, (env.get("TC_THREADS_USER_ID") or "").strip(),
                              (env.get("THREADS_USER_ID") or "").strip())
    except T.PostError as e:
        T.log(f"✗ Threads 關鍵字回覆：{e}")
        return 1, res
    st = T.load_json(state_path, {})
    replied, users = dict(st.get("replied") or {}), dict(st.get("users") or {})
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    replied = {k: v for k, v in replied.items() if v >= cutoff}
    users = {k: v for k, v in users.items() if v >= cutoff}
    rc, budget = 0, int(rcfg.get("max_per_run", 10))
    try:
        posts = T.api("threads", "GET", "/me/threads", tok,
                      {"fields": "id,timestamp", "limit": str(int(rcfg.get("lookback_posts", 5)))}).get("data") or []
    except T.PostError as e:
        T.log(f"✗ 讀不到自己的貼文：{e}")
        return 1, res
    for p in posts:
        try:
            rows = T.api("threads", "GET", f"/{p['id']}/replies", tok,
                         {"fields": "id,text,username,timestamp"}).get("data") or []
        except T.PostError as e:
            T.log(f"✗ 讀不到留言（多半是沒有 threads_read_replies）：{e}")
            rc = 1
            continue
        for r in rows:
            res["seen"] += 1
            if not r.get("id") or r.get("username") == me or not matched(r.get("text", ""), cfg.get("keywords") or []):
                continue
            rk, uk = h("r", r["id"]), h("u", r.get("username", ""), p["id"])
            if rk in replied or uk in users:
                continue
            if budget <= 0:
                T.log("本輪回覆數到上限，剩下的下一輪")
                break
            if not send:
                res["would_reply"] += 1
                replied[rk] = users[uk] = now.isoformat(timespec="seconds")   # 只在記憶體去重，不寫檔
                T.log(f"[只記錄] 會公開回覆 1 則留言（貼文 {p['id'][-4:]}）")
                continue
            try:
                cid = T.api("threads", "POST", f"/{uid}/threads", tok,
                            {"media_type": "TEXT", "text": rcfg["text"], "reply_to_id": r["id"]})["id"]
                T.SLEEP(5)
                T._threads_publish(uid, cid, tok)
            except T.PostError as e:
                T.log(f"✗ 公開回覆失敗：{e}")
                rc = 1
                continue
            replied[rk] = users[uk] = now.isoformat(timespec="seconds")
            budget -= 1
            res["replied"] += 1
    T.log(f"Threads 關鍵字回覆：看了 {res['seen']} 則留言，回覆 {res['replied']} 則，只記錄 {res['would_reply']} 則")
    if send and res["replied"]:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"replied": replied, "users": users}, indent=1) + "\n", encoding="utf-8")
    return rc, res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="頻道② Threads 留言關鍵字公開回覆")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return run(dict(os.environ), datetime.now(T.TAIPEI), a.dry_run)[0]


if __name__ == "__main__":
    sys.exit(main())
