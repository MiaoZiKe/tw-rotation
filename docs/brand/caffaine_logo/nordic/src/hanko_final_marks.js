// 像素印章精修三款（依 nordic/hanko/review.md）：07 主款、05 備案、01 第三
const { dirs: H, grid, AI } = require('./hanko_marks');
const by = id => H.find(v => v.id.startsWith(id));
const v07 = by('h07'), v05 = by('h05'), v01 = by('h01');
let uid = 0; const nid = p => `${p}f${++uid}`;
// 文字標用的像素 AI：A 頂端兩角各削一格（不會讀成 H），A 與 I 之間多空一格
const AIPX_FINE = ['..##....######', '.####.....##..', '##..##....##..', '##..##....##..', '######....##..', '##..##....##..', '##..##..######'];
// 圖形內的 5×5 A 維持原版（平頂已削兩角）；尖頂版在 5×5 會像房子，不採用
const A5P = ['.###.', '#...#', '#####', '#...#', '#...#'];
const AIP = A5P.map((r, i) => r + '.' + ['###', '.#.', '.#.', '.#.', '###'][i]);

function m07(c, small) {
  const cs = 8, sq = (x, y, s = cs) => `M${x} ${y}h${s}v${s}h-${s}z`;
  const body = ['#############..', '#############..', '###############', '#############.#', '#############.#', '#############.#', '###############', '#############..', '.###########...', '..#########....'];
  const ox = 40, oy = 92; let holes = '', b = '';
  AIP.forEach((r, y) => [...r].forEach((ch, x) => { if (ch === '#') holes += sq(ox + (x + 2) * cs, oy + (y + 2) * cs); }));
  body.forEach((r, y) => [...r].forEach((ch, x) => { if (ch === '#') b += sq(ox + x * cs, oy + y * cs); }));
  const steam = small ? [[80, 76], [88, 68], [88, 60], [80, 52], [80, 44], [88, 36], [88, 28], [80, 20]]
    : [[56, 76], [64, 68], [56, 60], [80, 76], [88, 68], [88, 60], [80, 52], [80, 44], [88, 36], [88, 28], [80, 20], [80, 12], [112, 76], [104, 68], [112, 60]];
  const st = steam.map(([x, y]) => sq(x, y)).join('');
  // 印框：缺口比上一版大一格（64～112）；40px 版階梯角放大成兩格、框線加粗
  const k = small ? 16 : 8, sw = small ? 10 : 7;
  const frame = `M64 50 H${22 + k} V${50 + k} H22 V${182 - k} H${22 + k} V182 H${178 - k} V${182 - k} H178 V${50 + k} H${178 - k} V50 H112`;
  return `<path d="${frame}" fill="none" stroke="${c.accent}" stroke-width="${sw}" stroke-linejoin="miter"/>
    <path d="${b}" fill="${c.cup}"/><path d="${holes}" fill="${c.paper}"/>${small ? '' : `<path d="${sq(ox + 8, oy + 8)}" fill="${c.hi}"/>`}<path d="${st}" fill="${c.hi}"/>`;
}
function fUneven(id, k, b, seed, sc) { return `<filter id="${id}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="${seed}" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ${-k} 0 0 0 ${b}" result="m"/><feDisplacementMap in="SourceGraphic" in2="n" scale="${sc}" xChannelSelector="R" yChannelSelector="G" result="d"/><feComposite in="d" in2="m" operator="in"/></filter>`; }
function m05(c, small) {
  if (small) // 大頭貼：不歪、框線加粗、墨色實心，AI 放大
    return `<rect x="22" y="22" width="156" height="156" rx="6" fill="none" stroke="${c.accent}" stroke-width="15"/>
      <path d="${grid(AIP, 12.5, 100, 72)}" fill="${c.accent}"/><path d="${grid(['########...', '##########.', '########.#.', '##########.', '.######....'], 11.5, 104, 136)}" fill="${c.sub}"/>`;
  const f = nid('u'), g2 = nid('u');
  return `<defs>${fUneven(f, 3.4, 2.75, 9, 2)}${fUneven(g2, 3.4, 2.75, 21, 2)}</defs>
    <g transform="rotate(-7 100 100)"><g filter="url(#${f})"><rect x="24" y="24" width="152" height="152" rx="6" fill="none" stroke="${c.accent}" stroke-width="10"/><path d="${grid(AIP, 11, 98, 66)}" fill="${c.accent}"/></g>
    <g filter="url(#${g2})"><path d="${grid(['########...', '##########.', '########.#.', '##########.', '.######....'], 11, 104, 134)}" fill="${c.sub}"/></g></g>`;
}
function m01(c, small) {
  // 印面加寬約 15%（100→116），字與杯放大；40px 版不加暈染
  const f = nid('b');
  const inner = `<rect x="42" y="10" width="116" height="180" rx="3" fill="${c.accent}"/>
    <path d="${grid(A5P, 10, 100, 44)}${grid(['###', '.#.', '.#.', '.#.', '###'], 10, 100, 100)}${grid(['##########.', '##########.', '########.#.', '##########.', '.######....'], 8.4, 102, 154)}" fill="${c.paper}"/>`;
  if (small) return inner;
  return `<defs><filter id="${f}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="3"/><feDisplacementMap in="SourceGraphic" scale="3.2" xChannelSelector="R" yChannelSelector="G"/></filter></defs><g filter="url(#${f})">${inner}</g>`;
}
const mk = (v, id, fn, extra) => ({ ...v, id, mark: c => fn(c, false), markSmall: c => fn(c, true), ...extra });
module.exports = { dirs: [
  mk(v07, 'f07_八位元衝框_主款', m07, { word: { ...v07.word, aipx: AIPX_FINE } }),
  mk(v05, 'f05_歪印雙色_備案', m05, { word: { ...v05.word, aipx: AIPX_FINE } }),
  mk(v01, 'f01_落款長印_第三', m01, {}),
] };
