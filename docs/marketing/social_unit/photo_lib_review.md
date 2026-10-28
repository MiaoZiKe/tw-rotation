# 公司實景照片審核清單（art-director，2026-10-28 第 1 版）

Andy 10-28 原話：新聞卡上方的大數字灰框改成「對應的實景圖片」（例如報導 SK 海力士／三星就放該公司總部或廠房照片），圖片上方放標題（主體＋事件小標），大數字仍在下方大標。圖片保持原色，不得套色調遮罩。

## 一、來源與入庫

- 只用 Wikimedia Commons 的 **CC0／CC BY／CC BY-SA／公有領域**照片；禁止新聞媒體照片、Google 圖片、公司官網照片、任何 LOGO 圖。
- 抓圖：`.github/workflows/company_photos.yml`（手動觸發＋每週一 03:17 台北）跑 `scripts/company_photos.py`，名單在 `social/photo_lib/targets.json`，中文主體名→slug 對照在 `social/photo_lib/aliases.json`（只做「完全相同名稱」比對，避免「南亞」吃到「南亞科」）。
- 每家存 `social/photo_lib/<slug>/photo.jpg`（原色、只縮放到寬 ≤1920）＋`meta.json`（license、author、source_url、file_title、reviewed:false）。
- 已審核（reviewed:true）的圖排程重抓時不會被覆蓋。

## 二、審核流程

1. art-director 用 Read 看 `photo.jpg` 全解析度，並開 `source_url` 的授權資訊（meta.json 已存）。
2. 再看**套上 D-實景版型後的成品**（照片會被裁成 952 寬的橫幅，取中段）。
3. 逐項填下表，任一條退回＝整張退回。
4. 通過：把 meta.json 的 `reviewed` 改 `true`、`reviewer` 填 `art-director`、`review_note` 寫日期與結論；並在本檔第四節加一列。
5. 退回：刪掉該 slug 資料夾或在 `targets.json` 換更精準的查詢字，重跑工作流程（`refresh=true`）。
6. **reviewed=false 的照片，`scripts/social_news.py` 一律不用**，那篇自動退回灰框大數字版。

## 三、審核項目

| # | 項目 | 通過 | 退回 |
|---|---|---|---|
| 1 | 主體正確 | 照片確實是該公司的總部、廠房、園區或該公司的船隊（航運） | 同名不同公司、別家公司建築、只是附近街景 |
| 2 | 授權 | CC0／CC BY／CC BY-SA／公有領域，作者欄可辨識；卡上標示「攝影：作者／授權・Wikimedia Commons」 | NC、ND、GFDL-only、授權不明、作者欄空白且無法補 |
| 3 | 無人臉、無個人 | 無可辨識人臉、車牌 | 主角是人物（執行長演講照等） |
| 4 | LOGO 佔比 | 建築上的招牌字只是場景的一部分、不是畫面主角 | 畫面主角是 LOGO 或招牌特寫 |
| 5 | 原色 | 未經套色、未加濾鏡遮罩（版型也不加） | 原圖本身是強烈濾鏡或黑白藝術照 |
| 6 | 裁切後 | 裁成 952×約 380～460 的橫幅後主體仍在畫面內、不被切掉 | 主體在畫面邊緣、裁完只剩天空或地面 |
| 7 | 清晰度 | 寬 ≥1200px，放大 100% 不糊 | 糊、色帶、壓縮方塊 |
| 8 | 時效與誤導 | 不暗示新聞事件本身（火災、抗議、施工事故） | 事故、示威、災害畫面 |
| 9 | 專業質感 | 構圖乾淨、日間、曝光正常 | 歪斜、嚴重逆光、雜物佔畫面 |

## 四、審核紀錄

| slug | 檔名 | 授權 | 結論 | 日期 | 備註 |
|---|---|---|---|---|---|
| （尚無；第一次抓圖後待審） | | | | | |
