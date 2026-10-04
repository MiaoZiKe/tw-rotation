# 孤立環節補邊證據表（被動元件以外，2026-10-04）

> 接 [`groups_passive_supply_evidence.md`](./groups_passive_supply_evidence.md)。Andy 的原話是「若是像這類只有單一個，幫我找找他是否有其他公司及族群，
> 例如他供應給誰、原物料是誰」。這份處理**被動元件以外**、在 `supply_chain.yaml` 裡沒有任何具名邊（孤立）的環節。
> 信心度與查證限制的定義同上一份（只有 WebSearch 摘要、沒讀到原文；高＝公司自己講＋多源轉述，中＝兩個以上獨立媒體，低＝推論，本批不畫低）。

## 1. 盤點（改前）

| 鏈 | 環節 | 台股節點數 | 孤立節點 | 本批結果 |
|---|---|---|---|---|
| semiconductor | test_interface 測試介面 | 4 | 旺矽、中華精測、雍智 | **三家都補上邊** |
| ai_server | hdi_pcb 高階 PCB | 6 | 精成科、瀚宇博、華通 | 華通補上（SpaceX）；精成科、瀚宇博查不到 |
| ai_server | ccl_material 銅箔／玻纖布／樹脂 | 6 | 榮科、德宏 | 榮科補上；德宏查不到 |
| ai_server | ccl | 4 | 騰輝 | 查不到 |
| ai_server | fpc | 2 | 嘉聯益 | 查不到 |
| electronics | passive_comp 等 | 5→ | 全部 | 見上一份 |
| electronics | handset_optics | 1 | 大立光 | 補上 Apple 官方名單「列名」邊 |
| electronics | net_equip | 4 | 中磊、正文、合勤 | 查不到（電信商不具名） |
| electronics | panel_mfg | 3 | 彩晶 | 沒重查（友達董事長明講不具名，上一輪已記） |
| software | sw_secops／sw_saas／sw_ecommerce | 8 | 全部 | 沒動（檔內已寫明上游不在這條鏈上、查不到原廠代理關係） |
| financial | fin_* | 20 | 全部 | 沒動（四種 rel 表達不了資金中介，刻意不畫） |

## 2. 新增邊（14 條：高 0、中 14、低 0）

| 邊 | 品項 | 來源（各講了什麼） |
|---|---|---|
| 雍智 → 聯發科 | 測試載板／SLT 介面 | cmnews https://cmnews.com.tw/article/newsyoudeservetoknow-472a54b5-4f63-11f1-8fe6-21616feae94d（聯發科為最大客戶、旗艦 Dimensity SLT）；NOWnews https://www.nownews.com/news/6789212 |
| 雍智 → 瑞昱 | Load Board | NOWnews 同上；第二次搜尋亦出現（長期主要客戶） |
| 雍智 → 世芯-KY | AI ASIC 測試載板 | 理財周刊 https://www.moneyweekly.com.tw/_Article?AID=249076；兩次搜尋都列世芯（3661）。摘要把世芯誤譯成 WorldWide Semiconductor，代號對得上 |
| 中華精測 → 聯發科／超微／輝達 | 晶圓測試卡、IC 測試板、AI GPU 測試載板 | 聯合新聞網 https://money.udn.com/money/story/5607/9478900（客戶涵蓋台日美系大廠，含聯發科、高通、超微、輝達、Apple；美系 GPU 大廠認證）；高通與 Apple 不連（高通本檔無節點、Apple 未見品項） |
| 旺矽 →（指定）輝達 | MEMS 探針卡 | 鉅亨 https://news.cnyes.com/news/id/6099629 等多家：通過 Rubin 專案驗證。**驗證≠出貨**，所以用 `designated_by` |
| 榮科 → 健鼎／華通／聯茂 | 電解銅箔 RTF／VLP／HVLP | udn https://money.udn.com/money/story/5607/9075210 與鉅亨公司簡介 https://www.cnyes.com/twstock/4989/company/profile：服務健鼎、華通、聯茂、KCE（敬鵬只出現在一篇、且不在本檔） |
| 華通 → SpaceX | 低軌衛星本體與地面接收站高階 HDI 板 | udn https://money.udn.com/money/story/5612/9280735、ETtoday https://finance.ettoday.net/news/3170056、鉅亨：合作逾十年。路透點名的是敬鵬、啟碁、昇達科，**華通不在路透點名名單**，是其他媒體寫「也供貨逾十年」 |
| 大立光／晶技／國巨 → Apple | 「列名」 | Apple 官方 Supplier List（PDF）、TrendForce https://www.trendforce.com/news/?p=8483、ocacnews https://ocacnews.net/article/321695：2023 名單把大立光、TXC、YAGEO 列為供應商；名單不列品項與金額，strength 一律 2 |

### 這批抓到的「摘要誤讀」（沒採用，留給下一個查的人）
1. **旺矽「取得亞馬遜 Trainium 3 兩大測試平台驗證」**：那兩個平台是 Advantest V93K 與 Teradyne UltraFLEX（**測試機台**），不是亞馬遜。畫「旺矽→雲端業者」會是錯的。
2. 搜尋摘要把「聯茂」譯成 Unimicron（欣興）。本檔的聯茂是 6213（CCL 廠），銅箔→CCL 的方向才合理。
3. 查榮科時，摘要有一次把「敬鵬」補進客戶名單；敬鵬 2355 不在本檔，且只在單一篇出現，不採用。
4. 查瀚宇博客戶，第二次搜尋只是把我的關鍵字（仁寶、廣達、和碩、緯創、英業達、鴻海…）原樣吐回來，**不算獨立來源**，所以那份客戶名單（出處不明）仍不畫。

## 3. 查不到（不畫，節點留著）

| 項目 | 查到什麼 | 為什麼不畫 |
|---|---|---|
| 精成科、瀚宇博 → 客戶 | 瀚宇博為精成科母公司（約 40% 持股，另有說法）；客戶名單出處單一不明 | 第二個獨立來源缺；母子關係無 `subsidiary_of`，不畫成 supplies |
| 德宏 → 客戶 | 石英纖維已穩定供應「日本客戶」三年、織布樣品送 CCL／PCB 認證 | 日本客戶與 CCL／PCB 客戶都不具名 |
| 騰輝 → 客戶 | 航太 PI 材料訂單強、切入高速光模組材料 | 客戶全不具名 |
| 嘉聯益 → 客戶 | 媒體稱開發 LCP 軟板天線供 Apple 手機、供美系筆電軟硬結合板、車用、低軌衛星 | 全部不具名（Apple 那一句來自媒體、公司未證實）；瀚宇博曾入股嘉聯益（持股關係，不畫） |
| 中磊／正文／合勤 → 電信商 | 中磊營收北美約 60％；北美前五大電信商（Comcast、Charter、AT&T、Verizon、T-Mobile）是整個 CPE 市場的買方 | 那是市場背景，不是「中磊供貨給 Comcast」。中磊、正文公司都不具名。另有**單一**第三方部落格 senki.org（US ISP CPE supply chain）寫 Comcast XB10 與 Charter 路由器有 Sercomm（中磊）供貨，以拆機／FCC 資料為依據；兩次再搜尋（英文、中文）都找不到第二個獨立來源，所以**不採用**，留給下一個查的人。 |
| 旺矽 → 雲端業者 | 見上「摘要誤讀」第 1 條 | 錯的 |
| 軟體鏈（安碁、中華資安、GSS、…）、金融鏈 | — | 沒重查（上游不在該鏈／schema 表達不了） |

## 4. 孤立節點棘輪（SC_ISO_MAX）

改前：ai_server 孤立 7（榮科、德宏、精成科、瀚宇博、華通、騰輝、嘉聯益），semiconductor 孤立 3（旺矽、中華精測、雍智）。
本批補完：ai_server 少 2（榮科、華通），semiconductor 少 3。實測數字與 `SC_ISO_MAX` 調整見 HANDOFF。
