# 驗收段落「管理區今日在線與訪客數」（Andy 2026-10-27：「新增 用戶當天使用多久，另外右上角有需要紀錄有多少訪客來過」）
# 這支由 _uitest.py 用 exec 載入：ok()、wait_until()、_pnav_ctx()、to_members() 直接可用。
# 假 Worker：/v1/admin/members 回三位會員的 todayMs（72 分／7 分／0）與 visitors（今日 238、近 30 天 6412）。
# 驗：欄位「今日在線」出現在「累計在線」左邊、格式同累計（1 小時 12 分／7 分／—）、點欄頭排序真的換順序、
# 工具列最右邊有「今日訪客 238／近 30 天 6,412」、Worker 沒給 visitors 時整個藏起來；390 寬不橫向溢出。
import json as _atv_json

_ATV_SHOTS = "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad/admin_today"


def t_admin_today_visitors(b, base, code):
    T = "管理區今日在線與訪客數"
    import os as _os
    _os.makedirs(_ATV_SHOTS, exist_ok=True)
    errs = []
    state = {"visitors": True, "hidden": [], "hide_calls": []}
    mem = [("vip@example.com", "王小明", 72 * 60000, 9 * 3600000), ("lee@example.com", "李大華", 7 * 60000, 3 * 3600000), ("chen@example.com", "陳一", 0, 30 * 60000)]

    def members_route(route):
        if route.request.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        out = {"now": 1761550000000, "hidden": list(state["hidden"]), "members": [
            {"email": e, "name": n, "plan": "free", "planName": "免費會員", "tier": "free", "paid": False, "expires": 0, "expired": False, "set": False,
             "created": 1759000000000, "seen": 1761549000000, "st": "ok", "onlineMs": tot, "todayMs": td, "online30": tot, "visits30": 5, "days30": 3,
             "views30": 20, "topFeat": [], "topStock": [], "hidden": e in state["hidden"]} for e, n, td, tot in mem]}
        if state["visitors"]:
            out["visitors"] = {"today": 238, "d30": 6412, "days": 30, "since": "2026-09-28"}
        route.fulfill(status=200, body=_atv_json.dumps(out), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    def hide_route(route):
        if route.request.method == "OPTIONS":
            return route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "POST"})
        b_ = _atv_json.loads(route.request.post_data or "{}")
        state["hide_calls"].append(b_)
        em = str(b_.get("email", "")).lower()
        state["hidden"] = [x for x in state["hidden"] if x != em] + ([em] if b_.get("hide") else [])
        route.fulfill(status=200, body=_atv_json.dumps({"ok": True, "hidden": state["hidden"]}), headers={"access-control-allow-origin": "*", "content-type": "application/json"})

    for W in (1440, 390):
        c, _sent = _pnav_ctx(b, True, width=W)
        c.route(PNAV_API + "/v1/admin/members", members_route)
        c.route(PNAV_API + "/v1/admin/members/hide", hide_route)
        pg = c.new_page(); pg.on("pageerror", lambda e, W=W: errs.append(f"{W}: {e}"))
        pg.goto(base + "#admin/perm", wait_until="domcontentloaded")
        a = pg.get_by_role("button", name="同意並繼續")
        if a.count() and a.first.is_visible():
            a.first.click(); pg.wait_for_timeout(300)
        to_members(pg)
        wait_until(pg, "() => document.querySelectorAll('#ptTable tr[data-email]').length === 3", 6000)
        vis = pg.evaluate("() => { const e = document.getElementById('pmVis'); return e && !e.hidden ? e.textContent.replace(/\\s+/g, ' ') : ''; }")
        ok(f"{T}（{W}）工具列有訪客數：今日訪客 238" + ("、近 30 天 6,412" if W > 640 else "（手機只留今日）"),
           "今日訪客 238" in vis and (W <= 640 or "近 30 天 6,412" in vis), vis)
        if W > 640:
            hdr = pg.evaluate("() => [...document.querySelectorAll('#ptTable th')].map(t => t.textContent.trim().replace(/[ ▲▼]+$/, ''))")
            i = hdr.index("今日在線") if "今日在線" in hdr else -1
            ok(f"{T}（{W}）欄位「今日在線」出現在「累計在線」左邊", i >= 0 and hdr[i + 1] == "累計在線", hdr)
            cells = pg.evaluate("() => [...document.querySelectorAll('#ptTable tr[data-email]')].map(r => [r.dataset.email, r.querySelector('.c-tdon').textContent.trim()])")
            d = dict(cells)
            ok(f"{T}（{W}）格式同累計在線：72 分＝「1 小時 12 分」、7 分＝「7 分」、0＝「—」",
               d.get("vip@example.com") == "1 小時 12 分" and d.get("lee@example.com") == "7 分" and d.get("chen@example.com") == "—", d)
            first = lambda: pg.evaluate("() => document.querySelector('#ptTable tr[data-email]').dataset.email")
            pg.click("#ptTable th[data-sort='today']")
            o1 = pg.evaluate("() => [...document.querySelectorAll('#ptTable tr[data-email]')].map(r => r.dataset.email).join()")
            pg.click("#ptTable th[data-sort='today']")
            o2 = pg.evaluate("() => [...document.querySelectorAll('#ptTable tr[data-email]')].map(r => r.dataset.email).join()")
            ok(f"{T}（{W}）點「今日在線」欄頭排序：兩次點擊順序相反，且依今日分鐘數（72／7／0）排",
               o1 != o2 and {o1, o2} == {"chen@example.com,lee@example.com,vip@example.com", "vip@example.com,lee@example.com,chen@example.com"}, (o1, o2))
            r = pg.evaluate("""() => { const t = document.getElementById('ptTable').getBoundingClientRect(), v = document.getElementById('pmVis').getBoundingClientRect(), s = document.getElementById('pmStatF').getBoundingClientRect();
                return { visRight: Math.round(v.right), tblRight: Math.round(t.right), afterFilter: v.left >= s.right - 1 }; }""")
            ok(f"{T}（{W}）訪客數在搜尋列最右邊（在狀態下拉右側、右緣對齊表格）", r["afterFilter"] and abs(r["visRight"] - r["tblRight"]) <= 24, r)
            pg.screenshot(path=f"{_ATV_SHOTS}/members_{W}.png", clip={"x": 0, "y": 0, "width": W, "height": 900})
            # ---- 隱藏帳號（Andy 10-27：「有幾個帳戶是我自己的帳號」）
            rows_n = lambda: pg.evaluate("() => document.querySelectorAll('#ptTable tr[data-email]').length")
            cnt = lambda: pg.inner_text("#pmCnt").strip()
            ok(f"{T}（{W}）隱藏前：3 列、共 3 位、沒有「顯示已隱藏」鈕、每列有眼睛（24px 點擊區、16px 圖示）",
               rows_n() == 3 and cnt() == "共 3 位" and pg.evaluate("() => document.getElementById('pmHidTg').hidden") and
               pg.evaluate("() => [...document.querySelectorAll('#ptTable .hideye')].every(e => { const r = e.getBoundingClientRect(), s = e.querySelector('svg').getBoundingClientRect(); return Math.round(r.width) === 24 && Math.round(s.width) === 16; }) && document.querySelectorAll('#ptTable .hideye').length === 3"))
            pg.click("#ptTable .hideye[data-hide='chen@example.com']")
            wait_until(pg, "() => document.querySelectorAll('#ptTable tr[data-email]').length === 2", 4000)
            ok(f"{T}（{W}）點眼睛 → 該列消失、不展開、共 3 位 → 共 2 位、伺服器收到 hide=true、出現「顯示已隱藏（1）」",
               rows_n() == 2 and cnt() == "共 2 位" and pg.evaluate("() => !document.querySelector('#ptTable tr.pmdet')") and state["hide_calls"][-1] == {"email": "chen@example.com", "hide": True, "t": state["hide_calls"][-1].get("t")}
               and "顯示已隱藏（1）" in pg.inner_text("#pmHidTg"), (state["hide_calls"], cnt(), pg.inner_text("#pmHidTg")))
            pg.screenshot(path=f"{_ATV_SHOTS}/members_{W}_hidden_off.png", clip={"x": 0, "y": 0, "width": W, "height": 900})
            pg.click("#pmHidTg")
            wait_until(pg, "() => document.querySelectorAll('#ptTable tr[data-email]').length === 3", 4000)
            st_ = pg.evaluate("() => { const r = document.querySelector('#ptTable tr.hid'); return r ? { email: r.dataset.email, op: getComputedStyle(r.querySelector('td.c-vis')).opacity, eye: r.querySelector('.hideye').classList.contains('off'), last: r === [...document.querySelectorAll('#ptTable tr[data-email]')].pop() } : null; }")
            ok(f"{T}（{W}）打開「顯示已隱藏」→ 3 列、已隱藏那列半透明＋斜線眼睛＋排最後、共 N 位仍是 2",
               bool(st_) and st_["email"] == "chen@example.com" and float(st_["op"]) < 0.7 and st_["eye"] and st_["last"] and cnt() == "共 2 位" and pg.get_attribute("#pmHidTg", "aria-pressed") == "true", (st_, cnt()))
            pg.screenshot(path=f"{_ATV_SHOTS}/members_{W}_hidden_on.png", clip={"x": 0, "y": 0, "width": W, "height": 900})
            pg.click("#ptTable .hideye[data-hide='chen@example.com']")
            wait_until(pg, "() => document.querySelectorAll('#ptTable tr.hid').length === 0", 4000)
            ok(f"{T}（{W}）再點斜線眼睛 → 取消隱藏：3 列回到一般、共 3 位、伺服器收到 hide=false",
               rows_n() == 3 and cnt() == "共 3 位" and state["hide_calls"][-1].get("hide") is False and pg.evaluate("() => document.querySelectorAll('#ptTable tr.hid').length") == 0,
               (rows_n(), cnt(), state["hide_calls"][-1]))
            pg.click("#pmHidTg") if pg.evaluate("() => !document.getElementById('pmHidTg').hidden") else None
            # Worker 還沒更新（沒給 visitors）→ 不顯示假的 0
            state["visitors"] = False
            pg.evaluate("() => { location.hash = '#overview'; }"); pg.wait_for_timeout(300)
            pg.evaluate("() => { location.hash = '#admin/perm'; }")
            wait_until(pg, "() => !!document.getElementById('pmCnt')", 6000)
            pg.reload(wait_until="domcontentloaded")
            to_members(pg)
            wait_until(pg, "() => document.querySelectorAll('#ptTable tr[data-email]').length === 3", 6000)
            ok(f"{T}（{W}）Worker 沒回 visitors（舊版）→ 訪客數整個藏起來、不顯示假的 0", pg.evaluate("() => { const e = document.getElementById('pmVis'); return !e || e.hidden || !e.textContent.trim(); }"))
            state["visitors"] = True
        else:
            ov = pg.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            ok(f"{T}（{W}）手機沒有橫向捲軸", ov <= 1, ov)
            pg.screenshot(path=f"{_ATV_SHOTS}/members_{W}.png")
        c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs)


register("管理區今日在線與訪客數", lambda pg, b, base, code: t_admin_today_visitors(b, base, code))
