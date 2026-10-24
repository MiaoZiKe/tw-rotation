# siph_cpo：矽光子／CPO 剖析 —— 光引擎怎麼被「共同封裝」進交換器，以及這條鏈的光與錢從哪走到哪

> 規格書先寫、`mechanical-engineer` 簽掉，`tech-illustrator` 才開畫（AGENTS.md §14）。
> 2026-10-24 由 mechanical-engineer 起草。證據等級一律是 **WebSearch 摘要**（容器擋 `WebFetch`），
> 沒有人讀過原文；來源與信心度集中在 §7。**查不到的一律標「示意」，不編數字。**
>
> **共同驗收條件引用 `dg3d_standard.md` §3**（結構／視覺／互動／效能／不畫真實廠商外觀），
> 3D 細緻度引用 `dg3d_standard.md` §5（倒角、微表面、流線、效能上限 ≤150,000 三角形／≤300 draw call）。
> 版面與卡片引用 `_STYLE.md`、`_TEMPLATE.md` §0（畫布 980、字級下限 12px、章節 2～4、§1 ≤ 560、色一律 `--dg-*`）。

- **id**：`siph_cpo`（兩張圖：**A＝`siph_cpo_pkg`**、**B＝`siph_cpo_chain`**）
- **放在哪（★ 要先被簽掉，見 §0-C）**：`ai_server` 鏈。`groups.yaml` 已有 `silicon_photonics`（矽光子與 CPO，上游）
  與 `optical_module`（高速光模組）兩個族群；`themes.yaml` 已有題材 `silicon_photonics`。
  `SLOTS` 的 key 必須等於族群 id（一個族群一個 slot），所以建議：

  ```js
  silicon_photonics: { level: 'group', chain: 'ai_server', name: 'CPO 交換器封裝：ASIC 與光引擎共封裝',
                       draw: siphCpoPkg,  scene: 'silicon_photonics', native: 980,
                       q: '光引擎為什麼要搬到交換晶片旁邊？EIC、PIC、光纖、外置雷射各在哪一層、哪一段是台廠做的？' },
  optical_module:    { level: 'group', chain: 'ai_server', name: '光訊號路徑與四種光互連架構',
                       draw: siphCpoChain, scene: null, native: 980,
                       q: '雷射、矽光子晶片、封裝、測試到機櫃佈線，錢與光各走哪一條？可插拔、LPO、NPO、CPO 差在哪？' },
  ```
  檔案放 `site/dg/siph_cpo.js`（`window.DG.register(...)` 註冊兩個 slot，不動 `industry.js`／`index.html`）；
  3D 場景放 `site/three3d.js` 的 `SCENES.silicon_photonics`。
  ⚠ **不要跟 `site/themes3d.js` 的 `T.silicon_photonics`（題材頁那張五站流程圖，同 id 但是另一套系統）混為一談**，
  那一張不動；`data-part` 前綴用 `sp_`（A）與 `spc_`（B），避免跟既有 `ag_*`、`sc_*` 撞名。
- **型式**：
  - **A**：**真 3D 爆炸（主）＋ 2D 剖面（輔，含光引擎放大、俯視佈局）**。Andy 指定要 3D，§1 說明為什麼這張符合 AGENTS §11 的 3D 判準。
  - **B**：**純 2D**（光訊號路徑帶 ＋ 三條供應鏈分道 ＋ 四架構對照）。不做 3D（§1 末段）。
- **版面寬度**：980 原生（DECISIONS #227）。字級下限 12px：`--dg-fs-ttl` 16 ／ `--dg-fs-hd` 13.5 ／ `--dg-fs-lbl` 12.5 ／ `--dg-fs-min` 12。

---

## 0. 開畫之前要先簽掉的四件事

### 0-A　跟既有圖的分工（實際讀過原始碼）

| 既有 | 位置 | 已經畫到的 | 這份不重畫什麼 |
|---|---|---|---|
| 題材頁「矽光子與 CPO」五站圖 | `themes3d.js` `T.silicon_photonics` | 磊晶 → 雷射 → 光引擎（一片蛇行波導）→ 光收發模組（OSFP）→ 交換器（1U 盒） | 單件示意，**沒有任何一件畫出它們互相怎麼接** |
| AI 伺服器機櫃 2D/3D | `diagrams.js` `aiServer`、`SCENES.ai_server` | 機櫃裡一顆「光通訊」方塊（`seg: optical`）、前面板可插拔 | 機櫃整體 |
| 先進封裝 `ai_adv_packaging` | `ic_package.md` | C4／µbump／混合鍵合尺度、CoWoS-S/R/L | **混合鍵合與 SoIC 只在這裡「引用」**，不重畫三種中介層對照 |
| 連接器 `ai_interconnect` | `connector_hsio.md` | 可插拔光模組籠（OSFP/QSFP-DD cage） | 這份只在 B 的架構對照裡畫「可插拔」那一格的位置，不畫籠子內部 |

**一句話分工**：既有的都是「單件長相」；這份回答的是 **「它們怎麼組成一台 CPO 交換器」（A）** 與 **「光與錢沿著哪幾條線走到交換器」（B）**。

### 0-B　這張圖的物理主軸（三句，畫錯任何一句整張就錯）

1. **雷射不在光引擎裡。** CPO 的雷射是**外置**的（ELS／ELSFP，從前面板插入，用**保偏光纖 PM fiber**把一道連續光送進光引擎）。
   理由：雷射怕熱、壽命隨溫度衰減，不能跟幾百瓦的交換晶片放在同一顆封裝裡；外置也讓雷射壞了可以在前面板直接換。（Senko 摘要：外置設計把雷射熱環境與共封裝 ASIC 分開，並以 IEC 60825-2 Hazard Level 1 為目標。）
2. **光引擎是「EIC 疊在 PIC 上」，不是並排。** PIC（光子晶片：波導、調變器、Ge 光偵測器、耦合器）在**下**，EIC（電子晶片：驅動 Driver、跨阻放大器 TIA）以 SoIC 混合鍵合**面對面疊在 PIC 上方**（台積電 COUPE 概念）。
   PIC 的**邊緣要露出來**給光纖陣列（FAU）耦合 —— **EIC 與散熱蓋不可以蓋住耦合邊**。
3. **距離是這四種架構的分水嶺。** 可插拔／LPO 的光在**前面板**，電訊號要走一長段 PCB 走線；NPO 的光引擎在板上 ASIC 旁（公分級）；CPO 的光引擎與 ASIC **在同一個封裝／載板上**（毫米級）。

### 0-C　掛在哪、題材分頁（★ 需 CEO／Andy 拍板，不是繪圖端能決定）

- Andy 說「產業地圖新增矽光子／CPO 題材分頁」。現況：`ai_server` 鏈已有 `silicon_photonics`（上游）與 `optical_module` 兩個族群，
  題材 `themes.yaml: silicon_photonics` 也已存在。**本規格假設「分頁」＝這兩個族群的圖別選單**，不新增鏈。
- 兩張圖要兩個 slot（一族群一 slot）→ A 掛 `silicon_photonics`、B 掛 `optical_module`（B 的主題是「模組怎麼被 CPO 取代」，掛光模組族群讀者找得到）。
  **備案**：若要兩張同族群，改成單一 slot、章節切換（A／B 兩個頁籤）。選哪個由 CEO 定，**圖的內容不受影響**。
- ⚠ `ai_server` 鏈目前 7 張圖，晶片列已經緊（`_TEMPLATE.md` §0-B：畫布額度 656）。再加 2 張可能讓選單換行、chrome 再 +38px，
  **`ai_server` 鏈上原有 7 張要全部回頭重量**（art-director）。
- 成分股（公司名稱稍後由調查補進，**本規格只用「段落名」**）：族群 `silicon_photonics` ＝ 磊晶／雷射晶粒／FAU 對準／被動光學；
  `optical_module` ＝ 模組組裝。**哪一檔掛在哪個零件，一律讀 `supply_chain.yaml` 的 `companies[].tech`，圖上不寫 YAML 沒有的角色描述。**

### 0-D　3D 判斷（照 AGENTS §11「轉一圈真的能多理解一件事」）

| 要講的事 | 轉一圈會多理解嗎 | 判定 |
|---|---|---|
| 光引擎**環繞**在 ASIC 四周（平面配置）× 每顆引擎內部**垂直**堆疊（EIC 在 PIC 上） | **會。** 同時需要平面位置與垂直層數，正是 `ic_package.md` §1 寫死的「回頭加 3D」條件 ①②。2D 剖面只切得到一個方向 | **3D（A 的主角）** |
| 光纖從引擎**邊緣向外**、不是向上；外置雷射在前面板另一處 | 會（光纖朝向是三維關係） | 3D |
| PIC 內部元件（調變器、波導、Ge PD）、混合鍵合界面、載板剖面 | 不會（全在剖面） | 2D 放大（A 的輔） |
| 四架構的距離／功耗／時程對照 | 不會，而且透視會毀掉比例 | 2D（B） |
| 供應鏈分道 | 不會 | 2D（B） |

> 回頭加 3D 給 B 的條件：不存在。B 是關係圖與對照表，**加 3D 不算理由**。

---

## 1. 這兩張圖要回答什麼問題

**A**：「CPO 交換器裡，ASIC 和光引擎是怎麼塞進同一顆封裝的？光從哪來、往哪去，光引擎裡面疊了什麼，每一層是哪一段台廠做的？」

讀者看完要能自己講出這五句（畫在 A 右側說明欄抬頭）：
1. 交換 ASIC 居中，**周圍一圈光引擎**，同在一片大載板上，電訊號只走**毫米級**的短路。
2. **每顆光引擎＝PIC（下）＋EIC（上）**，用混合鍵合疊起來；EIC 管「電變成驅動」與「光電流變回電壓」，PIC 管「把光調變／偵測」。
3. **光纖從引擎的外緣出去**（FAU 對準接在 PIC 邊緣），不是往上。
4. **雷射不在封裝裡**：外置雷射模組（ELSFP）插在前面板，經保偏光纖把連續光送進 PIC。
5. 封裝上方的散熱蓋／冷板**壓在 ASIC 上**，不蓋住光纖耦合邊。

**B**：「雷射、矽光子晶片、封裝、測試到機櫃佈線，各段誰做？可插拔、LPO、NPO、CPO 差在哪？」

**成敗判準**：Andy 指著 A 圖任一層，要能說出「這層是誰做的（晶圓代工／載板廠／光學元件廠／設備商／測試介面），它變好會讓什麼變好」；
指著 B 圖任一格，要能說出「這格相對於可插拔，把光搬近了多少、換來什麼、付出什麼」。

---

## 2. 圖 A：CPO 交換器封裝剖析

### 2-A 零件清單（3D 與 2D 共用一份編號；相對尺寸用「大小關係」，畫面比例誇張但**大小關係不准倒過來**）

基準件：**一顆 CPO 交換器封裝**（一顆交換 ASIC 居中 ＋ N 顆光引擎環繞 ＋ 一片大型載板），外加前面板的 ELSFP 與光纖。

| # | 零件（中文／原文） | 真實相對尺寸 | 材質觀感 | `data-seg`（段落） | 依據 |
|---|---|---|---|---|---|
| 1 | 主板 PCB（host board） | 全圖**最大**的平面，比載板大很多 | 鼠尾草綠（`--dg-pcb`），走線可見 | `hdi_pcb`（高階 PCB） | 常識 |
| 2 | BGA 錫球 | 比 C4 大一個量級 | 銀灰球陣列 | `abf_pcb` | `ic_package.md` 3-A#1 |
| 3 | 封裝載板（ABF 增層基板） | **平面上最大的封裝件**，大於 ASIC 好幾倍；厚度居全封裝之冠 | 深綠，剖面可見多層線與盲孔 | `abf_pcb`（IC 載板） | `ic_package.md` 3-A#2 |
| 3b | ABF 增層膜 | 載板裡的介電薄層 | 半透明琥珀、無玻纖織紋 | `substrate_material`（載板材料） | `ic_package.md` 3-A#2b |
| 4 | C4 凸塊（晶粒↔載板） | 節距約 150–200 µm 量級（見 §7-E1） | 塌成鼓形焊錫 | `adv_pkg`（先進封裝）⚠ | `ic_package.md` §7-A2 |
| 5 | **交換 ASIC 晶粒**（switch ASIC die） | 全封裝**面積最大、最厚的晶粒**，位於**正中央**；每顆光引擎的面積明顯小於它（單邊 < ASIC 邊長約 1/3，示意） | 深藍矽色、頂面規則功能方塊（通用示意版圖，**不照真實晶片畫**） | `ic_design`（IC 設計，ASIC 設計）；晶圓製造 `foundry` | `dg3d_standard.md` §5 die |
| 6 | **光引擎（optical engine，OE）** × N | 環繞 ASIC，**至少 4 顆**，建議 **8 顆**（Bailly 例：八顆 6.4T 合成 51.2T，§7-A2）；分佈在 ASIC 四邊、**對稱** | 見 6a／6b | — | §7-A2 |
| 6a | **PIC（光子積體電路）** | **在 OE 的下層**，footprint 比 EIC 大，**外緣側伸出 EIC 之外**（露出耦合邊） | 矽色偏冷灰，頂面有細蛇行波導 | `foundry`（晶圓代工：PIC 製造） | §7-A1 |
| 6b | **EIC（電子積體電路：Driver／TIA）** | 在 OE 的**上層**，比 PIC **小**（只蓋住 PIC 內側、不蓋耦合邊）；很薄 | 同矽色、頂面規則格紋 | `ic_design`（EIC 設計）；`foundry`（65 奈米級製造，§7-A1） | §7-A1 |
| 6c | **混合鍵合界面**（EIC↔PIC） | 兩者之間**一條銅墊對銅墊的界線，沒有凸塊** | 細銅色虛線矩形 | `adv_pkg`（SoIC）⚠ | `ic_package.md` 3-A#6b |
| 6d | **PIC 底部接點＋TSV** | PIC 下面接載板；電訊號經 PIC 內 TSV 往下（**示意，§6-U1**） | 銅柱＋C4/µbump | `adv_pkg` ⚠ | §6-U1 |
| 7 | **FAU（光纖陣列單元，Fiber Array Unit）** | 一小塊**玻璃 V 槽塊**夾住一排光纖，**黏在 PIC 外緣**；寬度約等於 PIC 的耦合邊 | 透明玻璃塊＋細光纖 | `optical`（FAU 對準接合）| 供應鏈 YAML `foci` note |
| 8 | **資料光纖**（TX 出／RX 進） | 極細，從 FAU **水平向外**拉出封裝，彎向前面板 | 細線，一般單模光纖色（`--dg-sw-fiber`） | `optical`（光纖套件／Shuffle Box） | YAML `browave` tech |
| 9 | **雷射輸入光纖（保偏 PM fiber）** | 同樣細，但**要跟資料光纖區分標示**；方向是**往 PIC 進** | 細線，標記不同色環／虛線 | `optical` | §7-A4 |
| 10 | **ELSFP 外置雷射模組** | 在**前面板**，**不在載板上**；形狀是一支可插拔小模組（長方金屬殼） | 金屬殼 ＋ 前端光纖；內部不畫 | `optical`（ELS 模組）；其晶粒 `optical_epi` | §7-A4 |
| 10b | CW 雷射晶粒（ELSFP 內，局部放大） | 比 PIC 小很多的 InP 晶粒；**只在 2D 放大格出現，3D 不畫內部** | 金色小方塊＋出光箭頭 | `optical_epi`（磊晶／雷射晶粒） | YAML `lpc` |
| 11 | TIM1 | 極薄，夾在**ASIC 頂面**與散熱蓋／冷板之間，**只蓋 ASIC，不蓋光引擎** | 半透明灰 | `thermal` | `ic_package.md` 3-A#11 |
| 12 | 散熱蓋／冷板（lid／cold plate） | 壓在 ASIC 上，**上表面是全圖最高的一層**；對光引擎位置**挖空或讓開**，更不可蓋住 FAU 邊 | 金屬灰 | `thermal`（散熱） | §6-U3 |
| 13 | 補強環（stiffener） | 圍住載板邊緣的一圈，**不碰晶粒、不蓋光纖出口** | 金屬灰 | `adv_pkg` ⚠ | `ic_package.md` 3-A#10 |
| 14 | 前面板（faceplate）＋光纖連接器 | 一片立板；資料光纖終止在這裡的連接器（CPO 面板是**光纖連接器**，不是可插拔收發模組）；**ELSFP 插在同一面板** | 鈑金灰 | `connector`／`optical`（待調查補）| §7-A2（128 個 LC） |
| 15 | 底部填充（underfill） | 填在凸塊之間、邊緣有圓角 | 半透明琥珀 | `adv_pkg` ⚠ | `ic_package.md` 3-A#8 |

⚠ `adv_pkg`（先進封裝 CoWoS/SoIC）這格依 `ic_package.md` §7-D1 的狀態，**成分股可能 0 家**（以 `supply_chain.yaml` 現況為準，
本規格不假設）；點下去若為 0，畫面必須有一行說明，沿用 `ic_package` 的處理。

### 2-B 局部放大格（2D）

| # | 內容 | 說明 |
|---|---|---|
| Z1 | **PIC 內部元件特寫**（俯視＋剖面各一） | 由光的路徑順序放：**輸入耦合器 → 分光器 → 調變器（MZM 或微環 MRM，擇一畫，註明另一種存在）→ 輸出波導 → 邊緣耦合器**；RX 側：**邊緣耦合器 → 波導 → Ge 光偵測器**。頂層矽波導在 SOI 的頂矽層（見 §7-B1）。電極（調變器的 p-n 接面電極、Ge PD 的接點）向**上**連到 EIC。 |
| Z2 | **光引擎剖面放大**（A 的 2D 主體） | 由下到上 `載板 → C4 → PIC（含 TSV）→ 混合鍵合 → EIC`；PIC 外緣側 `邊緣耦合器 → FAU → 光纖` 水平向外 |
| Z3 | **俯視佈局小圖** | ASIC 居中、OE 環繞（8 顆，四邊各 2，**示意**）、每顆 OE 的 FAU 朝外、光纖匯往前面板；ELSFP 在面板 |
| Z4 | **ELSFP 光路小圖** | CW 雷射 → ELSFP 前端 → **PM 光纖（多條）** → 進各顆 OE 的輸入耦合器（一個 ELSFP 分供多顆引擎／多條光纖，§7-A4） |

### 2-C 版面（980 寬，寫死）

- **§1（永遠看得到，≤ 560）**：左欄卡片 ｜ 主剖面 Z2（中，由下到上）｜ 右欄卡片 ＋ Z3 俯視小圖。**卡片 ≤ 10 條**（上表 #1～#15 合併成 10 條：主板+BGA、載板、ASIC、PIC、EIC+混合鍵合、FAU+光纖、PM 光纖+ELSFP、TIM+冷板、補強環/底填、面板）。
- **章節（2～4 段，標題 ≤ 26 字、hint 寫裡面有什麼 ≤ 30 字）**：
  ① 「PIC 裡面有什麼」—— Z1；
  ② 「雷射為什麼放在外面」—— Z4 ＋ 熱的說明；
  ③ 「台股各做哪一段」—— 台股標示帶（§2-F）。
- **3D 場景（`#dg3d`）**：見 §3。

### 2-D 層別／流向順序（★ 可判定，最常錯的四組全部寫死）

**D1 封裝剖面由下到上（違反其一就退回）**

```
主板 PCB → BGA 錫球 → ABF 載板 → C4 凸塊 → { ASIC 晶粒 ｜ 光引擎: PIC(下) → 混合鍵合 → EIC(上) } → TIM1(只在 ASIC 上) → 散熱蓋／冷板
```
- ASIC 與光引擎**並排站在同一片載板上**（同一高度基準），**不是 OE 疊在 ASIC 上**。
- **EIC 在 PIC 上方**，不能在下方、也不能並排放在載板上（那是另一種做法，不是這張要畫的 COUPE 式）。
- EIC 與 PIC 之間**只有一條界線**（混合鍵合），**畫凸塊就錯**（跟 `ic_package` 的 R 規則一致）。
- 光引擎頂面**不高於 ASIC 頂面**（否則冷板壓不到 ASIC）；冷板只接觸 ASIC（經 TIM1）。

**D2 光的方向（最容易畫反）**

```
TX（發送）：ELSFP(CW 光) →PM 光纖→ PIC 輸入耦合器 → 分光 → 調變器 ←(電) EIC 驅動器 ←(電) ASIC
            調變後的光 → 輸出波導 → 邊緣耦合器 → FAU → 資料光纖 → 前面板
RX（接收）：前面板 → 資料光纖 → FAU → 邊緣耦合器 → 波導 → Ge 光偵測器 →(光電流)→ EIC 的 TIA →(電)→ ASIC
```
- **CW 光是「進」PIC 的**，箭頭指向 PIC；**資料光纖是「出／進」前面板**，兩者不可畫成同一條。
- **雷射端沒有任何箭頭指向 ELSFP**（雷射是光源，不是接收端）。
- **驅動器（Driver）在 EIC、Ge PD 在 PIC、TIA 在 EIC** —— 這三件的位置對應一次，錯一個就是結構錯。
- 電訊號：ASIC ↔ EIC 的連線是**短距離（毫米級）**，路徑經載板與 PIC 的 TSV（§6-U1，示意）。

**D3 光纖與面板**
- FAU 在 PIC **外緣（遠離 ASIC 的那一邊）**，光纖**向外**，絕不朝向 ASIC 中心。
- 光纖在封裝外才彎向前面板；**不穿過散熱蓋或冷板**（挖槽讓位也可，但要畫出讓位）。
- ELSFP 與資料光纖連接器**都在前面板**；ELSFP 旁邊要看得出**不是一般收發模組**（沒有資料光口，只有光源輸出）。

**D4 爆炸拆解的順序（3D）**：沿 Z 軸由下往上拉開 `主板 → BGA → 載板 → C4 → ASIC / PIC → 混合鍵合 → EIC → TIM → 冷板`；
FAU 與光纖沿**水平向外**拉開（不隨 Z 軸走）；ELSFP 與面板獨立擺在場景一側，用 PM 光纖連回。收攏位移為 0。

### 2-E 標註文字

| 指到哪 | 文字寫什麼 |
|---|---|
| ASIC | 「**交換晶片居中。** 光引擎環繞在它周圍的同一片載板上，電訊號只走毫米級的短路」 |
| 光引擎（整體） | 「**光引擎＝EIC 疊在 PIC 上。** 本圖畫 8 顆示意（Broadcom 51.2T 平台為 8 顆 × 6.4T，來源：廠商新聞稿 2024-03）；各家顆數與排法不同」 |
| PIC | 「**矽光子晶片（PIC）**：把光分路、調變、偵測的晶片。波導、調變器、鍺（Ge）光偵測器都做在這裡」 |
| EIC | 「**電子晶片（EIC）**：驅動調變器（Driver）、把光偵測器的微小電流放大（TIA）。台積電 COUPE 用 65 奈米級製程（來源：產業媒體 2024）」 |
| 混合鍵合 | 「**EIC 與 PIC 之間沒有凸塊**，銅墊直接對銅墊（混合鍵合／SoIC）。接點更密、路徑更短」 |
| FAU | 「**光纖陣列（FAU）接在 PIC 的邊緣**：把一排光纖對準到晶片上的耦合器。對準誤差是次微米級，所以要主動對準（來源：SWTest 2026 摘要）」 |
| 資料光纖 | 「**資料光纖**：從光引擎外緣拉出，通到前面板連接器」 |
| PM 光纖 | 「**保偏光纖（PM）**：把外置雷射的連續光送進 PIC，光的偏振方向要維持不變」 |
| ELSFP | 「**外置雷射模組（ELSFP）**：插在前面板，不在封裝裡。雷射怕熱，所以放在遠離幾百瓦交換晶片的地方，壞了也能前面板直接換」 |
| 冷板／蓋 | 「**散熱壓在 ASIC 上**；光引擎的位置讓開，光纖邊更不可被蓋住」 |
| 載板 | 「大型 ABF 載板：ASIC 與全部光引擎共用，尺寸比一般 AI 封裝更大（**相對大小示意**）」 |
| 台股帶 | 見 §2-F |

**畫面上一定要有的四行**（左下角）：
```
示意圖，非實物比例｜層厚、凸塊、波導與光纖尺寸均為誇張放大
光引擎顆數、排列與載板／中介層做法依各家方案而異，本圖為概念示意
PIC 內元件（調變器種類、耦合器形式）擇一示意，另一種亦存在
本圖畫「雷射外置」的 CPO；雷射整合在模組內的是可插拔，見「光訊號路徑與四種光互連架構」那張
```

### 2-F 台股標示帶（A 圖最下，**只寫段落名，公司名稍後補**）

| 帶 | 段落 | 說明（寫「做哪一件事」，公司由調查補） | `data-seg` |
|---|---|---|---|
| ① | 磊晶／雷射晶粒 | InP 磊晶片、CW 雷射晶粒（ELSFP 的心臟） | `optical_epi` |
| ② | 外置雷射模組（ELS／ELSFP） | 把雷射晶粒做成前面板模組 | `optical` |
| ③ | PIC 製造（晶圓代工） | 矽光子晶片與 EIC 的製造、SoIC 堆疊 | `foundry` |
| ④ | EIC／ASIC 設計 | 驅動／TIA 電路與交換晶片的設計（**交換 ASIC 的設計者為外商**，畫面註明） | `ic_design` |
| ⑤ | 光學耦合（FAU／光纖套件） | FAU 對準接合、Fiber Harness／Shuffle Box | `optical` |
| ⑥ | 載板 | ABF 載板與增層膜 | `abf_pcb`／`substrate_material` |
| ⑦ | 散熱 | 冷板、蓋 | `thermal` |
| ⑧ | 交換器整機 | CPO 交換器系統 | `switch` |

---

## 3. 圖 A：3D 細節規格（`SCENES.silicon_photonics`）

> 引用 `dg3d_standard.md` §5：倒角、微表面、流線、效能上限（≤150,000 三角形、≤300 draw call）。
> 不新增 3D 函式庫、不新增 CDN；晶粒版圖用通用示意（不照真實晶片）。

| 項 | 規格 |
|---|---|
| 相機 | 斜上方俯視，能同時看到 ASIC、至少 4 顆引擎、前面板一角；可轉 360 度含底部 |
| 零件 kind（建議，沿用既有為主） | 主板 `pcb`、BGA `balls`（整片鋪滿）、載板 `substrate`、C4 `bump`（鼓形）、ASIC `die`、PIC `die`（新增參數 `waveguide:true`：頂面蛇行波導＋耦合器）、EIC `die`（較小，疊上去）、FAU 新 kind `fau`（玻璃塊＋V 槽＋細光纖）、冷板 `lid` 或 `coldplate`、ELSFP `optic`（沿用金屬殼）|
| 流線 | ① **光**（`kind:'sig'` 光色）：ELSFP → PM 光纖 → PIC 輸入（**方向朝 PIC**）；② 調變後資料光：PIC → FAU → 資料光纖 → 面板；③ **電**：ASIC ↔ EIC 短線（毫米級，畫短）；④ **電力**由主板往上（`dir:-1`，沿用 hbm 場景做法）。動態模式才跑，靜止時走線與光纖本體仍看得見 |
| 脈衝 | `ELSFP → PM 光纖 → PIC → EIC ← ASIC` 一顆一顆接力點亮（單向，不來回） |
| 發光 | 只給被選的零件（`dg3d_standard` §3）；光纖不常亮 |
| 標籤／晶片 | `lbl3d` 沿用個股晶片（`twOf(sc, seg)`）；`adv_pkg`、`hyperscaler` 等 0 家的寫「台股無直接對應」 |
| 零件編號 | 與 §2-A 一致；`data-part` 前綴 `sp_`（`sp_pcb`、`sp_bga`、`sp_sub`、`sp_c4`、`sp_asic`、`sp_pic`、`sp_eic`、`sp_hb`、`sp_fau`、`sp_fiber`、`sp_pm`、`sp_elsfp`、`sp_tim`、`sp_lid`、`sp_face`） |

---

## 4. 圖 B：光訊號路徑與產業鏈分層（2D）

### 4-A 版面（980 寬，三區，上到下）

```
B1 光訊號路徑帶（橫向，單排）
B2 供應鏈分道（三條並行的道，匯到交換器整機，再到機櫃）
B3 四種光互連架構對照（四欄，同一把尺）
```
章節（2～4 段）：B1＋B2 為 §1（≤560）；B3 為章節「四種架構差在哪」；再一段「數字從哪來」（來源與口徑，收起）。

### 4-B B1　光訊號路徑帶（由左到右，一個 TX 方向＋一個 RX 方向）

`ELSFP（CW 雷射）→ PM 光纖 → 輸入耦合器 → 調變器（接 EIC 驅動器、ASIC 電訊號）→ 邊緣耦合器 → FAU → 資料光纖 → 前面板 → 機櫃光纖 → 遠端`
接收（下排，**箭頭反向**）：`遠端 → … → FAU → 邊緣耦合器 → Ge 光偵測器 → TIA → ASIC`
- 每一站下方標「**在哪個零件裡**」（EIC／PIC／FAU／面板），**驅動器與 TIA 標 EIC、調變器與光偵測器標 PIC**（同 §2-D D2）。
- 線色：光＝`--dg-sw-fiber`，電＝`--dg-sig`；一張圖一個主色（`--dg-accent-2d`），其餘灰階。

### 4-C B2　供應鏈分道（★ 這一段跟 Andy 給的線性順序不同，原因如下）

Andy 給的順序是「雷射 → PIC 製造 → EIC 設計 → 3D 堆疊與封裝 → 光學耦合 → 測試 → 交換器整機 → 機櫃光纖佈線」。
**物理上雷射不進光引擎封裝**（§0-B#1），它在**系統整機**才與光引擎相遇。若畫成單一直線，會暗示「雷射先進了 PIC」，**結構錯誤**。
所以畫成三條並行的道，**所有項目與順序都保留，只改連法**：

| 道 | 由左到右（寫死） | 在哪相遇 |
|---|---|---|
| **道 1 光源線** | `① InP 磊晶（optical_epi）→ ② 雷射晶粒（optical_epi）→ ③ ELS／ELSFP 模組（optical）` | 在**交換器整機**（面板插入），**不**進封裝 |
| **道 2 光引擎線（主線）** | `④ PIC 製造（foundry）＋ ⑤ EIC 設計（ic_design）→ ⑥ 3D 堆疊 SoIC（adv_pkg）→ ⑦ 光學耦合 FAU／對準（optical）→ ⑧ 光引擎測試 → ⑨ 與 ASIC 共封裝（載板：abf_pcb）` | ⑤ 與 ④ 在 ⑥ 匯合（兩顆晶片疊起來） |
| **道 3 交換 ASIC 線** | `⑩ ASIC 設計（ic_design，外商）→ ⑪ 晶圓製造（foundry）` | 與道 2 在 ⑨ 共封裝處匯合 |
| **匯合後（單線）** | `⑫ 交換器整機（switch）→ ⑬ 機櫃光纖佈線（optical／connector，待調查）→ 雲端業者（hyperscaler，終端需求）` | |

- **測試（⑧）畫成貫穿道 2 的一條橫帶**，標三個測試點（示意）：**晶圓級光電測試**（PIC 晶圓切割前，探針卡＋光纖對準，段落 `test_interface`）→ **光引擎測試**（FAU 接上後）→ **整機測試**（`osat_test`／`switch`）。
  設備端「主動對準」依 SWTest 2026 摘要為壓電定位器＋探針卡整合（§7-A6），**掛哪個 `data-seg` 待調查**（若無對應則標「台股無直接對應」）。
- **方向規則**：所有箭頭 **上游 → 下游**（錢與貨的方向）。「代工／委外」類的邊方向看 `supply_chain.yaml` 的 `rel`，**不得為了好看反向**（2026-09-19 圖十的教訓）。
- 每個節點寫**段落名**，公司名稱稍後調查補進；節點旁小標「時程」若引用 YAML note（例：FAU 2026Q3 才微量貢獻、2027 才放量），**照 YAML 寫，不得升級成現在式**。

### 4-D B3　四種架構對照（★ 四欄用「同一把尺」，欄序由左到右＝光離 ASIC 由遠到近）

欄序固定：**可插拔（DSP）→ LPO → NPO → CPO**。

| 列 | 可插拔（DSP） | LPO（線性可插拔） | NPO（近封裝光學） | CPO（共封裝光學） |
|---|---|---|---|---|
| **光在哪** | 前面板的可插拔模組 | 前面板的可插拔模組（同左，**拿掉模組內 DSP**，由 ASIC SerDes 補償） | **板上、ASIC 旁**的獨立光引擎（可拆、可更換） | **同一顆封裝／同一片載板**上，與 ASIC 共封裝 |
| **ASIC→光 電氣路徑** | 長：載板 → PCB 走線 → 面板籠（**公分～數十公分，量級示意**） | 同左（**位置不變**，省的是 DSP 不是距離） | **公分級**（來源：NPO 定義摘要，§7-A5） | **毫米級**（來源：CPO 摘要，§7-A3） |
| **功耗（口徑不同，見下）** | 800G 模組約 12–16 W ≈ **15–20 pJ/bit**（廠商引述，§7-A3） | 800G 約 4–8 W ≈ **5–10 pJ/bit**（模組級，Semtech 摘要，§7-A5） | **介於 LPO 與 CPO 之間（定性）**；**未取得獨立數字，不畫數字** | 約 **5–10 pJ/bit**（廠商宣稱 Broadcom：比可插拔低 70%）|
| **維修／更換** | 前面板直接抽換 | 同左 | 單一光引擎可換（失效影響一顆） | 光引擎在封裝內，**難換**（外置雷射 ELSFP 可前面板換） |
| **量產時程（目標，非保證）** | 現行主流 | 小量、部分採用，**未全面取代 DSP**（2026 業界摘要） | 過渡方案、標準推進中（2026） | 平台已交付客戶（Broadcom 2024-03）、NVIDIA 光子交換器 2025H2／2026H2 為**目標**；**大量導入預期 2027 前後**（YAML 對 FAU／ELSFP 的描述） |

**畫面規矩（物理與誠實性，缺一就退回）**
1. 功耗列用**區間條（range bar）**，不畫單點；**LPO 與 CPO 的區間在 5–10 pJ/bit 重疊要畫成重疊**，不得畫成「CPO 明顯更低」。
2. 功耗列下方固定一行：「**口徑不同：可插拔／LPO 為模組級，CPO 為廠商系統級宣稱；非同基準比較，數字僅示意量級**」。
3. **不採用**「NPO 約 1 pJ/bit」（單一廠商宣稱，且摘要自己標需查證）與「LPO 約 1 pJ/bit」（Adtran 單一產品，非產業典型）。
4. 距離列用一條**示意比例尺**（不標精確公分），只呈現「遠 → 近」的順序；順序不可亂。
5. 時程列每一格都帶「目標」或「預期」字樣，**不寫「已量產」除非來源明說**（可插拔例外）。
6. 底部固定：「**CPO 的優勢是省電與高密度，代價是維修與散熱；技術路線仍在演進，各家方案不同。**」

---

## 5. 一定要有的識別特徵（看到什麼才認得出）

- **A**：交換 ASIC 居中、**一圈光引擎**；每顆引擎能看出「**上小下大、兩層**」（EIC 疊在 PIC 上）；**玻璃 FAU 塊接在引擎外緣、細光纖向外**；
  前面板有一支**單獨的外置雷射模組**，用**不同標記的光纖**連回；**冷板只壓在 ASIC 上**。
- **PIC 放大格**：看得出**蛇行／直線波導、調變器的並行臂（MZM）或環（MRM）、鍺光偵測器的小方塊、邊緣的錐形耦合器**，而不是一堆方塊。
- **混合鍵合**：兩層之間是**一條界線**（銅墊虛線陣列），不是圓點。
- **B**：三條並行供應鏈道匯合；四欄架構由遠到近；功耗是區間條。

### 5-B 最常見的畫錯（逐條對應 §6）

1. 把雷射畫進光引擎或載板上（對應 L1）。
2. EIC 畫在 PIC 下面或並排（S2）。
3. 光纖朝上、朝向 ASIC 或穿過散熱蓋（F1、F2）。
4. 冷板蓋滿整顆封裝包括光引擎與 FAU（S5、F3）。
5. 箭頭方向：CW 光畫成從 PIC 出去、或雷射端有接收箭頭（L2）。
6. 單線把「雷射」放在 PIC 前面（T1）。
7. 功耗用單點、CPO 畫得比 LPO 低很多（C1、C2）。
8. 把 NPO 畫成可插拔或跟 CPO 同位置（C3）。
9. 用了真實公司的產品外觀（M5）。

---

## 6. 結構審查清單（`mechanical-engineer` 逐條驗；★★★＝不過就退回、不進二輪）

**S 組・堆疊（圖 A 剖面與 3D）**
- S1 ★★★ 由下到上 `主板 → BGA → 載板 → C4 → 晶粒` 順序正確（D1）。
- S2 ★★★ **EIC 在 PIC 上方**；兩者之間是混合鍵合（一條界線），無凸塊（D1）。
- S3 ★★ ASIC 與光引擎**並排在同一載板**，高度基準一致；OE 不疊在 ASIC 上。
- S4 ★ ASIC 是全封裝面積最大、最厚的晶粒；每顆 OE 面積明顯小於 ASIC。
- S5 ★★★ **冷板／TIM1 只壓在 ASIC 上**；OE 頂面不高於 ASIC 頂面；冷板對 OE 與 FAU 邊讓開。
- S6 ★ 載板是平面上最大的封裝件；補強環圍邊、不碰晶粒、不蓋光纖出口。

**L 組・光與電的方向**
- L1 ★★★ **雷射（ELSFP）不在載板或光引擎上**，在前面板；有 PM 光纖連回（§0-B#1）。
- L2 ★★★ CW 光箭頭**指向 PIC**；資料光與 CW 光為兩種不同的線；雷射端無接收箭頭（D2）。
- L3 ★★ 驅動器與 TIA 標在 EIC、調變器與 Ge PD 標在 PIC（D2）。
- L4 ★ TX 與 RX 箭頭反向，且 RX 末端是 ASIC。
- L5 ★ ASIC↔EIC 的電連線畫得**短**（毫米級），遠短於 ASIC 到前面板的距離。

**F 組・光纖與面板**
- F1 ★★★ FAU 在 PIC 的**外緣（遠離 ASIC 側）**；光纖**水平向外**，不朝上、不朝 ASIC。
- F2 ★★ 光纖在封裝外才彎向面板，不穿過冷板／蓋（或有明確讓位）。
- F3 ★★ 耦合邊上方**沒有** EIC、蓋或 TIM（露出）。
- F4 ★ 面板上的光纖終端是連接器（非可插拔收發模組）；ELSFP 與之不同。

**P 組・PIC 放大格**
- P1 ★★ 波導、調變器、Ge PD、耦合器四件都畫出且順序符合光路（TX：輸入耦合器 → 分光 → 調變器 → 輸出；RX：耦合器 → Ge PD）。
- P2 ★ 調變器電極與 Ge PD 接點朝**上**（面對 EIC）；TSV 往下（示意已標）。
- P3 ★ 波導比 FAU 光纖**細很多**（耦合器有錐形放大），不可畫成同粗。

**T 組・供應鏈（圖 B）**
- T1 ★★★ **雷射線不進 PIC／封裝**，與光引擎線在**交換器整機**才相遇（§4-C）。
- T2 ★★★ 每條邊兩端是真上下游，方向無反（每條邊對照 `supply_chain.yaml` 的 `rel`）。
- T3 ★★ Andy 指定的八段全部出現且順序在各自的道內正確：雷射（磊晶→晶粒→ELS）→ PIC → EIC → 3D 堆疊 → 耦合 → 測試 → 整機 → 機櫃佈線。
- T4 ★ 測試是橫帶，有晶圓級／光引擎／整機三點。
- T5 ★ 每個節點只寫段落名；若引用 YAML 時程（FAU 2027 放量等），未升級成現在式。

**C 組・架構對照（圖 B）**
- C1 ★★★ 欄序 `可插拔 → LPO → NPO → CPO`，光離 ASIC 由遠到近。
- C2 ★★★ 功耗為區間條，LPO 與 CPO 重疊處畫成重疊；有「口徑不同」那一行。
- C3 ★★ NPO 光引擎在**板上**、可拆；CPO 在**封裝內**；可插拔與 LPO 在**面板**（位置圖示分得開）。
- C4 ★★ 沒有採用 §4-D 規矩 3 禁用的兩個數字。
- C5 ★ 時程列都帶「目標／預期」。

**M 組・範圍**
- M1 圖上沒有三種 CoWoS 中介層對照（那是 `ic_package`）。
- M2 圖上沒有可插拔模組籠內部、金手指（那是 `connector_hsio`）。
- M3 圖上沒有 PIC 製程細節（光罩層數、蝕刻步驟）。
- M4 圖上沒有任何**良率、市占、單價、產能、成本倍數**數字。
- M5 ★★ 沒有任何真實公司的 logo、產品外觀、包裝、商標；晶粒版圖為通用示意。

**Ho 組・誠實性**
- Ho1 §2-E 的四行聲明全部在畫面上。
- Ho2 帶年份的敘述（COUPE 65nm、Bailly 8 顆、2026 時程）都附「來源：…，年份」。
- Ho3 §6 所列不確定項（U1～U6）在畫面上都標「示意」或有退路，沒有寫成確定敘述。
- Ho4 Davisson 102.4T、NVIDIA 四 ASIC×六 OSA×三引擎等**單一來源**說法，畫面上**沒有**（§7-C）。

**R 組・3D 專屬**（引用 `dg3d_standard` §3）
- R1 轉得動、可平移、360 度含底部；點零件選起來且標籤同步；個股晶片可跳個股頁。
- R2 動態／靜止切換鈕有效，靜止時走線與光纖仍看得見。
- R3 爆炸：FAU／光纖水平向外、ELSFP 獨立，Z 軸拉開順序同 D4；收攏位移為 0。
- R4 ≤150,000 三角形、≤300 draw call；頁面切走停 rAF。

---

## 7. 查得到 ／ 要降信心 ／ 查不到

> **證據強度**：只有 `WebSearch`（`WebFetch` 擋住），下面每條都是**摘要**，沒有人讀過原文。

### A. 查得到來源的（可以寫進畫面，帶「來源：…，年份」）

| # | 事實 | 信心 | 來源 |
|---|---|---|---|
| A1 | 台積電 COUPE 把 EIC 以 SoIC-X 疊在 PIC 上（EIC-on-PIC）；EIC 為 65 奈米級；第一階段 1.6 Tbps 用於 OSFP 模組、第二階段「on substrate」與 CoWoS 共封裝、與交換 ASIC 共封，達 6.4 Tbps；第三階段 12.8 Tbps 為探索中 | 中高（多篇一致） | <https://www.datacenterdynamics.com/en/news/tsmc-partners-with-ansys-synopsys-and-cadence-to-boost-silicon-photonics-program>、<https://www.tomshardware.com/tech-industry/artificial-intelligence/co-packaged-optics-cpo-foundry-roadmaps-breaking-down-tsmc-intel-samsung-and-globalfoundries-approach-to-next-generation-scale-up-connectivity>、<https://technews.tw/2026/03/17/silicon-photonics-hits-the-market-tsmc-and-ase-spearhead-taiwans-strategic-push/> |
| A2 | Broadcom Bailly：Tomahawk 5（51.2T）共封裝**八顆 6.4T 矽光子光引擎**；4RU、128 埠 400G FR4、經 128 個雙工 LC 光連接器對外光纖耦合；系統設計相容多個遠端雷射模組（RLM）供現場更換；2024-03 交付客戶；宣稱光互連比可插拔**功耗低 70%**、矽面積效率 8 倍（廠商數字） | 高（原廠新聞稿，多處轉載） | <https://www.globenewswire.com/news-release/2024/03/14/2846314/19933/en/Broadcom-Delivers-Industry-s-First-51-2-Tbps-Co-Packaged-Optics-Ethernet-Switch-Platform-for-Scalable-AI-Systems.html>、<https://www.electronicdesign.com/technologies/embedded/article/21263811/electronic-design-broadcom-upgrades-co-packaged-optics-switch-to-512-tb-s> |
| A3 | 可插拔模組約 15–20 pJ/bit；CPO 約 5–10 pJ/bit，來自超短（毫米級）電氣路徑；800G 模組功耗 12–16 W | 中（引用廠商數字，來源間有出入） | <https://www.naddod.com/es/blog/cpo-optical-interconnects-in-ai-data-centers>、<https://www.senko.com/cpo-vs-pluggables-performance-power-and-scalability-benchmarking-in-the-800g-3-2t-era/> |
| A4 | ELSFP 是 OIF 為 CPO 定義的外置雷射形式，插前面板、與 ASIC 熱環境分離、以 IEC 60825-2 Hazard Level 1（眼睛安全）為目標；光經**保偏（PM）光纖**送出；單模組可供多條光纖（廠商產品例：8 條各 >100 mW；Molex 連接器最多 12 芯） | 中（廠商資料，未讀 OIF 規格原文） | <https://www.senko.com/?p=25566>、<https://www.molex.com/en-us/products/optical-solutions/elsfp-interconnect-system?>、<https://www.semiconductor-today.com/news_items/2023/mar/casela-030323.shtml> |
| A5 | LPO 拿掉模組內 DSP（DSP 占模組功耗 >40%，單一來源），800G 約 4–8 W vs DSP 12–16 W（Semtech）；NPO＝光引擎為板上獨立可拆單元，電氣路徑縮到公分級，是 pluggable 與 CPO 之間的過渡；CPO＝光學與 ASIC 在同一基板／封裝 | 中 | <https://blog.semtech.com/webinar-recap-linear-pluggable-optics-the-low-power-optical-interconnects-for-ai-and-hyperscaler-data-centers>、<https://www.tomshardware.com/tech-industry/near-packaged-optics-gains-ground-aso-the-industry-hedges-against-co-packaged-optics-growing-pains>、<https://www.wevolver.com/article/what-is-co-packaged-optics-architecture-benefits-challenges-and-performance> |
| A6 | 光耦合對次微米級位移極敏感，晶圓級光電測試需 FAU 主動對準；探針卡可整合壓電定位器（SWTest 2026：150 nm 精度）；台廠有光纖陣列探針卡與薄膜探針卡開發 | 中 | <https://www.swtest.org/library/2026proc/pdf/M01_04_OHYAMA_SWTest-2026.pdf>、<https://physikinstrumente.com/en/expertise/future-zone/electro-optical-wafer-probing>、<https://www.taiwannews.com.tw/news/6439046> |
| A7 | NVIDIA 光子交換器：Quantum-X 2025 下半年、Spectrum-X Photonics 2026 下半年為**目標**；採微環調變器（MRM）而非 MZM；基於台積電 SoIC | 中低（出貨未確認，日期互相不一致） | <https://trendforce.com/news/2025/03/19/news-nvidia-teams-up-with-tsmc-for-silicon-photonics-switches-expected-in-2025-26>、<https://naddod.com/blog/nvidia-s-silicon-photonics-cpo-the-beginning-of-a-transformative-journey-in-ai> |

### B. 有依據但要降信心，畫面上要留退路

- **B1 SOI 頂矽厚度約 220 nm、波導截面約數百奈米**：業界常識級，**本次未逐條查證**；畫面不標數字，只畫「波導遠細於光纖」。
- **B2 調變器種類**：Broadcom/TSMC 多為 MZM 類，NVIDIA 為 MRM（A7）。畫面擇一示意，旁註「另一種亦存在」。
- **B3 時程**：A1 的 2026 年 CPO 量產「目標」、A7 的出貨日期、YAML 的「2027 才放量」彼此不完全一致 → 畫面只寫「預期 2027 前後大量導入」並標「目標」，不寫年份精確值。
- **B4 DSP 占功耗 >40%**：單一來源（A5）→ 不上畫面，或標「約」。

### C. 查不到、或來源打架的（一律標示意、不准編數字，且不進畫面）

- C1 Broadcom Tomahawk 6 **Davisson 102.4T** 採 COUPE（僅一篇中文報導，未驗證）→ 不上畫面。
- C2 NVIDIA Quantum-X「四顆 ASIC、每顆六個光子次組件、每組三顆引擎」（僅一篇韓文部落格）→ 不上畫面。
- C3 光引擎**實際排法**（四邊各幾顆）、單顆尺寸、載板尺寸、各層厚度、凸塊節距、FAU 光纖節距與芯數 → 一律示意。
- C4 NPO 的 pJ/bit、LPO/CPO 同基準對照 → **查無獨立數字**，不畫。
- C5 良率、產能、市占、單價 → 不畫（M4）。
- C6 「主動對準設備」台股對應 → 待調查。

### D. 與 `supply_chain.yaml` 的對照（只引段落與既有 note，不新增角色描述）

- `optical_epi`（光通訊磊晶／雷射晶粒）、`optical`（光通訊模組／矽光子：含光收發模組、FAU、光纖套件、CPO 光引擎／ELSFP）、`switch`、`foundry`、`ic_design`、`adv_pkg`、`abf_pcb`、`substrate_material`、`test_interface`、`osat_test`、`thermal`、`hdi_pcb`、`connector`、`hyperscaler`。
- YAML 既有時程提醒（照抄，不升級）：FAU 2026Q3 微量貢獻、2027 才放量；ELSFP「量產準備中，2026–2027 才是第一波大量導入」；光纖套件「2026 量產、2026Q4 才放量」。
- 邊的方向範例（B2 畫邊時對照）：`lpc → luxnet`（`outsources_to`，**錢是聯亞付給華星光，方向跟直覺相反**，且為推論，confidence: estimated）；`foci → tsmc`（FAU 供應台積電 COUPE）；`pcl → broadcom`（CPO 光引擎／ELSFP）。

### E. 來源給 ic_package 共用的事實（引用，不重查）

- E1 C4 節距 150–200 µm、µbump 40–55 µm（`ic_package.md` §3D-細節 E1）。

### F. 已知不確定的地方（畫面上對應都標「示意圖，非實物比例」）

- **U1** PIC 內是否有 TSV、電訊號是否經 PIC 往下到載板（COUPE-on-substrate 的接法有不同說法）→ 標示意；若實作者另有可靠來源，改規格書重簽。
- **U2** 載板直接共封（Broadcom 式）或經 CoWoS 中介層（TSMC 式）→ 畫面擇一（建議載板直接共封，較簡單），旁註「亦有採中介層方案」。
- **U3** 冷板對光引擎的讓位形狀、是否有分區冷板 → 示意。
- **U4** 光引擎顆數與排列。
- **U5** 一個 ELSFP 供幾顆引擎、幾條 PM 光纖。
- **U6** 面板上光纖連接器種類（LC／MPO）→ 畫面寫「光纖連接器」，不指定型號。

---

## 8. 驗收條件

- **結構**（`mechanical-engineer` 簽）：照 §6 的 S／L／F／P／T／C／M／Ho／R 逐條給「過／不過＋理由」，不過者寫「錯在哪、應該是什麼」。
- **視覺**（`art-director` 簽）：字級全圖 ≥ 12px（量**畫面真實字級**，1440／1100／900／800／390 五個寬度）；深淺主題 × 各配色；一張圖一個主色；
  發光只給被選零件；文字不重疊、不出畫布；卡片在兩側欄不壓圖；**`ai_server` 鏈原有 7 張回頭重量**。
- **互動**（`_uitest.py` 真的操作）：點零件亮卡片、點卡片亮零件、點背景恢復、只亮不篩；
  依序點掛 `optical`／`foundry`／`abf_pcb` 的零件，成分股筆數**彼此不同**；點掛 `adv_pkg` 的零件（可能 0 家）畫面有說明行；
  動畫開關有效；章節開合；800px 不溢出。3D 另依 R 組。
- **效能**：不新增函式庫／CDN；一個 rAF，切走停。
- **不畫**任何真實公司的產品外觀、logo、包裝、商標。

---

## 9. 給 `tech-illustrator` 的實作邊界

- **先畫 B3 對照與 A 的 Z2 剖面**，先確認 800px 下「光離 ASIC 遠近」與「EIC 在 PIC 上」仍讀得出來，再畫其他。
- 光引擎用**同一個繪製函式**，換參數即可畫 8 顆（俯視）；EIC 比 PIC 小、PIC 外緣側伸出，這一個比例決定耦合邊是否露出（S5、F3）。
- 混合鍵合**不要用 `circle`**（會被讀成凸塊），用一排短矩形銅墊對銅墊。
- 光纖用 `m-fib` 沿既有慣例；PM 光纖與資料光纖**用不同線型**（虛線 vs 實線）。
- 功耗區間條用同一把尺（log 或分段，標在尺上）；LPO、CPO 區間重疊處用半透明疊色。
- 顏色一律 `--dg-*`，不寫死 `#xxxxxx`。`data-part` 一律要寫。
- 動畫只做兩件事：**CW 光由 ELSFP 進 PIC**、**調變後資料光由 PIC 出 FAU**。不要讓層跑來跑去。

---

## 審查紀錄

| 日期 | 審查者 | 過／不過 | 意見 |
|---|---|---|---|
| 2026-10-24 | mechanical-engineer（規格書作者） | 待簽 | **三件事要先拍板**：① §0-C 兩張圖掛哪兩個族群（`silicon_photonics`＋`optical_module`）與 `ai_server` 鏈晶片列是否換行；② B2 的**供應鏈三條道**取代 Andy 的線性順序（雷射不進封裝，線性畫法會結構錯誤）；③ 7 條不確定（U1～U6、C1～C6）已列明，實作遇到想補細節時**改規格書重簽，不要自行編**。證據全為 WebSearch 摘要。 |
| | art-director | | |
