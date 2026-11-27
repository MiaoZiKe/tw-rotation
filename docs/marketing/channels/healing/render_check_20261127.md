# 談晴說礙：分段渲染第一次使用的比對（2026-11-27）

Andy 2026-11-27：渲染一律照頻道②架構（matrix 分段、成品推存檔分支、第一次用要跟容器成品比對）。

## 做法
- 新流程：`.github/workflows/healing_render.yml`（plan → render 每支 8 台交錯渲、每段 60 幀 → finalize 接段＋配音軌＋檢查）。`render_video.js` 新增 `--from/--to/--chunk/--job/--jobs/--seg/--assemble`，不帶參數＝原行為。
- 成品推存檔分支 `renders/healing`：`renders/<資料夾>.<短sha>.mp4`＋檢查 json。工作分支只回寫小檔，video.mp4 ≤20MiB 才回寫。
- 比對對象：`queue/20261127v_food`（main 上容器渲好、輸入沒變，今晚要發；**main 的檔案一個字沒動**）。Actions 以 `writeback=0` 渲一次（不碰工作分支的該資料夾），再用 `v9/compare_render.py` 比對。
- 判準：片長差 ≤0.05 秒；逐秒抽格（每秒中點一格）同秒兩張的像素平均絕對差 ≤2%。

## 結果
（待填：Actions 跑完後取 renders/healing 的成品比對）
