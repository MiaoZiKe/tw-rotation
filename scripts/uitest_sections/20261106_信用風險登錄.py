# 驗收段落「信用風險登錄1106」：#market/credit「全市場信用風險（官方儀表板）」人工登錄（site/margindash.js）
#   · 站主（假的會員 Worker，/v1/me 回 owner:true）：填表 → 格式檢查擋錯（維持率 100～300、戶數整數、金額 ≥ 0）→ 送出 → 數字卡、走勢圖、明細表當場更新
#     → 修改（同一天覆蓋）→ 刪除（點兩下確認）→ 回到種子那兩筆
#   · 訪客：看不到表單與修改／刪除鈕，但看得到資料、資料日期、來源與儀表板連結
#   · 會員 Worker 沒有這支端點（404）：退回讀 margin_dashboard_seed.json；站主存的只留在這台瀏覽器並明寫
#   · 最新登錄比最近交易日舊 → 「最新登錄：MM/DD」標琥珀色，不假裝是今天
#   · 整塊在 #mktBody 裡（mkt.credit 的閘門蓋得到）
# 截圖：TW_MDASH_SHOTS=<資料夾>（1440／390 的站主表單與訪客畫面）
# 由 _uitest.py exec 載入，ok()、wait_until() 直接可用。
# flake8: noqa

MDASH_API = "https://acct-mdash.example.test"
MDASH_SEED_ROWS = [
    {"d": "2026-10-30", "mmr": None, "call_n": 199, "call_amt": None, "disp_n": 21, "disp_amt": None, "note": ""},
    {"d": "2026-11-05", "mmr": 159.77, "call_n": 2352, "call_amt": 26.86, "disp_n": 222, "disp_amt": 6.42, "note": ""},
]


def t_mdash_1106(b, base, code):
    T = "信用風險登錄1106"
    errs = []
    shots = pathlib.Path(os.environ["TW_MDASH_SHOTS"]) if os.environ.get("TW_MDASH_SHOTS") else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    fake_mf = json.dumps(_mf_fake())
    S = {"rows": [dict(r) for r in MDASH_SEED_ROWS], "puts": 0, "dels": 0, "missing": False}
    CORS = {"access-control-allow-origin": "*", "content-type": "application/json"}
    OWNER = {"email": "owner@example.com", "name": "站主", "admin": True, "owner": True}
    FREE = {"email": "free@example.com", "name": "會員", "admin": False}

    def acct(route):
        req = route.request
        path = re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try:
            body = json.loads(req.post_data or "{}")
        except Exception:
            body = {}
        who = {"tok-owner": OWNER, "tok-free": FREE}.get(body.get("t"))
        out, st = {}, 200
        if path == "/v1/me":
            if not who:
                return route.fulfill(status=401, body='{"error":"auth"}', headers=CORS)
            out = {"user": who}
        elif path == "/v1/perm/me":
            out = {"who": "owner" if who is OWNER else "member", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/notices":
            out = {"notices": []}
        elif path.startswith("/v1/mdash/") or path.startswith("/v1/admin/mdash/"):
            if S["missing"]:
                return route.fulfill(status=404, body='{"error":"not_found"}', headers=CORS)
            if path == "/v1/mdash/get":
                out = {"rows": S["rows"], "src": "server"}
            elif not (who and who.get("admin")):
                st, out = 403, {"error": "forbidden"}
            elif path == "/v1/admin/mdash/put":
                row = body.get("row") or {}
                S["rows"] = sorted([r for r in S["rows"] if r["d"] != row.get("d")] + [row], key=lambda r: r["d"])
                S["puts"] += 1
                out = {"ok": True, "rows": S["rows"], "src": "server"}
            elif path == "/v1/admin/mdash/del":
                S["rows"] = [r for r in S["rows"] if r["d"] != body.get("d")]
                S["dels"] += 1
                out = {"ok": True, "rows": S["rows"], "src": "server"}
        route.fulfill(status=st, body=json.dumps(out), headers=CORS)

    def meta_route(route):
        try:
            r = route.fetch(); j = r.json(); j["data_date"] = "2026-11-06"
            route.fulfill(status=200, content_type="application/json", body=json.dumps(j))
        except Exception:
            route.continue_()

    def open_as(who, w, missing=False):
        mob = w <= 640
        S["missing"] = missing
        c = b.new_context(viewport={"width": w, "height": 900 if not mob else 844}, is_mobile=mob, has_touch=mob, timezone_id="Asia/Taipei")
        tok = {"owner": "tok-owner", "free": "tok-free"}.get(who)
        user = {"owner": OWNER, "free": FREE}.get(who)
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + json.dumps({"api": MDASH_API}) + ";"
                          "try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');"
                          + (f"localStorage.setItem('tw.acct.tok','{tok}');localStorage.setItem('tw.acct.user'," + json.dumps(json.dumps(user)) + ");" if tok else "")
                          + "}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route("**/data/market_fut.json*", lambda r: r.fulfill(status=200, content_type="application/json", body=fake_mf))
        c.route("**/data/meta.json*", meta_route)
        c.route(MDASH_API + "/**", acct)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{who}{w}:{e}"))
        pg.goto(base + "#market/credit", wait_until="domcontentloaded")
        wait_until(pg, "() => !!document.querySelector('#mdash .md-tile')", 20000)
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        return c, pg

    tile = "(k) => { const t = document.querySelector(`#mdash .md-tile[data-k=\"${k}\"]`); return t ? { v: t.querySelector('.mf-v').textContent.trim(), ch: t.querySelector('.md-ch').textContent, title: t.title, d: (t.querySelector('.md-d') || {}).textContent } : null; }"
    chart_n = "() => { const el = document.getElementById('mdChart'); const i = el && window.echarts && echarts.getInstanceByDom(el); if (!i) return null; const o = i.getOption(); return { x: o.xAxis[0].data, s: o.series.map(s => s.data.map(v => (v && typeof v === 'object') ? v.value : v)) }; }"
    def fill(pg, vals):
        for k, v in vals.items():
            pg.fill(f"#mdForm input[name='{k}']", str(v))

    # ---------------- 站主：1440 與 390 ----------------
    for w in (1440, 390):
        S["rows"] = [dict(r) for r in MDASH_SEED_ROWS]
        c, pg = open_as("owner", w)
        try:
            ok(f"【{T}】{w} 區塊在 #mktBody 裡（mkt.credit 閘門蓋得到）", pg.evaluate("() => !!document.querySelector('#mktBody #mdash')"))
            t0 = pg.evaluate(tile, "mmr"); t1 = pg.evaluate(tile, "call_n")
            ok(f"【{T}】{w} 讀到會員伺服器的資料：維持率 159.77%、追繳 2,352 戶、較前筆 +2,153（跟 10/30 比）",
               t0 and t0["v"] == "159.77%" and t1 and t1["v"] == "2,352" and "+2,153" in t1["ch"] and pg.get_attribute("#mdash", "data-src") == "server", [t0, t1])
            ok(f"【{T}】{w} 每張卡標資料日期與來源（title 有 2026-11-05、證交所臺股儀表板（人工登錄））、卡上寫 11/05",
               "2026-11-05" in t0["title"] and "證交所臺股儀表板（人工登錄）" in t0["title"] and t0["d"] == "11/05", t0)
            last = pg.evaluate("() => { const e = document.getElementById('mdLast'); return { t: e.textContent, stale: e.classList.contains('stale') }; }")
            ok(f"【{T}】{w} 最近交易日 11/06 還沒登錄 → 寫「最新登錄：11/05」並標琥珀色，不寫今天", last["t"] == "最新登錄：11/05" and last["stale"], last)
            src = pg.evaluate("() => { const a = document.getElementById('mdSrc'); return { h: a.href, t: a.parentElement.textContent }; }")
            ok(f"【{T}】{w} 來源行附儀表板連結", src["h"] == "https://www.twse.com.tw/dashboard/zh/credit/margin.html" and "人工登錄" in src["t"], src)
            ok(f"【{T}】{w} 站主看得到「＋ 登錄數字」，表單預設收起", pg.is_visible("#mdAdd") and not pg.is_visible("#mdForm"))
            pg.click("#mdAdd"); pg.wait_for_selector("#mdForm", state="visible", timeout=4000)
            ok(f"【{T}】{w} 打開表單：資料日期預設最近交易日 2026-11-06", pg.input_value("#mdForm input[name='d']") == "2026-11-06")
            # 格式檢查：送出前就擋，不打伺服器
            p0 = S["puts"]
            for vals, want in (({"mmr": "99", "call_n": "1"}, "100～300"), ({"mmr": "", "call_n": "12.5"}, "整數"), ({"call_n": "", "call_amt": "-1"}, "負數"), ({"call_amt": ""}, "至少要填一個")):
                fill(pg, vals); pg.click("#mdSave"); pg.wait_for_timeout(150)
                m = pg.text_content("#mdMsg") or ""
                ok(f"【{T}】{w} 格式錯誤被擋：{vals} → 「{want}」、欄位標紅、沒送出", want in m and pg.locator("#mdForm .md-f.bad").count() >= 1 and S["puts"] == p0, m)
            if shots:
                pg.locator("#mdash").screenshot(path=str(shots / f"w{w}_owner_error.png"))
            fill(pg, {"mmr": "158.40", "call_n": "2,500", "call_amt": "28.1", "disp_n": "240", "disp_amt": "7", "note": "測試登錄"})
            if shots:
                pg.locator("#mdash").screenshot(path=str(shots / f"w{w}_owner_form.png"))
            ch0 = pg.evaluate(chart_n)
            pg.click("#mdSave")
            wait_until(pg, "() => document.getElementById('mdLast') && document.getElementById('mdLast').textContent === '最新登錄：11/06'", 6000)
            t0 = pg.evaluate(tile, "mmr"); t1 = pg.evaluate(tile, "call_n"); ch1 = pg.evaluate(chart_n)
            ok(f"【{T}】{w} 送出 → 伺服器收到 1 筆、表單收起、數字卡立刻換成 158.40% / 2,500、較前筆 −1.37 pp",
               S["puts"] == p0 + 1 and not pg.is_visible("#mdForm") and t0["v"] == "158.40%" and t1["v"] == "2,500" and "-1.37 pp" in t0["ch"], [t0, t1, S["puts"]])
            ok(f"【{T}】{w} 走勢圖多一天（11/06），三條線都有新值", ch0 and ch1 and len(ch1["x"]) == len(ch0["x"]) + 1 and ch1["x"][-1] == "11/06" and ch1["s"][0][-1] == 2500 and ch1["s"][1][-1] == 240 and ch1["s"][2][-1] == 158.4, [ch0, ch1])
            ok(f"【{T}】{w} 最新登錄＝最近交易日 → 不再標琥珀色；明細表 3 列、有修改／刪除鈕", not pg.evaluate("() => document.getElementById('mdLast').classList.contains('stale')")
               and pg.locator("#mdTbl tr[data-d]").count() == 3 and pg.locator("#mdTbl .md-ed").count() == 3, pg.locator("#mdTbl tr[data-d]").count())
            ok(f"【{T}】{w} 有備註的那天標「註」、滑過看得到備註", "測試登錄" in (pg.get_attribute("#mdTbl tr[data-d='2026-11-06']", "title") or "") and pg.locator("#mdTbl tr[data-d='2026-11-06'] .md-nt").count() == 1)
            # 修改
            if w <= 640 and pg.get_attribute(".md-tblbox", "data-open") == "0":
                pg.click("#mdTgl")
            pg.click("#mdTbl .md-ed[data-d='2026-11-06']"); pg.wait_for_selector("#mdForm", state="visible", timeout=4000)
            ok(f"【{T}】{w} 點「修改」→ 表單帶出那天的值", pg.input_value("#mdForm input[name='mmr']") == "158.4" and pg.input_value("#mdForm input[name='d']") == "2026-11-06" and pg.input_value("#mdForm input[name='note']") == "測試登錄")
            fill(pg, {"call_n": "2600"}); pg.click("#mdSave")
            wait_until(pg, "() => (document.querySelector('#mdash .md-tile[data-k=\"call_n\"] .mf-v') || {}).textContent === '2,600'", 6000)
            ok(f"【{T}】{w} 修改後數字卡變 2,600、仍是 3 筆（同一天覆蓋）", pg.evaluate(tile, "call_n")["v"] == "2,600" and len(S["rows"]) == 3 and pg.locator("#mdTbl tr[data-d]").count() == 3)
            # 刪除：點一下變「確定刪除？」，再點才刪
            if w <= 640 and pg.get_attribute(".md-tblbox", "data-open") == "0":
                pg.click("#mdTgl")
            pg.click("#mdTbl .md-del[data-d='2026-11-06']"); pg.wait_for_timeout(150)
            ok(f"【{T}】{w} 刪除點第一下只變「確定刪除？」不會刪", (pg.text_content("#mdTbl .md-del[data-d='2026-11-06']") or "").startswith("確定刪除") and len(S["rows"]) == 3)
            pg.click("#mdTbl .md-del[data-d='2026-11-06']")
            wait_until(pg, "() => document.getElementById('mdLast').textContent === '最新登錄：11/05'", 6000)
            ok(f"【{T}】{w} 確定後刪掉：回到 11/05、數字卡 159.77%、明細 2 列、走勢圖 2 天",
               S["dels"] >= 1 and pg.evaluate(tile, "mmr")["v"] == "159.77%" and pg.locator("#mdTbl tr[data-d]").count() == 2 and len(pg.evaluate(chart_n)["x"]) == 2)
            # 「?」：定義與口徑
            pg.click("#mdash .howbtn[data-how='mdash']"); pg.wait_for_timeout(250)
            how = pg.evaluate("() => [...document.querySelectorAll('.howbody, .howpop, [role=dialog]')].filter(e => e.offsetParent !== null).map(e => e.textContent).join('|')")
            ok(f"【{T}】{w} 「?」說明追繳（低於 130% 補繳）、處分、口徑上市＋上櫃整戶", "130%" in how and "處分" in how and "上市＋上櫃" in how and "整戶" in how, how[:120])
            pg.mouse.click(5, 5); pg.wait_for_timeout(150)
            sw = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
            ok(f"【{T}】{w} 無橫向捲軸", sw <= 1, sw)
            if shots:
                pg.click("#mdAdd"); pg.wait_for_selector("#mdForm", state="visible", timeout=4000)
                pg.locator("#mdash").scroll_into_view_if_needed(); pg.screenshot(path=str(shots / f"w{w}_owner_page.png"))
                pg.locator("#mdash").screenshot(path=str(shots / f"w{w}_owner.png"))
        except Exception as e:
            ok(f"【{T}】{w} 站主流程不出例外", False, repr(e)[:300])
        finally:
            c.close()

    # ---------------- 訪客與一般會員：看得到資料、看不到表單 ----------------
    for who in ("guest", "free"):
        for w in ((1440, 390) if who == "guest" else (1440,)):
            S["rows"] = [dict(r) for r in MDASH_SEED_ROWS] + [{"d": "2026-11-06", "mmr": 157.1, "call_n": 2700, "call_amt": 30.5, "disp_n": 260, "disp_amt": 8.1, "note": ""}]
            c, pg = open_as(who, w)
            try:
                pg.wait_for_timeout(600)
                ok(f"【{T}】{w} {who} 看不到登錄鈕、表單、修改／刪除", pg.locator("#mdAdd").count() == 0 and pg.locator("#mdForm").count() == 0 and pg.locator("#mdTbl .md-ed, #mdTbl .md-del").count() == 0)
                t0 = pg.evaluate(tile, "mmr")
                ok(f"【{T}】{w} {who} 看得到站主登錄的最新一筆（157.10%、11/06）與來源", t0["v"] == "157.10%" and t0["d"] == "11/06" and "證交所臺股儀表板（人工登錄）" in t0["title"]
                   and pg.text_content("#mdLast") == "最新登錄：11/06" and pg.get_attribute("#mdSrc", "href").startswith("https://www.twse.com.tw/dashboard/"), t0)
                ok(f"【{T}】{w} {who} 較上週：10/30 有登錄 → 追繳戶數較上週 +2,501", "較上週 +2,501" in pg.evaluate(tile, "call_n")["ch"], pg.evaluate(tile, "call_n"))
                if w <= 640:
                    ok(f"【{T}】{w} 手機明細預設收起、點了才展開", not pg.is_visible("#mdTbl") and (pg.click("#mdTgl") or True) and pg.is_visible("#mdTbl"))
                if shots and who == "guest":
                    pg.locator("#mdash").scroll_into_view_if_needed(); pg.screenshot(path=str(shots / f"w{w}_guest_page.png"))
                    pg.locator("#mdash").screenshot(path=str(shots / f"w{w}_guest.png"))
            except Exception as e:
                ok(f"【{T}】{w} {who} 流程不出例外", False, repr(e)[:300])
            finally:
                c.close()

    # ---------------- 會員 Worker 沒有這支端點：退回種子檔；站主存的只在這台瀏覽器 ----------------
    c, pg = open_as("guest", 1440, missing=True)
    try:
        t0 = pg.evaluate(tile, "mmr")
        ok(f"【{T}】端點不存在 → 訪客讀種子檔（159.77%、11/05）", t0["v"] == "159.77%" and pg.get_attribute("#mdash", "data-src") == "file", [t0, pg.get_attribute("#mdash", "data-src")])
    except Exception as e:
        ok(f"【{T}】端點不存在（訪客）不出例外", False, repr(e)[:300])
    finally:
        c.close()
    c, pg = open_as("owner", 1440, missing=True)
    try:
        pg.click("#mdAdd"); pg.wait_for_selector("#mdForm", state="visible", timeout=4000)
        ok(f"【{T}】端點不存在 → 站主表單明寫「其他訪客暫時看不到」", pg.is_visible("#mdWarn") and "其他訪客暫時看不到" in pg.text_content("#mdWarn"))
        fill(pg, {"d": "2026-11-06", "mmr": "160", "call_n": "100"}); pg.click("#mdSave")
        wait_until(pg, "() => document.getElementById('mdLast').textContent === '最新登錄：11/06'", 6000)
        pg.reload(wait_until="domcontentloaded"); wait_until(pg, "() => !!document.querySelector('#mdash .md-tile')", 20000)
        ok(f"【{T}】端點不存在 → 站主存在本機、重新整理還在（data-src=local）", pg.evaluate(tile, "mmr")["v"] == "160.00%" and pg.get_attribute("#mdash", "data-src") == "local")
    except Exception as e:
        ok(f"【{T}】端點不存在（站主）不出例外", False, repr(e)[:300])
    finally:
        c.close()
    ok(f"【{T}】無 pageerror", not errs, errs[:3])


register("信用風險登錄1106", lambda pg, b, base, code: t_mdash_1106(b, base, code))
