# 廣達待遇文：圖片來源與審查（2026-11-05）

| 張 | 內容 | 來源與授權 |
|---|---|---|
| 1_cover | 封面：廣達總部實景（玻璃天幕、大型藍色「Quanta」立體字與階梯），Andy 11-06 提供，640×427，填滿裁切成 1032×690 框（放大約 1.6 倍，Lanczos＋輕微銳化，檔案 `cover_photo.jpg`） | 來源：Andy 11-06 從 Google 圖片搜尋找到，標示為 www.quantatw.com；依 DECISIONS #373 官方照片可用並標「圖：廣達官方」；原始網址待 Andy 確認。署名寫在文案（Threads 留言、IG 文末），圖上不印 |
| 2_fields | 純文字欄位表，無照片、無公司 LOGO | 自製（`render_quanta.py`，改自 docs/tc/assets/scripts/render_samples.py） |

## 選圖說明
- 11-06 起封面改用 Andy 提供的廣達總部照，取代原 Wikimedia 上海廠區照（CC BY-SA、非桃園總部），相關授權句與「非桃園總部」說明已刪。
- 照片解析度僅 640×427，放大約 1.6 倍，略軟；若 Andy 找到原始頁面的大圖，換檔重出即可。
- 封面不放我方公司 LOGO；照片裡建築上的「Quanta」立體字是實景，不算我方放的 LOGO。

## 2026-11-06 第 2 張台灣地圖（第二版，取代 world-atlas 版）
- 海岸線與縣市界線：npm `taiwan-atlas@2021.9.20`（MIT 授權，© Daniel Kao）的 `counties-10t.json`，用 `make_taiwan_path.mjs`（topojson-client＋d3-geo 麥卡托）轉成 `taiwan_path.json`；含本島、澎湖與周邊小島，不含金門、連江。非 AI 繪製、非手描。
- 原始資料：內政部國土測繪中心「直轄市、縣市界線(TWD97經緯度)」（data.gov.tw 資料集 7442），**授權方式：政府資料開放授權條款－第 1 版，免費**（法遵 11-06 結論；依據為 WebSearch 摘要讀到資料集 7442 頁面列 Open Government Data License v1.0、提供機關內政部國土測繪中心，信心：中高；taiwan-atlas 的 README 也寫明取自此資料集，信心：中高）。條款要求依附件格式標示提供機關、資料名稱，未標示視為自始未取得授權；與 CC BY 4.0 相容。
- 文案署名（Threads 第 1 則留言、IG 文末）：「地圖資料：內政部國土測繪中心「直轄市、縣市界線(TWD97經緯度)」，依政府資料開放授權條款第1版（data.gov.tw/license）釋出，經簡化改繪。」
- taiwan-atlas 的 MIT 授權只管它的程式與轉檔，圖片本身不必印 MIT 聲明；留在本檔備查即可（信心：中）。
- 為什麼不用 world-atlas：海岸線與縣市線要同一份資料才對得齊；world-atlas 沒有縣市界。
- 總部點位：桃園龜山，北緯 25.03、東經 121.36（同一投影算出）。

## 2026-11-10 封面照片出處更正（取代上面「Andy 從 Google 圖片搜尋找到」的說法）
- 封面照（藍色立體字「Quanta」＋階梯）：**Andy 本人拍攝（2026-11-10 確認）**，版權無疑慮，不需外部署名；文案已拿掉原本的「圖：廣達官方」署名行。手機原圖取得後會用原圖重出封面。
- 法遵曾因「疑似新頭殼新聞圖、查不到圖說」建議改用圖池 photo_8（COSCUP／CC BY-SA 2.0，廣達研究院招牌牆）；因 Andy 說明照片是自己拍的，**不採用**，備案成品存為 `1_cover_photo8.png`（若要用須在文案署名「圖：COSCUP／CC BY-SA 2.0（經裁切）」並註明合成圖同樣依 CC BY-SA 2.0 釋出）。
