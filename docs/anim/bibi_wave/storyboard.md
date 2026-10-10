# 比比・揮手（打招呼／再見共用） 12 格

- 需求：`docs/marketing/video_1010/storyboard.md` 第 4 節（比比 5 組新動作）；規格照 `docs/anim/prompt_kit/01_總控Prompt.md`（raster_first）。
- 製作：`python scripts/anim/bibi_actions.py --out <scratchpad>/bibi --repo-out docs/anim [--only wave]`（每組約 50 秒）。
- 身體：全部是原圖 `site/brand/src/support_anim_1009.gif` 第 0 張（待機）的像素，用 `pose_tween.warp_body` 網格變形（擠壓／拉長／旋轉／頭頂毛慣性），沒有重畫。
- 補繪：小肉掌在身側上下小幅擺動＋身體搖、揮到兩端的弧形動作線；動作線與箭頭用 SVG 三次 Bézier。
- ★ 2026-10-11 Andy 退件「打招呼的手不會長這樣，四肢都是短短的」：拿掉 Bézier 長手臂，改用官方部件總表 `site/brand/src/bibi_parts_sheet_1011.webp` 的小肉掌原圖像素（去背後旋轉貼在身體右側邊緣，只冒出一小截）。
- 場景座標（5 組共用）：身體縮 0.75、中心 x=248、腳底 y=482；512×512、透明。每格都是不同姿勢（相鄰格差異最小值見 `<scratchpad>/bibi/index.json`）。
- repo 只放 `sheet_12*.png`（12 格總覽）、`anim*.webp`（透明動態）；獨立 PNG 在 scratchpad `bibi/wave/frames/`（不進版控），路徑清單在 `bibi/index.json`。

- 用在：鏡 04「我是比比！」、鏡 32「下次見～」。
- 備註：第 1 格＝jump K01 同一格身體，可從跳躍落地直接接；3～9 格可單獨循環當「一直揮」。


## 揮手（`wave`，合計 1000ms，第 12 格接回第 1 格）

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 待機 | 140 |
| 02 | 小肉掌從身側冒出 | 80 |
| 03 | 舉起來 | 70 |
| 04 | 揮向外 | 70 |
| 05 | 揮向內 | 70 |
| 06 | 揮向外 | 70 |
| 07 | 揮向內 | 70 |
| 08 | 揮向外 | 70 |
| 09 | 揮向內 | 70 |
| 10 | 手往下收 | 70 |
| 11 | 收回身側 | 80 |
| 12 | 回待機（微彈） | 140 |
