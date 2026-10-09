# 天竺鼠看盤（laptop）12 格

> 2026-10-09 Andy 給 12 格分鏡總表（`site/brand/src/laptop_storyboard_1009.webp`）：「幫我合成 GIF」。
> 照總控 Prompt 的 INPUT_TYPE=storyboard：只裁切、去標題、統一畫布、合成，不重畫。

- 指令：`python scripts/anim/storyboard_grid.py --in site/brand/src/laptop_storyboard_1009.webp --out docs/anim/laptop`
- 每格裁 332×332（避開 FRAME 字樣與圓角）→ 放大到 512×512。
- 對齊：AI 分鏡第 2 排桌面比第 1 排高 7px、第 3 排高 11～12px，用桌面線量垂直位移、用下方桌面／滑鼠比水平位移，對回第 1 格（位移寫在 `verify.json`）。
- 背景保留原畫（桌子、椅子、筆電是場景的一部分，去掉就不成畫面）。
- 節奏（ms）：待機 700｜注意 350｜想 K 線 600｜回看 350｜拿眼鏡 300｜戴上 300｜盯盤 350｜點滑鼠 300｜嚇到冒汗 450｜發亮 400｜開心眨眼 650｜摘眼鏡回待機 450 ＝ 一輪 5.2 秒、無限循環。
- 成品：`animation.gif`（512，1.2MB）、`animation-256.gif`（348KB）、`animation.webp`（252KB）、`storyboard_12.png`。12 張獨立 PNG 與 ZIP 不進 repo，重跑上面指令就有。
