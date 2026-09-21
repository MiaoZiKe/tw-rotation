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
**架構改成「族群優先、鏈為預設」是所有後續繪圖的前置條件**（`claude/dg-group-slots`，已完成）。

## 入口架構：同一條鏈但不同產品 → 各自獨立分頁（2026-09-21，Andy 拍板）

> 「不能一般電子點進去後就是 MLCC，因為他不代表全部…如果像是 IC 設計、晶圓代工、封裝等等，
>   那就可以放同一頁，形成一個架構，但若是其他同個族群、為不同產品，則需要獨立分頁」

Andy 劃的線只有一條，照著做就好：

| 圖的性質 | 例子 | 怎麼掛 |
|---|---|---|
| **有上下游關聯、構成一條架構** | 半導體鏈的 CoWoS 封裝剖面（IC 設計→晶圓代工→封裝）、AI 伺服器鏈的機櫃與運算托盤 | `level: 'chain'`，點進鏈就**直接看到**那一張 |
| **同一條鏈但彼此不相干的產品** | 一般電子鏈的 MLCC（被動元件）／面板疊層／交換器板卡 | `level: 'group'`，**各自一個網址**，鏈層級改成顯示「圖別選單」 |

改之前的錯：產業鏈頁沒選族群時會退回「這條鏈成交值最大的那張族群圖」，
`electronics` 只有 MLCC 一張，於是「點進一般電子 ＝ 看到 MLCC」——
等於在宣稱一般電子就是 MLCC。**那個跨族群退回已經整個拿掉**，
連帶那句道歉文案（「你選的族群還沒有專屬剖析圖，這張是這條鏈目前有的那一張」）也整句刪掉了。

### 新增一張圖要做的事（只有這三步）

1. 在 `site/diagrams.js` 的 `SLOTS` 註冊一行。**key 就是族群 id**（`groups.yaml` 裡那個），
   `chain` 寫它掛在哪一條鏈，`q` 寫**這張圖回答哪一個具體問題**：

   ```js
   pcb_rigid: { level: 'group', chain: 'ai_server', name: 'PCB：多層板剖面與銅箔走線',
                draw: pcbStack, scene: 'pcb', native: 980,
                q: '一塊 16 層 PCB 是怎麼疊出來的？銅箔、玻纖布、壓合各是誰在做？' },
   ```

2. 沒了。`site/industry.js` 會自動：
   - 把它排進那條鏈的**圖別選單**（卡片會顯示族群檔數、佔比、今日漲跌）
   - 給它一個網址 `#industry/<chain>/dg/<slot>`（可分享、可回上一頁、重新整理打得開）
   - 該族群的個股頁自動掛這一張（`dgPick` 是 strict 的，不會掛到別人的圖）

3. `scripts/_uitest.py` 的 `批次11-MLCC` 段加一條「入口數 ≥ N」即可；
   新圖自己的內容驗收另外開一段。

### 硬性規定

- **`q` 一定要寫。** 圖別選單就是靠它讓人在還沒點進去的時候就知道要不要點；
  沒有 `q` 的圖等於在叫人先點進去再猜。寫法：一句話、問句、講到「所以我該怎麼用」。
- **不准在別的地方再維護第二份圖的名單。** 查找一律走 `window.DiagramSlots`。
- **鏈層級的圖不要亂用。** 只有「這張圖真的涵蓋整條鏈的上下游」才給 `level: 'chain'`；
  拿一個族群的產品圖當鏈的門面，就是這次要修掉的那個錯。

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
