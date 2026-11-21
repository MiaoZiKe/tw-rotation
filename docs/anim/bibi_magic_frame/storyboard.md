# 比比・揮小肉掌畫出發光方框（框住重點） 12 格

- 需求：Andy 宣傳影片第 3 版（`docs/marketing/video_1010/v3_brief.md` 第 12 條）「表情、情境、道具要更豐富，並存成圖檔以後使用」→ E 批。
- 製作：`BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_e.py --out <scratchpad>/bibi --repo-out docs/anim --only magic_frame`。
- 身體：原圖 `site/brand/src/support_anim_1009.gif` 像素網格變形；表情只動眼睛那一小塊（蓋毛色再補黑點／^ ^／閉眼弧線）。場景座標同其他組（縮 0.75、中心 x=248、腳底 y=482），512×512、透明。
- 道具：SVG 三次 Bézier 4 倍繪製再 LANCZOS 縮回，懸空或放身前，不長手臂；需要手時只用官方部件總表 `site/brand/src/bibi_parts_sheet_1011.webp` 的小肉掌原圖像素。字用 jf open 粉圓。
- repo 只放 `sheet_12.png`、`anim.webp`；獨立 PNG 在 scratchpad `bibi/magic_frame/frames/`，索引 `bibi/index_e.json`。
- 方框四角座標（場景 512 座標）、畫到幾成、筆尖位置、透明度每格寫在 `index_e.json` 的 `frame_box_per_frame`：四角固定 (40,34)(472,34)(472,214)(40,214)。

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 小肉掌準備揮 | 100 |
| 02 | 揮！畫出上邊 | 60 |
| 03 | 上邊畫完 | 60 |
| 04 | 畫右邊 | 60 |
| 05 | 畫下邊 | 60 |
| 06 | 下邊快完 | 60 |
| 07 | 畫左邊 | 60 |
| 08 | 方框完成！ | 100 |
| 09 | 方框發光 | 100 |
| 10 | 比比開心 | 100 |
| 11 | 方框亮著 | 100 |
| 12 | 方框淡出 | 90 |

合計 950ms，無限循環，第 12 格接回第 1 格。
