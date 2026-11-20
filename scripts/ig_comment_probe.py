"""①哩股哩股 IG 讀留言診斷（2026-11-20，唯讀）。
起因：ligu_comments 讀到 comments_count=2 但 /{media}/comments 回 0 則；連帳號自己（也是 Instagram 測試人員）的留言都讀不到，
所以不像單純「開發模式只回測試人員留言」。這支換多種讀法比較，只印數量、狀態碼、錯誤碼，不印留言內容、使用者名稱、權杖。"""
import json, os, re, urllib.request, urllib.parse, urllib.error

T = (os.environ.get("IG_ACCESS_TOKEN_AUTO") or os.environ.get("IG_ACCESS_TOKEN") or "").strip()


def get(url, **p):
    p["access_token"] = T
    try:
        with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(p), timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": {"message": type(e).__name__}}


def err(b):
    e = (b or {}).get("error") or {}
    return f"code={e.get('code')} sub={e.get('error_subcode')} {re.sub(r'access_token=[^&\\s]+', '***', str(e.get('message')))[:160]}"


def show(label, st, b, key="data"):
    if st != 200:
        print(f"  [{st}] {label}：{err(b)}")
        return
    if key == "data":
        d = b.get("data") or []
        print(f"  [200] {label}：{len(d)} 則；欄位={sorted({k for x in d for k in x})}；有 paging={bool(b.get('paging'))}")
    else:
        v = b.get(key)
        n = len((v or {}).get("data") or []) if isinstance(v, dict) else v
        print(f"  [200] {label}：{key}={n if not isinstance(n, int) else n}")


# 2026-11-20 補：EAA（Facebook 登入）權杖的頻道②③④也看一次，只比對 comments_count 與讀回則數
FB = "https://graph.facebook.com/v24.0"
for pre in ("TECH_", "CAFFAINE_", "HEALING_"):
    tk = (os.environ.get(pre + "IG_ACCESS_TOKEN_AUTO") or os.environ.get(pre + "IG_ACCESS_TOKEN") or "").strip()
    uid = (os.environ.get(pre + "IG_USER_ID") or "").strip()
    if tk and not uid:
        try:  # 跟發文／留言程式同一套找法（粉絲專頁 → 多路徑探查）
            import sys; sys.path.insert(0, os.path.dirname(__file__))
            import healing_post as HP
            pages = HP.fb_pages(tk, with_token=True)
            uid, _ = HP.pick_ig(pages, HP.channel_account(pre))
            if not uid:
                ids, _ = HP.ig_choices(HP.fb_ig_candidates(tk), HP.channel_account(pre))
                uid = ids[0] if ids else ""
        except Exception as e:
            print(f"  找 IG 編號失敗：{type(e).__name__}")
    print(f"\n#### {pre}（{'EAA' if tk.startswith('EAA') else tk[:4]}，找到 IG 編號={bool(uid)}）")
    if not (tk and uid):
        print("  缺權杖或 IG 編號，略過"); continue
    T, keep = tk, T
    st, b = get(f"{FB}/{uid}/media", fields="id,timestamp,comments_count", limit=5)
    if st != 200:
        print(f"  讀貼文 [{st}] {err(b)}"); T = keep; continue
    for m in b.get("data") or []:
        if not m.get("comments_count"):
            continue
        st, c = get(f"{FB}/{m['id']}/comments", fields="id,timestamp", limit=50)
        n = len(c.get("data") or []) if st == 200 else f"[{st}] {err(c)}"
        print(f"  貼文 …{m['id'][-4:]} {m.get('timestamp','')[:10]} comments_count={m['comments_count']} 讀回={n}")
    T = keep
print()
if not T:
    print("沒有 IG_ACCESS_TOKEN"); raise SystemExit(0)
print("權杖類型：", "IGAA" if T.startswith("IG") else T[:3], "長度", len(T))
for base in ("https://graph.instagram.com/v24.0", "https://graph.instagram.com/v21.0", "https://graph.instagram.com"):
    st, b = get(base + "/me", fields="id,user_id,username,account_type")
    print(f"[{base}] /me → {st}；id 與 user_id 相同={b.get('id') == b.get('user_id')}；帳號類型={b.get('account_type')}" if st == 200 else f"[{base}] /me → {st} {err(b)}")
IGH = "https://graph.instagram.com/v24.0"
st, me = get(IGH + "/me", fields="id,user_id")
ME_IDS = {me.get("id"), me.get("user_id")} - {None}
st, b = get(IGH + "/me/media", fields="id,timestamp,comments_count,media_product_type,media_type,is_comment_enabled", limit=3)
if st != 200:
    print("讀貼文失敗", err(b)); raise SystemExit(0)
for m in b.get("data") or []:
    mid = m["id"]
    print(f"\n== 貼文 …{mid[-4:]} {m.get('timestamp')} 類型={m.get('media_product_type')}/{m.get('media_type')} comments_count={m.get('comments_count')} is_comment_enabled={m.get('is_comment_enabled')}")
    for base in ("https://graph.instagram.com/v24.0", "https://graph.instagram.com/v21.0", "https://graph.instagram.com"):
        st, c = get(f"{base}/{mid}/comments")
        show(f"{base.split('.com')[1] or '(無版本)'} /comments 不帶 fields", st, c)
    st, c = get(f"{IGH}/{mid}/comments", fields="id,timestamp,text,username,from,like_count,hidden,parent_id", limit=50)
    show("v24 /comments 全欄位", st, c)
    st, c = get(f"{IGH}/{mid}", fields="comments_count,comments{id,timestamp}")
    show("v24 欄位展開 comments{}", st, c, key="comments")
    st, c = get(f"{IGH}/{mid}", fields="owner,username")
    print(f"  貼文 owner 與 /me 相同：{(c.get('owner') or {}).get('id') in ME_IDS}" if st == 200 else f"  讀 owner 失敗：{err(c)}")
    st, c = get(f"https://graph.facebook.com/v24.0/{mid}/comments")
    show("graph.facebook.com /comments（IGAA 預期失敗）", st, c)
