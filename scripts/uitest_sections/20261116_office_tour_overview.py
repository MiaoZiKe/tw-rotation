# 驗收段落「辦公室新手引導與總覽通知」（2026-11-16，遊戲基礎設定第 7、8 項）：site/office/world/js/tour.js、overview.js、world/hud.css
#   ① 新手引導：第一次進場（沒有 aiOffice.game.tour）跳出 5 步聚光燈；每一步標題、洞的位置（員工／對話框／總覽鈕）、說明卡不遮住洞、
#      上一步／下一步／Esc／跳過、走完寫入 localStorage、之後重新整理不再跳、「?」裡的「重看新手引導」能再看一次；自動化瀏覽器預設不跳（?tour=1 才當真人）
#   ② 總覽面板：頂列「總覽」鈕開面板、列數＝畫面上的人數、狀態篩選晶片、點一列鏡頭真的移過去並開資訊卡
#   ③ 通知中心：真的用狀態事件（派工→完成、久沒動靜→卡住、點火→著火、等級欄位變大→升等）產生通知，紅點數字、通知分頁、點通知飛過去、全部已讀清零
#   ④ 手機 390×844：引導說明卡在畫面內、不蓋住洞、字不小於 11px；總覽鈕看得到、面板是底部抽屜、不出現橫向捲軸
#   ⑤ 文案沒有禁用字；功能鍵 office.overview 有登記（features.js、四個方案範本）
# 環境變數 TOUR_SHOTS 指到資料夾時順便存截圖（引導每一步、面板、通知、手機）。
# flake8: noqa

import os as _os
import re as _re

_OT_BAD = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")


def _ot_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _ot_shot(pg, name):
    d = _os.environ.get("TOUR_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _ot_open(b, base, w=1440, h=900, touch=False, tour="1", ls=None):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch)
    init = {"aiOffice.daytime": "day"}
    init.update(ls or {})
    c.add_init_script("try{" + "".join("localStorage.setItem(%r,%r);" % (k, v) for k, v in init.items()) + "}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    q = "?ambient=0&q=low&pr=0.6" + ("&tour=" + tour if tour is not None else "")
    pg.goto(_ot_root(base) + "/office/world.html" + q, wait_until="domcontentloaded")
    cond = "true" if touch else "window.__world.chars.get('ceo')._sx > 0"   # 手機直式：CEO 不一定在畫面內（名牌座標 -999），只等辦公室建好
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat && window.__world.chars.get('ceo') && " + cond, 90000)
    return c, pg, got


_OT_RECTS = """() => { const R = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; };
  const h = R('#trHole'), c = R('#trCard'); const ov = document.getElementById('trOv');
  return { hole: ov && !ov.classList.contains('nohole') ? h : null, card: c, title: (document.getElementById('trTitle') || {}).textContent, step: (document.getElementById('trStep') || {}).textContent,
           vw: innerWidth, vh: innerHeight }; }"""


def _ot_hit(a, b_):
    return a and b_ and a["l"] < b_["r"] and a["r"] > b_["l"] and a["t"] < b_["b"] and a["b"] > b_["t"]


def _ot_inside(r, vw, vh):
    return r["l"] >= -1 and r["t"] >= -1 and r["r"] <= vw + 1 and r["b"] <= vh + 1


def _ot_walk(pg, tag, vw, vh, shots):
    """從第 1 步走到第 5 步：每一步量標題、洞、說明卡；回傳每一步的量測。"""
    got = []
    want = ["這是你的辦公室", "點一下員工", "按住不放", "用對話框下指令", "總覽面板"]
    for i in range(5):
        pg.wait_for_timeout(420)   # 洞有 0.25 秒的移動動畫：等它停穩再量
        r = pg.evaluate(_OT_RECTS)
        got.append(r)
        ok(f"{tag}：第 {i + 1} 步標題是「{want[i]}」、顯示「第 {i + 1}／5 步」", want[i] in (r["title"] or "") and r["step"] == f"第 {i + 1}／5 步", r["title"])
        ok(f"{tag}：第 {i + 1} 步說明卡完整在畫面內", _ot_inside(r["card"], vw, vh), r["card"])
        if i == 0:
            ok(f"{tag}：第 1 步沒有洞（講整間辦公室）", r["hole"] is None, r["hole"])
        else:
            ok(f"{tag}：第 {i + 1} 步有洞、而且說明卡沒有蓋住洞", bool(r["hole"]) and not _ot_hit(r["hole"], r["card"]), [r["hole"], r["card"]])
        _ot_shot(pg, f"{shots}_step{i + 1}.png")
        if i < 4:
            pg.click("#trNext")
            wait_until(pg, f"() => document.getElementById('trStep').textContent === '第 {i + 2}／5 步'", 4000)
    return got


def _ot_target_checks(pg, got, tag):
    """第 2、3 步的洞在員工身上；第 4 步的洞蓋得到對話框；第 5 步的洞蓋得到「總覽」鈕。"""
    for i in (1, 2):
        h = got[i]["hole"]
        # 洞圈住的是畫面裡「某一位」員工（手機直式 CEO 不一定在畫面內，引導會改挑看得到的人）：名牌座標落在洞裡
        who = pg.evaluate("(h) => [...__world.chars.values()].filter(c => !c.spec.pet && c._sx > 0 && c._sx >= h.l - 40 && c._sx <= h.r + 40 && c._sy >= h.t - 40 && c._sy <= h.b + 40).map(c => c.spec.id)", h) if h else []
        ok(f"{tag}：第 {i + 1} 步的洞圈住員工（員工名牌座標在洞裡）", bool(h) and len(who) > 0, [h, who])
    chat = pg.evaluate("() => { const e = document.getElementById('chatForm') || document.getElementById('chatPanel'); const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; }")
    ok(f"{tag}：第 4 步的洞圈住對話框輸入列", _ot_hit(got[3]["hole"], chat), [got[3]["hole"], chat])
    ov = pg.evaluate("() => { const r = document.getElementById('ovBtn').getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom }; }")
    ok(f"{tag}：第 5 步的洞圈住頂列「總覽」鈕", _ot_hit(got[4]["hole"], ov), [got[4]["hole"], ov])


# ───────────────────────── ① 新手引導（桌機） ─────────────────────────
def _ot_tour_desktop(b, base):
    c, pg, got = _ot_open(b, base)
    try:
        if not ok("引導：辦公室頁載入完成", got):
            return
        ok("引導：第一次進場（沒有 aiOffice.game.tour）自動跳出", wait_until(pg, "() => !!document.getElementById('trOv')", 30000))
        ok("引導：一開始 localStorage 沒有 aiOffice.game.tour", pg.evaluate("() => localStorage.getItem('aiOffice.game.tour')") is None)
        # 擋點擊：蓋層底下的 3D 場景點不到（點員工不會開資訊卡）
        ceo = pg.evaluate("() => { const c = __world.chars.get('ceo'); return [c._sx, c._sy + 24]; }")
        pg.mouse.click(ceo[0], ceo[1])
        pg.wait_for_timeout(400)
        ok("引導：跳出時點 3D 場景不會誤開資訊卡（蓋層有擋）", pg.evaluate("() => document.getElementById('card').hidden"))
        got5 = _ot_walk(pg, "引導（桌機）", 1440, 900, "d_tour")
        _ot_target_checks(pg, got5, "引導（桌機）")
        txt = pg.evaluate("() => document.getElementById('trCard').innerText")
        ok("引導：說明文字沒有禁用字", not _OT_BAD.search(txt), txt)
        ok("引導：最後一步按鈕是「開始使用」、「跳過」收起來", pg.inner_text("#trNext") == "開始使用" and pg.evaluate("() => document.getElementById('trSkip').hidden"))
        # 上一步
        pg.click("#trPrev")
        ok("引導：「上一步」回到第 4 步", wait_until(pg, "() => document.getElementById('trStep').textContent === '第 4／5 步'", 3000))
        pg.keyboard.press("ArrowRight")
        ok("引導：方向鍵 → 前進到第 5 步", wait_until(pg, "() => document.getElementById('trStep').textContent === '第 5／5 步'", 3000))
        pg.click("#trNext")
        ok("引導：按「開始使用」引導關閉", wait_until(pg, "() => !document.getElementById('trOv')", 3000))
        ok("引導：走完寫入 localStorage（done）", pg.evaluate("() => localStorage.getItem('aiOffice.game.tour')") == "done")
        ok("引導：關閉後 3D 場景點得到員工（資訊卡打開）", (pg.mouse.click(ceo[0], ceo[1]) or True) and wait_until(pg, "() => !document.getElementById('card').hidden", 4000))
        ok("引導：沒有主控台錯誤", not pg.errs, pg.errs[:3])
        # 重新整理（保留 localStorage）：不再跳
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready", 90000)
        pg.wait_for_timeout(2500)
        ok("引導：看完之後重新整理不再跳出", not pg.evaluate("() => !!document.getElementById('trOv')"))
        # 「?」重看
        pg.click("#helpBtn")
        ok("引導：「?」說明裡有「重看新手引導」", wait_until(pg, "() => !!document.getElementById('tourAgain') && !document.getElementById('helpPop').hidden", 3000))
        _ot_shot(pg, "d_help.png")
        pg.click("#tourAgain")
        ok("引導：按「重看新手引導」又從第 1 步開始", wait_until(pg, "() => !!document.getElementById('trOv') && document.getElementById('trStep').textContent === '第 1／5 步'", 4000))
        ok("引導：重看時「?」說明收起來了", pg.evaluate("() => document.getElementById('helpPop').hidden"))
        pg.keyboard.press("Escape")
        ok("引導：Esc 跳過、引導關閉、紀錄改成 skip", wait_until(pg, "() => !document.getElementById('trOv')", 3000) and pg.evaluate("() => localStorage.getItem('aiOffice.game.tour')") == "skip")
        # 重看之後按「跳過」鈕
        pg.evaluate("() => __world.tourStart()")
        wait_until(pg, "() => !!document.getElementById('trOv')", 3000)
        pg.click("#trSkip")
        ok("引導：按「跳過」鈕也能關", wait_until(pg, "() => !document.getElementById('trOv')", 3000))
    finally:
        c.close()
    # 自動化瀏覽器預設不跳（沒帶 ?tour=1）、?tour=0 強制不跳
    for tr, nm in ((None, "沒帶 tour 參數（自動化瀏覽器）"), ("0", "?tour=0")):
        c, pg, got = _ot_open(b, base, tour=tr)
        try:
            wait_until(pg, "() => window.__world && window.__world.ready", 90000)
            pg.wait_for_timeout(2200)
            ok(f"引導：{nm}不自動跳出（驗收其他段落才不會被蓋住）", not pg.evaluate("() => !!document.getElementById('trOv')"))
        finally:
            c.close()


_OT_BURN = """(skip) => { const W = __world; for (const c of W.chars.values()) { if (c.spec.pet || c.absent || c.spec.isCeo || c.object3D.visible === false || (skip || []).includes(c.spec.id)) continue;
  if (W.fire.ignite(c, 'test')) { W.overview.poll(); return [c.spec.id, c.spec.nick]; } } return null; }"""   # 有些人免疫（泡過水、被拎著…）：挑第一個真的點得著的


def _ot_burn(pg, skip=None):
    return pg.evaluate(_OT_BURN, skip or [])


def _ot_clear(pg):
    """同事做的「今日結算」卡（growth_ui.js）可能在模擬加速時跳出來蓋住畫面：先關掉它再操作。"""
    pg.evaluate("() => { const d = document.getElementById('gmDay'); const b = d && d.querySelector('[data-gmx]'); if (b) b.click(); }")


def _ot_click(pg, sel):
    _ot_clear(pg)
    pg.click(sel)


def _ot_tap(pg, sel):
    _ot_clear(pg)
    pg.tap(sel)


# ───────────────────────── ②③ 總覽面板與通知中心（桌機） ─────────────────────────
_OT_PEOPLE = """() => [...__world.chars.values()].filter(c => !c.spec.pet && !c.absent && c.object3D.visible !== false).length"""


def _ot_overview_desktop(b, base):
    c, pg, got = _ot_open(b, base, ls={"aiOffice.game.tour": "done"})
    try:
        if not ok("總覽：辦公室頁載入完成", got):
            return
        ok("總覽：頂列有「總覽」鈕、一開始沒有紅點", pg.is_visible("#ovBtn") and pg.evaluate("() => document.getElementById('ovDot').hidden"))
        ok("總覽：功能鍵 office.overview 有登記（features.js）且放行", pg.evaluate("async () => { await __world.gate.load(); const f = window.TwFeatures && window.TwFeatures.byId('office.overview'); return !!f && f.cat === 'office' && __world.gate.peek('office.overview').pass; }"))
        ok("總覽：四個方案範本都有 office.overview", pg.evaluate("""async () => { const r = await fetch('../plan_presets.js'); const t = await r.text(); return (t.match(/"office\\.overview": ?(true|!0)/g) || []).length === 4; }"""))
        pg.wait_for_timeout(1200)
        _ot_click(pg, "#ovBtn")
        ok("總覽：按「總覽」開面板", wait_until(pg, "() => !document.getElementById('ovPanel').hidden && document.getElementById('ovBtn').getAttribute('aria-expanded') === 'true'", 4000))
        n = pg.evaluate(_OT_PEOPLE)
        rows = pg.evaluate("() => document.querySelectorAll('#ovList .ov-row').length")
        ok("總覽：列數＝畫面上的人數", rows == n and n > 0, [rows, n])
        ok("總覽：標題寫「共 N 人」", pg.inner_text("#ovSub") == f"共 {n} 人", pg.inner_text("#ovSub"))
        cnt = pg.evaluate("() => [...document.querySelectorAll('#ovChips .ov-chip b')].map(b => +b.textContent)")
        ok("總覽：狀態晶片的人數加起來＝總人數（全部那顆不算）", cnt and cnt[0] == n and sum(cnt[1:]) == n, cnt)
        ok("總覽：有一行白話說明「卡住＝…超過 3 分鐘沒有新動靜」", "3 分鐘" in pg.inner_text("#ovHow"), pg.inner_text("#ovHow"))
        txt = pg.evaluate("() => document.getElementById('ovPanel').innerText")
        ok("總覽：面板文字沒有禁用字", not _OT_BAD.search(txt), txt[:120])
        _ot_shot(pg, "d_overview.png")
        dr = pg.evaluate("() => { const r = e => { const x = document.querySelector(e); if (!x || x.hidden) return null; const b = x.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; }; return { a: r('#ovPanel'), tips: r('.pt-tips'), chat: r('#chatPanel'), bar: r('#bar') }; }")
        hit = lambda a, b_: a and b_ and a[0] < b_[2] and a[2] > b_[0] and a[1] < b_[3] and a[3] > b_[1]
        ok("總覽：桌機面板不跟對話框重疊", not hit(dr["a"], dr["chat"]), dr)
        # 點一列：鏡頭真的移過去、資訊卡打開
        pid = pg.evaluate("() => { const r = [...document.querySelectorAll('#ovList .ov-row')].map(x => x.dataset.id).filter(i => i !== 'ceo'); return r[r.length > 6 ? 5 : 0]; }")
        cam0 = pg.evaluate("() => { const p = __world.controls.target; return [p.x, p.y, p.z]; }")
        _ot_click(pg, f"#ovList .ov-row[data-id='{pid}']")
        ok("總覽：點一列→視角切到那個人（跟隨他）", wait_until(pg, f"() => __world.view.mode === 'char' && __world.view.char && __world.view.char.spec.id === '{pid}'", 4000), pid)
        wait_until(pg, "() => !__world.view.tween", 6000)
        cam1 = pg.evaluate("() => { const p = __world.controls.target; return [p.x, p.y, p.z]; }")
        ok("總覽：鏡頭注視點真的移動了", sum(abs(a - b_) for a, b_ in zip(cam0, cam1)) > 0.3, [cam0, cam1])
        ok("總覽：他的資訊卡打開", pg.evaluate("() => !document.getElementById('card').hidden"))
        pg.wait_for_timeout(1300)   # 面板每秒重新排一次位置（讓出操控提示）
        dr = pg.evaluate("() => { const r = e => { const x = document.querySelector(e); if (!x || x.hidden) return null; const b = x.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; }; return { a: r('#ovPanel'), tips: r('.pt-tips') }; }")
        ok("總覽：選了人、操控提示出現後，面板不被它蓋住（最下面的按鈕點得到）", dr["tips"] is not None and not hit(dr["a"], dr["tips"]), dr)
        ok("總覽：桌機點列後面板還開著（可以連續點）", pg.evaluate("() => !document.getElementById('ovPanel').hidden"))
        # 篩選：「著火」晶片 → 先沒人 → 空狀態字
        _ot_click(pg, "#ovChips .c-fire")
        ok("總覽：點「著火」晶片只列著火的人（現在沒有 → 空狀態文字）", pg.evaluate("() => document.querySelectorAll('#ovList .ov-row').length === 0 && /沒有這個狀態/.test(document.getElementById('ovList').innerText)"))
        _ot_click(pg, "#ovChips .c-fire")
        ok("總覽：再點一次取消篩選、列數回來", pg.evaluate("() => document.querySelectorAll('#ovList .ov-row').length") == n)

        # ── 事件 → 通知 ──
        info = pg.evaluate("""() => [...__world.chars.values()].filter(c => !c.spec.pet && !c.absent && !c.spec.isCeo && c.object3D.visible !== false).map(c => [c.spec.id, c.spec.nick]).slice(0, 4)""")
        (ia, na), (ib, nb), (ic, nc), (idd, nd) = info
        pg.evaluate("() => { __world.overview.poll(); }")
        base_unread = pg.evaluate("() => __world.overview.unread()")
        # 完成：真的派一個工作給 ia，再用 SubagentStop 收掉，等演出跑完（W.advance 加速模擬時間）
        pg.evaluate("(id) => { const S = __world.state; S.emit({ hook_event_name: 'SubagentStart', agent_id: 'tt-a', agent_type: id, description: '整理驗收報告' }); }", ia)
        pg.evaluate("() => __world.advance(25)")
        pg.evaluate("() => __world.overview.poll()")
        pg.evaluate("() => { __world.state.emit({ hook_event_name: 'SubagentStop', agent_id: 'tt-a', status: 'completed', last_assistant_message: '整理驗收報告 完成' }); }")
        done = wait_until(pg, "() => { __world.advance(10); __world.overview.poll(); return __world.overview.notes.some(n => n.kind === 'done'); }", 90000, 300)
        ok("通知：派工後完成（SubagentStop）→ 出現「完成」通知", done, pg.evaluate("() => __world.overview.notes.map(n => n.kind + ':' + n.text)"))
        # 卡住：另一位被派工後，把「最後動靜」往前推 5 分鐘（等於 5 分鐘沒動）
        pg.evaluate("(id) => { __world.state.emit({ hook_event_name: 'SubagentStart', agent_id: 'tt-b', agent_type: id, description: '修版面' }); }", ib)
        pg.evaluate("() => __world.advance(20)")
        pg.evaluate("() => __world.overview.poll()")
        pg.evaluate("(id) => { const a = __world.state.agent(id); a.lastToolAt -= 5 * 60e3; __world.overview.poll(); }", ib)
        ok("通知：超過 3 分鐘沒動靜 → 出現「卡住」通知，名字是他", pg.evaluate("(n) => __world.overview.notes.some(x => x.kind === 'stuck' && x.text.includes(n))", nb), pg.evaluate("() => __world.overview.notes.map(n => n.text)"))
        ok("總覽：他那一列狀態變「卡住」、排到最上面", pg.evaluate("(id) => { const r = document.querySelector('#ovList .ov-row'); return r && r.dataset.id === id && r.dataset.st === 'stuck'; }", ib), pg.evaluate("() => document.querySelector('#ovList .ov-row').outerHTML.slice(0, 160)"))
        # 著火
        burn = _ot_burn(pg)
        ok("通知：點火成功", bool(burn), burn)
        ic, nc = burn
        ok("通知：點火 → 出現「著火」通知", pg.evaluate("(n) => __world.overview.notes.some(x => x.kind === 'fire' && x.text.includes(n))", nc))
        ok("總覽：著火的人狀態是「著火」、排最上面", pg.evaluate("(id) => { const r = document.querySelector('#ovList .ov-row'); return r.dataset.id === id && r.dataset.st === 'fire'; }", ic))
        _ot_shot(pg, "d_overview_states.png")
        # 升等：等級欄位出現（對方的功能做好後的欄位協定：W.levelOf(id)）且變大
        pg.evaluate("(id) => { window.__lv = 2; window.__lvId = id; __world.levelOf = q => q === window.__lvId ? window.__lv : 1; __world.overview.poll(); }", idd)
        ok("總覽：等級欄位存在時才顯示「Lv N」", pg.evaluate("() => !!document.querySelector('#ovList .ov-row .lv')"))
        pg.evaluate("() => { window.__lv = 3; __world.overview.poll(); }")
        ok("通知：等級變大 → 出現「升等」通知", pg.evaluate("() => __world.overview.notes.some(x => x.kind === 'level')"))
        # 紅點
        un = pg.evaluate("() => __world.overview.unread()")
        dot = pg.evaluate("() => { const d = document.getElementById('ovDot'); return [d.hidden, d.textContent, getComputedStyle(d).backgroundColor]; }")
        ok("通知：頂列紅點顯示未讀數、數字正確", not dot[0] and dot[1] == str(un) and un >= 4, [dot, un])
        _ot_click(pg, "#ovTabNt")
        ok("通知：切到「通知」分頁，列出四種通知", wait_until(pg, "() => ['done', 'stuck', 'fire', 'level'].every(k => document.querySelector(`#ovList .ov-nt[data-k=${k}]`))", 4000))
        ok("通知：未讀的有高亮（.unread）、「全部已讀」鈕可按", pg.evaluate("() => document.querySelectorAll('#ovList .ov-nt.unread').length > 0 && !document.getElementById('ovAllRead').disabled"))
        _ot_shot(pg, "d_notify.png")
        # 點一則通知：標已讀、飛過去
        nid = pg.evaluate("() => document.querySelector('#ovList .ov-nt.unread[data-k=fire]').dataset.nid")
        _ot_click(pg, f"#ovList .ov-nt[data-nid='{nid}']")
        ok("通知：點一則→這則變已讀、鏡頭飛到他（示範模擬器也會一直產生新通知，所以只驗這一則）", wait_until(pg, f"() => __world.overview.notes.find(n => n.id === {nid}).read && __world.view.char && __world.view.char.spec.id === __world.overview.notes.find(n => n.id === {nid}).who", 4000))
        pg.evaluate("() => { __world.speed = 0; }")   # 暫停示範模擬器，免得它在驗收中途又產生新通知
        _ot_click(pg, "#ovAllRead")
        ok("通知：按「全部已讀」→ 紅點消失、未讀 0", pg.evaluate("() => document.getElementById('ovDot').hidden && __world.overview.unread() === 0 && document.querySelectorAll('#ovList .ov-nt.unread').length === 0"))
        ok("通知：全部已讀後按鈕灰掉", pg.evaluate("() => document.getElementById('ovAllRead').disabled"))
        # 之後的新事件又會亮
        burn2 = _ot_burn(pg, [ic])
        ok("通知：已讀之後的新事件紅點又亮起來", pg.evaluate("() => !document.getElementById('ovDot').hidden && __world.overview.unread() >= 1"))
        _ot_click(pg, "#ovX")
        ok("總覽：× 關閉面板、鈕不再是展開狀態", pg.evaluate("() => document.getElementById('ovPanel').hidden && document.getElementById('ovBtn').getAttribute('aria-expanded') === 'false'"))
        _ot_click(pg, "#ovBtn")
        pg.keyboard.press("Escape")
        ok("總覽：Esc 也能關閉", pg.evaluate("() => document.getElementById('ovPanel').hidden"))
        ok("總覽：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ④ 手機 390×844 ─────────────────────────
_OT_SMALL = """(sel) => { const out = []; const root = document.querySelector(sel); if (!root) return out; for (const e of root.querySelectorAll('*')) { if (!e.childNodes) continue;
  let own = ''; for (const n of e.childNodes) if (n.nodeType === 3) own += n.textContent; own = own.trim(); if (!own) continue; const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
  const fs = parseFloat(getComputedStyle(e).fontSize); if (fs < 11) out.push([own.slice(0, 12), fs]); } return out; }"""


def _ot_mobile(b, base):
    c, pg, got = _ot_open(b, base, w=390, h=844, touch=True)
    try:
        if not ok("手機：辦公室頁載入完成", got):
            return
        ok("手機：引導自動跳出", wait_until(pg, "() => !!document.getElementById('trOv')", 30000))
        got5 = _ot_walk(pg, "引導（手機）", 390, 844, "m_tour")
        _ot_target_checks(pg, got5, "引導（手機）")
        small = pg.evaluate(_OT_SMALL, "#trOv")
        ok("手機：引導文字都不小於 11px", not small, small)
        w = pg.evaluate("() => document.getElementById('trCard').getBoundingClientRect().width")
        ok("手機：說明卡寬度貼合畫面（≤ 366px、≥ 300px）", 300 <= w <= 366, w)
        _ot_click(pg, "#trNext")
        ok("手機：走完關閉並寫入紀錄", wait_until(pg, "() => !document.getElementById('trOv') && localStorage.getItem('aiOffice.game.tour') === 'done'", 3000))
        # 總覽
        vis = pg.evaluate("() => { const r = document.getElementById('ovBtn').getBoundingClientRect(); return [r.left >= 0, r.right <= innerWidth, r.height >= 36, r.width > 0]; }")
        ok("手機：頂列「總覽」鈕看得到、在畫面內、夠大", all(vis), vis)
        pg.wait_for_timeout(800)
        _ot_tap(pg, "#ovBtn")
        ok("手機：點「總覽」開面板（底部抽屜）", wait_until(pg, "() => !document.getElementById('ovPanel').hidden", 4000))
        r = pg.evaluate("() => { const r = document.getElementById('ovPanel').getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, h: r.height, vw: innerWidth, vh: innerHeight }; }")
        ok("手機：面板在畫面內、貼底、高度不超過 6 成", r["l"] >= 0 and r["r"] <= r["vw"] + 1 and r["b"] <= r["vh"] + 1 and r["h"] <= r["vh"] * 0.6, r)
        ok("手機：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1 && document.getElementById('ovPanel').scrollWidth <= document.getElementById('ovPanel').clientWidth + 1"))
        cr = pg.evaluate("() => { const a = document.getElementById('ovPanel').getBoundingClientRect(), c = (document.getElementById('chatForm') || document.getElementById('chatPanel')).getBoundingClientRect(); return { a: [a.left, a.top, a.right, a.bottom], c: [c.left, c.top, c.right, c.bottom] }; }")
        ok("手機：面板沒有跟底部主對話框輸入列重疊", cr["a"][3] <= cr["c"][1] + 1 or cr["a"][2] <= cr["c"][0] or cr["a"][0] >= cr["c"][2] or cr["a"][1] >= cr["c"][3], cr)
        small = pg.evaluate(_OT_SMALL, "#ovPanel")
        ok("手機：面板文字都不小於 11px", not small, small)
        hs = pg.evaluate("() => [...document.querySelectorAll('#ovList .ov-row')].slice(0, 6).map(x => x.getBoundingClientRect().height)")
        ok("手機：每一列夠好點（高度 ≥ 44px）", hs and min(hs) >= 44, hs)
        _ot_shot(pg, "m_overview.png")
        ok("手機：點火成功", bool(_ot_burn(pg)))
        _ot_tap(pg, "#ovTabNt")
        ok("手機：通知分頁有通知、紅點看得到", pg.evaluate("() => document.querySelectorAll('#ovList .ov-nt').length > 0 && !document.getElementById('ovDot').hidden"))
        _ot_shot(pg, "m_notify.png")
        _ot_tap(pg, "#ovAllRead")
        ok("手機：全部已讀 → 紅點消失", pg.evaluate("() => document.getElementById('ovDot').hidden"))
        _ot_tap(pg, "#ovTabP")
        pid = pg.evaluate("() => [...document.querySelectorAll('#ovList .ov-row')].map(x => x.dataset.id).filter(i => i !== 'ceo')[1]")
        _ot_tap(pg, f"#ovList .ov-row[data-id='{pid}']")
        ok("手機：點一列→鏡頭飛過去、面板自動收起來（才看得到他）", wait_until(pg, f"() => __world.view.char && __world.view.char.spec.id === '{pid}' && document.getElementById('ovPanel').hidden", 4000))
        ok("手機：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _ot_all(b, base):
    only = _os.environ.get("OT_ONLY", "")   # 除錯用：desk＝只跑桌機兩段、mobile＝只跑手機
    if only != "mobile":
        _ot_tour_desktop(b, base)
        _ot_overview_desktop(b, base)
    if only != "desk":
        _ot_mobile(b, base)


register("辦公室新手引導與總覽通知", lambda pg, b, base, code: _ot_all(b, base))
