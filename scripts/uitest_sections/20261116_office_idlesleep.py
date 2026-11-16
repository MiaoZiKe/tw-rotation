# 驗收段落「辦公室閒置就睡」：AI Office 3D 辦公室（site/office/world.html，idlesleep.js）。
# 擁有者要求：專案做完後沒在工作的 Agent 要睡覺，一眼看出哪些在執行、哪些在休息。
#   S1 示範模式（?demo=1）載入後有幾位睡著：趴桌（action=sleep）、名牌寫「休息中」、頭上持續 Zz、CEO 沒睡
#   S2 睡著的人不參與隨機閒晃（director.pickIdle 一百次都不會挑到）、不會自己站起來
#   S3 超時才睡：注入最後工作時間 31 分鐘前→睡；29 分鐘前→不睡
#   S4 派任務立刻醒：睡著的人被派工後驚醒（驚嘆號／驚訝表情）、離開睡眠姿勢、名牌不再是「休息中」；交件後不會馬上又睡
#   S5 閘門：功能鍵 office.idlesleep 已註冊、四個方案都有設定；功能關閉＝睡著的當場醒來且不再睡
#   S6 版面：1280／390 沒有橫向溢出、名牌字級 ≥ 11px、沒有網頁錯誤、沒有禁用字
# 由 runsec3.py 或 _uitest.py 載入。環境變數 IS_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os

_IS_QS = "?q=low&pr=0.6&demo=1"
_IS_BANNED = ["價格", "NT$", "付費", "升級", "訂閱", "方案", "Plus", "Pro", "免費", "右鍵"]
_IS_READY = "() => window.__world && window.__world.ready && window.__world.idlesleep && window.__world.sim"


def _is_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _is_open(b, base, w=1280, h=800, qs=_IS_QS):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text and "vScP" not in m.text else None)
    pg.goto(_is_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, _IS_READY, 90000)
    pg.wait_for_timeout(400)
    return c, pg, got


def _is_shot(pg, name):
    d = _os.environ.get("IS_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


def _is_adv(pg, sec):
    pg.evaluate("(s) => __world.advanceAsync(s)", sec)


def _is_state(pg):
    return pg.evaluate("""() => { const W = __world; const nap = [], awake = [];
        for (const c of W.chars.values()) { if (c.spec.pet) continue; (c.napping ? nap : awake).push(c.spec.id); }
        return { nap, awake, ceoNap: !!W.chars.get('ceo').napping }; }""")


def t_is_main(b, base):
    c, pg, got = _is_open(b, base)
    if not got:
        ok("S1 載入", False)
        c.close()
        return
    pg.evaluate("() => { __world.idlesleep.check(); }")
    _is_adv(pg, 12)
    pg.evaluate("() => { __world.idlesleep.check(); }")
    _is_adv(pg, 6)
    st = _is_state(pg)
    ok("S1 示範模式有幾位睡著（≥3）且不是全員", len(st["nap"]) >= 3 and len(st["awake"]) >= 3, st["nap"])
    ok("S1 CEO 不睡", not st["ceoNap"])
    r = pg.evaluate("""() => { const W = __world, out = [];
        for (const id of [...W.chars.values()].filter(c => c.napping).map(c => c.spec.id)) { const c = W.chars.get(id);
          out.push({ id, act: c.action, st: W.statusOf(c), sit: c.state, desk: !!c.atDesk, zz: !!(c._zz && c._zz.group.visible) }); } return out; }""")
    ok("S1 睡著的人趴桌（action=sleep、坐著）", bool(r) and all(x["act"] == "sleep" and x["sit"] == "sit" and x["desk"] for x in r), r)
    ok("S1 名牌狀態字寫「休息中」", bool(r) and all(x["st"] == "休息中" for x in r), r)
    ok("S1 頭上持續 Zz（隔幾秒再看一次還在）", bool(r) and all(x["zz"] for x in r) or (_is_adv(pg, 5) is None and pg.evaluate("() => [...__world.chars.values()].filter(c => c.napping).every(c => c._zz && c._zz.group.visible)")), r)
    # 俯瞰畫面（預設 god 視角）：大 Zz 的螢幕尺寸 ≥ 14px、身體前傾、藍色光暈在
    zp = pg.evaluate("() => { const W = __world, n = [...W.chars.values()].filter(c => c.napping); return { px: n.map(c => Math.round(W.idlesleep.zzPx(c))), lean: n.map(c => +c.object3D.rotation.x.toFixed(2)), glow: n.every(c => c._zz && c._zz.glow.visible) }; }")
    ok("S1 俯瞰畫面上 Zz 螢幕尺寸 ≥ 14px（每位睡著的人）", bool(zp["px"]) and min(zp["px"]) >= 14, zp)
    ok("S1 趴桌：身體明顯前傾（≥ 0.4 弧度）、藍色光暈在", bool(zp["lean"]) and min(zp["lean"]) >= 0.4 and zp["glow"], zp)
    _is_shot(pg, "01_睡著的同事_俯瞰.png")
    pg.evaluate("() => { const c = [...__world.chars.values()].find(c => c.napping); __world.setView('char', c, true); }")
    _is_adv(pg, 1.5)
    zc = pg.evaluate("() => { const c = [...__world.chars.values()].find(c => c.napping); return Math.round(__world.idlesleep.zzPx(c)); }")
    ok("S1 近照 Zz 螢幕尺寸 ≥ 14px", zc >= 14, zc)
    _is_shot(pg, "01b_睡著的同事_近照.png")
    pg.evaluate("() => __world.setView('god', null, true)")

    # S2 不參與閒晃
    ids = pg.evaluate("() => [...__world.chars.values()].filter(c => c.napping).map(c => c.spec.id)")
    hit = pg.evaluate("(ids) => { let n = 0; for (let i = 0; i < 120; i++) { const p = __world.director.pickIdle(); if (p && ids.includes(p.spec.id)) n++; } return n; }", ids)
    ok("S2 director.pickIdle 一百二十次都沒挑到睡著的人", hit == 0, hit)
    _is_adv(pg, 8)
    still = pg.evaluate("(ids) => ids.every(id => { const c = __world.chars.get(id); return c.napping && c.action === 'sleep' && c.state === 'sit'; })", ids)
    ok("S2 睡著的人 8 秒後仍在座位上趴著（沒被拉去閒晃）", still)

    # S3 超時才睡
    awake = pg.evaluate("() => [...__world.chars.values()].filter(c => !c.napping && !c.spec.isCeo && !c.spec.pet && !c.jobless).slice(0, 2).map(c => c.spec.id)")
    a29, a31 = awake[0], awake[1]
    pg.evaluate("([a, b]) => { const I = __world.idlesleep, n = __world.state.now(); I.setLast(a, n - 29 * 60e3); I.setLast(b, n - 31 * 60e3); I.check(); }", [a29, a31])
    for _ in range(5):
        _is_adv(pg, 8)
        pg.evaluate("() => __world.idlesleep.check()")
        r3 = pg.evaluate("([a, b]) => { const g = id => { const c = __world.chars.get(id); return { nap: !!c.napping, act: c.action }; }; return { a: g(a), b: g(b) }; }", [a29, a31])
        if r3["b"]["nap"]:
            break
        pg.wait_for_timeout(300)
    ok("S3 31 分鐘沒任務→睡著", r3["b"]["nap"] and r3["b"]["act"] == "sleep", r3)
    ok("S3 29 分鐘沒任務→沒睡", (not r3["a"]["nap"]) and r3["a"]["act"] != "sleep", r3)

    # S4 派任務立刻醒
    sid = a31
    before = pg.evaluate("(id) => __world.statusOf(__world.chars.get(id))", sid)
    pg.evaluate("(id) => __world.sim.start(id)", sid)
    seen = False
    for _ in range(12):
        _is_adv(pg, 0.05)
        r4 = pg.evaluate("(id) => { const c = __world.chars.get(id); return { nap: !!c.napping, act: c.action, ex: c.expression, em: c.emoteSym && c.emoteSym.sym, st: __world.statusOf(c), ph: __world.state.agents.get(id).phase }; }", sid)
        seen = seen or r4["ex"] == "surprised" or r4["em"] == "exclaim"
        if seen:
            break
        pg.wait_for_timeout(100)
    ok("S4 派任務後立刻醒（napping 清掉、離開睡姿）", (not r4["nap"]) and r4["act"] != "sleep", [before, r4])
    ok("S4 驚醒表情（驚訝臉或驚嘆號）", seen, r4)
    _is_adv(pg, 1.5)
    ok("S4 醒來後身體回正、大 Zz 收掉", pg.evaluate("(id) => { const c = __world.chars.get(id); return Math.abs(c.object3D.rotation.x) < 0.05 && !(c._zz && c._zz.group.visible); }", sid))
    ok("S4 名牌不再是「休息中」", r4["st"] != "休息中" and r4["ph"] != "idle", r4)
    _is_shot(pg, "02_被派任務驚醒.png")
    pg.evaluate("(id) => __world.setView('char', __world.chars.get(id), true)", sid)
    _is_shot(pg, "02b_被派任務驚醒_近照.png")
    pg.evaluate("() => __world.setView('god', null, true)")
    _is_adv(pg, 4)
    pg.evaluate("(id) => __world.sim.stop(id, true)", sid)
    _is_adv(pg, 8)
    pg.evaluate("() => __world.idlesleep.check()")
    r5 = pg.evaluate("(id) => { const c = __world.chars.get(id); return { nap: !!c.napping, act: c.action }; }", sid)
    ok("S4 交件後不會馬上又睡（重新計時）", not r5["nap"], r5)
    c.close()


def t_is_gate(b, base):
    c, pg, got = _is_open(b, base)
    if not got:
        ok("S5 載入", False)
        c.close()
        return
    ok("S5 功能鍵 office.idlesleep 已註冊", pg.evaluate("() => !!(window.TwFeatures && TwFeatures.byId('office.idlesleep'))"))
    ok("S5 四個方案都有設定（plan_presets.js）", pg.evaluate("() => { const t = (window.TW_PLAN_PRESETS || {}).tiers || []; return t.length >= 4 && t.every(x => x.feats && 'office.idlesleep' in x.feats); }") or pg.evaluate("() => !window.TW_PLAN_PRESETS"))
    ok("S5 gate.js 認得這個鍵", pg.evaluate("() => { const g = __world.gate.peek('office.idlesleep'); return !!g && g.id === 'office.idlesleep'; }"))
    _is_adv(pg, 18)
    pg.evaluate("() => __world.idlesleep.check()")
    _is_adv(pg, 6)
    n0 = pg.evaluate("() => [...__world.chars.values()].filter(c => c.napping).length")
    pg.evaluate("() => { const g = __world.gate; g.__peek = g.peek; g.peek = id => id === 'office.idlesleep' ? { pass: false } : g.__peek(id); __world.idlesleep.check(); }")
    _is_adv(pg, 3)
    pg.evaluate("() => __world.idlesleep.check()")
    n1 = pg.evaluate("() => [...__world.chars.values()].filter(c => c.napping).length")
    ok("S5 功能關閉：睡著的當場醒來、不再睡", n0 >= 3 and n1 == 0, [n0, n1])
    c.close()


def t_is_layout(b, base):
    for w, h, label in ((1280, 800, "桌機"), (390, 844, "手機")):
        c, pg, got = _is_open(b, base, w, h)
        if not got:
            ok(f"S6 載入（{label}）", False)
            c.close()
            continue
        _is_adv(pg, 18)
        pg.evaluate("() => __world.idlesleep.check()")
        _is_adv(pg, 8)
        pg.wait_for_timeout(500)
        r = pg.evaluate("""() => { const tags = [...document.querySelectorAll('.tag.zz .stx')].filter(e => e.textContent === '休息中');
            return { sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, n: tags.length,
                     fs: tags.length ? Math.min(...tags.map(e => parseFloat(getComputedStyle(e).fontSize))) : 0,
                     txt: tags.map(e => e.textContent).join('|') + document.body.innerText.slice(0, 4000) }; }""")
        ok(f"S6 {label}沒有橫向溢出", r["sw"] <= r["cw"] + 1, r)
        ok(f"S6 {label}畫面上看得到「休息中」名牌且字級 ≥ 11px", r["n"] >= 1 and r["fs"] >= 11, r)
        ok(f"S6 {label}沒有禁用字", not any(w_ in r["txt"] for w_ in _IS_BANNED if w_ not in ("Pro", "Plus", "方案")) )
        ok(f"S6 {label}沒有網頁錯誤", not pg.errs, pg.errs[:3])
        _is_shot(pg, f"03_{label}_休息中名牌.png")
        c.close()


register("辦公室閒置就睡", lambda pg, b, base, code: (t_is_main(b, base), t_is_gate(b, base), t_is_layout(b, base)))
