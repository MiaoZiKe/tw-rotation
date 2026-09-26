# ai_server：AI 伺服器機櫃（NVL72 式）3D 場景

- **id**：`ai_server`（`site/three3d.js` 的 `SCENES.ai_server`，路由 `#industry/ai_server/dg/ai_server`）
- **共同條件**：零件清單、配色、驗收條件沿用 `dg3d_standard.md`（圖九樣板）。這一份只記**逐件的結構細節與依據**。
- **型式**：真 3D（機櫃要繞著看才看得到後方的銅纜卡匣、側邊的液冷立柱、前方的光模組 —— 2D 一次只看得到一面）。

## §3D-細節（2026-09-26 第二批，B 組）

零件清單、編號、對應台股、卡片文字**都沒動**；只補「真實產品上看得到」的結構，以及修掉兩個結構錯誤。

| 零件 | 改了什麼 | 依據 |
|---|---|---|
| **運算托盤 · GPU 模組** | ① **位置修正**：以前 y 34、高 2.6，下半截埋進 y 35 那塊運算托盤板（34.4～35.6）裡，爆炸拆開也看不到；改成 y 36.7、高 2.2，底面剛好坐在板面上 ② 晶粒從 1 顆改成**兩顆光罩尺寸的運算晶粒**、中間一道縫（晶粒對晶粒介面），頂面各吃一張通用示意版圖 ③ 拿掉壓在晶粒上的那一小片銅（它把晶粒蓋住，而且不是真實的冷板形狀） | E1、E2 |
| **HBM4 記憶體** | 以前是晶片前方另外一排 4 顆「獨立的」HBM（跟 GPU 沒接在一起）。改成**站在同一片中介層上、晶粒左右各一排四疊，一顆 GPU 共八疊**；每疊＝底層邏輯晶粒＋四段 DRAM（層縫壓暗）。兩個零件同一個位置、同一個爆炸位移，拆開時一起走 | E1、E2 |
| **CPU（Grace / x86）** | 只修位置（y 34 → 36.6，同樣是被板子吃掉半截） | — |
| **主機板 高階 PCB** | 以前沿用共用 `pcb`：板上三條**插槽**＋前緣**金手指** —— 兩樣都不在這塊板上。改成 `agpcb`：CPU 左右各四顆**焊在板上的 LPDDR5X**、每顆 GPU 腳位前方一排六顆**供電電感**（多相）、**前緣**四個網卡籠架＋四個 E1.S 硬碟架（冷通道那一側）、**後緣**四個 NVLink 盲插連接器（推進去咬合銅纜卡匣）。蛇行差動對與電流粒子保留 | E3、E4 |
| **NVLink 銅背板** | 以前是「一塊 PCB ＋ 蛇行走線 ＋ 15 個連接器」—— **錯的**：實際是機櫃後方**四個直立的銅纜卡匣**、五千多條被動銅纜。改畫四個鈑金框、每框一束直立黑色纜線、每層托盤高度一個面朝托盤的插座（前緣金色接點）；電流粒子改成沿纜線上下跑 | E5 |
| **NVSwitch 托盤** | 一顆晶片 → **兩顆** NVLink Switch 晶片；鋁鰭片 → **銅冷板＋進出水管**（交換托盤也是液冷）；後緣一排插座、前面板管理埠 | E6、E7 |
| **電源櫃 PSU** | 以前是一顆大 PSU 外殼。改成 **1U 電源櫃：六顆熱插拔 PSU 並排（5＋1）＋ 左邊一格管理控制器**；每顆看得到風扇孔、把手、狀態燈；後面是**夾在直流匯流排上的兩片厚銅夾** | E8 |
| **液冷冷板 / CDU（立柱）** | 以前是一根青色柱子加兩顆泵。改成半透明外殼裡**供水（冷）／回水（熱）兩根直立主管**，朝機櫃那一側**每層一對分支＋快接頭**（每台托盤各自拿水、各自回水＝並聯），底部兩顆備援泵＋一支濾芯 | E9 |
| **光模組 / CPO** | OSFP 上蓋補一排**縱向鰭片**（OSFP 的上蓋本身就是散熱器，這是它跟 QSFP-DD 最好認的差別） | E10 |

### 效能（改前 → 改後）

| 指標 | 改前 | 改後 | 上限 |
|---|---|---|---|
| draw call | 270 | 見最終報告 | ≤ 300 |
| 三角形 | 46,490 | 見最終報告 | ≤ 67,000（L3 棘輪） |

做法：板上小件全部改成一個 InstancedMesh（平的 BoxGeometry，12 個三角形），HBM 八疊併成 2 個 mesh，
光模組把 LC 埠與拉環併成一個 mesh —— 省下來的 draw call 拿去畫電源櫃六顆 PSU 與液冷立柱的分支。

### 證據

> 證據等級：全部是 **WebSearch 摘要**（這個容器 WebFetch 被擋），沒有人讀過原文。A 組先查過一輪、交接給 B 組，B 組用不同關鍵字各再撈一次，兩次摘要講的是同一件事才採用。

| 代號 | 事實 | 信心 | 來源 |
|---|---|---|---|
| E1 | B200：兩顆光罩尺寸晶粒、晶粒間 10 TB/s 互連；8 疊 HBM3e、共 192 GB | 高（三個獨立來源一致） | <https://wccftech.com/nvidia-blackwell-gpu-architecture-official-208-billion-transistors-5x-ai-performance-192-gb-hbm3e-memory/>、<https://www.naddod.com/blog/nvidia-unveils-most-powerful-gpu-blackwell-b200-unleashes-ai-performance-speed>、<https://videocardz.com/newz/nvidia-blackwell-b100-to-feature-2-dies-and-192gb-of-hbm3e-memory-b200-with-288gb> |
| E2 | Rubin（卡片寫的 HBM4 世代）同樣是兩顆近光罩尺寸運算晶粒＋8 疊 HBM4（288 GB），放在 CoWoS-L 中介層上 —— 所以「兩顆晶粒＋八疊」對 B200 與 Rubin 都成立 | 中（摘要一致，未讀原文） | <https://blog.barrack.ai/nvidia-rubin-specs-architecture-2026/>、<https://www.techpowerup.com/350947/nvidia-details-the-rubin-architecture-die-annotation-vera-cpu-hbm4-and-disaggregated-inference> |
| E3 | 1U 運算托盤：2 顆 Grace ＋ 4 顆 Blackwell（兩片 Bianca 板，每片 1 CPU ＋ 2 GPU）；CPU／GPU 上是冷板；網卡與儲存（E1.S、M.2）在**前面**（冷通道），NVLink 經**後緣**連接器接到交換托盤 | 高（NVIDIA 使用手冊＋ SemiAnalysis＋ SuperPOD 參考架構） | <https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html>、<https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component>、<https://docs.nvidia.com/dgx-superpod/reference-architecture-scalable-infrastructure-gb200/latest/dgx-superpod-components.html> |
| E4 | Grace 的 LPDDR5X 是板載（沒有 DIMM 插槽） | 中（A 組交接，B 組未另外撈到獨立來源 —— 畫面只畫「焊在板上的小封裝」，不寫容量數字） | A 組交接（SemiAnalysis GB200 BOM） |
| E5 | 四個 NVLink 纜線卡匣直立裝在機櫃後方、五千多條銅纜；卡匣形成 NVLink 的實體資料面 | 高（NVIDIA 手冊＋ ServeTheHome＋ Leviathan） | <https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html>、<https://www.servethehome.com/this-is-the-nvidia-dgx-gb200-nvl72/>、<https://www.leviathansystems.co/articles/gb200-nvl72-deployment-deep-dive> |
| E6 | 每台 NVLink Switch 托盤 2 顆交換晶片、144 個 NVLink 埠；整櫃 9 台 | 高 | <https://jonathan-hui.medium.com/nvidia-blackwell-gb200-nvl72-networking-e36aade6ced9>、<https://www.naddod.com/blog/nvidia-gb200-interconnect-architecture-analysis-nvlink-infiniband-and-future-trends>、<https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component> |
| E7 | 交換托盤液冷（冷板）| **低～中**：摘要只講「運算托盤用冷板」，交換托盤液冷來自 A 組交接與整櫃液冷的描述，沒有撈到一句明講「交換托盤晶片上是冷板」的摘要。畫面照畫，列在「可能被否決」 | 同 E3 |
| E8 | 1U 33 kW 電源櫃：六顆 5.5 kW 熱插拔 PSU（5＋1）＋ 電源管理控制器；輸出約 50 V 直流接 1400 A 機櫃匯流排 | 高（兩家原廠產品頁一致） | <https://www.se.com/us/en/product/SENVPS33KB2/apc-netshelter-power-shelf-33kw-50v-dc-rackmount-1u-gb200/>、<https://www.vertiv.com/en-us/products-catalog/critical-power/dc-power-systems/Vertiv-PowerDirect-3000-33kW-50-VDC-Power-Systems/> |
| E9 | 機櫃後方有液冷分歧管（進出口、主管）；托盤經快接頭並聯到分歧管 | 高 | <https://docs.nvidia.com/dgx/dgxgb200-user-guide/hardware.html>、<https://www.leviathansystems.co/articles/gb200-nvl72-deployment-deep-dive> |
| E10 | OSFP 的整合式鰭片上蓋 | 中（業界常識，本輪沒有另外撈來源） | — |

### 仍是示意（畫面副標已有「示意」或卡片已講）

- 分歧管在實機上是**機櫃後方**的直立主管；這裡沿用原本的位置（機櫃右側外面），是為了不擋住後方的銅纜卡匣。
- 纜線密度（每卡匣 22 條）、HBM 層數（四段）、板上 LPDDR 顆數都是示意。
- 冷板**沒有**畫在 GPU 上：畫上去就把晶粒與 HBM 整個蓋住，而這張圖要回答的是「欣興／台積電做的是哪一塊」。冷板的內部結構在「液冷」那一張看。
