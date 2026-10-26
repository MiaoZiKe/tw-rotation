# Motion Library × Remotion 影片動態（學習筆記）

> 來源：社群學習資料，Andy 2026-10-26 貼給 CEO（「CEO 幫我安排人員學習這技能，這可以加強影片製作能力」）。
> ⚠ Motion Library 網站（kittenjam-motion-library.vercel.app）我們這邊**打不開**，下面的效果描述**以 Andy 貼的為準**，沒有自己查證過網站內容。
> 實作驗收：`remotion_components/`（三道練習題＋綜合示範，已用 Remotion 4.0.250 實際渲染）。

## 1. 這是什麼

Motion Library 是一個動態效果參考庫，共 327 種，每種有三位數編號與一段「AI 提示詞」。
- 元件維度：文字、按鈕、卡片、圖形、背景……
- 時機維度：進場、退場、切換、循環待機、懸停點擊、捲動、拖曳
- 情境維度：標題、強調重點、數字資訊、背景裝飾、轉場、Logo……
- 原始技術：CSS、GSAP、Canvas

範例「001 閃電砸落」：畫面先閃兩下強光並出現閃電線，文字從 2 倍大瞬間砸下縮回原尺寸，落地輕微震動，之後保持柔和外發光，約 2.4 秒。

## 2. 網頁動畫轉成影片動畫的規則（Remotion，影格驅動）

1. 只能用 `useCurrentFrame()`、`interpolate()`、`spring()`、`Easing`。**禁止** CSS transition、`@keyframes`、GSAP timeline、`requestAnimationFrame`。
2. 時長一律用 fps 計算（預設 30fps，2.4 秒＝72 幀）。
3. 懸停、點擊、捲動、拖曳類效果，改成在指定影格自動觸發。
4. 循環用 `frame % loopFrames`，首尾要無縫。
5. 粒子用 Remotion 的 `random(seed)`，**不能用 `Math.random()`**（否則每次渲染不同、影格不可重現）。
6. 畫布 1080×1920，上下各留約 250px 安全區；標題 ≥90px、內文 ≥48px。
7. 用品牌色，紅漲綠跌。
8. 一幕 2～4 秒；一支片的效果種類 3～5 種；重點數字才用強調型效果。

## 3. 財經短片選用對照

| 用途 | 可選效果 |
|---|---|
| 開場標題 | 001 閃電砸落、008 倒數砸落、006 心跳放大 |
| 關鍵數字 | 013 亂碼解讀、008、023 字重變粗 |
| 公司或代號揭曉 | 003 硬幣翻轉、013 |
| 轉場 | 002 雷射切斷、004 爆炸四散、005 粒子消散、027 像素溶解 |
| 背景 | 015 漸層流動（我們只准當很淡的背景，見第 5 節） |
| 列點 | 卡片群組進場 |
| 字幕 | 025 卡拉OK小球、018 逐字彈跳、009 波浪文字 |
| 比比貼圖 | 006 心跳放大、026 鐘擺搖晃、034 顫抖穩定、035 彈性拉伸 |

## 4. 工作流程

1. 讀懂需求
2. 把效果拆成「階段 × 影格區間 × 屬性變化」表
3. 寫可重用的 Remotion 元件，props 至少有 `text`、`startFrame`、`durationInFrames`、`color`
4. 自我檢查（無 transition／keyframes／Math.random、時長用 fps、安全區、循環首尾）
5. 交付：元件、使用範例、適用情境

## 5. 與我們規則的衝突處理（以 Andy 為準）

依據：`docs/marketing/videos/video_rules_1018.md`、`docs/marketing/videos/feature_series/plan.md`、`docs/marketing/video_1010/layout_rules.md`。

| 社群資料的做法 | 我們的規則 | 處理方式 |
|---|---|---|
| 001 的「柔和外發光」 | 零模糊 | 外發光做成**獨立底層**（`text-shadow` 只有 10px、不透明度 0.45 以下），**字本身在最上層**，邊緣銳利。字禁用 `filter: blur`、禁用半透明漸變出現（砸落用硬切出現）。 |
| 轉場可兩幕半透明交疊 | 不准遮擋、重疊、疊影 | 前後兩幕的字**不准半透明疊在一起超過 0.2 秒（6 幀）**。示範做法：A 幕粒子飛散時，B 幕在 A 幕字完全散完時才進場，只與尾端的淡粒子重疊 6 幀。 |
| 005 粒子消散（字會散掉） | 字必須讀得到 | **只准用在轉場**，且該幕的字在消散前**已完整停留至少 1 秒**（示範：36 幀＝1.2 秒）。不拿來當字幕或常駐效果。 |
| 015 漸層流動當背景 | 禁止「漸層背景＋置中標題」老套 | 只准當**很淡的背景**，不當主視覺；示範片一律用純深色底＋極淡格線，沒有用 015。 |
| 外部圖示庫、品牌圖 | 不用錢的圖示 | 不引入付費圖示；圖形用自繪（SVG／Canvas）或比比素材庫。 |
| 範例常見公司名、股票代號 | 不點名個股 | 練習題只用產業描述；練習 2 的「+38.6%」**只是練習用示意數字，不得寫成某公司的數字**，畫面上也標「練習用示意數字，非實際資料」。 |
| 001 先閃兩下強光 | 光敏性安全 | **每秒閃爍 ≤3 次**（示範兩次閃光相隔 12 幀＝2.5 次/秒）；閃光是局部放射光暈，最大不透明度 0.35，**不做整個畫面全白**。013 亂碼是字元替換（每 2 幀換一次），面積只有數字本身，不整畫面閃。 |
| 懸停／點擊類效果 | 影片沒有互動 | 一律改在指定影格自動觸發。 |
| 比比貼圖用 006／026 | 比比不說話、占比小、不蓋內容 | 比比放安全區內、固定位置，心跳／鐘擺只是待機，不出對話泡泡。 |

另外沿用：元件兩兩不得重疊（大字、泡泡、名牌、比比、道具、字幕、角標、網站畫面），要逐幀檢查並在回報寫「重疊檢查：程式 N 幀 0 筆；人工 M 格 0 筆」（`video_1010/layout_rules.md`）。

## 6. 實作心得（Remotion 4.0.250，2026-10-26 驗證）

- 安裝：npm 可連，`remotion`、`@remotion/cli`、`@remotion/bundler`、`@remotion/renderer` 一起裝（固定同一版本）。專案放 scratchpad（node_modules 不進 repo）。
- 瀏覽器：用本機 `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`，在 `remotion.config.ts` 用 `Config.setBrowserExecutable` 指定，不需下載。
- TypeScript 要 5.x（`typescript@latest` 若是 7.x 會讓 bundler 的 esbuild-loader 報 `typescript.sys` 不存在）。
- 字型：Noto Sans TC 的 ttf 放 `public/fonts/`，用 `FontFace` ＋ `delayRender` 載入後才渲染（DOM 與 Canvas 取樣共用同一套字型）。
- 粒子消散：在 Canvas 把字畫出來、每 4px 取樣，已離開的格子用 `clearRect` 挖掉，**剩下的字仍是銳利原字**；粒子位置全由 `random(seed)` 與影格算出，可重現。
- 數字「亂碼解讀」要固定每個字元的格寬，否則亂碼期間字寬會抖動。
- 與我們的 Python 合成器（PIL＋ffmpeg）相比：Remotion 的優點是 spring／interpolate／Easing 現成、DOM 排版省事；缺點是要裝 Node 環境、渲染比 PIL 慢。兩者原則相同（影格驅動、固定 seed）。

## 7. 建議下一支影片可採用的效果

見 `remotion_components/README.md` 最後一節。
