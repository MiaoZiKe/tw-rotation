"""頻道②「科技透明圈」發文（2026-11-08）。

Andy 原話：「開通自動發文，這部分幫我想辦法自動化」。說明：docs/marketing/channels/tc/autopost.md
工作流：.github/workflows/tc_post.yml（每 15 分鐘；手動觸發預設 dry_run）。

★ 跟頻道一（股市帳號）完全隔離：
  · 佇列：social/tc/queue/<日期>_<代號>/（頻道一是 social/threads/queue、social/ig/queue，互不讀）
  · 權杖：只讀 TC_THREADS_TOKEN／TC_IG_TOKEN（2026-11-10 起工作流從 TECH_*_ACCESS_TOKEN_AUTO／TECH_* 帶進來，頻道④交接），絕不讀頻道一的權杖
  · 發文前先打 /me：帳號 id 等於頻道一的 THREADS_USER_ID／IG_USER_ID → 整篇不發（防止發到股市帳號）
  · 紀錄：state/tc/posted.json（頻道一是 social-snaps 的 state/posted.json）
  · 開關：docs/marketing/social_unit/post_quota.json 的 "tc" 區塊

每篇一個資料夾：
  post.md     檔頭 status（draft／approved／posted／error）、scheduled_at、platforms（ig, threads）、images
  ig.txt      IG 說明文字（整段原樣）
  threads.txt 【主文】……【第 1 則留言】……
  *.jpg       圖（IG 只收 JPEG；IG 發輪播、Threads 主文帶同一組圖）

規則：
  · 只有 status: approved 才發；沒有 approved 稿 → 什麼都不做（不連 Meta）。
  · 一次最多發 1 篇；per_day／min_gap_hours 超過 → 順延（檔頭寫 deferred_until，不擠在同一天）。
  · 沒有 TC 權杖 → 安靜跳過、記錄 state/tc/status.json，結束碼 0（不寄失敗信）。
  · 封面一定有圖：Threads 圖上傳失敗不退回純文字，整篇標 error；發完回頭查兩個平台的 media_type。
  · 失敗不自動重發（避免重複貼文）：標 status: error＋done 記已發平台；修好改回 approved 只補沒發的平台。
  · 監工：approved 且（排定時間或順延時間）已過 30 分鐘仍沒發、或 status: error → 輸出 alert，工作流開 issue。
  · --dry-run：只驗證（格式、圖檔、/me 帳號），不發、不寫任何檔。
  · 自動刪文（2026-11-08 Andy：「還有自動刪文」）：post.md 檔頭可選填 delete_at。到時間：
      Threads → 用 API 先刪第 1 則留言再刪主文（需要 threads_delete 權限），回查確認刪掉，寫 deleted_threads；
      IG → Instagram 登入版 API 不能刪貼文，只開 issue 附 permalink 與手動刪除步驟，寫 ig_delete_notified。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ig_post as IG  # noqa: E402  只借用 API 呼叫與檔頭讀寫；不讀它的佇列與權杖
import post_quota  # noqa: E402
import threads_post as TP  # noqa: E402

QUEUE = ROOT / "social" / "tc" / "queue"
STATE_DIR = ROOT / "state" / "tc"
TAIPEI = timezone(timedelta(hours=8))
STATUSES = {"draft", "approved", "posted", "error"}
PLATFORMS = ("ig", "threads")
MONITOR_GRACE_MIN = 30
RAW = "https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/"
TC_DEFAULT = {"enabled": False, "threads": False, "ig": False, "per_day": 1, "min_gap_hours": 20}
SLEEP = time.sleep

_SECRETS: list[str] = []


class PostError(Exception):
    pass


def mask(v: str) -> None:
    if v and v not in _SECRETS:
        _SECRETS.append(v)
        print("::add-mask::" + v, flush=True)


def redact(s) -> str:
    s = str(s)
    for t in _SECRETS:
        s = s.replace(t, "***")
    return s


def log(*a) -> None:
    print(redact(" ".join(str(x) for x in a)), flush=True)


def fmt(d: datetime) -> str:
    return d.astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M+08:00")


# ---------- 設定 ----------

def settings(q: dict | None = None) -> dict:
    """post_quota.json 的 "tc" 區塊。讀不到或格式壞 → 全關（頻道②寧可不發）。"""
    q = q if q is not None else post_quota.load()
    tc = q.get("tc") if isinstance(q, dict) else None
    if not isinstance(tc, dict):
        return dict(TC_DEFAULT)
    out = dict(TC_DEFAULT)
    out.update({k: tc[k] for k in TC_DEFAULT if k in tc})
    for k in ("enabled", "threads", "ig"):
        out[k] = out[k] is True
    try:
        out["per_day"] = max(1, int(out["per_day"]))
        out["min_gap_hours"] = max(0.0, float(out["min_gap_hours"]))
    except (TypeError, ValueError):
        return dict(TC_DEFAULT)
    return out


# ---------- 讀稿 ----------

def parse_threads_txt(text: str) -> tuple[str, str]:
    m = re.search(r"【主文】\s*\n(.*?)(?:\n\s*【第\s*1\s*則留言】\s*\n(.*))?\Z", text.strip() + "\n", re.S)
    if not m:
        raise PostError("threads.txt 缺少【主文】")
    return m.group(1).strip(), (m.group(2) or "").strip()


def load(d: Path) -> dict:
    meta, _ = IG.parse((d / "post.md").read_text(encoding="utf-8"))
    p = {"dir": d, "id": d.name, "meta": meta}
    p["platforms"] = [x for x in re.split(r"[\s,]+", meta.get("platforms", "")) if x]
    p["images"] = [x for x in re.split(r"[\s,]+", meta.get("images", "")) if x]
    p["caption"] = (d / "ig.txt").read_text(encoding="utf-8").strip() if (d / "ig.txt").is_file() else ""
    p["main"], p["reply"] = ("", "")
    if (d / "threads.txt").is_file():
        try:
            p["main"], p["reply"] = parse_threads_txt((d / "threads.txt").read_text(encoding="utf-8"))
        except PostError:
            pass
    p["done"] = [x for x in re.split(r"[\s,]+", meta.get("done", "")) if x]
    return p


def sched(p: dict) -> datetime:
    d = datetime.fromisoformat(p["meta"]["scheduled_at"])
    return d if d.tzinfo else d.replace(tzinfo=TAIPEI)


WEEKDAYS = "一二三四五六日"   # datetime.weekday()：0＝星期一


def weekday_check(p: dict) -> tuple[str, str]:
    """檔頭 weekday: 跟 scheduled_at（台北）算出的星期幾比對。回 (錯誤, 警告)，沒事就是空字串。

    2026-11-12 事故：週表規定週四 20:30 發，CEO 把 11/13 誤當週四（其實是週五），當晚沒發。
    Andy：「避免再度發生」→ 排程的人要自己寫「這天是星期幾」，程式用日期反算，對不上就擋。
    缺欄位只警告不擋（舊稿相容）。
    """
    want = str(p["meta"].get("weekday", "")).strip()
    try:
        d = sched(p).astimezone(TAIPEI)
    except (KeyError, ValueError):
        return "", ""   # scheduled_at 本身錯，validate 另外會報
    real = WEEKDAYS[d.weekday()]
    if not want:
        return "", (f"{p['id']}：檔頭沒有 weekday:（scheduled_at {d:%Y-%m-%d} 是星期{real}），"
                    f"請補一行「weekday: {real}」；目前只警告不擋")
    w = want.removeprefix("星期").removeprefix("週").removeprefix("周")
    if w == "天":
        w = "日"
    if w not in WEEKDAYS or len(w) != 1:
        return f"weekday: {want!r} 看不懂（要寫一、二、三、四、五、六、日其中一個字）", ""
    if w != real:
        return (f"星期對不上，擋下不發：檔頭寫 weekday: {want}，但 scheduled_at {d:%Y-%m-%d %H:%M}（台北）"
                f"是星期{real}。請確認要發的是哪一天，改 scheduled_at 或 weekday 其中一個"), ""
    return "", ""


def validate(p: dict, check_files: bool = True) -> list[str]:
    m, errs = p["meta"], []
    werr, wwarn = weekday_check(p)
    if werr:
        errs.append(werr)
    if wwarn:
        log("⚠ " + wwarn)
    if m.get("status") not in STATUSES:
        errs.append(f"status 必須是 {sorted(STATUSES)} 之一，目前是 {m.get('status')!r}")
    try:
        sched(p)
    except (KeyError, ValueError):
        errs.append("scheduled_at 缺少或格式錯誤（要像 2026-11-10T20:30+08:00）")
    bad = [x for x in p["platforms"] if x not in PLATFORMS]
    if not p["platforms"] or bad:
        errs.append(f"platforms 只能填 ig、threads（目前 {m.get('platforms')!r}）")
    if not p["images"]:
        errs.append("封面一定要有圖：images 沒填")
    if len(p["images"]) > 10:
        errs.append(f"最多 10 張，目前 {len(p['images'])} 張")
    for x in p["images"]:
        if not x.lower().endswith((".jpg", ".jpeg")):
            errs.append(f"{x} 不是 JPEG（IG 只收 JPEG）")
        elif check_files and not (p["dir"] / x).is_file():
            errs.append(f"找不到圖檔 {x}")
    if "ig" in p["platforms"]:
        if not p["caption"]:
            errs.append("ig.txt 是空的")
        elif len(p["caption"]) > IG.MAX_CAPTION:
            errs.append(f"ig.txt {len(p['caption'])} 字，超過 {IG.MAX_CAPTION}")
        if len(re.findall(r"#\S+", p["caption"])) > IG.MAX_TAGS:
            errs.append(f"ig.txt #標籤超過 {IG.MAX_TAGS} 個")
    if "threads" in p["platforms"]:
        if not p["main"]:
            errs.append("threads.txt 缺少【主文】")
        for label, t in (("主文", p["main"]), ("第 1 則留言", p["reply"])):
            if t and TP._tlen(t) > TP.MAX_LEN:
                errs.append(f"threads.txt {label} {TP._tlen(t)} 字（表情符號以位元組計），超過 {TP.MAX_LEN}")
    return errs


def rel(p: dict, img: str) -> str:
    """圖的 repo 相對路徑（raw.githubusercontent.com 公開網址用；圖要先在 main 上）。"""
    return f"social/tc/queue/{p['id']}/{img}"


def image_urls(p: dict) -> list[str]:
    return [RAW + urllib.parse.quote(rel(p, x)) for x in p["images"]]


# ---------- 紀錄與名額 ----------

def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def posted_times(state_dir: Path) -> list[datetime]:
    out = []
    for e in (load_json(state_dir / "posted.json", {}).get("posts") or []):
        try:
            out.append(datetime.fromisoformat(e["first_posted_at"]))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out)


def effective_due(p: dict, history: list[datetime], cfg: dict) -> datetime:
    """排定時間，再套 min_gap_hours 與 per_day（台北日）順延。"""
    t = sched(p)
    for _ in range(60):
        if history:
            t = max(t, history[-1] + timedelta(hours=cfg["min_gap_hours"]))
        day = t.astimezone(TAIPEI).date()
        if sum(1 for h in history if h.astimezone(TAIPEI).date() == day) >= cfg["per_day"]:
            t = datetime.combine(day + timedelta(days=1), datetime.min.time(), TAIPEI)
            continue
        return t
    return t


# ---------- Meta API（單一出口，測試 mock 這裡） ----------

def _delete(platform: str, path: str, token: str) -> dict:
    import urllib.error
    import urllib.request
    base = TP.API if platform == "threads" else IG.API
    q = urllib.parse.urlencode({"access_token": token})
    req = urllib.request.Request(f"{base}{path}?{q}", method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise PostError(f"HTTP {e.code} {path}：{e.read().decode('utf-8', 'replace')[:300]}") from None
    except urllib.error.URLError as e:
        raise PostError(f"連線失敗 {path}：{e.reason}") from None


# ---------- IG：Facebook 登入版系統用戶權杖（EAA 開頭）走 graph.facebook.com（2026-11-10 頻道④交接 TECH_*）----------
# 頻道②帳號 @tech_01010909 的 IG 權杖是 EAA 系統用戶權杖（Instagram Graph API，graph.facebook.com），
# 不是 Instagram 登入版（graph.instagram.com）。/{ig-user-id}/media、media_publish、輪播 children、status_code、
# /{media}/comments 兩邊用法相同；帳號編號用頻道④的 healing_post.resolve_uid（/me/assigned_instagram_accounts 等多路徑）。
FB_HOST = "https://graph.facebook.com/v24.0"
TECH_PREFIX = "TECH_"


def is_fb_token(token: str) -> bool:
    return (token or "").startswith("EAA")


def _fb_call(method: str, path: str, token: str, params: dict | None = None) -> dict:
    import urllib.error
    import urllib.request
    q = dict(params or {})
    q["access_token"] = token
    data = urllib.parse.urlencode(q).encode()
    url = path if path.startswith("http") else f"{FB_HOST}{path}"
    req = urllib.request.Request(f"{url}?{data.decode()}") if method == "GET" else \
        urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise PostError(redact(f"HTTP {e.code} {path.split('?')[0]}：{e.read().decode('utf-8', 'replace')[:300]}")) from None
    except urllib.error.URLError as e:
        raise PostError(f"連線失敗 {path.split('?')[0]}：{e.reason}") from None


def resolve_eaa_uid(token: str) -> str:
    """EAA 權杖找 IG 帳號編號：重用頻道④的多路徑探查（不重寫）。"""
    import healing_post as HP  # noqa: PLC0415  延後載入：只有 EAA 才需要（它要 requests）
    return HP.resolve_uid("ig", "", token, prefix=TECH_PREFIX) or ""


def api(platform: str, method: str, path: str, token: str, params: dict | None = None) -> dict:
    if platform == "ig" and is_fb_token(token):
        if method == "DELETE":
            raise PostError("IG 貼文不能用 API 刪除（Instagram Graph API 沒有刪貼文端點）")
        return _fb_call(method, path, token, params)
    if method == "DELETE":
        return _delete(platform, path, token)
    try:
        return (TP._call if platform == "threads" else IG._call)(method, path, token, params)
    except (TP.PostError, IG.PostError) as e:
        raise PostError(redact(e)) from None


def check_public(url: str) -> None:
    try:
        IG.check_public(url)
    except IG.PostError as e:
        raise PostError(str(e)) from None


def whoami(platform: str, token: str) -> tuple[str, str]:
    if platform == "threads":
        d = api("threads", "GET", "/me", token, {"fields": "id,username"})
        return str(d.get("id") or ""), str(d.get("username") or "")
    d = api("ig", "GET", "/me", token, {"fields": "user_id,username"})
    return str(d.get("user_id") or d.get("id") or ""), str(d.get("username") or "")


def whoami_eaa(token: str, expect_id: str) -> tuple[str, str]:
    uid = expect_id or resolve_eaa_uid(token)
    if not uid:
        return "", ""
    d = api("ig", "GET", f"/{uid}", token, {"fields": "id,username"})
    return str(d.get("id") or uid), str(d.get("username") or "")


def preflight(platform: str, token: str, expect_id: str, ch1_id: str) -> tuple[str, str]:
    uid, uname = whoami_eaa(token, expect_id) if platform == "ig" and is_fb_token(token) else whoami(platform, token)
    if not uid:
        raise PostError(f"{platform} 權杖查不到帳號 id")
    if ch1_id and uid == ch1_id:
        raise PostError(f"{platform} 權杖是頻道一（股市帳號 @{uname}）的，整篇不發")
    if expect_id and uid != expect_id:
        raise PostError(f"{platform} 帳號 id 跟設定的 USER_ID 不一樣（@{uname}），整篇不發")
    return uid, uname


def _wait_threads(cid: str, token: str) -> None:
    for _ in range(12):
        st = api("threads", "GET", f"/{cid}", token, {"fields": "status,error_message"})
        s = st.get("status", "")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise PostError(f"Threads 容器處理失敗（{s}）：{st.get('error_message', '')}")
        SLEEP(5)
    raise PostError("Threads 容器 60 秒內沒處理完")


def _wait_ig(cid: str, token: str) -> None:
    for _ in range(12):
        s = api("ig", "GET", f"/{cid}", token, {"fields": "status_code"}).get("status_code", "")
        if s == "FINISHED":
            return
        if s in ("ERROR", "EXPIRED"):
            raise PostError(f"IG 容器處理失敗（{s}）")
        SLEEP(5)
    raise PostError("IG 容器 60 秒內沒處理完")


def _permalink(platform: str, mid: str, token: str) -> tuple[str, str]:
    try:
        d = api(platform, "GET", f"/{mid}", token, {"fields": "permalink,media_type"})
    except PostError:
        return "", ""
    return d.get("permalink", ""), d.get("media_type", "")


def post_ig(uid: str, urls: list[str], caption: str, token: str) -> dict:
    for u in urls:
        check_public(u)
    if len(urls) == 1:
        c = api("ig", "POST", f"/{uid}/media", token, {"image_url": urls[0], "caption": caption})["id"]
    else:
        kids = []
        for u in urls:
            k = api("ig", "POST", f"/{uid}/media", token, {"image_url": u, "is_carousel_item": "true"})["id"]
            _wait_ig(k, token)
            kids.append(k)
        c = api("ig", "POST", f"/{uid}/media", token,
                {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption})["id"]
    _wait_ig(c, token)
    mid = api("ig", "POST", f"/{uid}/media_publish", token, {"creation_id": c})["id"]
    link, mtype = _permalink("ig", mid, token)
    return {"id": mid, "permalink": link, "media_type": mtype}


def _threads_publish(uid: str, cid: str, token: str) -> str:
    for wait in (0, 10, 20, 30):
        SLEEP(wait)
        try:
            return api("threads", "POST", f"/{uid}/threads_publish", token, {"creation_id": cid})["id"]
        except PostError as e:
            if wait == 30 or "HTTP 4" not in str(e) or "190" in str(e):
                raise
    raise PostError("Threads 發布失敗")


def post_threads(uid: str, urls: list[str], main: str, reply: str, token: str) -> dict:
    """主文一定帶圖（1 張＝IMAGE、2 張以上＝CAROUSEL）；圖失敗不退回純文字。主文發出後再發第 1 則留言。"""
    if len(urls) == 1:
        params = {"media_type": "IMAGE", "image_url": urls[0], "text": main}
    else:
        kids = [api("threads", "POST", f"/{uid}/threads", token,
                    {"media_type": "IMAGE", "image_url": u, "is_carousel_item": "true"})["id"] for u in urls[:20]]
        for k in kids:
            _wait_threads(k, token)
        params = {"media_type": "CAROUSEL", "children": ",".join(kids), "text": main}
    cid = api("threads", "POST", f"/{uid}/threads", token, params)["id"]
    _wait_threads(cid, token)
    mid = _threads_publish(uid, cid, token)
    link, mtype = _permalink("threads", mid, token)
    out = {"id": mid, "permalink": link, "media_type": mtype, "reply_permalink": "", "reply_error": "", "reply_id": ""}
    if reply:
        try:
            SLEEP(5)
            rc = api("threads", "POST", f"/{uid}/threads", token,
                     {"media_type": "TEXT", "text": reply, "reply_to_id": mid})["id"]
            SLEEP(8)
            rid = _threads_publish(uid, rc, token)
            out["reply_id"] = rid
            out["reply_permalink"] = _permalink("threads", rid, token)[0] or f"id:{rid}"
        except PostError as e:
            out["reply_error"] = str(e)[:200]
    return out


# ---------- 主流程 ----------

def tokens_from(env: dict) -> dict:
    t = {"threads": (env.get("TC_THREADS_TOKEN") or "").strip(), "ig": (env.get("TC_IG_TOKEN") or "").strip()}
    for v in t.values():
        mask(v)
    return t


def publish_one(p: dict, env: dict, tok: dict, now: datetime, state_dir: Path) -> str:
    todo = [x for x in p["platforms"] if x not in p["done"]]
    # 先確認帳號（兩個平台都先查，任何一個不對就整篇不發，避免發一半）
    ids = {}
    for plat in todo:
        ids[plat] = preflight(plat, tok[plat], (env.get(f"TC_{plat.upper()}_USER_ID") or "").strip(),
                              (env.get("THREADS_USER_ID" if plat == "threads" else "IG_USER_ID") or "").strip())
    urls = image_urls(p)
    upd: dict = {}
    done = list(p["done"])
    err = ""
    for plat in todo:
        try:
            if plat == "ig":
                r = post_ig(ids["ig"][0], urls, p["caption"], tok["ig"])
                upd["urls_ig"] = r["permalink"] or f"id:{r['id']}"
                upd["ids_ig"] = r["id"]
                upd["verified_ig"] = r["media_type"] or "未知"
            else:
                r = post_threads(ids["threads"][0], urls, p["main"], p["reply"], tok["threads"])
                upd["urls_threads"] = r["permalink"] or f"id:{r['id']}"
                upd["ids_threads"] = r["id"]
                if r["reply_id"]:
                    upd["ids_threads_reply"] = r["reply_id"]
                upd["verified_threads"] = r["media_type"] or "未知"
                if p["reply"]:
                    upd["urls_threads_reply"] = r["reply_permalink"] or "(留言失敗)"
                if r["reply_error"]:
                    log(f"::warning::{p['id']}：Threads 主文已發，第 1 則留言失敗：{r['reply_error']}")
            done.append(plat)
            log(f"{p['id']}：{plat} 已發出（@{ids[plat][1]}）{upd.get('urls_' + plat, '')}")
        except PostError as e:
            err = f"{plat}：{e}"
            log(f"✗ {p['id']}：{err}")
            break
    meta = p["meta"]
    all_urls = " ".join(x for x in (meta.get("urls_ig") or upd.get("urls_ig"), meta.get("urls_threads") or upd.get("urls_threads"),
                                    meta.get("urls_threads_reply") or upd.get("urls_threads_reply")) if x)
    upd["done"] = ", ".join(done) or "(無)"
    if all_urls:
        upd["urls"] = all_urls
    if err:
        upd.update(status="error", error=err[:200].replace("\n", " "))
    else:
        upd.update(status="posted", posted_at=fmt(now), error="")
    for plat in done:
        v = upd.get("verified_" + plat) or meta.get("verified_" + plat, "")
        if v and v not in ("IMAGE", "CAROUSEL_ALBUM", "CAROUSEL"):
            log(f"::warning::{p['id']}：{plat} 回查 media_type＝{v}，不是圖片貼文，請人工確認")
    IG.rewrite_meta(p["dir"] / "post.md", upd)
    if len(done) > len(p["done"]):
        _record(state_dir, p, now, upd, meta)
    if err:
        raise PostError(err)
    return "已發出：" + all_urls


def _record(state_dir: Path, p: dict, now: datetime, upd: dict, meta: dict) -> None:
    path = state_dir / "posted.json"
    data = load_json(path, {})
    posts = data.get("posts") or []
    e = next((x for x in posts if x.get("id") == p["id"]), None)
    if e is None:
        e = {"id": p["id"], "first_posted_at": now.isoformat(timespec="seconds")}
        posts.append(e)
    for k in ("urls_ig", "urls_threads", "urls_threads_reply", "verified_ig", "verified_threads", "ids_ig"):
        v = upd.get(k) or meta.get(k)
        if v:
            e[k.replace("urls_", "")] = v
    e["last_posted_at"] = now.isoformat(timespec="seconds")
    data["posts"] = posts
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def delete_due(p: dict, now: datetime) -> bool:
    v = p["meta"].get("delete_at", "").strip()
    if not v or p["meta"].get("status") not in ("posted", "error"):
        return False
    d = datetime.fromisoformat(v)
    return (d if d.tzinfo else d.replace(tzinfo=TAIPEI)) <= now


def process_deletes(posts: list[dict], tok: dict, now: datetime, dry_run: bool, res: dict) -> int:
    rc = 0
    for p in posts:
        try:
            if not delete_due(p, now):
                continue
        except ValueError:
            res["errors"].append(f"{p['id']}：delete_at 格式錯誤")
            continue
        m, upd = p["meta"], {}
        if "threads" in p["done"] and not m.get("deleted_threads"):
            ids = [x for x in (m.get("ids_threads_reply", ""), m.get("ids_threads", "")) if x]
            if not tok["threads"]:
                log(f"{p['id']}：到了 delete_at，但沒有 TC Threads 權杖 → 安靜跳過")
            elif dry_run:
                log(f"[dry-run] {p['id']}：會刪 Threads {len(ids)} 則（留言＋主文）；沒有真的刪")
            else:
                try:
                    for mid in ids:
                        api("threads", "DELETE", f"/{mid}", tok["threads"])
                        try:
                            api("threads", "GET", f"/{mid}", tok["threads"], {"fields": "id"})
                            raise PostError(f"刪除後回查 {mid} 仍然存在")
                        except PostError as e:
                            if "仍然存在" in str(e):
                                raise
                    upd["deleted_threads"] = fmt(now)
                    log(f"{p['id']}：Threads 已刪除 {len(ids)} 則並回查確認")
                except PostError as e:
                    res["errors"].append(f"{p['id']}：Threads 自動刪除失敗（{e}）")
                    res["alert"].append(f"{p['id']}：到了 delete_at，Threads 自動刪除失敗（{str(e)[:100]}）")
                    rc = 1
        if "ig" in p["done"] and not m.get("ig_delete_notified"):
            res["ig_delete"].append(f"{p['id']}：{m.get('urls_ig', '(沒有連結)')}")
            if not dry_run:
                upd["ig_delete_notified"] = fmt(now)
        if upd and not dry_run:
            IG.rewrite_meta(p["dir"] / "post.md", upd)
    return rc


def monitor(posts: list[dict], history: list[datetime], cfg: dict, now: datetime, no_token: bool) -> list[str]:
    out = []
    for p in posts:
        st = p["meta"].get("status")
        if st == "error":
            out.append(f"{p['id']}：發文失敗（{p['meta'].get('error', '')[:120]}）")
        elif st == "approved":
            try:
                due = effective_due(p, history, cfg)
            except (KeyError, ValueError):
                out.append(f"{p['id']}：已核准但 scheduled_at 格式錯誤")
                continue
            if now > due + timedelta(minutes=MONITOR_GRACE_MIN):
                why = "沒有 TC 權杖（請跑 tc_token_intake）" if no_token else "請看這次 run 的 log"
                out.append(f"{p['id']}：已核准、應在 {fmt(due)} 發出，超過 {MONITOR_GRACE_MIN} 分鐘仍沒發（{why}）")
    return out


def run(env: dict, now: datetime, dry_run: bool, queue: Path = QUEUE, state_dir: Path = STATE_DIR,
        cfg: dict | None = None, only: str = "") -> tuple[int, dict]:
    cfg = cfg if cfg is not None else settings()
    tok = tokens_from(env)
    for k in ("TC_THREADS_USER_ID", "TC_IG_USER_ID", "THREADS_USER_ID", "IG_USER_ID"):
        mask((env.get(k) or "").strip())
    res = {"alert": [], "posted": [], "skipped": [], "deferred": [], "errors": [], "ig_delete": []}
    dirs = sorted(d for d in queue.glob("*/") if (d / "post.md").is_file()) if queue.is_dir() else []
    if only:
        dirs = [d for d in dirs if d.name == only]
    posts, rc = [], 0
    for d in dirs:
        try:
            p = load(d)
        except Exception as e:  # noqa: BLE001
            res["errors"].append(f"{d.name}：讀不到（{e}）")
            continue
        errs = validate(p)
        if errs:
            if p["meta"].get("status") == "approved":
                res["errors"].append(f"{d.name}：{'；'.join(errs)}")
                rc = 1
            else:
                log(f"{d.name}（{p['meta'].get('status')}）格式提醒：{'；'.join(errs)}")
            p["invalid"] = True
        posts.append(p)
        log(f"{d.name}：status={p['meta'].get('status')}，平台={','.join(p['platforms'])}，{len(p['images'])} 張圖"
            + ("" if errs else "，格式 OK"))

    if not cfg["enabled"]:
        log("頻道② 開關關閉（post_quota.json tc.enabled=false）：略過，不連 Meta")
        return 0, res
    history = posted_times(state_dir)
    rc |= process_deletes(posts, tok, now, dry_run, res)
    approved = [p for p in posts if p["meta"].get("status") == "approved" and not p.get("invalid")]
    need = {x for p in approved for x in p["platforms"] if x not in p["done"]}
    no_token = any(not tok[x] for x in need)
    res["alert"] = monitor(posts, history, cfg, now, no_token) if not dry_run else []

    if not approved:
        log("沒有 status: approved 的稿 → 什麼都不做")
        return rc, res
    approved.sort(key=lambda p: sched(p))
    cand = None
    for p in approved:
        due = effective_due(p, history, cfg)
        if due <= now and cand is None:
            cand = p
        elif due > sched(p):
            res["deferred"].append(f"{p['id']} → {fmt(due)}")
            if not dry_run and p["meta"].get("deferred_until") != fmt(due):
                IG.rewrite_meta(p["dir"] / "post.md", {"deferred_until": fmt(due)})
            log(f"{p['id']}：超過每日上限或間隔不足，順延到 {fmt(due)}")
        elif due > now:
            log(f"{p['id']}：還沒到 {fmt(due)}")
    if cand is None:
        return rc, res
    todo = [x for x in cand["platforms"] if x not in cand["done"]]
    off = [x for x in todo if not cfg.get(x)]
    if off:
        log(f"{cand['id']}：post_quota.json tc.{'／'.join(off)}=false → 這篇先不發")
        return rc, res
    missing = [x for x in todo if not tok[x]]
    if missing:
        log(f"{cand['id']}：沒有 TC 權杖（{'、'.join(missing)}）→ 安靜跳過，不寄失敗信（請 Andy 跑 tc_token_intake）")
        res["skipped"].append(cand["id"])
        if not dry_run:
            sp = state_dir / "status.json"
            s = load_json(sp, {})
            if not s.get("no_token_since"):
                s["no_token_since"] = fmt(now)
                state_dir.mkdir(parents=True, exist_ok=True)
                sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return rc, res
    if dry_run:
        for plat in todo:
            try:
                uid, uname = preflight(plat, tok[plat], (env.get(f"TC_{plat.upper()}_USER_ID") or "").strip(),
                                       (env.get("THREADS_USER_ID" if plat == "threads" else "IG_USER_ID") or "").strip())
                log(f"[dry-run] {cand['id']}：會發到 {plat} @{uname}（{len(cand['images'])} 張圖）；沒有真的發")
            except PostError as e:
                log(f"[dry-run] ✗ {cand['id']}：{e}")
                rc = 1
        return rc, res
    sp = state_dir / "status.json"
    if load_json(sp, {}).get("no_token_since"):
        sp.write_text("{}\n", encoding="utf-8")
    try:
        msg = publish_one(cand, env, tok, now, state_dir)
        res["posted"].append(cand["id"])
        log(f"{cand['id']}：{msg}")
    except PostError as e:
        res["errors"].append(f"{cand['id']}：{e}")
        res["alert"].append(f"{cand['id']}：發文失敗（{str(e)[:120]}）")
        rc = 1
    return rc, res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="頻道② 科技透明圈 發文")
    ap.add_argument("--dry-run", action="store_true", help="只驗證，不發、不寫檔")
    ap.add_argument("--check", action="store_true", help="只檢查格式（不連外）")
    ap.add_argument("--post", default="", help="只處理這個資料夾名稱")
    ap.add_argument("--queue", default=str(QUEUE))
    a = ap.parse_args(argv)
    if a.check:
        bad = 0
        q = Path(a.queue)
        for d in sorted(q.glob("*/")) if q.is_dir() else []:
            if not (d / "post.md").is_file():
                continue
            p = load(d)
            errs = validate(p)
            print(("✗ " if errs else "✓ ") + f"{d.name}（{p['meta'].get('status')}）" + ("：" + "；".join(errs) if errs else ""))
            bad += bool(errs) and p["meta"].get("status") == "approved"
        return 1 if bad else 0
    rc, res = run(dict(os.environ), datetime.now(TAIPEI), a.dry_run, queue=Path(a.queue), only=a.post)
    for e in res["errors"]:
        log("✗ " + e)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"alert={'1' if res['alert'] else '0'}\n")
            f.write("reasons=" + redact("；".join(res["alert"])).replace("\n", " ") + "\n")
            f.write(f"ig_delete={'1' if res['ig_delete'] else '0'}\n")
            f.write("ig_delete_list=" + redact("；".join(res["ig_delete"])).replace("\n", " ") + "\n")
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(f"### 頻道② 科技透明圈（{'dry-run' if a.dry_run else '正式'}）\n\n")
            for k, label in (("posted", "已發"), ("deferred", "順延"), ("skipped", "沒權杖跳過"), ("alert", "告警"), ("errors", "錯誤")):
                for x in res[k]:
                    f.write(f"- {label}：{redact(x)}\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
