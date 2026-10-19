/* SSD：一片 M.2 2280 NVMe 固態硬碟 —— 族群 `memory_module`（記憶體模組，semiconductor 鏈）
   2026-10-19 Andy：「SSD 也要，請繪圖團隊補 3D 圖」。

   合約＝`docs/diagram_specs/ssd.md`。主角是 3D（`site/three3d.js` 的 `SCENES.ssd`），
   這張 2D 是同一組零件的俯視＋側視（WebGL 不能用時的退路，也是預設的平面圖）。
   兩邊共用同一組 data-part（ssd_pcb、ssd_finger、ssd_ctrl…），2D 點完切 3D 還是選著同一個零件。

   版面（660 寬，v2 風格：說明卡外掛成 HTML，見 hbm.js 檔頭）：
     §1 俯視：板子照 22 × 80 比例畫（1 mm ＝ 7 px），左邊是主機板插槽，右端半圓螺絲缺口
     §1 側視：同一條板子從側面看，晶片的高低（誇張約 2.5 倍，跟 3D 同一個倍數）
     ② 章節（預設收合）：NAND 封裝切開 —— 晶粒錯開成階梯、金線打到基板
   顏色一律 `--dg-*` token，JS 裡沒有任何色碼。*/
(function () {
  'use strict';
  const D = window.DG;
  if (!D || typeof D.register !== 'function') return;
  const { extRow, note, fold, fx } = D;
  const CW = 660;

  const VARS = `<style>
    svg.dg.dgssd [data-seg].sel .part{filter:none;stroke-width:1.5}
    svg.dg.dgssd [data-seg].sel-part .part{stroke-width:2.6;filter:var(--dg-glow,drop-shadow(0 0 6px var(--cc)))}
    .dgwrap:has(svg.dg.dgssd) .dgc.dim{opacity:.55}
  </style>`;

  const n1 = (v) => +(+v).toFixed(1);
  const R = (x, y, w, h, fill, cls, rx, extra) =>
    `<rect${cls ? ` class="${cls}"` : ''} x="${n1(x)}" y="${n1(y)}" width="${n1(w)}" height="${n1(h)}"${rx ? ` rx="${rx}"` : ''} fill="${fill}"${extra || ''}/>`;
  const part = (id, inner, seg) => `<g data-part="${id}"${seg ? ` data-seg="${seg}"` : ''}>${inner}</g>`;
  const T = (x, y, s, cls, anchor, style) =>
    `<text class="${cls || 'sub'}" x="${n1(x)}" y="${n1(y)}"${anchor ? ` text-anchor="${anchor}"` : ''}${style ? ` style="${style}"` : ''}>${s}</text>`;
  const C = {
    pcb: 'var(--dg-pcb)', au: 'var(--dg-au)', emc: 'var(--dg-emc)', si: 'var(--dg-si)', ni: 'var(--dg-ni)',
    sn: 'var(--dg-sn)', cer: 'var(--dg-cer)', cu: 'var(--dg-cu)', mute: 'var(--dg-mute)', el: 'var(--dg-el, var(--dg-emc))',
  };
  const card = (o) => {
    const s = extRow({ seg: o.seg, part: o.part, title: o.title, sub: o.sub, no: o.no, side: o.side, ax: o.ax, ay: o.ay, color: o.color });
    return o.color ? s.replace('<g class="anc" ', `<g class="anc" style="--dg-card-c:${o.color}" `) : s;
  };

  /* ---- 座標：世界（mm，跟 3D 同一組數字）→ 畫布。x：−40～40 → 80～640；z：−11～11 → 上到下 */
  const SC = 7, OX = 80, OY = 64;
  const X = (x) => OX + (x + 40) * SC;
  const Y = (z) => OY + (z + 11) * SC;
  const NOTCH_Z = 5.3, NOTCH_W = 1.3, NOTCH_D = 4.2, SCREW_R = 1.75;   // 跟 three3d.js 的 SSD_NOTCH_* 同一組
  const box = (x0, x1, z0, z1) => [X(x0), Y(z0), (x1 - x0) * SC, (z1 - z0) * SC];

  function topView() {
    const g = [];
    // 主機板插槽（板子左邊、還沒插進去）
    const [sx, sy, sw, sh] = box(-48.5, -43.5, -12.5, 12.5);
    g.push(part('ssd_socket', fx.glass(sx, sy, sw, sh, { fill: C.emc, cls: 'part', rx: 2 })
      + R(sx + sw - 6, Y(NOTCH_Z) - 4, 6, 8, 'var(--dg-void)', '', 1), 'connector'));
    // 板子外形：長方形扣掉 M key 缺口與半圓螺絲缺口（path 的 evenodd 不好控制，直接畫輪廓）
    const x0 = X(-40), x1 = X(40), y0 = Y(-11), y1 = Y(11), nt = Y(NOTCH_Z - NOTCH_W / 2), nb = Y(NOTCH_Z + NOTCH_W / 2), nd = NOTCH_D * SC, r = SCREW_R * SC, cy = Y(0);
    const outline = `M${x0},${y0} H${x1} V${n1(cy - r)} A${n1(r)},${n1(r)} 0 0 0 ${x1},${n1(cy + r)} V${y1} H${x0} V${n1(nb)} H${n1(x0 + nd)} V${n1(nt)} H${x0} Z`;
    const traces = [];
    for (let i = 0; i < 4; i++) [-1, 1].forEach((sg) => { const yy = Y(0.4 + i * 1.05 + sg * 0.17); traces.push(`M${X(-36)},${n1(yy)} H${X(-29)}`); });
    [[6.4, 8.6], [-6.4, -8.6]].forEach(([a, b]) => { for (let i = 0; i < 6; i++) { const yy = Y(a + (b - a) * i / 5); traces.push(`M${X(-16)},${n1(yy)} H${X(a > 0 ? 2 : 16)}`); } });
    g.push(part('ssd_pcb', `<path class="part" d="${outline}" fill="${C.pcb}" stroke="var(--dg-line)" stroke-width="1"/>`
      + `<path d="${traces.join(' ')}" stroke="var(--dg-pcb-hi, var(--dg-line))" stroke-width="1" fill="none" opacity=".75"/>`
      + `<path d="M${x1},${n1(cy - r - 5)} A${n1(r + 5)},${n1(r + 5)} 0 0 0 ${x1},${n1(cy + r + 5)}" stroke="${C.au}" stroke-width="4" fill="none" opacity=".8"/>`, 'hdi_pcb'));
    // 金手指（M key 缺口那段沒有）
    const fz = [];
    for (let z = -10.5; z <= 10.5; z += 0.56) if (Math.abs(z - NOTCH_Z) > NOTCH_W / 2 + 0.3) fz.push(R(X(-39.8), Y(z) - 1.3, 3.5 * SC, 2.6, C.au, 'part', 0.6));
    g.push(part('ssd_finger', fz.join(''), 'hdi_pcb'));
    // 晶片
    const chip = (id, seg, b, fill, label, lid) => {
      const [x, y, w, h] = b;
      return part(id, fx.glass(x, y, w, h, { fill, cls: 'part', rx: 2, t: 2 })
        + (lid ? R(x + w * 0.11, y + h * 0.11, w * 0.78, h * 0.78, C.ni, '', 2, ' opacity=".55"') : '')
        + `<circle cx="${n1(x + 7)}" cy="${n1(y + 7)}" r="2.4" fill="var(--dg-cover)"/>`
        + (label ? T(x + w / 2, y + h / 2 + 5, label, 'lbl', 'middle', 'fill:var(--dg-cover);pointer-events:none') : ''), seg);
    };
    g.push(chip('ssd_ctrl', 'storage', box(-29, -16, -6.5, 6.5), C.emc, '主控', true));
    g.push(chip('ssd_dram', 'dram_nor', box(-14.5, -6.5, -6, 6), C.emc, 'DRAM'));
    g.push(part('ssd_nand', [box(-4, 8, -9, 9), box(10, 22, -9, 9)].map(([x, y, w, h]) =>
      fx.glass(x, y, w, h, { fill: C.emc, cls: 'part', rx: 2, t: 2 }) + `<circle cx="${n1(x + 7)}" cy="${n1(y + 7)}" r="2.4" fill="var(--dg-cover)"/>`
      + T(x + w / 2, y + h / 2 + 5, 'NAND', 'lbl', 'middle', 'fill:var(--dg-cover);pointer-events:none')).join(''), 'storage'));
    g.push(chip('ssd_pmic', 'ic_design', box(-34.5, -30.5, -8.5, -4.5), C.emc, ''));
    g.push(part('ssd_ind', R(...box(-34.2, -30.8, -3.1, 0.3), C.el, 'part', 2), 'passive_inductor'));
    const ml = []; for (let i = 0; i < 6; i++) { const cx = -33.9 + i * 1.8; ml.push(R(...box(cx - 0.55, cx + 0.55, 9.1, 9.7), C.cer, 'part', 0.5)); }
    g.push(part('ssd_mlcc', ml.join(''), 'passive_comp'));
    return g.join('');
  }

  /* 側視：同一條板子從 −z 那一面看，高度誇張約 2.5 倍（跟 3D 同一個倍數）。散熱片畫虛線（選配）。*/
  const SY = 312;    // 板子頂面
  function sideView() {
    const g = [];
    const H = (h) => h * SC;
    g.push(part('ssd_pcb', R(X(-40), SY, 80 * SC, H(1), C.pcb, 'part', 1), 'hdi_pcb'));
    g.push(part('ssd_finger', R(X(-39.8), SY - 1.5, 3.5 * SC, 1.5, C.au, 'part') + R(X(-39.8), SY + H(1), 3.5 * SC, 1.5, C.au, 'part'), 'hdi_pcb'));
    const up = (id, seg, x0, x1, h, fill) => part(id, R(X(x0), SY - H(h), (x1 - x0) * SC, H(h), fill, 'part', 1.5), seg);
    g.push(up('ssd_ctrl', 'storage', -29, -16, 2.8, C.emc));
    g.push(up('ssd_dram', 'dram_nor', -14.5, -6.5, 2.2, C.emc));
    g.push(part('ssd_nand', R(X(-4), SY - H(3.4), 12 * SC, H(3.4), C.emc, 'part', 1.5) + R(X(10), SY - H(3.4), 12 * SC, H(3.4), C.emc, 'part', 1.5), 'storage'));
    g.push(up('ssd_pmic', 'ic_design', -34.5, -30.5, 1.6, C.emc));
    g.push(part('ssd_hs', `<rect class="part" x="${X(-37)}" y="${n1(SY - H(3.4) - 26)}" width="${66 * SC}" height="18" rx="3" fill="none" stroke="var(--dg-mute)" stroke-width="1.4" stroke-dasharray="6 4"/>`
      + T(X(-4), SY - H(3.4) - 13, '散熱片（選配）', 'cap', 'middle'), 'thermal'));
    return g.join('');
  }

  /* ② NAND 封裝切開（章節）：基板 → 8 片晶粒往同一側錯開成階梯 → 每一階拉金線到基板 → 模封包住 */
  function nandCut() {
    const x0 = 40, y0 = 560, w = 400, sh = 16, n = 8, dh = 13, gap = 3, step = 14, dw = 280;
    const g = [];
    g.push(R(x0, y0 - 150, w, 150, C.emc, '', 6, ' opacity=".35"'));
    g.push(R(x0, y0, w, sh, 'var(--dg-core, var(--dg-pcb))', '', 2));
    const dies = [], wires = [];
    for (let i = 0; i < n; i++) {
      const yb = y0 - (i + 1) * (dh + gap);
      const xl = x0 + 30, xr = x0 + 30 + dw - i * step;
      dies.push(R(xl, yb, xr - xl, dh, C.si, 'part', 1.5));
      dies.push(R(xl, yb + dh, xr - xl, gap, 'var(--dg-cover)', '', 0, ' opacity=".7"'));
      wires.push(`M${n1(xr - 6)},${n1(yb + 2)} Q${n1(xr + 30 + i * 4)},${n1(yb - 18)} ${n1(x0 + w - 40 + (i % 2) * 8)},${y0}`);
    }
    g.push(part('ssd_nand_die', dies.join('') + `<path d="${wires.join(' ')}" stroke="${C.au}" stroke-width="1.6" fill="none"/>`, 'storage'));
    g.push(R(x0 + w - 48, y0 - 3, 24, 4, C.au, '', 1));
    for (let i = 0; i < 9; i++) g.push(`<circle cx="${x0 + 26 + i * 44}" cy="${y0 + sh + 6}" r="6" fill="${C.sn}"/>`);
    return `<g>${T(16, 392, 'NAND 封裝切開：晶粒怎麼疊、怎麼接出來', 'hd')}
      ${g.join('')}
      ${T(470, 432, '① 封裝基板（最底下）', 'sub')}
      ${T(470, 452, '② 晶粒 8 片（示意），每片往左', 'sub')}
      ${T(470, 470, '　 錯開一階，露出右邊的墊子', 'sub')}
      ${T(470, 490, '③ 金線從每一階打到基板', 'sub')}
      ${T(470, 510, '④ 模封膠把整疊包住', 'sub')}
      ${T(470, 530, '⑤ 底下錫球焊到 SSD 板上', 'sub')}
      ${T(16, 610, '★ 每一片晶粒「裡面」又是 200～400 層以上的 3D NAND 堆疊（微米級，這個尺度畫不出來）。', 'sub', null, 'fill:var(--dg-warn)')}</g>`;
  }

  function ssdFig() {
    return `<svg class="dg dgm rs dgssd" viewBox="0 0 ${CW} 640" width="100%" style="display:block">${D.STYLE}${VARS}
      <defs>${fx.glowDefs({ r: 4, soft: 4 })}</defs>
      <text class="ttl ext" x="0" y="0">SSD：一片 M.2 2280 NVMe 固態硬碟</text>
      <text class="cap ext" x="0" y="0">一條 22 × 80 mm 的小板子：左端金手指插進主機板（缺口偏一側＝M key），旁邊最大那顆是主控 IC，緊鄰的是 DRAM 快取（便宜的款沒有），往右排開的長方形大封裝是 NAND Flash —— 真正存資料的地方。右端半圓缺口是固定螺絲的位置。★ 台股站在哪：主控 8299 群聯；NAND 晶圓是外商（Kioxia、Samsung、SK hynix、Micron、SanDisk），台股做的是封測（6239 力成、8150 南茂）與模組（威剛、宜鼎、創見…都在這個族群）。示意圖，非實物比例。</text>
      ${T(16, 40, '① 從上面看（比例照實：1 mm ＝ 7 px）', 'hd')}
      ${topView()}
      ${T(16, 244, '② 從側面看（高度誇張約 2.5 倍）', 'hd')}
      ${sideView()}
      ${card({ seg: 'connector', part: 'ssd_socket', no: 1, side: 'l', color: C.emc, ax: X(-46), ay: Y(-9), title: '主機板上的 M.2 插槽', sub: ['板子斜插進這個口、尾端用螺絲壓平。口裡的擋塊跟金手指缺口對齊 —— key 不對插不進去。'] })}
      ${card({ seg: 'hdi_pcb', part: 'ssd_finger', no: 2, side: 'l', color: C.au, ax: X(-38), ay: Y(-8), title: 'M.2 金手指（M key）', sub: ['上下兩面都有接點；缺口偏一側，M key 走 PCIe ×4（NVMe）。'] })}
      ${card({ seg: 'ic_design', part: 'ssd_pmic', no: 3, side: 'l', color: C.emc, ax: X(-32.5), ay: Y(-6.5), title: 'PMIC 電源管理 IC', sub: ['把 3.3V 轉成主控、NAND、DRAM 各自要的電壓。'] })}
      ${card({ seg: 'passive_inductor', part: 'ssd_ind', no: 4, side: 'l', color: C.el, ax: X(-32.5), ay: Y(-1.4), title: '電源電感', sub: ['PMIC 降壓一定要搭的那顆。'] })}
      ${card({ seg: 'passive_comp', part: 'ssd_mlcc', no: 5, side: 'l', color: C.cer, ax: X(-29.4), ay: Y(9.4), title: '去耦電容（MLCC）', sub: ['穩住供電；實際板上有幾十顆，這裡畫一排示意。'] })}
      ${card({ seg: 'storage', part: 'ssd_ctrl', no: 6, side: 'l', color: C.ni, ax: X(-18), ay: Y(-4.6), title: '主控 IC（SSD 的大腦）', sub: ['★ 離金手指最近的大晶片：PCIe／NVMe 介面、位址對照（FTL）、ECC 糾錯、磨損平均。'] })}
      ${card({ seg: 'dram_nor', part: 'ssd_dram', no: 7, side: 'r', color: C.emc, ax: X(-8.2), ay: Y(-4.2), title: 'DRAM 快取（有／無兩種款）', sub: ['放 FTL 對照表；DRAM-less 款改借電腦主記憶體（HMB）。'] })}
      ${card({ seg: 'storage', part: 'ssd_nand', no: 8, side: 'r', color: C.si, ax: X(20), ay: Y(-7.2), title: 'NAND Flash 封裝（×2）', sub: ['真正存資料的地方；顆數依容量而定，大容量款背面也會貼。'] })}
      ${card({ seg: 'hdi_pcb', part: 'ssd_pcb', no: 9, side: 'r', color: C.pcb, ax: X(34), ay: Y(-7), title: 'PCB 板（寬 22、長 80 mm）', sub: ['一端金手指、一端半圓螺絲缺口；綠漆底下是 PCIe 與 NAND 通道走線。'] })}
      ${card({ seg: 'thermal', part: 'ssd_hs', no: 10, side: 'r', color: C.mute, ax: X(20), ay: SY - 7 * 3.4 - 17, title: '散熱片（選配）', sub: ['高速款主控很燙才加；很多款沒有。'] })}
      ${card({ seg: 'storage', part: 'ssd_nand_die', no: 11, side: 'r', color: C.si, ax: X(6), ay: Y(6.8), title: '封裝裡疊起來的 NAND 晶粒', sub: ['錯開成階梯才能打線；每片晶粒裡面又是數百層 3D 堆疊。'] })}
      ${note({ side: 'r', order: 98, title: '示意圖，非實物比例', lines: ['平面尺寸照 M.2 2280 規格（22 × 80 mm）；晶片位置照常見配置（主控靠金手指、NAND 往尾端排），各家設計不同。', '高度方向誇張約 2.5 倍；金手指根數、M key 缺口位置、晶粒片數為示意。'] })}
      ${fold('ssd2', '③ NAND 封裝切開：晶粒怎麼疊、怎麼接出來', '8 片晶粒錯開成階梯、金線打到基板、每片裡面又是數百層', nandCut())}
    </svg>`;
  }

  window.DG.register('memory_module', {
    level: 'group', chain: 'semiconductor',
    name: 'SSD：一片 M.2 2280 NVMe 固態硬碟',
    draw: ssdFig, native: CW, scene: 'ssd',
    q: 'SSD 是什麼？那一條小板子上每一顆晶片各做什麼？主控、DRAM、NAND 分別是誰做的、台股站在哪裡？',
    parts: {
      ssd_pcb: { name: 'PCB 板（M.2 2280）', desc: '寬 22、長 80 mm 的多層板（層數依設計）。一端金手指、一端半圓螺絲缺口；防焊漆底下是 PCIe 差動對與 NAND 通道走線。', cos: ['3044'], note: '健鼎既有資料寫「記憶體模組板」；是否含 SSD 板未查證。' },
      ssd_finger: { name: 'M.2 金手指（M key）', desc: '插進主機板的那一端，上下兩面都有接點、兩面錯開半格；缺口偏一側（M key），走 PCIe ×4（NVMe）。鍍金是板廠的製程。', cos: ['3044'] },
      ssd_ctrl: { name: '主控 IC（SSD 的大腦）', desc: '負責 PCIe／NVMe 介面、把電腦要的位址對到 NAND 的實體位置（FTL）、ECC 糾錯、磨損平均。晶圓找晶圓代工廠做。', cos: ['8299', '2379'], note: '群聯（NAND 控制 IC）；瑞昱既有資料：PCIe SSD 控制 IC，比重未揭露。' },
      ssd_dram: { name: 'DRAM 快取', desc: '放 FTL 對照表；DRAM-less 款改用主機記憶體緩衝（HMB）。', cos: ['2408', '3006'], note: '這個環節做 DRAM 的兩家；未逐家查證是否供 SSD 快取。' },
      ssd_nand: { name: 'NAND Flash 封裝', desc: '真正存資料的地方，斷電也不會忘。一顆封裝裡疊了好幾片晶粒。', cos: ['6239', '8150'], note: '力成、南茂做的是 NAND 的封裝測試，不是 NAND 晶圓。' },
      ssd_nand_die: { name: '封裝裡疊起來的 NAND 晶粒', desc: '一片一片往同一側錯開成階梯，從每一階拉金線打到基板。每片晶粒裡面又是 200～400 層以上的 3D 堆疊。', none: '3D NAND 晶圓由 Kioxia、Samsung、SK hynix、Micron、SanDisk 生產，台股無直接對應。' },
      ssd_pmic: { name: 'PMIC 電源管理 IC', desc: '把主機給的 3.3V 轉成主控、NAND、DRAM 各自要的電壓。', none: 'SSD 用 PMIC 公開資料多為外商；台股 PMIC 廠的 SSD 營收查不到，不列。' },
      ssd_ind: { name: '電源電感', desc: 'PMIC 做降壓轉換一定要搭的那顆。' },
      ssd_mlcc: { name: '去耦電容（MLCC）', desc: '穩住主控與 NAND 的供電。', cos: ['2327', '2492', '6173', '3026'] },
      ssd_hs: { name: '散熱片（選配）', desc: '高速款主控很燙，常加一片鋁散熱片，底下墊導熱墊。', none: 'SSD 散熱片多由模組廠自配，不列伺服器散熱廠。' },
      ssd_socket: { name: '主機板上的 M.2 插槽', desc: '板子斜插進去、尾端用螺絲壓平；插槽裡的擋塊跟金手指缺口對齊。', cos: ['3533'], note: '嘉澤有 M.2 插槽料號（信心中）。' },
    },
  });
})();
