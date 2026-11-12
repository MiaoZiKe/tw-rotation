// 動作：全部是程序式姿勢函式（時間 → 姿勢），動作之間用平滑混合過渡。
// 手臂可用「手腕目標點」解兩節骨反向運動（插口袋、抱胸、托下巴、舉手、鼓掌都靠它），腿用角度＋腳底貼地修正。
// 耳朵、尾巴、觸角、呆毛、馬尾、識別證由彈簧跟著身體晃。
import { THREE, clamp, lerp, sstep, softMat, ellipsoid, limbGeo } from './core.js';
import { makeSymbol } from './fx.js';

const { sin, cos, abs, max, min, PI } = Math;
const KEYS = ['rootX', 'rootY', 'rootZ', 'rootRX', 'rootRY', 'rootRZ', 'sq', 'gfix', 'hipsX', 'hipsY', 'hipsRX', 'hipsRY', 'hipsRZ', 'spRX', 'spRY', 'spRZ', 'spB', 'hdRX', 'hdRY', 'hdRZ',
  'aLsw', 'aLab', 'aLin', 'eL', 'eLtw', 'hLrx', 'hLry', 'hLrz', 'fcL', 'ikL', 'tLx', 'tLy', 'tLz', 'pLx', 'pLy', 'pLz',
  'aRsw', 'aRab', 'aRin', 'eR', 'eRtw', 'hRrx', 'hRry', 'hRrz', 'fcR', 'ikR', 'tRx', 'tRy', 'tRz', 'pRx', 'pRy', 'pRz',
  'lLsw', 'lLab', 'lLtw', 'kL', 'fL', 'lRsw', 'lRab', 'lRtw', 'kR', 'fR', 'tail', 'mouth', 'speed',
  'sAnger', 'sQ', 'sEx', 'sSpark', 'sBulb', 'sDrop', 'sHeart', 'sNote', 'puff', 'dizzy', 'bubble', 'burst', 'conf', 'glove', 'slam',
  'pDesk', 'pTable', 'pTablet', 'pGlass', 'pBook', 'pPen', 'pCarrot', 'ft', 'fp', 'nose'];
const P = (o = {}) => { const p = {}; for (const k of KEYS) p[k] = 0; p.gfix = 1; p.aLab = p.aRab = 0.2; p.eL = p.eR = 0.28; p.fcL = p.fcR = 0.35; p.lLtw = p.lRtw = 0.16;
  p.tLx = p.tRx = 0.21; p.tLy = p.tRy = -0.04; p.tLz = p.tRz = 0.04; p.pLx = p.pRx = 1; p.pLy = p.pRy = -0.2; p.pLz = p.pRz = -0.8; p.expr = 'neutral'; return Object.assign(p, o); };
const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const win = (t, a, b, f = 0.15) => sstep(a - f, a + f, t) * (1 - sstep(b - f, b + f, t)); // 時間窗（柔邊）
const look = (t) => sin(t * 0.55) * sstep(0.2, 0.9, sin(t * 0.37 + 2)) + 0.6 * sin(t * 0.23 + 1) * sstep(0.5, 1, sin(t * 0.31));
const talkM = (t, sp = 1) => clamp((0.55 + 0.45 * sin(t * 13 * sp)) * (0.45 + 0.55 * abs(sin(t * 3.1 * sp + 0.6))) * sstep(-0.2, 0.2, sin(t * 0.9 + 0.5) + 0.75));
// 手腕目標（軀幹座標，x 為「往外側」；pole 是手肘偏好的方向）
const hand = (p, k, t, pole, fc, w = 1) => { p['ik' + k] = w; p['t' + k + 'x'] = t[0]; p['t' + k + 'y'] = t[1]; p['t' + k + 'z'] = t[2]; if (pole) { p['p' + k + 'x'] = pole[0]; p['p' + k + 'y'] = pole[1]; p['p' + k + 'z'] = pole[2]; } if (fc !== undefined) p['fc' + k] = fc; };
const ARM = {
  pocket: (p, k) => { hand(p, k, [0.122, 0.006, 0.07], [1, 0.25, -1], 0.9); },
  hip: (p, k) => { hand(p, k, [0.168, 0.005, 0.03], [1, 0.1, -0.75], 0.85); p['h' + k + 'rx'] = 0.5; },
  clasp: (p, k) => { hand(p, k, k === 'L' ? [0.028, 0.03, 0.145] : [0.024, 0.02, 0.158], [1, -0.25, -0.35], 0.55); },
  hang: (p, k) => { p['ik' + k] = 0; },
  cross: (p, k) => { hand(p, k, k === 'L' ? [-0.1, 0.175, 0.115] : [-0.1, 0.148, 0.14], [1, -0.85, 0.1], 0.6); },
};
const IDLE_ARMS = { pocket: ['pocket', 'pocket'], clasp: ['clasp', 'clasp'], hip: ['hang', 'hip'], one: ['pocket', 'hang'] };

export const ACTIONS = {
  idle(t, c) { // 重心放一腳、另一腳往前外擺、歪頭
    const b = sin(t * 2.1), sw = sin(t * 0.7), p = P(), g = c.spec.ghost;
    p.spB = 0.012 * b; p.hipsRZ = -0.075 + 0.012 * sw; p.hipsX = -0.02; p.spRZ = 0.1 - 0.02 * sw; p.spRY = 0.1 + 0.05 * look(t - 0.3); p.hipsRY = -0.12;
    p.hdRZ = 0.12 + 0.035 * sin(t * 0.9 + 1); p.hdRY = -0.06 + 0.2 * look(t); p.hdRX = -0.01 + 0.025 * sin(t * 1.15);
    p.lLsw = 0.2; p.lLab = 0.17; p.lLtw = 0.5; p.kL = 0.26 + 0.03 * b; p.fL = 0.05; p.lRab = 0.03; p.lRtw = 0.1; p.kR = 0.03; p.lRsw = -0.02;
    const [l, r] = IDLE_ARMS[c.spec.idle || 'pocket']; ARM[l](p, 'L'); ARM[r](p, 'R');
    p.aLsw = 0.05 + 0.03 * sw; p.aRsw = 0.05 - 0.03 * sw; p.aLab = p.aRab = 0.2 + 0.02 * b; p.tail = 0.35 * sin(t * 1.6);
    if (g) { p.hipsRZ = 0.02 * sw; p.spRZ = 0.03 * sw; p.hipsX = 0; p.hipsRY = 0; }
    return p;
  },
  walk(t, c) {
    const w = t * (2 * PI / 0.72), s = sin(w), co = cos(w), p = P({ speed: 0.95 });
    p.lLsw = 0.5 * s; p.lRsw = -0.5 * s; p.kL = 0.1 + 0.8 * max(0, co) ** 1.3; p.kR = 0.1 + 0.8 * max(0, -co) ** 1.3;
    p.fL = -0.3 * max(0, s) + 0.3 * max(0, co); p.fR = -0.3 * max(0, -s) + 0.3 * max(0, -co); p.lLtw = p.lRtw = 0.1;
    p.hipsY = 0.018 * cos(2 * w + 0.4); p.hipsRZ = 0.045 * s; p.hipsRY = 0.13 * s; p.spRY = -0.22 * s; p.spRX = 0.05; p.spRZ = -0.04 * s;
    p.aLsw = -0.55 * s; p.aRsw = 0.55 * s; p.aLab = p.aRab = 0.17; p.eL = 0.3 + 0.3 * max(0, -s); p.eR = 0.3 + 0.3 * max(0, s);
    p.hdRZ = -0.035 * s; p.hdRX = 0.02 * cos(2 * w); p.hdRY = 0.1 * s + 0.1 * look(t); p.tail = 0.3 * s; p.spB = 0.008 * cos(2 * w);
    if (c.spec.ghost) { p.spRX = 0.16; p.hipsY = 0.03 * sin(t * 3); p.rootRZ = 0.04 * sin(t * 3); }
    return p;
  },
  run(t, c) {
    const w = t * (2 * PI / 0.44), s = sin(w), co = cos(w), p = P({ speed: 2.6, expr: 'happy' });
    p.lLsw = 0.85 * s + 0.12; p.lRsw = -0.85 * s + 0.12; p.kL = 0.25 + 1.3 * max(0, co) ** 1.2; p.kR = 0.25 + 1.3 * max(0, -co) ** 1.2;
    p.fL = -0.4 * max(0, s) + 0.5 * max(0, co); p.fR = -0.4 * max(0, -s) + 0.5 * max(0, -co); p.lLtw = p.lRtw = 0.05;
    p.gfix = 0.0; p.hipsY = -0.03 + 0.07 * abs(sin(w + 0.5)); p.hipsRZ = 0.06 * s; p.hipsRY = 0.2 * s; p.spRY = -0.3 * s; p.spRX = 0.24; p.hdRX = -0.14 + 0.03 * cos(2 * w);
    p.aLsw = -0.95 * s + 0.1; p.aRsw = 0.95 * s + 0.1; p.aLab = p.aRab = 0.2; p.eL = 1.35 + 0.2 * s; p.eR = 1.35 - 0.2 * s; p.fcL = p.fcR = 0.9; p.hdRZ = -0.05 * s; p.tail = 0.4 * s; p.mouth = 0.4; p.sq = 0.03 * cos(2 * w + 1);
    if (c.spec.ghost) { p.spRX = 0.5; p.hdRX = -0.4; p.hipsY = 0.04 * sin(t * 6); p.aLsw = p.aRsw = -0.9; p.eL = p.eR = 0.2; p.aLab = p.aRab = 0.5; }
    return p;
  },
  type(t, c) { // 坐在椅子上打電腦
    const p = P({ gfix: 0, pDesk: 1 }), g = c.spec.ghost;
    p.hipsY = (g ? 0.5 : 0.405) / c.S - c.HIP; p.lLsw = p.lRsw = 1.42; p.kL = 1.36 + 0.14 * sin(t * 2.6); p.kR = 1.36 + 0.14 * sin(t * 2.6 + 2.4); p.lLab = p.lRab = 0.05; p.lLtw = p.lRtw = 0.05; p.fL = p.fR = 0.0;
    const burst = sstep(-0.3, 0.1, sin(t * 0.8 + 0.4)), lk = win(t % 7.5, 5.6, 6.9, 0.25);
    p.spRX = 0.16 - 0.05 * lk; p.spB = 0.012 * sin(t * 2.3); p.spRY = 0.03 * sin(t * 0.7);
    const tapL = max(0, sin(t * 17)) ** 2 * burst, tapR = max(0, sin(t * 17 + 2.2)) ** 2 * burst;
    hand(p, 'L', [0.07 + 0.03 * sin(t * 2.9), 0.135 + 0.02 * tapL, 0.3], [1, -0.6, -0.4], 0.3 + 0.2 * tapL);
    hand(p, 'R', [0.07 + 0.03 * sin(t * 2.3 + 1), 0.135 + 0.02 * tapR, 0.3], [1, -0.6, -0.4], 0.3 + 0.2 * tapR);
    p.hLrx = -0.5 + 0.3 * tapL; p.hRrx = -0.5 + 0.3 * tapR; p.hLry = p.hRry = 1.3;
    p.hdRX = 0.16 - 0.22 * lk + 0.015 * sin(t * 6) * burst; p.hdRY = 0.08 * sin(t * 1.1) * (1 - lk) + 0.5 * lk; p.hdRZ = 0.04 * sin(t * 0.7) + 0.1 * lk;
    p.expr = lk > 0.5 ? 'happy' : 'neutral'; p.sNote = lk; p.tail = 0.25 * sin(t * 1.3);
    return p;
  },
  talk(t, c) { // 講話：右手比劃、偶爾雙手攤開
    const p = ACTIONS.idle(t, c), g = sin(t * 2.6), em = sstep(-0.2, 0.2, sin(t * 0.9 + 0.5) + 0.75);
    p.mouth = talkM(t); p.bubble = 1; p.hipsRY = 0; p.spRY = 0.1 * sin(t * 0.7);
    hand(p, 'R', [0.17 + 0.05 * sin(t * 1.3), 0.2 + 0.05 * g * em, 0.2 + 0.03 * sin(t * 2.6 + 1)], [1, -0.7, -0.1], 0.15); p.hRrx = -0.3 + 0.3 * sin(t * 5.2); p.hRry = 1.2;
    const l2 = win(t % 6, 2.6, 5, 0.3); if (c.spec.idle !== 'pocket' || true) { const tx = lerp(p.tLx, 0.19, l2), ty = lerp(p.tLy, 0.19 + 0.04 * sin(t * 2.6 + 2), l2), tz = lerp(p.tLz, 0.19, l2); hand(p, 'L', [tx, ty, tz], [1, lerp(p.pLy, -0.7, l2), lerp(p.pLz, -0.1, l2)], lerp(p.fcL, 0.15, l2), max(p.ikL, l2)); p.hLry = 1.2 * l2; }
    p.hdRX = 0.05 * sin(t * 5.2) * em - 0.03; p.hdRZ = 0.08 * sin(t * 1.1); p.hdRY = 0.14 * sin(t * 0.7); p.spRX = 0.03 + 0.03 * g; p.hipsY += 0.008 * abs(g) * em;
    p.expr = (t % 6) > 4.4 ? 'happy' : 'neutral';
    return p;
  },
  hit(t, c) { // 卡通式被打：拳套飛來 → 彈飛轉圈冒星星 → 落地暈眩 → 甩頭站起來
    const T = 4.6, u = t % T, p = P({ gfix: 0 }), g = c.spec.ghost;
    const gl = u < 0.5 ? ease(u / 0.42) : 1 - ease((u - 0.5) / 0.5); p.glove = u < 1.0 ? gl : 0;
    const tI = 0.42; // 擊中時刻
    if (u < tI) { const a = ease(u / tI); Object.assign(p, ACTIONS.idle(t, c)); p.gfix = 1; p.expr = u > 0.12 ? 'surprised' : 'neutral'; p.sEx = sstep(0.1, 0.25, u); p.hdRY = -0.5 * a; p.spRX = -0.06 * a; p.ikL = p.ikR = 1 - a; p.aLab = p.aRab = 0.3 + 0.6 * a; p.glove = gl; return p; }
    const fl = 0.95, f = (u - tI) / fl, sitY0 = g ? -0.2 : -(c.HIP - 0.1); // 飛行
    if (f < 1) {
      p.rootY = 1.3 * 4 * f * (1 - f) + 0.02; p.rootX = 1.0 * ease(f) ** 0.8; p.rootRZ = -(2 * PI) * ease(f); p.rootRY = 0.6 * f;
      p.sq = 0.16 * sin(min(1, f * 7) * PI / 2) * (1 - f) * cos(f * 9); p.aLab = p.aRab = 1.5; p.aLsw = p.aRsw = 0.2 + 0.3 * sin(f * 20); p.lLsw = 0.5 + 0.4 * sin(f * 18); p.lRsw = 0.5 - 0.4 * sin(f * 18); p.lLab = p.lRab = 0.3; p.kL = p.kR = 0.5; p.fcL = p.fcR = 0;
      const ld = sstep(0.55, 1, f); p.hipsY = sitY0 * ld; p.lLsw = lerp(p.lLsw, 1.5, ld); p.lRsw = lerp(p.lRsw, 1.5, ld); p.lLab = p.lRab = lerp(0.3, 0.26, ld); p.kL = p.kR = lerp(0.5, 0.1, ld); p.fL = p.fR = -0.3 * ld; p.spRX = -0.12 * ld; p.aLab = p.aRab = lerp(1.5, 0.5, ld); p.aLsw = lerp(p.aLsw, -0.45, ld); p.aRsw = lerp(p.aRsw, -0.45, ld); p.eL = p.eR = lerp(0.28, 0.2, ld);
      p.expr = 'surprised'; p.mouth = 1; p.burst = clamp(f * 1.25); return p;
    }
    const d = u - tI - fl; // 落地後
    const bounce = max(0, 1 - d / 0.5), up = sstep(2.55, 3.05, d);
    p.rootX = 1.0 * (1 - ease((d - 2.6) / 0.6)); p.rootY = 0.12 * abs(sin(d * 11)) * bounce + 0.3 * sin(PI * clamp((d - 2.6) / 0.6));
    p.sq = -0.2 * bounce * cos(d * 14); p.rootRY = 0.6 * (1 - up);
    p.hipsY = sitY0 * (1 - up); p.lLsw = p.lRsw = 1.5 * (1 - up); p.lLab = p.lRab = 0.26 * (1 - up); p.kL = p.kR = 0.1; p.fL = p.fR = -0.3 * (1 - up);
    const dz = win(d, 0.15, 2.0, 0.2); p.dizzy = dz; p.hdRX = 0.14 * sin(d * 5.2) * dz; p.hdRZ = 0.16 * cos(d * 5.2) * dz; p.spRZ = 0.08 * sin(d * 5.2) * dz; p.spRX = -0.12 * (1 - up);
    p.aLab = p.aRab = 0.2 + 0.3 * (1 - up); p.aLsw = p.aRsw = -0.45 * (1 - up); p.eL = p.eR = 0.2; p.fcL = p.fcR = 0.1;
    const shake = win(d, 2.05, 2.55, 0.08); p.hdRY = 0.4 * sin(d * 30) * shake;
    p.expr = d < 2.05 ? 'dizzy' : d < 2.7 ? 'sad' : 'neutral'; p.gfix = up; p.sDrop = win(d, 2.1, 3.1, 0.15);
    return p;
  },
  celebrate(t, c) { // 跳起來雙手高舉，每三下轉一圈
    const T = 1.15, n = Math.floor(t / T), u = (t % T) / T, p = P({ gfix: 0, expr: 'happy', mouth: 0.7 });
    const cr = sstep(0, 0.18, u) * (1 - sstep(0.18, 0.3, u)) + sstep(0.7, 0.8, u) * (1 - sstep(0.82, 1, u)), air = clamp((u - 0.22) / 0.52), ar = sin(PI * air);
    const jy = 0.42 * 4 * air * (1 - air); p.rootY = jy;
    p.hipsY = -0.07 * cr; p.kL = p.kR = 0.15 + 0.8 * cr + 0.6 * ar; p.lLsw = p.lRsw = 0.4 * cr + 0.3 * ar; p.lLab = p.lRab = 0.08 + 0.2 * ar; p.spRX = 0.2 * cr - 0.08 * ar;
    p.sq = -0.08 * cr + 0.06 * ar; p.gfix = 1 - sstep(0, 0.04, jy);
    const upA = sstep(0.1, 0.3, u) * (1 - sstep(0.78, 1, u));
    for (const [k, ph] of [['L', 0], ['R', 2]]) { hand(p, k, [lerp(0.24, 0.3 + 0.05 * sin(t * 16 + ph), upA), lerp(0.22, 0.74, upA), lerp(0.14, 0.0, upA)], [1, -0.3, -0.4], lerp(0.8, 0.05, upA)); p['h' + k + 'rz'] = 0.3 * sin(t * 16 + ph) * upA; }
    p.hdRX = -0.14 * upA; p.hdRZ = 0.1 * sin(t * 5.4); p.rootRY = n % 3 === 2 ? 2 * PI * ease(air) : 0; p.conf = (t % (T * 3)) / (T * 3); p.sHeart = n % 3 === 1 ? sin(PI * u) : 0; p.tail = 0.6 * sin(t * 10);
    return p;
  },
  argue(t, c) { // 爭執：比手畫腳大聲說 → 拍桌 → 雙手抱胸別過頭「哼」
    const T = 5.2, u = (t + (c.phase || 0)) % T, tt = t + (c.phase || 0), p = P({ expr: 'angry' });
    const A = max(win(u, 0.0, 1.9, 0.14), win(u - T, 0.0, 1.9, 0.14)), B = win(u, 1.9, 2.75, 0.1), Cc = max(win(u, 2.75, 5.2, 0.16), win(u + T, 2.75, 5.2, 0.16)), b = sin(tt * 2.3);
    // A 比手畫腳：右手往前指、左手握拳在旁邊抖
    const jab = sin(tt * 8.5), a = P();
    a.spRX = 0.2 + 0.05 * jab; a.hdRX = -0.04 + 0.07 * jab; a.hdRZ = 0.05 * sin(tt * 4); a.mouth = talkM(tt, 1.25) * 0.9 + 0.1;
    hand(a, 'R', [0.08, 0.31 + 0.02 * jab, 0.27 + 0.05 * max(0, jab)], [1, -0.6, -0.2], 0.8); a.hRrx = -0.2;
    hand(a, 'L', [0.2 + 0.02 * sin(tt * 17), 0.2 + 0.03 * sin(tt * 8.5 + 1), 0.13], [1, -0.4, -0.5], 1);
    a.hipsY = 0.012 * abs(jab); a.lRsw = 0.25 * max(0, sin(tt * 4.25)); a.kR = 0.5 * max(0, sin(tt * 4.25)); a.lLab = a.lRab = 0.08;
    // B 拍桌：雙手高舉 → 重重拍下
    const s = clamp((u - 1.9) / 0.38), hitT = u - 2.3, down = sstep(-0.07, 0.07, hitT), bm = P();
    for (const k of ['L', 'R']) hand(bm, k, [lerp(0.17, 0.12, down), lerp(0.22 + 0.36 * ease(s), 0.1, down), lerp(0.12, 0.27, down)], [1, lerp(0, -0.5, down), -0.4], 0.05);
    bm.hLrx = bm.hRrx = -1.0 * down; bm.hLry = bm.hRry = 1.4 * down;
    bm.spRX = lerp(-0.14 * ease(s), 0.36, down) + 0.03 * sin(hitT * 40) * max(0, 1 - hitT * 3) * down; bm.hdRX = lerp(-0.2 * s, -0.24, down); bm.mouth = 0.9; bm.sq = -0.07 * down * max(0, 1 - hitT * 5) * (hitT > 0 ? 1 : 0); bm.hipsY = -0.02 * down; bm.lLab = bm.lRab = 0.1;
    // C 抱胸、別過頭、搖頭、腳尖點地
    const cm = P(), sh = win(u, 3.5, 4.5, 0.15);
    ARM.cross(cm, 'L'); ARM.cross(cm, 'R');
    cm.spRY = 0.42; cm.hdRY = 0.36 + 0.3 * sin(tt * 9) * sh; cm.hdRX = -0.16; cm.hdRZ = -0.06; cm.spRX = -0.07; cm.hipsRZ = 0.03; cm.lLab = 0.1; cm.spB = 0.02 * b; cm.mouth = 0;
    cm.fR = -0.4 * max(0, sin(tt * 7)); cm.lRsw = 0.12; cm.lRtw = 0.4;
    const ws = [A, B, Cc], ps = [a, bm, cm], sum = A + B + Cc || 1;
    for (const k of KEYS) { let v = 0; for (let i = 0; i < 3; i++) v += ps[i][k] * ws[i]; p[k] = v / sum; }
    p.pTable = c.noTable ? 0 : 1; p.gfix = 1; p.slam = hitT > 0 && hitT < 0.9 ? hitT / 0.9 : 0;
    p.sAnger = 0.7 + 0.3 * A + 0.3 * B; p.puff = 0.5 + 0.5 * Cc; p.tail = 0.9 * sin(tt * 9);
    return p;
  },
  research(t, c) { // 查資料：左手平板、右手放大鏡，找到答案時亮燈泡
    const T = 6.4, u = t % T, p = ACTIONS.idle(t, c), found = win(u, 4.5, 6.0, 0.18), sc = sin(t * 1.5);
    p.pTablet = 1; p.pGlass = 1; p.hipsRY = 0; p.spRY = 0.05;
    hand(p, 'L', [0.085, 0.1, 0.2], [1, -0.7, -0.2], 0.45); p.hLry = 1.3; p.hLrx = -0.2;
    hand(p, 'R', [lerp(0.06 + 0.05 * sc, 0.2, found), lerp(0.2 + 0.015 * sin(t * 3), 0.52, found), lerp(0.23, 0.1, found)], [1, lerp(-0.7, -0.1, found), lerp(-0.1, -0.5, found)], 0.85); p.hRrx = lerp(-0.5, 0, found);
    p.hdRX = lerp(0.24 + 0.03 * sin(t * 3), -0.12, found); p.hdRY = lerp(0.08 + 0.12 * sc, 0, found); p.hdRZ = lerp(-0.1, 0.06, found); p.spRX = lerp(0.08, -0.02, found);
    p.expr = found > 0.5 ? 'happy' : 'think'; p.mouth = found * 0.6; p.sQ = win(u, 0.8, 4.2, 0.25); p.sBulb = found; p.rootY = 0.08 * abs(sin((u - 4.5) * 7)) * win(u, 4.5, 5.4, 0.1); p.gfix = 1 - win(u, 4.4, 5.5, 0.1);
    return p;
  },
  notes(t, c) { // 做筆記：左手筆記本、右手鉛筆寫字，偶爾抬頭看發言的人、點頭
    const T = 5.6, u = t % T, p = ACTIONS.idle(t, c), up = win(u, 3.6, 5.1, 0.2), wr = 1 - up, side = (Math.floor(t / T) % 2 ? 1 : -1) * (c.lookAmp ?? 0.35);
    p.pBook = 1; p.pPen = 1; p.hipsRY = 0;
    hand(p, 'L', [0.075, 0.1, 0.2], [1, -0.7, -0.2], 0.45); p.hLry = 1.3; p.hLrx = -0.2;
    hand(p, 'R', [0.0 + 0.03 * sin(t * 2.2) * wr + 0.004 * sin(t * 19) * wr, 0.15 + 0.004 * sin(t * 23) * wr, 0.225], [1, -0.7, -0.1], 0.8); p.hRrx = -0.3 + 0.12 * sin(t * 21) * wr;
    p.hdRX = lerp(0.24, -0.04 + 0.1 * max(0, sin((u - 3.9) * 9)), up); p.hdRY = lerp(0.08, side, up); p.hdRZ = lerp(-0.06, 0.05, up); p.spRX = 0.07; p.spRY = lerp(0.04, side * 0.3, up);
    p.expr = up > 0.5 ? 'neutral' : 'think'; p.tail = 0.3 * sin(t * 1.4);
    return p;
  },
  think(t, c) { // 思考：右手托下巴、左手托右肘、歪頭、腳尖點地
    const p = ACTIONS.idle(t, c); p.expr = 'think'; p.hipsRY = 0; p.spRY = 0.05;
    hand(p, 'R', [0.03, 0.305 + 0.004 * sin(t * 2), 0.205], [0.5, -1, 0.35], 0.7); p.hRrx = -0.35;
    hand(p, 'L', [-0.075, 0.115, 0.135], [1, -0.5, -0.1], 0.6);
    p.hdRZ = -0.14 + 0.03 * sin(t * 1.2); p.hdRX = 0.02; p.hdRY = 0.12 + 0.08 * sin(t * 0.6); p.spRZ = 0.03; p.sQ = 0.6 + 0.4 * sin(t * 2); p.fL = -0.35 * max(0, sin(t * 6)); p.tail = 0.5 * sin(t * 2.4);
    return p;
  },
  smug(t, c) { // 得意：雙手叉腰、抬下巴、身體微微後仰晃
    const p = ACTIONS.idle(t, c); p.expr = 'smug'; p.hipsRY = 0;
    ARM.hip(p, 'L'); ARM.hip(p, 'R'); p.lLsw = 0.05; p.lLab = 0.14; p.lRab = 0.1; p.kL = 0.05; p.hipsRZ = 0; p.hipsX = 0; p.spRZ = 0;
    p.spRX = -0.12; p.hdRX = -0.2; p.hdRZ = 0.08 * sin(t * 2.2); p.spRY = 0.14 * sin(t * 1.1); p.hipsY = 0.012 * abs(sin(t * 4.4)); p.sSpark = 1; p.mouth = 0.5 * win(t % 3, 1.6, 2.6, 0.2); p.tail = 0.8 * sin(t * 3);
    return p;
  },
  cross(t, c) { // 抱胸：雙手交叉在胸前、重心放一腳、微微點頭打量
    const p = ACTIONS.idle(t, c); ARM.cross(p, 'L'); ARM.cross(p, 'R'); p.spRX = -0.05; p.hdRX = 0.03 + 0.05 * max(0, sin(t * 1.6)) ** 3; p.hdRZ = -0.08; p.expr = (t % 5) > 3.2 ? 'smug' : 'neutral'; p.fL = -0.3 * max(0, sin(t * 5)) * win(t % 5, 0.5, 2.5, 0.2);
    return p;
  },
  raise(t, c) { // 舉手：右手高舉揮動、踮腳、「我我我！」
    const p = ACTIONS.idle(t, c), wv = sin(t * 9), hop = abs(sin(t * 4.5));
    hand(p, 'R', [0.34 + 0.07 * wv, 0.74, 0.03], [1, 0.1, -0.5], 0.0); p.hRrz = 0.35 * wv; p.hRry = 1.2;
    ARM.hang(p, 'L'); p.aLab = 0.3; p.aLsw = -0.1; p.eL = 0.5; p.fcL = 0.8;
    p.hipsRZ = 0; p.hipsX = 0; p.hipsRY = 0; p.spRZ = -0.1; p.spRY = 0; p.lLsw = 0; p.lLab = 0.06; p.lLtw = 0.2; p.kL = 0.05; p.fL = p.fR = 0.45 * hop; p.hipsY = 0.0; p.rootY = 0.012 * hop;
    p.hdRX = -0.1; p.hdRZ = -0.12; p.hdRY = 0; p.expr = 'happy'; p.mouth = 0.5 + 0.3 * sin(t * 6); p.sEx = win(t % 3, 0.2, 1.4, 0.15);
    return p;
  },
  clap(t, c) { // 鼓掌：雙手在胸前拍，身體跟著點
    const p = ACTIONS.idle(t, c), ph = t * 9.5, op = 0.5 - 0.5 * cos(ph), hitK = max(0, cos(ph)) ** 6;
    for (const k of ['L', 'R']) { hand(p, k, [0.062 + 0.07 * op, 0.2 + (k === 'L' ? 0.008 : 0), 0.19], [1, -0.9, -0.25], 0.0); p['h' + k + 'rx'] = -0.2; p['h' + k + 'rz'] = -0.35; }
    p.hipsRZ = 0; p.hipsX = 0; p.hipsRY = 0; p.spRZ = 0; p.spRY = 0.05 * sin(t * 1.2); p.lLsw = 0.02; p.lLab = 0.07; p.lLtw = 0.2; p.kL = 0.06;
    p.hipsY = -0.012 * hitK; p.spRX = 0.04 + 0.02 * hitK; p.hdRX = 0.03 * hitK - 0.03; p.hdRZ = 0.07 * sin(t * 2.4); p.expr = 'happy'; p.mouth = 0.45; p.sSpark = 0.8; p.sNote = win(t % 4, 2, 3.5, 0.2);
    return p;
  },
};
export const ACTION_LIST = [['idle', '待機'], ['walk', '走路'], ['run', '跑步'], ['type', '打電腦'], ['talk', '講話'], ['research', '查資料'], ['notes', '做筆記'], ['argue', '爭執'], ['think', '思考'], ['smug', '得意'], ['cross', '抱胸'], ['raise', '舉手'], ['clap', '鼓掌'], ['hit', '被打'], ['celebrate', '慶祝']];

// 寵物版動作
const PET = {
  idle(t) { const b = sin(t * 3.2), p = P({ gfix: 0 }); p.spB = 0.03 * b; p.nose = sin(t * 9) * sstep(0.2, 0.8, sin(t * 0.9)); p.spRY = 0.25 * look(t); p.spRZ = 0.04 * sin(t * 0.8); return p; },
  walk(t) { const w = t * 11, p = P({ gfix: 0, speed: 0.45 }); p.ft = 1; p.fp = w; p.hipsY = 0.012 * abs(sin(w)); p.spRZ = 0.07 * sin(w); p.spRY = 0.08 * sin(w); p.spRX = 0.03 * sin(2 * w); p.nose = sin(t * 9); return p; },
  run(t) { const w = t * 17, h = abs(sin(w * 0.5)), p = P({ gfix: 0, speed: 1.5, expr: 'happy' }); p.ft = 1.6; p.fp = w; p.rootY = 0.09 * h; p.spRX = -0.25 * cos(w); p.sq = 0.12 * (h - 0.5); return p; },
  type(t) { const p = PET.idle(t); p.pCarrot = 1; p.mouth = abs(sin(t * 15)); p.spRX = 0.12 + 0.03 * sin(t * 15); p.spRY = 0; p.nose = sin(t * 15); p.sHeart = win(t % 5, 3.5, 4.6, 0.2); return p; },
  talk(t) { const p = PET.idle(t), m = talkM(t, 1.2); p.mouth = m; p.spRX = -0.22 * m; p.sq = 0.06 * m; p.sNote = 1; return p; },
  research(t) { const p = PET.walk(t * 0.5); p.spRX = 0.2; p.nose = sin(t * 14); p.spRY = 0.5 * sin(t * 1.3); p.sQ = 1; p.speed = 0; return p; },
  notes(t) { const p = PET.idle(t); p.spRY = 0.5 * sin(t * 0.9); p.spRZ = 0.12 * sin(t * 0.9); return p; },
  argue(t) { const p = PET.idle(t), h = abs(sin(t * 9)); p.rootY = 0.03 * h; p.sq = 0.1 + 0.05 * h; p.mouth = talkM(t, 1.4); p.sAnger = 1; p.spRX = -0.12; return p; },
  think(t) { const p = PET.idle(t); p.spRZ = 0.22; p.sQ = 1; return p; },
  smug(t) { const p = PET.idle(t); p.spRX = -0.25; p.sSpark = 1; p.sq = 0.05; return p; },
  hit(t) { const u = t % 2.6, p = PET.idle(t); const f = clamp((u - 0.3) / 0.7); p.sEx = win(u, 0.2, 1.2, 0.1); if (u > 0.3 && f < 1) { p.rootY = 0.42 * 4 * f * (1 - f); p.rootRY = 2 * PI * ease(f); p.sq = 0.15 * sin(PI * f); } p.sq += -0.2 * max(0, 1 - abs(u - 1.05) * 6); return p; },
  cross(t) { const p = PET.idle(t); p.spRX = -0.12; p.spRZ = 0.1; return p; },
  raise(t) { const p = PET.idle(t), h = abs(sin(t * 4.5)); p.rootY = 0.06 * h; p.spRX = -0.3; p.sEx = 1; p.sq = 0.08 * h; return p; },
  clap(t) { const p = PET.idle(t), h = abs(sin(t * 9.5)); p.rootY = 0.03 * h; p.sq = 0.08 * (h - 0.5); p.sHeart = 1; p.ft = 1; p.fp = t * 19; return p; },
  celebrate(t) { const u = (t % 0.7) / 0.7, n = Math.floor(t / 0.7), p = P({ gfix: 0 }); const a = clamp((u - 0.15) / 0.7); p.rootY = 0.3 * 4 * a * (1 - a); p.sq = u < 0.15 ? -0.2 * sin(u / 0.15 * PI / 2) : 0.14 * sin(PI * a) - 0.15 * max(0, (u - 0.85) / 0.15); p.rootRZ = (n % 2 ? 1 : -1) * 0.35 * sin(PI * a); p.rootRY = n % 4 === 3 ? 2 * PI * ease(a) : 0; p.sHeart = 1; p.ft = 1; p.fp = t * 20; return p; },
};

// ───────── 特效：飛散星星、彩帶、拳套 ─────────
function attachFx(ch) {
  const root = ch.root;
  ch.burst = Array.from({ length: 9 }, (_, i) => { const s = makeSymbol(i % 3 === 2 ? 'spark' : 'star', 0.16); root.add(s); return s; });
  const cols = [0xffb3c7, 0x9ad0ff, 0xffe08a, 0xb9f0c9, 0xd9c2ff, 0xffc9a3];
  const geo = new THREE.PlaneGeometry(0.05, 0.03);
  ch.conf = Array.from({ length: 44 }, (_, i) => { const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: cols[i % 6], side: THREE.DoubleSide })); m.visible = false; root.add(m); m.userData = { a: i * 2.399, r: 0.25 + ((i * 37) % 60) / 100, v: 1.6 + ((i * 53) % 70) / 70, d: ((i * 17) % 40) / 100 }; return m; });
  const g = ch.glove = new THREE.Group(); root.add(g); g.visible = false;
  const gm = softMat('#ff8a9a'); const b = new THREE.Mesh(ellipsoid(0.15, 0.14, 0.13), gm); g.add(b);
  const th = new THREE.Mesh(ellipsoid(0.06, 0.07, 0.06, { w: 20, h: 14 }), gm); th.position.set(0.04, 0.1, 0.08); g.add(th);
  const cuff = new THREE.Mesh(limbGeo(0.085, 0.07), softMat('#fff6ea')); cuff.rotation.z = -PI / 2; cuff.position.x = -0.13; g.add(cuff);
  const arm = new THREE.Mesh(limbGeo(0.03, 1.2), softMat('#d9d4e6')); arm.rotation.z = -PI / 2; arm.position.x = -0.24; g.add(arm);
}

const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _qe = new THREE.Quaternion(), _qe2 = new THREE.Quaternion(), _e = new THREE.Euler(), _c = new THREE.Vector3(), _v = new THREE.Vector3();
const _T = new THREE.Vector3(), _E = new THREE.Vector3(), _pp = new THREE.Vector3(), _X = new THREE.Vector3(), _Y = new THREE.Vector3(), _Z = new THREE.Vector3(), _f = new THREE.Vector3(), _m = new THREE.Matrix4(), _XA = new THREE.Vector3(1, 0, 0);
export class Animator {
  constructor(ch) { this.ch = ch; this.name = 'idle'; this.t = 0; this.w = 1; this.fade = 0.35; this.from = null; this.out = P(); this.clock = Math.random() * 10; this.blinkT = 1 + Math.random() * 3; this.blink = 0; this.exprOverride = null; this.symW = {}; attachFx(ch); }
  play(name, fade = 0.38) { if (name === this.name) return; this.from = { ...this.out }; this.name = name; this.t = 0; this.w = 0; this.fade = name === 'hit' ? 0.15 : fade; }
  update(dt) {
    const ch = this.ch; this.t += dt; this.clock += dt;
    const tbl = ch.pet ? PET : ACTIONS; let p = (tbl[this.name] || tbl.idle)(this.t, ch);
    if (this.w < 1 && this.from) { this.w = min(1, this.w + dt / this.fade); const k = ease(this.w), f = this.from; for (const key of KEYS) p[key] = lerp(f[key], p[key], k); }
    this.out = p; let expr = p.expr;
    if (this.exprOverride) { // 手動指定表情時，附上對應的頭上符號
      expr = this.exprOverride; const o = { angry: ['sAnger', 'puff'], surprised: ['sEx'], think: ['sQ'], smug: ['sSpark'], sad: ['sDrop'], happy: ['sNote'] }[expr] || [];
      for (const k of ['sAnger', 'sQ', 'sEx', 'sSpark', 'sBulb', 'sDrop', 'sHeart', 'sNote', 'puff']) p[k] = o.includes(k) ? 1 : 0;
    }
    if (ch.debug) Object.assign(p, ch.debug);
    ch.pet ? this.applyPet(p, dt) : this.apply(p, dt);
    // 眨眼
    this.blinkT -= dt; if (this.blinkT < 0) { this.blinkT = 2.2 + ((this.clock * 7.3) % 3); this.blinkC = 0.16; if ((this.clock * 3.1) % 1 > 0.75) this.blinkT = 0.3; }
    if (this.blinkC > 0) { this.blinkC -= dt; this.blink = sin(clamp(1 - this.blinkC / 0.16) * PI); } else this.blink = 0;
    if (ch.face) { Object.assign(ch.face.s, { expr, mouth: p.mouth, blink: this.blink, t: this.clock, lx: clamp(-(p.hdRY + p.spRY + p.hipsRY) * 0.9, -1, 1) * (expr === 'neutral' || expr === 'happy' ? 1 : 0), ly: 0 }); ch.face.update(dt); }
    else if (ch.n.eyes) { const sy = expr === 'happy' ? 0.45 : 1 - 0.9 * this.blink; for (const e of ch.n.eyes) e.scale.y = sy; }
    ch.root.updateMatrixWorld(true);
    const sub = Math.max(1, Math.round(dt / (1 / 120))); for (let i = 0; i < sub; i++) for (const s of ch.springs) s.step(dt / sub);
    this.fx(p, dt);
  }
  // 手臂：角度式與目標點式兩種解，依權重混合
  arm(k, s, p) {
    const n = this.ch.n, arm = n['arm' + k], elb = n['elb' + k], w = p['ik' + k];
    if (!arm.userData.L1) Object.assign(arm.userData, { L1: -elb.position.y, L2: -n['hand' + k].position.y, y0: arm.position.y, x0: arm.position.x });
    arm.scale.y = 1; n['hand' + k].scale.y = 1; arm.position.set(arm.userData.x0, arm.userData.y0, arm.position.z);
    _e.set(-p['a' + k + 'sw'], -s * p['a' + k + 'in'], s * p['a' + k + 'ab'], 'YZX'); _q.setFromEuler(_e);
    _e.set(-p['e' + k], -s * p['e' + k + 'tw'], 0, 'YXZ'); _qe.setFromEuler(_e);
    if (w > 0.001) {
      // 目標在肩膀上方時聳肩；搆不到時手臂卡通式拉長（最多 1.3 倍）
      const sh = w * 0.045 * sstep(0.3, 0.6, p['t' + k + 'y']); arm.position.y = arm.userData.y0 + sh; arm.position.x = arm.userData.x0 - s * sh * 0.3;
      _T.set(s * p['t' + k + 'x'], p['t' + k + 'y'], p['t' + k + 'z']).sub(arm.position); const len = _T.length(), base = arm.userData.L1 + arm.userData.L2, st = lerp(1, clamp(len / (base - 0.004), 1, 1.3), w);
      const L1 = arm.userData.L1 * st, L2 = arm.userData.L2 * st; arm.scale.y = st; n['hand' + k].scale.y = 1 / st;
      const d = clamp(len, 0.03, L1 + L2 - 0.003); _T.normalize();
      const a = (L1 * L1 - L2 * L2 + d * d) / (2 * d), h = Math.sqrt(max(0, L1 * L1 - a * a));
      _pp.set(s * p['p' + k + 'x'], p['p' + k + 'y'], p['p' + k + 'z']); _pp.addScaledVector(_T, -_pp.dot(_T)); if (_pp.lengthSq() < 1e-6) _pp.set(s, 0, 0).addScaledVector(_T, -s * _T.x); _pp.normalize();
      _E.copy(_T).multiplyScalar(a).addScaledVector(_pp, h); _Y.copy(_E).normalize().negate();
      _f.copy(_T).multiplyScalar(d).sub(_E).normalize(); _Z.copy(_f).addScaledVector(_Y, -_f.dot(_Y)); if (_Z.lengthSq() < 1e-6) _Z.copy(_pp).negate(); _Z.normalize(); _X.crossVectors(_Y, _Z);
      _m.makeBasis(_X, _Y, _Z); _q2.setFromRotationMatrix(_m); _qe2.setFromAxisAngle(_XA, -Math.acos(clamp(-_f.dot(_Y), -1, 1)));
      _q.slerp(_q2, w); _qe.slerp(_qe2, w);
    }
    arm.quaternion.copy(_q); elb.quaternion.copy(_qe);
    n['hand' + k].rotation.set(p['h' + k + 'rx'], s * p['h' + k + 'ry'], s * p['h' + k + 'rz'], 'YXZ'); n['hm' + k].userData.curl(clamp(p['fc' + k]));
  }
  apply(p, dt) {
    const ch = this.ch, n = ch.n, rig = ch.rig;
    _e.set(p.rootRX, p.rootRY, p.rootRZ, 'YXZ'); _q.setFromEuler(_e); rig.quaternion.copy(_q);
    _c.set(0, 0.75, 0); _v.copy(_c).applyQuaternion(_q); rig.position.set(p.rootX / ch.S + _c.x - _v.x, p.rootY / ch.S + _c.y - _v.y, p.rootZ / ch.S + _c.z - _v.z);
    rig.scale.set(1 - p.sq * 0.5, 1 + p.sq, 1 - p.sq * 0.5);
    const hover = ch.spec.ghost ? 0.035 * sin(this.clock * 2.1) : 0;
    n.hips.position.set(p.hipsX, ch.HIP + p.hipsY + hover, 0); n.hips.rotation.set(p.hipsRX, p.hipsRY, p.hipsRZ);
    n.spine.rotation.set(p.spRX, p.spRY, p.spRZ); n.spine.scale.set(1 - p.spB * 0.3, 1 + p.spB, 1 + p.spB * 0.6);
    n.head.rotation.set(p.hdRX, p.hdRY, p.hdRZ, 'YXZ');
    this.arm('L', 1, p); this.arm('R', -1, p);
    for (const [s, k] of [[1, 'L'], [-1, 'R']]) if (n['leg' + k]) { n['leg' + k].rotation.set(-p['l' + k + 'sw'], s * p['l' + k + 'tw'], s * p['l' + k + 'ab']); n['knee' + k].rotation.x = p['k' + k]; n['foot' + k].rotation.x = p['f' + k]; }
    if (n.tail) n.tail.rotation.z = p.tail * 0.5;
    if (n.gtail) { n.gtail.rotation.x = 0.1 * sin(this.clock * 1.7) - 0.5 * p.spRX; n.gtail.rotation.z = 0.06 * sin(this.clock * 1.3); }
    if (p.gfix > 0.001 && n.footL) { // 腳貼地：取兩腳鞋底最低點，把整個人移到剛好踩在地上
      ch.root.updateMatrixWorld(true); let lo = 1e9;
      for (const f of [n.footL, n.footR]) for (const z of [-0.096, 0.05, 0.192]) { _v.set(0, -0.113, z).applyMatrix4(f.matrixWorld); lo = min(lo, _v.y); }
      ch.root.getWorldPosition(_v); rig.position.y -= p.gfix * (lo - _v.y) / ch.S;
    }
    const pr = ch.props, show = (o, w) => { if (!o) return; o.visible = w > 0.02; if (o.visible) { const k = ease(w), s0 = o.userData.s0 || 1; o.scale.set(s0 * k, s0 * k, s0 * k); } };
    show(pr.desk, p.pDesk); show(pr.table, p.pTable); show(pr.tablet, p.pTablet); show(pr.glass, p.pGlass); show(pr.book, p.pBook); show(pr.pen, p.pPen);
    if (pr.desk.visible) ch.screen.draw(this.clock);
    if (pr.book.visible) ch.noteTex.draw(this.clock);
    if (pr.table.visible) { const s = p.slam, j = s > 0 ? abs(sin(s * 14)) * (1 - s) ** 2 : 0; pr.paper.position.y = 0.407 + 0.09 * j; pr.paper.rotation.y = 0.5 * j; pr.tmug.position.y = 0.405 + 0.06 * j; pr.tmug.rotation.z = 0.25 * j * sin(s * 30); }
  }
  applyPet(p, dt) {
    const ch = this.ch, n = ch.n, rig = ch.rig;
    rig.position.set(p.rootX, p.rootY, p.rootZ); rig.rotation.set(p.rootRX, p.rootRY, p.rootRZ);
    n.hips.position.y = 0.165 + p.hipsY; n.hips.scale.set(1 - p.sq * 0.5 + p.spB * 0.4, 1 + p.sq + p.spB, 1 - p.sq * 0.5);
    n.spine.rotation.set(p.spRX, p.spRY, p.spRZ);
    n.feet.forEach((f, i) => { const ph = p.fp + (i === 0 || i === 3 ? 0 : PI); f.position.z = f.userData.z + p.ft * 0.045 * sin(ph); f.position.y = 0.022 + p.ft * 0.03 * max(0, cos(ph)); });
    n.nose.scale.setScalar(1 + 0.18 * p.nose); n.nose.position.y = n.nose.userData.y ?? (n.nose.userData.y = n.nose.position.y); n.nose.position.y += 0.004 * p.nose;
    n.mouth.scale.set(1 + 0.4 * p.mouth, 0.5 + 2 * p.mouth, 1);
    const car = ch.props.carrot; car.visible = p.pCarrot > 0.02; car.scale.setScalar(0.62 * ease(p.pCarrot));
  }
  fx(p, dt) {
    const ch = this.ch, t = this.clock, S = ch.pet ? 0.6 : 1.25;
    const place = { sAnger: ['anger', 0.3, 0.02, 0.24, (w) => 1 + 0.22 * sin(t * 11)], sQ: ['q', 0.3, 0.08, 0.24, () => 1], sEx: ['ex', 0.0, 0.14, 0.26, () => 1 + 0.1 * sin(t * 18)], sSpark: ['spark', -0.3, 0.02, 0.2, () => 0.75 + 0.35 * abs(sin(t * 4))],
      sBulb: ['bulb', 0, 0.16, 0.26, () => 1 + 0.06 * sin(t * 10)], sDrop: ['drop', 0.32, -0.12, 0.17, () => 1], sHeart: ['heart', 0.26, 0.08, 0.2, () => 1 + 0.15 * sin(t * 8)], sNote: ['note', 0.3, 0.06, 0.2, () => 1] };
    for (const k in place) {
      const [name, x, y, size, pulse] = place[k], s = ch.sym[name], w = clamp(p[k]); s.visible = w > 0.03; if (!s.visible) continue;
      const pop = w < 1 ? ease(w) * (1 + 0.35 * sin(w * PI)) : 1; s.scale.setScalar(size * S * pop * pulse(w));
      s.position.set(x * S, y * S + (k === 'sDrop' ? -0.05 * ((t * 0.8) % 1) : k === 'sNote' || k === 'sHeart' ? 0.03 * sin(t * 3) : 0.012 * sin(t * 4)), 0.1 * S);
      if (k === 'sQ') s.material.rotation = 0.2 * sin(t * 2.2); if (k === 'sNote') s.material.rotation = 0.25 * sin(t * 3); if (k === 'sSpark') s.material.rotation = t * 1.5;
    }
    if (ch.sym.spark.visible && !ch.spark2) { ch.spark2 = makeSymbol('spark', 0.12); ch.symAnchor.add(ch.spark2); }
    if (ch.spark2) { ch.spark2.visible = ch.sym.spark.visible; ch.spark2.position.set(0.34 * S, -0.1 * S, 0.1); ch.spark2.scale.setScalar(0.13 * S * (0.6 + 0.4 * abs(sin(t * 4 + 1.5)))); ch.spark2.material.rotation = -t * 1.2; }
    ch.puffs.forEach((s, i) => { const w = clamp(p.puff), u = (t * 0.9 + i / 3) % 1; s.visible = w > 0.03; s.position.set((i - 1) * 0.2 + 0.05 * sin(u * 6 + i), -0.02 + u * 0.3, 0); s.scale.setScalar(w * (0.1 + 0.16 * u)); s.material.opacity = (1 - u) * 0.95; });
    ch.dizzy.forEach((s, i) => { const w = clamp(p.dizzy), a = t * 4.5 + i * 2.094; s.visible = w > 0.03; s.position.set(cos(a) * 0.3 * S, -0.06 * S + 0.03 * sin(a * 2), sin(a) * 0.3 * S); s.scale.setScalar(0.13 * S * ease(w)); s.material.rotation = a; });
    if (ch.bubble) { const w = clamp(p.bubble); ch.bubble.visible = w > 0.03; ch.bubble.position.set(0.36, 0.06, 0.1); ch.bubble.scale.setScalar(0.3 * ease(w) * (1 + 0.03 * sin(t * 6)));
      ch.bdots.forEach((d, i) => { d.visible = ch.bubble.visible; const j = max(0, sin(t * 6 - i * 0.9)); d.position.set(0.36 - 0.062 + i * 0.062, 0.074 + 0.022 * j, 0.11); d.scale.setScalar(0.042 * ease(w)); }); }
    // 被打飛時四散的星星
    const b = p.burst; ch.burst.forEach((s, i) => { s.visible = b > 0.02 && b < 0.98; if (!s.visible) return; const a = i / 9 * PI * 2 + 0.3, r = 0.25 + 0.75 * (1 - (1 - b) ** 2); s.position.set(-0.05 + cos(a) * r * 1.2, 0.95 + sin(a) * r - 0.3 * b * b, 0.35 + 0.1 * sin(i * 3)); s.scale.setScalar((0.2 - 0.03 * (i % 3)) * sin(PI * min(1, b * 1.1)) ** 0.6); s.material.rotation = b * 5 + i; s.material.opacity = 1; });
    const cf = p.conf; ch.conf.forEach((m) => { const d = m.userData, u = cf * 3.2 - d.d * 2; m.visible = cf > 0.01 && u > 0 && u < 2.6; if (!m.visible) return; const x = cos(d.a) * d.r * min(1, u * 1.6), z = sin(d.a) * d.r * min(1, u * 1.6); m.position.set(x * 1.5, 1.5 + d.v * u - 0.85 * u * u, z * 1.5); if (m.position.y < 0.01) m.visible = false; m.rotation.set(u * 7 + d.a, u * 5, d.a); });
    const gl = p.glove; ch.glove.visible = gl > 0.01; if (ch.glove.visible) { ch.glove.position.set(lerp(-2.0, -0.5, gl), ch.pet ? 0.2 : 1.2 * ch.S, 0.08); ch.glove.scale.setScalar(1 + 0.25 * max(0, gl - 0.85) * 6); }
  }
}
