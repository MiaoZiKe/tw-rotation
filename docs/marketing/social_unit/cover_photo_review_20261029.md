# 封面實景照片審查紀錄（2026-10-29，Andy：「封面沒圖片需要添加」）

依 docs/marketing/social_unit/ai_image_review.md 的十條清單逐張檢查。**這批全部是 Wikimedia Commons 實景照片（不是 AI 生圖）**，
已在圖池 pool.json 經 art-director 審過（reviewed: true）；這裡另看「套版後成品」與「內容和主題是否相符、有無錯配」。
第 2 條（真實建築／logo）與第 9 條（版權）對實景照片的判準改為：可辨識建築只准配講那個機構的貼文（Fed 大樓只配 FOMC）；授權須為 CC BY／CC BY-SA／公眾領域並在卡上標作者與授權。
第 4 條明亮度：照片灰階平均 ≥ 100（實景照片放寬；夜景、看盤螢幕這類偏暗的 56／86 已排除在通用圖之外）。
程式重疊檢查：16 張 0 筆（render_news_cards CHECK）；人工：16 張全解析度逐張看過，文字都在照片下方白底區，無壓字。

審查人：美編（art-director 清單，由本批負責工程師代執行並逐張目視）｜時間：2026-10-29（台北）

| 卡 | 標題 | 照片 | 授權／作者 | 照片灰階 | 1 無多餘文字 | 2 建築／logo 配對 | 3 無畸形 | 4 明亮 | 5 色調 | 6 不擋標題 | 7 解析度 | 8 主題相符 | 9 授權 | 10 質感 | 結論 | 說明 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| news1 | 泰國央行／經濟成長率2.4% | `_category/航運/photo_3.jpg`（container port） | CC BY-SA 3.0／H. Zell | 136 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 外國央行沒有對應建築照 → 通用「貨櫃港口」，象徵經濟活動，不指涉特定國家或央行；不誤導 |
| news2 | 歐洲天然氣價格／97.35歐元/MWh | `_category/能源/photo_7.jpg`（LNG tanker） | CC BY-SA 4.0／Gordon Leggett | 169 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | LNG 運輸船，對應歐洲天然氣報價；相符 |
| news3 | 摩爾線程第3季財報／淨利4,930萬人民幣 | `_category/半導體/photo_1.jpg`（integrated circuit die） | CC BY-SA 4.0／Mister rf | 157 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 晶片裸晶（IC die），對應 GPU 晶片公司；相符（非摩爾線程產品實物，屬類別圖） |
| news4 | 康寧第3季核心／營收50.8億美元 | `_category/網通/photo_8.jpg`（patch panel network cables） | CC BY-SA 4.0／Dsimic | 117 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1280px） | 通過 | 通過 | 通過 | **通過** | 網路配線架（網通類別），對應光通訊營收；相符（類別圖） |
| news5 | Google第2季雲端／營收250億美元 | `alphabet/photo_1.jpg`（Google data center） | CC BY 2.0／Chad Davis | 106 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | Google 資料中心實景（公司圖池），對應雲端營收；相符 |
| evg_cowos | CoWoS／先進封裝一分鐘看懂 | `_category/半導體/photo_2.jpg`（integrated circuit die） | CC BY-SA 4.0／Mister rf | 149 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 晶片裸晶，對應先進封裝；相符（類別圖，非 CoWoS 實物） |
| evg_hbm | HBM／高頻寬記憶體是什麼 | `_category/記憶體/photo_5.jpg`（DDR4 SDRAM） | CC BY-SA 4.0／D-Kuru | 141 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | DRAM 記憶體模組；HBM 由 DRAM 堆疊而成，語意一致（非 HBM 實物） |
| evg_three_inst | 三大法人／是哪三類？ | `_category/金融/photo_2.jpg`（Xinyi District skyline） | CC BY 2.0／MiNe | 155 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 台北信義區金融區街景，對應法人／資本市場；通用財經 |
| evg_margin | 融資融券／是什麼意思？ | `_category/金融/photo_3.jpg`（Xinyi District skyline） | CC BY 2.0／Jirka Matousek | 157 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 台北信義區金融區街景，對應信用交易；通用財經 |
| evg_fomc | FOMC／利率決議怎麼看 | `_category/總經_央行/photo_1.jpg`（Marriner S. Eccles Federal Reserve Board Building） | CC BY-SA 3.0／AgnosticPreachersKid | 134 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 美國聯準會 Eccles 大樓，FOMC 開會地點；相符 |
| evg_cpi_pce | CPI 與 PCE／兩種物價指標 | `_category/總經_物價就業/photo_2.jpg`（supermarket shelves） | CC BY-SA 4.0／Wilfredor | 118 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 超市生鮮貨架，對應物價指數；相符 |
| evg_ic_flow | 一顆 IC／怎麼做出來？ | `_category/半導體/photo_3.jpg`（integrated circuit die） | CC BY-SA 4.0／Mister rf | 142 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 晶片裸晶與打線，對應 IC 製造流程；相符 |
| evg_cooling | AI 伺服器散熱／氣冷與液冷 | `_category/散熱/photo_2.jpg`（heat sink） | CC BY-SA 4.0／DMGualtieri | 158 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 散熱鰭片實物，對應氣冷散熱；相符 |
| evg_abf | ABF 載板／晶片的轉接層 | `_category/PCB/photo_1.jpg`（printed circuit board） | CC BY-SA 4.0／Mister rf | 183 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 電路板（PCB 類別），ABF 載板屬電路板／載板產業；相符（非 ABF 實物） |
| evg_monthly_rev | 月營收／年增與月增怎麼看 | `_category/總經/photo_6.jpg`（Taipei 101 skyline） | CC BY 2.0／Andrew Van Ova | 140 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 台北 101 日景，台股通用圖；通用財經 |
| evg_eps | EPS／每股盈餘是什麼 | `_category/總經/photo_7.jpg`（Taipei 101 skyline） | CC BY 2.0／othree | 126 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過 | 通過（1920px） | 通過 | 通過 | 通過 | **通過** | 台北 101 日景，台股通用圖；通用財經 |

- 結論：16 張全部通過。
- 第 1 條備註：三大法人原本配的證交所看盤螢幕（總經/photo_4，滿版數字、灰階 56）改掉，避免畫面裡的報價數字被誤認為當天行情。
- 退回與替換紀錄：HBM 原配老式陶瓷 DIP 晶片（記憶體/photo_1）→ 改 DRAM 模組；月營收原配台北夜景（總經/photo_2，灰階 86）→ 改 101 日景；
  歐洲天然氣原配抽油機（總經_能源/photo_8）→ 改 LNG 運輸船；泰國央行原配 CNC 切割機（總經_景氣/photo_1，與主題關聯弱）→ 改貨櫃港口。
- 圖檔：本機重出樣本（scratchpad，未進 repo）
