"""臨時探測：找全市場擔保維持率、追繳／處分戶數與金額的合法端點（只印 log，不寫檔）。"""
import json, os, re, requests

UA = {"User-Agent": "Mozilla/5.0 tw-rotation-probe"}
KW = ["維持率", "追繳", "處分", "信用交易", "融資", "融券", "授信", "儀表板", "違約", "Margin", "margin", "MI_MARGN"]


def get(url, **kw):
    try:
        r = requests.get(url, headers=UA, timeout=40, **kw)
        print(f"\n=== GET {url} -> {r.status_code} {r.headers.get('content-type')} len={len(r.content)}")
        return r
    except Exception as e:
        print(f"\n=== GET {url} -> ERR {e}")
        return None


def swagger(url):
    r = get(url)
    if not r or r.status_code != 200:
        return
    try:
        sw = r.json()
    except Exception:
        print(r.text[:500]); return
    paths = sw.get("paths", {})
    print("總端點數", len(paths))
    for p, ops in paths.items():
        txt = json.dumps(ops, ensure_ascii=False)
        summ = " | ".join(o.get("summary", "") for o in ops.values() if isinstance(o, dict))
        if any(k in txt or k in p for k in KW):
            print("  ★", p, "::", summ)


swagger("https://openapi.twse.com.tw/v1/swagger.json")
swagger("https://www.tpex.org.tw/openapi/swagger.json")

# data.gov.tw 搜尋
for q in ["擔保維持率", "追繳", "信用交易", "融資融券", "臺股儀表板"]:
    for u in [f"https://data.gov.tw/api/v2/rest/dataset?q={q}",
              f"https://data.gov.tw/api/front/dataset/list?q={q}"]:
        r = get(u)
        if r is not None:
            print(r.text[:1500])

# FinMind 資料集清單中跟維持率有關的
tok = os.environ.get("FINMIND_TOKEN", "")
for ds in ["TaiwanTotalExchangeMarginMaintenance", "TaiwanStockTotalMarginPurchaseShortSale"]:
    r = get("https://api.finmindtrade.com/api/v4/data", params={"dataset": ds, "start_date": "2026-10-25"},
            )
    if r is not None:
        print(r.text[:1500])
r = get("https://api.finmindtrade.com/api/v4/datalist", params={"dataset": "TaiwanStockInfo"})
r = get("https://api.finmindtrade.com/api/v4/translation", params={"dataset": "TaiwanTotalExchangeMarginMaintenance"})
if r is not None:
    print(r.text[:800])

# 找儀表板入口網址（只讀首頁與 sitemap 找連結，不打 /rwd/ 資料端點）
for u in ["https://www.twse.com.tw/zh/index.html", "https://www.twse.com.tw/sitemap.xml", "https://www.twse.com.tw/robots.txt",
          "https://www.tpex.org.tw/zh-tw/index.html", "https://www.tpex.org.tw/robots.txt"]:
    r = get(u)
    if r is not None and r.status_code == 200:
        t = r.text
        if u.endswith("robots.txt"):
            print(t[:2000])
        for m in set(re.findall(r'href="([^"]*(?:dashboard|Dashboard|儀表板|credit|margin)[^"]*)"', t)):
            print("  link:", m)
        for m in set(re.findall(r'.{0,120}儀表板.{0,120}', t)):
            print("  ctx:", m)
        for m in set(re.findall(r'<loc>([^<]*(?:dashboard|margin|credit)[^<]*)</loc>', t, re.I)):
            print("  loc:", m)
