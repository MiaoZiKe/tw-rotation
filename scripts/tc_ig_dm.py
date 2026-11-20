"""頻道②「科技透明圈」IG：留言關鍵字 → 私訊 → 對方回「好了」→ 查追蹤 → 送整理（2026-11-08，輪詢版）。

Andy 原話：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。設定：social/tc/dm_config.json 的 ig_dm。

★ 為什麼是「兩段式」（Meta 規定，不是我們想繞）：
  User Profile API 的 is_user_follow_business 要「對方先傳訊息給我們、建立同意」之後才查得到；
  只有留言、沒傳過訊息的人，查了會回「User consent is required to access user profile」。
  所以不能在第一則私訊前就檢查追蹤，只能：
    第 1 段：留言含關鍵字 → Private Reply 私訊一句「追蹤後回覆『好了』」（每則留言只能私回 1 次、留言 7 天內）。
    第 2 段：對方在私訊回「好了」（這時同意成立、開了 24 小時回覆窗）→ 查 is_user_follow_business：
             true → 送整理內容；false → 回「還沒看到你追蹤喔」（每人每天最多 3 次，避免洗版）。

follow_gate（2026-11-09 法遵審後加的開關，預設 true）：
  true  → 上面的兩段式（Andy 指示：私訊前要檢查追蹤）。法遵查不到 Meta 明文禁止「以追蹤為條件」，信心低，屬未確認風險。
  false → 法遵給的替代做法：不查追蹤，留言後直接私回重點（prompt_no_gate＋重點內容），追蹤只當鼓勵。
          ★ Meta 規定每則留言只能私回 1 則、對方回覆前不能再傳，所以開頭句和重點內容是合在同一則送出。

兩種收件方式，用 dm_config.json 的 ig_dm.mode 切換（同時只開一種，避免重複送）：
  "poll"（預設，本程式）：tc_post.yml 每 15 分鐘讀留言與私訊。好處：不用 webhook，所以不需要「comments／messages webhook」
        要求的 App 上線（Live）與 Advanced Access；壞處：最多延遲約 15 分鐘。
  "webhook"（workers/tc-dm）：Meta 即時推送；要 App Live＋Advanced Access（App Review），送審資料在
        docs/marketing/channels/tc/app_review/。審過後把 mode 改成 "webhook"，本程式就自動停手。

★ EAA 系統用戶權杖（2026-11-10 頻道④交接 TECH_*，帳號 @tech_01010909）：
  讀留言走 graph.facebook.com 的 /{media}/comments（權杖有 instagram_manage_comments）。
  但私訊（Private Reply、回覆私訊、查追蹤）在 Facebook 這條路上是 Messenger Platform：要「IG 連結的粉絲專頁」與
  「專頁權杖」，端點是 /{page-id}/messages、/{page-id}/conversations?platform=instagram。
  權杖看得到連結本帳號的粉絲專頁 → 用專頁權杖照樣跑兩段式；看不到 → **做不到**，只記錄「需要粉絲專頁」，安靜跳過（不紅燈）。

去重與隱私：state/tc/ig_dm.json 只存 sha256 雜湊（留言 id、使用者 id）、時間與結果，不存留言內容、帳號名稱、私訊內容。
上限：每則留言 1 次（Meta 也只准 1 次）；每人每天 per_user_per_day 次私訊；每輪 max_per_minute 則（輪詢一輪當一分鐘算）。
法遵閘：legal_reviewed 不是 true → 只記錄「會送什麼」，不送。

每篇專屬關鍵字（2026-11-15，Andy：「往後製作影片後面可以補上 留言『XXXX』我就把資訊傳給他，IG Thread 都是」）：
  比對字＝全域 keywords＋post_keywords[貼文代號]（IG 貼文 id → 代號用 state/tc/posted.json 的 ids_ig）；
  送的內容＝ig_dm.contents[代號]，沒有或還有「待填」就用 default。規則在 scripts/tc_dm_keys.py。

★ 私訊接不通時的保底（public_fallback，預設 true）：
  EAA 權杖看不到粉絲專頁 → 私訊做不到。以前是整段安靜跳過，留言的人什麼都收不到（文案寫了卻沒兌現）。
  現在改成「公開回覆那則留言一句＋文章連結」（POST /{comment-id}/replies，權杖本來就有 instagram_manage_comments），
  文字跟 Threads 同一份（threads_reply.texts[代號] → threads_reply.text），清單就用留言 id 雜湊輪流挑一句。
  每則留言 1 次、每人每篇 1 次；防洗版：每輪（＝每分鐘）最多 public_max_per_minute（3）則、
  每篇每小時最多 public_max_per_post_hour（30）則，超過的留到下一輪（不丟、不算失敗）。
  每篇每小時的計數只存「貼文 id 雜湊 → 回覆時間」，1 小時後清掉。
  私訊一接通（權杖看得到連結的粉絲專頁）就自動改回私訊流程，不用改設定。
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
import tc_dm_keys as K  # noqa: E402
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
    return K.has_kw(text, kws)


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


def content_of(d: dict, post: str, pending=None, key: str = "") -> str:
    c = d.get("contents") or {}
    return K.with_unlock(K.text_for(c, post, c.get("default", ""), pending, key), os.environ.get("TC_UNLOCK_CODE", ""))


def public_text(cfg: dict, post: str, cid: str = "") -> str:
    r = cfg.get("threads_reply") or {}
    return K.text_for(r.get("texts"), post, r.get("text", ""), cfg.get("legal_pending"), cid)


CTX: dict = {}


def messaging_ctx(uid: str, tok: str) -> tuple[dict | None, str]:
    """私訊要用哪個端點與權杖。IG 登入版（IGAA）：/{uid}/messages、/me/conversations、同一把權杖。
    EAA：要找到連結本 IG 帳號的粉絲專頁與專頁權杖（重用 healing_post.fb_pages），找不到回 (None, 原因)。"""
    if not T.is_fb_token(tok):
        return {"send": f"/{uid}/messages", "conv": "/me/conversations", "tok": tok}, ""
    try:
        import healing_post as HP  # noqa: PLC0415
        pages = [x for x in HP.fb_pages(tok, with_token=True) if x.get("ig_id") == uid and x.get("page_token")]
    except Exception as e:  # noqa: BLE001
        return None, f"查不到粉絲專頁（{T.redact(e)[:120]}）"
    if not pages:
        return None, ("EAA 系統用戶權杖看不到連結本 IG 帳號的粉絲專頁：IG 私訊（Private Reply、查追蹤）在 Facebook 這條路上"
                      "要用 Messenger Platform（粉絲專頁＋專頁權杖），目前做不到")
    pg = pages[0]
    T.mask(pg["page_token"])
    return {"send": f"/{pg['page_id']}/messages", "conv": f"/{pg['page_id']}/conversations", "tok": pg["page_token"]}, ""


def send(uid: str, tok: str, recipient: dict, text: str) -> None:
    c = CTX or {"send": f"/{uid}/messages", "tok": tok}
    T.api("ig", "POST", c["send"], c["tok"],
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
    ctx, why = messaging_ctx(uid, tok)
    public = False
    if ctx is None:
        res["unsupported"] = why
        if d.get("public_fallback", True) is False:
            T.log(f"IG 私訊：{why} → 安靜跳過（public_fallback 關閉；讀留言、發文不受影響）")
            return 0, res
        T.log(f"IG 私訊：{why} → 改用保底：公開回覆留言＋連結")
        public = True
        res["public"] = 0
    else:
        CTX.clear()
        CTX.update(ctx)
    fill = lambda s: (s or "").replace("{handle}", handle)  # noqa: E731
    st = T.load_json(state_path, {})
    comments, users, pending, msgs = (dict(st.get(k) or {}) for k in ("comments", "users", "pending", "msgs"))
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    for tbl in (comments, msgs, pending):
        for k in [k for k, v in tbl.items() if str(v.get("at", "")) < cutoff]:
            tbl.pop(k)
    today = now.astimezone(T.TAIPEI).strftime("%Y-%m-%d")
    users = {k: v for k, v in users.items() if v.get("day") == today}
    budget, per_user = int(d.get("max_per_minute", 10)), int(d.get("per_user_per_day", 1))
    if public:
        budget = min(budget, int(d.get("public_max_per_minute", 3)))
    per_hour = int(d.get("public_max_per_post_hour", 30))
    hour_ago = (now - timedelta(hours=1)).isoformat(timespec="seconds")
    rate = {k: [x for x in v if x >= hour_ago] for k, v in dict(st.get("rate") or {}).items()}
    rate = {k: v for k, v in rate.items() if v}
    post_of = {str(e.get("ig_id") or e.get("ids_ig") or ""): e.get("id") for e in (T.load_json(posted_path, {}).get("posts") or [])}
    rc = 0

    # ---- 第 1 段：留言 → Private Reply ----
    try:
        media = T.api("ig", "GET", f"/{uid}/media", tok, {"fields": "id,timestamp", "limit": "10"}).get("data") or []
    except T.PostError as e:
        T.log(f"✗ 讀不到自己的貼文：{e}")
        return 1, res
    for m in media:
        post = post_of.get(str(m["id"])) or "default"
        kws = K.keywords_for(cfg, post)
        try:
            rows = T.api("ig", "GET", f"/{m['id']}/comments", tok,
                         {"fields": "id,text,timestamp,from{id,username}", "limit": "50"}).get("data") or []
        except T.PostError as e:
            T.log(f"✗ 讀不到留言（多半是沒有 instagram_business_manage_comments）：{e}")
            rc = 1
            continue
        for c in rows:
            who = str((c.get("from") or {}).get("id") or "")
            if not c.get("id") or not who or who == uid or not has_kw(c.get("text", ""), kws):
                continue
            ck, uk = h("c", c["id"]), h("u", who)
            pk = h("up", who, m["id"])
            if ck in comments or (public and pk in comments):
                continue
            t = ts(c.get("timestamp"))
            if t and now - t > REPLY_WINDOW:
                comments[ck] = {"at": now.isoformat(timespec="seconds"), "result": "expired"}
                continue
            if (not public and users.get(uk, {}).get("n", 0) >= per_user) or budget <= 0:   # 公開回覆改用每人每篇 1 次（pk）
                res["skipped"] += 1
                continue
            if not live:
                res["would"] += 1
                T.log("[只記錄] 會" + ("公開回覆" if public else "私回") + " 1 則留言；不寫紀錄，法遵通過後照樣會送")
                continue
            if public:
                mh = h("m", m["id"])
                if len(rate.get(mh, [])) >= per_hour:
                    res["skipped"] += 1
                    continue
                try:
                    T.api("ig", "POST", f"/{c['id']}/replies", tok, {"message": public_text(cfg, post, c["id"])})
                except T.PostError as e:
                    T.log(f"✗ IG 公開回覆失敗：{e}")
                    rc = 1
                    continue
                comments[ck] = comments[pk] = {"at": now.isoformat(timespec="seconds"), "result": "public"}
                rate.setdefault(mh, []).append(now.isoformat(timespec="seconds"))
                users[uk] = {"day": today, "n": users.get(uk, {}).get("n", 0) + 1}
                budget -= 1
                res["public"] += 1
                continue
            gate = d.get("follow_gate", True) is not False
            body = fill(d.get("prompt")) if gate else (
                fill(d.get("prompt_no_gate")) + "\n\n" + content_of(d, post, cfg.get("legal_pending"), c["id"]))
            try:
                send(uid, tok, {"comment_id": c["id"]}, body)
            except T.PostError as e:
                T.log(f"✗ 私回失敗：{e}")
                rc = 1
                continue
            comments[ck] = {"at": now.isoformat(timespec="seconds"), "result": "prompted"}
            users[uk] = {"day": today, "n": users.get(uk, {}).get("n", 0) + 1}
            pending[uk] = {"post": post, "at": now.isoformat(timespec="seconds"), "sent": not gate, "nf": {}}
            budget -= 1
            res["prompted"] += 1

    # ---- 第 2 段：對方回「好了」→ 查追蹤 → 送內容（私訊接不通時沒有第 2 段）----
    convs: list = []
    try:
        if not public:
            convs = T.api("ig", "GET", CTX["conv"], CTX["tok"],
                          {"platform": "instagram", "fields": "id,updated_time", "limit": "20"}).get("data") or []
    except T.PostError as e:
        T.log(f"✗ 讀不到私訊（多半是沒有 instagram_business_manage_messages）：{e}")
        convs, rc = [], 1
    for cv in convs:
        u = ts(cv.get("updated_time"))
        if u and now - u > timedelta(hours=24):           # 24 小時回覆窗外的不處理
            continue
        try:
            ms = (T.api("ig", "GET", f"/{cv['id']}", CTX["tok"], {"fields": "messages.limit(5){id,from,message,created_time}"})
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
                prof = T.api("ig", "GET", f"/{who}", CTX["tok"], {"fields": "is_user_follow_business"})
                if prof.get("is_user_follow_business") is True:
                    send(uid, tok, {"id": who}, content_of(d, p.get("post"), cfg.get("legal_pending")))
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
    if public:
        T.log(f"IG 保底公開回覆：{res['public']} 則")
    T.log(f"IG 私訊：第 1 段私回 {res['prompted']}、送出整理 {res['delivered']}、提醒追蹤 {res['not_following']}、只記錄 {res['would']}")
    if not dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        new = {"comments": comments, "users": users, "pending": pending, "msgs": msgs, "rate": rate}
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
