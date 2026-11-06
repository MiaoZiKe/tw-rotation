import json, os, requests
tok = os.environ.get("FINMIND_TOKEN", "")
H = {"Authorization": f"Bearer {tok}", "User-Agent": "tw-rotation probe"}
for name, params in [("recent", {"dataset": "TaiwanOptionVix", "start_date": "2026-10-20"}),
                     ("range", {"dataset": "TaiwanOptionVix", "start_date": "2026-11-03", "end_date": "2026-11-05"}),
                     ("old", {"dataset": "TaiwanOptionVix", "start_date": "2016-01-04", "end_date": "2016-01-08"}),
                     ("year", {"dataset": "TaiwanOptionVix", "start_date": "2025-11-01", "end_date": "2026-11-06"}),
                     ("noauth", {"dataset": "TaiwanOptionVix", "start_date": "2026-11-03"})]:
    try:
        r = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, headers=H if name != "noauth" else {"User-Agent": "x"}, timeout=60)
        j = r.json(); d = j.get("data") or []
        print("=====", name, r.status_code, j.get("msg"), "rows", len(d))
        if d:
            print("cols", list(d[0].keys()))
            print("first", json.dumps(d[:3], ensure_ascii=False)[:1500])
            print("last", json.dumps(d[-3:], ensure_ascii=False)[:1500])
            dates = sorted({str(x.get("date"))[:10] for x in d}); print("ndates", len(dates), dates[:3], dates[-3:])
    except Exception as e:
        print("=====", name, "ERR", repr(e)[:300])
