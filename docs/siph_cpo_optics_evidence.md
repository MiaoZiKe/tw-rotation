# 矽光子／CPO 題材：光通訊與系統端查證報告

> 查證日：2026-10-24。分析師：ai-server-analyst。範圍：光源與磊晶、光被動、光引擎、模組、CPO 交換器、系統端。
> 半導體晶片／代工／封裝／設備由另一位同事負責，交界處以「交界」標註。本檔不改任何其他檔案、不 commit。

## 〇、環境限制（硬規矩第 6 條）

- 只能用 `WebSearch`，讀到的是**搜尋摘要而不是原文**。`WebFetch`／`curl` 被擋。
- 因此下表的「高」信心度＝**至少兩篇獨立摘要都講到同一件事**，並不代表我讀過原文。
- 最值得人工開一次原文的網址（已標 ★）：聯亞 2026-08-26 重訊與 Q2 法說、波若威 CPO 時程、眾達-KY 股東會、台積電 COUPE。
- 「括號英文對應」一律已獨立查證（本次沒有採用任何摘要自己湊出的中英對應）。

## 一、結構（由上游到系統端）

| 層 | 內容 | 重點 |
|---|---|---|
| L1 磊晶與晶粒 | InP／GaAs 磊晶片 → CW DFB／EML／VCSEL／PD 晶粒 | InP 基板缺料是全鏈瓶頸（2026-10 報導稱 9 月起逐步到貨）。聯亞是**磊晶廠**，晶粒後段另有代工 |
| L2 外部光源 | ELS／ELSFP（OIF 面板可插拔外置雷射模組），一個 ELSFP 供多個光引擎共用 | NVIDIA X800-Q3450 傳用 18 個 ELS、每個 8 顆 CW DFB（單一中文報導，信心中） |
| L3 光被動／光纖互連 | FAU（光纖陣列）、MT 插芯、V 型槽、微透鏡、隔離器、WDM、MPO／MTP、Shuffle Box、光纖背板 | FAU 對位精度 <0.1µm，被視為 CPO 量產瓶頸之一 |
| L4 光引擎 | 矽光子晶片＋FAU＋雷射耦合；台積電 COUPE 為封裝平台 | 光引擎晶圓與 COUPE 屬半導體同事範圍（交界） |
| L5 可插拔模組 | 800G／1.6T／3.2T；DSP、LPO、LRO 路線 | 1.6T 矽光模組佔比預估 60～70%（Nomura 觀點，單一來源）。3.2T 查不到可靠出貨資料 |
| L6 CPO 交換器 | NVIDIA Quantum-X／Spectrum-X Photonics；Broadcom TH5 Bailly、TH6 Davisson；Cisco、Arista | Davisson 2025-10 公告「shipping」實為送樣給早期客戶。Cisco／Arista 本次**查不到**具體產品資料，建議不畫或標「?」 |
| L7 機櫃內光互連／OCS | Google OCS（Lumentum MEMS、Coherent 液晶；自研由 Celestica 代工為推測） | **查不到台廠具名參與 OCS**；智邦 OCS／OWS 屬規劃與驗證階段 |
| L8 測試量測 | 光功率、BER | 本次未查到可具名台廠，留空 |

## 二、台股逐家查證

欄位：段落｜產品｜客戶｜時程（照原文，不寫現在式）｜信心｜來源與其具體內容。

### 2.1 L1 磊晶與雷射晶粒

**聯亞 3081（磊晶）｜信心：高（定位）／中（客戶具名）**
- 產品：InP／GaAs 磊晶片、CW Laser。客戶數由 7～8 家增至 10 家以上（uanalyze 摘要）。
- 重訊：2026-08-26 公告與「美國大廠」簽 4 年 CW Laser 長約（分析稱 2027～2030），公司未指名。
- 2026Q2 營收 12.21 億、EPS 4.62、毛利率 57.45%。2027 年產能倍數**兩說**：2.5 倍／1.5 倍，以法說簡報為準。
- 來源：uanalyze.com.tw/articles/2769454097（長約與增購 22.7 億設備）；uanalyze.com.tw/articles/6110153300（Q2 法說，明年產能 2.5 倍）；technews.tw/?p=1604562 系列。
- **聯亞→Coherent（現有 YAML 標 reported，strength 3）：本輪查不到任何來源**，Coherent／Lumentum 的 CW 需求與聯亞的直接供貨關係均未被摘要點名。建議降為 estimated 並補「推論依據」，或維持待補來源。

**全新 2455（磊晶，現屬 vpec／compound_semi）｜信心：中**
- 三五族磊晶龍頭；InP 磊晶台廠合計約 8 成由聯亞、全新、IET-KY 供應（單篇文章數字）。
- CW Laser：100／150mW 與日本客戶量產；多家美系大廠合作，**時程三說不一**（5 月說「已量產」、另一篇說「下半年量產」、8 月說「下半年小量出貨」）。EML 最快 2028 年後貢獻。
- 100G PD 自 2026-05 起出貨美系 800G 模組客戶；1.6T 的 200G PD 已完成驗證並進入量產（另一篇）。光電子占營收 27%（2026-04 單月）。
- 來源：wantrich.chinatimes.com/news/20260506900703-420101、ctee.com.tw/news/20260505700840-430205、uanalyze.com.tw/articles/2293048243。
- 缺：客戶未具名（「美系大廠」「日本客戶」）。**不可寫 Lumentum**。

**光環 3234（雷射晶粒後段代工＋自有 VCSEL）｜信心：中高**
- 已通過聯亞 CW Laser 後端製程驗證，**2026-06 起正式出貨**（technews truelight 2026/08/18 摘要）；另一篇稱「光環為聯亞後段代工廠」。2026 年代工營收比重預期高於 2025（公司說法），代工占比 19%。
- 自有 100G VCSEL／PD Array 仍在客戶認證或送樣；7 月營收約 0.96 億，2026 年 3 月單月仍虧損。
- 來源：technews.tw/2026/08/18/truelight-2026-july-and-q2-financial-report/；uanalyze.com.tw/articles/5537746443；moneyweekly.com.tw/_Article?AID=244679。
- **現有 YAML 沒有 lpc→光環 的 outsources_to 邊**，只有 lpc→luxnet。建議補（方向：聯亞付錢給光環）。

**交界（半導體同事）**：穩懋 3105（GaAs 代工，VCSEL／PIC，Lumentum 外包）、環宇-KY 4991（PD、70mW CW 已具量產能力、100G PD 2026-09 起出貨）、英特磊 4971（MBE InP 磊晶、PD 訂單成長、與光聖換股）。本檔不展開。

### 2.2 CW 雷射後段與模組

**華星光 4979｜信心：高（定位）／中（客戶）**
- CW Laser 後段代工＋光收發模組＋ELS。CW 出貨 2026 年較 2025 成長四倍；月產能將從 150 萬提升到 300～400 萬（**單位「片」「顆」兩說**），2027 年再增至 600 萬以上（單篇）。ZR 400G／800G 多為獨家代工，估市占 >50%。3 家以上美系 CSP 客戶（媒體說法，未具名）。
- 2025-11 ctee 摘要寫**最大客戶為邁威爾**；現有 YAML 的 `luxnet→accton` 邊（待補來源）本輪**找不到任何摘要支持**。建議降級或刪除，並以 Marvell／美系 CSP 為已見客戶。
- 1.6T 時程分歧：富果摘要稱「2026 小量」，較新報導稱「1.6T NPO 開發中、2027H2 量產」。採後者，並標「兩說」。
- 來源：uanalyze.com.tw/articles/2374955634；ctee.com.tw/news/20260723701022-430204；uanalyze.com.tw/articles/1095253305（聯亞法說稱外包代工）。

**聯鈞 3450｜信心：中高｜歸屬應為「雷射封測／ELS」而非上游磊晶**
- 全球前 3 大雷射二極體封測 EMS；具 EML 與 CW 封裝能力，雷射功率由 70mW 提高到 300～400mW。
- ELSFP 已進工程試產與小量生產（2026-09 報導），與雷射晶片廠、終端客戶、系統設計業者共同開發，**design-in 階段**。光創聯（非上市櫃）2027Q1 量產為同篇對照。
- 800G 模組驗證完成，2026 起逐季放量（2025-11 法說）；子公司源傑 AOC 打入美系雲端客戶。
- 來源：uanalyze.com.tw/articles/8331255940；news.cnyes.com/news/id/6243790；money.udn.com/money/story/5607/9649141。
- 缺：沒有任何客戶具名。

**前鼎 4908｜信心：中低**
- 實際營收主要是 100G～400G 光收發模組；ELSFP 屬**評估／開發中**（2025-08 法說），雷射 CoC 產線規劃 2026Q3 底完工。
- 「已打入輝達供應鏈」僅見股市新聞單一說法，另一篇明說小量，**本輪查不到公司或具名 NVIDIA 資料佐證**。不畫到 NVIDIA 的邊。
- 來源：uanalyze.com.tw/articles/5767855026；moneyweekly.com.tw/_Article?AID=255230；tw.stock.yahoo.com（GTC 釋利多）。

**眾達-KY 4977｜信心：高（Broadcom 關係）／中（時程）**
- Bailly CPO 光引擎與 ELSFP，配合 Broadcom。報導：「2026～2027 才是第一波大量導入」「2026 年對業績貢獻有限，2027 有機會顯著提升」（董座股東會）。
- 法人估每台 CPO 設備約需 32 顆 ELSFP，**是法人推估不是公司數字**。
- 來源：technews（finance.technews.tw/2025/12/09/pcl-technology/）；news.cnyes.com/news/id/6025072；moneyweekly.com.tw/_Article?AID=215069。
- 與現有 YAML 一致，無矛盾。

**訊芯-KY 6451（光寶集團，光引擎後段封裝）｜信心：中**
- 與台積電合作 COUPE，負責晶圓後的光學引擎後段整合、FAU、光柵耦合（董事長蔣尚義，股東會）。51.2T CPO 小量生產出貨中國與北美客戶，102.4T 已完成樣品（moneyweekly，未具名客戶）。
- **現有 groups.yaml／supply_chain.yaml 完全沒有訊芯-KY**，建議新增候選（需 Andy 校訂）。
- 來源：wantrich.chinatimes.com/news/20260626900590-420101；moneyweekly.com.tw/_Article?AID=246500。
- 缺：客戶未具名；母公司光寶科 2301 另稱「預期 2027 年出貨給 CPO 交換機廠」（單篇）。

### 2.3 光被動、光纖互連、光學元件

**波若威 3163｜信心：中高（NVIDIA）**
- CPO 產品：FAU、MPO、光纖套件／Shuffle Box，不做含 LD／PD／DSP 的收發模組。
- 時程（原文，非現在式）：CPO「第三季小量試產、第四季月出貨千顆等級、2027 年第一季萬顆等級」。已獲 NVIDIA「指定」之說來自報導，**本輪第二次搜尋沒有找到獨立原文**。
- 來源：technews.tw/2026/08/24/browave-shuffle-box-set-to-ramp-up-in-q4（現有 YAML 引用）；uanalyze.com.tw/articles/9352240540；news.cnyes.com/news/id/6297518。
- 與現有 YAML 一致。

**上詮 3363｜信心：中高**
- FAU：20／40／80 通道開發完成，部分已在客戶端量產測試；已開始交付 1.6T FAU（中時／工商報導）。
- 放量說法分歧：2025-11 櫃買業績發表會稱「2026 進入初期驗證基本產能，2027～2028 大規模放量」；較早報導稱 2026Q3 量產。**採前者**（公司自己講）。
- 「唯一與台積電 CPO 合作的光通訊廠」為單一分析觀點，未經證實。與現有 YAML 的 `foci→tsmc` 邊一致，但「COUPE 共同研發」建議保留 reported 即可、不再加碼。
- 來源：finance.technews.tw/2025/11/24/foci-3363/；news.cnyes.com/news/id/5809106；ctee.com.tw/news/20260724700230-430502。

**光聖 6442（含轉投資合聖）｜信心：中**
- 本業：資料中心光被動元件（北美大型資料中心／CSP，**未具名**；第三方稱「Google 概念股」，法說摘要未點名，**不可寫 Google**）。產能利用率 100%、訂單能見度到 2026 年底、毛利率 57%（法說摘要）。
- 合聖：CPO-ELS 模組（3.2T、6.4T 規格）與國際大廠後期驗證，最快 2026 年量產（市場消息）；FAU 送樣美系大廠，2026 年下半年小量試產；FAU 產線 2026Q4 試產、2027 下半年正式出貨。
- 與 IET-KY（英特磊）換股結盟（董事會 2025-12-04 決議，基準日兩度改期至 2026-05-05，**是否完成本輪未能確認**）。換股比例有兩種相反寫法，不寫比例。
- 來源：technews.tw/2026/06/22/authenx-taiwan-ipo/；blog.fugle.tw/post/earnings-call-6442-2026-03-12；udn.com/news/story/7240/9182814。

**大立光 3008｜信心：中（時程分歧大）**
- 四層堆疊 FA（精度 <0.3µm）通過客戶認證；FAU 第一條試量產線預計 9 月建置，「明年有望貢獻」；另一篇稱「最快 9 月試產、驗證 6 個月到一年、2028 年前才小量」。**兩說並列，不選**。
- 現有 YAML 註「收到量產型客戶正式規格、2026-07 送樣、2027 年中放量」，與本輪不衝突但比「2028 前小量」樂觀，建議註明分歧。
- 來源：bnext.com.tw/article/91621；technews.tw/2026/06/17/largan-2026-06-17-cpo/；uanalyze.com.tw/articles/8490656788。

**揚明光 3504｜信心：中（新增候選，使用者清單有名）**
- 2026-07-24 法說：MT 插芯 5 案開發、**2 案試產**，量產目標 2027 年初；模造玻璃 Lens Array 與光收發器為 POC。上半年稅後淨利僅 1,121 萬元。
- 來源：ec.ltn.com.tw/article/breakingnews/5516681；ctee.com.tw/news/20260724701827-430201。

**玉晶光 3406｜信心：中**
- V 型槽、稜鏡、光學插槽、MT 插芯，直接供 FAU 廠；多項已送樣、認證中；**CPO 真正放量落在 2027～2028 年，2026 全年 CPO 相關營收占比 <5%**（公司說法）。報導稱與上詮合作、3M 參與私募（4.68%）。
- 來源：ctee.com.tw/news/20260609700253-430502；ctee.com.tw/news/20260615700829-430201。

**亞光 3019｜信心：中低**
- 僅確認「奈米壓印超穎透鏡 Lens Array＋稜鏡一體化元件，預計 2026 年底送樣」（董事長說法）。玻璃 V 型槽／FAU 本身**查不到送樣**。屬「開發中」，邊強度 1 以下。
- 來源：udn.com/news/story/7253/9539162。

**統新 6426｜信心：中低｜東典 6588｜信心：低**
- 統新：光通訊濾光片（400G 用 7 片、800G 14 片、1.6T 28 片，報導數字）；2026Q1 營收 1.54 億、年增 56%。**客戶未具名；非 CPO 專屬**，建議放「光學薄膜／WDM 濾光片」。
- 東典：光通訊薄膜濾光片；2025-12 宣示轉型「整合型光電解決方案」；參與威力富增資，公司稱僅「評估」主動元件。**沒有量產雷射或模組證據**。
- 來源：wantrich.chinatimes.com/news/20260508900728-420101；udn.com/news/story/7240/9514545、wantrich.chinatimes.com/news/20260520900585-420101。

### 2.4 連接器、線纜、交換器、系統

**貿聯-KY 3665｜信心：高（事實）**
- 800G AEC 2025Q4 首度量產（銅纜，非光）；2026-01 完成收購深圳新富生光電（光纖跳線），技術移轉台南廠；2026-09 與 ams OSRAM 合作 scale-up 光互連（ECOC 2026 展示，**尚在展示階段**）；管理層稱 CPO 插拔接頭還要一兩年、短期以銅為主。
- 法人預估 CPO 相關方案「明年小量」（推估）。
- 來源：udn.com/news/story/7240/9345293；uanalyze.com.tw/articles/3176955718；cmoney.tw/notes/note-detail.aspx?nid=974381。

**鴻騰（鴻海／FIT，港股 6088，非台股）｜信心：中高**
- 展出 ELSFP 外置光源 2.0（對應 Tomahawk-6 CPO、16 通道 1.6T，已通過技術驗證）、224G NPO Socket、XPO；2024 年以約 10 億元取得華雲光電 70% 股權；與聯發科合作 CPO 連接方案。
- 來源：uanalyze.com.tw/articles/8458554813、bnext.com.tw/article/80012/fitconn-cpo-800g。
- 注意：**鴻騰不是鴻海 2317 本體**，代號與市場不同，建議以參考節點或掛鴻海之下。

**智邦 2345｜信心：高（Tomahawk）／中（CPO、OCS 時程）**
- 800G 已出貨（兩大 CSP＋一代工客戶），1.6T 2026H1 進入量產（Money 錢）。CPO（Tomahawk 6）與 OCS／OWS：「最快下半年」，**OCS 實際出貨未被任何摘要確認**；OWS 與美國 CSP、日本 NTT 在驗證階段。
- 智邦 OFC 2026 展示 Tomahawk 6 102.4T 交換器（官網，已在現有 YAML）。
- 「Micas Networks」的 Davisson CPO 1RU 計劃 2027Q1 投產，**是 Micas 不是智邦**，勿混。
- 來源：money.udn.com/money/story/5607/9442456；udn.com/news/story/7253/9561042；accton.com.tw/engineering-the-102-4t-switch/。

## 三、排除與「證據不足」清單

| 公司 | 結論 | 理由與來源 |
|---|---|---|
| 昇達科 3491 | **排除（且現有 groups.yaml silicon_photonics 含它，建議移出）** | 主力是低軌衛星毫米波／波導被動元件（LEO 營收占 69.9～80%）；搜尋摘要明說「沒有 CPO 或矽光子產品布局」。來源：pocket.tw/school/articles/7042/、moneyweekly.com.tw/_Article?AID=205962 |
| 萊德光電-KY 7717 | 排除出 CPO；現屬 optical_module 但**不是模組廠** | 光纖被動元件→衛星雷射通訊、高功率光纖合束器，客戶集中歐美，無 CPO 產品或客戶。來源：uanalyze.com.tw/articles/7571253780 |
| 廣達 2382、英業達 2356 | 查不到 CPO／矽光子角色 | 僅在股市新聞被順帶提及；不畫邊。來源：technews.tw/?p=1537032 |
| 正崴、嘉澤 | 查不到 | ELSFP 連接器摘要只有 TE、Molex、SENKO、Eugenlight，無台廠。不畫邊 |
| 建毅 | **無法辨識公司** | 搜尋無此公司；請 Andy 提供全名或代號 |
| 鴻海 2317 本體 | 無 CPO 光學直接證據 | 僅鴻騰有；2317 已是 assembly 節點 |
| Cisco、Arista | 查不到 CPO 產品細節 | 僅在市場報告名單出現。不畫 |
| 台廠×OCS | 查不到具名台廠供應 Google OCS | Cignal AI 20+ 供應商名單無台灣。智邦 OCS 屬自家規劃 |

## 四、關係（edges）

方向語意已自檢（錢／貨流向）。信心欄「高」＝兩個獨立摘要。時程皆照原文。

| from → to | rel | 品項 | 強度 | 信心 | 來源（具體內容） |
|---|---|---|---|---|---|
| 聯亞 → 美系光模組／雷射大廠（未具名） | supplies | CW Laser 磊晶（4 年長約，2027～2030） | 量產＋長約 | 高（事實）／對象未具名 | 公司重訊 2026-08-26（uanalyze/2769454097；另兩篇同） |
| 聯亞 → 中際旭創 | supplies | 磊晶 | 開發 | 低（推論，維持 estimated） | 現有 YAML 已降級；本輪仍未找到具名來源 |
| 聯亞 → Coherent | supplies | InP 磊晶 | 未知 | **低（本輪查不到）** | 現有 YAML 標 reported 沒有來源，建議降級 |
| 聯亞 → 華星光 | outsources_to | CW 晶粒後段代工（聯亞付錢） | 量產 | 中高 | 聯亞法說稱代工產能不足、部分外包（uanalyze/1095253305）；ctee 稱華星光為聯亞 CW 後段合作廠（2026 年 5 月摘要，間接引述） |
| 聯亞 → 光環 | outsources_to | CW 晶粒後段代工 | 2026-06 起出貨 | 中高 | technews truelight 2026/08/18；uanalyze/5537746443 |
| 華星光 → Marvell | supplies | 光收發模組 | 量產 | 中（2025-11 單篇 ctee） | 摘要：最大客戶為邁威爾 |
| 華星光 → 美系 CSP（3 家以上，未具名） | supplies | CW Laser／800G 模組 | 量產／小量 | 中 | 法說摘要 |
| 華星光 → 智邦 | supplies | 光收發模組 | 未知 | **低（查不到）** | 現有 YAML 待補來源，本輪無佐證 |
| 全新 → 美系 800G 模組客戶（未具名） | supplies | 100G PD 磊晶／晶粒 | 2026-05 起出貨 | 中 | wantrich 20260506900703 |
| 波若威 → NVIDIA | supplies | CPO 用光纖套件／FAU／Shuffle Box | 2026Q3 小量試產、Q4 千顆級、2027Q1 萬顆級 | 中高 | technews 2026/08/24；uanalyze/9352240540 |
| 上詮 → 台積電（COUPE） | supplies | FAU 對準接合 | 驗證／小量；大規模 2027～2028 | 中高 | technews 2025/11/24；cnyes/5809106 |
| 玉晶光 → 上詮 | supplies | V 型槽／稜鏡（FAU 零件） | 認證中 | 低～中（單篇報導稱合作） | ctee 20260615700829 |
| 眾達-KY → Broadcom | supplies | CPO 光引擎＋ELSFP（Bailly） | 量產準備；2026～2027 首波導入 | 高 | technews 2025/12/09；moneyweekly 215069；cnyes 6025072 |
| 聯鈞 → 未具名 | supplies | ELSFP／雷射封裝 | 工程試產＋小量；design-in | 中 | uanalyze/8331255940 |
| 光聖（合聖）→ 國際大廠（未具名） | supplies | CPO-ELS、FAU | 後期驗證／送樣；2026H2 小量 | 中 | technews 2026/06/22 |
| 訊芯-KY → 台積電（COUPE 夥伴）／北美客戶 | cooperates／supplies | 光引擎後段整合 | 51.2T 小量、102.4T 樣品 | 中 | wantrich 20260626900590 |
| 貿聯-KY → 資料中心客戶 | supplies | 800G AEC（銅）、光纖跳線 | 量產（銅）；光互連展示階段 | 高（銅）／低（光） | udn 9345293 |
| 鴻騰 → Broadcom TH6 平台 | supplies（展示） | ELSFP 2.0 | 技術驗證通過；出貨未揭露 | 中 | uanalyze/8458554813 |
| Broadcom → 智邦 | supplies | Tomahawk 交換器晶片 | 量產 | 高 | 現有 YAML（智邦官網）一致 |
| 台積電 → NVIDIA／Broadcom | supplies | COUPE 光引擎 | 2026 年量產說（NVIDIA 自述） | 中高（交界，半導體同事負責） | inside.com.tw/article/40860；storagereview（Davisson 採 COUPE） |
| Lumentum／Coherent → NVIDIA | supplies | CW／ELS 雷射 | 量產（Lumentum 為 Spectrum-X 供應） | 中 | optics.org、nand-research（國際參考節點） |
| 國際參考節點 | — | 中際旭創、新易盛、Fabrinet（3 位客戶 CPO 小量出貨、投資 Raytec）、Coherent、Lumentum | — | 中 | Fabrinet 財報電話會議摘要。**Fabrinet 與 NVIDIA 的合約本輪查不到** |

## 五、與既有資料的矛盾或需校訂處（最重要，依風險排序）

1. **昇達科 3491 在 `silicon_photonics`**：主力為衛星微波元件，無 CPO 證據，建議移出。
2. **`silicon_photonics` 的 note 寫「不含模組組裝」**，但群內有前鼎（模組）、聯鈞（雷射封測 EMS）、昇達科；與 `optical_module` 的定義互相打架。建議改成按環節重分組（見第六節）。
3. **`optical_module` note 寫「光收發模組的組裝與出貨」**，群內 4979 之外多為被動元件（波若威、光聖、統新、東典、萊德）或 ELS／引擎；分組語意與成分不符。
4. **`luxnet→accton` 邊**無佐證；**`lpc→coherent` 為 reported 但無來源**，兩條都應降級。
5. **缺 `lpc→光環` outsources_to**，且光環／全新 在 YAML 的歸屬（光環 3234 未見 supply_chain 節點、全新在 `compound_semi`）。
6. **時程**：上詮「FAU 2026Q3 微量貢獻」YAML 與公司 2025-11 說法（2026 進入初期驗證基本產能、2027～2028 放量）一致；大立光「2027 年中放量」與「2028 年前才小量」的報導並存，建議註明分歧。
7. 缺口：訊芯-KY、揚明光、玉晶光未在 YAML；鴻騰為港股，不宜用台股節點格式。

## 六、建議的分頁分組（供建分頁與畫圖）

| 組 | 成員（台股） | 參考節點 | 備註 |
|---|---|---|---|
| A 磊晶與晶粒 | 聯亞、全新、光環（後段代工） | 英特磊、環宇-KY、穩懋（交界） | 主圖上游；聯亞→光環／華星光為 outsources_to |
| B 外部光源 ELS／ELSFP | 眾達-KY、聯鈞、光聖(合聖)、前鼎(評估中)、華星光(CW 後段＋ELS) | 鴻騰、Lumentum、Coherent | 強度均標「驗證／小量」，畫細線 |
| C 光纖互連（FAU／MPO／Shuffle Box） | 波若威、上詮、光聖、大立光、揚明光、玉晶光、亞光(僅 Lens) | Corning | 全組標 2026H2～2028 試產／放量，禁現在式 |
| D 光引擎後段與封裝 | 訊芯-KY（需校訂新增） | 台積電 COUPE、Fabrinet | 與半導體同事交界 |
| E 可插拔模組與線纜 | 華星光、聯鈞(源傑 AOC)、前鼎、貿聯-KY（AEC／跳線） | 中際旭創、新易盛、Coherent | 800G 已量產、1.6T／3.2T 未全面 |
| F 光學薄膜／WDM | 統新、東典 | — | 低信心，可併入 E 或不上圖 |
| G CPO 交換器與系統 | 智邦（鴻海／鴻騰為參考） | NVIDIA、Broadcom、Cisco、Arista | 智邦 CPO／OCS 標「最快 2026H2」 |

**不上圖**：昇達科、萊德光電-KY、廣達、英業達、正崴、嘉澤、建毅（無法辨識）。

## 七、我沒問到、但撞到的錯誤（依風險）

1. 昇達科被歸在矽光子（見上）。
2. `lpc→coherent` 與 `luxnet→accton` 兩條無來源邊。
3. 摘要自己湊出的對應：把 Micas Networks 的 Davisson CPO 時程當成智邦（已排除）；把「大立光 FAU 2028 才量產」與「明年貢獻」混成同義（已並列）；IET-KY 與光聖換股比例兩種相反寫法（不採用）。
4. 全新：「已量產／下半年量產／下半年小量」三說，不可寫成單一現在式。
5. 「聯亞 2025 年矽光出貨成長」有「2～3 倍」與「23 倍」兩說（疑誤植），不採用。
6. 鴻騰為港股，與鴻海 2317 為不同證券。
7. 「七劍客」「8 家台廠」是投顧／媒體分類，非 NVIDIA 官方名單，不能當 NVIDIA 供應商佐證。
