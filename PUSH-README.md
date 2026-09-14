# 一鍵推上線

改完程式後，在 repo 根目錄執行：

- **Windows**：對 `push.bat` 按兩下（或 `push.bat "commit 訊息"`）
- **Mac / Linux**：`./push "commit 訊息"`（第一次要先 `chmod +x push`）

腳本會做：`git add -A` → `commit` → `pull --rebase origin main` → `push origin main`，
整個過程寫進 `push-log.txt`。

成功的話最後會出現 `SUCCESS - GitHub Actions will redeploy`。
接著等 Actions 部署完（約 8–12 分鐘），打開 <https://miaozike.github.io/tw-rotation/>
並按 **Ctrl + F5 強制重新整理**（不強制重整的話瀏覽器可能還在用舊的 JS）。

## 這個腳本刻意不做的事
- 不 force push
- 不動 `data/` 的 Parquet（那是 Actions 在維護的資料湖，只增不改）

## 換一台電腦怎麼開始
```
git clone https://github.com/MiaoZiKe/tw-rotation
```
clone 下來就是完整的一份（含資料湖與這兩支腳本）。那台只要裝了 git、
第一次 push 時登入過 GitHub，就跟原本那台完全對等。
