# 驗收段落「辦公室成績單、離開成果包、任務重播」（2026-11-16，第二輪參考研究第 4、5、9 項）
#   site/office/world/js/scorecard.js、awaypack.js、replay.js
#   ① 成績單：真的餵一串派工事件（開工→5 次工具呼叫→交件，事件自帶時間差 12 分 3 秒）→ 產生一張卡，數字逐項對（耗時、工具次數、測試、被退次數、誰做的）；
#      失敗一次再做好 → 被退次數變 1；頂列鈕小紅點、開關面板、上一件／下一件／歷史清單、員工資訊卡的入口、總覽通知「完成」點下去開對應那張
#   ② 重播：點「重播這件」→ 角落「重播中」、拉桿用滑鼠真的拖 → 角色位置跟著變、工作段的說明依工具類別換；1×／4× 真的差 4 倍；暫停；播到底自動回即時；
#      「結束重播」鈕；重播不產生新成績單、結束後角色不再是被操控狀態
#   ③ 離開成果包：模擬分頁隱藏→時鐘快轉 12 分鐘→回來 → 跳出摘要（完成、沒做成、卡住、晉級的人數與名字都對）；知道了可關；不到門檻不跳；
#      「之後不再顯示」寫進設定、再離開不跳；沒有成果時自動不打擾
#   ④ 到點提醒：瀏覽器同意 → 超過平均耗時沒交件 → 真的建立瀏覽器通知（分頁在背景）；瀏覽器拒絕 → 畫面上的提示
#   ⑤ 功能鍵 office.scorecard／awaypack／replay 已登記（features.js、四個方案範本、gate.js）；文案沒有禁用字；手機 390 寬沒有橫向溢出、字不小於 11px
# 環境變數 R2B_SHOTS 指到資料夾時存截圖。
# flake8: noqa

import os as _os
import re as _re

_SR_BAD = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")

_SR_NOTIF = """
(() => {
  window.__nots = [];
  class FN { constructor(t, o) { window.__nots.push({ t: t, body: (o || {}).body || '' }); this.close = () => {}; } }
  FN.permission = window.__permStart || 'default';
  FN.requestPermission = () => { FN.permission = window.__permAnswer || 'granted'; return Promise.resolve(FN.permission); };
  window.Notification = FN;
})();
"""


def _sr_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _sr_shot(pg, name):
    d = _os.environ.get("R2B_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _sr_open(b, base, w=1440, h=900, touch=False, perm="granted", ls=None, q=""):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch, reduced_motion="reduce")   # 減少動態：派工演出直接收尾，驗收不用等角色走路
    init = {"aiOffice.daytime": "day"}
    init.update(ls or {})
    c.add_init_script("window.__permAnswer=%r;" % perm)
    c.add_init_script(_SR_NOTIF)
    c.add_init_script("try{" + "".join("localStorage.setItem(%r,%r);" % (k, v) for k, v in init.items()) + "}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(60000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "Failed to load resource" not in m.text and "ERR_" not in m.text else None)
    pg.goto(_sr_root(base) + "/office/world.html?ambient=0&q=low&pr=0.6" + q, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat && window.__world.chars.get('ceo') && (window.__world.chars.get('ceo')._sx > 0 || innerWidth < 500) && window.__world.scorecard && window.__world.replay && window.__world.away", 150000)
    # 下班時間（台北 18:00 後）成長組的「今日結算」卡會在第一件完成時自動蓋住整個畫面，跟本段要驗的東西無關：驗收期間把它拿掉
    pg.evaluate("() => { new MutationObserver(() => { const d = document.getElementById('gmDay'); if (d) d.remove(); }).observe(document.body, { childList: true, subtree: true }); }")
    return c, pg, got


# 餵一件完整的派工事件：開工在 end-dur、5 次工具呼叫、end 交件（事件自帶時間，耗時由時間差決定）
_SR_JOB = """(a) => {
  const W = __world, S = W.state, e = (name, o) => S.emit(Object.assign({ hook_event_name: name, live: true }, o));
  const t0 = a.end - a.dur, aid = a.aid;
  e('SubagentStart', { uid: 's:' + aid, ts: t0, agent_id: aid, agent_type: a.who, description: a.title });
  const cats = a.cats || ['read', 'read', 'write', 'write', 'test'];
  cats.forEach((c, i) => e('PreToolUse', { uid: 't:' + aid + i, ts: t0 + Math.round(a.dur * (i + 1) / (cats.length + 1)), agent_id: aid, tool_category: c }));
  if (!a.noStop) e('SubagentStop', { uid: 'p:' + aid, ts: a.end, agent_id: aid, agent_type: a.who, status: a.failed ? 'failed' : 'completed', last_assistant_message: a.msg || '做完了' });
  return true;
}"""


def _sr_who(pg):
    return pg.evaluate("() => { const W = __world; for (const c of W.chars.values()) { if (!c.spec.isCeo && !c.spec.pet && !c.jobless && !c.away) return c.spec.id; } return null; }")


def _sr_pos(pg, who):
    return pg.evaluate("(id) => { const p = __world.chars.get(id).object3D.position; return [p.x, p.z]; }", who)


def _sr_text(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); return e && !e.hidden ? e.innerText : ''; }", sel)


def _sr_scorecard(b, base):
    c, pg, got = _sr_open(b, base)
    try:
        ok("成績單：辦公室載入完成（含成績單、重播、離開成果包三支）", got, "載入逾時")
        if not got:
            return
        who = _sr_who(pg)
        nick = pg.evaluate("(id) => __world.chars.get(id).spec.nick", who)
        ok("成績單：頂列有「成績單」鈕、一開始沒有紅點", pg.evaluate("() => { const b = document.getElementById('scBtn'); return !!b && !b.hidden && document.getElementById('scDot').hidden; }"), "鈕或紅點狀態不對")
        now = pg.evaluate("() => Date.now()")
        pg.evaluate(_SR_JOB, {"end": now - 5000, "dur": 723000, "aid": "ag1", "who": who, "title": "整理報表", "msg": "報表整理好了"})
        wait_until(pg, "() => __world.scorecard.cards.length === 1", 5000)
        c1 = pg.evaluate("() => __world.scorecard.cards[0]")
        ok("成績單：交件後多一張卡，誰做的對", c1 and c1["who"] == who and c1["nick"] == nick, c1)
        ok("成績單：耗時＝事件時間差 723 秒", c1 and c1["dur"] == 723000, c1 and c1["dur"])
        ok("成績單：工具呼叫 5 次、其中測試 1 次、沒被退過、結果成功", c1 and c1["toolN"] == 5 and c1["tests"] == 1 and c1["retries"] == 0 and not c1["failed"], c1)
        ok("成績單：頂列小紅點顯示 1", pg.evaluate("() => { const d = document.getElementById('scDot'); return !d.hidden && d.textContent === '1'; }"), "沒有紅點")
        pg.click("#scBtn")
        wait_until(pg, "() => { const p = document.getElementById('scPanel'); return p && !p.hidden; }", 4000)
        tx = _sr_text(pg, "#scPanel")
        ok("成績單：面板寫著誰、任務、順利交件", nick in tx and "整理報表" in tx and "順利交件" in tx, tx[:200])
        ok("成績單：面板耗時「12 分 3 秒」", "12 分 3 秒" in tx, tx[:300])
        ok("成績單：面板用量「5 次工具呼叫」且標明估算", "5 次工具呼叫" in tx and "估算" in tx, tx[:300])
        ok("成績單：面板被退次數 0（一次就過）、測試有跑 1 次", "0 次（一次就過）" in tx and "有跑 1 次" in tx, tx[:300])
        ok("成績單：開過之後紅點消失", pg.evaluate("() => document.getElementById('scDot').hidden"), "紅點還在")
        _sr_shot(pg, "r2b_scorecard_card.png")
        # 失敗一次、再做好：被退次數
        pg.evaluate(_SR_JOB, {"end": now - 4000, "dur": 120000, "aid": "ag2", "who": who, "title": "整理報表", "failed": True, "msg": "錯誤：欄位對不上", "cats": ["read", "write"]})
        wait_until(pg, "() => __world.scorecard.cards.length === 2", 5000)
        pg.evaluate(_SR_JOB, {"end": now - 3000, "dur": 300000, "aid": "ag3", "who": who, "title": "整理報表", "msg": "這次對了", "cats": ["read", "write", "test", "test"]})
        wait_until(pg, "() => __world.scorecard.cards.length === 3", 5000)
        cs = pg.evaluate("() => __world.scorecard.cards.map(c => ({ f: c.failed, r: c.retries, n: c.toolN }))")
        ok("成績單：失敗那張標失敗、被退 0；之後做好的那張被退 1 次", len(cs) == 3 and cs[1]["f"] and cs[1]["r"] == 0 and (not cs[0]["f"]) and cs[0]["r"] == 1, cs)
        tx = _sr_text(pg, "#scPanel")
        ok("成績單：正在看的卡不被新卡擠掉（仍是第 1 張、現在是第 3／3 件）", "第 3／3 件" in tx and "12 分 3 秒" in tx, tx[:120])
        pg.click("[data-sc=next]")
        tx = _sr_text(pg, "#scPanel")
        ok("成績單：下一件 → 第 2／3 件，是沒做成那張、寫第 1 次沒過", "第 2／3 件" in tx and "沒做成" in tx, tx[:200])
        pg.click("[data-sc=next]")
        tx = _sr_text(pg, "#scPanel")
        ok("成績單：再下一件 → 第 1／3 件，被退 1 次、測試有跑 2 次", "第 1／3 件" in tx and "做好之前沒過 1 次" in tx and "有跑 2 次" in tx, tx[:300])
        ok("成績單：最新一張的「下一件」鈕反灰", pg.evaluate("() => document.querySelector('#scPanel [data-sc=next]').disabled"), "沒有反灰")
        pg.click("[data-sc=list]")
        n = pg.evaluate("() => document.querySelectorAll('#scPanel [data-sc-i]').length")
        ok("成績單：歷史清單列出 3 張", n == 3, n)
        _sr_shot(pg, "r2b_scorecard_list.png")
        pg.click("#scPanel [data-sc-i='2']")
        tx = _sr_text(pg, "#scPanel")
        ok("成績單：從清單點最舊那張 → 開出 12 分 3 秒那張", "第 3／3 件" in tx and "12 分 3 秒" in tx, tx[:120])
        pg.click("#scPanel .x")
        ok("成績單：× 關得掉", pg.evaluate("() => document.getElementById('scPanel').hidden"), "沒關")
        # 資訊卡入口
        pg.evaluate("(id) => __world.ui.showCard(__world.chars.get(id))", who)
        wait_until(pg, "() => document.getElementById('scCardB')", 3000)
        ok("成績單：員工資訊卡有「最近成績單」一行", "最近成績單" in _sr_text(pg, "#scCardB"), _sr_text(pg, "#card")[:200])
        pg.click("#scCardB [data-sc-card]")
        ok("成績單：點資訊卡那一行 → 開出成績單面板", pg.evaluate("() => !document.getElementById('scPanel').hidden"), "沒開")
        pg.click("#scPanel .x")
        # 重新整理後歷史還在
        pg.reload(wait_until="domcontentloaded")
        wait_until(pg, "() => window.__world && window.__world.ready && window.__world.scorecard && window.__world.replay", 90000)
        ok("成績單：重新整理後歷史清單還在（存在本機）", pg.evaluate("() => __world.scorecard.cards.length") == 3, pg.evaluate("() => __world.scorecard.cards.length"))
        # 總覽通知：派一件做完，等總覽偵測出「完成」通知，點下去開對應那張
        pg.evaluate(_SR_JOB, {"end": pg.evaluate("() => Date.now()"), "dur": 90000, "aid": "ag9", "who": who, "title": "通知那件", "cats": ["read", "write"]})
        got_n = wait_until(pg, "() => (__world.overview.notes || []).some(n => n.kind === 'done')", 40000)
        ok("成績單：總覽出現「完成」通知（總覽自己的偵測）", got_n, "40 秒內沒有完成通知")
        if got_n:
            pg.click("#ovBtn")
            pg.click("#ovTabNt")
            wait_until(pg, "() => document.querySelector('.ov-nt[data-k=done]')", 3000)
            pg.click(".ov-nt[data-k=done]")
            wait_until(pg, "() => !document.getElementById('scPanel').hidden", 3000)
            tx = _sr_text(pg, "#scPanel")
            ok("成績單：點總覽的完成通知 → 開出對應那張成績單", "通知那件" in tx, tx[:150])
            _sr_shot(pg, "r2b_scorecard_from_notice.png")
        ok("成績單：頁面沒有 JS 錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _sr_replay(b, base):
    c, pg, got = _sr_open(b, base)
    try:
        ok("重播：辦公室載入完成", got, "載入逾時")
        if not got:
            return
        who = _sr_who(pg)
        now = pg.evaluate("() => Date.now()")
        pg.evaluate(_SR_JOB, {"end": now - 1000, "dur": 600000, "aid": "rp1", "who": who, "title": "重播這一件", "cats": ["read", "write", "search", "test", "write"], "msg": "弄好了"})
        wait_until(pg, "() => __world.scorecard.cards.length === 1", 5000)
        ok("重播：成績單面板有「重播這件」鈕", (pg.click("#scBtn") or True) and pg.evaluate("() => !!document.querySelector('#scPanel [data-sc=replay]')"), "沒有鈕")
        wait_until(pg, "() => { const W = __world; return [...W.state.agents.values()].every(a => a.phase === 'idle'); }", 8000)
        seat = pg.evaluate("(id) => { const c = __world.chars.get(id), h = c.homeSpot || __world.spots.find(q => q.name === 'seat:' + id); return [h.seat.x, h.seat.z]; }", who)
        n0 = pg.evaluate("() => __world.scorecard.cards.length")
        pg.click("#scPanel [data-sc=replay]")
        wait_until(pg, "() => __world.replay.on", 4000)
        ok("重播：角落出現「重播中」", "重播中" in _sr_text(pg, "#rpTag"), _sr_text(pg, "#rpTag"))
        ok("重播：控制列在、成績單面板收起、被重播的人標成接管", pg.evaluate("(id) => !document.getElementById('rpBar').hidden && document.getElementById('scPanel').hidden && __world.chars.get(id).piloted === true", who), "狀態不對")
        ov = pg.evaluate("() => { const t = document.getElementById('rpTag').getBoundingClientRect(), o = []; for (const e of document.querySelectorAll('#bar button, #bar .btn, #bar .seg, #rpBar, #card, #ovPanel')) { if (e.id === 'rpBar' && false) continue; const r = e.getBoundingClientRect(); if (r.width && r.height && getComputedStyle(e).visibility !== 'hidden' && !e.closest('[hidden]') && t.left < r.right && t.right > r.left && t.top < r.bottom && t.bottom > r.top) o.push(e.id || e.textContent.slice(0, 8)); } return o; }")
        ok("重播：「重播中」標籤沒有蓋到頂列按鈕或其他面板", ov == [], ov)
        _sr_shot(pg, "r2b_replay_start.png")
        pg.click("#rpPlay")
        ta = pg.evaluate("() => __world.replay.t")
        pg.wait_for_timeout(700)
        ok("重播：按暫停 → 時間不再前進", pg.evaluate("() => __world.replay.t") == ta and not pg.evaluate("() => __world.replay.playing"), "暫停後時間還在走")
        total = pg.evaluate("() => __world.replay.total")
        ok("重播：時間軸總長合理（被壓縮到 20～90 秒，不是原本的 10 分鐘）", 20 <= total <= 90, total)
        # 真的用滑鼠拖拉桿
        box = pg.evaluate("() => { const r = document.getElementById('rpSeek').getBoundingClientRect(); return { x: r.left, y: r.top + r.height / 2, w: r.width }; }")
        poses = {}
        for frac in (0.01, 0.14, 0.40, 0.62, 0.78, 0.97):
            pg.mouse.move(box["x"] + box["w"] * frac, box["y"])
            pg.mouse.down()
            pg.mouse.move(box["x"] + box["w"] * frac + 1, box["y"])
            pg.mouse.up()
            pg.wait_for_timeout(120)
            poses[frac] = (_sr_pos(pg, who), pg.evaluate("() => __world.replay.t"), pg.evaluate("() => document.getElementById('rpCap').innerText"))
        ts = [v[1] for v in poses.values()]
        ok("重播：拖拉桿 → 重播時間跟著變（由小到大）", ts == sorted(ts) and ts[-1] - ts[0] > total * 0.6, ts)
        distinct = {(round(v[0][0], 1), round(v[0][1], 1)) for v in poses.values()}
        ok("重播：拖到不同位置 → 角色位置真的不同（至少 4 個不同點）", len(distinct) >= 4, list(distinct))
        pg.evaluate("() => __world.replay.seek(0.2)")
        pg.wait_for_timeout(400)
        p0 = _sr_pos(pg, who)
        d0 = ((p0[0] - seat[0]) ** 2 + (p0[1] - seat[1]) ** 2) ** 0.5
        ok("重播：跳到最前面（0.2 秒）→ 角色在自己的座位上", d0 < 0.9, (d0, p0, seat, poses[0.01]))
        ok("重播：走去領任務那段的說明", "領任務" in poses[0.14][2] or "走去" in poses[0.14][2], poses[0.14][2])
        # 工作段：依工具類別換說明
        capw = []
        for k in range(5):
            pg.evaluate("() => { const R = __world.replay, w = R.segs.find(s => s.k === 'work'); R.seek(w.t0 + w.evs[%d].at + 0.05); }" % k)
            pg.wait_for_timeout(80)
            capw.append(pg.evaluate("() => document.getElementById('rpCap').innerText"))
        ok("重播：工作段依當時工具類別換說明（讀、寫、查、測試）", "讀資料" in capw[0] and "寫程式" in capw[1] and "查資料" in capw[2] and "跑測試" in capw[3], capw)
        _sr_shot(pg, "r2b_replay_work.png")
        pg.evaluate("() => { const R = __world.replay, s = R.segs[6]; R.seek(s.t0 + 1); }")
        pg.wait_for_timeout(120)
        pc = pg.evaluate("() => { const c = __world.chars.get('%s').object3D.position, d = __world.findSpots('ceo_front')[0]; return Math.hypot(c.x - d.x, c.z - d.z); }" % who)
        ok("重播：交件那一段，角色站在 CEO 桌前", pc < 0.8, pc)
        _sr_shot(pg, "r2b_replay_deliver.png")
        # 速度：1× 與 4× 差 4 倍
        pg.evaluate("() => __world.replay.seek(2)")
        pg.click("#rpPlay")
        t_a = pg.evaluate("() => __world.replay.t")
        pg.wait_for_timeout(1000)
        d1 = pg.evaluate("() => __world.replay.t") - t_a
        pg.click("#rpPlay")
        pg.evaluate("() => __world.replay.seek(2)")
        pg.click("[data-rs='4']")
        ok("重播：按 4× → 該鈕亮起（aria-pressed）", pg.evaluate("() => document.querySelector('[data-rs=\"4\"]').getAttribute('aria-pressed') === 'true' && __world.replay.speed === 4"), "沒切到 4×")
        pg.click("#rpPlay")
        t_b = pg.evaluate("() => __world.replay.t")
        pg.wait_for_timeout(1000)
        d4 = pg.evaluate("() => __world.replay.t") - t_b
        ok("重播：4× 的前進量約是 1× 的 4 倍", d1 > 0.1 and 3.0 <= d4 / d1 <= 6.5, (d1, d4))
        # 播到底：自動回到即時
        pg.evaluate("() => __world.replay.seek(__world.replay.total - 0.3)")
        got_end = wait_until(pg, "() => !__world.replay.on", 8000)
        ok("重播：播到底自動結束、回到即時（角落標籤與控制列消失）", got_end and pg.evaluate("() => document.getElementById('rpTag').hidden && document.getElementById('rpBar').hidden"), "沒有自動回即時")
        ok("重播：結束後角色不再是接管狀態", not pg.evaluate("(id) => __world.chars.get(id).piloted", who), "還被接管")
        ok("重播：重播沒有產生新的成績單", pg.evaluate("() => __world.scorecard.cards.length") == n0, pg.evaluate("() => __world.scorecard.cards.length"))
        # 「結束重播」鈕
        pg.evaluate("(id) => __world.replay.play(__world.scorecard.cards[0].id)", who)
        wait_until(pg, "() => __world.replay.on", 3000)
        pg.click("#rpExit")
        ok("重播：按「結束重播」立刻回到即時", pg.evaluate("() => !__world.replay.on && document.getElementById('rpTag').hidden"), "沒有結束")
        ok("重播：頁面沒有 JS 錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _sr_away(b, base):
    c, pg, got = _sr_open(b, base)
    try:
        ok("成果包：辦公室載入完成", got, "載入逾時")
        if not got:
            return
        who = _sr_who(pg)
        pg.evaluate("() => { window.__off = 0; const rn = Date.now.bind(Date); Date.now = () => rn() + window.__off; }")
        hide = "() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }"
        show = "() => { Object.defineProperty(document, 'hidden', { value: false, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); }"
        # 離開 3 分鐘（不到門檻 10 分鐘）：不該跳
        pg.evaluate(hide)
        pg.evaluate("() => { window.__off = 3 * 60000; }")
        pg.evaluate(show)
        pg.wait_for_timeout(1500)
        ok("成果包：只離開 3 分鐘 → 不跳摘要", pg.evaluate("() => document.getElementById('awPanel').hidden"), "不該跳卻跳了")
        # 離開 12 分鐘，期間：做完 2 件（其中 1 件沒做成）、派出 1 件沒收尾（會卡住）、一人晉級
        pg.evaluate("() => { window.__off = 0; }")
        pg.evaluate(hide)
        left = pg.evaluate("() => Date.now()")
        pg.evaluate(_SR_JOB, {"end": left + 60000, "dur": 50000, "aid": "aw1", "who": who, "title": "離開時做完的", "cats": ["read", "write"], "msg": "好了"})
        pg.evaluate(_SR_JOB, {"end": left + 90000, "dur": 40000, "aid": "aw2", "who": who, "title": "離開時失敗的", "cats": ["read"], "failed": True, "msg": "錯誤：連不上"})
        other = pg.evaluate("(w) => { for (const c of __world.chars.values()) { if (!c.spec.isCeo && !c.spec.pet && !c.jobless && c.spec.id !== w) return c.spec.id; } return null; }", who)
        pg.evaluate(_SR_JOB, {"end": left + 100000, "dur": 20000, "aid": "aw3", "who": other, "title": "還在做的那件", "cats": ["read"], "noStop": True})
        pg.evaluate("(id) => __world.emit('promoted', id, {})", who)
        pg.wait_for_timeout(1300)   # 讓總覽的輪詢先記下基準
        pg.evaluate("(id) => __world.emit('promoted', id, {})", who)
        pg.evaluate("() => { window.__off = 12 * 60000 + 5000; }")
        pg.evaluate(show)
        got_p = wait_until(pg, "() => !document.getElementById('awPanel').hidden", 5000)
        ok("成果包：離開 12 分鐘回來 → 跳出「你不在的時候」", got_p, "沒有跳出")
        tx = _sr_text(pg, "#awPanel")
        _sr_shot(pg, "r2b_awaypack.png")
        ok("成果包：標題與離開時間（約 12 分鐘）", "你不在的時候" in tx and "12 分鐘" in tx, tx[:160])
        ok("成果包：完成 1 件（寫出標題）", "完成了" in tx and "離開時做完的" in tx, tx[:400])
        ok("成果包：沒做成 1 件", "沒做成" in tx and "離開時失敗的" in tx, tx[:400])
        nick_o = pg.evaluate("(id) => __world.chars.get(id).spec.nick", other)
        ok("成果包：誰卡住（寫出還在做的那位與任務）", "卡住" in tx and nick_o in tx and "還在做的那件" in tx, tx[:500])
        ok("成果包：誰晉級", "晉級了" in tx, tx[:500])
        ok("成果包：沒有禁用字", not _SR_BAD.search(tx), _SR_BAD.search(tx))
        pg.click("#awPanel [data-aw=close]")
        ok("成果包：「知道了」關得掉", pg.evaluate("() => document.getElementById('awPanel').hidden"), "沒關")
        # 看成績單鈕
        pg.evaluate("() => __world.away.show(Date.now() - 20 * 60000)")
        pg.click("#awPanel [data-aw=cards]")
        ok("成果包：「看成績單」→ 開出歷史清單", pg.evaluate("() => !document.getElementById('scPanel').hidden && document.querySelectorAll('#scPanel [data-sc-i]').length >= 2"), "沒開")
        pg.click("#scPanel .x")
        # 沒有成果時不打擾
        pg.evaluate("() => { __world.scorecard.cards.length = 0; __world.scorecard.running.clear(); }")
        pg.evaluate("() => { for (const k of [...__world.state.agents.keys()]) { const a = __world.state.agents.get(k); a.phase = 'idle'; } __world.overview.notes.length = 0; }")
        pg.evaluate("() => { window.__off = 0; }")
        pg.evaluate(hide)
        pg.evaluate("() => { window.__off = 15 * 60000; }")
        pg.evaluate(show)
        pg.wait_for_timeout(1500)
        ok("成果包：離開很久但什麼事都沒發生 → 不打擾", pg.evaluate("() => document.getElementById('awPanel').hidden"), "沒成果卻跳了")
        # 之後不再顯示
        pg.evaluate("() => { window.__off = 0; }")
        pg.evaluate(hide)
        left = pg.evaluate("() => Date.now()")
        pg.evaluate(_SR_JOB, {"end": left + 60000, "dur": 50000, "aid": "aw5", "who": who, "title": "又一件", "cats": ["read"]})
        pg.evaluate("() => { window.__off = 20 * 60000; }")
        pg.evaluate(show)
        wait_until(pg, "() => !document.getElementById('awPanel').hidden", 5000)
        pg.click("#awPanel [data-aw=never]")
        ls = pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.game.awaycfg') || '{}')")
        ok("成果包：「之後不再顯示」寫進設定（off）並關掉面板", ls.get("off") is True and pg.evaluate("() => document.getElementById('awPanel').hidden"), ls)
        pg.evaluate("() => { window.__off = 0; }")
        pg.evaluate(hide)
        left = pg.evaluate("() => Date.now()")
        pg.evaluate(_SR_JOB, {"end": left + 60000, "dur": 50000, "aid": "aw6", "who": who, "title": "再一件", "cats": ["read"]})
        pg.evaluate("() => { window.__off = 20 * 60000; }")
        pg.evaluate(show)
        pg.wait_for_timeout(1500)
        ok("成果包：關掉之後再離開回來 → 不跳", pg.evaluate("() => document.getElementById('awPanel').hidden"), "關掉了還跳")
        ok("成果包：頁面沒有 JS 錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _sr_remind(b, base, perm):
    tag = "同意" if perm == "granted" else "拒絕"
    c, pg, got = _sr_open(b, base, perm=perm)
    try:
        ok("提醒（%s）：辦公室載入完成" % tag, got, "載入逾時")
        if not got:
            return
        who = _sr_who(pg)
        pg.evaluate("() => { window.__off = 0; const rn = Date.now.bind(Date); Date.now = () => rn() + window.__off; }")
        now = pg.evaluate("() => Date.now()")
        for i in range(3):   # 三件平均 60 秒的歷史，才有預估
            pg.evaluate(_SR_JOB, {"end": now - 200000 + i * 1000, "dur": 60000, "aid": "h%d" % i, "who": who, "title": "歷史%d" % i, "cats": ["read"]})
        wait_until(pg, "() => __world.scorecard.cards.length === 3", 5000)
        ok("提醒（%s）：預估耗時＝歷史平均 60 秒" % tag, pg.evaluate("(id) => Math.round(__world.away.etaMs(id) / 1000)", who) == 60, pg.evaluate("(id) => __world.away.etaMs(id)", who))
        pg.evaluate("() => __world.away.settings()")
        pg.click("#awPanel [data-aw=notif]")
        wait_until(pg, "() => document.getElementById('awMsg')", 2000)
        pg.wait_for_timeout(300)
        msg = pg.evaluate("() => (document.getElementById('awMsg') || {}).textContent || ''")
        cfg = pg.evaluate("() => JSON.parse(localStorage.getItem('aiOffice.game.awaycfg') || '{}')")
        if perm == "granted":
            ok("提醒（同意）：按「開啟瀏覽器通知」→ 設定記下已開啟、說明寫已開啟", cfg.get("notif") is True and "已開啟" in msg, (cfg, msg))
        else:
            ok("提醒（拒絕）：按「開啟瀏覽器通知」被拒 → 設定不開、說明寫改用畫面提示", cfg.get("notif") is False and "畫面上的提示" in msg, (cfg, msg))
        _sr_shot(pg, "r2b_remind_settings_%s.png" % perm)
        pg.click("#awPanel [data-aw=back]")
        # 派一件還沒做完的，時鐘快轉過預估，分頁在背景
        pg.evaluate(_SR_JOB, {"end": now, "dur": 1000, "aid": "run1", "who": who, "title": "跑很久的那件", "cats": ["read"], "noStop": True})
        pg.evaluate("() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true }); }")
        pg.evaluate("() => { window.__off = 3 * 60000; }")
        pg.evaluate("() => __world.away.checkEta()")
        pg.wait_for_timeout(300)
        nots = pg.evaluate("() => window.__nots")
        toast = _sr_text(pg, "#awToast")
        if perm == "granted":
            ok("提醒（同意）：超過預估還沒交件、分頁在背景 → 真的建立瀏覽器通知", len(nots) == 1 and "跑很久的那件" in nots[0]["body"] and "預估這時候該做完了" in nots[0]["body"], nots)
            ok("提醒（同意）：已用瀏覽器通知就不再重複跳畫面提示", toast == "", toast)
        else:
            ok("提醒（拒絕）：不會建立瀏覽器通知", len(nots) == 0, nots)
            ok("提醒（拒絕）：改用畫面上的提示", "跑很久的那件" in toast and "預估這時候該做完了" in toast, toast)
            _sr_shot(pg, "r2b_remind_toast.png")
        pg.evaluate("() => __world.away.checkEta()")
        pg.wait_for_timeout(200)
        ok("提醒（%s）：同一件只提醒一次" % tag, pg.evaluate("() => window.__nots.length") == (1 if perm == "granted" else 0), pg.evaluate("() => window.__nots.length"))
        ok("提醒（%s）：頁面沒有 JS 錯誤" % tag, not pg.errs, pg.errs[:3])
    finally:
        c.close()


def _sr_misc(b, base):
    root = _sr_root(base)
    import urllib.request as _ur
    feat = _ur.urlopen(root + "/features.js", timeout=20).read().decode("utf-8")
    pre = _ur.urlopen(root + "/plan_presets.js", timeout=20).read().decode("utf-8")
    gate = _ur.urlopen(root + "/office/world/js/gate.js", timeout=20).read().decode("utf-8")
    for k in ("office.scorecard", "office.awaypack", "office.replay"):
        ok("功能鍵 %s：features.js 有登記" % k, k in feat, k)
        ok("功能鍵 %s：四個方案範本都寫了開關" % k, len(_re.findall(r'"%s"\s*:\s*(?:true|!0)' % _re.escape(k), pre)) == 4, len(_re.findall(r'"%s"' % _re.escape(k), pre)))
        ok("功能鍵 %s：gate.js 的 GATE_IDS 有它" % k, k in gate, k)
    notices = _ur.urlopen(root + "/notices/features.json", timeout=20).read().decode("utf-8")
    ok("功能更新公告：有成績單／重播那則", "f-20261116-office-scorecard" in notices, "沒有公告")
    # 手機 390
    c, pg, got = _sr_open(b, base, w=390, h=844, touch=True)
    try:
        ok("手機：辦公室載入完成", got, "載入逾時")
        if not got:
            return
        who = _sr_who(pg)
        now = pg.evaluate("() => Date.now()")
        pg.evaluate(_SR_JOB, {"end": now - 1000, "dur": 500000, "aid": "mb1", "who": who, "title": "手機上看的成績單", "msg": "好了"})
        wait_until(pg, "() => __world.scorecard.cards.length === 1", 5000)
        chk = """() => { const o = []; const vw = innerWidth, vh = innerHeight;
          for (const id of ['scPanel', 'rpBar', 'awPanel', 'rpTag', 'scBtn']) { const e = document.getElementById(id); if (!e || e.hidden) continue; const r = e.getBoundingClientRect();
            if (r.left < -1 || r.right > vw + 1 || r.top < -1 || (id !== 'scPanel' && id !== 'awPanel' && r.bottom > vh + 1)) o.push([id, Math.round(r.left), Math.round(r.right), Math.round(r.top), Math.round(r.bottom)]);
            for (const el of e.querySelectorAll('*')) { if (!el.childNodes.length) continue; let own = ''; for (const n of el.childNodes) if (n.nodeType === 3) own += n.textContent; if (!own.trim()) continue; const f = parseFloat(getComputedStyle(el).fontSize); if (f < 11) o.push([id, 'font', f, own.trim().slice(0, 12)]); } }
          if (document.documentElement.scrollWidth > vw + 1) o.push(['page', 'scrollWidth', document.documentElement.scrollWidth]); return o; }"""
        pg.click("#scBtn")
        wait_until(pg, "() => !document.getElementById('scPanel').hidden", 3000)
        ok("手機：頂列有「成績單」鈕、沒有橫向溢出", pg.evaluate(chk) == [], pg.evaluate(chk))
        _sr_shot(pg, "r2b_m390_scorecard.png")
        pg.click("#scPanel [data-sc=replay]")
        wait_until(pg, "() => __world.replay.on", 4000)
        pg.wait_for_timeout(300)
        ok("手機：重播控制列與「重播中」在畫面內、字不小於 11px", pg.evaluate(chk) == [], pg.evaluate(chk))
        ok("手機：重播控制列的鈕 ≥ 32px 高", pg.evaluate("() => [...document.querySelectorAll('#rpBar button')].every(b => b.getBoundingClientRect().height >= 32)"), "鈕太小")
        _sr_shot(pg, "r2b_m390_replay.png")
        pg.click("#rpExit")
        pg.evaluate("() => __world.away.show(Date.now() - 20 * 60000)")
        ok("手機：離開成果包在畫面內、字不小於 11px", pg.evaluate(chk) == [], pg.evaluate(chk))
        _sr_shot(pg, "r2b_m390_away.png")
        txt = pg.evaluate("() => ['scPanel', 'awPanel', 'rpBar'].map(i => document.getElementById(i).innerText).join(' ')")
        ok("手機：文案沒有禁用字", not _SR_BAD.search(txt), _SR_BAD.search(txt))
    finally:
        c.close()


def _sr_all(pg, b, base, code):
    _sr_scorecard(b, base)
    _sr_replay(b, base)
    _sr_away(b, base)
    _sr_remind(b, base, "granted")
    _sr_remind(b, base, "denied")
    _sr_misc(b, base)


register("辦公室成績單與重播與成果包", _sr_all)
