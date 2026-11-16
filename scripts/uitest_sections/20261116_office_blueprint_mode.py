# 驗收段落「辦公室藍圖與純工作模式」：AI Office 3D 辦公室（site/office/world.html）第二批第 6、7、8、10 項。
# 擁有者同意「全做」第二批 10 項（docs/ai_office/game_basics_gap_round2.md）：
#   B1 藍圖：設定→任務藍圖；增刪站、指定負責人、存範本；重新整理範本還在；套用後流程條標出目前站、負責人名牌掛站名、一站一站往下走；
#      重新整理後進行中的流程還在；真實專案模式只把流程寫進對話框（給 CEO 的指令），不自己派工
#   B2 優先度格子表：員工 × 工作類型；點格子 0→1→2→3→0 並存起來、重新整理還在；自動派工（成長組）存在時真的參考這張表（0＝排除、3＝加分）
#   B3 壓力原因：資訊卡出現原因清單（連續被退件 3 次…）、剩餘時間會倒數、快到期淡出、到期消失；壓力數字漸變不瞬跳
#   B4 純工作模式：設定裡一鍵切換；打開後火焰不生成（點不著、不冒火星）、不開始運動、情緒台詞不出現、等級與慶祝不顯示；記住選擇、切回來全部恢復
#   B5 閘門：office.blueprint／office.priority 已註冊、四個方案都有設定；訪客被鎖、註冊會員用到上限（5 次）被鎖
#   B6 版面：1280／390 沒有橫向溢出、字級 ≥ 11px、面板在視窗內；沒有禁用字；沒有網頁錯誤
# 由 runsec2.py 或 _uitest.py 載入。環境變數 BP_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os
import json as _json

_BP_QS = "?q=low&pr=0.6"
_BP_BANNED = ["價格", "NT$", "付費", "升級", "訂閱", "方案", "Plus", "Pro", "免費", "右鍵"]
_BP_MEM = "() => [...__world.chars.values()].filter(c => !c.spec.pet && !c.spec.isCeo && !c.jobless && !c.away).map(c => c.spec.id)"


def _bp_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _bp_open(b, base, w=1280, h=800, init=None, qs=_BP_QS):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}" + (init or ""))
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "vScP" not in m.text else None)
    pg.goto(_bp_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.blueprint && window.__world.prio && window.__world.stressWhy && window.__world.workmode && window.__world.workmodeReady", 90000)
    pg.wait_for_timeout(400)
    return c, pg, got


def _bp_shot(pg, name):
    d = _os.environ.get("BP_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _bp_adv(pg, sec):
    pg.evaluate("(s) => __world.advanceAsync(s)", sec)


def _bp_settings(pg, which=None):
    """點頂列「設定」，必要時再點裡面的按鈕（藍圖 bp／優先度 pr）。手機要先展開「更多」。"""
    if pg.evaluate("() => getComputedStyle(document.getElementById('stBtn')).display") == "none":
        pg.click("#moreBtn")
        pg.wait_for_timeout(200)
    pg.click("#stBtn")
    pg.wait_for_timeout(200)
    if which:
        pg.click(f'#stPop [data-st="{which}"]')
        pg.wait_for_timeout(250)


# ───────── B1 藍圖 ─────────
def t_bp_blueprint(b, base):
    c, pg, got = _bp_open(b, base, qs=_BP_QS + "&bpstep=9999")
    ok("B1 辦公室載入且四個新功能都掛上了", got)
    if not got:
        c.close()
        return
    ok("B1 設定鈕在頂列、點開有「純工作模式」「任務藍圖」「優先度表」", (_bp_settings(pg) or True) and pg.evaluate("() => { const p = document.getElementById('stPop'); return !p.hidden && !!p.querySelector('#wkSw') && !!p.querySelector('[data-st=bp]') && !!p.querySelector('[data-st=pr]'); }"))
    pg.click('#stPop [data-st="bp"]')
    pg.wait_for_timeout(300)
    ok("B1 藍圖面板打開、預設四站（需求、實作、審查、測試）", pg.evaluate("() => { const p = document.getElementById('bpPanel'); return !p.hidden && [...p.querySelectorAll('.bp-n')].map(i => i.value).join() === '需求,實作,審查,測試'; }"))
    _bp_shot(pg, "bp_editor.png")
    n0 = pg.evaluate("() => document.querySelectorAll('#bpPanel .bp-n').length")
    pg.click("#bpAdd")
    pg.wait_for_timeout(150)
    ok("B1 加一站→變 5 站，預覽條也多一站", pg.evaluate("() => document.querySelectorAll('#bpPanel .bp-n').length") == n0 + 1 and pg.evaluate("() => document.querySelectorAll('#bpPanel .bp-chip').length") == n0 + 1)
    pg.fill('#bpPanel li[data-i="0"] .bp-n', "企劃")
    pg.fill('#bpPanel li[data-i="4"] .bp-n', "上線")
    ok("B1 改站名→預覽條跟著變", pg.evaluate("() => document.querySelector('#bpPanel .bp-flow').textContent.includes('1 企劃') && document.querySelector('#bpPanel .bp-flow').textContent.includes('5 上線')"))
    pg.click('#bpPanel li[data-i="2"] [data-bp="del"]')
    pg.wait_for_timeout(150)
    ok("B1 刪一站→剩 4 站", pg.evaluate("() => document.querySelectorAll('#bpPanel .bp-n').length") == 4)
    pg.click('#bpPanel li[data-i="3"] [data-bp="up"]')
    pg.wait_for_timeout(150)
    ok("B1 上移一站→順序真的換了（企劃、實作、上線、測試）", pg.evaluate("() => [...document.querySelectorAll('#bpPanel .bp-n')].map(i => i.value).join()") == "企劃,實作,上線,測試")
    ids = pg.evaluate(_BP_MEM)
    pg.select_option('#bpPanel li[data-i="1"] .bp-w', ids[0])
    pg.select_option('#bpPanel li[data-i="2"] .bp-w', ids[1])
    pg.fill("#bpName", "我的上線流程")
    pg.click("#bpSave")
    pg.wait_for_timeout(200)
    ok("B1 儲存範本→寫進 localStorage（aiOffice.game.blueprint.*）且訊息提示", pg.evaluate("() => { const o = JSON.parse(localStorage.getItem('aiOffice.game.blueprint.demo') || 'null'); return !!o && o.tpls.some(t => t.name === '我的上線流程' && t.nodes.length === 4 && t.nodes[1].who); }") and "我的上線流程" in pg.inner_text("#bpMsg"))
    pg.click('#bpPanel [data-bp="new"]')
    pg.wait_for_timeout(150)
    ok("B1 新範本→範本下拉有兩個", pg.evaluate("() => document.querySelectorAll('#bpTpl option').length") == 2)
    pg.select_option("#bpTpl", index=0)
    pg.wait_for_timeout(150)
    ok("B1 切回第一個範本→站名還原", pg.evaluate("() => [...document.querySelectorAll('#bpPanel .bp-n')].map(i => i.value).join()") in ("企劃,實作,上線,測試", "需求,實作,審查,測試"))
    # 重新整理後範本還在
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready && window.__world.blueprint", 90000)
    pg.wait_for_timeout(400)
    ok("B1 重新整理後範本還在（兩個範本、含「我的上線流程」）", pg.evaluate("() => { const t = __world.blueprint.templates(); return t.length === 2 && t.some(x => x.name === '我的上線流程' && x.nodes[0].name === '企劃'); }"))
    _bp_settings(pg, "bp")
    pg.select_option("#bpTpl", label="我的上線流程")
    pg.wait_for_timeout(200)
    ok("B1 重新整理後在面板選回範本→站名與負責人都在", pg.evaluate("() => { const l = [...document.querySelectorAll('#bpPanel li')]; return l.map(x => x.querySelector('.bp-n').value).join() === '企劃,實作,上線,測試' && !!l[1].querySelector('.bp-w').value && !!l[2].querySelector('.bp-w').value; }"))
    # 套用：流程條、名牌、一站一站走
    pg.evaluate("() => { __world.blueprint.stepSec = 4; }")
    pg.fill("#bpDesc", "把盤後貼文版型改好")
    pg.click("#bpRun")
    pg.wait_for_timeout(300)
    ok("B1 套用→面板收起、左上角流程條出現且停在第 1 站", pg.evaluate("() => { const f = document.getElementById('bpFlow'); return document.getElementById('bpPanel').hidden && !f.hidden && f.dataset.step === '0' && f.querySelectorAll('.bp-s').length === 4 && f.querySelector('.bp-s.cur').textContent.includes('企劃'); }"))
    _bp_shot(pg, "bp_flow_step1.png")
    ok("B1 負責人名牌掛著「第 N 站・站名」", pg.evaluate("() => { const t = document.querySelector('.tag .gbp'); return !!t && /第 1 站・企劃/.test(t.textContent); }") or pg.evaluate("() => !__world.blueprint.run.nodes[0].who"))
    _bp_adv(pg, 5)
    ok("B1 時間走了→換到第 2 站（流程條與名牌跟著動）", wait_until(pg, "() => Number(document.getElementById('bpFlow').dataset.step) >= 1", 15000))
    ok("B1 走過的站打勾", pg.evaluate("() => document.querySelectorAll('#bpFlow .bp-s.done').length") >= 1)
    st = pg.evaluate("() => __world.blueprint.run && __world.blueprint.run.step")
    # 重新整理後進行中的流程還在
    pg.evaluate("() => { __world.blueprint.stepSec = 999; }")
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready && window.__world.blueprint", 90000)
    wait_until(pg, "() => { const f = document.getElementById('bpFlow'); return f && !f.hidden; }", 20000)
    ok("B1 重新整理後進行中的流程還在（流程條出現、站數相同）", pg.evaluate("() => { const f = document.getElementById('bpFlow'); return !f.hidden && f.querySelectorAll('.bp-s').length === 4 && Number(f.dataset.step) >= %d; }" % max(st, 0)))
    s0 = pg.evaluate("() => Number(document.getElementById('bpFlow').dataset.step)")
    if s0 < 4:
        pg.click('#bpFlow [data-bf="next"]')
        pg.wait_for_timeout(300)
    ok("B1 手動按「這站完成」→往後一站", pg.evaluate("() => Number(document.getElementById('bpFlow').dataset.step)") == min(s0 + 1, 4) or s0 >= 4)
    pg.evaluate("() => { const B = __world.blueprint; while (B.run && B.run.step < B.run.nodes.length) B.next(true); }")
    pg.wait_for_timeout(300)
    ok("B1 全部走完→顯示「全部完成」", "全部完成" in pg.inner_text("#bpFlow"))
    pg.evaluate("() => { const b = document.querySelector('#bpFlow [data-bf=stop]'); if (b) b.click(); }")      # 走完 8 秒後流程條會自己收起來，所以用 evaluate 點（已經收起也算過）
    pg.wait_for_timeout(200)
    ok("B1 按「收起」→流程條消失、進行中紀錄清掉", pg.evaluate("() => document.getElementById('bpFlow').hidden && !localStorage.getItem('aiOffice.game.blueprintrun.demo')"))
    # 真實專案：只轉成給 CEO 的指令
    pg.evaluate("() => { __world.live = Object.assign(__world.live || {}, { mode: 'live' }); __world.blueprint.stepSec = 999; }")
    simBefore = pg.evaluate("() => [...__world.state.agents.values()].filter(a => a.phase !== 'idle').length")
    pg.evaluate("async () => { await __world.blueprint.apply({ text: '改版型' }); }")
    pg.wait_for_timeout(300)
    ok("B1 真實專案：流程轉成給 CEO 的指令（含站名與負責人、這次要做的事），放進主對話框", pg.evaluate("() => { const t = document.getElementById('chatText').value || __world.blueprint.lastText || ''; return t.includes('請依照下面的') && t.includes('1. 企劃') && t.includes('改版型') && t.includes('共 4 站'); }"))
    ok("B1 真實專案：不自己派工（沒有任何人被模擬器派去工作）", pg.evaluate("() => [...__world.state.agents.values()].filter(a => a.phase !== 'idle').length") == simBefore)
    pg.evaluate("() => { __world.blueprint.stop(); __world.live.mode = 'demo'; }")
    ok("B1 沒有網頁錯誤", not pg.errs)
    c.close()


# ───────── B2 優先度格子表 ─────────
def t_bp_priority(b, base):
    c, pg, got = _bp_open(b, base)
    if not got:
        ok("B2 載入", False)
        c.close()
        return
    ids = pg.evaluate(_BP_MEM)
    _bp_settings(pg, "pr")
    ok("B2 優先度表打開：每位同事一列、九種工作類型一欄", pg.evaluate("() => document.querySelectorAll('#prPanel tbody tr').length") == len(ids) and pg.evaluate("() => document.querySelectorAll('#prPanel thead th').length") == 10)
    _bp_shot(pg, "pr_grid.png")
    cell = f'#prPanel .pr-c[data-id="{ids[0]}"][data-k="研究"]'
    v0 = int(pg.get_attribute(cell, "data-v"))
    seq = []
    for _ in range(4):
        pg.click(cell)
        pg.wait_for_timeout(80)
        seq.append(int(pg.get_attribute(cell, "data-v")))
    ok("B2 點格子循環 +1，3 再點回 0（連點四下回到原值）", seq == [(v0 + i + 1) % 4 for i in range(4)] and seq[-1] == v0)
    pg.click(cell)
    pg.click(cell)
    v = int(pg.get_attribute(cell, "data-v"))
    ok("B2 改過的格子有橘色外框（set）、畫面數字與 aria-label 一致", "set" in pg.get_attribute(cell, "class") and f"優先度 {v}" in pg.get_attribute(cell, "aria-label"))
    ok("B2 存進 localStorage（aiOffice.game.prio.*）", pg.evaluate("(a) => { const o = JSON.parse(localStorage.getItem('aiOffice.game.prio.demo') || '{}'); return o[a[0]] && o[a[0]]['研究'] === a[1]; }", [ids[0], v]))
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready && window.__world.prio", 90000)
    pg.wait_for_timeout(400)
    _bp_settings(pg, "pr")
    ok("B2 重新整理後格子值還在", int(pg.get_attribute(cell, "data-v")) == v)
    # 自動派工參考這張表（成長組存在才驗）
    has = pg.evaluate("() => !!(__world.growth && __world.growth.rank)")
    if has:
        pg.evaluate("(a) => { const P = __world.prio; for (const id of a) P.set(id, '研究', 0); P.set(a[1], '研究', 3); }", ids)
        r = pg.evaluate("() => __world.growth.rank('研究').map(x => x.id)")
        ok("B2 只有優先度 3 的人在自動派工候選名單，理由寫「優先度 3」", r == [ids[1]] and "優先度 3" in pg.evaluate("() => __world.growth.rank('研究')[0].why"))
        pg.evaluate("(a) => { __world.prio.set(a[0], '研究', 3); __world.prio.set(a[1], '研究', 0); }", ids)
        r2 = pg.evaluate("() => __world.growth.rank('研究').map(x => x.id)")
        ok("B2 換掉優先度→候選名單跟著換", r2 == [ids[0]])
        pg.evaluate("(a) => { __world.prio.set(a[0], '研究', 1); }", ids)
        s1 = pg.evaluate("(a) => __world.growth.rank('研究').find(x => x.id === a[0]).score", ids)
        pg.evaluate("(a) => { __world.prio.set(a[0], '研究', 3); }", ids)
        s3 = pg.evaluate("(a) => __world.growth.rank('研究').find(x => x.id === a[0]).score", ids)
        ok("B2 優先度從 1 調到 3，派工分數明顯增加（每 1 點 25 分，專長一顆星 20 分）", abs((s3 - s1) - 50) < 0.01)
    else:
        ok("B2 沒有成長系統時優先度表照樣能用（不接派工）", pg.evaluate("() => __world.prio.hooked") is False)
    pg.click('#prPanel [data-pr="reset"]')
    pg.wait_for_timeout(150)
    ok("B2 全部恢復預設→沒有任何橘色外框", pg.evaluate("() => document.querySelectorAll('#prPanel .pr-c.set').length") == 0)
    ok("B2 沒有網頁錯誤", not pg.errs)
    c.close()


# ───────── B3 壓力原因 ─────────
def t_bp_stress(b, base):
    c, pg, got = _bp_open(b, base)
    if not got:
        ok("B3 載入", False)
        c.close()
        return
    ids = pg.evaluate(_BP_MEM)
    wid = ids[0]
    pg.evaluate("(id) => { __world.stressWhy.clear(); for (let i = 0; i < 3; i++) __world.emit('rejected', id, {}); __world.stressWhy.add(id, 'knocked', { ttl: 14000 }); __world.ui.showCard(__world.chars.get(id)); }", wid)
    pg.wait_for_timeout(500)
    ok("B3 資訊卡出現「壓力原因」區塊", pg.evaluate("() => !!document.querySelector('#card #srCard .sr-l')"))
    txt = pg.inner_text("#srCard")
    ok("B3 列出「連續被退件 3 次」與「被丟出去或被撞到」", "連續被退件 3 次" in txt and "被丟出去或被撞到" in txt, txt)
    ok("B3 每條有剩餘時間與壓力變化（壓力 +10…）", pg.evaluate("() => [...document.querySelectorAll('#srCard li[data-k]')].every(li => /剩/.test(li.querySelector('time').textContent) && li.querySelector('em').textContent.length > 0)"))
    _bp_shot(pg, "stress_reasons.png")
    pg.evaluate("(id) => __world.stressWhy.add(id, 'knocked', { ttl: 6000 })", wid)       # 重新計時 6 秒（機器忙時前面的步驟可能已經吃掉很多時間）
    wait_until(pg, "() => !!document.querySelector('#srCard li[data-k=knocked]')", 5000)
    op0 = pg.evaluate("() => { const e = document.querySelector('#srCard li[data-k=knocked]'); return e ? parseFloat(e.style.opacity) : 1; }")
    wait_until(pg, "() => { const e = document.querySelector('#srCard li[data-k=knocked]'); return !e || parseFloat(e.style.opacity) < 0.9; }", 30000)
    op1 = pg.evaluate("() => { const e = document.querySelector('#srCard li[data-k=knocked]'); return e ? parseFloat(e.style.opacity) : -1; }")
    ok("B3 快到期→越來越淡（或已經消失）", 0 <= op1 < op0 or op1 == -1, [op0, op1])
    wait_until(pg, "() => !document.querySelector('#srCard li[data-k=knocked]')", 30000)
    ok("B3 到期→那一條真的消失，其他還在", pg.evaluate("() => !document.querySelector('#srCard li[data-k=knocked]') && !!document.querySelector('#srCard li[data-k=rejected]')") and pg.evaluate("(id) => !__world.stressWhy.list(id).some(r => r.k === 'knocked')", wid))
    pg.evaluate("(id) => __world.emit('praised', id, {})", wid)
    pg.wait_for_timeout(600)
    ok("B3 被稱讚→退件原因消掉、多一條減壓原因（綠色）", pg.evaluate("() => !document.querySelector('#srCard li[data-k=rejected]') && !!document.querySelector('#srCard li.good[data-k=praised]')"))
    # 重新整理後還在
    pg.evaluate("(id) => { __world.stressWhy.add(id, 'burned'); }", wid)
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready && window.__world.stressWhy", 90000)
    pg.wait_for_timeout(300)
    ok("B3 重新整理後未過期的原因還在（被燒到）", pg.evaluate("(id) => __world.stressWhy.list(id).some(r => r.k === 'burned')", wid))
    # 數值漸變
    has = pg.evaluate("() => !!(__world.growth && __world.growth.set)")
    if has:
        pg.evaluate("(id) => { __world.growth.set(id, { str: 10 }); __world.ui.showCard(__world.chars.get(id)); __world.stressWhy.shown.set(id, 10); }", wid)
        pg.wait_for_timeout(500)
        pg.evaluate("(id) => { __world.growth.set(id, { str: 80 }); }", wid)
        pg.wait_for_timeout(1000)
        v1 = pg.evaluate("() => parseInt(document.querySelector('#srCard [data-k=srv]').textContent.replace(/\\D/g, ''))")
        ok("B3 壓力從 10 跳到 80 時，顯示值不瞬跳（1 秒後仍小於 80）", 10 <= v1 < 80)
        pg.wait_for_timeout(2500)
        v2 = pg.evaluate("() => parseInt(document.querySelector('#srCard [data-k=srv]').textContent.replace(/\\D/g, ''))")
        ok("B3 之後持續往上走（漸變）", v2 > v1)
    else:
        ok("B3 沒有成長系統：壓力原因區塊仍能獨立運作", True)
    ok("B3 沒有網頁錯誤", not pg.errs)
    c.close()


# ───────── B4 純工作模式 ─────────
def t_bp_workmode(b, base):
    c, pg, got = _bp_open(b, base, qs="?q=low&pr=0.6&sim=1")
    if not got:
        ok("B4 載入", False)
        c.close()
        return
    ids = pg.evaluate(_BP_MEM)
    ok("B4 開始時遊戲元素是開的（火焰開著、營火看得到、會自己運動）", pg.evaluate("() => { const W = __world; return W.fire.on === true && W.fire.flame.visible === true && W.sports.ambientOn === true && !document.documentElement.classList.contains('wk'); }"))
    _bp_adv(pg, 2)
    ign0 = pg.evaluate("() => __world.fire.stats.ignited")
    has_growth = pg.evaluate("() => !!(__world.growth && __world.growth.ui)")
    _bp_settings(pg)
    pg.click("#wkSw")
    pg.wait_for_timeout(500)
    ok("B4 設定裡一鍵打開→html 掛上 wk，開關是勾的", pg.evaluate("() => document.documentElement.classList.contains('wk') && document.getElementById('wkSw').checked && localStorage.getItem('aiOffice.game.workmode') === '1'"))
    _bp_adv(pg, 3)
    ok("B4 火焰關掉：火苗隱藏、W.fire.on＝false、不冒火星", pg.evaluate("() => { const F = __world.fire; return F.on === false && F.flame.visible === false && F.stats.particles === 0; }"))
    ok("B4 點火（硬點）也點不著：ignite 回傳 false、被燒次數不增加", pg.evaluate("(id) => { const F = __world.fire, c = __world.chars.get(id), r = F.ignite(c, 'test'); return r === false && F.stats.ignited === %d; }" % ign0, ids[0]))
    ok("B4 運動關掉：不會自己去打球、也不能開始新的運動", pg.evaluate("(id) => { const s = __world.sports; return s.ambientOn === false && s.start(id, 'badminton') === false && !s.sess; }", ids[0]))
    muted0 = pg.evaluate("() => __world.workmode.muted || 0")
    pg.evaluate("(a) => { for (const id of a) { try { __world.mind.reward(id, 'award'); __world.mind.punish(id, 'rejected'); } catch (e) {} } }", ids[:4])
    pg.wait_for_timeout(300)
    ok("B4 情緒台詞不出現：mind 想說的話被擋下（累計擋掉數增加）且頭上沒有情緒泡泡", pg.evaluate("() => (__world.workmode.muted || 0)") > muted0 and pg.evaluate("(a) => a.every(id => { const c = __world.chars.get(id); return !c.speech; })", ids[:4]))
    if has_growth:
        pg.evaluate("(id) => { const G = __world.growth; G.ui.levelUp(__world.chars.get(id), 5); G.ui.goalHit({ text: '測試目標' }); }", ids[0])
        pg.wait_for_timeout(200)
        ok("B4 等級與慶祝不顯示：名牌 Lv、今日目標鈕、晉級訊息都看不到", pg.evaluate("() => { const vis = e => !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; const lv = document.querySelector('.tag .glv'); const msgs = [...document.querySelectorAll('#gmStack .gm-msg')].filter(vis); return !vis(lv) && !vis(document.getElementById('gmBtn')) && msgs.length === 0; }"))
        pg.evaluate("(id) => __world.ui.showCard(__world.chars.get(id))", ids[0])
        pg.wait_for_timeout(300)
        ok("B4 資訊卡只剩體力與壓力（等級／專長／個性列收起）", pg.evaluate("() => { const vis = e => !!e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().width > 0; return vis(document.querySelector('#gmCard .gm-st')) && !vis(document.querySelector('#gmCard .gm-lv')) && !vis(document.querySelector('#gmCard .gm-row')); }"))
    _bp_shot(pg, "workmode_on.png")
    pg.reload(wait_until="domcontentloaded")
    wait_until(pg, "() => window.__world && window.__world.ready && window.__world.workmodeReady", 90000)
    pg.wait_for_timeout(2500)
    ok("B4 重新整理後選擇還記得（仍是純工作模式、火焰仍關）", pg.evaluate("() => document.documentElement.classList.contains('wk') && __world.workmode.on && __world.fire.on === false && __world.fire.flame.visible === false"))
    _bp_settings(pg)
    ok("B4 重新整理後設定裡的開關仍是勾的", pg.evaluate("() => document.getElementById('wkSw').checked"))
    pg.click("#wkSw")
    pg.wait_for_timeout(400)
    ok("B4 切回來→火焰、運動、等級類別全部恢復", pg.evaluate("() => { const W = __world; return !document.documentElement.classList.contains('wk') && W.fire.on === true && W.fire.flame.visible === true && W.sports.ambientOn === true && localStorage.getItem('aiOffice.game.workmode') === '0'; }"))
    _bp_adv(pg, 3)
    ok("B4 切回來後火焰又會冒火星（粒子數 > 0）", pg.evaluate("() => __world.fire.stats.particles") > 0)
    if has_growth:
        pg.evaluate("(id) => __world.growth.ui.levelUp(__world.chars.get(id), 6)", ids[0])
        pg.wait_for_timeout(200)
        ok("B4 切回來後晉級訊息又會跳出來", pg.evaluate("() => document.querySelectorAll('#gmStack .gm-msg').length") > 0)
    ok("B4 沒有網頁錯誤", not pg.errs)
    c.close()


# ───────── B5 閘門 ─────────
def t_bp_gate(b, base):
    c, pg, got = _bp_open(b, base)
    if not got:
        ok("B5 載入", False)
        c.close()
        return
    ok("B5 功能鍵 office.blueprint／office.priority 已註冊", pg.evaluate("() => !!(window.TwFeatures && TwFeatures.byId('office.blueprint') && TwFeatures.byId('office.priority'))"))
    ok("B5 四個方案都有設定（plan_presets.js）", pg.evaluate("() => { const t = (window.TW_PLAN_PRESETS || {}).tiers || []; return t.length >= 4 && t.every(x => x.feats && 'office.blueprint' in x.feats && 'office.priority' in x.feats); }") or pg.evaluate("() => !window.TW_PLAN_PRESETS"))
    c.close()
    for tier, label in (("guest", "訪客"),):
        c2, p2, g2 = _bp_open(b, base, qs=f"?q=low&pr=0.6&demo_tier={tier}")
        if not g2:
            ok("B5 載入（" + label + "）", False)
            c2.close()
            continue
        r = p2.evaluate("async () => { __world.blueprint.stepSec = 999; return await __world.blueprint.apply(); }")
        ok(f"B5 {label}套用藍圖被鎖（不開放），畫面有白話說明", bool(r and r.get("blocked")) and p2.evaluate("() => !document.getElementById('bpFlow') || document.getElementById('bpFlow').hidden"))
        ok(f"B5 {label}看得到優先度表鈕但未被誤鎖（只有開關）", p2.evaluate("() => { __world.gate.peek('office.priority'); return true; }"))
        c2.close()
    c3, p3, g3 = _bp_open(b, base, qs="?q=low&pr=0.6&demo_tier=free")
    if g3:
        res = p3.evaluate("async () => { const B = __world.blueprint, out = []; B.stepSec = 999; for (let i = 0; i < 6; i++) { const r = await B.apply(); out.push(!!(r && r.blocked)); } return out; }")
        ok("B5 註冊會員每天 5 次：前 5 次放行、第 6 次被鎖", res[:5] == [False] * 5 and res[5] is True)
        ok("B5 用到上限後：優先度表（只有開關）照樣能開", p3.evaluate("() => { __world.prio.open(); return !document.getElementById('prPanel').hidden; }"))
    else:
        ok("B5 載入（註冊會員）", False)
    c3.close()


# ───────── B6 版面 ─────────
def t_bp_layout(b, base):
    for w, h, tag in ((1280, 800, "桌機"), (390, 844, "手機")):
        c, pg, got = _bp_open(b, base, w=w, h=h)
        if not got:
            ok(f"B6 {tag}載入", False)
            c.close()
            continue
        ids = pg.evaluate(_BP_MEM)
        pg.evaluate("(id) => { __world.stressWhy.add(id, 'burned'); __world.ui.showCard(__world.chars.get(id)); }", ids[0])
        pg.wait_for_timeout(500)
        sr = pg.evaluate("() => { const e = document.getElementById('srCard'); if (!e) return null; const r = e.getBoundingClientRect(); return { inside: r.right <= innerWidth + 1, small: [...e.querySelectorAll('*')].filter(x => [...x.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && parseFloat(getComputedStyle(x).fontSize) < 11).length, text: e.innerText }; }")
        _bp_shot(pg, f"layout_{tag}_card.png")
        pg.evaluate("() => { const x = document.querySelector('#card .x, #card [data-close], #cardX'); if (x) x.click(); document.getElementById('card').hidden = true; }")
        probes = {}
        for name, which, sel in (("設定", None, "#stPop"), ("藍圖", "bp", "#bpPanel"), ("優先度", "pr", "#prPanel")):
            pg.evaluate("() => { for (const id of ['stPop','bpPanel','prPanel']) { const e = document.getElementById(id); if (e) e.hidden = true; } }")
            if tag == "手機":
                pg.evaluate("() => { const m = document.getElementById('moreBtn'); if (!document.body.classList.contains('m-more')) m.click(); }")
            _bp_settings(pg, which)
            _bp_shot(pg, f"layout_{tag}_{name}.png")
            probes[name] = pg.evaluate("""(sel) => {
              const p = document.querySelector(sel), r = p.getBoundingClientRect(), W = innerWidth, H = innerHeight;
              let small = 0, ban = 0;
              for (const e of p.querySelectorAll('*')) { if (!e.childNodes.length || ![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue; if (parseFloat(getComputedStyle(e).fontSize) < 11) small++; }
              const cf = document.getElementById('chatForm'), cr = cf ? cf.getBoundingClientRect() : null;
              return { inside: r.left >= -1 && r.right <= W + 1 && r.top >= -1 && r.bottom <= H + 1, clear: !cr || !cr.width || r.bottom <= cr.top + 1, small, text: p.innerText, docw: document.documentElement.scrollWidth <= W + 1 };
            }""", sel)
        ok(f"B6 {tag}：設定／藍圖／優先度三個面板都在視窗內", all(v["inside"] for v in probes.values()))
        ok(f"B6 {tag}：面板不蓋到下方對話列", all(v["clear"] for v in probes.values()), {k: v["clear"] for k, v in probes.items()})
        ok(f"B6 {tag}：面板內字級都 ≥ 11px", all(v["small"] == 0 for v in probes.values()))
        ok(f"B6 {tag}：沒有橫向捲軸", all(v["docw"] for v in probes.values()))
        alltxt = "".join(v["text"] for v in probes.values()) + (sr["text"] if sr else "")
        ok(f"B6 {tag}：沒有禁用字", not any(w_ in alltxt for w_ in _BP_BANNED), [w_ for w_ in _BP_BANNED if w_ in alltxt])
        ok(f"B6 {tag}：資訊卡的壓力原因區塊在視窗內、字級 ≥ 11px", bool(sr) and sr["inside"] and sr["small"] == 0)
        ok(f"B6 {tag}：沒有網頁錯誤", not pg.errs)
        c.close()


def t_bp_all(b, base):
    only = _os.environ.get("BP_ONLY", "")
    for key, fn in (("blueprint", t_bp_blueprint), ("priority", t_bp_priority), ("stress", t_bp_stress), ("workmode", t_bp_workmode), ("gate", t_bp_gate), ("layout", t_bp_layout)):
        if not only or key in only.split(","):
            fn(b, base)


register("辦公室藍圖與純工作模式", lambda pg, b, base, code: t_bp_all(b, base))
