"""臨時探測第二輪（只印 log，不寫檔）。"""
import csv, io, json, re, time, requests

UA = {"User-Agent": "Mozilla/5.0 tw-rotation-probe"}
KW = ["維持率", "追繳", "處分", "信用交易", "融資", "授信", "儀表板", "違約", "margin", "Margin"]


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=90, **kw)
            print(f"\n=== GET {url} -> {r.status_code} {r.headers.get('content-type')} len={len(r.content)}")
            return r
        except Exception as e:
            print(f"\n=== GET {url} -> ERR {e}")
            time.sleep(5)
    return None


# 1) 櫃買 swagger
for u in ["https://www.tpex.org.tw/openapi/swagger.json", "https://www.tpex.org.tw/openapi/v1/swagger.json"]:
    r = get(u)
    if r is not None and r.status_code == 200:
        try:
            sw = r.json()
        except Exception:
            print(r.text[:300]); continue
        paths = sw.get("paths", {})
        print("櫃買總端點數", len(paths))
        for p, ops in paths.items():
            txt = json.dumps(ops, ensure_ascii=False)
            summ = " | ".join(o.get("summary", "") for o in ops.values() if isinstance(o, dict))
            if any(k in txt or k in p for k in KW):
                print("  ★", p, "::", summ)
        break

# 2) 政府資料開放平臺全目錄
for u in ["https://data.gov.tw/datasets/export/csv", "https://data.gov.tw/datasets/export/json"]:
    r = get(u)
    if r is None or r.status_code != 200:
        continue
    t = r.content.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(t))) if u.endswith("csv") else None
    if rows:
        hdr = rows[0]
        print("目錄欄位", hdr[:12], "筆數", len(rows))
        for row in rows[1:]:
            line = " ".join(row)
            if any(k in line for k in ["維持率", "追繳", "信用交易", "融資融券", "儀表板", "擔保"]):
                print("  ★", " || ".join(c[:160] for c in row[:8]))
        break

# 3) 儀表板頁引用的資料主機（只讀一頁 HTML 與它的 JS，判斷資料來自哪個服務；不打任何資料端點）
base = "https://www.twse.com.tw"
r = get(base + "/dashboard/zh/credit/margin.html")
if r is not None and r.status_code == 200:
    t = r.text
    m = re.search(r"<title>(.*?)</title>", t, re.S); print("title:", m and m.group(1).strip())
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', t)
    print("scripts:", srcs)
    for m in set(re.findall(r'.{0,80}(?:使用條款|著作權|開放資料|下載|CSV|csv).{0,80}', t)):
        print("  ctx:", m)
    for s in srcs:
        if s.startswith("http") and "twse" not in s:
            continue
        u = s if s.startswith("http") else (base + s if s.startswith("/") else base + "/dashboard/zh/credit/" + s)
        rr = get(u)
        if rr is None or rr.status_code != 200:
            continue
        for m in sorted(set(re.findall(r'["\'`](/[A-Za-z0-9_\-/]*(?:rwd|api|dashboard|data)[A-Za-z0-9_\-/\.]*)', rr.text)))[:60]:
            print("  path:", m)
        for m in sorted(set(re.findall(r'https?://[A-Za-z0-9\.\-]+', rr.text)))[:30]:
            print("  host:", m)

# 4) 證交所網站使用條款頁（確認文字）
for u in [base + "/zh/page/about/company/terms.html", base + "/zh/terms/use.html", base + "/zh/page/terms.html"]:
    r = get(u)
    if r is not None and r.status_code == 200:
        txt = re.sub(r"<[^>]+>", " ", r.text)
        txt = re.sub(r"\s+", " ", txt)
        for m in re.findall(r".{0,200}(?:禁止|不得|程式|自動|爬|重製|轉載|商業).{0,200}", txt)[:8]:
            print("  terms:", m)
