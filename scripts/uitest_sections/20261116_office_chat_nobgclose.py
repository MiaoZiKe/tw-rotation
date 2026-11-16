# 驗收段落「辦公室對話框不因點背景收起」（2026-11-16）：AI 辦公室（site/office/world.html）
# 擁有者原話：對話框只能由使用者按收合鈕（右上角 ﹀）或 Esc 收起；點場景背景、拖曳鏡頭、點角色都不准收起（不論有沒有鎖定）。
# 桌機 1280 與手機 390 都驗；手機打開後看的是清單，所以先進對話串再點背景。環境變數 NB_SHOTS 指到資料夾時順便存截圖。
# flake8: noqa

import os as _os


def _nb_open(pg):
    return pg.evaluate("() => !!(window.__world && window.__world.chat && window.__world.chat.open)")


def _nb_run(b, base, w, h, mobile):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=mobile, is_mobile=mobile)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.game.tour','1');}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(60000)
    tag = "手機390" if mobile else "桌機1280"
    try:
        pg.goto(root + "/office/world.html?demo=1&ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat", 90000)
        ok(f"對話框不收（{tag}）：辦公室載入", got)
        if not got:
            return
        pg.evaluate("() => window.__world.chat.openTo('ceo')")
        pg.wait_for_timeout(600)
        ok(f"對話框不收（{tag}）：打開後是開著的", _nb_open(pg) and pg.is_visible("#chatPanel"))
        for lock in ([False] if mobile else [False, True]):
            if lock != pg.evaluate("() => !!document.querySelector('#mcLock[aria-pressed=true]')") and not mobile:
                pg.click("#mcLock")
                pg.wait_for_timeout(200)
            # 取對話框外、場景裡一個空白點（右上偏中，避開頂列與對話框）
            box = pg.evaluate("() => { const r = document.getElementById('chatPanel').getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }")
            pts = [(w * 0.5, 120 if not mobile else 90), (w * 0.8, h * 0.35), (w * 0.2, h * 0.3)]
            pts = [p for p in pts if not (box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3])]
            for (x, y) in pts:
                pg.mouse.click(x, y)
                pg.wait_for_timeout(250)
            if mobile:      # 手機對話框是全螢幕、沒有背景可點：直接對場景畫布送完整的按下／放開／點擊事件
                pg.evaluate("() => { const cv = document.querySelector('canvas'); for (const t of ['pointerdown','pointerup','click']) cv.dispatchEvent(new PointerEvent(t, { bubbles: true, clientX: 195, clientY: 60, pointerType: 'touch' })); }")
                pg.wait_for_timeout(250)
                pts = [(195, 60)]
            # 外部呼叫 close() 不帶「user」不准收
            pg.evaluate("() => window.__world.chat.close()")
            pg.wait_for_timeout(150)
            ok(f"對話框不收（{tag}，鎖定={lock}）：點場景空白處 {len(pts)} 次後仍開著", _nb_open(pg) and pg.is_visible("#chatPanel"), pts)
            x0, y0 = pts[0]
            pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x0 + 160, y0 + 40, steps=8); pg.mouse.move(x0 - 120, y0 + 80, steps=8); pg.mouse.up()
            pg.wait_for_timeout(300)
            ok(f"對話框不收（{tag}，鎖定={lock}）：拖曳鏡頭後仍開著", _nb_open(pg) and pg.is_visible("#chatPanel"))
        d = _os.environ.get("NB_SHOTS")
        if d:
            _os.makedirs(d, exist_ok=True)
            pg.screenshot(path=_os.path.join(d, f"after_bgclick_{w}.png"))
        # 只有收合鈕與 Esc 會收
        pg.click("#chatX")
        pg.wait_for_timeout(300)
        ok(f"對話框不收（{tag}）：按收合鈕 ﹀ 收起", not _nb_open(pg) and pg.evaluate("() => !document.getElementById('chatPanel').classList.contains('open')"))
        if not mobile:
            pg.evaluate("() => window.__world.chat.openTo('ceo')")
            pg.wait_for_timeout(400)
            pg.focus("#chatPanel textarea")
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            ok(f"對話框不收（{tag}）：Esc 收起", not _nb_open(pg))
    finally:
        c.close()


def t_office_chat_nobgclose(b, base):
    _nb_run(b, base, 1280, 800, False)
    _nb_run(b, base, 390, 844, True)


register("辦公室對話框點背景不收", lambda pg, b, base, code: t_office_chat_nobgclose(b, base))
