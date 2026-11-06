import json, os, re, requests
H = {"User-Agent": "Mozilla/5.0 tw-rotation probe"}
k = os.environ.get("FRED_API_KEY", "").strip()
try:
    r = requests.get("https://api.stlouisfed.org/fred/series", params={"series_id": "VIXCLS", "api_key": k, "file_type": "json"}, timeout=30)
    s = (r.json().get("seriess") or [{}])[0]; print("===== FRED VIXCLS info", r.status_code); print(json.dumps({x: s.get(x) for x in ["title", "observation_start", "observation_end", "frequency", "notes"]}, ensure_ascii=False)[:2500])
except Exception as e: print("ERR", e)
for p in ["DailyMarketReportOpt", "Daily_OPT"]:
    try:
        r = requests.get("https://openapi.taifex.com.tw/v1/" + p, headers={**H, "accept": "application/json"}, timeout=60)
        j = r.json(); print("=====", p, r.status_code, len(j)); 
        txo = [x for x in j if "TXO" in json.dumps(x, ensure_ascii=False)]
        print("keys", list(j[0].keys()) if j else None); print("txo rows", len(txo)); print(json.dumps(txo[:3], ensure_ascii=False)[:1500])
    except Exception as e: print("ERR", p, repr(e)[:300])
try:
    r = requests.get("https://data.gov.tw/datasets/export/csv", headers=H, timeout=120)
    t = r.content.decode("utf-8-sig", "replace")
    lines = [ln for ln in t.splitlines() if "期貨交易所" in ln]
    print("===== datagov taifex", len(lines))
    print("vix-like:", [ln[:300] for ln in lines if re.search("波動|VIX|vix|Volatility", ln)])
    print("all titles:", " | ".join(re.split(r'","', ln)[1][:40] for ln in lines if '","' in ln))
    print("anywhere 波動率指數:", [ln[:300] for ln in t.splitlines() if "波動率指數" in ln][:10])
except Exception as e: print("ERR", e)
