// 子 Agent 連線（2026-11-16 第二批第 2 項；Andy：「全做」）
//
// 派出子 Agent 時，派他的人（主工作階段＝CEO，第二個以上的工作階段＝CEO 分身）與那位同事之間畫一條柔和的弧線：
//   · 進行中：虛線緩緩流動（看得出「還在連著」）；同事從大門走進來（名冊沒有的新類型，roster.js 的報到演出）或從座位走去 CEO 那邊領任務（jobs.js），線一路跟著他。
//   · 交件（SubagentStop）：線變實、淡出（約 1.2 秒）後移除；同事照 jobs.js 的流程回座位。
//   · 區塊辦公室（blocks.js）：新類型由 roster.js 長出新區塊，線一樣連到新區塊裡的那位。
// 資料：live.js 在 startAgent（SubagentStart／快照裡進行中的子 Agent）呼叫 W.links.open(代號, 派工者, 同事)，SubagentStop 呼叫 W.links.close(代號)。
// 只畫線，不存任何資料；功能鍵 office.liveviz 關掉就不畫。
import { THREE } from './kit.js';

const NS = 'http://www.w3.org/2000/svg';

export function createLinks(W) {
  const K = { map: new Map(), nOpen: 0, nClose: 0, fadeMs: 1200 };
  W.links = K;
  const gateOn = () => { try { return !W.gate || !W.gate.peek || W.gate.peek('office.liveviz').pass !== false; } catch (e) { return true; } };
  const css = document.createElement('style'); css.id = 'lkCss';
  css.textContent = `
#lkLayer{position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:3;overflow:hidden}
#lkLayer path{fill:none;stroke:#f0a35e;stroke-width:3;stroke-linecap:round;stroke-dasharray:2 9;opacity:.85;animation:lkFlow 1.1s linear infinite;transition:opacity 1.2s ease-out,stroke-width .4s}
#lkLayer path.halo{stroke:#fffaf2;stroke-width:7;stroke-dasharray:none;opacity:.55;animation:none}
#lkLayer g.end path{stroke-dasharray:none;opacity:0}
#lkLayer circle{fill:#f0a35e;transition:opacity 1.2s}#lkLayer g.end circle{opacity:0}
@keyframes lkFlow{to{stroke-dashoffset:-22}}
@media (prefers-reduced-motion:reduce){#lkLayer path{animation:none}}`;
  document.head.append(css);
  const svg = document.createElementNS(NS, 'svg'); svg.id = 'lkLayer'; svg.setAttribute('aria-hidden', 'true'); document.body.append(svg);

  /** 開一條線。aid＝子 Agent 代號；from＝派工者角色；to＝同事角色（可以給函式，之後才知道是誰也可以） */
  K.open = (aid, from, to) => {
    if (!aid || !from || !gateOn()) return false;
    let x = K.map.get(aid);
    if (x && !x.ending) { x.from = from; x.to = to || x.to; return true; }
    if (x) x.g.remove();
    const g = document.createElementNS(NS, 'g'); g.dataset.aid = aid;
    const halo = document.createElementNS(NS, 'path'); halo.setAttribute('class', 'halo');
    const p = document.createElementNS(NS, 'path'), a = document.createElementNS(NS, 'circle'), b = document.createElementNS(NS, 'circle');
    a.setAttribute('r', '4'); b.setAttribute('r', '4');
    g.append(halo, p, a, b); svg.append(g);
    x = { aid, from, to, g, halo, p, a, b, ending: 0, born: Date.now() };
    K.map.set(aid, x); K.nOpen++;
    return true;
  };
  K.close = aid => {
    const x = K.map.get(aid); if (!x || x.ending) return false;
    x.ending = Date.now(); x.g.classList.add('end'); K.nClose++;
    setTimeout(() => { if (K.map.get(aid) === x) { K.map.delete(aid); x.g.remove(); } }, K.fadeMs + 200);
    return true;
  };
  K.reset = () => { for (const x of K.map.values()) x.g.remove(); K.map.clear(); };
  K.state = () => [...K.map.values()].map(x => ({ aid: x.aid, from: x.from && x.from.spec && x.from.spec.id, to: (typeof x.to === 'function' ? x.to() : x.to) && (typeof x.to === 'function' ? x.to() : x.to).spec.id, ending: !!x.ending, drawn: x.p.getAttribute('d') ? true : false, op: getComputedStyle(x.p).opacity }));

  const v = new THREE.Vector3();
  const scr = (c, r) => {
    const o = c && c.object3D; if (!o || !o.visible || !o.parent) return null;
    o.getWorldPosition(v); v.y += (c.height || 1.2) * 0.62; v.project(W.camera);
    if (v.z >= 1) return null;
    return [r.left + (v.x + 1) / 2 * r.width, r.top + (1 - v.y) / 2 * r.height];
  };
  function frame() {
    requestAnimationFrame(frame);
    if (!K.map.size || !W.camera || !W.renderer) return;
    if (!gateOn()) { K.reset(); return; }
    const r = W.renderer.domElement.getBoundingClientRect();
    for (const x of K.map.values()) {
      const to = typeof x.to === 'function' ? x.to() : x.to;
      const A = scr(x.from, r), B = scr(to, r);
      if (!A || !B) { x.g.style.display = 'none'; continue; }
      x.g.style.display = '';
      const dx = B[0] - A[0], dy = B[1] - A[1], d = Math.hypot(dx, dy) || 1, bend = Math.min(90, d * 0.28);
      const mx = (A[0] + B[0]) / 2 - dy / d * bend * 0.35, my = (A[1] + B[1]) / 2 - bend;   // 往上拱的柔和弧線
      const path = `M${A[0].toFixed(1)} ${A[1].toFixed(1)} Q${mx.toFixed(1)} ${my.toFixed(1)} ${B[0].toFixed(1)} ${B[1].toFixed(1)}`;
      x.p.setAttribute('d', path); x.halo.setAttribute('d', path);
      x.a.setAttribute('cx', A[0].toFixed(1)); x.a.setAttribute('cy', A[1].toFixed(1)); x.b.setAttribute('cx', B[0].toFixed(1)); x.b.setAttribute('cy', B[1].toFixed(1));
    }
  }
  requestAnimationFrame(frame);
  return K;
}
