"""W6 成效自動回收：抓 IG／Threads 洞察，append 進 state/insights.json（不覆寫歷史）。
用法：INSIGHTS_PATH=state/insights.json python3 scripts/social_insights.py
只印指標與成敗，不印權杖。權杖失效時印 ::error:: 並寫進 state，結束碼 1。"""
import json, os, re, sys, urllib.request, urllib.parse, urllib.error, datetime

IG_T = os.environ.get("IG_ACCESS_TOKEN", "")
TH_T = os.environ.get("THREADS_ACCESS_TOKEN", "")
PATH = os.environ.get("INSIGHTS_PATH", "state/insights.json")
TZ = datetime.timezone(datetime.timedelta(hours=8))
NOW = datetime.datetime.now(TZ)
TODAY = NOW.strftime("%Y-%m-%d")


def mask(s):
    s = str(s)
    for v in (IG_T, TH_T):
        if v:
            s = s.replace(v, "***")
    return re.sub(r"(access_token=)[^&\s\"']+", r"\1***", s)[:300]


def get(url, **p):
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": {"message": type(e).__name__}}


def err(b):
    e = (b or {}).get("error", {})
    return {"code": e.get("code"), "message": mask(e.get("message"))}


def ts(n):
    return int((NOW - datetime.timedelta(days=n)).timestamp())


def vals(b):
    out = {}
    for m in b.get("data", []):
        if "total_value" in m:
            out[m["name"]] = m["total_value"].get("value")
        else:
            v = m.get("values") or []
            out[m["name"]] = v[-1].get("value") if v else None
    return out


def ig():
    rec, tok = {}, {"status": "missing"}
    if not IG_T:
        return rec, tok
    base = "https://graph.instagram.com/v24.0"
    st, b = get(base + "/me", fields="user_id,username", access_token=IG_T)
    if st != 200:
        return {"error": err(b)}, {"status": "invalid", **err(b)}
    tok = {"status": "valid"}
    rec["username"] = b.get("username")
    st, b = get(base + "/me/insights", metric="reach,views", period="day", metric_type="total_value",
                since=ts(1), until=ts(0), access_token=IG_T)
    rec["account"] = vals(b) if st == 200 else {"error": err(b)}
    st, b = get(base + "/me/insights", metric="follower_count", period="day",
                since=ts(2), until=ts(0), access_token=IG_T)
    rec["follower_count"] = vals(b).get("follower_count") if st == 200 else {"error": err(b)}
    st, b = get(base + "/me/media", fields="id,timestamp,media_product_type,permalink", limit=10, access_token=IG_T)
    posts = []
    for m in (b.get("data", []) if st == 200 else []):
        s2, b2 = get(base + "/%s/insights" % m["id"], metric="views,reach", access_token=IG_T)
        posts.append({"id": m["id"], "time": m.get("timestamp"), "type": m.get("media_product_type"),
                      **(vals(b2) if s2 == 200 else {"error": err(b2)})})
    rec["posts"] = posts
    return rec, tok


def threads():
    rec, tok = {}, {"status": "missing"}
    if not TH_T:
        return rec, tok
    base = "https://graph.threads.net/v1.0"
    st, b = get(base + "/me", fields="id,username", access_token=TH_T)
    if st != 200:
        return {"error": err(b)}, {"status": "invalid", **err(b)}
    tok = {"status": "valid"}
    rec["username"] = b.get("username")
    st, b = get(base + "/me/threads_insights", metric="views", since=ts(1), until=ts(0), access_token=TH_T)
    rec["views_daily"] = ([{"end_time": v.get("end_time"), "value": v.get("value")}
                           for m in b.get("data", []) for v in (m.get("values") or [])]
                          if st == 200 else {"error": err(b)})
    st, b = get(base + "/me/threads_insights", metric="followers_count", access_token=TH_T)
    rec["followers_count"] = vals(b).get("followers_count") if st == 200 else {"error": err(b)}
    st, b = get(base + "/me/threads", fields="id,timestamp,permalink", limit=10, access_token=TH_T)
    posts = []
    for m in (b.get("data", []) if st == 200 else []):
        s2, b2 = get(base + "/%s/insights" % m["id"], metric="views,likes,replies", access_token=TH_T)
        posts.append({"id": m["id"], "time": m.get("timestamp"),
                      **(vals(b2) if s2 == 200 else {"error": err(b2)})})
    rec["posts"] = posts
    return rec, tok



CATALOG_PATH = os.environ.get("CATALOG_PATH", "state/posts_catalog.json")
FULL = os.environ.get("CATALOG_FULL", "") == "1"  # 1＝回補全部歷史；否則只更新最近 30 則


def paged(url, limit_total, **p):
    """分頁抓到底（或抓滿 limit_total 筆）；用 paging.next 續抓，權杖不印。"""
    rows, st, b = [], 0, {}
    st, b = get(url, **p)
    while st == 200:
        rows += b.get("data", [])
        nxt = (b.get("paging") or {}).get("next")
        if not nxt or len(rows) >= limit_total:
            break
        try:
            with urllib.request.urlopen(nxt, timeout=30) as r:
                b = json.loads(r.read().decode())
        except Exception as e:
            print("分頁中斷:", type(e).__name__)
            break
    return rows


def metrics(base, pid, names, tok):
    """逐一指標抓，某指標該貼文型態不支援就略過，不影響其他。"""
    out = {}
    s2, b2 = get(base + "/%s/insights" % pid, metric=",".join(names), access_token=tok)
    if s2 == 200:
        return vals(b2)
    for n in names:
        s3, b3 = get(base + "/%s/insights" % pid, metric=n, access_token=tok)
        if s3 == 200:
            out.update(vals(b3))
    return out


def catalog():
    try:
        cat = json.load(open(CATALOG_PATH, encoding="utf-8"))
    except Exception:
        cat = {"posts": {}}
    cat.setdefault("posts", {})
    cap = 100000 if FULL else 30
    n = {"ig": 0, "threads": 0}
    if IG_T:
        base = "https://graph.instagram.com/v24.0"
        rows = paged(base + "/me/media", cap, access_token=IG_T, limit=50,
                     fields="id,caption,media_type,media_product_type,permalink,timestamp")
        for m in rows:
            met = metrics(base, m["id"], ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions"], IG_T)
            cat["posts"]["ig:" + m["id"]] = {"platform": "ig", "id": m["id"], "time": m.get("timestamp"),
                "text": m.get("caption") or "", "media_type": m.get("media_type"),
                "product_type": m.get("media_product_type"), "permalink": m.get("permalink"),
                "metrics": met, "updated": NOW.isoformat(timespec="seconds")}
            n["ig"] += 1
    if TH_T:
        base = "https://graph.threads.net/v1.0"
        rows = paged(base + "/me/threads", cap, access_token=TH_T, limit=50,
                     fields="id,text,media_type,permalink,timestamp,shortcode,is_quote_post")
        for m in rows:
            met = metrics(base, m["id"], ["views", "likes", "replies", "reposts", "quotes", "shares"], TH_T)
            cat["posts"]["th:" + m["id"]] = {"platform": "threads", "id": m["id"], "time": m.get("timestamp"),
                "text": m.get("text") or "", "media_type": m.get("media_type"),
                "permalink": m.get("permalink"), "metrics": met, "updated": NOW.isoformat(timespec="seconds")}
            n["threads"] += 1
    cat["updated_at"] = NOW.isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(CATALOG_PATH) or ".", exist_ok=True)
    json.dump(cat, open(CATALOG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("貼文目錄：本次寫入 IG", n["ig"], "Threads", n["threads"], "；目錄總數", len(cat["posts"]), "（全量回補）" if FULL else "")


igr, igt = ig()
thr, tht = threads()
try:
    state = json.load(open(PATH, encoding="utf-8"))
except Exception:
    state = {"days": {}}
state.setdefault("days", {})
# 同一天重跑只換當天那筆，其他日期（歷史）一律保留
state["days"][TODAY] = {"fetched_at": NOW.isoformat(timespec="seconds"), "ig": igr, "threads": thr}
state["token_check"] = {"checked_at": NOW.isoformat(timespec="seconds"), "ig": igt, "threads": tht}
os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
json.dump(state, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"[{TODAY}] IG 帳號層:", igr.get("account"), "追蹤:", igr.get("follower_count"), "貼文數:", len(igr.get("posts", [])))
print(f"[{TODAY}] Threads 追蹤:", thr.get("followers_count"), "貼文數:", len(thr.get("posts", [])))
bad = False
for name, t in (("IG", igt), ("Threads", tht)):
    if t["status"] == "valid":
        print(f"權杖 {name}: 有效")
    else:
        bad = True
        print(f"::error::{name} 權杖{'失效' if t['status']=='invalid' else '未設定'}：{t.get('code')} {t.get('message','')}，請重新產生權杖並更新 Secrets")
try:
    catalog()
except Exception as e:
    print('::warning::貼文目錄失敗', mask(type(e).__name__))
sys.exit(1 if bad else 0)
