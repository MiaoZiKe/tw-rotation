"""各投信 PCF 端點「帶指定日期」會不會回那一天（只在 Actions 手動跑：probe-etf-pcf.yml mode=pcfdate）。

為什麼（2026-11-09 維修）：11-06 那天 etf_holdings 只存到 84/235 檔，要補抓，必須知道各家日期參數的格式、
以及帶了之後回應裡的基準日是不是真的變成那一天（有些端點會忽略日期、永遠回最新）。
用法：python scripts/probe_etf_pcf_dates2.py [目標日 YYYY-MM-DD]；每家挑一檔、每種格式打一次，印「格式 → 回應基準日／列數」。
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")
from pipeline.sources import etf_pcf as E  # noqa: E402
from pipeline.util import http  # noqa: E402

TARGET = sys.argv[1] if len(sys.argv) > 1 else "2026-11-06"
y, m, d = TARGET.split("-")
FMT = {"slash": f"{y}/{m}/{d}", "dash": TARGET, "compact": f"{y}{m}{d}", "roc": f"{int(y) - 1911}/{m}/{d}"}


def report(tag: str, rows: list[dict]) -> None:
    ds = sorted({str(r.get("date")) for r in rows})
    print(f"  {tag:<38} 列數 {len(rows):>4}  基準日 {ds}", flush=True)


def trial(name: str, fn) -> None:
    print(f"== {name}", flush=True)
    for k, v in FMT.items():
        try:
            report(f"{k} ({v})", fn(v) or [])
        except Exception as exc:  # noqa: BLE001
            print(f"  {k} 例外 {str(exc)[:150]}", flush=True)
        time.sleep(1)


s = http.session()

# 群益
lst = E._req("POST", E.CAPITAL_LIST, json_body=None)
funds = (((lst or {}).get("data") or {}).get("funds")) or []
f = next((x for x in funds if str(x.get("stockNo")) == "00919"), funds[0] if funds else {})
trial("群益 00919 buyback date", lambda v: E.parse_capital("00919", E._req("POST", E.CAPITAL_PCF, json_body={"fundId": f.get("fundNo"), "date": v})))

# 野村
trial("野村 00935 SearchDate", lambda v: E.parse_nomura("00935", E._req("POST", E.NOMURA_PCF, json_body={"FundID": "00935", "SearchDate": v})))

# 復華（已知 qDate=YYYY/MM/DD）
fl = E._req("GET", E.FH_LIST)
fid = next((str(x.get("fundID")) for x in ((fl or {}).get("result") or []) if str(x.get("etf002")).strip() == "00991A"), "ETF23")
trial("復華 00991A qDate", lambda v: E.parse_fuhhwa(E._req("GET", E.FH_ASSETS, params={"fundID": fid, "qDate": v})))

# 統一
page = E._req("GET", E.UNI_PAGE, expect="text")
codes = E.uni_fund_codes(page or "")
ue = "00981A" if "00981A" in codes else next(iter(codes), None)
if ue:
    trial(f"統一 {ue} date", lambda v: E.parse_uni(ue, E._req("POST", E.UNI_PCF, json_body={"fundCode": codes[ue], "date": v, "specificDate": True})))

# 凱基
kpage = E._req("GET", E.KGI_PAGE, expect="text")
ids = E.kgi_fund_ids(kpage or "", {"00915": "凱基優選高股息30", "00938": "凱基優選30"})
for ke, kf in list(ids.items())[:1]:
    def kfn(v, ke=ke, kf=kf):
        r = s.post(E.KGI_PCF, data={"fundID": kf, "queryDate": v}, timeout=30)
        return E.parse_kgi(ke, r.text)
    trial(f"凱基 {ke} queryDate", kfn)

# 國泰
cf = E.cathay_funds()
cfc = cf.get("00878")
if cfc:
    trial("國泰 00878 SearchDate", lambda v: E.parse_cathay("00878", v, E._req("GET", E.CATHAY_STOCKS, params={"FundCode": cfc, "SearchDate": v})))
    a = E._req("GET", E.CATHAY_ASSETS, params={"FundCode": cfc, "SearchDate": FMT["slash"]})
    print("  國泰 GetETFAssets 帶 SearchDate → preDate", ((a or {}).get("result") or {}).get("preDate"), flush=True)

# 中信
def call(path, body, token=E.CTBC_SITE):
    return E._req("POST", E.CTBC_API + path, params={"token": token}, json_body={"token": token, **body}, retries=1)
lst = call("etf/ETFList", {"IsWithETF": "Y"})
cl = [(str(x.get("ETF_ID")).strip(), str(x.get("FID")).strip()) for x in (((lst or {}).get("Data") or {}).get("Data") or [])]
if cl:
    ce, cfid = cl[0]
    tok = ((((call("home/AuthToken", {}) or {}).get("Data")) or {}).get("token")) or E.CTBC_SITE
    for v in (f"{TARGET}T00:00:00.000Z", f"{TARGET}T16:00:00.000Z", TARGET):
        report(f"中信 {ce} StartDate={v}", E.parse_ctbc(ce, call("etf/ETFHoldingWeight", {"FID": cfid, "StartDate": v}, tok)))

# 第一金
trial("第一金 00728 pStrDate", lambda v: E.parse_fsitc("00728", E._req("POST", E.FSITC_HD, json_body={"pStrFundID": "D90", "pStrDate": v})))

# 華南永昌
tk = s.post(E.HN_API + "Auth/SysLogin", headers={"client_id": "WFPAPIPublicClient"}, timeout=30).json().get("access_token")
def hfn(v):
    return E.parse_hn("009808", s.post(E.HN_API + "ETF/BuyBack", json={"ETFID": "009808", "DataDate": v}, headers={"Authorization": f"Bearer {tk}"}, timeout=30).json())
trial("華南永昌 009808 DataDate", hfn)

# 台新
trial("台新 00936 DataDate", lambda v: E.parse_tsit("00936", E._req("GET", E.TSIT_PCF.format(code="00936"), params={"FundType": "ALL", "DataDate": v}, expect="text")))

# 大華銀
trial("大華銀 pcfDate", lambda v: E.parse_uob(E._uob_get("WebSitePcfRequest", {"fundID": "88329556", "pcfDate": v})))

# 聯邦
ucodes = E.usitc_codes(E._req("GET", E.USITC_PCF, expect="text") or "")
if ucodes:
    def ufn(v):
        return E.parse_usitc(ucodes[0], s.post(E.USITC_PCF, data={"FundNo": ucodes[0], "sDate": v.replace("/", "-")}, timeout=30).text)
    trial(f"聯邦 {ucodes[0]} sDate", ufn)

# 永豐／富邦／元大／聯博／安聯／玉山：沒有已知日期參數，各試最可能的參數名
sc = E.sinopac_codes(E._req("GET", E.SINOPAC_PCF, expect="text") or "")
if sc:
    for pn in ("date", "queryDate", "pcfDate", "dataDate"):
        report(f"永豐 {sc[0]} {pn}={TARGET}", E.parse_sinopac(sc[0], E._req("GET", E.SINOPAC_PCF, params={"fundId": sc[0], pn: TARGET}, expect="text")))
for pn in ("date", "qDate", "dataDate", "pcfDate"):
    report(f"富邦 00900 {pn}={FMT['slash']}", E.parse_fubon("00900", E._req("GET", E.FUBON_ASSETS, params={"stkId": "00900", "lan": "TW", pn: FMT["slash"]}, expect="text")))
for pn in ("date", "asOfDate"):
    report(f"聯博 00404A {pn}", E.parse_ab("00404A", E._req("GET", E.AB_HOLD.format(isin=E.tw_isin("00404A")), params={pn: TARGET})))
