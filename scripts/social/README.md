# 貼文渲染與品管

## 素材先查庫

```powershell
python scripts/social/asset_catalog.py search "趴著觀察晶片" --include-review
python scripts/social/asset_catalog.py search "prone magnifier" --pose "趴" --include-review
python scripts/social/prepare_project_assets.py --project docs/social_posts/2026-10-17_asml-outlook
```

無空白中文需求會按姿勢、動作、物件等詞群計分；同分優先本機可驗證檔案。預設僅選有核可證據的approved，`--include-review`只是候選預覽，不代表正式批准。詳細分類與三維視角限制見docs/social_assets/ASSET_CATALOG.md。

```powershell
python scripts/social/carousel_engine.py --project output/2026-10-17_asml-outlook --cover-only
python scripts/social/qa_carousel.py --project output/2026-10-17_asml-outlook --cover-only
# 封面已實際檢視後，移除 --cover-only 產全套
```

依賴 Python、Pillow；字型預設 Windows 微軟正黑體。所有正式字、圖表數字與頁號以字型排版。素材缺失、沒有透明像素、文字高度溢出會直接報錯，不產低品質替代圖。

輸入 `slides_content.json`：頂層 `slides`，每頁 `page/title/subtitle/body/bubble/source_note/layout`。版型依序 cover、definition、signal、euv、comparison、results、chain、risks、summary、cta。流程/風險/摘要使用 `items:[{title,detail}]`；比較用 `columns:[{title,items}]`；數據圖 `chart:{unit,labels,values,forecast:{label,low,high}}`，預估值為框線柱並標財測。

必要資產：`assets/cover_scene.png`、`assets/poses/01.png`～`08.png`。各插畫保留透明底，原尺寸不限，等比例置入；封面與角色不變形。使用哪個來源資產與alpha範圍記在 `qa/layout_boxes.json`。

輸出：10張1080×1350 `slides/NN.png`、`overview.png`、`mobile_contact.png`、`qa/mobile/NN.png`、逐字型bbox與預留區 `qa/layout_boxes.json`。QA檢尺寸、頁序、真實文字bbox、安全邊界、文字彼此及插畫區重疊、透明度；機器無法判定的視覺與資料品質明列 `needs_human_review`，不得把機器 pass 宣稱為美術或發布通過。

本引擎的 EUV 光路為概念圖而非機台工程圖；實際來源光路須由研究與美術交叉複查。未來主題需新增適合版型，不能用ASML事實圖直接套其他主題。

頂層 `brand_label` 可替換封面品牌文字；逐頁 `pose_asset` 或 `bibi.asset_path` 可覆寫主持素材，接受專案相對路徑或絕對路徑。需求路徑與供應鏈可用 `item_icons:[路徑,…]` 依節點覆寫小圖。

EUV版型是半導體專用。其他主題可重用布局、換素材與品牌，但仍需重新研究與人工決定敘事，不保證一鍵拆解任意文章。來源／CTA內容也須依新主題更新，不能沿用本次ASML財報文字。
