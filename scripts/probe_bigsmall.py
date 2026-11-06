"""臨時探測（probe/bigsmall）：mis 欄位與更新頻率、FinMind 逐筆權限、證交所／櫃買 openapi 有沒有逐筆或單量分級端點。"""
import json, os, time, requests
out = {}
os.makedirs("probe_out", exist_ok=True)
H = {"User-Agent": "Mozilla/5.0", "Referer": "https://mis.twse.com.tw/stock/index.jsp"}
ex = "tse_2330.tw|tse_2317.tw|tse_1101.tw|otc_6488.tw|tse_2603.tw"
snaps = []
for i in range(30):
    try:
        r = requests.get("https://mis.twse.com.tw/stock/api/getStockInfo.jsp", params={"ex_ch": ex, "json": 1, "delay": 0, "_": int(time.time()*1000)}, headers=H, timeout=10)
        snaps.append({"i": i, "status": r.status_code, "at": time.time(), "body": r.json() if r.ok else r.text[:300]})
    except Exception as e:
        snaps.append({"i": i, "err": str(e)})
    time.sleep(3)
out["mis"] = {"n": len(snaps), "first": snaps[0], "keys": sorted({k for s in snaps if isinstance(s.get("body"), dict) for m in s["body"].get("msgArray", []) for k in m}),
              "changes": [[m.get("c"), m.get("t"), m.get("tlong"), m.get("z"), m.get("tv"), m.get("v")] for s in snaps if isinstance(s.get("body"), dict) for m in s["body"].get("msgArray", [])][:60]}
tok = os.environ.get("FINMIND_TOKEN", "")
for ds in ["TaiwanStockPriceTick", "TaiwanStockKBar", "TaiwanStockTradingDailyReport"]:
    try:
        r = requests.get("https://api.finmindtrade.com/api/v4/data", params={"dataset": ds, "data_id": "2330", "start_date": "2026-11-05", "end_date": "2026-11-05"}, headers={"Authorization": "Bearer " + tok}, timeout=30)
        j = r.json(); out[ds] = {"status": r.status_code, "msg": j.get("msg"), "n": len(j.get("data") or []), "sample": (j.get("data") or [])[:3]}
    except Exception as e:
        out[ds] = {"err": str(e)}
for name, url in [("twse", "https://openapi.twse.com.tw/v1/swagger.json"), ("tpex", "https://www.tpex.org.tw/openapi/swagger.json")]:
    try:
        j = requests.get(url, timeout=30).json()
        paths = j.get("paths", {})
        hits = []
        for p, v in paths.items():
            s = json.dumps(v, ensure_ascii=False)
            if any(k in s for k in ["逐筆", "明細", "大單", "鉅額", "筆數", "分價", "Tick", "tick"]):
                summ = [x.get("summary") for x in v.values() if isinstance(x, dict)]
                hits.append([p, summ])
        out[name] = {"n_paths": len(paths), "hits": hits}
    except Exception as e:
        out[name] = {"err": str(e)}
json.dump(out, open("probe_out/bigsmall_probe.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False)[:20000])
