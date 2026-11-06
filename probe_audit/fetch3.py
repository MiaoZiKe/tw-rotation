"""第三輪（只補查）：當沖 0 是真的還是缺料；TWSE 當沖標的（TWTB4U）、FinMind 當沖 2330/2317；TWSE 盤後統計 MI_INDEX 漲跌家數另找。"""
import json, os, urllib.request
OUT = "raw3"; os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 tw-rotation-audit"}
def get(url, out, hdr=None):
    try:
        req = urllib.request.Request(url, headers={**UA, **(hdr or {})})
        with urllib.request.urlopen(req, timeout=90) as r: b = r.read(); code = r.status
    except Exception as e: b = str(e).encode(); code = getattr(e, "code", -1)
    open(f"{OUT}/{out}", "wb").write(b); open(f"{OUT}/status.txt", "a").write(f"{code} {url}\n")
get("https://openapi.twse.com.tw/v1/exchangeReport/TWTB4U", "twse_TWTB4U.json")
get("https://openapi.twse.com.tw/v1/exchangeReport/TWT93U", "twse_TWT93U.json")
tok = os.environ.get("FINMIND_TOKEN", "")
h = {"Authorization": f"Bearer {tok}"} if tok else None
for c in ("2330", "2317", "2454"):
    get(f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDayTrading&data_id={c}&start_date=2026-10-30", f"finmind_daytrade_{c}.json", h)
get("https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDayTrading&start_date=2026-11-05&end_date=2026-11-05", "finmind_daytrade_all_1105.json", h)
get("https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInstitutionalInvestorsBuySell&data_id=2317&start_date=2026-11-04", "finmind_inst_2317.json", h)
