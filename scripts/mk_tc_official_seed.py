"""產生 site/tc/official_seed.json（科技透明圈公開版的種子資料）。

為什麼有這支：官方開放資料（pipeline/sources/salary_official.py）要在 GitHub Actions 才抓得到，開發容器連不到；
上線前頁面要有東西可看，所以把「媒體轉述官方公告」的數字人工整理成種子（每筆標來源與整理日）。
管線抓到官方資料後，前端以 data/tc_salary.json 為準、種子只補沒有的。用法：python scripts/mk_tc_official_seed.py
"""
import json, glob, re, sys
from pathlib import Path
root = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent.parent)
extra = {  # 搜尋摘要補的數字（2026-11-03 WebSearch，單一來源者在 note 註明）
    "3529": dict(avg_wan=317.3, median_wan=None, url="https://money.udn.com/money/story/5607/9598748",
                 note="平均數取自媒體轉述上櫃排行（第三名）；中位數未取得"),
    "3034": dict(median_wan=265.2, url="https://www.managertoday.com.tw/articles/view/72434",
                 note="中位數取自經理人報導前十名表（上市第 7 名）；平均數另見官方公告轉述"),
    "3711": dict(avg_wan=628.0, median_wan=None, url="https://blog.104.com.tw/salary-rankings-of-listed-companies-in-2025/",
                 note="平均數取自 104 職場力整理（日月光投控）；中位數未取得"),
}
U = "https://www.managertoday.com.tw/articles/view/72434"
for c, m in (("6526", 280.5), ("3443", 257.6), ("4961", 230.3), ("3014", 229.7)):
    extra[c] = dict(median_wan=m, url=U, note="中位數取自經理人報導的上市前十名表；平均數未取得")
YOY = {"2330": 19.55, "5269": 35.72, "5274": 13.31}   # 中位數年增（%），媒體轉述
rows, missing, cos = [], [], []
for f in sorted(glob.glob(root + "/site/tc/json/*.json")):
    d = json.load(open(f, encoding="utf-8"))
    for c in d["companies"]:
        code = c.get("code")
        if code and str(code).isdigit():
            cos.append(dict(code=str(code), name=c["name"], ind=d["industry"]))
        m = c.get("mops") or {}
        avg, med = m.get("avg_wan"), m.get("median_wan")
        url, note = m.get("url"), m.get("note")
        yr = m.get("year")
        yr = int(re.sub(r"\D", "", str(yr))) if yr else None
        if yr and yr < 1911:
            yr += 1911
        e = extra.get(str(code))
        if e:
            avg = e.get("avg_wan", avg) or avg
            med = e.get("median_wan", med) or med
            url = e.get("url") or url
            note = e.get("note") or note
            yr = yr or 2025
        if code and str(code).isdigit() and (avg or med):
            if note and note.startswith("查"):
                note = None
            rows.append(dict(code=str(code), name=c["name"], ind=d["industry"], year=yr,
                             avg_wan=avg, median_wan=med, n=m.get("n"), yoy_pct=YOY.get(str(code)),
                             url=url if url and url.startswith("http") else None, note=note))
        else:
            missing.append(c["name"])
out = dict(asof="2026-11-03", unit="萬元／年", scope="非擔任主管職務之全時員工",
           source="證交所／櫃買中心公告（經媒體轉述整理，人工核對標日期）；pipeline 上線後由官方開放資料自動取代",
           rows=rows, cos=cos)
json.dump(out, open(root + "/site/tc/official_seed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(rows), "家有數字；", len(missing), "家沒有")
for r in rows:
    print(r["code"], r["name"], r["year"], r["avg_wan"], r["median_wan"])
