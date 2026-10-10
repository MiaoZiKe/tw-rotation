# 比比・小火箭往上（持續進步） 12 格

- 需求：Andy 宣傳影片第 3 版（`docs/marketing/video_1010/v3_brief.md` 第 12 條）「表情、情境、道具要更豐富，並存成圖檔以後使用」→ E 批。
- 製作：`BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_e.py --out <scratchpad>/bibi --repo-out docs/anim --only rocket`。
- 身體：原圖 `site/brand/src/support_anim_1009.gif` 像素網格變形；表情只動眼睛那一小塊（蓋毛色再補黑點／^ ^／閉眼弧線）。場景座標同其他組（縮 0.75、中心 x=248、腳底 y=482），512×512、透明。
- 道具：SVG 三次 Bézier 4 倍繪製再 LANCZOS 縮回，懸空或放身前，不長手臂；需要手時只用官方部件總表 `site/brand/src/bibi_parts_sheet_1011.webp` 的小肉掌原圖像素。字用 jf open 粉圓。
- repo 只放 `sheet_12.png`、`anim.webp`；獨立 PNG 在 scratchpad `bibi/rocket/frames/`，索引 `bibi/index_e.json`。

| 格 | 姿勢 | 停留 ms |
|---|---|---|
| 01 | 火箭在右下點火 | 90 |
| 02 | 起飛！ | 60 |
| 03 | 往上衝 | 60 |
| 04 | 越飛越高 | 60 |
| 05 | 飛過頭頂 | 60 |
| 06 | 快出畫面 | 60 |
| 07 | 咻——出去了 | 70 |
| 08 | 眼睛發亮 | 90 |
| 09 | 開心蹦 | 70 |
| 10 | 蹦最高 | 70 |
| 11 | 落地 | 90 |
| 12 | 下一枚火箭準備 | 100 |

合計 880ms，無限循環，第 12 格接回第 1 格。
