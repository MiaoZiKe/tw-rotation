# 比比・驚嘆 12 格

- 需求：`docs/marketing/video_1010/storyboard.md` 第 4 節（比比 5 組新動作）；規格照 `docs/anim/prompt_kit/01_總控Prompt.md`（raster_first）。
- 製作：`python scripts/anim/bibi_actions.py --out <scratchpad>/bibi --repo-out docs/anim [--only wow]`（每組約 50 秒）。
- 身體：全部是原圖 `site/brand/src/support_anim_1009.gif` 第 0 張（待機）的像素，用 `pose_tween.warp_body` 網格變形（擠壓／拉長／旋轉／頭頂毛慣性），沒有重畫。
- 補繪（SVG 三次 Bézier、以 2048 繪製再 LANCZOS 縮回 512；顏色取自原圖：描邊 #1A0907、毛 #FDF5E9、肉掌 #E07E5E／#C55E44）：雙手肉掌貼臉、眼睛白色亮點、頭上「！」、兩側放射動作線、黃色四角閃光（看盤分鏡第 10 格那種）
- 場景座標（5 組共用）：身體縮 0.75、中心 x=248、腳底 y=482；512×512、透明。每格都是不同姿勢（相鄰格差異最小值見 `<scratchpad>/bibi/index.json`）。
- repo 只放 `sheet_12*.png`（12 格總覽）、`anim*.webp`（透明動態）；獨立 PNG 在 scratchpad `bibi/wow/frames/`（不進版控），路徑清單在 `bibi/index.json`。

- 用在：鏡 16「哇，拆開了！」。
- 備註：身體先往下壓再往上縮（腳底離地 10px），4～9 格貼臉抖動。


## 驚嘆（`wow`，合計 950ms，無限循環，第 12 格接回第 1 格）

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 待機 | 140 |
| 02 | 預備：往下壓 | 70 |
| 03 | 嚇一跳往上縮、手往上 | 50 |
| 04 | 雙手貼臉、「！」彈出 | 60 |
| 05 | 落回、眼睛發亮 | 70 |
| 06 | 抖一下（左） | 50 |
| 07 | 抖一下（右） | 50 |
| 08 | 抖一下（左） | 50 |
| 09 | 定住、閃光 | 140 |
| 10 | 「！」縮小 | 70 |
| 11 | 手放下 | 80 |
| 12 | 回待機（微彈） | 120 |
