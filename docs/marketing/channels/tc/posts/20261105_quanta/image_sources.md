# 廣達待遇文：圖片來源與審查（2026-11-05）

| 張 | 內容 | 來源與授權 |
|---|---|---|
| 1_cover | 封面：廣達總部實景（玻璃天幕、大型藍色「Quanta」立體字與階梯），Andy 11-06 提供，640×427，填滿裁切成 1032×690 框（放大約 1.6 倍，Lanczos＋輕微銳化，檔案 `cover_photo.jpg`） | 來源：Andy 11-06 從 Google 圖片搜尋找到，標示為 www.quantatw.com；依 DECISIONS #373 官方照片可用並標「圖：廣達官方」；原始網址待 Andy 確認。署名寫在文案（Threads 留言、IG 文末），圖上不印 |
| 2_fields | 純文字欄位表，無照片、無公司 LOGO | 自製（`render_quanta.py`，改自 docs/tc/assets/scripts/render_samples.py） |

## 選圖說明
- 11-06 起封面改用 Andy 提供的廣達總部照，取代原 Wikimedia 上海廠區照（CC BY-SA、非桃園總部），相關授權句與「非桃園總部」說明已刪。
- 照片解析度僅 640×427，放大約 1.6 倍，略軟；若 Andy 找到原始頁面的大圖，換檔重出即可。
- 封面不放我方公司 LOGO；照片裡建築上的「Quanta」立體字是實景，不算我方放的 LOGO。

## 2026-11-06 第 2 張台灣地圖
- 本島輪廓：npm 套件 `world-atlas@2.0.2`（ISC 授權，© Michael Bostock；資料來自 Natural Earth，公有領域）的 `countries-50m.json`，取 Taiwan 的本島多邊形，用 `make_taiwan_path.mjs`（topojson-client＋d3-geo 麥卡托）轉成 `taiwan_path.json`。非 AI 繪製、非手描。
- 總部點位：桃園龜山，北緯 25.03、東經 121.36（同一投影算出）。
