# 驗收段落「問卷結果1101」（管理區 #admin/survey，site/admin_survey.js）
# 這支由 _uitest.py 用 exec 載入；ok()、wait_until() 直接可用。不要在這裡寫三引號模組說明。
# flake8: noqa

# ===================================================================== 問卷結果1101
# Andy 11-01：新會員體驗到期前填問卷、好友邀請、Pro 許願；站主要看結果。
# 後端還在寫 → 用假後端（Python 小伺服器，契約見 wip/member-invite-api 的 docs/api/20261101_member_promo.md），瀏覽器真的操作：
#   ① 站主進得去：人數／平均／滿意以上／邀請數字正確、滿意度 5 列、最實用與需改善母分頁排行（母分頁數字取自 tree）
#   ② 點母分頁原地展開子分頁（排序正確），再點收起
#   ③ 文字意見：筆數、搜尋（篩出 1 筆、清空恢復）、匯出 CSV 內容（BOM、標題、列數、真實 email）
#   ④ 願望清單：筆數、搜尋、改狀態（假後端真的收到 id＋status）、CSV
#   ⑤ 錄影模式：有 TwRecMask 時畫面 email 遮罩、CSV 仍是真實 email
#   ⑥ 非站主：看到「不是管理者」、沒有任何表格或數字
#   ⑦ 版面：1440 與 390 沒有整頁橫向捲軸、按鈕不重疊
import http.server as _hs
import threading as _th

_SV_DATA = {
    "n": 11, "avg": 4.0, "sat": {"1": 1, "2": 0, "3": 2, "4": 3, "5": 5},
    "useful": {"stock": 10, "stock/kline": 5, "stock/chips": 3, "stock/fin": 2, "flow": 4, "overview": 1},
    "useful_tree": {"stock": {"n": 10, "subs": {"kline": 5, "chips": 3, "fin": 2}}, "flow": {"n": 4, "subs": {}}, "overview": {"n": 1, "subs": {}}},
    "improve": {"industry": 4, "industry/chain": 3, "season": 2},
    "improve_tree": {"industry": {"n": 4, "subs": {"chain": 3}}, "season": {"n": 2, "subs": {}}},
    "want": {"etf": 4, "tc": 2},
    "texts": [
        {"at": 1793500000000, "sat": 5, "email": "alice@example.com", "improve_text": "K 線載入有點慢", "want": ["etf"], "want_text": "想要選擇權"},
        {"at": 1793400000000, "sat": 4, "email": "bob@example.com", "improve_text": "", "want": [], "want_text": "多一點新聞"},
        {"at": 1793300000000, "sat": 1, "email": "carol@example.com", "improve_text": "手機版太擠", "want": ["tc"], "want_text": ""},
    ],
    "invite": {"codes": 6, "uses": 3},
}
_SV_WISH = {"items": [
    {"id": "w1", "at": 1793500000000, "email": "dave@example.com", "name": "Dave", "text": "希望可以看期貨籌碼", "feature": "market/futures", "status": "new"},
    {"id": "w2", "at": 1793400000000, "email": "erin@example.com", "name": "Erin", "text": "要有 LINE 通知", "feature": "alerts", "status": "doing"},
]}


def t_survey_1101(b, base, code):
    import json as _j
    T = "問卷結果1101"
    errs: list[str] = []
    got: list = []

    class H(_hs.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, st, obj):
            body = _j.dumps(obj).encode()
            self.send_response(st)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send(204, {})

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("content-length") or 0) or 0)
            try:
                body = _j.loads(raw or b"{}")
            except Exception:  # noqa: BLE001
                body = {}
            tok = body.get("t")
            who = {"tadmin": {"email": "andy@example.com", "name": "Andy", "admin": True, "tier": "pro"},
                   "tuser": {"email": "mem@example.com", "name": "Mem", "tier": "free"}}.get(tok)
            if self.path == "/v1/me":
                return self._send(200, {"user": who}) if who else self._send(401, {})
            if self.path.startswith("/v1/admin/"):
                if not (who and who.get("admin")):
                    return self._send(403, {"error": "forbidden"})
                if self.path == "/v1/admin/survey":
                    return self._send(200, _SV_DATA)
                if self.path == "/v1/admin/wishes":
                    return self._send(200, _SV_WISH)
                if self.path == "/v1/admin/wish/status":
                    got.append(body)
                    return self._send(200, {"ok": True})
            return self._send(200, {})

    srv = _hs.ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    _th.Thread(target=srv.serve_forever, daemon=True).start()
    shots = os.environ.get("TW_SURVEY_SHOTS")
    if shots:
        pathlib.Path(shots).mkdir(parents=True, exist_ok=True)

    def ctx(tok, W=1440):
        c = b.new_context(viewport={"width": W, "height": 900}, accept_downloads=True)
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": f"http://127.0.0.1:{port}"}) + ";"
                          f"try{{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.acct.tok','{tok}')}}catch(e){{}}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        return c

    def shot(pg, name):
        if shots:
            pg.screenshot(path=str(pathlib.Path(shots) / name), full_page=True)

    OVL = """() => { const bs = [...document.querySelectorAll('#svAdm button, #svAdm select, #svAdm input')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height; });
        const bad = []; for (let i = 0; i < bs.length; i++) for (let j = i + 1; j < bs.length; j++) { const a = bs[i].getBoundingClientRect(), c = bs[j].getBoundingClientRect();
          if (bs[i].contains(bs[j]) || bs[j].contains(bs[i])) continue;
          if (Math.min(a.right, c.right) - Math.max(a.left, c.left) > 1 && Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top) > 1) bad.push(bs[i].innerText + ' × ' + bs[j].innerText); }
        return { bad: bad.slice(0, 5), sw: document.documentElement.scrollWidth - innerWidth }; }"""
    try:
        c = ctx("tadmin"); pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        J = lambda js, *a: pg.evaluate(js, *a)
        pg.goto(base + "#admin/survey", wait_until="domcontentloaded")
        okp = False
        try:
            pg.wait_for_selector("#svN", timeout=15000); okp = True
        except Exception:  # noqa: BLE001
            pass
        if not ok(f"{T}：站主進得去 #admin/survey 看到問卷結果", okp):
            return
        ok(f"{T}：填寫人數 11", J("() => document.querySelector('#svN').textContent") == "11")
        ok(f"{T}：平均滿意度 4.00", J("() => document.querySelector('#svAvg').textContent") == "4.00")
        ok(f"{T}：滿意以上 73%（8 人）", "73%" == J("() => document.querySelector('#svGood').textContent"))
        ok(f"{T}：邀請碼 6／使用 3", [J("() => document.querySelector('#svInv').textContent"), J("() => document.querySelector('#svInvU').textContent")] == ["6", "3"])
        sat = J("() => [...document.querySelectorAll('#svSat .br')].map(r => r.querySelector('.nm').textContent.slice(0,1) + ':' + r.querySelector('.val').firstChild.textContent)")
        ok(f"{T}：滿意度 5 列 5→1 數量 5/3/2/0/1", sat == ["5:5", "4:3", "3:2", "2:0", "1:1"], sat)
        use = J("() => [...document.querySelectorAll('#svUseCard > .br')].map(r => r.querySelector('.nm').textContent + ':' + r.querySelector('.val').firstChild.textContent)")
        ok(f"{T}：最實用母分頁排行 個股10／資金流向4／總覽1（不重複加總子分頁）", use == ["個股:10", "資金流向:4", "總覽:1"], use)
        imp = J("() => [...document.querySelectorAll('#svImpCard > .br')].map(r => r.querySelector('.nm').textContent + ':' + r.querySelector('.val').firstChild.textContent)")
        ok(f"{T}：需改善排行 產業地圖4／週期統計2", imp == ["產業地圖:4", "週期統計:2"], imp)
        ok(f"{T}：想要的功能統計 ETF 4 票最前", J("() => document.querySelector('#svWant .br .nm').textContent") == "ETF" and J("() => document.querySelector('#svWant .br .val').firstChild.textContent") == "4")
        n0 = J("() => document.querySelectorAll('#svUseCard .subs').length")
        pg.click("#svUseCard [data-par]"); pg.wait_for_timeout(300)
        subs = J("() => [...document.querySelectorAll('#svUseCard .subs .br')].map(r => r.querySelector('.nm').textContent + ':' + r.querySelector('.val').firstChild.textContent)")
        ok(f"{T}：點「個股」原地展開子分頁（K 線5／籌碼3／財報2），原本沒展開", n0 == 0 and subs == ["K 線:5", "籌碼:3", "財報:2"], (n0, subs))
        ok(f"{T}：展開時網址沒離開 #admin/survey", "#admin/survey" in J("() => location.hash"))
        pg.click("#svUseCard [data-par]"); pg.wait_for_timeout(300)
        ok(f"{T}：再點一次收起", J("() => document.querySelectorAll('#svUseCard .subs').length") == 0)
        pg.click("#svUseCard [data-par]"); pg.wait_for_timeout(200)
        shot(pg, "result_1440.png")
        r = J(OVL)
        ok(f"{T}：1440 沒有橫向捲軸、按鈕不重疊", r["sw"] <= 0 and not r["bad"], r)
        # 文字意見
        pg.click("[data-t=texts]"); pg.wait_for_selector("#svTTbl")
        ok(f"{T}：文字意見 3 筆", J("() => document.querySelectorAll('#svTTbl tbody tr').length") == 3)
        ok(f"{T}：時間新到舊（alice 在第一列）、時間為臺北時間", "alice" in J("() => document.querySelector('#svTTbl tbody tr').innerText") and "2026-" in J("() => document.querySelector('#svTTbl tbody tr td').innerText"))
        pg.fill("#svTQ", "手機版"); pg.wait_for_timeout(200)
        ok(f"{T}：搜尋「手機版」只剩 carol 1 筆、計數 1 / 3", J("() => document.querySelectorAll('#svTTbl tbody tr').length") == 1 and "carol" in J("() => document.querySelector('#svTTbl').innerText") and "1 / 3" in J("() => document.querySelector('#svTCnt').textContent"))
        pg.fill("#svTQ", "etf"); pg.wait_for_timeout(200)
        ok(f"{T}：搜尋可搜到勾選的功能（ETF → alice）", "alice" in J("() => document.querySelector('#svTTbl').innerText") and J("() => document.querySelectorAll('#svTTbl tbody tr').length") == 1)
        pg.fill("#svTQ", ""); pg.wait_for_timeout(200)
        ok(f"{T}：清空搜尋恢復 3 筆", J("() => document.querySelectorAll('#svTTbl tbody tr').length") == 3)
        with pg.expect_download() as dl:
            pg.click("#svTCsv")
        csv = J("() => window.__surveyCsv")
        lines = csv.lstrip("﻿").split("\r\n")
        ok(f"{T}：CSV 有 BOM、標題列、3 筆資料", csv.startswith("﻿") and lines[0] == '"時間","email","滿意度","想改善的地方","想要的新功能"' and len(lines) == 4, lines[:2])
        ok(f"{T}：CSV 內容 alice 列正確（時間 2026、滿意度 5、勾選功能與自填）", any('alice@example.com' in l and '"5"' in l and 'K 線載入有點慢' in l and 'ETF；想要選擇權' in l for l in lines), lines)
        ok(f"{T}：下載檔名是 問卷文字意見_日期.csv", dl.value.suggested_filename.startswith("問卷文字意見_") and dl.value.suggested_filename.endswith(".csv"), dl.value.suggested_filename)
        pg.fill("#svTQ", "bob"); pg.wait_for_timeout(200)
        pg.click("#svTCsv"); csv2 = J("() => window.__surveyCsv")
        ok(f"{T}：搜尋後匯出只含篩出的那筆", csv2.count("\r\n") == 1 and "bob@" in csv2 and "alice" not in csv2, csv2)
        pg.fill("#svTQ", "")
        shot(pg, "texts_1440.png")
        # 願望
        pg.click("[data-t=wishes]"); pg.wait_for_selector("#svWTbl")
        ok(f"{T}：願望清單 2 筆", J("() => document.querySelectorAll('#svWTbl tbody tr').length") == 2)
        ok(f"{T}：功能欄顯示中文名（市場明細 › futures／提醒）", "市場明細" in J("() => document.querySelector('#svWTbl').innerText") and "提醒" in J("() => document.querySelector('#svWTbl').innerText"))
        pg.fill("#svWQ", "line"); pg.wait_for_timeout(200)
        ok(f"{T}：搜尋 line → erin 1 筆", J("() => document.querySelectorAll('#svWTbl tbody tr').length") == 1 and "erin" in J("() => document.querySelector('#svWTbl').innerText"))
        pg.fill("#svWQ", "")
        pg.select_option("select.wst[data-wid=w1]", "done"); pg.wait_for_timeout(500)
        ok(f"{T}：改狀態「已完成」→ 假後端收到 id=w1 status=done", got and got[-1].get("id") == "w1" and got[-1].get("status") == "done" and got[-1].get("t") == "tadmin", got)
        ok(f"{T}：狀態列寫「已更新：已完成」", "已完成" in J("() => document.querySelector('#svSt').textContent"))
        pg.click("[data-t=result]"); pg.click("[data-t=wishes]"); pg.wait_for_selector("#svWTbl")
        ok(f"{T}：切走再回來狀態仍是已完成", J("() => document.querySelector('select.wst[data-wid=w1]').value") == "done")
        pg.click("#svWCsv"); wc = J("() => window.__surveyCsv")
        ok(f"{T}：願望 CSV 含名稱、狀態欄", '"狀態"' in wc and "Dave" in wc and "已完成" in wc and "處理中" in wc, wc[:200])
        shot(pg, "wishes_1440.png")
        # 錄影模式
        J("() => { window.TwRecMask = (e) => String(e).replace(/^(.).*@/, '$1***@'); }")
        pg.click("[data-t=texts]"); pg.wait_for_selector("#svTTbl")
        em = J("() => [...document.querySelectorAll('#svTTbl td.e')].map(e => e.textContent)")
        ok(f"{T}：TwRecMask 存在 → 畫面 email 遮罩", em and all("***@" in x for x in em) and not any("alice" in x for x in em), em)
        pg.click("#svTCsv")
        ok(f"{T}：遮罩時匯出的 CSV 仍是真實 email", "alice@example.com" in J("() => window.__surveyCsv"))
        c.close()
        # 手機
        c = ctx("tadmin", 390); pm = c.new_page(); pm.on("pageerror", lambda e: errs.append("m: " + str(e)))
        pm.goto(base + "#admin/survey", wait_until="domcontentloaded"); pm.wait_for_selector("#svN", timeout=15000)
        r = pm.evaluate(OVL)
        small = pm.evaluate("() => [...document.querySelectorAll('#svAdm *')].filter(e => e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11).length")
        ok(f"{T}：390 沒有橫向捲軸、按鈕不重疊、沒有小於 11px 的字", r["sw"] <= 0 and not r["bad"] and small == 0, (r, small))
        if shots:
            pm.screenshot(path=str(pathlib.Path(shots) / "result_390.png"), full_page=True)
        pm.click("[data-t=texts]"); pm.wait_for_selector("#svTTbl")
        r = pm.evaluate(OVL)
        ok(f"{T}：390 文字意見表沒撐破頁面（表格在自己的捲動框內）", r["sw"] <= 0, r)
        c.close()
        # 非站主
        c = ctx("tuser"); pu = c.new_page(); pu.on("pageerror", lambda e: errs.append("u: " + str(e)))
        pu.goto(base + "#admin/survey", wait_until="domcontentloaded")
        denied = False
        try:
            pu.wait_for_selector("#svDeny", timeout=15000); denied = True
        except Exception:  # noqa: BLE001
            pass
        ok(f"{T}：非站主看到「不是管理者」", denied and "不是管理者" in pu.inner_text("#svDeny"))
        ok(f"{T}：非站主看不到任何數字或表格", pu.evaluate("() => !document.querySelector('#svN, #svTTbl, #svSat')"))
        c.close()
    finally:
        srv.shutdown()
    ok(f"{T}：整段沒有 JS 錯誤", not errs, errs[:3])


register("問卷結果1101", lambda pg, b, base, code: t_survey_1101(b, base, code))
