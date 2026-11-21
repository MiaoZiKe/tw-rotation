"""IG 權杖唯讀探測（2026-11-17）：各頻道權杖是 Instagram 登入版（IGAA）還是 Facebook 登入版（EAA），
以及有沒有 messages／comments 權限。只做 GET；不送私訊、不回覆留言、不印權杖與使用者名稱以外的個資。
輸出：權杖前綴類型、各呼叫成功／失敗與 Meta 錯誤碼。"""
import json, os, re, urllib.request, urllib.parse, urllib.error

CH = {"主帳號①": "", "談晴說礙④": "HEALING_", "科技②": "TECH_", "科技②(TC)": "TC_", "CaffAIne③": "CAFFAINE_"}
IGH, FBH = "https://graph.instagram.com/v24.0", "https://graph.facebook.com/v24.0"


def tok(prefix):
    return (os.environ.get(prefix + "IG_ACCESS_TOKEN_AUTO") or os.environ.get(prefix + "IG_ACCESS_TOKEN") or "").strip()


def get(url, token, **p):
    p["access_token"] = token
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": {"message": "非 JSON"}}
    except Exception as e:
        return 0, {"error": {"message": type(e).__name__}}


def rep(label, st, b, token):
    if st == 200:
        print(f"  [成功] {label}")
        return True
    e = (b or {}).get("error", {})
    msg = re.sub(r"access_token=[^&\s]+", "***", str(e.get("message")))[:220].replace(token, "***")
    print(f"  [失敗 HTTP {st}] {label}：code={e.get('code')} sub={e.get('error_subcode')} {msg}")
    return False


for name, pre in CH.items():
    t = tok(pre)
    print(f"== {name}（{pre or '無前綴'}IG_ACCESS_TOKEN）==")
    if not t:
        print("  未設定，略過")
        continue
    kind = "IGAA（Instagram 登入）" if t.startswith("IG") else "EAA（Facebook 登入）" if t.startswith("EAA") else "其他前綴"
    print("  權杖類型：", kind, "| 長度", len(t))
    host = FBH if t.startswith("EAA") else IGH
    if t.startswith("EAA"):
        st, b = get(FBH + "/me/permissions", t)
        if rep("me/permissions", st, b, t) and b.get("data") is not None:
            print("  已授權：", sorted(x["permission"] for x in b["data"] if x.get("status") == "granted"))
        st, b = get(FBH + "/me/accounts", t, fields="id,name,instagram_business_account")
        if rep("me/accounts（連結粉絲專頁）", st, b, t):
            print("  粉絲專頁數：", len(b.get("data", [])))
        continue
    st, b = get(IGH + "/me", t, fields="user_id,username,account_type")
    if not rep("me（instagram_business_basic）", st, b, t):
        continue
    print("  帳號：", b.get("username"), b.get("account_type"))
    st, b = get(IGH + "/me/permissions", t)
    rep("me/permissions（IG 登入版多半不支援）", st, b, t)
    st, b = get(IGH + "/me/media", t, fields="id,timestamp,comments_count", limit=1)
    if rep("me/media（取最新一則）", st, b, t) and b.get("data"):
        mid = b["data"][0]["id"]
        cc = b["data"][0].get("comments_count") or 0
        print("  最新貼文留言數：", cc)
        st, b = get(f"{IGH}/{mid}/comments", t, fields="id,timestamp", limit=1)
        if rep("讀留言 /{media}/comments（instagram_business_manage_comments）", st, b, t):
            got = len(b.get("data") or [])
            if cc > 0 and got == 0:
                # 2026-11-20：①留言數 2 但讀回 0 則，舊版只看狀態碼誤報成功。
                # 常見原因：Meta App 在開發模式／只有 Standard Access，只回傳 App 角色（測試者）的留言。
                print(f"  [讀不到] 貼文有 {cc} 則留言，API 回 0 則（HTTP 200 空資料）："
                      "多半是 App 在開發模式或缺 Advanced Access，一般讀者的留言被隱藏")
                print(f"::warning::{name}：留言數 {cc} 但讀回 0 則，留言私訊實際收不到讀者留言")
            else:
                print(f"  讀回留言 {got} 則（只取 1 則樣本）")
    st, b = get(IGH + "/me/conversations", t, platform="instagram", limit=1)
    rep("讀私訊對話 /me/conversations（instagram_business_manage_messages）", st, b, t)
