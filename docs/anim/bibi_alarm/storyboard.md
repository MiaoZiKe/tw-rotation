# 比比・鬧鐘響→按掉（省時間） 12 格

- 需求：Andy 宣傳影片第 3 版（`docs/marketing/video_1010/v3_brief.md` 第 12 條）「表情、情境、道具要更豐富，並存成圖檔以後使用」→ E 批。
- 製作：`BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_e.py --out <scratchpad>/bibi --repo-out docs/anim --only alarm`。
- 身體：原圖 `site/brand/src/support_anim_1009.gif` 像素網格變形；表情只動眼睛那一小塊（蓋毛色再補黑點／^ ^／閉眼弧線）。場景座標同其他組（縮 0.75、中心 x=248、腳底 y=482），512×512、透明。
- 道具：SVG 三次 Bézier 4 倍繪製再 LANCZOS 縮回，懸空或放身前，不長手臂；需要手時只用官方部件總表 `site/brand/src/bibi_parts_sheet_1011.webp` 的小肉掌原圖像素。字用 jf open 粉圓。
- repo 只放 `sheet_12.png`、`anim.webp`；獨立 PNG 在 scratchpad `bibi/alarm/frames/`，索引 `bibi/index_e.json`。

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 鬧鐘響！比比嚇一跳 | 90 |
| 02 | 鈴鈴鈴（左晃） | 70 |
| 03 | 鈴鈴鈴（右晃） | 70 |
| 04 | 吵死了…往鬧鐘靠 | 80 |
| 05 | 身體壓過去 | 70 |
| 06 | 小肉掌按下去 | 90 |
| 07 | 叮——停了 | 110 |
| 08 | 回正 | 80 |
| 09 | 鬆一口氣 | 120 |
| 10 | 省下時間、開心 | 100 |
| 11 | 站好 | 90 |
| 12 | …鬧鐘又要響了 | 80 |

合計 1050ms，無限循環，第 12 格接回第 1 格。
