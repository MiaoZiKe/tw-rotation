# ASML 為何是半導體景氣前哨？

- `slides/01.png`～`10.png`：十頁正式尺寸預覽。
- `overview.png`：十頁總覽；`mobile_contact.png`：各頁360px寬閱讀總覽。
- `caption.md`、`threads.md`：可複製文案；官方完整來源在 `sources.md`。
- `brief.md`：查核與財測分級；`qa_report.md`：機器檢查／視覺複查／Andy人工審核分開。
- `assets.json`、`asset_bindings.json`：每件素材的作者、父素材、版本與共用庫綁定。
- 本次18件素材均為review；完整圖卡已渲染供審閱，尚未人工核可與發布。

## 從repo重現

```powershell
python scripts/social/prepare_project_assets.py --project docs/social_posts/2026-10-17_asml-outlook
python scripts/social/carousel_engine.py --project docs/social_posts/2026-10-17_asml-outlook
python scripts/social/qa_carousel.py --project docs/social_posts/2026-10-17_asml-outlook
python scripts/social/asset_catalog.py search "好奇 晶圓" --include-review
```

Windows字型依賴見scripts/social/README.md。EUV版型為半導體教學用；新文章須先完成查核與結構化企劃，再重用版型和素材，不把舊事實直接套用。

校準期待Andy確認品牌視覺；PNG不依賴生圖模型生成正式中文與數字。備份狀態見backup_status.md。
