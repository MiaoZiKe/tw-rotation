// 新做法（Blender 參數化一體成形網格）的物種設定：哪些物種已換新模型、每個物種的材質預設、尺寸、能戴哪些配件、個性檔覆寫。
// 其餘物種仍走 play/ 的舊系統（兩套並存）。
import * as THREE from 'three';
import { resolveSpec } from '../play/species.js';

export const NEW_KINDS = {
  mochi: { preset: 'fur', rad: 0.31, walkK: 1.0, can: ['glasses', 'hat', 'crown', 'bow', 'tie', 'badge', 'scarf'] },
  bunny: { preset: 'fur', rad: 0.26, walkK: 1.0, can: ['glasses', 'hat', 'crown', 'bow', 'tie', 'badge', 'scarf'], hatY: 0.0 },
  pudding: { preset: 'matte', rad: 0.29, walkK: 1.0, can: ['glasses', 'bow', 'tie', 'badge'], cherry: true },
};
export const isNew = (id) => !!NEW_KINDS[id];

/** 依個體規格取顏色：本體色、頂色、區域色（布布的焦糖）、櫻桃色、配件色 */
export function colorsFor(look) {
  const rs = resolveSpec({ species: look.species, pal: look.pal, hue: look.hue, acc: look.acc, accColor: look.accColor, seed: look.seed });
  const p = rs.pal; return { color: p.body, top: p.top, zone: p.cap ?? (look.species === 'bunny' ? 0xffffff : null), zone2: look.species === 'pudding' ? 0xfff6ea : null, cherry: p.ch ?? 0xff5f6e, acc: rs.accColor, pal: p, accWorn: look.acc.filter(a => NEW_KINDS[look.species].can.includes(a)) };
}

// 各物種的個性檔覆寫（疊在 profiles/mochi.json 上）：只列有差異的鍵
export const PROFILE_OVERRIDE = {
  bunny: { waddle: 0.05, jump: { height: 0.78 }, move: { walk: 0.62, run: 1.4 }, secondary_gain: 1.35, bounce: { dy: 0.04, sq: 0.3, sway: 0.0 } },
  pudding: { waddle: 0.10, land: { peakK: 0.1, zeta: 0.28 }, move: { walk: 0.52, run: 1.2 }, bounce: { dy: 0.03, sq: 0.45, sway: 0.09 } },
};
export function mergeProfile(base, ov) {
  const out = JSON.parse(JSON.stringify(base)); if (!ov) return out;
  for (const [k, v] of Object.entries(ov)) { if (k === 'secondary_gain') { for (const s of out.secondary) s.gain *= v; continue; } if (v && typeof v === 'object' && !Array.isArray(v) && out[k] && typeof out[k] === 'object') Object.assign(out[k], v); else out[k] = v; }
  return out;
}
/** 辦公室用的個性檔：走路／跑步速度與步幅依「世界速度」放大 k 倍（距離與步幅同比放大，步頻不變；腳的可及範圍由腳 IK 夾住）。 */
export function officeProfile(base, k = 1.5) {
  const P = JSON.parse(JSON.stringify(base)); const M = P.move; M.walk *= k; M.run *= k * 1.6; M.accel *= k; M.decel *= k;
  for (const g of [P.gait.walk, P.gait.run]) { g.vmax *= (g === P.gait.run ? k * 1.6 : k); g.stride = g.stride.map(x => x * Math.min(k, 1.25)); g.lift *= Math.min(k, 1.2); }
  P.gait.walk.vmax *= 1; return P;
}

// 走路／跑步的 Q 彈：每步身體上下彈（dy 公尺）、落地擠壓／騰空拉長（sq）、左右搖晃（sway 弧度）。疊在控制器輸出之上（腳著地期的世界位置不受影響）。
import { CHANNELS } from './actions.js';
const _IX = Object.fromEntries(CHANNELS.map((n, i) => [n, i]));
export function applyBounce(ch, ctl, B) {
  if (!B || (ctl.state !== 'walk' && ctl.state !== 'run')) return; const p = ctl._p; if (!p) return;
  const u = ctl.feet.phase, w = (u * 2) % 1, bob = Math.sin(Math.PI * w), amp = ctl.gaitAmp, run = ctl.state === 'run' ? 1.4 : 1;
  ch.move('root', p[_IX['root.dx']], p[_IX['root.dy']] + B.dy * bob * amp * run, p[_IX['root.dz']]);
  if (B.sway) ch.rot('spine', p[_IX['spine.rx']], p[_IX['spine.ry']], p[_IX['spine.rz']] + B.sway * Math.sin(2 * Math.PI * u) * amp);   // 搖晃轉的是脊椎（腿在骨盆下面，不會被帶著滑）
  const land = Math.pow(1 - bob, 3) * amp, air = Math.pow(bob, 2) * amp;
  ch.morph('squash', Math.max(p[_IX['morph.squash']], B.sq * land)); ch.morph('stretch', Math.max(p[_IX['morph.stretch']], B.sq * 0.45 * air));
  ch.model.updateMatrixWorld(true);
}
