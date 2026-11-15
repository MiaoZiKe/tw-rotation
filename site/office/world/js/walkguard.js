// 走路保底（2026-11-15，無業遊民區「走路狀態卻原地不動」事故）。
// 根因：被丟出去落地後心情層讓他「頭暈」並暫停走路（pause，約 3.6～5 秒），但導演／人事在暫停期間就把路徑給了他 → 狀態是 walk、速度 0，
//   名牌與跟隨鏡頭都以為他在走。前面已改成「暫停結束才給路徑」（W.untilUnpaused）；這裡是最後一道保底，管所有還會發生的原地不動：
//   · 暫停超過 PAUSE_MAX 秒（而且不是「被你點選所以停下來面向你」那個設計）→ 強制解除暫停繼續走
//   · 沒暫停卻連續 STALL_T 秒沒前進（< 0.3 公尺）→ ① 從現在位置重新找路 ② 再不行：待業的人改站在原地（下一輪重新挑地方），在職的人直接滑向目的地（略過碰撞）
//   新角色在 newchar.js 本身另有 3 秒一階的保底（重新找路／略過／滑回），它換路徑時這裡的計時跟著歸零，所以只會接住它沒接到的（舊角色、被暫停卡住的）。
export function createWalkGuard(W) {
  const PAUSE_MAX = 9, STALL_T = 6, G = { stats: { pauseFix: 0, replan: 0, stand: 0, glide: 0 }, log: [] }, st = new Map(); let next = 0;
  const note = (c, what, p) => { G.log.push({ id: c.spec.id, what, t: +W.time.toFixed(1), x: +p.x.toFixed(2), z: +p.z.toFixed(2) }); if (G.log.length > 40) G.log.shift(); };
  G.tick = () => {
    if (W.time < next) return; const dt = 0.5; next = W.time + dt;
    for (const c of W.chars.values()) {
      let s = st.get(c); if (!s) st.set(c, s = {});
      if (!c._path || c.state === 'held' || c.state === 'sit' || c.piloted) { s.path = null; continue; }
      const p = c.object3D.position;
      if (s.path !== c._path) { s.path = c._path; s.t0 = W.time; s.x = p.x; s.z = p.z; s.stage = 0; s.pt = 0; }
      if (c._pause) {
        if (W.attn && W.attn.current() === c) { s.pt = 0; continue; }          // 被點選所以停下來面向你：是設計，不算
        if ((s.pt += dt) > PAUSE_MAX) { c.pause(false); G.stats.pauseFix++; note(c, 'pauseFix', p); s.pt = 0; s.t0 = W.time; s.x = p.x; s.z = p.z; }
        continue;
      }
      s.pt = 0;
      if (Math.hypot(p.x - s.x, p.z - s.z) > 0.3) { s.t0 = W.time; s.x = p.x; s.z = p.z; continue; }
      if (W.time - s.t0 < STALL_T) continue;
      s.t0 = W.time; const last = c._path[c._path.length - 1];
      if (s.stage === 0) {
        s.stage = 1; const np = W.nav.findPath({ x: p.x, z: p.z }, last);
        if (np && np.length >= 2) { c._path = np; c._pi = 1; c._prog = null; s.path = c._path; G.stats.replan++; note(c, 'replan', p); continue; }
      }
      if (c.jobless) { G.stats.stand++; note(c, 'stand', p); const f = W.nav.nearestFree(p.x, p.z, 8) || { x: p.x, z: p.z }; c.stop(false); c.standAt(f.x, f.z, c.heading); c.setAction('idle'); }
      else { G.stats.glide++; note(c, 'glide', p); c._path = [{ x: p.x, z: p.z }, last]; c._pi = 1; c._prog = null; c._ghost = 99; s.path = c._path; }
    }
  };
  W.walkGuard = G;
  return G;
}
