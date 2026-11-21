# 比比・星星收藏進盒子（自選清單） 12 格

- 需求：Andy 宣傳影片第 3 版（`docs/marketing/video_1010/v3_brief.md` 第 12 條）「表情、情境、道具要更豐富，並存成圖檔以後使用」→ E 批。
- 製作：`BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_e.py --out <scratchpad>/bibi --repo-out docs/anim --only star_save`。
- 身體：原圖 `site/brand/src/support_anim_1009.gif` 像素網格變形；表情只動眼睛那一小塊（蓋毛色再補黑點／^ ^／閉眼弧線）。場景座標同其他組（縮 0.75、中心 x=248、腳底 y=482），512×512、透明。
- 道具：SVG 三次 Bézier 4 倍繪製再 LANCZOS 縮回，懸空或放身前，不長手臂；需要手時只用官方部件總表 `site/brand/src/bibi_parts_sheet_1011.webp` 的小肉掌原圖像素。字用 jf open 粉圓。
- repo 只放 `sheet_12.png`、`anim.webp`；獨立 PNG 在 scratchpad `bibi/star_save/frames/`，索引 `bibi/index_e.json`。

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 盒子關著 | 90 |
| 02 | 星星出現 | 80 |
| 03 | 星星飄過來 | 80 |
| 04 | 盒子打開 | 80 |
| 05 | 星星飛向盒子 | 70 |
| 06 | 咻——掉進去 | 70 |
| 07 | 蓋上！ | 80 |
| 08 | 收藏 +1 | 110 |
| 09 | 開心 | 90 |
| 10 | 盒子彈一下 | 90 |
| 11 | 站好 | 80 |
| 12 | 下一顆星星 | 80 |

合計 1000ms，無限循環，第 12 格接回第 1 格。
