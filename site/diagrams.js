/* 產品剖析圖（原創示意 SVG，含動畫）。每個零件帶 data-seg = supply_chain.yaml 的環節 id，
   點零件會篩選該環節的供應商；個股頁上會把該公司所在的零件點亮。 */
(function () {
  'use strict';
  const STYLE = `<style>
    .dg text{font-family:"Noto Sans TC",sans-serif;font-size:12px;fill:#a9b6d6}
    .dg .lbl{font-size:12.5px;fill:#e8eeff;font-weight:600}
    .dg .sub{font-size:10.5px;fill:#6f7ea3}
    .dg [data-seg]{cursor:pointer}
    .dg [data-seg] .part{transition:.2s}
    .dg [data-seg]:hover .part,.dg [data-seg].sel .part{stroke:#3ee0ff;stroke-width:2;filter:drop-shadow(0 0 6px rgba(62,224,255,.9))}
    .dg [data-seg].sel .lbl{fill:#3ee0ff}
    .dg .flow{stroke-dasharray:6 6;animation:dash 1.2s linear infinite}
    .dg .flow2{stroke-dasharray:3 5;animation:dash 0.8s linear infinite}
    @keyframes dash{to{stroke-dashoffset:-24}}
    .dg .blink{animation:blink 1.4s ease-in-out infinite}
    .dg .blink.b2{animation-delay:.4s}.dg .blink.b3{animation-delay:.8s}
    @keyframes blink{0%,100%{opacity:.25}50%{opacity:1}}
    .dg .pulse{animation:pulse 2.4s ease-in-out infinite}
    @keyframes pulse{0%,100%{opacity:.55}50%{opacity:1}}
    .dg .spin{transform-box:fill-box;transform-origin:center;animation:spin 3s linear infinite}
    @keyframes spin{to{transform:rotate(360deg)}}
    .dg .heat{animation:heat 3s ease-in-out infinite}
    @keyframes heat{0%,100%{stop-color:#ff4d6d}50%{stop-color:#ffb454}}
    .dg .lead{stroke:#2a3860;stroke-width:1;fill:none}
  </style>`;

  function gpu(x, y, i) { // 一顆 GPU 封裝：CoWoS 中介層上放邏輯晶片 + HBM
    return `<g transform="translate(${x},${y})">
      <rect class="part" x="0" y="0" width="54" height="40" rx="3" fill="#16213f" stroke="#2a3860"/>
      <rect x="17" y="8" width="20" height="24" rx="2" fill="#1f2f5c" stroke="#3ee0ff" stroke-width=".8"/>
      <rect x="4" y="6" width="9" height="12" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/><rect x="4" y="22" width="9" height="12" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/>
      <rect x="41" y="6" width="9" height="12" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/><rect x="41" y="22" width="9" height="12" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".6"/>
      <rect class="pulse" x="20" y="11" width="14" height="18" fill="rgba(62,224,255,.25)" style="animation-delay:${i * .3}s"/>
    </g>`;
  }

  function aiServer() {
    const gpus = [[0, 0], [62, 0], [124, 0], [186, 0], [0, 48], [62, 48], [124, 48], [186, 48]].map(([x, y], i) => gpu(x, y, i)).join('');
    return `<svg class="dg" viewBox="0 0 720 450" width="100%" style="max-height:450px;display:block">${STYLE}
      <defs><linearGradient id="gCool" x1="0" x2="1"><stop offset="0" stop-color="#3ee0ff"/><stop offset="1" stop-color="#8b7bff"/></linearGradient>
        <linearGradient id="gHot" x1="0" y1="0" x2="0" y2="1"><stop class="heat" offset="0" stop-color="#ff4d6d"/><stop offset="1" stop-color="#2a3860"/></linearGradient></defs>
      <!-- 機櫃 -->
      <g data-seg="assembly"><rect class="part" x="18" y="24" width="120" height="400" rx="8" fill="#0f172b" stroke="#2a3860" stroke-width="1.5"/>
        <text class="lbl" x="22" y="16">整機櫃 / 系統組裝</text>
        ${[0, 1, 2, 3, 4, 5].map(i => `<rect x="28" y="${104 + i * 34}" width="100" height="26" rx="3" fill="#141e36" stroke="#1e2a48"/><circle class="blink b${(i % 3) + 1}" cx="36" cy="${117 + i * 34}" r="2.2" fill="#2ee59d"/><line x1="46" y1="${117 + i * 34}" x2="118" y2="${117 + i * 34}" stroke="#1e2a48"/>`).join('')}
        <text class="sub" x="34" y="98">GPU 運算托盤 ×N</text></g>
      <g data-seg="switch"><rect class="part" x="28" y="36" width="100" height="26" rx="3" fill="#182a3f" stroke="#2a3860"/>
        ${[0, 1, 2, 3, 4, 5, 6].map(i => `<rect class="blink b${(i % 3) + 1}" x="${36 + i * 12}" y="44" width="7" height="10" rx="1" fill="#ffb454"/>`).join('')}
        <text class="lbl" x="34" y="78">交換器（ToR）</text></g>
      <g data-seg="power"><rect class="part" x="28" y="318" width="100" height="30" rx="3" fill="#2b1f3f" stroke="#2a3860"/>
        <text class="lbl" x="34" y="337">電源櫃 PSU/BBU</text>
        <path class="flow2" d="M138,333 L170,333" stroke="#ffb454" stroke-width="2" fill="none"/></g>
      <g data-seg="thermal"><rect class="part" x="28" y="356" width="100" height="56" rx="3" fill="#0e2a33" stroke="#2a3860"/>
        <circle class="spin" cx="52" cy="384" r="12" fill="none" stroke="#3ee0ff" stroke-width="2" stroke-dasharray="6 5"/>
        <text class="lbl" x="72" y="381">CDU</text><text class="sub" x="72" y="395">液冷分配</text></g>
      <!-- 爆炸圖：運算托盤 -->
      <text class="lbl" x="180" y="16">GPU 運算托盤剖析（由下往上）</text>
      <g data-seg="ccl"><polygon class="part" points="180,404 500,404 560,364 240,364" fill="#12331f" stroke="#2a3860"/>
        ${[0, 1, 2, 3, 4].map(i => `<line x1="${196 + i * 62}" y1="400" x2="${256 + i * 62}" y2="368" stroke="#1f5a34" stroke-width=".8"/>`).join('')}
        <text class="lbl" x="184" y="424">CCL 銅箔基板（板材）</text></g>
      <g data-seg="abf_pcb"><polygon class="part" points="180,358 500,358 560,318 240,318" fill="#163a2a" stroke="#2a3860"/>
        <path class="flow" d="M210,343 L320,343 L350,326 L520,326" stroke="#2ee59d" stroke-width="1.2" fill="none" opacity=".8"/>
        <text class="lbl" x="184" y="378">主機板 高階 PCB / ABF 載板</text></g>
      <!-- 8 顆 GPU -->
      <g data-seg="adv_pkg" transform="translate(236,200)"><g>${gpus}</g>
        <rect class="part" x="-8" y="-8" width="254" height="104" rx="6" fill="none" stroke="#2a3860"/>
        <text class="lbl" x="254" y="30">先進封裝</text><text class="lbl" x="254" y="45">CoWoS</text><text class="sub" x="254" y="59">中介層＋晶片</text><text class="sub" x="254" y="72">＋HBM</text></g>
      <g data-seg="foundry"><rect class="part" x="572" y="28" width="132" height="30" rx="4" fill="#1f2f5c" stroke="#3ee0ff" stroke-width=".8"/><text class="lbl" x="580" y="47">GPU 晶片・晶圓代工</text><path class="lead" d="M572,43 C520,43 440,120 300,213"/></g>
      <g data-seg="hbm"><rect class="part" x="572" y="66" width="132" height="30" rx="4" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".8"/><text class="lbl" x="580" y="85">HBM 記憶體堆疊</text><path class="lead" d="M572,81 C520,81 440,150 306,226"/></g>
      <!-- 冷板與水路 -->
      <g data-seg="thermal" transform="translate(228,110)"><rect class="part" x="0" y="0" width="270" height="72" rx="6" fill="url(#gHot)" fill-opacity=".35" stroke="#3ee0ff" stroke-width=".8"/>
        <path class="flow" d="M10,14 H250 M10,32 H250 M10,50 H250" stroke="url(#gCool)" stroke-width="3" fill="none"/>
        <path class="flow" d="M-40,32 H10 M250,32 H300" stroke="#3ee0ff" stroke-width="3" fill="none"/>
        <text class="lbl" x="6" y="67">液冷冷板 + 快接頭 + 分歧管</text></g>
      <!-- 前面板：光模組 / NIC -->
      <g data-seg="optical" transform="translate(600,200)"><rect class="part" x="0" y="0" width="100" height="104" rx="6" fill="#141e36" stroke="#2a3860"/>
        ${[0, 1, 2, 3].map(i => `<rect x="10" y="${10 + i * 22}" width="80" height="14" rx="2" fill="#0f172b" stroke="#1e2a48"/><circle class="blink b${(i % 3) + 1}" cx="18" cy="${17 + i * 22}" r="2.5" fill="#3ee0ff"/><line class="flow2" x1="26" y1="${17 + i * 22}" x2="84" y2="${17 + i * 22}" stroke="#3ee0ff"/>`).join('')}
        <text class="lbl" x="0" y="120">光通訊 / 矽光子</text><text class="sub" x="0" y="134">800G–1.6T 光模組 / CPO</text></g>
      <!-- 電源 -->
      <g data-seg="power" transform="translate(168,200)"><rect class="part" x="0" y="0" width="52" height="104" rx="6" fill="#2b1f3f" stroke="#2a3860"/>
        <path class="flow2" d="M8,20 L44,20 M8,40 L44,40 M8,60 L44,60 M8,80 L44,80" stroke="#ffb454" stroke-width="2"/>
        <text class="lbl" x="-10" y="120">電源模組</text><text class="sub" x="-10" y="134">800V HVDC</text></g>
      <!-- 雲端需求 -->
      <g data-seg="hyperscaler"><path class="part" d="M612,150 a16,16 0 0 1 30,-6 a14,14 0 0 1 26,8 a12,12 0 0 1 -4,23 h-50 a13,13 0 0 1 -2,-25 z" fill="#0f172b" stroke="#8b7bff"/><text class="lbl" x="600" y="122">雲端業者（終端需求）</text><path class="lead flow2" d="M650,176 L650,200" stroke="#8b7bff"/></g>
    </svg>`;
  }

  function semiconductor() {
    const hbm = (x) => `<g transform="translate(${x},0)">${[0, 1, 2, 3, 4, 5, 6, 7].map(i => `<rect class="pulse" x="0" y="${118 - i * 9}" width="46" height="8" rx="1" fill="#3a2a5c" stroke="#8b7bff" stroke-width=".7" style="animation-delay:${i * .15}s"/>`).join('')}<rect x="0" y="126" width="46" height="8" rx="1" fill="#1f2f5c" stroke="#3ee0ff" stroke-width=".6"/></g>`;
    return `<svg class="dg" viewBox="0 0 660 330" width="100%" style="max-height:330px;display:block">${STYLE}
      <defs><linearGradient id="gSi" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#1f2f5c"/><stop offset="1" stop-color="#2b3f7a"/></linearGradient></defs>
      <text class="lbl" x="16" y="18">CoWoS 2.5D 封裝剖面（由下往上）</text>
      <!-- 晶圓 / 晶片設計（左側） -->
      <g data-seg="ip_eda"><rect class="part" x="16" y="40" width="120" height="40" rx="6" fill="#141e36" stroke="#2a3860"/><text class="lbl" x="24" y="57">IP / EDA / 設計服務</text><text class="sub" x="24" y="71">ASIC NRE、矽智財授權</text><path class="lead flow2" d="M76,80 L76,100" stroke="#3ee0ff"/></g>
      <g data-seg="ic_design"><rect class="part" x="16" y="100" width="120" height="40" rx="6" fill="#141e36" stroke="#2a3860"/><text class="lbl" x="24" y="117">IC 設計（GDS）</text><text class="sub" x="24" y="131">GPU / ASIC / 網通晶片</text><path class="lead flow2" d="M76,140 L76,160" stroke="#3ee0ff"/></g>
      <g data-seg="foundry"><circle class="part" cx="76" cy="212" r="42" fill="url(#gSi)" stroke="#3ee0ff" stroke-width="1"/>
        ${[-30, -20, -10, 0, 10, 20, 30].map(dy => `<line x1="${76 - Math.sqrt(42 * 42 - dy * dy) + 3}" y1="${212 + dy}" x2="${76 + Math.sqrt(42 * 42 - dy * dy) - 3}" y2="${212 + dy}" stroke="#0f172b" stroke-width=".8"/>`).join('')}
        ${[-30, -20, -10, 0, 10, 20, 30].map(dx => `<line x1="${76 + dx}" y1="${212 - Math.sqrt(42 * 42 - dx * dx) + 3}" x2="${76 + dx}" y2="${212 + Math.sqrt(42 * 42 - dx * dx) - 3}" stroke="#0f172b" stroke-width=".8"/>`).join('')}
        <rect class="pulse" x="70" y="206" width="12" height="12" fill="#3ee0ff"/>
        <text class="lbl" x="30" y="272">晶圓代工（先進製程）</text><text class="sub" x="30" y="286">3nm / 2nm 邏輯晶片與 HBM 基底</text>
        <path class="lead flow2" d="M118,212 L170,212" stroke="#3ee0ff"/></g>
      <!-- 剖面 -->
      <g data-seg="abf_pcb"><rect class="part" x="180" y="250" width="440" height="34" rx="4" fill="#163a2a" stroke="#2a3860"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map(i => `<circle cx="${205 + i * 44}" cy="290" r="5" fill="#ffb454"/>`).join('')}
        <text class="lbl" x="188" y="271">ABF 載板（基板）</text><text class="sub" x="330" y="271">BGA 錫球 → 主機板 PCB</text></g>
      <g data-seg="adv_pkg"><rect class="part" x="200" y="216" width="400" height="30" rx="3" fill="#1a2542" stroke="#2a3860"/>
        <path class="flow" d="M215,231 H585" stroke="#3ee0ff" stroke-width="2" fill="none"/>
        ${[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(i => `<rect x="${212 + i * 32}" y="246" width="6" height="5" fill="#ffb454"/>`).join('')}
        <text class="lbl" x="210" y="237">矽中介層 Interposer（CoWoS-S / L）＋微凸塊</text></g>
      <g data-seg="foundry"><rect class="part" x="340" y="130" width="120" height="84" rx="3" fill="url(#gSi)" stroke="#3ee0ff" stroke-width="1"/>
        ${[0, 1, 2, 3].map(i => `<rect class="pulse" x="${352 + i * 26}" y="${142}" width="18" height="60" fill="rgba(62,224,255,.18)" style="animation-delay:${i * .25}s"/>`).join('')}
        <text class="lbl" x="352" y="126">GPU / ASIC 邏輯晶片</text></g>
      <g data-seg="hbm">${hbm(224)}${hbm(280)}${hbm(480)}${hbm(536)}<text class="lbl" x="200" y="46">HBM3E 堆疊（8–12 層 DRAM）</text></g>
      <g data-seg="osat_test"><rect class="part" x="200" y="92" width="400" height="10" rx="2" fill="#2b3f7a" stroke="#2a3860"/><text class="lbl" x="470" y="30">封裝上蓋 → 測試 / 分選（封測）</text>
        ${[0, 1, 2].map(i => `<path class="blink b${i + 1}" d="M${300 + i * 90},60 v30" stroke="#ffb454" stroke-width="2"/>`).join('')}</g>
    </svg>`;
  }

  window.Diagrams = { ai_server: aiServer, semiconductor };
})();
