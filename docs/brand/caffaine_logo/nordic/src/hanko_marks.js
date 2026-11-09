// 「03 像素印章」10 個變體（Andy：「這個幫我修改，多點不同風格」）
// 避開 Adobe 系圖示：「圓角方塊＋實心亮紅＋白字」三者不同時出現
const DARK = '#231A15', CREAM = '#F5EBDC';
let uid = 0; const nid = p => `${p}${++uid}`;
// 像素陣列 → 單一路徑（同一條 path 不會出現接縫）
function grid(rows, cs, cx, cy, dot) {
  const w = Math.max(...rows.map(r => r.length)) * cs, h = rows.length * cs, ox = cx - w / 2, oy = cy - h / 2; let d = '';
  rows.forEach((r, y) => [...r].forEach((ch, x) => { if (ch === '#') {
    const X = ox + x * cs, Y = oy + y * cs;
    if (dot) { const rr = cs * dot; d += `M${(X + cs / 2 - rr).toFixed(2)} ${(Y + cs / 2).toFixed(2)}a${rr} ${rr} 0 1 0 ${2 * rr} 0a${rr} ${rr} 0 1 0 ${-2 * rr} 0z`; }
    else d += `M${X.toFixed(2)} ${Y.toFixed(2)}h${cs}v${cs}h-${cs}z`; } }));
  return d;
}
const A5 = ['.###.', '#...#', '#####', '#...#', '#...#'], I3 = ['###', '.#.', '.#.', '.#.', '###'];
const join = (a, b, gap) => a.map((r, i) => r + '.'.repeat(gap) + b[i]);
const AI = join(A5, I3, 1); // 9×5
const CUP = ['########...', '##########.', '########.#.', '##########.', '.######....'];
const ORIG = ['..###..###..', '.#...#..#...', '.#####..#...', '.#...#..#...', '.#...#.###..', '............', '.########...', '.##########.', '.########.#.', '.##########.', '..######....'];
const FINE = (() => { const A7 = ['..###..', '.#...#.', '##...##', '#######', '##...##', '##...##', '##...##'], I6 = ['######', '..##..', '..##..', '..##..', '..##..', '..##..', '######'];
  return [...A7.map((r, i) => '.' + r + '..' + I6[i]), '................',
    '.############...', '.##############.', '.############.#.', '.############.#.', '.##############.', '..##########....', '...########.....', '##############..']; })();
const TOGO2 = (() => { const inv = r => [...r].map(ch => ch === '#' ? '.' : '#').join('');
  return ['....#######....', '.#############.', '..###########..', '..###########..', ...AI.map(r => '..#' + inv(r) + '#..'), '..###########..', '...#########...', '...#########...', '....#######....']; })();
// 濾鏡：印泥暈染（邊緣毛邊）、印泥不均（斑駁小白點）、紙紋
const fBleed = (id, sc = 3.2, seed = 3) => `<filter id="${id}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="${seed}"/><feDisplacementMap in="SourceGraphic" scale="${sc}" xChannelSelector="R" yChannelSelector="G"/></filter>`;
const fUneven = (id, k = 4.2, b = 3.1, seed = 7, sc = 2.6) => `<filter id="${id}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" seed="${seed}" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ${-k} 0 0 0 ${b}" result="m"/><feDisplacementMap in="SourceGraphic" in2="n" scale="${sc}" xChannelSelector="R" yChannelSelector="G" result="d"/><feComposite in="d" in2="m" operator="in"/></filter>`;
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

const V = [
{ id: 'h01_落款長印', name: '落款長印 Rakkan', style: '直式落款印＋印泥暈染',
  desc: '像畫作落款的直式長印，由上而下刻 A、I、一杯咖啡，邊緣有印泥暈開的毛邊。',
  diff: '方印改成直式長方印、直角；亮紅降成印泥紅；加暈染質感；AI 改成直排；文字標右上角加落款小印。',
  light: { bg: '#F3ECE0', ink: '#2E2420', accent: '#A9473A', paper: '#F7EEE1' }, dark: { bg: DARK, ink: CREAM, accent: '#B4513F', paper: '#F7EEE1' },
  word: { font: 'Bitstream Charter', w: 700, aiW: 700, ai: 'rakkan' },
  mark: (c, small) => { const f = nid('b'); return `<defs>${fBleed(f, small ? 1.5 : 3.4)}</defs><g filter="url(#${f})">
    <rect x="50" y="10" width="100" height="180" rx="3" fill="${c.accent}"/>
    <path d="${grid(A5, 8.5, 100, 45)}${grid(I3, 8.5, 100, 99)}${grid(['##########.', '##########.', '########.#.', '##########.', '.######....'].map(r => r.slice(0, 11)), 7.2, 100, 152)}" fill="${c.paper}"/></g>`; } },
{ id: 'h02_橢圓細像素', name: '橢圓細像素 Oval 16', style: '乾淨扁平對照組',
  desc: '焦糖橘橢圓印，裡面是 16 格的細緻像素：A、帶襯線的 I、有杯耳和杯碟的咖啡杯。',
  diff: '外形改橢圓、改焦糖橘；像素從 12 格加細到 16 格；完全扁平無質感（乾淨對照組）。',
  light: { bg: '#F6EEE2', ink: '#33261E', accent: '#C3732F', paper: '#FFF7EC' }, dark: { bg: DARK, ink: CREAM, accent: '#D08240', paper: '#FFF7EC' },
  word: { font: 'Inter Display', w: 600, aiW: 800, ai: 'accent', iBars: true },
  mark: c => `<ellipse cx="100" cy="100" rx="96" ry="76" fill="${c.accent}"/><path d="${grid(FINE, 6.4, 100, 100)}" fill="${c.paper}"/>` },
{ id: 'h03_手刻可可', name: '手刻可可 Hand-carved', style: '手刻不規則邊＋刻痕',
  desc: '深可可色的手刻印，外框歪歪的、像素的邊是刀刻出來的微微抖動，還留著刻刀劃過的刻痕。',
  diff: '外形改手刻不規則邊；顏色改深可可；像素邊緣是手刻的微微抖動＋刻痕；文字標的 AI 改像素字。',
  light: { bg: '#EFE7DB', ink: '#3A2A21', accent: '#5B3B2B', paper: '#F4E6D2' }, dark: { bg: DARK, ink: CREAM, accent: '#6E4935', paper: '#F4E6D2', aiText: '#C99A72' },
  word: { font: 'Inter Display', w: 600, aiW: 800, ai: 'pixelAI', aiColor: 'accent' },
  mark: c => { const r = rng(11); uid; const pts = []; const P = (x, y) => pts.push(`${(x + (r() - .5) * 7).toFixed(1)},${(y + (r() - .5) * 7).toFixed(1)}`);
    for (let x = 18; x < 182; x += 20) P(x, 18); for (let y = 18; y < 182; y += 20) P(182, y); for (let x = 182; x > 18; x -= 20) P(x, 182); for (let y = 182; y > 18; y -= 20) P(18, y);
    const f = nid('w');
    return `<defs><filter id="${f}" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".13" numOctaves="2" seed="5"/><feDisplacementMap in="SourceGraphic" scale="4.5" xChannelSelector="R" yChannelSelector="G"/></filter></defs>
    <polygon points="${pts.join(' ')}" fill="${c.accent}"/><path d="${grid(ORIG, 11, 100, 100)}" fill="${c.paper}" filter="url(#${f})"/>
    <g stroke="${c.paper}" stroke-width="1.6" stroke-linecap="round" opacity=".5"><path d="M30 158 l14 -5"/><path d="M150 30 l16 4"/><path d="M160 150 l8 12"/><path d="M27 60 l3 16"/></g>`; } },
{ id: 'h04_抹茶雙框', name: '抹茶雙框 Matcha Double', style: '雙框印＋紙紋',
  desc: '深抹茶色的雙框直角印，像素是「印上去」的顏色而不是挖空，紙的纖維紋從印裡透出來。',
  diff: '直角方印＋內外雙框；改深抹茶色（偏橄欖，不像連鎖咖啡的綠）；正印（印出圖案）不是陰刻；加紙紋。',
  light: { bg: '#F2EDE2', ink: '#2F3325', accent: '#4D5836', paper: '#F2EDE2' }, dark: { bg: DARK, ink: '#E9E4D2', accent: '#8E9A6A', paper: DARK },
  word: { font: 'Caladea', w: 700, aiW: 700, ai: 'underline' },
  mark: (c, small) => { const f = nid('u'); return `<defs>${fUneven(f, small ? 2.5 : 3.6, small ? 2.6 : 2.85, 5, small ? 1 : 1.8)}</defs><g filter="url(#${f})" fill="${c.accent}">
    <path d="M14 14 H186 V186 H14 Z M24 24 V176 H176 V24 Z" fill-rule="evenodd"/>
    <path d="M31 31 H169 V169 H31 Z M34.5 34.5 V165.5 H165.5 V34.5 Z" fill-rule="evenodd"/>
    <path d="${grid(ORIG, 10, 100, 100)}"/></g>`; } },
{ id: 'h05_歪印雙色', name: '歪印雙色 Tilted Duo', style: '蓋歪的雙色手蓋印',
  desc: '一枚蓋歪了 7 度的框印，AI 用印泥紅、咖啡杯用可可色，兩次蓋印、墨色不均，像手作小店的章。',
  diff: '整枚蓋歪；只有框線不是實心；紅＋可可雙色分開蓋；印泥不均的斑駁感；文字標 AI 嵌成小印章。',
  light: { bg: '#F5EEE4', ink: '#3A2A21', accent: '#B0493A', paper: '#F5EEE4', sub: '#4B3326' }, dark: { bg: DARK, ink: CREAM, accent: '#C95A47', paper: DARK, sub: '#D9B48E' },
  word: { font: 'Inter Display', w: 600, aiW: 800, ai: 'inlineSeal' },
  mark: (c, small) => { const f = nid('u'), g2 = nid('u'); return `<defs>${fUneven(f, small ? 2.4 : 3.4, small ? 2.5 : 2.75, 9, small ? 1 : 2)}${fUneven(g2, small ? 2.4 : 3.4, small ? 2.5 : 2.75, 21, small ? 1 : 2)}</defs>
    <g transform="rotate(-7 100 100)"><g filter="url(#${f})"><rect x="24" y="24" width="152" height="152" rx="6" fill="none" stroke="${c.accent}" stroke-width="9"/><path d="${grid(AI, 11, 98, 66)}" fill="${c.accent}"/></g>
    <g filter="url(#${g2})"><path d="${grid(CUP, 11, 104, 134)}" fill="${c.sub}"/></g></g>`; } },
{ id: 'h06_墨黑粗框', name: '墨黑粗框 Sumi Bold', style: '墨黑單色直角粗框',
  desc: '只用墨黑一色，直角方印加極粗外框，像素用正印，配紙紋的細白點，像書法作品角落的章。',
  diff: '直角＋特粗外框；改墨黑單色；正印不挖空；加細紙紋；文字標 AI 改像素字。',
  light: { bg: '#F4F0E8', ink: '#1F1A17', accent: '#1F1A17', paper: '#F4F0E8' }, dark: { bg: DARK, ink: CREAM, accent: '#F1E6D4', paper: DARK },
  word: { font: 'JetBrains Mono', w: 700, aiW: 800, ai: 'pixelAI', aiColor: 'accent' },
  mark: (c, small) => { const f = nid('u'); return `<defs>${fUneven(f, small ? 2 : 3.0, small ? 2.6 : 2.6, 13, small ? .8 : 1.4)}</defs><g filter="url(#${f})" fill="${c.accent}">
    <path d="M12 12 H188 V188 H12 Z M32 32 V168 H168 V32 Z" fill-rule="evenodd"/><path d="${grid(ORIG, 10, 100, 101)}"/></g>`; } },
{ id: 'h07_八位元衝框', name: '八位元衝框 8-bit Break-out', style: '8 位元遊戲＋蒸氣衝出框',
  desc: '8 位元遊戲畫面般的階梯角外框，像素杯身上刻 AI，三道像素蒸氣衝出框外：新知滿到裝不下。',
  diff: '圓角改成像素階梯角、只有框線；三色 8 位元配色；AI 改刻在杯身；蒸氣衝出印框。',
  light: { bg: '#F4ECDF', ink: '#3B281F', accent: '#3B281F', paper: '#FFF6E8', cup: '#C77A3A', hi: '#E9A25D' }, dark: { bg: DARK, ink: CREAM, accent: '#E9D6BC', paper: DARK, cup: '#D08643', hi: '#F0B572' },
  word: { font: 'JetBrains Mono', w: 700, aiW: 800, ai: 'pixelAI', aiColor: 'cup' },
  mark: c => { const cs = 8; const body = ['#############..', '#############..', '###############', '#############.#', '#############.#', '#############.#', '###############', '#############..', '.###########...', '..#########....'];
    const ox = 40, oy = 92, sq = (x, y) => `M${x} ${y}h${cs}v${cs}h-${cs}z`; let holes = '', b = '';
    AI.forEach((r, y) => [...r].forEach((ch, x) => { if (ch === '#') holes += sq(ox + (x + 2) * cs, oy + (y + 2) * cs); }));
    body.forEach((r, y) => [...r].forEach((ch, x) => { if (ch === '#') b += sq(ox + x * cs, oy + y * cs); }));
    const st = [[56, 76], [64, 68], [56, 60], [80, 76], [88, 68], [88, 60], [80, 52], [80, 44], [88, 36], [88, 28], [80, 20], [80, 12], [112, 76], [104, 68], [112, 60]].map(([x, y]) => sq(x, y)).join('');
    return `<path d="M72 50 H30 V58 H22 V174 H30 V182 H170 V174 H178 V58 H170 V50 H104" fill="none" stroke="${c.accent}" stroke-width="7" stroke-linejoin="miter"/>
    <path d="${b}" fill="${c.cup}"/><path d="${holes}" fill="${c.paper}"/><path d="${sq(ox + 8, oy + 8)}" fill="${c.hi}"/><path d="${st}" fill="${c.hi}"/>`; } },
{ id: 'h08_外帶杯暈印', name: '外帶杯暈印 To-go Bleed', style: '切角印＋印泥暈染',
  desc: '八角切角的印泥紅印，刻的是像素外帶杯，杯套上空出 AI 兩個字，邊緣有印泥暈開的毛邊。',
  diff: '外形改切角八邊形；咖啡杯換成像素外帶杯、AI 改在杯套上；印泥紅降飽和；加暈染。',
  light: { bg: '#F4EDE3', ink: '#33241D', accent: '#A64A3B', paper: '#F8EEE0' }, dark: { bg: DARK, ink: CREAM, accent: '#B5543F', paper: '#F8EEE0' },
  word: { font: 'Bitstream Charter', w: 700, aiW: 700, ai: 'accent' },
  mark: (c, small) => { const f = nid('b'); return `<defs>${fBleed(f, small ? 1.5 : 3.6, 8)}</defs><g filter="url(#${f})">
    <polygon points="52,14 148,14 186,52 186,148 148,186 52,186 14,148 14,52" fill="${c.accent}"/>
    <path d="${grid(TOGO2, 9.4, 100, 101)}" fill="${c.paper}"/></g>`; } },
{ id: 'h09_郵票點陣', name: '郵票點陣 Stamp Dots', style: '郵票齒孔＋LED 點陣',
  desc: '把印章換成郵票：齒孔邊、紅陶色，像素改成圓點，像咖啡店門口的 LED 點陣招牌。',
  diff: '外形改郵票齒孔邊；方格像素改圓點點陣（LED 感）；紅陶色；文字標用襯線字＋AI 換色。',
  light: { bg: '#F1EADF', ink: '#3A2A21', accent: '#B5644A', paper: '#FBF1E4' }, dark: { bg: DARK, ink: CREAM, accent: '#C47054', paper: '#FBF1E4' },
  word: { font: 'Caladea', w: 700, aiW: 700, ai: 'accent' },
  mark: c => { const m = nid('m'); let holes = ''; for (let t = 20; t <= 180; t += 16) { holes += `<circle cx="${t}" cy="16" r="6"/><circle cx="${t}" cy="184" r="6"/><circle cx="16" cy="${t}" r="6"/><circle cx="184" cy="${t}" r="6"/>`; }
    return `<defs><mask id="${m}"><rect width="200" height="200" fill="#fff"/><g fill="#000">${holes}</g></mask></defs>
    <rect x="16" y="16" width="168" height="168" fill="${c.accent}" mask="url(#${m})"/>
    <path d="${grid(ORIG, 11, 100, 100, .44)}" fill="${c.paper}"/>`; } },
{ id: 'h10_對章', name: '對章 Seal Pair', style: '一對印章（姓名印＋雅號印）',
  desc: '書畫常見的一對章：可可色方印刻咖啡杯、紅色長印刻直排 AI，一杯咖啡配一個 AI。',
  diff: '一枚拆成兩枚、各管一件事；紅＋可可雙色；都是直角；文字標 AI 嵌成小印章。',
  light: { bg: '#F4EDE2', ink: '#2E2420', accent: '#A9473A', paper: '#F7EEE1', sub: '#4E3427' }, dark: { bg: DARK, ink: CREAM, accent: '#B9523F', paper: '#F7EEE1', sub: '#6A4836' },
  word: { font: 'Inter Display', w: 600, aiW: 800, ai: 'inlineSeal' },
  mark: (c, small) => { const f = nid('b'); return `<defs>${fBleed(f, small ? 1.2 : 2.6, 4)}</defs><g filter="url(#${f})">
    <rect x="10" y="62" width="112" height="112" rx="2" fill="${c.sub}"/><path d="${grid(['##########.', '##########.', '########.#.', '##########.', '.######....', '...........', '..#.#.#....', '..#.#.#....'].slice(0, 5), 9, 66, 118)}" fill="${c.paper}"/>
    <path d="${grid(['.#.#.', '.#.#.', '#.#..'], 6, 60, 82)}" fill="${c.paper}" opacity=".9"/>
    <rect x="132" y="22" width="58" height="152" rx="2" fill="${c.accent}"/><path d="${grid(A5, 7.6, 161, 66)}${grid(I3, 7.6, 161, 128)}" fill="${c.paper}"/></g>`; } },
];
V.forEach(v => { v.markSmall = c => v.mark(c, true); v.meaning = v.desc; v.ratio = ''; });
module.exports = { dirs: V, grid, AI, DARK };
