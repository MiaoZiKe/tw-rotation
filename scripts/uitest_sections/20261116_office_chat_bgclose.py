# 驗收段落「辦公室對話框點背景自動收起」（2026-11-16）：AI 辦公室（site/office/world.html）
# 擁有者原話：「收起來 這樣方便操作，我點擊背景後 會自動收起」。
# 桌機：對話框開著時點 3D 場景空白處／角色 → 收起（點角色資訊卡照開）；拖曳鏡頭、點對話框內部、鎖定打開時 → 不收。
# 手機 390 對話框全螢幕沒有背景可點，行為不變（對場景畫布送點擊不收）。環境變數 BC_SHOTS 指到資料夾時存「點背景前／後」截圖。
# flake8: noqa

import os as _os


def _bc_open(pg):
    return pg.evaluate("() => !!(window.__world && window.__world.chat && window.__world.chat.open)")


def _bc_open_chat(pg):
    pg.evaluate("() => window.__world.chat.openTo('ceo')")
    pg.wait_for_timeout(500)


def _bc_empty_pts(pg, w, h):
    # 取對話框外、且最上層元素就是場景畫布的點（避開頂列、面板、角色）
    return pg.evaluate("""([w, h]) => {
      const out = []; const cv = document.getElementById('cv');
      const cs = [...__world.chars.values()].map(c => [c._sx, c._sy]);
      for (const [fx, fy] of [[.5,.2],[.8,.35],[.2,.3],[.65,.5],[.35,.55],[.9,.6],[.1,.6]]) {
        const x = w * fx, y = h * fy;
        if (document.elementFromPoint(x, y) !== cv) continue;
        if (cs.some(p => Math.hypot(p[0] - x, p[1] - y) < 70)) continue;
        out.push([x, y]);
      }
      return out; }""", [w, h])


def _bc_desktop(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 1280, "height": 800})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.game.tour','1');}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(60000)
    shots = _os.environ.get("BC_SHOTS")
    try:
        pg.goto(root + "/office/world.html?demo=1&ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat", 90000)
        ok("點背景收起（桌機）：辦公室載入", got)
        if not got:
            return
        pg.wait_for_timeout(1500)
        _bc_open_chat(pg)
        ok("點背景收起（桌機）：打開後是開著的", _bc_open(pg) and pg.is_visible("#chatPanel"))
        pts = _bc_empty_pts(pg, 1280, 800)
        ok("點背景收起（桌機）：找得到場景空白點", len(pts) >= 2, pts)
        if len(pts) < 2:
            return
        if shots:
            _os.makedirs(shots, exist_ok=True); pg.screenshot(path=_os.path.join(shots, "before_click_1280.png"))
        # 1) 點對話框內部不收
        pg.click("#chatPanel textarea"); pg.wait_for_timeout(250)
        ok("點背景收起（桌機）：點對話框內部不收", _bc_open(pg) and pg.is_visible("#chatPanel"))
        # 2) 拖曳鏡頭不收
        x0, y0 = pts[0]
        pg.mouse.move(x0, y0); pg.mouse.down(); pg.mouse.move(x0 + 160, y0 + 40, steps=8); pg.mouse.move(x0 - 100, y0 + 60, steps=8); pg.mouse.up()
        pg.wait_for_timeout(300)
        ok("點背景收起（桌機）：拖曳鏡頭不收", _bc_open(pg) and pg.is_visible("#chatPanel"))
        # 3) 鎖定打開時點背景不收；解鎖後點背景收起
        pg.click("#mcLock"); pg.wait_for_timeout(200)
        ok("點背景收起（桌機）：鎖定已打開", pg.evaluate("() => !!document.querySelector('#mcLock[aria-pressed=true]')"))
        x1, y1 = pts[1]
        pg.mouse.click(x1, y1); pg.wait_for_timeout(350)
        ok("點背景收起（桌機）：鎖定時點空白處不收", _bc_open(pg) and pg.is_visible("#chatPanel"))
        pg.click("#mcLock"); pg.wait_for_timeout(200)
        ok("點背景收起（桌機）：鎖定已解除", pg.evaluate("() => !document.querySelector('#mcLock[aria-pressed=true]')"))
        pg.mouse.click(x1, y1); pg.wait_for_timeout(400)
        ok("點背景收起（桌機）：點場景空白處 → 收起", not _bc_open(pg) and not pg.evaluate("() => document.getElementById('chatPanel').classList.contains('open')"))
        if shots:
            pg.screenshot(path=_os.path.join(shots, "after_click_1280.png"))
        # 4) 點角色：收起且資訊卡照開
        _bc_open_chat(pg)
        ok("點背景收起（桌機）：再次打開", _bc_open(pg))
        cp = pg.evaluate("""() => { const cv = document.getElementById('cv'), pn = document.getElementById('chatPanel').getBoundingClientRect();
          for (const c of __world.chars.values()) { if (c.spec.pet) continue;
            for (const dy of [0, -10, -20, -30, -40, 10]) { const x = c._sx, y = c._sy + dy;
              if (!(x > 0 && y > 0 && x < innerWidth && y < innerHeight)) continue;
              if (x >= pn.left && x <= pn.right && y >= pn.top && y <= pn.bottom) continue;
              if (document.elementFromPoint(x, y) !== cv) continue;
              const hit = __world.pickChar({ clientX: x, clientY: y, pointerType: 'mouse' });
              if (hit === c) return [x, y, c.spec.id]; } }
          return null; }""")
        ok("點背景收起（桌機）：找得到可點的角色", bool(cp), cp)
        if cp:
            pg.mouse.click(cp[0], cp[1]); pg.wait_for_timeout(500)
            ok("點背景收起（桌機）：點角色 → 對話框收起", not _bc_open(pg))
            ok("點背景收起（桌機）：點角色 → 角色資訊卡照常開", pg.evaluate("() => { const c = document.getElementById('card'); return !!c && !c.hidden; }"))
        # 5) 外部 close() 不帶 user 仍不收（原有保護）
        _bc_open_chat(pg)
        pg.evaluate("() => window.__world.chat.close()"); pg.wait_for_timeout(150)
        ok("點背景收起（桌機）：外部不帶 user 的 close() 不收", _bc_open(pg))
    finally:
        c.close()


def _bc_mobile(b, base):
    root = base.split("/index.html")[0].rstrip("/")
    c = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day');localStorage.setItem('aiOffice.game.tour','1');}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(60000)
    try:
        pg.goto(root + "/office/world.html?demo=1&ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
        got = wait_until(pg, "() => window.__world && window.__world.ready && window.__world.chat", 90000)
        ok("點背景收起（手機390）：辦公室載入", got)
        if not got:
            return
        _bc_open_chat(pg)
        pg.evaluate("() => { const cv = document.getElementById('cv'); for (const t of ['pointerdown','pointerup','click']) cv.dispatchEvent(new PointerEvent(t, { bubbles: true, button: 0, pointerId: 7, clientX: 195, clientY: 60, pointerType: 'touch' })); }")
        pg.wait_for_timeout(300)
        ok("點背景收起（手機390）：全螢幕對話框行為不變（對畫布點擊不收）", _bc_open(pg) and pg.is_visible("#chatPanel"))
        pg.click("#chatX"); pg.wait_for_timeout(300)
        ok("點背景收起（手機390）：按收合鈕仍可收起", not _bc_open(pg))
    finally:
        c.close()


def t_office_chat_bgclose(b, base):
    _bc_desktop(b, base)
    _bc_mobile(b, base)


register("辦公室對話框點背景收起", lambda pg, b, base, code: t_office_chat_bgclose(b, base))
