// 動作庫：每個動作是「時間 → 姿勢描述」的純函式，執行時驅動骨頭；換動作時由 Char 做球面內插過渡。
// 座標：+x 是角色的左手邊、+y 向上、+z 是角色面向。手臂方向以胸為準、腿以髖為準。
const S = Math.sin, C = Math.cos, PI = Math.PI;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ss = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const lerp = (a, b, t) => a + (b - a) * t;
const lv = (a, b, t) => a.map((v, i) => lerp(v, b[i], t));
const arm = (p, s, up, fore, hand, tw = 0) => { const k = s > 0 ? 'L' : 'R'; p['arm' + k] = { dir: [up[0] * s, up[1], up[2]] }; p['fore' + k] = { dir: [fore[0] * s, fore[1], fore[2]], twist: tw * s }; if (hand) p['hand' + k + '_'] = { dir: [hand[0] * s, hand[1], hand[2]] }; };
// 腿：a 大腿前擺角、k 膝蓋彎曲角、splay 外開、pitch 腳掌下壓
const leg = (p, s, a = 0, k = 0, splay = 0.13, pitch = 0) => { const n = s > 0 ? 'L' : 'R';
  p['leg' + n] = { dir: [s * splay, -C(a), S(a)] }; p['shin' + n] = { dir: [s * splay * 0.7, -C(a - k), S(a - k)] }; p['foot' + n + '_'] = { world: [pitch, 0, 0] }; };
const REST_ARM = [[0.25, -0.96, 0.03], [0.2, -0.95, 0.2]];

export const ACTIONS = {
  idle: { label: '待機', stand: true, fn(t) { const b = S(t * 1.7), p = { root: { y: -0.004 * (1 + b) }, spine: [0.01 * b, 0, 0], chest: [-0.03 * b, 0, 0], head: [0.03 * S(t * 0.8), 0.1 * S(t * 0.5), 0.02 * S(t * 0.37)], shoulderL: [0, 0, 0.03 * b], shoulderR: [0, 0, -0.03 * b] };
    for (const s of [1, -1]) { arm(p, s, [0.25 + 0.012 * b, -0.96, 0.03], REST_ARM[1]); leg(p, s); p['fingers' + (s > 0 ? 'L' : 'R')] = 0.3; } return { pose: p }; } },

  walk: { label: '走路', loco: 0.65 },

  run: { label: '跑步', loco: 1.9, face: { expr: 'neutral', mouth: 0.3 } },

  sit: { label: '坐下打字', prop: 'desk', fn(t, m) { const p = { root: { y: -m.sitDrop, z: -0.02 }, hips: [-0.04, 0, 0], spine: [0.07, 0, 0], chest: [0.07, 0, 0], neck: [0.05, 0, 0], head: [0.1 + 0.015 * S(t * 2.3), 0.05 * S(t * 0.6), 0] };
    for (const s of [1, -1]) { const n = s > 0 ? 'L' : 'R'; p['leg' + n] = { dir: [s * 0.2, -0.1, 1] }; p['shin' + n] = { dir: [s * 0.1, -1, 0.1] }; p['foot' + n + '_'] = { world: [0, 0, 0] };
      const tap = 0.05 * Math.max(0, S(t * 13 + (s > 0 ? 0 : 2.1))) + 0.02 * S(t * 3.1 + s);
      arm(p, s, [0.3, -0.82, 0.45], [-0.12 + 0.05 * S(t * 2.2 + s), -0.3 + tap, 1], [-0.1, -0.35 - tap, 1]); p['fingers' + n] = 0.35 + tap * 3; } return { pose: p, face: { expr: 'focus' } }; } },

  talk: { stand: true, label: '講話手勢', fn(t) { const g = S(t * 3.2), g2 = S(t * 3.2 + 1.4), p = { root: { y: -0.004 }, spine: [0.02, 0.04 * S(t * 1.1), 0], chest: [0.02, 0.06 * S(t * 1.1), 0.02 * g], head: [0.05 * S(t * 3.2), 0.12 * S(t * 1.1), 0.04 * g2] };
    arm(p, -1, [0.3, -0.82, 0.4], [0.3 + 0.12 * g, 0.25 + 0.3 * g, 0.9], [0.3, 0.6, 0.6]);
    arm(p, 1, [0.28, -0.9, 0.25], [0.3 + 0.1 * g2, -0.25 + 0.25 * g2, 0.9], [0.3, 0.2, 0.9]);
    p.fingersL = 0.2; p.fingersR = 0.15; leg(p, 1); leg(p, -1); return { pose: p, face: { expr: 'neutral', mouth: clamp(0.45 + 0.5 * S(t * 11) * S(t * 2.3 + 1)) } }; } },

  argue: { stand: true, label: '爭執', fn(t) { const sh = S(t * 11), c = Math.abs(S(t * 4.2)) ** 3, p = { root: { y: -0.02 - 0.015 * c, z: 0.02 }, hips: [0.05, 0, 0], spine: [0.1, -0.08, 0], chest: [0.1 + 0.04 * c, -0.1, 0], neck: [-0.05, 0, 0], head: [-0.08, 0.1 * sh, 0] , shoulderL: [0, 0, 0.12], shoulderR: [0, 0, -0.12] };
    arm(p, -1, [0.25, -0.15, 1], [0.1, 0.1 + 0.16 * sh, 1], [0, 0.05 + 0.1 * sh, 1]);          // 右手往前指
    arm(p, 1, [0.5, -0.55 - 0.2 * c, 0.5], lv([0.25, 0.9, 0.45], [0.05, -0.35, 1], c), lv([0.2, 0.9, 0.3], [0, -0.6, 0.8], c)); // 左手往下拍
    p.fingersR = { index: 0, rest: 1, thumb: 0.9 }; p.fingersL = 1; leg(p, 1, 0.22, 0.25, 0.2); leg(p, -1, -0.2, 0.05, 0.16, 0); return { pose: p, face: { expr: 'angry', mouth: clamp(0.5 + 0.5 * S(t * 12)) } }; } },

  note: { stand: true, label: '做筆記', prop: 'note', fn(t) { const p = { root: { y: -0.004 }, spine: [0.04, 0, 0], chest: [0.05, 0.05, 0], neck: [0.1, 0, 0], head: [0.2 + 0.02 * S(t * 1.3), 0.08 + 0.03 * S(t * 0.9), 0] };
    arm(p, 1, [0.3, -0.88, 0.32], [-0.5, 0.12, 0.85], [-0.75, 0.25, 0.5]);
    const wx = 0.04 * S(t * 12), wy = 0.02 * C(t * 7);
    arm(p, -1, [0.3, -0.86, 0.4], [-0.38 + wx, 0.02 + wy, 0.9], [-0.5 + wx, -0.5, 0.6]);
    p.fingersR = { thumb: 0.75, index: 0.7, rest: 0.95 }; p.fingersL = 0.3; leg(p, 1); leg(p, -1); return { pose: p, face: { expr: 'focus' } }; } },

  raise: { stand: true, label: '舉手', fn(t) { const b = S(t * 5), up = 0.5 + 0.5 * S(t * 2.5), p = { root: { y: 0.01 * up, x: 0.02 }, spine: [-0.02, 0, -0.07], chest: [-0.03, 0, -0.08], neck: [0, 0, -0.06], head: [-0.08, -0.06, -0.14], shoulderR: [0, 0, -0.5], shoulderL: [0, 0, -0.08] };
    arm(p, -1, [0.52, 0.85, 0.12], [0.1 + 0.08 * b, 1, 0.06], [0.02 + 0.3 * b, 1, 0.1]);
    arm(p, 1, REST_ARM[0], REST_ARM[1]); p.fingersR = 0; p.fingersL = 0.3; leg(p, 1); leg(p, -1); return { pose: p, face: { expr: 'neutral', mouth: 0.45 } }; } },

  clap: { stand: true, label: '鼓掌', fn(t) { const c = 0.5 + 0.5 * S(t * 15), p = { root: { y: -0.004 + 0.006 * c }, spine: [0.02, 0, 0], chest: [0.02, 0, 0.03 * S(t * 3)], head: [0.02, 0, 0.06 * S(t * 3)] };
    for (const s of [1, -1]) arm(p, s, [0.1 + 0.1 * c, -0.6, 0.8], [-0.78 + 0.4 * c, 0.4, 0.5], [-0.62 + 0.45 * c, 0.65, 0.45], 1.2);
    leg(p, 1); leg(p, -1); return { pose: p, face: { expr: 'happy' } }; } },

  cheer: { label: '慶祝', fn(t) { const j = Math.abs(S(t * 4.6)), g = 1 - j, wv = S(t * 9.2), p = { root: { y: 0.2 * j - 0.05 * g * g }, spine: [-0.05, 0, 0], chest: [-0.08, 0, 0.04 * wv], head: [-0.16, 0, 0.05 * wv], shoulderL: [0, 0, 0.4], shoulderR: [0, 0, -0.4] };
    for (const s of [1, -1]) { arm(p, s, [0.74, 0.66, 0.1], [0.34 + 0.14 * wv * s, 0.93, 0.06], [0.3 + 0.2 * wv * s, 0.95, 0.1]); p['fingers' + (s > 0 ? 'L' : 'R')] = 0; const k = 0.75 * g * g; leg(p, s, k * 0.5 + 0.12 * j, k + 0.5 * j, 0.14 + 0.1 * j, 0.5 * j); }
    return { pose: p, face: { expr: 'happy' } }; } },

  look: { stand: true, label: '轉頭看人', fn(t, m, o) { const a = (o && o.lookYaw != null ? o.lookYaw : 0.62 * S(t * 1.3)), p = { root: { y: -0.004 }, spine: [0, 0.08 * a, 0], chest: [0, 0.14 * a, 0], neck: [0, 0.32 * a, 0], head: [0.02, 0.46 * a, 0] };
    for (const s of [1, -1]) { arm(p, s, REST_ARM[0], REST_ARM[1]); p['fingers' + (s > 0 ? 'L' : 'R')] = 0.3; leg(p, s); } return { pose: p, face: { expr: 'neutral', look: [a * 0.9, 0] } }; } },

  hit: { label: '被打彈飛', loop: 3.2, fx: 'hit', fn(t, m) { t = t % 3.2; const p = {}; let face = { expr: 'surprised' };
    const lie = -1.22, fly = clamp((t - 0.1) / 0.85), up = ss((t - 1.9) / 0.8);
    let rx, y, z, sp = 0;
    if (t < 0.1) { const u = t / 0.1; rx = -0.45 * u; y = 0; z = -0.05 * u; sp = 0.2; }
    else if (t < 0.95) { rx = lerp(-0.45, lie - 2 * PI, fly ** 0.9); y = 1.0 * 4 * fly * (1 - fly) + lerp(0, -m.lieDrop, fly); z = lerp(-0.05, -1.5, fly); sp = 1; }
    else if (t < 1.9) { const u = t - 0.95, bn = Math.abs(S(u * 9)) * Math.exp(-u * 5); rx = lie - 2 * PI + 0.25 * bn; y = -m.lieDrop + 0.22 * bn; z = -1.5 - 0.25 * (1 - Math.exp(-u * 4)); sp = 0.7; face = { expr: 'dizzy', mouth: 0 }; }
    else { rx = lerp(lie, 0, up); y = lerp(-m.lieDrop, 0, up) + 0.1 * S(up * PI); z = lerp(-1.75, 0, ss((t - 2.1) / 1.0)); sp = 0.7 * (1 - up); face = { expr: up < 0.6 ? 'dizzy' : 'sad' }; }
    p.root = { rx, y, z }; const f = S(t * 22) * 0.15 * sp;
    p.spine = [-0.15 * sp, 0, 0]; p.chest = [-0.15 * sp, 0, 0]; p.head = [0.3 * sp * (t < 0.95 ? 1 : -0.2), 0.25 * S(t * 7) * (t > 2.4 ? (1 - ss((t - 2.8) / 0.4)) : 0), 0];
    for (const s of [1, -1]) { arm(p, s, lv(REST_ARM[0], [0.85, 0.35 + f, 0.4], sp), lv(REST_ARM[1], [0.7, 0.7 - f, 0.4], sp));
      const n = s > 0 ? 'L' : 'R', a = (0.75 + f * s) * sp, k = 0.5 * sp; p['leg' + n] = { dir: [s * (0.13 + 0.3 * sp), -C(a), S(a)] }; p['shin' + n] = { dir: [s * (0.1 + 0.25 * sp), -C(a - k), S(a - k)] }; }
    return { pose: p, face, stars: t > 0.95 && t < 2.5 ? 1 : 0, impact: t < 0.25 ? 1 - t / 0.25 : 0 }; } },
};
export const ACTION_ORDER = ['idle', 'walk', 'run', 'sit', 'talk', 'look', 'argue', 'note', 'raise', 'clap', 'cheer', 'hit'];
