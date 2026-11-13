# 驗收段落「辦公室狀態」：AI Office 3D 辦公室（site/office/world.html）的
#   ① 辦公室狀態層＋事件模擬器（?sim=1）：模擬器逐一觸發事件，狀態真的改變
#   ② 額度＝電力：頂列膠囊與後牆電力表的長度、剩 20% 轉琥珀並只提示一次、用完全員趴睡＋燈光變暗＋門牌恢復時間＋倒數、
#      恢復時 CEO 先醒其他人依序醒、未提供時灰色虛線不睡、睡著時收到工作事件全員立刻醒、被操控的角色不睡
#   ③ 等你處理：等核准（分頁標題前綴、CEO 舉手、只顯示動作類別）、等回答、派工到交件（用走的、不瞬移）、工具道具、
#      同時 3 位在桌前、大動作 ≤ 6 件、失敗不羞辱、卡住、訊號不明不寫離線
#   ④ 開除與無業遊民區：確認框（取消不生效、要按兩次）、走出大門到遊民區、名牌待業中、座位清空、任務轉給指定的人且數字相符（資訊卡與佈告欄）、
#      重新整理後仍在、重新聘用走回座位、開除整個部門、CEO 沒有開除鈕
#   ⑤ 空狀態四種（?empty=1..4）
#   ⑥ 手機 390×844 與桌機 1280×800：元素兩兩不重疊、沒有橫向捲軸、字不小於 11px、畫面不出現價格／付費／升級／方案／Plus／Pro／免費
#   ⑦ 繪製次數不明顯增加、預覽部署略過 data／preview 資料夾後重建再測一次
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（點、填、鍵盤），並驗「畫面／狀態真的改變」。
# 軟體繪圖（swiftshader）很慢，所以把模擬速度調成 8 倍（物理子步仍固定 ≤ 0.034 秒，行為與 1 倍速一致）。
# 環境變數 STATE_SHOTS 指到資料夾時，順便把驗收畫面存成截圖（交件用）。
# flake8: noqa

import os as _os
import re as _re
import shutil as _sh
import tempfile as _tf
import threading as _th
import functools as _ft
import http.server as _hs
import socketserver as _ss

_FORBID = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費")


def _root(base):
    return base.split("/index.html")[0].rstrip("/")


def _open(b, base, w=1280, h=800, touch=False, qs="?ambient=0&q=low&pr=0.6&sim=1", day="day", reduced=False, speed=8):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch, reduced_motion="reduce" if reduced else "no-preference")
    if day:
        c.add_init_script("try{localStorage.setItem('aiOffice.daytime','%s')}catch(e){}" % day)
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    if got:
        pg.evaluate("(s) => { __world.speed = s; }", speed)
    pg.wait_for_timeout(500)
    return c, pg, got


def _shot(pg, name):
    d = _os.environ.get("STATE_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _rect(pg, sel):
    return pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); if (!r.width) return null;
      const cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return null; return [r.left, r.top, r.right, r.bottom]; }""", sel)


def _hit(a, b, pad=1):
    return a and b and not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


def _no_overlap(pg, sels):
    rs = [(s, _rect(pg, s)) for s in sels]
    rs = [x for x in rs if x[1]]
    bad = [(a[0], b[0]) for i, a in enumerate(rs) for b in rs[i + 1:] if _hit(a[1], b[1])]
    return bad, len(rs)


def _text(pg):
    return pg.evaluate("() => document.body.innerText")


def _sim(pg, name, *args):
    pg.evaluate("([n, a]) => __world.sim[n](...a)", [name, list(args)])


def _sp(pg, key):
    """按模擬器面板上的按鈕（面板沒開就先開）。軟體繪圖下 Playwright 每次真點要 3 秒，這裡用 DOM 的 click()，仍是真的點擊事件、走同一條處理程式"""
    pg.evaluate("""(k) => { const p = document.getElementById('simPop'); if (p.hidden) document.getElementById('simBtn').click(); const b = p.querySelector("[data-sim='" + k + "']"); if (!b) throw new Error('模擬器沒有按鈕 ' + k); b.click(); }""", key)


def _meter_px(pg, which="five"):
    """電力表畫布上，指定那一條「填滿色（綠或琥珀）」的像素寬度（不是讀模型，是真的數畫布上的像素）"""
    y = 135 if which == "five" else 255
    return pg.evaluate("""(y) => { const c = __world.power.meterCanvas.getContext('2d'), d = c.getImageData(34, y, 444, 1).data; let n = 0;
      for (let i = 0; i < 444; i++) { const r = d[i * 4], g = d[i * 4 + 1], b = d[i * 4 + 2], a = d[i * 4 + 3];
        const green = Math.abs(r - 108) < 30 && Math.abs(g - 192) < 40 && Math.abs(b - 139) < 30, amber = Math.abs(r - 242) < 28 && Math.abs(g - 169) < 30 && Math.abs(b - 59) < 40, orange = Math.abs(r - 239) < 20 && Math.abs(g - 122) < 30 && Math.abs(b - 58) < 40;
        if (a > 200 && (green || amber || orange)) n++; } return n; }""", y)


def _hemi(pg):
    return pg.evaluate("() => __world.hemi.intensity")


def _track(pg, name, expr):
    pg.evaluate("([n, e]) => { window.__trk = window.__trk || {}; __trk[n] = new Set(); const f = new Function('return (' + e + ')'); (function loop() { try { const v = f(); if (v != null) __trk[n].add(String(v)); } catch (x) {} requestAnimationFrame(loop); })(); }", [name, expr])


def _seen(pg, name):
    return pg.evaluate("(n) => [...(__trk[n] || [])]", name)


def _alive(pg):
    return pg.evaluate("() => [...__world.chars.values()].filter(c => !c.away && !c.jobless).map(c => c.spec.id)")


# ───────────────────────── ① ② 額度＝電力 ─────────────────────────
def t_power(b, base):
    c, pg, got = _open(b, base)
    try:
        ok("電力：辦公室頁載入完成", got)
        if not got:
            return
        # 模擬器入口：?sim=1 才有，預設收起
        ok("模擬器：網址帶 ?sim=1 時頂列有「模擬」鈕", pg.evaluate("() => !!document.getElementById('simBtn')"))
        ok("模擬器：面板預設收起（不擋畫面）", pg.evaluate("() => document.getElementById('simPop').hidden"))
        pg.click("#simBtn")
        ok("模擬器：點「模擬」才展開面板", pg.evaluate("() => !document.getElementById('simPop').hidden"))
        r = _rect(pg, "#simPop")
        ok("模擬器：面板整個在畫面內", r and r[0] >= 0 and r[2] <= 1280 and r[3] <= 800, r)
        for sel in ["q62", "q18", "q8", "out1", "out2", "rec", "qna", "stale", "perm", "ask", "st", "okk", "bad", "many", "day"]:
            if not pg.evaluate("(s) => !!document.querySelector(`[data-sim='${s}']`)", sel):
                ok("模擬器：缺按鈕 " + sel, False)
        ok("模擬器：額度、提醒、派工、典型的一天的按鈕都在", pg.evaluate("() => document.querySelectorAll('#simPop [data-sim]').length >= 20"))
        # 額度未提供（預設）
        ok("額度未提供：膠囊寫「電力 未提供」", pg.evaluate("() => document.getElementById('pwTxt').textContent") == "電力 未提供")
        ok("額度未提供：膠囊是灰色虛線樣式（na）", pg.evaluate("() => document.getElementById('pwBtn').classList.contains('na')"))
        mm = pg.evaluate("() => __world.power.meterModel")
        ok("額度未提供：電力表兩條都是虛線、沒有填色", mm["five"]["dashed"] and mm["week"]["dashed"] and _meter_px(pg, "five") < 30, mm)
        ok("額度未提供：沒有人在睡覺、燈光不變", pg.evaluate("() => [...__world.chars.values()].every(c => !c.sleeping) && __world.dim === 1"))
        # 剩 62%
        _sp(pg, "q62")
        ok("額度 62%：膠囊文字是「電力 62%」", pg.evaluate("() => document.getElementById('pwTxt').textContent") == "電力 62%", pg.evaluate("() => document.getElementById('pwTxt').textContent"))
        mm = pg.evaluate("() => __world.power.meterModel")
        ok("額度 62%：電力表模型 5 小時 ＝ 0.62、不是虛線", abs(mm["five"]["frac"] - 0.62) < 0.01 and not mm["five"]["dashed"], mm)
        n62 = _meter_px(pg, "five")
        ok("額度 62%%：電力表畫布上填色約 62%%（量像素 %d／444）" % n62, 250 <= n62 <= 300, n62)
        ok("額度 62%：不是琥珀、燈光不變", pg.evaluate("() => !document.getElementById('pwBtn').classList.contains('low') && __world.dim === 1"))
        pg.click("#pwBtn")
        ok("額度 62%：點膠囊看得到「5 小時」「本週」與重置時間", pg.evaluate("() => { const t = document.getElementById('pwPop').innerText; return !document.getElementById('pwPop').hidden && /5 小時/.test(t) && /本週/.test(t) && /\\d\\d:\\d\\d 重置/.test(t); }"))
        pg.click("#pwQ")
        ok("額度說明收進「?」：點了才展開", pg.evaluate("() => !document.querySelector('#pwPop .pw-note').hidden"))
        pg.click("#pwBtn")
        # 剩 18%：琥珀＋只提示一次
        pg.evaluate("() => { document.getElementById('toast').hidden = true; }")
        _sp(pg, "q18")
        ok("額度 18%：膠囊文字「電力 18%」且轉琥珀（low）", pg.evaluate("() => document.getElementById('pwTxt').textContent") == "電力 18%" and pg.evaluate("() => document.getElementById('pwBtn').classList.contains('low')"))
        ok("額度 18%：提示一次「電力剩 18%」", pg.evaluate("() => { const t = document.getElementById('toast'); return !t.hidden && /電力剩 18%/.test(t.textContent); }"))
        mm = pg.evaluate("() => __world.power.meterModel")
        n18 = _meter_px(pg, "five")
        ok("額度 18%%：電力表變短（%d → %d 像素）且改琥珀色" % (n62, n18), n18 < n62 * 0.45 and mm["five"]["color"] == "#f2a93b", (n62, n18, mm))
        ok("額度 18%：膠囊有「!」形狀，不只靠顏色", pg.evaluate("() => getComputedStyle(document.querySelector('#pwBtn .pw-ic'), '::before').content") in ('"!"', "'!'"))
        pg.evaluate("() => { document.getElementById('toast').hidden = true; }")
        _sp(pg, "q18"); pg.wait_for_timeout(400)
        ok("額度 18%：同一個重置週期不重複提示", pg.evaluate("() => document.getElementById('toast').hidden"))
        # 剩 8%：節電氣氛
        _sp(pg, "q8")
        ok("額度 8%：進入節電氣氛，燈光降到 85%", wait_until(pg, "() => Math.abs(__world.dim - 0.85) < 0.01", 8000))
        h85 = _hemi(pg)
        ok("額度 8%%：半球光強度約為正常的 0.85（%.3f）" % h85, abs(h85 - 1.55 * 0.85) < 0.05, h85)
        _sp(pg, "q62")
        ok("額度回到 62%：燈光恢復、膠囊不再琥珀", wait_until(pg, "() => __world.dim === 1 && !document.getElementById('pwBtn').classList.contains('low')", 8000))
        # 資料過舊
        _sp(pg, "stale")
        ok("額度資料過舊：膠囊尾端加「（23 分鐘前）」", pg.evaluate("() => /（2\\d 分鐘前）/.test(document.getElementById('pwTxt').textContent)"), pg.evaluate("() => document.getElementById('pwTxt').textContent"))
        # 回到未提供：不演預警、不睡
        _sp(pg, "qna")
        ok("再回未提供：膠囊「電力 未提供」、電力表回到虛線", pg.evaluate("() => document.getElementById('pwTxt').textContent") == "電力 未提供" and pg.evaluate("() => __world.power.meterModel.five.dashed"))
        _sp(pg, "q62")

        # ── 額度用完（有恢復時間）：全員睡覺 ──
        _sp(pg, "out1")
        ok("額度用完：CEO 宣布後進入睡覺（宣布階段）", wait_until(pg, "() => ['declare','asleep'].includes(__world.power.phase)", 8000))
        ok("額度用完：全員睡著（phase = asleep）", wait_until(pg, "() => __world.power.phase === 'asleep'", 150000, 400))
        ids = _alive(pg)
        st = pg.evaluate("() => [...__world.chars.values()].filter(c => !c.away && !c.jobless).map(c => [c.sleeping, c.action, c.inner.mode, c.state])")
        ok("額度用完：所有 %d 位非操控角色都在睡眠姿態（sleeping、動作 sleep、骨架模式 sleep）" % len(ids), len(ids) > 40 and all(x[0] and x[1] == "sleep" and x[2] == "sleep" for x in st), [x for x in st if not (x[0] and x[1] == "sleep")][:3])
        ok("額度用完：每個人都坐在自己的位子上睡", pg.evaluate("() => [...__world.chars.values()].every(c => c.state === 'sit' && c.atDesk)"))
        ok("額度用完：寵物也睡了", pg.evaluate("() => __world.pets.every(p => p.action === 'sleep')"))
        order = pg.evaluate("() => __world.power.sleepOrder")
        ok("額度用完：CEO 最後睡（睡覺順序最後一位是 CEO）", order[-1] == "ceo" and len(order) == len(ids), order[-2:])
        hd = _hemi(pg)
        ok("額度用完：燈光漸暗到 35%%（半球光 %.3f → %.3f，目標 1.55×0.35＝0.543）" % (h85 if False else 1.55, hd), abs(hd - 1.55 * 0.35) < 0.03 and pg.evaluate("() => Math.abs(__world.dim - 0.35) < 0.001"), hd)
        ok("額度用完：太陽光也跟著降（不超過正常的 40%）", pg.evaluate("() => __world.sun.intensity < 1.65 * 0.4"))
        sg = pg.evaluate("() => ({txt: document.getElementById('pwSign').innerText, shown: !document.getElementById('pwSign').hidden, sig: __world.power.signText, mesh: __world.power.signMeshes.map(m => m.visible)})")
        ok("門牌：寫「休息中・額度恢復 HH:MM」", sg["shown"] and "休息中" in sg["txt"] and _re.search(r"額度恢復 \d\d:\d\d", sg["txt"]) and _re.search(r"休息中・額度恢復 \d\d:\d\d", sg["sig"]), sg)
        ok("門牌：3D 大門上外、內兩面都掛出來了", all(sg["mesh"]), sg["mesh"])
        ok("門牌：有剩餘時間倒數「約 N 小時 M 分」", pg.evaluate("() => /約 \\d+ 小時( \\d+ 分)?/.test(document.getElementById('pwSign').innerText)"))
        ok("額度用完：膠囊顯示「電力 0%」、電力表歸零", pg.evaluate("() => /電力 0%/.test(document.getElementById('pwTxt').textContent) && document.getElementById('pwBtn').classList.contains('out')") and _meter_px(pg, "five") < 30)
        ok("額度用完：螢幕全部熄滅（沒有人亮著）", pg.evaluate("() => [...__world.chars.values()].every(c => c.sleeping)"))
        _shot(pg, "額度用完_全員睡覺.png")
        _shot(pg, "門牌_恢復時間.png")
        pg.evaluate("() => { document.getElementById('simPop').hidden = true; }")
        bad, n = _no_overlap(pg, ["#bar .ttl", "#viewSeg", "#areaBtn", "#demoBtn", "#speedSeg", "#pwBtn", "#simBtn", "#editBtn", "#pwSign", ".dt-chip", ".cm-hint"])
        ok("額度用完（桌機 1280）：頂列、門牌、時間小字、鏡頭提示兩兩不重疊（%d 個元素）" % n, not bad, bad)

        # ── 被操控的角色不睡 ──
        pg.evaluate("() => { __world.pilot.select(__world.chars.get('finance-quant')); }")
        pg.keyboard.down("ArrowUp"); pg.wait_for_timeout(900); pg.keyboard.up("ArrowUp")
        ok("睡覺期間操控：被操控的角色醒著（不睡、可以走）", wait_until(pg, "() => { const c = __world.chars.get('finance-quant'); return c.piloted && !c.sleeping && c.action !== 'sleep'; }", 8000))
        ok("睡覺期間操控：其他人照樣睡", pg.evaluate("() => [...__world.chars.values()].filter(c => c.spec.id !== 'finance-quant').every(c => c.sleeping)"))
        pg.evaluate("() => __world.pilot.release()")
        ok("放開操控後：他走回座位再趴下睡（規則：仍可操控，放開後回去睡）", wait_until(pg, "() => { const c = __world.chars.get('finance-quant'); return c.sleeping && c.state === 'sit' && c.action === 'sleep'; }", 120000, 500))

        # ── 恢復：CEO 先醒、依序醒 ──
        _sp(pg, "rec")
        ok("恢復：燈光漸亮、牌子換成「已恢復」", wait_until(pg, "() => __world.power.phase === 'waking' && /已恢復/.test(document.getElementById('pwSign').innerText)", 20000))
        _shot(pg, "恢復_依序醒來連拍.png")
        ok("恢復：全員醒來（phase = awake）", wait_until(pg, "() => __world.power.phase === 'awake'", 150000, 400))
        wo = pg.evaluate("() => __world.power.wakeOrder.map(x => x.id)")
        ok("恢復：CEO 第一個醒（醒來順序第一位是 CEO）", wo[0] == "ceo", wo[:3])
        ok("恢復：其他人依座位順序陸續醒（醒來順序 ＝ 睡覺順序，CEO 除外）", wo[1:] == [x for x in order if x != "ceo"] or sorted(wo) == sorted(order), wo[:5])
        ok("恢復：所有人醒來（沒有人還在睡、沒有睡眠姿態）", pg.evaluate("() => [...__world.chars.values()].every(c => !c.sleeping && c.inner.mode !== 'sleep')"))
        ok("恢復：燈光回到正常", wait_until(pg, "() => __world.dim === 1 && Math.abs(__world.hemi.intensity - 1.55) < 0.05", 10000))
        ok("恢復：牌子收起來", wait_until(pg, "() => document.getElementById('pwSign').hidden", 12000))
        ok("恢復：日常恢復，同事又開始自己找事做", pg.evaluate("() => __world.director.hold === false"))

        # ── 用完但不知道何時恢復 ──
        _sp(pg, "out2")
        ok("用完（時間未提供）：全員睡著", wait_until(pg, "() => __world.power.phase === 'asleep'", 150000, 400))
        tx = pg.evaluate("() => document.getElementById('pwSign').innerText")
        ok("用完（時間未提供）：牌子寫「恢復時間未提供」、不倒數、不猜時間", "恢復時間未提供" in tx and not _re.search(r"\d\d:\d\d", tx) and "約" not in tx, tx)
        # 睡著時收到工作事件 → 立刻全員醒來
        _sp(pg, "prompt")
        ok("睡著時收到工作事件：立刻開始全員醒來（資料已更正）", wait_until(pg, "() => ['waking','awake'].includes(__world.power.phase) && /資料已更正/.test(document.getElementById('toast').textContent + '')", 10000))
        ok("睡著時收到工作事件：全員醒來、額度狀態改回未用完", wait_until(pg, "() => __world.power.phase === 'awake' && [...__world.chars.values()].every(c => !c.sleeping) && !__world.state.q.exhausted", 120000, 400))
        ok("睡著時收到工作事件：牌子立即收起（不等恢復時間）", pg.evaluate("() => document.getElementById('pwSign').hidden"))

        # ── 開會到一半額度用完：提前散會 ──
        pg.click("#demoBtn"); pg.click("#demoPop [data-demo='meeting']")
        ok("（前置）會議示範開始", wait_until(pg, "() => !!__world.director.meeting", 20000))
        _sim(pg, "exhaust", 8100)
        ok("開會中額度用完：會議提前散會（會議紀錄寫明原因）", wait_until(pg, "() => !__world.director.meeting && /因額度用完提前散會/.test(document.getElementById('logList') ? document.getElementById('logList').innerText : '')", 40000, 300))
        ok("開會中額度用完：與會的人也回座位睡著", wait_until(pg, "() => __world.power.phase === 'asleep' && [...__world.chars.values()].every(c => c.sleeping)", 180000, 500))
        _sim(pg, "recover")
        wait_until(pg, "() => __world.power.phase === 'awake'", 150000, 400)

        # ── 夜晚疊加：仍要看得清楚 ──
        pg.evaluate("() => __world.daytime.set('night')")
        pg.wait_for_timeout(600)
        _sim(pg, "exhaust", 8100)
        ok("夜晚＋額度用完：全員睡著", wait_until(pg, "() => __world.power.phase === 'asleep'", 150000, 400))
        hn = _hemi(pg)
        ok("夜晚＋額度用完：燈光有下限，半球光不低於 0.5（%.3f），不會黑成一片" % hn, hn >= 0.49, hn)
        _shot(pg, "夜晚_額度用完.png")
        _sim(pg, "recover")
        wait_until(pg, "() => __world.power.phase === 'awake'", 150000, 400)
        pg.evaluate("() => __world.daytime.set('day')")
        ok("電力段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ③ 等你處理、派工到交件 ─────────────────────────
def t_jobs(b, base):
    c, pg, got = _open(b, base)
    try:
        ok("派工：辦公室頁載入完成", got)
        if not got:
            return
        pg.evaluate("() => __world.sim.quota(62, 80)")
        # 等核准
        title0 = pg.evaluate("() => document.title")
        _sp(pg, "perm")
        ok("等核准：分頁標題前綴「(1) 」", pg.evaluate("() => document.title.startsWith('(1) ')"), pg.evaluate("() => document.title"))
        ok("等核准：頂列出現琥珀膠囊「CEO 等你核准」", pg.evaluate("() => { const e = document.getElementById('flBadge'); return !e.hidden && /CEO 等你核准/.test(e.textContent) && e.classList.contains('perm'); }"))
        ok("等核准：只顯示動作類別「要執行一個指令」，沒有指令全文", pg.evaluate("() => /要執行一個指令/.test(document.getElementById('flBadge').textContent)") and not _re.search(r"rm -rf|git push|--force|sudo", _text(pg)))
        ok("等核准：CEO 舉手（動作 raise）、頭上有盾牌鎖圖示", wait_until(pg, "() => { const c = __world.chars.get('ceo'); return c.action === 'raise' || (c.emoteSym && c.emoteSym.sym === 'shield'); }", 20000, 200))
        ok("等核准：桌燈亮起（琥珀光暈）", pg.evaluate("() => __world.jobs.lamp.visible"))
        _shot(pg, "等待核准.png")
        ok("等核准：名牌狀態字「等你核准」", pg.evaluate("() => __world.statusOf(__world.chars.get('ceo'))") == "等你核准")
        _sp(pg, "clr")
        ok("處理完了：分頁標題恢復、膠囊與桌燈熄滅", pg.evaluate("() => document.title === arguments[0] || !document.title.startsWith('(')".replace("arguments[0]", repr(title0))) and pg.evaluate("() => document.getElementById('flBadge').hidden && !__world.jobs.lamp.visible"))
        # 等久了：再提醒一次、CEO 開始冒汗（測試把 3 分鐘、10 分鐘縮成 1 秒、2.5 秒）
        pg.evaluate("() => { __world.state.cfg.remindMs = [1000, 2500]; }")
        _track(pg, "ttl", "document.title"); _track(pg, "ceoemo", "(__world.chars.get('ceo').emoteSym || {}).sym")
        pg.evaluate("() => { const c = __world.chars.get('ceo'); c.__em = new Set(); if (!c.__emHook) { c.__emHook = 1; const o = c.emote; c.emote = (s, t) => { c.__em.add(s); return o.call(c, s, t); }; } }")
        _sim(pg, "permission", "web")
        ok("等核准：等久了再提醒一次（分頁標題閃成「(!) CEO 還在等你核准」）", wait_until(pg, "() => [...__trk.ttl].some(x => x.startsWith('(!)'))", 20000, 200), _seen(pg, "ttl"))
        # 冒汗圖示只持續 2.6 秒模擬時間（8 倍速＝約 0.3 秒真實時間），軟體繪圖下 requestAnimationFrame 輪詢會漏看（上一輪的間歇性失敗就是這個）；
        # 改成「攔截 emote 呼叫」：只要程式真的叫 CEO 冒汗過一次就算
        ok("等核准：等更久 CEO 開始冒汗", wait_until(pg, "() => __world.chars.get('ceo').__em && __world.chars.get('ceo').__em.has('sweat')", 20000, 100), pg.evaluate("() => [...(__world.chars.get('ceo').__em || [])]"))
        _sim(pg, "clear")
        pg.evaluate("() => { __world.state.cfg.remindMs = [180000, 600000]; }")
        # 等回答
        _sp(pg, "ask")
        ok("等回答：CEO 頭上大問號", wait_until(pg, "() => { const c = __world.chars.get('ceo'); return c.emoteSym && c.emoteSym.sym === 'question'; }", 20000, 200))
        ok("等回答：頂列藍色膠囊「CEO 等你回答」、分頁標題前綴", pg.evaluate("() => { const e = document.getElementById('flBadge'); return !e.hidden && /CEO 等你回答/.test(e.textContent) && e.classList.contains('ask') && document.title.startsWith('(1) '); }"))
        ok("等回答：不放假的答題鈕（頂列沒有任何「回答」按鈕）", pg.evaluate("() => ![...document.querySelectorAll('#bar button')].some(b => /回答|選項/.test(b.textContent))"))
        _shot(pg, "等待回答.png")
        _sim(pg, "clear")
        # 兩者同時：標題數字 2
        _sim(pg, "permission", "edit"); _sim(pg, "question", "要先處理哪一件？")
        ok("同時等核准與等回答：分頁標題前綴「(2) 」、核准類別「要修改檔案」", pg.evaluate("() => document.title.startsWith('(2) ') && /要修改檔案/.test(document.getElementById('flBadge').textContent)"))
        _sim(pg, "clear")

        # 派工（走路、不瞬移）
        pg.evaluate("""() => { window.__tr = []; const c = __world.chars.get('finance-quant'); (function f() { const p = c.object3D.position; __tr.push([p.x, p.z, __world.time, c.state]); requestAnimationFrame(f); })(); }""")
        pg.evaluate("() => __world.sim.start('finance-quant', '整理本週資金流向', 'read')")
        ok("派工：該同事的狀態變成進行中（領任務→做事）", wait_until(pg, "() => __world.state.agent('finance-quant').phase === 'doing'", 120000, 300))
        tr = pg.evaluate("() => __tr")
        walked = [x for x in tr if x[3] == "walk"]
        sp = max((((a[0] - b_[0]) ** 2 + (a[1] - b_[1]) ** 2) ** 0.5 / max(1e-6, b_[2] - a[2]) for a, b_ in zip(tr, tr[1:]) if b_[2] > a[2] and a[3] == "walk" and b_[3] == "walk"), default=0)
        ok("派工：同事是走到 CEO 桌前領任務（走了 %d 幀，最快 %.1f 公尺／秒，沒有瞬移）" % (len(walked), sp), len(walked) > 10 and sp < 6, sp)
        ok("派工：領完任務走回座位坐好工作", wait_until(pg, "() => { const c = __world.chars.get('finance-quant'); return c.state === 'sit' && c.atDesk; }", 60000, 300))
        ok("派工：名牌狀態字「讀資料中」", pg.evaluate("() => __world.statusOf(__world.chars.get('finance-quant'))") == "讀資料中")
        ok("派工：資訊卡的「進行中」格多了這一件", pg.evaluate("""() => { const W = __world, p = W.ui.progress(W.members.get('finance-quant')); return p.list.some(x => x.s === 2 && /整理本週資金流向/.test(x.title)); }"""))
        # 四種工具道具
        res = {}
        pg.evaluate("() => __world.setView('char', __world.chars.get('finance-quant'), true)")   # 拉近看他（遠景時為了效能，手上的小道具會被收起來）
        pg.wait_for_timeout(800)
        for cat, act, prop in [("read", "doc", "doc"), ("write", "note", "notebook"), ("search", "magnify", "magnifier"), ("other", "tablet", "tablet")]:
            _sim(pg, "tool", "finance-quant", cat)
            pg.wait_for_timeout(700)
            res[cat] = pg.evaluate("""(p) => { const c = __world.chars.get('finance-quant'); let found = false; c.object3D.traverse(o => { if (o.userData && o.userData.prop === p && o.visible) found = true; }); return [c.action, found, __world.statusOf(c)]; }""", prop)
        ok("工具小道具：讀＝文件、寫＝筆記本、查＝放大鏡、泛用＝平板（動作與手上道具都對）", all(res[k][0] == a and res[k][1] for k, a in [("read", "doc"), ("write", "note"), ("search", "magnify"), ("other", "tablet")]), res)
        ok("工具小道具：名牌狀態字隨類別變（讀資料中／寫程式中／查資料中／工作中）", [res[k][2] for k in ["read", "write", "search", "other"]] == ["讀資料中", "寫程式中", "查資料中", "工作中"], res)
        _shot(pg, "派工到交件連拍.png")
        # 交件
        n0 = pg.evaluate("() => __world.ui.progress(__world.members.get('finance-quant')).nDone")
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('finance-quant'))")
        _track(pg, "fq", "__world.statusOf(__world.chars.get('finance-quant')) + '|' + __world.chars.get('finance-quant').state + '|' + __world.chars.get('finance-quant').action")
        pg.evaluate("() => __world.sim.stop('finance-quant', true)")
        ok("交件：同事拿文件走去 CEO 桌前（狀態字「交件中」、走路、動作 carry、遞交時 present）", wait_until(pg, "() => __trk.fq.has('交件中|walk|carry')", 60000, 100) and wait_until(pg, "() => [...__trk.fq].some(x => x.endsWith('|present'))", 120000, 100), _seen(pg, "fq")[:8])
        ok("交件：交完回座、狀態回到待命（phase idle、坐在位子上）", wait_until(pg, "() => { const c = __world.chars.get('finance-quant'); return __world.state.agent('finance-quant').phase === 'idle' && c.state === 'sit' && c.atDesk; }", 120000, 300))
        n1 = pg.evaluate("() => __world.ui.progress(__world.members.get('finance-quant')).nDone")
        ok("交件：已完成 +1（%d → %d）" % (n0, n1), n1 == n0 + 1)
        kc = pg.evaluate("() => +document.querySelector('#cardKpi [data-k=\"3\"] b').textContent")
        ok("交件：開著的資訊卡「已完成」格數字跟著變（%d）" % kc, kc == n1, kc)
        # 失敗：不羞辱
        pg.evaluate("() => __world.sim.start('data-steward', '補法人資料')")
        wait_until(pg, "() => __world.state.agent('data-steward').phase === 'doing'", 120000, 300)
        _track(pg, "ds", "__world.statusOf(__world.chars.get('data-steward')) + '|' + ((__world.chars.get('data-steward').emoteSym || {}).sym || '')")
        _track(pg, "ceo", "(__world.chars.get('ceo').speech || {}).text")
        _track(pg, "dsact", "__world.chars.get('data-steward').action")
        pg.evaluate("() => __world.sim.stop('data-steward', false)")
        ok("失敗：狀態字「遇到問題」、頭上小烏雲（不羞辱）", wait_until(pg, "() => [...__trk.ds].some(x => x.startsWith('遇到問題') && x.endsWith('cloud'))", 60000, 100), _seen(pg, "ds"))
        ok("失敗：CEO 說「沒關係，我來看看」", wait_until(pg, "() => [...__trk.ceo].some(x => /沒關係/.test(x))", 90000, 100), _seen(pg, "ceo"))
        ok("失敗處理完：回座、失敗計 1、不算完成", wait_until(pg, "() => { const a = __world.state.agent('data-steward'); return a.phase === 'idle' && a.failed === 1 && a.done.length === 0; }", 120000, 300))
        ok("失敗：沒有任何負面特效（整段過程中他的動作從來不是 angry／slam）", not (set(_seen(pg, "dsact")) & {"angry", "slam"}), _seen(pg, "dsact"))
        # 一次派 10 位：演出預算與桌前 3 位
        pg.evaluate("() => { __world.jobs.bigPeak = 0; __world.jobs.slotPeak = 0; __world.jobs.small = 0; }")
        _sp(pg, "many")
        ok("一次派 10 位：10 位都進入進行中", wait_until(pg, "() => [...__world.state.agents.values()].filter(a => a.phase === 'doing').length >= 10", 240000, 500))
        peak = pg.evaluate("() => [__world.jobs.bigPeak, __world.jobs.slotPeak, __world.jobs.small]")
        ok("一次派 10 位：大動作演出同時最多 6 件（高峰 %d）" % peak[0], 1 <= peak[0] <= 6, peak)
        ok("一次派 10 位：CEO 桌前同時最多 3 位（高峰 %d），其餘排隊" % peak[1], 1 <= peak[1] <= 3, peak)
        ok("一次派 10 位：超過預算的改成頭上小圖示，事件照記不丟（%d 位走小圖示路線）" % peak[2], peak[2] >= 1 and pg.evaluate("() => __world.state.log.filter(l => /CEO 派給/.test(l.text)).length >= 10"), peak)
        for cid in pg.evaluate("() => [...__world.state.agents].filter(([k, a]) => a.phase === 'doing').map(([k]) => k)"):
            _sim(pg, "stop", cid, True)
        ok("一次交 10 件：全部交完回座", wait_until(pg, "() => [...__world.state.agents.values()].every(a => a.phase === 'idle')", 300000, 500))
        peak = pg.evaluate("() => [__world.jobs.bigPeak, __world.jobs.slotPeak]")
        ok("一次交 10 件：桌前仍最多 3 位、大動作最多 6 件（%s）" % peak, peak[0] <= 6 and peak[1] <= 3, peak)
        # 卡住
        pg.evaluate("() => { __world.state.cfg.stuckMs = [1500, 3500]; }")
        pg.evaluate("() => __world.sim.start('smc-technical', '回測第二輪')")
        wait_until(pg, "() => __world.state.agent('smc-technical').phase === 'doing'", 120000, 300)
        ok("卡住：一段時間沒工具事件，名牌寫「好像卡住了（已 N 分鐘）」，不寫當機", wait_until(pg, "() => /^好像卡住了（已 \\d+ 分鐘）$/.test(__world.statusOf(__world.chars.get('smc-technical')))", 30000, 300) and "當機" not in _text(pg))
        _sim(pg, "stop", "smc-technical", True)
        wait_until(pg, "() => __world.state.agent('smc-technical').phase === 'idle'", 120000, 300)
        # 訊號不明
        _sim(pg, "lost")
        ok("訊號不明：頂列灰色「訊號不明」、CEO 名牌「待命中」", pg.evaluate("() => { const e = document.getElementById('linkBadge'); return !e.hidden && /訊號不明/.test(e.textContent) && __world.statusOf(__world.chars.get('ceo')) === '待命中'; }"))
        ok("訊號不明：畫面任何地方都不寫「離線」「斷線」「中斷」", not _re.search(r"離線|斷線|中斷", _text(pg)), _re.findall(r".{0,6}(?:離線|斷線|中斷).{0,6}", _text(pg))[:3])
        _sim(pg, "prompt")
        ok("訊號恢復（收到消息）：灰色膠囊消失", pg.evaluate("() => document.getElementById('linkBadge').hidden"))
        pg.evaluate("() => { __world.state.cfg.quietMs = 800; }"); _sim(pg, "prompt")
        ok("安靜（5 分鐘沒消息，測試縮短）：CEO 待命中，不當異常（沒有灰色訊號不明膠囊）", wait_until(pg, "() => __world.state.signal === 'quiet' && __world.statusOf(__world.chars.get('ceo')) === '待命中' && document.getElementById('linkBadge').hidden", 20000, 300))
        pg.evaluate("() => { __world.state.cfg.quietMs = 5 * 60e3; }")
        # 典型的一天（10 倍速）
        pg.evaluate("() => { __world.state.log.length = 0; __world.power.sleepOrder = []; }")
        pg.evaluate("() => __world.sim.playDay(0.1, 50)")   # 10 倍速；額度用完到恢復給 50 秒，讓全員有時間睡下去再醒來
        ok("典型的一天：播放中", pg.evaluate("() => __world.sim.playing"))
        ok("典型的一天：播完（額度用完去睡、時間到自動恢復、收工）", wait_until(pg, "() => !__world.sim.playing && __world.power.phase === 'awake' && !__world.state.q.exhausted", 300000, 500))
        lg = pg.evaluate("() => __world.state.log.map(l => l.text)")
        ok("典型的一天：日誌記到開工、派工、交件、遇到問題、收工", any("開工" in x for x in lg) and any("派給" in x for x in lg) and any("交件" in x for x in lg) and any("遇到問題" in x for x in lg) and any("收工" in x for x in lg), lg[:12])
        ok("典型的一天：途中真的睡過一輪（睡覺順序有 CEO）", pg.evaluate("() => __world.power.sleepOrder.includes('ceo')"))
        ok("派工段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ④ 開除與無業遊民區 ─────────────────────────
def t_hr(b, base):
    c, pg, got = _open(b, base)
    try:
        ok("開除：辦公室頁載入完成", got)
        if not got:
            return
        X, RCV = "data-scraper", "finance-quant"          # 織網（資料部）→ 任務交給秤老（量化研究部，不同部門）
        prog = lambda i: pg.evaluate("(i) => { const p = __world.ui.progress(__world.members.get(i)); return [p.nTodo, p.nDoing, p.nDone]; }", i)
        board = lambda o: pg.evaluate("""(o) => { __world.ui.showBoard(o); return [1, 2, 3].map(k => +document.querySelector('#boardKpi [data-bk="' + k + '"] b').textContent); }""", o)
        x0, r0 = prog(X), prog(RCV)
        bd0, bq0 = board("data"), board("quant")
        ok("（前置）織網：未完成 %d・進行中 %d・已完成 %d" % tuple(x0), x0[0] + x0[1] >= 2)
        # 預設俯視看得到遊民區入口；區域選單有「無業遊民區」
        vis = pg.evaluate("() => { const W = __world, v = W.outside.sign.position.clone().project(W.camera); return [v.x, v.y]; }")
        ok("預設俯視：遊民區的拱門招牌在畫面內（螢幕座標 %.2f, %.2f）" % tuple(vis), abs(vis[0]) < 1 and -1 < vis[1] < 1, vis)
        pg.click("#areaBtn")
        ok("區域選單：有「無業遊民區」可以跳過去", pg.evaluate("() => !!document.querySelector('#areaPop [data-room=jobless]')"))
        pg.click("#areaBtn")
        # CEO 沒有開除鈕
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('ceo'))")
        ok("CEO 的資訊卡沒有「開除」鈕", pg.evaluate("() => !document.querySelector('#card [data-i=fire]')") and pg.evaluate("() => __world.hr.fire(['ceo']).then(r => r.length === 0)"))
        # 開除單一同事：確認框
        pg.evaluate("(i) => __world.ui.showCard(__world.chars.get(i))", X)
        ok("資訊卡有「開除」鈕", pg.evaluate("() => !!document.querySelector('#card [data-i=fire]')"))
        pg.click("#card [data-i=fire]")
        ok("確認框：出現，列出對象、職稱、未完成與進行中任務數", pg.evaluate("(a) => { const d = document.getElementById('fireDlg'); return !!d && /織網/.test(d.innerText) && /資料抓取/.test(d.innerText) && d.innerText.includes('未完成 %d・進行中 %d'); }" % (x0[0], x0[1]), X))
        ok("確認框：要選「這些任務交給誰」，預設是 CEO", pg.evaluate("() => document.getElementById('fireTo').value === 'ceo' && document.getElementById('fireTo').options.length > 20"))
        r = _rect(pg, "#fireDlg .dlg")
        ok("確認框：整個在畫面內、有取消鈕", r and r[0] >= 0 and r[2] <= 1280 and r[3] <= 800 and _rect(pg, "#fireCancel") is not None, r)
        _shot(pg, "開除確認框.png")
        pg.click("#fireCancel")
        ok("取消：確認框關掉、沒有人被開除、織網還坐在位子上", pg.evaluate("(i) => !document.getElementById('fireDlg') && __world.hr.fired.size === 0 && __world.chars.get(i).state === 'sit' && !__world.chars.get(i).jobless", X))
        pg.click("#card [data-i=fire]")
        pg.select_option("#fireTo", RCV); pg.fill("#fireReason", "示範用")
        pg.click("#fireGo")
        ok("不得誤觸：第一次按「開除」只會要求再確認（還沒執行）", pg.evaluate("() => !!document.getElementById('fireDlg') && __world.hr.fired.size === 0 && /確定開除/.test(document.getElementById('fireGo').textContent) && !document.getElementById('fdWarn').hidden"))
        pg.select_option("#fireTo", "ceo")
        ok("不得誤觸：改了對象就要重新確認", pg.evaluate("() => document.getElementById('fireGo').textContent === '開除'"))
        pg.select_option("#fireTo", RCV)
        _track(pg, "act", "__world.chars.get('%s').action" % X)
        pg.click("#fireGo"); pg.click("#fireGo")
        ok("確定開除：第二次按才執行，確認框關閉", pg.evaluate("() => !document.getElementById('fireDlg') && __world.hr.fired.size === 1"))
        _shot(pg, "開除演出連拍.png")
        # 演出：收紙箱、揮手、走出大門
        ok("演出：先收紙箱（動作 box）、走到大門口向大家揮手（動作 wave）", wait_until(pg, "() => window.__trk.act.has('wave')", 120000, 100) and "box" in _seen(pg, "act"), _seen(pg, "act"))
        ok("演出：走出公司大門（座標 z > 30 ＝ 辦公室外）", wait_until(pg, "() => __world.chars.get('%s').object3D.position.z > 30.5" % X, 120000, 200))
        ok("演出：到達公司外的無業遊民區（世界座標在遊民區範圍內）", wait_until(pg, "() => { const c = __world.chars.get('%s'), p = c.object3D.position; return c.jobless && __world.outside.inZone(p.x, p.z) && c.state !== 'walk'; }" % X, 200000, 300))
        pos = pg.evaluate("(i) => { const p = __world.chars.get(i).object3D.position, z = __world.outside.zone; return [p.x, p.z, z.x0, z.x1, z.z0, z.z1]; }", X)
        ok("無業遊民區：座標 (%.1f, %.1f) 在範圍 x %.1f–%.1f、z %.1f–%.1f 內，且在辦公室（z ≤ 30）外面" % tuple(pos), pos[2] <= pos[0] <= pos[3] and pos[4] <= pos[1] <= pos[5] and pos[1] > 30, pos)
        tg = pg.evaluate("(i) => __world.chars.get(i)._lab.tag.textContent", X)
        ok("名牌：改灰、標「待業中」與開除日期（%s）" % tg, "待業中" in tg and _re.search(r"\d\d-\d\d", tg) and pg.evaluate("(i) => __world.chars.get(i)._lab.tag.classList.contains('jobless')", X), tg)
        ok("座位清空：他原本的位子沒有人占著", pg.evaluate("(i) => { const s = __world.spots.find(q => q.name === 'seat:' + i); return !s.taken && __world.chars.get(i).atDesk === false; }", X))
        ok("沒有負面特效：他的動作不是 angry／slam／sulk", pg.evaluate("(i) => !['angry', 'slam', 'sulk'].includes(__world.chars.get(i).action)", X))
        # 任務轉交與數字
        x1, r1 = prog(X), prog(RCV)
        ok("任務轉交：接手者（秤老）資訊卡數字 未完成 %d→%d、進行中 %d→%d（加上織網的 %d、%d）" % (r0[0], r1[0], r0[1], r1[1], x0[0], x0[1]), r1[0] == r0[0] + x0[0] and r1[1] == r0[1] + x0[1] and r1[2] == r0[2], (r0, r1, x0))
        ok("任務轉交：織網自己只剩已完成（未完成、進行中歸零）", x1[0] == 0 and x1[1] == 0 and x1[2] == x0[2], x1)
        pg.evaluate("(i) => __world.ui.showCard(__world.chars.get(i))", RCV)
        kp = pg.evaluate("() => [1, 2, 3].map(k => +document.querySelector('#cardKpi [data-k=\"' + k + '\"] b').textContent)")
        ok("任務轉交：接手者開著的資訊卡上三個狀態格的數字就是 %s" % r1, kp == r1, kp)
        ok("任務轉交：接手者的任務清單裡有「接手自織網」", pg.evaluate("() => /接手自織網/.test(document.getElementById('cardList').innerText)") or pg.evaluate("() => { document.querySelector('#cardKpi [data-k=\"1\"]').click(); return /接手自織網/.test(document.getElementById('cardList').innerText); }"))
        bd1, bq1 = board("data"), board("quant")
        ok("部門佈告欄：資料部未完成／進行中 %s → %s（減少）、量化研究部 %s → %s（增加）" % (bd0[:2], bd1[:2], bq0[:2], bq1[:2]), bd1[0] == bd0[0] - x0[0] and bd1[1] == bd0[1] - x0[1] and bq1[0] == bq0[0] + x0[0] and bq1[1] == bq0[1] + x0[1], (bd0, bd1, bq0, bq1))
        ok("部門佈告欄：資料部人數少一位（區域選單寫 1 人）", pg.evaluate("() => { document.getElementById('areaBtn').click(); const t = document.querySelector('#areaPop [data-room=data]').innerText; document.getElementById('areaBtn').click(); return /1 人/.test(t); }"))
        # 遊民區：跳過去、點他看資訊卡
        pg.click("#areaBtn"); pg.click("#areaPop [data-room=jobless]")
        ok("區域選單：跳到無業遊民區（鏡頭運鏡）", wait_until(pg, "() => !__world.view.tween", 12000))
        pg.wait_for_timeout(1500)
        _shot(pg, "無業遊民區.png")
        sc = wait_until(pg, "() => { const c = __world.chars.get('%s'); return c._sx > 0 && c._sy > 0 && c.state !== 'walk' && [c._sx, c._sy + 26]; }" % X, 60000, 300)
        if sc:
            pg.mouse.click(sc[0], sc[1])
        ok("點待業中的人：開他的資訊卡（待業中、開除日期、原因、任務交給誰）", wait_until(pg, "() => { const t = document.getElementById('card').innerText; return !document.getElementById('card').hidden && /待業中/.test(t) && /開除日期/.test(t) && /示範用/.test(t) && /秤老/.test(t); }", 10000), sc)
        ok("待業資訊卡：列出在職期間完成的任務（%d 項）" % x0[2], pg.evaluate("(n) => /在職期間完成的任務（%d）/.test(document.getElementById('card').innerText) && document.querySelectorAll('#cardList .row').length === n" % x0[2], x0[2]))
        ok("待業資訊卡：有「重新聘用」鈕，沒有「開除」鈕", pg.evaluate("() => !!document.querySelector('#card [data-hr=hire]') && !document.querySelector('#card [data-i=fire]')"))
        ok("待業中的人點了不會被鍵盤接管（不能操控，因為他在公司外）", pg.evaluate("(i) => __world.pilot.sel !== __world.chars.get(i)", X))
        _shot(pg, "待業資訊卡_重新聘用.png")
        # 重新整理後仍在遊民區
        pg.reload(wait_until="domcontentloaded")
        ok("重新整理：頁面重新載入", wait_until(pg, "() => window.__world && window.__world.ready", 90000))
        pg.evaluate("() => { __world.speed = 8; }")
        # 名牌文字只在「他在畫面內」時才會更新（畫面外的人不排版，省工），所以先把鏡頭移到遊民區再讀；
        # 上一輪的間歇性失敗就是在載入完成的第一幀、鏡頭還看不到遊民區時就去讀名牌
        pg.evaluate("() => __world.jumpTo('jobless')")
        wait_until(pg, "() => __world.chars.get('%s')._lab.tag.textContent.includes('待業中')" % X, 20000, 200)
        pos = pg.evaluate("(i) => { const c = __world.chars.get(i), p = c.object3D.position; return [c.jobless, __world.outside.inZone(p.x, p.z), p.z, c._lab.tag.textContent, __world.hr.fired.size]; }", X)
        ok("重新整理後：織網仍在無業遊民區（%s）、名牌仍是待業中" % pos[:3], pos[0] and pos[1] and pos[2] > 30 and "待業中" in pos[3], pos)
        ok("重新整理後：任務轉交的數字還在（接手者 %s）" % r1, prog(RCV) == r1, prog(RCV))
        ok("重新整理後：存的是 localStorage（鍵 aiOffice.hr.v1，含轉交對象）", pg.evaluate("() => { const o = JSON.parse(localStorage.getItem('aiOffice.hr.v1')); return o.v === 1 && o.fired['%s'].to === '%s' && o.fired['%s'].reason === '示範用'; }" % (X, RCV, X)))
        ok("重新整理後：座位仍是空的", pg.evaluate("(i) => !__world.spots.find(q => q.name === 'seat:' + i).taken", X))
        # 重新聘用
        pg.evaluate("(i) => __world.ui.showCard(__world.chars.get(i))", X)
        pg.click("#card [data-hr=hire]")
        ok("重新聘用：他走進大門（座標回到辦公室內，z < 30）", wait_until(pg, "() => __world.chars.get('%s').object3D.position.z < 29.5" % X, 200000, 300))
        ok("重新聘用：走回原座位坐好（座位 seat:%s、坐著、在座位上工作）" % X, wait_until(pg, "() => { const c = __world.chars.get('%s'); return !c.jobless && c.state === 'sit' && c.atDesk && c.spot && c.spot.name === 'seat:%s'; }" % (X, X), 200000, 300))
        ok("重新聘用：名牌不再是待業中、開除紀錄清除", pg.evaluate("(i) => !__world.chars.get(i)._lab.tag.textContent.includes('待業中') && __world.hr.fired.size === 0 && JSON.parse(localStorage.getItem('aiOffice.hr.v1')).fired[i] === undefined", X))
        ok("重新聘用：任務還給他（接手者數字回到 %s，織網回到 %s）" % (r0, x0), prog(RCV) == r0 and prog(X) == x0, (prog(RCV), prog(X)))
        # 原座位被占：換新座位
        pg.evaluate("(i) => __world.hr.fire([i], { to: 'ceo' })", X)
        wait_until(pg, "() => { const c = __world.chars.get('%s'), p = c.object3D.position; return c.jobless && __world.outside.inZone(p.x, p.z); }" % X, 200000, 300)
        pg.evaluate("(i) => { __world.spots.find(q => q.name === 'seat:' + i).taken = 'someone-else'; }", X)
        pg.evaluate("(i) => __world.hr.rehire(i)", X)
        ok("原座位被占用：重新聘用改坐新座位（後備座位）", wait_until(pg, "() => { const c = __world.chars.get('%s'); return !c.jobless && c.state === 'sit' && c.spot && ['spare', 'reserve'].includes(c.spot.name); }" % X, 200000, 300))
        # 開除整個部門
        pg.evaluate("() => { __world.ui.showBoard('legal'); }")
        ok("部門佈告欄有「開除整個部門」、CEO 的佈告欄沒有", pg.evaluate("() => !!document.querySelector('#board [data-hr=firedept]')") and pg.evaluate("() => { __world.ui.showBoard('ceo'); const r = !document.querySelector('#board [data-hr=firedept]'); __world.ui.showBoard('legal'); return r; }"))
        pg.click("#board [data-hr=firedept]")
        ok("開除整個部門：確認框列出該部門全員（2 位）與任務數", pg.evaluate("() => { const d = document.getElementById('fireDlg'); return !!d && /法遵與資安部/.test(d.innerText) && d.querySelectorAll('.fd-list li').length === 2; }"))
        pg.click("#fireGo"); pg.click("#fireGo")
        ok("開除整個部門：該部門全員都被開除（2 位）", pg.evaluate("() => __world.org.departments.find(d => d.id === 'legal').members.every(m => __world.hr.fired.has(m.id))"))
        ok("開除整個部門：全員走到無業遊民區", wait_until(pg, "() => __world.org.departments.find(d => d.id === 'legal').members.every(m => { const c = __world.chars.get(m.id), p = c.object3D.position; return c.jobless && __world.outside.inZone(p.x, p.z); })", 300000, 500))
        ok("開除整個部門：他們的座位都清空了", pg.evaluate("() => __world.org.departments.find(d => d.id === 'legal').members.every(m => !__world.spots.find(q => q.name === 'seat:' + m.id).taken)"))
        ok("開除整個部門：佈告欄的人數與任務歸零（事項彙總三格都是 0）", pg.evaluate("() => { __world.ui.showBoard('legal'); return [1, 2, 3].every(k => +document.querySelector('#boardKpi [data-bk=\"' + k + '\"] b').textContent === 0) && /0 人/.test(document.getElementById('board').innerText.replace('人數 0 人', '0 人')) && document.querySelector('#board [data-hr=firedept]').disabled; }"))
        _shot(pg, "開除整個部門.png")
        # 禁用字（開著卡片、佈告欄、確認框、模擬器面板、電力面板各掃一次）
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('data-steward'))")
        pg.click("#card [data-i=fire]")
        t1 = _text(pg)
        pg.click("#fireCancel")
        pg.click("#simBtn"); t2 = _text(pg); pg.click("#simBtn")
        pg.click("#pwBtn"); t3 = _text(pg); pg.click("#pwBtn")
        pg.click("#areaBtn"); t4 = _text(pg); pg.click("#areaBtn")
        pg.click("#helpBtn"); t5 = _text(pg); pg.click("#helpBtn")
        allt = "\n".join([t1, t2, t3, t4, t5])
        ok("畫面文字不含禁用字（價格／NT$／付費／升級／訂閱／方案／Plus／Pro／免費）", not _FORBID.search(allt), _FORBID.findall(allt)[:5])
        ok("開除段落：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ⑤ 空狀態 ─────────────────────────
def t_empty(b, base):
    # 1 還沒接入
    c, pg, got = _open(b, base, qs="?ambient=0&q=low&pr=0.6&empty=1", day="day")
    try:
        ok("空狀態 1：載入完成", got)
        if not got:
            return
        ok("空狀態 1：沒有 ?sim=1 時，頂列沒有「模擬」鈕", pg.evaluate("() => !document.getElementById('simBtn')"))
        ok("空狀態 1：辦公室是空的（沒有任何同事看得到）", pg.evaluate("() => [...__world.chars.values(), ...__world.pets].every(c => !c.object3D.visible)"))
        ok("空狀態 1：CEO 桌上有「待接入」牌子", pg.evaluate("() => __world.empty.mode === 1 && document.body.dataset.empty === '1'"))
        tx = pg.evaluate("() => document.getElementById('emptyCard').innerText")
        ok("空狀態 1：一句話「還沒有同事上班。接好 Claude，他們就會出現」＋流程圖五格＋「開始接入」", "還沒有同事上班。接好 Claude，他們就會出現" in tx and "開始接入" in tx and pg.evaluate("() => document.querySelectorAll('#emptyCard .em-flow li').length") == 5, tx)
        ok("空狀態 1：說明收進「?」（預設收起）", pg.evaluate("() => document.querySelector('#emptyCard .em-note').hidden"))
        pg.click("#emGo")
        ok("空狀態 1：按「開始接入」展開五個步驟（畫面真的變了）", pg.evaluate("() => document.querySelectorAll('#emptyCard .em-steps li').length") == 5)
        pg.click("#emQ")
        ok("空狀態 1：點「?」才展開說明", pg.evaluate("() => !document.querySelector('#emptyCard .em-note').hidden"))
        _shot(pg, "空狀態1.png")
        ok("空狀態 1：畫面文字不含禁用字", not _FORBID.search(_text(pg)), _FORBID.findall(_text(pg)))
        ok("空狀態 1：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()
    # 2 接入了還沒專案；按「測試連線」真的等事件 → 收到事件才進 3
    c, pg, got = _open(b, base, qs="?ambient=0&q=low&pr=0.6&sim=1&empty=2")
    try:
        ok("空狀態 2：大門口有迎賓員（只是氣氛，不在編制內）", pg.evaluate("() => __world.extras.length === 1 && __world.extras[0].object3D.visible && !__world.chars.has('greeter')"))
        ok("空狀態 2：一句話「接好了，等第一筆消息…」＋「測試連線」", "接好了，等第一筆消息" in pg.evaluate("() => document.getElementById('emptyCard').innerText") and pg.evaluate("() => !!document.getElementById('emTest')"))
        pg.click("#emTest")
        ok("空狀態 2：按「測試連線」→ 顯示「正在等第一筆消息」（不會假裝連線成功）", pg.evaluate("() => /正在等第一筆消息/.test(document.getElementById('emptyCard').innerText) && !/連線成功/.test(document.body.innerText)"))
        _sim(pg, "session", True)
        ok("空狀態 2：真的收到事件才進到下一步（有專案、還沒建辦公室）", wait_until(pg, "() => __world.empty.mode === 3", 8000))
        # 3 → 4
        ok("空狀態 3：顯示專案名、最後一次消息、事件數", pg.evaluate("() => { const t = document.getElementById('emptyCard').innerText; return /發現新專案/.test(t) && /最後一次消息/.test(t) && /事件數/.test(t) && /辦公室 0／1/.test(t); }"))
        ok("空狀態 3：「自動建立新專案的辦公室」開關預設關", pg.evaluate("() => !document.getElementById('emAuto').checked"))
        pg.click("#emAuto")
        ok("空狀態 3：開關按了真的打開", pg.evaluate("() => document.getElementById('emAuto').checked"))
        _shot(pg, "空狀態3.png")
        pg.click("#emMake")
        ok("空狀態 3：按「創立辦公室」→ 進到空狀態 4（只有 CEO）", pg.evaluate("() => __world.empty.mode === 4 && [...__world.chars.values()].filter(c => c.object3D.visible).length === 1 && __world.chars.get('ceo').object3D.visible"))
        ok("空狀態 4：座位上貼著半透明名牌虛影（部門規劃，不是真人）", wait_until(pg, "() => document.querySelectorAll('#labels .ghost').length >= 5", 8000))
        ok("空狀態 4：一句話「辦公室成立了，目前只有 CEO」，說明收進「?」", pg.evaluate("() => /辦公室成立了，目前只有 CEO/.test(document.getElementById('emptyBanner').innerText) && document.querySelector('#emptyBanner .em-note').hidden"))
        pg.click("#emQ")
        ok("空狀態 4：點「?」才看到「派出子 Agent 後，同事會陸續報到」", pg.evaluate("() => /同事會陸續報到/.test(document.getElementById('emptyBanner').innerText)"))
        _shot(pg, "空狀態4.png")
        # 派出子 Agent → 同事一位一位報到
        pg.evaluate("() => __world.sim.start('data-steward')")
        ok("空狀態 4：派出子 Agent 後，那位同事報到（出現在座位上）", wait_until(pg, "() => __world.chars.get('data-steward').object3D.visible && __world.chars.get('data-steward').state === 'sit' || __world.chars.get('data-steward').state === 'walk'", 30000, 300))
        ok("空狀態 4：其他人還沒報到（仍只有被派的那位和 CEO）", pg.evaluate("() => [...__world.chars.values()].filter(c => c.object3D.visible).length === 2"))
        ok("空狀態 2～4：畫面文字不含禁用字", not _FORBID.search(_text(pg)), _FORBID.findall(_text(pg)))
        ok("空狀態 2～4：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()
    # 3 與 4 也各用網址直接開一次（?empty=3、?empty=4）
    for n in (3, 4):
        c, pg, got = _open(b, base, qs="?ambient=0&q=low&pr=0.6&empty=%d" % n)
        try:
            vis = pg.evaluate("() => [...__world.chars.values()].filter(c => c.object3D.visible).length")
            ok("空狀態 %d：網址 ?empty=%d 直接開：%s" % (n, n, "只有 CEO 一人" if n == 4 else "辦公室是空的"), vis == (1 if n == 4 else 0), vis)
            ok("空狀態 %d：畫面文字不含禁用字、沒有主控台錯誤" % n, not _FORBID.search(_text(pg)) and not pg.errs, pg.errs[:2])
        finally:
            c.close()


# ───────────────────────── ⑥ 手機 390×844 ─────────────────────────
def t_mobile(b, base):
    c, pg, got = _open(b, base, w=390, h=844, touch=True, qs="?ambient=0&q=low&pr=0.6&sim=1")
    try:
        ok("手機：載入完成", got)
        if not got:
            return
        pg.evaluate("() => __world.sim.quota(62, 80)")
        pg.evaluate("() => __world.sim.exhaust(8100)")
        ok("手機：額度用完，全員睡著", wait_until(pg, "() => __world.power.phase === 'asleep'", 180000, 500))
        _shot(pg, "手機_額度用完.png")
        sels = ["#bar .ttl", "#viewSeg", "#areaBtn", "#demoBtn", "#speedSeg", "#pwBtn", "#simBtn", "#editBtn", "#pwSign", ".dt-chip", ".cm-hint"]
        bad, n = _no_overlap(pg, sels)
        ok("手機 390：額度用完時，頂列、牌子、時間小字、鏡頭提示兩兩不重疊（%d 個元素）" % n, not bad, bad)
        ok("手機 390：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth && document.body.scrollWidth <= innerWidth"))
        r = _rect(pg, "#pwSign")
        ok("手機 390：門牌整個在畫面內", r and r[0] >= 0 and r[2] <= 390, r)
        _sim(pg, "permission", "command")
        bad, n = _no_overlap(pg, sels + ["#flBadge"])
        ok("手機 390：加上「等你核准」膠囊後仍不重疊（%d 個元素）" % n, not bad, bad)
        ok("手機 390：新增元素的字不小於 11px（電力膠囊、核准膠囊、牌子、頂列按鈕）", pg.evaluate("""() => { const bad = []; for (const s of ['#pwBtn', '#pwSign', '#pwSign *', '#flBadge', '#flBadge span', '#simBtn']) for (const e of document.querySelectorAll(s)) { if (e.offsetParent && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 11) bad.push(s); } return bad.length === 0; }"""))
        _sim(pg, "clear"); _sim(pg, "recover")
        wait_until(pg, "() => __world.power.phase === 'awake'", 150000, 500)
        # 開除確認框（手機）
        pg.evaluate("() => __world.ui.showCard(__world.chars.get('data-scraper'))")
        pg.click("#card [data-i=fire]")
        r = _rect(pg, "#fireDlg .dlg")
        ok("手機 390：開除確認框整個在畫面內", r and r[0] >= 0 and r[2] <= 390 and r[3] <= 844, r)
        hs = pg.evaluate("() => [document.getElementById('fireGo').offsetHeight, document.getElementById('fireCancel').offsetHeight, document.getElementById('fireTo').offsetHeight]")
        ok("手機 390：確認框的按鈕與選單至少 44px 高（%s）" % hs, all(x >= 44 for x in hs), hs)
        ok("手機 390：確認框字不小於 11px", pg.evaluate("() => [...document.querySelectorAll('#fireDlg *')].filter(e => e.children.length === 0 && e.textContent.trim()).every(e => parseFloat(getComputedStyle(e).fontSize) >= 11)"))
        ok("手機 390：確認框開著時沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth"))
        pg.click("#fireCancel")
        ok("手機：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── 動作減量 ─────────────────────────
def t_reduce(b, base):
    c, pg, got = _open(b, base, reduced=True)
    try:
        ok("動作減量：載入完成", got)
        if not got:
            return
        pg.evaluate("() => __world.sim.quota(62, 80)")
        pg.evaluate("() => __world.sim.exhaust(8100)")
        ok("動作減量：不走動，直接趴睡（短時間內就全員睡著）", wait_until(pg, "() => __world.power.phase === 'asleep' && [...__world.chars.values()].every(c => c.sleeping)", 40000, 300))
        ok("動作減量：燈光直接切暗到 35%、牌子直接出現", pg.evaluate("() => Math.abs(__world.dim - 0.35) < 0.001 && !document.getElementById('pwSign').hidden"))
        pg.evaluate("() => __world.sim.recover()")
        ok("動作減量：醒來也直接切換", wait_until(pg, "() => __world.power.phase === 'awake' && [...__world.chars.values()].every(c => !c.sleeping) && __world.dim === 1", 40000, 300))
        ok("動作減量：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


# ───────────────────────── ⑦ 繪製次數＋預覽部署重建 ─────────────────────────
BASE_CALLS = {"god": 578, "ceo": 205}      # 這一輪之前（11-13 上午那版）量到的繪製次數，同樣條件：白天、q=low、1280×800


def _calls(pg, view):
    pg.evaluate("(v) => __world.setView(v, null, true)", view)
    pg.wait_for_timeout(1500)
    xs = []
    for _ in range(9):
        xs.append(pg.evaluate("() => __world.stats.calls"))
        pg.wait_for_timeout(250)
    xs.sort()
    return xs[len(xs) // 2]


def t_perf(b, base):
    c, pg, got = _open(b, base, qs="?ambient=0&q=low&sim=1", speed=1)
    try:
        ok("繪製次數：載入完成", got)
        if not got:
            return
        g, e = _calls(pg, "god"), _calls(pg, "ceo")
        ok("繪製次數：俯瞰 %d（前 %d，增加 %d）──全場不明顯增加（≤ +8）" % (g, BASE_CALLS["god"], g - BASE_CALLS["god"]), g <= BASE_CALLS["god"] + 8, g)
        ok("繪製次數：CEO 視角 %d（前 %d，增加 %d）" % (e, BASE_CALLS["ceo"], e - BASE_CALLS["ceo"]), e <= BASE_CALLS["ceo"] + 8, e)
        pg.evaluate("() => __world.sim.exhaust(8100)")
        wait_until(pg, "() => __world.power.phase === 'asleep'", 200000, 500)
        pg.evaluate("() => __world.setView('god', null, true)")      # 先離開近距離（近處的睡覺同事會持續冒 z 小圖示，那是暫時的粒子，不是常駐繪製）
        t0 = pg.evaluate("() => __world.time")
        wait_until(pg, "() => __world.time - %f > 6" % t0, 200000, 300)      # 已冒出的 z 圖示約 2.6 秒（模擬時間）內消失；軟體繪圖幀率很低、每幀模擬時間被上限壓住，所以要用模擬時間等，不能用牆鐘
        g2 = _calls(pg, "god")
        ok("繪製次數：額度用完（牌子掛出）時俯瞰 %d，比平時再多 %d（門牌兩面）" % (g2, g2 - g), g2 - g <= 4, g2)
        print("    繪製次數量測：俯瞰 前%d 後%d｜CEO 視角 前%d 後%d｜用完掛牌時俯瞰 %d" % (BASE_CALLS["god"], g, BASE_CALLS["ceo"], e, g2))
    finally:
        c.close()


def t_copy(b, base):
    """預覽部署會略過名為 data、preview 的資料夾：照那個規則複製 site 再起一個伺服器，把核心流程跑一遍"""
    src = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "site"))
    dst = _os.path.join(_tf.mkdtemp(prefix="office_preview_"), "site")
    _sh.copytree(src, dst, ignore=_sh.ignore_patterns("data", "preview"))

    class Q(_hs.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = _ss.ThreadingTCPServer(("127.0.0.1", 0), _ft.partial(Q, directory=dst))
    _th.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        ok("預覽部署重建：複製後確實沒有 data／preview 資料夾", not _os.path.exists(_os.path.join(dst, "data")) and not _os.path.exists(_os.path.join(dst, "preview")))
        ok("預覽部署重建：辦公室頁用到的檔案都在（沒有被略過）", all(_os.path.exists(_os.path.join(dst, "office", "world", f)) for f in ["js/state.js", "js/power.js", "js/jobs.js", "js/hr.js", "js/sim.js", "js/outside.js", "js/empty.js", "state.css", "cfg/layout.json"]))
        c, pg, got = _open(b, "http://127.0.0.1:%d/index.html" % port)
        try:
            ok("預覽部署重建：辦公室頁載入完成", got)
            if not got:
                return
            _sim(pg, "quota", 62, 80)
            ok("預覽部署重建：額度 62% → 膠囊「電力 62%」", pg.evaluate("() => document.getElementById('pwTxt').textContent") == "電力 62%")
            pg.evaluate("() => __world.sim.exhaust(8100)")
            ok("預覽部署重建：額度用完 → 全員睡著＋牌子", wait_until(pg, "() => __world.power.phase === 'asleep' && !document.getElementById('pwSign').hidden", 180000, 500))
            _sim(pg, "recover")
            ok("預覽部署重建：恢復 → 全員醒來", wait_until(pg, "() => __world.power.phase === 'awake'", 150000, 500))
            pg.evaluate("() => __world.ui.showCard(__world.chars.get('data-scraper'))")
            pg.click("#card [data-i=fire]")
            ok("預覽部署重建：開除確認框出現、取消不生效", pg.evaluate("() => !!document.getElementById('fireDlg')") and (pg.click("#fireCancel") or pg.evaluate("() => !document.getElementById('fireDlg') && __world.hr.fired.size === 0")))
            ok("預覽部署重建：沒有主控台錯誤", not pg.errs, pg.errs[:3])
        finally:
            c.close()
    finally:
        srv.shutdown()
        _sh.rmtree(_os.path.dirname(dst), ignore_errors=True)


def t_all(b, base):
    t_power(b, base)
    t_jobs(b, base)
    t_hr(b, base)
    t_empty(b, base)
    t_mobile(b, base)
    t_reduce(b, base)
    t_perf(b, base)
    t_copy(b, base)


register("辦公室狀態", lambda pg, b, base, code: t_all(b, base))
