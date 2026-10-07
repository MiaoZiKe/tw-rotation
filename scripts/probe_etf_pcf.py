"""ETF 成分股（投信每日 PCF／持股明細）候選端點探測 —— 只在 Actions 上手動跑。

為什麼要這支：Claude 容器出口被擋，投信官網只有 Actions 打得到。
規矩是「沒有實測回應就不寫 parser」，所以先把每個候選的 HTTP 碼、型別、前幾百字印出來；
HTML 頁再把裡面看得到的 api／json／xls 網址撈出來，給下一輪探測用（多數投信是 SPA，資料走背後的 API）。
額外網址用命令列參數傳；要 POST 就寫成 `POST|網址|JSON body`。
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import sys

import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
today = dt.date.today()
d_slash = today.strftime("%Y/%m/%d")
d_ymd = today.strftime("%Y%m%d")

CANDS = [
    ("twse-openapi-swagger", "GET", "https://openapi.twse.com.tw/v1/swagger.json", None),
    ("tpex-openapi-swagger", "GET", "https://www.tpex.org.tw/openapi/swagger.json", None),
    ("yuanta-StkWeights-0050", "GET", "https://www.yuantaetfs.com/api/StkWeights?date=&fundid=1066", None),
    ("yuanta-Composition-0050", "GET", "https://www.yuantaetfs.com/api/Composition?date=&fundid=1066", None),
    ("yuanta-html-0050", "GET", "https://www.yuantaetfs.com/product/detail/0050/ratio", None),
    ("cathay-weightexcel", "GET", f"https://cwapi.cathaysite.com.tw/api/ETF/DownloadETFWeightExcel?FundCode=CN&SearchDate={d_slash}", None),
    ("cathay-html", "GET", "https://www.cathaysite.com.tw/ETF/detail/EDA?tab=etf4", None),
    ("fubon-pcf-006208", "GET", "https://websys.fsit.com.tw/FubonETF/Trade/Pcf.aspx?lan=TW&stock=006208", None),
    ("capital-buyback-00919", "POST", "https://www.capitalfund.com.tw/CFWeb/api/etf/buyback", {"fundId": "399", "date": None}),
    ("capital-html", "GET", "https://www.capitalfund.com.tw/etf/product/detail/399/portfolio", None),
    ("fhtrust-excel", "GET", f"https://www.fhtrust.com.tw/api/assetsExcel/ETF23/{d_ymd}", None),
    ("ctbc-html-00896", "GET", "https://www.ctbcinvestments.com/Etf/00896/Combination", None),
    ("ctbc-home", "GET", "https://www.ctbcinvestments.com/Etf/00896", None),
    ("sinopac-html", "GET", "https://sitc.sinopac.com/SinopacEtf/", None),
    ("kgi-html", "GET", "https://www.kgifund.com.tw/Fund/Detail?fundID=J012", None),
    ("nomura-html", "GET", "https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00935&tab=Shareholding", None),
    ("fundclear", "GET", "https://announce.fundclear.com.tw/MOPSonshoreFundWeb/doc.jsp", None),
]
if len(sys.argv) > 1 and sys.argv[1] == "--only-extra":
    CANDS = []
    sys.argv.pop(1)
for i, a in enumerate(sys.argv[1:]):
    if a.startswith("GREP~"):
        # 用 ~ 分隔的版本：正規式裡常需要 |（多選一），舊的 GREP| 寫法會被切壞
        _, pat, u = a.split("~", 2)
        CANDS.append((f"grep-{i}", "GREP", u, pat))
    elif a.startswith("GREP|"):
        _, pat, u = a.split("|", 2)
        CANDS.append((f"grep-{i}", "GREP", u, pat))
    elif a.startswith("POST|"):
        _, u, b = a.split("|", 2)
        CANDS.append((f"extra-{i}", "POST", u, json.loads(b)))
    else:
        CANDS.append((f"extra-{i}", "GET", a, None))

API_RE = re.compile(r"""["'(`]((?:https?:)?/?/?[^"'()`\s]{0,120}(?:api/|Api/|API/|\.json|xls|pcf|PCF|Pcf)[^"'()`\s]{0,120})["')`]""")

for tag, m, url, body in CANDS:
    print("=" * 100)
    print(f"[{tag}] {m} {url}")
    try:
        if m == "GREP":
            # 在大檔（JS bundle）裡找某個字樣，印前後文 —— 用來找 SPA 背後真正呼叫的 API 與參數
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            print(f"  HTTP {r.status_code}  bytes={len(r.content)}")
            for mm in list(re.finditer(body, r.text))[:25]:
                print("   >>", r.text[max(0, mm.start() - 250):mm.end() + 350].replace("\n", " "))
            continue
        if m == "POST":
            r = requests.post(url, json=body, headers={"User-Agent": UA}, timeout=30)
        else:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        ct = r.headers.get("content-type", "")
        print(f"  HTTP {r.status_code}  type={ct}  bytes={len(r.content)}")
        if "excel" in ct or "spreadsheet" in ct or r.content[:2] == b"PK" or r.content[:4] == b"\xd0\xcf\x11\xe0":
            print("  （二進位試算表）")
            try:
                import pandas as pd
                x = pd.read_excel(io.BytesIO(r.content), header=None)
                print(x.head(30).to_string()[:4000])
                print("  列數", len(x))
            except Exception as e:  # noqa: BLE001
                print("  讀 excel 失敗", e)
            continue
        t = r.text
        if tag.endswith("swagger"):
            try:
                paths = list(json.loads(t).get("paths", {}).keys())
                print("  paths 數", len(paths))
                for p in paths:
                    if re.search(r"etf|ETF|fund|Fund|pcf|PCF", p):
                        print("   *", p)
            except Exception as e:  # noqa: BLE001
                print("  swagger 解析失敗", e, t[:300])
            continue
        print("  前 5000 字:", t[:(60000 if m == "POST" else 5000)].replace("\n", " "))
        if "html" in ct or "javascript" in ct:
            for f in sorted(set(API_RE.findall(t)))[:200]:
                print("   api?", f[:240])
            # 伺服器端渲染（SSR）頁面：直接看成分股是不是已經在 HTML 裡（找台積電前後文）
            for kw in ("2330", "台積電"):
                k = t.find(kw)
                if k >= 0:
                    print(f"   「{kw}」前後文:", t[max(0, k - 700):k + 500].replace("\n", " "))
            for s in sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', t)))[:20]:
                print("   js:", s)
    except Exception as e:  # noqa: BLE001
        print("  例外:", type(e).__name__, str(e)[:300])
