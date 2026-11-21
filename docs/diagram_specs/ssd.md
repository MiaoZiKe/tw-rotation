# ssd：一片 M.2 2280 NVMe SSD 拆開來是什麼

> Andy 2026-10-19：「SSD 也要，請繪圖團隊補 3D 圖」。背景：比比知識要介紹 SSD，
> 網站 3D 場景（`site/three3d.js`）20 張、題材 2.5D（`site/themes3d.js`）22 張都沒有 SSD／NAND。
>
> 共同驗收條件引用 `dg3d_standard.md` §3（結構／視覺／互動／效能），這裡只寫這張圖自己的
> 零件清單、層序、識別特徵、標註與不確定處。

- **id**：3D 場景 `SCENES.ssd`；2D 退路與掛載點 `site/dg/memory_module.js`（`DG.register('memory_module', { scene: 'ssd' })`）
- **放在哪**：族群 `memory_module`（記憶體模組，`pipeline/groups/groups.yaml`，鏈 `semiconductor`）。
  路由 **`#industry/semiconductor/dg/memory_module`**（也可從 `#industry/group/memory_module` 進），剖析圖區按「2D｜3D」切到 3D。
  選這個族群的理由：它的 note 就是「買顆粒做模組與控制晶片：DRAM 模組、SSD／儲存與工控儲存」，成分股 8299 群聯、3260 威剛、5289 宜鼎、2451 創見…正是做 SSD 的人。
- **型式**：真 3D（另附一張 2D 俯視＋側視當 WebGL 退路）。
  為什麼 3D 值得：SSD 的三個識別特徵分在**三個方向** —— 板邊的金手指與 M key 缺口（從正面看）、
  板上晶片的左右排列（從上面看）、NAND 封裝裡疊起來的晶粒（要切開往側面看）。轉一圈正好三件都看到。

## 1. 這張圖要回答什麼問題

「SSD 是什麼？那一小條板子上每一顆晶片各做什麼、台股做的是哪一顆？」

## 2. 零件清單（11 件）與環節對應

| # | part | 零件 | 尺寸（mm，x 長 × z 寬 × y 高） | 環節 `seg` | 小卡列的台股 |
|---|---|---|---|---|---|
| 1 | `ssd_pcb` | PCB 板（M.2 2280 外形） | 80 × 22 × 0.8（畫 1.0） | `hdi_pcb` | `codes: ['3044']` 健鼎（既有 tech 欄「記憶體模組板」；是否含 SSD 板未查證，卡片註明） |
| 2 | `ssd_finger` | M.2 金手指（M key） | 板邊約 4 長、上下兩面 | `hdi_pcb` | 同上（金手指是板廠的鍍金製程） |
| 3 | `ssd_ctrl` | 主控 IC（NVMe 控制器） | 約 13 × 13 × 1.2 | `storage` | `codes: ['8299', '2379']` 群聯、瑞昱（瑞昱既有 note：PCIe SSD 控制 IC，比重未揭露） |
| 4 | `ssd_dram` | DRAM 快取（有／無兩種款） | 約 8 × 12 × 1.0 | `dram_nor` | `codes: ['2408', '3006']` 南亞科、晶豪科（這一環節做 DRAM 的兩家；**未逐家查證是否供 SSD 快取**，卡片註明） |
| 5 | `ssd_nand` | NAND Flash 封裝 ×2（切開一角） | 約 12 × 18 × 1.3 | `storage` | `codes: ['6239', '8150']` 力成、南茂（既有資料：記憶體封測，客戶含 Kioxia／Micron）——**做的是封測，不是 NAND 晶圓** |
| 6 | `ssd_nand_die` | 封裝裡疊起來的 NAND 晶粒（階梯＋打線） | 8 層晶粒示意 | `storage` | `codes: []` → 「台股無直接對應」（3D NAND 晶圓是 Kioxia／Samsung／SK hynix／Micron／SanDisk） |
| 7 | `ssd_pmic` | PMIC 電源管理 IC | 約 4 × 4 × 0.9 | `ic_design` | `codes: []`（見 §6 建議新增環節） |
| 8 | `ssd_ind` | 電源電感 | 約 3 × 3 × 1.5 | `passive_inductor` | 走環節預設（臺慶科、千如、鈞寶…） |
| 9 | `ssd_mlcc` | 去耦電容（MLCC 一排） | 0402／0603 級 | `passive_comp` | `codes: ['2327', '2492', '6173', '3026']` |
| 10 | `ssd_hs` | 散熱片（選配，擺在板子後面當配件，不裝上去） | 約 66 × 18 × 3 | `thermal` | `codes: []`（SSD 散熱片多由模組廠自配，散熱環節的伺服器散熱廠不列） |
| 11 | `ssd_socket` | 主機板上的 M.2 插槽 | 約 6 × 24 × 4 | `connector` | `codes: ['3533']` 嘉澤（LOTES M.2 Key B 插槽型號見於開發板文件，信心中） |

## 3. 層別／排列順序（寫死）

**由左（插槽端）到右（螺絲端），全部在正面：**

1. 主機板的 M.2 插槽（板子還沒插進去，隔一小段距離，看得到金手指）
2. 金手指（M key 缺口在一側，不在正中）
3. PMIC ＋ 電源電感 ＋ 一排 MLCC（靠插槽那一端：電從金手指進來先經過這一區）
4. **主控 IC**（離金手指最近的大顆晶片 —— PCIe 走線越短越好）
5. DRAM 快取（緊鄰主控；DRAM-less 款這一格是空的）
6. NAND 封裝 ×2（往螺絲端排開；顆數依容量而定，2TB 以上常見正反兩面都貼）
7. 板尾：半圓形螺絲缺口（2280 的固定孔位）

**由下到上：** 板子 → 晶片（BGA 錫球焊在板上）→（選配）導熱墊 ＋ 散熱片。
**NAND 封裝內部由下到上：** 封裝基板 → 晶粒 1 … 晶粒 8（每層往同一側錯開一階，露出打線墊）→ 金線打到基板 → 模封膠包住。

## 4. 一定要有的識別特徵

- 板子 **22 × 80 長條**、一端金手指、一端**半圓螺絲缺口** —— 少了任何一個就不像 M.2。
- 金手指**上下兩面**都有、中間有一個**缺口（M key）**，而且缺口偏一側。
- 主控是**最大的那顆方形晶片**，在金手指旁邊；NAND 是**長方形的大封裝**，排在後段。
- NAND 切開那一角看得到**一疊錯開成階梯的晶粒**與**打線**（不是一塊實心）。
- 板面有走線（主控 → 金手指的 PCIe 差動對、主控 → NAND 的通道）、有導通孔與絲印。
- 卡片明講：每一顆 NAND 晶粒**裡面**還有 200～400 層以上的 3D 堆疊（微米級，這張圖的尺度看不到）。

## 5. 標註文字（卡片標題）

| 零件 | 標題 | 一句說明（重點） |
|---|---|---|
| 金手指 | M.2 金手指（M key） | 插進主機板的那一端；缺口位置決定插得進哪種插槽，M key 走 PCIe ×4（NVMe） |
| 主控 | 主控 IC（SSD 的大腦） | 負責 PCIe／NVMe 介面、把邏輯位址對到 NAND 的實體位置（FTL）、ECC 糾錯、磨損平均 |
| DRAM | DRAM 快取 | 放 FTL 對照表；沒有這顆的「DRAM-less」款改借主機記憶體（HMB） |
| NAND | NAND Flash 封裝 | 真正存資料的地方；一顆封裝裡疊了好幾片晶粒 |
| NAND 晶粒 | 封裝裡疊起來的晶粒 | 錯開成階梯才能打線；每一片晶粒內部又是數百層 3D 堆疊 |
| PMIC | PMIC 電源管理 IC | 把 3.3V 轉成主控、NAND、DRAM 各自要的電壓 |
| 插槽 | 主機板上的 M.2 插槽 | 板子斜插進去、尾端用螺絲壓平 |

## 6. 已知不確定的地方（畫面標「示意圖，非實物比例」）

- **高度方向誇張約 2.5 倍**（晶片實際只有 1～1.5 mm 高，照實畫在 80 mm 長的板子上會看不出來）；平面尺寸（22 × 80、晶片佔位）照實際量級。
- M key 缺口位置、金手指根數（每面約 37～38 根，間距 0.5 mm）是依規格的示意，不是逐根照標準畫。
- NAND 封裝內晶粒層數畫 8 層示意（實際 4～16 層依容量）；打線根數示意。
- 主控、DRAM、PMIC 的實際位置依各家設計不同；本圖照「主控靠金手指、NAND 往尾端排」的常見配置（拆解報導多為此配置）。
- 單面款。雙面款（背面也貼 NAND）只寫在卡片，不另畫。
- 台股對應：
  - **PMIC**：搜得到的 SSD 用 PMIC 公開資料多為外商（TI、瑞薩／IDT）；台股 PMIC 廠（致新、茂達、力智）的 SSD 營收查不到，**不列**。
  - **建議新增環節**（不在這一批動 YAML，等 Andy 校訂）：`ssd_pmic` 或更廣的「類比／電源管理 IC」環節；目前 `ic_design` 底下沒有對應的公司，所以小卡顯示「台股無直接對應」。
  - **建議補公司**：`connector` 環節只有 3665 貿聯；M.2 插槽的嘉澤 3533 在 `groups.yaml` 的連接器族群裡有，但 `supply_chain.yaml` 沒有它的公司節點 —— 這張圖只用零件自己的 `codes` 指名，不動 YAML。
  - 健鼎、南亞科、晶豪科「是否供 SSD」未查證，卡片寫明是「這個環節做這類東西的公司」。

### 查證來源（WebSearch 摘要，引用範圍只到摘要內容）

| 事實 | 來源 | 信心 |
|---|---|---|
| 2280＝寬 22 mm、長 80 mm；M key 缺口在第 59～66 腳位置；單面款總厚約 2.3 mm（板約 0.8 mm） | [Wikipedia M.2](https://en.wikipedia.org/wiki/M.2)、[Thomas-Krenn M.2](https://www.thomas-krenn.com/en/wiki/M.2)（Micron 7450 規格書列 2280 最大 22×80×3.9 mm，同一次搜尋摘要） | 高 |
| 主控在金手指旁、NAND 往另一端排；電源區分成金手指端輸入濾波、中段主控供電、尾段 NAND 供電 | [igor'sLAB ORICO IG740 Pro 拆解](https://www.igorslab.de/en/orico-ig740-pro-2tb-nvme-ssd-in-test-without-dram-but-with-brass-cooler-in-the-solid-midfield/2)、[TechPowerUp Kingston NV3](https://techpowerup.com/review/kingston-nv3/2.html) | 中（單篇最完整，其他拆解佐證） |
| DRAM 放 FTL 對照表；DRAM-less 用 HMB 借主機記憶體 | [hwbusters Lexar Thor Ultra](https://hwbusters.com/news/lexar-thor-ultra-hits-11-gb-s-without-a-dram-cache-and-the-timing-isnt-an-accident/)、[hardware-corner SSD 資料庫](https://www.hardware-corner.net/ssd-database/Lexar-NM620/) | 高 |
| 3D NAND 層數量級：Micron 276 層（2024）、SK hynix 321 層、Samsung 286 層（V9）並規劃 400 層以上 | [TrendForce](https://www.trendforce.com/news/2024/10/29/news-samsung-reportedly-plans-400-layer-vertical-nand-by-2026-targeting-1000-layer-nand-by-2030/)、[Wccftech](https://wccftech.com/sk-hynix-400-layer-nand-late-2025-321-layer-nand-1h-2025/amp/) | 中（多為公司規劃） |
| NAND 封裝內多晶粒堆疊（8／16 層），打線須錯開成階梯或加墊片；16 層 BGA-152 封裝高 1.9 mm | [Kioxia 2015 新聞稿](https://kioxia.com/en-jp/about/news/2015/20150806-1.html)、[AnandTech](https://at-web1.www.anandtech.com/show/9520/toshiba-brings-throughsilicon-vias-to-nand-flash) | 高 |
| SSD 用 PMIC 公開資料為外商（TI、IDT／瑞薩） | [eeNews Europe TI](https://cdn.eenewseurope.com/en/ti-introduces-industrys-smallest-power-management-ics-for-solid-state-drives/)、[Renesas](https://renesas.com/en/about/newsroom/toshiba-memory-corporation-selects-idt-s-highly-scalable-power-management-ic-solution-its-flagship) | 中 |
| 嘉澤（LOTES）有 M.2 Key B 插槽料號 APCI0087-P001A | [UDOO M.2 Connectors](https://udoo.org/docs-x86/Hardware_Reference/M.2_Connectors.html) | 中 |

查過但沒結果：「群聯 PMIC 自研」「致新／力智 SSD PMIC」—— 查無 SSD 專用 PMIC 的台股營收揭露，所以 PMIC 不列台股。

---

## 審查紀錄

| 日期 | 審查者 | 過／不過 | 意見 |
|---|---|---|---|
| 2026-10-19 | tech-illustrator（本規格作者） | 規格成立 | 依 Andy 10-19 指令直接開畫；結構重點：金手指＋M key、半圓螺絲缺口、主控靠金手指、NAND 切開見階梯晶粒 |
