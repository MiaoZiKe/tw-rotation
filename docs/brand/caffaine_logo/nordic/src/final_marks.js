// N1 蒸氣寫字 精修版（依 review_final.md：描邊加粗約 20%、拿掉杯下底線、A 橫筆節點收斂；另做 40px 用粗線簡化版）
const { dirs } = require('./marks');
const base = dirs[0];
const S = (d, c, w) => `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
// 主圖形：描邊 9 → 11
const mark = c => `<g transform="translate(-11 0)">
  ${S('M62 98 C64 84 70 74 73 62 C76 48 82 38 89 22', c.ink, 11)}
  ${S('M89 22 C96 38 101 50 104 62 C107 74 113 84 116 98', c.ink, 11)}
  ${S('M76 72 H101', c.accent, 9)}
  <circle cx="74" cy="72" r="6.5" fill="${c.accent}"/><circle cx="103" cy="72" r="6.5" fill="${c.accent}"/>
  ${S('M142 32 C137 46 147 60 142 74 C139 83 142 90 142 96', c.ink, 11)}
  ${S('M130 28 H154', c.ink, 11)}${S('M130 98 H154', c.ink, 11)}
  <path d="M46 116 H150 V144 Q150 178 116 178 H80 Q46 178 46 144 Z" fill="${c.paper}" stroke="${c.ink}" stroke-width="11" stroke-linejoin="round"/>
  ${S('M150 124 Q176 124 176 144 Q176 164 150 162', c.ink, 11)}</g>`;
// 大頭貼簡化版：描邊 17、AI 放大、蒸氣只留一個彎、節點併入橫筆
const markSmall = c => `<g transform="translate(-10 0)">
  ${S('M52 98 L70 46 Q76 30 84 20 Q92 30 98 46 L116 98', c.ink, 17)}
  ${S('M66 74 H102', c.accent, 17)}
  ${S('M146 30 C140 46 152 62 146 78 L146 96', c.ink, 17)}
  ${S('M128 26 H164', c.ink, 17)}${S('M128 98 H164', c.ink, 17)}
  <path d="M42 120 H150 V142 Q150 180 114 180 H78 Q42 180 42 142 Z" fill="${c.paper}" stroke="${c.ink}" stroke-width="17" stroke-linejoin="round"/>
  ${S('M150 128 Q178 128 178 146 Q178 164 150 164', c.ink, 17)}</g>`;
module.exports = { dirs: [{ ...base, id: '', mark, markSmall }] };
