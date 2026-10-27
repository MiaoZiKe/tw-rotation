# 驗收段落「自選日報提醒1027」（site/digest.js、notices.js 鈴鐺、watchpage.js、Worker /v1/alerts/*）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、re 直接可用，不要 import _uitest。
# Andy 2026-10-27 拍板 T-4：自選日報（Pro）＋自設提醒（註冊 1、Plus 5、Pro 不限）。假 Worker（page.route）＋假 digest.json：
# Pro：自選頁看到日報表（只有事實欄位）→ 鈴鐺出現「自選日報」通知 → 設一條「收盤價高於 3000」（現價 2385、不成立，鈴鐺不變）
#      → 把 digest.json 換成收盤 3100 的版本、重新載入（模擬條件成立）→ 鈴鐺多一則「提醒」→ 點通知卡跳 #watch。
# Plus：日報顯示鎖定說明、提醒上限 5（已有 5 條時「加入提醒」反灰、顯示上限）。
# 1440 與 390 各一次，截圖存 scratchpad/digest_*.png。
import copy as _dg_copy
import json as _dg_json

_DG_API = "https://digest1027.example.test"
_DG_SHOTS = "/tmp/claude-0/-home-user-tw-rotation/5cb9df1a-365b-5e58-9994-2ccda431af9a/scratchpad"
_DG_DATA = {
    "v": 1, "asof": "2026-10-22", "prev": "2026-10-21", "ia": "2026-10-22", "unit": {},
    "s": {
        "2330": {"n": "台積電", "c": 2385.0, "pc": 2420.0, "v": 29797, "i": [-12695, 1350, 1196, -10149], "k": [-12, 17, -12],
                 "r": {"ym": "2026-09", "rev": 5118.57, "yoy": 54.6, "mom": -0.6, "ann": "2026-10-10"}, "e": [["法說會", "2026-10-30"]]},
        "2317": {"n": "鴻海", "c": 245.0, "pc": 244.0, "v": 51234, "i": [800, 0, 1200, 2000], "k": [3, 0, 4], "x": {"d": "2026-11-05", "a": 1.5}},
    },
}
_DG_BAD = re.compile(r"評分|排名|訊號|燈號|建議買|買點|賣點|進場|出場|目標價|看多|看空|推薦|最佳時機")


def _dg_ctx(b, W, plan, st, errs):
    mob = W <= 640
    feats = {"watch.page": True, "watch.tabs": 50, "watch.size": 200, "watch.digest": plan == "pro", "watch.alert": 200 if plan == "pro" else 5}

    def handle(route):
        req = route.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        body = {}
        try:
            body = _dg_json.loads(req.post_data or "{}")
        except Exception:
            pass
        out, status = {}, 200
        if path == "/v1/me":
            out = {"user": {"email": plan + "@example.com", "name": "測試", "admin": False, "owner": False}}
        elif path == "/v1/perm/me":
            out = {"who": "member", "plan": plan, "planName": plan.capitalize(), "feats": feats, "lims": {}, "dq": None}
        elif path == "/v1/lists/get":
            out = {"lists": [{"id": "t1", "name": "我的", "codes": ["2330", "2317"]}], "rev": 1}
        elif path == "/v1/lists/put":
            out = {"ok": True, "rev": 2, "lists": body.get("lists", [])}
        elif path == "/v1/alerts/get":
            out = {"alerts": st["rules"], "rev": st["rev"], "cap": feats["watch.alert"]}
        elif path == "/v1/alerts/put":
            if len(body.get("alerts", [])) > max(feats["watch.alert"], len(st["rules"])):
                out, status = {"error": "alert_limit", "limit": feats["watch.alert"], "alerts": st["rules"], "rev": st["rev"]}, 403
            else:
                st["rules"] = body["alerts"]; st["rev"] += 1; st["puts"] += 1
                out = {"ok": True, "rev": st["rev"], "alerts": st["rules"], "cap": feats["watch.alert"]}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path == "/v1/grants/public":
            out = {"now": 0, "promo": [], "welcome": []}
        elif path == "/v1/grants/me":
            out = {"now": 0, "today": {}, "grants": []}
        route.fulfill(status=status, body=_dg_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    c = b.new_context(viewport={"width": W, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
    c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _dg_json.dumps({"api": _DG_API}) + ";"
                      "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.tourDone','1');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.acct.tok','tok-test')}catch(e){}")
    c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    c.route("**/notices/features.json*", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    c.route("**/data/digest.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=_dg_json.dumps(st["digest"])))
    c.route(_DG_API + "/**", handle)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{W}/{plan}: {e}"))
    return c, pg


def _dg_open_watch(pg, base):
    pg.goto(base + "#watch", wait_until="domcontentloaded")
    a = pg.get_by_role("button", name="同意並繼續")
    if a.count() and a.first.is_visible():
        a.first.click(); pg.wait_for_timeout(300)
    return wait_until(pg, "() => !!document.getElementById('wdCard') && !!document.querySelector('#wdCard .seg')", 15000)


def t_digest_1027(b, base, code):
    T = "自選日報提醒1027"
    errs = []
    for W in (1440, 390):
        mob = W <= 640
        # ---------- Pro
        st = {"rules": [], "rev": 0, "puts": 0, "digest": _dg_copy.deepcopy(_DG_DATA)}
        c, pg = _dg_ctx(b, W, "pro", st, errs)
        got = _dg_open_watch(pg, base)
        ok(f"{T}（{W}/Pro）自選頁出現「自選日報與提醒」卡，預設在「今日日報」", bool(got) and pg.evaluate("() => document.querySelector('#wdCard .seg .on').dataset.wdv") == "digest")
        wait_until(pg, "() => !!document.querySelector('#wdTbl tbody tr')", 8000)
        tbl = pg.evaluate("() => { const t = document.getElementById('wdTbl'); return t ? t.innerText : ''; }")
        ok(f"{T}（{W}/Pro）日報表有收盤價、成交量、法人買賣超、月營收、公告事件，且沒有評分／建議字樣",
           "2,385.00" in tbl and "29,797" in tbl and "-12,695" in tbl and "5,118.6" in tbl and "法說會 10/30" in tbl and "除息 11/05" in tbl and not _DG_BAD.search(tbl), tbl[:300])
        col = pg.evaluate("() => { const r = document.querySelector('#wdTbl tbody tr'), g = (e) => getComputedStyle(e).color; return { ext: g(r.children[4]), chg: g(r.children[2]), ink: g(r.children[1]) }; }")
        ok(f"{T}（{W}/Pro）賣超紅漲綠跌配色：外資賣超（負）與跌幅同色（綠）、不是一般文字色", col["ext"] == col["chg"] and col["ext"] != col["ink"], col)
        card = pg.evaluate("() => document.getElementById('wdCard').innerText")
        ok(f"{T}（{W}/Pro）整張卡沒有評分／建議字樣", not _DG_BAD.search(card), card[:200])
        pg.evaluate("() => document.getElementById('wdCard').scrollIntoView({block:'start'})")
        pg.wait_for_timeout(200)
        pg.screenshot(path=f"{_DG_SHOTS}/digest_table_{W}.png")
        # 鈴鐺：日報通知
        wait_until(pg, "() => { const d = document.getElementById('ntDot'); return !!d && !d.hidden && d.textContent === '1'; }", 8000)
        pg.click("#ntBell")
        wait_until(pg, "() => document.querySelectorAll('#ntDrop .ntitem').length >= 1", 3000)
        item = pg.evaluate("() => { const e = document.querySelector('#ntDrop .ntitem'); return e ? { t: e.innerText, k: !!e.querySelector('.ntkind.k-digest') } : null; }")
        ok(f"{T}（{W}/Pro）鈴鐺紅點 1，下拉有「自選日報」通知（台積電、鴻海兩檔、事實欄位、非投資建議）",
           bool(item) and item["k"] and "自選日報 10/22：2 檔自選" in item["t"] and "台積電" in item["t"] and "鴻海" in item["t"] and "非投資建議" in item["t"] and not _DG_BAD.search(item["t"]), item)
        pg.screenshot(path=f"{_DG_SHOTS}/digest_bell_{W}.png")
        pg.keyboard.press("Escape"); pg.mouse.click(5, 300); pg.wait_for_timeout(200)
        # 設提醒：高於 3000（現價 2385，不成立）
        pg.click("#wdCard [data-wdv=rules]")
        wait_until(pg, "() => !!document.getElementById('wdAdd')", 3000)
        pg.select_option("#wdCode", "2330"); pg.select_option("#wdType", "above")
        pg.fill("#wdX", "3000"); pg.click("#wdAdd")
        saved = wait_until(pg, "() => document.querySelectorAll('#wdCard .wdrule').length === 1", 4000)
        txt = pg.evaluate("() => document.querySelector('#wdCard .wdrule .tx').innerText")
        ok(f"{T}（{W}/Pro）加入「收盤價高於 3000」→ 打 /v1/alerts/put、列表出現一條、文案中性", bool(saved) and st["puts"] == 1 and "收盤價高於 3,000.00 元" in txt and not _DG_BAD.search(txt), [st["puts"], txt])
        pg.wait_for_timeout(300)
        dot = pg.evaluate("() => document.getElementById('ntDot').textContent")
        ok(f"{T}（{W}/Pro）現價 2385 未超過 3000 → 條件不成立，鈴鐺沒有多通知", dot == "1", dot)
        # 再加一條「法人連買」：台積電投信連買 17 天 ≥ 5 → 立刻成立 → 鈴鐺 2
        pg.select_option("#wdType", "streak"); wait_until(pg, "() => !!document.getElementById('wdN')", 2000)
        pg.select_option("#wdWho", "trust"); pg.select_option("#wdSide", "buy"); pg.fill("#wdN", "5"); pg.click("#wdAdd")
        wait_until(pg, "() => document.getElementById('ntDot').textContent === '2'", 4000)
        pg.click("#ntBell")
        wait_until(pg, "() => document.querySelectorAll('#ntDrop .ntitem').length >= 2", 3000)
        al = pg.evaluate("() => [...document.querySelectorAll('#ntDrop .ntitem')].map(e => e.innerText).find(t => t.indexOf('提醒：') >= 0) || ''")
        ok(f"{T}（{W}/Pro）法人連買條件成立 → 鈴鐺 2，通知寫「你設定的條件成立：投信已連續買超 17 天」", "投信連續買超 5 天以上" in al and "你設定的條件成立" in al and "投信已連續買超 17 天" in al, al)
        pg.keyboard.press("Escape"); pg.mouse.click(5, 300); pg.wait_for_timeout(200)
        # 模擬「高於 3000」成立：換一份收盤 3100 的 digest（隔日資料），重新載入
        st["digest"]["asof"] = "2026-10-23"
        st["digest"]["s"]["2330"]["c"] = 3100.0
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => { const d = document.getElementById('ntDot'); return !!d && !d.hidden && Number(d.textContent) >= 3; }", 12000)
        pg.click("#ntBell")
        wait_until(pg, "() => [...document.querySelectorAll('#ntDrop .ntitem')].some(e => e.innerText.indexOf('收盤價高於 3,000.00 元') >= 0)", 4000)
        items = pg.evaluate("() => [...document.querySelectorAll('#ntDrop .ntitem')].map(e => e.innerText)")
        hit = [t for t in items if "收盤價 3,100.00 元，高於你設定的 3,000.00 元" in t]
        ok(f"{T}（{W}/Pro）資料日換成 10/23、收盤 3100 → 「高於 3000」成立，鈴鐺出現提醒；10/23 的日報也出現", bool(hit) and any("自選日報 10/23" in t for t in items) and not any(_DG_BAD.search(t) for t in items), items)
        pg.screenshot(path=f"{_DG_SHOTS}/digest_alert_{W}.png")
        # 點通知卡 → 跳 #watch
        pg.goto(base + "#overview", wait_until="domcontentloaded"); pg.wait_for_timeout(800)
        pg.click("#ntBell")
        wait_until(pg, "() => document.querySelectorAll('#ntDrop .ntitem').length >= 1", 3000)
        pg.click("#ntDrop .ntitem .ttl")
        moved = wait_until(pg, "() => location.hash.startsWith('#watch')", 4000)
        ok(f"{T}（{W}/Pro）點通知卡 → 跳到 #watch", bool(moved), pg.evaluate("() => location.hash"))
        # 刪一條 → 打 put、列表少一條；啟用開關
        _dg_open_watch(pg, base)
        pg.click("#wdCard [data-wdv=rules]")
        wait_until(pg, "() => document.querySelectorAll('#wdCard .wdrule').length === 2", 5000)
        p0 = st["puts"]
        pg.click("#wdCard [data-wddel]")
        wait_until(pg, "() => document.querySelectorAll('#wdCard .wdrule').length === 1", 4000)
        ok(f"{T}（{W}/Pro）刪除一條提醒 → 打 put、剩 1 條", st["puts"] == p0 + 1 and len(st["rules"]) == 1, [st["puts"], len(st["rules"])])
        # 版面：手機不得橫向捲、字不小於 11px
        ovf = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        small = pg.evaluate("() => [...document.querySelectorAll('#wdCard *')].filter(e => e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11).length")
        ok(f"{T}（{W}/Pro）沒有橫向捲軸、卡內沒有小於 11px 的字", ovf <= 1 and small == 0, [ovf, small])
        pg.screenshot(path=f"{_DG_SHOTS}/digest_rules_{W}.png")
        c.close()

    # ---------- Plus：日報鎖定、提醒上限 5
    for W in (1440, 390):
        st = {"rules": [{"id": f"r{i}", "code": "2330", "type": "above", "x": 5000 + i, "on": True} for i in range(5)], "rev": 5, "puts": 0, "digest": _dg_copy.deepcopy(_DG_DATA)}
        c, pg = _dg_ctx(b, W, "plus", st, errs)
        got = _dg_open_watch(pg, base)
        lock = pg.evaluate("() => (document.getElementById('wdBody') || {}).innerText || ''")
        ok(f"{T}（{W}/Plus）日報顯示「Pro 方案功能」鎖定說明、沒有日報表、鈴鐺沒有日報通知", bool(got) and "Pro 方案功能" in lock and not pg.query_selector("#wdTbl")
           and pg.evaluate("() => { const d = document.getElementById('ntDot'); return !d || d.hidden; }"), lock)
        pg.screenshot(path=f"{_DG_SHOTS}/digest_plus_{W}.png")
        pg.click("#wdCard [data-wdv=rules]")
        wait_until(pg, "() => document.querySelectorAll('#wdCard .wdrule').length === 5", 5000)
        lab = pg.evaluate("() => document.querySelector('#wdCard [data-wdv=rules]').innerText")
        dis = pg.evaluate("() => { const a = document.getElementById('wdAdd'); return a && a.disabled; }")
        msg = pg.evaluate("() => document.getElementById('wdMsg').innerText")
        ok(f"{T}（{W}/Plus）分頁寫「我的提醒 5／5」、「加入提醒」反灰、顯示 5 條上限", "5／5" in lab and dis and "5 條上限" in msg, [lab, dis, msg])
        pg.screenshot(path=f"{_DG_SHOTS}/digest_plus_rules_{W}.png")
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)


register("自選日報提醒1027", lambda pg, b, base, code: t_digest_1027(b, base, code))
