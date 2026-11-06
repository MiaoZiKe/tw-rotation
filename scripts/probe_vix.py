import json, re, io, csv, requests
H = {"User-Agent": "Mozilla/5.0 tw-rotation probe"}
def show(name, r, n=1500):
    try:
        t = r.content.decode("utf-8", "replace")
    except Exception as e:
        t = repr(e)
    print("=====", name, r.status_code, r.headers.get("content-type"), len(r.content)); print(t[:n]); return t
def safe(f):
    try: return f()
    except Exception as e: print("ERR", repr(e)[:300])
# 1 期交所 VIX 頁面上的所有連結
for u in ["https://www.taifex.com.tw/cht/7/vixDaily3MNew", "https://www.taifex.com.tw/cht/7/vixMinNew", "https://www.taifex.com.tw/cht/7/vixMin3MNew"]:
    def f(u=u):
        r = requests.get(u, headers=H, timeout=30); t = r.text
        i = t.find("交易日期"); print("=====", u, r.status_code); print(re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", "", t[i-3000:i+6000], flags=re.S))[:5000])
        print("links", sorted(set(re.findall(r'(?:href|src|action|onclick)=["\']([^"\']+)["\']', t)) - set())[:400])
    safe(f)
# 2 data.gov.tw 全部資料集清單（CSV）找期交所／波動率
def g():
    for u in ["https://data.gov.tw/datasets/export/csv", "https://data.gov.tw/datasets/export/json"]:
        r = requests.get(u, headers=H, timeout=120)
        print("=====", u, r.status_code, r.headers.get("content-type"), len(r.content))
        if r.ok and len(r.content) > 10000:
            t = r.content.decode("utf-8-sig", "replace")
            hits = [ln for ln in t.splitlines() if ("期貨交易所" in ln or "期交所" in ln)]
            print("taifex rows", len(hits))
            for ln in hits: 
                if re.search("波動|VIX|vix", ln): print("VIXHIT", ln[:1500])
            print("sample taifex titles", [re.split(r",", h)[1][:40] if "," in h else h[:60] for h in hits[:80]])
            break
safe(g)
for q in ["波動率指數", "VIX"]:
    safe(lambda q=q: show("datagov_post_" + q, requests.post("https://data.gov.tw/api/v2/rest/dataset", json={"q": q}, headers=H, timeout=30), 2500))
    safe(lambda q=q: show("datagov_search_" + q, requests.get("https://data.gov.tw/api/front/dataset/list", params={"q": q}, headers=H, timeout=30), 1500))
# 3 data.twse.com.tw
safe(lambda: show("datatwse_detail", requests.get("https://data.twse.com.tw/front/detail/444e9fc719b7472f914d943bcc59b882", headers=H, timeout=30), 3000))
safe(lambda: show("taifex_vixQA", requests.get("https://www.taifex.com.tw/cht/7/vixQA", headers=H, timeout=30), 200))
