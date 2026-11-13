// 動作資料（第三階段）：通道清單、步態循環表、一次型動作（五段）、待機小動作、各狀態的靜態姿勢。
// 全部是資料；控制器直譯，不在別處直接寫 transform。通道命名：骨頭名.軸（rx ry rz＝繞模型座標軸的旋轉，弧度；dx dy dz＝位移，公尺）、morph.形態鍵、eye.y／eye.p＝視線。
// 模型座標：X 往角色的左、Y 向上、Z 朝前。rx＋＝上半身前傾／鼻子向下；ry＋＝往左轉；rz＋＝左側抬高（L 側手臂往上）。
// L 手臂骨朝 +X：ry＋＝手往後；R 手臂骨朝 −X：ry＋＝手往前；耳朵骨朝上：rx＋＝往前、rz＋＝往 −X 傾；尾巴朝 −Z：ry＋＝往 −X 擺。

export const CHANNELS = [
  'root.dx', 'root.dy', 'root.dz', 'root.rx', 'root.ry', 'root.rz',
  'pelvis.rx', 'pelvis.ry', 'pelvis.rz', 'spine.rx', 'spine.ry', 'spine.rz', 'head.rx', 'head.ry', 'head.rz',
  'tail.rx', 'tail.ry', 'tail.rz', 'tail.tip.rx', 'tail.tip.ry', 'tail.tip.rz',
  'ear.L.rx', 'ear.L.rz', 'ear.R.rx', 'ear.R.rz', 'ear.tip.L.rx', 'ear.tip.L.rz', 'ear.tip.R.rx', 'ear.tip.R.rz',
  'arm.L.ry', 'arm.L.rz', 'arm.R.ry', 'arm.R.rz', 'hand.L.rz', 'hand.R.rz',
  'morph.squash', 'morph.stretch', 'morph.land', 'morph.plump', 'morph.breath', 'morph.cheek.L', 'morph.cheek.R',
  'eye.y', 'eye.p',
];

/** 步態循環表：m = 相位 − duty/2（左腳站立中點為 0，單位＝循環）。value = (base + amp·sin(2π(k·m + ph)))·lerp(n[0], n[1], 速度比)·(w ? 擺動係數 : 1)
 *  drv＝由即時訊號（wy 轉向角速度、n 速度比、speed）驅動的通道（分段線性）。 */
export const CYCLES = {
  walk: {
    terms: [
      { ch: 'root.dx', amp: 0.022, k: 1, ph: 0.25, n: [0.4, 1], w: 1 },            // 重心左右移向站立腳
      { ch: 'root.rz', amp: -0.085, k: 1, ph: 0.25, n: [0.4, 1], w: 1 },           // 頂部倒向站立腳（企鵝式左右晃）
      { ch: 'root.ry', amp: 0.055, k: 1, ph: 0.25, n: [0.4, 1], w: 1 },            // 擺動腳那側稍向前
      { ch: 'root.dy', base: 0.009, amp: 0.006, k: 2, ph: 0.25, n: [0.5, 1] },     // 站立中點最高、雙腳著地最低
      { ch: 'root.rx', base: 0.025, n: [0.4, 1.2] },                              // 前傾
      { ch: 'head.rz', amp: 0.04, k: 1, ph: 0.25, n: [0.4, 1], w: 1 },             // 頭比身體穩
      { ch: 'head.rx', amp: 0.03, k: 2, ph: 0.4, n: [0.5, 1] },
      { ch: 'head.ry', amp: 0.05, k: 1, ph: 0.0, n: [0.5, 1] },
      { ch: 'morph.squash', base: 0.05, amp: 0.05, k: 2, ph: 0.75, n: [0.4, 1] }, // 每步一次輕微壓扁（雙腳著地時）
      { ch: 'arm.L.ry', amp: 0.38, k: 1, ph: 0.0, n: [0.5, 1] },
      { ch: 'arm.R.ry', amp: -0.38, k: 1, ph: 0.0, n: [0.5, 1] },
      { ch: 'arm.L.rz', base: 0.12 }, { ch: 'arm.R.rz', base: -0.12 },
      { ch: 'tail.ry', amp: 0.36, k: 1, ph: 0.5, n: [0.5, 1] },
      { ch: 'tail.tip.ry', amp: 0.22, k: 1, ph: 0.65, n: [0.5, 1] },
    ],
    drv: [
      { ch: 'root.rz', src: 'wy', map: [[-7, 0.1], [0, 0], [7, -0.1]] },            // 轉彎時身體往內傾
    ],
    expr: 'smile',
  },
  run: {
    terms: [
      { ch: 'root.dx', amp: 0.012, k: 1, ph: 0.25, n: [0.5, 1], w: 1 },
      { ch: 'root.rz', amp: -0.06, k: 1, ph: 0.25, n: [0.5, 1], w: 1 },
      { ch: 'root.ry', amp: 0.075, k: 1, ph: 0.25, n: [0.5, 1], w: 1 },
      { ch: 'root.dy', base: 0.011, amp: -0.007, k: 2, ph: 0.25 },                  // 站立中點最低、騰空最高
      { ch: 'root.rx', base: 0.17, n: [0.5, 1] },
      { ch: 'head.rx', base: -0.09, amp: 0.04, k: 2, ph: 0.4 },
      { ch: 'head.rz', amp: 0.03, k: 1, ph: 0.25, w: 1 },
      { ch: 'morph.squash', base: 0.07, amp: 0.1, k: 2, ph: 0.75 },                 // 著地壓扁、騰空拉長
      { ch: 'morph.stretch', base: 0.09, amp: 0.1, k: 2, ph: 0.25 },
      { ch: 'arm.L.ry', base: 0.15, amp: 0.8, k: 1, ph: 0.0 },
      { ch: 'arm.R.ry', base: -0.15, amp: -0.8, k: 1, ph: 0.0 },
      { ch: 'arm.L.rz', base: 0.28 }, { ch: 'arm.R.rz', base: -0.28 },
      { ch: 'tail.ry', amp: 0.3, k: 1, ph: 0.5 },
      { ch: 'tail.rx', base: -0.25 },
      { ch: 'ear.L.rx', base: -0.3 }, { ch: 'ear.R.rx', base: -0.3 },
    ],
    drv: [
      { ch: 'root.rz', src: 'wy', map: [[-7, 0.16], [0, 0], [7, -0.16]] },
    ],
    expr: 'smile',
  },
};

/** 一次型動作：五段（start 起始姿態、pre 預備、main 主動作、settle 緩衝收尾、out 回到待機）。
 *  每段 d＝秒（或 until＝由控制器事件結束）；to＝這一段結束時的姿勢（沒寫的通道＝回到 0）；e＝緩動。
 *  段與段之間的起點永遠是「目前實際輸出的姿勢」，所以接不上、跳幀是構造上不可能的。 */
export const CLIPS = {
  jump: [
    { n: 'start', d: 0.03, to: { 'morph.squash': 0.12 } },
    { n: 'pre', d: 0.10, e: 'in2', to: { 'morph.squash': 0.62, 'root.rx': 0.07, 'head.rx': 0.1, 'arm.L.ry': 0.55, 'arm.R.ry': -0.55, 'ear.L.rx': -0.3, 'ear.R.rx': -0.3, 'tail.rx': 0.2 } },
  ],
  land: [
    { n: 'start', d: 0.0, to: { 'root.rx': 0.05, 'head.rx': 0.08, 'arm.L.rz': 0.35, 'arm.R.rz': -0.35, 'ear.L.rx': 0.12, 'ear.R.rx': 0.12 } },
    { n: 'settle', d: 0.26, e: 'out2', to: { 'arm.L.rz': 0.2, 'arm.R.rz': -0.2, 'head.rx': 0.03, 'root.rx': 0.02 } },
    { n: 'out', d: 0.22, e: 'io', to: {} },
  ],
  riseHop: [
    { n: 'start', d: 0.02, to: { 'morph.squash': 0.12 } },
    { n: 'pre', d: 0.11, e: 'in2', to: { 'morph.squash': 0.5, 'root.rx': 0.08, 'head.rx': 0.08, 'arm.L.ry': 0.5, 'arm.R.ry': -0.5, 'ear.L.rx': -0.25, 'ear.R.rx': -0.25 } },
  ],
  sleepIn: [
    { n: 'start', d: 0.1, to: { 'morph.squash': 0.08 } },
    { n: 'pre', d: 0.5, e: 'io', to: { 'morph.squash': 0.3, 'head.rx': 0.2, 'root.rx': 0.06, 'ear.L.rx': -0.15, 'ear.R.rx': -0.15 } },
    { n: 'main', d: 0.9, e: 'io', to: { 'morph.squash': 0.46, 'morph.plump': 0.42, 'head.rx': 0.5, 'root.rx': 0.14, 'ear.L.rx': -0.45, 'ear.R.rx': -0.45, 'tail.rx': -0.1, 'arm.L.rz': 0.1, 'arm.R.rz': -0.1 } },
  ],
  wake: { expr: 'neutral', segs: [
    { n: 'start', d: 0.0, to: { 'morph.squash': 0.46, 'morph.plump': 0.42, 'head.rx': 0.5, 'root.rx': 0.14, 'ear.L.rx': -0.45, 'ear.R.rx': -0.45 } },
    { n: 'pre', d: 0.35, e: 'io', to: { 'morph.stretch': 0.55, 'head.rx': -0.18, 'arm.L.rz': 0.8, 'arm.R.rz': -0.8, 'ear.L.rx': 0.2, 'ear.R.rx': 0.2 } },
    { n: 'main', d: 0.35, e: 'io', to: { 'morph.stretch': 0.3, 'head.rx': -0.05, 'arm.L.rz': 0.4, 'arm.R.rz': -0.4 } },
    { n: 'out', d: 0.3, e: 'io', to: {} },
  ] },
  // 覆蓋層動作（疊在 Idle／Sit 上；結束自動回原狀態）。expr＝動作期間的表情。
  hit: { expr: 'ouch', segs: [
    { n: 'start', d: 0.0, to: {} },
    { n: 'pre', d: 0.06, e: 'out2', to: { 'morph.squash': 0.55, 'root.rx': -0.14, 'head.rx': -0.25, 'ear.L.rx': 0.5, 'ear.R.rx': 0.5, 'arm.L.rz': 0.7, 'arm.R.rz': -0.7, 'morph.cheek.L': 0.8, 'morph.cheek.R': 0.8 } },
    { n: 'main', d: 0.16, e: 'io', to: { 'morph.stretch': 0.3, 'root.rx': 0.06, 'head.rx': 0.12, 'ear.L.rx': -0.2, 'ear.R.rx': -0.2, 'arm.L.rz': 0.3, 'arm.R.rz': -0.3 } },
    { n: 'settle', d: 0.3, e: 'out2', to: { 'head.rx': 0.05 } },
    { n: 'out', d: 0.25, e: 'io', to: {} },
  ] },
  happy: { expr: 'happy', segs: [
    { n: 'start', d: 0.0, to: {} },
    { n: 'pre', d: 0.12, e: 'in2', to: { 'morph.squash': 0.4, 'arm.L.ry': 0.4, 'arm.R.ry': -0.4 } },
    { n: 'main', d: 0.22, e: 'out2', to: { 'root.dy': 0.07, 'morph.stretch': 0.5, 'arm.L.rz': 0.9, 'arm.R.rz': -0.9, 'head.rx': -0.12, 'ear.L.rx': 0.2, 'ear.R.rx': 0.2, 'tail.ry': 0.5 } },
    { n: 'main2', d: 0.2, e: 'in2', to: { 'morph.squash': 0.3, 'arm.L.rz': 0.5, 'arm.R.rz': -0.5, 'tail.ry': -0.5 } },
    { n: 'main3', d: 0.2, e: 'out2', to: { 'root.dy': 0.05, 'morph.stretch': 0.35, 'arm.L.rz': 0.8, 'arm.R.rz': -0.8, 'tail.ry': 0.5 } },
    { n: 'settle', d: 0.3, e: 'in2', to: { 'morph.squash': 0.2, 'tail.ry': -0.3 } },
    { n: 'out', d: 0.3, e: 'io', to: {} },
  ] },
  angry: { expr: 'angry', segs: [
    { n: 'start', d: 0.0, to: {} },
    { n: 'pre', d: 0.18, e: 'in2', to: { 'morph.squash': 0.25, 'morph.plump': 0.5, 'head.rx': 0.14, 'ear.L.rx': -0.5, 'ear.R.rx': -0.5, 'arm.L.rz': 0.1, 'arm.R.rz': -0.1 } },
    { n: 'main', d: 0.2, e: 'io', to: { 'morph.squash': 0.3, 'morph.plump': 0.7, 'head.ry': 0.2, 'head.rx': 0.14, 'ear.L.rx': -0.55, 'ear.R.rx': -0.55, 'root.rz': 0.04, 'tail.ry': 0.6 } },
    { n: 'main2', d: 0.2, e: 'io', to: { 'morph.squash': 0.3, 'morph.plump': 0.7, 'head.ry': -0.2, 'head.rx': 0.14, 'ear.L.rx': -0.55, 'ear.R.rx': -0.55, 'root.rz': -0.04, 'tail.ry': -0.6 } },
    { n: 'main3', d: 0.2, e: 'io', to: { 'morph.squash': 0.3, 'morph.plump': 0.7, 'head.ry': 0.15, 'head.rx': 0.14, 'ear.L.rx': -0.55, 'ear.R.rx': -0.55, 'root.rz': 0.03, 'tail.ry': 0.6 } },
    { n: 'settle', d: 0.3, e: 'io', to: { 'morph.plump': 0.25, 'head.rx': 0.06 } },
    { n: 'out', d: 0.3, e: 'io', to: {} },
  ] },
  sad: { expr: 'sad', segs: [
    { n: 'start', d: 0.0, to: {} },
    { n: 'pre', d: 0.35, e: 'io', to: { 'head.rx': 0.2, 'root.rx': 0.05, 'morph.squash': 0.12, 'ear.L.rx': -0.35, 'ear.R.rx': -0.35 } },
    { n: 'main', d: 1.2, e: 'io', to: { 'head.rx': 0.34, 'root.rx': 0.09, 'morph.squash': 0.2, 'ear.L.rx': -0.55, 'ear.R.rx': -0.55, 'ear.L.rz': -0.15, 'ear.R.rz': 0.15, 'tail.rx': -0.2, 'arm.L.rz': -0.05, 'arm.R.rz': 0.05 } },
    { n: 'settle', d: 0.35, e: 'io', to: { 'head.rx': 0.12, 'ear.L.rx': -0.2, 'ear.R.rx': -0.2 } },
    { n: 'out', d: 0.35, e: 'io', to: {} },
  ] },
};

/** 靜態姿勢（狀態專屬）。drv＝即時訊號驅動（vy 垂直速度、n、speed、wy）。 */
export const POSES = {
  idle: { pose: {}, expr: 'neutral' },
  air: {
    pose: { 'arm.L.rz': 0.55, 'arm.R.rz': -0.55, 'arm.L.ry': 0.3, 'arm.R.ry': -0.3, 'tail.rx': 0.25, 'root.rx': -0.03 },
    drv: [
      { ch: 'morph.stretch', src: 'vy', map: [[-6, 0.5], [-1, 0.1], [0, 0], [1, 0.1], [5, 0.72]] },
      { ch: 'morph.squash', src: 'vy', map: [[-1, 0], [0, 0.04], [1, 0]] },
      { ch: 'ear.L.rx', src: 'vy', map: [[-6, 0.55], [0, 0], [5, -0.55]] },
      { ch: 'ear.R.rx', src: 'vy', map: [[-6, 0.55], [0, 0], [5, -0.55]] },
      { ch: 'head.rx', src: 'vy', map: [[-6, 0.12], [0, 0], [5, -0.14]] },
      { ch: 'arm.L.rz', src: 'vy', map: [[-6, 0.95], [0, 0.55], [5, 0.35]] },
      { ch: 'arm.R.rz', src: 'vy', map: [[-6, -0.95], [0, -0.55], [5, -0.35]] },
    ],
    expr: 'happy',
  },
  sit: {
    pose: { 'morph.squash': 0.1, 'arm.L.ry': -0.35, 'arm.R.ry': 0.35, 'arm.L.rz': -0.08, 'arm.R.rz': 0.08, 'root.dy': 0, 'tail.rx': -0.18, 'ear.L.rx': -0.08, 'ear.R.rx': -0.08 },
    expr: 'smile',
  },
  sleep: {
    pose: { 'morph.squash': 0.46, 'morph.plump': 0.42, 'head.rx': 0.5, 'root.rx': 0.14, 'ear.L.rx': -0.45, 'ear.R.rx': -0.45, 'tail.rx': -0.1, 'arm.L.rz': 0.1, 'arm.R.rz': -0.1 },
    expr: 'sleep',
  },
  held: {
    pose: { 'arm.L.rz': 0.7, 'arm.R.rz': -0.7, 'arm.L.ry': 0.2, 'arm.R.ry': -0.2, 'morph.stretch': 0.38, 'ear.L.rx': 0.35, 'ear.R.rx': 0.35, 'tail.rx': 0.35, 'head.rx': -0.1 },
    expr: 'surprised',
  },
  tumble: {
    pose: { 'arm.L.rz': 0.9, 'arm.R.rz': -0.9, 'morph.stretch': 0.15, 'ear.L.rx': 0.5, 'ear.R.rx': 0.5, 'tail.rx': 0.3 },
    expr: 'whee',
  },
  recover: {
    pose: { 'head.rx': 0.1, 'morph.squash': 0.12, 'ear.L.rx': -0.2, 'ear.R.rx': -0.2 },
    expr: 'dizzy',
  },
};

/** 待機小動作（疊加層；兩端都回到 0，所以不會留下殘姿）。ch＝通道 → [[時間, 值], …]，段與段之間用 smoothstep。 */
export const MICRO = {
  lookAround: { dur: 3.0, ch: {
    'head.ry': [[0, 0], [0.4, 0.5], [1.2, 0.5], [1.8, -0.5], [2.5, -0.5], [3.0, 0]],
    'eye.y': [[0, 0], [0.25, 0.3], [1.2, 0.3], [1.6, -0.3], [2.5, -0.3], [3.0, 0]],
    'spine.ry': [[0, 0], [0.5, 0.06], [1.2, 0.06], [1.9, -0.06], [2.5, -0.06], [3.0, 0]],
    'ear.L.rz': [[0, 0], [0.5, 0.12], [1.9, -0.12], [3.0, 0]], 'ear.R.rz': [[0, 0], [0.5, 0.12], [1.9, -0.12], [3.0, 0]] } },
  earFlick: { dur: 0.7, ch: {
    'ear.L.rz': [[0, 0], [0.08, -0.5], [0.2, 0.25], [0.32, -0.3], [0.5, 0.08], [0.7, 0]], 'ear.tip.L.rz': [[0, 0], [0.1, -0.6], [0.22, 0.4], [0.36, -0.3], [0.7, 0]],
    'head.rz': [[0, 0], [0.1, -0.05], [0.3, 0.02], [0.7, 0]] } },
  sniff: { dur: 1.7, ch: {
    'head.rx': [[0, 0], [0.25, -0.2], [0.4, -0.12], [0.55, -0.22], [0.7, -0.12], [0.85, -0.2], [1.1, -0.12], [1.7, 0]],
    'root.rx': [[0, 0], [0.3, 0.05], [1.2, 0.05], [1.7, 0]],
    'eye.p': [[0, 0], [0.25, 0.2], [1.2, 0.2], [1.7, 0]],
    'morph.cheek.L': [[0, 0], [0.3, 0.5], [1.2, 0.5], [1.7, 0]], 'morph.cheek.R': [[0, 0], [0.3, 0.5], [1.2, 0.5], [1.7, 0]] } },
  tiltHead: { dur: 2.0, ch: {
    'head.rz': [[0, 0], [0.35, 0.28], [1.5, 0.28], [2.0, 0]], 'head.rx': [[0, 0], [0.35, -0.05], [1.5, -0.05], [2.0, 0]],
    'ear.L.rz': [[0, 0], [0.4, 0.15], [1.5, 0.15], [2.0, 0]], 'eye.y': [[0, 0], [0.3, -0.15], [1.5, -0.15], [2.0, 0]] } },
  shake: { dur: 0.9, ch: {
    'root.ry': [[0, 0], [0.1, 0.12], [0.22, -0.12], [0.34, 0.1], [0.46, -0.08], [0.6, 0.04], [0.9, 0]],
    'ear.L.rz': [[0, 0], [0.12, -0.3], [0.3, 0.3], [0.5, -0.2], [0.9, 0]], 'ear.R.rz': [[0, 0], [0.12, -0.3], [0.3, 0.3], [0.5, -0.2], [0.9, 0]],
    'tail.ry': [[0, 0], [0.15, 0.5], [0.35, -0.5], [0.55, 0.3], [0.9, 0]], 'morph.plump': [[0, 0], [0.2, 0.2], [0.9, 0]] } },
};

/** 狀態轉場表：[從][到] = 'o' 直接 | 'd' 經過渡（淡化較久）| 缺＝拒絕（回傳 false 並記錄）。fade＝交叉淡化秒數。 */
export const STATES = ['idle', 'walk', 'run', 'jumpPrep', 'air', 'land', 'sit', 'sleep', 'held', 'tumble', 'recover'];
export const TRANSITIONS = {
  idle:     { walk: 'o', run: 'o', jumpPrep: 'o', sit: 'o', sleep: 'd', held: 'o', air: 'o' },
  walk:     { idle: 'd', run: 'o', jumpPrep: 'o', sit: 'o', held: 'o', air: 'o' },
  run:      { idle: 'd', walk: 'o', jumpPrep: 'o', held: 'o', air: 'o', sit: 'o' },
  jumpPrep: { air: 'o', held: 'o', idle: 'o' },
  air:      { land: 'o', held: 'o', tumble: 'o', sit: 'o' },
  land:     { idle: 'o', walk: 'o', run: 'o', jumpPrep: 'o', held: 'o', sit: 'o' },
  sit:      { idle: 'd', land: 'o', jumpPrep: 'o', air: 'o', sleep: 'o', held: 'o', walk: 'd', run: 'd' },
  sleep:    { idle: 'd', sit: 'o', held: 'o' },
  held:     { air: 'o', tumble: 'o', idle: 'o' },
  tumble:   { held: 'o', recover: 'o', land: 'o', air: 'o' },
  recover:  { idle: 'o', held: 'o' },
};
export const FADE = { default: 0.16, 'idle>walk': 0.22, 'walk>idle': 0.26, 'walk>run': 0.25, 'run>walk': 0.25, 'run>idle': 0.3, 'idle>run': 0.22, 'air>land': 0.04, 'jumpPrep>air': 0.05, 'land>idle': 0.12 };
