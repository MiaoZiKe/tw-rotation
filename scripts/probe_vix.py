"""台指VIX 端點探測（只在 probe/vix 分支跑，不進 main）。"""
import json, os, re, sys, requests
H = {"User-Agent": "Mozilla/5.0 tw-rotation probe"}
out = {}
def hit(name, url, method="GET", **kw):
    try:
        r = requests.request(method, url, headers=kw.pop("headers", H), timeout=30, **kw)
        t = r.content.decode("utf-8", "replace") if "big5" not in (r.headers.get("content-type","").lower()) else r.content.decode("big5","replace")
        try:
            t2 = r.content.decode("utf-8")
        except Exception:
            t2 = r.content.decode("big5", "replace")
        out[name] = {"url": url, "status": r.status_code, "ctype": r.headers.get("content-type"), "len": len(r.content), "head": t2[:3000]}
        return r, t2
    except Exception as e:
        out[name] = {"url": url, "err": repr(e)[:300]}
        return None, ""
# 1 期交所 OpenAPI swagger
r, t = hit("taifex_openapi_swagger", "https://openapi.taifex.com.tw/swagger.json")
if r is not None and r.ok:
    try:
        sw = r.json(); paths = list((sw.get("paths") or {}).keys())
        out["taifex_openapi_paths"] = paths
        out["taifex_openapi_vix_like"] = [p for p in paths if re.search(r"vix|volat|波動", json.dumps(sw["paths"][p], ensure_ascii=False), re.I)]
        for p in out["taifex_openapi_vix_like"][:4]:
            hit("openapi" + p, "https://openapi.taifex.com.tw/v1" + p if not p.startswith("/v1") else "https://openapi.taifex.com.tw" + p)
    except Exception as e:
        out["taifex_openapi_parse_err"] = repr(e)
for alt in ["https://openapi.taifex.com.tw/v1/swagger.json", "https://openapi.taifex.com.tw/"]:
    hit("alt_" + alt, alt)
# 2 期交所 VIX 網頁（近 3 個月每日收盤）＋分鐘檔下載頁
r, t = hit("vixDaily3MNew", "https://www.taifex.com.tw/cht/7/vixDaily3MNew")
if t:
    m = re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)
    out["vixDaily3MNew_rows"] = [re.sub(r"<[^>]+>|\s+", " ", x).strip() for x in m[:12]] + [re.sub(r"<[^>]+>|\s+", " ", x).strip() for x in m[-5:]]
r, t = hit("vixMinNew", "https://www.taifex.com.tw/cht/7/vixMinNew")
if t:
    out["vixMinNew_links"] = re.findall(r'(?:href|onclick)="([^"]*(?:txt|zip|csv|file)[^"]*)"', t)[:40]
r, t = hit("vixDaily3MNew_eng", "https://www.taifex.com.tw/enl/eng7/vixDaily3MNew")
# 3 data.gov.tw 搜尋
for q in ["波動率指數", "VIX", "臺指選擇權"]:
    hit("datagov_" + q, "https://data.gov.tw/api/v2/rest/dataset", params={"q": q, "limit": 20})
# 4 mis.taifex 即時（VIX 是否在 getQuoteList）
for body in [{"MarketType": "0", "SymbolType": "O", "KindID": "1", "CID": "TXO", "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"},
             {"MarketType": "0", "SymbolType": "F", "KindID": "1", "CID": "", "ExpireMonth": "", "RowSize": "全部", "PageNo": "", "SortColumn": "", "AscDesc": "A"}]:
    r, t = hit("mis_quote_" + body["SymbolType"], "https://mis.taifex.com.tw/futures/api/getQuoteList", method="POST", json=body,
               headers={**H, "Content-Type": "application/json", "Referer": "https://mis.taifex.com.tw/futures/", "Origin": "https://mis.taifex.com.tw"})
    if t:
        out["mis_quote_" + body["SymbolType"] + "_vix"] = [m.start() for m in re.finditer("VIX|波動", t)][:5]
        i = t.find("VIX"); out["mis_quote_" + body["SymbolType"] + "_vixctx"] = t[max(0,i-400):i+400] if i >= 0 else ""
for u in ["https://mis.taifex.com.tw/futures/api/getVIX", "https://mis.taifex.com.tw/futures/VolatilityQuotes/", "https://mis.taifex.com.tw/futures/api/getVixData"]:
    hit("mis_" + u.rsplit("/",1)[-1], u, method="POST" if "api" in u else "GET", json={} if "api" in u else None,
        headers={**H, "Content-Type": "application/json", "Referer": "https://mis.taifex.com.tw/futures/"})
# 5 FRED VIXCLS
k = os.environ.get("FRED_API_KEY", "").strip()
r, t = hit("fred_vixcls", "https://api.stlouisfed.org/fred/series/observations",
           params={"series_id": "VIXCLS", "api_key": k, "file_type": "json", "sort_order": "desc", "limit": 5})
out.get("fred_vixcls", {}).pop("url", None)
# 6 FinMind 嘗試
tok = os.environ.get("FINMIND_TOKEN", "")
for ds in ["TaiwanVIX", "TaiwanOptionVIX", "VIX"]:
    r, t = hit("finmind_" + ds, "https://api.finmindtrade.com/api/v4/data", params={"dataset": ds, "start_date": "2026-10-01"},
               headers={**H, "Authorization": f"Bearer {tok}"})
    out["finmind_" + ds]["url"] = ds
r, t = hit("finmind_datalist", "https://api.finmindtrade.com/api/v4/datalist", params={"dataset": "TaiwanStockInfo"}, headers={**H, "Authorization": f"Bearer {tok}"})
out["finmind_datalist"]["url"] = "datalist"
r, t = hit("taifex_terms", "https://www.taifex.com.tw/cht/edu/userTerms")
if t:
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    out["taifex_terms_text"] = re.sub(r"<[^>]+>|\s+", " ", body)[:6000]
os.makedirs("probe_out", exist_ok=True)
json.dump(out, open("probe_out/vix_probe.json", "w"), ensure_ascii=False, indent=1)
for k, v in out.items():
    if k == "taifex_openapi_paths": continue
    print("=====", k); print(json.dumps(v, ensure_ascii=False)[:5000])
