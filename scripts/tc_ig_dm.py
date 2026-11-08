"""頻道②「科技透明圈」IG：留言關鍵字 → 私訊 → 對方回「好了」→ 查追蹤 → 送整理（2026-11-08，輪詢版）。

Andy 原話：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。設定：social/tc/dm_config.json 的 ig_dm。

★ 為什麼是「兩段式」（Meta 規定，不是我們想繞）：
  User Profile API 的 is_user_follow_business 要「對方先傳訊息給我們、建立同意」之後才查得到；
  只有留言、沒傳過訊息的人，查了會回「User consent is required to access user profile」。
  所以不能在第一則私訊前就檢查追蹤，只能：
    第 1 段：留言含關鍵字 → Private Reply 私訊一句「追蹤後回覆『好了』」（每則留言只能私回 1 次、留言 7 天內）。
    第 2 段：對方在私訊回「好了」（這時同意成立、開了 24 小時回覆窗）→ 查 is_user_follow_business：
             true → 送整理內容；false → 回「還沒看到你追蹤喔」（每人每天最多 3 次，避免洗版）。

兩種收件方式，用 dm_config.json 的 ig_dm.mode 切換（同時只開一種，避免重複送）：
  "poll"（預設，本程式）：tc_post.yml 每 15 分鐘讀留言與私訊。好處：不用 webhook，所以不需要「comments／messages webhook」
        要求的 App 上線（Live）與 Advanced Access；壞處：最多延遲約 15 分鐘。
  "webhook"（workers/tc-dm）：Meta 即時推送；要 App Live＋Advanced Access（App Review），送審資料在
        docs/marketing/channels/tc/app_review/。審過後把 mode 改成 "webhook"，本程式就自動停手。

去重與隱私：state/tc/ig_dm.json 只存 sha256 雜湊（留言 id、使用者 id）、時間與結果，不存留言內容、帳號名稱、私訊內容。
上限：每則留言 1 次（Meta 也只准 1 次）；每人每天 per_user_per_day 次私訊；每輪 max_per_minute 則（輪詢一輪當一分鐘算）。
法遵閘：legal_reviewed 不是 true → 只記錄「會送什麼」，不送。
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
STATE = ROOT / "state" / "tc" / "ig_dm.json"
POSTED = ROOT / "state" / "tc" / "posted.json"
REPLY_WINDOW = timedelta(days=7)
KEEP_DAYS = 30
NOT_FOLLOW_MAX_PER_DAY = 3


def norm(s: str) -> str:
    return "".join(unicodedata.normalize("NFKC", s or "").lower().split())


def h(*p: str) -> str:
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()[:24]


def has_kw(text: str, kws) -> bool:
    t = norm(text)
    return any(norm(k) and norm(k) in t for k in kws or [])


def ts(s) -> datetime | None:
    if not s:
        return None
    s = str(s).replace("Z", "+00:00")
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def send(uid: str, tok: str, recipient: dict, text: str) -> None:
    T.api("ig", "POST", f"/{uid}/messages", tok,
          {"recipient": json.dumps(recipient), "message": json.dumps({"text": text}, ensure_ascii=False)})


def run(env: dict, now: datetime, dry_run: bool, config_path: Path = CONFIG, state_path: Path = STATE,
        posted_path: Path = POSTED) -> tuple[int, dict]:
    cfg = T.load_json(config_path, {})
    d = cfg.get("ig_dm") or {}
    res = {"prompted": 0, "delivered": 0, "not_following": 0, "would": 0, "skipped": 0}
    if not d.get("enabled"):
        T.log("IG 私訊：設定關閉，略過")
        return 0, res
    if d.get("mode", "poll") != "poll":
        T.log("IG 私訊：mode 不是 poll（改由 Worker 即時處理），輪詢版不動作")
        return 0, res
    tok = T.tokens_from(env)["ig"]
    if not tok:
        T.log("IG 私訊：沒有 TC 權杖 → 安靜跳過")
        return 0, res
    live = cfg.get("legal_reviewed") is True and not dry_run
    if cfg.get("legal_reviewed") is not True:
        T.log("IG 私訊：文案還沒過法遵（legal_reviewed=false）→ 只記錄、不送出")
    try:
        uid, handle = T.preflight("ig", tok, (env.get("TC_IG_USER_ID") or "").strip(), (env.get("IG_USER_ID") or "").strip())
    except T.PostError as e:
        T.log(f"✗ IG 私訊：{e}")
        return 1, res
    fill = lambda s: (s or "").replace("{handle}", handle)  # noqa: E731
    st = T.load_json(state_path, {})
    comments, users, pending, msgs = (dict(st.get(k) or {}) for k in ("comments", "users", "pending", "msgs"))
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    for tbl in (comments, msgs):
        for k in [k for k, v in tbl.items() if str(v.get("at", "")) < cutoff]:
            tbl.pop(k)
    today = now.astimezone(T.TAIPEI).strftime("%Y-%m-%d")
    users = {k: v for k, v in users.items() if v.get("day") == today}
    budget, per_user = int(d.get("max_per_minute", 10)), int(d.get("per_user_per_day", 1))
    post_of = {str(e.get("ig_id") or e.get("ids_ig") or ""): e.get("id") for e in (T.load_json(posted_path, {}).get("posts") or [])}
    rc = 0

    # ---- 第 1 段：留言 → Private Reply ----
    try:
        media = T.api("ig", "GET", f"/{uid}/media", tok, {"fields": "id,timestamp", "limit": "10"}).get("data") or []
    except T.PostError as e:
        T.log(f"✗ 讀不到自己的貼文：{e}")
        return 1, res
    for m in media:
        try:
            rows = T.api("ig", "GET", f"/{m['id']}/comments", tok,
                         {"fields": "id,text,timestamp,from{id,username}", "limit": "50"}).get("data") or []
        except T.PostError as e:
            T.log(f"✗ 讀不到留言（多半是沒有 instagram_business_manage_comments）：{e}")
            rc = 1
            continue
        for c in rows:
            who = str((c.get("from") or {}).get("id") or "")
            if not c.get("id") or not who or who == uid or not has_kw(c.get("text", ""), cfg.get("keywords")):
                continue
            ck, uk = h("c", c["id"]), h("u", who)
            if ck in comments:
                continue
            t = ts(c.get("timestamp"))
            if t and now - t > REPLY_WINDOW:
                comments[ck] = {"at": now.isoformat(timespec="seconds"), "result": "expired"}
                continue
            if users.get(uk, {}).get("n", 0) >= per_user or budget <= 0:
                res["skipped"] += 1
                continue
            if not live:
                res["would"] += 1
                T.log("[只記錄] 會私回 1 則留言（第 1 段：請對方追蹤後回『好了』）；不寫紀錄，法遵通過後照樣會送")
                continue
            try:
                send(uid, tok, {"comment_id": c["id"]}, fill(d.get("prompt")))
            except T.PostError as e:
                T.log(f"✗ 私回失敗：{e}")
                rc = 1
                continue
            comments[ck] = {"at": now.isoformat(timespec="seconds"), "result": "prompted"}
            users[uk] = {"day": today, "n": users.get(uk, {}).get("n", 0) + 1}
            pending[uk] = {"post": post_of.get(str(m["id"])) or "default", "at": now.isoformat(timespec="seconds"),
                           "sent": False, "nf": {}}
            budget -= 1
            res["prompted"] += 1

    # ---- 第 2 段：對方回「好了」→ 查追蹤 → 送內容 ----
    try:
        convs = T.api("ig", "GET", "/me/conversations", tok,
                      {"platform": "instagram", "fields": "id,updated_time", "limit": "20"}).get("data") or []
    except T.PostError as e:
        T.log(f"✗ 讀不到私訊（多半是沒有 instagram_business_manage_messages）：{e}")
        convs, rc = [], 1
    for cv in convs:
        u = ts(cv.get("updated_time"))
        if u and now - u > timedelta(hours=24):           # 24 小時回覆窗外的不處理
            continue
        try:
            ms = (T.api("ig", "GET", f"/{cv['id']}", tok, {"fields": "messages.limit(5){id,from,message,created_time}"})
                  .get("messages") or {}).get("data") or []
        except T.PostError as e:
            T.log(f"✗ 讀不到對話：{e}")
            rc = 1
            continue
        for msg in ms:                                    # Meta 由新到舊排；只看對方傳的
            who = str((msg.get("from") or {}).get("id") or "")
            if not who or who == uid:
                continue
            mk, uk = h("m", msg.get("id", "")), h("u", who)
            if mk in msgs or uk not in pending or not has_kw(msg.get("message", ""), d.get("followed_keywords")):
                break
            p = pending[uk]
            if not live:
                res["would"] += 1
                break
            msgs[mk] = {"at": now.isoformat(timespec="seconds")}
            try:
                if p.get("sent"):
                    send(uid, tok, {"id": who}, fill(d.get("already_sent")))
                    break
                prof = T.api("ig", "GET", f"/{who}", tok, {"fields": "is_user_follow_business"})
                if prof.get("is_user_follow_business") is True:
                    body = (d.get("contents") or {}).get(p.get("post")) or (d.get("contents") or {}).get("default", "")
                    send(uid, tok, {"id": who}, body)
                    p["sent"] = True
                    res["delivered"] += 1
                elif p.get("nf", {}).get(today, 0) < NOT_FOLLOW_MAX_PER_DAY:
                    send(uid, tok, {"id": who}, fill(d.get("not_following")))
                    p.setdefault("nf", {})[today] = p.get("nf", {}).get(today, 0) + 1
                    res["not_following"] += 1
            except T.PostError as e:
                T.log(f"✗ 第 2 段失敗：{e}")
                msgs.pop(mk, None)
                rc = 1
            break
    T.log(f"IG 私訊：第 1 段私回 {res['prompted']}、送出整理 {res['delivered']}、提醒追蹤 {res['not_following']}、只記錄 {res['would']}")
    if not dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        new = {"comments": comments, "users": users, "pending": pending, "msgs": msgs}
        if new != {k: st.get(k) or {} for k in new}:
            state_path.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return rc, res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="頻道② IG 留言關鍵字私訊（輪詢版）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return run(dict(os.environ), datetime.now(T.TAIPEI), a.dry_run)[0]


if __name__ == "__main__":
    sys.exit(main())
