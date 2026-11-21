# 比比・歪頭疑問 12 格

- 需求：`docs/marketing/video_1010/storyboard.md` 第 4 節（比比 5 組新動作）；規格照 `docs/anim/prompt_kit/01_總控Prompt.md`（raster_first）。
- 製作：`python scripts/anim/bibi_actions.py --out <scratchpad>/bibi --repo-out docs/anim [--only tilt]`（每組約 50 秒）。
- 身體：全部是原圖 `site/brand/src/support_anim_1009.gif` 第 0 張（待機）的像素，用 `pose_tween.warp_body` 網格變形（擠壓／拉長／旋轉／頭頂毛慣性），沒有重畫。
- 補繪（SVG 三次 Bézier、以 2048 繪製再 LANCZOS 縮回 512；顏色取自原圖：描邊 #1A0907、毛 #FDF5E9、肉掌 #E07E5E／#C55E44）：頭上「？」（兩段 Bézier 鉤＋圓點，粗黑筆刷）
- 場景座標（5 組共用）：身體縮 0.75、中心 x=248、腳底 y=482；512×512、透明。每格都是不同姿勢（相鄰格差異最小值見 `<scratchpad>/bibi/index.json`）。
- repo 只放 `sheet_12*.png`（12 格總覽）、`anim*.webp`（透明動態）；獨立 PNG 在 scratchpad `bibi/tilt/frames/`（不進版控），路徑清單在 `bibi/index.json`。

- 用在：鏡 07、09、22。
- 備註：歪頭是整顆身體以腳底為軸旋轉 12°（過頭到 14° 再回），頭頂毛有慣性延遲。原本試過「手托下巴」，縮小後像一塊污漬，拿掉了。


## 歪頭疑問（`tilt`，合計 1040ms，無限循環，第 12 格接回第 1 格）

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 待機 | 140 |
| 02 | 微縮（預備） | 70 |
| 03 | 頭開始歪 | 60 |
| 04 | 歪到 14°（過頭） | 70 |
| 05 | 回到 12°、「？」冒出 | 60 |
| 06 | 「？」彈大 | 60 |
| 07 | 「？」回正常 | 80 |
| 08 | 「？」晃一下 | 80 |
| 09 | 停著想 | 160 |
| 10 | 頭開始回正、「？」縮 | 70 |
| 11 | 快回正、「？」消失 | 70 |
| 12 | 回待機（微彈） | 120 |
