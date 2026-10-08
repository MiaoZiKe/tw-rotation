"""台新／凱基／華南永昌的 PCF 回應裡，每一個日期字樣前後文（只在 Actions 手動跑：probe-etf-pcf.yml mode=dates）。

為什麼（2026-10-08 第五輪）：10-08 晚上實抓，這三家有 30 檔的「資料日」是 2026-10-12 ——
那是 PCF 適用的「下一個營業日」（10-09、10-10 連假），不是持股基準日。要找回應裡真正的淨值日欄位，
所以把回應裡所有日期與前後 60 字印出來，照實改 parser（沒看過真回應不寫 parser）。
"""
from __future__ import annotations

import html as _html
import json
import re
import sys

sys.path.insert(0, ".")
from pipeline.sources import etf_pcf  # noqa: E402
from pipeline.util import http  # noqa: E402

DATE = re.compile(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{3}/\d{1,2}/\d{1,2})")


def show(tag: str, text: str) -> None:
    t = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " | ", text or "")))
    print("=" * 100)
    print(tag, "bytes", len(text or ""))
    seen = 0
    for m in DATE.finditer(t):
        print("   ", t[max(0, m.start() - 70):m.end() + 50])
        seen += 1
        if seen > 25:
            break


s = http.session()
show("台新 00936", s.get(etf_pcf.TSIT_PCF.format(code="00936"), params={"FundType": "ALL", "DataDate": ""}, timeout=30).text)
r = s.get(etf_pcf.TSIT_PCF.format(code="00936"), params={"FundType": "ALL", "DataDate": ""}, timeout=30).text
for m in re.finditer(r'<input[^>]*(DATE|Date|date)[^>]*>', r):
    print("   input:", m.group(0)[:200])

page = s.get(etf_pcf.KGI_PAGE, timeout=30).text
ci_names = {"00915": "凱基優選高股息30", "00938": "凱基優選30"}
ids = etf_pcf.kgi_fund_ids(page, ci_names)
for etf, fid in list(ids.items())[:2]:
    show(f"凱基 {etf} {fid}", s.post(etf_pcf.KGI_PCF, data={"fundID": fid, "queryDate": ""}, timeout=30).text)

tok = s.post(etf_pcf.HN_API + "Auth/SysLogin", headers={"client_id": "WFPAPIPublicClient"}, timeout=30).json().get("access_token")
p = s.post(etf_pcf.HN_API + "ETF/BuyBack", json={"ETFID": "009808", "DataDate": ""}, headers={"Authorization": f"Bearer {tok}"}, timeout=30).json()
d = p.get("Data") if isinstance(p, dict) else None
print("=" * 100)
print("華南永昌 009808 Data 的非清單欄位：", json.dumps({k: v for k, v in (d or {}).items() if not isinstance(v, (list, dict))}, ensure_ascii=False)[:1500])
for k, v in (d or {}).items():
    if isinstance(v, dict):
        print("  子物件", k, json.dumps({a: b for a, b in v.items() if not isinstance(b, (list, dict))}, ensure_ascii=False)[:800])
