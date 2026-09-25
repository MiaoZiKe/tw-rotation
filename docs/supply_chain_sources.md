# 供應鏈關係的原文來源（supply_chain.yaml edges[].source_url）

2026-09-25 建立。Andy：「有媒體報導，需要貼文章，因為給讀者看」。產業鏈頁資訊欄的「媒體報導／官方揭露」標籤，
有 `source_url` 的會變成連到原文的連結（開新分頁）。

## 查證方法與限制

- 工具只有 WebSearch（WebFetch／curl 被出口代理擋）。**沒有讀過任何一篇原文**，只讀到搜尋結果的標題與摘要。
- 收錄條件：標題或摘要**明確講到這兩家公司的這段關係**。只講其中一家、或只是並列在概念股清單裡的，不收。
- 摘要會補出原文沒有的對應（CLAUDE.md 記過兩次），所以優先挑「標題本身就寫出兩家」的那篇；
  只有摘要提到、標題沒寫的，信心度降為「中」。
- 找不到可靠來源的：標籤照樣顯示但不是連結，YAML 那一行尾端註記 `# 待補來源`。不編網址。
- 信心度：高＝標題就寫明雙方關係，或公司官網／新聞稿；中＝只有摘要提到，或來源是投顧／轉貼平台，或跟 YAML 既有 note 的細節對不上。

## 已補上連結（45 條；另有 4 條媒體報導邊原本就有 source_url）

| # | 關係 | 來源 | 信心度 | 摘要重點 |
|---|---|---|---|---|
| 6 | 金居 → 台光電（HVLP 銅箔） | [經濟日報](https://money.udn.com/money/story/5607/8729665) | 中 | 標題：CCL 族群帶動台光電、聯茂、台燿走強，銅箔供應商金居能否接棒；摘要：金居為上游銅箔，客戶涵蓋台光電、聯茂、台燿 |
| 7 | 金居 → 聯茂（HVLP 銅箔） | [經濟日報](https://money.udn.com/money/story/5607/8729665) | 中 | 同上，聯茂為金居客戶 |
| 8 | 金居 → 台燿（HVLP 銅箔） | [經濟日報](https://money.udn.com/money/story/5607/8729665) | 中 | 同上，台燿為金居客戶 |
| 11 | 日東紡 Nittobo → 南亞（第二代低介電玻璃原紗 NER） | [南亞公司官網新聞稿](https://www.npc.com.tw/j2npc/zhtw/newsdetail/5JEFBU9NW1C) | 高 | 日東紡長期穩定供應第二代低介電玻璃原紗 NER 給南亞；2027 年日東紡特殊玻纖布約 20% 由南亞協助織造 |
| 12 | 日東紡 Nittobo → 建榮（高階玻璃原紗（日東紡持股 47.65%、過半董事席次）） | [口袋學堂](https://www.pocket.tw/school/report/SCHOOL/7035/) | 中 | 建榮為日東紡持股約 47% 的台灣子公司，集團供紗、建榮織布 |
| 13 | 富喬 → CSP（Microsoft / Google / Amazon / Meta）（LDK2 低介電玻纖布通過 CSP 認證，指定用於下一代 ASIC 平台） | [工商時報](https://www.ctee.com.tw/news/20260914700227-430203) | 高 | 富喬 LDK2 低介電玻纖布獲 CSP 大廠認證，用於下一代 ASIC；未指名哪家 CSP |
| 14 | 光洋科 → 台積電（高階濺鍍靶材（釕靶，2/3/5nm 先進製程）） | [經濟日報](https://money.udn.com/money/story/11074/9488929) | 中 | 光洋科獲台積大單；摘要：子公司獲台積電 2nm 靶材訂單、為台積電最大國內靶材供應商 |
| 27 | 家登 → 台積電（EUV 光罩傳送盒 EUV Pod / 晶圓載具 FOUP） | [工商時報](https://www.ctee.com.tw/news/20220224701097-439901) | 高 | 家登 EUV 光罩盒通吃台積電、英特爾，訂單看到隔年 |
| 28 | 家登 → Intel（EUV 光罩傳送盒 EUV Pod） | [工商時報](https://www.ctee.com.tw/news/20220224701097-439901) | 高 | 同上，英特爾為家登 EUV Pod 客戶 |
| 29 | 帆宣 → 應用材料 Applied Materials（客製化設備 / 模組 OEM 代工（2022 年應用材料最佳供應商獎）） | [工商時報](https://www.ctee.com.tw/news/20220413700695-430502) | 高 | 京鼎、帆宣、上銀獲應用材料 2022 年最佳供應商獎 |
| 30 | 京鼎 → 應用材料 Applied Materials（半導體設備模組 / 備品製造） | [工商時報](https://www.ctee.com.tw/news/20220413700695-430502) | 高 | 同上；另一篇摘要稱京鼎承接薄膜及蝕刻設備模組與備品生產 |
| 31 | 力積電 → Intel（12 吋矽電容 IPD / 矽中介層（Intel EMIB 先進封裝平台，已通過認證）） | [科技新報](https://technews.tw/2026/05/08/psmc-into-intel-emib/) | 高 | 力積電躋身英特爾 EMIB 先進封裝夥伴；12 吋矽電容通過 Intel EMIB 認證 |
| 33 | 祥碩 → AMD（桌上型平台晶片組 ASIC（AM5 / 800 系列）） | [聯合新聞網（經濟日報）](https://udn.com/news/story/7253/7917138) | 高 | 祥碩吃下超微高中低階 800 系列晶片組訂單，並供 USB4 主控 IC |
| 36 | 辛耘 → 台積電（濕製程 / 貼合解貼合設備） | [數位時代](https://www.bnext.com.tw/article/81545/tsmc-supply-chain-company) | 高 | 台積電 27 家優良供應商、7 家台廠，辛耘首次上榜（先進封裝量產支援） |
| 37 | 弘塑 → 台積電（濕製程設備） | [商周財富網](https://wealth.businessweekly.com.tw/GArticle.aspx?id=ARTL003017917) | 中 | 弘塑、辛耘等台積電先進封裝擴產受惠設備廠；另摘要稱弘塑已成台積電主要（濕製程）設備供應商 |
| 40 | 竑騰 → 日月光投控（均熱片植片 / 壓合 / 點膠 / AOI 設備） | [CMoney 股市爆料同學會（轉貼公開資訊觀測站公告）](https://www.cmoney.tw/forum/article/179927330) | 中 | 矽品於 115/6/12 前自竑騰取得營業用機器設備 83 批，總額約 14.27 億元；原始出處為觀測站重大訊息，此頁為轉貼 |
| 43 | 萬潤 → 日月光投控（點膠 / 封裝設備） | [鉅亨網](https://news.cnyes.com/news/id/6006991) | 高 | 萬潤獲日月光大單挹注；多筆觀測站公告顯示日月光／矽品向萬潤取得設備（10.09～12.4 億元不等）。★ note 寫的 10.86 億元這次沒查到同一數字 |
| 44 | 京元電 → NVIDIA（AI 晶片測試） | [今周刊](https://www.businesstoday.com.tw/article/category/183015/post/202601070039/) | 高 | IC 測試王京元電獨攬輝達最終測試與 SLT 大單 |
| 49 | 力成 → Broadcom（FOPLP 面板級先進封裝（CPO）） | [科技新報](https://finance.technews.tw/2026/07/17/powertech-and-broadcom-establish-joint-venture-in-singapore/) | 高 | 力成攜博通設新加坡合資公司、投資 4 億美元，2028 年量產 |
| 50 | 台積電 → 精材（晶圓針測 CP 外溢訂單 + 12 吋晶圓背面處理） | [理財周刊](https://www.moneyweekly.com.tw/ArticleData/Info/Article/222984) | 中 | 台積電訂單保障，精材測試產能大擴張；摘要：承接台積電外溢晶圓測試 |
| 51 | 台積電 → 欣銓（晶圓針測 CP 外溢訂單（AI ASIC）） | [FTNN 新聞網](https://www.ftnn.com.tw/news/543340) | 中 | 欣銓承接台積電 CP 測試外溢訂單（龍潭廠，鎖定 AI ASIC） |
| 59 | 南亞科 → SanDisk（DRAM（多年期策略供應協議）） | [今周刊](https://www.businesstoday.com.tw/article/category/183008/post/202603250081/) | 高 | 南亞科私募引進 SanDisk、鎧俠、Solidigm、思科；SanDisk 公告已簽多年期 DRAM 策略供應協議 |
| 60 | 南亞科 → Kioxia（DRAM（長期供應協議）） | [經濟日報](https://money.udn.com/money/story/5612/9402940) | 高 | 鎧俠等四大廠參與南亞科私募；摘要：鎧俠已與南亞科簽長期 DRAM 供應協議 |
| 61 | 南亞科 → Solidigm（SK hynix 子公司）（DRAM） | [經濟日報](https://money.udn.com/money/story/5612/9402911) | 中 | 南亞科私募引進 Solidigm 等四方；摘要稱認購者簽有多年期供應協議（Solidigm 個別條款未揭露） |
| 62 | 旺宏 → NVIDIA（NOR Flash（GB300 GPU 插槽旁 512Mb 韌體／開機）） | [經濟日報](https://money.udn.com/money/story/11162/8634454) | 高 | 旺宏以 NOR Flash 打入輝達 GB300 鏈（報導用獨家，公司未證實） |
| 63 | 華邦電 → NVIDIA（NOR Flash（Vera Rubin 平台，2026H2 起）） | [DIGITIMES（獨家）](https://www.digitimes.com.tw/tech/dt/n/shwnws.asp?CnlID=1&Cat=40&id=0000759074_3Y9LNQ1186LDM13LXJR5A) | 中 | 華邦電 NOR Flash 首度打入 NVIDIA 供應鏈（Vera Rubin，2026H2）；仍是單一原始來源 |
| 64 | 穎崴 → NVIDIA（測試座 / 探針卡 / 熱控系統） | [數位時代](https://www.bnext.com.tw/article/60666/winway-nvidia-ic-test-socket) | 中 | 穎崴搭上 NVIDIA 直通車；★ note 的「5 年長約」這次沒查到 |
| 72 | 臻鼎-KY → NVIDIA（高階 HDI / 高層數伺服器板 / IC 載板（NVIDIA MGX 生態系）） | [經濟日報](https://money.udn.com/money/story/5612/9539045) | 高 | 臻鼎宣布加入 NVIDIA MGX 平台（2026-06-01） |
| 73 | 健鼎 → CSP（Microsoft / Google / Amazon / Meta）（伺服器 / 網通 PCB、記憶體模組板） | [CMoney 研究筆記](https://www.cmoney.tw/notes/note-detail.aspx?nid=1013058) | 中 | 健鼎伺服器／網通板出貨美系四大 CSP（Meta、Google、AWS、Microsoft） |
| 74 | 台郡 → NVIDIA（AI 機櫃漏液感測軟板（輝達 COMPUTEX MGX 供應鏈展示區公開點名）） | [經濟日報](https://money.udn.com/money/story/5612/8751119) | 高 | 輝達 MGX 伺服器供應鏈名單公開，台郡漏液感測吸睛 |
| 75 | 金像電 → CSP（Microsoft / Google / Amazon / Meta）（CSP 自研 ASIC 平台直接指定 PCB 料號（AVL）） | [理財周刊](https://www.moneyweekly.com.tw/ArticleData/Info/Article/250682) | 中 | 金像電 AWS、Google、Meta 三路 ASIC 成長；摘要稱為四大 CSP 自研 ASIC 平台主要 PCB 供應商 |
| 79 | 南電 → Broadcom（網通 / ASIC ABF 載板） | [Yahoo 股市](https://tw.stock.yahoo.com/news/q4%E8%BC%89%E6%9D%BF%E6%9A%AB%E7%84%A1%E6%BC%B2%E5%83%B9%E8%A8%88%E7%95%AB-%E5%A4%A7%E5%AE%A2%E6%88%B6%E5%8D%9A%E9%80%9A%E5%B0%87%E8%87%AA%E5%BB%BA%E7%94%A2%E8%83%BD-%E5%8D%97%E9%9B%BB%E7%88%86%E9%87%8F%E8%B7%8C%E5%81%9C-063117937.html) | 中 | 標題：大客戶博通將自建產能，南電爆量跌停；★ note 的「網通占 65～70%」這次沒查到 |
| 81 | 景碩 → NVIDIA（CPU / GPU ABF 載板） | [FTNN 新聞網](https://www.ftnn.com.tw/news/555113) | 中 | ABF 載板廠手握 Vera Rubin 大單、拚 45% 市占；摘要指名景碩 |
| 84 | 一詮 → NVIDIA（Grace CPU 均熱片 lid） | [鉅亨網](https://news.cnyes.com/news/id/6322956) | 中 | 一詮均熱片產量拚倍增；摘要：供應輝達 Grace CPU 均熱片已於 2025Q4 量產 |
| 93 | 高力 → Bloom Energy（SOFC 燃料電池 Hot Box 熱反應盒（每台 SOFC 用 6 顆）） | [科技新報](https://technews.tw/2026/05/11/sofc-bloom-enegy-hot-box/) | 高 | 高力 SOFC 業務爆發，助攻 Bloom Energy；摘要：Bloom 為高力最大單一客戶 |
| 94 | Bloom Energy → CSP（Microsoft / Google / Amazon / Meta）（SOFC 燃料電池系統（供 Oracle AI 資料中心，擴大合作達 2.8GW）） | [經濟日報](https://money.udn.com/money/story/5612/9442059) | 高 | 甲骨文與 Bloom Energy 擴大合作（2.8GW） |
| 98 | 台達電 → NVIDIA（800V HVDC 電源櫃 / DC-DC 模組） | [鏈新聞 ABMedia](https://abmedia.io/nvidia-800v-hvdc-delta-2027-q1-production) | 中 | 台達電 2027Q1 投產輝達 800V HVDC、Q2 放量。★ 與 item 寫的「最快 2026H2 出貨」時程不一致，見 docs |
| 101 | 貿聯-KY → NVIDIA（GB200 Busbar 匯流排 + power whip 電源線組） | [鉅亨網](https://news.cnyes.com/news/id/5593524) | 高 | 貿聯-KY 通過輝達認證，成 GB200 首批受惠者（匯流排／Busbar） |
| 106 | 波若威 → NVIDIA（CPO 用 800G/1.6T 光纖套件（Fiber Harness / Shuffle Box）） | [科技新報](https://technews.tw/2026/08/24/browave-shuffle-box-set-to-ramp-up-in-q4) | 高 | 受惠輝達 CPO 需求，波若威 Shuffle Box Q4 拼放量 |
| 107 | 上詮 → 台積電（CPO / 矽光子 COUPE 封裝用光纖陣列 FAU（光纖與矽光子晶片對準接合）） | [經濟日報](https://money.udn.com/money/story/5612/9461053) | 高 | 台積電 CPO 報捷，帶動夥伴上詮（FAU）業務 |
| 108 | 眾達-KY → Broadcom（CPO 光引擎 / ELSFP 外置雷射光源模組（Tomahawk-5 Bailly 51.2T 平台）） | [科技新報](https://finance.technews.tw/2025/12/09/pcl-technology/) | 高 | 眾達-KY 搶攻博通 CPO 供應鏈（TH5 Bailly、ELSFP），明年可望大量導入 |
| 109 | Broadcom → 智邦（Tomahawk 交換器晶片） | [智邦官網](https://www.accton.com.tw/engineering-the-102-4t-switch/) | 中 | 智邦 102.4T 交換器；摘要稱其採用 Broadcom Tomahawk 6（OFC 2026 展出） |
| 110 | 瑞昱 → NVIDIA（PCIe SSD 控制 IC） | [鉅亨網](https://news.cnyes.com/news/id/6307515) | 高 | 瑞昱 SSD 控制晶片打入輝達鏈（Quantum-X 平台） |
| 118 | NVIDIA → 技嘉（HGX / GB200 NVL4 GPU 平台） | [技嘉官網新聞稿](https://www.gigabyte.com/tw/press/news/2360) | 高 | 技鋼發表基於 NVIDIA GB200 NVL4 平台伺服器 |
| 122 | 緯穎 → CSP（Microsoft / Google / Amazon / Meta）（雲端伺服器（以 ASIC 專案為主，Meta 佔比逾五成）） | [聯合新聞網](https://udn.com/news/story/7240/8514999) | 中 | Meta 砸錢建 AI 資料中心；摘要：緯穎來自 Meta 營收占比逾五成 |

## 查過但沒收的（摘要對不上，保持待補）

- 金居 → NVIDIA（RTF）：摘要只談 HVLP4 與 Rubin 需求，沒講到「2025 初打入 AI 伺服器」那件事。
- 奇鋐 → 鴻海／廣達：摘要只談奇鋐通過 GB300 認證，沒有具名鴻海、廣達是買方。
- 聯亞 → 中際旭創：摘要明說沒找到中際旭創是最大客戶，只找到與**美國客戶**簽 4 年 CW Laser 長約。這條邊值得人工覆核。
- 矽格 → 聯發科、群聯 → NVIDIA、Kioxia → 群聯、健策 → AMD、建準 → NVIDIA、台燿 → CSP：摘要講得到，但分不出是哪一篇講的，無法指定網址。

## 待補來源（82 條）

YAML 同一行尾端有 `# 待補來源` 註記。

- #0 味之素 Ajinomoto → 欣興（ABF 增層膜；reported）
- #1 味之素 Ajinomoto → 南電（ABF 增層膜；reported）
- #2 味之素 Ajinomoto → 景碩（ABF 增層膜；reported）
- #3 三菱瓦斯化學 MGC → 欣興（BT 樹脂 core CCL；reported）
- #4 三菱瓦斯化學 MGC → 南電（BT 樹脂 core CCL；reported）
- #5 三菱瓦斯化學 MGC → 景碩（BT 樹脂 core CCL；reported）
- #9 金居 → NVIDIA（高頻高速反轉銅箔 RTF（2025 初打入 AI 伺服器供應鏈）；reported）
- #10 日東紡 Nittobo → 台光電（高階玻纖布 / T-glass；reported）
- #15 台積電 → 創意（晶圓 + 先進封裝產能；verified）
- #16 台積電 → 世芯-KY（先進製程晶圓 + CoWoS；verified）
- #17 聯電 → 智原（成熟製程 ～14nm 晶圓；reported）
- #18 聯電 → 聯詠（28/22nm 高壓製程晶圓；reported）
- #19 台積電 → NVIDIA（GPU 晶圓 + CoWoS；verified）
- #20 台積電 → AMD（晶圓 + 封裝；reported）
- #21 台積電 → Broadcom（ASIC 晶圓；reported）
- #22 台積電 → Marvell（ASIC 晶圓（3nm，roadmap 到 A14）+ CoWoS；reported）
- #23 台積電 → 聯發科（晶圓；reported）
- #24 M31 → 台積電（製程平台矽智財授權（高速介面 / 基礎 IP）；verified）
- #25 力旺 → 台積電（eNVM / OTP 矽智財授權（權利金按晶圓片數提撥）；verified）
- #26 應用材料 Applied Materials → 台積電（前段製程設備（沉積 / 蝕刻 / 佈植 / CMP）；verified）
- #32 力積電 → 晶豪科（利基型 DRAM / Flash 成熟製程晶圓（簽有每月最低投片量的產能保證長約）；reported）
- #35 台積電 → 日月光投控（封裝外溢；reported）
- #38 弘塑 → 日月光投控（濕製程設備 + 製程化學品；reported）
- #39 萬潤 → 台積電（點膠 / 固晶設備；reported）
- #41 竑騰 → 台積電（先進封裝點膠 / 檢測設備；reported）
- #42 竑騰 → 力成（封裝設備；reported）
- #45 矽格 → 聯發科（測試代工；reported）
- #46 力成 → Micron（記憶體封測；reported）
- #47 力成 → Kioxia（記憶體封測；reported）
- #48 力成 → SK hynix（記憶體封測；reported）
- #52 南茂 → Micron（記憶體封測（NAND / 利基型 DRAM）；reported）
- #53 南茂 → 聯詠（驅動 IC 封測（TCP/COF、COG、金凸塊）；reported）
- #54 力成 → AMD（FOPLP 面板級先進封裝；reported）
- #55 台積電 → 群聯（SSD 控制 IC 晶圓（6nm/7nm；Gen7 走 4nm）；reported）
- #56 Kioxia → 群聯（NAND 晶圓（已簽長約 LTA）；reported）
- #57 群聯 → NVIDIA（企業級 SSD / Boot Drive；reported）
- #58 群聯 → CSP（Microsoft / Google / Amazon / Meta）（PCIe Gen5 企業級 SSD（Pascari X201/D201）；reported）
- #65 穎崴 → AMD（測試座 / 探針卡；reported）
- #66 SK hynix → NVIDIA（HBM；reported）
- #67 Micron → NVIDIA（HBM；reported）
- #68 台光電 → 金像電（極低損耗高階 CCL；reported）
- #69 聯茂 → 金像電（高階 CCL；reported）
- #76 台光電 → NVIDIA（GB200/GB300 UBB 板材 AVL；reported）
- #77 台燿 → CSP（Microsoft / Google / Amazon / Meta）（AWS Trainium ASIC 伺服器主板 M8 CCL（AVL 第二供應商）；reported）
- #78 欣興 → NVIDIA（ABF 載板；reported）
- #80 南電 → AMD（CPU / GPU ABF 載板；reported）
- #82 景碩 → AMD（FPGA ABF 載板（原 Xilinx）；reported）
- #83 景碩 → 聯發科（BT 載板；reported）
- #85 一詮 → CSP（Microsoft / Google / Amazon / Meta）（Google TPU / AWS Trainium 均熱片；reported）
- #86 一詮 → Broadcom（AI ASIC 均熱片；reported）
- #87 健策 → NVIDIA（GPU 均熱片 lid/IHS + 補強框；reported）
- #88 健策 → AMD（MI450/MI455 均熱片；reported）
- #89 奇鋐 → 鴻海（水冷板；reported）
- #90 奇鋐 → 廣達（水冷板；reported）
- #91 雙鴻 → 鴻海（水冷板；reported）
- #92 建準 → NVIDIA（GB200 / GB300 RVL 系列伺服器風扇（已列入輝達認證供應鏈）；reported）
- #95 台達電 → 鴻海（電源 / CDU；reported）
- #96 台達電 → 廣達（電源；reported）
- #97 台達電 → 緯穎（電源 / Power Shelf；reported）
- #99 光寶科 → 鴻海（PSU；reported）
- #100 光寶科 → CSP（Microsoft / Google / Amazon / Meta）（AI 電源櫃 / 110kW Power Shelf；reported）
- #102 聯亞 → 中際旭創 Innolight（CW Laser 磊晶片 / InP 磊晶；reported）
- #103 聯亞 → Coherent（InP / GaAs 磊晶；reported）
- #105 華星光 → 智邦（光收發模組；reported）
- #111 Marvell → CSP（Microsoft / Google / Amazon / Meta）（客製化 AI ASIC（Trainium / Maia / Google）；reported）
- #112 創意 → CSP（Microsoft / Google / Amazon / Meta）（ASIC 設計服務；reported）
- #113 世芯-KY → CSP（Microsoft / Google / Amazon / Meta）（ASIC 設計服務；reported）
- #114 NVIDIA → 鴻海（GB300 模組；reported）
- #115 NVIDIA → 廣達（GPU 模組；reported）
- #116 NVIDIA → 緯創（GPU 模組；reported）
- #117 NVIDIA → 英業達（GB200 GPU 模組；reported）
- #119 鴻海 → CSP（Microsoft / Google / Amazon / Meta）（整櫃系統；reported）
- #120 廣達 → CSP（Microsoft / Google / Amazon / Meta）（AI 伺服器；reported）
- #121 緯創 → CSP（Microsoft / Google / Amazon / Meta）（AI 伺服器 / GB200-GB300 機架系統；reported）
- #123 英業達 → CSP（Microsoft / Google / Amazon / Meta）（AI 伺服器主機板 L6 / 整櫃 L10-L11（北美四大 CSP GB200 專案）；reported）
- #124 技嘉 → CSP（Microsoft / Google / Amazon / Meta）（AI 伺服器 / GIGAPOD 機櫃級方案；reported）
- #125 智邦 → CSP（Microsoft / Google / Amazon / Meta）（白牌交換器；reported）
- #138 和碩 → Apple（iPhone / iPad 組裝代工；reported）
- #139 鴻海 → Apple（iPhone 組裝代工；reported）
- #140 公有雲原廠（AWS／Azure／GCP） → 伊雲谷（公有雲資源與授權（通過 AWS MSP Partner 三年期評鑑、AWS 核心級服務合作夥伴）；reported）
- #141 公有雲原廠（AWS／Azure／GCP） → 宏碁資訊（公有雲資源與授權（2022 年取得 Microsoft Azure Expert MSP 認證；2026 年初整合宏碁智雲後補上 AWS 與 GCP）；reported）
- #142 公有雲原廠（AWS／Azure／GCP） → 精誠（公有雲資源與軟體授權（加值型代理經銷 VAD；摘要稱其為微軟 Azure 在台主要服務商）；reported）

## 查證時發現跟 YAML 既有內容對不上的地方（這次沒改 YAML 的文字，留給下一輪覆核）

- #43 萬潤 → 日月光：note 寫「含稅約 10.86 億元」，這次查到的公告是 10.09／10.3／10.7／12.4 億元，沒有 10.86。
- #64 穎崴 → NVIDIA：note 寫「簽有至少 5 年長約」，這次沒查到。
- #79 南電 → Broadcom：note 寫「網通載板占營收 65～70%」，這次沒查到。
- #98 台達電 → NVIDIA：item 寫「最快 2026H2 出貨」，ABMedia 標題是「2027Q1 投產、Q2 放量」。

## 第二輪覆核（2026-09-25，換關鍵字再查；以公司自己講的為準）

| 關係 | 第二輪查到什麼 | 處理 |
|---|---|---|
| 聯亞 → 中際旭創 | 只有 CMoney 論壇摘要一句「聯亞供中際旭創」；聯亞公告的 4 年長約對象是「美國客戶」，未指名 | **降為產業推論**、strength 4→2，note 寫推論依據與缺的是，附 [MoneyDJ](https://www.moneydj.com/kmdj/news/newsviewer.aspx?a=600a927c-818e-45d6-9bda-8021508a6f48)（CW Laser 供給） |
| 萬潤 → 日月光 10.86 億 | 第二輪摘要有出現「含稅約 10.86 億元」，但分不出是哪一則公告；觀測站公告另有 10.24／10.3／10.7／12.4／18／18.93 億元 | note 改成「單筆約 10～19 億元」區間，連結換成 [矽品 18.93 億元公告](https://news.cnyes.com/news/id/6524336)；「約當 2025 營收 20.2%」查不到，刪除 |
| 穎崴 5 年長約 | [法說備忘錄](https://blog.fugle.tw/post/earnings-call-6515-2026-05-26) 只講北美 AI 客戶逾 80%、未具名；Phase 2／5 年長約兩輪都查不到 | note 刪掉 Phase 與長約，改寫「媒體報導未證實」；維持媒體報導 |
| 南電 網通 65～70% | [南電法說備忘錄 2026-03-17](https://blog.fugle.tw/post/earnings-call-8046-2026-03-17)：網路通訊應用首季營收占比約 49% | note 改為 49%（法說），博通對應標明是媒體說法 |
| 台達電 → NVIDIA 時點 | [台達電法說 2026-04-30](https://technews.tw/2026/04/30/hvdc-400-800-hvdc/)：董事長確認 800V 2026H2 小量出貨、2027 主要貢獻 | 原 item「2026H2」與法說一致；連結換成法說報導，ABMedia「2027Q1 投產」記為不同口徑 |

⚠ 萬潤、穎崴、南電的法說內容是「富果法說備忘錄」與媒體轉述的摘要，不是法說簡報原文。
