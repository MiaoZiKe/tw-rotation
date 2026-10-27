"""社群自動發布：讀 manifest.json，發 Threads（單圖／多圖輪播）與 IG 限動。

用法：
  python scripts/social_publish.py --manifest <資料夾>/manifest.json --base-url <圖片公開網址前綴> [--dry-run]

金鑰只從環境變數讀（缺權杖的平台改 dry-run、不報錯）：
  THREADS_USER_ID  THREADS_ACCESS_TOKEN  IG_USER_ID  IG_ACCESS_TOKEN
  USER_ID 空白但有權杖時，用權杖自動查帳號編號（2026-10-26）：
    Threads  GET https://graph.threads.net/v1.0/me?fields=id
    IG       GET https://graph.instagram.com/v24.0/me?fields=user_id,username（取 user_id）
  查到的編號只在 log 印末 4 碼。
★ 總開關（2026-10-26）：repo 檔 docs/marketing/social_unit/LIVE_ENABLED 存在才真的發；不存在＝一律 dry-run（即使有金鑰）。
  Andy 說「開始發」之前不建立這個檔。
權杖絕不寫檔、不進 log（輸出一律先過 redact）。
防重複：manifest 旁的 posted.json（工作流會把它留在 social-snaps 分支）。
官方做法與來源見 docs/marketing/social_unit/meta_api_setup.md。
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

THREADS_HOST = "https://graph.threads.net"
THREADS_ME = "https://graph.threads.net/v1.0/me"
IG_ME = "https://graph.instagram.com/v24.0/me"
LIVE_FLAG = Path(__file__).resolve().parents[1] / "docs" / "marketing" / "social_unit" / "LIVE_ENABLED"
IG_HOST = "https://graph.instagram.com/v24.0"
THREADS_TEXT_MAX = 500
POLL_EVERY = 5      # 秒
POLL_TIMEOUT = 300  # 秒（Meta 建議最多輪詢 5 分鐘）
HTTP_TIMEOUT = 60

_SECRETS: list[str] = []  # 目前出現過的權杖，輸出前一律遮蔽


def redact(s) -> str:
    s = str(s)
    for t in _SECRETS:
        if t:
            s = s.replace(t, "***")
    return s


def log(*a):
    print(redact(" ".join(str(x) for x in a)), flush=True)


def http(method: str, url: str, **kw) -> dict:
    """單一出口，方便測試 mock。回傳 JSON；HTTP 錯誤丟 RuntimeError（訊息已遮蔽權杖）。"""
    r = requests.request(method, url, timeout=HTTP_TIMEOUT, **kw)
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:200]}
    if r.status_code >= 400 or (isinstance(data, dict) and "error" in data):
        err = data.get("error", data) if isinstance(data, dict) else data
        raise RuntimeError(redact(f"HTTP {r.status_code} {json.dumps(err, ensure_ascii=False)[:300]}"))
    return data


def _sleep(sec):
    time.sleep(sec)


def retry_once(label, fn, tries: int = 3):
    """失敗重試（2026-10-27 起最多 3 次、間隔 5／15 秒；IG 偶發「Media Not Found」重建容器通常就過）。"""
    for k in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if k == tries - 1:
                raise
            log(f"[{label}] 失敗，第 {k + 1} 次重試：{redact(e)}")
            _sleep(5 if k == 0 else 15)


def wait_ready(host, token, cid, label, field):
    """輪詢容器狀態到 FINISHED。Threads 欄位 status、IG 欄位 status_code。"""
    waited = 0
    _sleep(3)      # 剛建立的容器馬上查常回「Media Not Found」（IG 2207006，2026-10-27 盤中測試踩到）→ 先等一下
    while True:
        try:
            d = http("GET", f"{host}/{cid}", params={"fields": field, "access_token": token})
        except RuntimeError as e:
            if ("2207006" in str(e) or "does not exist" in str(e)) and waited < 60:      # 還沒同步好，不是真的失敗
                _sleep(POLL_EVERY)
                waited += POLL_EVERY
                continue
            raise
        st = d.get(field)
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"{label} 媒體處理失敗：{st} {d.get('error_message', '')}")
        if waited >= POLL_TIMEOUT:
            raise RuntimeError(f"{label} 媒體處理逾時（{POLL_TIMEOUT} 秒）狀態={st}")
        _sleep(POLL_EVERY)
        waited += POLL_EVERY


# ---------- 總開關與帳號編號 ----------
def live_enabled(flag: Path | None = None) -> bool:
    """總開關：repo 檔 LIVE_ENABLED 存在＝可以真的發；不存在＝一律 dry-run。
    例外：workflow 的「測試真發一篇」（live_test，2026-10-27 Andy）設 SOCIAL_LIVE_TEST=1 → 這一輪可以發（只在手動派工時）。"""
    if os.environ.get("SOCIAL_LIVE_TEST") == "1":
        return True
    return Path(flag or LIVE_FLAG).exists()


def mask_id(x) -> str:
    x = str(x or "")
    return ("…" + x[-4:]) if len(x) > 4 else "…"


def resolve_user_id(platform: str, env_id: str, token: str) -> str:
    """USER_ID 有填就用；空白但有權杖 → 用權杖查（Threads /me?fields=id、IG /me?fields=user_id,username）。查不到回 ''。
    查到的編號不印全文（只印末 4 碼），並加進遮蔽清單與 ::add-mask::。"""
    if env_id:
        return env_id
    if not token:
        return ""
    try:
        if platform == "threads":
            uid = str(http("GET", THREADS_ME, params={"fields": "id", "access_token": token}).get("id") or "")
        else:
            uid = str(http("GET", IG_ME, params={"fields": "user_id,username", "access_token": token}).get("user_id") or "")
    except Exception as e:  # noqa: BLE001
        log(f"[{platform}] 用權杖查帳號編號失敗：{redact(e)}")
        return ""
    if not uid:
        log(f"[{platform}] 用權杖查帳號編號：回應裡沒有編號")
        return ""
    print("::add-mask::" + uid, flush=True)
    if len(uid) >= 6:
        _SECRETS.append(uid)
    log(f"[{platform}] USER_ID 沒填，已用權杖查到帳號編號（末 4 碼 {mask_id(uid)}）")
    return uid


# ---------- 權杖延長（每次發文前；失敗不中斷）----------
def refresh_token(platform, token):
    """回傳（可能是新的）權杖。延長後換新字串時只提醒、不印值，並用 ::add-mask:: 遮蔽。"""
    if platform == "threads":
        url, gt = f"{THREADS_HOST}/refresh_access_token", "th_refresh_token"
    else:
        url, gt = "https://graph.instagram.com/refresh_access_token", "ig_refresh_token"
    try:
        d = http("GET", url, params={"grant_type": gt, "access_token": token})
    except Exception as e:  # noqa: BLE001
        log(f"[{platform}] 權杖延長失敗（不影響這次發文）：{redact(e)}")
        return token
    new = d.get("access_token") or token
    days = int(d.get("expires_in", 0)) // 86400
    if new != token:
        _SECRETS.append(new)
        print("::add-mask::" + new, flush=True)
        log(f"[{platform}] 權杖已延長（約 {days} 天），但拿到新字串；GitHub Secrets 需人工更新，舊字串到期前仍可用")
    else:
        log(f"[{platform}] 權杖已延長，剩約 {days} 天（字串不變，Secrets 不用動）")
    return new


# ---------- Threads ----------
def publish_threads(uid, token, text, urls):
    host = f"{THREADS_HOST}/{uid}"
    if len(text) > THREADS_TEXT_MAX:
        log(f"[threads] 文字 {len(text)} 字超過 {THREADS_TEXT_MAX}，已截斷")
        text = text[:THREADS_TEXT_MAX - 1] + "…"

    def go():
        if not urls:
            c = http("POST", f"{host}/threads", data={"media_type": "TEXT", "text": text, "access_token": token})
            cid = c["id"]
        elif len(urls) == 1:
            c = http("POST", f"{host}/threads", data={"media_type": "IMAGE", "image_url": urls[0],
                                                     "text": text, "access_token": token})
            cid = c["id"]
        else:
            kids = []
            for u in urls[:20]:
                k = http("POST", f"{host}/threads", data={"media_type": "IMAGE", "image_url": u,
                                                         "is_carousel_item": "true", "access_token": token})
                wait_ready(THREADS_HOST, token, k["id"], "threads 輪播項", "status")
                kids.append(k["id"])
            c = http("POST", f"{host}/threads", data={"media_type": "CAROUSEL", "children": ",".join(kids),
                                                     "text": text, "access_token": token})
            cid = c["id"]
        wait_ready(THREADS_HOST, token, cid, "threads", "status")
        return http("POST", f"{host}/threads_publish", data={"creation_id": cid, "access_token": token})["id"]

    pid = retry_once("threads", go)
    link = ""
    try:
        link = http("GET", f"{THREADS_HOST}/{pid}", params={"fields": "permalink", "access_token": token}).get("permalink", "")
    except Exception:  # noqa: BLE001
        pass
    return {"id": pid, "link": link}


def publish_threads_reply(uid, token, text, reply_to):
    """同一篇底下的第一則回覆（2026-10-27 盤前：主文放今日焦點，盤面解讀＋融資放回覆）。Threads API：建容器時帶 reply_to_id。"""
    host = f"{THREADS_HOST}/{uid}"
    if len(text) > THREADS_TEXT_MAX:
        text = text[:THREADS_TEXT_MAX - 1] + "…"

    def go():
        c = http("POST", f"{host}/threads", data={"media_type": "TEXT", "text": text, "reply_to_id": reply_to, "access_token": token})
        wait_ready(THREADS_HOST, token, c["id"], "threads 回覆", "status")
        return http("POST", f"{host}/threads_publish", data={"creation_id": c["id"], "access_token": token})["id"]

    pid = retry_once("threads", go)
    link = ""
    try:
        link = http("GET", f"{THREADS_HOST}/{pid}", params={"fields": "permalink", "access_token": token}).get("permalink", "")
    except Exception:  # noqa: BLE001
        pass
    return {"id": pid, "link": link}


# ---------- IG 限動 ----------
def publish_story(uid, token, url):
    def go():
        c = http("POST", f"{IG_HOST}/{uid}/media", data={"media_type": "STORIES", "image_url": url, "access_token": token})
        wait_ready(IG_HOST, token, c["id"], "ig 限動", "status_code")
        return http("POST", f"{IG_HOST}/{uid}/media_publish", data={"creation_id": c["id"], "access_token": token})["id"]

    pid = retry_once("ig", go)
    link = ""
    try:
        link = http("GET", f"{IG_HOST}/{pid}", params={"fields": "permalink", "access_token": token}).get("permalink", "")
    except Exception:  # noqa: BLE001
        pass
    return {"id": pid, "link": link}


# ---------- 主流程 ----------
def slot_key(m: dict) -> str:
    t = m.get("taken_at", "")
    date = t[:10]
    if m.get("kind") == "close":      # 2026-10-26 盤後法人＋融資融券合併：以資料日為鍵（融資到齊可能已過午夜）
        return f"close-{(m.get('data_date') or date)[:10]}"
    if m.get("kind") == "credit":      # 盤後融資：以融資資料日為鍵（常在隔天清晨才到齊，用發文日會錯天）
        return f"credit-{(m.get('data_date') or date)[:10]}"
    kind = m.get("kind", "intraday")
    if kind == "premarket":      # 盤前一天一篇，以目標開盤日為鍵（跟 social_premarket.py 的 premarket-<目標日> 同一套）
        return f"premarket-{(m.get('data_date') or date)[:10]}"
    if kind == "intraday":
        return f"intraday-{date}"     # 盤中一天一篇（台北 12:00，2026-10-26）
    return f"{kind}-{date}-{t[11:13]}"  # 同一小時算同一時段


def load_posted(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run(manifest_path, base_url, dry_run=False, env=None, flag=None) -> int:
    env = os.environ if env is None else env
    live = live_enabled(flag)
    if not live and not dry_run:
        log(f"總開關關閉（{Path(flag or LIVE_FLAG).name} 不存在）→ dry-run，不真的發布")
    off = dry_run or not live
    mp = Path(manifest_path)
    m = json.loads(mp.read_text(encoding="utf-8"))
    for k in ("THREADS_ACCESS_TOKEN", "IG_ACCESS_TOKEN"):
        if env.get(k):
            _SECRETS.append(env[k])
    key = slot_key(m)
    posted_file = mp.parent / "posted.json"
    posted = load_posted(posted_file)
    done = posted.get(key, {})
    base = base_url.rstrip("/")

    def pub(rel):
        return f"{base}/{quote(Path(rel).as_posix())}"

    th = m.get("threads") or {}
    th_urls = [pub(i) for i in th.get("images", [])]
    st_urls = [pub(i) for i in m.get("story", [])]
    fail = False
    log(f"時段 {key}（{m.get('taken_at')}）")
    # 帳號編號：只有真的要發（總開關開、不是 dry-run、有權杖）才去查
    th_uid = ig_uid = ""
    if not off:
        th_uid = resolve_user_id("threads", env.get("THREADS_USER_ID", ""), env.get("THREADS_ACCESS_TOKEN", ""))
        ig_uid = resolve_user_id("ig", env.get("IG_USER_ID", ""), env.get("IG_ACCESS_TOKEN", ""))

    # Threads
    only = os.environ.get("SOCIAL_ONLY", "")      # 測試補發用：ig＝只發 IG 限動（Threads 已發過）、threads＝只發 Threads
    if not th.get("text") or only == "ig":
        pass
    elif "threads" in done:
        log(f"[threads] 已發過（{done['threads'].get('link') or done['threads'].get('id')}），略過")
    elif off or not (th_uid and env.get("THREADS_ACCESS_TOKEN")):
        why = "--dry-run" if dry_run else ("總開關關閉" if not live else
               ("缺 THREADS_ACCESS_TOKEN" if not env.get("THREADS_ACCESS_TOKEN") else "查不到 Threads 帳號編號"))
        if live and not dry_run and env.get("THREADS_ACCESS_TOKEN"):
            fail = True      # 有權杖、開關也開了卻查不到編號 → 讓工作流變紅，不要默默不發
        mode = "單圖" if len(th_urls) == 1 else ("輪播" if th_urls else "純文字")
        log(f"[threads] dry-run（{why}）{mode}，圖 {th_urls}\n文字：\n{th['text']}")
    else:
        try:
            tok = refresh_token("threads", env["THREADS_ACCESS_TOKEN"])
            done["threads"] = publish_threads(th_uid, tok, th["text"], th_urls)
            log(f"[threads] 已發布 id={done['threads']['id']} {done['threads']['link']}")
        except Exception as e:  # noqa: BLE001
            fail = True
            log(f"[threads] 發布失敗：{redact(e)}")
    # 同一篇底下的第一則回覆（盤前：盤面解讀＋融資）；主文已發、回覆還沒發才補
    if th.get("reply") and only != "ig" and "threads" in done and "threads_reply" not in done:
        if off or not (th_uid and env.get("THREADS_ACCESS_TOKEN")):
            log(f"[threads] dry-run 回覆：\n{th['reply']}")
        else:
            try:
                tok = refresh_token("threads", env["THREADS_ACCESS_TOKEN"])
                done["threads_reply"] = publish_threads_reply(th_uid, tok, th["reply"], done["threads"]["id"])
                log(f"[threads] 回覆已發布 id={done['threads_reply']['id']} {done['threads_reply']['link']}")
            except Exception as e:  # noqa: BLE001
                fail = True
                log(f"[threads] 回覆發布失敗：{redact(e)}")
    elif th.get("reply") and off:
        log(f"[threads] dry-run 回覆：\n{th['reply']}")

    # IG 限動
    if not st_urls or only == "threads":
        pass
    elif "story" in done and len(done["story"]) >= len(st_urls):
        log("[ig] 限動已發過，略過")
    elif off or not (ig_uid and env.get("IG_ACCESS_TOKEN")):
        why = "--dry-run" if dry_run else ("總開關關閉" if not live else
               ("缺 IG_ACCESS_TOKEN" if not env.get("IG_ACCESS_TOKEN") else "查不到 IG 帳號編號"))
        if live and not dry_run and env.get("IG_ACCESS_TOKEN"):
            fail = True
        log(f"[ig] dry-run（{why}）限動 {len(st_urls)} 張：{st_urls}")
    else:
        try:
            tok = refresh_token("ig", env["IG_ACCESS_TOKEN"])
            res = done.setdefault("story", [])
            for u in st_urls[len(res):]:  # 中途失敗重跑時，只補沒發的
                res.append(publish_story(ig_uid, tok, u))
                log(f"[ig] 限動已發布 id={res[-1]['id']} {res[-1]['link']}")
        except Exception as e:  # noqa: BLE001
            fail = True
            log(f"[ig] 發布失敗：{redact(e)}")

    if done and not off:
        # 記下台北發布時間：social_snap.posted_ok 用它判斷紀錄是不是正式時段發的（測試誤記不算）
        done.setdefault("at", datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"))
        posted[key] = done
        posted_file.write_text(json.dumps(posted, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if fail else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--base-url", default=os.environ.get("SOCIAL_BASE_URL", ""),
                    help="圖片公開網址前綴，圖片網址 = 前綴/相對路徑")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not a.base_url:
        a.base_url = "https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/social-snaps"
    return run(a.manifest, a.base_url, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
