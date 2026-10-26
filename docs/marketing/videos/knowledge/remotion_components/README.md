# Remotion 元件（Motion Library 練習）

環境：Node 22、remotion@4.0.250（@remotion/cli／bundler／renderer 同版）、react 18.3.1、typescript 5.6.3。
瀏覽器：`remotion.config.ts` 指到 `/opt/pw-browsers/chromium_headless_shell-1194/...`。字型 Noto Sans TC（Bold／Black ttf 放 `public/fonts/`）、比比用 `docs/anim/bibi_library/wave/key.png` 放 `public/bibi/key.png`（這兩樣沒複製進 repo）。
專案位置（未進 repo）：scratchpad `remotion_lab/`；成片 `out/ex1.mp4 ex2.mp4 ex3.mp4 demo.mp4`（1080×1920、30fps）。
渲染：`npx remotion render src/index.ts Ex1 out/ex1.mp4 --crf=16`（Ex1／Ex2／Ex3／Demo）。

| 元件 | props | 適用 |
|---|---|---|
| `LightningSlam` | text、startFrame、durationInFrames、color、glowColor、fontSize、startScale、centerY、seed | 開場標題 |
| `DecodeNumber` | text、startFrame、durationInFrames、color、fontSize、centerY、seed | 關鍵數字（漲紅跌綠由 color 傳入） |
| `ParticleDissolve` | lines、startFrame、durationInFrames、showStaticBefore、seed | 只用於轉場，字須先停留 ≥1 秒 |
| `Bibi` | x、bottom、size、startFrame、mode（heart／pendulum）、loopFrames | 比比待機 |

## 自我檢查（逐條）
- 無 CSS transition、`@keyframes`、GSAP、`requestAnimationFrame`、`Math.random`：grep 全 src 0 筆。粒子與亂碼全用 `random(seed字串)`。
- 時長用 fps：影格數＝秒數×30（72／90／105／240）；spring 內傳 `fps`。
- 安全區：文字全在上下 250px 內（標題最高 y≈425、比比底 y=1660）；標題 108px、數字 230px、內文 48～56px。
- 循環：比比 `frame % loopFrames`，t=0 與 t=loop 皆為 scale 1，無縫。
- 不糊：外發光是底層獨立文字，上層字無 filter；砸落硬切出現。
- 閃光：兩次閃光相隔 12 幀（2.5 次/秒），局部光暈最大不透明度 0.35。
- 拼圖檢查（每 3 幀＝0.1 秒一格，單格 360×640；demo 每 6 幀）：字不糊、不被切、無重疊。已知可見重疊：砸落第 21 幀字與正在淡出的閃電尾端（不透明度 ≈0.15）重疊 1 格；粒子尾端與 B 幕開頭重疊 ≤6 幀。
- 程式逐幀重疊檢查（overlap_report）這次沒做，只做人工拼圖；正式上線的片要補。

## 沒做／注意
- 演示用示意文案，非正式腳本；「+38.6%」是練習用示意數字。
- 消散前由 DOM 換成 Canvas 畫同樣的字，換手那一幀位置一致（拼圖確認），但外發光與「示意」標籤在換手時收掉。
- 比比用靜態 key.png 做心跳，沒用 anim.webp／sheet 逐格動作。

## 建議下一支影片採用的效果（3～5 種）
1. 001 閃電砸落：開場標題（每支片只用一次）。
2. 013 亂碼解讀：本片唯一的關鍵數字（漲紅跌綠）。
3. 卡片群組進場：列點（三點以內，每張間隔 8 幀）。
4. 005 粒子消散：段落間唯一一次轉場，前一幕字先停 ≥1 秒。
5. 006 心跳放大（比比待機）：固定在下方安全區。
字幕可評估 025 卡拉OK小球，但要先確認不與旁白字幕規則衝突。
