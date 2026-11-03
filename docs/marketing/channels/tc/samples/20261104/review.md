# 美編審查紀錄（2026-11-04）

> 說明：本次執行環境沒有可派工的 Agent 工具，無法真的叫 `art-director` 與三位供應鏈分析師。以下是執行者依 art-director 清單自查的結果，**不等於專業美編審過**，請 CEO 補派 `art-director` 複審後再採用（建議複審項目列在最後）。

| 項目 | 01 先進封裝 | 02 HBM | 03 液冷 | 結論 |
|---|---|---|---|---|
| 版型 = 頻道二瑞士極簡（白／黑／瑞士紅／灰／細線／淡灰面） | 符 | 符 | 符 | 通過 |
| 照片為主、標題條與出處列分離 | 符 | 符 | 符 | 通過 |
| 出處字在圖上看得清楚（23～25px，灰 #595959 對白底對比約 7:1） | 符 | 符 | 符 | 通過 |
| 照片與主題相符 | 部分：早期 ROM 裸晶打線封裝，只能示意「封裝」，不是 CoWoS | 部分：一般 DDR4 模組，不是 HBM | 符：水冷冷板＋銅管 | 圖說已明寫「示意、非 CoWoS／非 HBM／非 AI 伺服器」；若要更貼題需官方新聞室素材（待 Andy 下載） |
| 照片裁切 | 裸晶居中、不切到重點 | 模組完整 | 冷板與銅管完整 | 通過 |
| 照片內可見廠牌 | 晶片僅編號 | 晶片上有廠牌標記（照片原貌） | 無 | 02 圖說已寫「與文中公司無關」；建議換圖或接受 |
| LOGO | 無 | 無 | 無 | 通過 |
| 比比／AI 生圖／新聞照 | 無 | 無 | 無 | 通過 |
| 文末一句「與各公司無合作或授權關係」 | 有 | 有 | 有 | 通過 |
| 字型 | 文泉驛正黑（容器唯一中文字型） | 同 | 同 | 正式出圖建議換 Noto Sans TC |
| 重疊檢查（程式，逐元素 getBoundingClientRect 兩兩相交＋溢出） | 0 筆 | 0 筆 | 0 筆 | 通過 |

## 人工目視（全解析度 1080×1350 逐張看過）
- 標題兩行不擠、與細線留白足夠；步驟卡 4 張等寬等高，卡內最長文字（「以 CoWoS 接在同一片矽中介層」）兩行內收完。
- 「誰供應誰」小字在 02、03 兩張實為流程而非供應關係，宜改為「流程示意」（待美編決定，已列複審項）。

## 建議 art-director 複審項目
1. 02 圖是否換成其他無廠牌的記憶體照（圖庫 `記憶體/photo_7.jpg` 為報廢模組堆，不建議）。
2. 步驟卡下方留白偏多，可把照片高度加到 460。
3. 字型換 Noto Sans TC 後重跑 `render.py` 並重做重疊檢查。


## art-director 複審（2026-11-04）

> 前面的自查表不是專業審；本節為 art-director 依審圖清單逐張審的結論，已直接改圖並重出。

| 項目 | 01 先進封裝 | 02 HBM | 03 液冷 |
|---|---|---|---|
| 字級（內文 29、步驟名 30、說明 23、出處 22～25，皆 ≥ 22px） | 過 | 過 | 過 |
| 層次（標題 68 > 內文 29 > 卡片 > 出處；只有瑞士紅一個重點色） | 過 | 過（紅色只給 TSV，一眼看到重點） | 過 |
| 出處字可讀性（灰 #595959 對白底約 7:1） | 過 | 過 | 過 |
| 照片裁切／主體 | 過（裸晶居中，打線完整） | 改：DDR4 照片整張換成自繪 HBM 剖面示意 | 過（冷板與銅管完整） |
| 留白 | 改：步驟卡原先下方空 1/3，改為卡高 188、內文與卡片間距縮小，照片加高到 460 | 同左 | 同左 |
| 孤字 | 改：卡片說明「櫃」「換熱」孤字，改寫為「組成機櫃出貨」「二次水路換熱」並加高卡片 | — | 改：圖說「伺服器。」孤行，縮短 |
| 小字「誰供應誰」 | 維持（01 確為供應鏈分工） | 改「流程示意（依公開資料繪製）」 | 改「流程示意（依公開資料繪製）」 |
| 字型 | 改 Noto Sans TC（可變字重 TTF 由 raw.githubusercontent.com/google/fonts 的 ofl/notosanstc 取得，OFL；12MB 不進 repo，路徑用環境變數 TC_FONT） | 同左 | 同左 |

**02 換圖**：repo 圖庫 `social/photo_lib/_category/記憶體` 十張全部是有廠牌的模組、舊式 DRAM 晶片、SSD、報廢模組堆（photo_3 被標條碼貼紙退件、photo_2 德州儀器 LOGO 退件、photo_5 即原圖），找不到「看不到廠牌標記又貼近 HBM」的；依指示改為自繪示意圖，來源與授權寫在 `02/image_sources.md`，原始向量檔 `hbm_diagram.svg`。
**待辦**：HBM 剖面結構（層序、TSV 位置、GPU 與 HBM 同在中介層上）請 CEO 派 mechanical-engineer 審；本環境無法派 Agent，自繪時對照通則：DRAM 晶粒在上、基底晶粒在下、TSV 貫穿、中介層連 GPU，目前自認結構無誤，但未經專業簽核。

**重疊檢查：程式 3 張 0 筆**（逐元素邊界兩兩相交＋文字溢出，容許 Noto Sans TC 行盒 0.3em 內的字面留白）；人工目視 1080×1350 全解析度逐張看過 0 筆。

## 重出圖方式
`TC_FONT=<NotoSansTC.ttf 路徑> TW_CHROME=<chromium 路徑> python render.py`


## art-director 複審 04（2026-11-04）

| 項目 | 結論 |
|---|---|
| 照片是否貼題 | 不過：資料中心機房全景與「光模組靠近晶片」關聯弱、畫質偏舊。已查圖庫 `網通`（9 張）、`資料中心`（16 張）、`AI伺服器`（11 張）：網通 photo_2 有 TP-Link 字樣、photo_1 為 DE-CIX 招牌、photo_3/4 為光纜加量尺、photo_5 有人手、photo_7 為光纖耦合器單品、photo_8 有 D-Link／Cisco／Panduit，其餘為機房／刀鋒伺服器，皆無貼題且無廠牌標記的 CC 照 → 不換照片 |
| 處置 | 照片區（1080×460）改為自繪「三種位置對照」示意圖 `npo_diagram.svg`：① 可插拔光模組在機櫃面板（紅線電訊號最長）② NPO 光學引擎在板上、靠近晶片封裝但在封裝外（紅線短）③ CPO 光學引擎在封裝內；右側黑線為機櫃面板、灰虛線為光纖；圖說標「示意圖」，不標距離數字 |
| NPO／CPO 位置敘述查證 | 本環境無法派 mechanical-engineer／ai-server-analyst，改 WebSearch 自查：可插拔＝前面板；NPO＝光引擎在主機板、靠近 ASIC 但封裝外；CPO＝封裝內或緊鄰。來源 https://www.wevolver.com/article/what-is-co-packaged-optics-architecture-benefits-challenges-and-performance（產業文章，非標準文件）。與貼文敘述「位置介於可插拔與 CPO 之間」一致。專業簽核待 CEO 補派 |
| 字級／層次 | 圖內最小 22px、列標 28px 粗體；紅色只用於電訊號線（一個重點：越靠近越短），其餘黑灰；步驟卡與其他篇一致 |
| 留白 | 示意圖三列等高等距、左欄標題與右側圖不頂邊；右側 CPO 列後段留白屬光纖延伸，不算空白 |
| 修正過程 | 首版 CPO 列「晶片」字被紅線壓住，封裝框由 200 加寬到 260 後解決；重疊檢查程式新增 SVG 內文字兩兩相交、出界、壓線檢查 |
| 文字檔 | threads.txt／ig.txt 出處行由 Faber CC 照改為「自行繪製示意圖」，Threads 留言附位置描述參考連結；`image_sources.md` 重寫 |

**重疊檢查：程式 1 張 0 筆**（含 SVG 內文字相交／出界／壓線）；人工目視 1080×1350 全解析度 0 筆。


## ai-server-analyst 技術簽核 04（2026-11-04）

結論：**通過（文案小修 2 處，圖不需改）**。

| 項目 | 結論 | 來源／信心 |
|---|---|---|
| 新聞稿事實與日期 | 通過。Tower 新聞稿 2026-11-03 存在（GlobeNewswire、ir.towersemi.com、towersemi.com 皆有）；內容：Innolight 首款 NPO 元件在 Tower PH18M 矽光子製程早期量產（200mm，加州廠）；多款 NPO 已在 300mm 平台 tape-out（＝設計定稿）。貼文寫法照抄原文，未寫成已放量。Tower 另在 Q3 財報稱有逾十家客戶在試做 NPO，有意義的出貨目標是 2027 下半年，取決於採用度，與貼文「早期量產」不衝突，建議不加進貼文以免被讀成已放量 | 高（多個獨立轉述一致；本環境只讀到搜尋摘要，未讀全文，連結發文前人工核對） |
| 圖：可插拔在面板、電訊號最長 | 通過 | 高（多來源一致：前面板可插拔，經長 PCB 走線到 ASIC） |
| 圖：NPO 在主機板上、靠近 ASIC 封裝、在封裝外 | 通過。多來源描述 NPO 光學引擎在自己的基板／板上、靠近交換 ASIC、不在其封裝內，常以插座與板連接 | 中高（來源多為廠商／產業文章，無標準文件；圖未標距離，風險低） |
| 圖：CPO 在封裝內 | 通過。CPO 光學引擎與 ASIC 共用封裝基板 | 高 |
| 用詞：NPO 全名 | 有分歧：多數稱 near-package（near-packaged）optics，亦有文章稱 near-board optics；本次新聞稿用 Near-Package Optics，貼文「近封裝光學」與之一致。OBO（板載光學）則指光引擎與晶片間仍經大塊 PCB 連接，與 NPO 不同；貼文與圖都沒有混用 | 中高 |
| 文案修正 1 | 「光模組廠需要有矽光子製程的晶圓廠代工」過度斷言（廠商可有自家產線）→ 改「常找」；Threads 並補「這次 Innolight 用的是 Tower 的矽光子平台」 | — |
| 文案修正 2 | Threads 刪「Tower 稿中提到其平台可把多種光學功能整合在同一顆晶片」：搜尋摘要無法核實這句 → 刪除；Threads 新聞稿句末補「量產規模與時程以公司後續公告為準」 | — |
| 圖 | 未改，故未重出 04.png，沿用既有 PNG（重疊檢查結果沿用前述 0 筆） | — |

來源：https://www.globenewswire.com/news-release/2026/11/03/3394669/0/en/tower-semiconductor-and-innolight-advance-high-performance-near-package-optics-for-ai-infrastructure.html ；https://convergedigest.com/innolight-tower-semiconductor-npo-silicon-photonics-production/ ；https://resources.l-p.com/knowledge-center/npo-vs-cpo-optics-placement-speed-efficiency-data-center ；https://www.tomshardware.com/tech-industry/near-packaged-optics-gains-ground-aso-the-industry-hedges-against-co-packaged-optics-growing-pains
未查到 OIF 的對應標準文件（搜尋未命中），故位置關係信心上限為中高。
