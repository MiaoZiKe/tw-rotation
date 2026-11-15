"""頻道④「談晴說礙」IG：讀主留言 → 檢查有沒有追蹤 → 自動私訊（Private Replies）。

2026-11-08 Andy：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。
說明文件：docs/marketing/channels/healing/comment_dm.md

用法：
  python scripts/healing_comments.py [--dry-run]

流程（輪詢，不用 webhook）：
  1. 貼文來源：state/posted.json 近 N 天的 IG 貼文 id ＋ GET /{ig-user-id}/media（近 N 天，含手動發的）。
  2. 每則貼文 GET /{media_id}/comments?fields=id,text,timestamp,from{id,username},username（只有主留言）。
  3. 每則新留言（state/comments_dm.json 以 comment_id 雜湊去重）：
       自己帳號的留言 → 略過
       自傷關鍵字     → 不送一般私訊，改送關懷資源訊息（不看追蹤），摘要提醒 CEO（legal.md 2-7）
       查追蹤 GET /{igsid}?fields=is_user_follow_business
         true  → Private Reply：POST /{ig-user-id}/messages recipient={"comment_id": ...}
         false → 不私訊，只記錄
         查不到 → 依 dm_config.json 的 unknown_follow（預設 skip）
  4. 留言超過 7 天（Meta 私回期限）→ 記錄 expired，不送。

隱私：state 只存 comment_id 的 SHA-256 前 16 碼、時間、結果；不存留言全文、使用者名稱、使用者編號。
權杖：只從環境變數讀（HEALING_IG_ACCESS_TOKEN_AUTO 優先，其次 HEALING_IG_ACCESS_TOKEN），輸出一律過 redact。
沒有權杖：空跑、結束碼 0，摘要寫「等待權杖」。

2026-11-09 多頻道（Andy：「幫忙協助其他頻道 一起建立 Tech_01010909 Shrimp_01010909 caffaine.ai」）：
  python scripts/healing_comments.py --channel tech [--dry-run]
  頻道清單 docs/marketing/channels/channels.json（prefix、state、dm_config）；只讀 <前綴>IG_ACCESS_TOKEN(_AUTO)。
  新三個頻道的 dm_config.json 預設 enabled=false（Andy 還沒定私訊內容）；enabled=true 但 message 空白 → 不私訊、紅燈提醒。
  不給 --channel 就是頻道④，行為不變。工作流：頻道④ healing_comments.yml；其他頻道 channel_comments.yml。

2026-11-16 每篇專屬留言關鍵字（照頻道② scripts/tc_ig_dm.py 的思路，見 comment_dm.md 第九節）：
  佇列 meta.json 設 "comment_keyword": "結婚"（字串或清單）→ 只在那一篇觸發；dm_config.json 的
  keyword_replies[關鍵字] = {"dm": 私訊全文, "public": [公開回覆 2～3 句，依留言 id 雜湊固定輪流]}。
  IG 貼文 id → 佇列資料夾用 state/posted.json（鍵＝資料夾名，值 ig.id／threads.id）。
  判斷順序：自傷關鍵字（照舊最優先，送關懷訊息）→ 專屬關鍵字 → 一般問候（照舊）。
  專屬關鍵字：
    私訊接得通 且 查得到有追蹤 → 私訊 keyword_replies.dm（只私訊有追蹤者，規則照舊）
    沒追蹤／查不到追蹤／私訊接不通（EAA 權杖看不到粉絲專頁）／私訊送出失敗
      → 保底：公開回覆那則留言一句（POST /{comment-id}/replies），內容是數字摘要＋出處所在＋網站文章網址
    每人每篇 1 次；公開回覆每輪最多 public_max_per_run、每篇每小時最多 public_max_per_post_hour，超過的留到下一輪。
  內容還有「待填」→ 不送半成品，改用 keyword_default_public（保底，一定有回）。
  Threads（沒有私訊 API、查不到追蹤）：只對設了 comment_keyword 的貼文，讀留言 → 公開回覆同一份 public 文字；
    自傷關鍵字不自動回、只提醒 CEO。紀錄 state/threads_replied.json（只存雜湊）。
  --dry-run 會多做一次只讀的「能力檢查」（debug_token 權限、粉絲專頁數、私訊接不接得通），不送任何東西。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_publish as SP  # noqa: E402  共用 http()／redact()／resolve_user_id()

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "docs" / "marketing" / "channels" / "healing"
CONFIG = CH / "dm_config.json"
STATE = CH / "state" / "comments_dm.json"
POSTED = CH / "state" / "posted.json"
IG = SP.IG_HOST            # https://graph.instagram.com/v24.0（Instagram 登入版 IGAA 權杖）
FB = "https://graph.facebook.com/v24.0"   # Facebook 登入版 EAA 權杖（2026-11-10 起兩種都吃）
_PAGE: dict = {}           # EAA：使用者權杖 → {page_id, page_token}（私訊、查追蹤要用專頁權杖；只在記憶體）
TAIPEI = timezone(timedelta(hours=8))
REPLY_WINDOW = timedelta(days=7)
MAX_SEND_TRIES = 3         # 私訊送出失敗最多重試幾輪（每則留言 Meta 只准私回 1 次）
KEEP_DAYS = 30             # state 只留 30 天的紀錄

DEFAULT_CFG = {
    "enabled": True, "only_followers": True, "unknown_follow": "skip", "max_per_run": 20,
    "lookback_days": 7, "message": "", "care_enabled": True, "care_message": "",
    "self_harm_keywords": [], "self_harm_exclude": [],
    "keyword_replies": {}, "keyword_default_public": "", "keyword_public_fallback": True,
    "public_max_per_run": 10, "public_max_per_post_hour": 30, "threads_reply": {},
}
PLACEHOLDER = "待填"
THREADS_STATE_NAME = "threads_replied.json"


# ---------- 小工具 ----------
def load_json(p: Path, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_cfg(p: Path = CONFIG) -> dict:
    cfg = dict(DEFAULT_CFG)
    cfg.update({k: v for k, v in load_json(p, {}).items() if not k.startswith("_")})
    return cfg


def h(cid: str) -> str:
    return hashlib.sha256(str(cid).encode("utf-8")).hexdigest()[:16]


def parse_ts(s) -> datetime | None:
    if not s:
        return None
    s = str(s).replace("Z", "+00:00")
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":      # Meta 給 +0000 這種
        s = s[:-2] + ":" + s[-2:]
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


PREFIX = "HEALING_"
CHANNELS_FILE = ROOT / "docs" / "marketing" / "channels" / "channels.json"


def _pfx(prefix: str | None) -> str:
    import re
    prefix = PREFIX if prefix is None else prefix
    if not re.fullmatch(r"[A-Z]+_", prefix or ""):      # 空前綴＝頻道①的權杖名稱，絕不准
        raise ValueError(f"權杖前綴要是大寫英文加底線（例如 TECH_），目前是 {prefix!r}")
    return prefix


def get_token(env: dict, prefix: str | None = None) -> str:
    """只讀這個頻道自己前綴的 IG 權杖（預設頻道④）；_AUTO（續期寫回）優先。"""
    p = _pfx(prefix)
    return (env.get(p + "IG_ACCESS_TOKEN_AUTO") or "").strip() or (env.get(p + "IG_ACCESS_TOKEN") or "").strip()


def channel_paths(code: str, path: Path = CHANNELS_FILE) -> dict:
    """channels.json 的頻道 → {name, prefix, cfg, state, posted}（絕對路徑）。"""
    d = load_json(path, {}).get("channels") or {}
    if code not in d:
        raise SystemExit(f"沒有這個頻道：{code}（channels.json 有 {'、'.join(d)}）")
    c = d[code]
    st = ROOT / c["state"]
    return {"code": code, "name": c.get("name", code), "prefix": _pfx(c["prefix"]),
            "cfg": ROOT / c.get("dm_config", str(Path(c["state"]).parent / "dm_config.json")),
            "state": st / "comments_dm.json", "posted": st / "posted.json"}


def is_self_harm(text: str, cfg: dict) -> bool:
    t = "".join(str(text or "").split())
    for x in cfg.get("self_harm_exclude") or []:
        t = t.replace(x, "")
    return any(k and k in t for k in cfg.get("self_harm_keywords") or [])


def iso_week(d: datetime) -> str:
    y, w, _ = d.astimezone(TAIPEI).isocalendar()
    return f"{y}-W{w:02d}"


# ---------- 每篇專屬留言關鍵字（2026-11-16）----------
def norm(s: str) -> str:
    import unicodedata
    return "".join(unicodedata.normalize("NFKC", str(s or "")).lower().split())


def queue_dir(posted_path: Path) -> Path:
    """state/posted.json → 同一頻道的 queue/。"""
    return Path(posted_path).parent.parent / "queue"


def post_keywords(folder: str, queue: Path) -> list[str]:
    """佇列 meta.json 的 comment_keyword（字串或清單）；沒有回 []。"""
    if not folder:
        return []
    v = load_json(Path(queue) / folder / "meta.json", {}).get("comment_keyword")
    v = [v] if isinstance(v, str) else (v or [])
    return [str(x).strip() for x in v if str(x).strip()]


def media_folders(posted: dict, platform: str = "ig") -> dict:
    """posted.json → {平台貼文 id: 佇列資料夾名}。"""
    out = {}
    for k, v in (posted or {}).items():
        x = v.get(platform) if isinstance(v, dict) else None
        if isinstance(x, dict) and x.get("id"):
            out[str(x["id"])] = k
    return out


def match_kw(text: str, kws: list[str]) -> str:
    t = norm(text)
    return next((k for k in kws if norm(k) and norm(k) in t), "")


def ready(v) -> bool:
    if isinstance(v, list):
        return bool(v) and all(ready(x) for x in v)
    return bool(str(v or "").strip()) and PLACEHOLDER not in str(v)


def rotate(v, key: str = "") -> str:
    """清單 → 依 key（留言 id）的 sha256 固定挑一句（防洗版）；字串原樣回。"""
    if not isinstance(v, list):
        return str(v or "")
    return v[int(hashlib.sha256(str(key).encode()).hexdigest(), 16) % len(v)] if v else ""


def kw_texts(cfg: dict, kw: str, key: str = "") -> tuple[str, str]:
    """(私訊全文, 公開回覆一句)。沒設或還有「待填」→ 私訊空白（不私訊）、公開回覆用 keyword_default_public。"""
    rep = (cfg.get("keyword_replies") or {}).get(kw) or {}
    dm = rep.get("dm") if ready(rep.get("dm")) else ""
    pub = rep.get("public") if ready(rep.get("public")) else cfg.get("keyword_default_public")
    return rotate(dm, key), rotate(pub, key)


def cta_keywords(caption: str) -> list[str]:
    """文案裡「留言「X」」的 X（交件檢查用，tests 會查佇列）。"""
    import re
    return re.findall(r"留言「([^」]+)」", caption or "")


# ---------- Meta API ----------
def _ig(token: str) -> str:
    return FB if (token or "").startswith("EAA") else IG


def me(token: str, prefix: str | None = None) -> dict:
    """IGAA：/me。EAA（Facebook 登入）：/me/accounts 找本頻道的 IG 商業帳號，並記下該粉絲專頁的專頁權杖。"""
    if (token or "").startswith("EAA"):
        import healing_post as HP
        pages = HP.fb_pages(token, with_token=True)
        uid, why = HP.pick_ig(pages, HP.channel_account(prefix))
        SP.log(f"[ig] Facebook 登入版權杖：{why}")
        if not uid:
            # 系統用戶權杖只指派了 IG 帳號、沒有粉絲專頁（/me/accounts 0 個）→ 改用多路徑探查找編號（沒有專頁權杖，私訊用原權杖）
            ids, why2 = HP.ig_choices(HP.fb_ig_candidates(token), HP.channel_account(prefix))
            SP.log(f"[ig] 多路徑探查：{why2}")
            if not ids:
                raise RuntimeError(why + "；" + why2)
            _PAGE[token] = {"page_id": "", "page_token": ""}
            return {"id": ids[0], "username": HP.channel_account(prefix)}
        pg = next(x for x in pages if x["ig_id"] == uid)
        _PAGE[token] = {"page_id": pg.get("page_id", ""), "page_token": pg.get("page_token", "")}
        return {"id": uid, "username": pg["ig_username"]}
    d = SP.http("GET", f"{IG}/me", params={"fields": "user_id,username", "access_token": token})
    return {"id": str(d.get("user_id") or d.get("id") or ""), "username": str(d.get("username") or "")}


def recent_media(uid: str, token: str, since: datetime, posted: dict) -> list[str]:
    ids: list[str] = []
    for v in (posted or {}).values():                      # 自動發文紀錄（頻道④ healing_post.py 寫的）
        ig = v.get("ig") if isinstance(v, dict) else None
        if isinstance(ig, dict) and ig.get("id"):
            at = parse_ts(ig.get("at") or v.get("at"))
            if at is None or at >= since:
                ids.append(str(ig["id"]))
    try:                                                   # 帳號上全部貼文（含手動發的）
        url, params = f"{_ig(token)}/{uid}/media", {"fields": "id,timestamp", "limit": 25, "access_token": token}
        for _ in range(4):
            d = SP.http("GET", url, params=params)
            old = False
            for m in d.get("data") or []:
                ts = parse_ts(m.get("timestamp"))
                if ts and ts < since:
                    old = True
                    continue
                ids.append(str(m.get("id")))
            nxt = (d.get("paging") or {}).get("next")
            if old or not nxt:
                break
            url, params = nxt, None
    except Exception as e:  # noqa: BLE001
        SP.log(f"[ig] 讀貼文清單失敗，只用 posted.json：{SP.redact(e)}")
    return list(dict.fromkeys(i for i in ids if i and i != "None"))


def comments(media_id: str, token: str) -> list[dict]:
    out: list[dict] = []
    url = f"{_ig(token)}/{media_id}/comments"
    params = {"fields": "id,text,timestamp,username,from{id,username}", "limit": 50, "access_token": token}
    for _ in range(10):
        d = SP.http("GET", url, params=params)
        out.extend(d.get("data") or [])
        nxt = (d.get("paging") or {}).get("next")
        if not nxt:
            break
        url, params = nxt, None
    return out


def follows(igsid: str, token: str) -> bool | None:
    """True／False；查不到（未授權、權限不足、對方沒傳過訊息）回 None。"""
    if not igsid:
        return None
    try:
        tk = (_PAGE.get(token) or {}).get("page_token") or token      # EAA：要用專頁權杖
        d = SP.http("GET", f"{_ig(token)}/{igsid}", params={"fields": "is_user_follow_business", "access_token": tk})
    except Exception as e:  # noqa: BLE001
        SP.log(f"[ig] 查追蹤失敗（記為無法確認）：{SP.redact(e)[:200]}")
        return None
    v = d.get("is_user_follow_business")
    return v if isinstance(v, bool) else None


def private_reply(uid: str, token: str, comment_id: str, text: str) -> dict:
    """IGAA：/{ig-user-id}/messages。EAA：Instagram 私訊（Facebook 登入）走 /{page-id}/messages＋專頁權杖。"""
    pg = _PAGE.get(token) or {}
    if (token or "").startswith("EAA"):
        if not (pg.get("page_id") and pg.get("page_token")):
            raise RuntimeError("Facebook 登入版權杖拿不到粉絲專頁權杖，無法私訊（要 pages_show_list、instagram_manage_messages）")
        return SP.http("POST", f"{FB}/{pg['page_id']}/messages", params={"access_token": pg["page_token"]},
                       json={"recipient": {"comment_id": comment_id}, "message": {"text": text}})
    return SP.http("POST", f"{IG}/{uid}/messages", params={"access_token": token},
                   json={"recipient": {"comment_id": comment_id}, "message": {"text": text}})


def dm_available(token: str) -> bool:
    """IGAA：同一把權杖就能私訊。EAA：要拿到連結 IG 的粉絲專頁權杖（Messenger Platform）才行。"""
    if not (token or "").startswith("EAA"):
        return True
    pg = _PAGE.get(token) or {}
    return bool(pg.get("page_id") and pg.get("page_token"))


def public_reply(comment_id: str, token: str, text: str) -> dict:
    """公開回覆一則 IG 留言（instagram_manage_comments／instagram_business_manage_comments）。"""
    return SP.http("POST", f"{_ig(token)}/{comment_id}/replies", params={"message": text, "access_token": token})


def probe(token: str) -> dict:
    """只讀的能力檢查（不送任何東西）：私訊接不接得通、權杖權限。"""
    out = {"token": "EAA（Facebook 登入）" if (token or "").startswith("EAA") else "IGAA（Instagram 登入）",
           "dm_available": dm_available(token)}
    if (token or "").startswith("EAA"):
        try:
            d = SP.http("GET", f"{FB}/debug_token", params={"input_token": token, "access_token": token}).get("data") or {}
            out["scopes"] = sorted(d.get("scopes") or [])
        except Exception as e:  # noqa: BLE001
            out["scopes_error"] = SP.redact(e)[:160]
            try:                                   # 系統用戶權杖不是 App 擁有者時 debug_token 會被拒 → 改問 /me/permissions
                ps = SP.http("GET", f"{FB}/me/permissions", params={"access_token": token}).get("data") or []
                out["scopes"] = sorted(x.get("permission") for x in ps if x.get("status") == "granted")
            except Exception as e2:  # noqa: BLE001
                out["permissions_error"] = SP.redact(e2)[:160]
        if "scopes" in out:
            out["can_public_reply"] = "instagram_manage_comments" in out["scopes"]
        out["page"] = "有粉絲專頁權杖" if dm_available(token) else "看不到連結本 IG 的粉絲專頁（私訊做不到 → 走公開回覆保底）"
    return out


# ---------- 主流程 ----------
def run(env: dict | None = None, dry_run: bool = False, now: datetime | None = None,
        cfg_path: Path = CONFIG, state_path: Path = STATE, posted_path: Path = POSTED,
        prefix: str | None = None) -> tuple[int, dict]:
    prefix = _pfx(prefix)
    env = dict(os.environ if env is None else env)
    now = now or datetime.now(timezone.utc)
    cfg = load_cfg(cfg_path)
    res = {"at": now.astimezone(TAIPEI).isoformat(timespec="seconds"), "mode": "dry" if dry_run else "live",
           "counts": {}, "alerts": 0, "errors": [], "summary": ""}

    def bump(k):
        res["counts"][k] = res["counts"].get(k, 0) + 1

    if not cfg.get("enabled"):          # 先看開關：關著就什麼都不做（不讀權杖、不連 Meta）
        res["mode"] = "disabled"
        res["summary"] = "dm_config.json 的 enabled=false，本輪不讀留言"
        return 0, res
    if not str(cfg.get("message") or "").strip():
        res["errors"].append("dm_config.json 的 message 是空的：私訊內容還沒定，不私訊")
        res["summary"] = "enabled=true 但 message 空白，本輪不讀留言（請先填私訊內容）"
        return 1, res
    token = get_token(env, prefix)
    if not token:
        res["mode"] = "wait_token"
        res["summary"] = f"等待權杖（{prefix}IG_ACCESS_TOKEN），本輪空跑"
        return 0, res
    SP._SECRETS.append(token)
    print("::add-mask::" + token, flush=True)

    try:
        acct = me(token, prefix)
    except Exception as e:  # noqa: BLE001
        res["errors"].append(f"查自己帳號失敗：{SP.redact(e)[:200]}")
        res["summary"] = "權杖無效或權限不足（查不到自己帳號）"
        return 1, res
    uid = (env.get(prefix + "IG_USER_ID") or "").strip() or acct["id"]
    if not uid:
        res["summary"] = "查不到 IG 帳號編號"
        return 1, res
    if len(uid) >= 6:
        SP._SECRETS.append(uid)
    own = {acct["id"], uid}

    state = load_json(state_path, {})
    before = json.dumps({k: state.get(k) or {} for k in ("seen", "weekly", "rate")}, sort_keys=True, ensure_ascii=False)
    seen: dict = state.setdefault("seen", {})
    stats: dict = state.setdefault("weekly", {})
    since = now - timedelta(days=int(cfg.get("lookback_days") or 7))
    posted = load_json(posted_path, {})
    media = recent_media(uid, token, since, posted)
    SP.log(f"[ig] 近 {cfg.get('lookback_days')} 天貼文 {len(media)} 則")
    cap = int(cfg.get("max_per_run") or 0)
    sent = 0
    capped = False
    folder_of, queue = media_folders(posted, "ig"), queue_dir(posted_path)
    can_dm = dm_available(token)
    if dry_run:
        res["probe"] = probe(token)
        SP.log(f"[ig] 能力檢查（只讀）：{json.dumps(res['probe'], ensure_ascii=False)}")
    if not can_dm:
        SP.log("[ig] 私訊接不通（EAA 權杖看不到連結本 IG 的粉絲專頁）→ 專屬關鍵字留言改用公開回覆保底")
    pub_cap, per_hour = int(cfg.get("public_max_per_run") or 0), int(cfg.get("public_max_per_post_hour") or 0)
    hour_ago = (now - timedelta(hours=1)).isoformat(timespec="seconds")
    rate = {k: [x for x in v if x >= hour_ago] for k, v in dict(state.get("rate") or {}).items()}
    rate = {k: v for k, v in rate.items() if v}
    pub_sent = 0

    def do_public(mid, cid, text):
        """公開回覆保底；回 None＝成功，"cap"＝上限留到下一輪，其他字串＝錯誤訊息。"""
        nonlocal pub_sent
        mh = "m" + h(mid)
        if (pub_cap and pub_sent >= pub_cap) or (per_hour and len(rate.get(mh, [])) >= per_hour):
            return "cap"
        if not text:
            return "沒有公開回覆文字（keyword_default_public 也是空的）"
        if not dry_run:
            try:
                SP.retry_once("ig-reply", lambda: public_reply(cid, token, text), tries=2)
            except Exception as e:  # noqa: BLE001
                return SP.redact(e)[:200]
            rate.setdefault(mh, []).append(now.isoformat(timespec="seconds"))
        pub_sent += 1
        return None

    for mid in media:
        kws = post_keywords(folder_of.get(str(mid), ""), queue)
        try:
            cs = comments(mid, token)
        except Exception as e:  # noqa: BLE001
            res["errors"].append(f"讀留言失敗（貼文 …{str(mid)[-4:]}）：{SP.redact(e)[:200]}")
            continue
        for c in cs:
            cid = str(c.get("id") or "")
            if not cid:
                continue
            key = h(cid)
            rec = seen.get(key)
            if rec and rec.get("result") != "send_failed":
                continue
            if rec and rec.get("tries", 0) >= MAX_SEND_TRIES:
                continue
            frm = c.get("from") or {}
            who_id = str(frm.get("id") or "")
            who_name = str(frm.get("username") or c.get("username") or "")
            ts = parse_ts(c.get("timestamp"))
            base = {"at": res["at"], "comment_at": ts.astimezone(TAIPEI).isoformat(timespec="seconds") if ts else ""}

            if who_id in own or (acct["username"] and who_name == acct["username"]):
                result, follow, harm, text = "own", None, False, None
            elif ts and now - ts > REPLY_WINDOW:
                result, follow, harm, text = "expired", None, False, None
            elif kws and match_kw(c.get("text"), kws) and not is_self_harm(c.get("text"), cfg):
                # ---- 專屬關鍵字（自傷關鍵字已在條件裡排除 → 走下面原本的關懷訊息，優先）----
                kw = match_kw(c.get("text"), kws)
                upk = "u" + h(f"{who_id or who_name}|{mid}")        # 每人每篇 1 次
                if upk in seen:
                    if not dry_run:
                        seen[key] = dict(base, result="kw_dup")
                    bump("kw_dup")
                    continue
                dm_text, pub_text = kw_texts(cfg, kw, cid)
                follow = follows(who_id, token) if (can_dm and dm_text) else None
                result, why = "", ""
                if follow is True:
                    if cap and sent >= cap:
                        capped = True
                        continue
                    if dry_run:
                        result = "kw_dm"
                    else:
                        try:
                            SP.retry_once("ig-dm", lambda: private_reply(uid, token, cid, dm_text), tries=2)
                            result = "kw_dm"
                        except Exception as e:  # noqa: BLE001
                            msg = SP.redact(e)
                            if "already" in msg.lower() or "2534" in msg:
                                result = "kw_dm_already"
                            else:
                                why = "dm_failed"
                                res["errors"].append(f"私訊失敗，改公開回覆保底：{msg[:200]}")
                    if result:
                        sent += 1
                else:
                    why = "no_dm" if not can_dm else ("not_follower" if follow is False else "unknown_follow")
                if not result:
                    if cfg.get("keyword_public_fallback") is False:
                        result = "kw_skip_" + why
                    else:
                        err = do_public(mid, cid, pub_text)
                        if err == "cap":
                            capped = True
                            continue          # 不記錄，下一輪再處理
                        if err:
                            res["errors"].append(f"公開回覆失敗：{err}")
                            tries = (rec or {}).get("tries", 0) + 1
                            seen[key] = dict(base, result="send_failed", intended="kw_public", tries=tries)
                            bump("send_failed")
                            continue
                        result = "kw_public_" + why
                if dry_run:
                    result = "dry_" + result
                entry = dict(base, result=result, kw=True)
                if follow is not None:
                    entry["follow"] = follow
                if not dry_run:
                    seen[key] = entry
                    if not result.startswith("kw_skip"):
                        seen[upk] = {"at": res["at"], "result": "kw_user"}
                bump(result)
                if not dry_run:
                    wk = stats.setdefault(iso_week(now), {})
                    wk[result] = wk.get(result, 0) + 1
                continue
            else:
                harm = is_self_harm(c.get("text"), cfg)
                follow = None if harm else follows(who_id, token)
                if harm:
                    text = cfg.get("care_message") if cfg.get("care_enabled") else None
                    result = "care" if text else "care_disabled"
                    res["alerts"] += 1
                elif follow is True or (follow is None and not cfg.get("only_followers")):
                    text, result = cfg.get("message"), "dm"
                elif follow is None:
                    if cfg.get("unknown_follow") == "send":
                        text, result = cfg.get("message"), "dm_unknown_follow"
                    else:
                        text, result = None, "skip_unknown_follow"
                else:
                    text, result = None, "skip_not_follower"

            if text:
                if cap and sent >= cap:
                    capped = True
                    continue          # 不記錄，下一輪再處理（仍在 7 天內）
                if dry_run:
                    result = "dry_" + result
                else:
                    try:
                        SP.retry_once("ig-dm", lambda: private_reply(uid, token, cid, text), tries=2)
                    except Exception as e:  # noqa: BLE001
                        msg = SP.redact(e)
                        if "already" in msg.lower() or "2534" in msg:     # 已私回過 → 視為完成，不再送
                            result = result + "_already"
                        else:
                            res["errors"].append(f"私訊失敗：{msg[:200]}")
                            tries = (rec or {}).get("tries", 0) + 1
                            seen[key] = dict(base, result="send_failed", intended=result, tries=tries,
                                             self_harm=bool(harm))
                            bump("send_failed")
                            continue
                sent += 1
            entry = dict(base, result=result)
            if follow is not None:
                entry["follow"] = follow
            if harm:
                entry["self_harm"] = True
            if not dry_run:
                seen[key] = entry
            bump(result)
            wk = stats.setdefault(iso_week(now), {})
            if not dry_run:
                wk[result] = wk.get(result, 0) + 1

    # 只留 30 天紀錄
    cut = (now - timedelta(days=KEEP_DAYS)).astimezone(TAIPEI).isoformat(timespec="seconds")
    state["seen"] = {k: v for k, v in seen.items() if str(v.get("at", "")) >= cut}
    state["weekly"] = dict(sorted(stats.items())[-12:])
    if rate or state.get("rate"):
        state["rate"] = rate
    after = json.dumps({k: state.get(k) or {} for k in ("seen", "weekly", "rate")}, sort_keys=True, ensure_ascii=False)
    if not dry_run and after != before:        # 沒有新結果就不寫檔（避免每 15 分鐘一個空 commit）
        state["last_change"] = {k: res[k] for k in ("at", "counts", "alerts")}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(SP.redact(json.dumps(state, ensure_ascii=False, indent=1)) + "\n", encoding="utf-8")

    parts = [f"{k} {v}" for k, v in sorted(res["counts"].items())]
    res["summary"] = (f"貼文 {len(media)} 則；" + ("、".join(parts) if parts else "沒有新留言")
                      + (f"；已達每輪上限 {cap}（公開回覆 {pub_cap}），其餘下一輪處理" if capped else ""))
    unknown_week = (stats.get(iso_week(now)) or {}).get("skip_unknown_follow", 0)
    if unknown_week:
        res["summary"] += f"；本週「無法確認追蹤」未私訊 {unknown_week} 則"
    return (1 if res["errors"] and not res["counts"] else 0), res


# ---------- Threads：專屬關鍵字 → 公開回覆（Threads 沒有私訊 API、查不到追蹤）----------
TH = SP.THREADS_HOST + "/v1.0"


def threads_token(env: dict, prefix: str | None = None) -> str:
    p = _pfx(prefix)
    return (env.get(p + "THREADS_ACCESS_TOKEN_AUTO") or "").strip() or (env.get(p + "THREADS_ACCESS_TOKEN") or "").strip()


def threads_run(env: dict | None = None, dry_run: bool = False, now: datetime | None = None,
                cfg_path: Path = CONFIG, state_path: Path | None = None, posted_path: Path = POSTED,
                prefix: str | None = None) -> tuple[int, dict]:
    """只看「佇列 meta.json 有 comment_keyword」的貼文：讀 Threads 留言 → 含關鍵字 → 公開回覆一句（每人每篇 1 次）。"""
    prefix = _pfx(prefix)
    env = dict(os.environ if env is None else env)
    now = now or datetime.now(timezone.utc)
    cfg = load_cfg(cfg_path)
    tcfg = cfg.get("threads_reply") or {}
    state_path = state_path or Path(posted_path).parent / THREADS_STATE_NAME
    res = {"counts": {}, "alerts": 0, "errors": [], "summary": ""}

    def bump(k):
        res["counts"][k] = res["counts"].get(k, 0) + 1

    if not cfg.get("enabled") or not tcfg.get("enabled"):
        res["summary"] = "Threads 關鍵字回覆關閉"
        return 0, res
    posted = load_json(posted_path, {})
    queue = queue_dir(posted_path)
    since = now - timedelta(days=int(cfg.get("lookback_days") or 7))
    targets = []
    for folder, v in (posted or {}).items():
        th = v.get("threads") if isinstance(v, dict) else None
        kws = post_keywords(folder, queue)
        at = parse_ts((th or {}).get("at") or (v or {}).get("at")) if isinstance(v, dict) else None
        if isinstance(th, dict) and th.get("id") and kws and (at is None or at >= since):
            targets.append((str(th["id"]), folder, kws))
    token = threads_token(env, prefix)
    if not targets and dry_run and token:          # 空跑：拿最近一篇 Threads 貼文只讀測一次 threads_read_replies
        last = sorted(((str(v.get("threads", {}).get("at") or ""), str(v["threads"]["id"])) for v in (posted or {}).values()
                       if isinstance(v, dict) and isinstance(v.get("threads"), dict) and v["threads"].get("id")), reverse=True)
        if last:
            SP._SECRETS.append(token)
            try:
                n = len(SP.http("GET", f"{TH}/{last[0][1]}/replies", params={"fields": "id", "access_token": token}).get("data") or [])
                res["summary"] = f"能力檢查（只讀）：最近一篇 Threads 貼文讀留言成功（{n} 則），threads_read_replies 可用；"
            except Exception as e:  # noqa: BLE001
                res["summary"] = f"能力檢查（只讀）：讀 Threads 留言失敗：{SP.redact(e)[:160]}；"
    if not targets:
        res["summary"] = res["summary"] + "近期沒有設 comment_keyword 的 Threads 貼文"
        return 0, res
    if not token:
        res["summary"] = f"等待權杖（{prefix}THREADS_ACCESS_TOKEN），本輪空跑"
        return 0, res
    SP._SECRETS.append(token)
    print("::add-mask::" + token, flush=True)
    try:
        me_ = SP.http("GET", f"{TH}/me", params={"fields": "id,username", "access_token": token})
    except Exception as e:  # noqa: BLE001
        res["errors"].append(f"Threads 查自己帳號失敗：{SP.redact(e)[:200]}")
        res["summary"] = "Threads 權杖無效或權限不足"
        return 1, res
    uid = (env.get(prefix + "THREADS_USER_ID") or "").strip() or str(me_.get("id") or "")
    mine = str(me_.get("username") or "")
    st = load_json(state_path, {})
    replied = {k: v for k, v in (st.get("replied") or {}).items()
               if v >= (now - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")}
    before = dict(replied)
    budget = int(tcfg.get("max_per_run") or 10)
    for tid, folder, kws in targets:
        try:
            rows = SP.http("GET", f"{TH}/{tid}/replies",
                           params={"fields": "id,text,username,timestamp", "access_token": token}).get("data") or []
        except Exception as e:  # noqa: BLE001
            res["errors"].append(f"Threads 讀留言失敗（多半是沒有 threads_read_replies）：{SP.redact(e)[:200]}")
            continue
        for r in rows:
            rid, who = str(r.get("id") or ""), str(r.get("username") or "")
            if not rid or (mine and who == mine):
                continue
            kw = match_kw(r.get("text"), kws)
            if not kw:
                continue
            rk, uk = "r" + h(rid), "u" + h(f"{who}|{tid}")
            if rk in replied or uk in replied:
                continue
            if is_self_harm(r.get("text"), cfg):          # 自傷優先：不自動回資料，提醒 CEO 人工處理（legal.md 2-7）
                res["alerts"] += 1
                bump("care_manual")
                if not dry_run:
                    replied[rk] = now.isoformat(timespec="seconds")
                continue
            if budget <= 0:
                res["summary"] = "本輪到上限，其餘下一輪"
                break
            _, text = kw_texts(cfg, kw, rid)
            if dry_run:
                bump("dry_threads_public")
                continue
            try:
                def go():
                    cid = SP.http("POST", f"{TH}/{uid}/threads", data={"media_type": "TEXT", "text": text,
                                                                     "reply_to_id": rid, "access_token": token})["id"]
                    SP._sleep(3)
                    return SP.http("POST", f"{TH}/{uid}/threads_publish", data={"creation_id": cid, "access_token": token})
                SP.retry_once("threads-reply", go, tries=2)
            except Exception as e:  # noqa: BLE001
                res["errors"].append(f"Threads 公開回覆失敗（多半是沒有 threads_manage_replies）：{SP.redact(e)[:200]}")
                continue
            replied[rk] = replied[uk] = now.isoformat(timespec="seconds")
            budget -= 1
            bump("threads_public")
    if not dry_run and replied != before:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"replied": replied}, indent=1) + "\n", encoding="utf-8")
    parts = [f"{k} {v}" for k, v in sorted(res["counts"].items())]
    res["summary"] = (f"Threads 關鍵字貼文 {len(targets)} 篇；" + ("、".join(parts) if parts else "沒有新的關鍵字留言")
                      + (f"；{res['summary']}" if res["summary"] else ""))
    return (1 if res["errors"] and not res["counts"] else 0), res


LABEL = {
    "dm": "已私訊（有追蹤）", "dm_unknown_follow": "已私訊（追蹤無法確認，設定為照樣送）",
    "care": "已送關懷資源訊息（自傷關鍵字）", "care_disabled": "自傷關鍵字（關懷訊息已關閉，未送）",
    "skip_not_follower": "沒追蹤，未私訊", "skip_unknown_follow": "追蹤無法確認，未私訊",
    "own": "自己帳號的留言", "expired": "超過 7 天，無法私回", "send_failed": "私訊失敗（下一輪重試）",
    "kw_dm": "專屬關鍵字：已私訊完整資料（有追蹤）", "kw_dm_already": "專屬關鍵字：已私回過",
    "kw_public_no_dm": "專屬關鍵字：私訊接不通，已公開回覆（保底）",
    "kw_public_not_follower": "專屬關鍵字：沒追蹤，已公開回覆（保底）",
    "kw_public_unknown_follow": "專屬關鍵字：追蹤無法確認，已公開回覆（保底）",
    "kw_public_dm_failed": "專屬關鍵字：私訊失敗，已公開回覆（保底）",
    "kw_dup": "專屬關鍵字：同一人同一篇已回過", "threads_public": "Threads 專屬關鍵字：已公開回覆",
    "care_manual": "Threads 自傷關鍵字：未自動回，請人工處理",
}


def summary_md(res: dict, name: str = "談晴說礙") -> str:
    lines = [f"## {name}：IG 留言自動私訊", "", f"- 時間（台北）：{res['at']}", f"- 模式：{res['mode']}",
             f"- 摘要：{res['summary']}"]
    if res["counts"]:
        lines += ["", "| 結果 | 則數 |", "|---|---|"]
        for k, v in sorted(res["counts"].items()):
            base = k[4:] if k.startswith("dry_") else k
            lines.append(f"| {LABEL.get(base.replace('_already', ''), base)}{'（空跑）' if k.startswith('dry_') else ''} | {v} |")
    if res["alerts"]:
        lines += ["", f"### ⚠️ 自傷訊號 {res['alerts']} 則：請 CEO 依 legal.md 2-7 人工處理（到 IG 收件匣看原留言，評估級別、公開回範本 A、必要時檢舉）"]
    if res.get("probe"):
        lines += ["", "### 能力檢查（只讀）"] + [f"- {k}：{v}" for k, v in res["probe"].items()]
    for e in res["errors"]:
        lines.append(f"- 錯誤：{e}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--channel", default="", help="channels.json 的頻道代碼；不給＝頻道④談晴說礙")
    a = ap.parse_args(argv)
    if a.channel and a.channel != "healing":
        c = channel_paths(a.channel)
        code, res = run(dry_run=a.dry_run, cfg_path=c["cfg"], state_path=c["state"], posted_path=c["posted"],
                        prefix=c["prefix"])
        md = summary_md(res, c["name"])
    else:
        code, res = run(dry_run=a.dry_run)
        md = summary_md(res)
        tcode, tres = threads_run(dry_run=a.dry_run)             # 頻道④ Threads 專屬關鍵字公開回覆
        md += f"\n## 談晴說礙：Threads 專屬關鍵字回覆\n\n- 摘要：{tres['summary']}\n" + "".join(
            f"- 錯誤：{e}\n" for e in tres["errors"])
        if tres["alerts"]:
            md += f"\n### ⚠️ Threads 自傷訊號 {tres['alerts']} 則：請 CEO 依 legal.md 2-7 人工處理\n"
            res["alerts"] += tres["alerts"]
        if tcode or tres["errors"]:      # Threads 出錯只警告、不讓整個工作流紅燈（IG 私訊才是主流程）
            print("::warning::談晴說礙 Threads 專屬關鍵字回覆有錯誤：" + SP.redact("；".join(tres["errors"]))[:300])
    print(SP.redact(md))
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as f:
            f.write(SP.redact(md))
    if res["alerts"]:
        print(f"::warning::{a.channel or 'healing'} IG 留言出現自傷訊號 {res['alerts']} 則，請 CEO 依 legal.md 2-7 處理")
    return code


if __name__ == "__main__":
    sys.exit(main())
