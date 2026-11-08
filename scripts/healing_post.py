"""頻道④「談晴說礙」自動發文（IG 輪播＋Threads 輪播）（2026-11-08）。

Andy 原話（2026-11-08）：「開通自動發文，這部分幫我想辦法自動化」。
工作流：.github/workflows/healing_post.yml（每天台北 20:27，21:57 補跑一次）。說明：docs/marketing/channels/healing/auto_post.md

佇列：docs/marketing/channels/healing/queue/<YYYYMMDD>_<名稱>/
  1.png … n.png   圖（Threads 用 PNG；IG 只收 JPEG → 同名 n.jpg，缺的用 --prepare 自動轉）
  caption.txt     內文（IG 用全文；Threads 超過 500 字照 social_publish 的規則截斷）
  meta.json       {"platforms": ["ig","threads"], "status": "approved", "publish_at": null 或 "2026-11-10T20:27+08:00"}
                  status 只有 approved 會發；publish_at 是「最早可以發的時間」（台北），null＝下一個時段就發。

規則：
  · 每次最多發 1 則：照資料夾名排序，取「最早一則 approved、時間到、還沒全部發完」的。
  · 開關 docs/marketing/channels/healing/post_quota.json：live=false 整個停；per_day＝台北每天最多幾則新貼文。
  · 防重發：state/posted.json 以資料夾名為鍵，各平台分開記；已發過的平台絕不再發（一個平台失敗，下次只補那個平台）。
  · 權杖只讀頻道④自己的 Secrets（絕不讀頻道①的 IG_ACCESS_TOKEN／THREADS_ACCESS_TOKEN）：
      HEALING_IG_ACCESS_TOKEN(_AUTO)、HEALING_THREADS_ACCESS_TOKEN(_AUTO)；
      HEALING_IG_USER_ID、HEALING_THREADS_USER_ID 選填（沒填就用權杖呼叫 /me 查）。
    兩把都沒有 → 空跑：印出會發什麼，不呼叫任何 Meta 端點，以成功結束，摘要寫「等待 Andy 設定權杖」。
  · Threads 權杖若是 1 小時短效（續期失敗）：有 THREADS_APP_SECRET 就自動換成 60 天長效，並用 META_SECRETS_PAT
    寫回 HEALING_THREADS_ACCESS_TOKEN_AUTO；沒有 app secret 就在摘要提醒換長效。
  · 失敗：每個平台重試 3 次（social_publish.retry_once）；仍失敗 → state/last_run.json 記原因、結束碼 1（工作流紅燈、GitHub 寄信）。
  · 權杖、帳號編號一律 ::add-mask:: 並經 social_publish.redact 才輸出。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import social_publish as SP  # noqa: E402  http／retry_once／wait_ready／publish_threads／resolve_user_id／redact

HEAL = ROOT / "docs" / "marketing" / "channels" / "healing"
QUEUE = HEAL / "queue"
STATE = HEAL / "state"
QUOTA = HEAL / "post_quota.json"
RAW = "https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/"
TAIPEI = timezone(timedelta(hours=8))
IG_MAX_CAPTION, IG_MAX_TAGS, IG_MAX_IMAGES = 2200, 30, 10
PLATFORMS = ("ig", "threads")
THREADS_EXCHANGE = "https://graph.threads.net/access_token"
THREADS_REFRESH = "https://graph.threads.net/refresh_access_token"


class QueueError(Exception):
    pass


# ---------- 設定與狀態 ----------
def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_quota(p: Path = QUOTA) -> dict:
    q = load_json(p, None)
    if not isinstance(q, dict):
        print(f"::warning::讀不到 {p.name}，當成 live=false（不發）")
        return {"live": False, "per_day": 0}
    return {"live": bool(q.get("live")), "per_day": int(q.get("per_day", 1) or 0)}


def tokens(env: dict) -> dict:
    """只讀頻道④的權杖：先讀續期寫回的 _AUTO，沒有才用 Andy 設的那把。"""
    out = {}
    for p in PLATFORMS:
        base = f"HEALING_{p.upper()}_ACCESS_TOKEN"
        t = (env.get(base + "_AUTO") or "").strip() or (env.get(base) or "").strip()
        if t:
            mask(t)
        out[p] = t
    return out


def mask(s: str) -> None:
    if s and s not in SP._SECRETS:
        SP._SECRETS.append(s)
        print("::add-mask::" + s, flush=True)


# ---------- 佇列 ----------
def images(folder: Path) -> list[str]:
    nums = sorted(int(m.group(1)) for f in folder.iterdir() if (m := re.fullmatch(r"(\d+)\.png", f.name)))
    return [f"{n}.png" for n in nums]


def read_item(folder: Path) -> dict:
    meta = load_json(folder / "meta.json", None)
    if not isinstance(meta, dict):
        raise QueueError("meta.json 讀不到或不是 JSON")
    cap_p = folder / "caption.txt"
    caption = cap_p.read_text(encoding="utf-8").strip() if cap_p.exists() else ""
    imgs = images(folder)
    return {"name": folder.name, "dir": folder, "meta": meta, "caption": caption, "images": imgs,
            "platforms": [p for p in (meta.get("platforms") or list(PLATFORMS))]}


def validate(it: dict) -> list[str]:
    errs = []
    m, imgs = it["meta"], it["images"]
    if m.get("status") not in ("draft", "approved", "posted"):
        errs.append(f"status 要是 draft／approved／posted，目前是 {m.get('status')!r}")
    bad = [p for p in it["platforms"] if p not in PLATFORMS]
    if bad:
        errs.append(f"platforms 只能是 ig／threads，多了 {bad}")
    if not imgs:
        errs.append("沒有圖（要有 1.png、2.png…）")
    if [f"{i}.png" for i in range(1, len(imgs) + 1)] != imgs:
        errs.append(f"圖要從 1.png 連號，目前是 {imgs}")
    if "ig" in it["platforms"] and len(imgs) > IG_MAX_IMAGES:
        errs.append(f"IG 輪播最多 {IG_MAX_IMAGES} 張，目前 {len(imgs)} 張")
    if not it["caption"]:
        errs.append("caption.txt 是空的或不存在")
    if len(it["caption"]) > IG_MAX_CAPTION:
        errs.append(f"內文 {len(it['caption'])} 字，超過 IG 上限 {IG_MAX_CAPTION}")
    if len(re.findall(r"#\S+", it["caption"])) > IG_MAX_TAGS:
        errs.append(f"#標籤超過 {IG_MAX_TAGS} 個")
    if m.get("publish_at"):
        try:
            publish_at(m)
        except ValueError:
            errs.append(f"publish_at 格式錯誤（要像 2026-11-10T20:27+08:00）：{m['publish_at']!r}")
    return errs


def publish_at(meta: dict):
    v = meta.get("publish_at")
    if not v:
        return None
    d = datetime.fromisoformat(str(v))
    return d if d.tzinfo else d.replace(tzinfo=TAIPEI)


def pending_platforms(it: dict, posted: dict) -> list[str]:
    done = posted.get(it["name"]) or {}
    return [p for p in it["platforms"] if p not in done]


def next_item(queue: Path, posted: dict, now: datetime) -> tuple[dict | None, list[str]]:
    """最早一則 approved、時間到、還有平台沒發的。回傳（那一則或 None, 略過原因清單）。"""
    notes = []
    if not queue.is_dir():
        return None, ["佇列資料夾不存在"]
    for d in sorted(x for x in queue.iterdir() if x.is_dir()):
        try:
            it = read_item(d)
        except QueueError as e:
            notes.append(f"{d.name}：{e}")
            continue
        if it["meta"].get("status") != "approved":
            continue
        if not pending_platforms(it, posted):
            continue
        errs = validate(it)
        if errs:
            raise QueueError(f"{d.name}：" + "；".join(errs))
        t = publish_at(it["meta"])
        if t and t > now:
            notes.append(f"{d.name}：還沒到 {t.isoformat()}")
            continue      # 指定時間還沒到 → 看下一則（不讓一則卡住整個佇列）
        return it, notes
    return None, notes


def started_today(posted: dict, now: datetime) -> int:
    """台北今天開始發的貼文則數（任一平台第一次發出的時間在今天）。"""
    today = now.astimezone(TAIPEI).date().isoformat()
    return sum(1 for v in posted.values() if isinstance(v, dict) and str(v.get("at", ""))[:10] == today)


# ---------- 圖片網址 ----------
def public_url(it: dict, fname: str) -> str:
    rel = (it["dir"]).relative_to(ROOT).as_posix() + "/" + fname
    return RAW + quote(rel)


def ig_files(it: dict) -> list[str]:
    return [f.replace(".png", ".jpg") for f in it["images"]]


def prepare(queue: Path = QUEUE) -> list[Path]:
    """IG 只收 JPEG：每個 n.png 缺 n.jpg 就轉一張（Pillow，品質 92）。回傳新產生的檔案。"""
    from PIL import Image
    made = []
    for d in sorted(x for x in queue.iterdir() if x.is_dir()):
        for f in images(d):
            j = d / f.replace(".png", ".jpg")
            if not j.exists():
                Image.open(d / f).convert("RGB").save(j, "JPEG", quality=92)
                made.append(j)
    return made


def check_public(url: str, want: str, tries: int = 6) -> None:
    """Meta 要能抓到圖：200 而且 content-type 對。剛推上 main 的檔，raw 可能慢一點 → 每 30 秒再試，最多 6 次。"""
    import requests
    last = ""
    for k in range(tries):
        try:
            r = requests.head(url, allow_redirects=True, timeout=30)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and ct.startswith(want):
                return
            last = f"HTTP {r.status_code} content-type={ct}"
        except requests.RequestException as e:
            last = f"連線失敗：{type(e).__name__}"
        if k < tries - 1:
            SP._sleep(30)
    raise RuntimeError(f"圖片網址 Meta 抓不到（{last}）：{url}；圖要先推上 main")


# ---------- Threads 權杖：短效自動換長效 ----------
def threads_token_check(token: str, env: dict, notes: list[str], saver=None) -> str:
    """先試續期（長效權杖滿 24 小時才能續）；續期失敗＝可能是 1 小時短效 → 有 app secret 就換成 60 天長效並寫回。"""
    try:
        d = SP.http("GET", THREADS_REFRESH, params={"grant_type": "th_refresh_token", "access_token": token})
        new = str(d.get("access_token") or token)
        if new != token:
            mask(new)
            _writeback(new, env, notes, saver, "續期後拿到新字串")
        return new
    except Exception as e:  # noqa: BLE001
        SP.log(f"[threads] 權杖續期失敗（可能是 1 小時短效，或長效權杖未滿 24 小時）：{SP.redact(e)}")
    secret = (env.get("THREADS_APP_SECRET") or "").strip()
    if not secret:
        notes.append("Threads 權杖可能是 1 小時短效（續期失敗）：請照 auto_post.md 第 5 節換成 60 天長效；"
                      "或在 Secrets 加 THREADS_APP_SECRET 讓工作流自動換")
        return token
    mask(secret)
    try:
        d = SP.http("GET", THREADS_EXCHANGE, params={"grant_type": "th_exchange_token", "client_secret": secret,
                                                     "access_token": token})
    except Exception as e:  # noqa: BLE001
        SP.log(f"[threads] 換長效失敗（權杖若本來就是長效，這是正常的）：{SP.redact(e)}")
        return token
    new = str(d.get("access_token") or "")
    if not new:
        return token
    mask(new)
    days = int(d.get("expires_in", 0) or 0) // 86400
    SP.log(f"[threads] 短效權杖已換成長效（約 {days} 天）")
    _writeback(new, env, notes, saver, "已換成長效")
    return new


def _writeback(new: str, env: dict, notes: list[str], saver, why: str) -> None:
    pat = (env.get("META_SECRETS_PAT") or "").strip()
    mask(pat)
    if not pat:
        notes.append(f"Threads 權杖{why}，但沒有 META_SECRETS_PAT 可寫回；這次先用新權杖發，下次仍讀舊的")
        return
    if saver is None:
        import meta_token_refresh as MTR
        saver = MTR.save_secret
    ok = saver("HEALING_THREADS_ACCESS_TOKEN_AUTO", new, env.get("GITHUB_REPOSITORY", "MiaoZiKe/tw-rotation"), pat)
    SP.log("[threads] 新權杖已寫回 HEALING_THREADS_ACCESS_TOKEN_AUTO" if ok else "[threads] 新權杖寫回失敗")
    if not ok:
        notes.append(f"Threads 權杖{why}，但寫回 HEALING_THREADS_ACCESS_TOKEN_AUTO 失敗")


# ---------- IG 輪播（流程同 ig_post.publish，改走 social_publish.http 以便遮蔽與輪詢）----------
def publish_ig(uid: str, token: str, urls: list[str], caption: str) -> dict:
    host = SP.IG_HOST

    def go():
        if len(urls) == 1:
            c = SP.http("POST", f"{host}/{uid}/media", data={"image_url": urls[0], "caption": caption,
                                                            "access_token": token})["id"]
        else:
            kids = []
            for u in urls:
                k = SP.http("POST", f"{host}/{uid}/media", data={"image_url": u, "is_carousel_item": "true",
                                                                "access_token": token})["id"]
                SP.wait_ready(host, token, k, "ig 輪播項", "status_code")
                kids.append(k)
            c = SP.http("POST", f"{host}/{uid}/media", data={"media_type": "CAROUSEL", "children": ",".join(kids),
                                                            "caption": caption, "access_token": token})["id"]
        SP.wait_ready(host, token, c, "ig", "status_code")
        return SP.http("POST", f"{host}/{uid}/media_publish", data={"creation_id": c, "access_token": token})["id"]

    pid = SP.retry_once("ig", go)
    link = ""
    try:
        link = SP.http("GET", f"{host}/{pid}", params={"fields": "permalink", "access_token": token}).get("permalink", "")
    except Exception:  # noqa: BLE001
        pass
    return {"id": pid, "link": link}


# ---------- 驗證模式（只建容器、等 FINISHED，不呼叫 publish）----------
def verify_ig(uid: str, token: str, urls: list[str], caption: str) -> str:
    host = SP.IG_HOST

    def go():
        if len(urls) == 1:
            c = SP.http("POST", f"{host}/{uid}/media", data={"image_url": urls[0], "caption": caption,
                                                            "access_token": token})["id"]
        else:
            kids = []
            for u in urls:
                k = SP.http("POST", f"{host}/{uid}/media", data={"image_url": u, "is_carousel_item": "true",
                                                                "access_token": token})["id"]
                SP.wait_ready(host, token, k, "ig 驗證輪播項", "status_code")
                kids.append(k)
            c = SP.http("POST", f"{host}/{uid}/media", data={"media_type": "CAROUSEL", "children": ",".join(kids),
                                                            "caption": caption, "access_token": token})["id"]
        SP.wait_ready(host, token, c, "ig 驗證", "status_code")
        return str(c)
    return SP.retry_once("ig", go)


def verify_threads(uid: str, token: str, urls: list[str], text: str) -> str:
    host = f"{SP.THREADS_HOST}/{uid}"

    def go():
        if len(urls) == 1:
            c = SP.http("POST", f"{host}/threads", data={"media_type": "IMAGE", "image_url": urls[0], "text": text,
                                                        "access_token": token})["id"]
        else:
            kids = []
            for u in urls[:20]:
                k = SP.http("POST", f"{host}/threads", data={"media_type": "IMAGE", "image_url": u,
                                                            "is_carousel_item": "true", "access_token": token})["id"]
                SP.wait_ready(SP.THREADS_HOST, token, k, "threads 驗證輪播項", "status")
                kids.append(k)
            c = SP.http("POST", f"{host}/threads", data={"media_type": "CAROUSEL", "children": ",".join(kids),
                                                        "text": text, "access_token": token})["id"]
        SP.wait_ready(SP.THREADS_HOST, token, c, "threads 驗證", "status")
        return str(c)
    return SP.retry_once("threads", go)


VERIFIERS = {"ig": verify_ig, "threads": verify_threads}


def is_verified(state: Path, p: str) -> bool:
    return bool((load_json(state / "verify.json", {}).get(p) or {}).get("verified"))


def mark_verified(state: Path, p: str, now: datetime, cid: str) -> None:
    v = load_json(state / "verify.json", {})
    v[p] = {"verified": True, "at": now.astimezone(TAIPEI).isoformat(timespec="seconds"), "container": str(cid)}
    state.mkdir(parents=True, exist_ok=True)
    (state / "verify.json").write_text(SP.redact(json.dumps(v, ensure_ascii=False, indent=1)) + "\n", encoding="utf-8")


def _live_token(p: str, env: dict, tok: dict, notes: list[str], saver) -> tuple[str, str]:
    token = tok[p]
    if p == "threads":
        token = threads_token_check(token, env, notes, saver)
    uid = SP.resolve_user_id(p, (env.get(f"HEALING_{p.upper()}_USER_ID") or "").strip(), token)
    if not uid:
        raise RuntimeError("查不到帳號編號（權杖無效或權限不足）")
    return token, uid


def sample_item(queue: Path, posted: dict, now: datetime) -> dict | None:
    """驗證／測試用的圖：下一則要發的；佇列發完了就用資料夾名最後一則。"""
    try:
        it, _ = next_item(queue, posted, now)
    except QueueError:
        it = None
    if it:
        return it
    ds = sorted(x for x in queue.iterdir() if x.is_dir()) if queue.is_dir() else []
    for d in reversed(ds):
        try:
            x = read_item(d)
        except QueueError:
            continue
        if x["images"]:
            return x
    return None


def run_verify(env: dict, now: datetime, dry_run: bool = False, queue: Path = QUEUE, state: Path = STATE,
               check=check_public, saver=None, verifiers: dict | None = None) -> tuple[int, dict]:
    """mode=verify：有權杖的平台各建一次輪播容器、等 FINISHED，不發布；通過寫 state/verify.json。"""
    ver = {**VERIFIERS, **(verifiers or {})}
    res = {"at": now.isoformat(timespec="seconds"), "mode": "verify" + ("（dry-run）" if dry_run else ""),
           "item": None, "posted": {}, "errors": {}, "notes": [], "summary": ""}
    it = sample_item(queue, load_json(state / "posted.json", {}), now)
    if it is None:
        res["summary"] = "佇列裡沒有可用來驗證的圖"
        return 1, res
    res["item"] = it["name"]
    tok = tokens(env)
    if dry_run or not any(tok.values()):
        res["summary"] = (f"驗證模式空跑：會用 {it['name']} 的圖建容器（不發布）" if dry_run else
                          "等待 Andy 設定權杖（HEALING_IG_ACCESS_TOKEN、HEALING_THREADS_ACCESS_TOKEN），驗證模式沒有跑")
        return 0, res
    fail, ok = False, []
    for p in PLATFORMS:
        if not tok[p]:
            res["notes"].append(f"{p} 沒有權杖，沒驗證")
            continue
        try:
            urls = [public_url(it, f) for f in (ig_files(it) if p == "ig" else it["images"])]
            for u in urls:
                check(u, "image/jpeg" if p == "ig" else "image/png")
            token, uid = _live_token(p, env, tok, res["notes"], saver)
            cid = ver[p](uid, token, urls, it["caption"] if p == "ig" else _threads_text(it["caption"]))
            mark_verified(state, p, now, cid)
            ok.append(f"{p} 通過（容器 {cid} FINISHED，未發布）")
        except Exception as e:  # noqa: BLE001
            fail = True
            res["errors"][p] = SP.redact(e)[:300]
    res["summary"] = "驗證模式：" + "；".join(ok + [f"{p} 失敗：{v}" for p, v in res["errors"].items()])
    _write_last(state, res, False)
    return (1 if fail else 0), res


# ---------- 刪文 ----------
def delete_media(p: str, mid: str, token: str) -> dict:
    """Threads：DELETE /v1.0/{id}（要 threads_delete 權限）。IG：試 DELETE /v24.0/{id}（Instagram 登入版不一定支援）。"""
    url = f"{SP.THREADS_HOST}/v1.0/{mid}" if p == "threads" else f"{SP.IG_HOST}/{mid}"
    d = SP.http("DELETE", url, params={"access_token": token})
    if isinstance(d, dict) and d.get("success") is False:
        raise RuntimeError("API 回 success=false")
    return d if isinstance(d, dict) else {}


def run_delete(env: dict, now: datetime, target: str, dry_run: bool = False, platforms=PLATFORMS,
               state: Path = STATE, deleter=delete_media) -> tuple[int, dict]:
    """mode=delete：target＝佇列資料夾名（刪該則已發的 IG／Threads）或貼文 id（在 posted.json 找；找不到當 Threads id）。
    Threads 刪掉 → posted.json 標 deleted；IG 刪不掉 → 列進 state/manual_delete.json，摘要寫「需手動」。"""
    res = {"at": now.isoformat(timespec="seconds"), "mode": "delete" + ("（dry-run）" if dry_run else ""),
           "item": target, "posted": {}, "errors": {}, "notes": [], "summary": ""}
    target = (target or "").strip()
    if not target:
        res["summary"] = "沒有指定要刪哪一則（target＝佇列資料夾名或貼文 id）"
        return 2, res
    posted_p = state / "posted.json"
    posted = load_json(posted_p, {})
    jobs = []      # (平台, 貼文 id, posted 鍵或 None)
    if target in posted:
        for p in platforms:
            r = (posted[target] or {}).get(p)
            if isinstance(r, dict) and r.get("id") and not r.get("deleted"):
                jobs.append((p, r["id"], target))
    else:
        for k, v in posted.items():
            for p in platforms:
                if isinstance((v or {}).get(p), dict) and v[p].get("id") == target and not v[p].get("deleted"):
                    jobs.append((p, target, k))
        if not jobs and re.fullmatch(r"\d{8}_.+", target):
            res["summary"] = f"{target}：這則還沒發過（posted.json 沒有紀錄），沒有東西可刪"
            return 0, res
        if not jobs and "threads" in platforms:
            jobs.append(("threads", target, None))
    if not jobs:
        res["summary"] = f"{target}：沒有找到還沒刪的貼文"
        return 0, res
    tok = tokens(env)
    if dry_run or not any(tok[p] for p, _, _ in jobs):
        res["summary"] = (("刪文空跑：會刪 " if dry_run else "等待 Andy 設定權杖，沒有刪：")
                          + "；".join(f"{p} {mid}" for p, mid, _ in jobs))
        return 0, res
    manual = load_json(state / "manual_delete.json", [])
    fail, done = False, []
    for p, mid, key in jobs:
        if not tok[p]:
            res["errors"][p] = f"沒有 {p} 權杖"
            fail = True
            continue
        try:
            deleter(p, mid, tok[p])
            done.append(f"{p} {mid} 已刪")
            if key:
                posted[key][p]["deleted"] = now.astimezone(TAIPEI).isoformat(timespec="seconds")
        except Exception as e:  # noqa: BLE001
            msg = SP.redact(e)[:300]
            if p == "ig":
                res["notes"].append(f"IG 無法用 API 刪除，需手動（{msg}）")
                link = (posted.get(key or "", {}).get("ig") or {}).get("link", "")
                if not any(x.get("id") == mid for x in manual):
                    manual.append({"id": mid, "key": key, "link": link, "at": now.isoformat(timespec="seconds"),
                                   "reason": msg})
                done.append(f"ig {mid} 需手動刪除")
            else:
                fail = True
                res["errors"][p] = msg
    state.mkdir(parents=True, exist_ok=True)
    posted_p.write_text(SP.redact(json.dumps(posted, ensure_ascii=False, indent=1)) + "\n", encoding="utf-8")
    if manual:
        (state / "manual_delete.json").write_text(SP.redact(json.dumps(manual, ensure_ascii=False, indent=1)) + "\n",
                                                  encoding="utf-8")
    res["summary"] = "刪文：" + "；".join(done + [f"{p} 失敗：{v}" for p, v in res["errors"].items()])
    _write_last(state, res, False)
    return (1 if fail else 0), res


def run_test_delete(env: dict, now: datetime, dry_run: bool = False, queue: Path = QUEUE, state: Path = STATE,
                    check=check_public, saver=None, publisher=None, deleter=delete_media) -> tuple[int, dict]:
    """mode=test_delete（只有 Threads；Andy 要求「先真發一則測試再刪」時才用）：
    真發一則測試輪播 → 確認拿到貼文 id → 立刻刪（60 秒內）→ 記 state/tests.json。IG 不做這個，只用驗證模式。"""
    import time
    publisher = publisher or SP.publish_threads
    res = {"at": now.isoformat(timespec="seconds"), "mode": "test_delete" + ("（dry-run）" if dry_run else ""),
           "item": None, "posted": {}, "errors": {}, "notes": [], "summary": ""}
    it = sample_item(queue, load_json(state / "posted.json", {}), now)
    if it is None:
        res["summary"] = "佇列裡沒有可用來測試的圖"
        return 1, res
    res["item"] = it["name"]
    tok = tokens(env)
    if dry_run or not tok["threads"]:
        res["summary"] = ("測試發文空跑：會用 " + it["name"] + " 的圖發一則 Threads 測試輪播再刪" if dry_run else
                          "等待 Andy 設定 HEALING_THREADS_ACCESS_TOKEN，測試發文沒有跑")
        return 0, res
    text = "（系統測試貼文，會在 60 秒內自動刪除）"
    rec = {"at": now.isoformat(timespec="seconds"), "item": it["name"]}
    rc = 0
    try:
        urls = [public_url(it, f) for f in it["images"]]
        for u in urls:
            check(u, "image/png")
        token, uid = _live_token("threads", env, tok, res["notes"], saver)
        t0 = time.monotonic()
        r = publisher(uid, token, text, urls)
        rec.update(id=str(r.get("id")), link=r.get("link", ""), published=True)
        try:
            deleter("threads", rec["id"], token)
            rec.update(deleted=True, seconds=round(time.monotonic() - t0, 1))
            res["summary"] = f"測試發文：Threads 發出 {rec['link'] or rec['id']}，{rec['seconds']} 秒內已刪除"
        except Exception as e:  # noqa: BLE001
            rc = 1
            rec.update(deleted=False, error=SP.redact(e)[:300])
            res["errors"]["threads"] = rec["error"]
            res["summary"] = f"⚠️ 測試貼文已發出但刪不掉（{rec['error']}），請手動刪：{rec['link'] or rec['id']}"
    except Exception as e:  # noqa: BLE001
        rc = 1
        rec.update(published=False, error=SP.redact(e)[:300])
        res["errors"]["threads"] = rec["error"]
        res["summary"] = f"測試發文失敗（沒有發出）：{rec['error']}"
    tests = load_json(state / "tests.json", [])
    tests.append(rec)
    state.mkdir(parents=True, exist_ok=True)
    (state / "tests.json").write_text(SP.redact(json.dumps(tests, ensure_ascii=False, indent=1)) + "\n", encoding="utf-8")
    _write_last(state, res, False)
    return rc, res


# ---------- 主流程 ----------
def run(env: dict, now: datetime, dry_run: bool = False, queue: Path = QUEUE, state: Path = STATE,
        quota_path: Path = QUOTA, publishers: dict | None = None, check=check_public, saver=None,
        verifiers: dict | None = None) -> tuple[int, dict]:
    """回傳（結束碼, 結果）。結果的 summary 給工作流摘要用。
    某平台權杖第一次出現（state/verify.json 沒有 verified 紀錄）→ 先跑驗證模式（只建容器不發布），通過才正式發。"""
    pub = {"ig": publish_ig, "threads": SP.publish_threads, **(publishers or {})}
    ver = {**VERIFIERS, **(verifiers or {})}
    res = {"at": now.isoformat(timespec="seconds"), "mode": "dry-run" if dry_run else "live", "item": None,
           "posted": {}, "errors": {}, "notes": [], "summary": ""}
    q = load_quota(quota_path)
    if not q["live"]:
        res["summary"] = "開關關閉（post_quota.json live=false），這次不發"
        return 0, res
    posted_p = state / "posted.json"
    posted = load_json(posted_p, {})
    try:
        it, skips = next_item(queue, posted, now)
    except QueueError as e:
        res["errors"]["queue"] = str(e)
        res["summary"] = f"佇列格式錯誤：{e}"
        _write_last(state, res, dry_run)
        return 1, res
    res["notes"] += skips
    if it is None:
        res["summary"] = "佇列已空（沒有 approved 且時間到、還沒發的貼文）"
        return 0, res
    todo = pending_platforms(it, posted)
    partial = it["name"] in posted          # 已發一半的那則一定補完，不算今天新的一則
    if not partial and started_today(posted, now) >= q["per_day"]:
        res["summary"] = f"今天已發 {started_today(posted, now)} 則（per_day={q['per_day']}），下一則留到明天：{it['name']}"
        return 0, res
    res["item"] = it["name"]
    tok = tokens(env)
    th_urls = [public_url(it, f) for f in it["images"]]
    ig_urls = [public_url(it, f) for f in ig_files(it)]
    missing = [p for p in todo if not tok[p]]
    if dry_run or not any(tok[p] for p in todo):
        why = "--dry-run" if dry_run else "缺頻道④權杖（HEALING_*_ACCESS_TOKEN）"
        res["mode"] = "dry-run" if dry_run else "空跑（缺權杖）"
        SP.log(f"空跑（{why}）：下一則 {it['name']}，要發 {todo}")
        for p in todo:
            if not is_verified(state, p):
                SP.log(f"[{p}] 權杖設好後第一輪會先跑驗證模式（只建輪播容器、等 FINISHED、不發布），通過才正式發")
        for p in todo:
            urls = ig_urls if p == "ig" else th_urls
            text = it["caption"] if p == "ig" else _threads_text(it["caption"])
            SP.log(f"[{p}] 會發 {'輪播' if len(urls) > 1 else '單圖'} {len(urls)} 張：")
            for u in urls:
                SP.log(f"    {u}")
            SP.log(f"[{p}] 文字（{len(text)} 字）：\n{text}")
        res["summary"] = (f"空跑（--dry-run）：下一則 {it['name']}" if dry_run else
                          f"等待 Andy 設定權杖（HEALING_IG_ACCESS_TOKEN、HEALING_THREADS_ACCESS_TOKEN）；下一則 {it['name']}")
        return 0, res

    # 真的發：先確認圖片網址 Meta 抓得到
    fail = False
    for p in missing:
        res["notes"].append(f"{p} 沒有權杖（HEALING_{p.upper()}_ACCESS_TOKEN），這個平台先不發；設好後下一輪會補")
    entry = posted.setdefault(it["name"], {})
    for p in [x for x in todo if tok[x]]:
        try:
            urls = ig_urls if p == "ig" else th_urls
            for u in urls:
                check(u, "image/jpeg" if p == "ig" else "image/png")
            token = tok[p]
            if p == "threads":
                token = threads_token_check(token, env, res["notes"], saver)
            uid = SP.resolve_user_id(p, (env.get(f"HEALING_{p.upper()}_USER_ID") or "").strip(), token)
            if not uid:
                raise RuntimeError("查不到帳號編號（權杖無效或權限不足）")
            if not is_verified(state, p):
                SP.log(f"[{p}] 這把權杖還沒驗證過 → 先跑驗證模式（只建輪播容器、等 FINISHED，不發布）")
                try:
                    cid = ver[p](uid, token, urls, it["caption"] if p == "ig" else _threads_text(it["caption"]))
                except Exception as e:  # noqa: BLE001
                    raise RuntimeError(f"驗證模式失敗（沒有發文）：{SP.redact(e)}") from None
                mark_verified(state, p, now, cid)
                res["notes"].append(f"{p} 驗證模式通過（容器 {cid} 已 FINISHED，未發布），接著正式發文")
            if p == "threads":      # publish_threads(uid, token, text, urls)：超過 500 字自己會截斷
                r = pub[p](uid, token, _threads_text(it["caption"]), urls)
            else:                   # publish_ig(uid, token, urls, caption)：IG 用 caption.txt 全文
                r = pub[p](uid, token, urls, it["caption"])
            r = {"id": str(r.get("id")), "link": r.get("link") or r.get("permalink") or "",
                 "at": now.astimezone(TAIPEI).isoformat(timespec="seconds")}
            entry[p] = r
            entry.setdefault("at", r["at"])
            res["posted"][p] = r
            SP.log(f"[{p}] 已發布 id={r['id']} {r['link']}")
        except Exception as e:  # noqa: BLE001
            fail = True
            res["errors"][p] = SP.redact(e)[:300]
            SP.log(f"[{p}] 發布失敗（已重試）：{SP.redact(e)}")
    if not entry:
        posted.pop(it["name"], None)
    else:
        posted_p.parent.mkdir(parents=True, exist_ok=True)
        posted_p.write_text(SP.redact(json.dumps(posted, ensure_ascii=False, indent=1)) + "\n", encoding="utf-8")
        if not pending_platforms(it, posted):
            m = dict(it["meta"], status="posted",
                     urls={p: (entry[p].get("link") or entry[p]["id"]) for p in it["platforms"]})
            (it["dir"] / "meta.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    links = "；".join(f"{p} {v['link'] or v['id']}" for p, v in res["posted"].items())
    errs = "；".join(f"{p} 失敗：{v}" for p, v in res["errors"].items())
    res["summary"] = f"{it['name']}：" + ("；".join(x for x in (links and f"已發 {links}", errs) if x) or "沒有發出")
    _write_last(state, res, dry_run)
    return (1 if fail else 0), res


def _threads_text(caption: str) -> str:
    if len(caption) > SP.THREADS_TEXT_MAX:
        return caption[:SP.THREADS_TEXT_MAX - 1] + "…"
    return caption


def _write_last(state: Path, res: dict, dry_run: bool) -> None:
    if dry_run:
        return
    state.mkdir(parents=True, exist_ok=True)
    out = {k: res[k] for k in ("at", "mode", "item", "posted", "errors", "notes", "summary")}
    (state / "last_run.json").write_text(SP.redact(json.dumps(out, ensure_ascii=False, indent=1)) + "\n",
                                         encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="頻道④談晴說礙自動發文")
    ap.add_argument("--dry-run", action="store_true", help="只印出會發什麼，不呼叫任何 Meta 端點、不寫 state")
    ap.add_argument("--prepare", action="store_true", help="把佇列裡缺的 n.jpg 從 n.png 轉出來（IG 只收 JPEG）")
    ap.add_argument("--mode", default="post", choices=["post", "verify", "delete", "test_delete"],
                    help="post＝正式發（預設）；verify＝只建容器不發布；delete＝刪 --target；test_delete＝Threads 真發測試再刪")
    ap.add_argument("--target", default="", help="mode=delete：佇列資料夾名或貼文 id")
    ap.add_argument("--platform", default="all", choices=["all", "ig", "threads"], help="mode=delete 只刪哪個平台")
    a = ap.parse_args(argv)
    if a.prepare:
        made = prepare()
        print("新產生 JPEG：" + ("、".join(str(p.relative_to(ROOT)) for p in made) or "無"))
        return 0
    env, now = dict(os.environ), datetime.now(TAIPEI)
    if a.mode == "verify":
        rc, res = run_verify(env, now, a.dry_run)
    elif a.mode == "delete":
        plats = PLATFORMS if a.platform == "all" else (a.platform,)
        rc, res = run_delete(env, now, a.target, a.dry_run, plats)
    elif a.mode == "test_delete":
        rc, res = run_test_delete(env, now, a.dry_run)
    else:
        rc, res = run(env, now, a.dry_run)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(f"### 談晴說礙自動發文（{res['mode']}）\n\n{SP.redact(res['summary'])}\n")
            for p, v in res["posted"].items():
                f.write(f"\n- {p}：{v['link'] or v['id']}")
            for n in res["notes"]:
                f.write(f"\n- ⚠️ {SP.redact(n)}")
            f.write("\n")
    for n in res["notes"]:
        print("::warning::" + SP.redact(n))
    SP.log("結果：" + res["summary"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
