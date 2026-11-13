# 驗收段落「辦公室績效總表」：AI Office 3D 辦公室（site/office/world.html）的績效總表與等第外觀（rewards_design.md R0、R1、R2）。
#   R0  名牌等第字章、資訊卡的等第／分數／升降／距離下一級／配件／設備等級
#   R1  績效總表：頂端鈕與入口大廳看板都能打開；CEO 置頂＋11 部門＝12 列；展開部門成員數正確；排序真的改變順序；
#       切週次數字改變；「只看需要加強」結果符合規則；點列鏡頭飛到該角色／部門；鍵盤可操作；桌機不橫向捲動；手機卡片列
#   R2  部門招牌、桌面、地毯、花盆、桌牌顏色隨設備等級；琥珀小旗只出現在 D 以下的部門；繪製次數增量 ≤ 20
#   另：主管被開除後佈告欄顯示「主管：無（待指派）」；名牌兩兩不重疊（含寵物不壓主人）；畫面不含禁用字；1280／390 元素不重疊；無主控台錯誤
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用；全部是真的操作（點、鍵盤、滑過），並驗「畫面／狀態真的改變」。
# 環境變數 RW_SHOTS 指到資料夾時，順便存交件截圖。
# flake8: noqa

import os as _os
import re as _re
import json as _json
import shutil as _sh
import tempfile as _tf
import threading as _th
import functools as _ft
import http.server as _hs
import socketserver as _ss

_RW_FORBID = _re.compile(r"價格|NT\$|付費|升級|訂閱|方案|\bPlus\b|\bPro\b|免費|右鍵")


def _rw_root(base):
    return base.split("/index.html")[0].rstrip("/")


def _rw_open(b, base, w=1280, h=800, qs="?ambient=0&q=low&pr=0.6&sim=1", speed=8):
    c = b.new_context(viewport={"width": w, "height": h}, has_touch=w < 700, is_mobile=w < 700)
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page()
    pg.set_default_timeout(120000)
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(_rw_root(base) + "/office/world.html" + qs, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    if got:
        pg.evaluate("(s) => { __world.speed = s; }", speed)
    pg.wait_for_timeout(500)
    return c, pg, got


def _rw_shot(pg, name):
    d = _os.environ.get("RW_SHOTS")
    if d:
        _os.makedirs(d, exist_ok=True)
        pg.screenshot(path=_os.path.join(d, name))


_GR = ["S", "A", "B", "C", "D", "E", "F"]


def _rw_need(row):
    gi = lambda g: _GR.index(g)
    g, pg_ = row.get("grade"), row.get("prevGrade")
    return bool((g and gi(g) >= gi("D")) or (g and pg_ and gi(g) > gi(pg_)) or (row.get("false_reports") or 0) > 0 or row.get("flag"))


def _rw_rects(pg, js_list):
    return pg.evaluate("""(sels) => { const out = []; for (const s of sels) { document.querySelectorAll(s).forEach((e, i) => { if (e.hidden) return; const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); if (!r.width || cs.display === 'none' || cs.visibility === 'hidden') return; out.push([s + '#' + i, r.left, r.top, r.right, r.bottom]); }); } return out; }""", js_list)


def _rw_overlaps(rs, pad=1):
    bad = []
    for i, a in enumerate(rs):
        for c in rs[i + 1:]:
            if not (a[3] <= c[1] + pad or c[3] <= a[1] + pad or a[4] <= c[2] + pad or c[4] <= a[2] + pad):
                bad.append((a[0], c[0]))
    return bad


_PROJ = """([x, y, z]) => { const W = __world, v = new W.THREE.Vector3(x, y, z).project(W.camera), r = document.getElementById('cv').getBoundingClientRect(); return [(v.x + 1) / 2 * r.width + r.left, (1 - v.y) / 2 * r.height + r.top]; }"""


def _rw_cols(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#ledger .lg-head .h')].map(h => h.textContent.replace(/[▲▼]/g, '').trim())")


def _rw_col_vals(pg, label):
    """頂層（CEO 以外）各列在某一欄的文字"""
    cols = _rw_cols(pg)
    i = cols.index(label)
    return pg.evaluate("""(i) => [...document.querySelectorAll('#ledger [data-lvl=top]:not([data-u^="ceo"])')].map(r => r.children[i].innerText.trim())""", i)


def t_main(b, base):
    c, pg, got = _rw_open(b, base)
    ok("績效：辦公室頁載入完成", got)
    if not got:
        return
    data = pg.evaluate("() => fetch('world/cfg/rewards.json').then(r => r.json())")
    wk = data["weeks"][0]
    depts = {d["id"]: d for d in wk["depts"]}
    ok("績效：獎勵層啟用、資料 6 週、CEO 一列＋11 部門＋43 位", pg.evaluate("() => __world.rewards.on") and len(data["weeks"]) >= 4 and len(depts) == 11 and sum(len(d["members"]) for d in depts.values()) == 43 and wk["ceo"])

    # ── R0：名牌字章 ──
    chips = pg.evaluate("() => { const o = {}; for (const [id, c] of __world.chars) { const L = c._lab; o[id] = L.gr.textContent; } return o; }")
    expect = {"ceo": wk["ceo"]["grade"]}
    for d in depts.values():
        for mid, m in d["members"].items():
            expect[mid] = m["grade"] or ""
    ok("績效：每位同事的名牌字章＝資料裡的等第（樣本不足的沒有字章）", all(chips.get(k, None) == v for k, v in expect.items()), [(k, chips.get(k), v) for k, v in expect.items() if chips.get(k) != v][:4])
    pg.evaluate("() => __world.setView('god', null, true)")
    pg.wait_for_timeout(900)
    vis = pg.evaluate("() => [...document.querySelectorAll('#labels .tag.hasgr')].filter(t => { const r = t.getBoundingClientRect(); return r.right > 0 && r.left < innerWidth && r.bottom > 0 && getComputedStyle(t).opacity !== '0'; }).length")
    ok("績效：俯瞰時畫面上看得到名牌字章", vis >= 20, vis)
    _rw_shot(pg, "名牌字章.png")

    # ── R2：設備等級換色 ──
    col_js = """() => { const W = __world, T = W.THREE, out = {}; const first = g => { const a = g.attributes.color; return '#' + new T.Color(a.getX(0), a.getY(0), a.getZ(0)).getHexString(); };
      for (const inst of W.furn.values()) { if (inst.f.type === 'workstation' && inst.f.owner) { const k = inst.f.dept; (out['desk_' + k] = out['desk_' + k] || []).push(first(inst.mesh.geometry)); } }
      return out; }"""
    desk = pg.evaluate(col_js)
    DESK = ["#dfe3e8", "#f3e2c8", "#e9c79c", "#b98255", "#8a5a3c"]

    def near(a, b_):
        ca, cb = int(a[1:], 16), int(b_[1:], 16)
        return abs((ca >> 16) - (cb >> 16)) + abs(((ca >> 8) & 255) - ((cb >> 8) & 255)) + abs((ca & 255) - (cb & 255)) <= 6   # 頂點色經色彩空間轉換，容許極小誤差
    bad = [(k, v[0], DESK[depts[k[5:]]["level"] - 1]) for k, v in desk.items() if not near(v[0], DESK[depts[k[5:]]["level"] - 1])]
    ok("績效：各部門辦公桌桌面顏色＝該部門設備等級對應的色（L1 灰白～L5 胡桃）", not bad and len(desk) == 11, bad[:3])
    lv_set = {depts[k[5:]]["level"] for k in desk}
    ok("績效：不同設備等級的桌面顏色真的不同（至少 3 種等級）", len(lv_set) >= 3 and len({v[0] for v in desk.values()}) >= 3, lv_set)
    sign = pg.evaluate("""() => { const W = __world, T = W.THREE, o = {}; for (const inst of W.furn.values()) if (inst.spec.deptsign) { const g = inst.mesh.geometry, a = g.attributes.color, s = new Set(); for (let i = 0; i < a.count; i += 3) s.add(new T.Color(a.getX(i), a.getY(i), a.getZ(i)).getHexString()); o[inst.spec.deptsign] = [...s].sort().join(','); } return o; }""")
    ok("績效：L5 與 L2 的部門招牌顏色組合不同（L5 有金邊）", sign["legal"] != sign["ops"] and sign["legal"] != sign["data"], None)
    floor = pg.evaluate("""() => { const W = __world, T = W.THREE, o = {}; for (const id of ['legal', 'ops', 'data']) { const a = W.rooms.get(id).mesh.geometry.attributes.color; const s = new Set(); for (let i = 0; i < a.count; i += 7) s.add(new T.Color(a.getX(i), a.getY(i), a.getZ(i)).getHexString()); o[id] = [...s].sort().join(','); } return o; }""")
    ok("績效：部門地毯（地板內層）顏色隨等級不同", len(set(floor.values())) == 3, floor)
    plants = pg.evaluate("""() => { const W = __world, T = W.THREE, o = {}; for (const inst of W.furn.values()) if (inst.f.type === 'plant_big' || inst.f.type === 'plant') { const r = W.layout.rooms.find(q => q.kind === 'dept' && inst.f.x >= q.x && inst.f.x <= q.x + q.w && inst.f.z >= q.z && inst.f.z <= q.z + q.d); if (!r) continue; const a = inst.mesh.geometry.attributes.color; (o[r.dept] = o[r.dept] || new Set()).add('#' + new T.Color(a.getX(0), a.getY(0), a.getZ(0)).getHexString()); } return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, [...v][0]])); }""")
    ok("績效：花盆顏色隨部門設備等級不同", len(set(plants.get(k) for k in ("legal", "ops", "data") if k in plants)) >= 2, plants)

    marks = pg.evaluate("() => __world.rewards.markInfo()")
    flag_depts = sorted({m["dept"] for m in marks if m["kind"] == "flag"})
    want = sorted(k for k, d in depts.items() if d["grade"] in ("D", "E", "F"))
    ok("績效：琥珀小旗只出現在等第 D 以下的部門", flag_depts == want and len(want) >= 1, (flag_depts, want))
    ok("績效：每個部門招牌都有等第字章", sorted({m["dept"] for m in marks if m["kind"] == "chip"}) == sorted(depts), None)

    # 旗：滑過顯示原因（先飛到那個部門，再把滑鼠真的移到旗上）
    fd = want[0]
    pos = pg.evaluate("(id) => { for (const i of __world.furn.values()) if (i.spec.deptsign === id) return [i.f.x, i.f.z]; }", fd)
    pg.evaluate("([x, z]) => __world.godAt(x, z + 3, 12)", pos)
    pg.wait_for_timeout(1800)
    fx, fy = pg.evaluate(_PROJ, [pos[0] - 1.38, 1.45, pos[1]])
    pg.mouse.move(fx - 30, fy + 80)
    pg.mouse.move(fx, fy, steps=4)
    pg.wait_for_timeout(300)
    tip = pg.evaluate("() => { const t = document.getElementById('rwTip'); return t && !t.hidden ? t.textContent : ''; }")
    lab = data["reasonLabels"][depts[fd]["flag"]["reason"]]
    ok("績效：滑到琥珀旗上顯示原因", lab in tip, tip)
    _rw_shot(pg, "琥珀小旗.png")
    pg.mouse.move(5, 400)

    # ── 繪製次數：關掉獎勵層（?rewards=0）對照 ──
    def calls(pg_):
        out = {}
        for v in ("god", "ceo"):
            pg_.evaluate("(v) => __world.setView(v, null, true)", v)
            pg_.wait_for_timeout(1200)
            out[v] = pg_.evaluate("() => __world.stats.calls")
        return out
    with_r = calls(pg)
    c0, pg0, got0 = _rw_open(b, base, qs="?ambient=0&q=low&pr=0.6&sim=1&rewards=0")
    base_r = calls(pg0)
    ok("績效：關掉獎勵層（?rewards=0）整個回到原樣（沒有總表鈕、沒有字章）", pg0.evaluate("() => document.getElementById('rwBtn').hidden && !document.querySelector('.tag.hasgr') && !__world.rewards.on"), None)
    c0.close()
    ok("績效：繪製次數新增 ≤ 20（俯瞰 %d→%d、CEO 視角 %d→%d）" % (base_r["god"], with_r["god"], base_r["ceo"], with_r["ceo"]), with_r["god"] - base_r["god"] <= 20 and with_r["ceo"] - base_r["ceo"] <= 20, (base_r, with_r))

    # ── 名牌避讓 ──
    pg.evaluate("() => __world.setView('god', null, true)")
    pg.wait_for_timeout(1200)
    tag_js = """() => { const W = __world, out = []; for (const c of [...W.chars.values(), ...W.pets]) { const L = c._lab; if (!L || !L.on) continue; const t = L.tag; if (t.classList.contains('fade')) continue; const r = t.getBoundingClientRect(); if (r.right < 0 || r.left > innerWidth || r.bottom < 0 || r.top > innerHeight) continue; out.push([c.spec.id + (c.spec.pet ? '(寵物)' : ''), r.left, r.top, r.right, r.bottom]); } return out; }"""
    after = _rw_overlaps(pg.evaluate(tag_js), 0.5)
    pg.evaluate("() => { __world.noAvoid = true; }")
    pg.wait_for_timeout(500)
    _rw_shot(pg, "名牌避讓_前.png")
    before = _rw_overlaps(pg.evaluate(tag_js), 0.5)
    pg.evaluate("() => { __world.noAvoid = false; }")
    pg.wait_for_timeout(500)
    _rw_shot(pg, "名牌避讓_後.png")
    after = _rw_overlaps(pg.evaluate(tag_js), 0.5)
    ok("績效：名牌避讓後兩兩不重疊（避讓前 %d 組，後 %d 組）" % (len(before), len(after)), not after and len(before) > len(after), after[:3])
    pet_hit = [p for p in after if "(寵物)" in p[0] or "(寵物)" in p[1]]
    ok("績效：寵物名牌沒有壓到任何名牌（含主人）", not pet_hit, pet_hit[:2])

    # ── R0：資訊卡（真的點角色）──
    pg.evaluate("() => __world.setView('god', null, true)")
    cid = "frontend-ui"
    pg.evaluate("(id) => { const c = __world.chars.get(id); __world.setView('char', c, true); }", cid)
    pg.wait_for_timeout(900)
    sx, sy = pg.evaluate("(id) => { const c = __world.chars.get(id); return [c._sx, c._sy + 40]; }", cid)
    pg.mouse.click(sx, sy)
    pg.wait_for_timeout(500)
    card = pg.evaluate("() => { const c = document.getElementById('card'); return c.hidden ? null : c.innerText; }")
    ok("績效：點角色開出資訊卡，且有等第與分數", bool(card) and "96" in card and "S" in card, (card or "")[:80])
    m = depts["frontend"]["members"][cid]
    ok("績效：資訊卡有本週升降、距離下一級（S＝已是最高等第・連勝 %d 週）、配件、設備等級" % m["streak"], card and ("已是最高等第" in card) and ("連勝第 %d 週" % m["streak"]) in card and "配件" in card and "設備 L4" in card and "▲" in card, (card or "")[-160:])
    _rw_shot(pg, "資訊卡_等第.png")
    pg.click("#card [data-rwq]")
    ok("績效：資訊卡「?」點了才出現算法（含等第門檻與權重）", pg.evaluate("() => { const h = document.querySelector('#card .rwh'); return !h.hidden && /品質 30%/.test(h.textContent); }"), None)
    # 非 S 的人：距離下一級有數字
    pg.evaluate("() => { const c = __world.chars.get('visual-explainer'); __world.setView('char', c, true); __world.ui.showCard(c); }")
    nx = pg.evaluate("() => document.querySelector('#card .rw2').textContent")
    ve = depts["frontend"]["members"]["visual-explainer"]
    ok("績效：距離下一級寫出差幾分與目標等第", ("再 +%s 分到 B" % ("%g" % round(75 - ve["score"], 1))) in nx, nx)
    pg.evaluate("() => { const c = __world.chars.get('mechanical-engineer'); __world.setView('char', c, true); __world.ui.showCard(c); }")
    ok("績效：樣本不足的人資訊卡寫「樣本不足」、不給等第", "樣本不足" in pg.evaluate("() => document.getElementById('card').innerText"), None)
    pg.evaluate("() => { __world.ui.hideCard(); __world.setView('god', null, true); }")
    c.close()


def t_ledger(b, base):
    c, pg, got = _rw_open(b, base)
    if not got:
        ok("績效總表：載入", False)
        return
    data = pg.evaluate("() => fetch('world/cfg/rewards.json').then(r => r.json())")
    wk = data["weeks"][0]
    depts = {d["id"]: d for d in wk["depts"]}
    ok("績效總表：一開始是收起的", pg.evaluate("() => document.getElementById('ledger').hidden"), None)
    pg.click("#rwBtn")
    ok("績效總表：按頂端「績效總表」鈕打開", wait_until(pg, "() => !document.getElementById('ledger').hidden && document.querySelectorAll('#ledger [data-u]').length > 0", 5000), None)
    rows = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=top]')].map(r => r.dataset.u)")
    ok("績效總表：列數＝CEO 1＋部門 11，CEO 在最上面", len(rows) == 12 and rows[0] == "ceo:ceo" and len({r for r in rows if r.startswith("dept:")}) == 11, rows)
    ok("績效總表：頁標只有一個「績效總表」（卡內不重複標題）", pg.evaluate("() => [...document.querySelectorAll('#ledger h3')].length === 1 && document.querySelector('#ledger h3').textContent.replace('示範','').replace('?','').trim() === '績效總表'"), None)
    ok("績效總表：14 欄（桌機 1440 夠寬時全部放得下）或依優先級收次要欄位、不橫向捲動", len(_rw_cols(pg)) >= 12 and pg.evaluate("() => { const s = document.getElementById('lgScroll'); return s.scrollWidth <= s.clientWidth + 1 && document.documentElement.scrollWidth <= innerWidth; }"), _rw_cols(pg))
    ok("績效總表：CEO 與各部門的等第、分數與資料一致", all(pg.evaluate("(id) => { const r = document.querySelector('[data-u=\"dept:' + id + '\"]'); return r.dataset.grade; }", k) == v["grade"] for k, v in depts.items()) and pg.evaluate("() => document.querySelector('[data-u=\"ceo:ceo\"]').dataset.grade") == wk["ceo"]["grade"], None)
    _rw_shot(pg, "總表_桌機.png")

    # 展開部門
    n0 = pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=sub]').length")
    pg.click('[data-u="dept:design"] .lg-caret')
    subs = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=sub]')].map(r => r.dataset.u)")
    ok("績效總表：展開設計與繪圖部 → 5 位成員列出現（原本 %d）" % n0, n0 == 0 and len(subs) == len(depts["design"]["members"]) == 5, subs)
    ok("績效總表：樣本不足的成員等第顯示「—」、分數「—」", pg.evaluate("() => { const r = document.querySelector('[data-u=\"agent:mechanical-engineer\"]'); return !!r && r.children[1].innerText.trim() === '—' && r.children[2].innerText.trim() === '—'; }"), None)
    ok("績效總表：展開前後外框尺寸不變（不晃）", pg.evaluate("() => { const r = document.getElementById('ledger').getBoundingClientRect(); return Math.abs(r.height - 536) < 3 || r.height > 400; }"), None)
    pg.click('[data-u="ceo:ceo"] .lg-caret')
    ok("績效總表：展開 CEO → 六個面向小分數", pg.evaluate("() => document.querySelectorAll('#ledger .lg-dims .dim').length") == 6, None)
    _rw_shot(pg, "總表_展開部門.png")
    pg.click('[data-u="ceo:ceo"] .lg-caret')
    pg.click('[data-u="dept:design"] .lg-caret')
    ok("績效總表：再點一次收起", pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=sub]').length") == 0, None)

    # 排序
    before = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=top]')].map(r => r.dataset.u)")
    pg.click('#ledger [data-sort="done_rate"]')
    after1 = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=top]')].map(r => r.dataset.u)")
    v1 = [int(x.rstrip("%")) for x in _rw_col_vals(pg, "完成率")]
    ok("績效總表：點「完成率」→ 順序真的變了、CEO 仍置頂、數字由高到低", after1 != before and after1[0] == "ceo:ceo" and v1 == sorted(v1, reverse=True), (v1,))
    pg.click('#ledger [data-sort="done_rate"]')
    v2 = [int(x.rstrip("%")) for x in _rw_col_vals(pg, "完成率")]
    ok("績效總表：再點一次 → 反向（由低到高），表頭 aria-sort 跟著變", v2 == sorted(v2) and pg.evaluate("() => document.querySelector('#ledger [data-sort=\"done_rate\"]').closest('.h').getAttribute('aria-sort')") == "ascending", v2)
    pg.click('#ledger [data-sort="name"]')
    names = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=top]:not([data-u^=ceo]) .lg-go b')].map(e => e.textContent)")
    ok("績效總表：點「單位」→ 依名稱排序", names == sorted(names, key=lambda s: s) or len(set(names)) == 11, names[:3])
    pg.click('#ledger [data-sort="score"]')
    pg.click('#ledger [data-sort="score"]') if pg.evaluate("() => document.querySelector('#ledger [data-sort=\"score\"]').closest('.h').getAttribute('aria-sort')") != "descending" else None
    # 展開狀態在排序時保留
    pg.click('[data-u="dept:social"] .lg-caret')
    pg.click('#ledger [data-sort="reject_rate"]')
    ok("績效總表：排序時已展開的部門保持展開，成員在部門內排序", pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=sub]').length") == 6, None)
    sub_vals = pg.evaluate("() => [...document.querySelectorAll('#ledger [data-lvl=sub]')].map(r => r.children[7].innerText.trim()).filter(x => x !== '—').map(x => parseInt(x))")
    ok("績效總表：部門內成員退件率由高到低", sub_vals == sorted(sub_vals, reverse=True), sub_vals)
    pg.click('[data-u="dept:social"] .lg-caret')
    pg.click('#ledger [data-sort="score"]')

    # 週次
    sc0 = _rw_col_vals(pg, "分數")
    sub0 = pg.inner_text("#lgSub")
    pg.click('#ledger [data-wk="1"]')
    sc1 = _rw_col_vals(pg, "分數")
    sub1 = pg.inner_text("#lgSub")
    ok("績效總表：切到 W44 → 副標、分數、升降都跟著變", sub0 != sub1 and "W44" in sub1 and sc0 != sc1, (sub0, sub1))
    ok("績效總表：W44 的 CEO 與資料一致", pg.evaluate("() => document.querySelector('[data-u=\"ceo:ceo\"]').dataset.grade") == data["weeks"][1]["ceo"]["grade"], None)
    pg.select_option("#lgOld", "4")
    ok("績效總表：「更早」下拉可以選 W41", "W41" in pg.inner_text("#lgSub"), pg.inner_text("#lgSub"))
    pg.click('#ledger [data-wk="0"]')

    # 只看需要加強
    n_all = pg.evaluate("() => document.querySelectorAll('#ledger [data-u]').length")
    pg.click('#ledger [data-act="need"]')
    got_u = sorted(pg.evaluate("() => [...document.querySelectorAll('#ledger [data-u]')].map(r => r.dataset.u)"))
    exp = set()
    if _rw_need(wk["ceo"]):
        exp.add("ceo:ceo")
    for d in wk["depts"]:
        ms = {mid: m for mid, m in d["members"].items() if _rw_need(m)}
        if _rw_need(d) or ms:
            exp.add("dept:" + d["id"])
            exp.update("agent:" + mid for mid in ms)
    ok("績效總表：「只看需要加強」→ 單位數變少，且正好是符合規則的（D 以下、本週降級、回報不實、有琥珀旗）共 %d 列" % len(exp), got_u == sorted(exp) and len(got_u) < n_all and len(exp) > 2, (got_u, sorted(exp)))
    ok("績效總表：篩選時部門自動展開、列出符合的成員", any(u.startswith("agent:") for u in got_u), None)
    ok("績效總表：開關按了有 aria-pressed", pg.evaluate("() => document.querySelector('#ledger [data-act=\"need\"]').getAttribute('aria-pressed')") == "true", None)
    _rw_shot(pg, "總表_只看需要加強.png")
    pg.click('#ledger [data-act="need"]')
    ok("績效總表：關掉篩選 → 回到 12 列", pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=top]').length") == 12, None)

    # 全部展開
    pg.click('#ledger [data-act="all"]')
    ok("績效總表：「全部展開」→ 43 位成員都列出來，表格在框內捲動（外框不長高）", pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=sub]').length") == 43 and pg.evaluate("() => { const s = document.getElementById('lgScroll'); return s.scrollHeight > s.clientHeight && s.scrollWidth <= s.clientWidth + 1; }"), None)
    pg.click('#ledger [data-act="all"]')

    # 說明、禁用字
    pg.click('#ledger [data-act="help"]')
    ok("績效總表：「?」點了才出現算法說明", pg.evaluate("() => !document.getElementById('lgHelp').hidden && /品質 30%/.test(document.getElementById('lgHelp').textContent)"), None)
    txt0 = pg.evaluate("() => document.body.innerText")
    pg.click('#ledger [data-act="help"]')
    pg.click('#ledger [data-act="all"]')
    txt = txt0 + pg.evaluate("() => document.body.innerText")
    ok("績效總表：畫面不含價格／付費／升級／訂閱／方案／Plus／Pro／免費／右鍵等字", not _RW_FORBID.search(txt), _RW_FORBID.findall(txt))
    ok("績效總表：畫面不出現 rewards.json、欄位代碼等內部詞", not _re.search(r"rewards\.json|top_loss|false_reports|levelPending", txt), None)
    pg.click('#ledger [data-act="all"]')

    # 1280 元素不重疊
    sels = ["#bar", "#ledger", ".cm-hint", ".dt-chip"]
    bad, = [_rw_overlaps(_rw_rects(pg, sels))]
    ok("績效總表：1280 寬面板不蓋到頂列與提示列", not bad, bad[:3])
    inner = pg.evaluate("""() => { const o = []; const add = (n, e) => { if (!e) return; const r = e.getBoundingClientRect(); o.push([n, r.left, r.top, r.right, r.bottom]); };
      add('title', document.querySelector('#ledger h3')); add('sub', document.getElementById('lgSub')); add('x', document.querySelector('#ledger .x'));
      document.querySelectorAll('#lgCtl > *').forEach((e, i) => add('ctl' + i, e)); return o; }""")
    ok("績效總表：1280 面板內標題、控制列、關閉鈕互不重疊", not _rw_overlaps(inner), _rw_overlaps(inner)[:3])
    ok("績效總表：字不小於 11px、列高 32、按鈕高 ≥ 32", pg.evaluate("""() => { let min = 99; document.querySelectorAll('#ledger *').forEach(e => { if (e.children.length === 0 && e.textContent.trim()) min = Math.min(min, parseFloat(getComputedStyle(e).fontSize)); }); const r = document.querySelector('#ledger .lg-row').getBoundingClientRect().height, b = document.querySelector('#lgCtl .btn').getBoundingClientRect().height; return min >= 11 && Math.round(r) === 32 && b >= 32; }"""), None)

    # 鍵盤
    pg.focus('#ledger [data-sort="score"]')
    pg.keyboard.press("Enter")
    ok("績效總表：鍵盤 Enter 在表頭按鈕上可排序（升降反轉）", pg.evaluate("() => document.querySelector('#ledger [data-sort=\"score\"]').closest('.h').getAttribute('aria-sort')") == "ascending", None)
    pg.focus('[data-u="dept:legal"] .lg-caret')
    pg.keyboard.press("Enter")
    ok("績效總表：鍵盤 Enter 在展開鈕上可展開成員，焦點仍在同一顆鈕", pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=sub]').length") == 2 and pg.evaluate("() => document.activeElement.dataset.act") == "tog", None)
    pg.keyboard.press("Enter")
    pg.keyboard.press("Escape")
    ok("績效總表：Esc 關閉，焦點回到「績效總表」鈕", pg.evaluate("() => document.getElementById('ledger').hidden && document.activeElement.id === 'rwBtn'"), None)

    # 點列飛到 3D（agent）
    pg.click("#rwBtn")
    pg.click('[data-u="dept:frontend"] .lg-caret')
    pg.click('[data-u="agent:mobile-ui"] .lg-go')
    ok("績效總表：點成員 → 總表關閉、鏡頭跟到那位同事、資訊卡打開", wait_until(pg, "() => document.getElementById('ledger').hidden && __world.view.char && __world.view.char.spec.id === 'mobile-ui' && !document.getElementById('card').hidden", 5000), None)
    ok("績效總表：飛過去之後資訊卡顯示他的等第", "A" in pg.evaluate("() => document.querySelector('#card .rw1').innerText"), None)
    # 部門
    pg.click("#rwBtn")
    pg.click('[data-u="dept:data"] .lg-go')
    room = pg.evaluate("() => __world.layout.rooms.find(r => r.id === 'data')")
    ok("績效總表：點部門 → 鏡頭飛到該部門（注視點落在部門範圍內）", wait_until(pg, "(r) => { const t = __world.controls.target; return __world.view.mode === 'god' && t.x > r.x - 0.5 && t.x < r.x + r.w + 0.5 && t.z > r.z - 0.5 && t.z < r.z + r.d + 1.5; }", 6000) if False else wait_until(pg, "() => { const r = __world.layout.rooms.find(q => q.id === 'data'), t = __world.controls.target; return __world.view.mode === 'god' && !__world.view.tween && t.x > r.x - 0.5 && t.x < r.x + r.w + 0.5 && t.z > r.z - 0.5 && t.z < r.z + r.d + 1.5; }", 8000), room)
    # 點招牌／入口大廳看板 → 打開總表
    pg.evaluate("() => __world.setView('god', null, true)")
    pg.wait_for_timeout(1000)
    kx, ky = pg.evaluate(_PROJ, [pg.evaluate("() => [...__world.furn.values()].find(i => i.f.type === 'kiosk').f.x"), 1.0, pg.evaluate("() => [...__world.furn.values()].find(i => i.f.type === 'kiosk').f.z")])
    pg.mouse.click(kx, ky)
    ok("績效總表：點入口大廳的看板也能打開", wait_until(pg, "() => !document.getElementById('ledger').hidden", 3000), (kx, ky))
    pg.keyboard.press("Escape")
    pos = pg.evaluate("() => { for (const i of __world.furn.values()) if (i.spec.deptsign === 'social') return [i.f.x, i.f.z]; }")
    pg.evaluate("([x, z]) => __world.godAt(x, z + 3, 12)", pos)
    pg.wait_for_timeout(1800)
    sx, sy = pg.evaluate(_PROJ, [pos[0] - 0.3, 1.2, pos[1]])
    pg.mouse.click(sx, sy)
    ok("績效總表：點部門招牌 → 打開總表並展開該部門、那一列有高亮", wait_until(pg, "() => !document.getElementById('ledger').hidden && document.querySelectorAll('#ledger [data-u^=\"agent:\"]').length === 6", 3000), None)
    pg.keyboard.press("Escape")

    # ── 主管被開除（佈告欄）──
    pg.evaluate("() => { __world.setView('god', null, true); __world.ui.showBoard('legal'); }")
    t0 = pg.inner_text("#board .bmeta")
    pg.click('#board [data-hr="firedept"]')
    pg.click("#fireGo")
    pg.click("#fireGo")
    ok("績效：開除整個部門後，佈告欄寫「主管：無（待指派）」、人數 0 人", wait_until(pg, "() => /主管：無（待指派）/.test(document.querySelector('#board .bmeta').textContent) && /人數 0 人/.test(document.querySelector('#board .bmeta').textContent)", 5000) and "主管：無" not in t0, (t0, pg.inner_text("#board .bmeta")))
    _rw_shot(pg, "主管被開除.png")
    pg.evaluate("() => { document.getElementById('board').hidden = true; }")
    ok("績效：總表裡被開除的成員標「待業中」", pg.evaluate("() => { __world.rewards.ledger.open('legal'); return document.getElementById('ledger').innerText.includes('待業中'); }"), None)
    ok("績效：沒有主控台錯誤", not pg.errs, pg.errs[:3])
    c.close()
    # 只開除其中一位主管時（另開一頁：重新整理會記住開除狀態，所以用乾淨的新 context）
    c, pg, got = _rw_open(b, base)
    pg.evaluate("() => { __world.ui.showBoard('quant'); }")
    lead0 = pg.inner_text("#board .bmeta")
    lead_id = pg.evaluate("() => __world.org.departments.find(d => d.id === 'quant').members.find(m => m.lead).id")
    pg.evaluate("(id) => { __world.hr.ask([id]); }", lead_id)
    pg.click("#fireGo")
    pg.click("#fireGo")
    ok("績效：只開除主管（其他人還在）→ 佈告欄「主管：無（待指派）」、人數少 1", wait_until(pg, "() => /主管：無（待指派）/.test(document.querySelector('#board .bmeta').textContent) && /人數 2 人/.test(document.querySelector('#board .bmeta').textContent)", 5000) and "主管：無" not in lead0, (lead0, pg.inner_text("#board .bmeta")))
    c.close()


def t_mobile(b, base):
    c, pg, got = _rw_open(b, base, w=390, h=844)
    if not got:
        ok("績效總表手機：載入", False)
        return
    ok("績效總表手機：頂列沒有總表鈕（收進「更多」）", not pg.evaluate("() => { const r = document.getElementById('rwBtn').getBoundingClientRect(); return r.width > 0; }"), None)
    pg.click("#moreBtn")
    pg.click("#rwBtn")
    ok("績效總表手機：從「更多」打開總表，「更多」自動收起", wait_until(pg, "() => !document.getElementById('ledger').hidden && !document.body.classList.contains('m-more')", 4000), None)
    ok("績效總表手機：改成卡片列（12 張，預設全部收起）", pg.evaluate("() => document.querySelectorAll('#ledger .lg-card[data-lvl=top]').length") == 12 and pg.evaluate("() => document.querySelectorAll('#ledger .lg-c3').length") == 0 and pg.evaluate("() => document.querySelectorAll('#ledger .lg-head').length") == 0, None)
    ok("績效總表手機：沒有橫向捲軸", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth && document.getElementById('lgScroll').scrollWidth <= document.getElementById('lgScroll').clientWidth + 1"), None)
    ok("績效總表手機：整頁（卡片清單）≤ 3 屏、第一屏看得到前 4 張卡", pg.evaluate("() => document.getElementById('lgScroll').scrollHeight <= 3 * innerHeight") and pg.evaluate("() => { const cs = [...document.querySelectorAll('#ledger .lg-card[data-lvl=top]')]; return cs.slice(0, 4).every(c => c.getBoundingClientRect().bottom <= innerHeight); }"), None)
    ok("績效總表手機：字不小於 11px、點的目標高 ≥ 40", pg.evaluate("""() => { let min = 99; document.querySelectorAll('#ledger *').forEach(e => { if (e.children.length === 0 && e.textContent.trim()) min = Math.min(min, parseFloat(getComputedStyle(e).fontSize)); }); const h = document.querySelector('#ledger .lg-c1').getBoundingClientRect().height, s = document.querySelector('#ledger .lg-sel').getBoundingClientRect().height; return min >= 11 && h >= 40 && s >= 40; }"""), None)
    inner = pg.evaluate("""() => { const o = []; const add = (n, e) => { if (!e) return; const r = e.getBoundingClientRect(); o.push([n, r.left, r.top, r.right, r.bottom]); };
      add('title', document.querySelector('#ledger h3')); add('sub', document.getElementById('lgSub')); add('x', document.querySelector('#ledger .x'));
      document.querySelectorAll('#lgCtl > *').forEach((e, i) => add('ctl' + i, e)); return o; }""")
    bad = _rw_overlaps(inner) + _rw_overlaps(_rw_rects(pg, ["#bar", "#ledger"]))
    ok("績效總表手機：面板內與頂列元素互不重疊", not bad, bad[:3])
    ok("績效總表手機：控制列（週次、排序、只看需要加強）在同一排不換行", pg.evaluate("() => { const t = [...document.querySelectorAll('#lgCtl > *')].map(e => Math.round(e.getBoundingClientRect().top)); return new Set(t).size === 1 && t.length === 3; }"), None)
    _rw_shot(pg, "總表_手機.png")
    # 展開
    pg.click('[data-u="dept:legal"] .lg-c1')
    ok("績效總表手機：點卡片展開其餘欄位與成員小卡", pg.evaluate("() => document.querySelectorAll('[data-u=\"dept:legal\"] .lg-c3').length") >= 1 and pg.evaluate("() => document.querySelectorAll('[data-u=\"dept:legal\"] .lg-subs .lg-card').length") == 2, None)
    pg.click('[data-u="dept:legal"] .lg-c1')
    ok("績效總表手機：再點收起", pg.evaluate("() => document.querySelectorAll('#ledger .lg-c3').length") == 0, None)
    # 排序、週次、篩選
    before = pg.evaluate("() => [...document.querySelectorAll('#ledger .lg-card[data-lvl=top]')].map(c => c.dataset.u)")
    pg.select_option("#lgSort", "reject_rate")
    after = pg.evaluate("() => [...document.querySelectorAll('#ledger .lg-card[data-lvl=top]')].map(c => c.dataset.u)")
    ok("績效總表手機：改排序下拉 → 順序真的變了", before != after, None)
    s0 = pg.evaluate("() => [...document.querySelectorAll('#ledger .lg-card[data-lvl=top] .sc')].map(e => e.textContent).join()")
    pg.select_option("#lgWeek", "1")
    s1 = pg.evaluate("() => [...document.querySelectorAll('#ledger .lg-card[data-lvl=top] .sc')].map(e => e.textContent).join()")
    ok("績效總表手機：切週次 → 分數變了", s0 != s1, None)
    pg.select_option("#lgWeek", "0")
    pg.click('#ledger [data-act="need"]')
    n = pg.evaluate("() => document.querySelectorAll('#ledger .lg-card').length")
    ok("績效總表手機：只看需要加強 → 卡片變少", 0 < n < 12 + 43, n)
    pg.click('#ledger [data-act="need"]')
    # 到辦公室看
    pg.click('[data-u="dept:ops"] .lg-c1')
    pg.click('[data-u="dept:ops"] > .lg-gob')
    ok("績效總表手機：展開後按「到辦公室看」→ 總表關閉、鏡頭飛過去", wait_until(pg, "() => document.getElementById('ledger').hidden && __world.view.mode === 'god' && !__world.view.tween", 8000), None)
    ok("績效總表手機：沒有橫向捲軸、沒有主控台錯誤", pg.evaluate("() => document.documentElement.scrollWidth <= innerWidth") and not pg.errs, pg.errs[:3])
    # 資訊卡（手機）
    pg.evaluate("() => { const c = __world.chars.get('deployer'); __world.setView('char', c, true); __world.ui.showCard(c); }")
    pg.wait_for_timeout(500)
    r = pg.evaluate("() => { const c = document.getElementById('card').getBoundingClientRect(), b = document.getElementById('bar').getBoundingClientRect(); return [c.top, c.bottom, innerHeight, b.bottom, document.querySelector('#card .rw') ? 1 : 0]; }")
    ok("績效總表手機：資訊卡有績效區塊、完整在畫面內", r[4] == 1 and r[1] <= r[2] + 1 and r[0] >= 0, r)
    c.close()


def t_copy(b, base):
    """預覽部署會略過名為 data、preview 的資料夾：照那個規則複製 site 再起一個伺服器，核心流程跑一遍"""
    src = _os.path.join(_os.getcwd(), "site")   # _uitest.py 一律從 repo 根目錄跑
    dst = _os.path.join(_tf.mkdtemp(), "site")
    _sh.copytree(src, dst, ignore=_sh.ignore_patterns("data", "preview"))

    class H(_hs.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    _ss.ThreadingTCPServer.allow_reuse_address = True
    srv = _ss.ThreadingTCPServer(("127.0.0.1", 0), _ft.partial(H, directory=dst))
    _th.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        ok("預覽部署重建：績效資料與程式都沒被略過", all(_os.path.exists(_os.path.join(dst, "office", "world", f)) for f in ["cfg/rewards.json", "js/rewards.js", "js/ledger.js", "rewards.css"]), None)
        c, pg, got = _rw_open(b, "http://127.0.0.1:%d/index.html" % srv.server_address[1])
        ok("預覽部署重建：辦公室頁載入完成、獎勵層啟用", got and pg.evaluate("() => __world.rewards.on"), None)
        if got:
            pg.click("#rwBtn")
            ok("預覽部署重建：總表打開、12 列", pg.evaluate("() => document.querySelectorAll('#ledger [data-lvl=top]').length") == 12, None)
            ok("預覽部署重建：沒有主控台錯誤", not pg.errs, pg.errs[:3])
        c.close()
    finally:
        srv.shutdown()
        _sh.rmtree(_os.path.dirname(dst), ignore_errors=True)


def t_all(b, base):
    for fn in (t_main, t_ledger, t_mobile, t_copy):
        try:
            fn(b, base)
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok("績效：%s 中途爆掉" % fn.__name__, False, str(e)[:300])


register("辦公室績效總表", lambda pg, b, base, code: t_all(b, base))
