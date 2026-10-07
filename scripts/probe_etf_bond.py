"""債券型 ETF 持股端點探測（2026-10-08 第四輪）—— 只在 Actions 手動跑（probe-etf-pcf.yml mode=bond）。

為什麼要這支：已接上的 8 家投信（群益、野村、復華、統一、凱基、國泰、中信、元大）原本一律跳過代號尾碼 B/D 的債券型，
規矩是「沒看過真回應不寫 parser」。這支用跟股票型同一支端點打每家 1～2 檔債券型，把原始回應印出來
（JSON 印結構＋前 2500 字，HTML 印有「債」字的表格前後文），下一步才寫 parser。
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.sources import etf_pcf as E  # noqa: E402


def show(tag: str, p) -> None:
    print("=" * 100)
    print(f"[{tag}]")
    if p is None:
        print("  None")
        return
    if isinstance(p, str):
        t = p
        for m in list(re.finditer(r"債|到期|票面|利率|Coupon|Maturity", t))[:6]:
            print("   >>", t[max(0, m.start() - 800):m.end() + 1500].replace("\n", " "))
        if not re.search(r"債|到期", t):
            print(t[:2500])
        return
    print(json.dumps(p, ensure_ascii=False)[:4000])


def main2() -> None:
    """第二輪：前一輪印不到資料本體的幾家（元大 BondWeights 資料、統一 asset、復華有資料的日子、台新卡片）。"""
    today = dt.date.today()
    for c in ("00679B", "00720B"):
        pg = E._req("GET", E.YUANTA_PCF.format(code=c), expect="text") or ""
        body, env = E._nuxt_env(pg)
        for m in list(re.finditer(r"\.FundWeights=\{", body))[:2]:
            v = E._JS(body[m.end() - 1:], env).val()
            print(f"元大 {c} FundWeights 值：", json.dumps(v, ensure_ascii=False, default=str)[:3000])
        m = re.search(r"\.PCF=\{", body)
        print(f"元大 {c} PCF：", json.dumps(E._JS(body[m.end() - 1:], env).val() if m else None, ensure_ascii=False, default=str)[:600])
    page = E._req("GET", E.UNI_PAGE, expect="text")
    uc = E.uni_fund_codes(page or "")
    roc = f"{today.year - 1911}/{today.month:02d}/{today.day:02d}"
    for c in ("00853B",):
        p = E._req("POST", E.UNI_PCF, json_body={"fundCode": uc[c], "date": roc, "specificDate": False})
        print("統一 asset：", json.dumps((p or {}).get("asset"), ensure_ascii=False)[:3000])
        print("統一 schema：", json.dumps((p or {}).get("assetDetailSchema"), ensure_ascii=False)[:1500])
    fl = E._req("GET", E.FH_LIST)
    fh = {str(f.get("etf002") or "").strip(): str(f.get("fundID")) for f in ((fl or {}).get("result") or [])}
    for c in ("00710B",):
        for back in range(0, 8):
            q = (today - dt.timedelta(days=back)).strftime("%Y/%m/%d")
            p = E._req("GET", E.FH_ASSETS, params={"fundID": fh[c], "qDate": q}, retries=1)
            if isinstance(p, dict) and (p.get("result") or [{}])[0].get("detail"):
                print("復華", c, q, json.dumps(p, ensure_ascii=False)[:3000])
                break
    for c in ("00775B", "00842B"):
        pg = E._req("GET", E.TSIT_PCF.format(code=c), params={"FundType": "ALL", "DataDate": ""}, expect="text") or ""
        k = pg.find("card-header")
        print("台新", c, "card-header@", k, pg[k - 200:k + 3000].replace("\n", " ") if k >= 0 else pg[-3000:].replace("\n", " "))


def main3() -> None:
    """第三輪（永豐、玉山）：永豐 PCF 頁用 ?fundId= 換基金是否有效、各資產區塊長相；玉山 FundNo 對照。"""
    import time
    for c in ("00888", "00836B", "00410A"):
        pg = E._req("GET", "https://sitc.sinopac.com/SinopacEtfs/Etfs/Pcf", params={"fundId": c}, expect="text") or ""
        sel = re.search(r'<option[^>]*selected[^>]*>[^<]*</option>', pg)
        print("永豐", c, "selected:", sel.group(0) if sel else None, " qdate:", re.findall(r'id="qdate"[^>]*', pg)[:1])
        for m in list(re.finditer(r'cash_title-s">([^<]+)</div>', pg))[:8]:
            print("   區塊", m.group(1), "：", re.sub(r"\s+", " ", pg[m.end():m.end() + 2500]))
        for m in list(re.finditer(r"\d{4}/\d{2}/\d{2}", pg))[:5]:
            print("   日期", pg[max(0, m.start() - 80):m.end() + 20].replace("\n", " "))
    for no in range(1, 121):
        p = E._req("POST", "https://www.esunam.com/ETFAPI/GetFundTradeInfo", json_body={"FundNo": str(no)}, retries=1)
        e = (p or {}).get("Entries") or {}
        if isinstance(e, dict) and e.get("CFundShortName"):
            print("玉山 FundNo", no, e.get("CFundShortName"), e.get("CNavDt"), [t.get("TableTitle") for t in e.get("DynamicTableData") or []],
                  json.dumps([(t.get("TableTitle"), [c.get("Name") for c in t.get("Columns") or []], (t.get("Rows") or [])[:2]) for t in e.get("DynamicTableData") or []], ensure_ascii=False)[:800])
        time.sleep(0.2)


def main4() -> None:
    """第四輪（安聯）：webapi 直接 POST 回 400，看取 AntiForgery token 後帶哪個標頭會過，再試 FundID → 代號。"""
    import requests
    S = requests.Session()
    S.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    S.get("https://etf.allianzgi.com.tw/etf-list", timeout=30)
    r = S.get("https://etf.allianzgi.com.tw/webapi/api/AntiForgery/GetAntiForgeryToken", timeout=30)
    print("token 回應", r.status_code, r.text[:300], "cookies", list(S.cookies.keys()))
    try:
        tok = r.json()
    except ValueError:
        tok = r.text
    t = tok if isinstance(tok, str) else (tok.get("token") or tok.get("Token") or tok.get("requestToken") or json.dumps(tok))
    xs = S.cookies.get("XSRF-TOKEN") or t
    for h in ("X-XSRF-TOKEN", "RequestVerificationToken", "X-CSRF-TOKEN", None):
        hd = {"Content-Type": "application/json", "Origin": "https://etf.allianzgi.com.tw", "Referer": "https://etf.allianzgi.com.tw/etf-info/E0001?tab=1"}
        if h:
            hd[h] = xs
        q = S.post("https://etf.allianzgi.com.tw/webapi/api/Fund/GetFundAssets", json={"FundID": "E0001"}, headers=hd, timeout=30)
        print("標頭", h, q.status_code, q.text[:300])
        if q.status_code == 200:
            for i in range(1, 12):
                fid = f"E{i:04d}"
                d = S.post("https://etf.allianzgi.com.tw/webapi/api/Fund/GetFundDetail", json={"FundID": fid}, headers=hd, timeout=30)
                print("  detail", fid, d.status_code, d.text[:400])
            break


def main() -> None:
    today = dt.date.today()
    # 群益：清單 → fundNo
    lst = E._req("POST", E.CAPITAL_LIST, json_body=None)
    funds = {str(f.get("stockNo")).strip(): str(f.get("fundNo")) for f in (((lst or {}).get("data") or {}).get("funds") or [])}
    for c in ("00722B", "00937B"):
        if c in funds:
            show(f"群益 {c}", E._req("POST", E.CAPITAL_PCF, json_body={"fundId": funds[c], "date": None}))
    # 野村
    show("野村 00987B", E._req("POST", E.NOMURA_PCF, json_body={"FundID": "00987B", "SearchDate": None}))
    # 復華
    fl = E._req("GET", E.FH_LIST)
    fh = {str(f.get("etf002") or "").strip(): str(f.get("fundID")) for f in ((fl or {}).get("result") or [])}
    for c in ("00710B", "00768B"):
        if c in fh:
            for back in range(0, 6):
                q = (today - dt.timedelta(days=back)).strftime("%Y/%m/%d")
                p = E._req("GET", E.FH_ASSETS, params={"fundID": fh[c], "qDate": q}, retries=1)
                if isinstance(p, dict) and p.get("result"):
                    show(f"復華 {c} {q}", p)
                    break
    # 統一
    page = E._req("GET", E.UNI_PAGE, expect="text")
    uc = E.uni_fund_codes(page or "")
    roc = f"{today.year - 1911}/{today.month:02d}/{today.day:02d}"
    for c in ("00853B", "00931B"):
        if c in uc:
            show(f"統一 {c}", E._req("POST", E.UNI_PCF, json_body={"fundCode": uc[c], "date": roc, "specificDate": False}))
    # 凱基：清單頁沒有代號，只有簡稱
    kp = E._req("GET", E.KGI_PAGE, expect="text")
    m = re.search(r'value="(\[\{&quot;label.*?\])"', kp or "") or re.search(r'value="(\[\{"label".*?\])"', kp or "")
    import html as _h
    try:
        kl = json.loads(_h.unescape(m.group(1))) if m else []
    except ValueError:
        kl = []
    print("凱基清單：", [(x.get("label"), x.get("fundID")) for x in kl][:80])
    for x in kl:
        if "債" in str(x.get("label")):
            r = E.http.session().post(E.KGI_PCF, data={"fundID": x["fundID"], "queryDate": ""}, timeout=30)
            show(f"凱基 {x.get('label')}", r.text)
            break
    # 國泰
    cf = E.cathay_funds()
    for c in ("00687B", "00725B"):
        if c in cf:
            a = E._req("GET", E.CATHAY_ASSETS, params={"FundCode": cf[c]}, retries=1)
            show(f"國泰 {c} assets", a)
            day = E._iso(((a or {}).get("result") or {}).get("preDate")) or today.isoformat()
            for ep in ("GetETFDetailStockList", "GetETFDetailBondList", "GetETFDetailList"):
                show(f"國泰 {c} {ep}", E._req("GET", "https://cwapi.cathaysite.com.tw/api/ETF/" + ep,
                                                  params={"FundCode": cf[c], "SearchDate": day.replace("-", "/")}, retries=1))
    # 中信
    def call(path, body, token=E.CTBC_SITE):
        return E._req("POST", E.CTBC_API + path, params={"token": token}, json_body={"token": token, **body}, retries=1)
    cl = call("etf/ETFList", {"IsWithETF": "Y"})
    cm = {str(x.get("ETF_ID") or "").strip(): str(x.get("FID")) for x in (((cl or {}).get("Data") or {}).get("Data") or [])}
    tok = ((((call("home/AuthToken", {}) or {}).get("Data")) or {}).get("token")) or E.CTBC_SITE
    for c in ("00772B", "00981D"):
        if c in cm:
            start = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            p = call("etf/ETFHoldingWeight", {"FID": cm[c], "StartDate": start}, tok)
            show(f"中信 {c}", {"FundAssets": ((p or {}).get("Data") or {}).get("FundAssets"),
                               "blocks": [(b.get("Code"), (b.get("Data") or [])[:3]) for b in (((p or {}).get("Data") or {}).get("FundAssetsDetail") or [])]})
    # 元大
    for c in ("00679B", "00720B"):
        pg = E._req("GET", E.YUANTA_PCF.format(code=c), expect="text") or ""
        for key in ("FundWeights", "BondWeights", "Bond", "InKind"):
            k = pg.find(key)
            print(f"元大 {c} {key}@{k}:", pg[max(0, k - 100):k + 1500].replace("\n", " ") if k >= 0 else "無")
    # 台新債券（前一輪 00775B、00842B 沒抓到）
    for c in ("00775B", "00842B"):
        show(f"台新 {c}", E._req("GET", E.TSIT_PCF.format(code=c), params={"FundType": "ALL", "DataDate": ""}, expect="text"))


if __name__ == "__main__":
    main4() if "--round4" in sys.argv else main3() if "--round3" in sys.argv else (main2() if "--round2" in sys.argv else main())
