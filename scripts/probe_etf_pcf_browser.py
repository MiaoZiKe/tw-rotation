"""用真瀏覽器打開各投信的「持股／申購買回清單」頁，把背後回傳成分股的 XHR 抓出來（只在 Actions 手動跑）。

為什麼要這支：多數投信官網是 SPA（Angular／Vue／Nuxt），HTML 裡沒有資料，
資料是頁面載入後才向自家 API 要的；逐家讀 JS bundle 猜參數太慢。
這裡讓瀏覽器自己跑一次，記下「回應內容裡出現 2330 或台積電」的那幾個請求
（網址、方法、POST body、前 800 字），下一步才照實寫 parser —— 規矩仍是「沒看過真回應不寫 parser」。
"""
from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

PAGES = [
    ("元大 0050", "https://www.yuantaetfs.com/tradeInfo/pcf/0050"),
    ("國泰 00878", "https://www.cathaysite.com.tw/ETF/detail/EDA?tab=etf4"),
    ("富邦 006208", "https://websys.fsit.com.tw/FubonETF/Trade/Pcf.aspx?lan=TW&stkId=006208"),
    ("中信 00896", "https://www.ctbcinvestments.com/Etf/00896/Combination"),
    ("統一 PCF", "https://www.ezmoney.com.tw/ETF/Transaction/PCF"),
    ("凱基 ETF", "https://www.kgifund.com.tw/ETF/PCF"),
    ("大華 00918", "https://www.dahuasitc.com.tw/ETF/PCF/00918"),
    ("復華 00929", "https://www.fhtrust.com.tw/ETF/etf_detail/ETF23#stockhold"),
    ("野村 00935", "https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00935&tab=Shareholding"),
]
if len(sys.argv) > 1:
    PAGES = [(f"extra-{i}", u) for i, u in enumerate(sys.argv[1:])]

KEYS = ("2330", "台積電", "2317", "鴻海")

with sync_playwright() as p:
    br = p.chromium.launch()
    for tag, url in PAGES:
        print("=" * 100)
        print(f"[{tag}] {url}")
        ctx = br.new_context(locale="zh-TW", user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        pg = ctx.new_page()
        hits = []
        allreq = []

        def on_resp(r, hits=hits, allreq=allreq):
            try:
                rt = r.request.resource_type
                if rt not in ("xhr", "fetch", "document"):
                    return
                t = r.text()
                u = r.url
                if not any(x in u for x in ("google", "doubleclick", "scupio", "on.aws", "facebook", "line-scdn")):
                    pdd = (r.request.post_data or "")[:300]
                    allreq.append(f"{r.status} {r.request.method} {u[:300]}" + (f"\n        body={pdd}" if pdd else "")
                                  + f"\n        resp={t[:300]!r}")
                if any(k in t for k in KEYS):
                    hits.append((r.status, r.request.method, r.url, r.request.post_data, r.headers.get("content-type", ""), t))
            except Exception:  # noqa: BLE001 —— 探測，抓不到就算了
                pass

        pg.on("response", on_resp)
        clicks = []
        if "@@" in url:   # 網址@@文字1@@文字2：開頁後依序點含該文字的元素（SPA 要點進去才會打 API）
            url, *clicks = url.split("@@")
        try:
            pg.goto(url, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(3000)
            for c in clicks:
                try:
                    pg.get_by_text(c, exact=False).first.click(timeout=10000)
                    pg.wait_for_load_state("networkidle", timeout=30000)
                    pg.wait_for_timeout(3000)
                    print("  已點：", c, "→", pg.url)
                except Exception as e:  # noqa: BLE001
                    print("  點不到：", c, str(e)[:120])
            print("  最終網址:", pg.url, " 標題:", pg.title())
        except Exception as e:  # noqa: BLE001
            print("  開頁失敗:", type(e).__name__, str(e)[:200])
        try:
            links = pg.eval_on_selector_all("a[href]", "els => els.map(e => (e.innerText||'').trim().slice(0,20) + ' -> ' + e.href)")
            for l in links:
                if any(k in l for k in ("PCF", "pcf", "Pcf", "申購買回", "持股", "成分", "投資組合")):
                    print("    連結:", l[:200])
        except Exception:  # noqa: BLE001
            pass
        print(f"  XHR／文件請求 {len(allreq)} 個：")
        for a in allreq[:40]:
            print("    ", a)
        print(f"  含成分股字樣的回應 {len(hits)} 個：")
        for st, m, u, pd_, ct, t in hits[:6]:
            print(f"   ★ {st} {m} {u}")
            if pd_:
                print("     POST body:", pd_[:400])
            print("     type:", ct, " bytes:", len(t))
            k = min([t.find(x) for x in KEYS if t.find(x) >= 0])
            print("     開頭:", t[:500].replace("\n", " "))
            print("     2330 前後:", t[max(0, k - 400):k + 400].replace("\n", " "))
        ctx.close()
    br.close()
