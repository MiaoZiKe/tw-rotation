# 產品架構圖盤點（2026-10-19）

給「比比知識」選題與撰寫用。來源：`site/three3d.js`（3D 場景 `SCENES`，21 個；2026-10-19 補 SSD）、`site/themes3d.js`（題材 2.5D 等角剖析圖 `T.*`，22 張）、`site/diagrams.js`（產業鏈 2D 剖析圖，目前有 `SLOTS` 的 ai_server、mlcc 與 `DG.register` 的 pcb_rigid）、`site/artillus.js`（文章插圖積木，kind 只有 cowos／rack／custom）。
看圖路徑：3D 與 2D 在 `#industry/<鏈>` 或 `#industry/group/<族群 id>` 的剖析圖區（有 3D 場景的有 3D 切換鈕）；題材 2.5D 在 `#heatmap/theme/<題材 id>`（舊 `#themes/<id>` 會導過去）。
取用方式：文章放對應頁連結＋該頁截圖，或用 `illus`（style:2）重畫；3D 優先。

## 一、3D 場景（three3d.js）—— 21 張，知識題優先從這裡挑

| 圖 id | 名稱 | 類型 | 看得到的路由 | 適合的比比知識 |
|---|---|---|---|---|
| foundry | 晶圓代工：一顆電晶體與一個製程迴圈 | 3D | #industry/group/foundry | IC 代工是什麼 |
| silicon_wafer | 矽晶圓：從熔湯到一片鏡面 | 3D | #industry/group/silicon_wafer | 矽晶圓是什麼 |
| wide_bandgap | 第三代半導體：SiC 與 GaN 功率元件 | 3D | #industry/group/wide_bandgap | SiC／GaN 差在哪 |
| semiconductor | CoWoS-L 先進封裝（立體剖面） | 3D | #industry/group/ai_adv_packaging | CoWoS（已有 k_cowos，可寫進階版） |
| hbm | HBM：堆疊記憶體與底下邏輯晶粒 | 3D | #industry/group/hbm | HBM（已有 k_hbm，已上架） |
| ssd | SSD：一片 M.2 2280 NVMe 固態硬碟（金手指、主控、DRAM、NAND 切開見疊層晶粒） | 3D（另有 2D 俯視＋側視） | #industry/semiconductor/dg/memory_module（族群 memory_module） | SSD 是什麼？ |
| ic_substrate | IC 載板：ABF 增層剖面 | 3D | #industry/group/ic_substrate | ABF 載板是什麼 |
| pcb_rigid | PCB 硬板：多層板剖面與四種孔 | 3D（另有 2D） | #industry/group/pcb_rigid | PCB 是什麼、為何高階板吃緊 |
| ai_server | AI 伺服器機櫃（NVL72 式） | 3D（另有 2D） | #industry/ai_server | AI 機櫃裡有什麼 |
| server_psu | 電源：PSU 拆開到晶片核心電壓 | 3D | #industry/group/server_psu | 伺服器電源／PSU 與 BBU |
| liquid_cooling | 液冷：從晶片到 CDU | 3D | #industry/group/liquid_cooling | 液冷（已有 k_cooling） |
| air_cooling | 氣冷：風扇拆開＋熱交給空氣 | 3D | #industry/group/air_cooling | 氣冷 vs 液冷何時換 |
| switch_wireless | 網通：交換器板卡＋800G 光模組＋CPO | 3D | #industry/group/switch_wireless | 800G 交換器、CPO（k_cpo 已上架） |
| ai_interconnect | 高速連接器：一個接點拆開 | 3D | #industry/group/ai_interconnect | 高速連接器是什麼 |
| mlcc | MLCC 積層陶瓷電容（切開近角） | 3D（另有 2D 疊層） | #industry/group/mlcc | MLCC 是什麼 |
| capacitor | 電容器：鋁電解縱剖開 | 3D | #industry/group/capacitor | 電容怎麼分 |
| power_inductor | 電感・電阻・石英三顆各切一半 | 3D | #industry/group/power_inductor | 電感是什麼 |
| resistor_protect | 被動保護：四顆並排剖開 | 3D | #industry/group/resistor_protect | 保護元件 |
| panel | 面板：TFT-LCD 拆成十三層 | 3D | #industry/group/panel | 面板怎麼疊出來 |
| motion_axis | 工業自動化：一個會動的軸 | 3D | #industry/group/factory_automation | 線性滑軌／伺服軸 |
| machine_tool | CNC 工具機：立式綜合加工機 | 3D | #industry/group/machine_tool | 工具機是什麼 |

## 二、題材 2.5D 等角剖析圖（themes3d.js）—— 22 張

路由一律 `#heatmap/theme/<id>`。

| 圖 id | 名稱 | 類型 | 適合的比比知識 |
|---|---|---|---|
| cowos | CoWoS 先進封裝：一顆 AI 加速器怎麼做出來 | 2.5D | CoWoS |
| hbm_memory | HBM 與記憶體：從一顆 DRAM 到一條模組 | 2.5D | HBM、DRAM 入門（SSD 改用 3D 的 ssd 那張） |
| pcb_ccl | 高階 PCB 與 CCL：一片板子怎麼壓出來 | 2.5D | PCB／CCL |
| glass_substrate | 玻璃基板：下一代封裝載板 | 2.5D | 玻璃基板 |
| asic_ip | ASIC 與矽智財：一顆客製晶片的組成 | 2.5D | ASIC／IP |
| ai_server | AI 伺服器：從一顆晶片到一座機櫃 | 2.5D | AI 伺服器 |
| power_bbu | 伺服器電源與 BBU：機櫃的心臟 | 2.5D | BBU |
| thermal | 散熱與液冷：熱從晶片到機房 | 2.5D | 液冷 |
| silicon_photonics | 矽光子與 CPO：電變光再送進機房 | 2.5D | 矽光子、CPO |
| semi_equipment | 半導體設備與材料：資本支出落在哪 | 2.5D | 半導體設備 |
| apple_chain | 蘋果供應鏈：一支手機怎麼組起來 | 2.5D | 手機結構 |
| edge_ai_pc | 邊緣 AI 與 AI PC | 2.5D | AI PC |
| robotics | 機器人：一個關節的價值分佈 | 2.5D | 機器人關節 |
| drone | 無人機：四旋翼供應鏈 | 2.5D | 無人機 |
| satellite | 低軌衛星：天上與地面 | 2.5D | 低軌衛星 |
| ev_auto | 車用與電動車：台廠切在哪幾塊 | 2.5D | 電動車架構（可接馬斯克快訊） |
| defense | 軍工國防：預算變成哪些載具 | 2.5D | 軍工 |
| heavy_electric | 重電與電網：電從電廠到機房 | 2.5D | 重電 |
| switch_800g | 高速交換器 800G／1.6T | 2.5D | 800G 交換器 |
| mlcc_passive | 被動元件／MLCC 怎麼做出來 | 2.5D | MLCC |
| panel_pkg | 面板轉封裝（面板級封裝） | 2.5D | FOPLP |
| petrochemical | 石化／塑化：輕油怎麼變塑膠 | 2.5D | 石化 |

## 三、文章插圖積木（artillus.js）

`illus` 區塊 kind：`cowos`（CoWoS 剖面）、`rack`（機櫃）、`custom`（文章 JSON 自描述部件，style:2）。其餘產品用 `custom` 重畫或改放站內頁連結＋截圖。

## 四、缺口

- ~~SSD／NAND 沒有專屬圖~~ → 2026-10-19 已補 3D 場景 `ssd`（規格 `docs/diagram_specs/ssd.md`）。題材 2.5D 仍沒有 SSD 專屬圖。
- IC 設計、先進製程（GAA）沒有獨立圖，可借 foundry 3D。
