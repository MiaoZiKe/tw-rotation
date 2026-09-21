# 2D / 3D 產品剖析圖 —— 完整清單與繪製順序

> Andy 2026-09-21：「需要對 2D 3D 圖的描繪更加細緻，包含電路 銅線 被動元件 主動元件
> 散熱 風扇 PCB ABF 銅箔基板 面板 IC Chip 網通 等等等 太多了，只要有相關就先列出，
> 若繪製方向沒頭緒就網路找諮詢參考，並且需要先安排題材繪製順序，
> 做完一張就先推上去 並且馬上發布我要看成果」

## 現況（2026-09-21 量出來的，不是印象）

| 檔案 | 行數 | 張數 | 性質 |
|---|---|---|---|
| `site/diagrams.js` | 324 | 2（半導體鏈、AI 伺服器鏈） | **真的手繪 SVG**：有實際幾何、零件形狀、剖面、標註線 |
| `site/themes3d.js` | 526 | 19 | **樣板化**：每張只有約 14 行設定，全部走 `chainScene()` / `explodeScene()` 兩個通用場景，畫出來是排成一列的方塊 |
| `docs/diagram_specs/` | — | 5 份規格書 | MLCC、面板疊層、交換器板卡、輕油裂解、變壓器GIS —— **只有規格書，一張都還沒畫** |

「更細緻」要處理的就是中間那一列：19 張樣板圖要升級成真的畫出來的零件。

## 為什麼之前卡住

`window.Diagrams` 是**一條產業鏈一個 slot**（`site/diagrams.js` 結尾），
但五份規格書畫的全是**族群層級**的東西。一般電子一條鏈要掛 MLCC、面板、交換器三張，
傳產一條鏈要塞塑化＋生技＋觀光＋食品 —— 塞不下，所以畫了也沒地方放。
**架構改成「族群優先、鏈為預設」是所有後續繪圖的前置條件**（`claude/dg-group-slots` 進行中）。

## 完整可畫清單（依 Andy 點名的項目對回實際族群）

| Andy 點名 | 對應族群 | 鏈 |
|---|---|---|
| 電路、銅線 | `pcb_rigid` PCB 硬板製造、`flex_pcb` 軟板、`copper_foil` 銅箔 | ai_server |
| PCB | `pcb_rigid`、`flex_pcb` | ai_server |
| ABF | `ic_substrate` PCB 載板 | ai_server |
| 銅箔基板 | `ccl` CCL 銅箔基板、`glass_fiber` 玻纖布 | ai_server |
| 被動元件 | `mlcc` 被動元件 MLCC、`resistor_protect` 電阻與被動保護、`capacitor` 電容器、`power_inductor` 功率電感、`crystal` 石英頻率控制、`jp_passive` 日本被動元件 | electronics |
| 主動元件 / IC Chip | `foundry` 晶圓代工、`ai_adv_packaging` AI 先進封裝、`osat` 封測代工、`hbm` HBM、`analog_power_ic` 類比與功率 IC、`wide_bandgap` 第三代半導體 | semiconductor |
| 散熱 | `liquid_cooling` 液冷散熱 | ai_server |
| 風扇 | `air_cooling` 氣冷與核心組件 | ai_server |
| 面板 | `panel` 面板產業、`microled` MicroLED、`display_driver_ic` 顯示驅動 IC | electronics / semiconductor |
| 網通 | `switch_wireless` 高速交換器與無線網路、`optical_module` 高速光模組、`silicon_photonics` 矽光子與 CPO、`hpc_network_ic` HPC 與網通 IC | ai_server / semiconductor |

另外沒被點名但同樣有實體可畫的：`server_psu` 電源供應器、`bbu` BBU 電池備援、
`connector_ind` / `connector_auto` 連接器、`ai_interconnect` AI 互連元件、
`chassis_rail` 機殼與滑軌、`silicon_wafer` 矽晶圓、`glass_substrate` 玻璃基板、
`battery_cell` 電芯、`solar` 太陽能、`wind_power` 離岸風電、`heavy_electric` 重電設備、
`petrochemical` 石化、`machine_tool` CNC 工具機、`satellite` 低軌衛星。

## 繪製順序（一張一部署）

排序原則：① Andy 點名的優先 ② 規格書已寫完的優先 ③ 一張圖能同時交代多個點名項目的優先
④ 成交值權重大的鏈優先。

| # | 圖 | 一張圖交代掉的點名項目 | 規格書 | 掛在 |
|---|---|---|---|---|
| 0 | **架構：slot 改族群層級** | —（前置條件，沒有它後面都無處可掛） | — | — |
| 1 | **MLCC 疊層剖面** | 被動元件 | ✅ 已寫 | `mlcc` |
| 2 | **多層 PCB 剖面＋走線＋銅箔** | 電路、銅線、PCB、銅箔基板 | ✗ | `pcb_rigid` |
| 3 | **ABF 載板剖析** | ABF | ✗ | `ic_substrate` |
| 4 | **IC 封裝剖析（晶粒→凸塊→中介層→封裝體）** | 主動元件、IC Chip | ✗ | `ai_adv_packaging` |
| 5 | **液冷冷板＋均熱片 VC＋熱管** | 散熱 | ✗ | `liquid_cooling` |
| 6 | **風扇與氣冷模組** | 風扇 | ✗ | `air_cooling` |
| 7 | **面板疊層** | 面板 | ✅ 已寫 | `panel` |
| 8 | **交換器板卡＋800G 光模組＋CPO** | 網通 | ✅ 已寫 | `switch_wireless` |
| 9 | 電源供應器 PSU ＋ BBU | — | ✗ | `server_psu` |
| 10 | 連接器與高速互連 | — | ✗ | `connector_ind` |
| 11 | 電感／電阻／石英（其餘被動元件） | 被動元件（補完） | ✗ | `power_inductor` 等 |
| 12 | 第三代半導體功率元件 | 主動元件（補完） | ✗ | `wide_bandgap` |
| 13 | 輕油裂解 | — | ✅ 已寫 | `petrochemical` |
| 14 | 變壓器 GIS | — | ✅ 已寫 | `heavy_electric`（**待決定取代或並存**） |

## 工作方式（Andy 2026-09-21 指定）

1. **一張畫完就推 main、馬上部署**，不要累積。
2. 部署完**主動提醒 Andy 去看**，附網址與版號徽章。
3. 提醒完**不要停下來等**，直接接著畫下一張；他會自己回覆。
4. **沒頭緒就上網查參考**（CLAUDE.md 的「有疑問先上網查證」那條）：
   原廠產品頁與技術文件、各大新聞媒體、投顧與研究平台。查到的來源寫進規格書。
5. 每張圖開畫前先有 `docs/diagram_specs/<id>.md`，畫完過 `mechanical-engineer`（結構）
   與 `art-director`（視覺）雙審。
6. **零件的 `data-part` 一律要寫**（2026-09-21 晚間新增，見 `site/diagrams.js` 的 `stampParts`）。
   高亮現在分兩層：被點的那一個 `.sel-part`（最強）→ 同 `data-seg` 的其餘 `.sel`（次強）→ 其餘 `dim`。
   沒寫 `data-part` 的零件會被自動補一個「環節 id ＋ 文件順序」的 key，
   所以**圖還是會動**，但那個 key 只在同一張圖裡有效，**2D 點完切到 3D 會對不起來**。
   要讓兩邊同步就替 2D 的 `data-part` 與 `three3d.js` 場景零件的 `part` 寫同一個字串；
   2D 拆成好幾塊、3D 只有一塊（或反過來）時用 `data-alias` / `alias` 接起來。
   ⚠ **單一環節的圖（整張只有一個 `data-seg`）尤其要注意**：後面 13 張多數是這種，
   沒有零件身分的話「點誰都一樣」—— MLCC 那張改之前就是點零件 A 跟點零件 B
   逐像素完全相同。`stampParts` 會自動替這種圖補上 `.dg1`，
   CSS 才知道要把「同環節但不是主角」的那幾個退到 `--dg-sib-o`。

## 平行的另一條線：19 張樣板題材圖升級

`site/themes3d.js` 的 19 張（cowos / hbm_memory / pcb_ccl / glass_substrate / asic_ip /
ai_server / power_bbu / thermal / silicon_photonics / semi_equipment / apple_chain /
edge_ai_pc / robotics / drone / satellite / ev_auto / defense / heavy_electric）
目前都是 `chainScene()` / `explodeScene()` 排方塊。
上面 1～14 每畫完一張真的零件，能共用的就回頭把對應的題材圖換掉，不另外排一條工。
