"""第二輪：讀 swagger 找關鍵字端點再抓；FinMind 補市場總量（法人、融資、期貨法人）。"""
import json, os, re, urllib.request, datetime
OUT = "raw/official"
UA = {"User-Agent": "Mozilla/5.0 tw-rotation-audit"}
def get(url, out, hdr=None):
    try:
        req = urllib.request.Request(url, headers={**UA, **(hdr or {})})
        with urllib.request.urlopen(req, timeout=90) as r:
            b = r.read(); code = r.status
    except Exception as e:
        b = str(e).encode(); code = getattr(e, "code", -1)
    open(out, "wb").write(b)
    open("raw/status.txt", "a").write(f"{code} {url}\n")
def paths(f):
    try: return list(json.load(open(f)).get("paths", {}).keys())
    except Exception: return []
pl = {}
for src, base, kw in [
    ("twse", "https://openapi.twse.com.tw/v1", r"fund/|MARGN|MI_INDEX|FMTQIK|BFI|T86"),
    ("tpex", "https://www.tpex.org.tw/openapi/v1", r"3insti|margin|index|highlight|daily_close|market_value|summary"),
    ("taifex", "https://openapi.taifex.com.tw/v1", r"Institutional|DailyMarketReportFut|LargeTraders|PutCall"),
]:
    ps = paths(f"{OUT}/{src}_swagger.json"); pl[src] = ps
    for p in ps:
        if re.search(kw, p) and "{" not in p:
            fn = f"{OUT}/{src}_{p.strip('/').replace('/','_')}.json"
            if not os.path.exists(fn) or os.path.getsize(fn) < 50:
                get(base + p, fn)
json.dump(pl, open(f"{OUT}/_swagger_paths.json", "w"), ensure_ascii=False, indent=1)
tok = os.environ.get("FINMIND_TOKEN", "")
start = (datetime.date.today() - datetime.timedelta(days=20)).isoformat()
for ds, extra in [("TaiwanStockTotalInstitutionalInvestors", ""), ("TaiwanStockTotalMarginPurchaseShortSale", ""),
                  ("TaiwanFuturesInstitutionalInvestors", "&data_id=TX"), ("TaiwanStockPrice", "&data_id=2330"),
                  ("TaiwanStockPrice", "&data_id=2317"), ("TaiwanStockPrice", "&data_id=2454"), ("TaiwanStockPrice", "&data_id=3231"), ("TaiwanStockPrice", "&data_id=6669"),
                  ("TaiwanStockInstitutionalInvestorsBuySell", "&data_id=2330"), ("TaiwanStockMarginPurchaseShortSale", "&data_id=2330"),
                  ("TaiwanStockMonthRevenue", "&data_id=2330")]:
    st = start if ds != "TaiwanStockMonthRevenue" else "2026-01-01"
    url = f"https://api.finmindtrade.com/api/v4/data?dataset={ds}{extra}&start_date={st}"
    get(url, f"{OUT}/finmind_{ds}{extra.replace('&data_id=','_')}.json", {"Authorization": f"Bearer {tok}"} if tok else None)
