# 驗收段落「大戶散戶買賣1107」
# 這支由 _uitest.py 用 exec 載入它自己的全域命名空間：ok()、wait_until()、_sub_ctx() 直接可用，不要 import _uitest。
# ⚠ 全域名稱一律用 _BS1107_ 開頭（所有段落 exec 進同一個命名空間）。
# Andy 2026-11-07：「個股可以看到 大戶 散戶 當前買賣狀況，即時的資訊 以及 日K級別資訊 這功能記得也要顯在權限內 但暫不開放」。
# 真的操作：
#   1. 功能鍵：stock.bigsmall 登記（個股頁分頁、def false）、四個方案範本都 false、在「編輯：新會員體驗」可選清單；
#      stock.bigsmall.live 是 adminOnly＋ownerOnly（不在體驗清單、不進訂閱頁權益表）；站主打開 #admin/perm 看得到這兩個開關
#   2. 站主 1440：大戶／散戶分頁集保圖下面有 #bsCard、沒鎖；「今日即時」每 5 秒真的打 /quote、KPI 數字與走勢線真的跟著變、
#      切「日 K」→ 大單／小單柱子＋日 K 對照、期間鈕 20→60 真的改變點數（資料不足的反灰有 title）；「?」說明寫明推估與門檻
#   3. 一般會員、訪客（桌機＋手機）：看不到（整張卡不畫、手機沒有分段）、不抓 data/bigsmall、不打即時、計時器沒開
#   4. 手機 390 站主：「大戶／散戶」分頁的「買賣推估」分段畫出 #bsCard、沒有橫向捲軸
#   截圖（TW_BS_SHOTS＝資料夾）：1440 站主即時、1440 站主日 K、390 站主、1440 一般會員看不到。站主畫面的數字是假資料（畫面上標「示意資料（非真實）」）。
import json as _bs1107_json
import os as _bs1107_os
from urllib.parse import parse_qs as _bs1107_qs, urlparse as _bs1107_up

_BS1107_CODE = "2330"


def _bs1107_daily(n=30):
    """假的日資料（標 sample，畫面會寫「示意資料（非真實）」）：最後 n 個平日。"""
    import datetime as _d
    days, d = [], _d.date(2026, 11, 6)
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d -= _d.timedelta(days=1)
    days.reverse()
    rows = []
    for i, x in enumerate(days):
        bn = round(((i * 37) % 23 - 11) * 120.0, 1); sn = round(-bn * 0.6 + ((i * 13) % 7 - 3) * 40, 1)
        rows.append([x, bn, sn, int(bn * 1000 * 1400), int(sn * 1000 * 1400), 0.18 + (i % 5) / 50, 1200.0, 30000.0, 20000000])
    return {"cols": ["date", "big_net", "small_net", "big_net_amt", "small_net_amt", "coverage", "pre", "observed", "threshold"],
            "days": rows, "thr": 20000000, "sample": True}


def _bs1107_ctx(b, who, owner=False, width=1440, touch=False):
    c, sent, st = _sub_ctx(b, who, owner=owner, width=width, touch=touch)
    S = {"q": 0, "daily": 0, "quote": 0}
    if not owner:      # 一般會員／訪客＝正式站的樣子：沒有即時後門（全站預設注入的 TW_LIVE_OVERRIDE 是管理者視角）
        c.add_init_script("window.TW_LIVE_OVERRIDE = false;")
    c.add_init_script("window.TW_BS_FORCE_OPEN = true; window.TW_BS_SAMPLE = true; try { localStorage.setItem('tw.theme','light'); localStorage.removeItem('tw.bs.live.2330'); localStorage.setItem('tw.bs.mode','live'); localStorage.setItem('tw.bs.win','20'); } catch (e) {}")

    def daily(route):
        S["daily"] += 1
        u = route.request.url
        if u.split("?")[0].endswith("/_thr.json"):
            return route.fulfill(status=200, content_type="application/json", body=_bs1107_json.dumps({"floor": 1000000, "mult": 4, "thr": {_BS1107_CODE: 20000000}}))
        if ("/" + _BS1107_CODE + ".json") in u:
            return route.fulfill(status=200, content_type="application/json", body=_bs1107_json.dumps(_bs1107_daily()))
        route.fulfill(status=404, body="")

    def quote(route):
        p = _bs1107_up(route.request.url)
        ex = (_bs1107_qs(p.query).get("ex_ch") or [""])[0]
        if ("_" + _BS1107_CODE + ".") not in ex or "|" in ex:      # 別的模組的報價：照一般形狀回（不干擾）
            return route.fallback()
        S["quote"] += 1
        k = S["quote"]
        # 一買一賣交替、單量大小交替；價在 1400 附近（大單門檻 2000 萬＝14.3 張以上）
        z = 1400 + (5 if k % 2 else -5)
        tv = 40 if k % 3 == 0 else 3
        v = 20000 + k * 25
        m = {"c": _BS1107_CODE, "n": "台積電", "ex": "tse", "d": "20261109", "t": "10:%02d:%02d" % (10 + k // 12, (k * 5) % 60),
             "z": f"{z:.4f}", "tv": str(tv), "v": str(v), "y": "1395.0000", "o": "1398.0000", "h": "1410.0000", "l": "1390.0000",
             "a": f"{1400 + 5:.4f}_{1410:.4f}_", "b": f"{1400 - 5:.4f}_{1390:.4f}_"}
        route.fulfill(status=200, content_type="application/json", body=_bs1107_json.dumps({"rtcode": "0000", "msgArray": [m]}))

    c.route("**/data/bigsmall/**", daily)
    c.route("**/quote?*", quote)
    return c, S


def _bs1107_open(pg, base, mobile=False):
    pg.goto(base + "#stock/" + _BS1107_CODE, wait_until="domcontentloaded")
    ag = pg.get_by_role("button", name="同意並繼續")
    pg.wait_for_timeout(500)
    if ag.count() and ag.first.is_visible():
        ag.first.click(); pg.wait_for_timeout(300)
    if mobile:
        wait_until(pg, "() => !!document.querySelector('#mbTabs button[data-t=\"big\"]') && !!window.TwBigSmall", 40000)
        pg.locator('#mbTabs button[data-t="big"]').first.click()
        wait_until(pg, "() => !!document.querySelector('#mbBody .mbseg button[data-s=\"bs\"]')", 10000)
        pg.locator('#mbBody .mbseg button[data-s="bs"]').first.click()
    else:
        wait_until(pg, "() => !!document.querySelector('#stockTabs button[data-t=\"holders\"]') && !!window.TwBigSmall", 40000)
        pg.locator('#stockTabs button[data-t="holders"]').first.click()
    return wait_until(pg, "() => !!document.querySelector('#bsCard')", 10000)


_BS1107_ST = "() => Object.assign(TwBigSmall.state(), { plk: (document.querySelector('#bsCard') || {}).getAttribute ? document.querySelector('#bsCard').getAttribute('data-plk') : null, kpi: (document.querySelector('#bsKpi') || {}).innerText || '', note: (document.querySelector('#bsCard .bsnote') || {}).innerText || '', sw: document.documentElement.scrollWidth, vw: innerWidth })"


def t_bigsmall_1107(b, base, code):
    T = "大戶散戶買賣1107"
    errs: list = []
    shots = _bs1107_os.environ.get("TW_BS_SHOTS")

    # ---------------------------------------------------------------- 1. 功能鍵與權限編輯器
    c, S = _bs1107_ctx(b, "admin", owner=True)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "#overview", wait_until="domcontentloaded")
    wait_until(pg, "() => !!window.TwFeatures && !!window.TW_PLAN_PRESETS", 30000)
    r = pg.evaluate("""() => { const F = TwFeatures, P = TW_PLAN_PRESETS, f = F.byId('stock.bigsmall'), g = F.byId('stock.bigsmall.live');
        const tier = (t) => P.tiers.find(x => x.key === t);
        const BAN = ['live.tick', 'stock.k_min'];
        const ed = F.list.filter(x => x.kind === 'bool' && !x.adminOnly && x.cat !== 'grp' && !BAN.includes(x.id)).map(x => x.id);
        return { f: f ? [f.kind, f.cat, f.def, (f.veil || []).map(v => v[0]).join(',')] : null, g: g ? [!!g.adminOnly, !!g.ownerOnly] : null,
          feats: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats['stock.bigsmall']), live: ['guest', 'free', 'plus', 'pro'].map(t => tier(t).feats['stock.bigsmall.live']),
          lims: ['guest', 'free', 'plus', 'pro'].map(t => (tier(t).lims || {})['stock.bigsmall'] == null ? null : tier(t).lims['stock.bigsmall']),
          inEd: ed.includes('stock.bigsmall'), liveInEd: ed.includes('stock.bigsmall.live') }; }""")
    ok(f"{T} 功能鍵 stock.bigsmall 登記（bool、個股頁分頁、def false、蓋 #bsCard）；四個方案範本都 false（暫不開放）、沒有預設次數",
       r["f"] == ["bool", "stocktab", False, "#bsCard"] and r["feats"] == [False] * 4 and r["lims"] == [None] * 4, r)
    ok(f"{T} stock.bigsmall 在「編輯：新會員體驗」可選清單（不在 GRANT_BAN、體驗不預設）；即時鍵 stock.bigsmall.live 是 adminOnly＋ownerOnly、四方案 false、不在體驗清單",
       r["inEd"] and r["g"] == [True, True] and r["live"] == [False] * 4 and not r["liveInEd"], r)
    pg.goto(base + "#admin/perm", wait_until="domcontentloaded")
    has = wait_until(pg, "() => !!document.querySelector('input[data-f=\"stock.bigsmall\"]')", 20000)
    pe = pg.evaluate("() => { const a = document.querySelector('input[data-f=\"stock.bigsmall\"]'), b = document.querySelector('input[data-f=\"stock.bigsmall.live\"]'); return { a: !!a, b: !!b, bDis: b ? b.disabled : null, row: a ? (a.closest('[data-f], .prow, li, tr, label') || a).closest('div, li, tr').innerText.slice(0, 80) : '' }; }")
    ok(f"{T} 站主打開 #admin/perm（權限編輯器）看得到「大戶／散戶買賣（推估）」開關；即時那一列鎖住不能撥", bool(has) and pe["a"] and pe["b"] and pe["bDis"] is True, pe)

    # ---------------------------------------------------------------- 2. 站主 1440：今日即時
    pg.close()
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    opened = _bs1107_open(pg, base)
    wait_until(pg, "() => TwBigSmall.state().pts >= 2", 15000)
    s1 = pg.evaluate(_BS1107_ST)
    pos = pg.evaluate("() => { const h = document.getElementById('hoDuo'), c = document.getElementById('bsCard'); return h && c ? Math.round(c.getBoundingClientRect().top - h.getBoundingClientRect().bottom) : null; }")
    ok(f"{T} 站主：大戶／散戶分頁集保圖下面有 #bsCard、沒被鎖、預設「今日即時」、5 秒計時器開著", bool(opened) and s1["plk"] is None and s1["mode"] == "live" and s1["timer"] and pos is not None and pos >= 0, (s1, pos))
    pg.wait_for_timeout(5600)
    s2 = pg.evaluate(_BS1107_ST)
    ch = pg.evaluate("() => { const ch = echarts.getInstanceByDom(document.getElementById('bsChart')); const o = ch && ch.getOption(); return o ? { names: o.series.map(s => s.name), n: o.series[0].data.length } : null; }")
    ok(f"{T} 站主：過 5 秒真的再打一次 /quote、累計量與走勢點數真的變多、KPI 文字跟著變", S["quote"] >= 3 and s2["pts"] > s1["pts"] and s2["row"]["observed"] > s1["row"]["observed"] and s2["kpi"] != s1["kpi"], (S, s1["row"], s2["row"]))
    ok(f"{T} 站主：走勢線兩條（大單淨、小單淨）、KPI 有大單（大戶）／小單（散戶）淨額與涵蓋率、標明示意資料", ch and ch["names"] == ["大單淨", "小單淨"] and ch["n"] >= 2
       and "大單（大戶）" in s2["kpi"] and "小單（散戶）" in s2["kpi"] and "涵蓋率" in s2["kpi"] and "示意資料" in s2["note"], (ch, s2["kpi"]))
    tot = s2["row"]
    ok(f"{T} 站主：大單＋小單＋不分方向＝收集期間成交量（量守恆）", abs(tot["big_buy"] + tot["big_sell"] + tot["small_buy"] + tot["small_sell"] + tot["neutral"] - tot["observed"]) < 0.5, tot)
    pg.locator("#bsCard .howbtn").click()
    wait_until(pg, "() => { const e = document.getElementById('how-skbs'); return !!e && !e.hidden && e.getClientRects().length > 0; }", 4000)
    hw = pg.evaluate("() => (document.getElementById('how-skbs') || {}).innerText || ''")
    ok(f"{T} 按「?」→ 說明寫明推估、大單門檻、外盤內盤判斷、涵蓋率", all(k in hw for k in ("推估", "100 萬", "外盤", "內盤", "涵蓋率")), hw[:200])
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    if shots:
        _bs1107_os.makedirs(shots, exist_ok=True)
        pg.locator("#bsCard").scroll_into_view_if_needed(); pg.wait_for_timeout(400)
        pg.locator("#bsCard").screenshot(path=_bs1107_os.path.join(shots, "bs_1440_owner_live.png"))
    # 切日 K
    pg.locator("#bsMode button[data-v=\"day\"]").click(); pg.wait_for_timeout(800)
    d1 = pg.evaluate("() => { const ch = echarts.getInstanceByDom(document.getElementById('bsChart')); const o = ch && ch.getOption(); return { st: TwBigSmall.state(), o: o ? { names: o.series.map(s => s.name), n: o.series[1].data.length, nn: o.series[1].data.filter(v => v != null).length, k: o.series[0].data.length, ymin: o.yAxis[0].min, solid: typeof o.series[1].itemStyle.color === 'string' && typeof o.series[2].itemStyle.color === 'string' } : null, ls: localStorage.getItem('tw.bs.mode'), wins: [...document.querySelectorAll('#bsWin button')].map(b => b.innerText + (b.classList.contains('on') ? '*' : '') + (b.disabled ? '!' : '')), rows: document.querySelectorAll('#bsTbl tbody tr').length }; }")
    ok(f"{T} 切「日 K」→ 計時器停、上格日 K（Y 軸不從 0 起）＋下格大單淨／小單淨實色柱子、20 日、明細表 20 列、選擇記住", not d1["st"]["timer"] and d1["o"] and d1["o"]["names"] == ["日 K", "大單淨", "小單淨"]
       and d1["o"]["k"] == 20 and d1["o"]["nn"] > 0 and d1["o"]["ymin"] > 0 and d1["o"]["solid"] and d1["ls"] == "day" and d1["wins"][0] == "20 日*" and d1["rows"] == 20, d1)
    ok(f"{T} 資料只有 30 天：120 日鈕反灰並有 title（滿 60 天才開），60 日可按", d1["wins"][2].endswith("!") and not d1["wins"][1].endswith("!")
       and "滿 60 天" in (pg.get_attribute("#bsWin button[data-v=\"120\"]", "title") or ""), d1["wins"])
    pg.locator("#bsWin button[data-v=\"60\"]").click(); pg.wait_for_timeout(600)
    d2 = pg.evaluate("() => { const o = echarts.getInstanceByDom(document.getElementById('bsChart')).getOption(); return { k: o.series[0].data.length, rows: document.querySelectorAll('#bsTbl tbody tr').length }; }")
    ok(f"{T} 按「60 日」→ 日 K 根數變多（> 20）、明細表列數＝收集到的天數（30）", d2["k"] > 20 and d2["rows"] == 30, d2)
    pg.locator("#bsWin button[data-v=\"20\"]").click(); pg.wait_for_timeout(500)
    if shots:
        pg.locator("#bsCard").screenshot(path=_bs1107_os.path.join(shots, "bs_1440_owner_day.png"))
    c.close()

    # ---------------------------------------------------------------- 3. 一般會員、訪客：看不到（整張卡不畫）、不抓資料、不打即時；手機也沒有「買賣推估」分段
    for who, nm, w in (("member", "一般會員", 1440), (None, "訪客", 1440), ("member", "一般會員 390", 390)):
        c, S = _bs1107_ctx(b, who, width=w, touch=w < 500)
        pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "#stock/" + _BS1107_CODE, wait_until="domcontentloaded")
        if w < 500:
            wait_until(pg, "() => !!document.querySelector('#mbTabs button[data-t=\"big\"]') && !!window.TwBigSmall", 40000)
            pg.locator('#mbTabs button[data-t="big"]').first.click(); pg.wait_for_timeout(800)
            segs = pg.evaluate("() => [...document.querySelectorAll('#mbBody .mbseg button')].map(b => b.dataset.s)")
        else:
            wait_until(pg, "() => !!document.querySelector('#stockTabs button[data-t=\"holders\"]') && !!window.TwBigSmall", 40000)
            pg.locator('#stockTabs button[data-t="holders"]').first.click()
            wait_until(pg, "() => !!document.getElementById('hoDuo')", 10000)
            segs = []
        pg.wait_for_timeout(6000)
        s = pg.evaluate("() => ({ card: !!document.getElementById('bsCard'), st: TwBigSmall.state(), can: TwBigSmall.can() })")
        ok(f"{T} {nm}：看不到（沒有 #bsCard、手機沒有「買賣推估」分段）、不抓 data/bigsmall、6 秒內沒打這一檔的大小單即時、計時器沒開",
           not s["card"] and not s["can"] and "bs" not in segs and S["daily"] == 0 and S["quote"] == 0 and not s["st"]["timer"] and s["st"]["mode"] is None, (s, S, segs))
        if shots and who == "member" and w == 1440:
            pg.evaluate("() => document.getElementById('hoDuo').scrollIntoView({block: 'start'})"); pg.wait_for_timeout(400)
            pg.screenshot(path=_bs1107_os.path.join(shots, "bs_1440_member_hidden.png"))
        c.close()

    # ---------------------------------------------------------------- 4. 手機 390 站主
    c, S = _bs1107_ctx(b, "admin", owner=True, width=390, touch=True)
    pg = c.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    opened = _bs1107_open(pg, base, mobile=True)
    wait_until(pg, "() => TwBigSmall.state().pts >= 1", 15000)
    m = pg.evaluate("() => { const c = document.getElementById('bsCard').getBoundingClientRect(), k = document.getElementById('bsKpi'), ch = document.getElementById('bsChart').getBoundingClientRect();"
                    " return { l: Math.round(c.left), r: Math.round(c.right), vw: innerWidth, sw: document.documentElement.scrollWidth, kh: k ? Math.round(k.getBoundingClientRect().height) : 0, chw: Math.round(ch.width), seg: [...document.querySelectorAll('#bsMode button')].map(b => Math.round(b.getBoundingClientRect().height)) }; }")
    ok(f"{T} 390 站主：「買賣推估」分段畫出 #bsCard、整張在畫面內、沒有橫向捲軸、KPI 兩欄、圖寬 ≥ 300、分段鈕高 ≥ 32", bool(opened) and m["l"] >= 0 and m["r"] <= m["vw"] and m["sw"] <= m["vw"]
       and m["kh"] > 0 and m["chw"] >= 300 and all(x >= 32 for x in m["seg"]), m)
    if shots:
        pg.evaluate("() => { const e = document.querySelector('#mbBody .mbseg'); const y = e.getBoundingClientRect().top + scrollY - 70; scrollTo(0, y); }"); pg.wait_for_timeout(500)
        pg.screenshot(path=_bs1107_os.path.join(shots, "bs_390_owner.png"), full_page=False)
    c.close()
    ok(f"{T}：全程沒有網頁錯誤", not errs, errs[:5])


register("大戶散戶買賣1107", lambda pg, b, base, code: t_bigsmall_1107(b, base, code))
