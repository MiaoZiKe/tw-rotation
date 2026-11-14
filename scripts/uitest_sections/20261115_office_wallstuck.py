# 辦公室：角色被丟到牆邊／角落／CEO 室椅子旁之後，一定要走得回座位（2026-11-15 驗收 B 問題 3）
#   事故：新模型「跳跳」(bibi-animator) 丟到 CEO 椅子旁，回座位的路徑點 (0.63, 13.63) 貼著西牆，
#   新模型的物理邊界多扣了一次身體半徑，只能走到 x=1.06 → 原地跑步 20 秒以上、沒有重新找路也沒有保底。
#   這一段用真滑鼠（長按 0.9 秒 → 拖 → 放開）把新舊模型角色丟到各處，按畫面上的「4×」，量：
#     · 回到座位坐好的模擬時間（≤ 60 秒）
#     · 走路中「原地不前進」（0.2 公尺內）連續最久幾秒（≤ 4.5 秒：3 秒保底門檻＋重新找路的餘裕；刻意暫停的暈眩演出不算）
#     · 新模型用了哪一種保底（重新找路／略過路徑點／平順滑回），以及有沒有瞬移（相鄰取樣的平均速度 > 6 公尺／秒＝瞬移；跑步約 3）
import math as _m
import os as _os

_NEW = ["bibi-animator", "motion-designer", "hr-officer", "efficiency-planner", "ceo"]
_OLD = ["storyboard-artist", "data-steward", "finance-quant", "video-editor", "art-director"]


def _ws_open(b, base, w=1280, h=800):
    c = b.new_context(viewport={"width": w, "height": h})
    c.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)[:200]))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(base.split("/index.html")[0].rstrip("/") + "/office/world.html?ambient=0&q=low&pr=0.6", wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    pg.wait_for_timeout(800)
    return c, pg, got


def _ws_spots(pg):
    """丟放地點（世界座標）：CEO 室椅子左側、西牆（事故那一點）、北牆、東牆、部門內牆旁、西北角、東北角"""
    return pg.evaluate("""() => { const W = __world, L = W.layout, Wd = L.size.w, D = L.size.d, out = [];
      const ch = W.phys && W.phys.props.find(q => q.id === 'ceo_desk_2/chair0');
      if (ch) { const h = W.phys.homePos(ch); out.push(['CEO 室椅子左側', h.x - 0.9, h.z + 0.3]); }
      out.push(['西牆邊（事故點）', 0.7, 13.63], ['北牆邊', Wd * 0.5, 0.7], ['東牆邊', Wd - 0.7, D * 0.45], ['西北角', 0.7, 0.7], ['東北角', Wd - 0.7, 0.7]);
      const inner = L.walls.filter(w => { const xs = [w.x1, w.x2], zs = [w.z1, w.z2]; return !(xs.every(x => x < 0.3) || xs.every(x => x > Wd - 0.3) || zs.every(z => z < 0.3) || zs.every(z => z > D - 0.3)) && Math.hypot(w.x2 - w.x1, w.z2 - w.z1) > 2; });
      if (inner.length) { const w = inner[Math.floor(inner.length / 2)], mx = (w.x1 + w.x2) / 2, mz = (w.z1 + w.z2) / 2, vert = Math.abs(w.x2 - w.x1) < Math.abs(w.z2 - w.z1);
        out.push(['部門內牆旁', vert ? mx + 0.45 : mx, vert ? mz : mz + 0.45]); }
      return out; }""")


def _ws_drop(pg, who, wx, wz, limit=60):
    pg.evaluate("() => __world.setView('god', null, true)"); pg.wait_for_timeout(700)
    # 先確定他在座位上坐好（上一回合可能還在走）
    wait_until(pg, f"() => {{ const c = __world.chars.get('{who}'); return c.state === 'sit' && c.atDesk; }}", 60000, 300)
    q = pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id), cv = document.getElementById('cv'); if (!c || !(c._sx > 0)) return null;
      const k = cv.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd); return [c._sx, c._sy + k * 0.45 * (c.scale || 1)]; }""", who)
    if not q:
        return {"err": "角色不在畫面上"}
    pg.mouse.move(q[0], q[1]); pg.mouse.down(); pg.wait_for_timeout(900); pg.mouse.move(q[0] + 8, q[1] - 8, steps=2); pg.wait_for_timeout(400)
    held = pg.evaluate(f"() => __world.chars.get('{who}').state")
    tg = pg.evaluate("([x, z]) => { const W = __world, s = new W.THREE.Vector3(x, 1.05, z).project(W.camera); return [(s.x + 1) / 2 * innerWidth, (1 - s.y) / 2 * innerHeight]; }", [wx, wz])
    pg.mouse.move(tg[0], tg[1], steps=6); pg.wait_for_timeout(700); pg.mouse.up()
    r0 = pg.evaluate("() => (window.__ncStats && __ncStats.rescue) || 0")
    t0 = pg.evaluate("() => __world.time")
    samp, seated = [], False
    while True:
        s = pg.evaluate(f"""() => {{ const W = __world, c = W.chars.get('{who}'), p = c.object3D.position;
          return [W.time, p.x, p.z, c.state, !!c.atDesk, c._lastRescue || '', !!c._pause]; }}""")
        samp.append(s)
        if s[3] == "sit" and s[4]:
            seated = True; break
        if s[0] - t0 > limit:
            break
        pg.wait_for_timeout(250)
    # 走路中原地不前進：從每個 walk 取樣往後看，0.2 公尺圓內連續停留最久多久
    #   排除刻意的暫停（c._pause：被丟下後的暈眩、有人看他時停下腳步），那是演出不是卡住
    worst = 0.0
    for i, a in enumerate(samp):
        if a[3] != "walk" or a[6]:
            continue
        for bq in samp[i + 1:]:
            if bq[3] != "walk" or bq[6] or _m.hypot(bq[1] - a[1], bq[2] - a[2]) > 0.2:
                break
            worst = max(worst, bq[0] - a[0])
    jump = max([_m.hypot(samp[i][1] - samp[i - 1][1], samp[i][2] - samp[i - 1][2]) / max(0.05, samp[i][0] - samp[i - 1][0]) for i in range(1, len(samp))] or [0])   # 最大平均速度（公尺／模擬秒）
    land = samp[0][1:3] if samp else None
    r1 = pg.evaluate("() => (window.__ncStats && __ncStats.rescue) || 0")
    return {"held": held, "seated": seated, "t": round(samp[-1][0] - t0, 1) if samp else None, "worst": round(worst, 2), "jump": round(jump, 2),
            "rescue": r1 - r0, "how": samp[-1][5] if samp else "", "land": [round(v, 2) for v in land] if land else None}


def t_wallstuck(b, base):
    c, pg, got = _ws_open(b, base)
    try:
        ok("牆邊卡住：頁面載入", got)
        if not got:
            return
        pg.click("#speedSeg [data-s='4']"); pg.wait_for_timeout(300)
        ok("牆邊卡住：按畫面上的「4×」", pg.evaluate("() => __world.speed") == 4)
        spots = _ws_spots(pg)
        only = _os.environ.get("WS_ONLY")            # 除錯用：只跑名稱含這些字的地點（逗號分隔）；驗收不設，全跑
        kinds = _os.environ.get("WS_KINDS", "新模型,舊模型").split(",")
        ok("牆邊卡住：丟放地點有 CEO 室、牆邊、角落、部門內牆（%d 處）" % len(spots), len(spots) >= 7, spots)
        for kind, ids in (("新模型", _NEW), ("舊模型", _OLD)):
            if kind not in kinds:
                continue
            ids = [i for i in ids if pg.evaluate(f"() => {{ const c = __world.chars.get('{i}'); return !!c && !c.away && !c.jobless && (!!c.newModel) === {'true' if kind == '新模型' else 'false'}; }}")]
            if not ids:
                ok(f"牆邊卡住：找得到{kind}角色", False); continue
            n = 0
            for name, x, z in spots:
                if only and not any(o in name for o in only.split(",")):
                    continue
                for k in range(3):
                    who = ids[n % len(ids)]; n += 1
                    r = _ws_drop(pg, who, x, z)
                    tag = f"{kind} {who} 丟到{name}（{x:.2f},{z:.2f}）第 {k + 1} 次"
                    print("    ", tag, r, flush=True)
                    if r.get("err"):
                        ok(tag + "：" + r["err"], False, r); continue
                    ok(f"{tag}：被拎起來（held）→ 放開後 {r['t']} 秒內回座位坐好、原地不前進最久 {r['worst']} 秒（≤ 4.5）、沒有瞬移（最大速度 {r['jump']} 公尺／秒 ≤ 6）、保底 {r['rescue']} 次 {r['how']}",
                       r["held"] == "held" and r["seated"] and r["worst"] <= 4.5 and r["jump"] <= 6, r)
        ok("牆邊卡住：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_rescue(b, base):
    """保底本身：在路上放一個導航網格不知道的隱形障礙（只在新模型的物理世界裡），逼他卡住，看三段保底依序接手、最後平順到達"""
    c, pg, got = _ws_open(b, base)
    try:
        ok("保底：頁面載入", got)
        if not got:
            return
        pg.evaluate("() => { __world.speed = 4; }")
        for who in ("bibi-animator", "hr-officer", "ceo"):
            st = pg.evaluate("""(id) => { const W = __world, c = W.chars.get(id); if (!c || !c.newModel) return null;
              // 找一段 3 公尺直線空地
              for (let z = 3; z < W.layout.size.d - 3; z += 0.5) for (let x = 3; x < W.layout.size.w - 6; x += 0.5) { let ok = true; for (let s = 0; s <= 3.4 && ok; s += 0.2) for (const o of [-0.6, 0, 0.6]) if (!W.nav.isFree(x + s, z + o)) { ok = false; break; }
                if (ok) { c.standAt(x, z, Math.PI / 2); const s = c.scale || 1; c.inner.ctl.world.addBox({ id: 'test-wall', cx: (x + 1.6) / s, cz: z / s, hx: 0.08 / s, hz: 1.5 / s, y0: 0, y1: 2 });
                  window.__rs = { t0: W.time, how: [], done: null }; const r0 = __ncStats.rescue;
                  c.walkTo([{ x, z }, { x: x + 3, z }], { speed: 1.6 }).then(v => { __rs.done = { ok: v, t: W.time - __rs.t0, x: c.object3D.position.x, z: c.object3D.position.z, n: __ncStats.rescue - r0 }; });
                  return [x, z]; } }
              return null; }""", who)
            if not st:
                ok(f"保底（{who}）：找得到空地", False); continue
            seq, last = [], None
            for _ in range(240):
                s = pg.evaluate(f"() => {{ const c = __world.chars.get('{who}'), p = c.object3D.position; return [__world.time - __rs.t0, p.x, p.z, c._lastRescue || '', __rs.done]; }}")
                if s[3] and s[3] != last:
                    seq.append(s[3]); last = s[3]
                if s[4]:
                    break
                pg.wait_for_timeout(250)
            done = s[4]
            pg.evaluate(f"() => {{ const c = __world.chars.get('{who}'), w = c.inner.ctl.world, i = w.boxes.findIndex(b => b.id === 'test-wall'); if (i >= 0) w.boxes.splice(i, 1); }}")
            ok(f"保底（{who}）：被隱形牆擋住 → 依序 {seq} → {round(done['t'], 1) if done else '—'} 秒到達（≤ 25）、到達點離目的地 {round(_m.hypot(done['x'] - st[0] - 3, done['z'] - st[1]), 2) if done else '—'} 公尺（≤ 0.2）、用了 {done['n'] if done else '—'} 次保底",
               bool(done) and done["ok"] and done["t"] <= 25 and _m.hypot(done["x"] - st[0] - 3, done["z"] - st[1]) <= 0.2 and seq and seq[-1] == "glide", (seq, done, st))
        ok("保底：全程沒有主控台錯誤", not pg.errs, pg.errs[:3])
    finally:
        c.close()


def t_all(b, base):
    t_rescue(b, base)
    t_wallstuck(b, base)


register("辦公室牆邊卡住", lambda pg, b, base, code: t_all(b, base))
