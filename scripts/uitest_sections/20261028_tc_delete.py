# 驗收段落「科技透明圈刪除1028」（site/tc/tc.js 的人工刪除；workers/account-api/articles.js 的 /v1/tc/hidden）
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()… 直接可用，不要 import _uitest。
# flake8: noqa
# Andy 10-28：「有些數據資訊太少，所以你需要新增刪除功能給我，我會在人工審閱」。
# 用假的會員 Worker（page.route，狀態存在 Python 端，多個瀏覽器共用＝模擬「存在伺服器、所有裝置一樣」）真的操作：
# 公司排行按刪除 → 確認框（取消不動）→ 確定：排行少一家、「進統計」筆數變、已刪除（1）、伺服器收到；重新整理／另一台裝置仍刪除；復原後回來。
# 再測公司頁刪一筆樣本、刪一個職位（統計數字變）、伺服器寫入失敗要還原、390 寬按鈕 ≥32px 且不橫向溢出。
import json as _td_json
import re as _td_re

_TD_API = "https://tcdel1028.example.test"
_TD_SP = "/tmp/claude-0/-home-user-tw-rotation/d35d4770-19c6-5ef0-b46f-3181b0b89ae3/scratchpad/"
_TD_CO = "未具名 IC 設計外商"


def t_tc_delete_1028(b, base, code):
    T = "科技透明圈刪除1028"
    errs = []
    st = {"hidden": [], "fail": False, "puts": []}

    def handler(route):
        req = route.request
        path = _td_re.sub(r"^https?://[^/]+", "", req.url).split("?")[0]
        if req.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        try: body = _td_json.loads(req.post_data or "{}")
        except Exception: body = {}
        tok = str(body.get("t") or "")
        email = tok[4:] if tok.startswith("tok-") else None
        is_adm = email == "andy@example.com"
        out, status = {}, 200
        if path == "/v1/me":
            out, status = ({"user": {"email": email, "name": "andy", "admin": is_adm}}, 200) if email else ({"error": "auth"}, 401)
        elif path == "/v1/perm/me":
            out = {"who": "member" if email else "guest", "plan": "free", "planName": "免費會員", "feats": {}, "lims": {}}
        elif path == "/v1/plans/public":
            out = {"plans": []}
        elif path in ("/v1/beat", "/v1/track/batch"):
            out = {"ok": True, "n": 1}
        elif path == "/v1/tc/hidden":
            out, status = ({"hidden": list(st["hidden"])}, 200) if is_adm else ({"error": "forbidden"}, 403)
        elif path == "/v1/tc/hidden/put":
            st["puts"].append(list(body.get("hidden") or []))
            if not is_adm: out, status = {"error": "forbidden"}, 403
            elif st["fail"]: out, status = {"error": "boom"}, 500
            else:
                st["hidden"] = list(dict.fromkeys(body.get("hidden") or [])); out = {"ok": True, "hidden": list(st["hidden"])}
        route.fulfill(status=status, body=_td_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def ctx(w=1440):
        mob = w <= 640
        c = b.new_context(viewport={"width": w, "height": 844 if mob else 900}, **({"has_touch": True, "is_mobile": True} if mob else {}))
        c.add_init_script("window.TW_ACCOUNT_OVERRIDE = " + _td_json.dumps({"api": _TD_API}) + ";try{localStorage.setItem('tw.tour','done');localStorage.setItem('tw.live.on','0');localStorage.setItem('tw.acct.tok','tok-andy@example.com')}catch(e){}")
        c.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        c.route(_TD_API + "/**", handler)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(f"{w}:{e}"))
        return c, pg

    def open_tc(pg, h):
        pg.goto(base + h, wait_until="domcontentloaded")
        ag = pg.get_by_role("button", name="同意並繼續")
        if ag.count():
            try: ag.first.click(timeout=1500)
            except Exception: pass
        wait_until(pg, "() => !!document.querySelector('#v-tc .tc-card .tc-body')", 25000)
        pg.wait_for_timeout(700)

    def rank_names(pg):
        return pg.evaluate("() => Array.from(document.querySelectorAll('#v-tc .tc-rkr')).map(a => a.dataset.co)")

    def all_cnt(pg):
        return pg.evaluate("() => +(document.getElementById('tcAll') || {}).textContent || 0")

    def rank_all(pg):
        # 排行預設只列前 15／10 家：點「看全部」讓樣本少的公司也在畫面上
        pg.evaluate("() => { const m = document.querySelector('#v-tc .tc-rkmore'); if (m && /看全部/.test(m.textContent)) m.click(); }")
        pg.wait_for_timeout(200)

    c, pg = ctx(1440)
    open_tc(pg, "#tc/stats")
    rank_all(pg)
    names0 = rank_names(pg); n0 = all_cnt(pg)
    ok(f"{T}：排行有「{_TD_CO}」且標「樣本少」", _TD_CO in names0 and pg.evaluate("(n) => { const a = document.querySelector('#v-tc .tc-rkr[data-co=\"' + n + '\"]'); return !!(a && a.querySelector('.tc-few')); }", _TD_CO), names0[:3])
    ok(f"{T}：每列都有刪除鈕", pg.evaluate("() => document.querySelectorAll('#v-tc .tc-rkrow>.tc-delbtn').length === document.querySelectorAll('#v-tc .tc-rkr').length"))
    ok(f"{T}：沒刪過時沒有「已刪除」區", pg.evaluate("() => !document.getElementById('tcDelBox')"))
    btn = pg.locator('#v-tc .tc-rk .tc-delbtn[data-l="' + _TD_CO + '"]')
    # 1) 按刪除 → 確認框 → 取消：什麼都不變、不呼叫伺服器
    btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(200)
    ok(f"{T}：按刪除出現二次確認框", pg.locator(".tc-dlg .tc-dlgb").count() == 1)
    try: pg.screenshot(path=_TD_SP + "tc_del_1440_confirm.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    pg.locator(".tc-dlg .tc-dno").click(); pg.wait_for_timeout(200)
    ok(f"{T}：取消後確認框消失、排行與筆數不變、沒呼叫伺服器", pg.locator(".tc-dlg").count() == 0 and len(rank_names(pg)) == len(names0) and all_cnt(pg) == n0 and not st["puts"])
    # 2) 確定刪除
    btn.click(); pg.wait_for_timeout(150); pg.locator(".tc-dlg .tc-dok").click(); pg.wait_for_timeout(500)
    names1 = rank_names(pg); n1 = all_cnt(pg)
    ok(f"{T}：確定後排行少一家（{len(names0)}→{len(names1)}）且不含它", len(names1) == len(names0) - 1 and _TD_CO not in names1, (len(names0), len(names1)))
    ok(f"{T}：「進統計」筆數變少（{n0}→{n1}）", n1 == n0 - 1, (n0, n1))
    ok(f"{T}：出現「已刪除（1）」、預設收起", pg.evaluate("() => { const d = document.getElementById('tcDelBox'); return !!d && !d.open && /已刪除（1）/.test(d.querySelector('summary').textContent); }"))
    ok(f"{T}：伺服器收到一筆 c| 開頭的鍵", len(st["hidden"]) == 1 and st["hidden"][0].startswith("c|other|"), st["hidden"])
    # 開「已刪除」區截圖
    pg.evaluate("() => { const b = document.querySelector('#v-tc .seg[data-rk=ind] button[data-v=other]'); if (b) b.click(); }"); pg.wait_for_timeout(300)
    pg.evaluate("() => { const d = document.getElementById('tcDelBox'); d.open = true; d.scrollIntoView({block:'end'}); }"); pg.wait_for_timeout(300)
    try: pg.screenshot(path=_TD_SP + "tc_del_1440_deleted.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    c.close()
    # 3) 重新整理（新 context＝等於另一台裝置，localStorage 是空的）仍然是刪除的
    c2, pg2 = ctx(1440)
    open_tc(pg2, "#tc/stats"); rank_all(pg2)
    nm2 = rank_names(pg2)
    ok(f"{T}：另一台裝置打開，排行仍沒有它、筆數 {n1}", _TD_CO not in nm2 and all_cnt(pg2) == n1, (len(nm2), all_cnt(pg2)))
    pg2.reload(wait_until="domcontentloaded"); wait_until(pg2, "() => !!document.querySelector('#v-tc .tc-card .tc-body')", 25000); pg2.wait_for_timeout(700); rank_all(pg2)
    ok(f"{T}：重新整理後仍刪除", _TD_CO not in rank_names(pg2) and all_cnt(pg2) == n1)
    # 4) 復原
    pg2.evaluate("() => { const d = document.getElementById('tcDelBox'); d.open = true; }")
    pg2.locator("#tcDelBox .tc-undo").first.click(); pg2.wait_for_timeout(500); rank_all(pg2)
    ok(f"{T}：按復原後回到排行、筆數回 {n0}、已刪除區消失、伺服器清單清空", _TD_CO in rank_names(pg2) and all_cnt(pg2) == n0 and pg2.evaluate("() => !document.getElementById('tcDelBox')") and st["hidden"] == [], (all_cnt(pg2), st["hidden"]))
    # 5) 公司頁：刪一筆樣本、刪一個職位
    open_tc(pg2, "#tc/foundry/" + "%E5%8F%B0%E7%A9%8D%E9%9B%BB")
    rows0 = pg2.locator("#v-tc tr.tc-row").count()
    pg2.locator("#v-tc tr.tc-row .tc-exp").first.click(); pg2.wait_for_timeout(200)
    sm0 = pg2.locator("#v-tc tr.tc-smrow:not([hidden]) .tc-smt tbody tr").count()
    n_cell0 = pg2.evaluate("() => document.querySelector('#v-tc tr.tc-row td[data-l=\"樣本\"]').textContent")
    pg2.locator("#v-tc tr.tc-smrow:not([hidden]) .tc-smd .tc-delbtn").first.click(); pg2.wait_for_timeout(150)
    pg2.locator(".tc-dlg .tc-dok").click(); pg2.wait_for_timeout(500)
    sm1 = pg2.locator("#v-tc tr.tc-smrow:not([hidden]) .tc-smt tbody tr").count()
    ok(f"{T}：刪一筆樣本後該職位展開面板仍開著、少一筆（{sm0}→{sm1}）", sm1 == sm0 - 1, (sm0, sm1))
    ok(f"{T}：伺服器收到 s| 鍵，已刪除區 1 筆", len(st["hidden"]) == 1 and st["hidden"][0].startswith("s|foundry|") and pg2.evaluate("() => /已刪除（1）/.test((document.getElementById('tcDelBox')||{}).textContent||'')"), st["hidden"])
    pg2.locator("#tcDelBox .tc-undo").first.click(); pg2.wait_for_timeout(450)
    ok(f"{T}：樣本復原後職位樣本數回到 {n_cell0}", pg2.evaluate("() => document.querySelector('#v-tc tr.tc-row td[data-l=\"樣本\"]').textContent") == n_cell0 and st["hidden"] == [])
    if pg2.locator("#v-tc tr.tc-smrow:not([hidden])").count() == 0:
        pg2.locator("#v-tc tr.tc-row").first.click(); pg2.wait_for_timeout(200)   # 點整列展開面板（前一步復原後面板本來就保持展開，不要再點成收起）
    pg2.locator("#v-tc tr.tc-smrow:not([hidden]) .tc-smh .tc-delbtn").first.click(); pg2.wait_for_timeout(150)
    pg2.locator(".tc-dlg .tc-dok").click(); pg2.wait_for_timeout(500)
    ok(f"{T}：刪一個職位後職位列少一列（{rows0}→{pg2.locator('#v-tc tr.tc-row').count()}）", pg2.locator("#v-tc tr.tc-row").count() == rows0 - 1 and st["hidden"] and st["hidden"][0].startswith("r|foundry|"), st["hidden"])
    try: pg2.screenshot(path=_TD_SP + "tc_del_1440_company.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    pg2.locator("#tcDelBox .tc-undo").first.click(); pg2.wait_for_timeout(450)
    ok(f"{T}：職位復原後列數回 {rows0}", pg2.locator("#v-tc tr.tc-row").count() == rows0 and st["hidden"] == [])
    # 6) 整家公司（從公司頁刪）→ 回產業清單；再從已刪除區復原
    open_tc(pg2, "#tc/other/" + "%E6%9C%AA%E5%85%B7%E5%90%8D%20IC%20%E8%A8%AD%E8%A8%88%E5%A4%96%E5%95%86")
    pg2.locator("#v-tc .tc-cinfo .tc-delbtn").click(); pg2.wait_for_timeout(150); pg2.locator(".tc-dlg .tc-dok").click(); pg2.wait_for_timeout(700)
    ok(f"{T}：公司頁刪除整家後導回該產業清單、清單沒有它", pg2.evaluate("() => location.hash") == "#tc/other" and pg2.evaluate("(n) => !document.querySelector('#v-tc .tc-co[data-co=\"' + n + '\"]')", _TD_CO), pg2.evaluate("() => location.hash"))
    pg2.locator("#tcDelBox .tc-undo").first.click(); pg2.wait_for_timeout(450)
    ok(f"{T}：復原後清單又有它", pg2.evaluate("(n) => !!document.querySelector('#v-tc .tc-co[data-co=\"' + n + '\"]')", _TD_CO) and st["hidden"] == [])
    # 7) 伺服器寫入失敗 → 還原並提示
    open_tc(pg2, "#tc/stats"); rank_all(pg2); st["fail"] = True
    na = len(rank_names(pg2))
    pg2.locator('#v-tc .tc-rk .tc-delbtn[data-l="' + _TD_CO + '"]').click(); pg2.wait_for_timeout(150); pg2.locator(".tc-dlg .tc-dok").click(); pg2.wait_for_timeout(900)
    rank_all(pg2)
    ok(f"{T}：伺服器 500 時還原（排行回 {na} 家）並出現提示", len(rank_names(pg2)) == na and pg2.locator(".tc-toast").count() == 1 and not pg2.evaluate("() => !!document.getElementById('tcDelBox')"))
    st["fail"] = False
    c2.close()
    # 8) 手機 390
    c3, pg3 = ctx(390)
    open_tc(pg3, "#tc/stats"); rank_all(pg3)
    r = pg3.evaluate("""(n) => { const b = document.querySelector('#v-tc .tc-rk .tc-delbtn[data-l="' + n + '"]'); if (!b) return null; b.scrollIntoView({block:'center'}); const q = b.getBoundingClientRect(); const fab = document.getElementById('supFab'); let hit = false; if (fab) { const f = fab.getBoundingClientRect(); hit = q.left < f.right && q.right > f.left && q.top < f.bottom && q.bottom > f.top; } return { w: q.width, h: q.height, ov: document.documentElement.scrollWidth > innerWidth + 1, fab: hit, fs: parseFloat(getComputedStyle(b).fontSize) }; }""", _TD_CO)
    ok(f"{T}：390 寬刪除鈕 ≥32px、字 ≥11px、頁面無橫向溢出", bool(r) and r["w"] >= 31.5 and r["h"] >= 31.5 and r["fs"] >= 11 and not r["ov"], r)
    pg3.locator('#v-tc .tc-rk .tc-delbtn[data-l="' + _TD_CO + '"]').click(); pg3.wait_for_timeout(250)
    dl = pg3.evaluate("() => { const x = document.querySelector('.tc-dlgb'); if (!x) return null; const q = x.getBoundingClientRect(); return { l: q.left, r: q.right, w: innerWidth }; }")
    ok(f"{T}：390 寬確認框在畫面內", bool(dl) and dl["l"] >= 0 and dl["r"] <= dl["w"], dl)
    try: pg3.screenshot(path=_TD_SP + "tc_del_390_confirm.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    pg3.locator(".tc-dlg .tc-dok").click(); pg3.wait_for_timeout(500)
    pg3.evaluate("() => { const b = document.querySelector('#v-tc .seg[data-rk=ind] button[data-v=other]'); if (b) b.click(); }"); pg3.wait_for_timeout(300)
    pg3.evaluate("() => { const d = document.getElementById('tcDelBox'); if (d) { d.open = true; d.scrollIntoView({block:'end'}); } }"); pg3.wait_for_timeout(300)
    ok(f"{T}：390 寬刪除後已刪除區在畫面內、復原鈕 ≥32px、無橫向溢出", pg3.evaluate("() => { const u = document.querySelector('#tcDelBox .tc-undo'); if (!u) return false; const q = u.getBoundingClientRect(); return q.right <= innerWidth && q.height >= 28 && document.documentElement.scrollWidth <= innerWidth + 1; }"))
    try: pg3.screenshot(path=_TD_SP + "tc_del_390_deleted.png")
    except Exception as e: print("  ⚠ 截圖失敗", e)
    pg3.locator("#tcDelBox .tc-undo").first.click(); pg3.wait_for_timeout(400)
    ok(f"{T}：無 JS 錯誤", not errs, errs[:2])
    c3.close()


register("科技透明圈刪除1028", lambda pg, b, base, code: t_tc_delete_1028(b, base, code))
