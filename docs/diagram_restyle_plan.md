# 剖析圖全面改風格 —— 執行排程（DECISIONS #238）

> Andy 2026-09-22：「針對所有圖片進行大改風格，麻煩執行到底。」
> 兩種模式：亮色「閱讀」／暗色「科技」。視覺語言見 DECISIONS #238。

## 範圍（機器盤點）
- 2D 量產剖析圖：**17 張**（`site/dg/*.js` 14 張 ＋ `diagrams.js` 的 MLCC、AI 伺服器鏈層級圖，＋ 進行中的 3 張一般電子）
- 3D 場景：**3 個**（`three3d.js`：ai_server／semiconductor／mlcc）
- 題材頁 2.5D：**18 張**（`themes3d.js`，走 `chainScene`／`explodeScene` 樣板）

## 波次（每波最多 3 支 agent；上限是速率限制，不是人力）

| 波 | 內容 | 交付 |
|---|---|---|
| **0 地基** | ① 風格系統：`_STYLE.md`、兩套色票、共用元件卡片化（`labelRow`／`processBar`／引線／陰影）② 3D：兩套打光材質、根治環節色當底色、大件倒角、爆炸動畫 | 兩張對照樣板（MLCC、面板）亮／暗各一 |
| 1 | AI 伺服器鏈：液冷、氣冷、PSU＋BBU | 每張：爆炸拆解 ＋ 收進 ≤700 ＋ 兩模式 |
| 2 | AI 伺服器鏈：ABF 載板、硬板 PCB、交換器板卡、高速互連 | 同上 |
| 3 | 半導體鏈：先進封裝、晶圓代工、矽晶圓 | 同上 |
| 4 | 半導體鏈：HBM、第三代半導體；一般電子：MLCC、面板 | 同上 |
| 5 | 一般電子：被動 RLC ＋ 進行中三張（工業自動化、鋁電容、電路保護） | 同上 |
| 6 | 傳產／基建：輕油裂解、變壓器 GIS；AI 伺服器鏈層級圖（`diagrams.js`） | 同上 |
| 7 | 題材頁 18 張 2.5D：先改 `chainScene`／`explodeScene` 樣板（一次 18 張跟著變），再逐張補細節 | |

每波做完就合併、驗、推、部署，Andy 可以一波一波看。
**每張圖交付時附：亮／暗兩張 1440 截圖、收合高度、12px 與對比度量測、既有互動全過。**

## 3D 補充（Andy 2026-09-22 稍後；細節見 DECISIONS #238「3D 補充」）
- 半透明／霧面玻璃機櫃外框；托盤三色分區（訊號藍 `--dg-sig`／電力橘 `--dg-pwr`／液冷青綠 `--dg-cool`）
- 液冷／CDU、光模組／CPO 的**發光流線**（`flow` 材質；靜止時要停）；風扇**氣流細線**（`airflow`）
- 托盤**半拉出**（抽屜式，不是全散開）；PCB 上晶片看得見；留白
- 卡片磨砂玻璃、引線發光端點、**卡片與元件同色系串聯**（`--dg-card-c` ← `data-dgcolor`，2D／3D 共用介面）
- 併進 **0 地基**：style-system 出卡片／引線／三組語意色，style-3d 出 `glass`／`flow`／`airflow` 材質並先拿 AI 伺服器機櫃當範本

## 版面補充（Andy 2026-09-22：左右對齊、填滿、依螢幕寬變化；細節見 DECISIONS #238「版面補充」）
- 卡片在畫布**左右兩欄**，`.dgwrap` 用 grid 填滿容器；≥1280 兩欄卡片、960–1279 右欄、<960 單欄
- 不放大 SVG 去填（高度會破 700）；標題列／章節列／卡片欄與畫布左緣對齊；引線 resize 重算
- 2D／3D 共用同一組 grid class

## 每張圖的固定驗收（寫進各自的 `_uitest.py` 段落）
1. 兩種模式各切一次 → 底色、卡片、引線真的變
2. 收合 ≤ 700px、章節列打得開收得回、全開文字變多（沒刪內容）
3. 點零件只亮不篩、點背景恢復、小卡「誰做的」正確
4. 12px 下限（閱讀 13px）；對比度正文 ≥ 4.5、次要 ≥ 3
5. 800／390 不溢出

## 卡片介面（2D／3D 共用；art-director 2026-09-22 訂，style-3d 照這個餵）

規格全文在 `docs/diagram_specs/_STYLE.md` §3～§5。這裡只寫「兩邊怎麼接」。

### 卡片的元件色 `--dg-card-c`

| 誰 | 怎麼餵 | 讀到的地方 |
|---|---|---|
| 2D（`diagrams.js`） | `labelRow`／`lrow3`／`note` 的群組上寫 `data-dgcolor="#xxxxxx"`，或 inline style `--dg-card-c:#xxxxxx`；`stampParts()` 會把 `data-dgcolor` 搬成 inline 的 `--dg-card-c` | `STYLE` 的 `.lrow{--card-c:var(--dg-card-c,var(--cc,var(--dg-ink)))}`；HTML 卡片 `.dgc` 同一條 |
| 3D（`three3d.js`） | 在 `.lbl3d` 那個 div 上 `style.setProperty('--dg-card-c', hex)`；引線端點 `.ld-dot` 也給同一個 `--dg-card-c`（或 inline stroke） | `index.html` 的 `.lbl3d{--card-c:var(--dg-card-c,var(--c,var(--dg-ink)))}`、`.lead3d .ld-dot` 的光暈色 |
| 沒餵 | 落回環節色（2D 是 `--cc`，3D 是 `--c`），再沒有就 `--dg-ink` | |

用到 `--card-c` 的地方（兩邊一樣）：左側 3px 色條、編號圓點（科技實心／閱讀粉彩底＋色環）、
邊框（跟 `--dg-card-s` 混 40%，選到時 100%）、選到時的底染（12%／主角 26%）、引線選到時的線色、引線端點的光暈。

### 磨砂玻璃

- HTML 卡片（`.lbl3d`、`.dgc`、零件小卡）：`background:var(--dg-card-f)` ＋ `backdrop-filter:var(--dg-card-blur)`。
  不支援 backdrop-filter 的瀏覽器自然退回半透明實色。
- SVG 卡片（`.lrow rect.bg`）：只有半透明實色（`--dg-card-f`）—— backdrop-filter 對 SVG 元素無效。
- 科技：`rgba(14,20,36,.66)` ＋ `blur(8px) saturate(1.15)`（偏冷）；閱讀：`rgba(255,255,255,.80)` ＋ `blur(10px)`（霧面白）。

### 引線與端點

- 2D：`D.pointer(ax, ay, bx, by, {elbow, drop, node})`；v2 版面由 `externalize()` 在 `.dglead` 疊層上畫，resize 重算。
- 3D：`.lead3d .ld`（線）吃 `--dg-lead`／`--dg-lead-w`；`.lead3d .ld-dot`（端點）科技帶 `--dg-node-glow` 的光暈、閱讀 `filter:none`。
- 端點顏色＝元件色；有編號時端點就是編號圓點。

### 語意色三組（3D 托盤分區也用這三個）

`--dg-sig`（訊號藍）、`--dg-pwr`（電力橘）、`--dg-cool`（液冷青綠），兩種模式各一套（`_STYLE.md` §1-B 有對比度表）。
`--dg-sw-sig`／`--dg-sw-pwr` 是別名，值就是前兩個。

### 3D 打光 token（`index.html` 的 `.dg3d[data-pal]`）

`tech`＝`.dg3d` 的預設值（沒動）；`read`＝`--dg-1:#f7f6f2 --dg-2:#e2dfd6 --dg-mix:#f2ede3 --dg-mix-k:.14 --dg-sat:.72 --dg-led:0 --dg-sel-em:0 --dg-hemi:.95 --dg-key:1.25 --dg-fill:.5`
是一組能跑的起始值，細調是 style-3d 的事。`three3d.js` 的 `PALS` 只認 `tech`／`read`。

## 逐張改造時的起點：§1 高度與建議切法（dg-scale 量的，2026-09-22）
`§1` ＝ 永遠看得到那一段的底部（viewBox 單位，上限 560）。標 ★ 的超過 560，**收納收不到，改風格時要順手把主圖壓矮**。
切點就是各檔原始碼裡 `<!-- ===== -->` 的分區註解。機制（`D.fold()`、`wireFolds` 自動量 `getBBox`）已在 main；
13 張的收納草稿與 `批次22-剖析圖尺寸` 棘輪表留在 `claude/dg-scale` 的 `847838d`，可以撿來當起點，不必從頭切。

| 圖 | §1 | 章節數 | 建議切法 |
|---|---|---|---|
| 電感電阻石英 | 278 | 2 | ② 三欄剖面｜③ 共同的尺＋兩個電流＋結論框 |
| 高速互連 | 282 | 2 | ② 2×2 四格｜③ 底部損耗對照條 |
| 液冷 | 467 | 3 | ③ 迴路｜④⑤ 均熱片 vs VC＋三種做法｜⑥⑦ 結論框＋流程列 |
| 面板 | 471 | 2 | ③④⑤ 三個放大區｜⑥ 製程＋兩結論框＋標示 |
| 氣冷風扇 | 483 | 3 | ③④⑤ 軸承四型＋軸流 vs 離心＋P-Q｜⑥⑦ 氣流路徑＋混合散熱與噪音｜⑧⑨ 說明框＋流程列 |
| 硬板 PCB | 502 | 3 | ②③ 四種孔＋走線｜④ 材料｜⑤ 製程五格＋兩結論＋誰做的 |
| 交換器板卡 | 502 | 3 | ② 層數為什麼多｜③ 800G 光模組＋價值鏈流程列｜④ 可插拔 vs CPO |
| 輕油裂解 | 529 | 2 | ⑤⑥ 四支基本原料與下游｜結論框＋製程列＋誠實性標示 |
| 第三代半導體 | 551 | 2 | ② 能隙帶狀圖＋長晶到切片＋流程列｜結論框 |
| MLCC ★ | 570 | 3 | ② 端電極四層＋板彎裂｜③ 製程五格＋良率曲線｜④ 尺寸代號＋成分＋來源（main 上已是手寫章節） |
| 變壓器 GIS ★ | 591 | 2 | ④⑤⑥ 資料中心側＋工程統包｜結論框＋六格流程列＋標示 |
| ABF 載板 ★ | 606 | 2 | ③④⑤ 結論＋三格放大＋路線圖｜⑤ 製程五格＋台股掛零說明。右欄九列列距 49 → 44 可省 40px |
| 伺服器電源 ★ | 643 | 1 | 只放得下一段。機櫃虛線框 104～636 裡 104～186 是空的，但左邊設施欄佔同一水平帶，要改橫排或把托盤細節縮一階才壓得下去 |
| AI 伺服器機櫃 | 534 | 0 | 1220 寬舊圖，靠 `.dgw` 收進 984；改風格時直接重畫成 980 |
| 先進封裝 CoWoS | — | 4 | main 上已重畫（689） |

一句要留下來的：**「同一個畫面有兩種寬度，就要兩種都量」**（抽屜開／關）—— 1.366 倍那個 bug 是這樣逼出來的，不是看出來的。

## 3D ↔ style-system 的介面（`claude/style-3d`，2026-09-22）

3D（`site/three3d.js`）已經照 #238 ＋ 三個推薦改完；下面是兩邊約好的名字，**style-system 改共用 CSS 時照這組來，不要各寫一套**。

### 卡片（`.lbl3d`，DOM，three3d.js 產生）
| 介面 | 意思 | 誰寫 |
|---|---|---|
| `--c` ＝ `--dg-card-c`（行內樣式，兩個名字同值） | 這張卡片指到的**元件顏色**：有角色就是角色色（v3 五色系，見下），沒有就是材質族的底色；太暗的會先往 `--dg-lit` 提亮到編號圓點看得見 | 3D 餵、CSS 吃（邊框、編號圓點、引線、端點） |
| `data-dgcolor` | 同 `--c`（給量測與不吃 CSS 變數的地方） | 3D |
| `--seg`／`data-dgseg` | 環節色（segColor）。只用在 `.sel-part` 的外圈與零件本體的提亮，**不再當底色** | 3D |
| `data-dgno` ＋ `em.no3d` | 編號（01、02…） | 3D 餵、CSS 畫圓點 |
| `data-dgrole` | `sig`（訊號／網通）`opt`（光）`pwr`（電力／快接頭）`gpu`（運算晶粒）`ind`（NVSwitch）`cool`（CDU／manifold）`hot`（排熱）`cu`（紅銅／銅箔）或空字串 | 3D |
| `b small.en` | 英文標題（v3 §4 中英雙語），字級 12px、顏色 `--dg-ink-3` | 3D 餵、CSS 排 |
| `data-dgpart` | 零件身分（跟 2D 的 `data-part` 同一組 key） | 3D |
| 狀態 class | `.sel`（同環節）`.sel-part`（被點的那一顆）`.dim`（別的環節）`.hid`（轉到背面）`.below`（在底下那一排） | 3D |
| 文字顏色 | 合併 main 之後照 style-system：`--dg-ink`／`-2`／`-3`（跟 `html[data-dgpal]` 走；`setPal` 會把 html 的 data-dgpal 一起對齊） | CSS |

角色色的 token 在 `.dg3d{}`：`--dg-fl-sig/opt/pwr/gpu/ind/cool/cold/hot/cu/cu-2/trace/air`；
其中 `--dg-fl-sig/opt/pwr/cool` 寫成 `var(--dg-sig, …)` 那種形式，**style-system 若在 `:root` 定義 `--dg-sig`／`--dg-opt`／`--dg-pwr`／`--dg-cool`，3D 會直接吃它們**。

### 族群晶片列 ↔ 機櫃內元件的連線（v3 §5，style-system 畫線、3D 出端點）
`Rack3D.current` 上的三支：
- `pointOf(id)` → `{x, y, front, part, color}`：`id` 是零件 id（`ag_cdu`）或環節 id（`thermal`），回**視窗座標**（引線的終點）與那個零件的元件色；轉到背面 `front=false` 就不要畫線。
- `colorOf(id)` → 元件色（跟卡片的 `data-dgcolor` 同一個值，晶片上的發光小點用這個）。
- `partsOf(seg)` → 這個環節在場景裡的零件 id 清單（一個環節可能有好幾顆，例如 thermal → cdu／uqd／fan）。
每一幀零件在動（自轉、爆炸拆解），所以連線要在 rAF 裡重取 `pointOf`，不能存一次。

### 卡片欄（響應式，Andy 2026-09-22「版面需要左右對齊…會依據螢幕大小變化」）
容器 `#prod3d.dg3d` 掛 `.dgstage` ＋ 模式 class；**斷點看視窗寬度**（跟 style-system 的 media query 同一組數字），**欄寬看容器寬度**（側欄開著時容器比較窄，欄就縮到下限 220）：

| 模式 class | 視窗寬 | 版面 | 等價的 grid |
|---|---|---|---|
| `.dgstage--lr` | ≥ 1280 | `.dgstage-l` ＋ 畫布 ＋ `.dgstage-r` | `minmax(220px,1fr) minmax(0,984px) minmax(220px,1fr)` |
| `.dgstage--r` | 960～1279 | 畫布 ＋ `.dgstage-r`，卡片全部靠右 | `minmax(0,984px) minmax(220px,1fr)` |
| `.dgstage--below` | < 960（390 也是） | 畫布，卡片搬進 `.dgstage-b`（一欄、文件流），畫布上用編號圓點 `.ld-no` 標位置 | `1fr` |

欄寬＝那條 grid 解出來的值（`max(220, (容器寬 − 984) / 欄數)`）。
欄位塞不下時的順序（Andy 2026-09-22：「不准掉到下面」）：① 那一欄的卡片**收成一行**（`.compact`：標題＋英文＋前兩顆晶片；被點的那一張維持全開、滑過暫時展開）→ ② 收了還塞不下才往 `.dgstage-b` 排（畫布上補一個編號圓點）。
收起來／排到底下的狀態是**黏的**（自轉時投影點每幀都在動，不黏就會閃），欄寬、模式、選取變了才重算。
引線 `.lead3d` 每 4 幀重算一次，resize 時模式一變就重新取景（`fitCamera`）；模型吃畫布高度的 ~94%（v3 第二輪「畫布要把中欄填滿」）。

### 模式與 token
- `Rack3D.current.setPal('tech' | 'read')`；舊名字 `soft`／`casual` → `read`、`calm` → `tech`；沒指定就跟全站主題（淺色 → 閱讀）。
- 3D 專用 token 全部在 `index.html` 的 `.dg3d{}` 與 `.dg3d[data-pal="read"]{}`（打光、材質手感、玻璃、流線、角色色、陰影、卡片）。
- **材質色仍讀 `:root` 的 `--dg-*`**（#230：2D／3D 同一份）。閱讀模式下 3D 會讀這些 token，style-system 定義 `:root[data-dgpal="read"]` 時請一併給粉彩值，3D 就會自動跟上：
  `--dg-cer --dg-cover --dg-cu --dg-pcb --dg-si --dg-sn --dg-ni --dg-el --dg-organic --dg-emc --dg-alu --dg-steel --dg-frame --dg-au --dg-edge --dg-abf --dg-vap --dg-wick --dg-mute`
  （建議：板子鼠尾草綠 `#7fa08a`、矽霧藍 `#7f93b8`、銅赤陶 `#c98b63`、模封暖灰 `#8a847c`、金屬銀 `#b9bfc6`）。
  這批**沒有**在 3D 那一側另外寫第二份材質色 —— 那正是 #230 要防的事；所以在 root 的 read token 出來之前，閱讀模式的板子與矽是「去飽和的深色」而不是粉彩。

## 不做的事
- 不生點陣圖、不引入字型或 CDN
- 不動 `industry.js` 版面結構（已退回原本格式）
- 不動 `pipeline/groups/*.yaml`
