# 比比・存錢筒（金幣投進去、叮） 12 格

- 需求：Andy 2026-10-10「幫我在影片中新增多點 GIF 圖，並且越豐富，情境越多越好」；用在 `docs/marketing/video_1010/storyboard.md` 的「ETF 配息／行事曆」段。
- 製作：`BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_b.py --out <scratchpad>/bibi --repo-out docs/anim --only piggy`（約 1.5 分鐘）。
- 身體：原圖 `site/brand/src/support_anim_1009.gif` 的像素網格變形（raster_first）；開心蹲／落地用原圖第 2 張（瞇眼笑）。場景座標與 A 批相同：身體縮 0.75、中心 x=248、腳底 y=482；512×512、透明。
- 道具：粉色小豬存錢筒放在比比身前右側地上（臉朝比比），一隻小肉掌貼在小豬背上；金幣從上方翻面掉進投幣孔，「叮！」用 jf open 粉圓。
- 道具畫法：SVG 三次 Bézier（Catmull-Rom 轉 C、外框點微抖動＝手繪感），描邊 #1A0907、粗細同原圖；4 倍繪製後 LANCZOS 縮回。依 Andy 退件教訓，不畫從身體伸出的長手臂，只露小肉掌。
- 成品：`anim.webp`（本資料夾）；獨立 PNG 與 GIF 在 scratchpad `bibi/piggy/`，路徑記在 `bibi/index_b.json`。
- 合計 1030ms，無限循環；相鄰格皆有實際差異（無重複影格）。

| 格 | 動作 | 停留 ms |
|---|---|---|
| 01 | 金幣冒出、抬頭看 | 140 |
| 02 | 金幣往下掉（翻面） | 70 |
| 03 | 金幣經過臉旁 | 60 |
| 04 | 金幣對準投幣孔 | 60 |
| 05 | 投進去！存錢筒一沉 | 70 |
| 06 | 「叮」閃光 | 110 |
| 07 | 開心蹲（瞇眼笑） | 80 |
| 08 | 彈起來 | 70 |
| 09 | 落地（瞇眼笑） | 80 |
| 10 | 回彈、摸摸小豬 | 90 |
| 11 | 微晃 | 90 |
| 12 | 抬頭等下一枚 | 110 |
