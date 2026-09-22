/* 產品剖析圖的「真 3D」版本（Three.js）。

   Andy 要「圖片需要改成具備長寬高概念，並非 2D 平面」，而且拍板先試 Three.js。
   四條硬性驗收（做不到就退回 SVG 等角圖，不要硬上）：
     1. 可以繞著機櫃轉                      → OrbitControls
     2. 點零件仍然亮起並帶出台股清單         → Raycaster，事件接回 industry.js 原本那條路
     3. 文字標籤用 DOM 疊上去               → 自己排版的 DOM 層（_preview.py 的文字重疊檢查才還能跑）
     4. WebGL 不能用就自動退回現有 SVG      → supported() 先問，問不到就不掛

   2026-09-18 第 3 批（Andy 的 E1〜E4）在這個檔案落地：
     E1 文字太小 → **引線 ＋ 外部文字框**：標籤不再貼在零件頭上，改成排在畫面左右兩欄
        （字 12.5px、加一行說明），用引線接回零件。排版與避讓自己算（layoutLabels）。
     E2 螢光感太重 → 底層 emissive 一律 0、金屬度降到 0.22、拿掉青色 rim light，
        高亮改用「其餘變透明 ＋ 選中的稍微提亮」而不是整顆發光。只有指示燈才准發光。
     E3 零件更細膩 → 每個零件不再是一顆方塊：PARTS 裡一個 kind 一支建造函式
        （風扇有扇片、電池有電芯與端子與電量燈、PSU 有進氣孔、HBM 有層與 TSV、BGA 是球）。
     E4 動態／靜止 → setAnim()：動態＝緩慢自轉＋風扇轉＋指示燈呼吸；靜止＝完全不自己動。
        使用者一拖曳就先停自轉，放開兩秒半後才接回去（不然會跟他搶）。

   其他刻意的設計：
   - three.js 是**動態 import**，只有真的切到 3D 才付那 670KB；平面圖使用者完全不用載。
   - 函式庫內建在 site/vendor/（Andy 公司網路擋 CDN），OrbitControls 的 `from 'three'`
     已改成相對路徑，所以不需要 import map。
   - 場景是「資料」不是「程式」：SCENES 裡一個零件一列，之後要補別條產業鏈是加資料。
   - 捲出畫面或分頁切走就停 requestAnimationFrame，不讓它在背景空轉。 */
(function (global) {
  'use strict';

  // 動態 import 一定要用 './'：沒有前綴會被當成 bare specifier，直接 resolve 失敗
  const V = './vendor/';
  let mods = null;                 // 動態 import 的結果，載一次就好

  function supported() {
    try {
      const c = document.createElement('canvas');
      return !!(window.WebGLRenderingContext
        && (c.getContext('webgl2') || c.getContext('webgl') || c.getContext('experimental-webgl')));
    } catch (e) { return false; }
  }

  async function load() {
    if (mods) return mods;
    const [THREE, oc] = await Promise.all([
      import(V + 'three.module.min.js'),
      import(V + 'OrbitControls.js'),
    ]);
    mods = { THREE, OrbitControls: oc.OrbitControls };
    return mods;
  }

  /* ---------------------------------------------------------------- 場景資料
     單位：1 = 1 公分左右的感覺，機櫃高 42U 畫成 84。
     每個零件：{ seg, part, alias, name, note, kind, box:[w,h,d], at:[x,y,z], n:重複幾個, gap, axis }
     `part` ＝**零件身分**，對得上 2D 剖析圖那個零件的 `data-part`（site/diagrams.js）。
       兩層高亮靠它分辨「你剛剛點的是哪一個」，也靠它讓「2D 點完切到 3D」維持同一個狀態。
       沒寫就自動補 `seg#3d<idx>` —— 同一個場景裡夠用，但跟 2D 對不起來。
     `alias` ＝這一塊在 2D 上被拆成好幾塊時，那幾塊的 data-part（例如 MLCC 的端電極：
       2D 有消費級與車規兩張放大剖面，3D 只有一圈）。
     ★ n > 1 時 at 是**整排的中心**（程式會把整排對稱擺在 at 兩側），不是第一個的位置——
       寫成第一個的位置，整排就會整個偏出機櫃外面（第一版就是這樣，GPU 模組跑到機櫃左邊去了）。
     kind 決定用哪支建造函式（見下面的 PARTS）；沒寫就是一顆方塊。
     seg 對得上 supply_chain.yaml 的環節 id —— 點下去就能帶出該環節的台股。*/
  const SCENES = {
    ai_server: {
      title: 'AI 伺服器機櫃（NVL72 式）',
      sub: '18 個運算托盤 × 4 顆 GPU；後方是 NVLink 銅背板，前方是光模組，側邊是電源與液冷',
      camera: [86, 62, 96], target: [0, 34, 0], fit: 1,
      parts: [
        { seg: 'assembly', part: 'ag_rack', name: '機櫃與機構件', note: '19吋機櫃、滑軌、鈑金；整櫃出貨前做燒機與水路壓測',
          kind: 'rack', box: [52, 84, 40], at: [0, 42, 0], frame: true },
        { seg: 'switch', part: 'ag_backplane', name: 'NVLink 銅背板', note: '機櫃內把 72 顆 GPU 連成一台（scale-up）；走銅不走光',
          kind: 'backplane', box: [46, 52, 3], at: [0, 44, -17] },
        { seg: 'switch', part: 'ag_nvswitch', name: 'NVSwitch 托盤', note: 'NVLink 交換晶片，9 台夾在運算托盤之間',
          kind: 'tray', box: [44, 2.2, 30], at: [0, 62, 1], n: 3, gap: 6, axis: 'y' },
        { seg: 'adv_pkg', part: 'ag_gpu', name: '運算托盤 · GPU 模組', note: 'CoWoS-L 封裝：邏輯晶粒（SoIC 堆疊）＋ HBM 放在中介層上',
          kind: 'gpu', box: [9, 2.6, 9], at: [0, 34, 2], n: 4, gap: 10, axis: 'x' },
        { seg: 'foundry', part: 'ag_cpu', name: 'CPU（Grace / x86）', note: '與 GPU 同板 C2C 連接，負責排程與資料搬運',
          kind: 'chip', box: [7, 2, 7], at: [0, 34, -11], n: 2, gap: 34, axis: 'x' },
        { seg: 'hbm', part: 'ag_hbm', name: 'HBM4 記憶體', note: '12–16 層 DRAM 用 TSV 打通；base die 改用邏輯製程、由晶圓代工做',
          kind: 'hbm', box: [3, 3.2, 3], at: [0, 34.4, 9], n: 4, gap: 10, axis: 'x' },
        { seg: 'hdi_pcb', part: 'ag_pcb', name: '主機板 高階 PCB', note: '托盤底板，50 層以上 MLB／30 層以上 UBB（金像電）；IC 載板是另一個環節（欣興/南電/景碩），供應商完全不同',
          kind: 'pcb', box: [46, 1.2, 32], at: [0, 31, 0], n: 6, gap: 8, axis: 'y' },
        { seg: 'ccl', part: 'ag_ccl', name: 'CCL 銅箔基板', note: 'M8/M9 以上超低損耗板材，Df ≤ 0.002 @10GHz；PCB 的原料',
          kind: 'laminate', box: [46, 0.5, 32], at: [0, 30.2, 0] },
        { seg: 'thermal', part: 'ag_cdu', alias: ['ag_coldplate'], name: '液冷冷板 / CDU', note: '冷板貼晶片 → UQD 快接頭 → manifold 分歧管 → CDU → 機房一次側',
          kind: 'cdu', box: [4.5, 64, 4.5], at: [31, 38, 0] },
        { seg: 'thermal', part: 'ag_uqd', name: 'UQD 快接頭 / manifold', note: '漏液是 2026 年最被盯的品質風險；OCP 有規格',
          kind: 'uqd', box: [4, 3, 4], at: [24, 20, 12], n: 3, gap: 14, axis: 'y' },
        /* 2026-09-18 新增：Andy 舉的例子就是「風扇有扇片」。真的機櫃後門本來就有風扇牆，
           原本的場景整個漏掉這一段，等於把散熱只畫了液冷那一半。*/
        { seg: 'thermal', part: 'ag_fan', name: '後門風扇模組', note: '液冷之外仍要帶走記憶體與電源的熱；風扇牆掛在後門',
          kind: 'fan', box: [13, 13, 5], at: [0, 24, 19], n: 3, gap: 15, axis: 'x' },
        { seg: 'power', part: 'ag_psu', name: '電源櫃 PSU', note: '今天是 415V AC 進 PSU → 機櫃內 DC busbar；800V HVDC 是下一世代',
          kind: 'psu', box: [22, 5, 30], at: [0, 13, 0], n: 3, gap: 6, axis: 'y' },
        { seg: 'power', part: 'ag_bbu', name: 'BBU 電池 / 超級電容', note: '掉電到柴發接手之間撐住；超電處理 GPU 毫秒級功率突波',
          kind: 'battery', box: [18, 4, 26], at: [0, 4, 0] },
        { seg: 'optical', part: 'ag_optic', name: '光模組 / CPO', note: '800G–1.6T 前面板可插拔；CPO 把光引擎搬到交換 ASIC 旁',
          kind: 'optic', box: [2.4, 1.4, 8], at: [0, 72, 15], n: 8, gap: 4.4, axis: 'x' },
        { seg: 'switch', part: 'ag_tor', name: 'ToR 交換器', note: '跨機櫃那張網（scale-out）：InfiniBand 或 Ethernet',
          kind: 'switch', box: [46, 4, 30], at: [0, 76, 0] },
        { seg: 'hyperscaler', part: 'ag_csp', name: '雲端業者 / Neocloud', note: '終端需求：CSP、主權 AI、Neocloud',
          box: [26, 4, 18], at: [0, 90, 0], ghost: true },
      ],
    },
    /* CoWoS-L 先進封裝：這個場景 2026-09-22 起是 `ai_adv_packaging` 那張圖的 3D
       （DECISIONS #234 —— 鏈層級的 2D CoWoS 剖面退場，3D 跟著搬過來、而且要更細緻）。

       兩件事跟著改：
       ① **`part` 全部從 `sc_*` 改成 `icp_*`**，跟 2D 用同一組身分 ——
          `sc_*` 的另一個主人（鏈層級那張圖）沒了，對齊之後
          「2D 點完一個零件再切到 3D，還是同一個零件被選著」才成立。
       ② **接點自己要是一層**：以前載板直接貼著中介層、中介層直接貼著晶粒，
          中間那兩層接點（C4 與微凸塊）在 3D 上完全不存在 ——
          但整張 2D 的靈魂就是「接點由下往上一路變小」。
          現在用 `bump` 字彙補上，而且兩層的 box 高度刻意差一倍，轉過去看得出大小差。
       ③ Andy「他是電路圖就是要有電路圖的樣貌」→ 載板上補了**去耦電容**
          （`mlccchip`，端電極包住端部五個面），正面一排、背面一排。

       堆疊由下往上（y 是**中心**，不是底面）：
         BGA -0.4 ｜ 載板 0–3 ｜ C4 3.0–3.9 ｜ 中介層 3.9–5.5（矽橋埋在裡面）
         ｜ 微凸塊 5.5–6.2 ｜ 晶粒 6.2–8.6 ｜ SoIC 上層 8.6–10.4 ｜ HBM 6.2–11.6 ｜ 上蓋 11.5–13.7
       改任何一個 y 之前先回來對這一排，不然層會互相穿過去。*/
    semiconductor: {
      title: 'CoWoS-L 先進封裝（立體剖面）',
      sub: '由下往上：BGA → ABF 載板 → C4 → 有機重佈線＋LSI 矽橋 → 微凸塊 → 晶粒與 HBM → 上蓋；載板正反面都有去耦電容',
      camera: [50, 34, 52], target: [0, 7, 0], fit: 1, hk: 0.46,
      parts: [
        { seg: 'abf_pcb', part: 'icp_sub', name: 'ABF 載板', note: 'core ＋ 增層，雷射盲孔電鍍銅；把幾萬個接點扇出到主機板。表面看得到蛇行等長的走線',
          kind: 'substrate', box: [44, 3, 34], at: [0, 1.5, 0] },
        { seg: 'abf_pcb', part: 'icp_bga', name: 'BGA 錫球', note: '載板背面那一整片球，接到主機板；全圖最大的接點',
          kind: 'balls', box: [2, 1.6, 2], at: [0, -0.4, -12], n: 6, gap: 7.2, axis: 'x' },
        /* ★ 2026-09-22 新增：正面去耦電容。晶粒瞬間抽電時來不及等主機板，
           就近由載板上的電容頂著 —— 這是「板子上真的有被動元件」最基本的一件事。
           `mlccchip` 的識別特徵是端電極包住端部五個面，轉到背面看得到。*/
        { seg: 'passive_comp', part: 'icp_decap', name: '載板正面的去耦電容', note: '晶粒一瞬間抽大電流，等主機板送電來不及，由這排電容就近補；端電極包住端部五個面',
          kind: 'mlccchip', box: [2.6, 1.1, 1.5], at: [0, 3.55, 14.5], n: 6, gap: 4.4, axis: 'x',
          codes: ['2327', '2492', '3026', '6173'], chipnote: '做 MLCC 的那幾家（不在半導體鏈的環節名單上）' },
        { seg: 'passive_comp', part: 'icp_lsc', name: '背面去耦電容 LSC', note: '正面擺不下就往背面擺，夾在 BGA 球陣列中間；代價是那一塊的錫球要讓位',
          kind: 'mlccchip', box: [2.6, 1.0, 1.5], at: [0, -0.5, 6], n: 3, gap: 5.2, axis: 'x',
          codes: ['2327', '2492', '3026', '6173'], chipnote: '做 MLCC 的那幾家（不在半導體鏈的環節名單上）' },
        /* ★ 2026-09-22 新增：兩層接點。box 的高度 0.9 vs 0.55 刻意差一倍 ——
           2D 整張圖的靈魂就是「接點由下往上一路變小」，3D 不表達出來就等於少了一半。*/
        { seg: 'adv_pkg', part: 'icp_c4', name: 'C4 凸塊', note: '接「載板 ↔ 中介層」，節距 150–200 µm 級；迴焊之後塌成鼓形',
          kind: 'bump', box: [36, 0.9, 26], at: [0, 3.45, 0], codes: ['2330', '3711'] },
        { seg: 'adv_pkg', part: 'icp_interposer', alias: ['icp_rdl'], name: '中介層：有機重佈線（CoWoS-L）', note: '2026 主力是 L 不是 S：有機 RDL ＋ 局部矽橋，不是一整片矽中介層',
          kind: 'rdl', box: [36, 1.6, 26], at: [0, 4.7, 0], codes: ['2330', '3711'] },
        { seg: 'adv_pkg', part: 'icp_cowos_l', name: 'LSI 局部矽橋', note: '只埋在兩顆晶粒的交界正下方，負責 die-to-die 的高密度連線 —— 要高密度的地方才用到矽',
          kind: 'bridge', box: [6, 1, 10], at: [0, 5.1, 0], n: 2, gap: 12, axis: 'x', codes: ['2330', '3711'] },
        { seg: 'adv_pkg', part: 'icp_ubump', name: '微凸塊 µbump', note: '接「中介層 ↔ 晶粒」，銅柱＋錫帽，節距 30–60 µm 級 —— 比下面的 C4 小一個數量級',
          kind: 'bump', box: [30, 0.55, 22], at: [0, 5.85, 0], codes: ['2330', '3711'] },
        { seg: 'foundry', part: 'icp_die', name: 'GPU 晶粒（SoIC 堆疊）', note: '先 SoIC 混合鍵合疊兩顆（銅對銅、無凸塊），再進 CoWoS-L；四周那一圈空白是切割道',
          kind: 'die', box: [14, 2.4, 14], at: [0, 7.4, 0] },
        { seg: 'adv_pkg', part: 'icp_soic', name: 'SoIC 上層晶粒', note: '3D 堆疊的第二顆，銅墊直接對銅墊，中間沒有任何凸塊',
          kind: 'die', box: [12, 1.8, 12], at: [0, 9.5, 0], codes: ['2330', '3711'] },
        { seg: 'hbm', part: 'icp_hbm', name: 'HBM4 堆疊', note: '12–16 層 DRAM ＋ TSV ＋ base die（邏輯製程，台廠位置在這）；貼著晶粒放，線越短越省電',
          kind: 'hbm', box: [7, 5.4, 11], at: [0, 8.9, 0], n: 2, gap: 26, axis: 'x' },
        { seg: 'adv_pkg', part: 'icp_uf', name: 'Underfill / MUF', note: '底填膠，撐住凸塊並分散應力；側面會爬出一圈圓角。膠的材料以日商為主',
          box: [34, 0.8, 24], at: [0, 5.9, 0], ghost: true, codes: ['2330', '3711'] },
        { seg: 'adv_pkg', part: 'icp_stiff', name: 'Stiffener 補強環', note: '圍在載板邊緣的一圈金屬框，大尺寸封裝防翹曲',
          box: [44, 3.4, 3], at: [0, 4.7, 0], n: 2, gap: 31, axis: 'z', codes: ['2330', '3711'] },
        /* ★ 2026-09-21 更正：以前掛 `osat_test`，那是**封測服務廠**（日月光、力成、京元電、矽格…）。
           做探針卡與測試座的是 `test_interface`（6515 穎崴、6223 旺矽、6510 中華精測、6683 雍智）——
           **設備耗材 ≠ 封測服務**，這正是 AGENTS 半導體鏈那節第 3 條點名的錯。
           掛錯的後果不是「少列幾家」，是**點下去列出一批不做這個東西的公司**。 */
        { seg: 'test_interface', part: 'icp_probe', name: '探針卡 / 測試座', note: 'CP 晶圓測試與 FT 成品測試；AI 晶片測試時間長，是良率成本大宗',
          kind: 'probe', box: [10, 1.2, 10], at: [26, 2, 18] },
        { seg: 'osat_test', part: 'icp_lid', name: '散熱上蓋 + TIM', note: 'TIM1 在晶粒↔上蓋、TIM2 在上蓋↔冷板；上蓋的腳踩在載板邊緣',
          box: [40, 2.2, 30], at: [0, 12.6, 0], ghost: true },
      ],
    },
    /* 被動元件：MLCC 疊層（規格書 docs/diagram_specs/mlcc_stack.md）。
       規格書原本寫「不用真 3D，轉一圈只會看到一顆不透明的陶瓷方塊」——
       那句話對「完整的一顆」成立，對**切開近角的一顆**不成立：
         ① 端電極是「包住端部五個面的一段」，是不是真的包住五個面，只有轉過去看得到
         ② 側邊餘白是第三個方向上的事，2D 剖面畫不出來
       所以這裡做的是 cut-away 3D，切法跟 2D 那張完全一致（x>0 且 z>0 那一角挖掉），
       兩邊看到的是同一個剖面。轉到背面就是完整、沒被切開的一顆。 */
    mlcc: {
      title: 'MLCC 積層陶瓷電容（切開近角）',
      sub: '陶瓷疊層 ＋ 交錯指狀電極 ＋ 端電極 Cu → Ni → Sn；圖上 12 層為示意，實際 400～1000 層',
      camera: [64, 44, 72], target: [0, 18, 0], fit: 1, hk: 0.56,
      /* A5（mechanical-engineer 2026-09-21 複驗）：文字框底下那排台股改成列
         **「被動元件 MLCC」族群**（2327／2492／3026／6173），不是 passive_comp 環節。
         ⚠ 審查意見當時的理由有一半已經被 YAML 的更新推翻，所以這裡寫的是**現在的**理由：
           · 環節在 2026-09-21 已經補進 3026 禾伸堂與 6173 信昌電，所以「真正做 MLCC 的
             兩家在圖上完全不出現」那條**已經不成立**（那一條是 YAML 修掉的，不是這裡）。
           · 還成立的是這一條：環節現在有五家，而晶片只排得下四個 ——
             照 YAML 順序切前四家會**留下凱美、擠掉信昌電**，正好是最不該的那四家。
             而 supply_chain.yaml 自己寫「凱美**不做 MLCC**，是用電阻進到這一格的」，
             它被貼在「陶瓷本體與交錯電極／介電層 0.5–2 µm」這段說明正下方，就是在宣稱它做 MLCC。
         `data-seg` 一律保留 passive_comp（顏色連動、環節色標、篩選全靠它），YAML 一行都沒動。
         `chipnote` 是晶片上方那行小字，把「這排是哪一群」講白。
         第三個零件（PCB 焊墊）沒有 codes —— 它不是 MLCC 專屬的結構，照舊走環節名單。 */
      parts: [
        { seg: 'passive_comp', part: 'mlcc_body', name: '陶瓷本體與交錯電極', note: '介電層 0.5–2 µm、內電極鎳 Ni 約 0.5 µm；一端進、另一端留餘白，兩把梳子互插但不相碰',
          kind: 'mlcc', box: [62, 30, 30], at: [0, 22, 0],
          codes: ['2327', '2492', '3026', '6173'], chipnote: '「被動元件 MLCC」族群的台股' },
        { seg: 'passive_comp', part: 'mlcc_term', alias: ['mlcc_term_cons', 'mlcc_term_auto'], name: '端電極（Cu → Ni → Sn）', note: '銅膏約 800–900 °C 燒附 → 鍍 Ni 阻障 → 鍍 Sn 助焊；車規在 Cu 與 Ni 之間多一層導電樹脂（軟端子）',
          kind: 'mlccterm', box: [62, 30, 30], at: [0, 22, 0],
          codes: ['2327', '2492', '3026', '6173'], chipnote: '「被動元件 MLCC」族群的台股' },
        { seg: 'passive_comp', part: 'mlcc_pad', name: 'PCB 焊墊與焊錫', note: '板子受力 → 應力從焊點傳進陶瓷 → 板彎裂（flex crack）；車規靠軟端子擋這一刀',
          kind: 'mlccpad', box: [86, 4, 44], at: [0, 2, 0] },
      ],
    },
  };

  function hasScene(id) { return !!SCENES[id]; }

  /* ================================================================ E3：零件建造函式
     每支拿到 (T, p, K)：T 是 THREE、p 是零件資料、K 是這個零件專屬的材質工具箱。
     一律「畫在自己的局部座標、以 box 的中心為原點」，擺位交給外面統一處理。
     K.mat(明暗, 選項) 回傳材質：明暗 > 0 偏亮、< 0 偏暗，同一組參數會共用同一顆材質，
     highlight() 才有辦法一次把整個零件變透明。led:true 的是指示燈（E2 唯一准發光的東西）。 */
  function kit(THREE, hex, ghost, css) {
    const base = new THREE.Color(hex);
    const white = new THREE.Color(0xffffff), dark = new THREE.Color(0x070b14);
    const cache = {}, all = [];
    /* 這顆顏色字串是從哪一個 `--dg-*` 讀來的（cssv 登記、mat 取用）。
       為什麼需要：配色切換（applyPal）以前只改飽和與混色，材質的**原色**是建場景那一刻
       從 CSS 讀進來就固定了。休閒配色會換掉材質 token 本身（陶瓷、鋁、鋼、錫…），
       沒有這張對照表的話，「3D 開著的時候切到休閒」只會套到混色、原色還是冷的 ——
       使用者看到的就是「2D 暖、3D 冷」，正好是「不准兩份硬編碼」要防的那件事。*/
    const varOf = new Map();
    const col = (k) => { const c = base.clone(); return k > 0 ? c.lerp(white, k) : (k < 0 ? c.lerp(dark, -k) : c); };
    function mat(k, o) {
      o = o || {};
      const key = `${k}|${o.color || ''}|${o.rough || ''}|${o.metal || ''}|${o.op || ''}|${o.led ? 1 : 0}`;
      if (cache[key]) return cache[key];
      const m = new THREE.MeshStandardMaterial({
        color: o.color ? new THREE.Color(o.color) : col(k || 0),
        // E2：金屬度與粗糙度改成「實體塑膠／陽極鋁」的手感，不是會反青光的鏡面
        roughness: o.rough != null ? o.rough : (ghost ? 0.92 : 0.55),
        metalness: o.metal != null ? o.metal : (ghost ? 0.02 : 0.22),
        transparent: !!(ghost || o.op != null),
        opacity: ghost ? 0.14 : (o.op != null ? o.op : 1),
      });
      if (o.led) { m.emissive = new THREE.Color(o.color || 0x86f3b4); m.emissiveIntensity = 0.55; m.userData = { led: true }; }
      if (o.color && varOf.has(o.color)) m.userData = Object.assign(m.userData || {}, { dgvar: varOf.get(o.color) });
      cache[key] = m; all.push(m);
      return m;
    }
    // 邊線用的 LineBasicMaterial 不是從 mat() 來的，要自己登記，highlight 才吃得到它
    const reg = (m) => { all.push(m); return m; };
    /* B5／B6（art-director 2026-09-21）：**材質色一律讀 CSS 變數 `--dg-*`，JS 不寫死 #xxxxxx。**
       這一支讓零件建造函式拿得到那組變數 —— 以前 3D 的陶瓷是「把環節色 --c 調淡」，
       所以同一顆電容切到 3D 就從暖米白（42°）變成冷灰白，跟 2D 對不上，
       而且陶瓷與 Ni／Sn 全是灰白、畫面上分不出哪塊是陶瓷哪塊是金屬。
       讀不到（沒掛上 DOM、舊瀏覽器）就回 dflt，不要讓整個 3D 掛掉。*/
    const cssv = (name, dflt) => {
      let v = '';
      try { v = css ? css(name) : ''; } catch (e) { v = ''; }
      const out = v || dflt;
      if (out) varOf.set(out, name);       // 記下「這個色值來自哪一個 token」，換配色時才回得去重讀
      return out;
    };
    return { mat, col, reg, css: cssv, mats: all };
  }

  function mkBuilders(T) {
    const box = (w, h, d, m) => new T.Mesh(new T.BoxGeometry(w, h, d), m);
    const cyl = (r, h, m, seg) => new T.Mesh(new T.CylinderGeometry(r, r, h, seg || 14), m);
    const ball = (r, m) => new T.Mesh(new T.SphereGeometry(r, 12, 9), m);
    const put = (o, x, y, z) => { o.position.set(x || 0, y || 0, z || 0); return o; };
    const edge = (mesh, K, op) => {
      const e = new T.EdgesGeometry(mesh.geometry);
      mesh.add(new T.LineSegments(e, K.reg(new T.LineBasicMaterial({
        color: K.col(0.3), transparent: true, opacity: op == null ? 0.5 : op }))));
      return mesh;
    };

    /* ================================================================ 圖九 2-1
       走線 ／ PIN 腳 ／ 電流
       規格書：docs/diagram_specs/dg3d_standard.md 第 2-1 節。
       Andy 的判準是「一眼看得出這是電子零件」，所以三件事都有硬性的識別特徵：
         走線  —— 蛇行等長線、差動對成雙、轉角一律 45°、線寬一致（不是隨機亂畫的線）
         PIN 腳 —— BGA 成陣列且是球、金手指成排鍍金有倒角、電源端子看得出匯流排厚度
         電流  —— 沿著走線跑的粒子，只在動態模式時跑；靜止時走線本身仍然看得見
       走線的點一律用 [x, z] 的二維陣列表示（板子是平的），y 由呼叫端給。 */

    /* 蛇行等長線：直線 → 45° 斜上 → 直線 → 45° 斜下，一個循環。
       斜段的 dx 與 dz 相等才會是真的 45°，所以 amp 直接拿 span 來用。*/
    function meander(x0, x1, z, amp, cycles) {
      const pts = [[x0, z]];
      const span = (x1 - x0) / (cycles * 4);
      const a = Math.min(amp, Math.abs(span));           // 保證 45°
      for (let i = 0; i < cycles; i++) {
        const bx = x0 + i * span * 4;
        pts.push([bx + span, z]);
        pts.push([bx + span * 2, z + a]);
        pts.push([bx + span * 3, z + a]);
        pts.push([bx + span * 4, z]);
      }
      return pts;
    }

    /* 把一整層的走線**併成一個 mesh**：每一段一個貼在板面上的長方形（兩個三角形）。
       ★ 一段一個方塊會死人：一塊板 160 段、六塊板就是 960 個 draw call，
         實測整台機櫃從 483 個 mesh 暴增到 1846、frame rate 直接砍半（29.8 → 14.1 fps，
         容器裡的軟體渲染）。AGENTS.md 對繪圖寫的是「不准掉幀」，所以一層併成一個。
       線寬（wdt）整條一致 —— 寬度不一致一眼就看得出來不是真的走線；
       每段沿著方向各延長半個線寬，轉角才不會有缺口。*/
    function traceMesh(runs, wdt, y, m) {
      const pos = [], idx = [];
      let v = 0;
      runs.forEach(pts => {
        for (let i = 1; i < pts.length; i++) {
          const [x0, z0] = pts[i - 1], [x1, z1] = pts[i];
          const dx = x1 - x0, dz = z1 - z0, len = Math.hypot(dx, dz);
          if (len < 1e-6) continue;
          const ux = dx / len, uz = dz / len, hw = wdt * 0.5;
          const ax = x0 - ux * hw, az = z0 - uz * hw, bx = x1 + ux * hw, bz = z1 + uz * hw;
          const nx = -uz * hw, nz = ux * hw;
          pos.push(ax + nx, y, az + nz, bx + nx, y, bz + nz, bx - nx, y, bz - nz, ax - nx, y, az - nz);
          idx.push(v, v + 1, v + 2, v, v + 2, v + 3); v += 4;
        }
      });
      const g = new T.BufferGeometry();
      g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      const mesh = new T.Mesh(g, m);
      m.side = T.DoubleSide;        // 平的銅箔從底下看也要在
      return mesh;
    }

    /* 一塊板子的走線層：n 組**差動對**（成雙、間距固定、轉角 45°）。
       回傳的 group 上掛 userData.flows＝這些走線的路徑，電流粒子沿著它跑。*/
    function traceLayer(K, w, d, y, opt) {
      const o = opt || {};
      const g = new T.Group();
      const wdt = o.wdt || Math.min(w, d) * 0.012;
      const thk = o.thk || wdt * 0.6;
      const cu = K.mat(0.5, { metal: 0.72, rough: 0.28 });     // 銅
      const pairs = o.pairs || 4, cycles = o.cycles || 5;
      const flows = [];
      const x0 = -w * 0.44, x1 = w * 0.44;
      const amp = d * 0.05;
      const runs = [];
      for (let i = 0; i < pairs; i++) {
        const z = (-(pairs - 1) / 2 + i) * d * 0.17;
        [-1, 1].forEach(sgn => {                                // 差動對：兩條並排、間距固定
          const pts = meander(x0, x1, z + sgn * wdt * 1.9, amp, cycles);
          runs.push(pts);
          if (sgn > 0) flows.push({ pts, y, dir: o.dir || 1 });
        });
      }
      g.add(traceMesh(runs, wdt, y, cu));      // 整層一個 mesh，不是一段一個方塊
      /* 電流：沿著走線跑的粒子。粒子跟走線放在同一個 group，
         所以背板那種整層轉 90° 的情況不用另外換算座標。
         靜止模式時整個 Points 隱藏起來 —— 走線本身還在，看得見板子是有線路的。*/
      if (flows.length) {
        const paths = flows.map(f => f.pts.map(([px, pz]) => new T.Vector3(px, y + thk, pz)));
        const per = 6;
        const arr = new Float32Array(paths.length * per * 3);
        const geo = new T.BufferGeometry();
        geo.setAttribute('position', new T.BufferAttribute(arr, 3));
        const pm = K.reg(new T.PointsMaterial({
          size: wdt * 3.2, color: K.col(0.78), transparent: true, opacity: 0.92,
          depthWrite: false, sizeAttenuation: true }));
        const pt = new T.Points(geo, pm);
        pt.userData.flow = { paths, per, t: 0, dir: o.dir || 1, speed: o.speed || 0.2 };
        g.add(pt);
      }
      return { group: g, flows };
    }

    /* 金手指：成排、鍍金、前緣倒角。少了倒角看起來就只是一排小方塊。*/
    function fingers(K, w, h, d, n, y, z) {
      const g = new T.Group();
      // 2026-09-22：色值改讀 `--dg-sw-gold`（2D 那邊金手指用的就是它），
      // fallback 維持原本的 #d8b25a —— 讀不到變數時外觀一個像素都不變。
      const au = K.mat(0.62, { color: K.css('--dg-sw-gold', '#d8b25a'), metal: 0.85, rough: 0.22 });
      /* ★ 2026-09-22：從「一根手指兩個 Mesh」改成兩個 InstancedMesh。
         外觀完全一樣，但 14 根手指從 28 個 draw call 變成 2 個 ——
         主機板 ×6 ＋ 光模組 ×8 都用到它，省下來的是三位數。*/
      const at = [], at2 = [];
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * (w / n);
        at.push([x, y, z]);
        // 倒角：前緣壓一片更薄的，看起來就是「插得進去」的那種斜邊
        at2.push([x, y - h * 0.3, z + d * 0.62]);
      }
      g.add(instOf(new T.BoxGeometry(w / n * 0.55, h, d), au, at));
      g.add(instOf(new T.BoxGeometry(w / n * 0.55, h * 0.45, d * 0.35), au, at2));
      return g;
    }

    /* BGA 球陣列：n×n 顆真的球。三顆三顆的看起來像腳墊，不像 BGA。*/
    function ballGrid(K, pitch, r, n, y) {
      // n×n 顆球用 InstancedMesh：25 顆球一個 draw call。
      // 一顆一個 Mesh 的話，六塊板 ×25 顆就是 150 個 draw call，只為了畫錫球。
      const m = K.mat(0.35, { metal: 0.6, rough: 0.35 });
      const im = new T.InstancedMesh(new T.SphereGeometry(r, 8, 6), m, n * n);
      const mx = new T.Matrix4();
      let k = 0;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
        mx.makeTranslation((-(n - 1) / 2 + i) * pitch, y || 0, (-(n - 1) / 2 + j) * pitch);
        im.setMatrixAt(k++, mx);
      }
      im.instanceMatrix.needsUpdate = true;
      return im;
    }

    /* 方塊（沒指定 kind 時的預設）。透明件補一圈邊線，
       不然半透明色塊會糊成一片、把底下的晶粒洗掉。*/
    function plain(p, K) {
      const g = new T.Group();
      const m = box(p.box[0], p.box[1], p.box[2], K.mat(0));
      if (p.ghost) edge(m, K, 0.5);
      g.add(m);
      return g;
    }

    // 機櫃：只畫框（實心會把裡面全擋住），再補四根立柱與 U 位安裝孔
    function rack(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const gm = new T.BoxGeometry(w, h, d);
      g.add(new T.LineSegments(new T.EdgesGeometry(gm), K.reg(new T.LineBasicMaterial({
        color: K.col(0.1), transparent: true, opacity: 0.6 }))));
      gm.dispose();
      const post = K.mat(-0.25, { metal: 0.45, rough: 0.5 });
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) =>
        g.add(put(box(1.6, h, 1.6, post), sx * (w / 2 - 1), 0, sz * (d / 2 - 1))));
      // 機櫃前柱上的 U 位安裝孔：一眼看得出是 19 吋機櫃而不是一個箱子
      const holeM = K.mat(-0.5, { rough: 0.8, metal: 0.1 });
      for (let i = -6; i <= 6; i += 2) {
        [-1, 1].forEach(sx => g.add(put(box(0.5, 0.9, 0.5, holeM), sx * (w / 2 - 1), i * (h / 16), d / 2 - 1)));
      }
      return g;
    }

    // 背板：板子 ＋ 一排排高速連接器
    function backplane(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.15)));
      const cm = K.mat(0.25, { metal: 0.55, rough: 0.35 });
      /* 圖九 2-1：連接器不只是一個方塊，要看得出裡面成排的端子。
         ★ 2026-09-22：15 個連接器 × 4 個 Mesh ＝ 60 個 draw call → 收成 2 個 InstancedMesh。
           畫出來的東西一個像素都沒變，省下來的是 58 個 draw call。*/
      const body = [], term = [];
      for (let r = -1; r <= 1; r++) for (let c = -2; c <= 2; c++) {
        body.push([c * w * 0.18, r * h * 0.26, d * 0.35]);
        for (let k = -1; k <= 1; k++) term.push([c * w * 0.18 + k * w * 0.026, r * h * 0.26, d * 0.62]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.1, h * 0.14, d * 0.9), cm, body));
      g.add(instOf(new T.BoxGeometry(w * 0.01, h * 0.07, d * 0.5), K.mat(0.55, { metal: 0.8, rough: 0.25 }), term));
      // 背板是直立的：走線鋪在 x–y 平面上，所以先把走線層轉 90° 再貼上去
      const tl = traceLayer(K, w, h, 0, { pairs: 4, cycles: 6, dir: 1 });
      tl.group.rotation.x = -Math.PI / 2; tl.group.position.z = d * 0.52;
      g.add(tl.group);
      g.userData.flows = tl.flows.map(f => ({ ...f, rotX: -Math.PI / 2, offZ: d * 0.52 }));
      return g;
    }

    // 托盤／NVSwitch：底板 ＋ 中間一顆晶片 ＋ 散熱鰭片
    function tray(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h * 0.5, d, K.mat(-0.2, { metal: 0.4 })));
      g.add(put(box(w * 0.26, h * 0.7, d * 0.4, K.mat(0.1)), 0, h * 0.5, 0));
      const fin = K.mat(0.3, { metal: 0.5, rough: 0.4 });
      for (let i = -5; i <= 5; i++) g.add(put(box(w * 0.012, h * 1.1, d * 0.38, fin), i * w * 0.028, h * 0.8, 0));
      return g;
    }

    // GPU 模組：載板 ＋ 中介層 ＋ 晶粒 ＋ 兩側 HBM ＋ 上蓋開口
    function gpu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.3, d, K.mat(-0.3)), 0, -h * 0.35, 0));
      g.add(put(box(w * 0.8, h * 0.18, d * 0.8, K.mat(-0.05, { metal: 0.35 })), 0, -h * 0.11, 0));
      g.add(put(box(w * 0.4, h * 0.42, d * 0.5, K.mat(0.28, { metal: 0.4, rough: 0.4 })), 0, h * 0.2, 0));
      const hb = K.mat(0.05, { rough: 0.6 });
      [-1, 1].forEach(s => { for (let i = -1; i <= 1; i++) g.add(put(box(w * 0.11, h * 0.36, d * 0.2, hb), s * w * 0.3, h * 0.17, i * d * 0.24)); });
      return g;
    }

    // 一般晶片：載板 ＋ 金屬上蓋 ＋ 四周被動元件
    function chip(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.35, d, K.mat(-0.3)), 0, -h * 0.32, 0));
      g.add(put(box(w * 0.66, h * 0.5, d * 0.66, K.mat(0.3, { metal: 0.55, rough: 0.35 })), 0, h * 0.15, 0));
      const pas = K.mat(-0.15, { rough: 0.7 });
      for (let i = -2; i <= 2; i++) {
        g.add(put(box(w * 0.06, h * 0.16, d * 0.09, pas), i * w * 0.13, -h * 0.06, d * 0.4));
        g.add(put(box(w * 0.06, h * 0.16, d * 0.09, pas), i * w * 0.13, -h * 0.06, -d * 0.4));
      }
      return g;
    }

    /* HBM：一層一片真的疊起來（Andy 要的「更細膩」＝ 看得出它是堆疊的），
       再補四根 TSV 貫穿柱與下面那顆 base die。*/
    function hbm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const n = 6, lay = h / (n + 2.2);
      g.add(put(box(w, lay * 1.3, d, K.mat(-0.35, { rough: 0.5 })), 0, -h / 2 + lay * 0.65, 0));   // base die
      const dram = K.mat(0.05), gapM = K.mat(-0.45, { rough: 0.85 });
      for (let i = 0; i < n; i++) {
        const y = -h / 2 + lay * 1.5 + i * lay;
        g.add(put(box(w * 0.94, lay * 0.62, d * 0.94, dram), 0, y, 0));
        g.add(put(box(w * 0.9, lay * 0.2, d * 0.9, gapM), 0, y + lay * 0.4, 0));
      }
      const tsv = K.mat(0.45, { metal: 0.7, rough: 0.3 });
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) =>
        g.add(put(cyl(Math.min(w, d) * 0.045, h * 0.86, tsv, 8), sx * w * 0.3, 0, sz * d * 0.3)));
      return g;
    }

    /* 主機板：板子 ＋ 線路層 ＋ 幾顆 IC ＋ 插槽 ＋ 電容
       ★ 2026-09-22（第一層零件字彙）：補上**焊墊陣列／絲印／鍍通孔／金手指**。
         Andy：「他是電路圖就是要有電路圖的樣貌」。一塊只有走線的綠板子還是像板材，
         要有「零件焊在哪裡（焊墊）、零件叫什麼（絲印）、訊號怎麼換層（通孔）、
         怎麼插到別人身上（金手指）」才看得出它是一塊**設計過的板子**。
         全部走 instOf／mboxes，四樣加起來只多 4 個 draw call。*/
    function pcb(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.25, { rough: 0.72, metal: 0.08 })));
      const ic = K.mat(0.15, { rough: 0.5 });
      [[-0.3, -0.2], [0.18, 0.24], [0.34, -0.3]].forEach(([fx, fz]) =>
        g.add(put(box(w * 0.1, h * 1.5, d * 0.14, ic), fx * w, h, fz * d)));
      const slot = K.mat(0.3, { metal: 0.4, rough: 0.45 });
      for (let i = -1; i <= 1; i++) g.add(put(box(w * 0.34, h * 1.2, d * 0.045, slot), -w * 0.06, h * 0.9, i * d * 0.17));
      const cap = K.mat(-0.05, { rough: 0.6 });
      for (let i = 0; i < 6; i++) g.add(put(cyl(Math.min(w, d) * 0.014, h * 2.2, cap, 8), (-0.42 + i * 0.05) * w, h * 1.4, d * 0.4));
      // 圖九 2-1：板面的蛇行等長差動對。訊號方向＝由 GPU（板中）往背板（-x）
      const tl = traceLayer(K, w, d, h * 0.55, { pairs: 4, cycles: 5, dir: -1 });
      g.add(tl.group); g.userData.flows = tl.flows;
      // 焊墊：每顆 IC 底下一整片（表面處理鍍金）
      g.add(padField(K, w * 0.22, d * 0.3, h * 0.52, 6, 5));
      // 絲印：三顆 IC 的外框 ＋ 第 1 腳記號
      g.add(silk(K, w, d, h * 0.53, [[-0.3 * w, -0.2 * d, w * 0.13, d * 0.18],
        [0.18 * w, 0.24 * d, w * 0.13, d * 0.18], [0.34 * w, -0.3 * d, w * 0.13, d * 0.18]]));
      // 鍍通孔：換層用的直筒孔（跟載板的錐形微孔是兩種設備）
      g.add(pthRow(K, w, h, d, 14, -d * 0.4));
      // 金手指：板子前緣的插接區（OCP／PCIe 那種）。
      // ★ 貼在板面、往內縮一點 —— 掛在板緣外面會變成一排凸出來的牙齒，那不是金手指的樣子。
      g.add(fingers(K, w * 0.46, h * 0.5, d * 0.08, 14, h * 0.5, d * 0.4));
      return g;
    }

    // CCL：銅箔 / 玻纖 / 銅箔 三層壓合，一眼看得出它是「板材」不是一塊板子
    function laminate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.28, d, K.mat(0.42, { metal: 0.6, rough: 0.34 })), 0, h * 0.36, 0));
      g.add(box(w, h * 0.44, d, K.mat(-0.3, { rough: 0.85, metal: 0.05 })));
      g.add(put(box(w, h * 0.28, d, K.mat(0.42, { metal: 0.6, rough: 0.34 })), 0, -h * 0.36, 0));
      return g;
    }

    // CDU 立柱：機箱 ＋ 幫浦 ＋ 上下進出水管
    function cdu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.1, { metal: 0.35 })));
      const pump = K.mat(0.2, { metal: 0.5, rough: 0.4 });
      [-0.3, 0.1].forEach(fy => g.add(put(cyl(w * 0.42, h * 0.1, pump), 0, fy * h, 0)));
      const pipe = K.mat(0.3, { metal: 0.55, rough: 0.35 });
      [[0.42, 1], [-0.42, -1]].forEach(([fy, sx]) => {
        const t = put(cyl(w * 0.22, d * 2.4, pipe, 10), sx * w * 0.2, fy * h, -d * 1.0);
        t.rotation.x = Math.PI / 2; g.add(t);
      });
      g.add(put(box(w * 0.5, h * 0.03, d * 0.5, K.mat(0, { led: true })), 0, h * 0.46, d * 0.52));
      return g;
    }

    // UQD 快接頭：本體 ＋ 鎖環 ＋ 軟管
    function uqd(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const body = put(cyl(w * 0.42, h * 1.1, K.mat(0.2, { metal: 0.5, rough: 0.38 })), 0, 0, 0);
      body.rotation.z = Math.PI / 2; g.add(body);
      const ring = put(cyl(w * 0.55, h * 0.3, K.mat(0.45, { metal: 0.7, rough: 0.25 })), w * 0.3, 0, 0);
      ring.rotation.z = Math.PI / 2; g.add(ring);
      const hose = put(cyl(w * 0.24, d * 2.2, K.mat(-0.25, { rough: 0.85, metal: 0.05 })), -w * 0.9, 0, 0);
      hose.rotation.z = Math.PI / 2; g.add(hose);
      return g;
    }

    /* 風扇：Andy 點名的例子 ——「風扇有扇片」。
       外框 ＋ 輪轂 ＋ 七片有角度的扇片，扇片掛在自己的 Group 上，setAnim(true) 時整組轉。*/
    function fan(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2, open = r * 1.64;
      const fm = K.mat(-0.2, { rough: 0.7 });
      // 外框：四條邊，中間留空才看得到扇片
      const tb = (h - open) / 2, lr = (w - open) / 2;
      g.add(put(box(w, tb, d, fm), 0, (h - tb) / 2, 0));
      g.add(put(box(w, tb, d, fm), 0, -(h - tb) / 2, 0));
      g.add(put(box(lr, open, d, fm), -(w - lr) / 2, 0, 0));
      g.add(put(box(lr, open, d, fm), (w - lr) / 2, 0, 0));
      const rotor = new T.Group();
      const hub = cyl(r * 0.26, d * 0.8, K.mat(0.1, { metal: 0.45, rough: 0.4 }));
      hub.rotation.x = Math.PI / 2; rotor.add(hub);
      const bm = K.mat(0.25, { rough: 0.5 });
      for (let i = 0; i < 7; i++) {
        const b = box(r * 0.62, r * 0.36, d * 0.16, bm);
        b.position.set(Math.cos(i * Math.PI * 2 / 7) * r * 0.48, Math.sin(i * Math.PI * 2 / 7) * r * 0.48, 0);
        b.rotation.z = i * Math.PI * 2 / 7 + Math.PI / 2;
        b.rotation.y = 0.42;                      // 扇片的攻角：平的看起來像葉輪玩具
        rotor.add(b);
      }
      rotor.userData.spin = { axis: 'z', speed: 2.4 };
      g.add(rotor);
      return g;
    }

    // PSU：機殼 ＋ 進氣孔陣列 ＋ 把手 ＋ 電源指示燈
    function psu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.15, { metal: 0.35 })));
      const hole = K.mat(-0.6, { rough: 0.9, metal: 0.05 });
      // ★ 2026-09-22：18 個進氣孔收成一個 InstancedMesh（圓柱預設立著，要放倒才是面對前面板的孔）
      const holes = [];
      for (let i = -4; i <= 4; i++) for (let j = -1; j <= 1; j += 2) {
        holes.push([i * w * 0.08, j * h * 0.22, d / 2, Math.PI / 2, 0, 0]);
      }
      g.add(instOf(new T.CylinderGeometry(w * 0.02, w * 0.02, d * 0.06, 6), hole, holes));
      g.add(put(box(w * 0.26, h * 0.16, d * 0.05, K.mat(0.3, { metal: 0.5 })), -w * 0.3, 0, d / 2 + d * 0.02));
      g.add(put(box(w * 0.05, h * 0.16, d * 0.03, K.mat(0, { led: true })), w * 0.38, 0, d / 2 + d * 0.02));
      /* 圖九 2-1：PSU 後端的**直流匯流排端子**。這是電源件最好認的特徵 ——
         一整片厚銅排加上鎖螺絲的孔，跟訊號端子完全不是同一個量級。*/
      const busM = K.mat(0.5, { color: '#c98a3c', metal: 0.8, rough: 0.3 });
      const scr = [];
      [-1, 1].forEach(sy => {
        g.add(put(box(w * 0.3, h * 0.13, d * 0.05, busM), sy * w * 0.22, sy * h * 0.22, -d / 2 - d * 0.02));
        for (let i = -1; i <= 1; i++) scr.push([sy * w * 0.22 + i * w * 0.09, sy * h * 0.22, -d / 2 - d * 0.03, Math.PI / 2, 0, 0]);
      });
      g.add(instOf(new T.CylinderGeometry(w * 0.012, w * 0.012, d * 0.07, 6), K.mat(-0.5, { rough: 0.85, metal: 0.1 }), scr));
      return g;
    }

    /* BBU 電池：Andy 點名的例子 ——「電池有電壓感」。
       外殼做成**托盤**不是密閉箱子 —— 密閉的話電芯全被蓋住，做得再細也看不到。
       托盤 ＋ 一排圓柱電芯 ＋ 正負端子（銅色／深色）＋ 剩餘電量燈條（會呼吸）。*/
    function battery(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const shell = K.mat(-0.3, { rough: 0.75, metal: 0.12 });
      g.add(put(box(w, h * 0.2, d, shell), 0, -h * 0.4, 0));                                  // 底盤
      [-1, 1].forEach(s => g.add(put(box(w * 0.04, h * 0.62, d, shell), s * (w / 2 - w * 0.02), -h * 0.06, 0)));
      [-1, 1].forEach(s => g.add(put(box(w, h * 0.62, d * 0.03, shell), 0, -h * 0.06, s * (d / 2 - d * 0.015))));
      const cellM = K.mat(0.15, { metal: 0.45, rough: 0.42 });
      const cells3 = [];
      for (let i = -2; i <= 3; i++) for (let j = -1; j <= 1; j += 2) {
        cells3.push([(i - 0.5) * w * 0.15, h * 0.06, j * d * 0.24]);
      }
      g.add(instOf(new T.CylinderGeometry(w * 0.055, w * 0.055, h * 0.8, 10), cellM, cells3));
      // 端子：一正一負，正極用銅色、負極壓深，遠看就知道哪邊是哪邊
      g.add(put(box(w * 0.1, h * 0.5, d * 0.1, K.mat(0, { color: '#c98a3a', metal: 0.75, rough: 0.3 })), w * 0.4, h * 0.5, -d * 0.32));
      g.add(put(box(w * 0.1, h * 0.5, d * 0.1, K.mat(0, { color: '#2b3240', metal: 0.55, rough: 0.5 })), w * 0.4, h * 0.5, d * 0.32));
      // 電量燈條：四格，這是 E2 之後整個場景唯一准發光的東西
      for (let i = 0; i < 4; i++) {
        g.add(put(box(w * 0.055, h * 0.16, d * 0.02, K.mat(0, { led: true })), (-0.2 + i * 0.075) * w, h * 0.06, d / 2 + 0.06));
      }
      return g;
    }

    // 光模組：本體 ＋ LC 雙埠 ＋ 拉環 ＋ 鏈路燈
    function optic(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d * 0.86, K.mat(0.05, { metal: 0.45, rough: 0.4 })));
      const port = K.mat(-0.55, { rough: 0.9, metal: 0.05 });
      [-1, 1].forEach(s => g.add(put(box(w * 0.3, h * 0.45, d * 0.1, port), s * w * 0.22, 0, d * 0.44)));
      g.add(put(box(w * 0.7, h * 0.16, d * 0.2, K.mat(0.35, { metal: 0.3, rough: 0.55 })), 0, -h * 0.5, d * 0.52));
      // 圖九 2-1：可插拔光模組後端的金手指 —— 成排、鍍金、前緣倒角
      g.add(fingers(K, w * 0.86, h * 0.1, d * 0.12, 7, -h * 0.28, -d * 0.44));
      g.add(put(box(w * 0.18, h * 0.12, d * 0.03, K.mat(0, { led: true })), 0, h * 0.4, d * 0.45));
      return g;
    }

    // 交換器：機殼 ＋ 前面板整排埠 ＋ 埠燈
    function switchBox(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.15, { metal: 0.35 })));
      const port = K.mat(-0.55, { rough: 0.9, metal: 0.05 });
      const led = K.mat(0, { led: true });
      for (let i = -7; i <= 7; i++) {
        g.add(put(box(w * 0.038, h * 0.32, d * 0.04, port), i * w * 0.06, -h * 0.12, d / 2));
        if (i % 2 === 0) g.add(put(box(w * 0.016, h * 0.07, d * 0.02, led), i * w * 0.06, h * 0.2, d / 2 + 0.02));
      }
      return g;
    }

    /* ABF 載板：core ＋ 上下增層 ＋ 表面的細線路
       ★ 2026-09-22：補上**雷射盲孔（微孔）**與第二層增層。
         載板跟硬板在圖上唯一分得開的地方就是孔形：載板是一層一層疊上去、
         每層用雷射打上寬下窄的錐形盲孔；硬板是整疊壓合完再機械鑽直筒通孔。
         兩者對到的是完全不同的設備、不同的廠（欣興／南電／景碩 vs 金像電）。*/
    function substrate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h * 0.5, d, K.mat(-0.3, { rough: 0.8, metal: 0.06 })));
      [-1, 1].forEach(s => g.add(put(box(w * 0.99, h * 0.22, d * 0.99, K.mat(-0.05, { rough: 0.6 })), 0, s * h * 0.36, 0)));
      // 增層第二層：比第一層窄一點，看得出是「一層一層疊上去」而不是一塊實心板
      /* 第二層增層：比第一層窄一階，看得出是「一層一層疊上去」。
         ★ 厚度刻意壓在 0.1h、疊到 0.54h 為止 —— 原本這顆的最高點是 0.49h，
           長太高會讓 fitCamera 重新取景、整張圖的構圖跟著跑掉（那就不是「更細緻」是「跑版」）。*/
      [-1, 1].forEach(s => g.add(put(box(w * 0.86, h * 0.1, d * 0.86,
        K.mat(0, { color: K.css('--dg-abf', '#c3b9a4'), rough: 0.66, metal: 0.08 })), 0, s * h * 0.49, 0)));
      // 雷射盲孔：錐形、上寬下窄，打穿最上面那層增層膜（所以要露在它上面看得到）
      g.add(microvias(K, w * 0.86, d * 0.86, h * 0.5, h * 0.12, 9, 6));
      // 圖九 2-1：以前是 15 條等距直線，看起來像百葉窗不像走線。
      // 換成蛇行等長線（差動對成雙、轉角 45°），這才是載板表面真正的樣子。
      // 表面線路擺在**最上層增層膜之上**（2026-09-22 起多了第二層增層，壓在下面就看不到了）
      const tl = traceLayer(K, w * 0.9, d * 0.9, h * 0.56, { pairs: 5, cycles: 6, wdt: Math.min(w, d) * 0.009, dir: 1 });
      g.add(tl.group); g.userData.flows = tl.flows;
      return g;
    }

    // BGA 錫球：球就是球，方塊看起來像腳墊
    function balls(p, K) {
      // 圖九 2-1：以前是 3×3 顆，看起來像腳墊。BGA 的識別特徵是「密密麻麻的球陣列」，
      // 改成 5×5、球徑對得上間距（球會微微相鄰但不重疊）。
      const g = new T.Group();
      const [w, h] = p.box;
      g.add(ballGrid(K, w * 0.62, Math.min(w, h) * 0.3, 5, 0));
      return g;
    }

    // RDL：有機重佈線層，表面用細線表示扇出
    function rdl(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.1, { rough: 0.65 })));
      const tr = K.mat(0.4, { metal: 0.65, rough: 0.3 });
      for (let i = -9; i <= 9; i++) g.add(put(box(w * 0.01, h * 0.12, d * 0.86, tr), i * w * 0.05, h * 0.52, 0));
      return g;
    }

    // LSI 矽橋：小矽片，上表面幾條 die-to-die 連線
    function bridge(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0.1, { rough: 0.35, metal: 0.3 })));
      const tr = K.mat(0.5, { metal: 0.7, rough: 0.25 });
      for (let i = -2; i <= 2; i++) g.add(put(box(w * 0.86, h * 0.14, d * 0.03, tr), 0, h * 0.55, i * d * 0.16));
      return g;
    }

    /* 晶粒：矽片 ＋ 表面功能區塊格
       ★ 2026-09-22：補上**切割道**與**金屬層紋理**。
         切割道（scribe lane）＝ 這顆晶粒是從一片晶圓上鋸下來的，四周留著那一圈空白；
         金屬層紋理＝ 晶粒上表面是縱橫兩層的金屬佈線，不是一片平的鏡面。
         這兩件事就是「晶粒」跟「一塊藍色方塊」的差別，而且它們各自對到
         切割（DA／DB 設備）與後段金屬製程 —— 不同的環節、不同的公司。*/
    function die(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0.05, { rough: 0.32, metal: 0.35 })));
      const blk = K.mat(0.3, { rough: 0.4, metal: 0.3 });
      for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
        if (i === 0 && j === 0) continue;
        g.add(put(box(w * 0.26, h * 0.1, d * 0.26, blk), i * w * 0.3, h * 0.53, j * d * 0.3));
      }
      g.add(put(box(w * 0.3, h * 0.12, d * 0.3, K.mat(0.45, { rough: 0.35, metal: 0.4 })), 0, h * 0.54, 0));
      // 切割道：四周一圈沒有電路的空白，鋸片就走在這裡
      const lane = K.mat(-0.3, { rough: 0.5, metal: 0.18 });
      const lw = Math.min(w, d) * 0.035;
      g.add(put(mboxes([[w, h * 0.08, lw, 0, 0, -d / 2 + lw / 2], [w, h * 0.08, lw, 0, 0, d / 2 - lw / 2],
        [lw, h * 0.08, d, -w / 2 + lw / 2, 0, 0], [lw, h * 0.08, d, w / 2 - lw / 2, 0, 0]], lane), 0, h * 0.5, 0));
      // 金屬層紋理：縱橫兩組細線（M1 走一個方向、M2 走另一個方向）
      const mtl = K.mat(0.55, { metal: 0.72, rough: 0.26 });
      const tw = Math.min(w, d) * 0.012, at = [];
      // 蓋在功能區塊**上面**（頂層金屬就是走在最上層）—— 壓在底下會被區塊整片擋掉
      for (let i = 0; i < 11; i++) at.push([(-5 + i) * w * 0.078, h * 0.605, 0]);
      g.add(instOf(new T.BoxGeometry(tw, h * 0.03, d * 0.84), mtl, at));
      const at2 = [];
      for (let i = 0; i < 8; i++) at2.push([0, h * 0.63, (-3.5 + i) * d * 0.105]);
      g.add(instOf(new T.BoxGeometry(w * 0.84, h * 0.03, tw), mtl, at2));
      return g;
    }

    /* ================================================================ MLCC（量產圖 11-1）
       切掉「x > 0 且 z > 0」那一角，露出兩個切面：
         z = 0 的切面 → 交錯指狀電極（一端進、另一端留餘白）
         x = 0 的切面 → 側邊餘白（電極不到側面）
       lslab() 就是「畫一塊方板，但把那一角挖掉」，所以每一層只要呼叫一次。
       over：讓電極在切面上多凸出一點點，不然它跟介電層在切面上共面會 z-fighting。*/
    function lslab(x0, x1, y0, y1, z0, z1, m, over) {
      const o = over || 0, out = [];
      const add = (ax0, ax1, az0, az1) => {
        if (ax1 - ax0 < 0.02 || az1 - az0 < 0.02) return;
        const b = box(ax1 - ax0, y1 - y0, az1 - az0, m);
        b.position.set((ax0 + ax1) / 2, (y0 + y1) / 2, (az0 + az1) / 2);
        out.push(b);
      };
      add(x0, x1, z0, Math.min(z1, o));                    // 後半（z ≤ 0）保留整條
      add(x0, Math.min(x1, o), Math.max(z0, 0), z1);       // 前半只留 x ≤ 0
      return out;
    }

    function mlccBody(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cov = h * 0.11;          // 上下保護層（無電極素坯）
      const em = w * 0.14;           // 端部餘白：不准碰到對面的端電極
      const sm = d * 0.1;            // 側邊餘白：電極不到側面
      const n = 12, pit = (h - cov * 2) / n, et = pit * 0.3;
      /* B6：材質色跟 2D 那張用同一組 `--dg-*`，不再拿環節色去調淡 ——
         以前 cer 是 K.mat(0.72)＝環節色 #ace3ec 調淡（冷灰白），
         2D 卻是 #d3cbb7（暖米白 42°），同一顆電容切到 3D 就換材質。*/
      const cer = K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.88, metal: 0.03 });   // 陶瓷：暖米白霧面
      const cvm = K.mat(0, { color: K.css('--dg-cover', '#ddd6c2'), rough: 0.92, metal: 0.02 }); // 保護層：淡一階，一眼分得出來
      const elm = K.mat(0, { color: K.css('--dg-el', '#4e5866'), rough: 0.32, metal: 0.78 });    // 內電極：暗鋼灰
      const push = (a) => a.forEach(o => g.add(o));
      push(lslab(-w / 2, w / 2, -h / 2, -h / 2 + cov, -d / 2, d / 2, cvm));
      push(lslab(-w / 2, w / 2, h / 2 - cov, h / 2, -d / 2, d / 2, cvm));
      for (let i = 0; i < n; i++) {
        const y0 = -h / 2 + cov + i * pit;
        push(lslab(-w / 2, w / 2, y0, y0 + pit, -d / 2, d / 2, cer));
        // ★ 交替：偶數層連左端、奇數層連右端。這一行就是規格書 §3-A 的硬規則
        const ex0 = (i % 2) ? -w / 2 + em : -w / 2;
        const ex1 = (i % 2) ? w / 2 : w / 2 - em;
        const ey = y0 + (pit - et) / 2;
        push(lslab(ex0, ex1, ey, ey + et, -d / 2 + sm, d / 2 - sm, elm, 0.3));
      }
      return g;
    }

    /* 端電極：由內到外 Cu → Ni → Sn，包住端部五個面的一段。
       ★ 順序不准對調（Ni 畫到 Sn 外面是最常見的錯）。厚薄只表達關係，不標數字。*/
    function mlccTerm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const wl = w * 0.18, tw = h * 0.13, cw = w * 0.11;
      const push = (a) => a.forEach(o => g.add(o));
      /* metalness 壓在 0.45 以下：這個場景只有方向光、沒有環境貼圖，
         金屬度拉高就變成一塊黑（第一版的端電極就是這樣，三層全糊在一起看不出來）。*/
      // B5／B6：Cu／Ni／Sn 三層也改讀 --dg-*，跟 2D 的端子剖面是同一組顏色
      const L3 = [[0, 0.62, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.42, rough: 0.42 })],
        [0.62, 0.85, K.mat(0, { color: K.css('--dg-ni', '#a9b1b9'), metal: 0.4, rough: 0.38 })],
        [0.85, 1, K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.3, rough: 0.34 })]];
      [-1, 1].forEach(sx => {
        const wx0 = sx < 0 ? -w / 2 : w / 2 - wl, wx1 = sx < 0 ? -w / 2 + wl : w / 2;
        L3.forEach(([a, b, m]) => {
          const x0 = sx < 0 ? -w / 2 - cw * b : w / 2 + cw * a;
          const x1 = sx < 0 ? -w / 2 - cw * a : w / 2 + cw * b;
          push(lslab(x0, x1, -h / 2 - tw, h / 2 + tw, -d / 2 - tw, d / 2 + tw, m));          // 端面
          push(lslab(wx0, wx1, h / 2 + tw * a, h / 2 + tw * b, -d / 2 - tw, d / 2 + tw, m)); // 上面
          push(lslab(wx0, wx1, -h / 2 - tw * b, -h / 2 - tw * a, -d / 2 - tw, d / 2 + tw, m)); // 下面
          push(lslab(wx0, wx1, -h / 2, h / 2, d / 2 + tw * a, d / 2 + tw * b, m));            // 兩側
          push(lslab(wx0, wx1, -h / 2, h / 2, -d / 2 - tw * b, -d / 2 - tw * a, m));
        });
      });
      return g;
    }

    // PCB 焊墊：板子 ＋ 兩塊銅墊 ＋ 焊錫圓角（圓角用壓扁的球，看得出是「爬上去」的）
    function mlccPad(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0, { rough: 0.9, metal: 0.05, color: K.css('--dg-pcb', '#1a4230') })));
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.42, rough: 0.44 });
      const sn = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.35, rough: 0.36 });
      [-1, 1].forEach(s => {
        g.add(put(box(w * 0.3, h * 0.6, d * 0.55, cu), s * w * 0.3, h * 0.7, 0));
        // 焊錫圓角：壓扁的球，看得出是「爬上端子側面」的那一圈，不是一顆大球
        const f = ball(w * 0.018, sn); f.scale.set(1.6, 1.8, 9);
        g.add(put(f, s * w * 0.375, h * 0.98, 0));
      });
      return g;
    }

    // 探針卡：基板 ＋ 一叢探針
    function probe(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.15, { rough: 0.7 })));
      const pin = K.mat(0.45, { metal: 0.8, rough: 0.25 });
      const pins = [];
      for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) pins.push([i * w * 0.16, -h * 0.9, j * d * 0.16]);
      g.add(instOf(new T.CylinderGeometry(w * 0.012, w * 0.012, h * 1.6, 6), pin, pins));
      return g;
    }

    /* ================================================================ 第一層：零件字彙
       （計畫在 docs/diagram_3d_upgrade.md §3「第一層」）

       Andy 2026-09-22：「所有 3D 圖請都麻煩補上（2D）這樣程度的細緻程度」
       ＋「不能看起來只有像是一般的方塊，他是電路圖就是要有電路圖的樣貌」。

       21 張場景共用同一套宣告式設定（一個零件一行、交給 kind 產生幾何），
       所以**補細緻度的正確位置是這裡**，不是回頭一張一張手刻。

       ★ 每一個零件只畫「對得到不同公司／不同原理」的特徵（docs/diagram_purpose.md 的 R2）。
         寫得出那一句話才畫，寫不出來就不畫 —— 所以螺絲沒有螺紋（畫了不會讓任何人更懂，
         只是多幾千個三角形），但 PCB 有走線、電感有繞線、鋁擠有鰭片。

       ★ 效能：陣列類（錫球、凸塊、鰭片、TSV、沖孔、滾珠）一律走 instOf()／mboxes()，
         收成一個 draw call。一個一個 Mesh 的代價實測過（2026-09-19）：
         走線一段一個方塊時整台機櫃從 483 個 mesh 暴增到 1846、fps 直接砍半。 */

    /* 同一個形狀重複很多次 → InstancedMesh（一次 draw call）。
       items 每一筆是 [x, y, z, rx, ry, rz, sx, sy, sz]（後六個可省）。*/
    function instOf(geo, m, items) {
      const im = new T.InstancedMesh(geo, m, items.length);
      const mx = new T.Matrix4(), q = new T.Quaternion(), e = new T.Euler();
      const v = new T.Vector3(), s = new T.Vector3();
      items.forEach((it, i) => {
        v.set(it[0] || 0, it[1] || 0, it[2] || 0);
        e.set(it[3] || 0, it[4] || 0, it[5] || 0); q.setFromEuler(e);
        s.set(it[6] == null ? 1 : it[6], it[7] == null ? 1 : it[7], it[8] == null ? 1 : it[8]);
        mx.compose(v, q, s); im.setMatrixAt(i, mx);
      });
      im.instanceMatrix.needsUpdate = true;
      return im;
    }

    /* 形狀不一樣、但同一種材質 → 併成一個 geometry（也是一次 draw call）。
       vendor 沒有內建 BufferGeometryUtils（而且不准為了這個引新函式庫），所以自己併。*/
    function mergeGeos(geos) {
      const pos = [], nor = [], idx = [];
      let base = 0;
      geos.forEach(g => {
        const gp = g.attributes.position, gn = g.attributes.normal;
        for (let i = 0; i < gp.count; i++) {
          pos.push(gp.getX(i), gp.getY(i), gp.getZ(i));
          nor.push(gn ? gn.getX(i) : 0, gn ? gn.getY(i) : 1, gn ? gn.getZ(i) : 0);
        }
        const gi = g.index;
        if (gi) { for (let i = 0; i < gi.count; i++) idx.push(base + gi.getX(i)); }
        else { for (let i = 0; i < gp.count; i++) idx.push(base + i); }
        base += gp.count;
        g.dispose();
      });
      const out = new T.BufferGeometry();
      out.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
      out.setAttribute('normal', new T.Float32BufferAttribute(nor, 3));
      out.setIndex(idx);
      return out;
    }
    // 一堆尺寸不同的方塊併成一個 mesh。每一筆 [w, h, d, x, y, z]
    function mboxes(list, m) {
      return new T.Mesh(mergeGeos(list.map(([w, h, d, x, y, z]) => {
        const g = new T.BoxGeometry(w, h, d); g.translate(x || 0, y || 0, z || 0); return g;
      })), m);
    }
    // nx × nz 的陣列座標（給 instOf 用）
    function gridXZ(nx, nz, px, pz, y) {
      const out = [];
      for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
        out.push([(-(nx - 1) / 2 + i) * px, y || 0, (-(nz - 1) / 2 + j) * pz]);
      }
      return out;
    }

    // ---------------------------------------------------------------- 板類

    /* 焊墊陣列：板子上「零件要焊在哪裡」的那些銅墊（表面處理鍍金）。
       為什麼值得畫：有焊墊才看得出這是一塊**要裝件的板子**而不是一片板材；
       而且焊墊的表面處理（ENIG／OSP）本身就是不同的製程與不同的藥水供應商。*/
    function padField(K, w, d, y, nx, nz) {
      const au = K.mat(0, { color: K.css('--dg-au', '#e3b75a'), metal: 0.8, rough: 0.26 });
      const pw = w / nx * 0.46, pd = d / nz * 0.46;
      return instOf(new T.BoxGeometry(pw, Math.max(0.02, w * 0.004), pd), au,
        gridXZ(nx, nz, w / nx, d / nz, y));
    }

    /* 鍍通孔（PTH）：貫穿板子、孔壁鍍銅。
       為什麼值得畫：**機械鑽孔的直孔**（PCB）跟**雷射盲孔的錐形微孔**（載板）
       是兩種完全不同的設備與供應商 —— 這兩個形狀就是分辨「板廠」與「載板廠」的那個特徵。*/
    function pthRow(K, w, h, d, n, z) {
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.74, rough: 0.3 });
      const vd = K.mat(0, { color: K.css('--dg-edge', '#0e1526'), rough: 0.95, metal: 0.02 });
      const g = new T.Group();
      const r = Math.min(w, d) * 0.009;
      const at = [];
      for (let i = 0; i < n; i++) at.push([(-(n - 1) / 2 + i) * (w * 0.7 / n), 0, z]);
      g.add(instOf(new T.CylinderGeometry(r * 2.1, r * 2.1, h * 1.02, 8), cu, at));  // 鍍銅孔壁
      g.add(instOf(new T.CylinderGeometry(r, r, h * 1.06, 6), vd, at));              // 孔本身（暗）
      return g;
    }

    /* 絲印：零件外框與極性記號的白漆。
       為什麼值得畫：絲印是「這塊板子已經被設計過、每個零件有自己的位置」的證據 ——
       沒有絲印的綠板子看起來就只是一片板材。*/
    function silk(K, w, d, y, marks) {
      const ink = K.mat(0, { color: K.css('--dg-cover', '#ddd6c2'), rough: 0.9, metal: 0.02 });
      const t = Math.min(w, d) * 0.006, list = [];
      (marks || []).forEach(([cx, cz, mw, md]) => {
        list.push([mw, t, t * 1.6, cx, y, cz - md / 2]);
        list.push([mw, t, t * 1.6, cx, y, cz + md / 2]);
        list.push([t * 1.6, t, md, cx - mw / 2, y, cz]);
        list.push([t * 1.6, t, md, cx + mw / 2, y, cz]);
        list.push([t * 2.6, t, t * 2.6, cx - mw / 2 - t * 3, y, cz - md / 2]);   // 第 1 腳記號
      });
      return mboxes(list, ink);
    }

    /* 微孔（雷射盲孔）：只打穿一層增層膜、孔形是**上寬下窄的錐**。
       為什麼值得畫：錐形＝雷射，直筒＝機械鑽 —— 這是載板與硬板分家的地方。*/
    function microvias(K, w, d, y, h, nx, nz) {
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.74, rough: 0.3 });
      const r = Math.min(w, d) * 0.012;
      return instOf(new T.CylinderGeometry(r, r * 0.45, h, 8), cu, gridXZ(nx, nz, w / (nx + 1), d / (nz + 1), y));
    }

    /* 矽中介層：識別特徵＝**貫穿整片的 TSV 陣列**。
       為什麼值得畫：有 TSV 的是矽中介層（CoWoS-S），沒有 TSV、只有有機重佈線的是 CoWoS-L ——
       對到的是不同的製程、不同的設備、不同的供應商。 */
    function interposer(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0, { color: K.css('--dg-si', '#33488a'), rough: 0.34, metal: 0.3 })));
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.74, rough: 0.3 });
      const r = Math.min(w, d) * 0.013;
      g.add(instOf(new T.CylinderGeometry(r, r, h * 1.08, 6), cu, gridXZ(11, 7, w * 0.082, d * 0.12, 0)));
      // 表面的重佈線（細、直、密 —— 中介層上不走蛇行等長線，那是板子的事）
      const tl = traceLayer(K, w, d, h * 0.54, { pairs: 5, cycles: 8, wdt: Math.min(w, d) * 0.007, dir: 1 });
      g.add(tl.group); g.userData.flows = tl.flows;
      return g;
    }

    // ---------------------------------------------------------------- 晶片類

    /* 微凸塊陣列：銅柱 ＋ 錫帽。
       為什麼值得畫：**銅柱凸塊**（micro-bump，間距數十 µm）跟**錫球**（BGA，間距 0.8 mm）
       差了一個數量級，用的材料與設備完全不同；畫成一樣大的球就看不出這件事。*/
    function bumpField(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const nx = 14, nz = 10, px = w / nx, pz = d / nz;
      const r = Math.min(px, pz) * 0.27;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.74, rough: 0.3 });
      const sn = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.38, rough: 0.34 });
      g.add(instOf(new T.CylinderGeometry(r, r, h * 0.62, 6), cu, gridXZ(nx, nz, px, pz, -h * 0.12)));
      g.add(instOf(new T.SphereGeometry(r * 1.15, 6, 4), sn, gridXZ(nx, nz, px, pz, h * 0.26)));
      return g;
    }

    /* BGA 封裝體：載板 ＋ 模封 ＋ 底下整片錫球。
       為什麼值得畫：BGA 的識別特徵是「看不到腳、腳全在肚子底下」——
       跟看得到腳的 QFP／連接器是完全不同的封裝與不同的封測廠。*/
    function bgaPkg(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.22, d, K.mat(0, { color: K.css('--dg-core', '#3f4a30'), rough: 0.72, metal: 0.08 })), 0, -h * 0.18, 0));
      g.add(put(box(w * 0.92, h * 0.5, d * 0.92, K.mat(0, { color: K.css('--dg-emc', '#2f3039'), rough: 0.62, metal: 0.1 })), 0, h * 0.2, 0));
      // 上蓋的第 1 腳圓點：封裝上一定有的方向記號
      g.add(put(cyl(Math.min(w, d) * 0.04, h * 0.06, K.mat(0, { color: K.css('--dg-cover', '#ddd6c2'), rough: 0.9, metal: 0.02 }), 10),
        -w * 0.34, h * 0.46, -d * 0.34));
      const sn = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.5, rough: 0.34 });
      const nx = 9, nz = 7, px = w * 0.92 / nx, pz = d * 0.92 / nz;
      g.add(instOf(new T.SphereGeometry(Math.min(px, pz) * 0.34, 8, 6), sn, gridXZ(nx, nz, px, pz, -h * 0.34)));
      return g;
    }

    // ---------------------------------------------------------------- 被動元件

    /* 晶片電容（0402／0603 那種，不是切開的那顆）：陶瓷本體 ＋ 兩端端電極。
       為什麼值得畫：端電極**包住端部五個面**是 MLCC 的識別特徵；
       只畫一個米白方塊的話，它跟電阻、跟電感在圖上長得一模一樣。*/
    function mlccChip(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w * 0.66, h, d, K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.88, metal: 0.03 })));
      const sn = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.34, rough: 0.34 });
      const ni = K.mat(0, { color: K.css('--dg-ni', '#a9b1b9'), metal: 0.4, rough: 0.38 });
      [-1, 1].forEach(s => {
        g.add(put(box(w * 0.2, h * 1.06, d * 1.06, ni), s * w * 0.31, 0, 0));   // Ni 阻障（露一圈）
        g.add(put(box(w * 0.14, h * 1.1, d * 1.1, sn), s * w * 0.37, 0, 0));    // Sn 最外層
      });
      return g;
    }

    /* 功率電感：鼓型磁芯 ＋ 看得見的繞線 ＋ 兩端電極。
       為什麼值得畫：**繞線**就是電感與電容在外觀上唯一分得開的地方；
       而繞線是扁線還是圓線、一體成型還是繞線式，對到的是不同的廠（乾坤／台慶科／美磊…）。*/
    function inductor(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const core = K.mat(0, { color: K.css('--dg-el', '#4e5866'), rough: 0.76, metal: 0.16 });
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.74, rough: 0.32 });
      const R = Math.min(w, d) * 0.5;
      g.add(put(cyl(R * 0.98, h * 0.14, core, 16), 0, h * 0.43, 0));     // 上凸緣
      g.add(put(cyl(R * 0.98, h * 0.14, core, 16), 0, -h * 0.43, 0));    // 下凸緣
      g.add(cyl(R * 0.4, h * 0.76, core, 14));                           // 中柱
      const rings = [], n = 7;
      for (let i = 0; i < n; i++) rings.push([0, -h * 0.28 + i * (h * 0.56 / (n - 1)), 0, Math.PI / 2, 0, 0]);
      g.add(instOf(new T.TorusGeometry(R * 0.62, h * 0.05, 5, 14), cu, rings));   // 繞線
      // 端電極：繞線的兩個線頭壓在下凸緣上，這是它焊得上板子的地方
      [-1, 1].forEach(s => g.add(put(box(w * 0.26, h * 0.1, d * 0.5, cu), s * w * 0.32, -h * 0.5, 0)));
      return g;
    }

    /* 厚膜晶片電阻：陶瓷基板 ＋ 電阻膜 ＋ **雷射調阻的切口** ＋ 保護玻璃 ＋ 兩端電極。
       為什麼值得畫：那道切口是電阻獨有的 —— 阻值靠雷射一刀一刀修到規格內，
       這一刀本身就是一道製程（也是為什麼電阻廠的良率結構跟電容廠不一樣）。*/
    function resistor(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w * 0.7, h * 0.72, d, K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.9, metal: 0.03 })));
      const film = K.mat(0, { color: K.css('--dg-emc', '#2f3039'), rough: 0.66, metal: 0.12 });
      g.add(put(box(w * 0.5, h * 0.16, d * 0.86, film), 0, h * 0.42, 0));            // 電阻膜
      // 雷射調阻切口：從一邊切進去一段（L 形的那一刀）
      const cut = K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.9, metal: 0.03 });
      g.add(put(box(w * 0.05, h * 0.2, d * 0.44, cut), -w * 0.08, h * 0.43, -d * 0.2));
      const sn = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.34, rough: 0.34 });
      [-1, 1].forEach(s => g.add(put(box(w * 0.18, h * 0.86, d * 1.04, sn), s * w * 0.35, 0, 0)));
      return g;
    }

    /* 鋁電解電容：鋁殼 ＋ 頂部**防爆紋** ＋ 絕緣套 ＋ 底部負極條。
       為什麼值得畫：防爆紋（十字刻痕）與負極條是電解電容獨有的 ——
       它有極性、會爆，這兩件事決定了它在電源板上怎麼擺、壽命怎麼算。*/
    function ecap(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, d) / 2;
      g.add(cyl(r, h, K.mat(0, { color: K.css('--dg-alu', '#a3b2c4'), metal: 0.62, rough: 0.34 }), 18));
      // 絕緣套：包住側面的那層塑膠，比鋁殼暗一階
      g.add(cyl(r * 1.03, h * 0.86, K.mat(0, { color: K.css('--dg-el', '#4e5866'), rough: 0.72, metal: 0.1 }), 18));
      // 防爆紋：頂面的十字刻痕
      const sc = K.mat(0, { color: K.css('--dg-edge', '#0e1526'), rough: 0.92, metal: 0.04 });
      g.add(put(mboxes([[r * 1.5, h * 0.04, r * 0.14, 0, 0, 0], [r * 0.14, h * 0.04, r * 1.5, 0, 0, 0]], sc), 0, h * 0.5, 0));
      // 負極條：側面一道垂直白條 ＋ 底部橡膠塞
      g.add(put(box(r * 0.5, h * 0.8, r * 0.06, K.mat(0, { color: K.css('--dg-cover', '#ddd6c2'), rough: 0.9, metal: 0.02 })), 0, 0, r * 1.02));
      g.add(put(cyl(r * 0.92, h * 0.08, K.mat(0, { color: K.css('--dg-resin', '#6f6858'), rough: 0.88, metal: 0.04 }), 16), 0, -h * 0.5, 0));
      return g;
    }

    // ---------------------------------------------------------------- 散熱

    /* 鋁擠／鏟齒散熱片：底板 ＋ 鰭片陣列。
       為什麼值得畫：鰭片間距與片數就是散熱片的規格本身；一個實心鋁塊散不了熱，
       畫成方塊等於把「為什麼需要這個零件」整個刪掉。*/
    function heatsink(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const al = K.mat(0, { color: K.css('--dg-alu', '#a3b2c4'), metal: 0.55, rough: 0.42 });
      const al2 = K.mat(0, { color: K.css('--dg-alu-2', '#75849a'), metal: 0.5, rough: 0.46 });
      g.add(put(box(w, h * 0.16, d, al2), 0, -h * 0.42, 0));            // 底板
      const n = Math.max(9, Math.round(w / (h * 0.16)));
      const ft = w / n * 0.34;
      const at = [];
      for (let i = 0; i < n; i++) at.push([(-(n - 1) / 2 + i) * (w / n), h * 0.08, 0]);
      g.add(instOf(new T.BoxGeometry(ft, h * 0.84, d * 0.96), al, at));  // 鰭片
      return g;
    }

    /* 均熱板（VC）：上下銅板 ＋ 毛細層 ＋ 蒸氣腔 ＋ 支撐柱陣列（掀開上蓋看得到裡面）。
       為什麼值得畫：支撐柱與毛細層是 VC 跟「一塊銅板」唯一的差別 ——
       兩相流靠毛細回水、靠支撐柱撐住真空不被壓扁，這兩件事決定了它是誰在做。*/
    function vaporChamber(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.7, rough: 0.32 });
      const wick = K.mat(0, { color: K.css('--dg-wick', '#8f6a45'), rough: 0.88, metal: 0.12 });
      const vap = K.mat(0, { color: K.css('--dg-vap', '#24324a'), rough: 0.8, metal: 0.05 });
      g.add(put(box(w, h * 0.2, d, cu), 0, -h * 0.4, 0));                       // 下銅板
      g.add(put(box(w * 0.96, h * 0.12, d * 0.96, wick), 0, -h * 0.24, 0));     // 燒結銅粉毛細層
      g.add(put(box(w * 0.96, h * 0.34, d * 0.96, vap), 0, h * 0.02, 0));       // 蒸氣腔（真空）
      // 支撐柱：把上下板撐開，不然大氣壓會把腔體壓扁
      g.add(instOf(new T.CylinderGeometry(Math.min(w, d) * 0.028, Math.min(w, d) * 0.028, h * 0.34, 8), cu,
        gridXZ(5, 4, w * 0.19, d * 0.22, h * 0.02)));
      // 上銅板只蓋一半 —— 剖開才看得到裡面，這張圖要講的就是裡面
      g.add(put(box(w, h * 0.2, d * 0.52, cu), 0, h * 0.3, -d * 0.24));
      return g;
    }

    /* 熱管：壓扁的銅管 ＋ 彎折 ＋ 切口露出管壁毛細與中央蒸氣道。
       為什麼值得畫：熱管一定是彎的（要繞過零件），而剖面的「外銅管／毛細／中空」
       三層就是它跟一根實心銅棒的差別。*/
    function heatpipe(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.72, rough: 0.3 });
      const wick = K.mat(0, { color: K.css('--dg-wick', '#8f6a45'), rough: 0.88, metal: 0.12 });
      const vap = K.mat(0, { color: K.css('--dg-vap', '#24324a'), rough: 0.82, metal: 0.05 });
      const r = Math.min(h, d) * 0.34;
      // U 形：一端貼晶片（蒸發段）、另一端插進鰭片（冷凝段）。熱管在機器裡一定是彎的。
      const curve = new T.CatmullRomCurve3([
        new T.Vector3(-w * 0.48, 0, d * 0.3), new T.Vector3(-w * 0.1, 0, d * 0.32),
        new T.Vector3(w * 0.18, 0, d * 0.05), new T.Vector3(w * 0.3, 0, -d * 0.24),
        new T.Vector3(w * 0.48, 0, -d * 0.3)]);
      const tube = new T.Mesh(new T.TubeGeometry(curve, 30, r, 10, false), cu);
      tube.scale.y = 0.5;                        // 壓扁：熱管貼上晶片那一段一定是扁的
      g.add(tube);
      // 切開的那一端：管壁毛細（環）＋ 中央蒸氣道。三層剖面＝它不是一根實心銅棒
      const end = put(cyl(r * 0.78, r * 0.34, wick, 14), -w * 0.49, 0, d * 0.3);
      end.rotation.z = Math.PI / 2; end.scale.z = 0.5; g.add(end);
      const core = put(cyl(r * 0.42, r * 0.4, vap, 14), -w * 0.5, 0, d * 0.3);
      core.rotation.z = Math.PI / 2; core.scale.z = 0.5; g.add(core);
      return g;
    }

    /* 冷板：銅底板 ＋ 內部微流道鰭片 ＋ 蓋板 ＋ 進出水接頭（藍進紅出）。
       為什麼值得畫：冷板值錢的地方全在裡面 —— 流道密度決定熱阻，
       而「進水是冷的、出水是熱的」是整條液冷鏈的敘事起點。
       ★ 冷熱用 --dg-cold／--dg-hot（語意色，任何配色都不准蓋）。*/
    function coldplate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.7, rough: 0.32 });
      const st = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.68, rough: 0.3 });
      g.add(put(box(w, h * 0.26, d, cu), 0, -h * 0.37, 0));                    // 底板（貼晶片那一面）
      // 微流道鰭片：一片一片鏟出來的，水從鰭片之間流過
      const n = 18, ft = w * 0.9 / n * 0.42;
      const at = [];
      for (let i = 0; i < n; i++) at.push([(-(n - 1) / 2 + i) * (w * 0.9 / n), -h * 0.06, 0]);
      g.add(instOf(new T.BoxGeometry(ft, h * 0.36, d * 0.78), cu, at));
      g.add(put(box(w, h * 0.16, d * 0.46, st), 0, h * 0.26, -d * 0.27));      // 蓋板只蓋一半（看得到流道）
      const cold = K.mat(0, { color: K.css('--dg-cold', '#4ea8dc'), metal: 0.4, rough: 0.4 });
      const hot = K.mat(0, { color: K.css('--dg-hot', '#e8854a'), metal: 0.4, rough: 0.4 });
      [[-1, cold], [1, hot]].forEach(([s, m]) => {
        const t = put(cyl(Math.min(w, d) * 0.07, h * 1.1, m, 12), s * w * 0.34, h * 0.5, -d * 0.3);
        g.add(t);
      });
      return g;
    }

    // ---------------------------------------------------------------- 連接

    /* 高速連接器：屏蔽金屬籠 ＋ 塑膠舌片 ＋ 舌片上的金手指 ＋ 背面壓接針。
       為什麼值得畫：籠子（cage）是高速連接器的識別特徵 —— 它是為了擋 EMI 才存在的；
       而金手指的根數就是通道數。畫成方塊的話，它跟電源端子分不開。*/
    function connector(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const sh = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.72, rough: 0.28 });
      const pl = K.mat(0, { color: K.css('--dg-emc', '#2f3039'), rough: 0.66, metal: 0.08 });
      const t = h * 0.12;
      // 籠子：四片鈑金圍成一個開口朝前的框
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0], [w, t, d, 0, -h / 2 + t / 2, 0],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2]], sh));
      // 塑膠舌片往前伸出籠口，金手指鋪在舌片上面 —— 不伸出來就被籠子擋住、等於沒畫
      g.add(put(box(w * 0.78, h * 0.24, d * 0.8, pl), 0, -h * 0.08, d * 0.26));
      g.add(fingers(K, w * 0.72, h * 0.1, d * 0.56, 9, h * 0.08, d * 0.3));
      // 背面壓接針：一整排壓進板子的針，這是它「怎麼裝上去」的答案
      const pin = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.66, rough: 0.32 });
      g.add(instOf(new T.BoxGeometry(w * 0.012, h * 0.5, w * 0.012), pin,
        gridXZ(12, 2, w * 0.07, w * 0.06, -h * 0.6).map(a => [a[0], -h * 0.6, a[2] - d * 0.4])));
      return g;
    }

    /* 線束：幾股絞在一起的導線 ＋ 束帶 ＋ 端子。
       為什麼值得畫：線束是「這兩個東西之間有實體連線」的視覺證據，
       而股數與線徑對到的是電流容量（電源線束跟訊號線束粗細差很多）。*/
    function cable(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const ins = K.mat(0, { color: K.css('--dg-emc', '#2f3039'), rough: 0.78, metal: 0.05 });
      const tie = K.mat(0, { color: K.css('--dg-mute', '#78859f'), rough: 0.8, metal: 0.06 });
      const r = h * 0.17;
      for (let i = 0; i < 4; i++) {
        const o = (i - 1.5) * r * 1.5;
        const curve = new T.CatmullRomCurve3([
          new T.Vector3(-w * 0.5, o * 0.4, d * 0.2 + o), new T.Vector3(-w * 0.15, h * 0.22 + o * 0.5, o),
          new T.Vector3(w * 0.15, -h * 0.16 + o * 0.5, -o), new T.Vector3(w * 0.5, o * 0.4, -d * 0.2 + o)]);
        g.add(new T.Mesh(new T.TubeGeometry(curve, 18, r, 7, false), ins));
      }
      const t1 = put(cyl(r * 2.6, w * 0.05, tie, 12), -w * 0.12, 0, 0); t1.rotation.z = Math.PI / 2; g.add(t1);
      const t2 = put(cyl(r * 2.6, w * 0.05, tie, 12), w * 0.2, 0, 0); t2.rotation.z = Math.PI / 2; g.add(t2);
      // 端子：一頭有殼、有鎖扣
      g.add(put(box(w * 0.12, h * 0.9, d * 0.7, K.mat(0, { color: K.css('--dg-frame', '#1a2540'), rough: 0.7, metal: 0.1 })), -w * 0.48, 0, 0));
      return g;
    }

    /* 匯流排銅排：厚銅條 ＋ 鎖固孔 ＋ 一段絕緣套。
       為什麼值得畫：銅排的**厚度**就是它的規格（幾百安培靠截面積過），
       鎖固孔則說明它是「鎖上去」不是「焊上去」—— 這是電源與訊號最大的差別。*/
    function busbar(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.8, rough: 0.28 });
      const ins = K.mat(0, { color: K.css('--dg-el', '#4e5866'), rough: 0.8, metal: 0.06 });
      g.add(box(w, h, d, cu));
      g.add(put(box(w * 0.36, h * 1.12, d * 1.12, ins), 0, 0, 0));      // 中段絕緣套
      /* 鎖固孔：**穿過厚度方向（y）** —— 銅排是用螺栓鎖上去的，不是焊的。
         這一條是電源件跟訊號件最直接的差別（訊號端子沒有人拿扳手鎖）。*/
      const r = Math.min(h, d) * 0.3;
      const hl = K.mat(0, { color: K.css('--dg-edge', '#0e1526'), rough: 0.92, metal: 0.04 });
      const at = [];
      [-1, 1].forEach(s => { for (let i = 0; i < 2; i++) at.push([s * w * (0.28 + i * 0.14), 0, 0]); });
      g.add(instOf(new T.CylinderGeometry(r, r, h * 1.3, 10), hl, at));
      return g;
    }

    // ---------------------------------------------------------------- 機構

    /* 滑軌：外軌 ＋ 內軌 ＋ 滾珠列。
       為什麼值得畫：滾珠是「這台機器抽得出來」的證據 ——
       機櫃裡每一台伺服器都要能單獨抽出來維修，這是機構件廠真正在賣的東西。*/
    function rail(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.66, rough: 0.34 });
      const st2 = K.mat(0, { color: K.css('--dg-steel-2', '#6b7683'), metal: 0.6, rough: 0.4 });
      const t = h * 0.14;
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0], [w, t, d, 0, -h / 2 + t / 2, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2]], st2));                        // 外軌（ㄈ 型）
      g.add(put(box(w * 0.86, h * 0.3, d * 0.5, st), w * 0.06, 0, d * 0.1));   // 內軌（抽出來一點）
      // 滾珠：排在內外軌之間的兩條滾道上 —— 這是「抽得出來」的那個機構
      const r = h * 0.15, at = [];
      for (let i = 0; i < 9; i++) [-1, 1].forEach(s => at.push([(-4 + i) * w * 0.1, s * h * 0.26, d * 0.22]));
      g.add(instOf(new T.SphereGeometry(r, 8, 6), st, at));
      return g;
    }

    /* 螺絲：頭 ＋ 墊圈 ＋ 桿。**刻意不畫螺紋** ——
       docs/diagram_purpose.md R2：再細下去對到的還是同一批公司，那就不要拆。
       螺紋只會多幾千個三角形，不會讓任何人更懂這張圖。*/
    function screw(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      // 直徑一律用 min(w, d)：螺絲是圓的，拿 w 當半徑的話 box 一寬它就變成一塊煎餅
      const r0 = Math.min(w, d) * 0.5;
      const st = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.72, rough: 0.3 });
      g.add(put(cyl(r0 * 0.62, h * 0.3, st, 6), 0, h * 0.35, 0));       // 六角頭
      g.add(put(cyl(r0 * 0.78, h * 0.08, st, 12), 0, h * 0.16, 0));     // 墊圈
      g.add(put(cyl(r0 * 0.32, h * 0.66, st, 10), 0, -h * 0.21, 0));    // 桿
      return g;
    }

    /* L 型支架：兩片折板 ＋ 補強肋 ＋ 鎖固孔。
       為什麼值得畫：折邊與補強肋是鈑金件的識別特徵（不是鑄造、不是塑膠），
       對到的是沖壓與折彎那一段工序。*/
    function bracket(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0, { color: K.css('--dg-steel-2', '#6b7683'), metal: 0.58, rough: 0.42 });
      const t = Math.min(w, h) * 0.1;
      g.add(mboxes([[w, t, d, 0, -h / 2 + t / 2, 0], [t, h, d, -w / 2 + t / 2, 0, 0]], st));
      // 補強肋：折角處的三角肋，鈑金件才有
      g.add(put(box(w * 0.4, h * 0.4, t * 0.8, st), -w * 0.22, -h * 0.22, 0));
      const r = Math.min(w, d) * 0.06;
      const hl = K.mat(0, { color: K.css('--dg-edge', '#0e1526'), rough: 0.92, metal: 0.04 });
      g.add(instOf(new T.CylinderGeometry(r, r, t * 2.2, 10), hl,
        [[w * 0.1, -h / 2 + t / 2, -d * 0.24], [w * 0.1, -h / 2 + t / 2, d * 0.24],
          [w * 0.32, -h / 2 + t / 2, 0]]));
      return g;
    }

    /* 機殼鈑金：面板 ＋ 沖孔網 ＋ 折邊 ＋ 把手。
       為什麼值得畫：**沖孔網**是伺服器面板一定有的（進氣要過），
       孔率直接決定風阻；一片沒有孔的鈑金在機殼上是不存在的東西。*/
    function chassis(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0, { color: K.css('--dg-steel-2', '#6b7683'), metal: 0.56, rough: 0.44 });
      const st2 = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.62, rough: 0.38 });
      const t = d * 0.16;
      g.add(box(w, h, t, st));                                          // 面板
      // 上下折邊：鈑金件一定有的折邊（靠它才有剛性）。只折一小段，折太深整片就看不出是面板了
      g.add(mboxes([[w, t, d * 0.45, 0, h / 2 - t / 2, -d * 0.2], [w, t, d * 0.45, 0, -h / 2 + t / 2, -d * 0.2]], st));
      // 沖孔網：六角排列的圓孔，一次 draw call
      const r = Math.min(w, h) * 0.032, holes = [];
      for (let i = 0; i < 16; i++) for (let j = 0; j < 7; j++) {
        holes.push([(-7.5 + i) * w * 0.055 + (j % 2 ? w * 0.027 : 0), (-3 + j) * h * 0.12, 0, Math.PI / 2, 0, 0]);
      }
      g.add(instOf(new T.CylinderGeometry(r, r, t * 1.08, 8),
        K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 }), holes));
      [-1, 1].forEach(s => g.add(put(box(w * 0.05, h * 0.34, t * 1.6, st2), s * w * 0.45, 0, t * 0.6)));  // 把手
      return g;
    }

    return { plain, rack, backplane, tray, gpu, chip, hbm, pcb, laminate, cdu, uqd, fan, psu, battery,
      optic, switch: switchBox, substrate, balls, rdl, bridge, die, probe,
      mlcc: mlccBody, mlccterm: mlccTerm, mlccpad: mlccPad, _lslab: lslab,
      /* ---- 第一層零件字彙（2026-09-22）。舊的 kind 一個都沒有拿掉：
         21 張既有場景照舊走原本那幾支，新的是**多出來的詞**，不是換掉。*/
      interposer, bump: bumpField, bga: bgaPkg,
      mlccchip: mlccChip, inductor, resistor, ecap,
      heatsink, vc: vaporChamber, heatpipe, coldplate,
      connector, cable, busbar,
      rail, screw, bracket, chassis,
      // 圖九 2-1 的共用件，量產圖11 時直接用
      _traceLayer: traceLayer, _fingers: fingers, _ballGrid: ballGrid, _meander: meander, _traceMesh: traceMesh,
      // 第一層的共用件：陣列類一律走這三支收成一個 draw call
      _instOf: instOf, _mboxes: mboxes, _gridXZ: gridXZ, _padField: padField, _pthRow: pthRow,
      _silk: silk, _microvias: microvias };
  }

  /* ---------------------------------------------------------------- 建場景 */
  async function mount(el, sceneId, opts) {
    const spec = SCENES[sceneId];
    if (!el || !spec || !supported()) return null;
    const o = Object.assign({ color: () => '#8ea0c4', onSeg: null, onBg: null, anim: true, members: null, onStock: null }, opts || {});
    const { THREE, OrbitControls } = await load();
    const B = mkBuilders(THREE);

    const W = () => Math.max(320, el.clientWidth);
    // 機櫃是直立的，畫面比例太扁會把上下切掉；0.62 是讓 42U 機櫃連同標籤都塞得下的比例
    // hk：畫面高度佔寬度的比例。機櫃是直立的要高（0.62）；封裝剖面又寬又扁，
    // 給它一樣高只會上下留一大片空白，所以那個場景自己指定 0.46。
    const H = () => Math.max(340, Math.round(Math.min(700, el.clientWidth * (spec.hk || 0.62))));
    // E1：標籤欄佔掉畫面左右各一塊，模型要縮進中間那段才不會被文字框壓到
    const narrow = () => W() < 560;
    const colW = () => (narrow() ? Math.min(158, Math.round(W() * 0.40)) : Math.max(112, Math.min(212, Math.round(W() * 0.23))));

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, W() / H(), 1, 2000);
    camera.position.set(spec.camera[0], spec.camera[1], spec.camera[2]);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(W(), H());
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.borderRadius = '10px';
    el.style.position = 'relative';
    el.appendChild(renderer.domElement);

    /* E1：標籤層自己做，不用 CSS2DRenderer。
       CSS2DRenderer 只會把標籤釘在零件的投影點上 —— 那正是 Andy 說「文字太小、擠在一起」的原因。
       這裡改成：標籤排在左右兩欄（固定寬度、字放大到 12.5px、多一行說明），
       用一條引線接回零件，位置與避讓自己算（layoutLabels）。*/
    const layer = document.createElement('div');
    layer.className = 'lbl3dLayer';
    layer.style.cssText = 'position:absolute;inset:0;pointer-events:none;overflow:hidden';
    const lead = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    lead.setAttribute('class', 'lead3d');
    lead.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none';
    layer.appendChild(lead);
    el.appendChild(layer);

    /* E2：打光改成「棚拍」而不是「霓虹」。
       原本有一盞青色 rim light（0x3ee0ff）＋ 每顆材質都帶 emissive，
       所以不管什麼零件都像在發光 —— Andy 說的螢光感就是這兩件事加起來。
       現在：天空光壓低、主光白、補光是中性冷白、底下一點回彈，rim 拿掉。*/
    const hemi = new THREE.HemisphereLight(0x99a7c2, 0x0b1120, 0.62); scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffffff, 1.0); key.position.set(60, 90, 70); scene.add(key);
    const fill = new THREE.DirectionalLight(0xc7d2e6, 0.34); fill.position.set(-70, 40, -60); scene.add(fill);
    const bounce = new THREE.DirectionalLight(0x8fa0bd, 0.16); bounce.position.set(0, -60, 20); scene.add(bounce);

    const root = new THREE.Group(); scene.add(root);
    const picks = [];            // 可以點的 group
    const byIdx = [];            // 每個零件的所有 mesh + 材質，highlight 時用
    const spinners = [];         // E4：會自己轉的東西（風扇葉輪）
    const leds = [];             // E4：會呼吸的指示燈材質
    const flowPts = [], flowAll = [], flowSeen = new Set();   // 圖九 2-1：電流粒子
    let labelDown = null;        // 這次按下去是從某個標籤開始的（可能只是想轉視角）

    spec.parts.forEach((p, idx) => {
      const hex = o.color(p.seg) || '#8ea0c4';
      // 零件身分：沒宣告就自動補一個（同場景內唯一，但跟 2D 的 data-part 對不起來）
      const pkey = p.part || (p.seg + '#3d' + idx);
      const K = kit(THREE, hex, p.ghost, (n) => getComputedStyle(el).getPropertyValue(n).trim());
      const build = B[p.kind] || B.plain;
      const proto = build(p, K);
      const n = p.n || 1, gap = p.gap || 0, axis = p.axis || 'x';
      const groups = [], meshes = [];
      for (let i = 0; i < n; i++) {
        // 重複件用 clone：幾何與材質是共用的，記憶體省下來，highlight 也一次全部吃到
        const g = i === 0 ? proto : proto.clone(true);
        const off = (i - (n - 1) / 2) * gap;
        g.position.set(p.at[0] + (axis === 'x' ? off : 0),
          p.at[1] + (axis === 'y' ? off : 0),
          p.at[2] + (axis === 'z' ? off : 0));
        g.userData = { seg: p.seg, part: pkey, idx, name: p.name, note: p.note };
        g.traverse(x => {
          if (x.isMesh) meshes.push(x);
          if (x.userData && x.userData.spin) spinners.push(x);
          // 圖九 2-1：電流粒子。clone 出來的重複件共用同一份 geometry，
          // 所以同一份只能推一次，不然一幀會被推 n 次、速度變 n 倍。
          if (x.isPoints && x.userData && x.userData.flow && !flowSeen.has(x.geometry)) {
            flowSeen.add(x.geometry); flowPts.push(x);
          }
          if (x.isPoints && x.userData && x.userData.flow) flowAll.push(x);
        });
        root.add(g); groups.push(g);
        if (!p.frame) picks.push(g);
      }
      K.mats.forEach(m => { if (m.userData && m.userData.led) leds.push(m); });
      byIdx[idx] = {
        seg: p.seg, part: pkey, alias: p.alias || [], groups, meshes, hex, ghost: !!p.ghost, name: p.name, note: p.note,
        mats: K.mats.slice(),
        baseOp: new Map(K.mats.map(m => [m, m.opacity])),
        baseCol: new Map(K.mats.map(m => [m, m.color.clone()])),
        // 引線接在零件頂端中央：接在中心的話線會插進零件裡看不到
        anchor: new THREE.Vector3(0, p.box[1] / 2, 0),
      };

      // 標籤：DOM 疊上去，不是畫進畫布，所以選得起來、也還驗得到文字重疊
      const d = document.createElement('div');
      d.className = 'lbl3d';
      d.innerHTML = `<b></b><i></i><u class="chips3d"></u>`;
      d.querySelector('b').textContent = p.name;
      d.querySelector('i').textContent = p.note || '';
      d.dataset.seg = p.seg;
      /* 圖九 2-3（規格書 docs/diagram_specs/dg3d_standard.md）：
         說明底下掛一排「這個環節的台股」，點了直接進個股頁。
         以前標籤只是死的文字 —— 使用者看得到「ABF 載板」，卻要自己回去翻是誰做的。
         該環節台股掛零（hyperscaler、HBM）就明講「台股無直接對應」，不要留白。*/
      const chipBox = d.querySelector('u.chips3d');
      /* A5-c（mechanical-engineer 2026-09-21）：零件可以自己指定要列哪幾檔（`codes`），
         沒指定才退回「這個環節的台股」（`members(seg)`）。理由見 SCENES.mlcc 那一段。
         一句話版本：一個環節可以比一個零件**廣**（「被動元件 MLCC / 電阻」含晶片電阻廠），
         晶片又只排得下四個，切前四家不一定切到對的四家 ——
         零件說明講的是 MLCC 的結構，底下列的名單就必須是真的做這件事的人。
         `data-seg` 沒有動（顏色連動、環節色標、篩選都靠它），動的只有「列誰」。*/
      const mem = (p.codes && p.codes.length)
        ? { list: p.codes.slice(0, 4).map(c => ({ code: c, name: (window.Link && window.Link.cname[c]) || c })), total: p.codes.length }
        : (o.members ? (o.members(p.seg) || { list: [], total: 0 }) : { list: [], total: 0 });
      // A5-b：晶片上方一行小字，講清楚這排台股是「哪一群」，不要讓它貼著零件說明被讀成「這幾家做這個零件」
      if (p.chipnote && mem.list.length) {
        const s = document.createElement('s');
        s.className = 'chipnote'; s.textContent = p.chipnote;
        chipBox.appendChild(s);
      }
      if (!mem.list.length) {
        chipBox.innerHTML = '<s>台股無直接對應</s>';
      } else {
        mem.list.forEach(c => {
          const a = document.createElement('a');
          a.className = 'chip3d'; a.textContent = c.name; a.title = `${c.name} ${c.code} · 看個股頁`;
          a.href = '#stock/' + c.code;
          a.style.pointerEvents = 'auto';
          // 晶片自己吃掉 pointerdown，不然會被下面那段轉給畫布、變成「點名字就開始轉機櫃」
          a.addEventListener('pointerdown', (e) => e.stopPropagation());
          a.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation();
            if (o.onStock) o.onStock(c.code); else location.hash = '#stock/' + c.code; });
          chipBox.appendChild(a);
        });
        if (mem.total > mem.list.length) {
          const more = document.createElement('s');
          more.textContent = '+' + (mem.total - mem.list.length);
          more.title = `這個環節共 ${mem.total} 檔台股`;
          chipBox.appendChild(more);
        }
      }
      d.style.setProperty('--c', hex);     // 文字框左邊那條色帶＝環節色，一眼對得上零件
      // 標籤本身也要可以點：機櫃裡的小零件（UQD、光模組）用滑鼠很難精準打到，
      // 點名字是最直覺的路。父層 pointerEvents 是 none，這裡個別開回來。
      d.style.pointerEvents = 'auto';
      d.style.cursor = 'pointer';
      d.title = p.note || p.name;
      d.addEventListener('pointerdown', (e) => {
        labelDown = { seg: p.seg, data: { seg: p.seg, part: pkey, idx, name: p.name, note: p.note } };
        /* 標籤蓋在畫布上，按在它上面畫布收不到 pointerdown，整台機櫃就轉不動了
           （驗收 1 就是這樣掛的）。把這個 pointerdown 原樣轉給畫布，OrbitControls
           會接手並 setPointerCapture，之後的移動與放開都走畫布那條路。 */
        renderer.domElement.dispatchEvent(new PointerEvent('pointerdown', {
          pointerId: e.pointerId, pointerType: e.pointerType || 'mouse', isPrimary: true,
          clientX: e.clientX, clientY: e.clientY, button: e.button, buttons: e.buttons,
          bubbles: true, cancelable: true,
        }));
        e.preventDefault();
      });
      layer.appendChild(d);
      byIdx[idx].el = d;
      // 引線：一條折線 ＋ 零件端的小圓點
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('class', 'ld');
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('class', 'ld-dot'); dot.setAttribute('r', '2.6');
      lead.appendChild(path); lead.appendChild(dot);
      byIdx[idx].path = path; byIdx[idx].dot = dot;
    });

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.target.set(spec.target[0], spec.target[1], spec.target[2]);
    /* N1（Andy 2026-09-19：「3D圖需要可以游標抓取移動，並且可以 360 都觀測
       我發現下面看不到」）。
       以前夾在 0.495π —— 註解寫「不要轉到地板底下」，但那正是「下面看不到」的原因：
       仰角被卡在水平面上方一點點，永遠繞不到底下去看機櫃底部、載板背面、BGA 錫球。
       改成 0 ~ π（完整 360 度），代價是可以轉到「頭下腳上」——
       接受這個代價，因為看不到底部是**功能缺失**，轉過頭只是一時不舒服，
       而且有「重設視角」一鍵回正。*/
    controls.minPolarAngle = 0.02;                 // 留一點點，正上方時 up 向量會翻
    controls.maxPolarAngle = Math.PI - 0.02;       // 同理，正下方也留一點
    /* 「游標抓取移動」＝平移。OrbitControls 預設右鍵才是平移，
       但一般人只會左鍵拖 —— 所以工具列多一顆「轉動／平移」切換，
       切到平移之後左鍵拖就是抓著場景移動。*/
    controls.enablePan = true;
    controls.screenSpacePanning = true;            // 沿著畫面平移，不是沿著地平面（直覺得多）
    controls.autoRotateSpeed = 0.55;               // E4：慢到可以邊看邊讀，不是在轉陀螺

    /* 相機距離用「把整個場景包起來的球」算出來，不要寫死：
       寫死的話換一個場景、或畫面比例一變，機櫃頭尾就被切掉（第一版就是這樣）。 */
    const fitCamera = () => {
      const box = new THREE.Box3().setFromObject(root);
      const sph = box.getBoundingSphere(new THREE.Sphere());
      const size = box.getSize(new THREE.Vector3());
      const vfov = camera.fov * Math.PI / 180;
      const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
      /* 用「外接盒」而不是「外接球」算距離：球對又扁又寬的封裝剖面會多退 30%，
         畫面中間只剩一小塊。半個深度是留給轉動時最靠近相機的那一角。
         E1 之後左右各被標籤欄吃掉一塊，所以水平方向要照「還剩多寬」再退一點。 */
      const usable = Math.max(140, W() - colW() * (narrow() ? 1 : 2));
      const shrink = W() / usable;
      const halfW = Math.max(size.x, size.z) / 2 * shrink, halfH = size.y / 2, halfD = Math.max(size.x, size.z) / 2;
      const dist = (Math.max(halfH / Math.tan(vfov / 2), halfW / Math.tan(hfov / 2)) + halfD) * 1.06 * (spec.fit || 1);
      const dir = new THREE.Vector3(spec.camera[0], spec.camera[1], spec.camera[2])
        .sub(new THREE.Vector3(spec.target[0], spec.target[1], spec.target[2])).normalize();
      controls.target.copy(sph.center);
      camera.position.copy(sph.center).addScaledVector(dir, dist);
      controls.minDistance = dist * 0.28; controls.maxDistance = dist * 2.6;
      camera.updateProjectionMatrix();
      controls.update();
    };
    fitCamera();

    // ---- 點零件：接回原本那條路（亮起來 ＋ 帶出台股清單）
    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2();
    let downAt = null;
    const toNdc = (e) => { const r = renderer.domElement.getBoundingClientRect();
      ptr.x = ((e.clientX - r.left) / r.width) * 2 - 1; ptr.y = -((e.clientY - r.top) / r.height) * 2 + 1; };
    // 零件現在是 Group（E3 之後一個零件好幾顆 mesh），所以 raycast 要遞迴，
    // 打到的是某顆小零件 —— 往上走到帶 seg 的那一層才知道它屬於誰
    const owner = (obj) => { let x = obj; while (x && !(x.userData && x.userData.seg)) x = x.parent; return x; };
    const hit = () => { ray.setFromCamera(ptr, camera); const xs = ray.intersectObjects(picks, true); return xs[0] && owner(xs[0].object); };
    renderer.domElement.addEventListener('pointerdown', (e) => { downAt = { x: e.clientX, y: e.clientY }; hold(); });
    const onUp = (e) => {
      const from = labelDown; labelDown = null;
      release();
      if (!downAt) return;
      const moved = Math.abs(e.clientX - downAt.x) + Math.abs(e.clientY - downAt.y);
      downAt = null;
      if (moved > 5) return;                       // 那是在轉視角，不是點零件
      if (from) { if (o.onSeg) o.onSeg(from.seg, from.data); return; }   // 從標籤按下去的，選那個標籤
      toNdc(e); const m = hit();
      if (m && o.onSeg) { o.onSeg(m.userData.seg, m.userData); return; }
      /* ★ 2026-09-22：打空＝點到場景背景 → 回到 Default（全部零件恢復全亮、小卡收掉）。
         Andy：「當點擊背景時會恢復到原來的 Default」。上面已經擋掉「拖超過 5px＝在轉視角」，
         所以走到這裡的一定是「原地按一下、而且沒打到任何零件」。*/
      if (!m && o.onBg) o.onBg();
    };
    renderer.domElement.addEventListener('pointerup', onUp);
    // 沒抓到 pointer capture 時（少數瀏覽器）放開會落在標籤上，補一條同樣的路；
    // onUp 第一次跑完就把 downAt 清掉，所以兩邊都收到也只會處理一次。
    layer.addEventListener('pointerup', onUp);
    renderer.domElement.addEventListener('pointermove', (e) => {
      toNdc(e); renderer.domElement.style.cursor = hit() ? 'pointer' : 'grab';
    });

    /* ---- E4：動態／靜止。
       動態＝場景緩慢自轉 ＋ 風扇轉 ＋ 指示燈呼吸；靜止＝一律不動。
       使用者一動手就先把自轉停掉（不然會跟他搶方向），放開兩秒半再接回去。*/
    let anim = o.anim !== false, userHold = false, holdT = null;
    const applyAuto = () => { controls.autoRotate = anim && !userHold; };
    function hold() { userHold = true; if (holdT) clearTimeout(holdT); applyAuto(); }
    function release() {
      if (holdT) clearTimeout(holdT);
      holdT = setTimeout(() => { userHold = false; applyAuto(); }, 2500);
    }
    function setAnim(on) {
      anim = !!on;
      applyAuto();
      // 圖九 2-1：靜止＝電流不跑，粒子也不留在畫面上；走線本身一直都看得見
      flowAll.forEach(x => { x.visible = anim; });
      if (!anim) {
        // 靜止時燈定在中間亮度；亮度基準由色票決定（soft 是 0，完全不發光）
        const lb = palNum('--dg-led', 0.55);
        leds.forEach(m => { m.emissiveIntensity = lb; });
        /* 「靜止」要立刻停住。OrbitControls 的阻尼會把剛才自轉的殘量再吐好幾秒，
           畫面看起來就是「按了關還在慢慢飄」。用 dampingFactor = 1 跑一次 update
           把殘量一次吃光並歸零（reset() 用的是同一招）。*/
        const df = controls.dampingFactor;
        controls.dampingFactor = 1; controls.update(); controls.dampingFactor = df;
      }
    }
    setAnim(anim);

    // ---- 高亮：和 SVG 版同一個介面（highlightSegments 會呼叫它）
    /* E2：高亮不再是「整顆發光」。選起來的維持原色、其餘變很透明，
       選起來的只給一點點 emissive（0.22）當提示。指示燈另外算，它本來就該亮。*/
    let lastHi = { on: null, color: null, part: null };
    /* 整個場景只有一個環節嗎（MLCC 那種）。單一環節的場景裡，「同環節的其餘」＝
       「除了主角以外的全部」，跟主角擺在一起分不出來，所以要另外退一階（見 index.html 的 .dg1.haspart）。*/
    const singleSeg = new Set(spec.parts.map(p => p.seg)).size === 1;
    el.classList.toggle('dg1', singleSeg);
    // 這個零件是不是「被點的那一個」（alias 見 SCENES 檔頭）
    const isPart = (p, key) => !!key && (p.part === key || (p.alias || []).indexOf(key) >= 0);
    // ↑ lastHi 要宣告在色票區塊之前：applyPal() 會回頭呼叫 highlight(lastHi...)，
    //   放在後面會踩到 TDZ，3D 直接退回平面圖（2026-09-19 實測到的）
    /* ---- 圖九 2-2：三種配色（tech / soft / calm）
       規格書 docs/diagram_specs/dg3d_standard.md。
       **所有顏色都讀 CSS 變數 `--dg-*`，JS 不寫死任何 #xxxxxx** ——
       這是 art-director 的紅線，也是淺色主題一堆白字白線的根因：
       顏色寫死在 JS 裡，切主題的 refreshPalette() 換不掉。
       色票只做三件事：背景（CSS 自己吃）、零件顏色的去飽和與混色、打光與發光強度。*/
    /* 2026-09-21 深夜新增第四個「休閒」（Andy：「2D3D 都需要新增那樣的風格」）。
       ★ 3D 這一側**沒有第二份色值** —— 零件的材質色是從 :root[data-dgpal="casual"] 的
       `--dg-*` 讀進來的（K.css），跟 2D 剖析圖同一份定義；這裡只有背景／混色／打光，
       那些本來就是 3D 才有的東西。原本三個配色一個值都沒動。*/
    const PALS = ['tech', 'soft', 'calm', 'casual'];
    const PAL_NAME = { tech: '科技', soft: '柔和', calm: '沉穩', casual: '休閒' };
    const origCol = new Map();          // 零件的「原色」，換色票一律從這裡重算，不要疊加
    let pal = 'tech';
    /* 這兩支刻意寫成 function 宣告（會被提升）—— setAnim() 在色票區塊「之前」就會被呼叫一次，
       寫成 const 箭頭函式的話那一次會踩到 TDZ，整個 3D 直接掛掉。*/
    function palNum(name, dflt) {
      const v = getComputedStyle(el).getPropertyValue(name).trim();
      const n = parseFloat(v); return Number.isFinite(n) ? n : dflt;
    }
    function palCol(name, dflt) {
      const v = getComputedStyle(el).getPropertyValue(name).trim();
      try { return new THREE.Color(v || dflt); } catch (e) { return new THREE.Color(dflt); }
    }
    /* 「讀得到就回顏色，讀不到就回 null」—— 不給 fallback 的版本。
       不能借用 palCol(name, null)：那一支讀不到時會走進 new THREE.Color(null)，在 catch 裡再炸一次。*/
    function palColOpt(name) {
      const v = getComputedStyle(el).getPropertyValue(name).trim();
      if (!v) return null;
      try { return new THREE.Color(v); } catch (e) { return null; }
    }
    function applyPal(name) {
      if (name) { pal = PALS.includes(name) ? name : 'tech'; }
      el.dataset.pal = pal;
      const mix = palCol('--dg-mix', '#ffffff'), k = palNum('--dg-mix-k', 0), sat = palNum('--dg-sat', 1);
      const hsl = {};
      byIdx.forEach(p => {
        if (!p) return;
        p.mats.forEach(m => {
          /* 這顆材質的顏色是某個 --dg-* 來的 → 每次換配色都回去重讀。
             休閒配色會換掉材質 token 本身，只靠 origCol 的快照會停在上一個配色的原色。*/
          const vn = m.userData && m.userData.dgvar;
          if (vn) { const c0 = palColOpt(vn); if (c0) origCol.set(m, c0); }
          if (!origCol.has(m)) origCol.set(m, m.color.clone());
          const c = origCol.get(m).clone();
          c.getHSL(hsl); c.setHSL(hsl.h, hsl.s * sat, hsl.l);
          if (k > 0) c.lerp(mix, k);
          p.baseCol.set(m, c.clone());
        });
      });
      hemi.intensity = palNum('--dg-hemi', 0.62);
      key.intensity = palNum('--dg-key', 1.0);
      fill.intensity = palNum('--dg-fill', 0.34);
      highlight(lastHi.on, lastHi.color, lastHi.part);     // 重新套用目前的選取狀態，顏色才會真的換掉
      return pal;
    }
    applyPal(o.pal || 'tech');     // 圖九 2-2：一掛上去就照使用者選的色票，不要先畫成預設再閃一下

    /* 兩層高亮（2026-09-21 晚間）：`part` 是**被點的那一個零件**的身分，
       跟 2D 剖析圖共用同一個 key（見 SCENES 檔頭的 `part`）。
         · 被點的那一個 → 最強（emissive 拉到 --dg-part-em、標籤加粗框）
         · 同環節的其餘 → 次強（維持原本的 --dg-sel-em，多環節場景的既有外觀一個值都沒動）
         · 其餘環節     → 淡出（本來就有的行為）
       單一環節的場景多一條：次強那一層要退到 --dg-sib-o，不然三顆長得一模一樣。*/
    function highlight(on, color, part) {
      lastHi = { on, color, part: part || null };
      const has = on && on.size > 0;
      const tint = color ? new THREE.Color(color) : null;
      const hasPart = !!part && byIdx.some(p => p && isPart(p, part));
      el.classList.toggle('haspart', hasPart);
      const sibO = palNum('--dg-sib-o', 0.4);
      byIdx.forEach(p => {
        if (!p) return;
        const sel = has && on.has(p.seg);
        const selPart = sel && isPart(p, part);
        // 單一環節的場景才壓暗「同環節但不是主角」的那幾顆；多環節場景維持原樣（零回歸）
        const sib = sel && hasPart && !selPart && singleSeg;
        const fade = has && !sel;
        p.mats.forEach(m => {
          const b = p.baseOp.get(m), bc = p.baseCol.get(m);
          m.opacity = fade ? Math.min(b, 0.12) : (sib ? Math.min(b, sibO) : b);
          m.transparent = fade || sib || b < 1;
          if (m.userData && m.userData.led) {
            // 圖九 2-2：指示燈的亮度基準由色票決定（soft 是 0＝完全不發光，印得出來）
            const lb = palNum('--dg-led', 0.55);
            m.emissiveIntensity = fade ? lb * 0.07 : (sel ? lb * 1.55 : lb); return;
          }
          if (m.emissive) m.emissiveIntensity = selPart ? palNum('--dg-part-em', 0.5) : (sel ? palNum('--dg-sel-em', 0.22) : 0);
          // 套族群色時只把原色往那個方向拉一半，保留零件本身的明暗結構
          if (sel && tint) m.color.copy(bc).lerp(tint, 0.55); else m.color.copy(bc);
        });
        if (p.el) {
          p.el.classList.toggle('sel', sel);
          p.el.classList.toggle('sel-part', selPart);
          p.el.classList.toggle('dim', fade);
        }
        // 引線跟著標籤一起淡出／亮起來，不然選了一個環節，畫面上還有一堆別人的線
        if (p.path) { p.path.style.opacity = fade ? 0.1 : (sel ? 1 : 0.72); p.path.style.stroke = sel ? p.hex : ''; }
        if (p.dot) p.dot.style.opacity = fade ? 0.1 : 0.9;
      });
    }

    /* ---- E1：標籤排版（引線 ＋ 外部文字框）
       1. 把每個零件的錨點投影到畫面上
       2. 依投影的 x 分到左欄／右欄（畫面太窄就全放右邊）
       3. 每欄由上到下排，撞到就往下推，推到底就把最不重要的藏起來
       4. 引線從錨點拉到文字框內側，最後一小段走水平（看起來才像工程圖的引線）
       ~16 個元素、每秒最多幾次，成本可以忽略。*/
    const vtmp = new THREE.Vector3();
    const GAP = 6;
    let lastCw = -1;
    /* 一欄由上往下擺：先各自貼著自己零件的高度，擠到的往下推；
       推到超出底部就再由下往上收一次。收完最上面那個還是負的＝這一欄塞不下。*/
    function pack(list, h) {
      let y = 4;
      list.forEach(it => { it.ty = Math.max(y, Math.min(h - it.hh - 4, it.sy - it.hh / 2)); y = it.ty + it.hh + GAP; });
      let yb = h - 4;
      for (let i = list.length - 1; i >= 0; i--) { const it = list[i]; it.ty = Math.min(it.ty, yb - it.hh); yb = it.ty - GAP; }
      return !list.length || list[0].ty >= 2;
    }
    function layoutLabels() {
      const w = W(), h = H(), cw = colW(), one = narrow();
      const items = [];
      byIdx.forEach(p => {
        if (!p || !p.el) return;
        p.groups[0].getWorldPosition(vtmp); vtmp.add(p.anchor);
        const v = vtmp.clone().project(camera);
        items.push({ p, sx: (v.x + 1) / 2 * w, sy: (-v.y + 1) / 2 * h, front: v.z < 1,
          d: camera.position.distanceTo(vtmp), sel: p.el.classList.contains('sel') });
      });
      // 重要度：選起來的最優先，其次是離相機近的（看得最清楚的那個）；塞不下時從最後面開始讓位
      items.slice().sort((a, b) => (b.sel - a.sel) || (a.d - b.d)).forEach((it, i) => { it.rank = i; });
      // 寬度只在版面真的變了才重設並重量高度：每幀量一次 offsetHeight 會一直逼瀏覽器重算版面
      if (cw !== lastCw) { byIdx.forEach(p => { if (p && p.el) p.el.style.width = (cw - 12) + 'px'; }); lastCw = cw; }
      items.forEach(it => { it.p.el.classList.remove('hid'); it.hh = it.p.el.offsetHeight || 42; });

      const hidden = items.filter(it => !it.front);       // 轉到背面去的零件，標籤跟著收起來
      const cols = { L: [], R: [] };
      /* 分左右欄：明顯偏一邊的就放那一邊，卡在中間的（機櫃是直立的，大部分零件都在正中央）
         放到目前比較空的那一欄 —— 只照 sx < w/2 分的話，整排零件會全部擠到左欄去。*/
      items.filter(it => it.front).sort((a, b) => a.sy - b.sy).forEach(it => {
        let side;
        if (one) side = 'R';
        else if (it.sx < w / 2 - w * 0.10) side = 'L';
        else if (it.sx > w / 2 + w * 0.10) side = 'R';
        else side = cols.L.length <= cols.R.length ? 'L' : 'R';
        cols[side].push(it);
      });
      ['L', 'R'].forEach(side => {
        const list = cols[side];
        while (list.length && !pack(list, h)) {
          let worst = 0; list.forEach((it, i) => { if (it.rank > list[worst].rank) worst = i; });
          hidden.push(list.splice(worst, 1)[0]);
        }
        const lx = side === 'L' ? 6 : w - cw - 6;
        const inner = side === 'L' ? lx + cw - 12 : lx;      // 文字框朝著模型的那一邊
        list.forEach(it => {
          it.p.el.style.left = lx + 'px';
          it.p.el.style.top = it.ty + 'px';
          const cy = it.ty + it.hh / 2;
          const bend = side === 'L' ? inner + 14 : inner - 14;
          it.p.path.setAttribute('d', `M${it.sx.toFixed(1)},${it.sy.toFixed(1)} L${bend.toFixed(1)},${cy.toFixed(1)} L${inner.toFixed(1)},${cy.toFixed(1)}`);
          it.p.path.style.display = '';
          it.p.dot.setAttribute('cx', it.sx.toFixed(1)); it.p.dot.setAttribute('cy', it.sy.toFixed(1));
          it.p.dot.setAttribute('stroke', it.p.hex);
          it.p.dot.style.display = '';
        });
      });
      hidden.forEach(it => {
        it.p.el.classList.add('hid');
        it.p.path.style.display = 'none'; it.p.dot.style.display = 'none';
      });
    }

    /* 圖九 2-1：把電流粒子往前推一格。
       路徑用「段索引」參數化（每段長度相近，肉眼看不出差別），
       dir 決定方向 —— 電源由下往上、訊號由 GPU 往背板、光訊號往前面板。*/
    function stepFlows(dt) {
      flowPts.forEach(o2 => {
        const f = o2.userData.flow;
        f.t = (f.t + dt * f.speed) % 1;
        const arr = o2.geometry.attributes.position.array;
        let k = 0;
        f.paths.forEach(path => {
          for (let i = 0; i < f.per; i++) {
            let u = (f.t + i / f.per) % 1;
            if (f.dir < 0) u = 1 - u;
            const at = (path.length - 1) * u;
            const si = Math.min(path.length - 2, Math.floor(at)), ft = at - si;
            const a = path[si], b = path[si + 1];
            arr[k++] = a.x + (b.x - a.x) * ft;
            arr[k++] = a.y + (b.y - a.y) * ft;
            arr[k++] = a.z + (b.z - a.z) * ft;
          }
        });
        o2.geometry.attributes.position.needsUpdate = true;
      });
    }

    // ---- 只在看得到的時候畫
    let raf = null, alive = true, visible = true, relayout = 0, t0 = performance.now();
    const tick = () => {
      if (!alive) return;
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      const dt = Math.min(0.05, (performance.now() - t0) / 1000); t0 = performance.now();
      if (anim) {
        spinners.forEach(s => { s.rotation[s.userData.spin.axis] += s.userData.spin.speed * dt; });
        const lb = palNum('--dg-led', 0.55);
        const k = lb + lb * 0.55 * (0.5 + 0.5 * Math.sin(performance.now() / 620));
        leds.forEach(m => { if (m.emissiveIntensity > 0.02) m.emissiveIntensity = k; });
        stepFlows(dt);
      }
      controls.update();
      renderer.render(scene, camera);
      // 每 4 幀重排一次標籤：自轉時引線要跟得上零件，停著的時候幾乎不花錢
      if (++relayout % 4 === 0) layoutLabels();
    };
    const io = typeof IntersectionObserver !== 'undefined'
      ? new IntersectionObserver(es => { visible = es.some(x => x.isIntersecting); }, { threshold: 0.02 }) : null;
    if (io) io.observe(el);
    const onVis = () => { visible = document.visibilityState !== 'hidden'; };
    document.addEventListener('visibilitychange', onVis);
    const onResize = () => {
      camera.aspect = W() / H(); camera.updateProjectionMatrix();
      renderer.setSize(W(), H());
      lead.setAttribute('viewBox', `0 0 ${W()} ${H()}`);
      layoutLabels();
    };
    window.addEventListener('resize', onResize);
    lead.setAttribute('viewBox', `0 0 ${W()} ${H()}`);
    tick();
    layoutLabels();

    function dispose() {
      alive = false;
      if (raf) cancelAnimationFrame(raf);
      if (holdT) clearTimeout(holdT);
      if (io) io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('resize', onResize);
      controls.dispose();
      scene.traverse(x => {
        if (x.geometry) x.geometry.dispose();
        if (x.material) (Array.isArray(x.material) ? x.material : [x.material]).forEach(m => m.dispose());
      });
      renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
      if (layer.parentNode) layer.parentNode.removeChild(layer);
    }

    // cam()／screen() 是給驗收腳本用的：驗「視角真的轉了」要比對相機座標
    // （canvas 沒開 preserveDrawingBuffer，readPixels 一律回 0，抓不到差異），
    // 驗「點零件」要知道某個零件現在在螢幕上的哪裡，才不是亂點一個座標碰運氣。
    const cam = () => [camera.position.x, camera.position.y, camera.position.z].map(v => +v.toFixed(2));
    const screen = (seg) => {
      const p = byIdx.find(x => x && x.seg === seg && x.groups.length);
      if (!p) return null;
      const v = new THREE.Vector3(); p.groups[0].getWorldPosition(v); v.project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (-v.y + 1) / 2 * r.height, front: v.z < 1 };
    };
    /* stats() 也是給驗收腳本用的：E2「去螢光」與 E3「零件細膩」要驗得到，
       不然只能用眼睛看 —— 那正是這個專案一直踩的坑。 */
    /* 圖九 2-2 要驗「換色票畫面真的變了」。
       canvas_hash 那一招對 WebGL 沒用（getContext('2d') 在 WebGL canvas 上回 null），
       所以改量真正被畫出去的東西：所有材質顏色的指紋。換色票這個數字一定要變。*/
    const colorSig = () => {
      let v = 0;
      byIdx.forEach(p => { if (!p) return; p.mats.forEach(m => {
        if (!m.color) return; v += m.color.r * 7.1 + m.color.g * 3.3 + m.color.b * 1.7; }); });
      return +v.toFixed(3);
    };
    /* 材質**狀態**的指紋（透明度 ＋ 自體發光），跟 colorSig（顏色）是兩回事。
       為什麼需要它：單一環節的場景（MLCC）點零件時，同環節的零件顏色本來就不會變 ——
       變的是「同環節但不是主角的那幾顆退到 --dg-sib-o」與主角的 emissive。
       只量 colorSig 的話，那張圖的「點零件真的有反應」就永遠驗不到（2026-09-22 實際踩到）。*/
    const matSig = () => {
      let v = 0;
      byIdx.forEach(p => { if (!p) return; p.mats.forEach(m => {
        v += (m.opacity == null ? 1 : m.opacity) * 3.1 + (m.emissiveIntensity || 0) * 7.7; }); });
      return +v.toFixed(3);
    };
    const stats = () => {
      let meshes = 0, maxEm = 0, idleEm = 0, maxMetal = 0, ledN = 0;
      byIdx.forEach(p => {
        if (!p) return;
        meshes += p.meshes.length;
        const sel = p.el && p.el.classList.contains('sel');
        p.mats.forEach(m => {
          if (m.userData && m.userData.led) { ledN++; return; }
          maxEm = Math.max(maxEm, m.emissiveIntensity || 0);
          // idleEmissive＝「沒被選起來的零件」的自體發光。E2 要驗的是這個：
          // 選起來的那一個本來就會提亮一點（0.22）當提示，拿它來驗會永遠是紅的。
          if (!sel) idleEm = Math.max(idleEm, m.emissiveIntensity || 0);
          maxMetal = Math.max(maxMetal, m.metalness || 0);
        });
      });
      // spinAt：所有會轉的東西現在轉到哪（弧度和）。驗「動態／靜止」要比這個數字有沒有變，
      // 不能只看 anim 旗標 —— 旗標是自己寫的，扇葉有沒有真的在轉才是使用者看到的事
      const spinAt = spinners.reduce((s, x) => s + x.rotation[x.userData.spin.axis], 0);
      /* 圖九 2-1 要驗的是「電流真的在跑」，不是「有沒有粒子物件」。
         ★ 2026-09-19 踩到：第一版的 flowAt 是「所有粒子座標的總和」——
           那是一個**幾乎不會變的數字**。粒子是沿著同一條路徑等距排 6 顆，
           整排往前推的時候，離開前面的量剛好被後面補回來，總和近乎守恆，
           取到小數第二位常常一模一樣（實測 131.68 → 131.68），驗收就誤判成「電流沒在跑」。
           這正是 DECISIONS #199 講的同一件事：**量的東西本身要真的會動**。
         改成兩個都給：
           flowT  ＝ 相位，只要在跑就單調前進，最直接
           flowAt ＝ **第一顆**粒子的座標（不是全部加起來），是使用者真的看到的位置 */
      let flowAt = 0, flowT = 0;
      flowPts.forEach(o2 => {
        const a = o2.geometry.attributes.position.array;
        flowAt += a[0] + a[1] + a[2];
        flowT += o2.userData.flow.t;
      });
      /* ★ 2026-09-22（第一層零件字彙）：**效能要量，不准憑感覺**。
         renderer.info.render 是 WebGL 真的送出去的東西：
           calls     ＝ 這一幀的 draw call 數（陣列類有沒有真的收成一個，看它就知道）
           triangles ＝ 這一幀畫了幾個三角形
         autoReset 預設是開的，所以讀到的是**上一幀**的數字（呼叫 stats() 時已經畫過很多幀了）。
         驗收用它訂上限；只看 mesh 數不夠 —— InstancedMesh 是 1 個 mesh、卻可能是 5 萬個三角形。*/
      const ri = renderer.info.render;
      return { drawCalls: ri.calls, triangles: ri.triangles,
        parts: byIdx.filter(Boolean).length, meshes, maxEmissive: +maxEm.toFixed(3),
        idleEmissive: +idleEm.toFixed(3), maxMetal: +maxMetal.toFixed(2), leds: ledN,
        spinners: spinners.length, spinAt: +spinAt.toFixed(3), anim, autoRotate: !!controls.autoRotate,
        flows: flowPts.length, flowVisible: flowAll.filter(x => x.visible).length,
        flowAt: +flowAt.toFixed(3), flowT: +flowT.toFixed(4), pal, colorSig: colorSig(), matSig: matSig(),
        chips: el.querySelectorAll('.lbl3d .chip3d').length };
    };
    /* 給驗收腳本用：「這個畫面座標打得到零件嗎」。
       驗「點背景要全部恢復全亮」一定要先找到一個**真的是背景**的點 ——
       用猜的（例如畫布左上角）會踩到標籤或剛好打到零件，那一條就變成隨機紅燈。 */
    const hitAt = (x, y) => {
      toNdc({ clientX: x, clientY: y });
      const m = hit();
      return m ? (m.userData.part || m.userData.seg || '?') : null;
    };
    const view = {
      highlight, cam, screen, stats, setAnim, hitAt,
      // 圖九 2-2：色票
      setPal: (n) => applyPal(n), pal: () => pal, pals: () => PALS.slice(), palName: (n) => PAL_NAME[n] || n,
      isAnim: () => anim,
      /* N1：切換左鍵拖曳的行為 —— 'rotate'（預設，繞著轉）或 'pan'（抓著移動）。
         右鍵一律保持平移，中鍵一律縮放，這樣習慣右鍵的人也不受影響。*/
      setDrag: (mode) => {
        const B = mods.THREE.MOUSE;
        controls.mouseButtons = {
          LEFT: mode === 'pan' ? B.PAN : B.ROTATE,
          MIDDLE: B.DOLLY,
          RIGHT: B.PAN,
        };
        renderer.domElement.style.cursor = mode === 'pan' ? 'move' : 'grab';
        return mode;
      },
      dragMode: () => (controls.mouseButtons && controls.mouseButtons.LEFT === mods.THREE.MOUSE.PAN ? 'pan' : 'rotate'),
      // 給驗收看的：仰角上下限（N1 要能轉到底下）
      polar: () => [+controls.minPolarAngle.toFixed(3), +controls.maxPolarAngle.toFixed(3)],
      segs: () => byIdx.filter(Boolean).map(p => p.seg),
      dispose: () => { dispose(); if (global.Rack3D.current === view) global.Rack3D.current = null; },
      /* 重設視角要跟第一次進來看到的「一模一樣」。麻煩的是 OrbitControls 內部還留著
         上一次拖曳的慣性（sphericalDelta），而且關掉阻尼時 update() 會把殘留量**整份**套上去，
         相機就會停在預設視角旁邊一兩度。先用 dampingFactor = 1 跑一次 update 把殘留吃光並歸零，
         再關阻尼重新取景，結果才是精準的。*/
      reset: () => {
        const damp = controls.enableDamping, df = controls.dampingFactor, ar = controls.autoRotate;
        controls.autoRotate = false;
        controls.enableDamping = true; controls.dampingFactor = 1;
        controls.update();
        controls.enableDamping = false;
        fitCamera();
        controls.enableDamping = damp; controls.dampingFactor = df; controls.autoRotate = ar;
        layoutLabels();
      },
      title: spec.title, sub: spec.sub,
    };
    global.Rack3D.current = view;     // 驗收腳本從這裡拿現場的相機與零件位置
    return view;
  }

  /* ---------------------------------------------------------------- 零件字彙的量測與清單
     第一層（docs/diagram_3d_upgrade.md §3）的驗收要的是兩件事：
       ① 這個 kind **真的比一顆方塊細**（三角形數有下限）
       ② 但**沒有失控**（三角形數有上限，陣列類要真的收成 InstancedMesh）
     mount() 只量得到「整個場景」，所以另外開這一支：離線建一次那個零件、數幾何。
     不開 renderer、不上畫面，量完就 dispose —— 驗收腳本可以一口氣把 30 幾個 kind 全量一遍。*/
  async function probe(kind, boxArr) {
    const { THREE } = await load();
    const B = mkBuilders(THREE);
    const build = B[kind];
    if (typeof build !== 'function') return null;
    const css = (n) => {
      try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); } catch (e) { return ''; }
    };
    const K = kit(THREE, '#8ea0c4', false, css);
    let grp;
    try { grp = build({ box: boxArr || [14, 7, 12], at: [0, 0, 0] }, K); } catch (e) {
      return { kind, error: String((e && e.message) || e) };
    }
    let meshes = 0, tris = 0, inst = 0, instTotal = 0;
    grp.traverse(x => {
      if (!x.isMesh) return;
      meshes++;
      const g = x.geometry;
      if (!g) return;
      const n = g.index ? g.index.count : (g.attributes.position ? g.attributes.position.count : 0);
      const c = x.isInstancedMesh ? x.count : 1;
      if (x.isInstancedMesh) { inst++; instTotal += c; }
      tris += (n / 3) * c;
    });
    grp.traverse(x => { if (x.geometry) x.geometry.dispose(); });
    K.mats.forEach(m => { if (m.dispose) m.dispose(); });
    return { kind, meshes, instanced: inst, instances: instTotal, tris: Math.round(tris), mats: K.mats.length };
  }
  /* 目前有哪些 kind（`_` 開頭的是共用件，不是零件本身）。
     場景設定裡寫了字彙表沒有的 kind 會安靜退回方塊 —— 有這支就查得出來是哪一個。*/
  async function kinds() {
    const { THREE } = await load();
    return Object.keys(mkBuilders(THREE)).filter(k => k[0] !== '_');
  }

  global.Rack3D = { supported, hasScene, mount, SCENES, probe, kinds, current: null };
})(window);
