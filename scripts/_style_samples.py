"""風格樣張沙盒：不改線上任何東西，只把風格「注入」進去然後截圖。

為什麼有這支（Andy 2026-09-22）
--------------------------------
> 「隨便挑一張 2D 圖給我，並且做出以下幾種風格，並貼在這裡我先看看，因為我需要調整
>   1.科技 2.休閒 3.專業 4.吉卜力／日系動畫 5.閱讀 6.卡通 7.豐富 8.素描／線稿
>   3D 圖給我以下兩種風格看看：1.3D 渲染／皮克斯風 2.像素風」

★ 最重要的一條：**必須是我們自己那張圖真的渲染出來的**，不是參考圖、不是示意圖。
  所以這支起本機伺服器、開真的網頁、把風格用 CSS／SVG filter 注入進去、再截圖。
  `site/` 底下**一個檔都沒有動** —— 風格全部活在這支腳本裡。

挑哪兩張
--------
  · 2D ＝ `mlcc`（`#industry/electronics/dg/mlcc`）—— Andy 最熟、而且剛壓到一個畫面看得完，
    八張並排比較才有意義。
  · 3D ＝ `ai_server`（`#industry/ai_server/dg/ai_server`）—— 零件最多、最看得出打光與材質差異。

注入怎麼生效（這一段是給下一個人看的）
--------------------------------------
  1. `--dg-*` 全部定義在 `:root`，所以 `page.add_style_tag` 加在 `head` 尾端的 `:root{}`
     就蓋得掉 —— 但 `:root[data-dgpal="casual"]` 的特異性比較高，所以一律加 `!important`。
  2. **3D 的打光參數不在 `:root`**，是寫在 `.dg3d{--dg-key:1;--dg-fill:.34;--dg-hemi:.62…}`。
     用 `#prod3d{…}`（id 特異性 1,0,0）才蓋得掉 class（0,1,0）。
  3. 零件的環節色 `--c` 是 `industry.js` 用 `style.setProperty` 寫成**行內樣式**的，
     所以只有 `!important` 蓋得掉。
  4. `three3d.js` 的 `applyPal()` 只在**掛載那一刻**讀 CSS 變數，
     所以 3D 一定要「先注入 CSS、再點 #dg3d 掛 3D」，順序反了就吃不到。
  5. 像素風不改 three.js：截圖之後用 PIL 降採樣＋色彩量化＋最近鄰放大。
     **標籤另外拍一張透明底的疊回去** —— 字級 ≥12px 是紅線，不能讓像素化把字吃掉。

用法
----
    python scripts/_style_samples.py              # 十張全跑
    python scripts/_style_samples.py --only 素描  # 只跑一種（調的時候用）

輸出在 `docs/_style/`（gitignore）。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = ROOT / "docs" / "_style"
PORT = int(os.environ.get("TW_STYLE_PORT", "8791"))

VIEW_2D = "industry/electronics/dg/mlcc"
VIEW_3D = "industry/ai_server/dg/ai_server"

# ---------------------------------------------------------------- 共用片段

# 截圖要可重現：動畫停在哪一幀會讓「同一個風格」看起來不一樣，
# 所以十張一律凍結動畫。這只影響截圖，不影響網站。
FREEZE = """
  .dg *, .dg3d *, .lbl3d, .lbl3dLayer * { animation:none !important; transition:none !important; }
"""


def grain(color: str, opacity: float, freq: float = 0.9, octaves: int = 4) -> str:
    """紙張顆粒：用 feTurbulence 做一張 data URI，當成容器的 background-image。

    為什麼不用 SVG filter 直接濾整張圖：那會連文字一起濾過去，
    12px 的中文經不起任何一點擾動。顆粒鋪在**底下**，字還是乾淨的。
    """
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="220">'
        f'<filter id="g"><feTurbulence type="fractalNoise" baseFrequency="{freq}" '
        f'numOctaves="{octaves}" stitchTiles="stitch"/>'
        '<feColorMatrix type="saturate" values="0"/></filter>'
        f'<rect width="220" height="220" filter="url(#g)" opacity="{opacity}" fill="{color}"/>'
        "</svg>"
    )
    return "url(\"data:image/svg+xml," + quote(svg, safe="") + "\")"


# 手繪抖動。scale 刻意很小（1.6~2.4）：再大就會讓 16 層電極的線互相碰到，
# 那時候「手繪感」是用「看不懂」換來的。
DEFS_SVG = """
<svg id="styleDefs" width="0" height="0" style="position:absolute;left:-9999px"
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="sxWobble" x="-6%" y="-6%" width="112%" height="112%">
      <feTurbulence type="fractalNoise" baseFrequency="0.019" numOctaves="3" seed="11" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="2.1"
                         xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="sxWobbleS" x="-6%" y="-6%" width="112%" height="112%">
      <feTurbulence type="fractalNoise" baseFrequency="0.026" numOctaves="3" seed="5" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="1.5"
                         xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <!-- 卡通的落影：不是發光，是實心的偏移影子 -->
    <filter id="sxToonShadow" x="-12%" y="-12%" width="126%" height="126%">
      <feDropShadow dx="2.4" dy="3" stdDeviation="0" flood-color="#1d1a17" flood-opacity="0.22"/>
    </filter>
    <!-- 皮克斯風的柔和高光（亮部才參與）。k3 刻意壓在 0.42：
         我們自己的規矩是「bloom 只給選起來的那一顆」，全場泛光是這個風格的代價，
         所以做得剛好看得出「有打光」就停。 -->
    <filter id="sxBloom" x="-8%" y="-8%" width="116%" height="116%">
      <feComponentTransfer in="SourceGraphic" result="bright">
        <feFuncR type="linear" slope="3.2" intercept="-1.72"/>
        <feFuncG type="linear" slope="3.2" intercept="-1.72"/>
        <feFuncB type="linear" slope="3.2" intercept="-1.72"/>
      </feComponentTransfer>
      <feGaussianBlur in="bright" stdDeviation="9" result="bl"/>
      <feComposite in="SourceGraphic" in2="bl" operator="arithmetic"
                   k1="0" k2="1" k3="0.42" k4="0"/>
    </filter>
    <!-- 素描的交叉線影：原本用漸層填色的「切面」改成用它，暗部才有東西 -->
    <!-- ★ 間距 7→11、不透明度 .62→.34：第一版的線影太密，
         把 16 層交錯電極整個蓋掉了 —— 那等於用「有手繪感」換掉「看得懂」。 -->
    <pattern id="sxHatch" width="11" height="11" patternUnits="userSpaceOnUse"
             patternTransform="rotate(38)">
      <rect width="11" height="11" fill="none"/>
      <line x1="0" y1="0" x2="0" y2="11" stroke="#3a332b" stroke-width="0.7" opacity="0.34"/>
    </pattern>
    <pattern id="sxHatch2" width="5" height="5" patternUnits="userSpaceOnUse"
             patternTransform="rotate(-42)">
      <rect width="5" height="5" fill="none"/>
      <line x1="0" y1="0" x2="0" y2="5" stroke="#3a332b" stroke-width="0.7" opacity="0.45"/>
    </pattern>
  </defs>
</svg>
"""

# ---------------------------------------------------------------- 漸層解鎖（這是一個真的缺陷）

# ★ 做樣張時量到的：`site/diagrams.js` 的 MLCC 有 **6 條漸層、12 個色值是寫死的 #hex**，
#   `--dg-*` 一個都換不掉（行號 705／707／709／710／711／712）：
#     mcL（左側陶瓷面）、mcCutB（切面 B 的陶瓷）、mcCovB（切面 B 的保護層）、
#     mcMetT／mcMetR／mcMetL（端電極金屬的上／右／左三個面）
#   症狀就是淺底樣張上那三塊**灰藍色的端子面** —— 底都換成米白了，它還留在深底時代的冷灰。
#   這正是 DECISIONS #198 那個病，只是這次發生在漸層的 stop 上。
#   `stop-color` 是**CSS 屬性**，所以沙盒可以用 CSS 蓋掉；正式採用時應該直接把
#   這 12 個值改寫成 var(--dg-*)，那才是根治。
#   ⚠ 科技與休閒兩張對照組**刻意不套**，好讓 Andy 看得到「現在真的長這樣」。
GRAD_FIX = """
  #mcL stop:nth-child(1){stop-color:var(--dg-cer-cut) !important}
  #mcL stop:nth-child(2){stop-color:var(--dg-cer-cut-2) !important}
  #mcCutB stop:nth-child(1){stop-color:var(--dg-cer-cut) !important}
  #mcCutB stop:nth-child(2){stop-color:var(--dg-cer-cut-2) !important}
  #mcCovB stop:nth-child(1){stop-color:var(--dg-cover-2) !important}
  #mcCovB stop:nth-child(2){stop-color:var(--dg-cover-2) !important}
  #mcMetT stop:nth-child(1){stop-color:var(--dg-sn) !important}
  #mcMetT stop:nth-child(2){stop-color:var(--dg-ni) !important}
  #mcMetR stop:nth-child(1){stop-color:var(--dg-ni) !important}
  #mcMetR stop:nth-child(2){stop-color:var(--dg-ni) !important}
  #mcMetL stop:nth-child(1){stop-color:var(--dg-ni) !important}
  #mcMetL stop:nth-child(2){stop-color:var(--dg-ni) !important}
"""

# ---------------------------------------------------------------- 八種 2D 風格

# 每一種寫成 (檔名, 說明, dgpal, CSS)。
# dgpal 是網站本來就有的四個配色之一；CSS 是這支腳本注入的覆寫。
STYLES_2D: list[tuple[str, str, str, str]] = [

    # ---- 1 科技：對照組。一個字都不注入（只凍結動畫，讓截圖可重現）
    ("2d-01-科技", "現行預設（data-dgpal=tech），當對照組", "tech", ""),

    # ---- 2 休閒：也是現成的，第二個對照組
    ("2d-02-休閒", "網站現有的 casual 配色（暖炭底＋琥珀），當第二個對照組", "casual", ""),

    # ---- 3 專業：技術文件／年報插圖
    ("2d-03-專業", "白底、低飽和、細線、零發光；Latin 走襯線", "tech", """
      :root{
        --dg-bg:#ffffff !important;
        --dg-ink:#16202e !important; --dg-ink-2:#3d4a5c !important; --dg-ink-3:#5d6b7d !important;
        --dg-mute:#8a97a6 !important;
        --dg-cer:#d2ccbe !important; --dg-cer-2:#bfb8a7 !important;
        --dg-cer-cut:#b8b2a2 !important; --dg-cer-cut-2:#a49d8c !important;
        --dg-cover:#e6e1d6 !important; --dg-cover-2:#d4cec1 !important;
        --dg-el:#58636f !important;
        --dg-sn:#c6cdd5 !important; --dg-ni:#98a0a9 !important;
        --dg-cu:#a2703c !important; --dg-resin:#7c7466 !important;
        --dg-pcb:#2f5e44 !important;
        --dg-accent-2d:#0f6b8c !important;
        --dg-frame-f:#f5f6f8 !important; --dg-frame-s:#ccd3dd !important;
        /* 語意色：色相一點都沒動（警語還是粉紅／裂紋還是紅），只把明度壓下去，
           不然 #ff4d6d 在白底上對比只有 3.0:1，「這是警告」就讀不出來。*/
        --dg-warn:#b0375a !important; --dg-err:#bb1026 !important;
        --dg-glow:none !important; --dg-hair-w:1.1 !important;
        --dg-chg-a:.10 !important;
      }
      /* 一張圖只有一個主色：環節色收成低飽和的工程藍灰 */
      .dg [data-seg], .dg .p3 { --c:#3a6182 !important; }
      /* Latin 走襯線、中文沒有可用的襯線 CJK（容器只有 WenQuanYi 黑體），
         所以實際效果是「數字與英文有襯線、中文是黑體」——「半襯線」。 */
      .dg text { font-family:"Liberation Serif",Georgia,"Noto Serif TC","WenQuanYi Zen Hei",serif !important; }
      .dg .tag, .dg .mono, .dgm .num { font-family:"Liberation Mono",monospace !important; }
      /* 細線：白底上沒有描邊的色塊會糊成一團 */
      .dg [data-seg] :is(path,rect,polygon,ellipse):not(.leader):not(.chg){
        stroke:#8d97a3 !important; stroke-width:.45 !important;
      }
      .dg [data-seg] .leader { stroke:#7c8896 !important; stroke-width:.8 !important; }
      .dg [data-seg] .part { stroke:#6f7b89 !important; stroke-width:.8 !important; filter:none !important; }
    """),

    # ---- 4 吉卜力／日系動畫
    ("2d-04-吉卜力", "暖紙底＋紙張顆粒、粉彩、手繪抖動的不規則邊", "tech", """
      :root{
        --dg-bg:#f2e9d6 !important;
        --dg-ink:#3a362c !important; --dg-ink-2:#5c564a !important; --dg-ink-3:#7b7466 !important;
        --dg-mute:#9a9284 !important;
        --dg-cer:#f0e2c2 !important; --dg-cer-2:#e2d0a8 !important;
        --dg-cer-cut:#e0cfa9 !important; --dg-cer-cut-2:#cdb98e !important;
        --dg-cover:#f8f0dd !important; --dg-cover-2:#e9ddc3 !important;
        --dg-el:#6e8190 !important;
        --dg-sn:#e4ecef !important; --dg-ni:#b3c1c7 !important;
        --dg-cu:#d3945a !important; --dg-resin:#a2917a !important;
        --dg-pcb:#7fa069 !important;
        --dg-accent-2d:#6ba6b8 !important;
        --dg-frame-f:rgba(255,252,242,.72) !important; --dg-frame-s:rgba(150,136,110,.42) !important;
        --dg-warn:#c04a6b !important; --dg-err:#c02a3c !important;
        --dg-glow:none !important; --dg-hair-w:1.3 !important;
        --dg-chg-a:.14 !important;
      }
      .dg [data-seg], .dg .p3 { --c:#7aa79c !important; }
      /* 紙張暈染：顆粒鋪在畫布底下，不碰文字 */
      #prodDiagram{
        background-color:#f2e9d6 !important;
        background-image:%%GRAIN_GHIBLI%%, radial-gradient(130% 100% at 30% 0%, #fbf5e6 0%, #ece0c6 100%) !important;
        background-blend-mode:multiply, normal !important;
      }
      /* 手繪抖動只給形狀，文字與引線不碰 */
      .dg [data-seg] :is(path,rect,polygon,ellipse):not(.leader):not(.bg){
        filter:url(#sxWobble) !important;
      }
      .dg [data-seg] .part { stroke:#8a7e68 !important; stroke-width:1.1 !important; }
      .dg [data-seg] .leader { stroke:#9a8f79 !important; stroke-width:1 !important; }
    """),

    # ---- 5 閱讀
    ("2d-05-閱讀", "米白紙底、字級整體放大、色塊少、引線細", "tech", """
      :root{
        --dg-bg:#f8f2e4 !important;
        --dg-ink:#211d17 !important; --dg-ink-2:#463f34 !important; --dg-ink-3:#665e50 !important;
        --dg-mute:#8f8677 !important;
        --dg-cer:#ddd2ba !important; --dg-cer-2:#cabda1 !important;
        --dg-cer-cut:#c8bb9f !important; --dg-cer-cut-2:#b4a688 !important;
        --dg-cover:#ece4d1 !important; --dg-cover-2:#dbd2bc !important;
        --dg-el:#5a5248 !important;
        --dg-sn:#d3cec3 !important; --dg-ni:#a49b8c !important;
        --dg-cu:#9c6a35 !important; --dg-resin:#7d7364 !important;
        --dg-pcb:#3d6144 !important;
        --dg-accent-2d:#1d6f79 !important;
        --dg-frame-f:rgba(255,253,246,.8) !important; --dg-frame-s:rgba(120,108,88,.34) !important;
        --dg-warn:#a8334f !important; --dg-err:#b01324 !important;
        --dg-glow:none !important; --dg-hair-w:1.1 !important;
        --dg-chg-a:.09 !important;
        /* 字級整組往上一階：這是「閱讀」跟「專業」唯一的結構性差別 */
        --dg-fs-ttl:19px !important; --dg-fs-hd:15px !important;
        --dg-fs-lbl:14px !important; --dg-fs-min:13px !important;
      }
      .dg [data-seg], .dg .p3 { --c:#2b6a72 !important; }
      #prodDiagram{
        background-color:#f8f2e4 !important;
        background-image:%%GRAIN_READ%% !important;
      }
      .dg [data-seg] .leader { stroke:#8b8272 !important; stroke-width:.85 !important; }
      .dg [data-seg] .part { stroke:#7d7464 !important; stroke-width:.8 !important; filter:none !important; }
      .dg text { letter-spacing:.015em !important; }
    """),

    # ---- 6 卡通
    ("2d-06-卡通", "粗黑外框、高飽和平塗、圓角、實心落影", "tech", """
      :root{
        --dg-bg:#fdf4dc !important;
        --dg-ink:#1d1a17 !important; --dg-ink-2:#3a342c !important; --dg-ink-3:#57503f !important;
        --dg-mute:#8a8270 !important;
        --dg-cer:#ffd98a !important; --dg-cer-2:#f0bd5f !important;
        --dg-cer-cut:#f5c86e !important; --dg-cer-cut-2:#e0a945 !important;
        --dg-cover:#fff0c2 !important; --dg-cover-2:#fadf9c !important;
        --dg-el:#4a5170 !important;
        --dg-sn:#dbe7f0 !important; --dg-ni:#93a3b3 !important;
        --dg-cu:#ef8e3c !important; --dg-resin:#9b7f5e !important;
        --dg-pcb:#34a86d !important;
        --dg-accent-2d:#2aa9c6 !important;
        --dg-frame-f:#fffaea !important; --dg-frame-s:#1d1a17 !important;
        --dg-warn:#d6295a !important; --dg-err:#e01b32 !important;
        --dg-glow:none !important; --dg-hair-w:1.8 !important;
        --dg-chg-a:.16 !important;
        --dg-fs-lbl:13px !important;
      }
      .dg [data-seg], .dg .p3 { --c:#f2a03c !important; }
      /* 粗黑外框：卡通風唯一不可少的那一件事。
         ★ 外輪廓粗、內部細節細 —— 第一版內外都給 2px，16 層電極就糊成一把黑梳子，
           而「交錯指狀電極」正是這張圖唯一要講的事。卡通的慣例本來也是這樣分兩階。*/
      .dg [data-seg] :is(path,rect,polygon,ellipse):not(.leader):not(.chg):not(.bg){
        stroke:#1d1a17 !important; stroke-width:1 !important;
        stroke-linejoin:round !important; stroke-linecap:round !important;
      }
      .dg [data-seg] .part { stroke:#1d1a17 !important; stroke-width:2.6 !important;
        filter:url(#sxToonShadow) !important; }
      .dg [data-seg] .leader { stroke:#1d1a17 !important; stroke-width:1.6 !important; }
      .dgm .frame { stroke-width:2 !important; rx:10 !important; }
      .dg .dgfold .fbar { stroke:#1d1a17 !important; stroke-width:2 !important; }
      .dg .ttl, .dg .lbl, .dgm .hd { font-weight:800 !important; }
    """),

    # ---- 7 豐富
    ("2d-07-豐富", "深底＋材質紋理與層次、多一階的配色、等角落影", "tech", """
      :root{
        --dg-bg:#0e1526 !important;
        --dg-ink:#f2f6ff !important; --dg-ink-2:#bfcbe6 !important; --dg-ink-3:#9aa9c8 !important;
        --dg-mute:#7d8aa4 !important;
        --dg-cer:#ddd2b6 !important; --dg-cer-2:#c2b795 !important;
        --dg-cer-cut:#bdb191 !important; --dg-cer-cut-2:#9f9476 !important;
        --dg-cover:#ece3c9 !important; --dg-cover-2:#d8cfb3 !important;
        --dg-el:#59657a !important;
        --dg-sn:#eaf0f6 !important; --dg-ni:#aab3bd !important;
        --dg-cu:#c4823f !important; --dg-resin:#7a7160 !important;
        --dg-pcb:#1d5138 !important;
        --dg-accent-2d:#f0b429 !important;
        --dg-frame-f:rgba(24,34,58,.72) !important; --dg-frame-s:rgba(150,178,225,.3) !important;
        --dg-glow:none !important; --dg-hair-w:2 !important;
        --dg-chg-a:.16 !important;
        --dg-sh0:#0b1120 !important; --dg-sh1:#111a30 !important;
        --dg-sh2:#0c1425 !important; --dg-sh3:#070d19 !important;
        --dg-part-mix:#33436d !important; --dg-line-mix:#26345a !important;
      }
      .dg [data-seg], .dg .p3 { --c:#57c8e0 !important; }
      /* 底層次：暈影 ＋ 細網格 ＋ 顆粒。資訊密度的「層次」從底開始做，不是加顏色 */
      #prodDiagram{
        background-color:#0e1526 !important;
        background-image:
          %%GRAIN_RICH%%,
          repeating-linear-gradient(0deg, rgba(120,150,210,.055) 0 1px, transparent 1px 28px),
          repeating-linear-gradient(90deg, rgba(120,150,210,.055) 0 1px, transparent 1px 28px),
          radial-gradient(120% 90% at 50% -10%, #18243f 0%, #0b1220 70%, #080d18 100%) !important;
      }
      .dg [data-seg] .part { stroke-width:1.2 !important;
        filter:drop-shadow(0 10px 16px rgba(0,0,0,.55)) !important; }
      .dg [data-seg] .leader { stroke-width:1.1 !important; }
      .dgm .frame { filter:drop-shadow(0 6px 10px rgba(0,0,0,.45)) !important; }
      /* 「豐富」在這張圖上只做得到「質感層次」，做不到「資訊層次」——
         多一層資訊要多畫東西，那是 tech-illustrator 的事，不是配色的事。
         所以這裡誠實地只做材質：陶瓷保留暖色、金屬保留冷色、中間拉開一階明度。*/
    """),

    # ---- 8 素描／線稿
    ("2d-08-素描", "只有線沒有面；暗部走交叉線影；紙底＋手繪抖動", "tech", """
      :root{
        --dg-bg:#f5f1e6 !important;
        --dg-ink:#241f18 !important; --dg-ink-2:#463f34 !important; --dg-ink-3:#635b4e !important;
        --dg-mute:#8b8375 !important;
        --dg-accent-2d:#3a332b !important;
        --dg-frame-f:transparent !important; --dg-frame-s:#8d8474 !important;
        --dg-warn:#a02b48 !important; --dg-err:#a8121f !important;
        --dg-glow:none !important; --dg-hair-w:1 !important;
        --dg-fs-min:12.5px !important; --dg-fs-lbl:13px !important;
      }
      .dg [data-seg], .dg .p3 { --c:#3a332b !important; }
      #prodDiagram{
        background-color:#f5f1e6 !important;
        background-image:%%GRAIN_SKETCH%% !important;
      }
      /* 面 → 線。原本用漸層填的「切面」改吃交叉線影，暗部才留得下來
         （靠 [fill^="url("] 認出來，不必知道每一張圖的漸層叫什麼名字） */
      .dg [data-seg] :is(path,rect,polygon,ellipse,circle):not(text){
        fill:none !important; stroke:#3a332b !important; stroke-width:.85 !important;
        stroke-linejoin:round !important;
      }
      .dg [data-seg] [fill^="url("]{ fill:url(#sxHatch) !important; }
      /* 薄斷面塗實 —— 這是工程手繪本來就有的慣例（太薄的剖面不畫線影，直接塗黑）。
         不塗的話 16 層電極只剩 16 圈細框，整張圖最重要的那件事就不見了。*/
      .dg [data-seg] [fill="var(--dg-el)"]{ fill:#4a4237 !important; stroke:none !important; }
      .dg [data-seg] .part { stroke:#241f18 !important; stroke-width:1.15 !important; filter:none !important; }
      .dg [data-seg] .leader { stroke:#6b6355 !important; stroke-width:.8 !important; }
      .dg [data-seg] .dot { fill:#3a332b !important; }
      .dg [data-seg] :is(path,rect,polygon):not(.leader):not(.bg){ filter:url(#sxWobbleS) !important; }
      .dgm .frame { fill:none !important; stroke:#8d8474 !important; stroke-width:.9 !important; }
      .dg .dgfold .fbar { fill:none !important; stroke:#8d8474 !important; }
      .dg .chg { fill:none !important; }
    """),
]

# ---------------------------------------------------------------- 兩種 3D 風格

# 3D 的打光參數寫在 `.dg3d{}`，所以覆寫一律掛 `#prod3d`（id 贏 class）。
CSS_3D_PIXAR = """
  #prod3d{
    /* 打光：主光拉亮、補光拉高（暗面不要死黑）、半球光拉高（環境光包覆感）*/
    --dg-key:1.92 !important; --dg-fill:.92 !important; --dg-hemi:1.22 !important;
    /* ★ sat 第一版開到 1.34，托盤那個本來就偏紫的底色直接被推成糖果紫，
       跟暖色背景打架。皮克斯的做法是「統一色溫」不是「拉飽和」，
       所以飽和收回 1.10，改用 mix 把全場往奶油色拉 0.24。*/
    /* ★★ 第二次調整：sat 1.10 還是不夠 —— 根因不是飽和，是**3D 的零件底色來自環節色**
       （three3d.js 的 kit(THREE, hex) 那個 hex 就是 segColor），
       所以「十個環節十個顏色」，整台機櫃是糖果紫。沙盒碰不到那個色，
       但 applyPal 的 sat 與 mix 碰得到：**把飽和壓到 .62、再往奶油色拉 .34**，
       等於在不改 JS 的前提下把十個色相收成一個色溫 —— 那才是皮克斯的做法
       （皮克斯是「少數幾個受控的色相 ＋ 很講究的打光」，不是「把顏色調很鮮」）。*/
    --dg-sat:.62 !important;
    --dg-mix:#f3dcbb !important; --dg-mix-k:.34 !important;
    --dg-led:.9 !important;
    --dg-1:#fbf1e2 !important; --dg-2:#d9c3a8 !important;     /* 攝影棚背景：暖色無縫背景紙 */
    /* 材質色整組換成「玩具塑膠」：明度高、飽和高、彼此拉得開 */
    --dg-alu:#dfe7f2 !important; --dg-alu-2:#a8b7cc !important; --dg-alu-3:#8797ae !important;
    --dg-steel:#e2e8ef !important; --dg-steel-2:#aab5c2 !important;
    --dg-cu:#e59a4e !important; --dg-cu-lit:#f6b96c !important; --dg-cu-dim:#c07a35 !important;
    --dg-die:#5c6fd0 !important; --dg-si:#6a7ce0 !important; --dg-si-2:#4455b0 !important;
    --dg-pcb:#2f9e6b !important; --dg-pcb-2:#238156 !important;
    --dg-sn:#f2f6fa !important; --dg-ni:#c3ccd6 !important;
    --dg-emc:#4a4a58 !important; --dg-metal-2:#b6c0cb !important;
    --dg-frame:#3f4a62 !important; --dg-void:#2a3145 !important;
    --dg-mag:#8a6fd0 !important; --dg-oil:#f0c765 !important;
    --dg-cold:#4ea8dc !important; --dg-hot:#e8854a !important;   /* ★ 語意色照原值，不准被風格吃掉 */
    background:radial-gradient(125% 100% at 50% 6%, #fffaf1 0%, #f0dfc6 52%, #cfae8b 100%) !important;
  }
  /* 柔和高光。整場泛光是這個風格的代價，k3 壓在 0.42 是刻意的 —— 見 DEFS_SVG 的註解 */
  #prod3d canvas{ filter:url(#sxBloom) saturate(1.08) contrast(1.03) !important; }
  /* 暖底上的標籤要換成淺色卡片，不然是深底樣式貼在亮底上 */
  #prod3d .lbl3d{
    background:rgba(255,252,246,.94) !important; border-color:rgba(120,92,58,.4) !important;
    color:#2e2820 !important; box-shadow:0 6px 16px -8px rgba(90,60,30,.55) !important;
  }
  #prod3d .lbl3d :is(b,strong,.t){ color:#1d1913 !important; }
"""

CSS_3D_PIXEL = """
  #prod3d{
    /* ★ 量化只有 20 色，**背景漸層會吃掉一半的色票**（第一版就是這樣，整台機櫃
       只剩三階灰褐）。所以背景改成一個純色，20 色全部留給模型。*/
    /* ★★ 第二次調整：像素圖靠的是**明度階差**不是飽和 —— 主光拉到 2.2、補光壓到 .25，
       每一面的亮暗才拉得開，量化之後才看得出「這是一個方塊」。
       第一版 fill .62 讓每一面亮度都差不多，馬賽克之後就糊成一坨。*/
    --dg-key:2.2 !important; --dg-fill:.25 !important; --dg-hemi:.4 !important;
    --dg-sat:1.7 !important;
    --dg-mix:#4fd0ff !important; --dg-mix-k:.16 !important;   /* 往青色收，離開那片洋紅 */
    --dg-led:1.3 !important;
    --dg-1:#1b1440 !important; --dg-2:#1b1440 !important;
    --dg-alu:#9aa6d8 !important; --dg-alu-2:#5b63a0 !important; --dg-alu-3:#3f4578 !important;
    --dg-steel:#b9c2e6 !important; --dg-steel-2:#6a73a8 !important;
    --dg-cu:#e08a3c !important; --dg-cu-lit:#f5b455 !important; --dg-cu-dim:#a85f22 !important;
    --dg-die:#4b6ad8 !important; --dg-si:#5a7ce8 !important; --dg-si-2:#2f43a0 !important;
    --dg-pcb:#2aa35e !important; --dg-pcb-2:#1b7443 !important;
    --dg-emc:#3a3050 !important; --dg-metal-2:#a6b0d0 !important;
    --dg-frame:#4a3f78 !important; --dg-void:#191233 !important;
    --dg-cold:#4ea8dc !important; --dg-hot:#e8854a !important;   /* ★ 語意色照原值 */
    background:#1b1440 !important;      /* 純色，不是漸層 —— 見上面那段註解 */
  }
  /* 截圖前先把顏色推開，量化才切得出分明的色階（這一步在瀏覽器做，PIL 只負責馬賽克） */
  #prod3d canvas{ image-rendering:pixelated !important;
    filter:saturate(1.6) contrast(1.38) brightness(1.02) !important; }
  /* 標籤改成「復古電玩對話框」：直角、粗邊、無陰影、無圓角。
     ★ 字級不動 —— 12px 是紅線，像素風不是把字變小的藉口。 */
  #prod3d .lbl3d{
    background:#17123a !important; border:2px solid #cfd6ff !important; border-radius:0 !important;
    box-shadow:none !important; color:#e8ecff !important;
  }
  #prod3d .chip3d{ border-radius:0 !important; border-width:2px !important; }
"""

# ---------------------------------------------------------------- 量測


MEASURE_2D = """() => {
  const svg = document.querySelector('#prodDiagram svg');
  if (!svg) return {err:'找不到 SVG'};
  let min = 1e9, minTxt = '';
  svg.querySelectorAll('text').forEach(t => {
    if (!t.textContent.trim()) return;
    const bb = t.getBoundingClientRect();
    if (bb.width < 0.5 || bb.height < 0.5) return;      // 收合起來沒顯示的不算
    const fs = parseFloat(getComputedStyle(t).fontSize);
    if (fs < min) { min = fs; minTxt = t.textContent.trim().slice(0, 18); }
  });
  const cs = getComputedStyle(document.documentElement);
  const wrapBg = getComputedStyle(document.querySelector('#prodDiagram')).backgroundColor;
  return {
    minFs: min === 1e9 ? null : min, minTxt,
    bg: cs.getPropertyValue('--dg-bg').trim(), wrapBg,
    err: cs.getPropertyValue('--dg-err').trim(),
    warn: cs.getPropertyValue('--dg-warn').trim(),
    accent: cs.getPropertyValue('--dg-accent-2d').trim(),
    nText: svg.querySelectorAll('text').length,
  };
}"""

MEASURE_3D = """() => {
  const host = document.querySelector('#prod3d');
  if (!host) return {err:'找不到 #prod3d'};
  let min = 1e9, minTxt = '';
  host.querySelectorAll('.lbl3d, .lbl3d *').forEach(t => {
    const txt = (t.childNodes.length && t.childNodes[0].nodeType === 3)
      ? t.childNodes[0].textContent.trim() : '';
    if (!txt) return;
    const bb = t.getBoundingClientRect();
    if (bb.width < 0.5) return;
    const fs = parseFloat(getComputedStyle(t).fontSize);
    if (fs < min) { min = fs; minTxt = txt.slice(0, 18); }
  });
  const cs = getComputedStyle(host);
  return {
    minFs: min === 1e9 ? null : min, minTxt,
    key: cs.getPropertyValue('--dg-key').trim(),
    fill: cs.getPropertyValue('--dg-fill').trim(),
    hemi: cs.getPropertyValue('--dg-hemi').trim(),
    sat: cs.getPropertyValue('--dg-sat').trim(),
    cold: cs.getPropertyValue('--dg-cold').trim(),
    hot: cs.getPropertyValue('--dg-hot').trim(),
    nLbl: host.querySelectorAll('.lbl3d').length,
    canvas: !!host.querySelector('canvas'),
  };
}"""


def _srgb(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lum(rgb) -> float:
    r, g, b = (_srgb(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _parse(col: str):
    col = (col or "").strip()
    if col.startswith("#"):
        h = col[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) >= 6:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    if col.startswith("rgb"):
        nums = [float(x) for x in col[col.index("(") + 1:col.index(")")].replace("/", ",").split(",")[:3]]
        return tuple(int(n) for n in nums)
    return None


def contrast(a: str, b: str):
    ca, cb = _parse(a), _parse(b)
    if not ca or not cb:
        return None
    la, lb = _lum(ca), _lum(cb)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


# ---------------------------------------------------------------- 像素化後製


def pixelate(src: Path, dst: Path, factor: int = 5, colors: int = 24) -> None:
    """降採樣 → 色彩量化 → 最近鄰放大。這就是像素風的全部，不必改 three.js。"""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    w, h = im.size
    small = im.resize((max(1, w // factor), max(1, h // factor)), Image.BOX)
    small = small.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    small = small.convert("RGB")
    im2 = small.resize((w, h), Image.NEAREST)
    im2.save(dst)


def overlay(base: Path, top: Path, dst: Path) -> None:
    from PIL import Image
    b = Image.open(base).convert("RGBA")
    t = Image.open(top).convert("RGBA")
    if t.size != b.size:
        t = t.resize(b.size, Image.NEAREST)
    Image.alpha_composite(b, t).convert("RGB").save(dst)


# ---------------------------------------------------------------- 主流程


def inject_grain(css: str) -> str:
    return (css
            .replace("%%GRAIN_GHIBLI%%", grain("#8a7a5a", 0.16, 0.85, 4))
            .replace("%%GRAIN_READ%%", grain("#7a6f59", 0.10, 0.95, 4))
            .replace("%%GRAIN_RICH%%", grain("#9fb4e0", 0.05, 1.1, 3))
            .replace("%%GRAIN_SKETCH%%", grain("#6d6353", 0.13, 0.8, 4)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只跑名字含這個字串的風格")
    ap.add_argument("--width", type=int, default=1440, help="視窗寬（不是輸出圖寬）")
    ap.add_argument("--out-width", type=int, default=1440, help="輸出 PNG 的寬度")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}/index.html"

    report: list[dict] = []
    errs: list[str] = []
    tmp = OUT / "_tmp"
    tmp.mkdir(exist_ok=True)

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")

            # 先量一次「圖到底多寬」，才算得出要多少 device_scale_factor 才輸出 1440
            pg = b.new_page(viewport={"width": args.width, "height": 1000})
            pg.goto(f"{base}#{VIEW_2D}", wait_until="networkidle")
            pg.wait_for_timeout(3000)
            w2d = pg.evaluate("() => document.querySelector('#prodDiagram').getBoundingClientRect().width")
            pg.close()
            dsf2d = round(args.out_width / w2d, 4)
            print(f"2D 容器寬 {w2d:.1f}px → device_scale_factor {dsf2d}（輸出 {args.out_width}px）")

            # ---------------- 2D 八張
            for name, desc, pal, css in STYLES_2D:
                if args.only and args.only not in name:
                    continue
                pg = b.new_page(viewport={"width": args.width, "height": 1000},
                                device_scale_factor=dsf2d)
                pg.add_init_script("try{localStorage.setItem('tw.dg3d','0');"
                                   f"localStorage.setItem('tw.dg3d.pal','{pal}');}}catch(e){{}}")
                pg.on("pageerror", lambda e, n=name: errs.append(f"{n}：{e}"))
                pg.goto(f"{base}#{VIEW_2D}", wait_until="networkidle")
                pg.wait_for_timeout(2600)
                pg.evaluate("html => document.body.insertAdjacentHTML('beforeend', html)", DEFS_SVG)
                # 漸層解鎖只給 3~8；科技與休閒是對照組，要維持「現在真的長這樣」
                pg.add_style_tag(content=FREEZE + (GRAD_FIX if css else "") + inject_grain(css))
                pg.wait_for_timeout(1200)
                m = pg.evaluate(MEASURE_2D)
                el = pg.query_selector("#prodDiagram")
                path = OUT / f"{name}.png"
                el.screenshot(path=str(path))
                m.update(name=name, desc=desc, pal=pal, file=str(path), kind="2D")
                m["對比_err_vs_底"] = contrast(m.get("err", ""), m.get("wrapBg", ""))
                m["對比_warn_vs_底"] = contrast(m.get("warn", ""), m.get("wrapBg", ""))
                report.append(m)
                print(f"✓ {name}　最小字級 {m.get('minFs')}px（「{m.get('minTxt')}」）")
                pg.close()

            # ---------------- 3D 兩張
            for name, desc, css, pixel in [
                ("3d-01-皮克斯", "打光／材質往圓潤有反光調，加柔和高光", CSS_3D_PIXAR, False),
                ("3d-02-像素", "降採樣＋24 色量化＋最近鄰放大；標籤保持清晰疊回去", CSS_3D_PIXEL, True),
            ]:
                if args.only and args.only not in name:
                    continue
                pg = b.new_page(viewport={"width": args.width, "height": 900},
                                device_scale_factor=1)
                # 先用 2D 進場（tw.dg3d=0），注入 CSS 之後再點 3D ——
                # three3d.js 的 applyPal() 只在掛載那一刻讀 CSS 變數
                pg.add_init_script("try{localStorage.setItem('tw.dg3d','0');"
                                   "localStorage.setItem('tw.dg3d.pal','tech');}catch(e){}")
                pg.on("pageerror", lambda e, n=name: errs.append(f"{n}：{e}"))
                pg.goto(f"{base}#{VIEW_3D}", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                pg.evaluate("html => document.body.insertAdjacentHTML('beforeend', html)", DEFS_SVG)
                pg.add_style_tag(content=FREEZE + css)
                pg.wait_for_timeout(400)
                pg.click("#dg3d")
                pg.wait_for_timeout(6500)
                m = pg.evaluate(MEASURE_3D)
                w3 = pg.evaluate("() => document.querySelector('#prod3d').getBoundingClientRect().width")
                path = OUT / f"{name}.png"

                if not pixel:
                    pg.query_selector("#prod3d").screenshot(path=str(path))
                else:
                    # ① 只有畫面（標籤藏起來）→ 像素化
                    pg.add_style_tag(content=".lbl3dLayer{visibility:hidden !important}")
                    pg.wait_for_timeout(500)
                    raw = tmp / "px-canvas.png"
                    pg.query_selector("#prod3d").screenshot(path=str(raw))
                    # ② 只有標籤（畫面藏起來、所有祖先底色透明）→ 透明底
                    pg.add_style_tag(content="""
                      .lbl3dLayer{visibility:visible !important}
                      #prod3d canvas{visibility:hidden !important}
                      #prod3d{background:transparent !important}
                      html,body,#app,.wrap,.card,.panel,#dgSec,#dgBody,.dgwrap,main,section{
                        background:transparent !important; background-image:none !important;}
                    """)
                    pg.wait_for_timeout(500)
                    lab = tmp / "px-labels.png"
                    pg.query_selector("#prod3d").screenshot(path=str(lab), omit_background=True)
                    pxd = tmp / "px-pixelated.png"
                    pixelate(raw, pxd, factor=6, colors=20)
                    overlay(pxd, lab, path)

                # 輸出寬度補到 out_width（3D 是 canvas，直接放大會糊，所以用 LANCZOS）
                if abs(w3 - args.out_width) > 2:
                    from PIL import Image
                    im = Image.open(path).convert("RGB")
                    k = args.out_width / im.width
                    rs = Image.NEAREST if pixel else Image.LANCZOS
                    im.resize((args.out_width, max(1, int(im.height * k))), rs).save(path)

                m.update(name=name, desc=desc, file=str(path), kind="3D")
                report.append(m)
                print(f"✓ {name}　最小字級 {m.get('minFs')}px（「{m.get('minTxt')}」）"
                      f"　標籤 {m.get('nLbl')} 個　canvas={m.get('canvas')}")
                pg.close()

            b.close()
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    (OUT / "_量測.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n---- 量測 ----")
    for r in report:
        if r["kind"] == "2D":
            print(f"{r['name']}：最小字級 {r.get('minFs')}px｜底 {r.get('wrapBg')}｜"
                  f"err {r.get('err')} 對比 {r.get('對比_err_vs_底')}｜"
                  f"warn {r.get('warn')} 對比 {r.get('對比_warn_vs_底')}")
        else:
            print(f"{r['name']}：最小字級 {r.get('minFs')}px｜key {r.get('key')} "
                  f"fill {r.get('fill')} hemi {r.get('hemi')} sat {r.get('sat')}｜"
                  f"冷 {r.get('cold')} 熱 {r.get('hot')}")
    if errs:
        print("\n⚠ 頁面錯誤：")
        for e in errs[:10]:
            print("  ·", e)
    print(f"\n輸出：{OUT}")
    return 0


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


if __name__ == "__main__":
    raise SystemExit(main())
