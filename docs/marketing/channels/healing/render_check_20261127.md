# 談晴說礙：分段渲染第一次使用的比對（2026-11-27）

Andy 2026-11-27：渲染一律照頻道②架構（matrix 分段、成品推存檔分支、第一次用要跟容器成品比對）。

## 做法
- 新流程：`.github/workflows/healing_render.yml`（plan → render 每支 8 台交錯渲、每段 60 幀 → finalize 接段＋配音軌＋檢查）。`render_video.js` 新增 `--from/--to/--chunk/--job/--jobs/--seg/--assemble`，不帶參數＝原行為。
- 成品推存檔分支 `renders/healing`：`renders/<資料夾>.<短sha>.mp4`＋檢查 json。工作分支只回寫小檔，video.mp4 ≤20MiB 才回寫。
- 比對對象：`queue/20261127v_food`（main 上容器渲好、輸入沒變，今晚要發；**main 的檔案一個字沒動**）。Actions 以 `writeback=0` 渲一次（不碰工作分支的該資料夾），再用 `v9/compare_render.py` 比對。
- 判準：片長差 ≤0.05 秒；逐秒抽格（每秒中點一格）同秒兩張的像素平均絕對差 ≤2%。

## 結果
（待填：Actions 跑完後取 renders/healing 的成品比對）

## 比對結果（2026-11-27 09:35 台北，④總編輯）
- 新流程成品：renders/healing 分支 `renders/20261127v_food.517f5482.mp4`（run 45921106579，8 台分段，總耗時約 8 分鐘；舊做法單台約 19 分鐘）。
- 容器成品：main `queue/20261127v_food/video.mp4`。
- `compare_render.py`：片長 51.067 vs 51.067（差 0.000 秒）；逐秒 51 格平均差 0.367%、最大 1.997%（第 38 秒，並排抽格人工看：畫面、文字、數字完全一致，差在背景光暈位置）。
- 判定：**通過**（片長差 ≤0.05 秒、逐秒差 ≤2%）。新分段流程自 2026-11-27 起正式啟用；之後④影片一律用它渲染。
