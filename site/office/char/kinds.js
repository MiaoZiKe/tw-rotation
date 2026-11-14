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

// 各物種的個性檔覆寫（疊在 profiles/mochi.json 上）：只列有差異的鍵（gait 這層是逐鍵合併，walk／run 整組換掉）
// 步態（2026-11-14 走路改版）：擁有者說「並沒有改善移動」——改版前腳藏在肚子下、抬腳 3 公分、身體彈跳在腳 IK 之後才套（著地腳被帶離地 3～4 公分＝浮著滑）。
//   · 垂垂：雙腳同步「小跳步」（sync 0，站立期蹲＋壓扁、騰空拋物線、耳朵甩），跑步是大跳；騰空高度與騰空時間大致合乎重力（h ≈ g·t²/8）。
//   · 布布：Q 彈小碎步（左右搖擺大、每步落地壓扁回彈）。
//   · 糰糰：小短腿、頭耳慢半拍、微晃。
//   kick 擺動後段腳往前踢出的距離（落地前收回落腳點，著地期不受影響）；style.rock 每步前後點頭。
//   每一組：stride 步幅（公尺，[慢, 快]）、duty 著地比例、lift 抬腳高度、liftPeak 抬腳最高點在擺動期的位置、style 見 controller.gaitStyle。
//   maxStretch 腿皮膚最多拉長倍數（卡通腿）；bobReach 身體起伏讓落腳可及半徑少算的量。
const GAIT = {
  mochi: { maxStretch: 1.4, bobReach: 0.03,
    walk: { vmax: 0.62, stride: [0.16, 0.26], duty: 0.58, lift: 0.06, liftPeak: 0.66, kick: 0.07, style: { type: 'alt', bob: 0.03, sq: 0.4, st: 0.25, rock: 0.05, sway: 0.1, shift: 0.012, lean: 0.0, spineLean: 0.05, head: 0.05, headRoll: 0.06, lag: 0.14, ear: 0.12, earSide: 0.07, tail: 0.3 } },
    run: { vmax: 1.35, stride: [0.32, 0.48], duty: 0.38, lift: 0.08, liftPeak: 0.62, kick: 0.06, style: { type: 'alt', bob: 0.04, sq: 0.5, st: 0.32, rock: 0.06, sway: 0.08, shift: 0.008, lean: -0.06, spineLean: 0.1, head: 0.06, headRoll: 0.04, lag: 0.12, ear: 0.18, earSide: 0.05, tail: 0.3 } } },
  bunny: { maxStretch: 1.4, bobReach: 0.02,
    walk: { vmax: 0.62, stride: [0.22, 0.32], duty: 0.42, sync: 0, lift: 0.075, liftPeak: 0.5, style: { type: 'hop', bob: 0.085, crouch: 0.016, sq: 0.55, st: 0.4, lean: 0.04, pitch: 0.08, ear: 0.28, earTip: 0.22, tail: 0.25, head: 0.06, arm: 0.3 } },
    run: { vmax: 1.4, stride: [0.42, 0.62], duty: 0.3, sync: 0, lift: 0.115, liftPeak: 0.5, style: { type: 'hop', bob: 0.1, crouch: 0.018, sq: 0.6, st: 0.45, lean: 0.12, pitch: 0.12, ear: 0.42, earTip: 0.3, tail: 0.3, head: 0.08, arm: 0.55 } } },
  pudding: { maxStretch: 1.45, bobReach: 0.035,
    walk: { vmax: 0.52, stride: [0.13, 0.2], duty: 0.55, lift: 0.065, liftPeak: 0.64, kick: 0.03, style: { type: 'alt', bob: 0.028, rock: 0.05, sq: 0.45, st: 0.26, sway: 0.15, shift: 0.016, lean: -0.025, spineLean: 0.05, head: 0.03, headRoll: 0.06, lag: 0.12 } },
    run: { vmax: 1.2, stride: [0.26, 0.4], duty: 0.38, lift: 0.08, liftPeak: 0.62, kick: 0.035, style: { type: 'alt', bob: 0.04, rock: 0.06, sq: 0.55, st: 0.36, sway: 0.1, shift: 0.01, lean: -0.17, spineLean: 0.2, head: 0.04, headRoll: 0.05, lag: 0.1 } } },
};
export const PROFILE_OVERRIDE = {
  mochi: { gait: GAIT.mochi },
  bunny: { waddle: 0.05, jump: { height: 0.78 }, move: { walk: 0.62, run: 1.4 }, secondary_gain: 1.35, gait: GAIT.bunny },
  pudding: { waddle: 0.10, land: { peakK: 0.1, zeta: 0.28 }, move: { walk: 0.52, run: 1.2 }, gait: GAIT.pudding },
};
export function mergeProfile(base, ov) {
  const out = JSON.parse(JSON.stringify(base)); if (!ov) return out; ov = JSON.parse(JSON.stringify(ov));
  for (const [k, v] of Object.entries(ov)) { if (k === 'secondary_gain') { for (const s of out.secondary) s.gain *= v; continue; } if (v && typeof v === 'object' && !Array.isArray(v) && out[k] && typeof out[k] === 'object') Object.assign(out[k], v); else out[k] = v; }
  return out;
}
/** 辦公室用的個性檔：走路／跑步速度與步幅依「世界速度」放大 k 倍（距離與步幅同比放大，步頻不變；腳的可及範圍由腳 IK 夾住）。 */
export function officeProfile(base, k = 1.5) {
  const P = JSON.parse(JSON.stringify(base)); const M = P.move; M.walk *= k; M.run *= k * 1.6; M.accel *= k; M.decel *= k;
  for (const g of [P.gait.walk, P.gait.run]) { g.vmax *= (g === P.gait.run ? k * 1.6 : k); g.stride = g.stride.map(x => x * Math.min(k, 1.25)); g.lift *= Math.min(k, 1.2); }
  P.gait.walk.vmax *= 1; return P;
}

// 舊的「事後彈跳」（2026-11-14 前）：在腳 IK 之後才把整個 root 往上推，著地腳被一起帶離地面＝浮著滑。已改由 controller.gaitStyle 在 IK 之前處理；
// 這個函式保留成空殼，避免舊呼叫端出錯。
export function applyBounce() { }
