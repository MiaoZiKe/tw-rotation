# 矽晶圓、第三代半導體、CNC 工具機、工業自動化 補環節與補邊證據表（2026-10-04）

> 接 [`groups_sc_fill_1004_evidence.md`](./groups_sc_fill_1004_evidence.md)。Andy（附「產業地圖 → 半導體 → 矽晶圓」剖析圖，3D 柴氏長晶爐，下方完全沒有供應鏈關聯圖）：
> 「為何矽晶圓沒有產業鏈，它應該要有供應誰以及供應商」。CEO 的口徑是：#317 規定剖析圖分頁下方顯示整條鏈並反亮「圖上標的環節」，
> 交集為空的四張（矽晶圓、CNC 工具機、工業自動化、寬能隙）當時整塊不顯示；這句話代表**四張都要有關聯圖**。
>
> 查證限制同上一份：只有 WebSearch 摘要（讀不到原文）；摘要會自己補對應關係，所以**第二個獨立來源**或**公司／官方文件自己講**才採用。
> 信心度：高＝`verified`（公司或官方文件自己講）、中＝`reported`（兩個以上獨立媒體，或公司說法經媒體轉述）、低＝`estimated`（推論，**本批不畫**）。

## 1. 查原因（為什麼那四張下面沒有關聯圖）

兩層，都要補：

1. **YAML 根本沒有對應的環節。** `supply_chain.yaml` 半導體鏈原本 14 格，沒有一格是矽晶圓，也沒有第三代半導體；一般電子鏈沒有傳動件、控制器、工具機整機、機器人。
   前一批的剖析圖作者因此**刻意一個 `data-seg` 都不掛**（硬掛 `semi_material`＝宣稱光洋科做矽晶圓、掛 `foundry`＝宣稱台積電自己長晶圓）。
2. **前端零件掛的是佔位 id。** 2D（`site/dg/*.js`）零件只有 `data-part`、沒有 `data-seg`；3D（`site/three3d.js`）零件的 `seg` 是佔位的族群 id
   （`silicon_wafer`／`wide_bandgap`／`motion_axis`／`machine_tool`），不是任何環節。#317 的 `relScopeNow()` 取「圖上 `data-seg` ∩ 這條鏈的環節」，所以交集為空、整塊 `#relSec` 被藏起來。

修法：補 11 個環節（`segments:` 尾端，color_idx 不洗掉既有顏色）→ 把兩邊的零件都掛到真的環節 → `_uitest` 把「交集空要整塊不顯示」改成「每張都要有關聯圖且反亮」。

## 2. 新增環節（11 個）

| 鏈 | 環節 id | 名稱 | 上中下游 | role | 台股節點 | 外商節點 |
|---|---|---|---|---|---|---|
| semiconductor | `poly_silicon` | 多晶矽原料 | 上游（layer 0） | material（`material_of: wafer_si`） | 無 | **只寫 note**（Wacker、Tokuyama、Hemlock、OCI） |
| semiconductor | `crystal_equip` | 長晶爐與熱場耗材 | 上游（0） | equipment | 無 | **只寫 note**（可引用的只有 PVA TePla） |
| semiconductor | `wafer_si` | 矽晶圓 | 中上游（1） | material（`material_of: foundry, dram_nor`） | 環球晶 6488、台勝科 3532、合晶 6182 | SUMCO、信越半導體 SEH、Siltronic、SK siltron |
| semiconductor | `wbg_substrate` | SiC／GaN 基板 | 上游（0） | material（`material_of: wbg_epi`） | 無（環球晶 SiC 基板在 `wafer_si`） | Wolfspeed |
| semiconductor | `wbg_epi` | SiC／GaN 磊晶 | 中上游（1） | material（`material_of: wbg_device`） | 嘉晶 3016 | — |
| semiconductor | `wbg_device` | 第三代半導體元件／代工 | 中游（2） | core | 漢磊 3707 | — |
| semiconductor | `power_idm` | 功率 IDM／GaN 設計商 | 下游（3） | core | 無 | Infineon、onsemi、STMicro、Renesas、Navitas |
| electronics | `motion_parts` | 傳動與氣動元件 | 上游（1） | core | 上銀 2049、全球傳動 4540、直得 1597、大銀微 4576、台灣精銳 4583、亞德客 1590 | — |
| electronics | `cnc_controller` | CNC 控制器與驅動 | 上游（1） | core | 新代 7750 | —（FANUC 等只寫 note） |
| electronics | `cnc_machine` | CNC 工具機整機 | 中游（2） | core | 東台 4526、程泰 1583、恩德 1528 | — |
| electronics | `factory_robot` | 機器人與自動化系統 | 上游（1） | core | 達明 4585、所羅門 2359、盟立 2464 | — |

兩個「只有 note、沒有公司節點」的環節（`poly_silicon`、`crystal_equip`）是**刻意的**：半導體鏈的孤立節點棘輪 `SC_ISO_MAX["semiconductor"] = 0`，
畫一個沒有邊的外商節點就會頂破它，而那種節點本來就沒有資訊量。關聯圖上沒有台股的環節會顯示 note，名字照樣看得到。

## 3. 新增邊（27 條：高 10、中 17、低 0）

### 3.1 高信心（公司或官方文件自己講）10 條

| 邊 | 品項 | 來源 |
|---|---|---|
| 環球晶／台勝科／SUMCO／信越半導體 SEH／Siltronic／SK siltron → 台積電（6 條） | 12 吋原料晶圓 | 台積電年報「採購」段：六家（FST、GlobalWafers、SEH、Siltronic、SK siltron、SUMCO）合計供應全球 9 成以上原料晶圓，並向多家採購以分散風險。2016 年版五家、2022 年版加入 SK siltron。https://investor.tsmc.com/static/annualReports/2022/english/ebook/files/basic-html/page106.html （搜尋摘要讀到該頁；各家占比年報不揭露，strength 一律 3） |
| 環球晶 → 美光 | 12 吋矽晶圓，10 年期供貨協議＋5 億美元策略資金 | 2026-07-09 雙方同步宣布：eeNews Europe https://www.eenewseurope.com/en/micron-texas-wafer-supply-globalwafers-500-million/ 、Tom's Hardware（美光新聞稿）。宣布時是「將簽訂」十年期協議 |
| 力積電 → Navitas | GaN 8 吋晶圓代工（100V～650V，竹南 8B 廠、0.18µm） | Navitas 2025-07-01 宣布策略合作；科技新報 https://technews.tw/?p=1406816 、鉅亨、經濟日報一致 |
| Wolfspeed → Infineon | 150 mm SiC 晶圓多年期供貨協議（2018 簽、後續擴大延長） | Wolfspeed 官網新聞稿 https://www.wolfspeed.com/company/news-events/news/infineon-and-wolfspeed-expand-and-extend-multi-year-silicon-carbide-sic-150mm-wafer-supply-agreement/zh-tw |
| Wolfspeed → Renesas | SiC 裸晶圓與磊晶片，10 年、20 億美元 | 科技新報 https://finance.technews.tw/2023/07/06/wolfspeed-renesas-electronics/ 。2025 年 Wolfspeed 曾聲請破產重整，現況以公司公告為準 |

### 3.2 中信心（兩個以上獨立來源，或公司說法經媒體轉述）17 條

| 邊 | 品項 | 來源與限制 |
|---|---|---|
| 台勝科 → 聯電／南亞科／華邦電／美光（4 條） | 8／12 吋矽晶圓 | 公司法說會（富果整理 2017、2018 逐字稿）＋NOWnews https://www.nownews.com/news/2611329 ，兩者客戶名單口徑一致：晶圓代工（台積電、聯電、世界先進、力晶、中芯）與記憶體（南亞科、旺宏、華邦電、美光）。法說是舊的，超過 180 天會自動標 stale。世界先進、旺宏、中芯、力晶沒有節點所以沒畫 |
| 合晶 → 台積電／聯電／力積電／英飛凌／安森美／意法（6 條） | 12 吋與功率元件用矽晶圓 | 總經理說明彰化二林廠「為了」這幾家而擴（Yahoo 股市 https://tw.stock.yahoo.com/news/%E5%90%88%E6%99%B6%E8%91%A3%E5%BA%A7%E7%9B%B4%E8%A8%80%E5%9B%9E%E5%8D%87%E9%80%9F%E5%BA%A6%E6%B2%92%E6%83%B3%E5%83%8F%E4%B8%AD%E5%BF%AB-%E5%BD%B0%E5%8C%96%E4%BA%8C%E6%9E%97%E6%93%B4%E5%BB%A0%E4%B8%BB%E4%BE%9B%E5%8F%B0%E7%A9%8D%E9%9B%BB%E8%88%87idm%E5%BB%A0-005239417.html 、另有 udn、工商時報、vocus 多篇同一組名單）。**是擴廠對象不是出貨金額**，strength ≤ 3；力積電只在其中一輪摘要出現，給 2 |
| SUMCO → 台勝科 | 大股東與 12 吋技術來源 | 優分析 https://uanalyze.com.tw/articles/4236154143 ＋科技新報：SUMCO TECHXIV 持股約 43～48%（各篇口徑不同）、2026-08-27 減持後約 38%；台勝科 12 吋擴建導入 SUMCO 技術。**語意是股東＋技術，不是買賣**，比照日東紡→建榮用 `supplies` 承載並在 item 寫明 |
| 嘉晶 → 漢磊 | 矽與 SiC 磊晶片 | 優分析 https://uanalyze.com.tw/articles/7456031963 、富果 2021Q3 法說：漢磊持股嘉晶約 52.5%、嘉晶主要供應漢磊代工。母子垂直分工 |
| 台積電 → Navitas | GaN 晶圓代工（台積電 2027-07-31 結束 GaN 代工） | 科技新報 https://technews.tw/2025/07/03/tsmc-withdraws-from-gallium-nitride-business/ ＋CMoney／理財周刊（Navitas 是台積電主要 GaN 客戶、占其 GaN 產能一半以上，法人估計）。「退場中」的關係 |
| 達明 → 廣達 | 協作型機器人（廣達工廠約 2,000 台） | 工商時報 https://www.ctee.com.tw/news/20251219700104-439901 、聯合報、財訊多家一致：廣達→廣明→達明；廣達是主要客戶之一。母集團關係 |
| 盟立 → 友達／群創（2 條） | 光電面板廠自動化搬運與倉儲 | CMoney https://www.cmoney.tw/notes/note-detail.aspx?nid=95411 ＋自由時報：客戶含台積電、友達、群創；2026 年光電面板自動化只占產品組合約 11%（媒體整理）。台積電在半導體鏈，跨鏈的邊畫不出來（見 §5） |
| 新代 → 程泰 | CNC 控制器（與程泰、亞崴策略結盟） | 自由時報 https://ec.ltn.com.tw/article/breakingnews/5451254 、聯合報、工商時報三家一致，2026-05。**結盟≠出貨**，沒揭露搭載量，strength 2 |

## 4. 查不到的（節點留著或只寫 note，不畫邊）

| 項目 | 查到什麼 | 為什麼不畫 |
|---|---|---|
| 多晶矽廠（Wacker、Tokuyama、Hemlock、OCI）→ 環球晶／台勝科／合晶 | 市調報告摘要只有「這四家是主要多晶矽廠」；Tokuyama 與 OCI 在馬來西亞砂拉越有合資的半導體級多晶矽廠（IFC 2026 新聞稿）；一個聚合器摘要稱 Wacker 把 SUMCO 與 GlobalWafers 列為客戶（單一低等級來源） | 沒有任何具名供貨協議原文。Wacker↔Siltronic 淵源很深（Siltronic 原為 Wacker 子公司），但兩次搜尋都沒找到多晶矽供貨協議原文。只寫 note |
| 石英坩堝、石墨熱場、長晶爐、切磨拋設備 → 環球晶等 | 長晶爐可引用的只有 PVA TePla（產品目錄列有 EKZ 系列 CZ 提拉爐，最大 300 mm 晶碇）；坩堝與熱場查不到可引用的廠商 | 台股查不到專做這幾項的上市櫃廠；沒有具名來源可以連。**不憑記憶補名單** |
| 中美晶 5483 | 持有環球晶約 47%；2026H1 中美晶合併營收 405.0 億中環球晶 292.0 億（約 72%，其餘是朋程、台特化、宏捷科等）；2025 全年 781.7 億中環球晶 606.0 億（約 78%） | **母子口徑**：放進來會把同一份晶圓營收算兩次；中美晶→環球晶不是買賣，畫不出邊，節點會孤立（棘輪）。只寫在環球晶節點與 `wafer_si` 的 note |
| 昇陽半導體 8028（再生晶圓）、中砂 1560 | 台灣再生晶圓龍頭；擴產與台積電 2 奈米、美光 HBM 需求有關（媒體） | 查不到具名客戶，節點會孤立。2D 零件 `sw_reclaim` 明寫 `cos: []` 並用文字講 |
| 世界先進 5347 | 2024-09 認購漢磊私募約 13% 成為最大股東，雙方推 8 吋 SiC（漢磊轉移技術、世界先進營運量產，目標 2026H 下半年）；台勝科客戶名單含世界先進；Navitas 評估過但選了力積電 | **加了節點就會在 AI 伺服器鏈圖上孤立**：晶圓代工環節在 `CHAIN_EXTRA.ai_server` 裡，世界先進的邊另一端（漢磊、台勝科）不在那張圖，`SC_ISO_MAX["ai_server"]` 剛好等於現況 5，頂破。所以只寫在漢磊的 note |
| 漢磊 → 客戶 | SiC 主要客戶近兩年來自中國電動車與太陽能（媒體）；2024 產品應用比重（工業 44%、車用 28%、消費 21%、綠能 7%） | 全部不具名 |
| 嘉晶 → 外部客戶、環球晶 SiC → 客戶 | 環球晶法說：8 吋 SiC 客戶以車用與高功率 IDM 為主 | 不具名 |
| 東台、程泰、恩德 → 客戶 | 東台電子事業部占接單約 30%（半導體、PCB 設備），客戶產業含半導體設備、新能源車、航太；程泰產品獲國內汽車零組件與航太大廠採用 | 全部不具名。「台灣八成工具機客戶指定 FANUC」只有單一媒體來源，不寫 |
| 上銀、全球傳動、直得、台灣精銳、亞德客 → 客戶 | 大銀微 → 應材／ASML／科磊（多家媒體）；上銀終端含工具機、半導體設備 | 大銀微的客戶是外商設備廠，另一端不在一般電子鏈；其餘都是泛稱 |
| 所羅門 → 客戶 | 媒體列的是國際品牌（Meta、Dell…） | 沒有具名台廠關係 |
| 盟立 → 台積電 | 盟立打進 CoWoS／CoPoS 的 EFEM、OHT（多家媒體） | 台積電在半導體鏈、盟立在一般電子鏈，**跨鏈的邊兩邊都畫不出來**（度數只算兩端都在這條鏈的邊），放進 YAML 只會是沒人看得到的死資料，改寫在節點 note |

## 5. 摘要誤讀與分類問題（留給下一個查的人）

1. **富強鑫 6603 不是 CNC 工具機**：它是塑膠射出成型機（媒體、公司產品頁一致），`groups.yaml` 把它放在 `machine_tool` 族群。這一批的 `cnc_machine` 環節**不放它**；2D 圖 `mc_inject` 一直明寫這件事。
   **建議（不自動改）**：Andy 校訂時考慮把 6603 從 `machine_tool` 移出，或另開塑機族群。
2. **盟立 2464 主體已偏半導體設備**：2026 年產品組合半導體設備系統約 57%、智慧自動化約 16%、光電面板自動化約 11%。放在 `factory_automation` 族群不算錯，但資金故事跟半導體先進封裝設備比較像。
3. **`groups.yaml` 的 `factory_automation` 還有五檔這一批沒放進節點**：和椿 6215、大量 3167、鈦昇 8027、竹陞 6739、精確 3162。
   這批沒有逐家查它們的主營收來源（時間花在有圖可驗證的那幾檔），**寧可少列一檔、不亂歸類**；它們的 3D 零件沒有掛 `codes`，點下去不會列它們。
   下一批要補時，先用 `盟立`那種方式查「產品組合占比」，再決定放 `factory_robot` 還是另開環節。
4. **穩懋 3105／宏捷科 8086 不放第三代半導體**：做的是 GaAs（砷化鎵）射頻，不是功率用寬能隙（穩懋另有 GaN 射頻製程，營收主體仍是 GaAs）。
   `wide_bandgap.js` 本來就有一條警語：一次搜尋摘要把兩檔直接譯成兩家美國公司，那組對應是摘要自己湊的。這一批沒有重蹈。
5. 搜尋摘要把「合晶客戶：台積電、聯電、力積電」譯成 "MediaTek (聯電)"、"PowerTech Technology"、"Power Integrated Electronics" 三種不同寫法，名單以公司總經理的中文說法為準。
6. 台灣精材（做半導體設備用高純度陶瓷／石英／矽耗材）**不是**長晶用石英坩堝廠，不放進 `crystal_equip`。

## 6. 孤立節點棘輪（SC_ISO_MAX）

改前：ai_server 5、semiconductor 0。這一批新增的半導體鏈節點（環球晶、台勝科、合晶、漢磊、嘉晶、SUMCO、SEH、Siltronic、SK siltron、Wolfspeed、Infineon、onsemi、STMicro、Renesas、Navitas）**每一個都至少有一條邊**；
新增的邊只連到半導體鏈內的節點。AI 伺服器鏈的圖只借用 `ic_design／foundry／adv_pkg／hbm／abf_pcb／substrate_material／osat_test／test_interface` 八格，新節點都不在這八格，所以 ai_server 孤立數不增。
一般電子鏈沒有棘輪：新增節點中孤立的是上銀、全球傳動、直得、大銀微、台灣精銳、亞德客、東台、恩德、所羅門（9 檔，查不到具名客戶；圖上掛「?」）。實測數字與 `SC_ISO_MAX` 見 HANDOFF。
