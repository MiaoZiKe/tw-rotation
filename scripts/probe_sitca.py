"""投信投顧公會（SITCA）公開統計頁探測（只在 Actions 手動跑，probe-etf-pcf.yml mode=sitca）。

為什麼要這支（2026-10-08 ETF 成分股第五輪）：發行投信官網抓不到的那幾家（兆豐擋雲端主機…），
公會每月公告「基金前十大投資標的」是第二順位的合法公開來源。公會網站是 ASP.NET WebForms，
要先 GET 拿 __VIEWSTATE 再 POST 表單才有表格 —— 這支把頁面上有哪些下拉選單（名稱、選項）印出來，
再照「最後一個年月＋第一個投信」送一次，印出回應表格的純文字，下一步才照實寫 parser（沒看過真回應不寫 parser）。

用法：python scripts/probe_sitca.py IN2629 IN2630 …（可帶 @欄位=值 覆寫送出的選項，例如 IN2629@ddlQ_Comid=A0005）
"""
from __future__ import annotations

import html as _html
import re
import sys

import requests

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BASE = "https://www.sitca.org.tw/ROC/Industry/{}.aspx"


def text_of(h: str) -> str:
    h = re.sub(r"(?is)<(script|style|select)[^>]*>.*?</\1>", " ", h)   # 下拉選單的幾百個選項會蓋掉表格
    h = re.sub(r"(?i)<br\s*/?>|</tr>|</p>|</div>", "\n", h)
    h = re.sub(r"(?i)</t[dh]>", " | ", h)
    t = _html.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"[ \t\r]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def fields(h: str) -> dict:
    out = {}
    for m in re.finditer(r'(?is)<input[^>]*type="hidden"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', h):
        out[m.group(1)] = _html.unescape(m.group(2))
    return out


def selects(h: str) -> dict:
    out = {}
    for m in re.finditer(r'(?is)<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', h):
        opts = re.findall(r'(?is)<option([^>]*)value="([^"]*)"[^>]*>([^<]*)', m.group(2))
        out[m.group(1)] = [(v, t.strip(), "selected" in a) for a, v, t in opts]
    return out


for arg in sys.argv[1:]:
    page, *over = arg.split("@")
    url = BASE.format(page)
    print("=" * 100)
    print("[", page, "]", url)
    s = requests.Session()
    s.headers["User-Agent"] = UA
    try:
        r = s.get(url, timeout=40)
        r.encoding = r.apparent_encoding or "utf-8"
        h = r.text
        print("  HTTP", r.status_code, "bytes", len(h))
        print("  頁面文字（前 1500 字）:", text_of(h)[:1500].replace("\n", " ⏎ "))
        sel = selects(h)
        for k, v in sel.items():
            print(f"  下拉 {k}：{len(v)} 個選項；" + ("全部：" + str([(a, b) for a, b, _ in v]) if "Class" in k or "CLASS" in k else f"前 8：{v[:8]}；最後 3：{v[-3:]}"))
        btns = re.findall(r'(?is)<input[^>]*type="submit"[^>]*name="([^"]+)"[^>]*value="([^"]*)"', h)
        print("  按鈕:", btns)
        data = fields(h)
        for k, v in sel.items():
            chosen = [x for x in v if x[2]]
            data[k] = (chosen[0][0] if chosen else (v[-1][0] if "YM" in k.upper() or "DATE" in k.upper() else (v[0][0] if v else "")))
        for o in over:
            k, _, v = o.partition("=")
            for name in list(sel):
                if name.endswith(k):
                    data[name] = v
        if btns:
            data[btns[0][0]] = btns[0][1]
        print("  送出:", {k: v for k, v in data.items() if not k.startswith("__")})
        r2 = s.post(url, data=data, timeout=60)
        r2.encoding = r2.apparent_encoding or "utf-8"
        t2 = text_of(r2.text)
        print("  POST HTTP", r2.status_code, "bytes", len(r2.text))
        k = t2.find("台積電")
        print("  回應文字（前 6000 字）:", t2[:6000].replace("\n", " ⏎ "))
        if k >= 0:
            print("  台積電前後:", t2[max(0, k - 1500):k + 1500].replace("\n", " ⏎ "))
        for kw in ("00918", "00921", "00905", "兆豐", "富蘭克林", "ETF"):
            i = t2.find(kw)
            if i >= 0:
                print(f"  「{kw}」前後:", t2[max(0, i - 300):i + 600].replace("\n", " ⏎ "))
    except Exception as e:  # noqa: BLE001 —— 探測，失敗只印
        print("  例外:", type(e).__name__, str(e)[:300])
