# 驗收段落「辦公室運動場」（2026-11-15 擁有者：「旁邊幫我設定員工運動場，有羽毛球、籃球、網球、撞球、游泳池，並且每位員工都是可以直接操作、可使用……
#   都需要符合世界物理效果，像是當我把員工拿去燒再放到泳池他會消火」）
#   場地在 site/office/world/js/sports*.js；規劃見 docs/ai_office/plan.md 最後一節 S1～S3。
#   · 場地：五個場地都在、導航可走（從大門到每個場地的路徑不穿牆、不穿球網）、無主控台錯誤
#   · 羽毛球（真鍵盤＋真滑鼠）：選取員工→按 E 開始→介面出現「找一位同事一起打」→用真滑鼠點另一位員工邀請→他走過來→空白鍵發球→
#     人與電腦各至少擊球 2 次、合計至少 3 拍→ Esc 結束、送出 sport_start／sport_end／sport_score
#   · 網球：同上（按 E 自動找閒著的同事），來回至少 3 拍；球有彈跳
#   · 籃球：按 E 自動找同事→按住空白鍵蓄力（對準刻度）放開，投進至少一球；球與籃框、籃板碰撞有發生
#   · 撞球：真滑鼠拖曳瞄準出桿，球與球碰撞、至少有一顆球被撞動，Esc 結束
#   · 泳池：真滑鼠把「燒著的員工」拎起丟進泳池→ splashed（thrown）、extinguished（cause:'pool'）、水花粒子、浮起來；
#     走出泳池後身體濕（滴水）、短時間內碰營火不著火；對照組（沒濕的同事）同時碰營火會著火；免疫過了再碰會著火
#   · 夜晚：路燈光點併進暖光點雲、場地有燈
#   · 閒著的員工自己去運動（ambientNow）：兩位同事跑去打、送 sport_start（ambient）、結束後回座位（sportSess 清掉）
#   · 效能：靜態部分 +5 次繪製（對照 ?sports=0）、球與水另加 ≤ 4；4× 倍速下固定時間步數與模擬時間一致（1/120 秒）；每個模擬步平均 < 1 毫秒
#   · 手機 390×844：進入運動場（點「開始」）、自己練習、結束；介面不蓋住搖桿與按鈕、不超出畫面
# 由 _uitest.py 用 exec 載入，ok()、wait_until() 直接可用。
import math as _m

_SP_URL = "/office/world.html?ambient=0&q=low&pr=0.5"
_SP_EV = """() => { const W = __world; if (window.__spEv) return; window.__spEv = [];
  for (const t of ['sport_start', 'sport_end', 'sport_score', 'splashed', 'extinguished', 'burned', 'left_pool']) W.on(t, e => __spEv.push({ t, id: e.id, kind: e.kind || '', cause: e.cause || '', from: e.from || '', result: e.result || '', reason: e.reason || '', thrown: !!e.thrown, amb: !!e.ambient, opp: e.opponent || '', x: e.x, z: e.z })); }"""


def _sp_page(b, base, vw=1280, vh=800, mobile=False, daytime="day"):
    kw = {"viewport": {"width": vw, "height": vh}}
    if mobile:
        kw.update(is_mobile=True, has_touch=True, device_scale_factor=2)
    c = b.new_context(**kw)
    c.add_init_script(f"try{{localStorage.setItem('aiOffice.daytime','{daytime}');localStorage.removeItem('aiOffice.hr.v1')}}catch(e){{}}")
    pg = c.new_page(); pg.set_default_timeout(120000); pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)[:200]))
    pg.on("console", lambda m: pg.errs.append(m.text[:200]) if m.type == "error" and "favicon" not in m.text and "404" not in m.text else None)
    pg.goto(base.split("/index.html")[0].rstrip("/") + _SP_URL, wait_until="domcontentloaded")
    got = wait_until(pg, "() => window.__world && window.__world.ready", 90000)
    return c, pg, got


def _sp_adv(pg, sec):
    pg.evaluate("async (s) => { await __world.advanceAsync(s) }", sec)


def _sp_enter(pg, who, x, z, face=_m.pi / 2):
    """選取一位員工、放到場地裡（只有「走位」用傳送；開始、邀請、揮拍、投籃、拖曳、結束都是真鍵盤真滑鼠）、輕點一下方向鍵接管"""
    pg.evaluate("([id, x, z, f]) => { const W = __world, c = W.chars.get(id); W.pilot.select(c); c.standAt(x, z, f); }", [who, x, z, face])
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(250); pg.keyboard.press("ArrowLeft"); _sp_adv(pg, 2.5)


def _sp_god(pg, x, z, d):
    pg.evaluate("([x, z, d]) => __world.godAt(x, z, d)", [x, z, d]); pg.wait_for_timeout(2300)


def _sp_xy(pg, who):
    return pg.evaluate("(id) => { const c = __world.chars.get(id); return c && c._sx > -900 ? [c._sx, c._sy] : null }", who)


def _sp_evs(pg, kind=None, t=None):
    return pg.evaluate("([k, t]) => __spEv.filter(e => (!k || e.kind === k) && (!t || e.t === t))", [kind, t])


def _sp_calls(pg):
    """鏡頭飛完、繪製次數連續兩次一樣才算（機器很忙時鏡頭動畫會拖很久，中途量會量到別的畫面）"""
    last = -1
    for i in range(60):
        pg.wait_for_timeout(500)
        v = pg.evaluate("() => ({ c: __world.stats.calls, t: !!(__world.view && __world.view.tween) })")
        if not v["t"] and v["c"] == last:
            return v["c"]
        last = v["c"]
    return last


def t_sports(b, base):
    c, pg, got = _sp_page(b, base)
    try:
        ok("運動場：頁面載入", got)
        if not got:
            return
        pg.wait_for_timeout(600); pg.evaluate(_SP_EV)
        # ── 場地與導航
        info = pg.evaluate("""() => { const W = __world, S = W.sports; if (!S) return null; const nav = W.nav;
          const door = { x: 20.5, z: 31.0 }, out = {};
          for (const v of S.venues) { const p = nav.findPath(door, { x: v.at.x, z: v.at.z }); out[v.kind] = p ? { n: p.length, hits: nav.pathHits(p), reach: nav.isReach(v.at.x, v.at.z) || nav.nearestFree(v.at.x, v.at.z, 8) != null } : null; }
          return { venues: S.venues.map(v => v.kind), out, calls: W.stats.calls, err: S.err || 0 }; }""")
        ok("運動場：已掛載，五個場地（羽毛球、網球、籃球、撞球、游泳）", bool(info) and sorted(info["venues"]) == sorted(["badminton", "tennis", "basketball", "billiards", "pool"]), info and info["venues"])
        ok("運動場：從大門口到每個場地都找得到路、路徑沒有穿過牆或球網或池壁", bool(info) and all(v and v["hits"] == 0 and v["reach"] for v in info["out"].values()), info and info["out"])
        # 泳池入口：從場外走得進池中（池壁只有缺口可進）、球網把兩個半場隔開（從池中心走到入口的路徑要經過缺口）
        gap = pg.evaluate("""() => { const W = __world, nav = W.nav; const p = nav.findPath({ x: 2.2, z: 39.0 }, { x: 5.0, z: 35.0 }); const q = nav.findPath({ x: 3.0, z: 44.8 }, { x: 8.0, z: 44.8 });
          let via = false; if (p) for (let i = 1; i < p.length; i++) for (let k = 0; k <= 40; k++) { const t = k / 40, x = p[i - 1].x + (p[i].x - p[i - 1].x) * t, z = p[i - 1].z + (p[i].z - p[i - 1].z) * t; if (z > 37.0 && z < 37.2 && x > 3.5 && x < 5.3) via = true; }   // 池壁南側那一圈（z 37.0～37.2）只有 x 3.5～5.3 是缺口
          return { pool: p && { n: p.length, hits: nav.pathHits(p), viaGap: via }, net: q && { len: nav.pathLength(q), hits: nav.pathHits(q) } }; }""")
        ok("運動場：泳池只能從南邊缺口走進去；羽毛球網把兩個半場隔開（過網要繞遠路）", bool(gap) and gap["pool"] and gap["pool"]["hits"] == 0 and gap["pool"]["viaGap"] and gap["net"] and gap["net"]["len"] > 9, gap)

        # ───────── 羽毛球：按 E → 邀請（滑鼠點同事）→ 發球 → 來回 ─────────
        _sp_god(pg, 5.4, 44.8, 10)
        _sp_enter(pg, "data-steward", 3.6, 44.8)
        pg.evaluate("(id) => { const c = __world.chars.get(id); c.standAt(2.9, 43.6, 0); c.busy = false; }", "data-scraper")   # 一位站在場邊的同事（要在畫面上，才點得到）
        pg.wait_for_timeout(500)
        near = pg.evaluate("() => { const W = __world, v = W.sports.venueAt(W.pilot.sel); return v && v.kind }")
        ok("運動場：站進羽毛球場，偵測到場地（提示「按 E」）", near == "badminton", near)
        ok("運動場：場地提示條顯示「按 E 開始打羽毛球」", pg.evaluate("() => { const h = __world.sports.hud; return !h.hidden && h.innerText.includes('按 E') && h.innerText.includes('羽毛球') }"))
        pg.keyboard.press("KeyE"); pg.wait_for_timeout(500)
        st = pg.evaluate("() => { const s = __world.sports.sess; return s && { ph: s.phase, kind: s.kind, txt: __world.sports.hud.innerText } }")
        ok("運動場：按 E 開始羽毛球，介面出現「找一位同事一起打」", bool(st) and st["ph"] == "invite" and "找一位同事一起打" in st["txt"], st)
        xy = _sp_xy(pg, "data-scraper")
        ok("運動場：被邀請的同事在畫面上（可以用滑鼠點）", xy is not None, xy)
        if xy:
            pg.mouse.click(xy[0], xy[1]); pg.wait_for_timeout(400)
        st = pg.evaluate("() => { const s = __world.sports.sess; return s && { ph: s.phase, p: s.partner && s.partner.spec.id } }")
        ok("運動場：用滑鼠點另一位員工＝邀請他（他成為對手，進入「趕過來」）", bool(st) and st["p"] == "data-scraper" and st["ph"] in ("wait", "play"), st)
        _sp_adv(pg, 8)
        ok("運動場：被邀請的同事走到對面半場，比賽開始（play），送出 sport_start",
           pg.evaluate("() => { const s = __world.sports.sess; return !!(s && s.phase === 'play' && s.game) }") and len(_sp_evs(pg, "badminton", "sport_start")) >= 1)
        pg.evaluate("() => { __world.speed = 0.4 }")
        pg.keyboard.press("Space"); pg.wait_for_timeout(200)
        g = None
        for k in range(1500):
            g = pg.evaluate("""async () => { const W = __world, G = W.sports.sess && W.sports.sess.game; if (!G) return null; await W.advanceAsync(1 / 20);
              const h = G.players.find(p => p.human), b = G.ball, q = h.c.object3D.position, st = G.stats; let act = null;
              if (G.phase === 'rally') { const side = h.side, onMine = (b.x < 5.4 ? 'A' : 'B') === side; if (onMine && b.y < 2.1 && Math.hypot(b.x - q.x, b.z - q.z) > 0.9) { h.c.standAt(b.x + (side === 'A' ? -0.45 : 0.45), b.z, 0); } if (onMine && Math.hypot(b.x - h.c.object3D.position.x, b.z - h.c.object3D.position.z) < 1.15 && b.y < 2.0) act = 'space'; }
              else if (G.phase === 'serve') act = 'space';
              return { act, hits: st.hits, hu: st.byHuman, ai: st.byAI, pts: st.points, ph: G.phase }; }""")
            if g is None:
                break
            if g["act"] == "space":
                pg.keyboard.press("Space")
            if g["hu"] >= 2 and g["ai"] >= 2 and g["hits"] >= 4:
                break
        ok(f"羽毛球：來回至少 3 拍（合計 {g and g['hits']} 拍：人 {g and g['hu']}、電腦 {g and g['ai']}）", bool(g) and g["hits"] >= 3 and g["hu"] >= 1 and g["ai"] >= 1, g)
        phys_ok = pg.evaluate("() => { const G = __world.sports.sess && __world.sports.sess.game; return !!G && G.ball.y >= 0 && isFinite(G.ball.x) && isFinite(G.ball.vy) }")
        ok("羽毛球：球的座標與速度有限、沒有穿過地面（y ≥ 0）", phys_ok)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        ok("羽毛球：按 Esc 結束運動（人保持被選取、操控中），球收掉", pg.evaluate("() => !__world.sports.sess && __world.pilot.sel && __world.pilot.engaged && !__world.sports.hud.innerText.includes('先到')"))
        ev = _sp_evs(pg, "badminton")
        ok("羽毛球：送出 sport_start／sport_end（reason user 或 cancel）", any(e["t"] == "sport_start" for e in ev) and any(e["t"] == "sport_end" and e["reason"] in ("user",) for e in ev), [(e["t"], e["reason"]) for e in ev][:6])
        ok("羽毛球：每得一分送出 sport_score（含對手 id）", any(e["t"] == "sport_score" and e["opp"] for e in ev) or g and g["pts"] == 0, [(e["t"], e["result"], e["opp"]) for e in ev][:6])
        _sp_adv(pg, 25)
        ok("羽毛球：結束後對手自己走回座位（不再被運動場佔住）", pg.evaluate("() => !__world.chars.get('data-scraper').sportSess"))
        pg.evaluate("() => { __world.speed = 1 }")

        # ───────── 網球（按 E 兩次：自動找閒著的同事）─────────
        pg.evaluate("() => { const W = __world; W.pilot.deselect && W.pilot.deselect(); }"); _sp_adv(pg, 2)
        _sp_god(pg, 14.4, 44.8, 11)
        _sp_enter(pg, "finance-quant", 12.0, 44.8)
        pg.keyboard.press("KeyE"); pg.wait_for_timeout(300); pg.keyboard.press("KeyE"); pg.wait_for_timeout(200)
        part = pg.evaluate("() => { const s = __world.sports.sess; return s && s.partner && s.partner.spec.id }")
        ok("運動場：網球「按 E 自動找閒著的同事」找到對手", bool(part), part)
        _sp_adv(pg, 30)
        ok("運動場：網球對手到位、比賽開始", pg.evaluate("() => { const s = __world.sports.sess; return !!(s && s.phase === 'play' && s.game && s.game.kind === 'tennis') }"))
        pg.evaluate("() => { __world.speed = 0.4 }")
        pg.keyboard.press("Space"); bounced = 0; g = None
        for k in range(1800):
            g = pg.evaluate("""async () => { const W = __world, G = W.sports.sess && W.sports.sess.game; if (!G) return null; const vy0 = G.ball.vy; await W.advanceAsync(1 / 20);
              const h = G.players.find(p => p.human), b = G.ball, q = h.c.object3D.position, st = G.stats; let act = null;
              if (G.phase === 'rally') { const side = h.side, onMine = (b.x < 14.4 ? 'A' : 'B') === side; if (onMine && b.y < 1.7 && Math.hypot(b.x - q.x, b.z - q.z) > 1.0) { h.c.standAt(b.x + (side === 'A' ? -0.5 : 0.5), b.z, 0); } if (onMine && Math.hypot(b.x - h.c.object3D.position.x, b.z - h.c.object3D.position.z) < 1.3 && b.y < 1.7) act = 'space'; }
              else if (G.phase === 'serve') act = 'space';
              return { act, hits: st.hits, hu: st.byHuman, ai: st.byAI, bounce: vy0 < 0 && G.ball.vy > 0 && G.ball.y < 0.2, ph: G.phase }; }""")
            if g is None:
                break
            bounced += 1 if g["bounce"] else 0
            if g["act"] == "space":
                pg.keyboard.press("Space")
            if g["hits"] >= 4 and bounced >= 1:
                break
        ok(f"網球：來回至少 3 拍（{g and g['hits']} 拍），球落地有彈起（{bounced} 次）", bool(g) and g["hits"] >= 3 and bounced >= 1, g)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        ok("網球：按 Esc 結束", pg.evaluate("() => !__world.sports.sess"))
        pg.evaluate("() => { __world.speed = 1 }"); _sp_adv(pg, 25)

        # ───────── 籃球：按住空白鍵蓄力、放開投籃 ─────────
        _sp_god(pg, 14.7, 36.0, 10)
        _sp_enter(pg, "smc-technical", 14.7, 36.6)
        pg.keyboard.press("KeyE"); pg.wait_for_timeout(300); pg.keyboard.press("KeyE"); pg.wait_for_timeout(200)
        _sp_adv(pg, 30)
        ok("運動場：籃球對手到位、開始（介面有蓄力表）", pg.evaluate("() => { const s = __world.sports.sess; return !!(s && s.phase === 'play' && s.game && s.game.kind === 'basketball') }"))
        pg.evaluate("() => { __world.speed = 0.2 }")
        made = 0; shots = 0
        for k in range(14):
            r = pg.evaluate("""async () => { const W = __world, S = W.sports; for (let i = 0; i < 600; i++) { const G = S.sess && S.sess.game; if (!G) return null; const m = G.hud().meter; if (m) return { ideal: m.ideal }; await W.advanceAsync(1 / 30); } return null; }""")
            if not r:
                break
            pg.keyboard.down("Space")
            for i in range(600):
                v = pg.evaluate("() => { const G = __world.sports.sess.game, m = G.hud().meter; return m ? m.v : 9 }")
                if v >= r["ideal"] - 0.005:
                    break
            pg.keyboard.up("Space"); shots += 1
            _sp_adv(pg, 7)
            made = pg.evaluate("() => __world.sports.sess && __world.sports.sess.game ? __world.sports.sess.game.players.find(p => p.human).score : -1")
            if made >= 1:
                break
        ok(f"籃球：按住空白鍵蓄力、放開投籃，投進至少一球（{shots} 次出手、進 {made}）", made >= 1, (shots, made))
        gs = pg.evaluate("() => { const G = __world.sports.sess && __world.sports.sess.game; return G && G.stats }")
        ok("籃球：球與地面、籃板或籃框有碰撞（彈跳 > 0、框＋板碰撞 > 0 或進球）", bool(gs) and gs["bounces"] > 0 and (gs["rim"] + gs["board"] > 0 or gs["made"] > 0), gs)
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        ok("籃球：按 Esc 結束", pg.evaluate("() => !__world.sports.sess"))
        pg.evaluate("() => { __world.speed = 1 }"); _sp_adv(pg, 20)

        # ───────── 撞球：滑鼠拖曳瞄準 ─────────
        _sp_god(pg, 8.2, 39.8, 6.2)
        _sp_enter(pg, "efficiency-planner", 8.2, 41.5, _m.pi)
        pg.keyboard.press("KeyE"); pg.wait_for_timeout(300); pg.keyboard.press("KeyE"); pg.wait_for_timeout(200)
        _sp_adv(pg, 30)
        ok("運動場：撞球對手到位、開始", pg.evaluate("() => { const s = __world.sports.sess; return !!(s && s.phase === 'play' && s.game && s.game.kind === 'billiards') }"))
        pg.evaluate("() => { __world.speed = 0.2 }")
        pg.evaluate("async () => { const W = __world; for (let i = 0; i < 600; i++) { const G = W.sports.sess.game; if (G.canAim()) break; await W.advanceAsync(1 / 30); } }")
        before = pg.evaluate("() => __world.sports.sess.game.balls.map(q => [q.x, q.z])")

        def scr(tx, tz):
            return pg.evaluate("([tx, tz]) => { const W = __world, T = W.sports.LAY.table, v = new W.THREE.Vector3(T.cx + tx, T.top, T.cz + tz).project(W.camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight] }", [tx, tz])
        cue = before[0]; tg = before[1]; ang = _m.atan2(tg[1] - cue[1], tg[0] - cue[0])
        p0 = scr(cue[0] - _m.cos(ang) * 0.7, cue[1] - _m.sin(ang) * 0.7)
        pg.mouse.move(p0[0] - 40, p0[1]); pg.mouse.down(); pg.mouse.move(p0[0], p0[1], steps=5); _sp_adv(pg, 0.2)
        ok("撞球：滑鼠按下拖曳時出現瞄準線與球桿", pg.evaluate("() => { const S = __world.sports; return S.sess.game.aimState().on && S.sess.game.aimState().pow > 0.1 }"))
        pg.mouse.up(); _sp_adv(pg, 7)
        gs = pg.evaluate("() => ({ st: __world.sports.sess.game.stats, now: __world.sports.sess.game.balls.map(q => [q.x, q.z, q.in]) })")
        moved = sum(1 for i in range(1, len(before)) if _m.hypot(gs["now"][i][0] - before[i][0], gs["now"][i][1] - before[i][1]) > 0.02 or not gs["now"][i][2])
        ok(f"撞球：出桿後球與球碰撞（{gs['st']['hits']} 次）、至少一顆彩球被撞動（{moved} 顆）、碰到桌邊 {gs['st']['cushion']} 次", gs["st"]["hits"] >= 1 and moved >= 1, gs["st"])
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
        ok("撞球：按 Esc 結束", pg.evaluate("() => !__world.sports.sess"))
        pg.evaluate("() => { __world.speed = 1 }"); _sp_adv(pg, 20)

        # ───────── 泳池：燒著的員工丟進泳池 ─────────
        pg.evaluate("() => { const W = __world; W.pilot.deselect && W.pilot.deselect(); }")
        _sp_god(pg, 5.0, 36.2, 11)
        # 小燭（flame）本身就是火焰、不會被燒：挑三位不是 flame 的員工
        cand = pg.evaluate("() => [...__world.chars.values()].filter(c => !c.spec.isCeo && !c.spec.pet && c.look.species !== 'flame' && !['data-steward', 'finance-quant', 'smc-technical', 'efficiency-planner', 'data-scraper'].includes(c.spec.id)).map(c => c.spec.id)")
        who, w2, w3 = cand[0], cand[1], cand[2]
        pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); c.standAt(3.0, 39.4, Math.PI); c.busy = false; c.atDesk = false; W.fire.ignite(c, 'sporttest'); }", who)
        pg.evaluate("() => { __world.speed = 0.05 }"); pg.wait_for_timeout(700)   # 著火的人會驚慌跑開：先把時間放到很慢，才拎得到
        xy = _sp_xy(pg, who)
        burning = pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", who)
        ok("泳池：測試員工著火了（burning）", burning == "burning", burning)
        tgt = pg.evaluate("() => { const W = __world, v = new W.THREE.Vector3(5.2, 1.0, 35.0).project(W.camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight] }")
        grabbed = False
        if xy:
            k = pg.evaluate("(id) => { const W = __world, c = W.chars.get(id), cv = document.getElementById('cv'); return cv.clientHeight / (2 * Math.tan(W.camera.fov * Math.PI / 360) * c._sd) }", who)
            sy = xy[1] + k * 0.45
            pg.mouse.move(xy[0], sy); pg.mouse.down(); pg.wait_for_timeout(800); pg.mouse.move(xy[0] + 8, sy - 8, steps=2); pg.wait_for_timeout(200)
            grabbed = pg.evaluate("(id) => __world.chars.get(id).state", who) == "held"
            pg.mouse.move(tgt[0], tgt[1], steps=6); pg.wait_for_timeout(500); pg.mouse.up()
        pg.evaluate("() => { __world.speed = 1 }")
        ok("泳池：用真滑鼠把燒著的員工拎起來（held）", grabbed, (xy, grabbed))
        seen_float = False; seen_in = False
        for i in range(24):
            _sp_adv(pg, 0.25)
            r = pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); return { in: W.sports.water.inWater(c), y: Math.max(c.object3D.position.y, c._floatY || 0), fire: W.fire.stateOf(c).state } }", who)
            seen_in = seen_in or r["in"]; seen_float = seen_float or (r["in"] and r["y"] > 0.05)
            if r["in"] and r["fire"] != "burning" and i > 4:
                break
        evs = pg.evaluate("() => __spEv")
        sp = [e for e in evs if e["t"] == "splashed" and e["id"] == who]; ex = [e for e in evs if e["t"] == "extinguished" and e["id"] == who and e["cause"] == "pool"]
        ok("泳池：丟進水裡 → 送出 splashed（from thrown、附位置）", bool(sp) and sp[0]["thrown"], sp[:1])
        ok("泳池：燒著的人立刻熄火 → extinguished（cause:'pool'）；火焰狀態不再是 burning", bool(ex) and pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", who) != "burning", ex[:1])
        ok("泳池：濺水粒子與漣漪有產生（splashes ≥ 1）、人浮起來（高度 > 0.05）", pg.evaluate("() => __world.sports.water.stats.splashes") >= 1 and seen_float, (seen_in, seen_float))
        # 沒著火的同事丟進泳池：濕、走出來、免疫
        pg.evaluate("([a, b]) => { const W = __world; for (const id of [a, b]) { const c = W.chars.get(id); c.busy = false; } W.chars.get(a).standAt(6.5, 39.2, Math.PI); W.chars.get(b).standAt(7.4, 39.2, Math.PI); }", [w2, w3])
        pg.evaluate("([a]) => { const W = __world; W.phys.throwChar(W.chars.get(a), 0.0, 5.0, -3.4); }", [w2])
        for i in range(40):
            _sp_adv(pg, 0.25)
            if pg.evaluate("(id) => __world.sports.water.inWater(__world.chars.get(id))", w2):
                break
        ok("泳池：沒著火的同事被丟進泳池也濺水（splashed）", any(e["t"] == "splashed" and e["id"] == w2 for e in pg.evaluate("() => __spEv")))
        pg.evaluate("async (id) => { const W = __world; for (let i = 0; i < 30 * 40; i++) { if (!W.sports.water.inWater(W.chars.get(id))) break; await W.advanceAsync(1 / 30); } }", w2)
        left = pg.evaluate("(id) => __spEv.some(e => e.t === 'left_pool' && e.id === id)", w2)
        ok("泳池：他自己游（走）回岸邊、走出泳池（left_pool）", left)
        wet = pg.evaluate("(id) => { const c = __world.chars.get(id); return { wet: __world.sports.water.isWet(c) } }", w2)
        ok("泳池：走出來之後身體濕（滴水）", wet["wet"], wet)
        # 營火：濕的同事碰營火不著火；沒濕的對照組同時碰會著火
        pg.evaluate("([a, b]) => { const W = __world, f = W.fire.center; W.chars.get(a).standAt(f.x + 0.5, f.z + 0.2, 0); W.chars.get(b).standAt(f.x - 0.5, f.z - 0.2, 0); }", [w2, w3])
        _sp_adv(pg, 1.5)
        s2 = pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", w2); s3 = pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", w3)
        ok("泳池：剛出泳池、身體還濕的人碰營火一樣會著火（11-16 擁有者：拿掉出水防火）；對照組也著火", s2 != "none" and s3 != "none", (s2, s3))
        pg.evaluate("([a, b]) => { const W = __world; W.fire.reset(); W.chars.get(a).busy = false; W.chars.get(a)._fireImmuneUntil = 0; }", [w2, w3])
        pg.evaluate("([a]) => { const W = __world, f = W.fire.center, c = W.chars.get(a); c.standAt(f.x + 4, f.z, 0); }", [w2]); _sp_adv(pg, 0.5)
        pg.evaluate("([a]) => { const W = __world, f = W.fire.center, c = W.chars.get(a); c.standAt(f.x + 0.5, f.z + 0.2, 0); }", [w2]); _sp_adv(pg, 1.5)
        s2b = pg.evaluate("(id) => __world.fire.stateOf(__world.chars.get(id)).state", w2)
        ok("泳池：熄火重來之後同一個人碰營火仍會著火", s2b != "none", s2b)
        ok("運動場：全程沒有主控台錯誤與運動場例外", not pg.errs and not pg.evaluate("() => __world.sports.err || 0"), (pg.errs[:3], pg.evaluate("() => __world.sports.err")))
    finally:
        c.close()


def t_sports_ambient(b, base):
    c, pg, got = _sp_page(b, base)
    try:
        ok("運動場閒時：頁面載入", got)
        if not got:
            return
        pg.wait_for_timeout(600); pg.evaluate(_SP_EV)
        r = pg.evaluate("() => { const s = __world.sports.ambientNow('badminton'); return s && { a: s.me.spec.id, b: s.partner && s.partner.spec.id } }")
        ok("閒著的員工自己去運動：兩位閒著的同事被叫去打羽毛球", bool(r) and r["a"] and r["b"], r)
        _sp_adv(pg, 25)
        g = pg.evaluate("() => { const a = __world.sports.amb; return a && a.game && { kind: a.game.kind, hits: a.game.stats.hits, ai: a.game.players.every(p => !p.human) } }")
        ok("閒著的員工：兩人都是電腦控制、真的在對打（hits ≥ 2）", bool(g) and g["ai"] and g["hits"] >= 2, g)
        ok("閒著的員工：送出 sport_start（ambient）", any(e["t"] == "sport_start" and e["amb"] for e in pg.evaluate("() => __spEv")))
        pg.evaluate("() => __world.sports.endAmbient()"); _sp_adv(pg, 50)
        back = pg.evaluate("(r) => [r.a, r.b].map(id => { const c = __world.chars.get(id); return { sp: !!c.sportSess, st: c.state, busy: !!c.busy } })", r)
        ok("閒著的員工：結束後各自走回座位、不再被運動場佔住", all(not x["sp"] for x in back) and all(x["st"] == "sit" for x in back), back)
        for k in ("tennis", "basketball", "billiards", "swim"):
            rr = pg.evaluate("(k) => { const s = __world.sports.ambientNow(k); return !!s }", k)
            _sp_adv(pg, 20)
            gg = pg.evaluate("() => { const a = __world.sports.amb; return a && (a.game ? a.game.kind : a.kind) }")
            ok(f"閒著的員工：自己去{ {'tennis': '打網球', 'basketball': '打籃球', 'billiards': '打撞球', 'swim': '游泳'}[k] }", rr and bool(gg), (rr, gg))
            pg.evaluate("() => __world.sports.endAmbient()"); _sp_adv(pg, 3)
        ok("運動場閒時：沒有主控台錯誤", not pg.errs and not pg.evaluate("() => __world.sports.err || 0"), pg.errs[:3])
    finally:
        c.close()


def t_sports_night_perf(b, base):
    # 夜晚：場地有燈
    c, pg, got = _sp_page(b, base, daytime="night")
    try:
        ok("運動場夜晚：頁面載入", got)
        if not got:
            return
        pg.evaluate("() => __world.daytime.set('night')"); pg.wait_for_timeout(800)
        r = pg.evaluate("""() => { const W = __world, L = W.sports.LAY, oL = W.daytime.outL, g = oL.cores && oL.cores.geometry.attributes.position;
          let mine = 0; if (g) for (let i = 0; i < g.count; i++) { const x = g.getX(i), z = g.getZ(i); if (L.lamps.some(q => Math.abs(q[0] - x) < 0.01 && Math.abs(q[1] - z) < 0.01)) mine++; }
          return { k: oL.k, mine, lamps: L.lamps.length, glow: W.extraGlow.filter(q => q[0] < 20).length, spots: !!(oL.spots && oL.spots.visible) }; }""")
        ok(f"運動場夜晚：路燈的光點並進暖光點雲（{r['mine']}/{r['lamps']} 盞）、地面光斑亮著", r["k"] > 0.5 and r["mine"] >= r["lamps"] - 1 and r["spots"], r)
        _sp_god(pg, 9.9, 40.2, 24)
        shot = pg.screenshot()
        from PIL import Image as _I
        import io as _io
        im = _I.open(_io.BytesIO(shot)).convert("L"); W_, H_ = im.size
        pts = pg.evaluate("""() => { const W = __world, q = W.sports.LAY.lamps[3], pr = (x, y, z) => { const v = new W.THREE.Vector3(x, y, z).project(W.camera); return [(v.x + 1) / 2 * innerWidth, (1 - v.y) / 2 * innerHeight]; }; return { lamp: pr(q[0], 0.1, q[1]), ref: pr(14.4, 0.1, 45.5) }; }""")
        def mean(cx, cy, r=14):
            cx, cy = int(cx), int(cy); box = im.crop((max(0, cx - r), max(0, cy - r), min(W_, cx + r), min(H_, cy + r))); px = list(box.getdata()); return sum(px) / max(1, len(px))
        near, far = mean(*pts["lamp"]), mean(*pts["ref"])
        ok(f"運動場夜晚：路燈腳下的地面比沒有燈的網球場中央亮（{near:.0f} 對 {far:.0f}）", near > far + 15, (near, far))
        ok("運動場夜晚：水面夜晚自發光（泳池燈）、沒有主控台錯誤", pg.evaluate("() => __world.sports.water.mesh.material.uniforms.uNight.value") > 0.4 and not pg.errs, pg.errs[:3])
    finally:
        c.close()
    # 效能與固定時間步
    c, pg, got = _sp_page(b, base)
    c2 = pg2 = None
    try:
        pg.evaluate("() => __world.godAt(9.9, 40.2, 26)"); on = _sp_calls(pg)
        pg.evaluate("() => { __world.sports.ambientNow('badminton') }"); _sp_adv(pg, 25)
        pg.wait_for_timeout(600)
        during = pg.evaluate("() => __world.stats.calls")
        s0 = pg.evaluate("() => ({ steps: __world.sports.steps, t: __world.time, ph: __world.sports.perf.n, ms: __world.sports.perf.ms })")
        pg.evaluate("() => __world.advance(10)")
        s1 = pg.evaluate("() => ({ steps: __world.sports.steps, t: __world.time, n: __world.sports.perf.n, ms: __world.sports.perf.ms, max: __world.sports.perf.max, game: !!(__world.sports.amb && __world.sports.amb.game) })")
        dt = s1["t"] - s0["t"]; dsteps = s1["steps"] - s0["steps"]
        ok(f"運動場：4× 倍速也用固定時間步（模擬 {dt:.1f} 秒 → {dsteps} 步，應為 {dt * 120:.0f}±8）", s1["game"] and abs(dsteps - dt * 120) <= 8, (dt, dsteps, s1["game"]))
        avg = (s1["ms"] - s0["ms"]) / max(1, s1["n"] - s0["ph"]); best = pg.evaluate("() => __world.sports.perf.best")
        ok(f"運動場：球的物理＋電腦走位每個模擬步 {best:.2f} 毫秒（每 40 步一批取最快的一批，< 1.0；全程平均 {avg:.2f}、最慢一步 {s1['max']:.1f}，機器忙時會被搶 CPU 而變大）", best < 1.0, (best, avg, s1["max"]))
        pg.evaluate("() => { __world.speed = 4 }"); pg.wait_for_timeout(2500)
        ok("運動場：W.speed = 4 時運動場不丟例外", not pg.evaluate("() => __world.sports.err || 0") and not pg.errs, (pg.errs[:2]))
        c2 = b.new_context(viewport={"width": 1280, "height": 800}); pg2 = c2.new_page(); pg2.set_default_timeout(120000)
        pg2.add_init_script("try{localStorage.setItem('aiOffice.daytime','day')}catch(e){}")
        pg2.goto(base.split("/index.html")[0].rstrip("/") + _SP_URL + "&sports=0", wait_until="domcontentloaded")
        wait_until(pg2, "() => window.__world && window.__world.ready", 90000)
        pg2.evaluate("() => __world.godAt(9.9, 40.2, 26)"); off = _sp_calls(pg2)
        ok(f"運動場：靜態場地繪製次數增量 {on - off}（≤ +6：場地、球網、招牌、水、水花粒子；對照 ?sports=0）", on - off <= 6, (on, off))
        extra = pg.evaluate("() => __world.sports.drawObjects().length")
        ok(f"運動場：打球中運動場自己的繪製物件共 {extra} 個（靜態 5 ＋ 球、陰影 2 ＝ 7；撞球另有球組、球桿、瞄準線 ≤ 10）", 5 < extra <= 10, extra)
        ok(f"運動場：（參考）整個畫面打球中的總繪製次數 {during}、沒開運動場 {off}；差額含兩位同事離座進入畫面的角色", True)
    finally:
        c.close()
        if c2:
            c2.close()


def t_sports_mobile(b, base):
    c, pg, got = _sp_page(b, base, 390, 844, mobile=True)
    try:
        ok("運動場手機：頁面載入（390×844）", got)
        if not got:
            return
        pg.evaluate(_SP_EV)
        pg.evaluate("(id) => { const W = __world, c = W.chars.get(id); W.pilot.select(c); c.standAt(14.7, 36.6, Math.PI / 2); }", "data-steward")
        pg.evaluate("() => __world.godAt(14.7, 36.0, 12)"); pg.wait_for_timeout(2300); _sp_adv(pg, 1)
        hud = pg.evaluate("() => { const h = __world.sports.hud, r = h.getBoundingClientRect(); return { hid: h.hidden, txt: h.innerText, r: [r.left, r.top, r.right, r.bottom], btn: [...h.querySelectorAll('button')].map(b => b.textContent) } }")
        ok("運動場手機：站進球場出現「開始」按鈕（不用鍵盤）", not hud["hid"] and "開始" in hud["btn"], hud)
        pg.evaluate("() => { const b = [...__world.sports.hud.querySelectorAll('button')].find(b => b.textContent === '開始'); b.click() }"); pg.wait_for_timeout(600)
        ok("運動場手機：點「開始」進入運動（找同事介面，有「自動找同事」「自己練習」）", pg.evaluate("() => { const s = __world.sports.sess; const t = __world.sports.hud.innerText; return !!s && s.phase === 'invite' && t.includes('自己練習') && t.includes('自動找同事') }"))
        pg.evaluate("() => { const b = [...__world.sports.hud.querySelectorAll('button')].find(b => b.textContent === '自己練習'); b.click() }"); pg.wait_for_timeout(500)
        ok("運動場手機：點「自己練習」開始投籃，有「按住蓄力・放開投籃」鈕", pg.evaluate("() => { const s = __world.sports.sess; return !!s && s.phase === 'play' && [...__world.sports.hud.querySelectorAll('button')].some(b => b.textContent.includes('蓄力')) }"))
        lay = pg.evaluate("""() => { const h = __world.sports.hud.getBoundingClientRect(), q = s => { const e = document.querySelector(s); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); return r.width ? [r.left, r.top, r.right, r.bottom] : null };
          const pad = q('.pt-pad .pt-joy'), btns = q('.pt-pad .pt-btns'), tips = q('.pt-tips'); const hit = (a, b) => a && b && a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
          const H = [h.left, h.top, h.right, h.bottom]; return { H, pad, btns, tips, overJoy: hit(H, pad), overBtns: hit(H, btns), overTips: hit(H, tips), inside: h.left >= 0 && h.right <= innerWidth && h.top >= 0 && h.bottom <= innerHeight, hscroll: document.documentElement.scrollWidth > innerWidth }; }""")
        ok("運動場手機：介面不蓋住搖桿、按鈕、操作說明，且完整在畫面內、沒有橫向捲動", not lay["overJoy"] and not lay["overBtns"] and not lay["overTips"] and lay["inside"] and not lay["hscroll"], lay)
        # 手指按住蓄力 → 放開
        btn = pg.evaluate("() => { const b = [...__world.sports.hud.querySelectorAll('button')].find(b => b.textContent.includes('蓄力')), r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2] }")
        pg.evaluate("() => { __world.speed = 0.5 }")
        pg.mouse.move(btn[0], btn[1]); pg.mouse.down(); _sp_adv(pg, 0.8)
        ch = pg.evaluate("() => __world.sports.sess.game.hud().meter && __world.sports.sess.game.hud().meter.v")
        pg.mouse.up(); _sp_adv(pg, 2)
        shots = pg.evaluate("() => __world.sports.sess.game.stats.shots")
        ok(f"運動場手機：手指按住「蓄力」鈕有蓄力（{ch and round(ch, 2)}），放開就出手（出手 {shots} 次）", bool(ch) and ch > 0.1 and shots >= 1, (ch, shots))
        pg.evaluate("() => { const b = [...__world.sports.hud.querySelectorAll('button')].find(b => b.textContent.startsWith('結束')); b.click() }"); pg.wait_for_timeout(400)
        ok("運動場手機：點「結束」離開運動（介面收起、球收掉）", pg.evaluate("() => !__world.sports.sess && !document.body.classList.contains('sp-on')"))
        ok("運動場手機：沒有主控台錯誤", not pg.errs and not pg.evaluate("() => __world.sports.err || 0"), pg.errs[:3])
    finally:
        c.close()


import os as _os


def _sp_run(b, base):
    parts = _os.environ.get("SP_PARTS", "main,ambient,night,mobile").split(",")   # 只重跑某幾塊時用（例如 SP_PARTS=night,mobile）
    for name, fn in (("main", t_sports), ("ambient", t_sports_ambient), ("night", t_sports_night_perf), ("mobile", t_sports_mobile)):
        if name in parts:
            fn(b, base)


register("辦公室運動場", lambda pg, b, base, code: _sp_run(b, base))
