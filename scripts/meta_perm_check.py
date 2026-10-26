"""Meta 權限檢查（只讀、不印權杖）。只輸出權限名稱與呼叫成功／失敗與錯誤訊息。"""
import json, os, re, urllib.request, urllib.parse, urllib.error, datetime

TOK = {k: os.environ.get(k, "") for k in ("IG_ACCESS_TOKEN", "THREADS_ACCESS_TOKEN")}
IDS = {k: os.environ.get(k, "") for k in ("IG_USER_ID", "THREADS_USER_ID")}


def mask(s):
    s = str(s)
    for v in list(TOK.values()) + list(IDS.values()):
        if v:
            s = s.replace(v, "***")
    return re.sub(r"(access_token=)[^&\s\"']+", r"\1***", s)[:600]


def get(url, **params):
    full = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": {"message": "非 JSON 回應"}}
    except Exception as e:
        return 0, {"error": {"message": type(e).__name__}}


def show(label, st, body):
    if st == 200:
        print(f"[成功] {label}")
        return True
    err = body.get("error", {}) if isinstance(body, dict) else {}
    print(f"[失敗 HTTP {st}] {label}：code={err.get('code')} subcode={err.get('error_subcode')} 訊息={mask(err.get('message'))}")
    return False


def day(n):
    return int((datetime.datetime.utcnow() - datetime.timedelta(days=n)).timestamp())


print("== 設定檢查（只看有沒有，不印值）==")
for k, v in {**TOK, **IDS}.items():
    print(f"{k}: {'已設定' if v else '未設定'}")

print("\n== IG（Instagram Login，graph.instagram.com）==")
t, uid = TOK["IG_ACCESS_TOKEN"], IDS["IG_USER_ID"]
if t:
    st, b = get("https://graph.instagram.com/v24.0/me", fields="user_id,username,account_type", access_token=t)
    if show("me（基本資料 instagram_business_basic）", st, b):
        print("  帳號類型:", b.get("account_type"), "| 帳號:", b.get("username"))
    st, b = get("https://graph.instagram.com/v24.0/me/permissions", access_token=t)
    if show("me/permissions", st, b):
        for p in b.get("data", []):
            print(f"  權限 {p.get('permission')}: {p.get('status')}")
    st, b = get("https://graph.instagram.com/v24.0/%s/insights" % (uid or "me"),
                metric="reach,views", period="day", metric_type="total_value", since=day(3), until=day(0), access_token=t)
    show("IG insights reach,views（帳號層級 total_value）", st, b)
    if st == 200:
        for m in b.get("data", []):
            print("  ", m.get("name"), "total:", m.get("total_value", {}).get("value"))
    st, b = get("https://graph.instagram.com/v24.0/%s/insights" % (uid or "me"),
                metric="follower_count", period="day", since=day(3), until=day(0), access_token=t)
    show("IG insights follower_count（day）", st, b)
    st, b = get("https://graph.instagram.com/v24.0/%s/media" % (uid or "me"), fields="id", limit=1, access_token=t)
    if show("IG 媒體清單（取一則）", st, b) and b.get("data"):
        mid = b["data"][0]["id"]
        st, b = get("https://graph.instagram.com/v24.0/%s/insights" % mid, metric="views,reach", access_token=t)
        show("IG 單則貼文 insights views,reach", st, b)
    st, b = get("https://graph.facebook.com/debug_token", input_token=t, access_token=t)
    show("debug_token（無 app token，預期可能失敗）", st, b)
    if st == 200:
        d = b.get("data", {})
        print("  scopes:", d.get("scopes"), "| 到期 expires_at:", d.get("expires_at"), "| data_access_expires_at:", d.get("data_access_expires_at"))
else:
    print("無 IG 權杖，略過")

print("\n== Threads（graph.threads.net）==")
t, uid = TOK["THREADS_ACCESS_TOKEN"], IDS["THREADS_USER_ID"]
if t:
    st, b = get("https://graph.threads.net/v1.0/me", fields="id,username", access_token=t)
    show("me（threads_basic）", st, b)
    st, b = get("https://graph.threads.net/v1.0/me/threads", fields="id", limit=1, access_token=t)
    show("me/threads 貼文清單（threads_basic）", st, b)
    first = (b.get("data") or [{}])[0].get("id") if st == 200 else None
    st, b = get("https://graph.threads.net/v1.0/me/threads_insights",
                metric="views,followers_count", since=day(3), until=day(0), access_token=t)
    show("Threads threads_insights views,followers_count（threads_manage_insights）", st, b)
    if st == 200:
        for m in b.get("data", []):
            print("  ", m.get("name"), json.dumps(m.get("values") or m.get("total_value"))[:200])
    if first:
        st, b = get("https://graph.threads.net/v1.0/%s/insights" % first, metric="views,likes,replies", access_token=t)
        show("Threads 單則貼文 insights views,likes,replies", st, b)
    st, b = get("https://graph.threads.net/v1.0/debug_token", input_token=t, access_token=t)
    show("debug_token（Threads，預期可能失敗）", st, b)
else:
    print("無 Threads 權杖，略過")
print("\n（權杖到期日：Meta 長效權杖約 60 天；上面 debug_token 失敗時，到期日無法從 API 取得，需看開發者後台或最後一次產生權杖的日期。）")
