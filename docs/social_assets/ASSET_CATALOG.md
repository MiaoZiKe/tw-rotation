# 比比姿勢與科技物件搜尋器

執行位置為專案根目錄；需 Python 與 Pillow。工具只讀索引與原檔，不移動歷史庫、不重產圖片。

```powershell
python scripts/social/asset_catalog.py scan --out output/2026-10-17_asml-outlook/catalog_local.json
python scripts/social/asset_catalog.py search "趴著觀察晶片" --include-review
python scripts/social/asset_catalog.py search --pose prone --prop magnifier --include-review
python scripts/social/asset_catalog.py self-test
```

`scan` 讀 `docs/social_assets/**/manifest.json`，支援中英文 pose／expression／orientation／prop／scene／tags 與舊版中文欄位；合併本次有來源證據的遠端快照。遠端資料只引用 GitHub 位置，不下載或搬移原始檔。搜尋回傳 score、status、selectable；分數是文字吻合比例，不是美術品質評分。已提供趴姿、放大鏡、晶片、晶圓、好奇、思考、指向、左右等中英同義詞；這是明確標籤檢索，尚非語意模型。

預設只回傳 `approved`；`--include-review` 允許預覽 `review`／`visual_checked`，不代表可自動選用。`rejected` 永不回傳。manifest 只有明確 `status: approved` **以及**非空 `approval_evidence` 才獲准；不得以「程式成功」「造型檢查通過」或舊文中 CEO 自檢文字推定 Andy 已核可。新增 imagegen 姿勢在 Andy 風格確認前最多 `visual_checked`。權利 unknown 必須保留，不能因加工而改掛原創；批准造型也不會自動授予權利。

本機圖片實測 SHA-256、尺寸、每格 alpha 極值與透明像素、動畫格數／總時長／平均 fps。RGBA 模式但 alpha 全 255 會標不具透明像素。遠端僅索引的素材，這些欄位不虛填；舊表的格數與秒數另列 declared，未當成實測。SVG 科技物件應保存可編輯來源，另用 PNG 衍生檔記檢查；Pillow 無法讀 SVG 時明列 inspection_error，不冒充通過。

尚需人工：角色一致、肢體正確、道具接觸、設備透視、品牌風格、權利依據與實際手機可讀性。工具輸出不能取代 qa_report.md 的逐頁放大與全篇複查。
