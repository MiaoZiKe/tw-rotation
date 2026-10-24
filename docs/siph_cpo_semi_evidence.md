# 矽光子／CPO 半導體端查證報告

> 查證日期：2026-10-24（台北）。查證人：半導體鏈事實查證分析師。範圍：技術結構、台股半導體與設備供應鏈、關係邊。
> 對應工作：產業地圖新增「矽光子／CPO」題材分頁與 2D／3D 結構圖。本檔只是查證報告，**未改任何其他檔、未 commit**。

## 0. 環境限制與讀法（必讀）

- 這個容器的 `WebFetch` 打不開任何外部站（實測 `getaddrinfo ENOTFOUND`），**只有 `WebSearch` 可用**。我讀到的全是「搜尋摘要」，不是原文。
- 摘要是線索、不是事實。下列做過獨立交叉的項目才給「高」；只有單一來源或只有投顧／社群整理的，一律「中」或「低」。**信心度「中」以下不建議直接寫進公開網站。**
- 日期紀律：本題材大部分是**預期、送樣、驗證**，不是量產。下表凡寫「2026Q3／2027／2028」都是公司或媒體的目標，**不可在網站上寫成現在式**。
- 最值得人工開一次原文的網址：
  1. DIGITIMES〈CPO 先進測試戰線前移 設備鏈組隊搶統包主導權〉 https://www.digitimes.com.tw/tech/dt/n/shwnws.asp?id=767232
  2. 台積電侯上勇（SEMI 矽光子論壇）談 COUPE 量產與三大瓶頸 https://technews.tw/ai-agent/testing-is-the-critical-bottleneck-in-cpo-mass-production/7101/
  3. 台積電 2025 年報（COUPE 時程的一手來源，本輪查不到原文）

---

## 1. 技術結構

### 1.1 矽光子（SiPh）晶片組成（PIC 與 EIC 分工）

| 層 | 元件 | 白話功能 | 備註 |
|---|---|---|---|
| 光子晶片 PIC（矽，SOI 晶圓） | 光調變器：馬赫–任德 MZM／微環 MRM | 把電訊號「寫」到光上 | NVIDIA Quantum-X／Spectrum-X Photonics 用 **MRM**（微環）；MRM 小、省電，但對溫度敏感 |
| | 波導、分光／合光器 | 在晶片內走光 | |
| | 鍺光偵測器 Ge-PD | 把光「讀」回電 | |
| | 光柵耦合器（GC，垂直耦合）／邊緣耦合器（EC，側向耦合） | 光進出晶片的口 | 台積電 COUPE 兩種都支援（TrendForce／技術報導） |
| 電子晶片 EIC | Driver（驅動）、TIA（轉阻放大）、控制與 SerDes | 驅動調變器、放大接收訊號 | COUPE 的 EIC 製程：兩個來源互相矛盾，見 1.3 |
| 外部 | 雷射光源：外置雷射 ELS（Broadcom 為 ELSFP 模組）或內建 | 矽不會發光，光源必須是 InP／GaAs 化合物半導體 | NVIDIA 與 Broadcom 路線都以外置光源為主；InP 供給吃緊是業界共識 |
| 光纖介面 | 光纖陣列單元 FAU、微透鏡陣列 MLA、光纖套件 | 把光纖與 PIC 對準接合 | 對位精度 0.1 微米等級，目前以「主動對準」為主 |

重點：**PIC 是 CMOS 成熟製程（65nm 級 SOI）、EIC 是先進製程**，兩種晶片靠先進封裝疊在一起，這是台積電能切入的原因。

### 1.2 CPO／NPO／LPO／可插拔差異

| 架構 | 光引擎在哪 | 電路徑 | 能否現場更換 | 現況 |
|---|---|---|---|---|
| 可插拔光模組 | 獨立模組，插在面板籠架 | 公分至數十公分（含 PCB 走線） | 可 | 目前主流；單顆 800G 約 14–17W，其中 DSP 約 6–8W（FS.com 與陸媒整理，廠商說法） |
| LPO（線性驅動可插拔） | 同可插拔，但**拿掉 DSP**，由交換器 SerDes 補償 | 同上 | 可 | 省電，但距離與主機端要求高 |
| NPO（近封裝光學） | 光引擎與 ASIC 在**同一片 PCB／基板上但分屬不同封裝**，用插座連接 | 公分級 | 可（插座） | 視為 CPO 量產前過渡；2026-03 Ciena、Marvell 等六家簽 Open CPX MSA（插座式光引擎規範） |
| CPO（共同封裝光學） | 光引擎與交換器 ASIC **在同一個封裝基板／中介層上** | 毫米級 | 不可（維修難） | 2026 為量產起點年，大規模放量看 2027–2028（見風險） |

來源與分歧：定性比較見 https://community.FS.COM/article/lpo-vs-cpo-which-will-dominate-the-data-center-optical-interconnect.html、 https://www.ansys.com/zh-tw/blog/what-is-co-packaged-optics。pJ/bit 數字全是廠商自述（Broadcom 稱 2026 OFC 的 NPO 引擎約 1 pJ/bit；Ayar Labs 展示 5 pJ/bit），**沒有獨立測試，網站不建議放數字**。Broadcom 執行長公開看法是可插拔未來 5–7 年仍主導橫向擴展市場（同上陸媒整理，單一來源，信心中）。

### 1.3 EIC＋PIC 堆疊：台積電 COUPE

- 結構：用 **SoIC-X（銅對銅無凸塊接合）把 EIC 疊在 PIC 上**，接合間距小於 10 微米；是 3D 堆疊。來源：TrendForce https://www.trendforce.com/news/2026/04/01/news-silicon-photonics-race-intensifies-as-tsmc-targets-2026-coupe-production-samsung-eyes-2029-cpo-turnkey/ ；技術報導（technews 2026-03-17）https://technews.tw/2026/03/17/silicon-photonics-hits-the-market-tsmc-and-ase-spearhead-taiwans-strategic-push/
- **EIC 製程有兩個說法互相矛盾**：一說 N7 疊在 65nm SOI PIC（單一二手來源，轉自日媒）；另一說 EIC 為 6 奈米、PIC 為 65 奈米（搜尋摘要）。**不要在圖上寫死 N7 或 N6，只寫「先進製程 EIC＋65nm 級 SOI PIC」。**
- 世代（信心：中。NVIDIA 路線對應，來源為媒體整理，**不是台積電官方三代命名**）：
  1. 第一代：OSFP 可插拔內的光引擎，1.6 Tb/s（2025 驗證，200G 微環調變器 2026 量產，TrendForce／技術報導）。
  2. 第二代：COUPE 放到 CoWoS 基板上（on-substrate）成為真 CPO，目標 6.4 Tb/s（2026 年）。
  3. 第三代：進入處理器封裝內（中介層）達 12.8 Tb/s，時程未定。
  來源：https://technews.tw/2025/08/25/nv-silicon-photonics-cpo/（NVIDIA Hot Chips 與路線對齊）、技術報導 2026-03-17。
- 台積電官方（侯上勇，SEMI 矽光子論壇）：COUPE「按計畫今年（2026）量產」，量產三大瓶頸是**晶圓測試、FAU 整合、高速光學封裝組裝**。來源：https://technews.tw/ai-agent/testing-is-the-critical-bottleneck-in-cpo-mass-production/7101/ （摘要含 TechNews AI 摘要成分，數字如 6.4 Tbps、2027 年 PIC 月產能一萬片**未被官方確認，不用**）。
- 郭明錤（2025-01 報告，較舊）：奇景光電（Himax，美股，**非台股**）為 COUPE 第一、二代微透鏡陣列（MLA）獨家；上詮為第一、二代 FAU 獨家；AMD 可能是第一個採用者，NVIDIA Rubin Ultra 可能是首款 NVIDIA 產品。來源：搜尋摘要（technews.tw/?p=1336311 與 finance.technews.tw 2025-01-23 Himax 文）。**單一分析師預測，信心中，且上詮「獨家」用語網站不宜採用。**
- 台積電另一個維度：SoIC 的 N2 對 N2 堆疊 2028、A14 對 A14 2029（TrendForce 摘要）——這是 SoIC 路線，**不是 COUPE 第二代的量產日**，不要混用。

### 1.4 交換器 ASIC 與光引擎如何共同封裝

- Broadcom TH6-Davisson（102.4T，**2025-10-08 宣布出貨**）：**16 顆 6.4T 矽光子引擎＋TH6 交換器矽晶，共用同一片基板**；官方稱每個引擎用台積電 COUPE（storagereview 轉述，Broadcom 新聞稿為一手）。來源：https://investors.broadcom.com/news-releases/news-release-details/broadcom-announces-tomahawkr-6-davisson-industrys-first-1024 、https://www.storagereview.com/news/broadcom-ships-tomahawk-6-davisson-cpo-ethernet-switch-doubling-bandwidth-to-102-4-tb-s-for-ai-fabrics 。信心：高（兩者獨立，但 Broadcom 新聞稿是主角方自述）。上一代 Bailly 是 TH5 51.2T。
- NVIDIA Quantum-X Photonics（InfiniBand，144 埠 800G，約 115 Tb/s）：一個封裝整合 18 顆矽光子引擎、36 條雷射輸入；用微環調變器、台積電 3D COUPE。**時程來源互相矛盾**（2025 年底 vs 2026 初）；Spectrum-X Photonics（乙太網路，128 埠 800G，SN6810 為 102.4 Tb/s）原定 2026 下半年出貨；另有一則摘要稱 2026-06 台北 GTC 宣布 Spectrum-X Photonics 進入量產（單一摘要，信心低，未能核對原文）。來源：https://convergedigest.com/nvidia-debuts-spectrum-x-and-quantum-x-photonics-switches/ 、https://nand-research.com/nvidia-is-rewiring-the-data-center-with-light/ 。
- NVIDIA 公布的 CPO 合作夥伴（官方名單，**未說各自貢獻**）：Browave（波若威）、Coherent、Corning、Fabrinet、Foxconn、Lumentum、Senko、SPIL（矽品，日月光投控子公司）、Sumitomo、TFC、TSMC。來源：同上 technews／fintool 摘要。NAND Research 補充：SPIL 做 CPO 多晶片模組封裝、Fabrinet 做 CPO 組裝代工、Foxconn 做系統整合（單一研究公司，信心中）。
- 產業風險（必須在頁面備註）：SemiAnalysis 認為 CPO 大量產可能從 2027 延至 2028–2029（光引擎耦合良率、ASIC 整合、成本），高盛、摩根大通認為出貨未停擺（技術報導摘要，2026-06）。

### 1.5 代表平台一覽

| 公司／平台 | 架構重點 | 狀態（日期） | 與台股關聯 | 信心 |
|---|---|---|---|---|
| NVIDIA Quantum-X／Spectrum-X Photonics | MRM＋COUPE＋外置雷射，交換器 CPO | 宣布 2025-03；出貨時程各源不一（見 1.4） | 台積電、日月光(SPIL)、波若威、鴻海 | 中 |
| Broadcom Bailly(TH5)→Davisson(TH6) | 16×6.4T 引擎＋ASIC 同基板，COUPE | Davisson 2025-10-08 宣布出貨 | 台積電、力成(FOPLP 與光引擎，見 2.3) | 高 |
| 台積電 COUPE | SoIC-X 堆疊 EIC＋PIC | 2026 量產目標（台積電官員）；第三代時程未定 | 上詮(FAU)、設備鏈 | 中高 |
| Marvell＋Celestial AI | Photonic Fabric，光 I/O 可到晶粒任意位置 | 2025-12 宣布以約 32.5 億美元收購；營收貢獻預期 FY2028 下半年；是否已完成交割**本輪查不到** | 無直接台股關聯 | 中 |
| Ayar Labs（TeraPHY 光學小晶片） | 光 I/O chiplet，與 ASIC 同基板 | 2026 募資 $6.5 億；聯發科、世芯為股東（見 2.2） | 聯發科、世芯 | 高 |
| Lightmatter（Passage 3D CPO） | 光子中介層 | 2026-01-26 與創意宣布合作量產 CPO 方案 | 創意 | 高（新聞稿） |
| Intel OCI | 光學 I/O 小晶片 | 本輪**查不到最新狀態**；Intel 為 Ayar Labs 股東 | 無 | — |
| 三星 | 2029 CPO 統包（TrendForce 標題） | 路線圖，非量產 | 無 | 低 |

---

## 2. 台股供應鏈

### 2.0 重要提醒：判斷「有沒有實證」的標準

- **高**：公司自己說（法說、重訊、官方新聞稿）＋另一獨立來源（外資報告或財經媒體報導）講同一件事。
- **中**：只有媒體／投顧單一來源，或公司說在驗證但無客戶、無金額。
- **低**：僅社群／概念股清單／標題並列。
- 「排除」＝本輪查到的資料不足以證明該公司在矽光子／CPO 有業務；**不是證明它沒有**，之後有證據再補。

### 2.1 晶圓代工與化合物半導體

| 代號 | 公司 | 鏈上段落 | 做什麼 | 客戶 | 時程 | 信心 | 主要來源 |
|---|---|---|---|---|---|---|---|
| 2330 | 台積電 | 矽光子 PIC 晶圓＋COUPE 堆疊（SoIC）＋CoWoS 基板上 CPO | 製造 PIC、EIC，SoIC-X 堆疊；CPO 封裝 | NVIDIA、Broadcom（COUPE 官方引用）；AMD 傳為首個客戶（郭明錤，單一預測） | 2026 量產目標；200G 微環調變器 2026 量產 | 高（NVIDIA／Broadcom 方皆公開） | Broadcom 新聞稿；技術報導 2026-03-17；台積電侯上勇（technews 7101） |
| 2303 | 聯電 | 矽光子 PIC 晶圓（SOI），新加坡 12 吋廠 | 與 SILITH 交付首批 1.6T 矽光子**量產**晶圓，已獲一家大型雲端客戶認證；另與多家客戶做 PIC 風險試產（2026–2027）；新加坡 Fab12i P3 是矽光子與 CPO 基地、目標 2027 量產 | SILITH（新加坡 fabless）；雲端客戶未具名 | 2026-07-14 宣布首批量產晶圓 | 高（UMC 官方新聞稿＋Focus Taiwan 報導） | https://www.umc.com/en/News/press_release/Content/technology_related/20260714 、https://focustaiwan.tw/business/202607140015 |
| 5347 | 世界先進 | 矽光子製程元件庫（PDK） | 只查到經濟部「矽光子國家隊」規劃與世界先進合作開發製程元件庫 | 無 | 計畫期 2025–2028 | 低（僅政策計畫，無量產／客戶） | https://technews.tw/2025/06/28/ai-cop-silicon-photonics-co-packaged-optics/ |
| 3105 | 穩懋 | InP 雷射晶片代工（光源） | 報導稱是 Lumentum 雷射晶片長期代工廠；董事長稱 CPO 未來 1–2 年成主流、InP 原料可克服 | Lumentum（單一報導） | 未揭露 | 中（**單一媒體**，且該篇有字誤） | https://uanalyze.com.tw/articles/7091454027 |
| 8086 | 宏捷科 | 砷化鎵 PA 為主 | 本輪**查不到** InP／ELS／矽光子實證 | — | — | 排除 | hao.cnyes.com/post/52939 僅舊評論 |
| 2455 | 全新 | 磊晶（GaAs／InP） | 見既有 groups.yaml；本輪未重查 | — | — | 沿用既有（未重驗） | — |
| 3081 | 聯亞 | InP 磊晶（CW 雷射） | 既有資料已有，沿用；本輪未重查 | 美國客戶長約（未具名，yaml 已寫） | 2027–2030 長約（yaml） | 沿用既有 | — |

> 代號 5347 世界先進、3105 穩懋、2303 聯電、2330 台積電：我沒在本輪逐一對個股基本資料頁驗證，**這四個是大型股、同 repo 既有檔案已用**，風險低；寫進 YAML 前仍照規矩補驗。

### 2.2 IC 設計與設計服務

方向規則：設計服務（創意、世芯）是 turnkey，**向晶圓廠與封裝廠買產能**，所以 `tsmc → gud`，不是反過來；與光學夥伴的關係是「合作」不是供貨。

| 代號 | 公司 | 鏈上段落 | 做什麼 | 夥伴／客戶 | 時程 | 信心 | 來源 |
|---|---|---|---|---|---|---|---|
| 2454 | 聯發科 | 資料中心 ASIC（EIC 自研）＋光引擎夥伴 | 2026 Q1 投資 Ayar Labs 約 9,000 萬美元（約 2.4% 股權）；Computex 2026 展示 CPO 樣品：EIC 自家設計、PIC 與 Ayar Labs 共同開發；總經理稱 CPO 是最重要技術投資方向之一 | Ayar Labs | 展示（2026-06）；量產時程未揭露 | 高（聯發科 Q1 法說稿自述＋多篇獨立報導） | https://finance.technews.tw/2026/02/06/mediatek-is-fully-committed-to-the-development-of-silicon-photonics-and-co-packaging-optics/ 、https://www.technetbooks.com/2026/02/mediatek-invests-90-million-dollars-in.html 、MediaTek Q1 說明會逐字稿 |
| 6526 (待驗) | 達發科技（聯發科旗下） | 光模組 DSP | 報導稱 50G SerDes PAM4 DSP 已打入全球前十大光模組廠 | 光模組廠（未具名） | 已出貨（報導） | 低中（**單一摘要，代號我未驗，不可直接用**） | 搜尋摘要 |
| 3661 | 世芯-KY | ASIC 設計服務＋CPO 合作 | 2025-09 與 Ayar Labs 在台積電 OIP 展示 CPO 參考設計（2 顆 full-reticle 加速器＋8 HBM＋8 TeraPHY 引擎）；為 Ayar Labs 投資人；與光程研創轉投資「光循科技」宣布兩項 CPO 方案初步驗證，首款預計 2026Q3 | Ayar Labs；光循 | 展示／驗證階段 | 高（Ayar Labs＋Alchip 聯合新聞稿，加 Ayar 募資名單） | https://insidehpc.com/2025/09/alchip-and-ayar-labs-unveil-co-packaged-optics-for-ai-datacenter/ 、Ayar Labs Series E 報導（Alchip 列新投資人）https://finance.yahoo.com/news/ayar-labs-secures-500m-funding-101323199.html |
| 3443 | 創意 | ASIC 設計服務＋CPO 合作 | 2026-01-26 與 Lightmatter 宣布合作，把 Passage 3D CPO 做進 ASIC 方案（創意出 ASIC 設計與先進封裝）；外資稱新專案 2027 下半年可帶來約 5–6 億美元營收（**外資預估，非公司揭露**）；2025 另有與 Ayar Labs 合作消息（單一舊摘要） | Lightmatter | 合作宣布（2026-01）；爆發看 2028（媒體預期） | 高（Lightmatter 新聞稿＋創意 digitimes 稿） | https://www.businesswire.com/news/home/20260126496882/en/Lightmatter-and-GUC-Partner-to-Produce-Co-Packaged-Optics-CPO-Solutions-for-AI-Hyperscalers 、https://technews.tw/2026/06/25/guc-0625-cpo-and-cowos/ |
| 3035 | 智原 | 聯電陣營 ASIC 服務 | 本輪未查 CPO；聯電矽光子平台與智原是否綁定**查不到** | — | — | 排除 | — |
| 2379／3034／6415／6756 | 瑞昱／聯詠／矽力／威鋒等 | — | 搜尋 DSP／TIA／Driver 台廠，除聯發科（達發）外**查不到**瑞昱、聯詠、矽力、譜瑞的矽光子實證 | — | — | 排除 | 搜尋無結果 |

### 2.3 先進封裝與封測（含 CPO 封裝）

| 代號 | 公司 | 鏈上段落 | 做什麼 | 客戶／夥伴 | 時程 | 信心 | 來源 |
|---|---|---|---|---|---|---|---|
| 3711 | 日月光投控（含矽品 SPIL） | CPO 封裝＋測試 | NVIDIA 官方 CPO 合作名單列 SPIL；日月光自架全自動試產線，客戶驗證階段，法說稱預計 2027 小規模量產；**Q2 法說稱 CPO 營收與 2027 展望暫不揭露，約兩季後才提供** | NVIDIA（官方名單，未說貢獻） | 試產中；2027 小量產 | 中高（NVIDIA 官方名單＋公司法說說法，但營收不揭露） | https://www.bnext.com.tw/article/91677/ase_leap_revenue_2027_capex 、https://www.stockfeel.com.tw/?p=270330 、NVIDIA 夥伴名單（technews 2025-08-25） |
| 6239 | 力成 | CPO 光引擎封裝／FOPLP | 董事長稱：2026 年底小量生產光學引擎元件、2027 年中 FOPLP 量產、2027 下半年整合進矽光子交換器、2028 用於 AI 晶片；與 Broadcom 合作 FOPLP 與光通訊封裝，新加坡合資擴面板級產能；AMD 與 Broadcom 預訂多數 FOPLP 產能（德文單一來源） | Broadcom | 小量生產 2026 年底；量產 2027 | 中高（公司董事長說法＋多篇報導，但客戶規模未揭露；既有 YAML 已有 pti→broadcom 邊） | https://uanalyze.com.tw/articles/8235654083 、https://www.taiwannews.com.tw/news/6428264 |
| 6147 | 頎邦 | 驅動 IC 封裝（金凸塊）→ 光通訊 PD／TIA／調變器封裝 | 報導稱已切入 PD、TIA、光學調變器封裝，首個 TIA 專案 2026Q1 量產 | 未具名 | 2026Q1 起 | 低中（單一摘要） | https://statementdog.com/news/16766 |
| 2449 | 京元電子 | 高功耗 AI 晶片測試 | 本輪**查不到** CPO／光測實證；2026 資本支出 500 億，並與 NVIDIA 簽預付款協議（AI 晶片測試，非光測） | NVIDIA（AI 晶片測試） | — | 排除（CPO），列「AI 晶片測試鄰接」 | 搜尋摘要 |
| 6257 | 矽格 | 封測 | 查不到 CPO 實證 | — | — | 排除 | — |
| 3264 | 欣銓 | 測試 | 查不到 CPO 實證 | — | — | 排除 | — |

### 2.4 設備與測試介面（逐一查證，這是本題材最容易誤歸類的一段）

> 營收驅動是「客戶資本支出」，與產能廠景氣拐點不同，圖上要放在**設備／耗材**那一列，不要和封測廠同格。穎崴是測試介面耗材，不是封測服務。

#### 2.4.1 有實證（可列入）

| 代號 | 公司 | 在鏈上哪一段 | 具體產品／事實 | 客戶 | 時程 | 信心 | 來源 |
|---|---|---|---|---|---|---|---|
| 2360 | 致茂 | 光電測試設備（Insertion 1–4） | 2026-04-30 法說：CPO 四階段測試，PIC 測試、E-PIC 測試、光引擎測試已取得**採購訂單**；第四階段「光進光出」已全數接單，BER 訊號測試 6 月試產；CPO 今年起貢獻營收、**先前未納入年度預測**；2026 試產、最快 2027 全面量產；花旗預估光電營收 2026／2027 為 77 億／254 億（**外資預估**）；半導體／Photonics 測試解決方案 Q1 營收 34.1 億 | 未具名 | 2026 試產，2027 量產 | 高（法說＋花旗＋DIGITIMES 都講同一件事） | https://technews.tw/2026/04/30/chroma-2026-q1-financial-report/ 、https://www.digitimes.com.tw/tech/dt/n/shwnws.asp?id=767232 |
| 6223 | 旺矽 | 探針卡＋自有**雙面晶圓探針系統**（Insertion 2 對應） | 董事長稱 CPO 專案與客戶推進順利，晶圓段電光同測是最大挑戰；與是德科技組光子晶片測試聯盟；高盛：設備通過驗證後 **2026 下半年**開始貢獻營收；報導稱已通過 3–4 家客戶認可（日期不明）；探針卡主業營收強勁，**CPO 金額未揭露**；另有 Technoprobe 專利訴訟（2026-05）為風險 | 未具名 | 2026H2 起貢獻（高盛預估） | 高（公司說法＋高盛＋多篇） | https://blog.fugle.tw/post/earnings-call-6223-2025-08-20 、https://n.yam.com/Article/20260512570112 、https://money.udn.com/money/story/5607/9733022（大摩） |
| 6515 | 穎崴 | 晶圓級 CPO **測試介面**（耗材） | 已推出晶圓級 CPO 測試介面方案、稱獲多家客戶驗證；224G CPO 測試方案；2023 年推微間距對位**雙邊探測**方案並通過美系客戶驗證；營收地區別北美為主（既有調查：北美 81%）→ 不可能以日月光／京元電為主要出貨對象 | 美系客戶（未具名） | 驗證中 | 高（公司說法＋大摩＋媒體） | https://udn.com/news/story/7240/9503188 、https://technews.tw/?p=1555964 |
| 6187 | 萬潤 | **FAU 與光電晶片耦合設備**（主動對準，含點膠固化） | 自研光耦合設備：六軸耦合手臂、影像辨識、Active Alignment；報導稱與「指標龍頭廠商」合作的 CPO 設備**預計 2026Q3 交機並貢獻營收**；為日月光關鍵封裝設備供應商（點膠、AOI）。**報導未點名客戶、未提台積電** | 未具名（「指標龍頭」不可寫成台積電） | 2026Q3 交機（預期） | 中（單一 UDN 業界消息，公司未重訊；另有 DIGITIMES／大摩名單與 technews 設備清單把萬潤列入，但無細節） | https://udn.com/news/story/7240/9374619 、https://technews.tw/2026/09/29/cpo-equipment-new-battlefield-fau-coupling-devices-competitive-landscape/ |
| 4573 | 高明鐵（興櫃） | **耦光對位**（六軸主動對位平台）＋FAU＋MLA 精密組裝＋晶圓級光學檢測 | 取得 800G／1.6T 光模組耦光對位模組訂單；切入 CPO／NPO 封裝測試設備；展示 120 通道 FAU 與 PIC 主動對準。**興櫃：站內個股頁可能無日 K 資料** | 蘋果供應鏈／光模組廠（未具名） | 已出貨光模組耦光，CPO 為延伸 | 中（媒體報導，客戶未揭露；代號 4573 由報導確認） | https://www.bnext.com.tw/article/91936/gmt-4573-cpo-coupling-equipment |
| 6706 | 惠特 | 矽光子元件貼合機、光纖貼合、單晶點測、FAU 測試＋雷射元件代工 | 貼合機通過客戶驗證並小量出貨，主要客戶為**美系廠商**；CPO 設備與多家客戶做實驗機驗證，小量營收；2026Q2 目標轉盈（**本業仍虧損**）；雷射 DFB／EEL 量測與代工占比拉高 | 美系廠商（未具名） | 小量出貨；量產看認證 | 中（uanalyze 多篇同源於法說，無第二獨立來源） | https://uanalyze.com.tw/articles/9072341367 |
| 3131／3583 | 弘塑／辛耘 | SoIC／CoWoS／CoPoS 濕製程設備 | 與 COUPE 的關係是**間接**：SoIC 堆疊需要濕製程；弘塑稱 CPO 為研發重點之一；摩根大通稱成長主軸 2026 轉 WMCM、2027 再過渡到 CPO；CoPoS 設備傳辛耘比重高於弘塑（**傳聞**）。**未找到 CPO 專屬機台或訂單** | 台積電（間接，非 CPO 專屬） | — | 低（列「間接受惠」，**不要畫 CPO 專屬邊**） | https://technews.tw/2026/03/15/cpo-copos/ 、https://news.nextapple.com/finance/20260423/FEECA6E664453C2F4FDF6EA556734D78 |
| 7734 | 印能科技 | CPO 封裝**助焊劑殘留與空洞**處理（真空高壓高溫） | 第四代 EvoRTS 把殘留控制與除泡合在同一平台，公司稱已切入矽光子封裝應用；CPO 實質放量待終端；Q2 營收 9.13 億（年增 48%）；**客戶只以「晶圓代工大廠」「一線封測大廠」泛稱** | 未具名 | 開發參與，放量待終端 | 中（公司說法，無第二獨立來源，客戶不明） | https://www.ctee.com.tw/news/20260617700235-430502 、https://uanalyze.com.tw/articles/8274353297 |
| 6937 | 天虹科技 | 晶圓鍵合機／解鍵合機（CPO）、InP 相關設備、PLP、ALD | 媒體稱用於 CPO 的 bonder／de-bonder 已出貨客戶（**日期不明**）；2025 年報導稱攜手 3 家客戶開發 CPO 設備；2026H1 報導仍把 CPO 列為開發中設備；InP 設備已有訂單、受 InP 基板供給所限 | 未具名 | 出貨日期不明 | 中低（資訊互有出入，最保守取「開發中」） | https://statementdog.com/news/17401 |
| 7769 | 鴻勁精密 | 測試分選機（Handler）、主動溫控 | 報導稱 SLT 分選機已用於矽光子模組量產；正推進電測＋光測整合，光測聚焦光纖連接與對位，**預期明年底（約 2027 年底）可進入整合與量產**（此句日期可能已變）；列於大摩 CPO 測試受惠名單 | 未具名 | 2027 末 | 低中（單一摘要，代號 7769 單一來源，需驗） | https://www.ctee.com.tw/news/20260203700978-430201 、https://money.udn.com/money/story/5607/9733022 |
| 7856 | 漢測（漢民測試） | 薄膜式探針卡（Insertion 2／3） | 法說稱成立專責團隊做矽光子測試，**薄膜式探針卡已開始出貨**、5–6 月送樣客戶；服務**美系大廠** | 美系大廠（未具名） | 出貨／送樣 2026 | 低中（單一來源，代號 7856 需驗） | https://uanalyze.com.tw/articles/1125350302 |
| 7728 | 光焱科技 | **PIC 光學缺陷檢測設備**（NightJar／Night Jar-H） | 2026 上櫃；Night Jar-H 已完成開發，與「國際一線大廠」完成 PoT，**未點名客戶**；與汎銓有專利訴訟（2026-03 提告），閎康傳向光焱買設備（傳聞） | 未具名 | 年底前完成設備驗證 | 中 | https://udn.com/news/story/7240/9660806 、https://udn.com/news/story/7240/9574169 |
| 6830 | 汎銓 | 分析（第三方）＋**光損偵測設備 MSS HG**（銷售版） | 持有台、美、日、韓光損偵測專利；稱服務 4 家以上晶圓廠、PIC 設計、CPO 封裝廠、模組廠，含一家 Tier-1 AI 客戶（2 年合作，分析項目以 CPO 半成品與光引擎晶片為主）；銷售版預計 2026-09 定型、年底前啟動銷售；單台價格說法 4,000 萬調到 1 億（董座說法） | Tier-1 AI（未具名） | 設備銷售 2026 年底啟動 | 中（公司自述；專利訴訟中） | https://udn.com/news/story/7240/9574673 、https://www.ctee.com.tw/news/20260611701529-430201 |
| 3587 | 閎康 | 第三方分析（失效分析）：矽光子晶圓與晶片光電分析 | 稱已在全球主要矽光子供應鏈有逾 50% 客戶覆蓋，前十大矽光子客戶 2025 年合計貢獻約 1.91 億元（**公司自述，未揭露客戶**）；首套設備 8 月前建置，CPO 封裝模組檢測平台 2027Q2 前部署 | 未具名 | 2027Q2 | 中（公司自述） | https://udn.com/news/story/7240/9574673 |
| 均英精密（代號待查，非均豪） | 均英精密 | **FAU 自動檢測機 GTK-OSI1**（量測重複性 3σ ≤ 0.1 μm）；協助嘉基科技開發 CPO 測試機台 | 新聞稿，無訂單 | 未具名 | 2026-06 發表 | 低（新聞稿，非上市櫃已確認） | https://www.inside.com.tw/article/42389-CPO-FAU |

#### 2.4.2 排除（本輪查無矽光子／CPO 實證）

| 代號 | 公司 | 查到什麼 | 判定 |
|---|---|---|---|
| 5443 | 均豪 | 只查到再生晶圓與先進封測業務；曾與**均英精密**搞混，兩者不同公司 | 排除 |
| 2467 | 志聖 | 搜尋無任何 CPO／矽光子報導 | 排除 |
| 8027 | 鈦昇 | 同上，無 | 排除 |
| 8064 | 東捷 | 同上，無 | 排除 |
| 3535 | 晶彩科 | 同上，無 | 排除 |
| 3680 | 家登 | 僅工商時報一句「CPO 光電整合推升封裝載具需求」，**未點出家登 CPO 專屬產品或客戶**；本業 EUV POD、FOUP | 排除（頂多「先進封裝載具，CPO 為需求描述」低信心） |
| 7751 | 竑騰 | 搜尋只得營收與「半導體自動化生產及光學檢測設備、治具」業務簡介，**無 CPO 實證**；且按研究規則，代號 7751（≠6428）需個股基本資料確認 | 排除（待查） |
| 6217 | 中探針 | 測試座與 MEMS 探針（AI 測試），未在大摩 CPO 名單 | 排除 |
| 6640 | 均華 | 主要受惠 CoWoS 晶粒挑揀接合，與 CPO 直接關聯弱（單一分析文） | 排除 |
| 6510 | 精測 | 只有法人說「產品涵蓋 CPO 與矽光子」，**找不到認證／訂單**；本業手機 AP 與 AI 晶片測試 | 低（僅「測試介面鄰接」，不畫邊） |

#### 2.4.3 國際設備商（只當參考節點，不是台股）

ficonTEC（德國，耦合與測試；被稱為把雙面測試架構列為 Insertion 2 的設備大廠）、Suruga Seiki（日）、FormFactor（美，探針卡）、Keysight／是德（美，與旺矽組光子晶片測試聯盟）、Aerotech＋santec＋Senko（2026-01 發表 PICAlign 主動對準架構）、MRSI／ASMPT／Besi（固晶，本輪未查到 CPO 專屬細節，**僅參考**）。來源：DIGITIMES 767232、controleng／Aerotech 新聞稿（見 https://www.aerotech.com/press_releases/aerotech-santec-and-senko-collaboration-transforms-multichannel-active-alignment-for-co-packaged-optics-cpo-production/ ）。

### 2.5 既有資料交叉（避免矛盾）

- `groups.yaml` 的 `silicon_photonics` 群組：聯亞 3081、全新 2455、聯鈞 3450、上詮 3363、前鼎 4908、昇達科 3491，描述為「上游：InP／GaAs 磊晶、雷射晶粒、FAU 與被動元件」。**本題材新增的設備／測試／封測／設計公司，與這個群組不重疊，建議新分頁自成分層，不要塞進去**。
- `optical_module` 群組（華星光、波若威、眾達-KY、光聖、統新、光環、萊德、東典）是模組組裝，**不是本題材半導體端**，供畫圖時當右側「模組端」對照。
- `supply_chain.yaml` 既有：`pti→broadcom`（FOPLP CPO，reported）、`browave→nvidia`（光纖套件）、`上詮→台積電`（FAU/COUPE，已寫「FAU 2026Q3 才開始微量貢獻營收、2027 才放量」）、大立光 FAU（2026-07 送樣、最快 2026Q3 底試產、2027 年中放量；董事長 2026-04 稱「只是 FAU 端、距量產還有很長距離、產能布建需一兩年」）、聯亞→中際旭創（推論）。本報告與之**無矛盾**；新增的是設備鏈與測試鏈。

---

## 3. 關係（edges）

欄位：from → to｜供應／合作品項｜強度（量產／送樣驗證／開發中／合作宣布）｜信心｜依據。方向已想過：`supplies` 是 from 供貨給 to；設計服務買產能，所以晶圓廠在 from 一側。

| from | to | rel | 品項 | 強度 | 信心 | 依據 |
|---|---|---|---|---|---|---|
| 台積電 2330 | Broadcom | supplies | TH6-Davisson 用的矽光子引擎（COUPE）晶圓與堆疊 | 出貨（Davisson 宣布出貨 2025-10；每顆引擎用 COUPE） | 高 | Broadcom 新聞稿；storagereview |
| 台積電 2330 | NVIDIA | supplies | Quantum-X／Spectrum-X Photonics 的 COUPE 引擎 | 宣布；出貨時程各源不一（2025 末至 2026H2） | 中高 | NVIDIA 夥伴名單；convergedigest。**時程不可寫成現在式** |
| 台積電 2330 | AMD | supplies | COUPE | 傳聞（郭明錤 2025-01 單一預測） | 低 | **不建議畫** |
| 聯電 2303 | SILITH（國際） | supplies | 矽光子 1.6T 晶圓（新加坡 12 吋） | 首批量產晶圓交付（2026-07-14） | 高 | UMC 新聞稿；Focus Taiwan |
| 日月光投控 3711（SPIL） | NVIDIA | outsources_to（NVIDIA 把 CPO 封裝委外） | CPO 多晶片模組封裝 | 官方名單列 SPIL；日月光試產線客戶驗證、2027 小量產 | 中 | NVIDIA 夥伴名單；NAND Research；法說。**貢獻度未揭露，線畫細** |
| Broadcom | 力成 6239 | outsources_to | FOPLP 面板級封裝／光學引擎元件 | 小量生產 2026 年底；量產 2027 | 中高 | 力成董事長說法；taiwannews。既有 YAML 已有 `pti→broadcom`，**方向用語要與既有一致，勿重複畫兩條相反的線** |
| 台積電 2330 | 創意 3443（buys） | supplies | 先進製程晶圓＋CoWoS／COUPE 產能 | 設計服務買產能 | 高（慣例） | 設計服務是 turnkey；`tsmc → gud` |
| 台積電 2330 | 世芯 3661 | supplies | 同上 | 同上 | 高（慣例） | 同上 |
| Lightmatter | 創意 3443 | partners | Passage 3D CPO 整合進 ASIC | 合作宣布（2026-01-26） | 高 | Lightmatter 新聞稿 |
| Ayar Labs | 世芯 3661 | partners | TeraPHY 光學小晶片＋ASIC 參考設計 | 展示（2025-09 OIP）；世芯為 Ayar 投資人 | 高 | Ayar／Alchip 新聞稿；Ayar 募資名單 |
| Ayar Labs | 聯發科 2454 | partners | CPO 樣品：EIC 聯發科設計、PIC 與 Ayar 共同開發 | 展示（Computex 2026-06）；聯發科入股約 2.4% | 高 | 聯發科 Q1 法說稿；多篇報導 |
| 致茂 2360 | 台積電？ | — | 光電測試設備 | 取得多段採購訂單，**客戶未具名** | 不畫連到台積電的邊 | 法說未點名客戶 |
| 旺矽 6223 | 未具名客戶 | — | 探針卡／雙面晶圓探針 | 驗證中，2026H2 起貢獻（預估） | 不畫連到特定客戶 | 同上 |
| 穎崴 6515 | 美系客戶 | — | 晶圓級 CPO 測試介面 | 驗證中 | 不畫具名客戶邊 | 同上 |
| 萬潤 6187 | 未具名「指標龍頭」 | — | FAU 耦合設備 | 預計 2026Q3 交機 | 不畫 | 報導未點名 |
| 上詮 3363 | 台積電 2330 | supplies | COUPE 用 FAU | 既有邊；FAU 2026Q3 微量、2027 放量 | 沿用既有 | yaml |

邊的總體建議：**「設備／測試→具體客戶」在本輪幾乎都查不到具名客戶**，網站上這一層應用「環節（Insertion 1–4）」表達，而不是畫公司對公司的線；掛「?」。

---

## 4. 結構分層建議（供畫圖與建分頁）

### 4.1 縱向（2D 主圖：由上游到系統）

1. **雷射光源層**（InP／GaAs）：穩懋(中)、聯亞、全新（既有）；外部：Lumentum、Coherent
2. **PIC 光子晶片層**（SOI）：台積電(高)、聯電(高)
3. **EIC／ASIC 層**：Broadcom、NVIDIA、聯發科、世芯、創意（設計服務買產能 → 箭頭由晶圓廠指向它）
4. **堆疊／封裝層**：台積電 COUPE（SoIC-X）→ CoWoS 基板上 CPO；日月光／SPIL、力成(中高)
5. **光纖耦合層**：FAU／MLA（上詮、大立光、波若威；奇景為美股，列參考）
6. **模組／系統層**（對照，非本題材半導體端）：可插拔、NPO、LPO 對照框

### 4.2 橫向（量測與設備，掛在各 Insertion 上）

| Insertion | 階段 | 台股（有實證者） |
|---|---|---|
| 1 | PIC 晶圓測試（光＋電） | 致茂、旺矽、穎崴、漢測(低中) |
| 2 | EIC＋PIC 堆疊後晶圓測試（雙面探測，「上電下光」） | 旺矽(雙面探針系統)、穎崴(雙邊探測)、致茂 |
| 3 | 光引擎測試 | 致茂（最大市場，下半年試產） |
| 4 | 光進光出＋BER（系統級） | 致茂（光進光出已接單；BER 6 月試產）、鴻勁(低中) |
| 製程設備 | FAU 耦合／主動對準 | 萬潤(中)、高明鐵(中)、惠特(中)；均英精密（檢測，低） |
| 製程設備 | 光學缺陷檢測／失效分析 | 光焱(中)、汎銓(中)、閎康(中) |
| 製程設備 | 封裝殘留／鍵合 | 印能(中)、天虹(中低) |
| 間接 | SoIC／CoPoS 濕製程 | 弘塑、辛耘（低，標「間接」） |

### 4.3 3D 圖建議

- 一顆 CPO 交換器的剖視：中央 ASIC（TH6／NVIDIA 交換器晶片），四周環繞 16 顆（Davisson）或 18 顆（Quantum-X）光引擎，共用基板；每顆光引擎＝PIC（底）＋EIC（上，SoIC-X 堆疊）＋ FAU 從側邊或上方連出；外置雷射 ELSFP 另在面板側。
- 3D 與 2D 配色：可借用站內 3D 規範的「訊號藍」代表光路、「電力橘」代表電路；與 CPO 光路 flow 動畫一致（DECISIONS 3D 規範已提及 CPO 光路 flow）。
- 不要在圖上放：pJ/bit 數字、市占率、單顆價格（皆廠商自述或查不到）。

### 4.4 建議的分頁「環節」（供 supply_chain.yaml 草稿，Andy 校訂用）

`siph_laser`（雷射光源）、`siph_foundry`（PIC 代工）、`siph_asic`（ASIC／設計服務）、`siph_pkg`（先進封裝與 CPO 封裝）、`siph_fau`（光纖耦合元件，既有 silicon_photonics 群組的一部分）、`siph_test`（量測與測試介面）、`siph_equip`（耦合與製程設備）、`siph_analysis`（檢測分析）。其中 `siph_test`、`siph_equip`、`siph_analysis` 三者**營收驅動是客戶資本支出**，建議在 UI 上標「設備／耗材」。

---

## 5. 你沒問到、但我撞到的錯誤或缺漏（由重到輕）

1. **均英精密 vs 均豪 5443 容易搞混**：CPO FAU 檢測機是均英精密，不是均豪。若有人從「均豪＋FAU」的標題收進來會直接錯公司。
2. **「指標龍頭廠商」不等於台積電**：萬潤報導原文只說「與指標龍頭廠商合作」，沒有提台積電、沒有客戶名。畫線到台積電是推論，不可標事實。
3. **台積電 COUPE 的 EIC 製程有 N7／N6 兩種說法**，且「第一代、第二代、第三代」是媒體對應 NVIDIA 路線的說法，不是台積電官方命名。圖上別寫死。
4. **NVIDIA 光子交換器出貨時程互相矛盾**：Quantum-X 一說 2025 年末、一說 2026 初；Spectrum-X 原定 2026H2，另有一則摘要稱 2026-06 已宣布量產（單源）。網站請用「宣布／預計」措辭，並附日期。
5. **郭明錤「上詮獨家 FAU」「奇景獨家 MLA」是 2025-01 的單一分析師說法**，不宜寫「獨家」。
6. **CPO 量產延後風險**：SemiAnalysis 認為大量產可能延到 2028–2029；多數設備商的「營收貢獻」依賴 2027 年放量，頁面備註要寫。
7. **代號未驗**：達發 6526(?)、漢測 7856、鴻勁 7769、4573 高明鐵（興櫃，個股頁多半沒資料）、均英精密代號。照規矩，寫進 YAML 前每個都要個股基本資料等級來源驗過。
8. **既有 YAML 已有的 `silicon_photonics` 群組不含任何半導體端公司**，新分頁建立後，台積電 2330、聯電 2303、日月光 3711 等要注意不要被「同一股票歸兩個題材」的量能規則卡住（題材量能不拆分，已有規則，正常）。
9. **汎銓與光焱專利訴訟、旺矽與 Technoprobe 專利訴訟**：三家公司的「CPO 概念」都有訴訟風險，頁面備註建議帶一句。
10. **世界先進 5347、聯電的矽光子描述不要混**：聯電已有量產晶圓宣布；世界先進僅政策計畫的元件庫，不能同列「量產」。
11. **Marvell＋Celestial AI**：收購案的交割狀態本輪沒查到。若要畫，標「已宣布」而非「已併入」。
12. **Intel OCI、三星 CPO 路線**本輪查不到最新資訊，圖上若放要標「參考」。

---

## 6. 本輪沒查到、建議人工補的清單

- 台積電官方：COUPE 第二代量產時程、EIC 製程節點（看 2025 年報／2026 技術論壇簡報）。
- 日月光 CPO 營收規模（Q2 法說稱約兩季後才揭露，等 2026Q4 法說）。
- 聯電 SILITH 之外的 PIC 客戶是否有台股公司。
- 光焱、汎銓、閎康三家的具名客戶。
- 欣銓、矽格、京元電是否有光測設備投資（目前一律查無）。
- 瑞昱、聯詠、矽力、譜瑞在 Driver／TIA 的角色（搜尋無結果，不代表沒有）。
