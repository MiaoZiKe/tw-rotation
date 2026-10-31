# 預覽轉送 Worker（Pages 進階模式）

`liguligu-puipui.com/preview/<名稱>/` → 轉到 Pages 專案 `tw-rotation-preview`（`tw-rotation-preview.pages.dev`）。
部署方式：`.github/workflows/pages.yml` 的 Cloudflare 步驟會把 `_worker.js` 與 `_routes.json`（只攔 `/preview/*`）放進主站部署包，不需要另外部署。
