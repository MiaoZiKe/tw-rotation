#!/usr/bin/env python3
"""IG 對標帳號採集（Meta 官方「商業帳號探索」business_discovery，只讀、不發文）。

用途：抓台灣財經／科技圖文 IG 帳號最近 25 篇貼文的公開數據，給 @liguligu0818 做對標。

合規說明：
  · 只用 Meta 官方 Instagram Graph API 的 business_discovery 欄位，不做任何網頁爬取。
  · business_discovery 只存在於「Instagram API with Facebook Login」這一套
    （主機 graph.facebook.com、IG 專業帳號要連 FB 粉專、權杖要有 instagram_basic、
    instagram_manage_insights、pages_read_engagement 或 pages_show_list）。
    我們發文用的 Instagram Login 權杖（graph.instagram.com，IGAA 開頭）呼叫不到；
    這支會先用它試一次，把 Meta 回的錯誤原樣記進輸出，當作證據。
  · 金鑰只讀環境變數，不印、不寫進任何檔案；錯誤訊息會先遮掉 access_token。

環境變數：
  IG_BENCH_FB_TOKEN     Facebook 登入的使用者權杖（或粉專權杖）。有它才抓得到。
  IG_BENCH_IG_USER_ID   （可省）我們 IG 專業帳號的 IG User ID；省略時從 /me/accounts 自動找。
  IG_ACCESS_TOKEN       （可省）現有 Instagram Login 權杖，只拿來做「這條路走不走得通」的探測。
  OUT_DIR               輸出資料夾，預設 research/ig_bench
"""
import json
import os
import re
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

VER = "v24.0"
TPE = timezone(timedelta(hours=8))
N_MEDIA = 25

# 名單：label＝中文名；handles＝候選帳號（依序試，第一個找得到的就用）；conf＝帳號名查證信心
# 查證方式：2026-11-09 WebSearch（限 instagram.com）＋媒體報導，見 research 檔的 accounts[].note
ACCOUNTS = [
    {"label": "30節約男子", "handles": ["30savingman", "save30man", "30_saving_man", "thirty.saving.man"], "conf": "低",
     "note": "媒體確認有此 IG（2023-12 逾 14 萬追蹤），但 WebSearch 撈不到帳號名，這裡是候選，跑完看哪個命中"},
    {"label": "好好理財 Marra", "handles": ["goodgood.tw"], "conf": "高", "note": "vocus 個人頁列 @goodgood.tw"},
    {"label": "財經M平方", "handles": ["macromicro.me"], "conf": "高", "note": "instagram.com 頁面標題「MacroMicro 財經M平方」"},
    {"label": "Mr.Market 市場先生", "handles": ["mrmarketjam"], "conf": "中", "note": "頁面標題「Mr.Market 市場先生」、簡介導向部落格"},
    {"label": "懶人經濟學", "handles": ["earning.tw"], "conf": "高", "note": "頁面標題「懶人經濟學｜虛擬貨幣 X 財經新聞」，官網 earning.tw"},
    {"label": "股癌", "handles": ["gooaye", "mengkung_h"], "conf": "中",
     "note": "節目官方 IG 未查到；@mengkung_h 是主持人謝孟恭個人帳號（約 20 萬追蹤）"},
    {"label": "財報狗", "handles": ["statementdog"], "conf": "高", "note": "頁面標題「財報狗 (@statementdog)」"},
    {"label": "鉅亨", "handles": ["anue.tw"], "conf": "高", "note": "頁面標題「anue鉅亨網財經新聞」"},
    {"label": "經濟日報", "handles": ["edn0420"], "conf": "中", "note": "頁面標題「經濟日報 (@edn0420)」，未見官網互連"},
    {"label": "數位時代", "handles": ["bnext_official"], "conf": "高", "note": "頁面標題「數位時代 (@bnext_official)」"},
    {"label": "股市爆料同學會", "handles": ["stock_chat_cmoney"], "conf": "高", "note": "頁面標題「股市爆料同學會」"},
    {"label": "小資YP", "handles": ["ypfinancialnote"], "conf": "中", "note": "頁面標題「小資YP投資理財筆記」，追蹤數偏小（約 1.4 千）"},
    # 自己補的台灣財經圖文帳號（WebSearch 結果中追蹤數 8～12 萬、同為圖文輪播型）
    {"label": "下班經濟學", "handles": ["worked_money"], "conf": "高", "note": "補充：約 11 萬追蹤、1 千多篇"},
    {"label": "理財館長", "handles": ["muscle__money"], "conf": "高", "note": "補充：指數化投資，約 9 萬追蹤"},
    {"label": "理享人生", "handles": ["lixianglife"], "conf": "高", "note": "補充：信用卡／投資，約 12 萬追蹤"},
    {"label": "純純存股", "handles": ["chunchunloveyou"], "conf": "高", "note": "補充：存股，約 11 萬追蹤"},
    {"label": "理財小時候", "handles": ["moneywings_org"], "conf": "高", "note": "補充：理財通識，約 8 萬追蹤"},
]
SELF = {"label": "我們（對照組）", "handles": ["liguligu0818"], "conf": "高", "note": "自己的帳號"}

MEDIA_FIELDS = "caption,like_count,comments_count,timestamp,media_type,media_product_type,permalink"
BD_FIELDS = "username,name,followers_count,media_count,media.limit(%d){%s}" % (N_MEDIA, MEDIA_FIELDS)


def scrub(s):
    return re.sub(r"access_token=[^&\s\"']+", "access_token=***", str(s))


def get(url, **params):
    q = urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url + "?" + q, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = {"error": {"message": "HTTP %s" % e.code}}
            # 額度或暫時性錯誤才重試
            code = (body.get("error") or {}).get("code")
            if code in (1, 2, 4, 17, 32, 613) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            return e.code, body
        except Exception as e:  # 網路錯誤
            if attempt < 2:
                time.sleep(3)
                continue
            return 0, {"error": {"message": scrub(e)}}
    return 0, {"error": {"message": "重試用完"}}


def err_of(body):
    e = (body or {}).get("error") or {}
    return {"code": e.get("code"), "subcode": e.get("error_subcode"), "type": e.get("type"),
            "message": scrub(e.get("message", ""))[:300]}


def probe_ig_login(token):
    """用 Instagram Login 權杖試 business_discovery，留下 Meta 的回覆當證據。"""
    if not token:
        return {"tried": False, "reason": "沒有 IG_ACCESS_TOKEN"}
    base = "https://graph.instagram.com/" + VER
    s, b = get(base + "/me", fields="user_id,username", access_token=token)
    me = b if s == 200 else {}
    s2, b2 = get(base + "/me", fields="business_discovery.username(statementdog){followers_count}", access_token=token)
    return {"tried": True, "host": "graph.instagram.com", "me_ok": s == 200, "me_username": me.get("username"),
            "business_discovery_status": s2, "ok": s2 == 200 and "business_discovery" in b2,
            "error": None if s2 == 200 else err_of(b2)}


def find_ig_user_id(base, token):
    s, b = get(base + "/me/accounts", fields="name,instagram_business_account{id,username}", limit=50, access_token=token)
    if s != 200:
        return None, err_of(b)
    for p in b.get("data", []):
        iba = p.get("instagram_business_account")
        if iba and iba.get("id"):
            return iba["id"], {"page": p.get("name"), "ig_username": iba.get("username")}
    # 粉專權杖：本身就是 /me
    s, b = get(base + "/me", fields="instagram_business_account{id,username}", access_token=token)
    if s == 200 and (b.get("instagram_business_account") or {}).get("id"):
        return b["instagram_business_account"]["id"], {"ig_username": b["instagram_business_account"].get("username")}
    return None, {"message": "權杖底下找不到連了 IG 專業帳號的粉專"}


def discover(base, ig_id, token, acc):
    tried = []
    for h in acc["handles"]:
        s, b = get(base + "/" + ig_id, fields="business_discovery.username(%s){%s}" % (h, BD_FIELDS), access_token=token)
        if s == 200 and b.get("business_discovery"):
            bd = b["business_discovery"]
            media = (bd.get("media") or {}).get("data", [])
            return {"label": acc["label"], "username": bd.get("username") or h, "name": bd.get("name"),
                    "conf": acc["conf"], "note": acc["note"], "tried": tried + [h], "ok": True,
                    "followers": bd.get("followers_count"), "media_count": bd.get("media_count"),
                    "media": [{k: m.get(k) for k in ("timestamp", "media_type", "media_product_type", "like_count",
                                                     "comments_count", "permalink", "caption")} for m in media]}
        tried.append(h)
        last = err_of(b)
        time.sleep(1)
    return {"label": acc["label"], "conf": acc["conf"], "note": acc["note"], "tried": tried, "ok": False, "error": last}


HASH = re.compile(r"#[^\s#]+")


def fmt_of(m):
    if m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO":
        return "Reels／影片"
    if m.get("media_type") == "CAROUSEL_ALBUM":
        return "輪播"
    return "單圖"


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 4) if xs else None


def account_stats(a):
    ms = a.get("media") or []
    f = a.get("followers") or 0
    if not ms:
        return {}
    ts = sorted(datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(TPE) for m in ms if m.get("timestamp"))
    span_days = max((ts[-1] - ts[0]).total_seconds() / 86400, 1) if len(ts) > 1 else None
    per_week = round((len(ts) - 1) / span_days * 7, 2) if span_days else None
    hours = Counter(t.hour for t in ts)
    wd = Counter("一二三四五六日"[t.weekday()] for t in ts)
    fmts = Counter(fmt_of(m) for m in ms)
    caps = [m.get("caption") or "" for m in ms]
    clen = [len(c) for c in caps]
    tags = [len(HASH.findall(c)) for c in caps]
    eng = []
    for m in ms:
        lk, cm = m.get("like_count"), m.get("comments_count")
        if lk is None and cm is None:
            eng.append(None)
            continue
        eng.append(((lk or 0) + (cm or 0)) / f if f else None)
    by_fmt = {}
    for k in fmts:
        v = [e for e, m in zip(eng, ms) if fmt_of(m) == k and e is not None]
        by_fmt[k] = med(v)
    hidden_likes = sum(1 for m in ms if m.get("like_count") is None)
    return {
        "n": len(ms), "posts_per_week": per_week,
        "first": ts[0].strftime("%Y-%m-%d") if ts else None, "last": ts[-1].strftime("%Y-%m-%d") if ts else None,
        "hours_tpe": dict(sorted(hours.items())), "top_hours": [h for h, _ in hours.most_common(3)],
        "weekday": dict(wd),
        "format_share": {k: round(v / len(ms), 3) for k, v in fmts.items()},
        "caption_len_median": med(clen), "hashtag_median": med(tags), "hashtag_mean": round(sum(tags) / len(tags), 2),
        "er_median": med(eng), "er_mean": round(st.mean([e for e in eng if e is not None]), 5) if any(e is not None for e in eng) else None,
        "er_median_by_format": by_fmt, "likes_hidden_posts": hidden_likes,
        "likes_median": med([m.get("like_count") for m in ms]), "comments_median": med([m.get("comments_count") for m in ms]),
    }


def cross_stats(rows):
    ok = [r for r in rows if r.get("ok") and r.get("stats") and not r.get("self")]
    if not ok:
        return {}
    allh = Counter()
    rel = {}  # 每篇互動 / 該帳號中位數，看「格式」「字數」「hashtag」對互動的相對影響（消掉帳號大小）
    for r in ok:
        f = r.get("followers") or 0
        base = r["stats"].get("er_median")
        for m in r["media"]:
            t = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(TPE)
            allh[t.hour] += 1
            if not f or not base or m.get("like_count") is None:
                continue
            e = ((m.get("like_count") or 0) + (m.get("comments_count") or 0)) / f / base
            cap = m.get("caption") or ""
            n = len(cap)
            lb = "<150字" if n < 150 else ("150-500字" if n < 500 else ">=500字")
            hb = "0個" if not HASH.findall(cap) else ("1-5個" if len(HASH.findall(cap)) <= 5 else ">5個")
            for key in ("格式:" + fmt_of(m), "字數:" + lb, "hashtag:" + hb, "時段:%02d時" % t.hour):
                rel.setdefault(key, []).append(e)
    lift = {k: {"n": len(v), "相對互動中位數": round(st.median(v), 2)} for k, v in sorted(rel.items()) if len(v) >= 5}
    S = lambda k: med([r["stats"].get(k) for r in ok])
    fmt_avg = {}
    for r in ok:
        for k, v in r["stats"]["format_share"].items():
            fmt_avg.setdefault(k, []).append(v)
    return {
        "accounts_ok": len(ok),
        "posts_per_week_median": S("posts_per_week"),
        "caption_len_median": S("caption_len_median"),
        "hashtag_median": S("hashtag_median"),
        "er_median_of_accounts": S("er_median"),
        "format_share_mean": {k: round(sum(v) / len(ok), 3) for k, v in fmt_avg.items()},
        "top_hours_tpe": [h for h, _ in allh.most_common(5)],
        "lift": lift,
        "rank_by_er": [(r["label"], r["username"], r["stats"].get("er_median"), r.get("followers")) for r in
                       sorted(ok, key=lambda r: -(r["stats"].get("er_median") or 0))],
    }


def pct(x):
    return "—" if x is None else "%.2f%%" % (x * 100)


def summary_md(out):
    L = ["# IG 對標採集摘要 %s" % out["date"], ""]
    if not out.get("ok"):
        L += ["**沒有抓到資料**：%s" % out.get("reason", ""), "", "Instagram Login 權杖探測：```%s```" %
              json.dumps(out.get("probe_ig_login"), ensure_ascii=False)]
        return "\n".join(L)
    L += ["| 帳號 | 追蹤 | 週發文 | 輪播 | Reels | 字數中位 | hashtag中位 | 互動率中位 | 常發時段(台北) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in out["accounts"]:
        if not r.get("ok"):
            L.append("| %s | ⚠️ 找不到（試過 %s） | | | | | | | |" % (r["label"], "、".join(r["tried"])))
            continue
        s = r["stats"]
        fs = s.get("format_share", {})
        L.append("| %s @%s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["label"], r["username"], r.get("followers"), s.get("posts_per_week"), pct(fs.get("輪播", 0)),
            pct(fs.get("Reels／影片", 0)), s.get("caption_len_median"), s.get("hashtag_median"), pct(s.get("er_median")),
            "、".join("%d時" % h for h in s.get("top_hours", []))))
    c = out.get("cross") or {}
    L += ["", "## 跨帳號共通點", "",
          "- 成功帳號數：%s" % c.get("accounts_ok"),
          "- 週發文中位數：%s" % c.get("posts_per_week_median"),
          "- 文案字數中位數：%s；hashtag 中位數：%s" % (c.get("caption_len_median"), c.get("hashtag_median")),
          "- 互動率（讚＋留言／追蹤）各帳號中位數的中位數：%s" % pct(c.get("er_median_of_accounts")),
          "- 平均格式比例：%s" % json.dumps(c.get("format_share_mean"), ensure_ascii=False),
          "- 最常發文時段（台北）：%s" % "、".join("%d時" % h for h in c.get("top_hours_tpe", [])),
          "", "相對互動（1.0＝該帳號自己的中位數；>1 代表這類貼文比自己平常好）：", ""]
    for k, v in (c.get("lift") or {}).items():
        if not k.startswith("時段:"):
            L.append("- %s：%s（%d 篇）" % (k, v["相對互動中位數"], v["n"]))
    return "\n".join(L)


def main():
    out_dir = os.environ.get("OUT_DIR", "research/ig_bench")
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.now(TPE)
    out = {"date": now.strftime("%Y-%m-%d"), "generated_tpe": now.strftime("%Y-%m-%d %H:%M"),
           "api": "Instagram Graph API business_discovery（官方，只讀）", "n_media_per_account": N_MEDIA}
    out["probe_ig_login"] = probe_ig_login(os.environ.get("IG_ACCESS_TOKEN", "").strip())
    tok = os.environ.get("IG_BENCH_FB_TOKEN", "").strip()
    code = 0
    if not tok:
        out.update(ok=False, reason="沒有 IG_BENCH_FB_TOKEN（Facebook 登入權杖）。business_discovery 只開放給 Facebook Login 那一套，Instagram Login 權杖探測結果見 probe_ig_login")
        code = 2
    else:
        base = "https://graph.facebook.com/" + VER
        ig_id = os.environ.get("IG_BENCH_IG_USER_ID", "").strip()
        info = {"from_env": bool(ig_id)}
        if not ig_id:
            ig_id, info = find_ig_user_id(base, tok)
        out["self_lookup"] = info
        if not ig_id:
            out.update(ok=False, reason="找不到我們的 IG User ID：%s" % json.dumps(info, ensure_ascii=False))
            code = 3
        else:
            rows = []
            for acc in ACCOUNTS + [SELF]:
                r = discover(base, ig_id, tok, acc)
                if acc is SELF:
                    r["self"] = True
                if r.get("ok"):
                    r["stats"] = account_stats(r)
                rows.append(r)
                print(("✅ " if r.get("ok") else "⚠️ ") + acc["label"] + (" @" + r["username"] if r.get("ok") else " " + json.dumps(r.get("error"), ensure_ascii=False)), flush=True)
            out["accounts"] = rows
            out["cross"] = cross_stats(rows)
            out["ok"] = any(r.get("ok") for r in rows)
            if not out["ok"]:
                code = 4
    path = os.path.join(out_dir, out["date"] + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    md = summary_md(out)
    with open(os.path.join(out_dir, out["date"] + ".md"), "w", encoding="utf-8") as fh:
        fh.write(md + "\n")
    print(md)
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as fh:
            fh.write(md + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
