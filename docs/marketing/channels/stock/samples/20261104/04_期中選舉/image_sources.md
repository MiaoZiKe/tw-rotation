# 圖片來源與授權｜期中選舉後台股怎麼走？

取得日期：2026-11-04（台北）

| 圖 | 內容 | 來源 | 授權 |
|---|---|---|---|
| 01_cover.jpg～05_close.jpg | 全部為自製圖表與版面（陽光糖果版型，SVG 幾何圖示、長條圖） | 自製；數據取自本站資料庫（證交所指數、Yahoo 美股指數日線）與公開媒體報導 | 自製，無第三方圖片；無比比、無 AI 生圖、無新聞照 |

- 未使用任何新聞通訊社或媒體照片。若日後要加國會大廈實景，備案為 Wikimedia Commons CC 授權照（須照授權標示、保存授權頁網址），本篇未用。
- 字型：Noto Sans TC（OFL）、Inter（OFL），可商用。

## 11-04 改版：A 柔和版（A_soft/）、B 專業版（B_pro/）封面真實照片

Andy 11-04：「版面風格調整不要太鮮豔、柔和一點，另一個專業點，封面必須附圖片、真實圖片，附出處小小備註」。

| 項目 | 內容 |
|---|---|
| 照片 | Eccles Building（美國聯準會總部大樓，華盛頓特區，門前有美國國旗），Wikimedia Commons「File:Eccles_Building_(26088200676).jpg」 |
| 頁面 | https://commons.wikimedia.org/wiki/File:Eccles_Building_(26088200676).jpg |
| 作者／授權 | Federalreserve（聯準會官方），Public domain（公有領域） |
| 取得 | repo 已審圖池 `social/photo_lib/_category/總經_央行/photo_2.jpg`（2026-10-28 art-director 審核通過），本次 2026-11-04 取用 |
| 圖上出處 | 「圖：Federal Reserve／公有領域（Wikimedia Commons）」，封面照片下方 20px，不壓在照片上 |
| 處理 | 只裁切與降飽和（A 較多、B 輕微），未修改內容；無人物、無新聞照、無 AI 生圖、無比比 |

- 備註：容器無法連 Commons，未能下載國會大廈照片，故用池內已審的美國華盛頓特區官方建築照；若 Andy 要國會大廈，需另取 Commons CC 照片。
- 第 3 張分類由「產業輪動」改「歷史對照」；其餘文字與數字不變。產生器：`render_AB.py`（需 Noto Sans TC 字型）。

## 11-04 下午：B 專業版封面換美國國會大廈（已發布）

Andy 11-04 13:2x：「B 專業版，封面換國會大廈」「B 專業版我喜歡等等發布」。只換 B_pro/01_cover.jpg，其他 4 張不動；A 柔和版仍是 Eccles Building。

| 項目 | 內容 |
|---|---|
| 照片 | United States Capitol 西側外觀（華盛頓特區），Wikimedia Commons「File:United States Capitol - west front.jpg」 |
| 頁面 | https://commons.wikimedia.org/wiki/File:United_States_Capitol_-_west_front.jpg |
| 作者／授權 | Architect of the Capitol（國會建築師辦公室，aoc.gov），Public domain（公有領域，美國聯邦政府作品） |
| 取得 | 2026-11-04 由 GitHub Actions「公司實景照片」（company_photos.yml，run 41779934868）抓進圖池 `social/photo_lib/_category/總經_美國政治/photo_1.jpg`（1920×996，原色只縮放） |
| 審核 | 2026-11-04 依 art-director 十條清單審核通過（灰階平均 132；無人物特寫、無文字、無 logo；可辨識建築只配美國國會／期中選舉主題），紀錄在該圖池 pool.json |
| 圖上出處 | 「圖：Architect of the Capitol／公有領域（Wikimedia Commons）」，封面照片下方 20px，不壓在照片上 |
| 處理 | 只裁切（object-position 50% 58%）與輕微降飽和（saturate .8），未修改內容；無 AI 生圖、無比比 |

- 重疊檢查：程式 14 個文字區塊 0 筆（check.js）；人工 1 格全解析度親自看過 0 筆（穹頂完整、出處在照片下方、標題不壓照片）。
- 發布用圖與佇列：main 的 `social/ig/images/manual/2026-11-04-midterm-pro/`、`social/threads/queue/2026-11-04_midterm-pro.md`、`social/ig/queue/2026-11-04_midterm-pro.md`。
- 發布前文案依 11/4 即時報導更新：參議院翻盤（CNBC、NBC、The Hill）；期貨幅度各家 -0.8%～-1.3%（標普）、-1.7%～-2.2%（那指），改寫成「約跌 1%／約跌 2%」。第 2 張圖保留「11/04 早盤快照」原數字（標普 −0.8%～−1%、那指 −1.8%），屬當時快照。
