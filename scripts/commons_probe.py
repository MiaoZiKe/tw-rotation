"""Commons 查詢探針（2026-11-09）：印出某查詢字的所有候選檔（授權、尺寸、mime），用來查圖池為什麼抓不到圖。用法：python scripts/commons_probe.py "cat:Jensen Huang" "Jensen Huang keynote" """
import sys, requests
sys.path.insert(0, "scripts")
import company_photos as cp
s = requests.Session(); s.headers["User-Agent"] = cp.UA
for q in sys.argv[1:]:
    print("=== ", q)
    try:
        for p in cp.search(s, q, 40):
            ii = (p.get("imageinfo") or [{}])[0]; md = ii.get("extmetadata") or {}
            print(p["title"], "|", ii.get("mime"), ii.get("width"), ii.get("height"), "|", cp.strip_html((md.get("LicenseShortName") or {}).get("value", "")), "|", cp.strip_html((md.get("Artist") or {}).get("value", ""))[:40])
    except Exception as ex:
        print("失敗", ex)
