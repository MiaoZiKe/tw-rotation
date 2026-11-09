// CaffAIne 北歐／日系線畫方向：8 個圖形（viewBox 0 0 200 200），全部手寫 SVG
const DARK_BG = '#231A15', CREAM = '#F3E8D8';
const S = (d, c, w, extra = '') => `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" ${extra}/>`;

const dirs = [
{
  id: 'n1_蒸氣寫字', name: '蒸氣寫字 Steam Script', en: 'Steam Script',
  meaning: '咖啡冒出的蒸氣自己寫出「AI」，橫筆兩端是電路節點：新知從一杯咖啡裡升起。',
  ratio: '咖啡 55／科技 45', style: '北歐單線',
  light: { bg: '#F5EEE3', ink: '#3B2A20', accent: '#C8643B', paper: '#FFFAF2' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#E07F55', paper: '#2E231D' },
  word: { font: 'Inter Display', w: 600, aiW: 800, ai: 'accent', iBars: true },
  mark: c => `
    <path d="M50 112 H146 V140 Q146 174 112 174 H84 Q50 174 50 140 Z" fill="${c.paper}" stroke="${c.ink}" stroke-width="9" stroke-linejoin="round"/>
    ${S('M146 120 Q172 120 172 139 Q172 158 146 157', c.ink, 9)}
    ${S('M34 188 H162', c.ink, 9)}
    ${S('M64 96 C66 82 72 74 74 62 C76 50 82 40 88 26', c.ink, 9)}
    ${S('M88 26 C94 40 98 50 100 62 C102 74 108 82 112 96', c.ink, 9)}
    ${S('M73 72 H103', c.accent, 8)}
    <circle cx="73" cy="72" r="7" fill="${c.accent}"/><circle cx="103" cy="72" r="7" fill="${c.accent}"/>
    ${S('M136 34 C131 48 141 62 136 76 C133 84 136 90 136 96', c.ink, 9)}
    ${S('M125 30 H147', c.ink, 9)}${S('M125 98 H147', c.ink, 9)}`
},
{
  id: 'n2_思考中手沖', name: '思考中的手沖 Drip Thinking', en: 'Drip Thinking',
  meaning: '濾杯滴下的咖啡落進對話框，變成「正在輸入…」三個點：手沖的等待＝AI 正在想答案。',
  ratio: '咖啡 60／科技 40', style: '日系手沖線畫',
  light: { bg: '#ECE9DD', ink: '#33261E', accent: '#C98A3E', paper: '#FBF8F0' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#E3A456', paper: '#2E231D' },
  word: { font: 'Bitstream Charter', w: 700, aiW: 700, ai: 'accent', iBars: false },
  mark: c => `
    ${S('M36 44 H164', c.ink, 9)}
    <path d="M50 44 L84 98 H116 L150 44" fill="${c.paper}" stroke="${c.ink}" stroke-width="9" stroke-linejoin="round"/>
    ${S('M84 58 L95 86', c.ink, 6, 'opacity=".55"')}${S('M116 58 L105 86', c.ink, 6, 'opacity=".55"')}
    <path d="M100 104 C104 110 107 114 107 118 A7 7 0 0 1 93 118 C93 114 96 110 100 104 Z" fill="${c.accent}"/>
    <path d="M72 132 H128 A24 24 0 0 1 128 180 H86 L62 194 L66 177 A24 24 0 0 1 72 132 Z" fill="${c.paper}" stroke="${c.ink}" stroke-width="9" stroke-linejoin="round"/>
    <circle cx="78" cy="156" r="7" fill="${c.ink}"/><circle cx="100" cy="156" r="7" fill="${c.accent}"/><circle cx="122" cy="156" r="7" fill="${c.ink}" opacity=".45"/>`
},
{
  id: 'n3_像素印章', name: '像素印章 Pixel Hanko', en: 'Pixel Hanko',
  meaning: '日本小店蓋在紙袋上的朱印，刻的是像素：一杯熱咖啡，冒出的蒸氣是像素字「AI」。',
  ratio: '咖啡 45／科技 55', style: '日系朱印＋像素',
  light: { bg: '#F2EEE6', ink: '#2E2420', accent: '#A8432F', paper: '#FBF4EA' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#B94C35', paper: '#FBF4EA' },
  word: { font: 'JetBrains Mono', w: 700, aiW: 800, ai: 'pill', iBars: false },
  mark: c => {
    const rows = [
      '..###..###..',
      '.#...#..#...',
      '.#####..#...',
      '.#...#..#...',
      '.#...#.###..',
      '............',
      '.########...',
      '.##########.',
      '.########.#.',
      '.##########.',
      '..######....'];
    let px = ''; const cs = 11, ox = 34, oy = 39.5;
    rows.forEach((r, y) => [...r].forEach((ch, x) => { if (ch === '#') px += `M${ox + x * cs} ${oy + y * cs}h${cs}v${cs}h-${cs}z`; }));
    return `<rect x="18" y="18" width="164" height="164" rx="20" fill="${c.accent}"/>
      <rect x="27" y="27" width="146" height="146" rx="13" fill="none" stroke="${c.paper}" stroke-width="3" opacity=".9"/>
      <path d="${px}" fill="${c.paper}"/>`;
  }
},
{
  id: 'n4_游標杯套', name: '游標杯套 Cursor Sleeve', en: 'Cursor Sleeve',
  meaning: '外帶杯的杯套上是「A」加一個文字游標：I 就是閃爍的輸入游標，邊喝邊問 AI。',
  ratio: '咖啡 50／科技 50', style: '北歐扁平線畫',
  light: { bg: '#F3ECE1', ink: '#3A2A21', accent: '#CF6B3E', paper: '#FFFAF3' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#DD7A4C', paper: '#2E231D' },
  word: { font: 'Inter Display', w: 700, aiW: 800, ai: 'accent', iBars: true },
  mark: c => `
    <path d="M56 68 L68 180 H132 L144 68 Z" fill="${c.paper}" stroke="${c.ink}" stroke-width="9" stroke-linejoin="round"/>
    <path d="M59.4 100 L64.6 148 H135.4 L140.6 100 Z" fill="${c.accent}" stroke="${c.ink}" stroke-width="9" stroke-linejoin="round"/>
    <rect x="46" y="52" width="108" height="18" rx="7" fill="${c.ink}"/>
    ${S('M64 52 Q66 38 82 38 H118 Q134 38 136 52', c.ink, 9)}
    ${S('M76 138 L88 110 L100 138', c.paper, 7)}${S('M81 127 H95', c.paper, 7)}
    ${S('M118 112 V136', c.paper, 6)}
    ${S('M110 109 Q118 109 118 115 Q118 109 126 109', c.paper, 5)}
    ${S('M110 139 Q118 139 118 133 Q118 139 126 139', c.paper, 5)}`
},
{
  id: 'n5_晨光載入', name: '晨光載入 Morning Loading', en: 'Morning Loading',
  meaning: '咖啡杯緣是地平線，升起半顆晨陽，陽光是一圈「載入中」的刻線：早上第一杯，新知正在載入。',
  ratio: '咖啡 50／科技 50', style: '溫暖晨光線畫',
  light: { bg: '#FBF1DA', ink: '#4A3428', accent: '#E09A2D', paper: '#FFF9EC', text: '#B8731A' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#F0B04A', paper: '#2E231D', text: '#F0B04A' },
  word: { font: 'Inter', w: 600, aiW: 800, ai: 'text', iBars: true },
  mark: c => {
    const cx = 98, cy = 112; let rays = '';
    [162, 138, 114, 90, 66, 42, 18].forEach((deg, i) => { const r = deg * Math.PI / 180, cs = Math.cos(r), sn = Math.sin(r);
      rays += S(`M${(cx + 40 * cs).toFixed(1)} ${(cy - 40 * sn).toFixed(1)} L${(cx + 56 * cs).toFixed(1)} ${(cy - 56 * sn).toFixed(1)}`, c.accent, 8, `opacity="${(1 - i * .13).toFixed(2)}"`); });
    return `
    <path d="M68 112 A30 30 0 0 1 128 112 Z" fill="${c.accent}"/>
    ${rays}
    <path d="M44 120 H152 V144 Q152 178 118 178 H78 Q44 178 44 144 Z" fill="${c.paper}" stroke="${c.ink}" stroke-width="9" stroke-linejoin="round"/>
    ${S('M152 128 Q176 128 176 146 Q176 164 152 162', c.ink, 9)}`;
  }
},
{
  id: 'n6_沙漏手沖', name: '沙漏手沖 Chemex Hourglass', en: 'Chemex Hourglass',
  meaning: '手沖壺本身就是沙漏（一杯咖啡的時間），下半壺是一個「A」，咖啡液面就是 A 的橫筆，落下的是資料方塊。',
  ratio: '咖啡 60／科技 40', style: '北歐器物線畫',
  light: { bg: '#E9DFCF', ink: '#2F2622', accent: '#7A4A30', paper: '#FAF4EA', wood: '#C08A57' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#B9774E', paper: '#2E231D', wood: '#C99463' },
  word: { font: 'Caladea', w: 700, aiW: 700, ai: 'underline', iBars: false },
  mark: c => `
    <path d="M58 28 L96 96 L58 170 Q55 178 64 178 H136 Q145 178 142 170 L104 96 L142 28" fill="${c.paper}" stroke="${c.ink}" stroke-width="8" stroke-linejoin="round"/>
    <path d="M74.5 142 H125.5 L141 170 Q144 176 136 176 H64 Q56 176 59 170 Z" fill="${c.accent}"/>
    ${S('M58 28 L96 96 L58 170 Q55 178 64 178 H136 Q145 178 142 170 L104 96 L142 28', c.ink, 8)}
    ${S('M70 142 H130', c.ink, 8)}
    ${S('M50 28 H150', c.ink, 8)}
    <path d="M84 80 H116 L110 96 L116 112 H84 L90 96 Z" fill="${c.wood}" stroke="${c.ink}" stroke-width="5" stroke-linejoin="round"/>
    ${S('M116 104 Q126 108 128 118', c.ink, 4)}<circle cx="129" cy="122" r="5" fill="${c.wood}" stroke="${c.ink}" stroke-width="3"/>
    <rect x="96" y="118" width="8" height="8" rx="1.5" fill="${c.ink}"/><rect x="97" y="130" width="6" height="6" rx="1.2" fill="${c.ink}" opacity=".6"/>
    <rect x="95" y="52" width="10" height="10" rx="2" fill="${c.accent}" opacity=".9"/>`
},
{
  id: 'n7_摺紙紙杯', name: '摺紙紙杯 Origami Cup', en: 'Origami Cup',
  meaning: '用摺紙的折面拼出外帶杯，正中央那一面就是一個大「A」，低多邊形的面＝3D 模型的網格。',
  ratio: '咖啡 40／科技 60', style: '日系摺紙幾何',
  light: { bg: '#F7E9DF', ink: '#3E2C24', accent: '#B4573A', paper: '#FBEFE6', f1: '#C9704A', f2: '#A9522F', f3: '#DE9068', f4: '#F6D9C4' },
  dark:  { bg: DARK_BG, ink: CREAM, accent: '#D9774F', paper: '#2E231D', f1: '#C9704A', f2: '#9C4B2C', f3: '#DE9068', f4: '#F6D9C4' },
  word: { font: 'Inter Display', w: 600, aiW: 800, ai: 'accent', iBars: true },
  mark: c => `
    <polygon points="50,64 100,64 58,122" fill="${c.f3}"/>
    <polygon points="58,122 100,64 71,180 66,180" fill="${c.f1}"/>
    <polygon points="150,64 100,64 142,122" fill="${c.f1}"/>
    <polygon points="142,122 100,64 129,180 134,180" fill="${c.f2}"/>
    <polygon points="100,64 71,180 129,180" fill="${c.f4}"/>
    ${S('M81 141 H119', c.f2, 9)}
    <polygon points="42,64 52,44 148,44 158,64" fill="${c.ink}"/>
    <polygon points="64,44 74,32 126,32 136,44" fill="${c.ink}" opacity=".8"/>
`
},
{
  id: 'n8_暖簾長條圖', name: '暖簾長條圖 Noren Chart', en: 'Noren Chart',
  meaning: '日本咖啡店門口的暖簾，三片布長短不一就是一張長條圖；三片寫著 A、I、一杯咖啡，最長那片是 I。',
  ratio: '咖啡 40／科技 60', style: '日系暖簾',
  light: { bg: '#EDE3D2', ink: '#2E2420', accent: '#C9612F', paper: '#F6EDDF' },
  dark:  { bg: DARK_BG, ink: '#E9DCC8', accent: '#D97040', paper: '#2B211C' },
  word: { font: 'Bitstream Charter', w: 700, aiW: 700, ai: 'pill', iBars: false },
  mark: c => {
    const dark = c.ink === '#E9DCC8';
    const panel = dark ? '#4A3A31' : c.ink, glyph = dark ? '#F3E8D8' : c.paper;
    const tab = (x) => `<rect x="${x}" y="28" width="9" height="22" rx="3" fill="${panel}"/>`;
    return `
    ${tab(46)}${tab(66)}${tab(90)}${tab(110)}${tab(134)}${tab(154)}
    ${S('M30 36 H170', c.ink, 7)}<circle cx="27" cy="36" r="7" fill="${c.ink}"/><circle cx="173" cy="36" r="7" fill="${c.ink}"/>
    <rect x="38" y="44" width="40" height="110" rx="3" fill="${panel}"/>
    <rect x="82" y="44" width="40" height="140" rx="3" fill="${c.accent}"/>
    <rect x="126" y="44" width="40" height="84" rx="3" fill="${panel}"/>
    ${S('M48 128 L58 98 L68 128', glyph, 7)}${S('M52 117 H64', glyph, 7)}
    ${S('M92 104 H112', glyph, 7)}${S('M102 104 V150', glyph, 7)}${S('M92 150 H112', glyph, 7)}
    <path d="M134 80 H155 V90 Q155 102 144.5 102 Q134 102 134 90 Z" fill="${glyph}"/>
    ${S('M155 84 Q162 84 162 90 Q162 96 155 96', glyph, 4)}
    ${S('M140 74 Q137 70 140 66', glyph, 3.5)}${S('M149 74 Q146 70 149 66', glyph, 3.5)}`;
  }
},
];
module.exports = { dirs, DARK_BG, CREAM };
