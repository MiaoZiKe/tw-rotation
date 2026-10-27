"""貼文格式統計：讀 state/posts_catalog.json（social-snaps 分支），分類並輸出 markdown 表。
用法：python3 scripts/social_style_stats.py catalog.json > out.md
每類：篇數、觀看中位數／平均、按讚率、回覆率、分享／轉發；樣本 < 5 標「樣本不足，不下結論」。"""
import json, re, sys, statistics as st, datetime, collections

TZ = datetime.timezone(datetime.timedelta(hours=8))
cat = json.load(open(sys.argv[1], encoding="utf-8"))["posts"].values()
EMO = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
URL = re.compile(r"https?://")


def feat(p):
    t = p["text"] or ""
    m = p["metrics"] or {}
    d = datetime.datetime.fromisoformat(p["time"].replace("Z", "+00:00")).astimezone(TZ) if p.get("time") else None
    mt = (p.get("media_type") or "").upper()
    if p["platform"] == "ig" and p.get("product_type") in ("REELS",):
        form = "影片/Reels"
    else:
        form = {"TEXT_POST": "純文字", "IMAGE": "單圖", "CAROUSEL_ALBUM": "輪播", "VIDEO": "影片/Reels", "REELS": "影片/Reels"}.get(mt, mt or "未知")
    if re.search(r"(盤前|盤中|盤後)3分鐘|盤後融資融券", t):
        tpl = "自動模板(盤前/中/後)"
    elif re.search(r"薪資|月薪|年薪|薪水", t):
        tpl = "破圈題材(薪資類)"
    elif re.search(r"是什麼|怎麼看|為什麼|懂|教學|入門|一次搞懂|name=", t):
        tpl = "知識教學"
    else:
        tpl = "其他"
    n = len(t)
    wc = "<=100" if n <= 100 else "101-200" if n <= 200 else "201-350" if n <= 350 else ">350"
    first = t.strip().split("\n")[0] if t.strip() else ""
    if re.search(r"[?？]", first):
        op = "問句開頭"
    elif re.match(r"\W*\d", first) or re.search(r"\d", first[:8]):
        op = "數字開頭"
    elif len(first) <= 14:
        op = "短標題開頭"
    else:
        op = "結論先行/長句"
    v = m.get("views") or 0
    return dict(p=p, form=form, tpl=tpl, wc=wc, bullet="有・條列" if "・" in t else "無條列",
                emoji="有emoji" if EMO.search(t) else "無emoji", op=op,
                url="有網址" if URL.search(t) else "無網址",
                hour=("%02d時" % d.hour) if d else "?", wd=("週" + "一二三四五六日"[d.weekday()]) if d else "?",
                views=v, likes=m.get("likes") or 0, rep=m.get("replies", m.get("comments")) or 0,
                sh=(m.get("reposts") or 0) + (m.get("quotes") or 0) + (m.get("shares") or 0))


def table(rows, key, title):
    g = collections.defaultdict(list)
    for r in rows:
        g[r[key]].append(r)
    out = ["### " + title, "", "| 類別 | 篇數 | 觀看中位數 | 觀看平均 | 按讚率 | 回覆率 | 分享/轉發率 | 備註 |", "|---|---|---|---|---|---|---|---|"]
    for k, L in sorted(g.items(), key=lambda kv: -st.median([x["views"] for x in kv[1]])):
        vs = [x["views"] for x in L]; V = sum(vs) or 1
        note = "樣本不足，不下結論" if len(L) < 5 else ""
        out.append("| %s | %d | %.0f | %.0f | %.2f%% | %.2f%% | %.2f%% | %s |" % (
            k, len(L), st.median(vs), st.mean(vs), 100 * sum(x["likes"] for x in L) / V,
            100 * sum(x["rep"] for x in L) / V, 100 * sum(x["sh"] for x in L) / V, note))
    return "\n".join(out) + "\n"


R = [feat(p) for p in cat]
for plat, name in (("threads", "Threads"), ("ig", "Instagram")):
    rows = [r for r in R if r["p"]["platform"] == plat]
    print("## %s（共 %d 篇）\n" % (name, len(rows)))
    if not rows:
        continue
    for k, t in (("form", "形式"), ("tpl", "版型"), ("wc", "字數區間"), ("bullet", "條列「・」"), ("emoji", "emoji"),
                 ("op", "開頭句型"), ("url", "網址"), ("hour", "發文時段"), ("wd", "星期")):
        print(table(rows, k, t))
    print("### 觀看前三名實際貼文\n")
    for r in sorted(rows, key=lambda x: -x["views"])[:3]:
        print("- 觀看 %d／讚 %d／回覆 %d｜%s｜%s\n  > %s" % (r["views"], r["likes"], r["rep"], r["form"], r["p"]["permalink"],
              (r["p"]["text"] or "").replace("\n", " ")[:80]))
    print()
