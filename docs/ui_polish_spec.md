# 桌面版介面精修規格（UI Polish Spec）

> Andy 的原話（2026-09-23，逐字）：
> 「桌面版本部分CEO 幫我安排 整體介面頁面UI 圖表 表格等等，優化的更好更平易靜人
>  包含滑動移動回饋等等效果都可以做出來讓使用者感受更好，若是不清楚如何製作網路找一下 ，
>  原來的版本先儲存，以免要退版」

本檔由 `art-director` 產出，**只寫規格與證據，沒有動任何前端程式碼**
（`site/index.html`／`site/app.js`／`site/industry.js` 當時有另一支 agent 在做手機改版，同時動會打架）。
實作由下一棒接手，所以每一條都寫成「照著做就能做出來」的形式。

---

## 0. 這份規格怎麼用

### 0.1 兩條紅線（違反就是白做）

1. **不准降低資訊密度。** 「更平易近人」不等於「變空、變少、變大塊」。
   現在看得到的每一則資訊，改完之後還要看得到。**收進摺疊／分頁／hover 可以（要有明顯入口），刪掉不行。**
2. **不准動資料口徑。** 這是視覺與互動的事，不是算法的事。任何一個數字的算法、單位、四捨五入都不准碰。

### 0.2 三條既有規矩（沿用，不重新討論）

- **紅漲綠跌是台股慣例，不准動**（`--rise` 是紅、`--fall` 是綠）。
  ⚠ 查到的國外設計指南一律說「綠漲紅跌是不可動搖的慣例」（見 §11 來源 A1），**那是美股的慣例，跟台股相反**。
  這份規格只調兩個顏色的**明度**讓它們在淺色主題讀得出來，**色相不動**（改動後色相差 ≤ 2°，見 §4.3）。
- **不引入新字型、新圖示庫、新 CDN**（Andy 公司網路擋 CDN，一切內建在 repo）。
  本規格所有建議都只用已經在用的字族與 CSS，**零新增外部資源**。
- **原來的版本先儲存**（Andy 明講）：實作前先開分支，並在 `DECISIONS.md` 記下「改動前的 token 值」，
  退版時直接把 §4 的「舊值」欄貼回去就還原。§4 的表格本身就是退版備份。

### 0.3 與「手機改版」那批的分界

手機改版那批（另一支 agent）動的是 **≤ 900px 的版面**：底部分頁列、卡片橫向滑動、搜尋列收合。
本規格動的是 **≥ 1024px 的桌面版**與**兩個主題共用的 token**。
⚠ **衝突處理**：`:root` 的 token（§4）兩邊共用，**以本規格為準**；
`@media (max-width:900px)` 內的規則本規格一律不碰。實作前先 `git pull`，確認手機那批已合併。

---

## 1. 稽核結果（證據）

**做法**：Playwright（Chromium 141）在 1440×950 走過 `#overview`／`#flow`／`#industry`／
`#industry/semiconductor`／`#stock/2330`／`#themes`／`#season`／`#delivery`／`#heatmap`，
深色與淺色各一輪，另加 800px 一輪。截圖在 `/tmp/ui-audit/`（`<主題>-<路由>.png`、
`<主題>-<路由>-full.png`、`<主題>-800-<路由>.png`），原始量測在 `/tmp/ui-audit/report.json`
與 `report800.json`。

⚠ 稽核環境的限制（看截圖時要知道）：本機伺服器沒有即時報價 API，所以頂部「即時」徽章顯示
`Failed to fetch`、大盤三張圖顯示「抓不到」。**那是環境造成的，不是 bug** ——
但它剛好暴露了 §7.4 的錯誤狀態設計問題，所以照樣列進來。

### 1.1 量到的十四個問題（照嚴重度排）

| # | 問題 | 量到的數字 | 影響 |
|---|---|---|---|
| A1 | **頂部導覽列在 1440px 就已經溢出，而且沒有任何看得出來的提示** | `.tabs` `scrollWidth − clientWidth` = **163～358px**，`overflow-x:auto`；`#flow` 與 `#industry` 溢出 352／358px | 「總覽」或「季節性」**整顆分頁被藏掉**：`dark-industry_semiconductor.png` 看不到「總覽」，`light-stock_2330.png` 看不到「季節性」。使用者不知道有東西被藏起來 |
| A2 | **股票代號字級 10.25px** | `.code` 實測 `font-size:10.25px`；全站 `font-size` 宣告有 **72 處 < 12px**，最小 8px | 代號是全站最常被掃描的欄位，卻是最小的字。Andy 講過「文字太小」 |
| A3 | **淺色主題的「跌」色對比只有 3.25:1** | `--fall:#0a9b6a` 對 `--bg:#f2f5fb` = **3.25**、對 `--panel-3` = 3.17、對白底 = 3.55（門檻 4.5） | 淺色主題下綠色跌幅數字讀不清楚。同組的 `--flat` 3.62、`--lime` 4.25、`--amber` 4.28、`--cyan` 4.56（非白底時 4.07）也都在邊緣 |
| A4 | **三階文字的第三階在兩個主題都不到 4.5:1** | 深色 `--ink-3:#6f7ea3` 對 `--panel` = 4.41、對 `--panel-2` = **4.09**；淺色 `--ink-3:#6a7896` 對 `--bg` = 4.06、對 `--panel-3` = **3.95** | 這是量最大的一階：單一頁面就有 **960 個** `.cat` 元素用它。說明文字、時間戳、次要指標幾乎全走這階 |
| A5 | **數字沒有等寬對齊** | 全站 `font-variant-numeric:tabular-nums` 只有 **2 處**；數值主要靠 `--mono` 字族頂著，但非 mono 的數字欄（漲跌幅、占比、KPI 大數字）沒有 | 數字欄位左右跳動、上下對不齊，一整排比不起來 |
| A6 | **完全沒有按下去的回饋** | 整份樣式表 `:active` 規則 **0 條** | 每一顆按鈕按下去都沒反應，要等畫面重畫才知道按到了。Andy 點名的「滑動移動回饋」第一個缺口 |
| A7 | **hover 是硬跳的** | 70 個 `:hover` 選擇器，其中 **57 個（81%）**的基底選擇器沒有任何 `transition` | 滑鼠掃過去顏色瞬間切換，像閃爍而不是回饋 |
| A8 | **`prefers-reduced-motion` 幾乎沒接** | CSS 只有 2 條（`.rbar .pb`、`.m3-pulse`），JS 2 處（`app.js:5194`、`three3d.js:6894`） | 關掉動效的使用者，剖析圖以外的地方照樣會動 |
| A9 | **看不見的鍵盤焦點** | `:focus-visible` 規則 2 條、`:focus` 3 條、`outline:0/none` 5 處；實測 `.tab` 聚焦後 `outline-width:0px` | 只用鍵盤的人完全不知道游標在哪 |
| A10 | **季節性熱力圖的格子字互相壓住** | 見 `light-season.png` / `dark-season.png`：每格塞兩行數字，格高約 14px、字約 8～9.5px | 「+3.4」跟下一行的「+2.1」黏成一團，這張圖是整站字最小、最糊的一塊 |
| A11 | **間距／圓角沒有尺度** | `border-radius` 用了 **9 種**（4/5/6/7/8/9/10/12/999px）；`gap` **11 種**（1~14px）；`padding` 數十種組合 | 每個元件看起來都差一點點，整體不像同一套系統。這是「不像專業儀器」最主要的來源 |
| A12 | **說明文字一行太長** | 多處段落量到寬度 640～1000px、字 13～13.7px，換算一行 **70～108 個字元**（中文更多） | 眼睛回行時找不到下一行的開頭 |
| A13 | **一張圖十種顏色** | 個股頁的指標膠囊列 11 顆，每顆一個不同色點與彩色邊框（見 `light-stock_2330.png`）；分類色盤 36 色 | 沒有重點。顏色應該用來分「開／關」與「哪一個被選中」，不是用來分「這是第幾顆」 |
| A14 | **錯誤狀態比內容還搶眼** | 頂部「即時：Failed to fetch」是紅框紅字膠囊，且會把導覽分頁擠掉（A1 的溢出在 `#flow` 變成 352px，比其他頁多 190px） | 一個次要的抓取失敗，視覺權重超過整個導覽 |

### 1.2 現況視覺變數表（`site/index.html` `:root`）

**全站色票（`--dg-*` 以外）** —— 括號內是我實測的對比值（前者對 `--panel`，後者對 `--panel-2`／`--panel-3`）：

| Token | 深色 | 對比 | 淺色 | 對比 |
|---|---|---|---|---|
| `--bg` / `--bg-2` | `#070b16` / `#0b1224` | 底 | `#f2f5fb` / `#e9edf7` | 底 |
| `--panel` / `--panel-2` / `--panel-3` | `#0f172b` / `#141e36` / `#1a2542` | 底 | `#ffffff` / `#f7f9fd` / `#eef2fa` | 底 |
| `--line` / `--line-2` | `#1e2a48` / `#2a3860` | 1.26 / 1.56 | `#dde4f1` / `#c2cde1` | 1.28 / — |
| `--ink` | `#e8eeff` | 15.37 / 14.27 | `#0f1830` | 17.59 / 15.68 |
| `--ink-2` | `#a9b6d6` | 8.79 / 8.16 | `#3f4e6d` | 8.33 / 7.42 |
| **`--ink-3`** | `#6f7ea3` | **4.41 / 4.09** ✗ | `#6a7896` | **4.43 / 3.95** ✗ |
| `--rise`（漲·紅） | `#ff4d6d` | 5.55 / 5.15 | `#dc2440` | 4.81 / **4.28** ✗ |
| **`--fall`（跌·綠）** | `#2ee59d` | 10.88 / 10.10 | `#0a9b6a` | **3.55 / 3.17** ✗ |
| `--flat` | `#8ea0c4` | 6.77 / 6.29 | `#7a879f` | **3.62 / 3.23** ✗ |
| `--cyan` | `#3ee0ff` | 11.30 / 10.49 | `#0b7fa6` | 4.56 / **4.07** ✗ |
| `--violet` | `#8b7bff` | 5.41 / 5.02 | `#5f4ddb` | 5.88 / 5.24 |
| `--amber` | `#ffb454` | 10.11 / 9.39 | `#b06a00` | **4.28 / 3.81** ✗ |
| `--lime` | `#c3ff5b` | 15.09 / 14.01 | `#4a8a15` | **4.25 / 3.79** ✗ |

**其他現有 token**：`--r:12px`、`--side-w:360px`、`--mono:"JetBrains Mono",...`、
`--glow`、`--shadow`、`--ontop`、`--chartbg`、`--topbar`／`--topbar-m`、`--grid`、`--drop`、
`--body-1`／`--body-2`、`--illus`。

**字級尺度（現況）**：`body 15.5px/1.6`；`h2 20px`、`h3 16.5px`、`h4 14.5px`、`small 12.5px`；
實際用到 **22 種** `font-size`，用最多的三種是 12.5px（57 處）、12px（48 處）、11.5px（38 處）。

**剖析圖那組 `--dg-*` 不在本規格的範圍內** —— 它已經有自己的一套（`docs/diagram_specs/_STYLE.md`，
深色＝科技／淺色＝閱讀兩套、語意色已量過對比）。本規格只要求一件事：
**§4 改了全站 token 之後，回頭確認 `--dg-*` 沒有被連帶影響**（`--illus`、`--dg-bg` 都是獨立值，理論上不受影響，但要驗）。

---

## 2. 版面與節奏

### 2.1 間距尺度

**現況**：`gap` 11 種、`padding` 數十種組合，沒有尺度（A11）。

**改成**：在 `:root` 定義**一組 8 階的間距尺度**，新寫的樣式一律用它；舊樣式**照 §9 的批次逐步收斂，不要一次全改**。

```css
:root{
  --s1:4px; --s2:6px; --s3:8px; --s4:12px; --s5:16px; --s6:24px; --s7:32px; --s8:48px;
}
```

對應關係（改的時候照這張表就位，**不准自己就近湊**）：

| 現況值 | 收斂到 | 用在哪 |
|---|---|---|
| 1、2、3、4px | `--s1` 4px | 同一行裡的圖示與文字、膠囊內的點與字 |
| 5、6、7px | `--s2` 6px | 同一組膠囊之間、表格儲存格的上下 padding |
| 8px | `--s3` 8px | 卡片內相鄰兩行、工具列按鈕之間 |
| 10、12px | `--s4` 12px | 卡片內兩個區塊之間、卡片的上下 padding |
| 14、16px | `--s5` 16px | 卡片的左右 padding、卡片與卡片之間 |
| 20、24px | `--s6` 24px | 區塊（section）之間 |
| 28、32px | `--s7` 32px | 頁面主要段落之間 |

**為什麼**：間距是「看起來是不是同一套系統」最大的來源。目前 10px 與 12px、6px 與 7px 混用，
單看每個元件都對，排在一起就是「差一點點」。查到的資料也指向同一件事：
資料密集的介面靠的是一致的節奏而不是加大留白（§11 來源 A2、A3）。

**怎麼驗**：`grep -oE '\bgap:[^;}]*' site/index.html | sort -u` 的結果**只剩 `var(--s?)` 與少數例外**；
例外要在該行加註解寫明為什麼。改完跑 `_preview.py`（多寬度溢出與文字重疊）。

### 2.2 欄寬與行長

**現況**：說明段落量到 640～1000px 寬、字 13～13.7px，一行 70～108 字元（A12）。

**改成**：所有「給人讀的整句話」（`.sub`、`.note`、`.kpinote`、`.qnote`、圖說、banner 內文）
加上 `max-width:68ch`。**表格、圖表、清單不加**（那些本來就要吃滿寬）。

```css
.sub,.note,.kpinote,.qnote,.banner p,.dgdesc{max-width:68ch}
```

**為什麼**：68ch 在中文約 34～40 個中文字，落在一般排版建議的舒適區。
限制的是「句子」不是「資料」——所以**不會降低資訊密度**，段落只是變窄，內容一個字都沒少。

**怎麼驗**：1440px 下量 `.sub` 的 `getBoundingClientRect().width / parseFloat(fontSize)`，
應該 ≤ 68；800px 下不受影響（本來就比 68ch 窄）。

### 2.3 卡片密度

**現況**：`.card` padding `12px 14px 10px`、`.kpi` `12px 14px`、`.tile` `12px 14px`，半徑 12/12/10px。

**改成**：三者統一成 `padding:var(--s4) var(--s5)`（12px 16px）、`border-radius:var(--r)`（12px）。
`.card` 底部那個 10px 改成 12px（現在上下不對稱是沒有理由的）。

**為什麼**：三種卡片是同一個層級的東西，應該長得一樣。

**怎麼驗**：`#overview` 截圖，三種卡片並排時上下內距目視一致；`_preview.py` 綠。

### 2.4 區塊之間的呼吸感

**現況**：`#overview` 一頁從上到下是 banner → 走勢圖三張 → KPI 列 → 候選 → 資金動力圖 → 輪動階段，
區塊之間沒有明顯的節奏差異，都靠卡片邊框分。

**改成**：
- 區塊與區塊之間 `margin-bottom:var(--s6)`（24px）；卡片與卡片之間 `gap:var(--s5)`（16px）。
  也就是**區塊間距要明顯大於卡片間距**（24 vs 16），讓人一眼分得出「這是新的一段」。
- 每個區塊給一個 **12px 的區塊標題列**（`h3` 16.5px ＋ 右側工具），標題與內容之間 `--s4`。

**為什麼**：現在所有間距都在 10～16px 之間，分不出層級。加大區塊間距不會減少資訊，
只是把同樣的東西分組分得更清楚。

**怎麼驗**：`#overview` 與 `#flow` 各截一張整頁圖，肉眼看得出「幾段」；
卷動一頁的資訊量**不准比改之前少**（截圖比對，同一個捲動位置看到的最後一個元件要一樣或更多）。

---

## 3. 字級與層次

### 3.1 尺度（**12px 是下限，不准破**）

**現況**：22 種字級，72 處宣告 < 12px，實測最小 8px（A2、A10）。

**改成**：收成 **7 階**，全部掛在 token 上。

```css
:root{
  --fs-xl:26px;   /* KPI 大數字（現在 26/27/34 三種 → 統一 26，唯一例外見下） */
  --fs-lg:20px;   /* h2 區塊大標 */
  --fs-md:16.5px; /* h3 卡片標題 */
  --fs-base:15px; /* 內文、分頁字（body 15.5 → 15，見下） */
  --fs-sm:13.5px; /* 次要內文、說明句 */
  --fs-xs:12.5px; /* 標籤、時間戳、表格內的次要欄 */
  --fs-min:12px;  /* ★ 硬下限。任何地方不得再小 */
}
```

對照現況的收斂表：

| 現況 | 收斂到 | 備註 |
|---|---|---|
| 34px / 27px / 26px | `--fs-xl` 26px | 只有「今日最重要的那一個數字」可以留 34px，其餘一律 26px |
| 22px / 20px | `--fs-lg` 20px | |
| 17px / 16.5px / 16px | `--fs-md` 16.5px | |
| 15.5px / 15px / 14.5px / 14px | `--fs-base` 15px | `body` 從 15.5 降到 15，讓 `--fs-sm` 13.5 有空間 |
| 13.5px / 13px | `--fs-sm` 13.5px | |
| 12.5px / 12px | `--fs-xs` 12.5px | |
| **11.5px / 11px / 10.5px / 10.25px / 10px / 9.5px / 8px** | **`--fs-min` 12px** | **這一列是本規格最重要的一項**（A2） |

⚠ **把 72 處小字一次升到 12px，一定會撐破一些版面**（那些版面是為 11px 排的）。
處理順序寫在 §9：第一階段**只升四個高頻位置**（`.code` 股票代號、`.cat` 新聞分類、
`.m` 次要說明、`.dlv-*`），其餘留到第二階段逐塊排版跟著改。

### 3.2 數字（`tabular-nums`）

**現況**：全站只有 2 處（A5）。

**改成**：
```css
:root{ --num:"JetBrains Mono","SFMono-Regular",Menlo,monospace; }
/* 所有會出現數字的地方 */
.kpi .v,.num,.pct,.money,td.num,th.num,.magrid .ma .v,.stage li .m,.hpanel .ms a .g,
table td,table th{ font-variant-numeric:tabular-nums; font-feature-settings:"tnum" 1; }
```
**所有數字欄一律靠右對齊**，代號欄用 `--mono` 且靠左。

**為什麼**：等寬數字讓同一欄的位數對齊，掃描時眼睛不用重新定位；
比整段換成等寬字族更好讀（§11 來源 B1、B2）。**這一項零風險、零版面影響**（字寬只會變一致，不會變大）。

**怎麼驗**：新增 `_uitest` 子測：抓任一數字欄相鄰兩列，量它們的
`getBoundingClientRect().right` 差值 **≤ 0.5px**（現在會差好幾 px）。

### 3.3 層次規則

一張卡片裡最多三階：**標題（`--fs-md` ＋ `--ink`）→ 數字（`--fs-xl`／`--fs-base` ＋ `--ink`）→
說明（`--fs-xs` ＋ `--ink-3`）**。不准出現第四階。
單位、百分號、「億」「檔」這種量詞一律比主數字小一階、用 `--ink-2`，**不要跟主數字同大小**。

**怎麼驗**：`#overview` 的 KPI 卡截圖，每張卡數得出來的字級 ≤ 3 種。

---

## 4. 配色與狀態

### 4.1 原則

- **一個畫面最多一個主色**（`--cyan`），其餘走灰階＋語意色。
  分類色盤（36 色）只給「圖表裡的資料系列」用，**不准拿來裝飾 UI 元件**（A13）。
- **深色主題用「底色變亮」表示層級**（`--panel` → `--panel-2` → `--panel-3`），不要靠陰影。這一條現況已經做對了，維持。
- **語意色的明度可以為底色重算，色相不准動**（這條沿用 `--dg-*` 已經拍板的規矩）。

### 4.2 要改的 token（**這張表同時就是退版備份**）

| Token | 主題 | 舊值 | 舊對比（panel / panel-2·3） | **新值** | 新對比 | 色相變化 | 理由 |
|---|---|---|---|---|---|---|---|
| `--ink-3` | 深 | `#6f7ea3` | 4.41 / 4.09 ✗ | **`#8493b8`** | **5.81 / 5.40** | 223°→223°（0） | 最大宗的一階文字（單頁 960 個元素），兩種底色都要過 4.5 |
| `--ink-3` | 淺 | `#6a7896` | 4.43 / 3.95 ✗ | **`#5b6884`** | **5.59 / 4.98** | 221°→221°（0） | 同上 |
| `--fall`（跌·綠） | 淺 | `#0a9b6a` | 3.55 / 3.17 ✗ | **`#07794f`** | **5.44 / 4.85** | 160°→158°（2°） | 淺色主題最嚴重的可讀性缺口 |
| `--rise`（漲·紅） | 淺 | `#dc2440` | 4.81 / 4.28 ✗ | **`#c81234`** | **5.85 / 5.21** | 351°→349°（2°） | 漲跌兩色要一起調，不然視覺重量會偏一邊 |
| `--flat` | 淺 | `#7a879f` | 3.62 / 3.23 ✗ | **`#5f6c85`** | **5.29 / 4.71** | 219°→219°（0） | 平盤色也是文字 |
| `--cyan` | 淺 | `#0b7fa6` | 4.56 / 4.07 ✗ | **`#0a6b8a`** | **6.03 / 5.37** | 195°→195°（0） | 主色當文字用（連結、強調）時非白底不過關 |
| `--amber` | 淺 | `#b06a00` | 4.28 / 3.81 ✗ | **`#8f5600`** | **6.00 / 5.35** | 36°→36°（0） | 警示色在淺色主題讀不出來 |
| `--lime` | 淺 | `#4a8a15` | 4.25 / 3.79 ✗ | **`#3f7512`** | **5.58 / 4.97** | 93°→93°（0） | 同上 |
| `--rise` | 深 | `#ff4d6d` | 5.55 / 5.15 ✓ | **不動** | — | — | 已達標 |
| `--fall` | 深 | `#2ee59d` | 10.88 / 10.10 ✓ | **不動** | — | — | 已達標 |

⚠ **`--violet` 上的白字**：深色主題 `.evbtn .n` 是白字印在 `#8b7bff` 上，實測 **3.29:1**（不過關）。
兩個修法，**選第一個**：字色改 `--ontop`（`#061018`）→ **5.82:1**；
（另一個是把底色壓深，但那會讓徽章在深底上消失，不要。）

⚠ **量測方法**（實作時要能重現）：WCAG 2.x 相對亮度公式，
`(L亮+0.05)/(L暗+0.05)`，底色取「往上找到的第一個不透明背景」。
`scripts/` 下可以放一支 10 行的算式驗證；本規格的每一個數字都是這樣算出來的。

### 4.3 兩個主題都要讀得出來（驗收門檻）

| 用途 | 門檻 | 依據 |
|---|---|---|
| 正文與數字（< 18.66px 或非粗體） | **≥ 4.5:1** | WCAG 2.2 AA |
| 大字（≥ 24px 或 ≥ 18.66px 粗體） | ≥ 3:1 | 同上 |
| 按鈕邊框、焦點環、圖表的線 | ≥ 3:1 | 同上（非文字對比） |
| 分隔線（`--line`） | ≥ 1.2:1 對面板 | 實測現況 1.26／1.28，**維持即可**，不要加深（加深會變成格線監獄） |

### 4.4 狀態色（三種狀態在兩個主題都要成立）

| 狀態 | 深色 | 淺色 | 用在哪 |
|---|---|---|---|
| 好／成功 | `--fall`（綠，台股＝跌，**所以「成功」不要用綠**） | 同左 | ⚠ **本站不設「綠＝好」**：綠色被漲跌佔用了。「成功／完成」一律用 `--cyan`＋文字說明 |
| 注意 | `--amber` | `--amber`（新值） | banner、暫定值、資料延遲 |
| 壞／錯誤 | `--rise`（紅，台股＝漲） | 同左 | ⚠ 同理，**錯誤不要只靠紅色**，一定要配文字或圖示，否則會跟「漲」混淆 |

**這是本站特有的取捨，要寫進 `DECISIONS.md`**：因為紅綠都被漲跌佔用，
**狀態一律「顏色＋文字」雙編碼**，不准只用顏色表達狀態。

---

## 5. 表格

**現況**：各頁量到 1～2 個 `<table>`，大量「表格狀」內容其實是 `div` 清單
（`.hpanel .ms`、`.stage li`、`.magrid`）。以下規則對兩者都適用。

### 5.1 對齊

| 欄型 | 對齊 | 字族 |
|---|---|---|
| 股票代號 | 靠左 | `--mono`，`--fs-min`（12px，從 10.25px 升上來） |
| 名稱／族群 | 靠左 | 內文字族 |
| 數值、漲跌幅、占比、金額 | **靠右**，`tabular-nums` | 內文字族 ＋ `tabular-nums` |
| 日期 | 靠左，`tabular-nums` | `--mono` |
| 標籤／狀態 | 置中或靠左 | 內文字族 |

**表頭對齊跟著欄內容走**（數字欄的表頭也靠右）。

### 5.2 斑馬紋 vs 分隔線

**改成**：**用細分隔線，不用斑馬紋**。
```css
table tr{border-bottom:1px solid var(--line)}
table tr:last-child{border-bottom:0}
```
**為什麼**：查到的資料兩邊都講得到 —— 斑馬紋在行數多、欄位多的表有幫助，
但**一旦表格有 hover／選取／停用等互動狀態，斑馬紋會跟這些狀態打架**，
而且量測研究顯示它對正確率沒有統計上顯著的改善（§11 來源 C1、C2）。
本站每一列都可以點（進個股頁），互動狀態比斑馬紋重要。

**例外**：季節性熱力圖那種「每格都有底色」的矩陣不適用本節，見 §6.4。

### 5.3 表頭吸頂

**現況**：全站有 13～14 個 `position:sticky` 元素，但表格表頭不在其中。

**改成**：
```css
table thead th{position:sticky; top:0; z-index:2; background:var(--panel);
  box-shadow:0 1px 0 var(--line-2)}
```
⚠ 頂部導覽列本身是 sticky 的，所以 `top` 要吃導覽列高度：
定義 `--topbar-h`（實測 `.tabs` 高 35px、`.evbtn` 34px，整條頂列約 58px），
表頭用 `top:var(--topbar-h)`。**這個值要用 JS 量一次寫回 CSS 變數，不要寫死**
（事件欄開關、錯誤徽章換行都會改變頂列高度 —— A14 就是實例）。

### 5.4 排序的視覺提示

**改成**：可排序的表頭 `cursor:pointer`；目前排序的那一欄，表頭文字用 `--ink`（其餘 `--ink-2`），
並在文字後面加一個 8px 的三角（`▲`／`▼`，用 `::after` 的 `content`，**不引入圖示庫**）。
未排序的欄位 hover 時才浮出一個淡的 `▲`（`opacity:.35`）。

**怎麼驗**：`_uitest` 加一段：點表頭 → 量第一列的內容**真的變了**（不是只驗有 class），
並量 `::after` 的 `content` 換了方向。

### 5.5 列 hover 與可點

```css
table tbody tr{transition:background var(--dur-fast) var(--ease)}
table tbody tr:hover{background:var(--row-hover)}
:root{--row-hover:#17213c}                        /* 深：對 panel 1.12:1 */
:root[data-theme="light"]{--row-hover:#eef2fa}    /* 淺：對 panel 1.12:1 */
```
**兩個主題都量到 1.12:1** —— 看得出來、但不會搶走文字。
**hover 不准位移、不准放大、不准加陰影**（現況 `.tile:hover{transform:translateY(-1px)}`
與 `.stage li:hover{transform:translateX(2px)}` 這兩條在列表裡要拿掉，
整列跳起來會讓相鄰的列跟著抖）。

### 5.6 資料很多時怎麼不糊掉

1. **列高固定**：`td{padding:var(--s2) var(--s3); line-height:1.45}` → 每列約 30px，不因內容長短跳動。
2. **長文字截斷**：名稱欄 `overflow:hidden;text-overflow:ellipsis;white-space:nowrap`，
   並加 `title` 屬性（滑上去看得到全文）。**這是「藏起來但有入口」，不是刪掉。**
3. **每 5 列加一條較明顯的分隔**（`tr:nth-child(5n) {border-bottom-color:var(--line-2)}`）——
   給眼睛一個定位點，比斑馬紋輕。
4. **超過 20 列就給表格容器 `max-height` ＋ 內捲**，配合 §5.3 的吸頂表頭。

---

## 6. 圖表

### 6.1 座標軸與格線的權重

**現況**：`axisStyle` 已經走 `CH.line`／`CH.ink3`／`CH.grid`，機制正確。

**改成**（只調權重，不動機制）：
- 格線：`--grid`，寬度 1px，**只留水平格線**，垂直格線拿掉（除非是時間對齊必要）。
- 軸線：`--line-2`，1px。
- 軸標籤：`--ink-3`（新值，見 §4.2）、`--fs-xs`（12.5px）、`tabular-nums`。
- **資料本身的線寬要明顯大於格線**：主系列 ≥ 2px，格線 1px。

**為什麼**：查到的一致說法是「把格線淡化成背景、把墨水留給資料」（§11 來源 D1、D2）。

### 6.2 tooltip

**現況**：`app.js:184` 的 `tip` 物件初始值寫死深色（`#141e36`／`#2a3860`／`#e8eeff`），
但 `refreshPalette()` 會在切主題時就地改寫成 `--panel-2`／`--line-2`／`--ink` ——
**機制是對的，初始值只是 fallback**。

**改成**：
- 形狀：`border-radius:var(--r)`（12px）、`padding:var(--s3) var(--s4)`、
  `box-shadow:0 8px 24px -12px var(--drop)`。
- 內容：**第一行是標的名稱＋代號，之後每一行「色點 ＋ 系列名 ＋ 靠右的值」**，值用 `tabular-nums`。
  漲跌值一律帶正負號。
- `confine:true`（現況已有，保留）—— tooltip 不准跑出容器。
- **hover 延遲 60ms 才顯示**，避免滑鼠掃過整排時 tooltip 狂閃。

**怎麼驗**：`_uitest` 對 `#overview` 與 `#flow` 各一張圖，滑到資料點上 → 量 tooltip 的
`getBoundingClientRect()` **完全落在圖表容器內**；切淺色主題再驗一次背景色 ≠ 深色。

### 6.3 圖例與標籤

- **圖例一律放在圖的上方或右側，不要放下方**（放下方會被卡片裁掉）。
- **每一個標籤都要指到圖上真的有的值**：標籤文字必須由資料產生，不准寫死示意文字。
- **標籤不准互相重疊或被裁掉**：ECharts 用 `labelLayout:{hideOverlap:true}`；
  SVG 手繪的圖（`diagrams.js`）維持既有的外側文字框做法。
- **輪動時鐘的左側標籤堆**（見 `light-flow.png`）：現在 13 個標籤擠在左邊一欄、
  引線互相穿越。改成**只給前 8 名直接標註，其餘靠 hover**（入口＝圖下方一行「其餘 N 個族群（滑過圖上的點看）」）。
  ⚠ 這一項會**改變畫面上一眼看到的資訊量**，所以要放第二階段，並且先截圖給 Andy 看。

### 6.4 季節性熱力圖（A10，單獨處理）

**現況**：每格兩行數字、格高約 14px、字約 8～9.5px，上下行黏在一起。

**改成**（三選一，**建議 B**）：
- A：格高加到 22px、字 12px、**每格只留一個數字**（另一個移到 tooltip）。→ 表變高，要捲。
- **B（建議）：每格只畫顏色不畫字，數字全部進 tooltip；另外在右側加一欄「年度合計」用 12px 數字。**
  → 顏色本來就是這張圖的主體，數字看不清等於沒有；合計欄補回「可以比大小」的能力。
- C：維持兩行但字升到 12px、格高 28px。→ 一屏放不下 40 個族群。

**⚠ 這一項踩到「不准降低資訊密度」的邊界**：B 把每格的數字藏進 tooltip。
我的判斷是**現在那些數字在 8px 且互相壓住的狀態下，本來就讀不到，等於已經不存在**，
藏進 tooltip 反而是把它變成「讀得到」。但這是**我自己的判斷，Andy 可能不同意** —— 見 §12。

---

## 7. 「滑動移動回饋」（Andy 特別點名的）

### 7.1 動效 token

```css
:root{
  --dur-fast:120ms;   /* hover、色彩變化 */
  --dur:180ms;        /* 展開、切換 */
  --dur-slow:240ms;   /* 面板滑入（上限） */
  --ease:cubic-bezier(.2,0,0,1);       /* 標準：進場快、收尾慢 */
  --ease-out:cubic-bezier(0,0,.2,1);
}
@media (prefers-reduced-motion:reduce){
  :root{ --dur-fast:0ms; --dur:0ms; --dur-slow:0ms; }
}
```

**為什麼是這幾個數字**：查到的設計系統與文章一致落在
「微互動 100～200ms、中型轉場 200～300ms、超過 500ms 就像卡頓」；
Material Design 3 的 `DurationShort3` 就是 **150ms**，指定用途正是
「按鈕按下回饋、膠囊選取、分頁指示器」（§11 來源 E1、E2）。
本站選 120／180／240 是在那個區間偏快的一端 —— **這是一個看盤工具，不是形象網站，
任何讓人等的動畫都是扣分**。**超過 240ms 的轉場一律不准**。

### 7.2 hover（要有分寸）

**現況**：70 個 hover 選擇器、81% 硬跳；三處會位移（A6、A7）。

**改成**：
- **只改這三樣：底色、邊框色、文字色。**
  `transition:background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease)`
- **不准 `transform`**（位移／放大／浮起）。現有的
  `.tile:hover{transform:translateY(-1px)}` 與 `.stage li:hover{transform:translateX(2px)}` **拿掉**。
- **不准改變元素尺寸**（`padding`、`font-size`、`border-width`）—— 那會讓旁邊的東西跟著動。
  要加邊框就用 `box-shadow:inset 0 0 0 1px`，不要改 `border-width`。

**為什麼**：hover 的工作是「告訴你這個可以點」，不是表演。整塊跳起來在密集列表裡會造成連鎖位移。

### 7.3 按下的回饋（現在完全沒有）

```css
button:active,.tab:active,.evbtn:active,.pill:active,.seg button:active,a.card:active{
  transform:scale(.985); transition:transform 60ms var(--ease);
}
@media (prefers-reduced-motion:reduce){
  button:active,.tab:active,.evbtn:active,.pill:active,.seg button:active,a.card:active{
    transform:none; background:var(--panel-3);
  }
}
```
**0.985 的縮放**：小到不會讓文字模糊，大到手指／眼睛感覺得到。
關閉動效時改成「底色壓深一階」**依然有回饋**（這一點很重要 ——
關動效不等於沒有回饋，只是回饋不用動的）。

⚠ **`scale` 會讓文字重新柵格化**，在 12px 的小字上可能糊一幀。
**所以只對「整顆按鈕」用，不對「表格列」用**；表格列按下去改成底色壓一階。

### 7.4 三種狀態長什麼樣

| 狀態 | 長相 | 現況問題 |
|---|---|---|
| **載入中** | 骨架（skeleton）：用 `--panel-2` 畫出跟真實內容**一樣尺寸**的灰塊，1.4s 的 `opacity:.5→1` 呼吸。**不准用轉圈圈**（轉圈圈沒有告訴你會長出什麼） | 現在圖表區在載入時是空白，看起來像壞掉 |
| **空資料** | 沿用現有 `.empty`（`min-height:160px`、置中、`--ink-3`），但**加一行「為什麼是空的」＋一顆可以做點什麼的按鈕**（重試／換條件） | 現在只有一句話，使用者不知道下一步 |
| **錯誤** | **不准用大紅框**。改成：`--amber` 的左側 3px 直條 ＋ `--panel-2` 底 ＋ 一行說明 ＋ 一顆「重試」。文字要說「哪一段資料沒拿到」，不是拋 `Failed to fetch` | A14：頂部「即時：Failed to fetch」是紅框紅字，視覺權重超過導覽列，還把分頁擠掉 |

**錯誤徽章專項（A14）**：頂部即時狀態徽章改成**固定寬度**（`min-width:0;max-width:180px` ＋ 截斷 ＋ `title`），
**不准因為錯誤訊息變長就把導覽分頁擠掉**。

### 7.5 捲動

- **頂部導覽列**：維持 sticky；捲動超過 8px 時加一條 `box-shadow:0 1px 0 var(--line-2)`
  （告訴你下面還有內容）。**不要在捲動時改變高度**（會造成整頁跳動）。
- **表頭吸頂**：見 §5.3。
- **淡出**：可橫向捲動的容器（導覽列、膠囊列、表格）兩端加遮罩，
  用 `mask-image:linear-gradient(90deg,transparent,#000 16px,#000 calc(100% - 16px),transparent)`，
  **捲到底時那一側的遮罩要消失**（用 `scroll` 事件切 class）。
- **A1 的導覽列溢出**：除了遮罩，**再加左右兩顆箭頭鈕**（`‹` `›`，純文字，不引入圖示庫），
  只在真的溢出時顯示。**這是第一階段最該做的一項** —— 現在是整顆分頁被吃掉且毫無提示。

### 7.6 切換分頁／切換資料的轉場

- **分頁切換**：內容區 `opacity:0→1`，`--dur`（180ms），**不准用左右滑入**
  （滑入會讓人以為資料在移動，而且在 12px 的密集表格上會糊）。
- **資料更新**（即時報價每分鐘刷新）：**只有變動的那一格閃一下**——
  `background` 從 `--rise`／`--fall` 的 12% 透明度淡回透明，`--dur-slow`（240ms）。
  **整張表不准重畫閃爍**。現況 `live.js` 已經只更新 `[data-live]` 標記過的格子，機制對，補上這層視覺即可。
- **⚠ 動效不准影響資訊的正確性**：轉場期間顯示的數字必須是「舊值」或「新值」，
  不准出現插值動畫（數字從 47,800 滾到 47,900 那種）。看盤的人截圖時會截到假的數字。

### 7.7 `prefers-reduced-motion`（硬性）

**現況**：CSS 只有 2 條、JS 2 處（A8）。

**改成**：
1. 全站兜底（放在樣式表最後）：
```css
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{
    animation-duration:.01ms !important; animation-iteration-count:1 !important;
    transition-duration:.01ms !important; scroll-behavior:auto !important;
  }
}
```
2. `html{scroll-behavior:smooth}` 現況寫死，被上面那條蓋掉 —— 正確。
3. JS 驅動的動畫（`app.js:5194`、`three3d.js:6894` 已做）**其餘一律補上同樣的檢查**，
   並且**要監聽變化**（`matchMedia(...).addEventListener('change',...)`），
   使用者中途改系統設定要立刻生效。
4. **關掉動效之後，回饋不准消失**，只是不用動的表達（見 §7.3）。

**為什麼**：WCAG 2.3.3 要求「互動觸發的動態效果要能關掉」，
標準做法就是 `prefers-reduced-motion`（W3C 技術文件 C39）（§11 來源 F1、F2）。

**怎麼驗**：`_uitest` 用 `page.emulate_media(reduced_motion="reduce")` 開一個 context，
點分頁切換 → 量切換前後兩幀的 `opacity` **一步到位**（沒有中間值）；
按鈕按下去 → 量 `background` **有變**（回饋還在）。

---

## 8. 鍵盤與焦點

**現況**：`:focus-visible` 2 條、`outline:0/none` 5 處，`.tab` 聚焦後 `outline-width:0px`（A9）。

**改成**：
```css
:root{ --focus:#3ee0ff; }                      /* 對 panel 11.30:1 */
:root[data-theme="light"]{ --focus:#0a5f7d; }  /* 對白底 7.13:1 */

:where(a,button,input,select,textarea,[tabindex]):focus-visible{
  outline:2px solid var(--focus);
  outline-offset:2px;
  border-radius:inherit;
}
```
- **所有 `outline:0` 的地方都要配一條 `:focus-visible`**（現有 5 處：`.search input`、
  `.livepop input`、`.cgpop #cgSearch`、`.chip input`、以及 `.rbar .dual input[type=range]` 已有）。
- `outline-offset:2px` 讓焦點環不會被元素自己的邊框吃掉。
- **焦點順序要跟視覺順序一致**：不准用正數 `tabindex`。
- **跳過導覽**：頁面第一個可聚焦元素是一個視覺隱藏的「跳到主要內容」連結，
  `:focus` 時才顯示（只有鍵盤使用者看得到，不影響版面）。
- **彈出層（`.livepop`、`.cfgpop`、`.morepop`、縮放層 `.zoomov`）**：
  開啟時焦點移進去、`Esc` 關閉、關閉後焦點回到觸發的按鈕。

**怎麼驗**：`_uitest` 新增一段「鍵盤走一遍」：從頁首連按 `Tab` 30 次，
每一次量 `document.activeElement` 的 `outline-width > 0`，**任何一次是 0 就算紅**；
並確認 30 次之內走得到主要內容（沒有被困在導覽列裡）。

---

## 9. 分階段

### 第一階段（先做）—— 投報率最高、風險最低

照這個順序做，**每做完一項就可以單獨部署**（符合 CLAUDE.md「做到一個段落就先部署」）。

| # | 項目 | 章節 | 風險 | 工作量 | 為什麼排這裡 |
|---|---|---|---|---|---|
| 1 | **數字全面 `tabular-nums` ＋ 數字欄靠右** | §3.2、§5.1 | **極低**（字寬只會變一致，不會變大） | 1～2h | 零風險，效果立刻看得到，整站數字突然「對齊了」 |
| 2 | **`--ink-3` 兩個主題各調一次** | §4.2 | **低**（只換兩個 token 的值） | 0.5h | 影響單頁 960 個元素，一改全站可讀性跳一階 |
| 3 | **淺色主題六個色 token 調明度** | §4.2 | **低**（色相不動，紅漲綠跌不變） | 1h | 淺色主題現在有六個顏色不到 4.5:1，這是「一堆字看不清」的根因 |
| 4 | **導覽列溢出：遮罩 ＋ 左右箭頭 ＋ 錯誤徽章限寬** | §7.5、§7.4 | **中**（要動頂列版面，手機那批也碰這裡 → 一定要等它合併後再做） | 3～4h | **整顆分頁被藏掉**是目前最嚴重的功能性缺陷 |
| 5 | **動效 token ＋ hover 過渡 ＋ `:active` 回饋** | §7.1～7.3 | **低**（只加 `transition`／`:active`，拿掉 3 條 `transform`） | 2～3h | Andy 點名的「滑動移動回饋」，做完手感差很多 |
| 6 | **`prefers-reduced-motion` 全站兜底** | §7.7 | **極低**（一條 media query） | 0.5h | 一條規則解決一整類問題 |
| 7 | **焦點樣式 ＋ 5 處 `outline:0` 補回** | §8 | **低** | 1～2h | 現在鍵盤完全沒辦法用 |
| 8 | **四個高頻小字升到 12px**（`.code` 10.25→12、`.cat` 11→12、`.m` 11.5→12、`.dlv-*` 11→12） | §3.1 | **中**（會撐開一些版面，要逐一驗 1440 與 800） | 2～3h | Andy 講過「文字太小」；`.code` 是全站最常掃描的欄位 |
| 9 | **表格：分隔線、列 hover、列高固定、表頭吸頂** | §5.2、§5.3、§5.5、§5.6 | **中**（`--topbar-h` 要用 JS 量，容易踩到頂列高度會變） | 3～4h | 表格是「資料密集但不糊」的主戰場 |

**第一階段合計約 14～20 小時**，可以拆成 4～5 次部署。

### 第二階段（之後再說）

| # | 項目 | 章節 | 風險 | 工作量 |
|---|---|---|---|---|
| 10 | 間距尺度 `--s1`～`--s8` 全站收斂 | §2.1 | **高**（要動幾十處樣式，每動一處就可能擠壞一個版面） | 8～12h |
| 11 | 字級尺度收成 7 階（剩下的 68 處小字） | §3.1 | **高**（同上，而且會連帶改版面） | 8～12h |
| 12 | 圓角收成 3 階（6／12／999px） | §2.1 | 中 | 2～3h |
| 13 | 卡片 padding／區塊節奏統一 | §2.3、§2.4 | 中 | 3～4h |
| 14 | 段落 `max-width:68ch` | §2.2 | 低 | 1h |
| 15 | 載入骨架、空資料、錯誤三態統一 | §7.4 | 中（要改每一個 render 函式的分支） | 6～8h |
| 16 | 圖表軸線／格線權重、tooltip 形狀與內容 | §6.1、§6.2 | 中 | 4～6h |
| 17 | **季節性熱力圖改版** | §6.4 | **高**（會改變一眼看到的資訊，要先給 Andy 看） | 3～4h |
| 18 | **輪動時鐘標籤只標前 8 名** | §6.3 | **高**（同上） | 3～4h |
| 19 | 排序視覺提示、長文字截斷＋`title` | §5.4、§5.6 | 中 | 3～4h |
| 20 | 彈出層焦點管理、跳過導覽連結 | §8 | 中 | 3～4h |
| 21 | 分類色盤不准裝飾 UI（指標膠囊列改單色） | §4.1、A13 | 中（Andy 可能習慣了現在的彩色） | 2～3h |

**第二階段合計約 46～67 小時。**

### 共同的風險（兩個階段都適用）

1. **`--dg-*` 那組剖析圖 token 不在本規格範圍**，但 §4 改了全站 token 之後
   **一定要回頭驗 19 張剖析圖在兩個主題下沒有變色**（`--illus`、`--dg-bg` 是獨立值，理論上不受影響）。
2. **`site/app.js` 有 132 處、`industry.js` 65 處、`chart.js` 70 處寫死的 6 碼色碼。**
   其中大部分是 `refreshPalette()` 的 fallback 預設值與分類色盤（分類色盤已有淺色版），
   機制是對的；但**改 token 之前要逐一確認哪些是「活的寫死值」**，
   不然會出現「CSS 改了、圖表沒跟著改」。
3. **手機改版那批同時在動 `index.html`／`app.js`／`industry.js`** ——
   第一階段的第 4、8、9 項一定要**等它合併後再開工**，否則必衝突。

---

## 10. 怎麼驗（每一項都要能跑）

### 10.1 每一批都要跑的

```bash
python scripts/_preview.py                      # 多寬度溢出與文字重疊，約 2 分鐘
python scripts/_uitest.py --only <對應段落>     # 照 CLAUDE.md 的對照表挑
```
**純前端改動可以跳過 `pytest`**（用 `git diff --name-only` 判斷，不准靠記憶）。

### 10.2 本規格要新增的 `_uitest` 段落

| 新段落名 | 驗什麼 | 紅的條件 |
|---|---|---|
| `UI-對比` | 走過 9 個路由 × 2 主題，量每個有文字的元素對其背景的對比 | 任何 `font-size < 18.66px` 的元素對比 < 4.5 |
| `UI-字級下限` | 同上，量 `font-size` | 任何可見文字 < 12px |
| `UI-數字對齊` | 每個數字欄取相鄰兩列，量 `getBoundingClientRect().right` | 差值 > 0.5px |
| `UI-導覽不被吃` | 1440／1280／1024／800 四個寬度，量 `.tabs` 每一顆分頁是否完整可見或有捲動提示 | 有分頁被裁且沒有提示 |
| `UI-焦點` | 連按 Tab 30 次，量 `activeElement` 的 `outline-width` | 任何一次 = 0 |
| `UI-關動效` | `emulate_media(reduced_motion="reduce")`，切分頁、按按鈕 | 有中間幀（有動）／或按下去完全沒回饋 |
| `UI-按下回饋` | 每一種按鈕 `mouse.down()` 後量樣式 | 樣式完全沒變 |

### 10.3 交付時要附的

**四張截圖：深色＋淺色 × 1440px＋800px**，加上逐條的過／不過清單，
以及**改了哪幾個 token（舊值 → 新值 ＋ 理由）** —— §4.2 的表格就是這份清單的格式。

⚠ **800px 一定要驗**（Andy 把瀏覽器縮成半邊就是這個寬度；2026-09-18 的 E6 縮圖 bug
就是只驗寬螢幕放過去的）。

---

## 11. 來源與信心度

⚠ 本次只有 `WebSearch` 可用（`WebFetch`／`curl` 被出口代理擋掉，回 `EGRESS_BLOCKED`），
**只讀得到搜尋摘要，點不進原文**。所以以下每一條都標了信心度，
並且**凡是要寫進規格的結論，都用不同關鍵字撈第二次，確認有第二個獨立來源講同一件事**。

| 代號 | 結論 | 來源 | 信心度 |
|---|---|---|---|
| A1 | 金融平台普遍「綠＝漲、紅＝跌」，偏離會破壞信任 | Lollypop《Trading App Design》、Medium David Pham 同篇轉載 | **高**（但**不適用台股** —— 台股相反，見 §0.2。這條我是拿來當「慣例不能亂改」的佐證，不是拿來改顏色） |
| A2 | 資料密度要看使用者：Bloomberg 型使用者要最大密度、消費型才給留白 | 同上 | **中**（只有一個來源系列；但與 A3 互相支持） |
| A3 | 密集儀表板靠視覺重量分層（重要數字大而粗、次要小而淡），而不是靠刪東西 | Wildnet Edge《Fintech UX Design: 10 Best Practices》、Pixel Show《Designing Data-Dense Dashboards》 | **高**（兩個獨立來源） |
| B1 | `font-variant-numeric:tabular-nums`（OpenType `tnum`）讓數字等寬，適合表格對齊 | MDN `font-variant-numeric` | **高**（規範文件） |
| B2 | 在比例字體上用 `tabular-nums` 比整段改等寬字可讀性更好 | DEV《Tabular Numbers in CSS: font-variant-numeric vs Monospace Hacks》、carmenansio.com《CSS tabular & old-style figures》 | **高**（兩個獨立來源） |
| C1 | 斑馬紋在寬表有幫助，但實測對正確率**沒有統計顯著改善** | A List Apart《Zebra Striping: Does it Really Help?》＋《More Data for the Case》 | **高**（該系列是這個題目的原始量測研究） |
| C2 | 有 hover／選取／停用等互動狀態時，斑馬紋難以管理；替代做法是細分隔線＋列 hover | Pencil & Paper《Enterprise Data Tables》、uxmovement《9 Design Techniques for User-Friendly Tables》 | **高**（兩個獨立來源） |
| D1 | 格線要細、要淡、要退到背景；優先水平格線或刻度 | data-meets-design《Grid lines》、UDAIR《Visualization Best Practices》 | **高**（兩個獨立來源） |
| D2 | 資料墨水比：移除裝飾性元素（厚格線、背景、3D、重複圖例），標籤節制、細節交給 tooltip | Holistics《Data-ink Ratio》、NN/g《Clutter-Free》 | **高**（NN/g 是可靠來源） |
| E1 | 微互動 100～200ms、中型轉場 200～300ms、> 500ms 感覺像卡頓；hover 100～150ms 最佳 | Social Animal《Micro-Interactions》、Equal Design《5 Rules for Motion in UI Transitions》 | **高**（兩個獨立來源，數字一致） |
| E2 | Material Design 3 的 `DurationShort3` = **150ms**，指定用於「按鈕按下回饋、膠囊選取、分頁指示器」；標準緩動 `cubic-bezier(0.2,0,0,1)` | m3.material.io《Easing and duration》 | **高**（第一手設計系統文件） |
| F1 | WCAG 2.3.3（AAA）要求互動觸發的動態效果可關閉，除非該動態是必要的 | W3C WAI、Deque University、Silktide 三處 | **高** |
| F2 | 標準技術是 `@media (prefers-reduced-motion:reduce)`（W3C 技術編號 C39）；JS 動畫要用 `matchMedia` 並監聽變化 | W3C WAI C39、Pope Tech《Design accessible animation》 | **高**（兩個獨立來源，其一為規範） |
| G1 | 深色模式：避免純黑（用 #121212 一類）、避免純白字（用 #E8E8E8 一類）、降飽和避免色彩振動、用「面板變亮」表示層級而不是陰影 | Superdesign《Dark Mode UI》、onething.design《10 Best Practices for Dark Mode UI》 | **高**（兩個獨立來源；本站現況已經符合，這條是用來確認「不要改壞」） |
| G2 | WCAG 2.2：正文 4.5:1、大字與 UI 元件 3:1 | colorcontrast.org、accessibilitychecker.org | **高**（與規範一致） |

**Sources:**
- [Trading App Design: The Complete Guide to UI, UX & System Architecture (2026) — Lollypop](https://lollypop.design/blog/2026/june/trading-app-design/)
- [Fintech UX Design: 10 Best Practices for Dashboards — Wildnet Edge](https://www.wildnetedge.com/blogs/fintech-ux-design-best-practices-for-financial-dashboards)
- [Designing Data-Dense Dashboards: 8 Lessons from Building a Trading Journal — Pixel Show](https://pixel-show.com/blog/designing-data-dense-dashboards)
- [font-variant-numeric — MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-variant-numeric)
- [Tabular Numbers in CSS: font-variant-numeric vs Monospace Hacks — DEV](https://dev.to/alanwest/tabular-numbers-in-css-font-variant-numeric-vs-monospace-hacks-25cn)
- [CSS tabular & old-style figures: fix dashboard numbers — Carmen Ansio](https://www.carmenansio.com/articles/opentype-features-css/)
- [Zebra Striping: Does it Really Help? — A List Apart](https://alistapart.com/article/zebrastripingdoesithelp/)
- [Zebra Striping: More Data for the Case — A List Apart](https://alistapart.com/article/zebrastripingmoredataforthecase/)
- [Data Table Design UX Patterns & Best Practices — Pencil & Paper](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables)
- [9 Design Techniques for User-Friendly Tables — UX Movement](https://uxmovement.com/content/9-design-techniques-for-user-friendly-tables/)
- [Grid lines — Data Meets Design](https://www.data-meets-design.com/docs/plotelements/gridlinestickmarks/)
- [Visualization Best Practices — University of Missouri UDAIR](https://udair.missouri.edu/visualization-chart-best-practices/)
- [Data-ink Ratio: How to Simplify Data Visualization — Holistics](https://www.holistics.io/blog/data-ink-ratio/)
- [Clutter-Free: One of the 3 Cs for Better Charts — NN/g](https://www.nngroup.com/articles/clutter-charts/)
- [Micro-Interactions: Timing, CSS, and INP — Social Animal](https://socialanimal.dev/blog/micro-interactions-web-design/)
- [5 Rules for Motion in UI Transitions — Equal Design](https://www.equal.design/blog/5-rules-for-motion-in-ui-transitions)
- [Easing and duration — Material Design 3](https://m3.material.io/styles/motion/easing-and-duration/tokens-specs)
- [C39: Using the CSS prefers-reduced-motion query to prevent motion — W3C WAI](https://www.w3.org/WAI/WCAG21/Techniques/css/C39)
- [2.3.3 Animations from Interactions (AAA) — Deque University](https://dequeuniversity.com/resources/wcag2.1/2.3.3-animations-from-interactions)
- [WCAG 2.3.3: Animation from Interactions (Level AAA) — Silktide](https://silktide.com/accessibility-guide/the-wcag-standard/2-3/seizures-and-physical-reactions/2-3-3-animation-from-interactions/)
- [Design accessible animation and movement with code examples — Pope Tech](https://blog.pope.tech/2025/12/08/design-accessible-animation-and-movement/)
- [Dark Mode UI: Token Sheet With Computed Contrast — Superdesign](https://superdesign.dev/styles/dark-mode)
- [10 Best Practices for Dark Mode UI Design — onething.design](https://www.onething.design/post/best-practices-for-dark-mode-ui-design)
- [Dark Mode Contrast: The Complete Guide to WCAG-Compliant Dark UI — ColorContrast](https://www.colorcontrast.org/blog/dark-mode-contrast-accessibility-guide/)

---

## 12. 我自己判斷過、但 Andy 可能不同意的地方

一次列出來讓他一次否決，不要一項一項問。

1. **季節性熱力圖每格不再畫數字（§6.4 方案 B）。** 我的理由是「8px 且互相壓住的數字本來就讀不到」，
   但這確實是把一眼看得到的東西移進 tooltip。**如果他要保留數字，就走方案 A（格高 22px、每格一個數字、表變高要捲）。**
2. **輪動時鐘只標前 8 名（§6.3）。** 現在 13 個標籤擠在左邊、引線互相穿越。
   但「一眼看到全部族群的名字」可能正是他要的。
3. **個股頁的指標膠囊列改成單色（§4.1、A13）。** 11 顆彩色膠囊現在是「每個指標一個代表色」，
   而那個色會對應到圖上的線 —— 如果是這樣，**彩色是有功能的，我這條要撤回**。
   實作前先確認膠囊顏色與圖上線色是不是同一組。
4. **`body` 字級從 15.5px 降到 15px（§3.1）。** 為了讓 13.5／12.5 兩階有空間。
   他講過「文字太小」，所以降主字級可能會踩到他的雷 —— **替代做法是主字級不動，把 `--fs-sm` 改成 14px**。
5. **`--fs-xl` 從 34px 收到 26px（§3.1）。** 現在 34px 只有一處。如果那一處是他刻意要大的，就留著。
6. **狀態色不用綠（§4.4）。** 因為綠被「跌」佔用了，所以「成功／完成」改用青色。
   這跟大部分人的直覺相反，但在台股介面裡用綠色表示「好」會直接造成誤讀。
7. **hover 一律不准位移（§7.2）。** 這會拿掉 `.tile` 的浮起效果 —— 那個效果他可能喜歡。
   我的立場是：在密集列表裡位移會造成連鎖抖動，卡片區塊倒是還好。**如果他要留，就只留 `.tile`，列表一律不准。**

---

## 13. 沒查到／不確定的部分（老實寫）

1. **中文（繁體）介面的最小可讀字級**，查不到有量測根據的數字。
   12px 這個下限是沿用本專案 `--dg-fs-min` 已經拍板的值與 Andy 講過的「文字太小」，
   **不是我從外部資料查來的**。
2. **68ch 這個行長**：查到的「一行 45～75 字元」是拉丁文的研究，
   **中文的對應值我沒查到可靠來源**。68ch 在中文約 34～40 字，是我依現況推的，
   實作後要用截圖再校一次。
3. **`transform:scale(.985)` 會不會讓 12px 中文字在按下那一幀糊掉**，我沒有實測。
   §7.3 已經寫了「只對整顆按鈕用、不對表格列用」當保險，但實作時要真的按一次看清楚。
4. **這個容器打不開線上網站**（`curl` 回 `CONNECT tunnel failed 403`、`WebFetch` 回 `EGRESS_BLOCKED`），
   所以**所有截圖都是本機伺服器 ＋ 本機 `site/data/*.json`**。
   線上的資料量比本機大（例如族群數、成分股數），**版面在線上可能比截圖更擠**。
5. **本次稽核跑的是「手機改版那批還沒合併」的工作區狀態**
   （`git status` 顯示 `site/app.js`、`site/index.html`、`site/industry.js` 都有未提交的改動）。
   §1 的數字要在那批合併後**重量一次**才算最終基準。
6. **本機沒有即時報價 API**，所以盤中相關的互動（每分鐘更新、換手閃爍）我沒有實際看到，
   §7.6 的「只有變動的格子閃一下」是依 `live.js` 的既有機制推的規格，**沒有實測過**。

---

**最後更新：2026-09-23（台北）** by `art-director`
