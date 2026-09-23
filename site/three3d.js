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
  /* ★ 2026-09-22 兩種模式（DECISIONS #238，Andy 的三個推薦）之後，每個零件多了三個可選欄位：
       role  ＝ 這一塊在機器裡扮演的角色，決定它**外殼的半透明色**與卡片的顏色：
               'sig' 訊號（藍）／'pwr' 電力（橘）／'cool' 液冷與散熱（青綠）／'opt' 光（青）。
               沒寫的零件外殼走材質色（板子是板子色、金屬是金屬色）。
       mat   ＝ 材質族（'metal' | 'cer' | 'pcb' | 'cu' | 'glass' | 'plastic' | 'si' | 'sn' | 'organic'），
               沒寫就照 kind 的預設（FAMILY）。★ 零件的底色**只**來自這裡，不再來自環節色。
       ex    ＝ 爆炸拆解的位移 [dx, dy, dz]：進場時從原位慢慢拉到這裡（動畫關掉就直接停在這裡）。
               機櫃是「托盤像抽屜一樣半拉出來」，不是全散開；封裝是層與層垂直懸浮。
     場景層級：
       flows ＝ 不屬於某顆零件本身、但掛在它身上的流線（液冷水路、光訊號、風扇氣流），
               kind 決定顏色 token（--dg-fl-cool／opt／air／sig／pwr）；靜止模式時粒子停、線還在。*/
  const SCENES = {
    ai_server: {
      title: 'AI 伺服器機櫃（NVL72 式）',
      sub: '18 個運算托盤 × 4 顆 GPU；後方是 NVLink 銅背板，前方是光模組，側邊是電源與液冷',
      camera: [86, 62, 96], target: [0, 34, 0], fit: 1,
      parts: [
        { seg: 'assembly', part: 'ag_rack', name: '機櫃與機構件', note: '19吋機櫃、滑軌、鈑金；整櫃出貨前做燒機與水路壓測',
          kind: 'rack', box: [52, 84, 40], at: [0, 42, 0], frame: true, mat: 'glass' },
        { seg: 'switch', part: 'ag_backplane', name: 'NVLink 銅背板', note: '機櫃內把 72 顆 GPU 連成一台（scale-up）；走銅不走光',
          kind: 'backplane', box: [46, 52, 3], at: [0, 44, -17], role: 'sig', ex: [0, 0, -7] },
        { seg: 'switch', part: 'ag_nvswitch', name: 'NVSwitch 托盤', note: 'NVLink 交換晶片，9 台夾在運算托盤之間',
          kind: 'tray', box: [44, 2.2, 30], at: [0, 62, 1], n: 3, gap: 6, axis: 'y', role: 'sig', ex: [0, 0, 7] },
        { seg: 'adv_pkg', part: 'ag_gpu', name: '運算托盤 · GPU 模組', note: 'CoWoS-L 封裝：邏輯晶粒（SoIC 堆疊）＋ HBM 放在中介層上',
          kind: 'gpu', box: [9, 2.6, 9], at: [0, 34, 2], n: 4, gap: 10, axis: 'x', role: 'gpu', ex: [0, 0, 11] },
        { seg: 'foundry', part: 'ag_cpu', name: 'CPU（Grace / x86）', note: '與 GPU 同板 C2C 連接，負責排程與資料搬運',
          kind: 'chip', box: [7, 2, 7], at: [0, 34, -11], n: 2, gap: 34, axis: 'x', ex: [0, 0, 11] },
        { seg: 'hbm', part: 'ag_hbm', name: 'HBM4 記憶體', note: '12–16 層 DRAM 用 TSV 打通；base die 改用邏輯製程、由晶圓代工做',
          kind: 'hbm', box: [3, 3.2, 3], at: [0, 34.4, 9], n: 4, gap: 10, axis: 'x', ex: [0, 0, 11] },
        /* 運算托盤：六塊板子整排像抽屜一樣**半拉出**（+z 11，托盤深 32 的三分之一），
           板上的 GPU／CPU／HBM／CCL 跟著同一個位移走，拉出來之後晶片才看得見。*/
        { seg: 'hdi_pcb', part: 'ag_pcb', name: '主機板 高階 PCB', note: '托盤底板，50 層以上 MLB／30 層以上 UBB（金像電）；IC 載板是另一個環節（欣興/南電/景碩），供應商完全不同',
          kind: 'pcb', box: [46, 1.2, 32], at: [0, 31, 0], n: 6, gap: 8, axis: 'y', ex: [0, 0, 11] },
        /* CCL 的卡片色走紅銅（v3 badge 08 橙）：它就是「銅箔」貼在基板上；剖面本身照舊是銅／介電交疊。*/
        { seg: 'ccl', part: 'ag_ccl', name: 'CCL 銅箔基板', note: 'M8/M9 以上超低損耗板材，Df ≤ 0.002 @10GHz；PCB 的原料',
          kind: 'laminate', box: [46, 0.9, 32], at: [0, 29.9, 0], role: 'cu', ex: [0, 0, 11] },
        { seg: 'thermal', part: 'ag_cdu', alias: ['ag_coldplate'], name: '液冷冷板 / CDU', note: '冷板貼晶片 → UQD 快接頭 → manifold 分歧管 → CDU → 機房一次側',
          kind: 'cdu', box: [4.5, 64, 4.5], at: [31, 38, 0], role: 'cool', ex: [6, 0, 0] },
        /* 快接頭走亮橙（v3 §2：亮橙＝電力／快接頭） */
        { seg: 'thermal', part: 'ag_uqd', name: 'UQD 快接頭 / manifold', note: '漏液是 2026 年最被盯的品質風險；OCP 有規格',
          kind: 'uqd', box: [4, 3, 4], at: [24, 20, 12], n: 3, gap: 14, axis: 'y', role: 'pwr', ex: [5, 0, 0] },
        /* 2026-09-18 新增：Andy 舉的例子就是「風扇有扇片」。真的機櫃後門本來就有風扇牆，
           原本的場景整個漏掉這一段，等於把散熱只畫了液冷那一半。
           v3：風扇排的是熱風 → 角色 hot（卡片 11 紅），氣流線本身仍是淡藍白（air）。*/
        { seg: 'thermal', part: 'ag_fan', name: '後門風扇模組', note: '液冷之外仍要帶走記憶體與電源的熱；風扇牆掛在後門',
          kind: 'fan', box: [13, 13, 5], at: [0, 24, 19], n: 3, gap: 15, axis: 'x', role: 'air', ex: [0, 0, 9] },
        { seg: 'power', part: 'ag_psu', name: '電源櫃 PSU', note: '今天是 415V AC 進 PSU → 機櫃內 DC busbar；800V HVDC 是下一世代',
          kind: 'psu', box: [22, 5, 30], at: [0, 13, 0], n: 3, gap: 6, axis: 'y', role: 'pwr', ex: [0, -2, 9] },
        { seg: 'power', part: 'ag_bbu', name: 'BBU 電池 / 超級電容', note: '掉電到柴發接手之間撐住；超電處理 GPU 毫秒級功率突波',
          kind: 'battery', box: [18, 4, 26], at: [0, 4, 0], role: 'pwr', ex: [0, -7, 0] },
        { seg: 'optical', part: 'ag_optic', name: '光模組 / CPO', note: '800G–1.6T 前面板可插拔；CPO 把光引擎搬到交換 ASIC 旁',
          kind: 'optic', box: [2.4, 1.4, 8], at: [0, 72, 15], n: 8, gap: 4.4, axis: 'x', role: 'opt', ex: [0, 3, 7] },
        { seg: 'switch', part: 'ag_tor', name: 'ToR 交換器', note: '跨機櫃那張網（scale-out）：InfiniBand 或 Ethernet',
          kind: 'switch', box: [46, 4, 30], at: [0, 76, 0], role: 'sig', ex: [0, 3, 0] },
        { seg: 'hyperscaler', part: 'ag_csp', name: '雲端業者 / Neocloud', note: '終端需求：CSP、主權 AI、Neocloud',
          box: [26, 4, 18], at: [0, 88, 0], ghost: true, mat: 'glass', ex: [0, 4, 0] },
      ],
      /* 流線（Andy 2026-09-22 推薦一：發光流線）。座標是**爆炸之後**的位置。
         cool：CDU → 頂部 manifold → 沿機櫃後方往下 → 回到 CDU 底部（一個迴路）
         opt ：光模組往前面板外送出去
         air ：三顆風扇各一條往後吹的氣流細線 */
      flows: [
        /* 冷水去程（螢光藍）從 CDU 頂端沿機櫃後方往下送；熱水回程（發光紅）從底部沿另一側回到 CDU（v3 §3-09）*/
        { kind: 'cold', part: 'ag_cdu', r: 0.7, per: 14, speed: 0.16,
          pts: [[37, 70, 0], [30, 74, -8], [0, 72, -13], [-16, 60, -13], [-16, 24, -13], [0, 12, -12], [30, 8, -6], [37, 8, 0]] },
        { kind: 'hot', part: 'ag_cdu', r: 0.6, per: 12, speed: 0.14,
          pts: [[37, 12, 4], [30, 10, 10], [-20, 12, -6], [-20, 56, -9], [0, 68, -9], [30, 66, -4], [37, 62, 2]] },
        { kind: 'opt', part: 'ag_optic', r: 0.35, per: 10, speed: 0.4,
          pts: [[0, 75, 23], [6, 80, 34], [22, 88, 44]] },
        { kind: 'airline', part: 'ag_fan', line: true, per: 8, speed: 0.3,
          pts: [[-15, 24, 30], [-16, 27, 40], [-19, 31, 50]] },
        { kind: 'airline', part: 'ag_fan', line: true, per: 8, speed: 0.3,
          pts: [[0, 24, 30], [0, 28, 40], [0, 33, 50]] },
        { kind: 'airline', part: 'ag_fan', line: true, per: 8, speed: 0.3,
          pts: [[15, 24, 30], [16, 27, 40], [19, 31, 50]] },
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
      /* 爆炸拆解（ex）：層與層**垂直懸浮**。同一層的東西（矽橋埋在中介層裡、HBM 站在微凸塊上）
         給同一個位移，拆開之後仍看得出誰跟誰是一組。*/
      parts: [
        { seg: 'abf_pcb', part: 'icp_sub', name: 'ABF 載板', note: 'core ＋ 增層，雷射盲孔電鍍銅；把幾萬個接點扇出到主機板。表面看得到蛇行等長的走線',
          kind: 'substrate', box: [44, 3, 34], at: [0, 1.5, 0] },
        { seg: 'abf_pcb', part: 'icp_bga', name: 'BGA 錫球', note: '載板背面那一整片球，接到主機板；全圖最大的接點',
          kind: 'balls', box: [2, 1.6, 2], at: [0, -0.4, -12], n: 6, gap: 7.2, axis: 'x', ex: [0, -3, 0] },
        /* ★ 2026-09-22 新增：正面去耦電容。晶粒瞬間抽電時來不及等主機板，
           就近由載板上的電容頂著 —— 這是「板子上真的有被動元件」最基本的一件事。
           `mlccchip` 的識別特徵是端電極包住端部五個面，轉到背面看得到。*/
        { seg: 'passive_comp', part: 'icp_decap', name: '載板正面的去耦電容', note: '晶粒一瞬間抽大電流，等主機板送電來不及，由這排電容就近補；端電極包住端部五個面',
          kind: 'mlccchip', box: [2.6, 1.1, 1.5], at: [0, 3.55, 14.5], n: 6, gap: 4.4, axis: 'x',
          codes: ['2327', '2492', '3026', '6173'], chipnote: '做 MLCC 的那幾家（不在半導體鏈的環節名單上）' },
        { seg: 'passive_comp', part: 'icp_lsc', name: '背面去耦電容 LSC', note: '正面擺不下就往背面擺，夾在 BGA 球陣列中間；代價是那一塊的錫球要讓位',
          kind: 'mlccchip', box: [2.6, 1.0, 1.5], at: [0, -0.5, 6], n: 3, gap: 5.2, axis: 'x', ex: [0, -3, 0],
          codes: ['2327', '2492', '3026', '6173'], chipnote: '做 MLCC 的那幾家（不在半導體鏈的環節名單上）' },
        /* ★ 2026-09-22 新增：兩層接點。box 的高度 0.9 vs 0.55 刻意差一倍 ——
           2D 整張圖的靈魂就是「接點由下往上一路變小」，3D 不表達出來就等於少了一半。*/
        { seg: 'adv_pkg', part: 'icp_c4', name: 'C4 凸塊', note: '接「載板 ↔ 中介層」，節距 150–200 µm 級；迴焊之後塌成鼓形',
          kind: 'bump', box: [36, 0.9, 26], at: [0, 3.45, 0], codes: ['2330', '3711'], ex: [0, 3, 0] },
        { seg: 'adv_pkg', part: 'icp_interposer', alias: ['icp_rdl'], name: '中介層：有機重佈線（CoWoS-L）', note: '2026 主力是 L 不是 S：有機 RDL ＋ 局部矽橋，不是一整片矽中介層',
          kind: 'rdl', box: [36, 1.6, 26], at: [0, 4.7, 0], codes: ['2330', '3711'], mat: 'organic', ex: [0, 6, 0] },
        { seg: 'adv_pkg', part: 'icp_cowos_l', name: 'LSI 局部矽橋', note: '只埋在兩顆晶粒的交界正下方，負責 die-to-die 的高密度連線 —— 要高密度的地方才用到矽',
          kind: 'bridge', box: [6, 1, 10], at: [0, 5.1, 0], n: 2, gap: 12, axis: 'x', codes: ['2330', '3711'], mat: 'si', ex: [0, 6, 0] },
        { seg: 'adv_pkg', part: 'icp_ubump', name: '微凸塊 µbump', note: '接「中介層 ↔ 晶粒」，銅柱＋錫帽，節距 30–60 µm 級 —— 比下面的 C4 小一個數量級',
          kind: 'bump', box: [30, 0.55, 22], at: [0, 5.85, 0], codes: ['2330', '3711'], ex: [0, 9, 0] },
        { seg: 'foundry', part: 'icp_die', name: 'GPU 晶粒（SoIC 堆疊）', note: '先 SoIC 混合鍵合疊兩顆（銅對銅、無凸塊），再進 CoWoS-L；四周那一圈空白是切割道',
          kind: 'die', box: [14, 2.4, 14], at: [0, 7.4, 0], ex: [0, 12, 0] },
        { seg: 'adv_pkg', part: 'icp_soic', name: 'SoIC 上層晶粒', note: '3D 堆疊的第二顆，銅墊直接對銅墊，中間沒有任何凸塊',
          kind: 'die', box: [12, 1.8, 12], at: [0, 9.5, 0], codes: ['2330', '3711'], ex: [0, 15, 0] },
        { seg: 'hbm', part: 'icp_hbm', name: 'HBM4 堆疊', note: '12–16 層 DRAM ＋ TSV ＋ base die（邏輯製程，台廠位置在這）；貼著晶粒放，線越短越省電',
          kind: 'hbm', box: [7, 5.4, 11], at: [0, 8.9, 0], n: 2, gap: 26, axis: 'x', ex: [0, 12, 0] },
        { seg: 'adv_pkg', part: 'icp_uf', name: 'Underfill / MUF', note: '底填膠，撐住凸塊並分散應力；側面會爬出一圈圓角。膠的材料以日商為主',
          box: [34, 0.8, 24], at: [0, 5.9, 0], ghost: true, mat: 'glass', codes: ['2330', '3711'], ex: [0, 9, 0] },
        { seg: 'adv_pkg', part: 'icp_stiff', name: 'Stiffener 補強環', note: '圍在載板邊緣的一圈金屬框，大尺寸封裝防翹曲',
          box: [44, 3.4, 3], at: [0, 4.7, 0], n: 2, gap: 31, axis: 'z', codes: ['2330', '3711'], mat: 'metal' },
        /* ★ 2026-09-21 更正：以前掛 `osat_test`，那是**封測服務廠**（日月光、力成、京元電、矽格…）。
           做探針卡與測試座的是 `test_interface`（6515 穎崴、6223 旺矽、6510 中華精測、6683 雍智）——
           **設備耗材 ≠ 封測服務**，這正是 AGENTS 半導體鏈那節第 3 條點名的錯。
           掛錯的後果不是「少列幾家」，是**點下去列出一批不做這個東西的公司**。 */
        { seg: 'test_interface', part: 'icp_probe', name: '探針卡 / 測試座', note: 'CP 晶圓測試與 FT 成品測試；AI 晶片測試時間長，是良率成本大宗',
          kind: 'probe', box: [10, 1.2, 10], at: [26, 2, 18], mat: 'cer' },
        { seg: 'osat_test', part: 'icp_lid', name: '散熱上蓋 + TIM', note: 'TIM1 在晶粒↔上蓋、TIM2 在上蓋↔冷板；上蓋的腳踩在載板邊緣',
          kind: 'lid', box: [40, 2.2, 30], at: [0, 12.6, 0], ghost: true, mat: 'glass', ex: [0, 20, 0] },
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
      /* 爆炸拆解：陶瓷本體往上抬出端電極、焊墊往下沉 —— 拆開才看得出「端電極是包住端部的一段」。*/
      parts: [
        { seg: 'passive_comp', part: 'mlcc_body', name: '陶瓷本體與交錯電極', note: '介電層 0.5–2 µm、內電極鎳 Ni 約 0.5 µm；一端進、另一端留餘白，兩把梳子互插但不相碰',
          kind: 'mlcc', box: [62, 30, 30], at: [0, 22, 0], ex: [0, 9, 0],
          codes: ['2327', '2492', '3026', '6173'], chipnote: '「被動元件 MLCC」族群的台股' },
        { seg: 'passive_comp', part: 'mlcc_term', alias: ['mlcc_term_cons', 'mlcc_term_auto'], name: '端電極（Cu → Ni → Sn）', note: '銅膏約 800–900 °C 燒附 → 鍍 Ni 阻障 → 鍍 Sn 助焊；車規在 Cu 與 Ni 之間多一層導電樹脂（軟端子）',
          kind: 'mlccterm', box: [62, 30, 30], at: [0, 22, 0], anchor: [-34, 19, 0],
          codes: ['2327', '2492', '3026', '6173'], chipnote: '「被動元件 MLCC」族群的台股' },
        { seg: 'passive_comp', part: 'mlcc_pad', name: 'PCB 焊墊與焊錫', note: '板子受力 → 應力從焊點傳進陶瓷 → 板彎裂（flex crack）；車規靠軟端子擋這一刀',
          kind: 'mlccpad', box: [86, 4, 44], at: [0, 2, 0], ex: [0, -8, 0] },
      ],
    },
    /* ===== 半導體鏈：晶圓代工 ===== */
    /* 2D 是 `site/dg/foundry.js`，`part` 沿用它的 `data-part`（fd_*）——
       2D 點完一個零件再切到 3D，還是同一個零件被選著。
       構圖：三顆電晶體並排在同一塊基板上（左：平面、中：FinFET、右：GAA），右邊一片 12 吋晶圓。
       三顆刻意用同一個畫法，因為這三格的意義就在「可以互相比較」。
       ⚠ 從晶圓到晶粒再到電晶體差七個數量級（300 mm 對 nm），所以這張一律是誇張放大的示意圖。*/
    foundry: {
      title: '晶圓代工：一顆電晶體與一個製程迴圈（立體）',
      sub: '左到右＝閘極管得到 1 面（平面）→ 3 面（FinFET）→ 4 面（GAA）；金色薄片就是「被閘極管到的那一面」，數得出來。右邊是 12 吋晶圓與晶粒陣列。示意圖，非實物比例',
      camera: [56, 58, 96], target: [10, 8, 4], fit: 0.88, hk: 0.58,
      parts: [
        { seg: 'foundry', part: 'fd_sub', name: '矽基板', note: '三顆共用同一塊基板、同一個位置、同一個顏色 —— 三格要能互相比較，用不同畫法讀者就比不了',
          kind: 'wbglay', box: [100, 3, 30], at: [-4, 1.5, -10], k: -0.4, ex: [0, -12, 0],
          codes: ['6488', '5483', '6182', '3532', '8028'], chipnote: '做 12 吋矽晶圓的台股（不在半導體鏈的環節名單上，見「矽晶圓」那張）' },
        { seg: 'foundry', part: 'fd_planar', name: '平面電晶體（閘極管 1 面）', note: '通道是基板表面下一條水平薄層，閘極只從正上方蓋下來 —— 只管得到一面，其餘三面關不住',
          kind: 'fetp', box: [30, 17, 24], at: [-38, 11.5, -10], ex: [-14, 9, 0] },
        { seg: 'foundry', part: 'fd_fin', name: 'FinFET 鰭式（閘極管 3 面）', note: '把通道立起來變成一片直立的鰭，閘極就罩得住頂面與兩個側面；鰭底埋在 STI 裡的那一段管不到',
          kind: 'fetf', box: [30, 17, 24], at: [-4, 11.5, -10], ex: [0, 11, 0],
          codes: ['2330'], chipnote: 'FinFET 先進節點在台股由台積電承擔（2D 那張圖的同一句話）' },
        { seg: 'foundry', part: 'fd_sheet', name: '奈米片通道（GAA）', note: '2～4 片水平堆疊、彼此不相連；片寬遠大於片厚 —— 正方形斷面那是奈米線，不是奈米片。源汲磊晶把所有片的端部一起接起來',
          kind: 'nsheet', box: [30, 17, 24], at: [30, 11.5, -10], ex: [12, 9, 0],
          codes: ['2330'], chipnote: 'GAA 奈米片節點（N2）目前在台股只有台積電做得到' },
        { seg: 'foundry', part: 'fd_gaa', name: '閘極金屬（全包覆，4 面）', note: '★「Gate-All-Around」的全部意義：金屬填進每一對相鄰奈米片之間的縫，最下面那片的下方也有。只畫在最上面＝畫的是 FinFET。拆開看得到那幾片梳齒',
          kind: 'gaagate', box: [30, 17, 24], at: [30, 11.5, -10], ex: [12, 26, 0],
          codes: ['2330'], chipnote: 'GAA 奈米片節點（N2）目前在台股只有台積電做得到' },
        { seg: 'foundry', part: 'fd_wafer', name: '12 吋晶圓與晶粒陣列', note: '圓片＋一個方位缺口（notch）＋規則排列的晶粒。邊緣那一圈暗的是切不出完整晶粒的格子 —— 晶圓越大，浪費掉的邊緣比例越小。格數為示意',
          kind: 'wafer', box: [38, 2.4, 38], at: [58, 1.2, 28], dies: 10, ex: [14, -6, 12],
          codes: ['6488', '5483', '6182', '3532', '8028'], chipnote: '做 12 吋矽晶圓的台股（不在半導體鏈的環節名單上）' },
        { seg: 'foundry', part: 'fd_die', name: '一顆晶粒', note: '晶圓上被切線分開的一格；四周那一圈空白是切割道。同一個缺陷密度下，晶粒越大、報廢的比例越高（本圖不寫任何良率數字）',
          kind: 'die', box: [9, 2.8, 9], at: [58, 9, 28], ex: [14, 14, 12] },
      ],
    },
    /* ===== 半導體鏈：矽晶圓 ===== */
    /* 2D 是 `site/dg/silicon_wafer.js`。那張圖的 §0-A 寫「不做真 3D，長晶爐是旋轉對稱體」——
       這裡做的是**切開的**長晶爐（開口約 117° 朝向預設相機），轉一圈看得到的兩件事
       剛好就是那張圖最重要的兩件事：坩堝裡有液面、晶碇正從液面往上長。
       ⚠ 爐內的氣氛與熱屏配置本圖沒有查證，所以只畫外殼與加熱器，不畫配置。
       ⚠ 這張圖**沒有對應的供應鏈環節**（半導體鏈 14 格裡沒有一格是矽晶圓），
          所以台股一律用零件自己的 `codes` 列，不走環節名單。*/
    silicon_wafer: {
      title: '矽晶圓：從熔湯到一片鏡面（切開的長晶爐）',
      sub: '柴氏（CZ）提拉法：石英坩堝裡的熔湯 → 籽晶沾上去 → 一邊轉一邊往上拉 → 頸縮、肩、等徑段。右邊是線鋸切好的一疊與最上面那片拋光鏡面片。示意圖，非實物比例',
      camera: [66, 62, 96], target: [2, 26, 0], fit: 1.05, hk: 0.68,
      parts: [
        { seg: 'silicon_wafer', part: 'sw_chamber', name: '爐體（切開）', note: '長晶要在受控氣氛與受控熱場裡進行。爐內的氣氛與熱屏配置本圖沒有查證，所以只畫外殼、不寫配置；朝鏡頭那一段切掉才看得見裡面',
          kind: 'czshell', box: [38, 56, 38], at: [-18, 28, 0], ex: [0, 32, 0] },
        { seg: 'silicon_wafer', part: 'sw_heater', name: '加熱器', note: '環繞在坩堝的側面（不是裝在爐子頂上）。熱場決定長晶速度與缺陷密度；石墨加熱器是一整條折來折去的帶子，所以上下各有一道連接環',
          kind: 'heater', box: [32, 24, 32], at: [-18, 15, 0], ex: [-26, 4, -14] },
        { seg: 'silicon_wafer', part: 'sw_susceptor', name: '石墨承座（示意）', note: '包在石英坩堝外面撐住它，底下是會自己轉的軸。⚠ 這一件本圖沒有查證到可引用的來源，只畫成示意、不寫規格',
          kind: 'susceptor', box: [30, 16, 30], at: [-18, 12, 0], ex: [0, -16, 0] },
        { seg: 'silicon_wafer', part: 'sw_crucible', name: '石英坩堝', note: '裝熔湯的那個碗。它是消耗品 —— 一次長晶就報廢一個',
          kind: 'crucible', box: [27, 13, 27], at: [-18, 12.5, 0], ex: [0, -6, 0] },
        { seg: 'silicon_wafer', part: 'sw_melt', name: '熔湯（melt）', note: '多晶矽熔成的一鍋湯。★ 看得到液面才是 CZ 提拉爐 —— 碳化矽與氮化鎵用的是昇華法（PVT），爐子裡沒有液面。中央被晶碇拉起來的是彎液面',
          kind: 'melt', box: [23, 6, 23], at: [-18, 14, 0], ex: [0, 9, 0],
          codes: ['6488', '3532', '6182'], chipnote: '做長晶這一段的台股（信心：中，來源為媒體與公司網站整理；不在供應鏈資料裡）' },
        { seg: 'silicon_wafer', part: 'sw_ingot', name: '晶碇（ingot／boule）', note: '先拉細（頸縮）把差排甩掉，再放大到目標直徑（肩），中間是等徑段。畫成一根上下等粗的圓柱就少了 CZ 的識別特徵。側面那條溝是刻在整根上的 notch',
          kind: 'ingot', box: [15, 34, 15], at: [-18, 34, 0], ex: [0, 16, 0],
          codes: ['6488', '3532', '6182'], chipnote: '做長晶這一段的台股（信心：中，來源為媒體與公司網站整理）' },
        { seg: 'silicon_wafer', part: 'sw_seed', name: '籽晶與籽晶桿', note: '一顆籽晶沾上熔湯，熔湯就照著它的晶格重新排列 —— 整根柱子因此是一顆單晶。★ 方向是往上拉（畫成往下就是把柱子推進湯裡，物理上不成立）',
          kind: 'seedrod', box: [4, 17, 4], at: [-18, 58.5, 0], ex: [0, 24, 0] },
        { seg: 'silicon_wafer', part: 'sw_saw', name: '線鋸切好的一疊晶圓', note: '一組平行的鋼線同時切過去（多線鋸），一根晶碇切出上百片。整疊的 notch 在同一個方位 —— 因為缺口是切片之前就刻在晶碇上的',
          kind: 'wstack', box: [26, 13, 26], at: [34, 6.5, 0], layers: 9, ex: [16, 0, 10],
          codes: ['6488', '3532', '6182'], chipnote: '做矽晶圓的台股（信心：中，來源為媒體與公司網站整理）' },
        { seg: 'silicon_wafer', part: 'sw_polish', name: '拋光鏡面片', note: '磨到鏡面，表面在剖面上是一條直線。拋光一定是最後一道表面加工 —— 拋完再畫一段研磨就是順序錯了',
          kind: 'wafer', box: [26, 1.2, 26], at: [34, 13.8, 0], mirror: true, ex: [16, 11, 10],
          codes: ['6488', '3532', '6182'], chipnote: '做矽晶圓的台股（信心：中，來源為媒體與公司網站整理）' },
      ],
    },
    /* ===== 半導體鏈：HBM ===== */
    /* 2D 是 `site/dg/hbm.js`。切掉「x > 0 且 z > 0」那一角（切法跟 MLCC 一致），
       因為這張圖唯一的主角是**一根貫穿的柱子**：不切開就只能相信它在裡面。
       由下往上（y 是中心，不是底面）：
         載板 0–3.2 ｜ 中介層 3.4–5.2 ｜ 對外凸塊 5.2–6.2 ｜ base die 6.2–8.0
         ｜ 微凸塊與 core die 8.0–18.1（6 層，層間 6 排凸塊）｜ TSV 6.2–18.1 貫穿
         ｜ GPU 晶粒 5.2–8.1（站在中介層上，**不是**疊在 HBM 上）
       改任何一個 y 之前先回來對這一排。*/
    hbm: {
      title: 'HBM：堆疊起來的記憶體與底下那顆邏輯晶粒（切開一角）',
      sub: 'HBM 站在 GPU 旁邊、不是疊在 GPU 上面；最底下那顆不是記憶體，是邏輯晶粒（base die）。切開的那一角看得到 TSV 真的貫穿每一層，而且跟層間的微凸塊上下對齊。示意圖，非實物比例',
      camera: [58, 40, 66], target: [0, 9, 0], fit: 1.0, hk: 0.52,
      parts: [
        { seg: 'abf_pcb', part: 'hb_sub', name: '載板（package substrate）', note: '整包封裝最底下那一層。載板的內部層數、補強環與模封是「IC 載板」與「先進封裝」那兩張的範圍，這裡刻意畫得簡單',
          kind: 'substrate', box: [58, 3.2, 42], at: [0, 1.6, 0], ex: [0, -10, 0] },
        { seg: 'adv_pkg', part: 'hb_interposer', name: '中介層（interposer）', note: '提供極密的金屬繞線、垂直連接與細間距微凸塊，把每一疊 HBM 接到運算晶粒的記憶體控制器。畫成一塊空白的板子就少了它存在的理由',
          kind: 'interposer', box: [46, 1.8, 32], at: [0, 4.3, 0], ex: [0, 2, 0],
          codes: ['2330', '3711'], chipnote: '「先進封裝 CoWoS/SoIC」這一格在供應鏈資料裡沒有公司，依既有 tech 欄直接指名這兩家' },
        { seg: 'hbm', part: 'hb_outbump', name: '對外凸塊', note: 'base die 底面的一排凸塊，接到中介層。整疊 HBM 對外就是從這裡出去',
          kind: 'bump', box: [11, 1.0, 14], at: [0, 5.7, 0], n: 2, gap: 30, axis: 'x', ex: [0, 6, 0] },
        { seg: 'foundry', part: 'hb_base', name: 'base die（邏輯晶粒）', note: '★ 最底下這顆不是記憶體，是邏輯晶粒：負責對外介面與控制，上面每一層都透過 TSV 跟它交換資料。它比 core die 厚、而且不同色',
          kind: 'hbmbase', box: [11, 1.8, 14], at: [0, 7.1, 0], n: 2, gap: 30, axis: 'x', ex: [0, 10, 0],
          codes: ['2330'], chipnote: 'SK hynix 的 HBM4 base die 採台積電 12 奈米邏輯製程（來源：產業媒體 2026）。是做那顆邏輯晶粒，不是做 HBM 顆粒' },
        { seg: 'hbm', part: 'hb_ubump', name: '微凸塊（層間 6 排）', note: '夾在每兩層之間。N 層晶粒就有 N−1 排（本圖 base die ＋ 6 層 core die ＝ 7 層、6 排）。★ 它跟 TSV 上下對齊成一條連續的導通柱 —— 對不齊就電氣上接不起來',
          kind: 'ubumprows', box: [11, 9.6, 14], at: [0, 13.3, 0], layers: 6, baseRow: true, n: 2, gap: 30, axis: 'x', ex: [0, 15, 0] },
        { seg: 'hbm', part: 'hb_core', name: 'HBM 記憶體晶粒（core die）', note: '一層一層疊上去的 DRAM。本圖畫 6 層示意；實際層數依世代而定 —— 查不到可引用的層數說明，所以不寫 8-high／12-high 這種規格',
          kind: 'hbmcore', box: [11, 9.6, 14], at: [0, 13.3, 0], layers: 6, n: 2, gap: 30, axis: 'x', ex: [0, 19, 0] },
        { seg: 'hbm', part: 'hb_tsv', name: '穿矽孔（TSV）', note: '一根根垂直貫穿每一層，把上面的記憶體跟底下的邏輯晶粒接起來。只有最上面那一層可以不用 —— 但不可以只有最上層有，那把整個結構畫反了。直徑與間距查不到可引用的數字，所以不標數字',
          kind: 'tsvcol', box: [11, 11.9, 14], at: [0, 12.15, 0], n: 2, gap: 30, axis: 'x', ex: [0, 26, 0] },
        { seg: 'foundry', part: 'hb_gpu', name: '運算晶粒（GPU／ASIC）', note: '★ HBM 是站在它旁邊，不是疊在它上面 —— 兩者一起放在中介層上。疊上去是完全不同的封裝架構',
          kind: 'die', box: [17, 2.9, 17], at: [0, 6.65, 0], ex: [0, 8, 0],
          codes: ['2330'], chipnote: '先進節點晶圓代工（這一格講的是「誰代工」，不是「誰設計這顆 GPU」）' },
      ],
      /* ---- C6 運轉動畫：**訊號沿 TSV 由上而下貫穿**。
         為什麼是由上而下：HBM 的核心晶粒堆在最上面，資料要送出去一定得穿過整疊的穿矽孔（TSV）
         落到最底下的 base die（邏輯晶粒），由它做序列化之後再經中介層橫向送給 GPU。
         所以動畫是兩段：先是兩疊 HBM 的 TSV 由上往下（sig），
         再從 base die 橫著走中介層進到運算晶粒 —— 這正是 HBM 比 GDDR 快的原因（路徑短、位元寬）。
         兩疊記憶體分別在 x = ±15（n: 2、gap: 30）。*/
      flows: [
        { kind: 'sig', part: 'hb_tsv', r: 0.32, per: 10, speed: 0.55, pts: [[-15, 19, -4], [-15, 12, -4], [-15, 7.4, -4]] },
        { kind: 'sig', part: 'hb_tsv', r: 0.32, per: 10, speed: 0.55, pts: [[-15, 19, 4], [-15, 12, 4], [-15, 7.4, 4]] },
        { kind: 'sig', part: 'hb_tsv', r: 0.32, per: 10, speed: 0.55, pts: [[15, 19, -4], [15, 12, -4], [15, 7.4, -4]] },
        { kind: 'sig', part: 'hb_tsv', r: 0.32, per: 10, speed: 0.55, pts: [[15, 19, 4], [15, 12, 4], [15, 7.4, 4]] },
        /* base die → 中介層 → 運算晶粒（橫向，這一段才是「1024 bit 寬匯流排」）*/
        { kind: 'sig', part: 'hb_interposer', r: 0.3, per: 12, speed: 0.5, pts: [[-15, 6.2, 0], [-9, 5.2, 0], [0, 6.4, 0]] },
        { kind: 'sig', part: 'hb_interposer', r: 0.3, per: 12, speed: 0.5, pts: [[15, 6.2, 0], [9, 5.2, 0], [0, 6.4, 0]] },
        /* 供電是**反向**的：從載板往上餵給核心晶粒（dir: -1 讓同一條路反著跑）*/
        { kind: 'pwr', part: 'hb_sub', r: 0.26, per: 8, speed: 0.3, dir: -1, pts: [[-24, 3.4, 12], [-20, 5.6, 12], [-15, 8, 12], [-15, 16, 12]] },
      ],
      /* 訊號穿層：核心晶粒 → 微凸塊 → TSV → base die → 中介層 → 運算晶粒，一顆一顆接力點亮 */
      pulses: [{ parts: ['hb_core', 'hb_ubump', 'hb_tsv', 'hb_base', 'hb_interposer', 'hb_gpu'], period: 2.6, kind: 'sig' }],
    },
    /* ===== 半導體鏈：第三代半導體 ===== */
    /* 2D 是 `site/dg/wide_bandgap.js`。兩顆元件並排、切掉同一個角：
       左邊 SiC MOSFET 是**垂直**元件（汲極在背面），右邊 GaN HEMT 是**橫向**元件
       （源／閘／汲三個電極全在上表面、背面一個都沒有）。
       這一組對比是整張圖最重要的視覺事實，而它只有「兩顆擺在一起、正反面都看得到」才成立。
       ⚠ 這張圖**沒有對應的供應鏈環節**，台股一律用零件自己的 `codes` 列。
       ⚠ 基板（長晶／切片／研磨拋光）那三段本圖查不到台股的具名對應，所以那兩個零件刻意留空。*/
    wide_bandgap: {
      title: '第三代半導體：SiC 與 GaN 功率元件（立體剖面）',
      sub: '左：SiC MOSFET —— 電流垂直穿過整片晶片，汲極在背面，耐壓靠漂移層的厚度。右：GaN HEMT —— 電流橫著在表面下跑，三個電極全在上表面。示意圖，非實物比例',
      camera: [58, 44, 96], target: [0, 11, 0], fit: 1.02, hk: 0.46,
      parts: [
        { seg: 'wide_bandgap', part: 'wbg_sic_drain', name: 'SiC：汲極金屬（背面）', note: '在背面。電流從正面的源極穿過整片晶片到這裡 —— 三個電極畫在同一面就是 GaN HEMT，不是 SiC MOSFET',
          kind: 'wbglay', box: [40, 2.4, 32], at: [-32, 1.2, 0], tint: '--dg-m-rack', metal: 0.86, rough: 0.3, ex: [0, -9, 0],
          codes: ['3707'], chipnote: '做元件製造這一段的台股（背面金屬跟正面金屬是同一段製程，信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_sic_sub', name: 'SiC：n⁺ 基板', note: '機械支撐＋導電。這一片的品質決定上面能不能長出好磊晶 —— 微管與基面差排這類缺陷在長晶那一步就決定了，後面救不回來。它比漂移層厚得多',
          kind: 'wbglay', box: [40, 7, 32], at: [-32, 6.2, 0], k: -0.32, ex: [0, -4, 0] },
        { seg: 'wide_bandgap', part: 'wbg_sic_drift', name: 'SiC：n⁻ 漂移層（磊晶）', note: '這一層的厚度就是耐壓。寬能隙 → 崩潰電場高 → 同樣耐壓只要更薄的一層 → 電阻低、損耗小。它比底下的基板薄得多，因為它是長上去的、不是切出來的',
          kind: 'wbglay', box: [40, 5, 32], at: [-32, 12.2, 0], k: 0.08, ex: [0, 3, 0],
          codes: ['3016'], chipnote: '做磊晶這一段的台股（信心：中，來源為投資研究平台整理；不在供應鏈資料裡）' },
        { seg: 'wide_bandgap', part: 'wbg_sic_body', name: 'SiC：p-body 與 n⁺ 源極區', note: '通道就在 p-body 的表面；兩個 p-body 之間被夾成的那條窄路就是 JFET 區（只有平面閘才有）。★ n⁺ 源極區一定被 p-body 包住，碰到 n⁻ 漂移層就等於把元件短路掉了',
          kind: 'wbgbody', box: [40, 3.4, 32], at: [-32, 16.4, 0], ex: [0, 8, 0],
          codes: ['3707'], chipnote: '做元件製造這一段的台股（SiC／GaN 功率半導體晶圓代工，信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_sic_gox', name: 'SiC：閘極氧化層 ＋ 閘極', note: '氧化層夾在閘極與半導體之間，是全圖最薄的一層之一 —— ★ 沒有這一層就不叫 MOSFET（閘極直接碰到半導體那是 JFET 或 HEMT）。它同時是 SiC 的長期可靠度課題之一',
          kind: 'wbggate', box: [16, 2.6, 32], at: [-32, 19.4, 0], ex: [0, 13, 0],
          codes: ['3707'], chipnote: '做元件製造這一段的台股（信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_sic_src', name: 'SiC：源極金屬（正面）', note: '蓋住正面大部分，靠接觸窗下去接到 n⁺ 源極與 p-body。它和閘極在同一面、和背面的汲極分屬兩側 —— 這就是「垂直元件」的定義',
          kind: 'wbgtop', box: [40, 2.6, 32], at: [-32, 21.9, 0], ex: [0, 16.5, 0],
          codes: ['3707'], chipnote: '做元件製造這一段的台股（信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_gan_sub', name: 'GaN：基板（Si 或 SiC）', note: 'GaN 功率元件多半長在 Si 或 SiC 基板上。Si 便宜且相容既有 CMOS 廠，但晶格失配大、緩衝層要厚；SiC 導熱好、失配小，但貴',
          kind: 'wbglay', box: [40, 7, 32], at: [32, 3.5, 0], k: -0.32, ex: [0, -8, 0] },
        { seg: 'wide_bandgap', part: 'wbg_gan_buf', name: 'GaN：緩衝層（AlN／AlGaN）', note: '厚薄由基板決定：長在 Si 上晶格差約 17%，要厚過渡；長在 SiC 上只差約 3.5%，可以薄很多。兩者畫成一樣厚就是把這件事抹掉了',
          kind: 'wbglay', box: [40, 3.6, 32], at: [32, 8.8, 0], k: -0.06, ex: [0, -3, 0],
          codes: ['3016'], chipnote: '做磊晶這一段的台股（信心：中，來源為投資研究平台整理）' },
        { seg: 'wide_bandgap', part: 'wbg_gan_ch', name: 'GaN：通道層', note: '2DEG 就長在它的上表面。它比上面的 AlGaN 阻障層厚',
          kind: 'wbglay', box: [40, 2.2, 32], at: [32, 11.7, 0], k: 0.22, ex: [0, 3, 0],
          codes: ['3016'], chipnote: '做磊晶這一段的台股（信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_2deg', name: 'GaN：二維電子氣（2DEG）', note: 'AlGaN 與 GaN 貼在一起，界面自己長出一層電子（極化誘發）。★ 它在界面的 GaN 那一側，不是在 AlGaN 裡、也不是在兩層正中央。電子跑得快，所以切換可以到 MHz 級',
          kind: 'wbglay', box: [40, 0.6, 32], at: [32, 13.1, 0], tint: '--dg-m-trace', metal: 0.9, rough: 0.26, ex: [0, 7, 0] },
        { seg: 'wide_bandgap', part: 'wbg_gan_bar', name: 'GaN：AlGaN 阻障層', note: '比底下的 GaN 通道層薄。它和 GaN 的界面就是 2DEG 的所在，三個電極都做在它的上表面',
          kind: 'wbglay', box: [40, 1.3, 32], at: [32, 14.05, 0], k: 0.5, ex: [0, 11, 0],
          codes: ['3016'], chipnote: '做磊晶這一段的台股（信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_pgan', name: 'GaN：p-GaN 閘（常關做法之一）', note: 'GaN 原生是「常開」的（零偏壓下 2DEG 就導通）。在 AlGaN 上長一層 p 型 GaN，內建電位把閘極底下的 2DEG 耗盡，零偏壓時就不導通。★ p-GaN 一定在閘極金屬與 AlGaN 之間',
          kind: 'wbgpgan', box: [8, 1.2, 24], at: [32, 15.3, 0], ex: [0, 16, 0],
          codes: ['3707'], chipnote: '做元件製造這一段的台股（信心：中）' },
        { seg: 'wide_bandgap', part: 'wbg_gan_elec', name: 'GaN：源極／閘極／汲極（都在上表面）', note: '★ 三個電極全部做在同一個上表面、背面一個都沒有 —— 這就是「橫向元件」。也正因為是橫向，它受表面崩潰限制，主流停在 650V 級。中間那顆閘極站在 p-GaN 上，比兩側高一階',
          kind: 'wbgelec', box: [40, 2.6, 32], at: [32, 16.0, 0], ex: [0, 19, 0],
          codes: ['3707'], chipnote: '做元件製造這一段的台股（信心：中）' },
      ],
    },
    /* ===== AI 伺服器鏈：IC 載板 ===== */
    /* 2D 是 `site/dg/ic_substrate.js`，`part` 沿用它的 `data-part`（abf_*）——
       2D 點完一個零件再切到 3D，還是同一個零件被選著。
       半剖（z > 0 整個切掉），留下一個乾淨的 z = 0 剖面：這是**一疊薄層**，
       切角只會變成「一疊缺了一角的板子」（#247 §二 已經踩過一次）。
       由下往上（y 是中心）：
         主機板 −18~−14 ｜ BGA 錫球 −13.9~−10.1 ｜ 下防焊 −10.05 ｜ 增層 L3/L2/L1 −8.5~−3
         ｜ core −3~3 ｜ 增層 U1/U2/U3 3~9.6 ｜ 上防焊 10.05 ｜ bump pad 10.4 ｜ 晶粒剪影 16
       改任何一個 y 之前先回來對這一排；ABF 那組常數（core 6／增層 2.2／各 3 層）寫在
       mkBuilders 的 `ABF`，四支建造函式共用。*/
    ic_substrate: {
      title: 'IC 載板：ABF 增層剖面（半剖立體）',
      sub: '中間一片最厚、而且**只有它看得出玻纖織紋**的是 core；上下各三層均勻無織紋的是 ABF 增層膜。孔的形狀就是載板與硬板分家的地方：core 走直筒貫孔、增層走上寬下窄的雷射微孔，而且窄的那一端一律朝向 core。示意圖，非實物比例',
      camera: [54, 38, 90], target: [0, -1, -8], fit: 0.98, hk: 0.62,
      parts: [
        { seg: 'substrate_material', part: 'abf_core', name: '核心層 core（玻纖補強樹脂）', note: '全圖最厚、也是**唯一看得出織紋**的一層（剖面上：經紗被切斷成一排圓、緯紗順著切面成一條帶）。它的工作是撐住不變形，上下增層才有東西可以長。core 只有一片、而且在正中間 —— 畫成「兩片 core 夾膠片」就是畫成 PCB 了',
          kind: 'abfcore', box: [60, 6, 44], at: [0, 0, 0], ex: [0, 5, 0] },
        { seg: 'abf_pcb', part: 'abf_core_via', name: 'core 貫孔（鍍銅、填塞、兩端蓋銅）', note: '★ **只穿 core**，一格增層都不准穿進去 —— 它跟 PCB 那張的機械通孔（貫穿全板）不是同一件事。孔內是**填塞**的、不是空心，兩端還要蓋一片銅，上面那一層的微孔才疊得上來',
          kind: 'abfvia', v: 'core', box: [60, 6, 44], at: [0, 0, 0], ex: [0, 17, 0] },
        { seg: 'substrate_material', part: 'abf_film', name: 'ABF 增層膜（上下各 3 層）', note: '味之素的增層膜（Ajinomoto Build-up Film）。它是**膜**不是膠片，而且**不含織造玻纖** —— 畫出織紋就是結構錯誤。★ 上下層數與厚度必須相等：不對稱就翹曲，而翹曲正是這塊板子做大之後最難的一關',
          kind: 'abfbu', box: [60, 19.2, 44], at: [0, 0, 0], ex: [-28, 0, 0] },
        { seg: 'abf_pcb', part: 'abf_trace', name: '增層裡的細線路（半加成 SAP／mSAP）', note: '線寬比主機板的走線細一個量級，所以做法也不一樣：不是把整片銅蝕刻掉多餘的（減成），是先鍍一層薄銅、再把要的地方長厚（半加成）。這一段就是載板廠的門檻所在',
          kind: 'abftrace', box: [60, 19.2, 44], at: [0, 0, 0], ex: [-28, 0, 14] },
        { seg: 'abf_pcb', part: 'abf_uvia', name: '雷射微孔（錐形，窄端朝 core）', note: '★ 錐度方向是這張圖最容易錯的一條：上半部的孔**朝下**收窄、下半部的孔**朝上**收窄 —— 兩邊都是「從外面往 core 打」。只穿一層增層；畫成直筒那是機械鑽孔，畫成空心就疊不上去',
          kind: 'abfvia', v: 'micro', box: [60, 19.2, 44], at: [0, 0, 0], ex: [-28, 0, -14] },
        { seg: 'abf_pcb', part: 'abf_stack_via', name: '疊孔（stacked via）', note: '兩個微孔**軸心對齊**疊起來，中間看得到一段被電鍍填平的銅。沒有填平就不准疊 —— 上面那個孔會塌進去。疊孔讓訊號從表面直接下到深層，不必在板面上繞路',
          kind: 'abfvia', v: 'stack', box: [60, 19.2, 44], at: [0, 0, 0], ex: [-28, 12, -14] },
        { seg: 'abf_pcb', part: 'abf_sr', name: '防焊層與開窗（solder resist）', note: '上下兩面都有一層，而且**在墊子的位置開窗**（不是整片蓋滿）。開窗的位置決定焊錫黏在哪 —— 開窗開歪了，凸塊就接不到下面的銅',
          kind: 'abfsr', box: [60, 21.9, 44], at: [0, 0, 0], ex: [26, 0, 0] },
        { seg: 'abf_pcb', part: 'abf_bump_pad', name: '凸塊墊 ＋ 表面處理', note: '★ 只長在**上表面**（接晶片那一面）開窗露出來的銅上；下表面是 BGA 球墊。兩者對調就是把「上面接晶片、下面接主機板」整個講反了',
          kind: 'abfpad', box: [40, 1.4, 30], at: [0, 10.4, -11], ex: [0, 18, 0] },
        { seg: 'abf_pcb', part: 'abf_bga', name: 'BGA 錫球（載板 ↔ 主機板）', note: '三種接點裡**最大**的那一種（微凸塊 ＜ C4 凸塊 ＜ BGA 錫球，差一個量級）。迴焊之後是略扁的球，不是正圓，也不是方塊',
          kind: 'abfbga', box: [52, 3.8, 38], at: [0, -12, -11], ex: [0, -17, 0] },
        { seg: 'adv_pkg', part: 'abf_die_ghost', name: '晶粒與中介層（剪影）', note: '這一段是**別張圖的主題** —— 微凸塊、TSV、CoWoS 的 LSI 與重佈線請看半導體鏈的「先進封裝」與「HBM」。這裡只畫輪廓，是為了說明載板的上表面是接到什麼東西',
          box: [30, 6, 22], at: [0, 16, -11], ghost: true, mat: 'glass', ex: [0, 27, 0], codes: [],
          chipnote: '' },
        { seg: 'hdi_pcb', part: 'abf_motherboard', name: '主機板（只畫一小段）', note: '載板的下游。★ 它跟載板**不是同一批廠**：主機板走機械鑽的通孔、走一般減成線路（金像電、健鼎那一群），載板走雷射微孔與半加成細線（欣興、南電、景碩）。設備不同、廠不同、毛利也不同',
          kind: 'pcb', box: [66, 4, 48], at: [0, -16, -2], ex: [0, -30, 0] },
      ],
    },
    /* ===== AI 伺服器鏈：PCB 硬板 ===== */
    /* 2D 是 `site/dg/pcb_rigid.js`。同樣半剖，剖面是唯一的主角。
       疊構（規格書 pcb_stackup.md §3-A）：10 層銅、4 片芯板、5 片半固化片，上下完全對稱。
       ★ **core 一定是「銅－介電－銅」三件一組；prepreg 一定沒有銅** —— 兩者畫成同一種顏色
         是這張圖最常見也最致命的錯，所以厚度表寫死在 mkBuilders 的 `pcbStack()`，五支共用。
       四種孔並排在同一張剖面上，跨距寫死：PTH L1→L10、背鑽 L1→L4（從背面鑽、留殘餘）、
       盲孔 L1→L2、埋孔 L4→L7。*/
    pcb_rigid: {
      title: 'PCB 硬板：多層板剖面與四種孔（半剖立體）',
      sub: '一片高層數板是很多片薄板壓起來的：芯板（銅－介電－銅 三件一組）與半固化片（沒有銅）交替，上下對稱。四種孔的差別只在「從哪一層到哪一層」—— 通孔上下貫穿、背鑽從背面鑽掉用不到的那一段、盲孔只碰一個外層、埋孔兩端都碰不到外層。示意圖，非實物比例',
      camera: [56, 38, 92], target: [0, 0, -9], fit: 0.98, hk: 0.6,
      parts: [
        { seg: 'ccl', part: 'pcb_core', name: '芯板 core（銅－介電－銅）', note: '★ 它是**已經固化、而且兩面已經覆好銅**的一片 CCL。整片板子是拿好幾片芯板去疊的 —— 這就是「為什麼一片 38 層板是很多片薄板壓起來的」那句話的實體',
          kind: 'pcblay', lay: 'core', box: [64, 21, 46], at: [0, 0, 0], ex: [-32, 0, 0] },
        { seg: 'ccl', part: 'pcb_pp', name: '半固化片 prepreg（無銅）', note: '★ 它**沒有銅**，工作是把芯板黏起來。把它跟芯板畫成同一種顏色的介電層，是這張圖最常見也最致命的錯 —— 那樣就看不出層數是怎麼疊出來的',
          kind: 'pcblay', lay: 'pp', box: [64, 21, 46], at: [0, 0, 0], ex: [32, 0, 0] },
        { seg: 'ccl_material', part: 'pcb_foil', name: '銅箔（外層兩面）', note: '板子最外面那兩層銅。銅箔的**稜面粗糙度**（HTE → RTF → HVLP 越來越平）直接決定高速訊號的損耗 —— 越平損耗越小，但也越難黏住',
          kind: 'pcblay', lay: 'foil', box: [64, 21, 46], at: [0, 0, 0], ex: [0, 28, 0] },
        { seg: 'ccl_material', part: 'fiber_weave', name: '玻纖織紋（fiber weave）', note: '芯板與半固化片裡都有一層織造玻纖布。剖面上經紗被切斷成一排圓。★ 織紋會讓差動對的兩條線一條壓在玻纖上、一條壓在樹脂上，介電常數不一樣 → 兩條線速度不一樣（織效應）。這是高速板要斜著布線的原因',
          kind: 'pcblay', lay: 'weave', box: [64, 21, 46], at: [0, 0, 0], ex: [-32, 15, 0] },
        { seg: 'hdi_pcb', part: 'pcb_plane', name: '接地／電源平面（整片銅）', note: '★ **每一層高速訊號層的正上方與正下方，都必須各有一層完整的參考層。** 這一條就是「為什麼層數這麼多」的全部答案 —— 兩層訊號層直接相鄰、中間沒有地，訊號就互相串擾。平面是整片銅，不准開一堆槽',
          kind: 'pcblay', lay: 'plane', box: [64, 21, 46], at: [0, 0, 0], ex: [0, -28, 0] },
        { seg: 'hdi_pcb', part: 'pcb_trace', name: '內層線路（帶狀線差動對）', note: '夾在兩層接地之間的走線叫帶狀線。剖面上是**一對一對**的小方塊 —— 成雙才是差動對，單一根那是單端線',
          kind: 'pcbtrc', box: [64, 21, 46], at: [0, 0, 0], ex: [0, 0, -28] },
        { seg: 'hdi_pcb', part: 'pcb_top_trace', name: '頂層走線（蛇行等長、45° 轉角）', note: '外層看得到的那一組：差動對成雙並排、間距固定、轉角一律 45°（90° 會在轉角形成阻抗不連續），長度不夠的那一條用蛇行繞回來補 —— 兩條線長度差一點點，到了接收端就變成相位差',
          kind: 'pcbtrc', top: true, box: [64, 21, 46], at: [0, 0, 0], ex: [0, 22, -15] },
        { seg: 'hdi_pcb', part: 'pcb_mask', name: '防焊（solder mask）與開窗', note: '外層**兩面都要有**，而且在焊墊處**開窗**（不是整片蓋滿）。防焊決定焊錫流到哪裡去，也是板子看起來是綠色的原因',
          kind: 'pcbmask', box: [64, 21, 46], at: [0, 0, 0], ex: [0, 0, 28] },
        { seg: 'hdi_pcb', part: 'pcb_enig', name: '表面處理（ENIG＝化鎳浸金）', note: '★ **只出現在防焊開窗露出來的銅上**，不准畫在防焊之上、也不准畫成整片。鎳（暗）在下擋擴散、金（亮）在上防氧化。ENIG／OSP／ENEPIG 是三種不同的藥水與設備，對到不同的供應商',
          kind: 'pcbenig', box: [64, 21, 46], at: [0, 0, 0], ex: [0, 34, 0] },
        { seg: 'hdi_pcb', part: 'pcb_pth', name: '機械通孔 PTH ＋ 殘端', note: '從 L1 一路貫穿到 L10，兩端都開口。★ 紅色那一段是**殘端（stub）**：訊號其實只走到 L4，L4 以下那一截是多出來的，在高速下會變成一根天線 —— 這就是下一顆「背鑽」存在的理由',
          kind: 'pcbvia', via: 'pth', box: [64, 21, 46], at: [-21, 0, 0], ex: [-10, 26, 0] },
        { seg: 'hdi_pcb', part: 'pcb_backdrill', name: '背鑽（back drill）', note: '從**背面**用一支**比原孔粗**的鑽頭往上鑽，把殘端的孔銅吃掉。★ 一定要留一小段鑽不乾淨的殘餘 —— 工程上鑽不到零，畫成「鑽得剛剛好」就是把這張圖唯一的工程現實抹掉了',
          kind: 'pcbvia', via: 'bd', box: [64, 21, 46], at: [-7, 0, 0], ex: [-3, 26, 0] },
        { seg: 'hdi_pcb', part: 'pcb_blind', name: '雷射盲孔（micro via）', note: '只穿**一層**介電（L1 → L2），**只碰得到一個外層**、不准穿到另一面。形狀是上寬下窄的錐 —— 錐形＝雷射，直筒＝機械鑽，這是兩種完全不同的設備',
          kind: 'pcbvia', via: 'blind', box: [64, 21, 46], at: [7, 0, 0], ex: [3, 26, 0] },
        { seg: 'hdi_pcb', part: 'pcb_buried', name: '埋孔（buried via）', note: '從 L4 到 L7，**兩端都不准碰到任何外層** —— 上下都要看得到介電把它蓋住。它是在壓合之前就先鑽好、鍍好的，所以壓完之後外面完全看不到',
          kind: 'pcbvia', via: 'buried', box: [64, 21, 46], at: [21, 0, 0], ex: [10, 26, 0] },
      ],
    },
    /* ===== AI 伺服器鏈：電源 ===== */
    /* 2D 是 `site/dg/server_psu.js`。3D 這張的主角是**一顆 PSU 被拆開**：
       電源架（左，N+1 有一格空著）→ 拉出來的那一顆（中：外罩掀起 → 主板上四級由後往前）
       → 匯流排與線組（右）→ 板上降壓與晶片（最右）；BBU 與超級電容掛在**直流側**（下方）。
       ★ 硬規則（規格書 §3-A／§3-B）：降壓不准跳級、匯流排是厚銅排不是圓線、
         板上 DC-DC 是一排等距元件（多相）、BBU 在直流側而 UPS 在交流側機櫃外
         —— UPS 與設施側不在這條產業鏈上，所以 3D 這張**不畫它**（2D 那張有）。*/
    server_psu: {
      title: '電源：一顆 PSU 拆開，到晶片核心電壓（立體）',
      sub: '交流進來 → PSU 的四級（PFC → LLC → 同步整流 → 輸出）→ 直流匯流排 → 板上多相降壓 → 晶片。每一級都有一個實體，降壓不跳級。BBU 與超級電容掛在直流側、在機櫃裡；UPS 在交流側、在機櫃外（不在這條鏈上，本圖不畫）。示意圖，非實物比例',
      camera: [74, 54, 132], target: [8, -4, 0], fit: 1.08, hk: 0.58,
      parts: [
        { seg: 'power', part: 'psu_shelf', name: '電源架（power shelf，N+1）', note: '★ 中間那一格刻意**空著** —— 那就是 N+1 冗餘：少一顆還撐得住，而且可以熱插拔換掉。整架的輸出併到同一組直流匯流排上',
          kind: 'pshelf', box: [30, 34, 46], at: [-54, 6, 0], ex: [-18, 0, 0] },
        { seg: 'power', part: 'psu_unit', name: 'PSU 外罩：上蓋、側板、前面板', note: 'CRPS（通用冗餘電源）把**尺寸、連接器與管理介面**標準化，所以不同家的可以互換、可以熱插拔。前面板有把手（抽得出來）與風扇開孔，後端是卡緣不是電線',
          kind: 'pshell', box: [30, 16, 44], at: [0, 4, 0], ex: [0, 20, 0] },
        { seg: 'power', part: 'psu_board', name: 'PSU 主板：PFC → LLC → 同步整流 → 輸出', note: '四級由後往前排開，而且**每一級的元件形狀不同**：① PFC 是兩顆大電解電容加一個扼流圈（整顆 PSU 裡最大的東西）② LLC 是一顆有繞線窗口的變壓器 ③ 同步整流是輸出側一整排扁平封裝（低壓大電流所以要並聯）④ 輸出是一條厚銅排往卡緣去',
          kind: 'pboard', box: [28, 12, 42], at: [0, -2, 0], ex: [0, -8, 0] },
        { seg: 'power', part: 'psu_cardedge', name: '卡緣連接器（card-edge）', note: '★ CRPS 的後端是**上下兩排鍍金接點**，不是一束電線 —— 畫成電線就認不出是伺服器 PSU。它同時走電力與管理訊號（主機讀得到電壓、電流、溫度與告警）',
          kind: 'pcardedge', box: [20, 3.4, 4], at: [0, -2, -23], ex: [0, 0, -20] },
        { seg: 'connector', part: 'psu_busbar', name: '直流匯流排（busbar）', note: '★ **厚銅排，不是圓線**，而且明顯比任何訊號線粗一個量級 —— 幾百安培靠的是截面積。鎖固孔說明它是**鎖**上去的不是焊的。正負兩條中間隔一片絕緣',
          kind: 'pbusbar', box: [10, 46, 8], at: [34, 6, 0], ex: [12, 0, 0] },
        { seg: 'connector', part: 'psu_whip', name: '電源線組（power whip）', note: '從匯流排的分接點拉到每一台運算托盤。股數與線徑對到的是電流容量 —— 電源線束跟訊號線束粗細差很多',
          kind: 'cable', box: [24, 6, 6], at: [50, -8, 0], ex: [6, -12, 0] },
        { seg: 'power', part: 'psu_vrm', name: '板上降壓 DC-DC／VRM（多相）', note: '★ 畫成**一排等距的電感**才對：一顆電感就是一相，多相輪流出力，電流才分得開、紋波才壓得下去。畫成一顆方塊就看不出「多相」這件事。它一定**緊鄰晶片** —— 電流大、壓降走不遠',
          kind: 'pvrm', box: [28, 6, 16], at: [68, 3, 12], ex: [12, 8, 0] },
        { seg: 'power', part: 'psu_die', name: 'GPU／ASIC 核心（受電端）', note: '整條供電路徑的終點：電壓降到零點幾伏特、電流上到幾百安培。★ 這一顆是**熱源與受電端，不是電源零件** —— 它由晶圓代工做，不是電源供應商做，所以底下不列電源台股',
          kind: 'die', box: [18, 4, 18], at: [68, 4, -14], ex: [12, 14, 0], codes: [] },
        { seg: 'power', part: 'psu_bbu', name: 'BBU 電池備援模組', note: '★ 掛在**直流側、機櫃裡面**（畫到交流側就變成 UPS 了，那是這張圖最致命的錯）。撐的是「掉電到柴油發電機接手」之間那一段。看得到電芯、看得到串聯的連片、看得到一正一負兩根極柱',
          kind: 'pbbu', box: [36, 15, 36], at: [-54, -30, 0], ex: [-18, -14, 0] },
        { seg: 'power', part: 'psu_scap', name: '超級電容／鋰離子電容（LIC）', note: '比 BBU 小，跟 BBU 掛在**同一個直流節點**上，但管的是**毫秒級**的功率突波（一整櫃 GPU 同時起算那一下），不是秒到分鐘的斷電。頂面的防爆刻痕是它的識別特徵',
          kind: 'pscap', box: [22, 13, 22], at: [-12, -32, 0], ex: [0, -16, 0] },
      ],
    },
    /* ===== AI 伺服器鏈：液冷 ===== */
    /* 2D 是 `site/dg/liquid_cooling.js`。3D 這張是**熱的路徑**由內到外攤開：
       裸晶 → TIM1 → 蓋板／VC → TIM2 → 冷板（剖開，看得到流道）→ 接口 → QD → 分歧管 → CDU（內含板熱）。
       ★ 硬規則（規格書 §3-A／§3-C）：每兩個固體之間都要有 TIM 而且 TIM 最薄、
         冷板一定在蓋板之上、進水冷出水熱兩種顏色、
         **兩個迴路只在板式熱交換器處靠在一起，絕不相接**。*/
    liquid_cooling: {
      title: '液冷：從晶片到 CDU 的一條路（立體剖面）',
      sub: '熱從裸晶出發，每經過一個界面就要一層導熱介面材料（TIM，全圖最薄的東西）。冷板剖開看得到微鰭片流道 —— 那才是冷板值錢的地方。進水冷、出水熱；機櫃這一環與機房那一環只在板式熱交換器處靠在一起，水完全不相通。示意圖，非實物比例',
      camera: [70, 50, 126], target: [-6, -6, 0], fit: 1.1, hk: 0.6,
      parts: [
        { seg: 'thermal', part: 'die', name: '裸晶 die（熱源）', note: '熱的起點。★ 它是**熱源，不是散熱零件** —— 這張圖上的台股都在它上面那幾層，所以這一顆底下不列散熱廠',
          kind: 'die', box: [22, 3.2, 22], at: [-54, -16, 0], ex: [0, -16, 0], codes: [] },
        { seg: 'thermal', part: 'tim1', name: 'TIM1（裸晶 ↔ 蓋板）', note: '★ **全圖最薄的一層**，而且是被壓扁的膏（四邊會溢出一點）。它薄不是因為省料，是因為它的導熱率比銅差兩個量級 —— 厚一點點熱阻就上去了',
          kind: 'timlay', box: [22, 1.1, 22], at: [-54, -13.7, 0], ex: [0, -9, 0] },
        { seg: 'thermal', part: 'ihs', name: '均熱片／蓋板（IHS，實心銅）', note: '一塊**實心**銅蓋，四周有裙邊黏在載板上。它跟均熱板 VC 的差別就是「實心 vs 真空腔」—— 實心靠銅本身導熱，VC 靠兩相流，後者等效導熱率高得多',
          kind: 'ihslid', box: [30, 5, 30], at: [-54, -10.6, 0], ex: [0, -3, 0] },
        { seg: 'thermal', part: 'tim2', name: 'TIM2（蓋板 ↔ 冷板）', note: '第二層導熱介面材料。★ **每兩個固體之間都要有一層** —— 少畫一層，熱就變成「直接穿過去」，那在物理上不成立。它一樣比上下的金屬層薄得多',
          kind: 'timlay', box: [30, 1.1, 30], at: [-54, -7.6, 0], ex: [0, 3, 0] },
        { seg: 'thermal', part: 'cold_plate', name: '冷板（cold plate）', note: '★ 冷板一定**在蓋板之上**（晶片在下），畫反就是把熱往下送。蓋板只蓋一半是為了看得到裡面。四顆彈簧螺絲說明它是**壓**在晶片上的 —— 壓力不夠，TIM 壓不薄，熱就過不去',
          kind: 'cplate', box: [34, 9, 34], at: [-54, -2, 0], ex: [0, 9, 0] },
        { seg: 'thermal', part: 'cp_fin', name: '冷板內部流道（微鰭片）', note: '一片一片鏟出來的微鰭片，水從鰭片之間流過。**鰭片密度就是熱阻**，也就是冷板有貴賤之分的原因。兩端各留一條沒有鰭片的集流走道，水才分得均勻',
          kind: 'cpfin', box: [30, 5, 30], at: [-54, -2.4, 0], ex: [0, 19, 0] },
        { seg: 'thermal', part: 'cp_port', name: '進出水口（進水冷、出水熱）', note: '★ 兩種顏色不是裝飾：**進水是冷的、出水是熱的**，而這個溫差乘上流量就是這塊冷板帶走的熱。顏色一路延續到分歧管與 CDU',
          kind: 'cpport', box: [12, 13, 26], at: [-54, 6, 0], ex: [0, 24, 0] },
        { seg: 'thermal', part: 'qd', name: '快接頭 QD（UQD／盲插 UQDB）', note: '每一個「可拆的接點」都要一組，而且**一定成對**（一進一出）。它讓一台伺服器可以單獨抽出來維修而不放掉整櫃的水。漏液是 2026 年最被盯的品質風險',
          kind: 'uqd', box: [9, 9, 9], at: [-14, 10, 0], n: 2, gap: 18, axis: 'z', ex: [8, 8, 0],
          chipnote: '散熱這一格的台股（★ 族群「液冷散熱」裡做快接頭的富世達 6805 不在這個環節名單上，點它列不出來）' },
        { seg: 'thermal', part: 'manifold', name: '分歧管（供水／回水各一根）', note: '★ 多個冷板是**並聯**：每一個冷板各自從供水管拿水、各自回到回水管。畫成「這一個的出水接下一個的進水」（串聯）就錯了 —— 那樣後面的晶片只拿得到已經被加熱過的水',
          kind: 'lcmani', box: [22, 42, 16], at: [6, 4, 0], ex: [10, 0, 0] },
        { seg: 'thermal', part: 'cdu', name: 'CDU（冷卻液分配單元）', note: '機櫃這一環（二次側）的心臟：泵在這裡、過濾與控制也在這裡。它把機櫃的熱交給機房的水，但兩邊的水不相通',
          kind: 'cdu', box: [16, 46, 16], at: [44, 2, 0], ex: [16, 0, 0] },
        { seg: 'thermal', part: 'phe', name: '板式熱交換器（PHE，CDU 內）', note: '★ 這張圖最致命的錯就是把兩個迴路畫成一條管。它是**一疊交錯的板片**：一片縫走機櫃的水、下一片縫走機房的水 —— 只有熱過得去，水過不去',
          kind: 'lcphe', box: [18, 18, 16], at: [44, -22, 0], ex: [16, -20, 0] },
        { seg: 'thermal', part: 'vc', name: '均熱板 VC（真空腔剖面）', note: '掀開上蓋看得到裡面：下蓋板 → **毛細層**（液體在這裡往熱源回流）→ **蒸氣腔**（蒸氣往冷端跑）→ **支撐柱**（撐住真空、不然大氣壓會把它壓扁）→ 上蓋板。★ 腔裡不准畫滿液體，它是真空腔加少量工作流體',
          kind: 'vc', box: [28, 8, 28], at: [-10, -34, 26], ex: [-8, -16, 10] },
        { seg: 'thermal', part: 'heatpipe', name: '熱管（heat pipe）', note: '跟 VC 同樣是兩相流，但形狀不同：**熱管是管、VC 是扁腔**，兩者不准互換。切開那一端看得到三層：外銅管 → 毛細 → 中央蒸氣道。★ 熱管**不准有支撐柱**（圓管靠管壁本身撐），而且它一定是彎的（要繞過零件）',
          kind: 'heatpipe', box: [36, 7, 18], at: [30, -34, 26], ex: [10, -16, 10] },
      ],
      /* ---- C6 運轉動畫：**冷卻液真的在跑一圈**。
         為什麼這樣動是對的 —— 液冷是一個封閉迴路，水一定回得來：
           CDU 打出冷水 → 分歧管 → 快接頭（z = -9 那一側）→ 冷板進水口 → 微鰭片吸熱
           → 冷板出水口 → 快接頭（z = +9 那一側）→ 分歧管 → CDU → 板式熱交換器 → 再出發。
         去程走 `cold`（青綠）、回程走 `hot`（紅），顏色分開才看得出哪一邊已經吸了熱。
         快接頭本身**不動**（它是機構件，會動的只有裡面的液體）—— 這是 Andy 指定的。
         熱管與均熱板另外兩組：蒸氣往熱端外跑、冷凝液沿毛細結構回來，
         所以它們各有一去一回、而且回程走比較低的一條路徑（液體靠重力與毛細回流）。
         座標用**收攏態**（零件的 at），因為預設畫面就是收攏的。*/
      flows: [
        { kind: 'cold', part: 'manifold', r: 0.8, per: 16, speed: 0.15,
          pts: [[44, 18, 0], [30, 20, -6], [10, 20, -9], [-6, 16, -9], [-14, 12, -9], [-36, 9, -9], [-52, 7, -9], [-54, 2, -6]] },
        { kind: 'hot', part: 'manifold', r: 0.7, per: 16, speed: 0.13,
          pts: [[-54, 2, 6], [-52, 7, 9], [-36, 9, 9], [-14, 12, 9], [-6, 16, 9], [10, 14, 9], [30, 8, 4], [44, 0, 0], [44, -14, 0]] },
        /* 冷板內部：水從進水口下來、在微鰭片之間繞一個 U 再回到出水口（流道就是這樣設計的）*/
        { kind: 'cold', part: 'cp_fin', r: 0.45, per: 12, speed: 0.3,
          pts: [[-54, 1, -13], [-64, -2, -8], [-64, -2, 2], [-44, -2, 2], [-44, -2, 8], [-54, 1, 13]] },
        /* 熱管：蒸氣從熱端往冷端（上半），冷凝液沿管壁毛細回熱端（下半）*/
        { kind: 'hot', part: 'heatpipe', r: 0.4, per: 10, speed: 0.34, pts: [[14, -32, 26], [30, -31, 26], [46, -32, 26]] },
        { kind: 'cold', part: 'heatpipe', r: 0.3, per: 10, speed: 0.22, pts: [[46, -36, 26], [30, -37, 26], [14, -36, 26]] },
        /* 均熱板：中央（貼晶片）蒸發往外擴散，邊緣冷凝後回到中央 */
        { kind: 'hot', part: 'vc', r: 0.35, per: 9, speed: 0.3, pts: [[-10, -31, 26], [-2, -31, 31], [2, -31, 37]] },
        { kind: 'cold', part: 'vc', r: 0.28, per: 9, speed: 0.2, pts: [[2, -37, 37], [-2, -37, 31], [-10, -37, 26]] },
      ],
      /* 熱從晶片一路交棒出去：裸晶 → TIM1 → 蓋板 → TIM2 → 冷板 → 流道。
         依序點亮＝熱阻是一串串聯的，前一段沒導出去後一段就不會熱。*/
      pulses: [{ parts: ['die', 'tim1', 'ihs', 'tim2', 'cold_plate', 'cp_fin'], period: 3.4, kind: 'hot' }],
    },
    /* ===== AI 伺服器鏈：氣冷 ===== */
    /* 2D 是 `site/dg/air_cooling.js`。3D 這張把**一顆風扇沿轉軸拆開** ——
       那正是「轉一圈能多理解一件事」的地方：2D 剖面只看得到切開的那一刀，
       看不到六個件是怎麼套在同一根軸上的。轉軸取 z（朝鏡頭），所有位移都沿 z 走。
       ★ 硬規則（規格書 §3-B）：扇葉從輪轂長出來、馬達在輪轂裡、軸承在軸與輪轂之間。
       右邊那一疊是氣流路徑：風扇牆 → 導風罩 → 鰭片（熱真正交給空氣的地方）→ 熱管／VC。*/
    air_cooling: {
      title: '氣冷：一顆風扇拆開，加上熱交給空氣的那一段（立體）',
      sub: '左邊沿轉軸拆開：扇框 → 前轉子（扇葉從輪轂長出來、有攻角）→ 輪轂（馬達裝在裡面）→ 定子馬達 → 軸承（在軸與輪轂之間）→ 後轉子（反轉，攻角相反）。右邊是氣流路徑：★ 風扇只是把空氣推過來，**熱真正交給空氣是在鰭片那一格**。示意圖，非實物比例',
      camera: [62, 44, 124], target: [0, -4, 0], fit: 1.12, hk: 0.62,
      parts: [
        { seg: 'thermal', part: 'fan_frame', name: '扇框（frame／housing）', note: '四角有鎖孔的方框、中間一個圓孔。四根支撐臂從框伸到中央撐住馬達 —— 沒有它，輪轂就是浮在空中的。鎖孔說明風扇是**鎖**在機殼上的，不是一顆自由的葉輪',
          kind: 'fframe', box: [46, 46, 13], at: [-48, 2, 0], ex: [0, 0, -24] },
        { seg: 'thermal', part: 'blade', name: '前轉子：扇葉（有攻角）', note: '★ 扇葉**一定從輪轂長出來**，不可以懸空。每一片都有攻角 —— 平的葉片推不動空氣，只會攪。攻角、片數與外徑決定它的風量與風壓',
          kind: 'frotor', box: [39, 39, 11], at: [-48, 2, 3], ex: [0, 0, 38] },
        { seg: 'thermal', part: 'hub', name: '輪轂（hub）', note: '一個開口朝後的**杯狀件** —— 馬達與軸承裝在它裡面。畫成實心圓柱就沒地方放馬達了。杯壁內側那一圈方塊是**轉子磁鐵**：外轉子馬達就是把磁鐵貼在輪轂內壁上',
          kind: 'fhub', box: [18, 18, 11], at: [-48, 2, 3], ex: [0, 0, 26] },
        { seg: 'thermal', part: 'motor', name: '馬達（定子線圈 ＋ 轉子磁鐵）', note: '★ **馬達一定在輪轂裡**，不在扇框上。定子是鐵芯的齒加上繞在齒上的銅線圈，在內；轉子磁鐵貼在輪轂內壁，在外；中間那一圈空隙是氣隙。底下那一小塊板上有霍爾元件 —— 轉速回授就是從那裡出去的',
          kind: 'fmotor', box: [15, 15, 10], at: [-48, 2, 0], ex: [0, 0, 14] },
        { seg: 'thermal', part: 'bearing', name: '軸承（在軸與輪轂之間）', note: '★ 位置是硬規則：**在軸與輪轂之間**。這裡畫的是滾珠型 —— **看得到鋼珠**才是滾珠軸承；含油軸承是軸與襯套直接接觸、沒有珠；流體動壓是中間一層油膜加襯套溝槽；磁浮是兩者之間有可見空隙。四型不准互換',
          kind: 'fbear', box: [9, 9, 14], at: [-48, 2, -1], ex: [0, 0, 4] },
        { seg: 'thermal', part: 'counter_rot', name: '後轉子（反轉雙轉子的第二組）', note: '第二組葉輪**反方向**轉，而且攻角相反。前轉子把空氣旋著吹出去，後轉子把那個旋轉再扳直 —— 所以同樣厚度下風壓明顯更高。兩組同向就不是反轉，只是兩顆風扇疊在一起',
          kind: 'frotor', rev: true, box: [39, 39, 10], at: [-48, 2, -8], ex: [0, 0, -40] },
        { seg: 'thermal', part: 'wire4', name: '四線接頭（電源／地／轉速／PWM）', note: '★ **四線**就是伺服器風扇跟家用風扇最好認的差別：多出來的兩條一條回報轉速、一條讓主機用 PWM 控速。兩線的風扇只能全速或不轉',
          kind: 'fwire', box: [14, 6, 18], at: [-48, -24, -3], ex: [0, -18, -12] },
        { seg: 'thermal', part: 'fan_wall', name: '風扇牆（fan wall，N+1）', note: '一整排風扇裝在同一個框上，而且**多一顆** —— 壞一顆時其餘的提高轉速頂上。每一顆都看得到框、輪轂與葉片；一排空圓圈不是風扇牆',
          kind: 'fwall', box: [60, 30, 10], at: [36, 28, 0], ex: [0, 28, 0] },
        { seg: 'assembly', part: 'shroud', name: '導風罩（air shroud／duct）', note: '它本身不散熱，但沒有它風會從鰭片旁邊溜掉。出風那一端收窄，氣流才會被逼著穿過鰭片。★ 氣流方向**全程單向、由前到後**，圖上不准出現往回吹的箭頭',
          kind: 'fshroud', box: [48, 20, 34], at: [36, 0, 2], ex: [0, 14, 26] },
        { seg: 'thermal', part: 'fin', name: '散熱鰭片組（heat sink fin stack）', note: '★ **這一格才是熱真正交給空氣的地方；風扇只是把空氣推過來。** 很多人以為「風扇在散熱」，其實風扇只負責換掉鰭片表面那層被加熱的空氣。鰭片的總表面積就是它的本事',
          kind: 'heatsink', box: [38, 17, 32], at: [36, -14, 0], ex: [0, -8, 0] },
        { seg: 'thermal', part: 'heatpipe', name: '熱管（heat pipe）', note: '把熱從晶片底座**橫著**搬到鰭片裡面去 —— 光靠鋁底板傳，遠端的鰭片根本吃不到熱。★ 熱的方向（晶片 → 底座 → 熱管 → 鰭片）跟氣流方向是**垂直交會**的，不是同一條線',
          kind: 'heatpipe', box: [38, 7, 28], at: [36, -26, 0], ex: [0, -20, 0] },
        { seg: 'thermal', part: 'vc', name: '均熱板 VC（當底座）', note: '晶片越大，熱越不可能只靠一塊銅底板攤開。VC 用兩相流把熱先**攤成一個面**再交給熱管與鰭片 —— 熱管是線、VC 是面，這就是兩者的分工',
          kind: 'vc', box: [34, 7, 30], at: [36, -34, 0], ex: [0, -30, 0] },
      ],
      /* ---- C6 運轉動畫：**風扇在轉、空氣在走**。
         扇葉與後轉子本來就會轉（frotor 自己掛了 userData.spin，反轉雙轉子第二組是負轉速）；
         這一批補的是風扇牆（InstancedMesh，28 片葉片，見 fanWall 的 ispin）與**氣流**。
         氣流為什麼是這樣：軸流風扇沿**軸向**（這裡是 z）吸進來、吹出去，
         吹出來的風被導風罩圍住、逼著穿過鰭片之間的縫隙（不然會從旁邊溜掉），
         最後帶著熱離開。所以氣流線是「先沿 z 穿過扇框」「再沿 z 穿過鰭片組」，
         而且出風端的 y 略高 —— 熱空氣會往上走。*/
      flows: [
        { kind: 'airline', part: 'blade', line: true, per: 9, speed: 0.36, pts: [[-58, 6, -34], [-56, 4, -12], [-56, 3, 12], [-57, 6, 34]] },
        { kind: 'airline', part: 'blade', line: true, per: 9, speed: 0.36, pts: [[-48, 2, -34], [-48, 2, -12], [-48, 2, 12], [-48, 4, 34]] },
        { kind: 'airline', part: 'blade', line: true, per: 9, speed: 0.36, pts: [[-38, -2, -34], [-40, 0, -12], [-40, 1, 12], [-39, 4, 34]] },
        /* 風扇牆 → 導風罩 → 鰭片：三條穿過鰭片組的縫隙（x 分開，看得出是一整面的風） */
        { kind: 'airline', part: 'fin', line: true, per: 9, speed: 0.4, pts: [[24, -12, -30], [24, -14, -8], [24, -14, 10], [24, -10, 30]] },
        { kind: 'airline', part: 'fin', line: true, per: 9, speed: 0.4, pts: [[36, -12, -30], [36, -14, -8], [36, -14, 10], [36, -10, 30]] },
        { kind: 'airline', part: 'fin', line: true, per: 9, speed: 0.4, pts: [[48, -12, -30], [48, -14, -8], [48, -14, 10], [48, -10, 30]] },
        { kind: 'airline', part: 'fan_wall', line: true, per: 8, speed: 0.44, pts: [[36, 28, -26], [36, 27, 0], [36, 30, 26]] },
      ],
      /* 熱從底下往上交棒：均熱板 → 熱管 → 鰭片，最後被風帶走。*/
      pulses: [{ parts: ['vc', 'heatpipe', 'fin'], period: 2.8, kind: 'hot' }],
    },
    /* ===== AI 伺服器鏈：網通 ===== */
    /* 2D 是 `site/dg/switch_wireless.js`。3D 這張是一張交換器板卡：
       主板（高層數 MLB）＋ 中央的 ASIC 與散熱片 ＋ 緊鄰它的 VRM
       ＋ 前面板的光模組籠架陣列（一顆模組抽出來，看得到裡面的四顆晶片）
       ＋ 同一片基板上的 CPO 光引擎（另一半答案）＋ 後方的風扇與 PSU。
       ★ 硬規則（規格書 §3-C）：**VRM 一定緊鄰 ASIC**（電流大、壓降走不遠）。
       ★ §2：**不准出現 DIMM 插槽、PCIe 插槽、CPU 插座** —— 那是伺服器主機板，
         所以主板不沿用 `pcb`（那一支畫了三條插槽），另寫了 `swboard`。*/
    switch_wireless: {
      title: '網通：交換器板卡 ＋ 800G 光模組 ＋ CPO（立體）',
      sub: '板中央那顆是交換晶片，散熱片蓋在它上面、多相供電緊貼在它旁邊（電流太大，壓降走不遠）。前面板是兩列光模組籠架，抽出來那一顆裡面有 DSP、驅動 IC、雷射與 TIA —— 光電轉換發生在模組裡，不在板子上。CPO 則是把光引擎搬到跟晶片同一片基板上。示意圖，非實物比例',
      camera: [68, 56, 122], target: [0, 4, 0], fit: 1.06, hk: 0.62,
      parts: [
        { seg: 'hdi_pcb', part: 'sw_pcb', name: '主板：高層數多層板（MLB）', note: '一塊 38–48 層等級的板子。★ 它上面**沒有記憶體插槽、沒有 PCIe 插槽** —— 有那些的是伺服器主機板。晶片底下那一片密密麻麻的過孔，是訊號從外層沉到內層的通道',
          kind: 'swboard', box: [92, 3.4, 64], at: [0, 0, 0], ex: [0, -18, 0] },
        { seg: 'ccl', part: 'sw_layers', name: '板子前緣那一疊：core／prepreg 交替', note: '把板緣切開才看得到：已覆銅的芯板（core）與沒有銅的半固化片（prepreg）交替壓起來。★ 層數之所以這麼多，是因為**每一層高速訊號層的上下都必須各有一層完整的接地參考層**',
          kind: 'laminate', box: [20, 5, 44], at: [-62, 0, 0], ex: [-24, 8, 0] },
        { seg: 'switch', part: 'sw_asic', name: '交換器晶片（switch ASIC）', note: '板上**最大的單一元件**：有機基板 ＋ 覆晶的矽晶粒 ＋ 上面的蓋板，底下一整片球柵陣列。它負責查表決定每一個封包要從哪一個埠出去 —— 整台交換器的頻寬就是這一顆的規格',
          kind: 'swasic', box: [22, 6, 22], at: [0, 4.4, -8], ex: [0, 12, 0],
          chipnote: '交換器這一格的台股（★ 是做**整機**的，不是做這顆晶片 —— 交換晶片由美系原廠設計，台股沒有直接對應）' },
        { seg: 'thermal', part: 'sw_hs', name: '晶片散熱片（鰭片順著前後氣流）', note: '鰭片的方向一定順著機箱前後的氣流走 —— 擺橫的就把風擋住了。它的覆蓋面積比晶片封裝大，因為熱要先攤開再交給空氣',
          kind: 'heatsink', box: [30, 15, 30], at: [0, 14, -8], ex: [0, 30, 0] },
        { seg: 'power', part: 'sw_vrm', name: '板上多相供電模組（VRM）', note: '★ **一定緊鄰 ASIC** —— 幾百安培的電流在板子上走不遠（壓降與損耗都吃不消）。一排等距的電感就是一相一顆；把它畫在板子另一頭是一眼就能驗的結構錯誤',
          kind: 'pvrm', box: [28, 6, 12], at: [0, 4, -26], ex: [0, 14, -14] },
        { seg: 'optical', part: 'sw_cage', name: '前面板光模組籠架（cage）', note: '金屬籠排成**上下兩列**佔滿前面板 —— 排數 × 列數就是埠數。籠子存在的理由有兩個：擋電磁干擾，以及把 800G 模組的熱帶出去（所以籠背上有鰭片）',
          kind: 'swcage', box: [84, 15, 14], at: [0, 9, 26], ex: [0, 8, 18] },
        { seg: 'optical', part: 'sw_mod_fiber', name: '抽出來的一顆光模組（OSFP／QSFP-DD800）', note: '★ 光電轉換發生在**模組裡面**，不在板子上。上蓋掀開一半看得到四顆：最大的那顆是 **DSP**（也是最耗電的一顆，正是 CPO 想拿掉的東西），再來是驅動 IC、雷射晶粒與 TIA。前端兩個接口接光纖',
          kind: 'swmod', box: [9, 7, 26], at: [-24, 9, 50], ex: [0, 6, 26] },
        { seg: 'connector', part: 'sw_mod_gold', name: '金手指：模組唯一的電接點', note: '在模組**後端**（插進籠子的那一頭），不是光纖那一頭。上下兩排鍍金接點，前緣倒角才插得進去。整顆模組跟板子之間所有的電，都只從這裡過',
          kind: 'swgold', box: [8, 4, 8], at: [-24, 9, 35], ex: [0, 6, 34] },
        { seg: 'optical', part: 'sw_cmp_cpo', name: '共同封裝光學（CPO）光引擎', note: '★ 這是「另一半答案」：把光引擎搬到**跟交換晶片同一片基板上**、環繞在它四周，光纖直接從基板邊緣拉出去。電訊號只要走幾公釐就進光引擎，DSP 那一顆的功耗因此省掉一大塊。代價是壞掉不能像可插拔模組那樣單顆換',
          kind: 'swcpo', box: [42, 5, 42], at: [0, 3, -8], ex: [0, 22, 12] },
        { seg: 'connector', part: 'sw_fly', name: '近晶片飛越纜線（flyover cable）', note: '從晶片旁邊的小連接器**架空**拉到籠架背面，繞開 PCB。理由很簡單：同樣的距離，細同軸纜線的損耗比板子上的銅走線小得多 —— 速率越高，這條替代路徑越划算。★ 走了纜線的那幾個埠，板子內層就不該再有同一條訊號的走線',
          kind: 'cable', box: [30, 5, 5], at: [18, 10, 12], ex: [0, 16, 10] },
        { seg: 'switch', part: 'sw_cpu', name: '管理用處理器（跑網路作業系統）', note: '角落那一小塊，明顯小於交換晶片。它不負責轉封包（那是 ASIC 的事），只負責跑網路作業系統、算路由表再寫進 ASIC。跟 ASIC 之間走的是低速管理匯流排，不是高速差動對',
          kind: 'chip', box: [12, 4, 12], at: [36, 3.5, -22], ex: [0, 12, -12], codes: [] },
        { seg: 'thermal', part: 'sw_fan', name: '系統風扇（後方、可熱抽換）', note: '★ 在**後方**不在前面板 —— 前面板全部留給 I/O。可熱抽換，壞一顆不必關機',
          kind: 'fan', box: [16, 16, 7], at: [22, 9, -36], n: 3, gap: 18, axis: 'x', ex: [0, 0, -20],
          chipnote: '散熱這一格的台股（★ 族群裡做風扇與熱管的尼得科超眾 6230、泰碩 3338、力致 3483、元山 6275 不在這個環節名單上）' },
        { seg: 'power', part: 'sw_psu', name: '電源供應器 PSU（後方、1+1 冗餘）', note: '兩顆並排、可熱抽換：一顆壞掉另一顆撐住。交流進來、轉成板上要的直流，再由板上的 VRM 降到晶片核心電壓',
          kind: 'psu', box: [26, 11, 18], at: [-32, 7, -36], ex: [0, 0, -24] },
      ],
    },
    /* ===== 一般電子鏈：面板 TFT-LCD 疊層 ===== */
    /* 2D 是 `site/dg/panel.js`，`part` 沿用它的 `data-part`（pn_*）。
       背光模組在 2D 上是**一個** data-part（`pn_backlight`），3D 把它拆成五層各自一件，
       所以那五件各自用 `alias: ['pn_backlight']` 指回去 —— 2D 點背光模組，3D 那五層一起亮。
       構圖：整疊沿 y 垂直爆炸。收攏時是一片完整的面板，展開時十三層的順序一目了然。
       ⚠ 共同電極、配向層、平坦化層沒有畫：它們的位置與有無依顯示模式（TN／VA／IPS）而異，
         查不到可引用的定論 —— 寧可不畫，也不要畫一個看起來很專業的錯結構（跟 2D 那張同一條）。*/
    panel: {
      title: '面板：一片 TFT-LCD 拆成十三層（垂直爆炸）',
      sub: '由下往上＝背板／反射片／導光板／下擴散／稜鏡片 → 下偏光 → 下玻璃與 TFT 陣列 → 液晶 → 彩色濾光片 → 上玻璃 → 上偏光。★ 兩片偏光板都在**兩片玻璃的外側**、而且透光軸正交；光源是導光板**側邊**那條 LED 燈條，不是正下方。下玻璃多出來的那一條是端子區，驅動 IC 與 COF 貼在那裡。示意圖，非實物比例',
      camera: [96, 78, 116], target: [0, 14, 0], fit: 0.98, hk: 0.46,
      parts: [
        { seg: 'panel_mfg', part: 'pn_bl_back', alias: ['pn_backlight'], name: '背板與膠框（整疊的底）', note: '鈑金盤 ＋ 壓在上緣的一圈塑膠膠框。★ 膠框不是裝飾：整疊光學膜片就是靠它壓住定位的，少了它整疊會鬆掉',
          kind: 'pnframe', box: [88, 4, 58], at: [0, 2, 0], ex: [0, -34, 0],
          codes: ['6176'], chipnote: '背光模組台股：6176 瑞儀（導光板／擴散板／背光模組）。供應鏈資料還沒把背光模組建成獨立環節，所以這一欄直接指名、不走環節名單' },
        { seg: 'panel_mfg', part: 'pn_bl_ref', alias: ['pn_backlight'], name: '反射片', note: '貼在導光板底下，把往下漏的光打回去。它只做一件事，但少了它整片亮度就掉一截',
          kind: 'pnfilm', box: [82, 0.6, 54], at: [0, 4.7, 0], k: 0.5, ex: [0, -26, 0],
          codes: ['6176'], chipnote: '背光模組台股：6176 瑞儀（供應鏈資料沒有這一格，直接指名）' },
        { seg: 'panel_mfg', part: 'pn_lgp', alias: ['pn_backlight'], name: '導光板（底面有網點）', note: '★ 底面的網點是它唯一的識別特徵：離入光側越遠、點越大越密。沒有這個梯度，光會全部從靠近 LED 那一頭漏出去，整片一邊亮一邊暗。畫成一塊光板子＝畫的是壓克力板',
          kind: 'pnlgp', box: [82, 3.4, 54], at: [0, 7, 0], ex: [0, -18, 0],
          codes: ['6176'], chipnote: '導光板台股：6176 瑞儀（供應鏈資料沒有這一格，直接指名）' },
        { seg: 'panel_mfg', part: 'pn_led', name: 'LED 燈條（側光式的光源）', note: '★ 一排白光 LED 朝著導光板的**側面**，不是朝上 —— 朝上就是直下式背光，那是另一種結構。背光是白的，畫面的顏色不是它給的',
          kind: 'pnledbar', box: [5, 3.4, 54], at: [-44, 7, 0], ex: [-30, -18, 0],
          codes: [], chipnote: 'LED 晶粒屬 LED 族群、燈條組裝屬背光模組（6176 瑞儀），兩者都不在這張圖涵蓋的環節裡 —— 這一格不指名，避免把「做燈條」講成「做面板」' },
        { seg: 'panel_mfg', part: 'pn_bl_diff', alias: ['pn_backlight'], name: '下擴散片', note: '把導光板打出來的光打散，網點才不會一顆一顆被看見。它在稜鏡片底下 —— 順序反了就會看到網點',
          kind: 'pnfilm', box: [82, 0.7, 54], at: [0, 9.5, 0], k: 0.36, ex: [0, -10, 0],
          codes: ['6176'], chipnote: '擴散板台股：6176 瑞儀（供應鏈資料沒有這一格，直接指名）' },
        { seg: 'panel_mfg', part: 'pn_bl_prism', alias: ['pn_backlight'], name: '稜鏡片 ×2（兩片正交）', note: '★ 兩片的稜線必須正交：一片只把光收一個方向，兩片同向就少收了另一個方向、正面亮度提不上去。這也是「為什麼是兩片不是一片」的答案',
          kind: 'pnprism', box: [82, 1.8, 54], at: [0, 11, 0], ex: [0, -3, 0],
          codes: ['6176'], chipnote: '背光模組台股：6176 瑞儀（供應鏈資料沒有這一格，直接指名）' },
        { seg: 'panel_mfg', part: 'pn_pol_lo', name: '下偏光板', note: '★ 貼在下玻璃的**外側**，不是夾在液晶旁邊。它先把背光整理成單一方向的光，液晶轉不轉才決定光到不到得了上偏光板',
          kind: 'pnpol', box: [80, 1.0, 52], at: [0, 12.5, 0], ex: [0, 4, 0],
          codes: ['8215', '4960'], chipnote: '偏光板台股：8215 明基材、4960 誠美材（在「面板產業」族群裡）。供應鏈資料還沒把偏光板建成獨立環節，所以這一欄直接指名' },
        { seg: 'display_material', part: 'pn_glass_lo', name: 'TFT 陣列玻璃基板（下玻璃）', note: '下面那片玻璃，內側做 TFT 陣列；★ 它比上玻璃大，多出來的那一條就是端子區。面板廠在這片玻璃上做大面積精細金屬線路的能力，就是它能轉去做封裝 RDL 的本錢。★ 台股沒有 TFT 玻璃基板廠 —— 康寧、AGC、NEG 三家外商供應；台玻 1802 做的是建築玻璃與玻纖，不是 TFT 基板',
          kind: 'pnglass', box: [88, 1.8, 52], at: [0, 14, 0], ex: [0, 10, 0], codes: [] },
        { seg: 'panel_mfg', part: 'pn_tft', name: 'TFT 陣列層', note: '★ 橫的閘極線選一列、縱的資料線送電壓，兩者正交成格，每一格角落一顆薄膜電晶體開關那一個子像素的像素電極。少掉其中一組線就不是「陣列」，只是一堆電極',
          kind: 'pntft', box: [76, 0.9, 50], at: [0, 15.4, 0], ex: [0, 16, 0] },
        { seg: 'panel_mfg', part: 'pn_lc', name: '液晶層', note: '★ 液晶靠「轉向」控制光，不是靠自己發光：不加電躺平、加電立起來，通過的光量就不同（圖上左右兩半就是這兩個狀態）。周邊一圈封框膠封住，中間幾根光阻間隙物撐住盒厚。哪一邊亮依顯示模式（TN／VA／IPS）而定，圖上不指定',
          kind: 'pnlc', box: [76, 1.8, 50], at: [0, 16.8, 0], ex: [0, 22, 0] },
        { seg: 'panel_mfg', part: 'pn_cf', name: '彩色濾光片（黑色矩陣 ＋ R／G／B 色阻）', note: '做在上玻璃內側。★ R／G／B 是三個**水平並排**的子像素，不是上下疊三層（疊三層等於把光濾光，什麼都看不到）。黑色矩陣把每一格框起來擋住串色。顏色是它濾出來的，不是背光給的',
          kind: 'pncf', box: [76, 1.0, 50], at: [0, 18.2, 0], ex: [0, 28, 0] },
        { seg: 'display_material', part: 'pn_glass_up', name: '彩色濾光片玻璃基板（上玻璃）', note: '上面那片玻璃，內側做彩色濾光片。★ 面積比下玻璃小 —— 下玻璃多出來的那一條是端子區。★ 台股沒有 TFT 玻璃基板廠：康寧、AGC、NEG 三家外商供應',
          kind: 'pnglass', box: [80, 1.8, 52], at: [0, 19.6, 0], ex: [0, 34, 0], codes: [] },
        { seg: 'panel_mfg', part: 'pn_pol_up', name: '上偏光板（透光軸與下片正交）', note: '★ 貼在上玻璃的**外側**，偏振方向與下偏光板正交。兩片一夾，液晶轉多少、光就過多少 —— 少一片就沒有「擋得掉」這件事，兩片同向則是永遠全亮',
          kind: 'pnpol', box: [80, 1.0, 52], at: [0, 21.1, 0], cross: true, ex: [0, 40, 0],
          codes: ['8215', '4960'], chipnote: '偏光板台股：8215 明基材、4960 誠美材（在「面板產業」族群裡，供應鏈資料還沒建成獨立環節）' },
        { seg: 'panel_mfg', part: 'pn_driver', name: '端子區：驅動 IC ＋ COF 軟板', note: '★ 貼在下玻璃外露的那一條端子區上 —— 兩片玻璃錯開就是為了留這條邊。COF 是壓在軟性電路板上再接過來，軟板往背面折。晶片本身屬半導體鏈的「顯示驅動 IC」（3034 聯詠等），這裡只畫它貼在哪裡，不宣稱晶片是面板廠做的',
          kind: 'pndriver', box: [16, 3.4, 50], at: [38, 15, 0], ex: [26, 10, 0] },
      ],
    },
    /* ===== 一般電子鏈：工業自動化／CNC 工具機 —— 一個會動的軸 ===== */
    /* 2D 是 `site/dg/motion_control.js`（一張圖掛兩個族群：`factory_automation` 與 `machine_tool`），
       所以這一個場景也被那兩個 id 共用。`part` 沿用 2D 的 `data-part`（mc_*）。
       構圖：一根單軸模組沿著 x 拆開 —— 馬達 → 聯軸器 → 軸承座 → 螺桿＋螺帽 → 滑軌＋滑塊 → 工作台。
       ⚠ 這張圖**沒有對應的供應鏈環節**：一般電子鏈 8 格裡沒有一格是傳動件，
         所以 `seg: 'motion_axis'` 只是佔位，台股一律用零件自己的 `codes` 列（跟矽晶圓那張同一套）。
       ⚠ 減速機（諧波／RV）與氣壓件在 2D 那張各有一格，3D 這一張只畫「直線軸」那一條 ——
         轉動關節的兩種減速機在剖面上比並排立體更清楚（那是齒數與相位的事，不是空間的事）。*/
    motion_axis: {
      title: '工業自動化：一個會動的軸沿著軸拆開',
      sub: '馬達轉 → 聯軸器接 → 軸承座撐 → 滾珠螺桿把「轉」變成「直線走」→ 滑軌撐住工作台不歪。★ 螺帽剖開看得到鋼珠與那條 U 形回流通道 —— 鋼珠是一個閉合的迴圈，沒有這條通道的螺桿是鎖緊用的梯形螺桿，不是傳動用的。示意圖，非實物比例',
      camera: [64, 56, 118], target: [0, 8, 0], fit: 1.02, hk: 0.5,
      parts: [
        { seg: 'motion_axis', part: 'mc_base', name: '底座（鋁擠型）', note: '★ 斷面有空腔：同樣重量下拿到比較高的斷面剛性 —— 實心方塊不是鋁擠型。上緣的 T 型槽是軌道與感測器鎖上去的地方',
          kind: 'mcbase', box: [122, 11, 46], at: [0, -6, 0], ex: [0, -14, 0], codes: [] },
        { seg: 'motion_axis', part: 'mc_enc', name: '編碼器（回授的起點）', note: '★ 裡面那片刻了一圈等距刻線的碼盤就是它的全部意義 ——「會轉」跟「知道自己轉到哪」是兩件事。它裝在馬達的尾端（遠離螺桿那一側），把位置送回驅動器與控制器',
          kind: 'mcenc', box: [13, 17, 17], at: [-70, 9, 0], ex: [-42, 4, 0],
          codes: [], chipnote: '編碼器這一件，查不到台股的具名對應 —— 查不到就寫查不到，不編一個對應' },
        { seg: 'motion_axis', part: 'mc_motor', name: '伺服馬達', note: '方殼、外殼有散熱肋、前面一片法蘭鎖到機構上、軸從法蘭伸出去。★ 沒有尾端那顆編碼器就只是一般感應馬達。本圖只畫外殼，不畫繞組剖面（那會跟變壓器那張撞題）',
          kind: 'mcmotor', box: [40, 20, 20], at: [-44, 9, 0], ex: [-24, 4, 0],
          codes: ['4576'], chipnote: '4576 大銀微系統（線性馬達與傳動，信心：verified）。★ 本圖畫的是旋轉馬達＋螺桿，直接驅動的線性馬達是另一種架構、本圖未畫。這一檔不在 supply_chain.yaml 的環節裡，所以直接指名' },
        { seg: 'motion_axis', part: 'mc_coupling', name: '聯軸器', note: '★ 馬達與螺桿之間一定要有它。直接畫成一根連續的軸就是錯 —— 那表示兩根軸完全同心且剛性連接，實務上做不到，也沒有可更換的犧牲件。中間那一段撓性溝就是它的識別特徵',
          kind: 'mccoup', box: [20, 13, 13], at: [-21, 9, 0], ex: [-12, 4, 0],
          codes: [], chipnote: '聯軸器這一件，查不到台股的具名對應' },
        { seg: 'motion_axis', part: 'mc_bearing', name: '軸承座（固定端／支撐端）', note: '螺桿兩端各一個：★ 一端固定（吃軸向力）、一端支撐（只導引，讓螺桿受熱可以伸長）—— 兩端都畫成固定端，螺桿熱起來就被自己頂彎。剖面看得到內外環與夾在中間的一圈滾珠',
          kind: 'mcbrg', box: [12, 20, 20], at: [0, 9, 0], n: 2, gap: 76, axis: 'x', ex: [0, 17, 0],
          codes: [], chipnote: '軸承座這一件，查不到台股的具名對應' },
        { seg: 'motion_axis', part: 'mc_screw', name: '滾珠螺桿・螺桿軸', note: '把馬達的「轉」變成工作台的「直線走」。★ 表面的溝槽剖面是圓弧（哥德弧或單圓弧），不是 V 形三角 —— V 形那是鎖緊用的螺絲，走的是滑動摩擦、裡面沒有鋼珠。兩端的軸頸比較細且有階級，那是要裝軸承的地方',
          kind: 'mcscrew', box: [86, 13, 13], at: [0, 9, 0], ex: [0, 3, 0],
          codes: ['2049', '4540'], chipnote: '2049 上銀（滾珠螺桿與線性滑軌）、4540 全球傳動（線性傳動）。終端不同：上銀多在工具機、全球傳動在產業機械（信心：中，來源為產業媒體整理）。兩檔都不在 supply_chain.yaml 裡，所以直接指名' },
        { seg: 'motion_axis', part: 'mc_nut', name: '滾珠螺桿・螺帽（含法蘭）', note: '套在螺桿上的金屬套筒，長度約螺桿全長的六分之一。★ 用半管切開而不是切方塊：壁厚看得見，才看得出鋼珠與回流通道真的在這個套筒的裡面。外側的法蘭是它鎖到工作台上的那一片',
          kind: 'mcnut', box: [22, 17, 17], at: [16, 9, 0], ex: [22, 3, 0],
          codes: ['2049', '4540'], chipnote: '同螺桿軸：2049 上銀、4540 全球傳動。兩檔都不在 supply_chain.yaml 裡' },
        { seg: 'motion_axis', part: 'mc_ball', name: '鋼珠（兩點接觸）', note: '★ 每一顆都同時碰到螺桿溝與螺帽溝 —— 浮在中間就不傳力。鋼珠把滑動摩擦換成滾動摩擦，這是滾珠螺桿跟一般螺桿唯一的差別',
          kind: 'mcballs', box: [22, 17, 17], at: [16, 9, 0], ex: [22, 13, 0],
          codes: [], chipnote: '鋼珠（鋼球）這一件，查不到台股的具名對應' },
        { seg: 'motion_axis', part: 'mc_return', name: '循環器（鋼珠回流通道）', note: '★ 這張圖的紅線零件：鋼珠滾到螺帽的一端之後，從這條 U 形通道繞回另一端，重新進入溝槽 —— 是一個閉合的迴圈。沒有這條通道的螺桿是鎖緊用的梯形螺桿，不是傳動用的滾珠螺桿',
          kind: 'mcreturn', box: [22, 17, 17], at: [16, 9, 0], ex: [22, 21, 0],
          codes: [], chipnote: '循環器是螺桿廠自己做的零件，查不到獨立供應的台股對應' },
        { seg: 'motion_axis', part: 'mc_rail', name: '線性滑軌・軌道 ×2', note: '凸出來的一條，兩側有圓弧溝。★ 一定是兩條平行軌，而且螺桿在兩軌之間 —— 螺桿畫在旁邊的話推力不在滑座形心上，工作台會被扭起來。鎖付孔也不能省：軌道是鎖在底座上的',
          kind: 'mcrail', box: [110, 8, 13], at: [0, 2, 0], n: 2, gap: 30, axis: 'z', ex: [0, -6, 0],
          codes: ['2049', '1597'], chipnote: '2049 上銀（滾珠螺桿與線性滑軌）、1597 直得（線性滑軌）。兩檔都不在 supply_chain.yaml 裡，所以直接指名' },
        { seg: 'motion_axis', part: 'mc_block', name: '線性滑軌・滑塊 ×2', note: '★ ㄇ 字形，從上方罩下來、包住軌道的兩側。畫成「一個方塊放在軌道上面」就是錯的 —— 那樣的東西吃不了側向力也吃不了拉拔力，而滑軌存在的理由就是吃這兩種力。滑軌不出力，只負責「別歪掉」與承重',
          kind: 'mcblock', box: [26, 11, 21], at: [26, 5, 0], n: 2, gap: 30, axis: 'z', ex: [26, 13, 0],
          codes: ['2049', '1597'], chipnote: '同軌道：2049 上銀、1597 直得。兩檔都不在 supply_chain.yaml 裡' },
        { seg: 'motion_axis', part: 'mc_table', name: '工作台（滑座）', note: '★ 同時鎖在螺帽與滑塊上：螺帽推它走、滑塊撐住它不歪 —— 兩個連接都要有，少一個這根軸就不成立。上面的 T 型槽是工件鎖上去的地方',
          kind: 'mctable', box: [52, 9, 44], at: [22, 14, 0], ex: [22, 30, 0], codes: [] },
      ],
    },
    /* ===== 一般電子鏈：被動保護 —— 過流與過壓元件 ===== */
    /* 2D 是 `site/dg/circuit_protection.js`，`part` 沿用它的 `data-part`（cp_*）。
       構圖：四顆並排、切掉同一個角（半剖，切掉 z > 0）。
       ★ 為什麼非得剖開：這四顆的外觀都只是小方塊，差別**全部在裡面**——
         MOV 是陶瓷晶粒與晶界、PPTC 是高分子與碳黑鏈、NTC 是均質燒結陶瓷、TVS 是 PN 接面與空乏區。
         不剖開就等於沒有畫出任何一件事。
       ⚠ 2D 那張的第 ② 段講的是串／並聯拓樸（哪一顆掛在地上、哪一顆串在線上）——
         那是電路關係不是空間形狀，所以 3D 這一張不重畫，保留在 2D。
       ⚠ 氣體放電管（GDT）不在這一張：它的內部是氣體游離電漿，畫不出可查證的結構，
         而且 2D 已經明寫「查不到台股對應」。*/
    resistor_protect: {
      title: '被動保護：四顆並排剖開，四種完全不同的物理',
      sub: '左到右＝PPTC（高分子＋碳黑鏈，過流自恢復）／NTC（均質燒結陶瓷，擋開機湧浪電流）／MOV（氧化鋅晶粒＋晶界，過壓導走能量）／TVS（PN 接面＋空乏區，把電壓壓到最低、擺最靠近 IC）。★ 四顆的外觀都只是小方塊，差別全部在裡面。示意圖，非實物比例',
      camera: [62, 48, 104], target: [0, 7, 0], fit: 1.0, hk: 0.48,
      parts: [
        { seg: 'passive_comp', part: 'cp_ins', name: 'PPTC：外包絕緣層', note: '最外面那一層樹脂或塑膠薄膜。它不參與導電，只是把裡面包起來 —— 所以這裡畫成一個空的殼，不是一塊實心',
          kind: 'cpshell', box: [26, 17, 20], at: [-42, 8, 0], ex: [0, -14, 0],
          codes: ['6224', '6642'], chipnote: 'PPTC 自恢復保險絲台股：6224 聚鼎、6642 富致。兩家都不在 supply_chain.yaml 裡，所以直接指名；本圖不區分兩家的技術差異（查不到就不編）' },
        { seg: 'passive_comp', part: 'cp_ni', name: 'PPTC：鎳電極箔 ×2', note: '上下各一片，夾住中間的高分子基體。★ 是相對的兩面，不是同一面的兩端 —— 電流要垂直穿過高分子。底下那一層薄錫說明它是表面黏著件',
          kind: 'cpfoil', box: [22, 14, 18], at: [-42, 8, 0], ex: [0, 9, 0],
          codes: ['6224', '6642'], chipnote: 'PPTC 台股：6224 聚鼎、6642 富致（兩家都不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'cp_poly', name: 'PPTC：高分子基體', note: '聚乙烯類的高分子。低溫時結晶之間的導電粒子構成三維網路而導通；電流過大升溫後體積膨脹、由結晶態轉為非結晶態，網路斷裂而不導通；溫度降低後恢復結晶，又可導通 —— 這就是「自恢復」',
          kind: 'cppoly', box: [22, 10, 18], at: [-42, 8, 0], ex: [0, 4, 0],
          codes: ['6224', '6642'], chipnote: 'PPTC 台股：6224 聚鼎、6642 富致（兩家都不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'cp_carbon', name: 'PPTC：導電碳黑粒子（串成鏈）', note: '★ 常溫時黑色顆粒連成貫穿上下電極的通路 —— 它是一條一條的鏈，不是均勻的黑色。過流發熱時高分子膨脹、鏈被拉斷。只畫「變紅」不畫「變厚＋斷鏈」就沒有解釋機制。膨脹的實際比例查不到，本圖不寫百分比',
          kind: 'cpcarbon', box: [22, 10, 18], at: [-42, 8, 0], ex: [0, 16, 0],
          codes: ['6224', '6642'], chipnote: 'PPTC 台股：6224 聚鼎、6642 富致（兩家都不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'cp_ntc', name: 'NTC 熱敏電阻（串在線上）', note: '★ 金屬氧化物燒結的均質陶瓷本體 ＋ 兩個相對面電極，沒有晶界網也沒有 PN 接面。★ 它擋的不是突波電壓，是開機瞬間的湧浪電流 —— 跟另外三顆不是同一件事，而且它串在主線上、沒有接地腿',
          kind: 'cpntc', box: [22, 16, 18], at: [-14, 7, 0], ex: [0, 8, 0],
          codes: ['2428'], chipnote: '2428 興勤（NTC 熱敏電阻、壓敏電阻與保護元件）。興勤不在 supply_chain.yaml 裡，所以直接指名。信心：reported（產業媒體）' },
        { seg: 'passive_comp', part: 'cp_grain', name: 'MOV：ZnO 晶粒（本體）', note: '氧化鋅晶粒燒結而成（加入少量鉍、鈷、錳等金屬氧化物）。★ 一堆大小不一的多邊形，不是一塊均質陶瓷 —— 畫成均質方塊就不是 MOV，那跟旁邊的 NTC 長得一模一樣。晶粒的實際尺寸與數量查不到，圖上是示意',
          kind: 'cpgrain', box: [24, 15, 18], at: [14, 8, 0], ex: [0, 2, 0],
          codes: ['2428'], chipnote: '2428 興勤（壓敏電阻 MOV 與保護元件）。興勤不在 supply_chain.yaml 裡。信心：reported（產業媒體）' },
        { seg: 'passive_comp', part: 'cp_gb', name: 'MOV：晶界（電流真正被擋住的地方）', note: '★ MOV 的非線性完全來自晶界：每一對相鄰晶粒之間的界面形成一個微觀位壘，一顆裡面有數以百萬計個，串並聯成一張三維的網。圖上那條折線是電流穿過好幾道晶界的路徑（示意，不是只有一條）',
          kind: 'cpgb', box: [24, 15, 18], at: [14, 8, 0], ex: [0, 15, 0],
          codes: ['2428'], chipnote: '2428 興勤（壓敏電阻 MOV 與保護元件，不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'cp_movel', name: 'MOV：電極 ×2（並聯到地）', note: '★ 在兩個相對的面（上下），不是同一面的兩端 —— 電流要垂直穿過整疊晶粒才會撞到那些晶界。★ 它是會消耗的：每吸收一次突波內部就退化一點，最後通常以短路收場；寄生電容大，不適合掛在高速資料線上',
          kind: 'cpelec', box: [24, 19, 18], at: [14, 8, 0], ex: [0, 10, 0],
          codes: ['2428'], chipnote: '2428 興勤（壓敏電阻 MOV，不在 supply_chain.yaml 裡）。「每擋一次就退化、最終短路」與「寄生電容大」來自同一篇比較型整理（單一來源），所以本圖不寫任何鉗位比、電壓值與 pF 數字' },
        { seg: 'passive_comp', part: 'cp_pn', name: 'TVS：PN 接面（P 區／空乏區／N 區）', note: '★ 兩種不同摻雜的半導體區、中間一條空乏區窄帶 —— 這是 TVS 的識別特徵，雪崩就發生在那條窄帶裡。畫成陶瓷晶粒就是畫成了 MOV（兩者的物理機制完全不同），畫成三明治薄膜就是畫成了晶片電阻',
          kind: 'cppn', box: [22, 13, 18], at: [42, 7, 0], ex: [0, 3, 0],
          codes: ['6284'], chipnote: '6284 佳邦（ESD／TVS 等過電壓保護元件）。佳邦不在 supply_chain.yaml 裡，所以直接指名' },
        { seg: 'passive_comp', part: 'cp_tvsel', name: 'TVS：金屬電極 ×2（並聯到地，最靠近 IC）', note: '上下各一片，把 PN 接面夾在中間。★ 它與 IC 之間不准再插別的元件：把電壓壓得比壓敏電阻更低、漂移更小 —— 這就是「分層」，靠外的第一道擋大能量、靠近 IC 的第二道把電壓壓下來。順序反過來就沒有意義',
          kind: 'cpelec', box: [22, 17, 18], at: [42, 7, 0], ex: [0, 11, 0],
          codes: ['6284'], chipnote: '6284 佳邦（ESD／TVS 過電壓保護元件，不在 supply_chain.yaml 裡）' },
      ],
    },
    /* ===== 一般電子鏈：電容器 —— 鋁電解與固態電容剖面 ===== */
    /* 2D 是 `site/dg/alum_cap.js`，`part` 沿用它的 `data-part`（ac_*）。
       構圖：左邊整顆鋁電解縱剖（用半管切，壁厚看得見）、中間把捲芯的四層水平拉開、右邊固態電容對照。
       ★ 為什麼非得立體：鋁電解是一顆**捲**出來的東西，這是它跟 MLCC（疊出來的）最根本的差別 ——
         整顆縱剖看得到捲芯塞在鋁殼裡、頂面那幾圈同心弧說明它是捲的，四層帶再拉開才看得懂
         「四層一起捲」跟「一層一層疊」不是同一件事。
       ⚠ 防爆閥畫在與封口相反的那一端，但這一點查不到可引用的來源（各家做法不同），標為示意。*/
    capacitor: {
      title: '電容器：一顆鋁電解縱剖開，加上它捲起來的那四層',
      sub: '左：整顆鋁電解縱剖 —— 外套膠膜／鋁殼／捲芯／橡膠封口／兩根導針／底部防爆閥。中：捲芯的四層水平拉開 —— 陽極箔（表面咬出蜂窩孔、孔壁長氧化膜）／電解紙含浸電解液／陰極箔（一樣有孔，但沒有氧化膜）。★ 真正的陰極是電解液，不是陰極箔；介電質是長出來的氧化膜，不是買來的。右：固態電容對照。示意圖，非實物比例',
      camera: [72, 66, 108], target: [6, 26, 0], fit: 1.0, hk: 0.52,
      parts: [
        { seg: 'passive_comp', part: 'ac_sleeve', name: '外套膠膜', note: '包在鋁殼外面的有色薄膜。★ 本圖上面一個字、一個色碼、一個廠商標示都沒有 —— 那些是產品外觀，不是結構',
          kind: 'acsleeve', box: [29, 56, 29], at: [-30, 28, 0], ex: [-28, 0, 0],
          codes: ['2375', '2472', '4939'], chipnote: '做鋁質電解電容的台股：2375 智寶，另有 2472 立隆電與 4939 亞電（兩家不在 supply_chain.yaml 裡，這裡一併指名）' },
        { seg: 'passive_comp', part: 'ac_can', name: '鋁殼', note: '捲芯含浸完之後裝進去的薄壁圓筒，一端封死、另一端才封口。★ 用半管切開而不是切方塊：壁厚看得見，才看得出「裡面裝著捲芯」。上緣那道頸縮就是封口橡膠卡住的地方',
          kind: 'accan', box: [28, 56, 28], at: [-30, 28, 0], ex: [-16, 0, 0],
          codes: ['2375', '2472', '4939'], chipnote: '做鋁質電解電容的台股：2375 智寶、2472 立隆電、4939 亞電（後兩家不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'ac_winding', name: '捲芯（四層一起捲成一個圓柱）', note: '★ 四層同時捲在一個大直徑輪上，兩張箔稍微橫向錯開避免邊緣接觸。三層捲起來，上一圈的陽極會直接碰到下一圈的陰極 —— 短路。頂面那幾圈同心弧就是「它是捲出來的」的證據',
          kind: 'accore', box: [23, 44, 23], at: [-30, 27, 0], ex: [-6, 0, 0],
          codes: ['2375', '2472', '4939'], chipnote: '做鋁質電解電容的台股：2375 智寶、2472 立隆電、4939 亞電' },
        { seg: 'passive_comp', part: 'ac_seal', name: '橡膠封口', note: '在鋁殼的一端，兩根導針從這裡穿出去。它同時是密封件，也是壓力上來時的洩壓路徑之一',
          kind: 'acseal', box: [26, 6, 26], at: [-30, 53, 0], ex: [0, 22, 0],
          codes: ['2375', '2472', '4939'], chipnote: '做鋁質電解電容的台股：2375 智寶、2472 立隆電、4939 亞電' },
        { seg: 'passive_comp', part: 'ac_lead', name: '導針（引線）×2', note: '一根接陽極箔、一根接陰極箔。★ 整顆的兩根導針從同一端穿出（徑向引線型）—— 一端一根那是軸向型，跟這裡的捲芯畫法對不起來。焊在箔上的那一段是扁的，穿出去的那一段才是圓的',
          kind: 'aclead', box: [3.4, 18, 3.4], at: [-30, 63, 0], n: 2, gap: 12, axis: 'x', ex: [0, 32, 0],
          codes: [], chipnote: '導針這一件，查不到台股的具名對應' },
        { seg: 'passive_comp', part: 'ac_vent', name: '防爆閥（刻痕）', note: '壓力上來時先從這裡裂開，不讓整顆炸掉。★ 本圖把它畫在與封口相反的那一端，但這一點查不到可引用的來源（徑向引線型的防爆結構各家做法不同），所以標為示意，也不寫刻痕形狀的規格',
          kind: 'acvent', box: [24, 3, 24], at: [-30, 1.5, 0], ex: [0, -20, 0],
          codes: ['2375', '2472', '4939'], chipnote: '做鋁質電解電容的台股：2375 智寶、2472 立隆電、4939 亞電' },
        { seg: 'passive_comp', part: 'ac_anode', name: '陽極箔（容量就是從這裡來的）', note: '先用電化學蝕刻把表面咬成蜂窩狀，有效表面積放大很多倍 —— 容量就是從這裡來的。再通電做陽極氧化，在孔壁上長出氧化鋁介電質',
          kind: 'acfoil', box: [40, 2.6, 22], at: [26, 43, 0], k: 0.3, ex: [16, 18, 0],
          codes: ['2375'], chipnote: '★ 這一層的上游是 6175 立敦（電容用鋁箔 —— 電蝕箔、化成箔）。立敦不做電容成品，它做的是這一層的材料；立敦不在 supply_chain.yaml 裡' },
        { seg: 'passive_comp', part: 'ac_pore', name: '蝕刻孔（隧道／海綿狀）', note: '咬出來的孔。孔越多越深，同一片箔的表面積越大。★ 兩面都咬，中間要留一條實心芯 —— 沒有芯的箔會斷。本圖不寫孔徑、孔密度與表面積放大倍數（查不到共通值）',
          kind: 'acpore', box: [40, 2.6, 22], at: [26, 43, 0], ex: [16, 27, 0],
          codes: ['2375'], chipnote: '上游是 6175 立敦（電容用鋁箔，不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'ac_core', name: '箔的基體（未蝕刻的芯部）', note: '兩面被咬之後中間留下來的那一條實心鋁。圖上的芯厚是「箔厚 − 2×孔深」真的減出來的，不是目測',
          kind: 'acspine', box: [40, 2.6, 22], at: [26, 43, 0], ex: [16, 36, 0],
          codes: ['2375'], chipnote: '上游是 6175 立敦（電容用鋁箔，不在 supply_chain.yaml 裡）' },
        { seg: 'passive_comp', part: 'ac_oxide', name: '陽極氧化膜（Al₂O₃，介電質）', note: '★ 介電質不是買來的，是長出來的：鋁箔通電做陽極氧化，表面長出一層氧化鋁。膜厚由外加電壓決定 —— 耐壓越高、膜越厚、容量越小（每伏特幾埃是 roughly 的說法，所以不寫數字）。★ 它只長在陽極箔上，陰極箔沒有這層膜，這就是「為什麼有極性」',
          kind: 'acoxide', box: [40, 3.0, 22], at: [26, 43, 0], ex: [16, 11, 0],
          codes: [], chipnote: '氧化膜是「化成」這一道製程長出來的，屬於箔的加工、不是電容廠的獨立採購件 —— 做化成箔的是 6175 立敦，它不做電容成品也不在 supply_chain.yaml 裡，所以這一格不列' },
        { seg: 'passive_comp', part: 'ac_paper', name: '電解紙（隔離紙）', note: '天然纖維素做的紙，含浸電解液，同時把兩張箔隔開。★ 它本身不是電極，也不是介電質 —— 介電質是陽極箔上那層氧化膜',
          kind: 'acpaper', box: [40, 1.6, 22], at: [26, 34, 0], ex: [16, 2, 0],
          codes: [], chipnote: '電解紙與電解液這一段，查不到台股對應，先標為未知 —— 查不到就寫查不到' },
        { seg: 'passive_comp', part: 'ac_elyte', name: '電解液（★ 它才是真正的陰極）', note: '★ 這張圖的第三句話：陰極箔不是陰極，真正的陰極是含浸在紙裡的電解液。它要鑽進陽極箔的孔裡、貼住氧化膜 —— 只畫在紙裡就是沒有接觸到介電質，電容不成立',
          kind: 'acelyte', box: [40, 1.4, 22], at: [26, 30, 0], ex: [16, -6, 0],
          codes: [], chipnote: '電解液的配方與化學品這一段，查不到台股對應，先標為未知' },
        { seg: 'passive_comp', part: 'ac_cathode', name: '陰極箔（不是陰極，是集電體）', note: '★ 一樣有蝕刻孔，但沒有那層氧化膜（只有自然氧化層）。它的工作是把電解液的電引出來 —— 兩面都畫氧化膜就變成了雙極性電容，而且把「為什麼有極性」這件事畫掉了',
          kind: 'acfoil', box: [40, 2.6, 22], at: [26, 25, 0], k: -0.12, ex: [16, -16, 0],
          codes: [], chipnote: '陰極箔是誰做的本次查不到。查到的 6175 立敦講的是電蝕箔與化成箔（陽極側），不能直接套到陰極箔上' },
        { seg: 'passive_comp', part: 'ac_solid', name: '固態電容（對照組）', note: '★ 固態電容只換了一樣東西：把電解液換成固態的導電高分子。它一樣要鑽進陽極箔的孔裡。等效串聯電阻大幅下降，而且沒有液體可以汽化，所以不會鼓脹爆漿（來源只講材料導電度，不是成品的 ESR 改善倍數，所以不寫倍數）',
          kind: 'acsolid', box: [24, 26, 24], at: [66, 13, 0], ex: [30, 0, 0],
          codes: ['6449'], chipnote: '6449 鈺邦（固態電容）。鈺邦不在 supply_chain.yaml 裡，所以直接指名' },
      ],
    },
    /* ===== 一般電子鏈：被動元件 —— 電感・電阻・石英 ===== */
    /* 2D 是 `site/dg/power_inductor.js`，`part` 沿用它的 `data-part`（ind_* / res_* / xtal_*）。
       構圖：三顆並排、各自切掉朝鏡頭那一半。
       ★ 這三顆的識別特徵**都被蓋住了** —— 繞組埋在磁粉裡、雷射修整溝壓在玻璃層底下、
         石英片封在密封腔裡。半剖是唯一看得到它們的方式，這就是這張圖做 3D 的理由。
       ⚠ 三者之間**沒有上下游關係**，所以這一張刻意沒有任何流線與箭頭
         （放在一起是因為它們真的在同一塊板子的同一區）。
       ⚠ 只有「晶片電阻」那一欄對得到供應鏈環節（passive_comp）；
         電感與石英在供應鏈圖上還沒有自己的一格，所以台股用零件自己的 `codes` 列。*/
    power_inductor: {
      title: '被動元件：電感・電阻・石英，三顆各切開一半',
      sub: '左：功率電感 —— 磁芯與外殼是同一塊金屬磁粉，扁平銅線立繞埋在裡面，磁通走在本體裡不外漏。中：晶片電阻 —— 陶瓷基板上印電阻膜，量完用雷射切一道 L 形溝把阻值修上去，再蓋玻璃層（所以溝在玻璃底下）。右：石英諧振器 —— 石英片只靠同一端的兩點架著、懸空在密封腔裡，封不住時間就走鐘。示意圖，非實物比例',
      camera: [58, 46, 100], target: [0, 7, 0], fit: 1.0, hk: 0.46,
      parts: [
        { seg: 'power_inductor', part: 'ind_body', name: '電感：金屬磁粉壓製的本體', note: '★ 磁芯與外殼是同一塊 —— 看不到縫，那正是它跟「繞線型＋鐵氧體上蓋」最好分辨的地方（後者磁芯、圓線、上蓋是分開的件，看得到縫隙）。比鐵氧體更耐大電流。剖面上那層細顆粒是壓製的粉粒感（示意）',
          kind: 'indbody', box: [30, 16, 24], at: [-36, 8, 0], ex: [0, -4, 0],
          codes: ['3357', '3236', '6155'], chipnote: '台股在「功率電感」族群：3357 臺慶科、3236 千如、6155 鈞寶。★ 這一欄在供應鏈圖上沒有自己的環節，所以直接指名' },
        { seg: 'power_inductor', part: 'ind_wind', name: '電感：扁平銅線繞組', note: '★ 斷面是長方形（高 > 寬）—— 扁平線立繞，同樣空間塞進更多銅，直流電阻更低。畫成圓線就變成另一種做法了。一段一段拼成的環就是「繞」出來的，不是一顆環',
          kind: 'indwind', box: [24, 12, 18], at: [-36, 8, 0], ex: [0, 15, 0],
          codes: ['3357', '3236', '6155'], chipnote: '台股在「功率電感」族群：3357 臺慶科、3236 千如、6155 鈞寶（供應鏈圖上沒有這一格）' },
        { seg: 'power_inductor', part: 'ind_flux', name: '電感：磁通路徑（封閉、走在本體裡）', note: '★ 磁通不跑出本體之外 —— 那就是「磁屏蔽」這個說法的意思。而且路徑一定是封閉的：從繞組中心往上、沿本體外圍下來、再回到中心。畫成一條有頭有尾的線就是把磁路畫成了電路',
          kind: 'indflux', box: [30, 16, 24], at: [-36, 8, 0], ex: [0, -16, 0],
          codes: [], chipnote: '磁通是物理現象，不是一個買得到的零件' },
        { seg: 'power_inductor', part: 'ind_term', name: '電感：引出端子（只在底面）', note: '★ 繞組兩端折出來貼在底面，所以它是表面黏著件，不是插件（沒有腳穿過板子）。★ 規格要看兩個電流：飽和電流 Isat 與溫升電流 Irms，小的那一個才是天花板',
          kind: 'indterm', box: [30, 2.6, 24], at: [-36, 1, 0], ex: [0, -10, 0],
          codes: ['3357', '3236', '6155'], chipnote: '台股在「功率電感」族群：3357 臺慶科、3236 千如、6155 鈞寶' },
        { seg: 'passive_comp', part: 'res_substrate', name: '電阻：氧化鋁陶瓷基板', note: '整顆零件的底，也是散熱的路；上面的每一層都印在它身上',
          kind: 'reslay', box: [26, 2.8, 18], at: [0, 1.4, 0], ex: [0, -6, 0] },
        { seg: 'passive_comp', part: 'res_bottom', name: '電阻：背面電極', note: '基板背面也印一層 —— 它是散熱與焊接的路。只畫正面那一層的話，這顆零件焊在板子上是靠什麼貼住的就沒有答案',
          kind: 'resback', box: [26, 0.8, 18], at: [0, -0.4, 0], ex: [0, -14, 0] },
        { seg: 'passive_comp', part: 'res_film', name: '電阻：電阻膜（釕系厚膜）', note: '網印上去再燒結。★ 兩端壓在電極上（是重疊，不是頭碰頭對接）—— 對接的接口一受熱就開路',
          kind: 'resfilm', box: [26, 1.4, 18], at: [0, 3.5, 0], ex: [0, 9, 0] },
        { seg: 'passive_comp', part: 'res_trim', name: '電阻：雷射修整溝 ← 它的身分證', note: '★ 印出來的阻值不會剛好，量完用雷射切一道溝，把電流的路徑拉長、阻值往上修。溝是 L 形（先切進去再轉向），不是一條直線 —— 直線切過頭就報廢了，L 形才修得準',
          kind: 'restrim', box: [26, 1.6, 18], at: [0, 3.6, 0], ex: [0, 17, 0] },
        { seg: 'passive_comp', part: 'res_glass', name: '電阻：玻璃保護層', note: '★ 修完才蓋上去，所以那道溝在它底下 —— 溝露在最外面就是畫錯。半透明才看得到底下那道溝，那正是這一層要證明的事',
          kind: 'resglass', box: [20, 1.2, 18], at: [0, 4.9, 0], ex: [0, 24, 0] },
        { seg: 'passive_comp', part: 'res_term3', name: '電阻：三層端電極', note: '★ 一定是三層：內層（與電阻膜接觸）→ 鎳阻障（擋焊錫把內層吃掉）→ 錫（好焊）。少掉鎳那一層，焊兩次就把內層吃光。這跟 MLCC 的端電極是同一套道理',
          kind: 'resterm', box: [28, 7, 18], at: [0, 3.4, 0], ex: [0, 1, 0] },
        { seg: 'power_inductor', part: 'xtal_base', name: '石英：陶瓷底座（有凹穴）', note: '★ 石英片是懸空在凹穴裡的，不是貼在底面上 —— 貼死就振不動了。底面四個焊墊說明它是表面黏著件',
          kind: 'xtalbase', box: [28, 6, 20], at: [38, 3, 0], ex: [0, -8, 0],
          codes: ['3042', '2484', '3221'], chipnote: '台股在「石英頻率控制」族群：3042 晶技、2484 希華、3221 台嘉碩。★ 這一欄在供應鏈圖上沒有自己的環節，所以直接指名' },
        { seg: 'power_inductor', part: 'xtal_mount', name: '石英：只靠同一端的兩點架著', note: '★ 四周都不能碰到東西 —— 碰到就振不動。支撐點數量為示意。導電膠同時是機械支撐與電氣連接（電極的引線就走這裡下來）',
          kind: 'xtalmount', box: [10, 2.4, 14], at: [38, 7.2, 0], ex: [0, 6, 0],
          codes: ['3042', '2484', '3221'], chipnote: '台股在「石英頻率控制」族群：3042 晶技、2484 希華、3221 台嘉碩' },
        { seg: 'power_inductor', part: 'xtal_blank', name: '石英：石英片（AT 切）', note: '★ 厚度決定頻率（越薄頻率越高）—— 所以這一片的厚薄不是隨便畫的。AT 切＝相對於晶軸切一個特定角度，那個角度決定它的溫度特性',
          kind: 'xtalblank', box: [22, 1.4, 15], at: [38, 9, 0], ex: [0, 13, 0],
          codes: ['3042', '2484', '3221'], chipnote: '台股在「石英頻率控制」族群：3042 晶技、2484 希華、3221 台嘉碩' },
        { seg: 'power_inductor', part: 'xtal_elec', name: '石英：電極（上下各一片）', note: '★ 面積比石英片小 —— 電場要垂直穿過石英才激得起厚度剪切振動。兩片各自拉一條引線到同一端的支撐點，所以那兩條引線一定在同一側、不是對角',
          kind: 'xtalelec', box: [22, 3, 15], at: [38, 9, 0], ex: [0, 20, 0],
          codes: ['3042', '2484', '3221'], chipnote: '台股在「石英頻率控制」族群：3042 晶技、2484 希華、3221 台嘉碩' },
        { seg: 'power_inductor', part: 'xtal_cavity', name: '石英：密封的空腔（裡面是空的）', note: '★ 封不住，頻率就跟著環境跑掉 —— 這是這一類零件的生死線。這一格是「空的」，不是一種材料',
          kind: 'plain', box: [23, 5.5, 16], at: [38, 9.6, 0], ghost: true, mat: 'glass', ex: [0, -18, 0],
          codes: [], chipnote: '空腔不是一個買得到的零件' },
        { seg: 'power_inductor', part: 'xtal_lid', name: '石英：金屬蓋＋縫焊密封', note: '用電阻加熱把金屬蓋焊在陶瓷底座上。★ 焊縫是一圈連續的 —— 斷一個點就封不住，時間就跟著走鐘',
          kind: 'xtallid', box: [28, 5, 20], at: [38, 13, 0], ex: [0, 28, 0],
          codes: ['3042', '2484', '3221'], chipnote: '台股在「石英頻率控制」族群：3042 晶技、2484 希華、3221 台嘉碩' },
      ],
    },
    /* ===== AI 伺服器鏈：高速連接器與互連 ===== */
    /* 2D 是 `site/dg/ai_interconnect.js`，`part` 沿用它的 `data-part`（st_*／cage_*／gold_finger…）。
       ★ 2026-09-23 Andy 親自點名「連接器少了 3D 圖 請補上」，所以這張從 `scene: null` 補成真 3D。
         2D 檔頭原本寫「不做真 3D」，理由是「這四類連接器在機櫃裡的位置，ai_server 鏈層級的場景已經在做」——
         那個理由只對「位置」成立，對「一個接點本身長什麼樣」不成立：
         籠子是一個五面包起來的盒子、金手指鋪在舌片的**上下兩面**、壓接針從底下穿進板子、
         飛越纜線從晶片旁邊**架空**拉到籠背 —— 這四件都是遮蔽關係，剖面畫不出來，轉一圈才看得到。
       ★ 硬規則（規格書 W1-1 的四件事，缺一不可）：
         ① 屏蔽金屬籠（cage） ② 塑膠舌片 ＋ 舌片上**成對**排列的金手指
         ③ 背面壓接針（連到 PCB 的那一端） ④ 飛越纜線（繞開 PCB 損耗）。
       ★ 顏色（兩種模式都量過，兩兩 CIE76 ΔE ≥ 27.4）：
         籠與模組殼銀灰 --dg-m-rack ／ 板材墨綠 --dg-m-pcb ／ 金手指金 --dg-m-trace ／
         塑膠件藍灰 --dg-m-fanf ／ 壓接針青銅 --dg-organic ／ 線纜外被訊號藍 --dg-fl-sig ／
         光纖接口青 --dg-fl-opt。*/
    ai_interconnect: {
      title: '高速連接器：一個接點拆開（立體）',
      sub: '中間那個金屬盒子就是屏蔽籠 —— 高速連接器之所以長這樣，是為了擋電磁干擾、順便把模組的熱帶走。籠子裡是塑膠舌片，舌片的上下兩面鋪著金手指，而且是★成對排的（一對＝一組差動訊號），不是一根一根等距。籠子底下一整排壓接針壓進板子的孔裡 —— 壓接不是焊接，所以它拔得下來重工。右邊那束飛越纜線從晶片旁邊架空拉到籠背，繞開板子：同樣的距離，細同軸纜線的損耗比板上銅走線小得多。示意圖，非實物比例',
      camera: [70, 52, 120], target: [0, 6, 0], fit: 1.06, hk: 0.6,
      parts: [
        { seg: 'hdi_pcb', part: 'st_board', alias: ['pcb_route'], name: '板子（只畫輪廓與走線）', note: '這張圖的主題是**接點**不是板子 —— 所以板子只畫一片薄板與表面走線，層數、疊構與背鑽是「PCB 硬板剖面」那張的事。訊號從晶片出來之後就分兩條路：走板子（會被板材吃掉），或走右邊那束架空的線纜',
          kind: 'swboard', box: [88, 3, 58], at: [0, 0, 0], ex: [0, -16, 0] },
        { seg: 'connector', part: 'st_asic', name: 'ASIC／GPU（訊號的起點）', note: '★ 這一顆是**訊號的起點，不是連接器零件** —— 它由晶圓代工與封裝廠做，所以底下不列連接器台股。畫它只是為了交代「飛越纜線是從晶片旁邊拉出去的」這件事',
          kind: 'hsasic', box: [20, 7, 20], at: [-26, 5, -4], ex: [0, 10, -10],
          codes: [], chipnote: '晶片不是這張圖的主題，也不掛連接器環節（它在半導體鏈那幾張圖裡）' },
        { seg: 'connector', part: 'cage_body', alias: ['st_cage', 'emi_finger', 'cage_hs', 'belly'], name: '屏蔽金屬籠（cage）', note: '★ **籠子就是高速連接器的識別特徵** —— 它是為了擋電磁干擾才存在的，順便把模組的熱帶出去（所以籠背有鰭片、側壁有通風孔）。籠口那一圈被壓住的薄片是 EMI 指片：模組插進來時接地才連續。沒有籠子，它跟一個電源端子在外形上分不開',
          kind: 'hscage', box: [30, 16, 28], at: [22, 9.5, 4], ex: [0, 18, 0] },
        { seg: 'hdi_pcb', part: 'gold_finger', alias: ['st_finger', 'card_edge', 'chamfer'], name: '塑膠舌片 ＋ 舌片上下兩面的金手指', note: '★ 金手指**成對**排列（一對＝一組差動訊號），每兩對之間夾一根比較寬的接地腳 —— 一根一根等距的那是低速端子。由內到外是銅 → 鎳阻障 → 硬金，前緣倒角才插得進去。收攏時它被籠子蓋住，游標移過去拆開才看得到',
          kind: 'hstongue', box: [23, 7, 21], at: [22, 8, 4], ex: [0, 2, 34] },
        { seg: 'connector', part: 'cage_pressfit', name: '背面壓接針（press-fit）', note: '★ 壓接針**不是焊上去的**：針腰那個「針眼」被孔壁夾扁、靠彈性維持接觸，所以整顆連接器拔得下來重工 —— 焊上去的拔不下來。材質是磷青銅，所以顏色偏青銅不是錫白。這一整排就是「它怎麼裝到板子上」的答案',
          kind: 'hspin', box: [26, 8, 22], at: [22, -3, 4], ex: [0, -16, 0] },
        { seg: 'connector', part: 'slot_housing', alias: ['slot_beam', 'slot_leg', 'beam_zoom'], name: '母端插槽：塑膠殼 ＋ 上下兩列懸臂彈片', note: '★ 導通靠的是**彈片被金手指撐開**的那個法向力，不是「插到底就通」。插入時接點擦過金手指表面（擦拭），把氧化層刮掉 —— 這兩件事就是連接器真正在賣的東西。畫成一條溝就全看不到了',
          kind: 'hsslot', box: [26, 10, 11], at: [-6, 6, 25], ex: [-14, 6, 14] },
        { seg: 'connector', part: 'twinax', alias: ['st_twinax', 'st_cable', 'cable_body', 'cable_plug', 'cable_recept'], name: '飛越纜線（flyover，twinax 雙軸線）', note: '★ 它存在的理由只有一個：同樣的距離，細同軸纜線的損耗比板子上的銅走線小得多。所以它一定是**架空**的（不貼板），而且走了纜線的那幾個埠，板子內層就不該再有同一條訊號的走線。剖開的那一端看得到遮蔽層裡是**兩根等徑導體**（差動對），不是一根',
          kind: 'hsfly', box: [46, 16, 9], at: [-2, 16, -18], ex: [0, 14, -10] },
        { seg: 'optical', part: 'optic_module', name: '插進籠子的光模組（只有外殼與拉環）', note: '這張圖只畫模組的外殼、拉環與前端的光纖接口 —— 它自己的內部（DSP、驅動 IC、雷射、TIA）是「交換器板卡」那張的主題。模組唯一的電接點在**後端**（插進籠子的那一頭），不是光纖那一頭',
          kind: 'swmod', box: [9, 7, 26], at: [22, 9.5, 22], ex: [0, 10, 42] },
      ],
    },
  };

  function hasScene(id) { return !!SCENES[id]; }

  /* ================================================================ E3：零件建造函式
     每支拿到 (T, p, K)：T 是 THREE、p 是零件資料、K 是這個零件專屬的材質工具箱。
     一律「畫在自己的局部座標、以 box 的中心為原點」，擺位交給外面統一處理。
     K.mat(明暗, 選項) 回傳材質：明暗 > 0 偏亮、< 0 偏暗，同一組參數會共用同一顆材質，
     highlight() 才有辦法一次把整個零件變透明。led:true 的是指示燈（E2 唯一准發光的東西）。 */
  /* ★★ 2026-09-22 根治「零件底色來自環節色」（DECISIONS #238）。
       以前 kit(THREE, hex) 的 hex 就是 segColor(seg)：一個場景有幾個環節就有幾個色相，
       整台機櫃紫粉綠褐混在一起 —— 那正是「一張圖一個主色」的反面。
       現在：**大塊幾何讀材質族的 token**（板子是板子色、金屬是金屬色），
       環節色只留給「被點的那一顆」的提亮與卡片上的小圓點（segHex 存在 byIdx，不進材質）。
     材質族 → token（讀不到就退到後面那個，最後才用 dflt；dflt 跟 :root 的值一樣，只是保險）。*/
  /* ★ 2026-09-22（DECISIONS #244，規格書一-4）：每一族先讀「模組色」token（`--dg-m-*`）。
     以前的根因是**顏色依角色（訊號／電力／液冷）整片上色**，整台被青藍洗掉，
     關掉標籤就認不出哪塊是電源、哪塊是運算。現在顏色由「這是什麼模組、什麼材質」決定：
       機架銀灰金屬 ／ PCB 墨綠 ／ 晶片深藍與石墨灰 ／ 銅件暖銅 ／ 液冷青綠 ／ 風扇框藍灰 ／ 電源暖橘。
     `--dg-m-*` 只定義在 `.dg3d` 上（2D 讀不到、一個像素都不受影響），
     讀不到就往後退到原本的 token，所以 probe()／舊環境仍然畫得出東西。*/
  const FAMILY_TOKENS = {
    metal:   [['--dg-m-rack', '--dg-metal', '--dg-steel'], '#9aa6b4'],
    cer:     [['--dg-cer'], '#d3cbb7'],
    pcb:     [['--dg-m-pcb', '--dg-pcb-3d', '--dg-pcb'], '#1a4230'],
    cu:      [['--dg-m-cu', '--dg-cu'], '#b0743a'],
    glass:   [['--dg-glass'], '#8fb6c9'],
    plastic: [['--dg-m-fanf', '--dg-plastic', '--dg-frame'], '#1a2540'],
    si:      [['--dg-m-die', '--dg-si'], '#33488a'],
    sn:      [['--dg-sn'], '#e2e7ec'],
    organic: [['--dg-organic'], '#8a6636'],
    alu:     [['--dg-m-hs', '--dg-alu'], '#a3b2c4'],
    emc:     [['--dg-m-graphite', '--dg-emc'], '#2f3039'],
  };
  /* 材質族的 PBR 預設手感（規格書一-4 那張表的第三欄）。
     以前所有材質不分族都是 `rough .55 / metal .22` —— 那個 .22 是「沒有環境貼圖只好壓低金屬度」
     的補償值（根因 1），補上 envMap 之後就不必了，金屬可以真的是金屬。
     建造函式自己寫了 metal／rough 的地方**優先**，這張表只補沒寫的。*/
  const FAMILY_PBR = {
    metal:   { metal: 0.85, rough: 0.35 },   // 機架／滑軌／鈑金：銀灰霧面金屬
    alu:     { metal: 0.70, rough: 0.45 },   // 鋁擠鰭片／散熱蓋
    cu:      { metal: 0.90, rough: 0.30 },   // 銅件／快接頭／冷板
    sn:      { metal: 0.60, rough: 0.34 },   // 錫（球、鍍層）
    pcb:     { metal: 0.05, rough: 0.55 },   // 板材是介電質，不是金屬
    cer:     { metal: 0.04, rough: 0.58 },   // 陶瓷
    si:      { metal: 0.35, rough: 0.45 },   // 矽（晶粒、中介層）
    organic: { metal: 0.06, rough: 0.68 },   // 有機基材（ABF、重佈線）
    emc:     { metal: 0.10, rough: 0.62 },   // 模封
    plastic: { metal: 0.15, rough: 0.62 },   // 塑膠框
    glass:   { metal: 0.02, rough: 0.14 },
  };
  // kind 的預設材質族（場景可以用 `mat:` 蓋掉）
  const FAMILY = {
    rack: 'glass', backplane: 'pcb', tray: 'metal', gpu: 'cer', chip: 'cer', hbm: 'si', pcb: 'pcb', laminate: 'pcb',
    cdu: 'metal', uqd: 'metal', fan: 'plastic', psu: 'metal', battery: 'plastic', optic: 'metal', switch: 'metal',
    substrate: 'organic', balls: 'sn', rdl: 'organic', bridge: 'si', die: 'si', probe: 'cer', lid: 'glass',
    mlcc: 'cer', mlccterm: 'sn', mlccpad: 'pcb', plain: 'metal',
    interposer: 'si', bump: 'cu', bga: 'emc', mlccchip: 'cer', inductor: 'emc', resistor: 'cer', ecap: 'alu',
    heatsink: 'alu', vc: 'cu', heatpipe: 'cu', coldplate: 'cu', connector: 'metal', cable: 'emc', busbar: 'cu',
    rail: 'metal', screw: 'metal', bracket: 'metal', chassis: 'metal',
    /* 半導體鏈四張（2026-09-23）。材質族決定底色：矽（晶粒、晶圓、磊晶層）一律 si＝深藍，
       金屬機構件（爐體、提拉桿）走 metal＝銀灰，石墨件走 emc＝石墨灰，銅柱走 cu＝暖銅。
       ⚠ 這四張刻意**都只有一個主色**（矽），層與層之間靠明暗（K.mat 的 k）分，
          不是一層一個色相 —— 那正是 #244 要收掉的「整張被洗成調色盤」。*/
    fetp: 'si', fetf: 'si', nsheet: 'si', gaagate: 'metal', wafer: 'si', wstack: 'si',
    czshell: 'metal', crucible: 'cer', susceptor: 'emc', melt: 'si', ingot: 'si',
    seedrod: 'metal', heater: 'emc',
    hbmcore: 'si', hbmbase: 'si', tsvcol: 'cu', ubumprows: 'cu',
    wbglay: 'si', wbgbody: 'si', wbggate: 'si', wbgtop: 'metal', wbgpgan: 'organic', wbgelec: 'metal',
    /* AI 伺服器鏈六張（2026-09-23，DECISIONS #250）。同一條規矩：一張圖一個主色，
       層與層之間靠明暗分，不是一層一個色相。
         載板／硬板 → 有機基材與板材（organic／pcb），銅件（走線、孔、墊）走 cu、錫球走 sn
         電源       → 鈑金銀灰（metal）＋ 板材（pcb）＋ 銅排（cu）；電池殼走 plastic（卡片仍是電源暖橘）
         液冷       → 銅（cu）為主，接頭與管路走 metal，TIM 是有機膏（organic）
         氣冷       → 風扇框與導風罩走 plastic（藍灰）、輪轂走 alu、馬達與線材走 emc（石墨灰）
         網通       → 板材 pcb、籠架與模組殼 metal、ASIC 模封 emc、CPO 光引擎 si */
    abfcore: 'organic', abfbu: 'organic', abftrace: 'cu', abfvia: 'cu',
    abfsr: 'organic', abfpad: 'cu', abfbga: 'sn',
    pcblay: 'pcb', pcbtrc: 'cu', pcbmask: 'pcb', pcbenig: 'cu', pcbvia: 'cu',
    pshelf: 'metal', pshell: 'metal', pboard: 'pcb', pcardedge: 'pcb',
    pbusbar: 'cu', pvrm: 'pcb', pbbu: 'plastic', pscap: 'alu',
    timlay: 'organic', ihslid: 'cu', cplate: 'cu', cpfin: 'cu', cpport: 'metal',
    lcmani: 'metal', lcphe: 'metal',
    fframe: 'plastic', frotor: 'plastic', fhub: 'alu', fmotor: 'emc',
    fbear: 'metal', fwire: 'emc', fwall: 'plastic', fshroud: 'plastic',
    swboard: 'pcb', swasic: 'emc', swcage: 'metal', swmod: 'metal',
    swgold: 'pcb', swcpo: 'si',
    /* 一般電子鏈六張（2026-09-23）。同樣是**多出來的詞**，舊的一個都沒有動。
       ⚠ 一張圖一個主色（#244）：面板整疊走玻璃／薄膜的冷色，靠明暗分十三層；
          傳動件整根走金屬銀灰；保護元件走陶瓷與有機；電容走鋁；電感電阻石英走各自的本體材質。
          層與層之間靠 K.mat 的 k（明暗）分，不是一層一個色相。*/
    pnframe: 'metal', pnfilm: 'sn', pnlgp: 'glass', pnledbar: 'cer', pnprism: 'glass',
    pnpol: 'emc', pnglass: 'glass', pntft: 'cu', pnlc: 'glass', pncf: 'cer', pndriver: 'emc',
    mcbase: 'alu', mcmotor: 'metal', mcenc: 'emc', mccoup: 'metal', mcbrg: 'metal', mcscrew: 'metal',
    mcnut: 'metal', mcballs: 'metal', mcreturn: 'plastic', mcrail: 'metal', mcblock: 'metal', mctable: 'alu',
    cppoly: 'organic', cpcarbon: 'emc', cpfoil: 'metal', cpshell: 'plastic', cpntc: 'cer',
    cpgrain: 'cer', cpgb: 'cer', cpelec: 'metal', cppn: 'si',
    accan: 'alu', acsleeve: 'plastic', accore: 'cer', acfoil: 'alu', acpore: 'alu', acspine: 'alu',
    acoxide: 'cer', acpaper: 'organic', acelyte: 'organic', acseal: 'organic', aclead: 'metal',
    acvent: 'alu', acsolid: 'emc',
    indbody: 'emc', indwind: 'cu', indflux: 'si', indterm: 'sn',
    reslay: 'cer', resfilm: 'emc', restrim: 'cer', resglass: 'glass', resterm: 'sn', resback: 'sn',
    xtalbase: 'cer', xtalmount: 'cu', xtalblank: 'glass', xtalelec: 'metal', xtallid: 'metal',
    /* 2026-09-23 第二批補的高速連接器（規格書 docs/batch_0923b_spec.md W1-1，Andy 親自點名）。
       同樣是**多出來的詞**，舊的一個都沒有動。
       ⚠ 重電與石化原本也在這一批裡，Andy 當天親口否決（「這不用附上 3D 圖」），所以那兩張沒有場景。
       ⚠ 這幾支的建造函式幾乎每一塊都自己明講模組色 token，所以這裡的材質族主要是在決定
          PBR 手感（金屬度／粗糙度）與沒寫顏色那幾塊的底色，不是在決定主色。*/
    hsasic: 'si', hscage: 'metal', hstongue: 'plastic', hspin: 'organic', hsfly: 'emc', hsslot: 'plastic',
  };
  /* 角色 → 顏色 token（科技 v3 的五色系，docs/diagram_style_tech_v3.md §2；
     閱讀模式（v9，docs/diagram_refs/README.md）是同名 token 的中飽和值＋約 40% 柔光，不是灰粉彩）
       sig 訊號／網通／NVSwitch  opt 光  pwr 電力／快接頭  gpu 運算晶粒  cool CDU／manifold
       cold 冷水  hot 熱水／排熱  cu 紅銅  trace 金色走線
       air 風扇框（科技＝藍光、閱讀＝橘框）  blade 扇葉  airline 氣流環
       ind 保留給樣式系統（目前沒有零件用它） */
  const ROLE_TOKENS = { sig: '--dg-fl-sig', pwr: '--dg-fl-pwr', cool: '--dg-fl-cool', opt: '--dg-fl-opt', air: '--dg-fl-air',
    gpu: '--dg-fl-gpu', ind: '--dg-fl-ind', cold: '--dg-fl-cold', hot: '--dg-fl-hot', cu: '--dg-fl-cu', trace: '--dg-fl-trace',
    blade: '--dg-fl-blade', airline: '--dg-fl-airline' };
  // air ＝ 風扇模組（框與卡片：科技藍、閱讀橙），blade ＝ 扇葉，airline ＝ 吹出來的氣流線（CEO 2026-09-22：風扇走 role:'air'）
  /* 卡片的英文標題（v3 §4 中英雙語）。用零件身分當 key，三個場景共用一張表。*/
  const EN = {
    ag_rack: 'Rack & mechanicals', ag_backplane: 'NVLink copper backplane', ag_nvswitch: 'NVSwitch tray',
    ag_gpu: 'Compute tray · GPU module', ag_cpu: 'CPU (Grace / x86)', ag_hbm: 'HBM4 memory', ag_pcb: 'High-layer-count PCB',
    ag_ccl: 'CCL copper-clad laminate', ag_cdu: 'Liquid cold plate / CDU', ag_uqd: 'UQD couplings / manifold',
    ag_fan: 'Rear-door fan module', ag_psu: 'Power shelf PSU', ag_bbu: 'BBU battery / supercap', ag_optic: 'Optical module / CPO',
    ag_tor: 'ToR switch', ag_csp: 'Cloud / Neocloud',
    icp_sub: 'ABF substrate', icp_bga: 'BGA solder balls', icp_decap: 'Decoupling MLCCs (top)', icp_lsc: 'Land-side capacitors',
    icp_c4: 'C4 bumps', icp_interposer: 'Interposer: organic RDL (CoWoS-L)', icp_cowos_l: 'LSI silicon bridge', icp_ubump: 'Micro-bumps',
    icp_die: 'GPU die (SoIC stack)', icp_soic: 'SoIC top die', icp_hbm: 'HBM4 stack', icp_uf: 'Underfill / MUF',
    icp_stiff: 'Stiffener ring', icp_probe: 'Probe card / test socket', icp_lid: 'Heat-spreader lid + TIM',
    mlcc_body: 'Ceramic body & interleaved electrodes', mlcc_term: 'Terminations (Cu → Ni → Sn)', mlcc_pad: 'PCB pads & solder',
    /* 半導體鏈四張（2026-09-23）。key 用的是**2D 那張圖同一組 data-part**，
       所以 2D 點完一個零件再切到 3D，還是同一個零件被選著。*/
    fd_sub: 'Silicon substrate', fd_planar: 'Planar transistor (1-side gate)', fd_fin: 'FinFET (3-side gate)',
    fd_sheet: 'GAA nanosheet channels', fd_gaa: 'Gate-all-around metal (4 sides)',
    fd_wafer: '300 mm wafer & die array', fd_die: 'A single die',
    sw_chamber: 'CZ puller chamber', sw_heater: 'Graphite heater', sw_susceptor: 'Graphite susceptor (schematic)',
    sw_crucible: 'Quartz crucible', sw_melt: 'Silicon melt', sw_seed: 'Seed crystal & pull rod',
    sw_ingot: 'Single-crystal ingot (boule)', sw_saw: 'Wire-sawn wafers', sw_polish: 'Polished mirror wafer',
    hb_sub: 'Package substrate', hb_interposer: 'Interposer', hb_outbump: 'Bumps to interposer',
    hb_base: 'Base die (logic)', hb_core: 'HBM core dies (DRAM)', hb_ubump: 'Micro-bumps between dies',
    hb_tsv: 'Through-silicon vias', hb_gpu: 'Compute die (GPU / ASIC)',
    wbg_sic_drain: 'SiC drain metal (backside)', wbg_sic_sub: 'n+ SiC substrate', wbg_sic_drift: 'n- drift layer',
    wbg_sic_body: 'p-body & n+ source', wbg_sic_gox: 'Gate oxide & gate', wbg_sic_src: 'Source metal (front)',
    wbg_gan_sub: 'GaN substrate (Si / SiC)', wbg_gan_buf: 'Buffer layer (AlN / AlGaN)', wbg_gan_ch: 'GaN channel layer',
    wbg_2deg: 'Two-dimensional electron gas', wbg_gan_bar: 'AlGaN barrier', wbg_pgan: 'p-GaN gate',
    wbg_gan_elec: 'Source / gate / drain (all on top)',
    /* AI 伺服器鏈六張（2026-09-23）。key 一樣用**2D 那張圖同一組 data-part**。
       ⚠ `vc`／`heatpipe` 同時出現在液冷與氣冷兩張圖上，兩邊講的是同一個零件，所以共用一列。*/
    abf_core: 'Core layer (glass-reinforced)', abf_core_via: 'Plated through-hole in core',
    abf_film: 'ABF build-up films', abf_trace: 'Fine lines (SAP / mSAP)',
    abf_uvia: 'Laser micro-vias (tapered)', abf_stack_via: 'Stacked vias',
    abf_sr: 'Solder resist & openings', abf_bump_pad: 'Bump pads & surface finish',
    abf_bga: 'BGA solder balls', abf_die_ghost: 'Die & interposer (silhouette)',
    abf_motherboard: 'Motherboard (partial)',
    pcb_core: 'Core (copper-dielectric-copper)', pcb_pp: 'Prepreg (no copper)',
    pcb_foil: 'Copper foil (outer layers)', fiber_weave: 'Glass fibre weave',
    pcb_plane: 'Ground / power plane', pcb_trace: 'Inner-layer striplines',
    pcb_top_trace: 'Top-layer routing', pcb_mask: 'Solder mask & openings',
    pcb_enig: 'Surface finish (ENIG)', pcb_pth: 'Through-hole + stub',
    pcb_backdrill: 'Back drill', pcb_blind: 'Laser blind via', pcb_buried: 'Buried via',
    psu_shelf: 'Power shelf (N+1)', psu_unit: 'PSU enclosure', psu_board: 'PSU main board (4 stages)',
    psu_cardedge: 'Card-edge connector', psu_busbar: 'DC busbar', psu_whip: 'Power whip',
    psu_vrm: 'On-board multiphase VRM', psu_die: 'GPU / ASIC (load)',
    psu_bbu: 'BBU battery module', psu_scap: 'Supercapacitors / LIC',
    die: 'Bare die (heat source)', tim1: 'TIM1 (die to lid)', ihs: 'Integrated heat spreader',
    tim2: 'TIM2 (lid to cold plate)', cold_plate: 'Cold plate', cp_fin: 'Micro-fin channels',
    cp_port: 'Inlet (cold) / outlet (hot)', qd: 'Quick disconnects', manifold: 'Supply / return manifolds',
    cdu: 'Coolant distribution unit', phe: 'Plate heat exchanger',
    vc: 'Vapor chamber', heatpipe: 'Heat pipe',
    fan_frame: 'Fan frame', blade: 'Front rotor blades', hub: 'Hub', motor: 'Stator & rotor magnets',
    bearing: 'Bearing (shaft to hub)', counter_rot: 'Counter-rotating rear rotor',
    wire4: '4-wire connector', fan_wall: 'Fan wall (N+1)', shroud: 'Air shroud', fin: 'Heat-sink fin stack',
    sw_pcb: 'Main board (high-layer MLB)', sw_layers: 'Core / prepreg stack-up',
    sw_asic: 'Switch ASIC', sw_hs: 'ASIC heat sink', sw_vrm: 'On-board multiphase VRM',
    sw_cage: 'Front-panel optical cages', sw_mod_fiber: 'Pluggable optical module',
    sw_mod_gold: 'Gold fingers', sw_cmp_cpo: 'Co-packaged optics', sw_fly: 'Flyover cable',
    sw_cpu: 'Management CPU', sw_fan: 'System fans (rear)', sw_psu: 'PSU (rear, 1+1)',
    /* 一般電子鏈六張（2026-09-23）。key 一樣用 2D 那張圖的同一組 data-part，
       所以 2D 點完一個零件再切到 3D，還是同一個零件被選著。
       背光模組那五層在 2D 是同一個 data-part，3D 拆開之後各自有自己的 key（pn_bl_*）。*/
    pn_bl_back: 'Back plate & plastic frame', pn_bl_ref: 'Reflector film', pn_lgp: 'Light guide plate',
    pn_led: 'LED light bar (edge-lit)', pn_bl_diff: 'Lower diffuser film', pn_bl_prism: 'Prism films x2 (crossed)',
    pn_pol_lo: 'Lower polarizer', pn_glass_lo: 'TFT array glass substrate', pn_tft: 'TFT array layer',
    pn_lc: 'Liquid crystal layer', pn_cf: 'Color filter (BM + RGB)', pn_glass_up: 'Color filter glass substrate',
    pn_pol_up: 'Upper polarizer (crossed axis)', pn_driver: 'Driver IC & COF on the terminal ledge',
    mc_base: 'Extruded aluminium base', mc_enc: 'Encoder', mc_motor: 'Servo motor', mc_coupling: 'Shaft coupling',
    mc_bearing: 'Bearing housings (fixed / supported)', mc_screw: 'Ball screw shaft', mc_nut: 'Ball nut with flange',
    mc_ball: 'Steel balls (two-point contact)', mc_return: 'Ball return circuit', mc_rail: 'Linear guide rails x2',
    mc_block: 'Guide blocks x2', mc_table: 'Moving table',
    cp_ins: 'PPTC outer insulation', cp_ni: 'PPTC nickel foil electrodes', cp_poly: 'PPTC polymer matrix',
    cp_carbon: 'PPTC carbon-black chains', cp_ntc: 'NTC thermistor', cp_grain: 'MOV zinc-oxide grains',
    cp_gb: 'MOV grain boundaries', cp_movel: 'MOV electrodes', cp_pn: 'TVS p-n junction', cp_tvsel: 'TVS electrodes',
    ac_sleeve: 'Outer sleeve film', ac_can: 'Aluminium can', ac_winding: 'Wound element (4 layers)',
    ac_seal: 'Rubber seal', ac_lead: 'Lead wires x2', ac_vent: 'Pressure-relief vent (scored)',
    ac_anode: 'Anode foil', ac_pore: 'Etched tunnels', ac_core: 'Unetched foil core',
    ac_oxide: 'Anodic oxide (dielectric)', ac_paper: 'Separator paper', ac_elyte: 'Electrolyte (the real cathode)',
    ac_cathode: 'Cathode foil (current collector)', ac_solid: 'Polymer (solid) capacitor',
    ind_body: 'Molded metal-powder body', ind_wind: 'Flat-wire winding', ind_flux: 'Closed magnetic flux path',
    ind_term: 'Bottom terminations', res_substrate: 'Alumina substrate', res_bottom: 'Back-side electrode',
    res_film: 'Thick-film resistive layer', res_trim: 'Laser trim cut', res_glass: 'Glass overcoat',
    res_term3: 'Three-layer terminations', xtal_base: 'Ceramic base with cavity', xtal_mount: 'Two-point mounts',
    xtal_blank: 'AT-cut quartz blank', xtal_elec: 'Electrodes (both faces)', xtal_cavity: 'Sealed cavity',
    xtal_lid: 'Metal lid & seam weld',
    /* 2026-09-23 第二批補的高速連接器。key 一樣用 2D 那張圖的同一組 data-part。*/
    st_board: 'Board (outline & routing)', st_asic: 'ASIC / GPU (signal source)',
    cage_body: 'EMI shielding cage', gold_finger: 'Paddle card & gold fingers (differential pairs)',
    cage_pressfit: 'Press-fit pins', slot_housing: 'Receptacle housing & cantilever beams',
    twinax: 'Flyover twinax cable', optic_module: 'Pluggable optical module',
  };

  function kit(THREE, fam, ghost, css, role) {
    const cache = {}, all = [];
    /* 這顆顏色字串是從哪一個 `--dg-*` 讀來的（cssv 登記、mat 取用）。
       為什麼需要：配色切換（applyPal）以前只改飽和與混色，材質的**原色**是建場景那一刻
       從 CSS 讀進來就固定了。換模式會換掉材質 token 本身（陶瓷、鋁、鋼、錫…），
       沒有這張對照表的話，「3D 開著的時候切模式」只會套到混色、原色還是舊的。*/
    const varOf = new Map();
    const cssv = (name, dflt) => {
      let v = '';
      try { v = css ? css(name) : ''; } catch (e) { v = ''; }
      const out = v || dflt;
      if (out) varOf.set(out, name);       // 記下「這個色值來自哪一個 token」，換配色時才回得去重讀
      return out;
    };
    // 材質族的底色：依序試 token，第一個讀得到的就用
    const famSpec = FAMILY_TOKENS[fam] || FAMILY_TOKENS.metal;
    let baseHex = '', baseVar = famSpec[0][0];
    for (const n of famSpec[0]) { let v = ''; try { v = css ? css(n) : ''; } catch (e) { v = ''; } if (v) { baseHex = v; baseVar = n; varOf.set(v, n); break; } }
    if (!baseHex) { baseHex = famSpec[1]; varOf.set(baseHex, famSpec[0][0]); }
    const base = new THREE.Color(baseHex);
    // col(k) 的兩端也是 token（閱讀模式的暗端不是黑，是暖灰 —— 黏土感就從這裡來）
    const lit = new THREE.Color(cssv('--dg-lit', '#ffffff')), dim = new THREE.Color(cssv('--dg-dim', '#070b14'));
    const col = (k) => { const c = base.clone(); return k > 0 ? c.lerp(lit, k) : (k < 0 ? c.lerp(dim, -k) : c); };
    const roleHex = role && ROLE_TOKENS[role] ? cssv(ROLE_TOKENS[role], '') : '';
    function mat(k, o) {
      o = o || {};
      const key = `${k}|${o.color || ''}|${o.rough || ''}|${o.metal || ''}|${o.op || ''}|${o.led ? 1 : 0}|${o.glass ? 1 : 0}|${o.glow || 0}|${o.shell ? 1 : 0}|${o.cool ? 1 : 0}`;
      if (cache[key]) return cache[key];
      /* ★ 2026-09-22（DECISIONS #244，規格書一-3「收透明」＋ 一-4「依模組配色」）：
         `shell:true` **不再等於半透明的角色色**。
         以前外殼一律染成角色色（訊號藍／電力橘／液冷青）而且半透明，兩件事一起造成
         「整台被青藍洗掉」與「五六層半透明疊在一起」—— 根因 3 與根因 5。
         現在：外殼是**不透明**的，顏色由建造函式明講的 `--dg-m-*` 模組色決定；
         只有三種東西可以透明 —— 機櫃外殼板（glass:true）、液冷（cool:true）、示意層（ghost）。
         `role` 留著，但只用在卡片與引線的顏色（calcElColor），不再進材質。*/
      const isGlass = !!o.glass;
      const isCool = !!o.cool;
      const colorHex = o.color || null;
      /* ★ 2026-09-22：沒指定 metal／rough 的材質改吃**材質族的 PBR 預設**（FAMILY_PBR），
         不再是所有東西都 `.22 / .55`。那個 .22 是沒有環境貼圖時的補償值，
         補上 envMap 之後就該讓金屬是金屬、板材是介電質。*/
      const pbr = FAMILY_PBR[fam] || FAMILY_PBR.metal;
      const m = new THREE.MeshStandardMaterial({
        color: colorHex ? new THREE.Color(colorHex) : col(k || 0),
        roughness: o.rough != null ? o.rough : (isCool ? 0.15 : (isGlass ? 0.18 : (ghost ? 0.92 : pbr.rough))),
        metalness: o.metal != null ? o.metal : (isGlass || isCool ? 0.04 : (ghost ? 0.02 : pbr.metal)),
        transparent: !!(ghost || isGlass || isCool || o.op != null),
        opacity: isCool ? 0.62 : (isGlass ? 0.3 : (ghost ? 0.14 : (o.op != null ? o.op : 1))),
      });
      m.envMapIntensity = 1;      // 實際值由 applyPal 依 --dg-env 套（兩種模式不同）
      m.userData = { rough0: m.roughness, metal0: m.metalness };
      /* 透明件的排序（規格書一-3）：實體透明件（機櫃外殼板、液冷管線）**要** depthWrite，
         不然前後會疊成一片分不出來；只有發光點與引線才准關掉 depthWrite。*/
      if (isGlass) { m.userData.glass = true; m.depthWrite = true; }
      if (isCool) { m.userData.cool = true; m.depthWrite = true; }
      if (o.led) { m.emissive = new THREE.Color(o.color || cssv('--dg-led-c', '#86f3b4')); m.emissiveIntensity = 0.55; m.userData.led = true; }
      /* glow ＝ 流線（水路、光路、氣流、金色走線、接口燈）：科技模式微發光（--dg-flow-em × glowK），
         閱讀模式不發光只留顏色。glow 給數字就是那個倍率（走線用 .35，不然一片金光）。*/
      if (o.glow) { m.emissive = new THREE.Color(colorHex || baseHex); m.userData.glow = true; m.userData.glowK = typeof o.glow === 'number' ? o.glow : 1; }
      const cv = colorHex || '';
      if (cv && varOf.has(cv)) m.userData.dgvar = varOf.get(cv);
      /* 沒指定顏色的材質＝材質族底色的明暗變化（col(k)）。也要記下來自哪個 token 與 k，
         換模式時 applyPal 才能用**那個模式的**底色重算 —— 不然板子、玻璃這些「衍生色」會停在掛載當下的模式
         （v9 第一版就是這樣：閱讀模式的板子還是科技的深綠、玻璃還是藍的）。*/
      if (!colorHex) { m.userData.dgvar = baseVar; m.userData.dgk = k || 0; }
      cache[key] = m; all.push(m);
      return m;
    }
    // 邊線用的 LineBasicMaterial 不是從 mat() 來的，要自己登記，highlight 才吃得到它
    const reg = (m) => { all.push(m); return m; };
    /* AO 墊片的材質（每個零件工具箱一顆、共用）：MeshBasic ＋ radial sprite，顏色／不透明度由 applyPal 從 --dg-ao 重讀。
       貼圖由 mkBuilders 的 spriteTex 供應（kit 建立時還沒有 THREE 的 builders，所以用 setter 延後給）。*/
    let aoM = null;
    const ao = () => {
      if (aoM) return aoM;
      aoM = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.4, depthWrite: false, color: new THREE.Color(cssv('--dg-ao', '#000000')) });
      if (kit.spriteTex) aoM.map = kit.spriteTex();
      aoM.userData = { ao: true };
      all.push(aoM);
      return aoM;
    };
    return { mat, col, reg, css: cssv, mats: all, base: baseHex, baseVar, role: roleHex, fam, ao };
  }

  function mkBuilders(T) {
    const box = (w, h, d, m) => new T.Mesh(new T.BoxGeometry(w, h, d), m);
    const cyl = (r, h, m, seg) => new T.Mesh(new T.CylinderGeometry(r, r, h, seg || 14), m);
    const ball = (r, m) => new T.Mesh(new T.SphereGeometry(r, 12, 9), m);
    const put = (o, x, y, z) => { o.position.set(x || 0, y || 0, z || 0); return o; };
    const edge = (mesh, K, op) => {
      // 倒角過的幾何用 14° 的門檻，不然圓角上每一小段都會被畫成一條線（看起來像毛邊）
      const e = new T.EdgesGeometry(mesh.geometry, 14);
      mesh.add(new T.LineSegments(e, K.reg(new T.LineBasicMaterial({
        color: K.col(0.3), transparent: true, opacity: op == null ? 0.5 : op }))));
      return mesh;
    };

    /* ================================================================ 圓潤（DECISIONS #238）
       皮克斯樣張做不到「圓潤」是因為零件全是 BoxGeometry。這裡用 ExtrudeGeometry 的 bevel
       做倒角方塊：shape 是 (w-2r)×(h-2r) 的圓角矩形、往 z 擠 (d-2r)、兩端各倒 r ——
       加起來剛好 w×h×d，跟 BoxGeometry 可以直接對調。
       ★ 只給**大塊機構件**（機櫃柱、托盤、外殼、冷板、風扇框、上蓋）；陣列小件一律不准用
         （一顆約 300 個三角形，錫球 25 顆就 7,500）。*/
    function rshape(w, h, r) {
      const s = new T.Shape(), x = -w / 2, y = -h / 2;
      s.moveTo(x + r, y);
      s.lineTo(x + w - r, y); s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0, false);
      s.lineTo(x + w, y + h - r); s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2, false);
      s.lineTo(x + r, y + h); s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI, false);
      s.lineTo(x, y + r); s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5, false);
      return s;
    }
    function rboxGeo(w, h, d, r, hole) {
      r = Math.max(0.02, Math.min(r, w * 0.45, h * 0.45, d * 0.45));
      const s = rshape(w - 2 * r, h - 2 * r, r);
      if (hole) {                       // 風扇框：中間挖一個圓，孔的邊也一起倒角
        const p = new T.Path(); p.absarc(0, 0, hole, 0, Math.PI * 2, true); s.holes.push(p);
      }
      const g = new T.ExtrudeGeometry(s, { depth: Math.max(0.02, d - 2 * r), bevelEnabled: true,
        bevelThickness: r, bevelSize: r, bevelOffset: 0, bevelSegments: 2, steps: 1, curveSegments: 4 });
      g.center();
      return g;
    }
    const rbox = (w, h, d, r, m, hole) => new T.Mesh(rboxGeo(w, h, d, r, hole), m);

    /* ================================================================ 流線（Andy 2026-09-22 推薦一）
       粒子改用一張 radial gradient 的 sprite（一張 CanvasTexture，全場共用）：
       科技模式用加法混色＝微發光的光點；閱讀模式改普通混色＋降不透明度＝柔和半透明的點。
       沒有 canvas（極舊環境）就退回實心方點。*/
    let _spriteTex = null;
    kit.spriteTex = () => spriteTex();     // 給 kit.ao() 用（AO 墊片跟粒子共用同一張 radial 貼圖）
    function spriteTex() {
      if (_spriteTex) return _spriteTex;
      try {
        const c = document.createElement('canvas'); c.width = c.height = 64;
        const x = c.getContext('2d');
        const g = x.createRadialGradient(32, 32, 2, 32, 32, 30);
        g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.35, 'rgba(255,255,255,.85)');
        g.addColorStop(1, 'rgba(255,255,255,0)');
        x.fillStyle = g; x.fillRect(0, 0, 64, 64);
        _spriteTex = new T.CanvasTexture(c);
      } catch (e) { _spriteTex = null; }
      return _spriteTex;
    }
    /* 一條流線：管（或細線）＋ 沿著它跑的粒子。pts 是世界座標的折點，用 CatmullRom 抹順。
       回傳的 group 上掛 userData.flow（給 stepFlows 用，跟走線的電流同一套機制）。*/
    function flowPath(K, spec) {
      const g = new T.Group();
      const curve = new T.CatmullRomCurve3(spec.pts.map(a => new T.Vector3(a[0], a[1], a[2])));
      const colHex = K.css(ROLE_TOKENS[spec.kind] || '--dg-fl-sig', '#4fa3ff');
      const paths = [curve.getPoints(40)];
      if (spec.line) {
        const lg = new T.BufferGeometry().setFromPoints(paths[0]);
        const lm = K.reg(new T.LineBasicMaterial({ color: new T.Color(colHex), transparent: true, opacity: 0.75 }));
        lm.userData = { dgvar: ROLE_TOKENS[spec.kind], flowLine: true };
        g.add(new T.Line(lg, lm));
      } else {
        const tm = K.mat(0, { color: colHex, glow: true, rough: 0.35, metal: 0.05, op: 0.9 });
        g.add(new T.Mesh(new T.TubeGeometry(curve, 48, spec.r || 0.5, 7, false), tm));
      }
      const per = spec.per || 10;
      const arr = new Float32Array(per * 3);
      const geo = new T.BufferGeometry();
      geo.setAttribute('position', new T.BufferAttribute(arr, 3));
      const pm = K.reg(new T.PointsMaterial({
        size: (spec.r || 0.5) * 4.2 + (spec.line ? 2.2 : 1.2), color: new T.Color(colHex), transparent: true, opacity: 0.9,
        depthWrite: false, sizeAttenuation: true, map: spriteTex() || null }));
      pm.userData = { dgvar: ROLE_TOKENS[spec.kind], flowPts: true };
      const pt = new T.Points(geo, pm);
      /* C6：流線多三個旋鈕（幾何完全不變，只是同一條路徑上的粒子怎麼走）
           dir   -1 ＝ 逆著路徑跑（供電與訊號常常是反向的同一條路）
           bidir  秒數 ＝ 每半個週期換一次方向（交流／充放電：電流真的會反向，不是在轉圈）
           gate  [週期, 佔空比] ＝ 只有「導通」的那一段時間才跑而且看得見
                 （MOSFET 閘極關掉、PPTC 跳脫、壓敏電阻沒突波時，電流本來就是 0） */
      pt.userData.flow = { paths, per, t: 0, dir: spec.dir === -1 ? -1 : 1, speed: spec.speed || 0.25,
        bidir: spec.bidir ? (spec.bidir === true ? 2.6 : +spec.bidir) : 0,
        gate: spec.gate ? { per: spec.gate[0] || 2, duty: spec.gate[1] == null ? 0.5 : spec.gate[1] } : null, age: 0 };
      g.add(pt);
      return g;
    }

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
      const wdt = (o.wdt || Math.min(w, d) * 0.012) * 1.3;   // v3 第二輪：線寬加三成，金線才看得見
      const thk = o.thk || wdt * 0.6;
      // v3 §3：板上的走線是**金色、發光**（--dg-fl-trace；閱讀模式是不發光的淡金）
      const cu = K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.28, glow: 0.45 });
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
    function ballGrid(K, pitch, r, n, y, segs) {
      // n×n 顆球用 InstancedMesh：25 顆球一個 draw call。
      // 一顆一個 Mesh 的話，六塊板 ×25 顆就是 150 個 draw call，只為了畫錫球。
      // segs：球的細分（預設 8×6）。板上那種小到只有幾個像素的錫球給 [6,4] 就夠了 —— 三角形數差一倍。
      const m = K.mat(0.35, { metal: 0.6, rough: 0.35 });
      const im = new T.InstancedMesh(new T.SphereGeometry(r, (segs || [8, 6])[0], (segs || [8, 6])[1]), m, n * n);
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
      const m = box(p.box[0], p.box[1], p.box[2], K.mat(0, p.mat === 'glass' ? { glass: true } : null));
      if (p.ghost) edge(m, K, 0.5);
      g.add(m);
      return g;
    }

    /* 散熱上蓋：圓角的玻璃罩（拆解圖裡它是最上面那一片，做成霧面玻璃才看得到底下的晶粒），
       四隻腳踩在載板邊緣 —— 上蓋是靠腳黏在載板上的，不是浮著。*/
    function lid(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const m = rbox(w, h, d, h * 0.35, K.mat(0, { glass: true }));
      edge(m, K, 0.45); g.add(m);
      const foot = K.mat(-0.1, { metal: 0.5, rough: 0.4 });
      const at = [];
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) => at.push([sx * (w / 2 - 2), -h * 0.5 - h * 0.6, sz * (d / 2 - 2)]));
      g.add(instOf(new T.BoxGeometry(4, h * 1.2, 4), foot, at));
      return g;
    }

    /* 機櫃（Andy 2026-09-22 推薦一：「機櫃的外框與不重要的金屬板改成半透明或霧面玻璃材質，
       讓內部托盤看得到」）：四根圓角立柱 ＋ 兩片側板 ＋ 一片後板全部是玻璃，
       外框線留著（玻璃太透的時候還看得出機櫃的輪廓）。U 位安裝孔改成柱子上的一排小凹點。*/
    function rack(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      /* v9：玻璃框要有**厚度與邊緣高光**（參考圖）。外框線改成玻璃邊光 token（科技淡藍、閱讀白），
         立柱加粗到 3、側板 0.9 厚、上下各一片玻璃橫樑 —— 有厚度的東西邊緣才有高光可言。*/
      const gm = new T.BoxGeometry(w, h, d);
      const edgeM = K.reg(new T.LineBasicMaterial({ color: new T.Color(K.css('--dg-glass-edge', '#9FE0FF')), transparent: true, opacity: 0.55 }));
      edgeM.userData = { dgvar: '--dg-glass-edge', edge: true };
      g.add(new T.LineSegments(new T.EdgesGeometry(gm), edgeM));
      gm.dispose();
      /* ★ 2026-09-22（規格書一-3「收透明」＋一-4「機架是銀灰霧面金屬」）：
         以前**整座機櫃連立柱帶橫樑都是玻璃**，所以「機架與機構件」這一類
         在圖上根本沒有自己的顏色，而且是五六層半透明的第一層。
         現在：**立柱與上下橫樑是實體銀灰金屬**（19 吋機櫃的柱子本來就是鈑金），
         只有「要看見內部」的側板與後板留半透明玻璃，而且更透（--dg-shell-a .28）、更薄。*/
      const steel = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.85, rough: 0.35 });
      const glass = K.mat(0, { glass: true });
      [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) =>
        g.add(put(rbox(3, h, 3, 1, steel), sx * (w / 2 - 1.5), 0, sz * (d / 2 - 1.5))));
      // 上下橫樑：圓角金屬板，機櫃看起來是一個有厚度的框，不是四根線
      g.add(put(rbox(w, 2.2, d, 0.6, steel), 0, h / 2 - 1.1, 0));
      g.add(put(rbox(w, 2.2, d, 0.6, steel), 0, -h / 2 + 1.1, 0));
      // 側板與後板：霧面玻璃（前面留空，托盤才抽得出來）；0.6 厚 —— 它是「看得進去的殼」不是結構件
      [-1, 1].forEach(sx => g.add(put(box(0.6, h * 0.94, d * 0.88, glass), sx * (w / 2 - 0.3), 0, 0)));
      g.add(put(box(w * 0.88, h * 0.94, 0.6, glass), 0, 0, -(d / 2 - 0.3)));
      // 機櫃前柱上的 U 位安裝孔：一眼看得出是 19 吋機櫃而不是一個箱子
      const holeM = K.mat(-0.5, { rough: 0.8, metal: 0.1 });
      const holes = [];
      for (let i = -6; i <= 6; i += 2) [-1, 1].forEach(sx => holes.push([sx * (w / 2 - 1.5), i * (h / 16), d / 2 - 1.5 + 1.4]));
      g.add(instOf(new T.BoxGeometry(0.5, 0.9, 0.5), holeM, holes));
      return g;
    }

    /* 托盤底下的淡陰影（AO，參考圖「托盤底下有淡陰影」）：一片 radial sprite 的軟橢圓貼在零件底面下方，
       顏色與不透明度走 --dg-ao／--dg-ao-a（科技深、閱讀淡）。一片 2 個三角形、1 個 draw call；
       只給大塊托盤類（板子、托盤、PSU、交換器、電池），不給陣列小件。*/
    function aoPad(K, w, d, y) {
      const m = K.ao();
      const mesh = new T.Mesh(new T.PlaneGeometry(1, 1), m);
      mesh.rotation.x = -Math.PI / 2;
      mesh.scale.set(w * 1.12, d * 1.12, 1);
      mesh.position.y = y;
      mesh.renderOrder = -1;
      return mesh;
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

    // 托盤／NVSwitch：有厚度的圓角底板（有角色就是那個角色的半透明色）＋ 中間一顆晶片 ＋ 散熱鰭片 ＋ 底下 AO
    function tray(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      // 托盤是鈑金件：銀灰金屬實體（規格書一-4）。以前是角色色半透明，整排托盤被染成同一個藍
      g.add(rbox(w, h * 0.7, d, h * 0.25, K.mat(-0.18, { metal: 0.8, rough: 0.4 })));
      g.add(aoPad(K, w, d, -h * 0.35 - 0.9));
      // 托盤中央那顆是交換／控制晶片：石墨灰模封（不是跟鈑金同色的一塊凸起）
      g.add(put(box(w * 0.26, h * 0.7, d * 0.4, K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), metal: 0.18, rough: 0.6 })), 0, h * 0.5, 0));
      const fin = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.7, rough: 0.42 });
      const at = [];
      for (let i = -5; i <= 5; i++) at.push([i * w * 0.028, h * 0.8, 0]);
      g.add(instOf(new T.BoxGeometry(w * 0.012, h * 1.1, d * 0.38), fin, at));
      return g;
    }

    /* GPU 模組：載板 ＋ 中介層 ＋ CoWoS 晶粒（紫，v3）＋ 兩側各 3 顆 HBM 堆疊（每顆 4 層、層縫看得見）＋ 銅質冷板壓在晶粒上
       ★ v3 §3-04：「處理器上蓋 CoWoS／SoIC 晶粒（紫）＋ HBM4 多層堆疊 6～8 顆（層與層有細縫）」；
         「銅質水冷頭壓在晶片上」（§3-09）。6 顆 × 4 層 ＝ 24 塊併成一個 mesh，一個 draw call。*/
    function gpu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      // 運算模組的載板：深藍（規格書一-4「晶片本體（GPU／ASIC／CPU）深藍」）——
      // 這是整台機櫃認得出「哪幾層在算」的那個顏色，不能跟陶瓷米白混在一起
      g.add(put(box(w, h * 0.3, d, K.mat(0, { color: K.css('--dg-m-die', '#1E2E52'), metal: 0.35, rough: 0.45 })), 0, -h * 0.35, 0));
      g.add(put(box(w * 0.8, h * 0.18, d * 0.8, K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), metal: 0.3, rough: 0.5 })), 0, -h * 0.11, 0));
      /* ★ 規格書一-6「發光克制」：CoWoS 晶粒與 HBM 以前掛 emissive 0.55／0.18，
         那是「整片 emissive」—— 一顆矽晶粒本來就不發光，發光的是指示燈與資料流。
         現在改成**矽的材質**（深藍、金屬度 .35），立體感交給 envMap 與陰影去做。*/
      g.add(put(box(w * 0.4, h * 0.3, d * 0.5, K.mat(0, { color: K.css('--dg-si', '#33488a'), metal: 0.35, rough: 0.35 })), 0, h * 0.14, 0));
      // 銅質冷板：壓在晶粒上的一小片紅銅，金屬度拉高才有高光
      g.add(put(box(w * 0.46, h * 0.16, d * 0.56, K.mat(0, { color: K.css('--dg-m-cu', '#D6A886'), metal: 0.9, rough: 0.22 })), 0, h * 0.37, 0));
      // HBM 堆疊：兩側各 3 顆、每顆 4 層 DRAM（層縫＝每層之間留 0.2h 的空隙）
      const hb = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.5, metal: 0.2 });
      const layers = [], lay = h * 0.36 / 4;
      [-1, 1].forEach(s => { for (let i = -1; i <= 1; i++) for (let L = 0; L < 4; L++) {
        layers.push([w * 0.11, lay * 0.72, d * 0.2, s * w * 0.3, h * 0.0 + L * lay + lay * 0.36, i * d * 0.24]);
      } });
      g.add(mboxes(layers, hb));
      return g;
    }

    // 一般晶片：載板 ＋ 金屬上蓋 ＋ 四周被動元件
    function chip(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      // 載板深藍（運算）、上蓋是銀灰散熱蓋（規格書一-4 的「晶片散熱蓋／鰭片」比機架亮一階）
      g.add(put(box(w, h * 0.35, d, K.mat(0, { color: K.css('--dg-m-die', '#1E2E52'), metal: 0.35, rough: 0.45 })), 0, -h * 0.32, 0));
      g.add(put(box(w * 0.66, h * 0.5, d * 0.66, K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.7, rough: 0.4 })), 0, h * 0.15, 0));
      const pas = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.62, metal: 0.12 });
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
      g.add(aoPad(K, w, d, -h / 2 - 1.2));        // v9：板子底下的淡陰影
      /* ★ 2026-09-22 減面：三顆 IC、三條插槽、六顆電容以前是 12 個獨立 Mesh（六塊板 ＝ 72 個 draw call）。
         形狀沒變、位置沒變，只是同材質的併成一個、同形狀的收成 InstancedMesh。*/
      // 板上的 IC 封裝是黑色模封（石墨灰），不是跟板子同色的凸塊 —— 規格書一-4 的「晶片本體」那一列
      const ic = K.mat(0.15, { rough: 0.5, metal: 0.18, color: K.css('--dg-m-graphite', '#3A3F47') });
      g.add(mboxes([[-0.3, -0.2], [0.18, 0.24], [0.34, -0.3]].map(([fx, fz]) =>
        [w * 0.1, h * 1.5, d * 0.14, fx * w, h, fz * d]), ic));
      const slot = K.mat(0.3, { metal: 0.4, rough: 0.45 });
      g.add(mboxes([-1, 0, 1].map(i => [w * 0.34, h * 1.2, d * 0.045, -w * 0.06, h * 0.9, i * d * 0.17]), slot));
      const cap = K.mat(-0.05, { rough: 0.6 });
      const capAt = [];
      for (let i = 0; i < 6; i++) capAt.push([(-0.42 + i * 0.05) * w, h * 1.4, d * 0.4]);
      g.add(instOf(new T.CylinderGeometry(Math.min(w, d) * 0.014, Math.min(w, d) * 0.014, h * 2.2, 6), cap, capAt));
      // 圖九 2-1：板面的蛇行等長差動對。訊號方向＝由 GPU（板中）往背板（-x）
      const tl = traceLayer(K, w, d, h * 0.55, { pairs: 4, cycles: 5, dir: -1 });
      g.add(tl.group); g.userData.flows = tl.flows;
      // 焊墊：每顆 IC 底下一整片（表面處理鍍金）
      g.add(padField(K, w * 0.22, d * 0.3, h * 0.52, 5, 4));
      // v3 §3-04：板上的 BGA 錫球陣列（instanced 低細分球）—— 一組 3×3 放在第三顆 IC 旁邊
      //（六塊板共用同一份幾何；4×4 的 8×6 球一塊板就 1,500 個三角形，六塊板會把場景推破 40,000 的上限）
      g.add(put(ballGrid(K, w * 0.02, w * 0.007, 3, 0, [6, 3]), w * 0.06, h * 0.56, -d * 0.3));
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

    /* CCL／多層板剖面（v3 §3-08）：「50 層以上的層疊剖面（金／銅／綠交疊），層間有微小導通孔」。
       畫 12 對「銅箔＋介電」交疊（示意，不是真的 50 層 —— 太薄畫不出來），兩個 InstancedMesh；
       再補一排鍍通孔（pthRow）與表面幾條髮絲走線。*/
    function laminate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const n = 12, pit = h / n;
      const cu = K.mat(0, { color: K.css('--dg-fl-cu', '#E8A97E'), metal: 0.72, rough: 0.3 });
      const die = K.mat(-0.3, { rough: 0.85, metal: 0.05 });
      const cuAt = [], dieAt = [];
      for (let i = 0; i < n; i++) {
        const y = -h / 2 + pit * (i + 0.5);
        cuAt.push([0, y + pit * 0.25, 0]); dieAt.push([0, y - pit * 0.2, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w, pit * 0.28, d), cu, cuAt));
      g.add(instOf(new T.BoxGeometry(w * 0.995, pit * 0.6, d * 0.995), die, dieAt));
      g.add(pthRow(K, w, h, d, 12, -d * 0.3));
      g.add(pthRow(K, w, h, d, 9, d * 0.28));
      // 表面髮絲走線（金色、微發光）
      const tl = traceLayer(K, w * 0.9, d * 0.9, h * 0.52, { pairs: 3, cycles: 5, wdt: Math.min(w, d) * 0.006, dir: -1 });
      g.add(tl.group); g.userData.flows = tl.flows;
      return g;
    }

    /* CDU 立柱：圓角機箱（液冷角色＝青綠半透明）＋ 幫浦 ＋ 上下進出水管。
       ★ 進水冷（--dg-cold）、出水熱（--dg-hot）是語意色，任何模式都不准蓋；
         兩根管子掛 glow —— 科技模式微發光，閱讀模式只留顏色。*/
    function cdu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      /* 液冷是規格書一-3 准許透明的三種之一：青綠半透明、粗糙度低、**有厚度**
         （外殼半透明 ＋ 內層較飽和的水體，轉過去看得出「裡面有水」而不是一片色紙）。*/
      g.add(rbox(w, h, d, w * 0.22, K.mat(0, { color: K.css('--dg-m-cool', '#2FB8A6'), cool: true })));
      g.add(put(rbox(w * 0.62, h * 0.94, d * 0.62, w * 0.14,
        K.mat(0, { color: K.css('--dg-fl-cold', '#2FD9C4'), op: 0.78, rough: 0.2, metal: 0.05 })), 0, 0, 0));
      const pump = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.7, rough: 0.4 });
      [-0.3, 0.1].forEach(fy => g.add(put(cyl(w * 0.42, h * 0.1, pump), 0, fy * h, 0)));
      // v3：冷水管螢光藍、熱水管發光紅（3D 自己的 token，閱讀模式是粉彩版，不發光）
      const cold = K.mat(0, { color: K.css('--dg-fl-cold', '#58C4FF'), glow: true, metal: 0.2, rough: 0.4 });
      const hot = K.mat(0, { color: K.css('--dg-fl-hot', '#FF4D5E'), glow: true, metal: 0.2, rough: 0.4 });
      [[0.42, 1, cold], [-0.42, -1, hot]].forEach(([fy, sx, m]) => {
        const t = put(cyl(w * 0.22, d * 2.4, m, 10), sx * w * 0.2, fy * h, -d * 1.0);
        t.rotation.x = Math.PI / 2; g.add(t);
      });
      g.add(put(box(w * 0.5, h * 0.03, d * 0.5, K.mat(0, { led: true })), 0, h * 0.46, d * 0.52));
      return g;
    }

    // UQD 快接頭：本體 ＋ 鎖環 ＋ 軟管
    function uqd(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      /* 快接頭（UQD）是**銅合金**件（規格書一-4 的「銅件／接頭／快接頭」），
         不是銀灰鈑金 —— 圖上看得出它跟機櫃柱子不是同一種東西，才對得上不同的供應商。*/
      const cuM = K.mat(0, { color: K.css('--dg-m-cu', '#C98A5E'), metal: 0.9, rough: 0.3 });
      const body = put(cyl(w * 0.46, h * 1.15, cuM), 0, 0, 0);
      body.rotation.z = Math.PI / 2; g.add(body);
      const ring = put(cyl(w * 0.55, h * 0.3, K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.85, rough: 0.25 })), w * 0.3, 0, 0);
      ring.rotation.z = Math.PI / 2; g.add(ring);
      // 軟管是橡膠：深灰、完全不金屬（跟銅接頭的對比就是「金屬 vs 非金屬」）
      const hose = put(cyl(w * 0.24, d * 2.2, K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.85, metal: 0.05 })), -w * 0.9, 0, 0);
      hose.rotation.z = Math.PI / 2; g.add(hose);
      return g;
    }

    /* 風扇：Andy 點名的例子 ——「風扇有扇片」。
       外框 ＋ 輪轂 ＋ 七片有角度的扇片，扇片掛在自己的 Group 上，setAnim(true) 時整組轉。*/
    function fan(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2, open = r * 1.64;
      // 風扇外框：藍灰、不透明（規格書一-4）。以前是角色色半透明 —— 扇葉看起來像浮在空中
      const fm = K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), metal: 0.5, rough: 0.5 });
      // 外框：一塊圓角方框、中間挖一個圓（ExtrudeGeometry 的 hole）—— 這才是風扇框的樣子
      g.add(rbox(w, h, d, Math.min(w, h) * 0.08, fm, open / 2));
      const rotor = new T.Group();
      const hub = cyl(r * 0.26, d * 0.8, K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.7, rough: 0.4 }));
      hub.rotation.x = Math.PI / 2; rotor.add(hub);
      /* ★ 規格書一-4：扇葉是**實體**深灰藍，不准只剩透明輪廓、也不准發霓虹光。
         「電競 RGB」是 Andy 點名要拿掉的那一件事；風扇之所以看得出是風扇，
         靠的是七片有攻角的實心葉片與輪轂，不是藍光。*/
      const bm = K.mat(0, { color: K.css('--dg-m-blade', '#2E3A45'), rough: 0.6, metal: 0.2 });
      for (let i = 0; i < 7; i++) {
        const b = box(r * 0.62, r * 0.36, d * 0.16, bm);
        b.position.set(Math.cos(i * Math.PI * 2 / 7) * r * 0.48, Math.sin(i * Math.PI * 2 / 7) * r * 0.48, 0);
        b.rotation.z = i * Math.PI * 2 / 7 + Math.PI / 2;
        b.rotation.y = 0.42;                      // 扇片的攻角：平的看起來像葉輪玩具
        rotor.add(b);
      }
      rotor.userData.spin = { axis: 'z', speed: 2.4 };
      g.add(rotor);
      /* v3 §3-11：向外旋轉出淡藍白的氣流波紋 —— 兩圈越往外越大、越淡的環（一個 InstancedMesh）。
         波紋本身是靜的（氣流的「動」由場景層級的 airflow 粒子負責，靜止模式一起停）。*/
      const airM = K.mat(0, { color: K.css('--dg-fl-airline', '#BFE9FF'), glow: 0.35, rough: 0.6, metal: 0, op: 0.3 });
      // 減面：波紋是淡到幾乎看不見的細環，截面 5×20 換成 4×12（一個風扇省 288 個三角形）
      g.add(instOf(new T.TorusGeometry(r * 0.7, r * 0.03, 4, 12), airM,
        [[0, 0, d * 0.9, 0, 0, 0, 1, 1, 1], [0, 0, d * 1.7, 0, 0, 0, 1.25, 1.25, 1]]));
      return g;
    }

    // PSU：機殼 ＋ 進氣孔陣列 ＋ 把手 ＋ 電源指示燈
    function psu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      // 電源櫃：暖橘實體（規格書一-4 的「電源／BBU 暖橘」）——「暖三成」的主要來源就是這幾台
      g.add(rbox(w, h, d, h * 0.18, K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), metal: 0.4, rough: 0.5 })));
      g.add(aoPad(K, w, d, -h / 2 - 0.8));
      const hole = K.mat(-0.6, { rough: 0.9, metal: 0.05 });
      // ★ 2026-09-22：18 個進氣孔收成一個 InstancedMesh（圓柱預設立著，要放倒才是面對前面板的孔）
      const holes = [];
      for (let i = -4; i <= 4; i++) for (let j = -1; j <= 1; j += 2) {
        holes.push([i * w * 0.08, j * h * 0.22, d / 2, Math.PI / 2, 0, 0]);
      }
      // 減面：孔是「管」，兩端的圓盤看不到 → openEnded（18 個孔省 144 個三角形 × 3 台）
      g.add(instOf(new T.CylinderGeometry(w * 0.02, w * 0.02, d * 0.06, 6, 1, true), hole, holes));
      g.add(put(box(w * 0.26, h * 0.16, d * 0.05, K.mat(0.3, { metal: 0.5 })), -w * 0.3, 0, d / 2 + d * 0.02));
      g.add(put(box(w * 0.05, h * 0.16, d * 0.03, K.mat(0, { led: true })), w * 0.38, 0, d / 2 + d * 0.02));
      /* 圖九 2-1：PSU 後端的**直流匯流排端子**。這是電源件最好認的特徵 ——
         一整片厚銅排加上鎖螺絲的孔，跟訊號端子完全不是同一個量級。*/
      const busM = K.mat(0.5, { color: K.css('--dg-cu', '#b0743a'), metal: 0.8, rough: 0.3 });
      const scr = [];
      [-1, 1].forEach(sy => {
        g.add(put(box(w * 0.3, h * 0.13, d * 0.05, busM), sy * w * 0.22, sy * h * 0.22, -d / 2 - d * 0.02));
        for (let i = -1; i <= 1; i++) scr.push([sy * w * 0.22 + i * w * 0.09, sy * h * 0.22, -d / 2 - d * 0.03, Math.PI / 2, 0, 0]);
      });
      g.add(instOf(new T.CylinderGeometry(w * 0.012, w * 0.012, d * 0.07, 6, 1, true), K.mat(-0.5, { rough: 0.85, metal: 0.1 }), scr));
      return g;
    }

    /* BBU 電池：Andy 點名的例子 ——「電池有電壓感」。
       外殼做成**托盤**不是密閉箱子 —— 密閉的話電芯全被蓋住，做得再細也看不到。
       托盤 ＋ 一排圓柱電芯 ＋ 正負端子（銅色／深色）＋ 剩餘電量燈條（會呼吸）。*/
    function battery(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      // BBU 跟 PSU 同一類（電源）：暖橘托盤 ＋ 石墨灰電芯
      const shell = K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), rough: 0.5, metal: 0.4 });
      g.add(put(rbox(w, h * 0.2, d, h * 0.08, shell), 0, -h * 0.4, 0));                       // 底盤（圓角托盤）
      g.add(aoPad(K, w, d, -h * 0.5 - 0.8));
      [-1, 1].forEach(s => g.add(put(box(w * 0.04, h * 0.62, d, shell), s * (w / 2 - w * 0.02), -h * 0.06, 0)));
      [-1, 1].forEach(s => g.add(put(box(w, h * 0.62, d * 0.03, shell), 0, -h * 0.06, s * (d / 2 - d * 0.015))));
      const cellM = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), metal: 0.45, rough: 0.42 });
      const cells3 = [];
      for (let i = -2; i <= 3; i++) for (let j = -1; j <= 1; j += 2) {
        cells3.push([(i - 0.5) * w * 0.15, h * 0.06, j * d * 0.24]);
      }
      g.add(instOf(new T.CylinderGeometry(w * 0.055, w * 0.055, h * 0.8, 10), cellM, cells3));
      // 端子：一正一負，正極用銅色、負極壓深，遠看就知道哪邊是哪邊
      g.add(put(box(w * 0.1, h * 0.5, d * 0.1, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.75, rough: 0.3 })), w * 0.4, h * 0.5, -d * 0.32));
      g.add(put(box(w * 0.1, h * 0.5, d * 0.1, K.mat(0, { color: K.css('--dg-el', '#4e5866'), metal: 0.55, rough: 0.5 })), w * 0.4, h * 0.5, d * 0.32));
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
      g.add(box(w, h, d * 0.86, K.mat(0.05, { metal: 0.82, rough: 0.34 })));
      const port = K.mat(-0.55, { rough: 0.9, metal: 0.05 });
      [-1, 1].forEach(s => g.add(put(box(w * 0.3, h * 0.45, d * 0.1, port), s * w * 0.22, 0, d * 0.44)));
      g.add(put(box(w * 0.7, h * 0.16, d * 0.2, K.mat(0.35, { metal: 0.3, rough: 0.55 })), 0, -h * 0.5, d * 0.52));
      // 圖九 2-1：可插拔光模組後端的金手指 —— 成排、鍍金、前緣倒角
      g.add(fingers(K, w * 0.86, h * 0.1, d * 0.12, 7, -h * 0.28, -d * 0.44));
      g.add(put(box(w * 0.18, h * 0.12, d * 0.03, K.mat(0, { led: true })), 0, h * 0.4, d * 0.45));
      return g;
    }

    // 交換器：機殼 ＋ 前面板整排埠 ＋ 埠燈
    /* 交換器（v3 §3-15）：前面板**兩排**微光接口（上排 800G／CPO 光纖接口＝松石綠微光、下排 RJ45／訊號＝藍微光），
       全部 instanced；再接出三條細彩色線纜到外面（光路青、訊號藍）。*/
    function switchBox(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(rbox(w, h, d, h * 0.2, K.mat(-0.12, { metal: 0.82, rough: 0.38 })));
      g.add(aoPad(K, w, d, -h / 2 - 1.0));
      const port = K.mat(-0.55, { rough: 0.9, metal: 0.05 });
      const optHex = K.css('--dg-fl-opt', '#22E5C8'), sigHex = K.css('--dg-fl-sig', '#58C4FF');
      const ledO = K.mat(0, { color: optHex, glow: 1.1, rough: 0.5, metal: 0.1 });
      const ledS = K.mat(0, { color: sigHex, glow: 0.9, rough: 0.5, metal: 0.1 });
      const ports = [], lo = [], ls = [];
      for (let i = -8; i <= 7; i++) {
        const x = (i + 0.5) * w * 0.055;
        ports.push([x, h * 0.18, d / 2]); ports.push([x, -h * 0.2, d / 2]);
        lo.push([x, h * 0.18, d / 2 + 0.03]); ls.push([x, -h * 0.2, d / 2 + 0.03]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.04, h * 0.26, d * 0.04), port, ports));
      // 發光面要夠大（接口面的一大半），不然在 1440 只剩幾個像素、看不出是亮的
      g.add(instOf(new T.BoxGeometry(w * 0.034, h * 0.2, d * 0.02), ledO, lo));
      g.add(instOf(new T.BoxGeometry(w * 0.034, h * 0.2, d * 0.02), ledS, ls));
      // 三條細線纜：從前面板接口垂下去、往外拉（青＝光纖、藍＝銅纜）
      [[-0.3, optHex], [0.05, optHex], [0.32, sigHex]].forEach(([fx, hex]) => {
        const curve = new T.CatmullRomCurve3([
          new T.Vector3(fx * w, h * 0.18, d / 2 + 0.2), new T.Vector3(fx * w + w * 0.04, -h * 0.4, d / 2 + 2.5),
          new T.Vector3(fx * w + w * 0.1, -h * 1.6, d / 2 + 5), new T.Vector3(fx * w + w * 0.14, -h * 3.4, d / 2 + 6)]);
        g.add(new T.Mesh(new T.TubeGeometry(curve, 12, h * 0.05, 5, false),
          K.mat(0, { color: hex, glow: 0.3, rough: 0.6, metal: 0.05 })));
      });
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
      /* ★ 2026-09-22（規格書一-1）：以前這裡把 metalness 壓在 0.45 以下，註解自己寫了原因 ——
         「這個場景只有方向光、沒有環境貼圖，金屬度拉高就變成一塊黑」。
         那是**症狀的補償**不是修正。環境貼圖補上之後上限解除：
         Cu／Ni／Sn 三層現在是真的鍍層，轉一圈看得出三種不同的金屬光澤。*/
      // B5／B6：Cu／Ni／Sn 三層也改讀 --dg-*，跟 2D 的端子剖面是同一組顏色
      const L3 = [[0, 0.62, K.mat(0, { color: K.css('--dg-m-cu', '#C98A5E'), metal: 0.9, rough: 0.3 })],
        [0.62, 0.85, K.mat(0, { color: K.css('--dg-ni', '#a9b1b9'), metal: 0.82, rough: 0.26 })],
        [0.85, 1, K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.6, rough: 0.2 })]];
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
      g.add(box(w, h, d, K.mat(0, { rough: 0.55, metal: 0.05, color: K.css('--dg-m-pcb', '#0E3B32') })));
      /* 焊墊是**朝上的大平面**：metalness 拉到 .9 的話它整片鏡射上方那片大柔光板，
         銅色被沖成白色（2026-09-22 截圖實測）。壓到 .72／rough .45 —— 還是金屬，
         但看得出是銅。焊錫維持高反射（錫本來就亮）。*/
      const cu = K.mat(0, { color: K.css('--dg-m-cu', '#C98A5E'), metal: 0.72, rough: 0.45 });
      const sn = K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.6, rough: 0.28 });
      /* ★ 2026-09-22：兩塊銅墊併成一個 mesh、兩個焊錫圓角收成一個 InstancedMesh ——
         省下的 2 個 draw call是給模型底下那片接觸陰影用的（#238「柔和環境陰影」），
         MLCC 場景的棘輪（93）才守得住。畫出來的東西一個像素都沒變。*/
      g.add(mboxes([[w * 0.3, h * 0.6, d * 0.55, -w * 0.3, h * 0.7, 0], [w * 0.3, h * 0.6, d * 0.55, w * 0.3, h * 0.7, 0]], cu));
      // 焊錫圓角：壓扁的球，看得出是「爬上端子側面」的那一圈，不是一顆大球
      const r = w * 0.018;
      g.add(instOf(new T.SphereGeometry(r, 12, 9), sn,
        [[-w * 0.375, h * 0.98, 0, 0, 0, 0, 1.6, 1.8, 9], [w * 0.375, h * 0.98, 0, 0, 0, 0, 1.6, 1.8, 9]]));
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
      const au = K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.28 });
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
      /* ★ 2026-09-22 減面（DECISIONS #244）：孔壁與孔本身都是**管**，兩端的圓盤蓋
         不是被板子夾住就是被對方擋住，一個像素都看不到 —— openEnded 砍掉它們。
         細分同時從 8／6 降到 6／5：一個孔從 48 個三角形變成 22 個，
         一塊主機板 14 個孔省 364、六塊板省 2,184，剛好是「加陰影」要的預算。*/
      g.add(instOf(new T.CylinderGeometry(r * 2.1, r * 2.1, h * 1.02, 6, 1, true), cu, at));  // 鍍銅孔壁
      g.add(instOf(new T.CylinderGeometry(r, r, h * 1.06, 5, 1, true), vd, at));              // 孔本身（暗）
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
      g.add(instOf(new T.CylinderGeometry(r, r, t * 2.2, 6, 1, true), hl,
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
      g.add(instOf(new T.CylinderGeometry(r, r, t * 1.08, 6, 1, true),
        K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 }), holes));
      [-1, 1].forEach(s => g.add(put(box(w * 0.05, h * 0.34, t * 1.6, st2), s * w * 0.45, 0, t * 0.6)));  // 把手
      return g;
    }

    /* ================================================================ 半導體鏈的零件字彙（2026-09-23）
       Andy 2026-09-23：「確保這邊都有 3D 圖」。晶圓代工／矽晶圓／HBM／第三代半導體
       四張原本都是 `scene: null`，各自的規格書 §0 寫的理由是「剖面／平面就講得完」。
       這一批推翻的不是那個理由，是它漏掉的那一半 —— 四件**只有立體才成立**的事：
         · 電晶體的成敗是「閘極包得到幾個面」，那本來就是三維的事，一個切面只看得到其中一面
         · 長晶爐確實是旋轉對稱體，但**切開**之後「坩堝裡有液面、晶碇正從液面往上長」要立體才看得懂
         · TSV 是一根貫穿的柱子，切掉一角轉過去，才看得到它真的穿過每一層而不是畫在表面
         · SiC 是垂直元件、GaN 是橫向元件 —— 兩顆並排轉一圈，電極在哪一面是一眼的事
       所以四張走的都是**切開／並排**的立體，不是把 2D 拉厚。
       共同規矩：顏色一律走 FAMILY_TOKENS 與 `--dg-*`（不寫死色值）、陣列類一律 InstancedMesh、
       不加任何自體發光（Andy：「不是電競 RGB」）。*/

    /* 切開的殼（爐體、坩堝）要看得到內壁，但 mat() 的快取 key 不含 side，
       直接改會把共用同一組參數的別人也一起變成雙面。所以複製一顆、登記進 K.mats ——
       登記過 highlight()（點零件時的淡出）與 applyPal()（換模式重讀顏色）才吃得到它。*/
    function twoSided(K, m) {
      const c = m.clone();
      c.side = T.DoubleSide;
      c.userData = Object.assign({}, m.userData || {});
      K.reg(c);
      return c;
    }
    /* 切掉「x > 0 且 z > 0」那一角之後剩下的兩塊（給 mboxes 用，一層＝一次 draw call）。
       切法跟 MLCC 那張的 lslab 完全一致 —— 同一個專案裡「剖面」只能有一種切法，
       不然使用者在兩張圖之間要重新學一次「哪一面是切面」。*/
    function cutSlab(w, h, d, y) {
      return [[w, h, d / 2, 0, y || 0, -d / 4], [w / 2, h, d / 2, -w / 4, y || 0, d / 4]];
    }
    /* 剖面上的切面要比外表面暗一階，不然「被切開的面」跟「原本就有的面」長得一模一樣。
       兩片薄板貼在 x = 0 與 z = 0 的切口上，一次 draw call。*/
    function cutFace(K, w, h, d, y, k) {
      const t = Math.max(0.03, Math.min(w, d) * 0.006);
      return mboxes([[t, h * 0.98, d / 2, t / 2, y || 0, d / 4], [w / 2, h * 0.98, t, -w / 4, y || 0, t / 2]],
        K.mat((k == null ? 0 : k) - 0.3, { rough: 0.72, metal: 0.08 }));
    }
    /* 半剖（把 z > 0 整個切掉）。給「一整疊薄層」用的切法。
       為什麼不跟 HBM 用同一種切角：切角在**厚**的東西上很好讀（看得到裡面的柱子），
       在一疊**薄**片上只會變成一疊 L 形的板子 —— 那不是剖面，那是缺了一角的板子。
       半剖留下一個乾淨的 z = 0 剖面，內部構造（n⁺ 源極區、接觸窗）一律做到這個面上才看得到。*/
    function halfSlab(w, h, d, y) { return [[w, h, d / 2, 0, y || 0, -d / 4]]; }
    function halfFace(K, w, h, d, y, k) {
      const t = Math.max(0.03, Math.min(w, d) * 0.006);
      return mboxes([[w * 0.995, h * 0.98, t, 0, y || 0, t / 2]],
        K.mat((k == null ? 0 : k) - 0.3, { rough: 0.72, metal: 0.08 }));
    }

    /* ---------------------------------------------------------------- 晶圓代工：三種電晶體
       三顆的畫法刻意完全一致（同一塊基板、同一個通道方向、同一種金色面標），
       因為這三格的意義就在「可以互相比較」—— 用不同畫法讀者就無法比較。
       通道一律沿 x 走（源極在 −x、汲極在 +x），閘極一律橫跨 z 方向，
       金色薄片 ＝「閘極管得到的那一面」，數金片就是數 1／3／4。*/
    const FET_LG = 0.22;        // 閘極長度佔零件寬的比例（三顆共用，才比得出來）

    function fetFaces(K, list) {
      // 金色面標：閘極管得到的面。用 instOf 收成一次 draw call
      const au = K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.26 });
      const g = new T.Group();
      list.forEach(([geo, at]) => g.add(instOf(geo, au, at)));
      return g;
    }

    /* 平面電晶體：閘極只從正上方蓋下來，管得到的只有**上面這一面**。*/
    function fetPlanar(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const si = K.mat(-0.32, { rough: 0.46 });
      const ch = K.mat(0.44, { rough: 0.34 });
      const ox = K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.4, metal: 0.04 });
      const mt = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.85, rough: 0.32 });
      const sp = K.mat(0, { color: K.css('--dg-abf', '#c3b9a4'), rough: 0.7, metal: 0.05 });
      const sd = K.mat(0.16, { rough: 0.5 });
      g.add(put(box(w, h * 0.52, d, si), 0, -h * 0.24, 0));                                   // 基板
      g.add(put(box(w * 0.54, h * 0.07, d * 0.62, ch), 0, h * 0.06, 0));                      // 通道：表面下一條水平薄層
      g.add(put(box(w * FET_LG, h * 0.05, d * 0.5, ox), 0, h * 0.125, 0));                    // 閘極介電層（只在閘極底下）
      g.add(put(box(w * FET_LG, h * 0.26, d * 0.5, mt), 0, h * 0.28, 0));                     // 閘極：一塊蓋子，連ㄇ字都談不上
      [-1, 1].forEach(s => {
        g.add(put(box(w * 0.04, h * 0.22, d * 0.5, sp), s * (w * FET_LG / 2 + w * 0.02), h * 0.26, 0));   // 間隙壁
        g.add(put(box(w * 0.2, h * 0.2, d * 0.66, sd), s * w * 0.37, h * 0.12, 0));                       // 源極／汲極
      });
      // 金色面標放在閘極**前後**（閘極本身不透明，壓在底下就看不到了）
      g.add(fetFaces(K, [[new T.BoxGeometry(w * FET_LG, h * 0.02, d * 0.05),
        [[0, h * 0.1, d * 0.28], [0, h * 0.1, -d * 0.28]]]]));
      return g;
    }

    /* FinFET：通道立起來變成一片直立的鰭，閘極罩住鰭的**頂面與兩個側面**＝三面。
       鰭底那一段埋在 STI 裡，閘極包不到 —— 那就是 FinFET 走到盡頭的地方。*/
    function fetFin(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const si = K.mat(-0.32, { rough: 0.46 });
      const fin = K.mat(0.44, { rough: 0.34 });
      const sti = K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.6, metal: 0.04 });
      const mt = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.85, rough: 0.32 });
      const sd = K.mat(0.16, { rough: 0.5 });
      g.add(put(box(w, h * 0.4, d, si), 0, -h * 0.3, 0));
      // 三片直立的鰭：鰭高刻意是鰭寬的數倍（畫面可辨識性的下限，不是實物比例的宣稱）
      const fw = d * 0.09, fh = h * 0.56, fz = [-d * 0.2, 0, d * 0.2];
      g.add(instOf(new T.BoxGeometry(w * 0.72, fh, fw), fin, fz.map(z => [0, h * 0.18, z])));
      // STI：填在鰭與鰭之間的**下半段**，只淹到鰭的下部
      g.add(put(box(w * 0.74, h * 0.2, d * 0.62, sti), 0, 0, 0));
      /* ㄇ 字形閘極：一條橫樑橫跨過三片鰭，四支腳插進鰭與鰭之間（以及最外側兩邊）。
         橫樑＋四支腳併成一顆 mesh —— 它是一體成型的一塊金屬，不是五根棒子。*/
      const legs = [[w * FET_LG, h * 0.14, d * 0.86, 0, h * 0.46, 0]];
      [-0.3, -0.1, 0.1, 0.3].forEach(fz2 => legs.push([w * FET_LG, h * 0.3, d * 0.09, 0, h * 0.24, fz2 * d]));
      g.add(mboxes(legs, mt));
      [-1, 1].forEach(s => g.add(put(box(w * 0.2, h * 0.34, d * 0.6, sd), s * w * 0.38, h * 0.13, 0)));
      /* 金色面標：中間那片鰭的頂面 ＋ 兩個側面，放在閘極前方看得到的地方。
         頂面一片、側面兩片 ＝ 三片，數得出來。*/
      g.add(fetFaces(K, [
        [new T.BoxGeometry(w * 0.05, h * 0.02, fw), [[w * 0.2, h * 0.46, 0]]],
        [new T.BoxGeometry(w * 0.05, fh * 0.6, h * 0.02), [[w * 0.2, h * 0.28, fw * 0.55], [w * 0.2, h * 0.28, -fw * 0.55]]],
      ]));
      return g;
    }

    /* GAA 的奈米片通道：2～4 片水平堆疊、彼此不相連；片寬遠大於片厚
       （正方形斷面那是奈米線 nanowire，不是奈米片）。
       ★ 這一支只畫「片」，閘極金屬是另一個零件（gaagate）—— 拆解時閘極抬起來，
         才看得到金屬原本是**填進每一對片之間的縫**，而不是只蓋在最上面那片上方。*/
    function nanoSheet(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const si = K.mat(-0.32, { rough: 0.46 });
      const sh = K.mat(0.46, { rough: 0.32 });
      const sd = K.mat(0.16, { rough: 0.5 });
      const sp = K.mat(0, { color: K.css('--dg-abf', '#c3b9a4'), rough: 0.7, metal: 0.05 });
      g.add(put(box(w, h * 0.34, d, si), 0, -h * 0.33, 0));
      const st = h * 0.055, pit = h * 0.19, y0 = -h * 0.04;
      const at = [];
      for (let i = 0; i < 3; i++) at.push([0, y0 + i * pit, 0]);
      g.add(instOf(new T.BoxGeometry(w * 0.62, st, d * 0.5), sh, at));
      // 源／汲磊晶：把三片的端部**一起**接起來，不是一片接一個
      [-1, 1].forEach(s => g.add(put(box(w * 0.18, pit * 2 + st * 2.6, d * 0.58, sd), s * w * 0.39, y0 + pit, 0)));
      // 內間隙壁：每一片的兩端，夾在閘極金屬與源汲磊晶之間（沒有它，閘極會跟源汲短路）
      const isp = [];
      for (let i = 0; i < 3; i++) [-1, 1].forEach(s => isp.push([s * w * 0.28, y0 + i * pit, 0]));
      g.add(instOf(new T.BoxGeometry(w * 0.035, pit - st * 0.2, d * 0.5), sp, isp));
      return g;
    }

    /* GAA 的閘極金屬：★ 這是「Gate-All-Around」這個名字的全部意義 ——
       金屬不只在最上面那片的上方，而是**填進每一對相鄰奈米片之間的縫**，最下面那片的下方也有。
       只畫在最上面＝畫的是 FinFET。幾何刻意跟 nanoSheet 用同一組 pit／y0：
       合攏時剛好咬合、拆開時抬起來就看得到那幾片梳齒。*/
    function gaaGate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const mt = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.85, rough: 0.32 });
      const st = h * 0.055, pit = h * 0.19, y0 = -h * 0.04;
      const gw = w * FET_LG;
      const slabs = [];
      // 四層水平金屬：最下面那片的**下方**也有一層（少了它就退回 FinFET）
      for (let i = 0; i < 4; i++) slabs.push([gw, pit - st, d * 0.72, 0, y0 - pit / 2 + i * pit, 0]);
      // 兩側的立牆把四層接起來：金屬是一塊，不是四片
      [-1, 1].forEach(s => slabs.push([gw, pit * 3 + st, d * 0.1, 0, y0 + pit, s * d * 0.31]));
      g.add(mboxes(slabs, mt));
      /* 金色面標：中間那片的**四面**（上、下、左、右），放在閘極前方看得到的位置。
         四片 —— 跟平面的 1 片、FinFET 的 3 片數得出來。*/
      g.add(fetFaces(K, [
        [new T.BoxGeometry(w * 0.05, h * 0.018, d * 0.5), [[w * 0.2, y0 + pit + st * 0.6, 0], [w * 0.2, y0 + pit - st * 0.6, 0]]],
        [new T.BoxGeometry(w * 0.05, st, h * 0.018), [[w * 0.2, y0 + pit, d * 0.26], [w * 0.2, y0 + pit, -d * 0.26]]],
      ]));
      return g;
    }

    /* 12 吋晶圓：圓片 ＋ notch ＋ 規則排列的晶粒。
       識別特徵有兩個，缺一個就不是晶圓：① 邊緣那一個方位缺口（notch）
       ② 邊緣那一圈**切不出完整晶粒**的格子（圖上顏色較暗的那些）。
       p.mirror：拋光片（鏡面，沒有晶粒）。p.dies：一邊幾格（示意，實際數量視晶粒大小而定）。*/
    function waferDisc(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      g.add(cyl(R, h, K.mat(p.mirror ? 0.3 : 0.18, { rough: p.mirror ? 0.08 : 0.3, metal: p.mirror ? 0.55 : 0.34 }), 48));
      // notch：整根晶碇上刻一條軸向的溝，切完每一片自然都在同一個方位
      g.add(put(box(R * 0.11, h * 1.3, R * 0.11, K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 })),
        0, 0, -R + R * 0.02));
      const n = p.dies || 0;
      if (n > 0) {
        const px = (R * 2) / n, full = [], rim = [];
        for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
          const x = (-(n - 1) / 2 + i) * px, z = (-(n - 1) / 2 + j) * px;
          const corner = Math.hypot(Math.abs(x) + px / 2, Math.abs(z) + px / 2);
          if (corner <= R * 0.97) full.push([x, h * 0.55, z]);
          else if (Math.hypot(x, z) <= R * 0.9) rim.push([x, h * 0.55, z]);
        }
        const gd = px * 0.82, gh = h * 0.42;
        g.add(instOf(new T.BoxGeometry(gd, gh, gd), K.mat(0.5, { rough: 0.3, metal: 0.4 }), full));
        // 邊緣那一圈：切不出完整晶粒，所以暗一階（晶圓越大，浪費掉的邊緣比例越小）
        if (rim.length) g.add(instOf(new T.BoxGeometry(gd, gh, gd), K.mat(-0.32, { rough: 0.6, metal: 0.16 }), rim));
      }
      return g;
    }

    /* ---------------------------------------------------------------- 矽晶圓：柴氏（CZ）長晶爐
       爐體、坩堝、承座三件一律**切掉朝向鏡頭的一段**。理由就是規格書說「不做 3D」的那一句：
       長晶爐是旋轉對稱體，不切開的話轉一圈看到的每一面都一樣 ——
       而真正要給人看的（液面、晶碇從湯裡長出來）全部在裡面。*/
    const CZ_T0 = Math.PI * 0.575, CZ_TL = Math.PI * 1.35;      // 開口約 117°，朝向預設相機那一側

    function czShell(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const st = twoSided(K, K.mat(-0.08, { metal: 0.5, rough: 0.52 }));
      g.add(put(new T.Mesh(new T.CylinderGeometry(R, R, h * 0.62, 28, 1, true, CZ_T0, CZ_TL), st), 0, -h * 0.12, 0));      // 爐壁
      // 上方收口：往上收成提拉室（晶碇就是從這裡被拉出去的）
      g.add(put(new T.Mesh(new T.CylinderGeometry(R * 0.22, R, h * 0.2, 28, 1, true, CZ_T0, CZ_TL), st), 0, h * 0.29, 0));
      g.add(put(new T.Mesh(new T.CylinderGeometry(R * 0.22, R * 0.22, h * 0.2, 20, 1, true, CZ_T0, CZ_TL), st), 0, h * 0.45, 0));
      g.add(put(cyl(R * 1.04, h * 0.06, K.mat(0.06, { metal: 0.82, rough: 0.34 }), 28), 0, -h * 0.46, 0));                 // 底座
      return g;
    }

    /* 石英坩堝：裝熔湯的那個碗，一次長晶就報廢一個（消耗品）。
       ★ 看得到**液面**才是 CZ 提拉爐 —— 碳化矽與氮化鎵用的是昇華法（PVT），爐子裡沒有液面。*/
    function czCrucible(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2, t = R * 0.07;
      const m = twoSided(K, K.mat(0.28, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.3, metal: 0.05 }));
      // 封閉的剖面（內壁 → 越過碗口 → 外壁 → 碗底），繞一圈就是一個有厚度的碗
      const prof = [[R * 0.02, t], [R * 0.58, t * 0.5], [R * 0.93, h * 0.42], [R * 0.93, h],
        [R, h], [R, h * 0.4], [R * 0.6, 0], [R * 0.02, 0], [R * 0.02, t]];
      g.add(new T.Mesh(new T.LatheGeometry(prof.map(a => new T.Vector2(a[0], a[1] - h / 2)), 26, CZ_T0, CZ_TL), m));
      return g;
    }

    /* 石墨承座（示意）：包在石英坩堝外面撐住它，底下是會自己轉的軸。
       ⚠ 這一件本圖沒有查證到可引用的來源，只畫成示意、不寫規格。*/
    function czSusceptor(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const gm = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.74, metal: 0.12 });
      const m = twoSided(K, gm);
      const prof = [[R * 0.04, 0], [R * 0.64, 0], [R, h * 0.44], [R, h], [R * 0.9, h],
        [R * 0.9, h * 0.48], [R * 0.58, h * 0.1], [R * 0.04, h * 0.1], [R * 0.04, 0]];
      g.add(new T.Mesh(new T.LatheGeometry(prof.map(a => new T.Vector2(a[0], a[1] - h / 2)), 24, CZ_T0, CZ_TL), m));
      g.add(put(cyl(R * 0.13, h * 0.7, gm, 12), 0, -h * 0.8, 0));      // 轉軸：坩堝不轉就長不出等徑的單晶
      return g;
    }

    /* 熔湯：多晶矽熔成的一鍋湯。畫的是**液面**與中央被晶碇拉起來的那一圈彎液面。
       顏色走 --dg-m-pwr（暖橘＝高溫），刻意**不加自體發光** —— Andy：「不是電競 RGB」。*/
    function czMelt(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const hot = K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), rough: 0.22, metal: 0.42 });
      g.add(new T.Mesh(new T.CylinderGeometry(R, R * 0.9, h, 26, 1, false, CZ_T0, CZ_TL), hot));
      // 彎液面：晶碇把湯拉起來的那一圈（有它才看得出「晶碇是從液面長出來的」）
      g.add(put(new T.Mesh(new T.CylinderGeometry(R * 0.44, R * 0.3, h * 0.42, 22, 1, true, CZ_T0, CZ_TL),
        twoSided(K, K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), rough: 0.18, metal: 0.5 }))), 0, h * 0.5, 0));
      return g;
    }

    /* 晶碇（ingot／boule）：由籽晶往下長成一根圓柱。
       ★ 識別特徵是那條輪廓線：頸縮（把差排甩掉）→ 肩（放大到目標直徑）→ 等徑段 → 生長界面。
         畫成一根上下等粗的圓柱就少了 CZ 的識別特徵。
       另外沿著整根刻一條軸向的溝（notch）—— 切完每一片自然都有同一個方位記號。*/
    function czIngot(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const si = K.mat(0.16, { rough: 0.22, metal: 0.42 });
      // profile 由下（生長界面，泡在湯裡）往上（籽晶端）
      const prof = [[0, 0], [R * 0.86, h * 0.02], [R, h * 0.1], [R, h * 0.58],
        [R * 0.42, h * 0.74], [R * 0.16, h * 0.82], [R * 0.15, h * 0.97], [0, h]];
      g.add(new T.Mesh(new T.LatheGeometry(prof.map(a => new T.Vector2(a[0], a[1] - h / 2)), 30), si));
      g.add(put(box(R * 0.16, h * 0.46, R * 0.16, K.mat(-0.4, { rough: 0.5, metal: 0.2 })), 0, -h * 0.17, -R * 0.96));
      return g;
    }

    /* 籽晶與籽晶桿：一顆籽晶沾上熔湯，熔湯就照著它的晶格重新排列 ——
       整根柱子因此是一顆單晶，不是一堆晶粒。桿子一邊轉一邊**往上**拉
       （畫成往下就是在把柱子推進湯裡，物理上不成立）。*/
    function czSeed(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const st = K.mat(0.1, { metal: 0.85, rough: 0.3 });
      g.add(put(cyl(R * 0.3, h * 0.66, st, 12), 0, h * 0.17, 0));                                                // 提拉桿
      g.add(put(cyl(R, h * 0.12, st, 14), 0, -h * 0.2, 0));                                                      // 夾頭
      g.add(put(box(R * 0.9, h * 0.2, R * 0.9, K.mat(0.3, { rough: 0.24, metal: 0.42 })), 0, -h * 0.38, 0));      // 籽晶本體
      return g;
    }

    /* 加熱器：環繞在坩堝的**側面**（不是裝在爐子頂上）。
       真的石墨加熱器是一整條折來折去的帶子，所以上下各一道連接環把立柱接起來。*/
    function czHeater(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const gm = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.72, metal: 0.12 });
      const n = 16, at = [];
      for (let i = 0; i < n; i++) {
        const a = CZ_T0 + CZ_TL * (i + 0.5) / n;
        at.push([Math.sin(a) * R, 0, Math.cos(a) * R, 0, a, 0]);
      }
      g.add(instOf(new T.BoxGeometry(R * 0.22, h * 0.82, R * 0.08), gm, at));
      const ring = twoSided(K, K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.66, metal: 0.16 }));
      [-1, 1].forEach(s => g.add(put(new T.Mesh(new T.CylinderGeometry(R, R, h * 0.09, 26, 1, true, CZ_T0, CZ_TL), ring), 0, s * h * 0.45, 0)));
      return g;
    }

    /* 一疊切好的晶圓：多線鋸一次切出上百片，所以它是**一疊**不是一片。
       每一片的 notch 都在同一個方位（切片之前就刻在晶碇上）—— 整疊對齊就是這件事的證據。*/
    function waferStack(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const n = p.layers || 9;
      const t = h / (n * 1.9), pit = (h - t) / (n - 1);
      const m = K.mat(0.24, { rough: 0.2, metal: 0.46 });
      const nm = K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 });
      const at = [], nt = [];
      for (let i = 0; i < n; i++) {
        const y = -h / 2 + t / 2 + i * pit;
        at.push([0, y, 0]); nt.push([0, y, -R + R * 0.02]);
      }
      g.add(instOf(new T.CylinderGeometry(R, R, t, 34), m, at));
      g.add(instOf(new T.BoxGeometry(R * 0.1, t * 1.2, R * 0.1), nm, nt));
      return g;
    }

    /* ---------------------------------------------------------------- HBM：切掉一角的堆疊
       切法跟 MLCC 一致（x > 0 且 z > 0 那一角挖掉）。切開的理由只有一個：
       **TSV 是一根貫穿的柱子，不切開就永遠只能相信它在裡面**。
       hbmLayout 由 hbmCore 與 ubumpRows 共用 —— 凸塊要跟每一層的縫**對得齊**，
       各自算一套一定會錯開，而「對不齊就電氣上接不起來」正是這張圖要講的事。*/
    function hbmLayout(h, n) {
      const t = h / (n * 1.45), pit = t * 1.45;
      const gaps = [];
      for (let i = 0; i < n - 1; i++) gaps.push(-h / 2 + i * pit + t + (pit - t) / 2);
      return { t: t, pit: pit, gap: pit - t, gaps: gaps, y0: -h / 2 };
    }

    /* HBM 的記憶體晶粒（core die）堆：一層一層疊上去的 DRAM。
       本圖畫 6 層示意；實際層數依世代而定（查不到可引用的層數說明，所以不寫 8-high／12-high）。*/
    function hbmCore(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const n = p.layers || 6;
      const L = hbmLayout(h, n);
      const slabs = [];
      for (let i = 0; i < n; i++) cutSlab(w, L.t, d, L.y0 + i * L.pit + L.t / 2).forEach(b => slabs.push(b));
      g.add(mboxes(slabs, K.mat(0.1, { rough: 0.36, metal: 0.32 })));
      for (let i = 0; i < n; i++) g.add(cutFace(K, w, L.t, d, L.y0 + i * L.pit + L.t / 2, 0.1));
      /* 最上面那一層的 TSV 可以不用（它沒有東西要往上接），所以頂面留一片沒有柱子的區 ——
         不是裝飾，是「頂層跟其他層不一樣」這件事在畫面上唯一的線索。*/
      const top = L.y0 + (n - 1) * L.pit + L.t;
      g.add(mboxes(cutSlab(w * 0.72, L.t * 0.16, d * 0.72, top), K.mat(0.38, { rough: 0.3, metal: 0.4 })));
      return g;
    }

    /* base die（邏輯晶粒）：★ 最底下這顆**不是記憶體**，是邏輯晶粒（base die／buffer die）。
       它比 core die 厚、而且不同色；上面每一層記憶體都透過 TSV 跟它交換資料與控制訊號。*/
    function hbmBase(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(cutSlab(w, h, d), K.mat(-0.22, { rough: 0.34, metal: 0.36 })));
      g.add(cutFace(K, w, h, d, 0, -0.22));
      // 上表面的邏輯區塊：它是一顆**跑邏輯製程**的晶片，不是一片空白的矽
      const at = [];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) {
        const x = (-1 + i) * w * 0.28, z = (-0.5 + j) * d * 0.4;
        if (x > 0 && z > 0) continue;                 // 被切掉的那一角不畫
        at.push([x, h * 0.53, z]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.2, h * 0.1, d * 0.28), K.mat(0.34, { rough: 0.4, metal: 0.34 }), at));
      return g;
    }

    /* 穿矽孔（TSV）：一根根**垂直貫穿**每一層，把上面的記憶體跟底下的邏輯晶粒接起來。
       ⚠ 柱子畫在被切掉的那一角裡 —— 剖視圖的慣例就是「切開是為了看見裡面那些柱子」。
       直徑、間距與每一疊的數量查不到可引用的數字，所以只畫關係、不標數字。*/
    function tsvCols(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-m-cu', '#D6A886'), metal: 0.9, rough: 0.3 });
      const r = Math.min(w, d) * 0.028, at = [];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) at.push([w * (0.12 + i * 0.14), 0, d * (0.12 + j * 0.14)]);
      g.add(instOf(new T.CylinderGeometry(r, r, h, 8), cu, at));
      return g;
    }

    /* 微凸塊（microbump）：夾在每兩層之間。N 層晶粒就有 N−1 排。
       ★ 它跟 TSV **上下對齊成一條連續的導通柱**，所以 x／z 的排法跟 tsvCols 一模一樣。
       p.baseRow：多算一排 ＝ base die 與最底下那層 core die 之間那一排。*/
    function ubumpRows(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const n = p.layers || 6;
      const L = hbmLayout(h, n);
      const cu = K.mat(0, { color: K.css('--dg-m-cu', '#D6A886'), metal: 0.88, rough: 0.32 });
      const ys = L.gaps.slice();
      if (p.baseRow) ys.unshift(-h / 2 - L.gap / 2);
      const r = Math.min(w, d) * 0.042, at = [];
      ys.forEach(y => { for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) at.push([w * (0.12 + i * 0.14), y, d * (0.12 + j * 0.14)]); });
      g.add(instOf(new T.CylinderGeometry(r, r, L.gap * 0.92, 10), cu, at));
      // 層間填充（示意）：填在每兩層之間、微凸塊周圍。⚠ 沒有查證，不寫材料名稱、不寫製程名稱
      const fill = [];
      ys.forEach(y => cutSlab(w * 0.98, L.gap * 0.6, d * 0.98, y).forEach(b => fill.push(b)));
      g.add(mboxes(fill, K.mat(0, { color: K.css('--dg-abf', '#c3b9a4'), rough: 0.72, metal: 0.05, op: 0.55 })));
      return g;
    }

    /* ---------------------------------------------------------------- 第三代半導體：兩顆並排的剖面
       兩顆元件都切掉同一個角。SiC 是**垂直**元件（汲極在背面）、GaN 是**橫向**元件
       （三個電極全在上表面）—— 這一組對比是這張圖最重要的視覺事實，
       而它只有把兩顆擺在一起、而且正反面都看得到，才成立。
       p.k 給明暗（同一顆元件內靠明暗分層，一張圖一個主色）、p.tint 給 token 名。*/
    function wbgLayer(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const k = p.k == null ? 0 : p.k;
      const m = p.tint ? K.mat(0, { color: K.css(p.tint, ''), rough: p.rough, metal: p.metal })
        : K.mat(k, { rough: p.rough, metal: p.metal });
      g.add(mboxes(halfSlab(w, h, d), m));
      g.add(halfFace(K, w, h, d, 0, k));
      return g;
    }

    /* p-body 與 n⁺ 源極區：兩個 p-body 把電流夾成一條窄路（JFET 區，只有平面閘才有）。
       ★ n⁺ 源極區一定被 p-body 包住，不能直接碰到 n⁻ 漂移層 —— 碰到就等於把元件短路掉了。
       兩個 n⁺ 做到 z = 0 的剖面上（不然它埋在 p-body 裡，從外面一個像素都看不到）。*/
    function wbgBody(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const blocks = [], nblocks = [];
      [-1, 1].forEach(s => {
        const cx = s * w * 0.3;
        blocks.push([w * 0.34, h, d / 2, cx, 0, -d / 4]);
        nblocks.push([w * 0.16, h * 0.4, d * 0.44, cx, h * 0.22, -d / 4 + d * 0.03]);
      });
      g.add(mboxes(blocks, K.mat(0.34, { rough: 0.44 })));
      g.add(mboxes(nblocks, K.mat(0.66, { rough: 0.38 })));
      g.add(halfFace(K, w, h, d, 0, 0.34));
      return g;
    }

    /* 閘極氧化層 ＋ 閘極：氧化層夾在閘極與半導體之間，是全圖最薄的一層之一 ——
       ★ 沒有這一層就不叫 MOSFET（閘極直接碰到半導體那是 JFET 或 HEMT）。*/
    function wbgGate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w, h * 0.3, d, -h * 0.35),
        K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.36, metal: 0.04 })));
      g.add(mboxes(halfSlab(w * 0.96, h * 0.6, d * 0.96, h * 0.2),
        K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.85, rough: 0.32 })));
      return g;
    }

    /* 正面金屬（源極）：蓋住正面大部分，靠接觸窗下去接到 n⁺ 源極與 p-body。
       它和閘極在同一面、和背面的汲極分屬兩側 —— 這就是「垂直元件」的定義。*/
    function wbgTop(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const mt = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.86, rough: 0.3 });
      g.add(mboxes(halfSlab(w, h * 0.5, d, h * 0.25), mt));
      const plugs = [];
      [-1, 1].forEach(s => plugs.push([w * 0.14, h * 0.7, d * 0.4, s * w * 0.3, -h * 0.3, -d * 0.22]));
      g.add(mboxes(plugs, mt));                        // 接觸窗：金屬不是浮在上面的一片板子
      g.add(halfFace(K, w, h * 0.5, d, h * 0.25, 0));
      return g;
    }

    /* p-GaN 閘（常關做法之一）：在 AlGaN 上長一層 p 型 GaN，
       內建電位把閘極底下的 2DEG 耗盡，零偏壓時就不導通。
       ★ p-GaN 一定在**閘極金屬與 AlGaN 之間**。*/
    function wbgPgan(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w, h, d), K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.5, metal: 0.1 })));
      g.add(halfFace(K, w, h, d, 0, 0));
      return g;
    }

    /* 源極／閘極／汲極：★ 三個電極**全部做在同一個上表面**、背面一個都沒有 ——
       這就是「橫向元件」。也正因為是橫向，它受表面崩潰限制，主流停在 650V 級。*/
    function wbgElec(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const pads = [];
      /* 每一筆是 [中心 x, 高, 寬, 底面離零件底面多高]。
         源極與汲極直接坐在 AlGaN 阻障層上（底面 0）；閘極**站在 p-GaN 上**，
         所以它的底面要抬高一層 p-GaN 的厚度 —— 閘極金屬直接碰到 AlGaN 就不是 p-GaN 閘了。*/
      [[-w * 0.33, h * 0.46, w * 0.2, 0], [0, h * 0.54, w * 0.13, h * 0.46],
        [w * 0.33, h * 0.46, w * 0.2, 0]].forEach(a => {
        const cx = a[0], hh = a[1], ww = a[2], cy = a[3] + hh / 2 - h / 2;
        pads.push([ww, hh, d / 2, cx, cy, -d / 4]);
      });
      g.add(mboxes(pads, K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.86, rough: 0.3 })));
      return g;
    }


    /* ================================================================ AI 伺服器鏈六張的零件字彙（2026-09-23，DECISIONS #250）
       這六張的規格書 §0 都寫過「不做真 3D」。推翻的不是那幾句話，是它們**漏掉的另一半**
       （跟 #247 同一條判準：「轉一圈能不能多理解一件事」）—— 逐張的理由寫在 DECISIONS #250。
       畫法上的共同規矩（跟半導體鏈那四張一致，不要在這裡另立一套）：
         · **一疊薄層**（IC 載板、多層板）一律**半剖**（`_halfSlab`／`_halfFace`），
           孔畫成貼在剖面上的**半截管** —— 整根管埋進不透明的板子裡等於沒畫。
         · **立體件**（PSU、風扇、冷板、交換器板卡）不切，層次交給爆炸位移拉開。
         · 顏色只走 FAMILY_TOKENS 與 `--dg-*`；一張圖一個主色，層與層靠明暗（`K.mat` 的 k）分。
         · 陣列（錫球、微孔、鰭片、籠架、電芯、光模組籠）一律 `instOf`（InstancedMesh）。
         · 不加自體發光，只有指示燈（`led`）例外 —— Andy：「不是電競 RGB」。*/

    /* 半剖的剖面上，孔是一截**內壁朝向鏡頭**的半管。
       CylinderGeometry 的 theta 0 在 +z，[π/2, π] 這一段剛好落在留下來的 z < 0 那一半；
       從 +z 看過去看到的是它的背面，所以材質一定要 `twoSided`，不然會被背面剔除吃掉。*/
    function halfTube(r0, r1, h, seg) {
      return new T.CylinderGeometry(r0, r1, h, seg || 10, 1, true, Math.PI / 2, Math.PI);
    }

    /* ---------------------------------------------------------------- IC 載板：ABF 增層剖面
       規格書 docs/diagram_specs/abf_substrate.md §3-A／§3-B 的硬規則，這裡逐條畫出來：
         · core **只有一片、在正中間、明顯最厚**，而且**全圖只有它看得出織紋**；
         · 上下增層**層數與厚度相等**（不對稱＝翹曲，而翹曲正是這張圖在講的事）；
         · 微孔是**錐形**、**窄的那一端朝向 core**：上半朝下收窄、下半朝上收窄。
       ABF 這組常數是**四支建造函式共用**的（核心層、增層、走線、孔）——
       各算各的一定會錯開，而「孔對不準銅線就導不通」正是這張圖的主題。*/
    const ABF = { core: 6, bu: 2.2, n: 3 };
    function abfY(i) {                     // 第 i 層增層的中心 y（i ＞ 0 往上、i ＜ 0 往下）
      const s = i > 0 ? 1 : -1, k = Math.abs(i);
      return s * (ABF.core / 2 + ABF.bu * (k - 0.5));
    }
    const abfTop = () => ABF.core / 2 + ABF.bu * ABF.n;        // 最上層增層的上表面

    /* 核心層 core：半剖的厚板 ＋ 剖面上的玻纖織紋 ＋ 兩面覆銅。
       織紋畫在**剖面上**才對：經紗被切斷 → 一排小圓；緯紗順著切面 → 一條長帶。
       畫成一片均勻的板子就分不出 core 與 ABF 膜，而那是這張圖的第一件事。*/
    function abfCore(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box, h = ABF.core;
      g.add(mboxes(halfSlab(w, h, d), K.mat(-0.34, { rough: 0.7, metal: 0.06 })));
      g.add(halfFace(K, w, h, d, 0, -0.34));
      const fz = Math.max(0.06, Math.min(w, d) * 0.004) * 2.4;      // 剖面板的前方一點點
      const wv = K.mat(0.26, { color: K.css('--dg-pp', '#8a8355'), rough: 0.82, metal: 0.04 });
      const cir = [];
      for (let i = 0; i < 11; i++) cir.push([(-5 + i) * (w / 12), h * 0.16, fz, Math.PI / 2, 0, 0]);
      g.add(instOf(new T.CylinderGeometry(h * 0.1, h * 0.1, fz, 8), wv, cir));      // 經紗（被切斷）
      g.add(mboxes([[w * 0.96, h * 0.12, fz, 0, -h * 0.2, fz / 2]], wv));           // 緯紗（順著切面）
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.8, rough: 0.3 });
      g.add(mboxes([[w, h * 0.08, d / 2, 0, h * 0.46, -d / 4],
        [w, h * 0.08, d / 2, 0, -h * 0.46, -d / 4]], cu));                          // core 兩面的線路
      return g;
    }

    /* ABF 增層膜：上下各 n 層，**均勻、沒有織紋**（ABF 本來就不含織造玻纖，畫了是結構錯誤）。
       每一層自己一塊半剖的板，層與層之間留一條更暗的接縫 —— 看得出是「一層一層貼上去」的。*/
    function abfBuildup(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      /* ★ 顏色走**材質族 organic 的明暗**，不寫死 `--dg-abf`：
         那個 token（淺色 #cfc6b1）是給 2D「畫在白紙上、外面有描邊」用的，
         3D 沒有描邊、底又是淡藍灰，整疊載板會糊進背景裡（截圖比對出來的）。
         膜亮、接縫暗、core 更暗 —— #244 的「一張圖一個主色，層與層靠明暗分」。*/
      const film = K.mat(0.3, { rough: 0.66, metal: 0.06 });
      const seam = K.mat(-0.08, { rough: 0.76, metal: 0.05 });
      const slabs = [], seams = [];
      for (let s = -ABF.n; s <= ABF.n; s++) {
        if (!s) continue;
        const y = abfY(s);
        // ★ 上下對稱：同一個 |s| 的厚度完全一樣。外層略窄一階，看得出是疊上去不是一塊實心板
        const kw = w * (1 - Math.abs(s) * 0.02);
        slabs.push([kw, ABF.bu * 0.86, d / 2, 0, y, -d / 4]);
        seams.push([kw, ABF.bu * 0.1, d / 2 * 0.995, 0, y - (s > 0 ? 1 : -1) * ABF.bu * 0.47, -d / 4]);
      }
      g.add(mboxes(slabs, film));
      g.add(mboxes(seams, seam));
      return g;
    }

    /* 增層裡的銅線路（半加成 SAP／mSAP 做出來的細線）：剖面上是一排**明顯比 PCB 走線細**的矩形。
       每一層增層的底面都有一層 —— 微孔就是打到這一層的銅上才停的。*/
    function abfTrace(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu-lit', '#c88a4e'), metal: 0.88, rough: 0.26 });
      const tw = w * 0.012, at = [];
      for (let s = -ABF.n; s <= ABF.n; s++) {
        if (!s) continue;
        const y = abfY(s) - (s > 0 ? 1 : -1) * ABF.bu * 0.4;
        for (let i = 0; i < 15; i++) at.push([(-7 + i) * (w / 17), y, -d / 4]);
      }
      g.add(instOf(new T.BoxGeometry(tw, ABF.bu * 0.16, d / 2 * 0.98), cu, at));
      return g;
    }

    /* 三種孔共用一支（`v`）：core 貫孔 ／ 雷射微孔 ／ 疊孔。
       ★ 它們的差別就是這張圖跟「PCB 硬板」那張分家的地方，所以形狀一條都不准含糊：
         core  ＝ **直筒**、只穿 core、孔內**填塞**、兩端**蓋銅**（不是空心）
         micro ＝ **錐形**、只穿**一層**增層、**窄端朝 core**（上半朝下、下半朝上收窄）
         stack ＝ 兩個微孔**軸心對齊**、中間看得到一段被電鍍填平的銅（沒填平就不准疊）*/
    function abfVia(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const cu = twoSided(K, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.86, rough: 0.28 }));
      const fill = K.mat(-0.15, { rough: 0.8, metal: 0.06 });
      const cap = K.mat(0, { color: K.css('--dg-cu-lit', '#c88a4e'), metal: 0.88, rough: 0.26 });
      const fz = Math.max(0.06, Math.min(w, d) * 0.004) * 2.2;
      const v = p.v || 'core';
      if (v === 'core') {
        const r = w * 0.022, h = ABF.core;
        const at = [];
        for (let i = 0; i < 5; i++) at.push([(-2 + i) * (w * 0.17), 0, fz]);
        g.add(instOf(halfTube(r, r, h, 10), cu, at));                        // 鍍銅孔壁（直筒）
        g.add(instOf(halfTube(r * 0.72, r * 0.72, h * 0.99, 8), fill, at));  // 填塞物（不是空心）
        const caps = [];
        at.forEach(a => { caps.push([r * 2.6, h * 0.07, fz, a[0], h * 0.46, fz / 2]);
          caps.push([r * 2.6, h * 0.07, fz, a[0], -h * 0.46, fz / 2]); });
        g.add(mboxes(caps, cap));                                            // 兩端蓋銅
      } else if (v === 'micro') {
        const r = w * 0.014;
        const up = [], dn = [];
        for (let s = -ABF.n; s <= ABF.n; s++) {
          if (!s) continue;
          const y = abfY(s);
          for (let i = 0; i < 6; i++) (s > 0 ? up : dn).push([(-3.4 + i * 1.25) * (w * 0.1), y, fz]);
        }
        // 上半：上寬下窄（窄端朝下＝朝 core）；下半：上窄下寬（窄端朝上＝朝 core）
        g.add(instOf(halfTube(r * 2.2, r, ABF.bu * 0.9, 8), cu, up));
        g.add(instOf(halfTube(r, r * 2.2, ABF.bu * 0.9, 8), cu, dn));
      } else {
        const r = w * 0.016;
        const upAt = [], dnAt = [], mid = [];
        [-1, 1].forEach(sg => {
          const x = sg * w * 0.3;
          for (let k = 1; k <= 2; k++) {
            const y = abfY(sg > 0 ? k : -k);
            (sg > 0 ? upAt : dnAt).push([x, y, fz]);
            if (k < 2) mid.push([r * 2.8, ABF.bu * 0.18, fz, x, y + sg * ABF.bu * 0.5, fz / 2]);
          }
        });
        // 疊孔的兩顆跟一般微孔一樣朝 core 收窄，而且**軸心對齊**（沒對齊就不叫疊孔）
        g.add(instOf(halfTube(r * 2.3, r, ABF.bu * 0.92, 8), cu, upAt));
        g.add(instOf(halfTube(r, r * 2.3, ABF.bu * 0.92, 8), cu, dnAt));
        g.add(mboxes(mid, cap));                                             // 中間那一段被電鍍填平的銅
      }
      return g;
    }

    /* 防焊層（solder resist）與開窗：上下各一片，**在墊子的位置開窗**（不是整片蓋滿）。
       一條連續的帶子被缺口斷開 —— 缺口就是開窗，墊子從那裡露出來。*/
    function abfSr(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const sr = K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.72, metal: 0.05 });
      /* 寬度跟**最外層增層膜**一致（那一層是 w × 0.94）—— 比它寬的話，合攏時防焊帶會從板子兩側凸出來，
         看起來像掛在外面的裝飾條而不是蓋在板面上的一層。*/
      const bw = w * (1 - ABF.n * 0.02);
      const t = 0.9, segs = [], gap = bw * 0.055, n = 7;
      [1, -1].forEach(sg => {
        const y = sg * (abfTop() + t / 2);
        for (let i = 0; i <= n; i++) {
          const x0 = -bw / 2 + i * (bw / (n + 1)), x1 = x0 + (bw / (n + 1)) - gap;
          segs.push([x1 - x0, t, d / 2, (x0 + x1) / 2, y, -d / 4]);
        }
      });
      g.add(mboxes(segs, sr));
      return g;
    }

    /* 凸塊墊（bump pad）＋ 表面處理：只長在**上表面**開窗露出來的銅上。
       上下對調（把球墊畫成 bump pad）就是把「上面接晶片、下面接主機板」整個講反了。*/
    function abfPad(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu-lit', '#c88a4e'), metal: 0.88, rough: 0.26 });
      const au = K.mat(0, { color: K.css('--dg-sw-gold', '#d9a441'), metal: 0.9, rough: 0.22 });
      const at = gridXZ(7, 5, w / 7.6, d / 5.6, 0);
      g.add(instOf(new T.BoxGeometry(w / 7.6 * 0.5, h * 0.55, d / 5.6 * 0.5), cu, at));
      g.add(instOf(new T.BoxGeometry(w / 7.6 * 0.5, h * 0.2, d / 5.6 * 0.5), au,
        at.map(a => [a[0], a[1] + h * 0.36, a[2]])));
      return g;
    }

    /* BGA 錫球：三種節距裡**最大**的那一種（微凸塊 ＜ C4 ＜ BGA）。
       球就是球 —— 方塊看起來像腳墊。迴焊之後是略扁的球，所以 y 方向壓過。*/
    function abfBga(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      /* ★ 錦球刷暗一階，不用 `--dg-sn` 的原色：
         量出來的對比是 **1.06**（#e2e7ec 對閱讀模式的淡藍灰底 #E8EDF2）——
         白球在白底上幾乎看不見。走材質族的明暗（k 負）拉到 1.6 以上。*/
      const sn = K.mat(-0.32, { metal: 0.6, rough: 0.34 });
      const r = Math.min(w / 5, d / 4) * 0.3;
      const at = [];
      for (let i = 0; i < 5; i++) for (let j = 0; j < 4; j++) {
        at.push([(-2 + i) * (w / 5), 0, (-1.5 + j) * (d / 4), 0, 0, 0, 1, Math.max(0.5, h / (r * 2)) * 0.6, 1]);
      }
      g.add(instOf(new T.SphereGeometry(r, 10, 7), sn, at));
      return g;
    }

    /* ---------------------------------------------------------------- PCB 硬板：多層板剖面與四種孔
       規格書 docs/diagram_specs/pcb_stackup.md §3-A：
         **core 一定是「銅－介電－銅」三件一組；prepreg 一定沒有銅。**
         兩者畫成同一種顏色的介電層是這張圖最常見也最致命的錯 —— 所以連厚度表都寫死共用。
       由下到上：外層銅 L10 ｜ pp ｜ core(L9-介電-L8) ｜ pp ｜ core(L7-介電-L6)
                 ｜ pp ｜ core(L5-介電-L4) ｜ pp ｜ core(L3-介電-L2) ｜ pp ｜ 外層銅 L1
       ＝ 10 層銅、4 片芯板、5 片半固化片，上下完全對稱。*/
    const PCB_CU = 0.45, PCB_PP = 1.7, PCB_DI = 2.0;
    const PCB_CORE_H = PCB_CU * 2 + PCB_DI;
    const PCB_H = PCB_CU * 2 + PCB_PP * 5 + PCB_CORE_H * 4;          // 21.0
    /* 由下往上把每一片排好：[種類, 中心 y, 厚度]。五支建造函式共用同一張表 ——
       各算各的一定會錯開，而「孔停在哪一層銅上」全靠這張表對齊。*/
    function pcbStack() {
      const out = [];
      let y = -PCB_H / 2;
      const push = (t, h) => { out.push([t, y + h / 2, h]); y += h; };
      push('foil', PCB_CU);
      for (let i = 0; i < 4; i++) { push('pp', PCB_PP); push('core', PCB_CORE_H); }
      push('pp', PCB_PP); push('foil', PCB_CU);
      return out;
    }
    // 第 n 層銅（1 ＝ 最上面那一層外層銅，10 ＝ 最下面）的中心 y
    function pcbCuY(n) {
      const cu = [];
      pcbStack().forEach(([t, cy, h]) => {
        if (t === 'foil') cu.push(cy);
        else if (t === 'core') { cu.push(cy + (h - PCB_CU) / 2); cu.push(cy - (h - PCB_CU) / 2); }
      });
      cu.sort((a, b) => b - a);
      return cu[Math.max(0, Math.min(cu.length - 1, n - 1))];
    }

    /* 五種層共用一支（`lay`）：芯板 core ／ 半固化片 prepreg ／ 外層銅箔 ／ 接地平面 ／ 玻纖織紋。
       全部畫成半剖（z > 0 切掉），剖面才是這張圖唯一的主角。*/
    function pcbLayer(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const lay = p.lay || 'core';
      const st = pcbStack();
      if (lay === 'core') {
        // 芯板：已固化的介電 ＋ **兩面**覆銅。銅一定明顯薄於它旁邊的介電
        const di = [], cus = [];
        st.filter(a => a[0] === 'core').forEach(([, cy, h]) => {
          di.push([w, PCB_DI, d / 2, 0, cy, -d / 4]);
          cus.push([w, PCB_CU, d / 2, 0, cy + (h - PCB_CU) / 2, -d / 4]);
          cus.push([w, PCB_CU, d / 2, 0, cy - (h - PCB_CU) / 2, -d / 4]);
        });
        g.add(mboxes(di, K.mat(-0.2, { color: K.css('--dg-core', '#3f4a30'), rough: 0.72, metal: 0.05 })));
        g.add(mboxes(cus, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.82, rough: 0.28 })));
      } else if (lay === 'pp') {
        // 半固化片：**沒有銅**。它是把芯板黏起來的膠片，顏色與芯板明顯不同
        g.add(mboxes(st.filter(a => a[0] === 'pp').map(([, cy]) => [w * 0.998, PCB_PP, d / 2, 0, cy, -d / 4]),
          K.mat(0.08, { color: K.css('--dg-pp', '#8a8355'), rough: 0.78, metal: 0.04 })));
      } else if (lay === 'foil') {
        g.add(mboxes(st.filter(a => a[0] === 'foil').map(([, cy]) => [w, PCB_CU, d / 2, 0, cy, -d / 4]),
          K.mat(0.25, { color: K.css('--dg-cu-lit', '#c88a4e'), metal: 0.88, rough: 0.24 })));
      } else if (lay === 'plane') {
        // 接地／電源平面：**整片**銅（不准開一堆槽）。畫在 L3／L5／L6／L8 四層上
        g.add(mboxes([3, 5, 6, 8].map(n => [w * 0.99, PCB_CU * 1.12, d / 2 * 0.99, 0, pcbCuY(n), -d / 4]),
          K.mat(0.12, { color: K.css('--dg-cu-dim', '#9a5f34'), metal: 0.84, rough: 0.3 })));
      } else {
        // 玻纖織紋：只有 core 與 prepreg 有（外層銅箔沒有）。做在剖面上：經紗被切斷成一排圓
        const fz = Math.max(0.06, Math.min(w, d) * 0.004) * 2.4;
        const wv = K.mat(0.3, { color: K.css('--dg-cer-2', '#bbb39f'), rough: 0.84, metal: 0.03 });
        const at = [];
        st.forEach(([t, cy]) => {
          if (t === 'foil') return;
          for (let i = 0; i < 13; i++) at.push([(-6 + i) * (w / 14), cy, fz, Math.PI / 2, 0, 0]);
        });
        g.add(instOf(new T.CylinderGeometry(PCB_PP * 0.2, PCB_PP * 0.2, fz, 7), wv, at));
      }
      return g;
    }

    /* 走線：內層是夾在兩層接地之間的**帶狀線**差動對；外層是頂視看得到的蛇行等長線。
       `top` ＝ 頂層那一組（走在 L1 的上表面，45° 轉角、成雙成對）。*/
    function pcbTrace(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      if (p.top) {
        const tl = traceLayer(K, w * 0.92, d * 0.42, pcbCuY(1) + PCB_CU * 0.8, { pairs: 4, cycles: 5, dir: 1 });
        tl.group.position.z = -d / 4;
        g.add(tl.group); g.userData.flows = tl.flows;
        return g;
      }
      const cu = K.mat(0.3, { color: K.css('--dg-cu-lit', '#c88a4e'), metal: 0.88, rough: 0.24 });
      const at = [];
      // 高速訊號層（L4／L7）：剖面上是一對一對的小方塊 —— 成雙才是差動對
      [4, 7].forEach(n => {
        const y = pcbCuY(n);
        for (let i = 0; i < 6; i++) {
          const x = (-2.5 + i) * (w * 0.15);
          at.push([x - w * 0.018, y, -d / 4]); at.push([x + w * 0.018, y, -d / 4]);
        }
      });
      g.add(instOf(new T.BoxGeometry(w * 0.022, PCB_CU * 1.1, d / 2 * 0.98), cu, at));
      return g;
    }

    /* 防焊（solder mask）：外層兩面都要有，而且**在焊墊處開窗**（不是整片蓋滿）。
       一條被缺口斷開的帶子 —— 缺口就是開窗。*/
    function pcbMask(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const sm = K.mat(-0.15, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.7, metal: 0.04 });
      const t = PCB_CU * 1.5, segs = [], n = 6, gap = w * 0.06;
      [1, -1].forEach(sg => {
        const y = sg * (PCB_H / 2 + t / 2);
        for (let i = 0; i <= n; i++) {
          const x0 = -w / 2 + i * (w / (n + 1)), x1 = x0 + (w / (n + 1)) - gap;
          segs.push([x1 - x0, t, d / 2, (x0 + x1) / 2, y, -d / 4]);
        }
      });
      g.add(mboxes(segs, sm));
      return g;
    }

    /* 表面處理（ENIG＝化鎳浸金）：**只出現在防焊開窗露出來的銅上**，
       不准畫在防焊之上、也不准畫成整片。鎳（暗）在下、金（亮）在上，兩層。*/
    function pcbEnig(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const ni = K.mat(0, { color: K.css('--dg-steel-2', '#6b7683'), metal: 0.8, rough: 0.34 });
      const au = K.mat(0, { color: K.css('--dg-sw-gold', '#d9a441'), metal: 0.92, rough: 0.2 });
      const n = 6, gap = w * 0.06, pw = gap * 0.9;
      const niL = [], auL = [];
      [1, -1].forEach(sg => {
        const y = sg * (PCB_H / 2 + PCB_CU * 0.4);
        for (let i = 0; i < n; i++) {
          const x = -w / 2 + (i + 1) * (w / (n + 1)) - gap / 2;
          niL.push([pw, PCB_CU * 0.5, d / 2 * 0.9, x, y, -d / 4]);
          auL.push([pw * 0.94, PCB_CU * 0.26, d / 2 * 0.88, x, y + sg * PCB_CU * 0.36, -d / 4]);
        }
      });
      g.add(mboxes(niL, ni)); g.add(mboxes(auL, au));
      return g;
    }

    /* 四種孔共用一支（`via`）。跨距與形狀照規格書 §3-B 寫死，一條都不准含糊：
         pth      L1 → L10，**上下都貫穿、兩端都開口**，另標一段**殘端**（stub）
         bd       背鑽：從**背面**往上鑽掉深層的孔銅，**鑽頭比原孔粗**，
                  而且**一定留一小段鑽不乾淨的殘餘**（工程上鑽不到零，畫成剛剛好就是錯的）
         blind    L1 → L2，**只穿一層介電**、**上寬下窄的錐形**，不准穿到另一面
         buried   L4 → L7，**兩端都不准碰到任何外層**，上下都要看得到介電把它蓋住 */
    function pcbVia(p, K) {
      const g = new T.Group();
      const [w, , d] = p.box;
      const v = p.via || 'pth';
      const cu = twoSided(K, K.mat(0.1, { color: K.css('--dg-cu', '#b0743a'), metal: 0.86, rough: 0.28 }));
      const stub = twoSided(K, K.mat(0, { color: K.css('--dg-fl-hot', '#FF4D5E'), metal: 0.4, rough: 0.45 }));
      const gone = twoSided(K, K.mat(0, { color: K.css('--dg-void', '#0d1424'), metal: 0.05, rough: 0.94 }));
      const fz = Math.max(0.06, Math.min(w, d) * 0.004) * 2.2;
      const r = w * 0.016;
      const xs = [-w * 0.16, w * 0.16];
      const span = (a, b) => ({ y: (pcbCuY(a) + pcbCuY(b)) / 2, h: Math.abs(pcbCuY(a) - pcbCuY(b)) + PCB_CU });
      if (v === 'pth') {
        const s = span(1, 10);
        g.add(instOf(halfTube(r, r, s.h, 10), cu, xs.map(x => [x, s.y, fz])));
        // 殘端：訊號其實只走到 L4，L4 以下那一段是「多出來的」—— 它會變成天線
        const st = span(4, 10);
        g.add(instOf(halfTube(r * 0.99, r * 0.99, st.h * 0.98, 8), stub, xs.map(x => [x, st.y, fz + 0.02])));
      } else if (v === 'bd') {
        const s = span(1, 10);
        g.add(instOf(halfTube(r, r, s.h, 10), cu, xs.map(x => [x, s.y, fz])));
        // 鑽掉的那一段：孔徑**比原孔粗**（鑽頭要能吃掉原本的孔銅）
        const dr = span(5, 10);
        g.add(instOf(halfTube(r * 1.55, r * 1.55, dr.h, 8), gone, xs.map(x => [x, dr.y, fz + 0.03])));
        // 鑽不乾淨的殘餘：一小截還留在 L5 下面（畫成剛剛好＝把這張圖唯一的工程現實抹掉）
        g.add(instOf(halfTube(r, r, PCB_CU * 2.4, 8), stub,
          xs.map(x => [x, pcbCuY(5) - PCB_CU * 1.6, fz + 0.05])));
      } else if (v === 'blind') {
        const y0 = pcbCuY(1), y1 = pcbCuY(2), h = y0 - y1 + PCB_CU;
        // 上寬下窄的錐（雷射打的），只碰到 L1 這一個外層
        g.add(instOf(halfTube(r * 2, r * 0.9, h, 8), cu, xs.map(x => [x, (y0 + y1) / 2, fz])));
      } else {
        const s = span(4, 7);
        g.add(instOf(halfTube(r, r, s.h, 8), cu, xs.map(x => [x, s.y, fz])));
      }
      return g;
    }

    /* ---------------------------------------------------------------- 電源：PSU、匯流排、板上降壓與 BBU
       規格書 docs/diagram_specs/server_psu.md §3-A／§3-B 的硬規則：
         · **降壓不准跳級**：交流 → PSU（約 50–54 V 直流）→ 匯流排 → 板上 DC-DC → 晶片核心電壓。
         · **匯流排是厚銅排、不是圓線**，而且明顯比訊號線粗一個量級。
         · **板上 DC-DC 是「一排等距元件」**（多相），畫成一顆就看不出「多相」這件事。
         · **BBU 掛在直流側、在機櫃裡**（畫到交流側就變成 UPS 了）。
       3D 這張把「一顆 PSU 拆開」當主角：電源架拉出一顆 → 外罩掀起來 → 主板上四級由後往前排開。*/

    /* 電源架（power shelf）：一排 PSU 槽位，其中一格**空著**——
       那一格就是 N+1 冗餘的畫面證據（少一顆還撐得住）。*/
    function psuShelf(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.82, rough: 0.38 });
      const t = h * 0.05;
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0], [w, t, d, 0, -h / 2 + t / 2, 0],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2]], st));                       // 框
      const slotH = h / 3.4, pw = K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), metal: 0.42, rough: 0.5 });
      const at = [];
      for (let i = 0; i < 3; i++) at.push([0, (i - 1) * (h / 3.2), d * 0.04]);
      // 中間那一格刻意留空：N+1 —— 一顆失效時另外兩顆接手
      g.add(instOf(new T.BoxGeometry(w * 0.9, slotH * 0.74, d * 0.9), pw, [at[0], at[2]]));
      g.add(put(box(w * 0.9, slotH * 0.74, d * 0.9,
        K.mat(-0.55, { rough: 0.9, metal: 0.08 })), at[1][0], at[1][1], at[1][2]));   // 空槽（暗）
      // 每一顆的前面板指示燈
      g.add(instOf(new T.BoxGeometry(w * 0.05, slotH * 0.12, d * 0.02), K.mat(0, { led: true }),
        [[w * 0.38, at[0][1], d / 2 + 0.05], [w * 0.38, at[2][1], d / 2 + 0.05]]));
      g.add(aoPad(K, w, d, -h / 2 - 0.8));
      return g;
    }

    /* PSU 外罩：上蓋 ＋ 兩側板 ＋ 前面板（把手、風扇開孔）。
       它是一個倒 ㄇ 字的鈑金罩 —— 合攏時看起來是一顆完整的 CRPS，
       爆炸時整個往上掀，底下的主板與四級才露出來。*/
    function psuShell(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0.05, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.84, rough: 0.34 });
      const t = h * 0.08;
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0],
        [t, h * 0.92, d, -w / 2 + t / 2, t * 0.4, 0], [t, h * 0.92, d, w / 2 - t / 2, t * 0.4, 0]], st));
      // 前面板：把手 ＋ 風扇開孔（CRPS 是熱插拔的，把手是它「抽得出來」的證據）
      g.add(put(box(w * 0.98, h * 0.9, t, st), 0, t * 0.4, d / 2 - t / 2));
      g.add(put(box(w * 0.3, h * 0.16, t * 1.6, K.mat(0.3, { metal: 0.6, rough: 0.35 })), -w * 0.28, 0, d / 2 + t * 0.4));
      const hole = K.mat(-0.6, { rough: 0.9, metal: 0.05 });
      const hl = [];
      for (let i = -2; i <= 2; i++) for (let j = -1; j <= 1; j++) {
        hl.push([w * 0.2 + i * w * 0.07, j * h * 0.2, d / 2, Math.PI / 2, 0, 0]);
      }
      g.add(instOf(new T.CylinderGeometry(w * 0.024, w * 0.024, t * 2.4, 6, 1, true), hole, hl));
      g.add(put(box(w * 0.04, h * 0.12, t * 1.4, K.mat(0, { led: true })), w * 0.44, -h * 0.28, d / 2 + t * 0.4));
      return g;
    }

    /* PSU 主板：底殼 ＋ 板子 ＋ **四級由後往前**排開 —— 這是整張圖的主軸。
         ① PFC（功率因數校正）：大電感 ＋ 大電解電容（整顆 PSU 裡最大的那幾顆）
         ② LLC 諧振轉換：變壓器（一顆有繞線的大方塊）＋ 諧振電感
         ③ 同步整流：輸出側一排低壓大電流的功率元件
         ④ 輸出：厚銅排 → 卡緣
       ⚠ 每一級的**元件形狀刻意不同**：電容是圓柱、變壓器是有窗口的方塊、整流是一排扁平封裝。
         全部畫成一樣的小方塊，讀者就看不出這是四個不同的級。*/
    function psuBoard(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const tray = K.mat(-0.1, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.8, rough: 0.42 });
      g.add(put(box(w, h * 0.12, d, tray), 0, -h * 0.44, 0));                        // 底殼
      g.add(put(box(w * 0.94, h * 0.1, d * 0.94,
        K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 })), 0, -h * 0.3, 0));  // 板
      const y0 = -h * 0.25;
      // ① PFC：大電解電容（圓柱，立著）＋ 扼流圈
      const alu = K.mat(0, { color: K.css('--dg-alu', '#a3b2c4'), metal: 0.72, rough: 0.4 });
      g.add(instOf(new T.CylinderGeometry(w * 0.075, w * 0.075, h * 0.62, 12), alu,
        [[-w * 0.3, y0 + h * 0.31, -d * 0.3], [-w * 0.3, y0 + h * 0.31, -d * 0.12]]));
      g.add(put(box(w * 0.16, h * 0.34, d * 0.16,
        K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.66, metal: 0.14 })), -w * 0.3, y0 + h * 0.17, d * 0.08));
      // ② LLC：變壓器 —— 有繞線窗口的方塊（跟電容、跟整流都不是同一個形狀）
      const fer = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.62, metal: 0.16 });
      const cuw = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.82, rough: 0.3 });
      g.add(put(box(w * 0.22, h * 0.5, d * 0.3, fer), 0, y0 + h * 0.25, -d * 0.1));
      g.add(put(box(w * 0.24, h * 0.2, d * 0.2, cuw), 0, y0 + h * 0.25, -d * 0.1));   // 繞線
      g.add(put(box(w * 0.1, h * 0.26, d * 0.12, fer), 0, y0 + h * 0.13, d * 0.2));   // 諧振電感
      // ③ 同步整流：輸出側一排扁平的功率元件（低壓大電流，所以是一整排並聯）
      const pkg = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.55, metal: 0.2 });
      const rec = [];
      for (let i = 0; i < 7; i++) rec.push([w * 0.2 + 0, y0 + h * 0.08, (-3 + i) * d * 0.11]);
      g.add(instOf(new T.BoxGeometry(w * 0.1, h * 0.16, d * 0.06), pkg, rec));
      // ④ 輸出：厚銅排往卡緣去（比板上任何一條線都粗一個量級）
      g.add(put(box(w * 0.3, h * 0.08, d * 0.06, cuw), w * 0.3, y0 + h * 0.04, d * 0.34));
      g.add(put(box(w * 0.06, h * 0.08, d * 0.7, cuw), w * 0.42, y0 + h * 0.04, 0));
      return g;
    }

    /* 卡緣連接器（card-edge）：CRPS 的後端是**一排鍍金接點**，不是一束電線。
       畫成電線就認不出是 CRPS 型的伺服器 PSU（規格書 §6-S2）。*/
    function psuCardEdge(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const pl = K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 });
      g.add(box(w, h, d, pl));
      // 上下兩排金手指（CRPS 是 2 排）—— 排數就是它跟一般單排卡緣的差別
      g.add(put(fingers(K, w * 0.9, h * 0.22, d * 0.8, 13, h * 0.3, 0), 0, 0, 0));
      g.add(put(fingers(K, w * 0.9, h * 0.22, d * 0.8, 13, -h * 0.3, 0), 0, 0, 0));
      return g;
    }

    /* 直流匯流排（busbar）：沿機櫃背面**垂直**走的厚銅排 ＋ 分接點 ＋ 鎖固孔。
       它的**厚度**就是它的規格（幾百安培靠截面積過），而鎖固孔說明它是鎖上去不是焊上去。*/
    function psuBusbar(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.84, rough: 0.28 });
      const ins = K.mat(0, { color: K.css('--dg-el', '#4e5866'), rough: 0.82, metal: 0.06 });
      [-1, 1].forEach(s => g.add(put(box(w * 0.34, h, d, cu), s * w * 0.32, 0, 0)));   // 正負兩條
      g.add(put(box(w * 0.2, h * 0.9, d * 0.66, ins), 0, 0, -d * 0.14));              // 中間絕緣隔板（往後縮，正面看得到兩條銅排）
      // 分接點：每一層托盤從這裡接一組出去（成對，正負各一）
      const tap = [];
      for (let i = 0; i < 4; i++) [-1, 1].forEach(s => tap.push([s * w * 0.32, (-1.5 + i) * h * 0.22, d * 0.62]));
      g.add(instOf(new T.BoxGeometry(w * 0.3, h * 0.05, d * 0.3), cu, tap));
      const hl = K.mat(0, { color: K.css('--dg-edge', '#0e1526'), rough: 0.92, metal: 0.04 });
      g.add(instOf(new T.CylinderGeometry(w * 0.05, w * 0.05, d * 1.3, 8, 1, true), hl,
        tap.map(a => [a[0], a[1], a[2], Math.PI / 2, 0, 0])));
      return g;
    }

    /* 板上降壓 DC-DC／VRM：**一排等距的電感**（多相）＋ 旁邊一串電容。
       畫成一顆方塊就看不出「多相」，而多相正是「大電流怎麼供到晶片」的答案。*/
    function psuVrm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.16, d, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 })), 0, -h * 0.42, 0));
      const ind = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.62, metal: 0.16 });
      const n = 8, at = [];
      for (let i = 0; i < n; i++) at.push([(-(n - 1) / 2 + i) * (w / n), 0, -d * 0.16]);
      g.add(instOf(new T.BoxGeometry(w / n * 0.66, h * 0.62, d * 0.4), ind, at));       // 一排電感＝一相一顆
      const cap = K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.55, metal: 0.05 });
      const cat = [];
      for (let i = 0; i < n * 2; i++) cat.push([(-(n * 2 - 1) / 2 + i) * (w / (n * 2)), -h * 0.24, d * 0.3]);
      g.add(instOf(new T.BoxGeometry(w / (n * 2) * 0.5, h * 0.2, d * 0.14), cap, cat));
      // 電感底下那一排厚銅：相電流就是從這裡灌進晶片底下的
      g.add(put(box(w * 0.94, h * 0.08, d * 0.5, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.84, rough: 0.3 })), 0, -h * 0.3, -d * 0.16));
      return g;
    }

    /* BBU 電池備援模組：托盤 ＋ **一排電芯** ＋ 正負極柱 ＋ 管理電路 ＋ 電量燈條。
       Andy 點名過「看到電池要感覺得到電壓／極柱」—— 所以極柱一正一負、顏色不同、而且比殼高。
       ★ 它掛在**直流側、機櫃裡**（畫到交流側或櫃外就變成 UPS 了，規格書 §3-B）。*/
    function psuBbu(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const shell = K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), rough: 0.5, metal: 0.4 });
      g.add(put(rbox(w, h * 0.18, d, h * 0.07, shell), 0, -h * 0.41, 0));
      g.add(aoPad(K, w, d, -h * 0.5 - 0.8));
      [-1, 1].forEach(s => g.add(put(box(w * 0.035, h * 0.6, d, shell), s * (w / 2 - w * 0.018), -h * 0.02, 0)));
      [-1, 1].forEach(s => g.add(put(box(w, h * 0.6, d * 0.03, shell), 0, -h * 0.02, s * (d / 2 - d * 0.015))));
      // 電芯：兩排圓柱（看得到就是電池，看不到就只是一個橘盒子）
      const cell = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), metal: 0.45, rough: 0.42 });
      const at = [];
      for (let i = 0; i < 6; i++) for (let j = -1; j <= 1; j += 2) at.push([(-2.5 + i) * w * 0.15, h * 0.02, j * d * 0.22]);
      g.add(instOf(new T.CylinderGeometry(w * 0.06, w * 0.06, h * 0.72, 10), cell, at));
      // 電芯之間的連片：串聯起來電壓才疊得上去
      g.add(instOf(new T.BoxGeometry(w * 0.13, h * 0.05, d * 0.06),
        K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), metal: 0.62, rough: 0.34 }),
        at.filter((_, i) => i % 2 === 0).map(a => [a[0] + w * 0.075, h * 0.4, a[2]])));
      // 極柱：正銅、負深灰，而且比殼高 —— 一眼看得出哪邊是哪邊
      g.add(put(box(w * 0.09, h * 0.42, d * 0.09, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.82, rough: 0.28 })), w * 0.4, h * 0.44, -d * 0.3));
      g.add(put(box(w * 0.09, h * 0.42, d * 0.09, K.mat(0, { color: K.css('--dg-el', '#4e5866'), metal: 0.55, rough: 0.5 })), w * 0.4, h * 0.44, d * 0.3));
      // 管理電路（BMS）：一小塊板，它決定這組電池撐得住幾次充放
      g.add(put(box(w * 0.36, h * 0.1, d * 0.2, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 })), -w * 0.26, h * 0.36, 0));
      const led = [];
      for (let i = 0; i < 4; i++) led.push([(-0.2 + i * 0.08) * w, h * 0.02, d / 2 + 0.06]);
      g.add(instOf(new T.BoxGeometry(w * 0.05, h * 0.14, d * 0.02), K.mat(0, { led: true }), led));
      return g;
    }

    /* 超級電容／鋰離子電容（LIC）：**比 BBU 小**、圓柱陣列、跟 BBU 掛在**同一個直流節點**上。
       它管的是毫秒級的功率突波（GPU 一起動那一下），跟 BBU 的秒到分鐘不是同一回事。*/
    function psuScap(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const tray = K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), rough: 0.5, metal: 0.4 });
      g.add(put(rbox(w, h * 0.16, d, h * 0.06, tray), 0, -h * 0.42, 0));
      g.add(aoPad(K, w, d, -h * 0.5 - 0.8));
      const can = K.mat(0, { color: K.css('--dg-alu', '#a3b2c4'), metal: 0.74, rough: 0.36 });
      const at = [];
      for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) at.push([(-1 + i) * w * 0.3, h * 0.06, (-1 + j) * d * 0.3]);
      g.add(instOf(new T.CylinderGeometry(w * 0.115, w * 0.115, h * 0.78, 12), can, at));
      // 頂面的防爆刻痕：超電／電解電容的識別特徵（一個十字或 K 字）
      const sc = K.mat(-0.4, { rough: 0.7, metal: 0.3 });
      g.add(instOf(new T.BoxGeometry(w * 0.2, h * 0.02, w * 0.02), sc, at.map(a => [a[0], h * 0.45, a[2]])));
      g.add(instOf(new T.BoxGeometry(w * 0.02, h * 0.02, w * 0.2), sc, at.map(a => [a[0], h * 0.45, a[2]])));
      // 匯流條：九顆串在一起，接到跟 BBU 同一個直流節點
      g.add(put(box(w * 0.9, h * 0.06, d * 0.07, K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.82, rough: 0.3 })), 0, h * 0.49, -d * 0.3));
      return g;
    }

    /* ---------------------------------------------------------------- 液冷：冷板、均熱板 VC 與熱管
       規格書 docs/diagram_specs/liquid_cooling.md §3-A 的硬規則：
         · **每兩個固體之間都要有 TIM**，而且 TIM 畫得**比它上下的任何金屬層都薄**；
         · **冷板一定在蓋板／VC 之上**，不可以畫成冷板在下、晶片在上；
         · **進水冷、出水熱**，兩種顏色（`--dg-cold`／`--dg-hot` 是語意色，任何配色都不准蓋）；
         · 兩個迴路**只在板式熱交換器處靠在一起，絕不相接**（畫成一條管貫穿到底＝最致命的錯）。*/

    /* 導熱介面材料 TIM：**全圖最薄的一層**，而且看得出是被壓扁的膏狀物（邊緣會溢出來一點）。
       畫得跟金屬層一樣厚就把「熱阻卡在這裡」這句話抹掉了。*/
    function timLayer(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const tim = K.mat(0, { color: K.css('--dg-wick', '#8f6a45'), rough: 0.88, metal: 0.05 });
      g.add(box(w, h, d, tim));
      // 被壓出來的那一圈：四邊各溢出一點點，一看就知道它是膏不是板
      g.add(mboxes([[w * 1.03, h * 0.5, d * 0.16, 0, 0, -d / 2], [w * 1.03, h * 0.5, d * 0.16, 0, 0, d / 2],
        [w * 0.16, h * 0.5, d * 1.03, -w / 2, 0, 0], [w * 0.16, h * 0.5, d * 1.03, w / 2, 0, 0]], tim));
      return g;
    }

    /* 均熱片／蓋板（IHS）：**實心銅**的一塊蓋子，四周有腳黏在載板上。
       它跟 VC 的差別就是「實心 vs 真空腔」—— 所以這一顆刻意畫成一塊沒有內部構造的銅。*/
    function ihsLid(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0.1, { color: K.css('--dg-cu', '#b0743a'), metal: 0.86, rough: 0.28 });
      g.add(put(rbox(w * 0.82, h * 0.62, d * 0.82, h * 0.2, cu), 0, h * 0.18, 0));      // 中央凸台（貼晶片那一面）
      g.add(put(box(w, h * 0.3, d, cu), 0, -h * 0.34, 0));                              // 外緣的裙邊
      return g;
    }

    /* 冷板本體：銅底板 ＋ **掀開一半的蓋板**（不掀開就看不到裡面，而裡面才是它值錢的地方）
       ＋ 進出水的兩個接口座。*/
    function coldPlate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.86, rough: 0.3 });
      const st = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.8, rough: 0.32 });
      g.add(put(box(w, h * 0.24, d, cu), 0, -h * 0.38, 0));                             // 底板（貼 TIM2 那一面）
      // 四周的側牆：水被關在裡面才流得成流道
      const t = w * 0.045;
      g.add(mboxes([[w, h * 0.5, t, 0, 0, -d / 2 + t / 2], [w, h * 0.5, t, 0, 0, d / 2 - t / 2],
        [t, h * 0.5, d, -w / 2 + t / 2, 0, 0], [t, h * 0.5, d, w / 2 - t / 2, 0, 0]], cu));
      g.add(put(box(w, h * 0.16, d * 0.46, st), 0, h * 0.33, -d * 0.27));                // 蓋板只蓋一半
      // 鎖附的四顆彈簧螺絲：冷板是**壓**在晶片上的，壓力不夠熱就過不去
      const scr = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.8, rough: 0.3 });
      g.add(instOf(new T.CylinderGeometry(w * 0.035, w * 0.035, h * 0.9, 8), scr,
        gridXZ(2, 2, w * 0.88, d * 0.88, h * 0.1)));
      return g;
    }

    /* 冷板內部流道：一片一片鏟出來的**微鰭片**，水從鰭片之間流過。
       鰭片密度就是熱阻 —— 畫成一個空盒子，這張圖就沒有回答「冷板為什麼有貴賤之分」。*/
    function cpFin(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cu = K.mat(0.12, { color: K.css('--dg-cu-lit', '#c88a4e'), metal: 0.88, rough: 0.26 });
      const n = 22, at = [];
      for (let i = 0; i < n; i++) at.push([(-(n - 1) / 2 + i) * (w / n), 0, 0]);
      g.add(instOf(new T.BoxGeometry(w / n * 0.4, h, d * 0.86), cu, at));
      // 進出水的集流區：鰭片兩端各留一條沒有鰭片的走道，水才分得均勻
      g.add(mboxes([[w * 0.98, h * 0.2, d * 0.07, 0, -h * 0.38, -d * 0.45],
        [w * 0.98, h * 0.2, d * 0.07, 0, -h * 0.38, d * 0.45]], cu));
      return g;
    }

    /* 進出水口：**進水冷（藍）、出水熱（紅）**，兩個接口座 ＋ 各一小段管。
       冷熱是語意色（`--dg-cold`／`--dg-hot`），任何配色模式都不准蓋掉。*/
    function cpPort(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cold = K.mat(0, { color: K.css('--dg-cold', '#4ea8dc'), metal: 0.45, rough: 0.38 });
      const hot = K.mat(0, { color: K.css('--dg-hot', '#e8854a'), metal: 0.45, rough: 0.38 });
      const st = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.82, rough: 0.3 });
      [[-1, cold], [1, hot]].forEach(([s, m]) => {
        g.add(put(cyl(Math.min(w, d) * 0.3, h * 0.9, m, 14), 0, 0, s * d * 0.3));         // 管
        g.add(put(cyl(Math.min(w, d) * 0.42, h * 0.16, st, 14), 0, -h * 0.4, s * d * 0.3)); // 接口座
      });
      return g;
    }

    /* 分歧管（manifold）：供水、回水**各一根**，每一根有數個分支 ——
       多個冷板是**並聯**（各自從供水管拿水、各自回到回水管），不是一個接一個串下去。*/
    function lcManifold(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cold = K.mat(0, { color: K.css('--dg-cold', '#4ea8dc'), metal: 0.4, rough: 0.4 });
      const hot = K.mat(0, { color: K.css('--dg-hot', '#e8854a'), metal: 0.4, rough: 0.4 });
      const r = Math.min(w, d) * 0.16;
      [[-1, cold], [1, hot]].forEach(([s, m]) => {
        g.add(put(cyl(r, h, m, 14), s * w * 0.28, 0, 0));                                 // 主管（直立）
        const br = [];
        for (let i = 0; i < 4; i++) br.push([s * w * 0.28, (-1.5 + i) * h * 0.22, d * 0.26, Math.PI / 2, 0, 0]);
        g.add(instOf(new T.CylinderGeometry(r * 0.5, r * 0.5, d * 0.52, 10), m, br));      // 分支（並聯）
      });
      // 兩根管之間的固定夾：它們是兩條獨立的管路，不是同一條
      g.add(instOf(new T.BoxGeometry(w * 0.7, h * 0.05, d * 0.14),
        K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.8, rough: 0.4 }),
        [[0, h * 0.4, 0], [0, -h * 0.4, 0]]));
      return g;
    }

    /* 板式熱交換器（PHE，在 CDU 裡）：一疊**交錯**的板片。
       ★ 這張圖最致命的錯就是把兩個迴路畫成一條管 —— 所以這一顆刻意畫成
         「一片冷、一片熱交錯疊起來」：兩邊的水各走各的縫，只有熱過得去，水過不去。*/
    function lcPhe(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cold = K.mat(0, { color: K.css('--dg-cold', '#4ea8dc'), metal: 0.5, rough: 0.34 });
      const hot = K.mat(0, { color: K.css('--dg-hot', '#e8854a'), metal: 0.5, rough: 0.34 });
      const st = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.84, rough: 0.3 });
      const n = 9, pit = h / (n + 1), c = [], t = [];
      for (let i = 0; i < n; i++) {
        const y = -h / 2 + pit * (i + 1);
        (i % 2 ? t : c).push([0, y, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.9, pit * 0.42, d * 0.9), cold, c));   // 一次側（設施水）走的縫
      g.add(instOf(new T.BoxGeometry(w * 0.9, pit * 0.42, d * 0.9), hot, t));    // 二次側（機櫃水）走的縫
      [-1, 1].forEach(s => g.add(put(box(w, pit * 0.7, d, st), 0, s * h * 0.47, 0)));   // 上下端板
      return g;
    }

    /* ---------------------------------------------------------------- 氣冷：風扇、風扇牆與散熱模組
       規格書 docs/diagram_specs/air_cooling.md §3-B（風扇本體，由內到外）：
         軸／軸承 → 馬達（定子在內、轉子磁鐵在輪轂內壁）→ 輪轂 → 扇葉（有傾角）→ 扇框。
       硬規則：**扇葉一定從輪轂長出來**（不可以懸空）、**馬達一定在輪轂裡**（不在扇框上）、
               **軸承一定在軸與輪轂之間**。
       3D 這張把一顆風扇**沿轉軸**拆開 —— 那正是「轉一圈能多理解一件事」的地方：
       2D 剖面只看得到切開的那一刀，看不到六個件是怎麼套在同一根軸上的。
       轉軸一律取 z（朝鏡頭），所有零件的爆炸位移都沿 z 走，拆開仍看得出誰跟誰是一組。*/

    /* 扇框：四角有鎖孔的方框、中間一個圓孔（風從這裡過）。
       ExtrudeGeometry 的 hole 挖出來的才是風扇框的樣子，四條邊圍起來的不是。*/
    function fanFrame(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2;
      const fm = K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), metal: 0.45, rough: 0.55 });
      g.add(rbox(w, h, d * 0.86, Math.min(w, h) * 0.09, fm, r * 0.82));
      // 四角鎖孔：風扇是**鎖**在機殼上的，這是它跟一顆自由葉輪的差別
      const hl = K.mat(0, { color: K.css('--dg-edge', '#0e1526'), rough: 0.92, metal: 0.04 });
      const at = [];
      [-1, 1].forEach(sx => [-1, 1].forEach(sy => at.push([sx * w * 0.42, sy * h * 0.42, 0, Math.PI / 2, 0, 0])));
      g.add(instOf(new T.CylinderGeometry(w * 0.035, w * 0.035, d, 8, 1, true), hl, at));
      // 四根支撐臂：馬達是靠這幾根撐在框中央的（不然輪轂是浮著的）
      g.add(instOf(new T.BoxGeometry(r * 1.4, h * 0.05, d * 0.12), K.mat(-0.15, { metal: 0.4, rough: 0.6 }),
        [0, 1, 2, 3].map(i => [0, 0, -d * 0.3, 0, 0, i * Math.PI / 4])));
      return g;
    }

    /* 轉子的扇葉：七片有**攻角**的葉片，從輪轂長出來。
       `rev` ＝ 反轉雙轉子的第二組 —— 葉片的攻角與旋轉方向都跟前轉子相反
       （兩組同向就不是「反轉」，那只是兩顆風扇疊在一起）。*/
    function fanRotor(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2;
      const rev = !!p.rev, sg = rev ? -1 : 1;
      const rotor = new T.Group();
      const bm = K.mat(rev ? -0.12 : 0, { color: K.css('--dg-m-blade', '#2E3A45'), rough: 0.6, metal: 0.2 });
      for (let i = 0; i < 7; i++) {
        const a = i * Math.PI * 2 / 7;
        const b = box(r * 0.72, r * 0.4, d * 0.18, bm);
        b.position.set(Math.cos(a) * r * 0.56, Math.sin(a) * r * 0.56, 0);
        b.rotation.z = a + Math.PI / 2;
        b.rotation.y = 0.46 * sg;                       // 攻角：平的看起來像葉輪玩具
        rotor.add(b);
      }
      // 葉根：葉片是**從輪轂長出來**的，所以根部要有一圈實體把它們連起來
      const root = cyl(r * 0.3, d * 0.6, K.mat(-0.2, { metal: 0.3, rough: 0.6 }), 16);
      root.rotation.x = Math.PI / 2; rotor.add(root);
      rotor.userData.spin = { axis: 'z', speed: rev ? -2.1 : 2.4 };
      g.add(rotor);
      return g;
    }

    /* 輪轂（hub）：一個杯狀件 —— 開口朝後，馬達與軸承**裝在它裡面**。
       畫成實心圓柱就沒地方放馬達，那正是「馬達在輪轂裡」這條硬規則會被畫錯的原因。*/
    function fanHub(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2;
      const hm = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.72, rough: 0.38 });
      const wall = twoSided(K, K.mat(-0.06, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.7, rough: 0.4 }));
      const cap = put(cyl(r, d * 0.14, hm, 20), 0, 0, d * 0.42);
      cap.rotation.x = Math.PI / 2; g.add(cap);                                         // 前蓋
      const side = put(new T.Mesh(new T.CylinderGeometry(r, r, d * 0.84, 20, 1, true), wall), 0, 0, 0);
      side.rotation.x = Math.PI / 2; g.add(side);                                        // 杯壁（開口朝後）
      // 轉子磁鐵：貼在**輪轂內壁**上的一圈（外轉子馬達就是這樣裝的）
      const mag = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.58, metal: 0.3 });
      const at = [];
      for (let i = 0; i < 8; i++) at.push([Math.cos(i * Math.PI / 4) * r * 0.86, Math.sin(i * Math.PI / 4) * r * 0.86,
        -d * 0.08, 0, 0, i * Math.PI / 4]);
      g.add(instOf(new T.BoxGeometry(r * 0.2, r * 0.5, d * 0.5), mag, at));
      return g;
    }

    /* 馬達（定子）：鐵芯的**齒**＋ 纏在齒上的銅線圈 ＋ 底下的驅動板。
       定子在內、轉子磁鐵在輪轂內壁 —— 兩者之間那一圈空隙就是氣隙。
       畫成一個圓柱就看不出它是馬達，也看不出它為什麼要四線（電源／地／轉速／PWM）。*/
    function fanMotor(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2;
      const fe = K.mat(0, { color: K.css('--dg-steel-2', '#6b7683'), metal: 0.8, rough: 0.34 });
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.82, rough: 0.3 });
      const teeth = [], coils = [];
      for (let i = 0; i < 6; i++) {
        const a = i * Math.PI / 3;
        teeth.push([Math.cos(a) * r * 0.55, Math.sin(a) * r * 0.55, 0, 0, 0, a]);
        coils.push([Math.cos(a) * r * 0.55, Math.sin(a) * r * 0.55, 0, 0, 0, a]);
      }
      g.add(instOf(new T.BoxGeometry(r * 0.8, r * 0.28, d * 0.6), fe, teeth));           // 鐵芯的齒
      g.add(instOf(new T.BoxGeometry(r * 0.42, r * 0.52, d * 0.68), cu, coils));         // 繞在齒上的線圈
      const yoke = put(cyl(r * 0.34, d * 0.62, fe, 16), 0, 0, 0); yoke.rotation.x = Math.PI / 2; g.add(yoke);
      // 驅動板：霍爾元件在這上面，轉速回授就是從這裡出去的
      g.add(put(box(r * 1.7, r * 1.7, d * 0.1, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 })), 0, 0, -d * 0.4));
      return g;
    }

    /* 軸承：**在軸與輪轂之間**（不在扇框上）。這裡畫的是滾珠型 ——
       看得到鋼珠就是滾珠軸承；含油軸承是軸與襯套直接接觸、沒有珠。
       四種軸承的辨識特徵不准互換（規格書 §3-B），所以這一顆一定要看得到珠。*/
    function fanBearing(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, h) / 2;
      const st = K.mat(0, { color: K.css('--dg-steel', '#9aa6b4'), metal: 0.86, rough: 0.24 });
      const sh = K.mat(0.18, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.88, rough: 0.2 });
      const shaft = put(cyl(r * 0.32, d, sh, 14), 0, 0, 0); shaft.rotation.x = Math.PI / 2; g.add(shaft);  // 軸
      [-1, 1].forEach(s => {
        const ring = put(new T.Mesh(new T.CylinderGeometry(r, r * 0.92, d * 0.2, 18, 1, true),
          twoSided(K, st)), 0, 0, s * d * 0.3);
        ring.rotation.x = Math.PI / 2; g.add(ring);                                      // 外環
        const at = [];
        for (let i = 0; i < 8; i++) at.push([Math.cos(i * Math.PI / 4) * r * 0.64, Math.sin(i * Math.PI / 4) * r * 0.64, s * d * 0.3]);
        g.add(instOf(new T.SphereGeometry(r * 0.22, 8, 6), st, at));                     // 鋼珠（看得到才是滾珠軸承）
      });
      return g;
    }

    /* 四線接頭：電源／地／轉速回授／PWM。
       為什麼值得畫：**四線**就是「伺服器風扇會被主機控速、也會回報轉速」的證據 ——
       兩線的是家用風扇，那是這張圖 §「伺服器風扇跟家用風扇差在哪」的答案之一。*/
    function fanWire(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const hs = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.7, metal: 0.1 });
      g.add(put(box(w * 0.5, h, d * 0.3, hs), w * 0.24, 0, 0));                          // 接頭外殼
      const cols = ['--dg-el', '--dg-edge', '--dg-fl-sig', '--dg-fl-pwr'];
      cols.forEach((cv, i) => {
        const m = K.mat(0, { color: K.css(cv, '#4e5866'), rough: 0.8, metal: 0.08 });
        const o = (i - 1.5) * h * 0.2;
        const curve = new T.CatmullRomCurve3([
          new T.Vector3(0, o, -d * 0.4), new T.Vector3(-w * 0.2, o * 0.6, -d * 0.1),
          new T.Vector3(-w * 0.34, o * 0.4, d * 0.2), new T.Vector3(-w * 0.5, o * 0.3, d * 0.45)]);
        g.add(new T.Mesh(new T.TubeGeometry(curve, 12, h * 0.07, 5, false), m));
      });
      return g;
    }

    /* 風扇牆（fan wall）：一整排風扇裝在同一個框上，而且**多一顆**（N+1）。
       每一顆都看得到框、輪轂與葉片 —— 一排空圓圈不是風扇牆。*/
    function fanWall(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const n = 4, cw = w / n;
      const r = Math.min(cw, h) * 0.44;
      const fm = K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), metal: 0.45, rough: 0.55 });
      g.add(put(box(w, h, d * 0.2, fm), 0, 0, -d * 0.4));                                // 背板
      const hub = K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.72, rough: 0.4 });
      const bm = K.mat(0, { color: K.css('--dg-m-blade', '#2E3A45'), rough: 0.6, metal: 0.2 });
      const rings = [], hubs = [], blades = [];
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * cw;
        rings.push([x, 0, 0]);
        hubs.push([x, 0, 0, Math.PI / 2, 0, 0]);
        for (let j = 0; j < 7; j++) {
          const a = j * Math.PI * 2 / 7;
          blades.push([x + Math.cos(a) * r * 0.58, Math.sin(a) * r * 0.58, 0, 0, 0.44, a + Math.PI / 2]);
        }
      }
      g.add(instOf(new T.TorusGeometry(r, r * 0.09, 6, 16), fm, rings));                 // 每一顆的框
      g.add(instOf(new T.CylinderGeometry(r * 0.28, r * 0.28, d * 0.5, 12), hub, hubs));
      /* C6：風扇牆的葉片**真的在轉**。
         它是一個 InstancedMesh（4 顆風扇 × 7 片 ＝ 28 個實例、1 個 draw call），
         所以不能像單顆風扇那樣「轉一個 Group」—— 改成每幀重算 instanceMatrix。
         28 次矩陣組合 × 30fps ＝ 840 次／秒，可以忽略；
         換成 4 個 Group 會多 3 個 draw call，而且葉片的幾何要複製 4 份。*/
      const bi = instOf(new T.BoxGeometry(r * 0.66, r * 0.34, d * 0.14), bm, blades);
      bi.userData.ispin = { speed: 2.1, t: 0, items: blades.map((b, i) => ({
        cx: (-(n - 1) / 2 + Math.floor(i / 7)) * cw, cz: 0, r: r * 0.58,
        a0: (i % 7) * Math.PI * 2 / 7, ry: 0.44 })) };
      g.add(bi);
      return g;
    }

    /* 導風罩（air shroud／duct）：把氣流圍成一條路的塑膠件 ——
       上面一片頂蓋、兩側各一片、前後開口。它本身不散熱，但沒有它風會從旁邊溜掉。*/
    function fanShroud(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const pl = twoSided(K, K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), metal: 0.16, rough: 0.66, op: 0.72 }));
      const t = h * 0.07;
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0]], pl));
      // 收口：出風那一端收窄，氣流才會被逼著穿過鰭片而不是繞過去
      g.add(mboxes([[w * 0.2, h * 0.9, t * 1.4, -w * 0.38, 0, -d / 2 + t],
        [w * 0.2, h * 0.9, t * 1.4, w * 0.38, 0, -d / 2 + t]], pl));
      return g;
    }

    /* ---------------------------------------------------------------- 網通：交換器板卡 ＋ 光模組 ＋ CPO
       規格書 docs/diagram_specs/switch_board.md §3-C 的硬規則：
         **VRM 一定緊鄰 ASIC**（電流大、壓降走不遠），供電線明顯比訊號線粗。
       §2「不要出現的東西」：**DIMM 插槽陣列、PCIe 金手指插槽陣列、CPU 插座卡榫**——
       那是伺服器主機板；交換器板上只有一小塊管理用處理器。
       所以主板**不能**沿用 `pcb`（那一支畫了三條插槽），這裡另寫一支。*/

    /* 交換器主板（MLB）：深色防焊 ＋ 高速扇出走線 ＋ 晶片底下的密集過孔陣列 ＋ 邊緣露出的一疊層。
       沒有插槽、沒有記憶體插座 —— 那正是它跟伺服器主機板的差別。*/
    function swBoard(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.22, { rough: 0.72, metal: 0.06 })));
      g.add(aoPad(K, w, d, -h / 2 - 1.2));
      // 邊緣露出來的那一疊：38–48 層是很多片薄板壓起來的，切面才看得到
      const lam = K.mat(0.1, { color: K.css('--dg-pp', '#8a8355'), rough: 0.78, metal: 0.05 });
      const ly = [];
      for (let i = 0; i < 6; i++) ly.push([w * 0.999, h * 0.06, d * 0.06, 0, (-2.5 + i) * h * 0.13, -d / 2 + d * 0.03]);
      g.add(mboxes(ly, lam));
      // 高速扇出：從晶片底下往前面板方向走的蛇行等長差動對
      const tl = traceLayer(K, w * 0.9, d * 0.7, h * 0.56, { pairs: 5, cycles: 6, dir: 1 });
      g.add(tl.group); g.userData.flows = tl.flows;
      // 晶片底下的過孔陣列：訊號要從外層沉到內層，密度就是這裡
      g.add(put(padField(K, w * 0.24, d * 0.3, h * 0.53, 6, 6), 0, 0, -d * 0.1));
      const cu = K.mat(0, { color: K.css('--dg-cu', '#b0743a'), metal: 0.78, rough: 0.3 });
      g.add(instOf(new T.CylinderGeometry(w * 0.004, w * 0.004, h * 1.1, 6, 1, true), cu,
        gridXZ(9, 7, w * 0.028, d * 0.04, 0).map(a => [a[0], 0, a[2] - d * 0.1])));
      return g;
    }

    /* 交換器晶片（switch ASIC）：**板上最大的單一元件** ——
       有機基板 ＋ 底下一整片球柵陣列 ＋ 上面的矽蓋板。
       球柵陣列是它「怎麼接到板子」的答案，也是它跟一顆普通 IC 差一個量級的地方。*/
    function swAsic(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.3, d, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.06 })), 0, -h * 0.3, 0));
      g.add(put(box(w * 0.66, h * 0.36, d * 0.66, K.mat(0, { color: K.css('--dg-m-die', '#1E2E52'), metal: 0.4, rough: 0.4 })), 0, h * 0.02, 0));
      g.add(put(box(w * 0.78, h * 0.26, d * 0.78, K.mat(0, { color: K.css('--dg-m-hs', '#CBD5DE'), metal: 0.82, rough: 0.28 })), 0, h * 0.32, 0));  // 蓋板
      // 球柵陣列：整片、密密麻麻 —— 三顆三顆的看起來像腳墊
      g.add(put(ballGrid(K, w * 0.08, w * 0.028, 9, 0, [6, 4]), 0, -h * 0.5, 0));
      return g;
    }

    /* 前面板光模組籠架（cage）：**上下兩列**金屬籠佔滿前面板。
       籠子是為了擋 EMI 與導熱才存在的，而排數 × 列數就是這台機器的埠數 ——
       畫成一片平板就看不出「64 個埠」這件事。*/
    function swCage(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.84, rough: 0.34 });
      const dark = K.mat(-0.6, { rough: 0.9, metal: 0.06 });
      const n = 12, cw = w / n;
      const cells = [], holes = [];
      for (let i = 0; i < n; i++) for (let j = -1; j <= 1; j += 2) {
        const x = (-(n - 1) / 2 + i) * cw, y = j * h * 0.26;
        cells.push([x, y, 0]);
        holes.push([x, y, d * 0.12]);
      }
      // 一格籠子＝四片鈑金圍成的框（用薄壁盒子的外殼表示），開口朝前
      g.add(instOf(new T.BoxGeometry(cw * 0.86, h * 0.44, d * 0.9), st, cells));
      g.add(instOf(new T.BoxGeometry(cw * 0.66, h * 0.3, d * 0.72), dark, holes));     // 插槽開口（暗）
      // 籠架上的散熱鰭片：800G 模組的熱要靠籠子帶走，所以籠背上有鰭片
      const fin = [];
      for (let i = 0; i < n * 2; i++) fin.push([(-(n * 2 - 1) / 2 + i) * (w / (n * 2)), h * 0.5, -d * 0.1]);
      g.add(instOf(new T.BoxGeometry(w / (n * 2) * 0.3, h * 0.16, d * 0.7), st, fin));
      return g;
    }

    /* 可插拔光模組（OSFP／QSFP-DD800）：外殼 ＋ 拉環 ＋ 前端光纖接口 ＋ 內部四顆主要晶片。
       ★ 光電轉換發生在**模組裡面**，不在板子上 —— 所以這一顆一定要看得到裡面有東西：
         DSP（最大也最耗電）、驅動 IC、雷射晶粒、TIA。*/
    function swModule(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0.05, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.84, rough: 0.32 });
      const t = h * 0.14;
      // 上蓋掀開一半：不掀開就只是一個金屬盒子，光模組真正的內容看不到
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, -d * 0.22], [w, t, d, 0, -h / 2 + t / 2, 0],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0]], st));
      g.add(put(box(w * 0.2, h * 0.36, d * 0.36, K.mat(0, { color: K.css('--dg-m-pwr', '#E08A3C'), rough: 0.6, metal: 0.2 })), 0, h * 0.34, d * 0.56));  // 拉環
      const brd = K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 });
      g.add(put(box(w * 0.8, h * 0.1, d * 0.86, brd), 0, -h * 0.2, 0));
      const chip = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.52, metal: 0.22 });
      // 四顆一字排開，DSP 最大（它就是可插拔模組耗電的主因，也是 CPO 想拿掉的那一顆）
      g.add(mboxes([[w * 0.56, h * 0.26, d * 0.2, 0, -h * 0.02, -d * 0.24],
        [w * 0.4, h * 0.18, d * 0.1, 0, -h * 0.06, -d * 0.02],
        [w * 0.3, h * 0.16, d * 0.08, -w * 0.12, -h * 0.07, d * 0.12],
        [w * 0.24, h * 0.16, d * 0.08, w * 0.16, -h * 0.07, d * 0.12]], chip));
      // 前端的兩個光纖接口
      g.add(instOf(new T.CylinderGeometry(w * 0.09, w * 0.09, d * 0.16, 10),
        K.mat(0, { color: K.css('--dg-fl-opt', '#22E5C8'), glow: 0.5, rough: 0.5, metal: 0.1 }),
        [[-w * 0.17, -h * 0.06, d * 0.5, Math.PI / 2, 0, 0], [w * 0.17, -h * 0.06, d * 0.5, Math.PI / 2, 0, 0]]));
      return g;
    }

    /* 金手指：光模組**唯一**的電接點 —— 成排、鍍金、前緣倒角。
       它在模組的後端（插進籠子的那一頭），不是在光纖那一頭。*/
    function swGold(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.5, d, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.05 })), 0, 0, 0));
      g.add(fingers(K, w * 0.92, h * 0.3, d * 0.8, 9, h * 0.3, 0));
      g.add(fingers(K, w * 0.92, h * 0.3, d * 0.8, 9, -h * 0.3, 0));
      return g;
    }

    /* 共同封裝光學（CPO）：光引擎搬到**跟 ASIC 同一片基板上**、環繞在它四周，
       光纖直接從基板邊緣拉出去 —— 前面板就不必再插 64 顆會發熱的模組。
       ★ 這一顆是「另一半答案」的主角：它跟可插拔模組是**兩種做法**，不是同一條路。*/
    function swCpo(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const sub = K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.06 });
      g.add(put(box(w, h * 0.26, d, sub), 0, -h * 0.34, 0));                          // 共用的那一片基板
      const eng = K.mat(0, { color: K.css('--dg-m-die', '#1E2E52'), metal: 0.42, rough: 0.4 });
      const at = [];
      for (let i = 0; i < 3; i++) {
        const t = (-1 + i) * w * 0.3;
        at.push([t, 0, -d * 0.38]); at.push([t, 0, d * 0.38]);
        at.push([-w * 0.38, 0, t]); at.push([w * 0.38, 0, t]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.16, h * 0.4, d * 0.16), eng, at));          // 8 顆光引擎環繞
      // 光纖：直接從基板邊緣拉出去（這就是 CPO 省掉前面板模組的地方）
      const fib = K.mat(0, { color: K.css('--dg-fl-opt', '#22E5C8'), glow: 0.35, rough: 0.55, metal: 0.08 });
      [-1, 1].forEach(s => {
        const curve = new T.CatmullRomCurve3([
          new T.Vector3(s * w * 0.42, 0, 0), new T.Vector3(s * w * 0.72, h * 0.2, d * 0.2),
          new T.Vector3(s * w * 0.92, h * 0.1, d * 0.6), new T.Vector3(s * w * 0.98, -h * 0.1, d * 1.0)]);
        g.add(new T.Mesh(new T.TubeGeometry(curve, 14, h * 0.07, 5, false), fib));
      });
      return g;
    }


    /* ================================================================ 一般電子鏈的零件字彙（2026-09-23）
       一般電子鏈原本有六張剖析圖是 `scene: null`（面板／工業自動化／被動保護／鋁電容／被動 RLC）。
       跟半導體鏈那四張（#247）同一個判準：推翻「不做真 3D」的是**那個理由漏掉的另一半**，
       不是那個理由本身 —— 六件只有立體才成立的事：
         · 一片面板是十三層薄膜疊出來的，而「兩片偏光板在兩片玻璃的**外側**、光從**側邊**進來」
           這兩件事在一張剖面上只是兩條線；把整疊垂直拉開轉一圈，順序與內外就是一眼的事
         · 一根軸是「馬達 → 聯軸器 → 軸承座 → 螺桿＋螺帽 → 滑軌＋滑塊」串起來的**一串**，
           沿著軸拆開才看得出誰接誰；螺帽剖開才看得到鋼珠是一個**閉合的迴圈**
         · 四顆保護元件的差別全部在「裡面長什麼樣」（晶粒與晶界／高分子與碳黑鏈／PN 與空乏區），
           並排半剖轉一圈，四種物理機制一次比得出來
         · 鋁電解電容是一顆**捲**出來的東西：整顆縱剖看得到捲芯塞在鋁殼裡，
           捲芯再把四層帶拉出來，才看得懂「四層一起捲」跟「一層一層疊」不是同一件事
         · 電感的繞組埋在磁粉裡、電阻的雷射修整溝壓在玻璃層底下、石英片懸空在密封腔裡 ——
           三件都是「被蓋住的識別特徵」，半剖是唯一看得到它們的方式
       共同規矩（#244）：顏色一律走 FAMILY_TOKENS 與 `--dg-*`（不寫死色值）、一張圖一個主色、
       層與層靠明暗分、陣列類一律 InstancedMesh、不加任何自體發光（Andy：「不是電競 RGB」）。*/

    /* 沿 x 軸躺著的圓柱。傳動件（馬達軸、螺桿、軸承）幾乎都是躺著的，
       而 cyl() 給的是站著的（three.js 的 CylinderGeometry 軸在 y）。*/
    function cylX(r, l, m, seg) { const c = cyl(r, l, m, seg || 16); c.rotation.z = Math.PI / 2; return c; }

    /* 縱剖用的半管：外徑 ro、內徑 ri（ri = 0 就是實心半柱）、長 len，**保留 local y > 0 那一半**。
       為什麼不沿用 #247 的 halfSlab：那一支切的是方塊，切圓筒會變成「一個被削掉一邊的罐頭」。
       電容的鋁殼、螺帽、軸承座要的是「壁真的有厚度」——
       看得到壁厚才看得出「裡面裝著東西」，實心圓柱看不出來。
       ⚠ 保留哪一半是固定的（local y > 0），轉向由下面兩支包起來，
         兩支都保證最後切掉的是**世界座標的 z > 0**（跟全站其他剖面同一個切面，
         使用者不必在兩張圖之間重新學一次「哪一面是切面」）。*/
    function halfBore(ro, ri, len) {
      const s = new T.Shape();
      s.moveTo(-ro, 0);
      s.absarc(0, 0, ro, Math.PI, 0, true);
      if (ri > 0) { s.lineTo(ri, 0); s.absarc(0, 0, ri, 0, Math.PI, false); }
      s.lineTo(-ro, 0);
      const gg = new T.ExtrudeGeometry(s, { depth: len, bevelEnabled: false, curveSegments: 14 });
      gg.translate(0, 0, -len / 2);
      return gg;
    }
    // 軸沿 y（站著的圓筒：電容、固態電容、封口、防爆閥）
    function halfTubeY(ro, ri, len, m) { const x = new T.Mesh(halfBore(ro, ri, len), m); x.rotateX(-Math.PI / 2); return x; }
    // 軸沿 x（躺著的圓筒：螺帽、軸承座）。先把擠出方向轉到 x，再繞自己的軸轉 90°，切面才落在 z = 0
    function halfTubeX(ro, ri, len, m) {
      const x = new T.Mesh(halfBore(ro, ri, len), m);
      x.rotateY(Math.PI / 2); x.rotateZ(-Math.PI / 2);
      return x;
    }

    /* ---------------------------------------------------------------- 面板：TFT-LCD 十三層
       整疊沿 y 垂直爆炸。每一層都是一張**薄片**，所以每一支都要有「它是一張片」的識別特徵
       （定位耳、網點、稜線、格線、色阻），不然十三層疊起來就是十三塊一樣的板子。*/

    /* 背板與膠框：整個背光模組的底。鈑金盤 ＋ 壓在上緣的一圈塑膠膠框。
       ★ 膠框不是裝飾：整疊光學膜片就是靠它壓住定位的，少了它整疊會鬆掉。*/
    function pnFrame(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const t = h * 0.3;
      g.add(mboxes([[w, t, d, 0, -h / 2 + t / 2, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2], [w, h, t, 0, 0, d / 2 - t / 2],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0]], K.mat(-0.1, { rough: 0.4 })));
      const b = Math.max(0.05, w * 0.022);
      g.add(mboxes([[w, b, b * 2, 0, h / 2, -d / 2 + b], [w, b, b * 2, 0, h / 2, d / 2 - b],
        [b * 2, b, d, -w / 2 + b, h / 2, 0], [b * 2, b, d, w / 2 - b, h / 2, 0]],
        K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.66, metal: 0.1 })));
      return g;
    }

    /* 光學膜片（反射片／擴散片共用）：一張薄片 ＋ 四邊突出來的定位耳。
       定位耳就是「這是一張膜」而不是一塊板的識別特徵 —— 組裝時它卡在膠框上。*/
    function pnFilm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(p.k == null ? 0.42 : p.k, { rough: p.rough == null ? 0.72 : p.rough, metal: 0.04 })));
      const e = Math.max(0.05, w * 0.03);
      g.add(mboxes([[e * 2, h, e, -w * 0.28, 0, d / 2 + e / 2], [e * 2, h, e, w * 0.28, 0, d / 2 + e / 2],
        [e, h, e * 2, -w / 2 - e / 2, 0, 0], [e, h, e * 2, w / 2 + e / 2, 0, 0]],
        K.mat((p.k == null ? 0.42 : p.k) - 0.3, { rough: 0.82 })));
      return g;
    }

    /* 導光板：★ 底面的網點是它唯一的識別特徵 ——
       離入光側（−x）越遠、點越大越密。沒有這個梯度的話，光會全部從靠近 LED 那一頭漏出去，
       整片就是一邊亮一邊暗。畫成一塊光板子＝畫的是壓克力板，不是導光板。*/
    function pnLgp(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0.2, { rough: 0.12, metal: 0.02, op: 0.55 })));
      const dots = [], nx = 12, nz = 8;
      for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
        const s = 0.35 + (i / (nx - 1)) * 1.15;
        dots.push([(-0.5 + (i + 0.5) / nx) * w * 0.94, -h / 2 - h * 0.04,
          (-0.5 + (j + 0.5) / nz) * d * 0.94, 0, 0, 0, s, 1, s]);
      }
      g.add(instOf(new T.CylinderGeometry(w * 0.008, w * 0.008, h * 0.12, 6),
        K.mat(0.86, { rough: 0.92, metal: 0.02 }), dots));
      return g;
    }

    /* LED 燈條：★ 一排 LED 朝著導光板的**側面**（+x），不是朝上 ——
       朝上就是直下式背光，那是另一種結構（本圖畫的是側光式）。*/
    function pnLedBar(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w * 0.5, h, d, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.06 })));
      const n = 10, at = [];
      for (let i = 0; i < n; i++) at.push([w * 0.28, 0, (-(n - 1) / 2 + i) * (d / n)]);
      g.add(instOf(new T.BoxGeometry(w * 0.4, h * 0.5, d / n * 0.52),
        K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.42, metal: 0.05 }), at));
      // 發光面：只有這一小片准亮（#244 一-6 發光克制 —— 指示燈與光源類才准 led）
      g.add(instOf(new T.BoxGeometry(w * 0.06, h * 0.32, d / n * 0.34),
        K.mat(0, { color: K.css('--dg-l-key', '#FFF4E6'), led: true, rough: 0.3, metal: 0.02 }),
        at.map(a => [a[0] + w * 0.22, 0, a[2]])));
      return g;
    }

    /* 稜鏡片 ×2：★ 兩片的稜線必須**正交** —— 一片只把光收一個方向，
       兩片同向就少收了另一個方向，正面亮度提不上去。*/
    function pnPrism(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const m1 = K.mat(0.24, { rough: 0.16, metal: 0.02, op: 0.72 });
      const m2 = K.mat(0.48, { rough: 0.16, metal: 0.02, op: 0.72 });
      const a = h * 0.26;
      g.add(put(box(w, h * 0.16, d, m1), 0, -h * 0.34, 0));
      const lo = [], n = 24;
      for (let i = 0; i < n; i++) lo.push([(-(n - 1) / 2 + i) * (w / n), -h * 0.24, 0, 0, 0, Math.PI / 4]);
      g.add(instOf(new T.BoxGeometry(a, a, d), m1, lo));
      g.add(put(box(w, h * 0.16, d, m2), 0, h * 0.08, 0));
      const up = [], nz = 16;
      for (let i = 0; i < nz; i++) up.push([0, h * 0.18, (-(nz - 1) / 2 + i) * (d / nz), Math.PI / 4, 0, 0]);
      g.add(instOf(new T.BoxGeometry(w, a, a), m2, up));
      return g;
    }

    /* 偏光板：★ 兩片的透光軸**正交**（下片沿 x、上片沿 z，p.cross 決定）。
       兩片同向＝光全部通過，那片面板就永遠是亮的、液晶轉不轉都沒有用 ——
       「為什麼非得要兩片偏光板」這個問題的答案就是這一對方向。*/
    function pnPol(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.18, { rough: 0.54, metal: 0.05 })));
      const n = 20, at = [];
      const geo = p.cross ? new T.BoxGeometry(w * 0.05, h * 0.5, d * 0.94)
        : new T.BoxGeometry(w * 0.94, h * 0.5, d * 0.05);
      for (let i = 0; i < n; i++) {
        const u = (-(n - 1) / 2 + i);
        at.push(p.cross ? [u * (w / n), h * 0.4, 0] : [0, h * 0.4, u * (d / n)]);
      }
      g.add(instOf(geo, K.mat(0.5, { rough: 0.36, metal: 0.12 }), at));
      return g;
    }

    /* 玻璃基板：一片玻璃在畫面上如果只是一塊霧，它就跟旁邊的膜片分不開。
       切過的那一圈邊才是玻璃的識別特徵（它會反白光），所以上下緣各補一條亮邊。*/
    function pnGlass(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0.34, { rough: 0.08, metal: 0.02, op: 0.42 })));
      const t = h * 0.14;
      g.add(mboxes([[w, t, d * 1.004, 0, h / 2 - t / 2, 0], [w, t, d * 1.004, 0, -h / 2 + t / 2, 0]],
        K.mat(0.82, { rough: 0.05, metal: 0.06, op: 0.75 })));
      return g;
    }

    /* TFT 陣列層：★ 橫的閘極線選一列、縱的資料線送電壓，兩者**正交成格**，
       每一格角落一顆薄膜電晶體開關那一個子像素的像素電極。
       少掉其中一組線就不是「陣列」，只是一堆電極。*/
    function pnTft(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const nx = 10, nz = 7;
      const cu = K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.86, rough: 0.3 });
      const lw = Math.max(0.05, w * 0.007);
      const gate = [], data = [], px = [], tft = [];
      for (let j = 0; j < nz; j++) gate.push([0, h * 0.2, (-(nz - 1) / 2 + j) * (d / nz)]);
      for (let i = 0; i < nx; i++) data.push([(-(nx - 1) / 2 + i) * (w / nx), h * 0.34, 0]);
      g.add(instOf(new T.BoxGeometry(w * 0.96, h * 0.3, lw), cu, gate));
      g.add(instOf(new T.BoxGeometry(lw, h * 0.3, d * 0.96), cu, data));
      for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
        const x = (-(nx - 1) / 2 + i + 0.5) * (w / nx), z = (-(nz - 1) / 2 + j + 0.5) * (d / nz);
        px.push([x, -h * 0.1, z]);
        tft.push([x - w / nx * 0.36, h * 0.24, z - d / nz * 0.36]);
      }
      g.add(instOf(new T.BoxGeometry(w / nx * 0.74, h * 0.16, d / nz * 0.74),
        K.mat(0.55, { rough: 0.3, metal: 0.3 }), px));
      g.add(instOf(new T.BoxGeometry(w / nx * 0.2, h * 0.5, d / nz * 0.2),
        K.mat(-0.42, { rough: 0.5, metal: 0.2 }), tft));
      return g;
    }

    /* 液晶層：★ 液晶靠「轉向」控制光，不是靠自己發光。
       左半躺平（不加電）、右半立起來（加電）—— 畫成一片均勻的膠就把整張圖的機制畫掉了。
       周邊一圈封框膠把液晶封住，中間幾根光阻間隙物撐住盒厚（盒厚是被撐出來的，不是靠運氣）。*/
    function pnLc(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const b = Math.max(0.05, w * 0.02);
      g.add(mboxes([[w, h, b, 0, 0, -d / 2 + b / 2], [w, h, b, 0, 0, d / 2 - b / 2],
        [b, h, d, -w / 2 + b / 2, 0, 0], [b, h, d, w / 2 - b / 2, 0, 0]],
        K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.72, metal: 0.05 })));
      const at = [], nx = 12, nz = 8;
      for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
        const x = (-(nx - 1) / 2 + i + 0.5) * (w * 0.86 / nx), z = (-(nz - 1) / 2 + j + 0.5) * (d * 0.86 / nz);
        at.push([x, 0, z, 0, 0, x < 0 ? Math.PI / 2 : 0]);
      }
      g.add(instOf(new T.CylinderGeometry(h * 0.055, h * 0.055, h * 0.62, 5),
        K.mat(0.3, { rough: 0.3, metal: 0.1, op: 0.85 }), at));
      g.add(instOf(new T.CylinderGeometry(w * 0.006, w * 0.009, h, 6),
        K.mat(-0.3, { rough: 0.6, metal: 0.04 }), gridXZ(4, 3, w * 0.22, d * 0.28, 0)));
      return g;
    }

    /* 彩色濾光片：★ R／G／B 是三個**水平並排**的子像素，不是上下疊三層 ——
       疊三層就是把光濾光了，什麼都看不到。黑色矩陣把每一格框起來擋住串色。
       顏色本身就是這個零件的身分，所以這三個色是全圖唯一刻意的色相差異。*/
    function pnCf(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const nx = 11, nz = 7;
      const cw = w * 0.92 / nx, cd = d * 0.92 / nz;
      [K.css('--dg-fl-hot', '#FF4D5E'), K.css('--dg-m-cool', '#2FB8A6'), K.css('--dg-fl-sig', '#58C4FF')]
        .forEach((c, s) => {
          const at = [];
          for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
            at.push([(-(nx - 1) / 2 + i) * cw + (s - 1) * cw * 0.3, 0, (-(nz - 1) / 2 + j) * cd]);
          }
          g.add(instOf(new T.BoxGeometry(cw * 0.26, h * 0.72, cd * 0.8),
            K.mat(0, { color: c, rough: 0.5, metal: 0.04 }), at));
        });
      const bm = [];
      for (let i = 0; i <= nx; i++) bm.push([Math.max(0.03, w * 0.008), h, d * 0.92, (-nx / 2 + i) * cw, 0, 0]);
      for (let j = 0; j <= nz; j++) bm.push([w * 0.92, h, Math.max(0.03, d * 0.012), 0, 0, (-nz / 2 + j) * cd]);
      g.add(mboxes(bm, K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.9, metal: 0.02 })));
      return g;
    }

    /* 端子區：驅動 IC ＋ COF 軟板。★ 它貼在下玻璃**外露的那一條端子區**上 ——
       兩片玻璃錯開就是為了留這條邊。COF 是壓在軟板上再接過來，軟板往背面折。
       晶片本身屬半導體鏈的「顯示驅動 IC」，這裡只畫它貼在哪裡。*/
    function pnDriver(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const n = 5, pz = d / n;
      g.add(instOf(new T.BoxGeometry(w * 0.3, h * 0.34, pz * 0.6),
        K.mat(-0.2, { rough: 0.44, metal: 0.16 }), gridXZ(1, n, 0, pz, 0)));
      const fx = w * 0.22, cof = [];
      for (let j = 0; j < n; j++) {
        const z = (-(n - 1) / 2 + j) * pz;
        cof.push([w * 0.5, h * 0.08, pz * 0.66, fx, -h * 0.12, z]);
        cof.push([h * 0.08, h * 0.9, pz * 0.66, fx + w * 0.24, -h * 0.6, z]);
      }
      g.add(mboxes(cof, K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.62, metal: 0.07 })));
      g.add(put(box(w * 0.5, h * 0.2, d * 0.92,
        K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.58, metal: 0.06 })),
        fx + w * 0.34, -h * 1.05, 0));
      // 端子區的接點：玻璃邊上那一排 ITO 金手指，晶片就壓在它上面
      g.add(instOf(new T.BoxGeometry(w * 0.12, h * 0.05, pz * 0.5),
        K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.26 }),
        gridXZ(1, n, 0, pz, 0).map(a => [-w * 0.3, -h * 0.16, a[2]])));
      return g;
    }

    /* ---------------------------------------------------------------- 工業自動化：一根會動的軸
       沿 x 拆開。★ 這張圖的主張是「一根軸是一**串**零件」：
       馬達 → 聯軸器 → 軸承座 → 螺桿＋螺帽 → 滑軌＋滑塊 → 工作台。
       所以每一件都要看得出它接的是誰（軸、法蘭、鎖付孔、法蘭盤都不能省）。*/

    /* 底座（鋁擠型）：★ 斷面有空腔 —— 同樣重量下拿到比較高的斷面剛性。
       實心方塊不是鋁擠型，上緣的 T 型槽也是它的識別特徵（軌道與感測器鎖在裡面）。*/
    function mcBase(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const t = h * 0.22;
      g.add(mboxes([[w, t, d, 0, -h / 2 + t / 2, 0], [w, t, d, 0, h / 2 - t / 2, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2], [w, h, t, 0, 0, d / 2 - t / 2],
        [w, h, t, 0, 0, -d / 6], [w, h, t, 0, 0, d / 6]], K.mat(-0.12, { rough: 0.5 })));
      g.add(mboxes([[w, t * 0.5, t * 0.9, 0, h / 2 - t * 1.1, -d * 0.34],
        [w, t * 0.5, t * 0.9, 0, h / 2 - t * 1.1, d * 0.34]], K.mat(-0.5, { rough: 0.82 })));
      return g;
    }

    /* 伺服馬達：方殼 ＋ 散熱肋 ＋ 前法蘭與四顆鎖付孔 ＋ 伸出去的軸 ＋ 出線接頭。
       ★ 有軸才看得出它是「出力」的那一端；有法蘭才看得出它是被鎖在機構上的。
       本圖只畫外殼，不畫繞組剖面（那會跟變壓器那張撞題）。*/
    function mcMotor(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      const m = K.mat(-0.1, { rough: 0.38 });
      g.add(put(rbox(w * 0.6, R * 1.86, R * 1.86, R * 0.18, m), -w * 0.08, 0, 0));
      const fins = [];
      for (let i = 0; i < 7; i++) {
        fins.push([w * 0.56, R * 0.1, R * 0.12, -w * 0.08, R * 0.95, (-3 + i) * R * 0.5]);
        fins.push([w * 0.56, R * 0.1, R * 0.12, -w * 0.08, -R * 0.95, (-3 + i) * R * 0.5]);
      }
      g.add(mboxes(fins, K.mat(0.12, { rough: 0.44 })));
      g.add(put(cylX(R * 1.02, w * 0.08, m, 20), w * 0.26, 0, 0));
      g.add(instOf(new T.CylinderGeometry(R * 0.11, R * 0.11, w * 0.12, 8),
        K.mat(-0.6, { rough: 0.9, metal: 0.1 }),
        [[w * 0.26, R * 0.66, R * 0.66, 0, 0, Math.PI / 2], [w * 0.26, R * 0.66, -R * 0.66, 0, 0, Math.PI / 2],
          [w * 0.26, -R * 0.66, R * 0.66, 0, 0, Math.PI / 2], [w * 0.26, -R * 0.66, -R * 0.66, 0, 0, Math.PI / 2]]));
      g.add(put(cylX(R * 0.2, w * 0.3, K.mat(0.3, { rough: 0.22, metal: 0.95 }), 14), w * 0.42, 0, 0));
      g.add(put(box(w * 0.1, R * 0.4, R * 0.4, K.mat(-0.46, { rough: 0.7, metal: 0.2 })), -w * 0.1, R * 1.04, 0));
      return g;
    }

    /* 編碼器：★ 裡面那片刻了一圈等距刻線的碼盤就是它的全部意義 ——
       「會轉」跟「知道自己轉到哪」是兩件事，而差別只有這片盤。
       外罩切掉朝鏡頭那一半才看得到它。裝在馬達的**尾端**（遠離螺桿那一側）。*/
    function mcEnc(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      g.add(mboxes(halfSlab(w * 0.9, R * 1.8, R * 1.8), K.mat(-0.2, { rough: 0.64, metal: 0.2 })));
      g.add(halfFace(K, w * 0.9, R * 1.8, R * 1.8, 0, -0.2));
      g.add(put(cylX(R * 0.78, w * 0.06, K.mat(0.42, { rough: 0.2, metal: 0.5 }), 22), 0, 0, -R * 0.45));
      const slots = [];
      for (let i = 0; i < 20; i++) {
        const a = i / 20 * Math.PI * 2;
        slots.push([0, Math.sin(a) * R * 0.6, -R * 0.45 + Math.cos(a) * R * 0.6, a, 0, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.09, R * 0.24, R * 0.09),
        K.mat(-0.76, { rough: 0.95, metal: 0.02 }), slots));
      // 讀取頭：隔著碼盤讀那些刻線的那一小塊板子
      g.add(put(box(w * 0.22, R * 0.3, R * 0.26,
        K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.06 })), -w * 0.24, R * 0.66, -R * 0.45));
      return g;
    }

    /* 聯軸器：★ 中段那條螺旋切槽是它的識別特徵 ——
       沒有它就是一根硬軸，吃不了兩根軸之間必然存在的偏心與角度誤差，
       也沒有一個可更換的犧牲件。兩端各一顆夾緊螺絲。*/
    function mcCoup(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      const m = K.mat(0.06, { rough: 0.3, metal: 0.9 });
      g.add(put(cylX(R, w * 0.3, m, 18), -w * 0.34, 0, 0));
      g.add(put(cylX(R, w * 0.3, m, 18), w * 0.34, 0, 0));
      g.add(put(cylX(R * 0.94, w * 0.4, K.mat(-0.1, { rough: 0.34, metal: 0.88 }), 18), 0, 0, 0));
      const cuts = [], n = 22;
      for (let i = 0; i < n; i++) {
        const t = i / n, a = t * Math.PI * 5;
        cuts.push([(-0.5 + t) * w * 0.38, Math.sin(a) * R * 0.86, Math.cos(a) * R * 0.86, a, 0, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.024, R * 0.3, R * 0.24),
        K.mat(-0.8, { rough: 0.95, metal: 0.04 }), cuts));
      g.add(instOf(new T.CylinderGeometry(R * 0.16, R * 0.16, R * 0.5, 8),
        K.mat(-0.4, { rough: 0.5, metal: 0.82 }), [[-w * 0.34, R * 0.8, 0], [w * 0.34, R * 0.8, 0]]));
      return g;
    }

    /* 軸承座：座體半剖，裡面看得到內外環與夾在中間的一圈滾珠。
       ★ 沒有滾珠的「軸承」只是一個襯套（滑動摩擦），撐不住螺桿的軸向力。
       螺桿兩端各一個：一端固定（吃軸向力）、一端支撐（讓螺桿受熱可以伸長）。*/
    function mcBrg(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      g.add(mboxes(halfSlab(w, h, d), K.mat(-0.16, { rough: 0.46 })));
      g.add(halfFace(K, w, h, d, 0, -0.16));
      const st = K.mat(0.26, { rough: 0.2, metal: 0.95 });
      g.add(put(cylX(R * 0.72, w * 0.62, st, 20), 0, 0, -d * 0.24));
      g.add(put(cylX(R * 0.34, w * 0.7, K.mat(0.08, { rough: 0.24, metal: 0.95 }), 16), 0, 0, -d * 0.24));
      const balls = [];
      for (let i = 0; i < 12; i++) {
        const a = i / 12 * Math.PI * 2;
        balls.push([0, Math.sin(a) * R * 0.53, -d * 0.24 + Math.cos(a) * R * 0.53]);
      }
      g.add(instOf(new T.SphereGeometry(R * 0.17, 8, 6), st, balls));
      return g;
    }

    /* 滾珠螺桿・螺桿軸：★ 溝槽剖面是**圓弧**（哥德弧／單圓弧），不是 V 形三角 ——
       V 形那是鎖緊用的螺絲，走的是滑動摩擦、裡面沒有鋼珠。
       兩端的軸頸比較細而且有階級（那是要裝軸承的地方）。*/
    function mcScrew(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      const st = K.mat(0.2, { rough: 0.2, metal: 0.95 });
      g.add(cylX(R * 0.82, w, st, 20));
      const turns = 9, seg = turns * 12, pts = [];
      for (let i = 0; i <= seg; i++) {
        const t = i / seg, a = t * turns * Math.PI * 2;
        pts.push(new T.Vector3((-0.5 + t) * w * 0.96, Math.sin(a) * R * 0.86, Math.cos(a) * R * 0.86));
      }
      g.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), seg, R * 0.13, 6, false),
        K.mat(-0.3, { rough: 0.3, metal: 0.9 })));
      g.add(put(cylX(R * 0.5, w * 0.1, st, 14), -w * 0.53, 0, 0));
      g.add(put(cylX(R * 0.5, w * 0.1, st, 14), w * 0.53, 0, 0));
      return g;
    }

    /* 滾珠螺桿・螺帽：★ 用半管切開（不是切方塊）——
       壁厚看得見，才看得出「鋼珠與回流通道真的在這個套筒的**裡面**」。
       外側的法蘭是它鎖到工作台上的那一片：沒有法蘭就看不出它是推東西的那一端。*/
    function mcNut(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      g.add(halfTubeX(R, R * 0.62, w * 0.8, K.mat(-0.08, { rough: 0.42 })));
      const fl = halfTubeX(R * 1.46, R * 0.62, w * 0.16, K.mat(-0.2, { rough: 0.46 }));
      fl.position.x = -w * 0.44;
      g.add(fl);
      // 內壁的圓弧溝：跟螺桿上那一條對得起來，鋼珠才夾得住（兩點接觸）
      g.add(halfTubeX(R * 0.72, R * 0.6, w * 0.8, K.mat(-0.5, { rough: 0.55, metal: 0.65 })));
      return g;
    }

    /* 鋼珠：★ 每一顆都同時碰到螺桿溝與螺帽溝 —— 浮在中間就不傳力。
       只畫剖面看得到的那半圈（z < 0），另外幾顆畫在回流通道裡 ——
       因為鋼珠是一個**閉合的迴圈**，不是一條有頭有尾的鏈。*/
    function mcBalls(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      const at = [], n = 30;
      for (let i = 0; i < n; i++) {
        const t = i / (n - 1), a = -Math.PI / 2 + t * Math.PI * 4.5;
        const z = Math.cos(a) * R * 0.66;
        if (z > 0) continue;
        at.push([(-0.34 + t * 0.68) * w * 0.8, Math.sin(a) * R * 0.66, z]);
      }
      for (let i = 0; i < 6; i++) at.push([(-0.3 + i * 0.12) * w * 0.8, R * 0.92, -R * 0.3]);
      g.add(instOf(new T.SphereGeometry(R * 0.11, 8, 6),
        K.mat(0.34, { rough: 0.14, metal: 0.96 }), at));
      return g;
    }

    /* 循環器（鋼珠回流通道）：★ 這張圖的紅線零件 ——
       鋼珠沿溝槽滾到螺帽的一端之後，從這條 U 形通道繞回另一端重新進入溝槽。
       沒有這條通道的螺桿是鎖緊用的梯形螺桿，不是傳動用的滾珠螺桿。*/
    function mcReturn(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(h, d) / 2;
      const pts = [[-w * 0.34, R * 0.5, -R * 0.4], [-w * 0.38, R * 0.92, -R * 0.3],
        [0, R * 1.02, -R * 0.3], [w * 0.38, R * 0.92, -R * 0.3], [w * 0.34, R * 0.5, -R * 0.4]];
      g.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts.map(a => new T.Vector3(a[0], a[1], a[2]))),
        26, R * 0.17, 7, false),
        K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.6, metal: 0.12 })));
      // 兩張嘴：通道跟溝槽接起來的進出口
      g.add(instOf(new T.CylinderGeometry(R * 0.2, R * 0.2, R * 0.22, 10),
        K.mat(-0.3, { rough: 0.55, metal: 0.3 }),
        [[-w * 0.34, R * 0.46, -R * 0.4], [w * 0.34, R * 0.46, -R * 0.4]]));
      return g;
    }

    /* 線性滑軌・軌道：下寬上窄的一條，**兩側各有一道圓弧溝**（滾珠就滾在那兩道溝裡）。
       ★ 一定是兩條平行軌、而且螺桿在兩軌之間 —— 螺桿畫在旁邊的話推力不在滑座形心上，
       工作台會被扭起來。鎖付孔也不能省：軌道是鎖在底座上的，不是放上去的。*/
    function mcRail(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes([[w, h * 0.42, d, 0, -h * 0.29, 0], [w, h * 0.6, d * 0.7, 0, h * 0.2, 0]],
        K.mat(0.08, { rough: 0.26, metal: 0.92 })));
      g.add(instOf(new T.CylinderGeometry(h * 0.12, h * 0.12, w, 8),
        K.mat(-0.36, { rough: 0.4, metal: 0.8 }),
        [[0, h * 0.2, -d * 0.35, 0, 0, Math.PI / 2], [0, h * 0.2, d * 0.35, 0, 0, Math.PI / 2]]));
      const n = 5, holes = [];
      for (let i = 0; i < n; i++) holes.push([(-(n - 1) / 2 + i) * (w / n), h * 0.46, 0]);
      g.add(instOf(new T.CylinderGeometry(d * 0.12, d * 0.12, h * 0.34, 10),
        K.mat(-0.72, { rough: 0.9, metal: 0.1 }), holes));
      return g;
    }

    /* 線性滑軌・滑塊：★ ㄇ 字形，從上方罩下來包住軌道的**兩側**。
       畫成「一個方塊放在軌道上面」是錯的 —— 那樣的東西吃不了側向力也吃不了拉拔力，
       而滑軌存在的理由就是吃這兩種力。兩端的端蓋是滑塊內部滾珠循環的轉彎處。*/
    function mcBlock(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes([[w, h * 0.42, d, 0, h * 0.29, 0],
        [w, h * 0.6, d * 0.22, 0, -h * 0.2, -d * 0.39], [w, h * 0.6, d * 0.22, 0, -h * 0.2, d * 0.39]],
        K.mat(-0.12, { rough: 0.44 })));
      const at = [], n = 7;
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * (w / n);
        at.push([x, -h * 0.02, -d * 0.3]); at.push([x, -h * 0.02, d * 0.3]);
      }
      g.add(instOf(new T.SphereGeometry(h * 0.1, 8, 6), K.mat(0.3, { rough: 0.15, metal: 0.95 }), at));
      g.add(mboxes([[w * 0.08, h * 0.9, d * 0.96, -w * 0.46, 0, 0], [w * 0.08, h * 0.9, d * 0.96, w * 0.46, 0, 0]],
        K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.66, metal: 0.1 })));
      return g;
    }

    /* 工作台（滑座）：★ 同時鎖在螺帽與滑塊上 —— 螺帽推它走、滑塊撐住它不歪，
       兩個連接都要有，少一個這根軸就不成立。上面的 T 型槽是工件鎖上去的地方。*/
    function mcTable(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h * 0.45, d, K.mat(0.1, { rough: 0.5 })));
      g.add(mboxes([[w * 0.36, h * 0.55, d * 0.2, 0, -h * 0.5, -d * 0.36],
        [w * 0.36, h * 0.55, d * 0.2, 0, -h * 0.5, d * 0.36],
        [w * 0.22, h * 0.55, d * 0.3, -w * 0.3, -h * 0.5, 0]], K.mat(-0.1, { rough: 0.55 })));
      const sl = [], n = 3;
      for (let i = 0; i < n; i++) sl.push([w * 0.94, h * 0.2, d * 0.07, 0, h * 0.18, (-(n - 1) / 2 + i) * d * 0.3]);
      g.add(mboxes(sl, K.mat(-0.5, { rough: 0.8 })));
      return g;
    }

    /* ---------------------------------------------------------------- 被動保護：四顆並排半剖
       ★ 這四顆的差別**全部在裡面**：MOV 是陶瓷晶粒與晶界、PPTC 是高分子與碳黑鏈、
       NTC 是均質燒結陶瓷（沒有晶界網也沒有 PN）、TVS 是 PN 接面與空乏區。
       外觀上它們都只是四顆小方塊 —— 不剖開就等於沒有畫出任何一件事。
       半剖（切掉 z > 0）跟第三代半導體那張同一種切法：它們都是一疊薄層。*/

    /* PPTC 的高分子基體：低溫時結晶之間的導電粒子連成網路而導通；
       電流過大升溫 → 體積膨脹、聚合物由結晶態轉為非結晶態 → 網路斷裂而不導通；
       冷了恢復結晶又導通 —— 這就是「自恢復」。*/
    function cpPoly(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w, h, d), K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.74, metal: 0.05 })));
      g.add(halfFace(K, w, h, d, 0, 0));
      return g;
    }

    /* 導電碳黑粒子：★ 它是一條一條**貫穿上下電極的鏈**，不是均勻的黑色。
       只畫「變紅」不畫「變厚＋斷鏈」就沒有解釋機制。膨脹的實際比例查不到，本圖不寫百分比。*/
    function cpCarbon(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const at = [], nx = 9, ny = 6;
      for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
        const jit = ((i * 7 + j * 13) % 5 - 2) * w * 0.012;
        /* ⚠ z 一定要落在剖面**前方**（≈ 0），不是本體中心（−d/4）：
           halfFace 那片切面貼在 z = 0 的前面，擺在後面就整批被它擋住，
           畫了等於沒畫（第一版就是這樣，截圖上 PPTC 是一塊純色）。*/
        at.push([(-(nx - 1) / 2 + i) * (w * 0.88 / nx) + jit,
          (-(ny - 1) / 2 + j) * (h * 0.8 / ny), 0]);
      }
      g.add(instOf(new T.SphereGeometry(Math.min(w, h) * 0.038, 7, 5),
        K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.82, metal: 0.08 }), at));
      return g;
    }

    /* PPTC 的鎳電極箔 ×2：上下各一片、夾住中間的高分子基體。
       ★ 是**相對的兩面**，不是同一面的兩端 —— 電流要垂直穿過高分子。
       底下那一層薄錫說明它是表面黏著件。*/
    function cpFoil(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const m = K.mat(0.2, { rough: 0.3, metal: 0.9 });
      g.add(mboxes(halfSlab(w, h * 0.12, d, h * 0.44).concat(halfSlab(w, h * 0.12, d, -h * 0.44)), m));
      g.add(mboxes(halfSlab(w * 0.9, h * 0.06, d * 0.9, -h * 0.53),
        K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), rough: 0.36, metal: 0.6 })));
      return g;
    }

    /* PPTC 的外包絕緣層：最外面那一層樹脂或塑膠薄膜。
       它不參與導電，只是把裡面包起來 —— 所以它畫成一個**空的殼**，不是一塊實心。*/
    function cpShell(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const t = Math.min(w, h) * 0.06;
      g.add(mboxes([[w, t, d / 2, 0, h / 2 - t / 2, -d / 4], [w, t, d / 2, 0, -h / 2 + t / 2, -d / 4],
        [t, h, d / 2, -w / 2 + t / 2, 0, -d / 4], [t, h, d / 2, w / 2 - t / 2, 0, -d / 4]],
        K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.74, metal: 0.06 })));
      return g;
    }

    /* NTC 熱敏電阻：★ 金屬氧化物燒結的**均質**陶瓷本體 ＋ 兩個相對面電極，
       沒有晶界網也沒有 PN 接面。★ 它擋的不是突波電壓，是開機瞬間的湧浪電流
       —— 跟另外三顆不是同一件事。兩根導線從同一側出去（圓盤型的樣子）。*/
    function cpNtc(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w, h * 0.76, d), K.mat(-0.1, { rough: 0.64, metal: 0.04 })));
      g.add(halfFace(K, w, h * 0.76, d, 0, -0.1));
      const mt = K.mat(0.3, { rough: 0.3, metal: 0.86 });
      g.add(mboxes(halfSlab(w * 0.94, h * 0.07, d * 0.94, h * 0.42)
        .concat(halfSlab(w * 0.94, h * 0.07, d * 0.94, -h * 0.42)), mt));
      g.add(instOf(new T.CylinderGeometry(w * 0.03, w * 0.03, h * 0.8, 8), mt,
        [[-w * 0.26, -h * 0.82, -d * 0.2], [w * 0.26, -h * 0.82, -d * 0.2]]));
      return g;
    }

    /* MOV 的 ZnO 晶粒：★ 一堆**大小不一的多邊形**，不是一塊均質陶瓷 ——
       畫成均質方塊就不是 MOV，那跟 NTC 長得一模一樣。
       晶粒的實際尺寸與數量查不到，圖上是示意。*/
    function cpGrain(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const at = [], nx = 8, ny = 5;
      for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
        const s = 0.62 + ((i * 5 + j * 11) % 7) / 7 * 0.7;
        at.push([(-(nx - 1) / 2 + i) * (w * 0.9 / nx), (-(ny - 1) / 2 + j) * (h * 0.8 / ny), -d / 4 + d * 0.03,
          (i % 3) * 0.7, (j % 3) * 0.7, 0, s, s, s]);
      }
      g.add(instOf(new T.DodecahedronGeometry(Math.min(w / nx, h / ny) * 0.66, 0),
        K.mat(-0.04, { rough: 0.58, metal: 0.05 }), at));
      return g;
    }

    /* MOV 的晶界：★ 它的非線性**完全**來自晶界 ——
       每一對相鄰晶粒之間的界面形成一個微觀位壘，一顆裡面有數以百萬計個、
       串並聯成一張三維的網。這條折線是電流穿過好幾道晶界的路徑（示意，不是只有一條）。*/
    function cpGb(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const pts = [], n = 9;
      for (let i = 0; i < n; i++) {
        // z ≈ 0：這條路徑要跑在剖面上，埋進晶粒堆裡就看不到了
        pts.push(new T.Vector3(((i % 3) - 1) * w * 0.16, (-0.5 + i / (n - 1)) * h * 0.86, Math.min(w, h) * 0.02));
      }
      g.add(new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts), 30, Math.min(w, h) * 0.018, 6, false),
        K.mat(0, { color: K.css('--dg-fl-trace', '#FFD37A'), glow: 0.35, rough: 0.4, metal: 0.2 })));
      g.add(instOf(new T.BoxGeometry(w * 0.09, h * 0.014, d * 0.1),
        K.mat(0, { color: K.css('--dg-fl-hot', '#FF4D5E'), rough: 0.5, metal: 0.1 }),
        pts.slice(1, n - 1).map(v => [v.x, v.y, v.z])));
      return g;
    }

    /* 保護元件的金屬電極 ×2（MOV 與 TVS 共用）：
       ★ 在兩個**相對**的面（上下），不是同一面的兩端 ——
       電流要垂直穿過整疊晶粒／整個 PN 接面，才會撞到裡面那些界面。*/
    function cpElec(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const mt = K.mat(0.26, { rough: 0.3, metal: 0.88 });
      g.add(mboxes(halfSlab(w, h * 0.1, d, h * 0.45).concat(halfSlab(w, h * 0.1, d, -h * 0.45)), mt));
      g.add(instOf(new T.CylinderGeometry(w * 0.028, w * 0.028, h * 0.8, 8), mt,
        [[-w * 0.3, h * 0.9, -d * 0.2], [w * 0.3, h * 0.9, -d * 0.2]]));
      return g;
    }

    /* TVS 的 PN 接面：★ 兩種不同摻雜的半導體區 ＋ 中間一條**空乏區**窄帶，
       這是 TVS 的識別特徵。畫成陶瓷晶粒就是畫成了 MOV（兩者的物理機制完全不同），
       畫成三明治薄膜就是畫成了晶片電阻。雪崩就發生在那條窄帶裡。*/
    function cpPn(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      /* ⚠ 每一段各自補自己的切面，**不准**最後蓋一片整面的 halfFace ——
         那會把 p／n／空乏區三段的明暗差一起蓋掉，整顆變成一塊黑
         （第一版就是這樣，而 TVS 的識別特徵正好就是那三段）。*/
      g.add(mboxes(halfSlab(w, h * 0.42, d, h * 0.24), K.mat(0.62, { rough: 0.42 })));
      g.add(halfFace(K, w, h * 0.42, d, h * 0.24, 0.62));
      g.add(mboxes(halfSlab(w, h * 0.42, d, -h * 0.24), K.mat(-0.08, { rough: 0.42 })));
      g.add(halfFace(K, w, h * 0.42, d, -h * 0.24, -0.08));
      g.add(mboxes(halfSlab(w * 0.995, h * 0.1, d * 0.995, 0),
        K.mat(0, { color: K.css('--dg-fl-sig', '#58C4FF'), rough: 0.44, metal: 0.1 })));
      return g;
    }

    /* ---------------------------------------------------------------- 電容器：鋁電解整顆縱剖
       ★ 鋁電解是一顆**捲**出來的東西，這是它跟 MLCC（疊出來的）最根本的差別。
       所以整顆用半管縱剖（看得到鋁殼的壁厚與塞在裡面的捲芯），
       捲芯旁邊再把四層帶水平拉開 —— 「四層一起捲」才看得懂。*/

    /* 鋁殼：薄壁圓筒（縱剖）＋ 封死的底 ＋ 上緣那道頸縮（封口橡膠就卡在這道溝裡）。
       畫成實心圓柱就看不出「裡面裝著捲芯」。*/
    function acCan(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const m = K.mat(0.06, { rough: 0.34 });
      g.add(halfTubeY(R, R * 0.9, h * 0.94, m));
      g.add(put(halfTubeY(R, 0, h * 0.06, m), 0, -h * 0.47, 0));
      g.add(put(halfTubeY(R * 1.01, R * 0.86, h * 0.05, K.mat(-0.22, { rough: 0.46 })), 0, h * 0.38, 0));
      return g;
    }

    /* 外套膠膜：包在鋁殼外面的有色薄膜。
       ★ 本圖上面一個字、一個色碼、一個廠商標示都沒有 —— 那些是產品外觀，不是結構。*/
    function acSleeve(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      g.add(halfTubeY(R, R * 0.955, h, K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.68, metal: 0.08 })));
      return g;
    }

    /* 捲芯：★ 四層（陽極箔／紙／陰極箔／紙）**一起**捲在一個輪上。
       縱剖面看到的是一圈一圈交替的帶；頂面那幾圈同心弧說明它是「捲」出來的，不是疊出來的。
       三層捲起來，上一圈的陽極會直接碰到下一圈的陰極 —— 短路。*/
    function acCore(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      g.add(halfTubeY(R, 0, h, K.mat(-0.24, { rough: 0.6, metal: 0.2 })));
      const foil = K.mat(0.36, { rough: 0.3, metal: 0.82 });
      const paper = K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.8, metal: 0.03 });
      const fb = [], pb = [];
      for (let t = 0; t < 4; t++) for (let k = 0; k < 4; k++) {
        const r = R * (0.24 + (t * 4 + k) * 0.045);
        [-1, 1].forEach(s => (k % 2 ? pb : fb).push([s * r, 0, -R * 0.02]));
      }
      g.add(instOf(new T.BoxGeometry(R * 0.03, h * 0.9, R * 0.03), foil, fb));
      g.add(instOf(new T.BoxGeometry(R * 0.03, h * 0.9, R * 0.03), paper, pb));
      const ev = [], od = [];
      for (let i = 0; i < 6; i++) {
        const r = R * (0.24 + i * 0.13);
        const rg = new T.RingGeometry(r, r + R * 0.055, 14, 1, 0, Math.PI);
        rg.rotateX(-Math.PI / 2); rg.translate(0, h * 0.502, 0);
        (i % 2 ? od : ev).push(rg);
      }
      g.add(new T.Mesh(mergeGeos(ev), foil));
      g.add(new T.Mesh(mergeGeos(od), paper));
      return g;
    }

    /* 箔（陽極／陰極共用）：蝕刻過的表面不是鏡面，兩面都是粗糙的。
       ★ 陰極箔一樣有孔，它跟陽極箔的差別只在「有沒有那層氧化膜」——
       兩面都畫氧化膜就變成雙極性電容，而且把「為什麼有極性」這件事畫掉了。*/
    function acFoil(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const k = p.k == null ? 0.24 : p.k;
      g.add(box(w, h, d, K.mat(k, { rough: 0.46, metal: 0.8 })));
      const rid = [], n = 18;
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * (w * 0.94 / n);
        rid.push([x, h * 0.5, 0]); rid.push([x, -h * 0.5, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.94 / n * 0.5, h * 0.12, d * 0.94),
        K.mat(k - 0.35, { rough: 0.82, metal: 0.42 }), rid));
      return g;
    }

    /* 蝕刻孔（隧道／海綿狀）：★ 兩面都咬，中間要留一條實心芯 —— 沒有芯的箔會斷。
       孔越多越深，同一片箔的表面積越大，容量就是從這裡來的。
       本圖不寫孔徑、孔密度與表面積放大倍數（查不到共通值）。*/
    function acPore(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const at = [], n = 22, nz = 4;
      for (let i = 0; i < n; i++) for (let j = 0; j < nz; j++) {
        const x = (-(n - 1) / 2 + i) * (w * 0.92 / n), z = (-(nz - 1) / 2 + j) * (d * 0.76 / nz);
        at.push([x, h * 0.26, z]); at.push([x, -h * 0.26, z]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.92 / n * 0.4, h * 0.44, d * 0.76 / nz * 0.4),
        K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 }), at));
      return g;
    }

    /* 箔的基體（未蝕刻的芯部）：兩面被咬之後中間留下來的那一條實心鋁。
       厚度＝箔厚 − 2×孔深，是真的減出來的，不是目測。*/
    function acSpine(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h * 0.16, d, K.mat(0.48, { rough: 0.3, metal: 0.9 })));
      g.add(mboxes([[w * 1.004, h * 0.03, d * 1.004, 0, h * 0.095, 0],
        [w * 1.004, h * 0.03, d * 1.004, 0, -h * 0.095, 0]], K.mat(0.05, { rough: 0.62, metal: 0.5 })));
      return g;
    }

    /* 陽極氧化膜（Al₂O₃，介電質）：★ 它不是買來的，是**長出來的** ——
       鋁箔通電做陽極氧化，表面長出一層氧化鋁。膜厚由外加電壓決定
       （耐壓越高、膜越厚、容量越小；每伏特幾埃是 roughly 的說法，所以不寫數字）。
       ★ 膜是沿著**孔的內壁**長的，不是只鋪在表面 —— 只鋪表面就沒有那些被放大的面積。*/
    function acOxide(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const m = K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.3, metal: 0.04, op: 0.9 });
      g.add(mboxes([[w, h * 0.16, d, 0, h * 0.42, 0], [w, h * 0.16, d, 0, -h * 0.42, 0]], m));
      const at = [], n = 14;
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * (w * 0.92 / n);
        at.push([x, h * 0.16, 0]); at.push([x, -h * 0.16, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.92 / n * 0.54, h * 0.34, d * 0.9), m, at));
      return g;
    }

    /* 電解紙（隔離紙）：天然纖維素做的紙，含浸電解液、同時把兩張箔隔開。
       ★ 它本身不是電極，也不是介電質 —— 介電質是陽極箔上那層氧化膜。
       表面那些纖維是它跟金屬箔一眼分得開的地方。*/
    function acPaper(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.88, metal: 0.02 })));
      const at = [], n = 20;
      for (let i = 0; i < n; i++) at.push([(-(n - 1) / 2 + i) * (w * 0.96 / n), h * 0.5, 0, 0, (i % 3) * 0.4, 0]);
      g.add(instOf(new T.BoxGeometry(w * 0.03, h * 0.12, d * 0.9), K.mat(0.32, { rough: 0.9, metal: 0.02 }), at));
      return g;
    }

    /* 電解液：★ 它才是真正的陰極。它要鑽進陽極箔的孔裡、貼住氧化膜 ——
       只畫在紙裡就是沒有接觸到介電質，電容不成立。*/
    function acElyte(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const c = K.css('--dg-m-cool', '#2FB8A6');
      g.add(box(w, h * 0.5, d, K.mat(0, { color: c, rough: 0.2, metal: 0.05, op: 0.6 })));
      const at = [], n = 16;
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * (w * 0.92 / n);
        at.push([x, h * 0.6, 0]); at.push([x, -h * 0.6, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.92 / n * 0.42, h * 0.9, d * 0.8),
        K.mat(0, { color: c, rough: 0.22, metal: 0.05, op: 0.45 }), at));
      return g;
    }

    /* 橡膠封口：在鋁殼的一端，兩根導針從這裡穿出去。
       它同時是密封件，也是壓力上來時的洩壓路徑之一。*/
    function acSeal(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      g.add(halfTubeY(R * 0.92, 0, h, K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.88, metal: 0.03 })));
      g.add(instOf(new T.CylinderGeometry(R * 0.13, R * 0.13, h * 1.1, 10),
        K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.9, metal: 0.05 }),
        [[-R * 0.4, 0, -R * 0.3], [R * 0.4, 0, -R * 0.3]]));
      return g;
    }

    /* 導針（引線）×2：★ 整顆的兩根導針從**同一端**穿出（徑向引線型）——
       一端一根那是軸向型，跟這裡的捲芯畫法對不起來。
       焊在箔上的那一段是扁的，穿出去的那一段才是圓的。*/
    function acLead(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const r = Math.min(w, d) * 0.42;
      g.add(cyl(r, h, K.mat(0.3, { rough: 0.3, metal: 0.9 }), 12));
      g.add(put(box(r * 2.2, h * 0.3, r * 0.5, K.mat(0.05, { rough: 0.46, metal: 0.8 })), 0, -h * 0.58, 0));
      return g;
    }

    /* 防爆閥（刻痕）：壓力上來時先從這裡裂開，不讓整顆炸掉。
       ★ 本圖把它畫在與封口相反的那一端，但這一點**查不到可引用的來源**
       （徑向引線型的防爆結構各家做法不同），所以標為示意，也不寫刻痕形狀的規格。*/
    function acVent(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      g.add(halfTubeY(R, 0, h, K.mat(-0.1, { rough: 0.4 })));
      const sc = [];
      for (let i = 0; i < 3; i++) sc.push([0, h * 0.5, 0, 0, i * Math.PI / 3, 0]);
      g.add(instOf(new T.BoxGeometry(R * 1.5, h * 0.34, R * 0.1),
        K.mat(-0.76, { rough: 0.9, metal: 0.1 }), sc));
      return g;
    }

    /* 固態電容（對照）：★ 只換了一樣東西 —— 把電解液換成固態的導電高分子。
       它一樣要鑽進陽極箔的孔裡；沒有液體可以汽化，所以不會鼓脹爆漿。
       等效串聯電阻大幅下降（來源只講材料導電度，所以不寫倍數）。*/
    function acSolid(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      g.add(halfTubeY(R, R * 0.88, h * 0.9, K.mat(0.06, { rough: 0.34 })));
      g.add(halfTubeY(R * 0.86, 0, h * 0.84,
        K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.6, metal: 0.2 })));
      g.add(put(halfTubeY(R * 1.02, 0, h * 0.08,
        K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.72, metal: 0.08 })), 0, -h * 0.5, 0));
      g.add(instOf(new T.BoxGeometry(R * 0.5, h * 0.06, R * 0.3),
        K.mat(0.4, { rough: 0.3, metal: 0.85 }),
        [[-R * 0.5, -h * 0.55, -R * 0.3], [R * 0.5, -h * 0.55, -R * 0.3]]));
      return g;
    }

    /* ---------------------------------------------------------------- 被動元件：電感・電阻・石英
       三顆並排半剖。三者之間**沒有上下游關係**，放在一起是因為它們真的在同一塊板子的同一區；
       所以這一組刻意沒有任何流線與箭頭。
       每一顆的識別特徵都被蓋住了（繞組埋在磁粉裡、修整溝壓在玻璃層底下、石英片封在腔裡），
       半剖是唯一看得到它們的方式。*/

    /* 功率電感的本體：金屬磁粉壓製（一體成型）。
       ★ 磁芯與外殼是**同一塊** —— 看不到縫，那正是它跟「繞線型＋鐵氧體上蓋」最好分辨的地方。
       剖面上那層細顆粒是壓製的粉粒感（示意，不是真的顆粒尺寸）。*/
    function indBody(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w, h, d), K.mat(-0.06, { rough: 0.74, metal: 0.18 })));
      g.add(halfFace(K, w, h, d, 0, -0.06));
      const at = [], n = 10, ny = 5;
      for (let i = 0; i < n; i++) for (let j = 0; j < ny; j++) {
        const s = 0.6 + ((i * 3 + j) % 4) * 0.25;
        // z ≈ 0：粉粒要長在剖面上（埋進本體裡就被 halfFace 擋住了，見 cpCarbon 那一條）
        at.push([(-(n - 1) / 2 + i) * (w * 0.9 / n), (-(ny - 1) / 2 + j) * (h * 0.8 / ny), 0,
          0, 0, 0, s, s, s]);
      }
      g.add(instOf(new T.DodecahedronGeometry(Math.min(w, h) * 0.026, 0),
        K.mat(-0.3, { rough: 0.86, metal: 0.12 }), at));
      return g;
    }

    /* 扁平銅線繞組：★ 斷面是**長方形**（高 > 寬）—— 扁平線立繞，
       同樣空間塞進更多銅，直流電阻更低。畫成圓線就變成另一種做法了。
       一段一段拼成的環就是「繞」出來的，不是一顆環。*/
    function indWind(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const turns = 4, seg = 16, at = [];
      for (let t = 0; t < turns; t++) for (let i = 0; i < seg; i++) {
        const a = (i + t * 0.25) / seg * Math.PI * 2;
        at.push([Math.cos(a) * R * 0.66, (-(turns - 1) / 2 + t) * h * 0.2, Math.sin(a) * R * 0.66,
          0, -a + Math.PI / 2, 0]);
      }
      g.add(instOf(new T.BoxGeometry(R * 0.27, h * 0.17, R * 0.09),
        K.mat(0.12, { rough: 0.3, metal: 0.92 }), at));
      return g;
    }

    /* 磁通路徑：★ 磁通不跑出本體之外 —— 那就是「磁屏蔽」這個說法的意思。
       而且路徑一定是**封閉**的：從繞組中心往上、沿著本體外圍下來、再回到中心。
       畫成一條有頭有尾的線就是把磁路畫成了電路。*/
    function indFlux(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const R = Math.min(w, d) / 2;
      const m = K.mat(0, { color: K.css('--dg-fl-gpu', '#9B6DFF'), glow: 0.3, rough: 0.4, metal: 0.1, op: 0.8 });
      [-1, 1].forEach(s => {
        const pts = [[0, -h * 0.3, 0], [0, h * 0.3, 0], [s * R * 0.5, h * 0.42, 0],
          [s * R * 0.84, 0, 0], [s * R * 0.5, -h * 0.42, 0]];
        const cv = new T.CatmullRomCurve3(pts.map(a => new T.Vector3(a[0], a[1], a[2] - d * 0.24)), true);
        g.add(new T.Mesh(new T.TubeGeometry(cv, 26, Math.min(w, h) * 0.02, 5, true), m));
      });
      return g;
    }

    /* 引出端子：★ 繞組兩端折出來貼在**底面** —— 所以它是表面黏著件，不是插件
       （沒有腳穿過板子）。底下那一圈是真的焊在板子上的錫。*/
    function indTerm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes([[w * 0.3, h, d * 0.72, -w * 0.33, 0, 0], [w * 0.3, h, d * 0.72, w * 0.33, 0, 0]],
        K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), rough: 0.36, metal: 0.62 })));
      g.add(instOf(new T.BoxGeometry(w * 0.36, h * 0.5, d * 0.8),
        K.mat(0.2, { rough: 0.3, metal: 0.55 }), [[-w * 0.33, -h * 0.6, 0], [w * 0.33, -h * 0.6, 0]]));
      return g;
    }

    /* 晶片電阻的氧化鋁陶瓷基板：整顆零件的底，也是散熱的路 ——
       上面的每一層都印在它身上。半剖才看得到上面疊了幾層。*/
    function resLay(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const k = p.k == null ? -0.08 : p.k;
      g.add(mboxes(halfSlab(w, h, d), K.mat(k, { rough: 0.62, metal: 0.04 })));
      g.add(halfFace(K, w, h, d, 0, k));
      return g;
    }

    /* 電阻膜（釕系厚膜）：網印上去再燒結。
       ★ 兩端**壓在電極上**（是重疊，不是頭碰頭對接）—— 對接的接口一受熱就開路。*/
    function resFilm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const m = K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.66, metal: 0.1 });
      g.add(mboxes(halfSlab(w * 0.84, h, d * 0.92), m));
      g.add(mboxes([[w * 0.14, h * 0.8, d * 0.46, -w * 0.45, h * 0.3, -d * 0.23],
        [w * 0.14, h * 0.8, d * 0.46, w * 0.45, h * 0.3, -d * 0.23]], m));
      return g;
    }

    /* 雷射修整溝 ← ★ 它就是晶片電阻的身分證。
       印出來的阻值不會剛好，量完用雷射切一道溝，把電流的路徑拉長、阻值往上修。
       溝是 L 形（先切進去再轉向），不是一條直線 —— 直線切過頭就報廢了，L 形才修得準。*/
    function resTrim(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const cw = Math.max(0.04, w * 0.035), cd = Math.max(0.04, d * 0.035);
      g.add(mboxes([[cw, h, d * 0.3, 0, 0, -d * 0.34], [w * 0.22, h, cd, w * 0.1, 0, -d * 0.2]],
        K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 })));
      /* ★ 雷射是**切穿電阻膜**的，所以溝底露出來的是底下的陶瓷基板 ——
         溝畫成一條全黑的線就少了「它切到哪裡為止」這件事。*/
      g.add(mboxes([[cw * 1.6, h * 0.18, d * 0.3, 0, -h * 0.42, -d * 0.34],
        [w * 0.22, h * 0.18, cd * 1.6, w * 0.1, -h * 0.42, -d * 0.2]],
        K.mat(0, { color: K.css('--dg-cer', '#d3cbb7'), rough: 0.66, metal: 0.04 })));
      return g;
    }

    /* 玻璃保護層：★ 修完才蓋上去，所以那道溝在它**底下** —— 溝露在最外面就是畫錯。
       半透明才看得到底下那道溝，那正是這一層要證明的事。*/
    function resGlass(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w, h, d), K.mat(0.3, { rough: 0.16, metal: 0.03, op: 0.6 })));
      // 剖面上那一條切口比外表面暗一階，不然「被切開的面」跟原本就有的面長得一模一樣
      g.add(halfFace(K, w, h, d, 0, 0.3));
      return g;
    }

    /* 端電極：★ 一定是**三層** —— 內層（與電阻膜接觸）→ 鎳阻障（擋焊錫把內層吃掉）→ 錫（好焊）。
       少掉鎳那一層，焊兩次就把內層吃光。這跟 MLCC 的端電極是同一套道理（那張圖已經講完原理）。*/
    function resTerm(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      [['--dg-m-trace', '#E6B95C', 0.9], ['--dg-m-rack', '#B8C2CC', 0.8], ['--dg-sn', '#e2e7ec', 0.6]]
        .forEach((L, i) => {
          const t = 1 - i * 0.14, off = w * 0.45 - i * w * 0.05;
          const m = K.mat(0, { color: K.css(L[0], L[1]), metal: L[2], rough: 0.3 });
          g.add(mboxes([[w * 0.1, h * t, d / 2 * 0.98, -off, 0, -d / 4],
            [w * 0.1, h * t, d / 2 * 0.98, off, 0, -d / 4]], m));
        });
      return g;
    }

    /* 背面電極：基板背面也印一層 —— 它是散熱與焊接的路。
       只畫正面那一層的話，這顆零件焊在板子上是靠什麼貼住的就沒有答案。*/
    function resBack(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes(halfSlab(w * 0.9, h, d * 0.9),
        K.mat(0, { color: K.css('--dg-m-graphite', '#3A3F47'), rough: 0.62, metal: 0.2 })));
      g.add(halfFace(K, w * 0.9, h, d * 0.9, 0, 0));
      return g;
    }

    /* 石英諧振器的陶瓷底座：一個有**凹穴**的盒子。
       ★ 石英片是懸空在凹穴裡的，不是貼在底面上 —— 貼死就振不動了。
       底面四個焊墊說明它是表面黏著件。*/
    function xtalBase(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const t = h * 0.3;
      g.add(mboxes([[w, t, d, 0, -h / 2 + t / 2, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2], [w, h, t, 0, 0, d / 2 - t / 2],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0]],
        K.mat(-0.08, { rough: 0.62, metal: 0.04 })));
      g.add(instOf(new T.BoxGeometry(w * 0.22, h * 0.08, d * 0.3),
        K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.26 }),
        gridXZ(2, 2, w * 0.66, d * 0.52, -h / 2 - h * 0.04)));
      return g;
    }

    /* 導電膠支撐點：★ 只靠**同一端**的兩點架著，四周都不能碰到東西 —— 碰到就振不動。
       支撐點數量為示意。它同時是機械支撐與電氣連接（電極的引線就走這裡下來）。*/
    function xtalMount(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(instOf(new T.CylinderGeometry(w * 0.16, w * 0.22, h, 10),
        K.mat(0, { color: K.css('--dg-m-cu', '#D6A886'), rough: 0.5, metal: 0.6 }),
        [[-w * 0.25, 0, -d * 0.24], [-w * 0.25, 0, d * 0.24]]));
      return g;
    }

    /* 石英片（AT 切）：一片薄薄的長方形，★ **厚度決定頻率**（越薄頻率越高）——
       所以這一片的厚薄不是隨便畫的。兩條亮邊表示它是被「切」出來的
       （AT 切＝相對於晶軸切一個特定角度，那個角度決定它的溫度特性）。*/
    function xtalBlank(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(0.34, { rough: 0.1, metal: 0.03, op: 0.62 })));
      g.add(mboxes([[w * 1.002, h * 0.3, Math.max(0.03, d * 0.06), 0, 0, -d / 2],
        [w * 1.002, h * 0.3, Math.max(0.03, d * 0.06), 0, 0, d / 2]],
        K.mat(0.64, { rough: 0.08, metal: 0.05, op: 0.8 })));
      return g;
    }

    /* 電極：★ 上下各一片、面積比石英片小 ——
       電場要垂直穿過石英才激得起厚度剪切振動。兩片各自拉一條引線到同一端的支撐點
       （所以那兩條引線一定在同一側，不是對角）。*/
    function xtalElec(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(mboxes([[w * 0.56, h * 0.1, d * 0.6, 0, h * 0.4, 0], [w * 0.56, h * 0.1, d * 0.6, 0, -h * 0.4, 0],
        [w * 0.3, h * 0.08, d * 0.12, -w * 0.4, h * 0.4, -d * 0.24],
        [w * 0.3, h * 0.08, d * 0.12, -w * 0.4, -h * 0.4, d * 0.24]],
        K.mat(0.2, { rough: 0.24, metal: 0.92 })));
      return g;
    }

    /* 金屬蓋 ＋ 縫焊：用電阻加熱把金屬蓋焊在陶瓷底座上。
       ★ 焊縫是**一圈連續**的 —— 斷一個點就封不住，頻率會跟著環境跑掉，
       而「封不住，時間就跟著走鐘」是這一類零件的生死線。*/
    function xtalLid(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const t = h * 0.22;
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2], [w, h, t, 0, 0, d / 2 - t / 2],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0]],
        K.mat(0.12, { rough: 0.3, metal: 0.9 })));
      const sm = [], n = 14;
      for (let i = 0; i < n; i++) {
        const u = (-0.5 + (i + 0.5) / n) * w;
        sm.push([u, -h / 2, -d / 2]); sm.push([u, -h / 2, d / 2]);
      }
      for (let i = 0; i < 5; i++) {
        const v = (-0.5 + (i + 0.5) / 5) * d;
        sm.push([-w / 2, -h / 2, v]); sm.push([w / 2, -h / 2, v]);
      }
      g.add(instOf(new T.SphereGeometry(Math.min(w, d) * 0.03, 6, 5),
        K.mat(0, { color: K.css('--dg-sn', '#e2e7ec'), rough: 0.35, metal: 0.7 }), sm));
      return g;
    }

    /* ================================================================ 高速連接器與互連的零件字彙（2026-09-23）
       2D 是 `site/dg/ai_interconnect.js`。Andy 2026-09-23 親自點名「連接器少了 3D 圖 請補上」，
       所以那張的 `scene: null` 在這一輪補成真 3D（原本寫「不做真 3D」的理由與現在為什麼推翻，
       都留在 2D 檔頭與 SCENES.ai_interconnect 的註解裡，不要把舊理由直接刪掉）。
       ★ 硬規則（規格書 W1-1）：籠、舌片＋**成對**的金手指、背面壓接針、飛越纜線，四件缺一不可。
       ★ 顏色一律走模組色 token，一個色碼都不寫死；兩兩 CIE76 ΔE ≥ 27.4（深淺兩模式都量過）。*/

    /* 這張圖上的 ASIC／GPU：有機基板 ＋ **覆晶的矽晶粒** ＋ 底下一整片球柵陣列。
       ★ 刻意**不沿用** `swasic`（交換器板卡那張的同名零件）：那一支體積最大的一塊是綠色基板，
         在這張圖上會跟板子同色（實測 ΔE76 只有 3.6，關掉標籤完全分不開 ——
         那正是 #244 要收掉的毛病）。這一支把晶粒做成最大的一塊，所以它讀到的是晶片深藍。
       ⚠ 它在這張圖上只是「訊號的起點」，沒有內部細節 —— 晶片本身是半導體鏈那幾張的主題。*/
    function hsAsic(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(put(box(w, h * 0.18, d, K.mat(0, { color: K.css('--dg-m-pcb', '#0E3B32'), rough: 0.6, metal: 0.06 })), 0, -h * 0.34, 0));
      g.add(put(box(w * 0.82, h * 0.5, d * 0.82, K.mat(0, { color: K.css('--dg-m-die', '#1E2E52'), metal: 0.42, rough: 0.4 })), 0, h * 0.02, 0));
      // 邊緣那一圈補強膠：覆晶封裝一定有，它也是「這顆是覆晶不是打線」的證據
      g.add(put(box(w * 0.9, h * 0.1, d * 0.9, K.mat(0, { color: K.css('--dg-organic', '#8a6636'), rough: 0.7, metal: 0.06 })), 0, -h * 0.2, 0));
      g.add(put(ballGrid(K, w * 0.088, w * 0.03, 8, 0, [6, 4]), 0, -h * 0.46, 0));
      return g;
    }

    /* 屏蔽金屬籠（cage）：五片鈑金圍成、開口朝前（+z）；側壁通風孔、籠口一圈 EMI 指片、籠背鰭片。
       為什麼值得畫：**籠子就是高速連接器的識別特徵** —— 它不是外觀件，是為了擋電磁干擾
       與把模組的熱帶出去才存在的。沒有籠子，它跟一個電源端子在外形上分不開。*/
    function hsCage(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const st = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.84, rough: 0.34 });
      const t = Math.min(w, h) * 0.07;
      // 五片鈑金：上、下、左、右、後檔板 —— 開口朝 +z（模組從那一面插進來）
      g.add(mboxes([[w, t, d, 0, h / 2 - t / 2, 0], [w, t, d, 0, -h / 2 + t / 2, 0],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2]], st));
      // 側壁通風孔：800G 模組的熱要從籠子帶走，所以鈑金上一定打了孔
      const vd = K.mat(0, { color: K.css('--dg-void', '#0d1424'), rough: 0.95, metal: 0.02 });
      const hr = Math.min(h, d) * 0.055, hs = [];
      for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) {
        const z = (-1.5 + i) * d * 0.19, y = (-1 + j) * h * 0.26;
        [-1, 1].forEach(s => hs.push([s * (w / 2 - t / 2), y, z, 0, 0, Math.PI / 2]));
      }
      g.add(instOf(new T.CylinderGeometry(hr, hr, t * 1.4, 8, 1, true), vd, hs));
      // 籠口一圈 EMI 指片：模組插進來時被壓住，接地才連續 —— 這一圈就是「屏蔽」兩個字的實體
      const fn = 9, fg = [];
      for (let i = 0; i < fn; i++) {
        const u = (-(fn - 1) / 2 + i) * (w * 0.86 / fn);
        fg.push([u, h / 2 + t * 0.35, d / 2 - t * 1.2, 0.5, 0, 0]);
        fg.push([u, -h / 2 - t * 0.35, d / 2 - t * 1.2, -0.5, 0, 0]);
      }
      g.add(instOf(new T.BoxGeometry(w * 0.86 / fn * 0.58, t * 0.6, d * 0.18), st, fg));
      // 籠背鰭片：熱從模組經籠頂交給空氣（所以它在籠子外面、不在模組裡）
      const fc = 10, fin = [];
      for (let i = 0; i < fc; i++) fin.push([(-(fc - 1) / 2 + i) * (w * 0.9 / fc), h / 2 + h * 0.15, -d * 0.12]);
      g.add(instOf(new T.BoxGeometry(w * 0.9 / fc * 0.32, h * 0.28, d * 0.66), st, fin));
      return g;
    }

    /* 塑膠舌片 ＋ 舌片上下兩面的金手指。
       為什麼值得畫：★ 金手指**成對**排列（一對＝一組差動訊號），每兩對之間夾一根比較寬的接地腳。
       一根一根等距的是低速端子 —— 這是這張圖最容易畫錯、也最容易被一眼看穿的地方。*/
    function hsTongue(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const pl = K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.62, metal: 0.1 });
      g.add(put(box(w, h * 0.34, d, pl), 0, 0, 0));                       // 舌片本體
      g.add(put(box(w * 1.04, h * 0.9, d * 0.16, pl), 0, 0, -d * 0.48));  // 舌片根部那一塊絕緣體
      const au = K.mat(0.18, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.24 });
      const pairs = 5, unit = w * 0.92 / (pairs * 3), sig = [], gnd = [];
      for (let i = 0; i < pairs; i++) {
        const x0 = -w * 0.46 + unit * (i * 3 + 1.5);
        sig.push(x0 - unit * 0.5); sig.push(x0 + unit * 0.5);   // 一對兩根（差動）
        gnd.push(x0 + unit * 1.5);                              // 對與對之間的接地腳（比較寬）
      }
      [1, -1].forEach(s => {
        const y = s * h * 0.2;
        g.add(instOf(new T.BoxGeometry(unit * 0.5, h * 0.06, d * 0.8), au, sig.map(x => [x, y, 0])));
        g.add(instOf(new T.BoxGeometry(unit * 0.92, h * 0.06, d * 0.8), au, gnd.map(x => [x, y, 0])));
        // 前緣倒角：插得進去靠的就是這一小片斜邊
        g.add(instOf(new T.BoxGeometry(unit * 0.5, h * 0.04, d * 0.16), au,
          sig.map(x => [x, y - s * h * 0.03, d * 0.46])));
      });
      return g;
    }

    /* 背面壓接針（press-fit，針腰是「針眼」形）：一整排壓進板子的孔裡。
       為什麼值得畫：★ 壓接針**不是焊上去的** —— 針腰被孔壁夾扁、靠彈性維持接觸，
       所以整顆連接器拔得下來重工。針眼那個開口就是它跟焊接腳最好認的差別。
       材質是磷青銅，所以顏色走 --dg-organic（青銅）而不是錫白。*/
    function hsPin(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const br = K.mat(0, { color: K.css('--dg-organic', '#8a6636'), metal: 0.78, rough: 0.34 });
      const at = gridXZ(10, 3, w * 0.09, d * 0.3, 0);
      const t = Math.max(0.05, w * 0.018);
      g.add(instOf(new T.BoxGeometry(t, h, t), br, at));                       // 針身
      // 針眼：兩片薄壁夾出一個開口（壓進孔裡被壓扁的就是這一段）
      [-1, 1].forEach(s => g.add(instOf(new T.BoxGeometry(t * 0.55, h * 0.3, t), br,
        at.map(a => [a[0] + s * t * 0.85, h * 0.08, a[2]]))));
      // 針尖：導入斜角，不然插不進孔
      g.add(instOf(new T.ConeGeometry(t * 0.62, h * 0.16, 6), br,
        at.map(a => [a[0], -h * 0.5 - h * 0.06, a[2], Math.PI, 0, 0])));
      return g;
    }

    /* 飛越纜線（flyover）：晶片旁的小連接器座 ＋ 幾條架空拉出去的雙軸線纜（twinax）。
       為什麼值得畫：★ 它存在的理由只有一個 —— 同樣的距離，細同軸纜線的損耗比板上銅走線小得多。
       所以它一定是**架空**的（不貼板）。剖開的那一端看得到遮蔽層裡是**兩根等徑導體**，不是一根。*/
    function hsFly(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const jk = K.mat(0, { color: K.css('--dg-fl-sig', '#58C4FF'), rough: 0.7, metal: 0.08 });
      const sh = K.mat(0, { color: K.css('--dg-m-rack', '#B8C2CC'), metal: 0.8, rough: 0.34 });
      const cd = K.mat(0, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.26 });
      const hz = K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.62, metal: 0.1 });
      const r = Math.max(0.2, h * 0.11);
      for (let i = 0; i < 4; i++) {
        const o = (-1.5 + i) * r * 2.3;
        const c = new T.CatmullRomCurve3([
          new T.Vector3(-w * 0.44, -h * 0.34, o), new T.Vector3(-w * 0.18, h * 0.36, o * 0.6),
          new T.Vector3(w * 0.18, h * 0.3, o * 0.6), new T.Vector3(w * 0.44, -h * 0.3, o)]);
        g.add(new T.Mesh(new T.TubeGeometry(c, 20, r, 8, false), jk));
      }
      // 剖開的那一端：遮蔽層（管）＋ 兩根等徑導體（差動對）
      const zc = r * 3.45;
      const e = put(cyl(r * 0.76, r * 1.0, sh, 12), -w * 0.44, -h * 0.34, zc);
      e.rotation.x = Math.PI / 2; g.add(e);
      [-1, 1].forEach(s => {
        const c2 = put(cyl(r * 0.22, r * 1.15, cd, 8), -w * 0.44 + s * r * 0.33, -h * 0.34, zc);
        c2.rotation.x = Math.PI / 2; g.add(c2);
      });
      // 兩端的小連接器座（一端在晶片旁、一端在籠背）
      [-1, 1].forEach(s => g.add(put(box(w * 0.09, h * 0.34, d * 0.95, hz), s * w * 0.47, -h * 0.38, 0)));
      return g;
    }

    /* 母端插槽（受端）：塑膠殼 ＋ 上下兩列懸臂彈片，彈片前端有接觸凸點。
       為什麼值得畫：★ 導通靠的是**彈片被金手指撐開**的那個法向力，不是「插到底就通」；
       插入時接點擦過金手指表面（擦拭）把氧化層刮掉。這兩件事就是連接器真正在賣的東西，
       畫成一條溝就全看不到了。*/
    function hsSlot(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      const pl = K.mat(0, { color: K.css('--dg-m-fanf', '#5A7285'), rough: 0.62, metal: 0.1 });
      const au = K.mat(0.18, { color: K.css('--dg-m-trace', '#E6B95C'), metal: 0.9, rough: 0.24 });
      const t = h * 0.16;
      // 殼：一條開口朝上的溝（上面那一道縫就是卡片插進去的地方）
      g.add(mboxes([[w, t, d, 0, -h / 2 + t / 2, 0],
        [w, h, t, 0, 0, -d / 2 + t / 2], [w, h, t, 0, 0, d / 2 - t / 2],
        [t, h, d, -w / 2 + t / 2, 0, 0], [t, h, d, w / 2 - t / 2, 0, 0]], pl));
      // 上下兩列懸臂彈片：斜著伸進溝裡，前端一顆接觸凸點
      const n = 14, at = [], dot = [];
      for (let i = 0; i < n; i++) {
        const x = (-(n - 1) / 2 + i) * (w * 0.86 / n);
        [-1, 1].forEach(s => {
          at.push([x, s * h * 0.06, s * d * 0.16, s * 0.42, 0, 0]);
          dot.push([x, s * h * 0.14, 0]);
        });
      }
      g.add(instOf(new T.BoxGeometry(w * 0.86 / n * 0.46, h * 0.05, d * 0.5), au, at));
      g.add(instOf(new T.SphereGeometry(Math.min(w * 0.86 / n, h) * 0.16, 7, 5), au, dot));
      return g;
    }

    return { plain, rack, backplane, tray, gpu, chip, hbm, pcb, laminate, cdu, uqd, fan, psu, battery,
      optic, switch: switchBox, substrate, balls, rdl, bridge, die, probe, lid,
      // 兩種模式（DECISIONS #238）的共用件：圓角方塊、流線、粒子貼圖
      _rbox: rbox, _flowPath: flowPath, _spriteTex: spriteTex,
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
      _silk: silk, _microvias: microvias,
      /* ---- 半導體鏈四張的字彙（2026-09-23）。同樣是**多出來的詞**，舊的一個都沒有動。*/
      fetp: fetPlanar, fetf: fetFin, nsheet: nanoSheet, gaagate: gaaGate, wafer: waferDisc,
      czshell: czShell, crucible: czCrucible, susceptor: czSusceptor, melt: czMelt,
      ingot: czIngot, seedrod: czSeed, heater: czHeater, wstack: waferStack,
      hbmcore: hbmCore, hbmbase: hbmBase, tsvcol: tsvCols, ubumprows: ubumpRows,
      wbglay: wbgLayer, wbgbody: wbgBody, wbggate: wbgGate, wbgtop: wbgTop,
      wbgpgan: wbgPgan, wbgelec: wbgElec,
      /* ---- AI 伺服器鏈六張的字彙（2026-09-23，DECISIONS #250）。同樣是**多出來的詞**，舊的一個都沒有動。*/
      abfcore: abfCore, abfbu: abfBuildup, abftrace: abfTrace, abfvia: abfVia,
      abfsr: abfSr, abfpad: abfPad, abfbga: abfBga,
      pcblay: pcbLayer, pcbtrc: pcbTrace, pcbmask: pcbMask, pcbenig: pcbEnig, pcbvia: pcbVia,
      pshelf: psuShelf, pshell: psuShell, pboard: psuBoard, pcardedge: psuCardEdge,
      pbusbar: psuBusbar, pvrm: psuVrm, pbbu: psuBbu, pscap: psuScap,
      timlay: timLayer, ihslid: ihsLid, cplate: coldPlate, cpfin: cpFin, cpport: cpPort,
      lcmani: lcManifold, lcphe: lcPhe,
      fframe: fanFrame, frotor: fanRotor, fhub: fanHub, fmotor: fanMotor,
      fbear: fanBearing, fwire: fanWire, fwall: fanWall, fshroud: fanShroud,
      swboard: swBoard, swasic: swAsic, swcage: swCage, swmod: swModule,
      swgold: swGold, swcpo: swCpo,
      _halfTube: halfTube, _abfY: abfY, _pcbStack: pcbStack, _pcbCuY: pcbCuY,
      _cutSlab: cutSlab, _cutFace: cutFace, _twoSided: twoSided, _hbmLayout: hbmLayout,
      /* ---- 一般電子鏈六張的字彙（2026-09-23）。同樣是**多出來的詞**，舊的一個都沒有動。*/
      pnframe: pnFrame, pnfilm: pnFilm, pnlgp: pnLgp, pnledbar: pnLedBar, pnprism: pnPrism,
      pnpol: pnPol, pnglass: pnGlass, pntft: pnTft, pnlc: pnLc, pncf: pnCf, pndriver: pnDriver,
      mcbase: mcBase, mcmotor: mcMotor, mcenc: mcEnc, mccoup: mcCoup, mcbrg: mcBrg, mcscrew: mcScrew,
      mcnut: mcNut, mcballs: mcBalls, mcreturn: mcReturn, mcrail: mcRail, mcblock: mcBlock, mctable: mcTable,
      cppoly: cpPoly, cpcarbon: cpCarbon, cpfoil: cpFoil, cpshell: cpShell, cpntc: cpNtc,
      cpgrain: cpGrain, cpgb: cpGb, cpelec: cpElec, cppn: cpPn,
      accan: acCan, acsleeve: acSleeve, accore: acCore, acfoil: acFoil, acpore: acPore, acspine: acSpine,
      acoxide: acOxide, acpaper: acPaper, acelyte: acElyte, acseal: acSeal, aclead: acLead,
      acvent: acVent, acsolid: acSolid,
      indbody: indBody, indwind: indWind, indflux: indFlux, indterm: indTerm,
      reslay: resLay, resfilm: resFilm, restrim: resTrim, resglass: resGlass, resterm: resTerm, resback: resBack,
      xtalbase: xtalBase, xtalmount: xtalMount, xtalblank: xtalBlank, xtalelec: xtalElec, xtallid: xtalLid,
      /* ---- 2026-09-23 第二批補的高速連接器（規格書 W1-1）。同樣是**多出來的詞**，舊的一個都沒有動。*/
      hsasic: hsAsic, hscage: hsCage, hstongue: hsTongue, hspin: hsPin, hsfly: hsFly, hsslot: hsSlot,
      _cylX: cylX, _halfBore: halfBore, _halfTubeY: halfTubeY, _halfTubeX: halfTubeX };
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
    /* ★ 2026-09-22 響應式的卡片欄（Andy：「版面需要左右對齊，適當分配左右間隔，讓版面更滿…
       並且會依據螢幕大小變化」）。斷點看**視窗寬度**（跟 style-system 的 media query 同一組數字），
       欄寬看**容器寬度**（側欄開著時容器比較窄，欄就照 grid 的解縮到下限 220）：
         lr     視窗 ≥ 1280：左右兩欄卡片夾著 3D（等於 grid：minmax(220px,1fr) minmax(0,984px) minmax(220px,1fr)）
         r      960～1279：只留右欄，卡片全部靠右（minmax(0,984px) minmax(220px,1fr)）
         below  < 960：卡片移到 3D 底下排成一欄；3D 上改用**編號圓點**標位置（引線只給被選的那一顆）
       欄寬＝那條 grid 的解：1fr 分剩下的、但不少於 220。class 名跟 style-system 共用
       （dgstage / dgstage-l / dgstage-r / dgstage-b，寫在 docs/diagram_restyle_plan.md）。*/
    const COL_MIN = 220, STAGE_MAX = 984;
    const vw = () => (window.innerWidth || W());
    /* ★ 2026-09-22（Andy 的「圖二」：MLCC 的 3D 左右兩欄卡片被切掉、要左右滑才看得到）。
       斷點以前**只看視窗寬度**，但欄寬是從**容器寬度**算的 ——
       視窗 1280 而側欄開著時容器只有 836，兩欄各 220（下限，不准再窄，不然卡片的字會折成一長條）
       就吃掉 440，畫布只剩 396：機櫃被擠成一條，卡片幾乎貼著畫面邊。
       所以兩個條件都要成立：**視窗夠寬**（媒體查詢那組數字）**而且容器塞得下**
       （兩欄至少要留 54% 給模型，不然「左右兩欄」這個版面本身就不成立）。
       塞不下就退一階：兩欄 → 右欄 → 卡片搬到畫布底下。*/
    const fitsCols = (n) => (W() - COL_MIN * n) >= W() * 0.54;
    const mode = () => (vw() >= 1280 && fitsCols(2) ? 'lr' : ((vw() >= 960 && fitsCols(1)) ? 'r' : 'below'));
    const colW = () => { const m = mode(); if (m === 'below') return 0;
      return Math.max(COL_MIN, Math.round((W() - STAGE_MAX) / (m === 'lr' ? 2 : 1))); };
    const cols = () => (mode() === 'lr' ? 2 : (mode() === 'r' ? 1 : 0));
    const narrow = () => mode() !== 'lr';

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, W() / H(), 1, 2000);
    camera.position.set(spec.camera[0], spec.camera[1], spec.camera[2]);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    /* 電影感打光（DECISIONS #238）：ACES 色調映射讓亮部柔和收斂，主光可以開大而不會整片爆白；
       曝光量走 token（--dg-expo），兩種模式各自調。*/
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    /* ★ 2026-09-22（DECISIONS #244，規格書一-2）：開真的陰影。
       以前「扁」的第二個根因就是這裡 —— 托盤與托盤之間、晶片與板子之間完全沒有投影，
       只有一片貼在模型底下的 radial sprite（那片留著當軟接觸陰影，兩者疊加）。
       只有 key 投影、只有大件 castShadow、shadow camera 貼著外接盒收緊 ——
       不收緊的話 1024 的貼圖攤在整個場景上會糊成一團。
       手機（< 960）由 `--dg-shadow-on` 關掉：陰影 pass 等於多畫一次投影件，
       小螢幕看不出差別卻要付這個錢。*/
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    /* ★ 陰影貼圖**不要每幀重畫**。這個場景會動的只有「相機」與「爆炸拆解的那 1.6 秒」——
       而陰影貼圖只跟**光源與物體的位置**有關，相機怎麼轉它都不會變。
       每幀重畫一次等於把 44 顆投影件多畫一遍：實測（容器的軟體渲染）
       8.1 fps → 2.7 fps，直接砍成三分之一。關掉自動更新、只在「東西真的移動了」
       （爆炸拆解、換模式、改寬度）那幾幀補一次，fps 就回到跟改之前同一個量級。*/
    renderer.shadowMap.autoUpdate = false;
    const bumpShadow = () => { renderer.shadowMap.needsUpdate = true; };
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
    // 兩欄（疊在畫布左右）＋ 一個「底下那一排」（窄畫面時卡片搬到這裡，走正常的文件流）
    const colL = document.createElement('div'); colL.className = 'dgstage-l';
    const colR = document.createElement('div'); colR.className = 'dgstage-r';
    layer.appendChild(colL); layer.appendChild(colR);
    el.appendChild(layer);
    const below = document.createElement('div'); below.className = 'dgstage-b'; below.hidden = true;
    el.appendChild(below);
    el.classList.add('dgstage');

    /* E2：打光改成「棚拍」而不是「霓虹」。
       原本有一盞青色 rim light（0x3ee0ff）＋ 每顆材質都帶 emissive，
       所以不管什麼零件都像在發光 —— Andy 說的螢光感就是這兩件事加起來。
       現在：天空光壓低、主光白、補光是中性冷白、底下一點回彈，rim 拿掉。*/
    /* 2026-09-22 兩種模式：燈的**顏色與強度全部是 token**（--dg-l-*／--dg-key…），applyPal 會重讀。
       閱讀模式＝大半球光 ＋ 低主光（柔和環境光遮蔽感、沒有強高光）；
       科技模式＝主光偏強 ＋ 一盞從後方來的冷白輪廓光（電影感）。這裡先給一個中性的起始值。*/
    const hemi = new THREE.HemisphereLight(0xffffff, 0x000000, 0.62); scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffffff, 1.0); key.position.set(60, 90, 70); scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.34); fill.position.set(-70, 40, -60); scene.add(fill);
    const bounce = new THREE.DirectionalLight(0xffffff, 0.16); bounce.position.set(0, -60, 20); scene.add(bounce);
    const rim = new THREE.DirectionalLight(0xffffff, 0.0); rim.position.set(-40, 50, -90); scene.add(rim);
    /* 只有主光投影（規格書一-2）。補光與輪廓光投影只會讓同一個物體出現三組互相打架的影子，
       而且陰影 pass 的成本是「每一盞會投影的燈 × 每一顆 castShadow 的 mesh」。*/
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.bias = -0.0012;            // 自體陰影的條紋（shadow acne）：板子這麼薄一定要給
    key.shadow.normalBias = 0.6;
    scene.add(key.target);

    /* ================================================================ 環境貼圖（規格書一-1）
       ★ 這是「灰」的**最大主因**：PBR 的金屬幾乎全靠環境反射，沒有 envMap 的 metalness
         只會把物件變暗灰 —— 所以以前只好把金屬度壓低，結果銀灰機架、銅件、鰭片
         全都變成霧面塑膠。補上環境貼圖之後金屬才是金屬。
       vendor 的 three 有 `PMREMGenerator`（核心）但**沒有 RoomEnvironment**（那是 examples），
       而且不准為了這個多塞一支 vendor 檔（Andy 公司網路擋 CDN）——
       所以自己搭一個程序式的小棚：一個包住原點的暗房 ＋ 上方大柔光板 ＋ 左冷右暖兩片補光板
       ＋ 後上方一片輪廓光板 ＋ 下方暗板，再用 `fromScene()` 捲成 envMap。
       兩種模式各生一份（顏色不同），切模式時重生。*/
    /* 環境貼圖一個模式**只生一次**就快取起來（envByPal）。
       PMREM 要畫六個面再做多階模糊，在軟體渲染的環境裡要好幾百毫秒，而且是**同步**的 ——
       每切一次模式就重生會把 rAF 卡住，畫面上看到的就是「切配色的時候整個停一下」。*/
    let pmrem = null, envPal = '';
    const envByPal = {};
    const cssRead0 = (n) => { try { return getComputedStyle(el).getPropertyValue(n).trim(); } catch (e) { return ''; } };
    const envCol = (n, d) => new THREE.Color(cssRead0(n) || d);
    function buildEnv(key) {
      try {
        if (envByPal[key]) { scene.environment = envByPal[key]; return; }
        if (!pmrem) { pmrem = new THREE.PMREMGenerator(renderer); pmrem.compileEquirectangularShader(); }
        const es = new THREE.Scene();
        const geos = [];
        /* 面板一律用 MeshBasicMaterial：PMREM 是把這個小場景「拍」成環境光，
           面板本身就是光源，不需要再被照亮。*/
        const panel = (w, h, hex, dflt, px, py, pz, rx, ry) => {
          const gg = new THREE.PlaneGeometry(w, h); geos.push(gg);
          const mm = new THREE.MeshBasicMaterial({ color: envCol(hex, dflt), side: THREE.DoubleSide });
          const me = new THREE.Mesh(gg, mm);
          me.position.set(px, py, pz); me.rotation.set(rx || 0, ry || 0, 0);
          es.add(me); return me;
        };
        es.background = envCol('--dg-env-bot', '#0A0F18');                 // 暗房底色（照不到的地方是什麼顏色）
        panel(26, 26, '--dg-env-top', '#C8D8F0', 0, 9, 0, Math.PI / 2, 0);  // 上方大柔光板（主要的反射來源）
        panel(14, 20, '--dg-env-l', '#4E7FB8', -9, 1, 0, 0, Math.PI / 2);   // 左：冷色補光
        panel(14, 20, '--dg-env-r', '#C08A52', 9, 1, 0, 0, Math.PI / 2);    // 右：暖色補光（冷暖對比就是從這裡來的）
        panel(18, 10, '--dg-env-back', '#121A2A', 0, 5, -9, 0, 0);          // 後上方：勾邊緣的那一道
        panel(26, 26, '--dg-env-bot', '#0A0F18', 0, -9, 0, Math.PI / 2, 0); // 下方暗板：底面要暗，不然整台會浮起來
        /* 用「先拍成一張小的 cubemap、再交給 PMREM」而不是 fromScene()：
           fromScene 內部固定用 256 的立方體，產生的 cubeUV 貼圖很大；
           我們的棚只有五片純色板，64 就夠了（模糊之後看不出差別），
           而 envMap 的成本在 fragment shader 的取樣 —— 貼圖小很多才有機會省下來。*/
        const rt = new THREE.WebGLCubeRenderTarget(64);
        const cc = new THREE.CubeCamera(0.5, 60, rt);
        cc.update(renderer, es);
        const t = pmrem.fromCubemap(rt.texture).texture;
        rt.dispose();
        geos.forEach(g => g.dispose());
        es.traverse(x => { if (x.material) x.material.dispose(); });
        envByPal[key] = t;
        scene.environment = t;
      } catch (e) {
        /* 生不出來（極舊的 WebGL1、浮點貼圖不支援）就維持沒有 envMap 的樣子 ——
           畫面會回到「比較灰」但不會掛掉。*/
        scene.environment = null;
      }
    }

    const root = new THREE.Group(); scene.add(root);
    const picks = [];            // 可以點的 group
    /* frames：機櫃框那種「透過它點裡面的東西」的零件（frame:true）。
       ★ 2026-09-22：以前完全不參與 raycast，於是從側面看、射線從托盤縫隙穿過去、
         只碰到玻璃側板的時候，點下去等於點到背景 —— 驗收就會偶爾紅（跟相機轉到哪有關）。
         現在它排在**最後一順位**：射線先找非框的零件，都沒有才算點到框（＝選到「機櫃與機構件」）。*/
    const frames = [];
    const byIdx = [];            // 每個零件的所有 mesh + 材質，highlight 時用
    const spinners = [];         // E4：會自己轉的東西（風扇葉輪）
    const leds = [];             // E4：會呼吸的指示燈材質
    const flowPts = [], flowAll = [], flowSeen = new Set();   // 圖九 2-1：電流粒子
    /* ★ C6（Andy 2026-09-23：「3D 圖 幫我都做成會有動畫像是這儀器再運作」）。
       四種動法，全部是**零件自己在動或能量在流動**，不是鏡頭在繞：
         ① flow    沿路徑跑的粒子   —— 冷卻液、氣流、光、電流、差動訊號（既有機制，這次補 dir／bidir／gate）
         ② spin    零件繞自己的軸轉 —— 扇葉、螺桿、晶碇（既有機制，這次讓場景可以直接宣告）
         ③ ispin   陣列零件各自轉   —— 風扇牆（InstancedMesh，1 個 draw call 也要會轉）
         ④ pulse   一組零件依序點亮 —— 製程一站一站、訊號穿層、充放電（新增）
         ⑤ move    零件沿一軸位移   —— 螺帽沿軸走、晶碇上提、晶粒被取放（新增）
       全部不重建幾何：pulse 只改材質的 uniform（顏色／emissive），move 只改 position，
       ispin 只改 instanceMatrix。每幀的預算都花在「看得出來的變化」上，不是花在重建 buffer。*/
    const ispinners = [];        // C6 ③：陣列零件（InstancedMesh）各自繞自己的中心轉
    const pulses = [];           // C6 ④：一組零件依序點亮
    const movers = [];           // C6 ⑤：沿一軸位移的零件
    let labelDown = null;        // 這次按下去是從某個標籤開始的（可能只是想轉視角）
    let stickyBelow = new Set(); // 被排到底下那一排的卡片（黏住，直到欄寬／模式／選取變了才重排）；宣告在這裡是為了避開 TDZ
    let compactSide = { L: false, R: false };   // 這一欄的卡片有沒有收成一行（同樣黏住，同樣在欄寬／模式／選取變了才重算）

    /* ★ 2026-09-22 DECISIONS #238：只剩兩種模式 —— 暗色「科技」／亮色「閱讀」。
       舊的 soft／calm／casual 不再是模式，但舊的 localStorage 與還沒改版的鈕會送這些名字進來，
       一律映射（柔和、休閒 → 閱讀；沉穩 → 科技），不要讓 3D 因為一個舊名字掛掉。
       沒指定就跟著全站主題：淺色主題 → 閱讀、深色主題 → 科技。
       ★ 掛 data-pal 一定要在建零件**之前**：kit() 是在建零件那一刻讀 token 的，
         先建再掛的話所有材質都是科技的值，閱讀模式只剩 applyPal 重讀得到的那幾顆。*/
    const PALS = ['tech', 'read'];
    const PAL_NAME = { tech: '科技', read: '閱讀' };
    const PAL_LEGACY = { soft: 'read', casual: 'read', calm: 'tech' };
    const palByTheme = () => { try { return document.documentElement.dataset.theme === 'light' ? 'read' : 'tech'; } catch (e) { return 'tech'; } };
    const pal0 = (() => { const n = o.pal || palByTheme(); return PALS.includes(n) ? n : (PAL_LEGACY[n] || 'tech'); })();
    el.dataset.pal = pal0;
    const cssRead = (n) => getComputedStyle(el).getPropertyValue(n).trim();
    /* 卡片跟到的「元件顏色」：有角色就是角色色（訊號藍／電力橘／液冷青綠），沒有就是材質族的底色。
       明度依模式夾住（token：--dg-card-lmin／--dg-card-lmax）：
         · 科技（深底、圓點字是深色）→ 太暗的底色（板子的墨綠、矽的深藍、模封的黑）往 --dg-lit 拉亮到看得見為止；
         · 閱讀（白卡、圓點字是白色）→ 太亮的（玻璃、陶瓷、淺灰）壓到 lmax 以下，不然 .sel 卡片的標題字與圓點底
           會變成「白卡上的淡藍字」（v9 半導體場景的「散熱上蓋」就是這樣看不見的）。
       token 是跟 data-pal 走的，所以 applyPal() 每次切模式都要用當下的 token 重算一次，不能只在掛場景時算。*/
    const calcElColor = (K, role) => {
      const roleHex = role && ROLE_TOKENS[role] ? cssRead(ROLE_TOKENS[role]) : '';
      const baseHex = (K.baseVar && cssRead(K.baseVar)) || K.base;
      const c = new THREE.Color(roleHex || baseHex || '#888888');
      const hsl = {}; c.getHSL(hsl);
      const lmin = parseFloat(cssRead('--dg-card-lmin')) || 0.48;
      const lmax = parseFloat(cssRead('--dg-card-lmax')) || 1;
      if (hsl.l < lmin) c.lerp(new THREE.Color(cssRead('--dg-lit') || '#ffffff'), (lmin - hsl.l) / (1 - hsl.l) * 1.15);
      /* 上限用 sRGB 的明度夾（眼睛看到的那個）：getHSL 預設回的是線性工作空間的明度，
         線性 .40 換成 sRGB 大約是 .66 —— 用它夾出來的顏色在白卡上還是淡的。*/
      const srgb = {}; c.getHSL(srgb, THREE.SRGBColorSpace);
      if (srgb.l > lmax) c.setHSL(srgb.h, Math.max(srgb.s, 0.35), lmax, THREE.SRGBColorSpace);
      return '#' + c.getHexString();
    };
    /* 爆炸拆解（DECISIONS #238，行為在 #246 改掉）：每個 group 記住「原位」與「拆開的位移」，
       expT 0→1 之間插值。
       ★ 2026-09-23（DECISIONS #246，Andy：「所有 3D 圖都需要預設是收攏的，游標移動過去才會自動分開」）：
         進場一律 expT = 0（看起來是組裝好的成品），游標移進容器才補間到 1、移開再收回 0。*/
    let expT = 0;
    const explodable = [];
    /* ★ 按需渲染（#245）的兩個旗標宣告提前到這裡。
       爆炸補間（#246）在「建完場景、還沒進 tick()」的階段就會呼叫 markDirty()，
       留在原本 tick() 上面那一段（const 宣告）會踩到 TDZ，3D 直接退回平面圖。*/
    let dirty = true, lastDraw = 0;
    const markDirty = () => { dirty = true; };
    /* 一個 group 的最終位置 ＝ 原位 ＋ 爆炸位移 × expT ＋ 運轉位移（C6 ⑤ move）。
       兩件事必須疊加而不是互相覆寫：螺帽沿軸走的時候，使用者可能同時把圖拆開。*/
    const place = (g) => {
      const b = g.userData.base, e = g.userData.ex || [0, 0, 0], v = g.userData.mv;
      g.position.set(b.x + e[0] * expT + (v ? v.x : 0),
        b.y + e[1] * expT + (v ? v.y : 0),
        b.z + e[2] * expT + (v ? v.z : 0));
    };
    const applyExplode = (t) => {
      expT = Math.max(0, Math.min(1, t));
      explodable.forEach(place);
      bumpShadow();     // 零件真的移動了 → 這一幀要重畫陰影貼圖（見 shadowMap.autoUpdate）
      markDirty();      // #245：補間的每一幀都要真的畫出來，不能被「沒變就不畫」擋掉
    };
    /* 「零件離原位最遠跑了多少」。驗收用它證明**收攏態真的是合攏的**（t=0 時一定是 0），
       而不是只看 expT 這個變數 —— 變數改了不等於零件動了。*/
    const exMove = () => {
      let m = 0;
      explodable.forEach(g => {
        const e = g.userData.ex, k = Math.hypot(e[0], e[1], e[2]) * expT;
        if (k > m) m = k;
      });
      return +m.toFixed(3);
    };

    spec.parts.forEach((p, idx) => {
      const hex = o.color(p.seg) || '#8ea0c4';       // 環節色：只給卡片的小圓點與「被點的那一顆」
      // 零件身分：沒宣告就自動補一個（同場景內唯一，但跟 2D 的 data-part 對不起來）
      const pkey = p.part || (p.seg + '#3d' + idx);
      const fam = p.mat || FAMILY[p.kind] || 'metal';
      const K = kit(THREE, fam, p.ghost, cssRead, p.role);
      const build = B[p.kind] || B.plain;
      const proto = build(p, K);
      // 引線的錨點用**真的**外接盒頂端：kind 畫出來的東西常常比 box 高（鰭片、上蓋、扇框）
      const bb = new THREE.Box3().setFromObject(proto);
      const topY = Number.isFinite(bb.max.y) ? bb.max.y : p.box[1] / 2;
      const n = p.n || 1, gap = p.gap || 0, axis = p.axis || 'x';
      const groups = [], meshes = [];
      for (let i = 0; i < n; i++) {
        // 重複件用 clone：幾何與材質是共用的，記憶體省下來，highlight 也一次全部吃到
        const g = i === 0 ? proto : proto.clone(true);
        const off = (i - (n - 1) / 2) * gap;
        g.position.set(p.at[0] + (axis === 'x' ? off : 0),
          p.at[1] + (axis === 'y' ? off : 0),
          p.at[2] + (axis === 'z' ? off : 0));
        g.userData = { seg: p.seg, part: pkey, idx, name: p.name, note: p.note,
          base: g.position.clone(), ex: p.ex || [0, 0, 0], frame: !!p.frame };
        if (p.ex) explodable.push(g);
        g.traverse(x => {
          if (x.isMesh) meshes.push(x);
          if (x.userData && x.userData.spin) spinners.push(x);
          if (x.isInstancedMesh && x.userData && x.userData.ispin) ispinners.push(x);
          // 圖九 2-1：電流粒子。clone 出來的重複件共用同一份 geometry，
          // 所以同一份只能推一次，不然一幀會被推 n 次、速度變 n 倍。
          if (x.isPoints && x.userData && x.userData.flow && !flowSeen.has(x.geometry)) {
            flowSeen.add(x.geometry); flowPts.push(x);
          }
          if (x.isPoints && x.userData && x.userData.flow) flowAll.push(x);
        });
        root.add(g); groups.push(g);
        if (!p.frame) picks.push(g); else frames.push(g);
      }
      /* 場景層級的流線（水路／光路／氣流）掛在指定的零件上：跟它共用材質工具箱，
         點別的環節時它會跟著零件一起淡出；粒子跟走線的電流走同一套 stepFlows。*/
      (spec.flows || []).filter(f => f.part === pkey).forEach(f => {
        const fg = B._flowPath(K, f);
        fg.userData = { seg: p.seg, part: pkey, idx, flowOf: pkey };
        fg.traverse(x => {
          if (x.isMesh) meshes.push(x);
          if (x.isPoints && x.userData && x.userData.flow) { flowPts.push(x); flowAll.push(x); flowSeen.add(x.geometry); }
        });
        root.add(fg); groups.push(fg);
      });
      K.mats.forEach(m => { if (m.userData && m.userData.led) leds.push(m); });
      const elColor = calcElColor(K, p.role);   // 卡片／引線／圓點的顏色（依模式夾明度，切模式時 applyPal 會重算）
      byIdx[idx] = {
        seg: p.seg, part: pkey, alias: p.alias || [], groups, meshes, hex, ghost: !!p.ghost, name: p.name, note: p.note,
        fam, role: p.role || '', elColor, kit: K,
        mats: K.mats.slice(),
        baseOp: new Map(K.mats.map(m => [m, m.opacity])),
        baseCol: new Map(K.mats.map(m => [m, m.color.clone()])),
        // 引線接在零件頂端中央：接在中心的話線會插進零件裡看不到。
        // 零件可以自己指定 anchor（例如 MLCC 的端電極是兩端各一塊，中間是空的，頂端中央會指到空氣）
        anchor: p.anchor ? new THREE.Vector3(p.anchor[0], p.anchor[1], p.anchor[2]) : new THREE.Vector3(0, topY, 0),
      };

      /* 標籤：DOM 疊上去，不是畫進畫布，所以選得起來、也還驗得到文字重疊。
         2026-09-22 卡片語言（DECISIONS #238 ＋ Andy 推薦一）：編號圓點 ＋ 名稱 ＋ 說明 ＋ 台股晶片。
         給 style-system 那邊的介面（寫在 docs/diagram_restyle_plan.md）：
           --c             ＝ 這張卡片指到的元件顏色（邊框、編號圓點、引線、端點都用它）
           data-dgcolor    ＝ 同上（給不吃 CSS 變數的量測用）
           data-dgseg      ＝ 環節色（小圓點 .segdot 用；點零件時零件本體只提亮到這個顏色）
           data-dgno       ＝ 編號（01、02…，畫在 em.no3d 裡）
           data-dgrole     ＝ sig|pwr|cool|opt|''（角色，style-system 想依角色配色可以用）*/
      const d = document.createElement('div');
      d.className = 'lbl3d';
      d.innerHTML = `<em class="no3d"></em><b></b><i></i><u class="chips3d"></u>`;
      d.querySelector('em').textContent = String(idx + 1).padStart(2, '0');
      d.querySelector('b').textContent = p.name;
      // v3 §4 中英雙語標題：英文一行排在中文底下
      if (EN[pkey]) { const en = document.createElement('small'); en.className = 'en'; en.textContent = EN[pkey]; d.querySelector('b').appendChild(en); }
      d.querySelector('i').textContent = p.note || '';
      d.dataset.seg = p.seg;
      d.dataset.dgcolor = elColor; d.dataset.dgseg = hex; d.dataset.dgno = String(idx + 1).padStart(2, '0');
      d.dataset.dgrole = p.role || ''; d.dataset.dgpart = pkey;
      d.style.setProperty('--seg', hex);
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
      /* ★ 2026-09-23（DECISIONS #250）：`codes: []` ＝ **明說這個零件台股沒有直接對應**，
         不是「沒寫」。以前寫的是 `p.codes && p.codes.length`，空陣列會退回去列「這個環節的台股」——
         而那正是錯誤宣稱的來源：液冷那張的「裸晶 die」掛在 thermal 環節上，
         退回去就會列出奇鋐、雙鴻，等於說散熱廠在做那顆晶片。
         判斷改成「有沒有給 codes 這個欄位」：給了空陣列就照它，卡片顯示「台股無直接對應」。
         既有場景一個都沒受影響（它們的 codes 從來沒有空陣列）。*/
      const mem = p.codes
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
      d.style.setProperty('--c', elColor);   // 卡片的顏色＝它指到的元件的顏色（同色系串聯）
      d.style.setProperty('--dg-card-c', elColor);   // style-system 的卡片 CSS 吃這個名字（docs/diagram_restyle_plan.md）
      // 標籤本身也要可以點：機櫃裡的小零件（UQD、光模組）用滑鼠很難精準打到，
      // 點名字是最直覺的路。父層 pointerEvents 是 none，這裡個別開回來。
      d.style.pointerEvents = 'auto';
      d.style.cursor = 'pointer';
      d.title = p.note || p.name;
      d.addEventListener('pointerdown', (e) => {
        labelDown = { seg: p.seg, data: { seg: p.seg, part: pkey, idx, name: p.name, note: p.note } };
        /* 窄畫面時卡片在畫布底下、走文件流：按卡片就只是選它，**不要**轉給畫布 ——
           轉過去等於「手指一碰清單就開始轉機櫃」，頁面也捲不動。*/
        if (lastMode === 'below') { downAt = { x: e.clientX, y: e.clientY }; return; }
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
      colR.appendChild(d);                 // 先放右欄，layoutLabels 會依模式搬
      byIdx[idx].el = d;
      // 引線：一條折線 ＋ 零件端的小圓點（科技模式外面再套一圈發光暈，用 CSS 的 filter 做）
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('class', 'ld');
      const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      halo.setAttribute('class', 'ld-halo'); halo.setAttribute('r', '6');
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('class', 'ld-dot'); dot.setAttribute('r', '2.6');
      // 窄畫面用的編號圓點（畫在零件的投影點上；卡片在底下用同一個編號對得起來）
      const no = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      no.setAttribute('class', 'ld-no');
      const noC = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); noC.setAttribute('r', '9');
      const noT = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      noT.setAttribute('text-anchor', 'middle'); noT.setAttribute('dy', '4.2'); noT.textContent = String(idx + 1).padStart(2, '0');
      no.appendChild(noC); no.appendChild(noT); no.style.display = 'none';
      [path, halo, dot, no].forEach(x => { x.style.setProperty('--c', elColor); x.style.setProperty('--dg-card-c', elColor); lead.appendChild(x); });
      dot.setAttribute('stroke', elColor);        // main 的 .ld-dot 是「底色填滿 ＋ 元件色描邊 ＋ 元件色光暈」，描邊由這裡餵
      byIdx[idx].path = path; byIdx[idx].dot = dot; byIdx[idx].halo = halo; byIdx[idx].no = no;
    });

    /* ================================================================ C6：把場景宣告的動畫接到零件上
       SCENES 裡只寫「哪個零件、怎麼動」（宣告），真正的幾何與材質完全不知道自己會動 ——
       這樣同一套工具可以給 19 個場景用，而不是 19 份各寫一套。
       三件事都靠零件身分（part key）去找，找不到就靜靜跳過，不讓一個打錯的 key 把整張圖弄掛。*/
    /* ⚠ 不能借用下面那支 isPart：它宣告在高亮那一段（const 箭頭函式），
       這裡跑得比它早，用它會踩到 TDZ、整個 3D 退回平面圖（#246 踩過同一個坑）。*/
    const isPartKey = (p, key) => !!key && (p.part === key || (p.alias || []).indexOf(key) >= 0);
    const findPart = (key) => byIdx.filter(Boolean).find(p => isPartKey(p, key)) || null;
    /* ② spin：讓某個零件的整個 group 繞自己的軸轉（螺桿、晶碇、聯軸器）。
       零件的幾何本來就是以自己的中心為原點建的，所以繞 group 的軸轉 ＝ 繞零件自己的軸轉。*/
    (spec.spins || []).forEach(sp => {
      const p = findPart(sp.part); if (!p) return;
      p.groups.forEach(g => {
        g.userData.spin = { axis: sp.axis || 'y', speed: sp.speed || 1, base: sp.speed || 1, sync: sp.sync || '' };
        spinners.push(g);
      });
    });
    /* ④ pulse：一組零件**依序**點亮。用在「能量或訊號在一連串零件之間傳遞」——
       製程一站一站、訊號穿層、背光一層一層往上。
       被動元件本身不動，動的是電，所以只改顏色與 emissive，幾何一個頂點都不碰。*/
    (spec.pulses || []).forEach(pg => {
      const items = (pg.parts || []).map(findPart).filter(Boolean).map(p => ({ p, k: 0 }));
      if (!items.length) return;
      pulses.push({ items, period: pg.period || 3, sharp: pg.sharp || 8, phase: pg.phase || 0,
        amp: pg.amp == null ? 1 : pg.amp, token: ROLE_TOKENS[pg.kind] || '--dg-fl-sig' });
    });
    /* ⑤ move：零件沿一軸位移。pingpong ＝ 往復（螺帽沿軸走、晶圓在站之間往返），
       saw ＝ 單向循環（滾珠回流）。位移是疊在爆炸位移上的（見 place）。*/
    (spec.moves || []).forEach(mo => {
      const groups = [];
      (mo.parts || [mo.part]).forEach(key => {
        const p = findPart(key); if (!p) return;
        p.groups.forEach(g => { g.userData.mv = { x: 0, y: 0, z: 0 }; groups.push(g); });
      });
      if (!groups.length) return;
      movers.push({ name: mo.name || '', groups, axis: mo.axis || 'x', amp: mo.amp || 1,
        period: mo.period || 4, mode: mo.mode || 'pingpong', phase: mo.phase || 0, off: 0, vel: 0 });
    });

    /* 柔和的接觸陰影（兩種模式都要「柔和環境陰影」）：真的 shadow map 要幾百顆 mesh 都 castShadow，
       太貴；改用一片 radial gradient 的圓盤墊在模型底下 —— 1 個 draw call、40 個三角形。
       大小照**拆開之後**的外接盒算，顏色與不透明度走 token（--dg-shadow／--dg-shadow-a）。*/
    applyExplode(1);
    const shadowMat = new THREE.MeshBasicMaterial({ map: B._spriteTex ? B._spriteTex() : null, transparent: true,
      opacity: 0.4, depthWrite: false, color: new THREE.Color('#000000') });
    shadowMat.userData = { shadow: true };
    const shadowMesh = (() => {
      const bb = new THREE.Box3().setFromObject(root);
      const sz = bb.getSize(new THREE.Vector3());
      const m = new THREE.Mesh(new THREE.CircleGeometry(1, 40), shadowMat);
      m.rotation.x = -Math.PI / 2;
      m.scale.set(Math.max(sz.x, 1) * 0.72, Math.max(sz.z, 1) * 0.72, 1);
      m.position.set((bb.min.x + bb.max.x) / 2, bb.min.y - 0.4, (bb.min.z + bb.max.z) / 2);
      m.renderOrder = -1;
      return m;
    })();
    scene.add(shadowMesh);

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
      /* ★ 2026-09-23：取景一律用「**拆開之後**」的外接盒。
         進場改成收攏（#246）之後，`reset()` 在收攏狀態重算會得到比較小的盒子 →
         相機比第一次進來時更靠近，「重設視角真的回到預設」那條驗收就紅
         （實測 [114.3, 79.5, 134.2] → [103.7, 77.0, 124.6]，近了 9%）。
         做法：量之前先暫時攤開、量完立刻還原 —— 同一幀內完成，畫面上看不到。 */
      const keepT = expT;
      if (keepT !== 1) applyExplode(1);
      const box = new THREE.Box3().setFromObject(root);
      const sph = box.getBoundingSphere(new THREE.Sphere());
      const size = box.getSize(new THREE.Vector3());
      const vfov = camera.fov * Math.PI / 180;
      const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
      /* 用「外接盒」而不是「外接球」算距離：球對又扁又寬的封裝剖面會多退 30%，
         畫面中間只剩一小塊。半個深度是留給轉動時最靠近相機的那一角。
         E1 之後左右各被標籤欄吃掉一塊，所以水平方向要照「還剩多寬」再退一點。 */
      const usable = Math.max(140, W() - colW() * cols());
      const shrink = W() / usable;
      const halfW = Math.max(size.x, size.z) / 2 * shrink, halfH = size.y / 2, halfD = Math.max(size.x, size.z) / 2;
      /* 2026-09-22 第二輪（Andy：「畫布要把中欄填滿」）：模型要吃到畫布高度的 ~90%。
         以前是「外接盒 ＋ 整個半深度 ＋ 6% 邊」，機櫃只佔六成、四周一大片黑。
         現在外接盒佔 94%、轉動的深度餘量只留三分之一（最靠近相機的那一角偶爾會貼邊，接受）。*/
      const dist = (Math.max(halfH / Math.tan(vfov / 2), halfW / Math.tan(hfov / 2)) / 0.94 + halfD * 0.33) * (spec.fit || 1);
      const dir = new THREE.Vector3(spec.camera[0], spec.camera[1], spec.camera[2])
        .sub(new THREE.Vector3(spec.target[0], spec.target[1], spec.target[2])).normalize();
      controls.target.copy(sph.center);
      camera.position.copy(sph.center).addScaledVector(dir, dist);
      controls.minDistance = dist * 0.28; controls.maxDistance = dist * 2.6;
      camera.updateProjectionMatrix();
      controls.update();
      if (keepT !== 1) applyExplode(keepT);       // 還原成量之前的展開程度
    };
    fitCamera();

    /* ================================================================ 真陰影的兩件事（規格書一-2）
       ① shadow camera 要**貼著模型的外接盒**收緊。1024 的貼圖攤在預設的 ±5 正交範圍上
          （或反過來攤在整個場景上）都會糊成一片灰，看起來像髒掉而不是像影子。
       ② castShadow **只給大件**。一個零件有幾十顆小 mesh（錫球、微孔、走線、端子），
          全部投影等於把整個場景再畫一次：陰影 pass 的三角形與 draw call 都會翻倍，
          而使用者看到的差別是零 —— 一塊板子的影子就是那塊板子的輪廓。
          做法：每個零件取**體積最大的前三顆** mesh，而且那顆本身要「便宜」（≤ 600 個三角形）
          且不透明（玻璃、AO 墊、流線不投影）。*/
    const fitShadow = () => {
      const bb = new THREE.Box3().setFromObject(root);
      const c = bb.getCenter(new THREE.Vector3()), sz = bb.getSize(new THREE.Vector3());
      const r = Math.max(sz.x, sz.y, sz.z) * 0.78 + 2;
      /* 主光的方向刻意**偏到右側**而不是「跟相機同一邊的右上前 45°」：
         光跟相機同向時影子全部落在物體背後，等於做了陰影卻看不到
         （第一版的 MLCC 就是這樣，三個零件一個影子都看不見）。
         偏右之後影子往左前方落，預設視角就看得到，而且正面仍然吃得到掠射光。*/
      const dir = new THREE.Vector3(0.84, 0.78, 0.16).normalize();
      key.position.copy(c).addScaledVector(dir, r * 2.2);
      key.target.position.copy(c); key.target.updateMatrixWorld();
      const cam = key.shadow.camera;
      cam.left = -r; cam.right = r; cam.top = r; cam.bottom = -r;
      cam.near = Math.max(0.5, r * 0.4); cam.far = r * 4.4;
      cam.updateProjectionMatrix();
      bumpShadow();
    };
    /* 真陰影的開關（規格書一-2 的效能備案）：窄畫面關掉 —— 陰影 pass 等於把投影件再畫一次，
       小螢幕看不出差別卻要付這個錢。`--dg-shadow` 已經被「底下那片軟接觸陰影的**顏色**」佔用了，
       所以開關用 `--dg-shadow-on`。*/
    const applyShadowMode = () => {
      /* ⚠ 不可以寫成 `parseFloat(x) || 1`：token 是 "0" 的時候 parseFloat 回 0，
         `0 || 1` 會變成 1 —— 開關寫了等於沒寫（2026-09-22 實測踩到）。*/
      const raw = parseFloat(cssRead0('--dg-shadow-on'));
      const on = Number.isFinite(raw) ? raw : 1;
      const want = on > 0.5 && (window.innerWidth || W()) >= 960;
      if (renderer.shadowMap.enabled !== want) {
        renderer.shadowMap.enabled = want;
        // shader 會因為「有沒有陰影」而不同，不重編的話開關等於沒按
        scene.traverse(x => { if (x.isMesh && x.material) x.material.needsUpdate = true; });
      }
      key.castShadow = want;
      bumpShadow();
      return want;
    };
    const SHADOW_MAX = 60;          // 投影件的硬上限（驗收也用這個數字：太多＝效能會爆）
    const markShadows = () => {
      let n = 0;
      byIdx.forEach(p => {
        if (!p || p.ghost) return;
        const cand = [];
        p.meshes.forEach(x => {
          if (!x.geometry || !x.material) return;
          const ud = (x.material.userData) || {};
          if (ud.ao || ud.glass || ud.glow || ud.flowPts || ud.flowLine) return;   // 墊片、玻璃、流線不投影
          if (x.material.transparent && x.material.opacity < 0.95) return;
          const gi = x.geometry.index, gp = x.geometry.attributes.position;
          const tris = Math.round(((gi ? gi.count : (gp ? gp.count : 0)) / 3)) * (x.isInstancedMesh ? x.count : 1);
          if (tris > 600) return;                                                  // 陣列小件（錫球、凸塊）太貴
          if (!x.geometry.boundingBox) x.geometry.computeBoundingBox();
          const sz = x.geometry.boundingBox.getSize(new THREE.Vector3());
          cand.push({ x, v: Math.abs(sz.x * sz.y * sz.z) * (x.scale.x * x.scale.y * x.scale.z || 1) });
        });
        cand.sort((a, b) => b.v - a.v);
        cand.slice(0, 3).forEach(o2 => {
          if (n >= SHADOW_MAX) return;
          o2.x.castShadow = true; o2.x.receiveShadow = true; n++;
        });
      });
      return n;
    };
    markShadows();
    fitShadow();

    // ---- 點零件：接回原本那條路（亮起來 ＋ 帶出台股清單）
    const ray = new THREE.Raycaster(); const ptr = new THREE.Vector2();
    let downAt = null;
    const toNdc = (e) => { const r = renderer.domElement.getBoundingClientRect();
      ptr.x = ((e.clientX - r.left) / r.width) * 2 - 1; ptr.y = -((e.clientY - r.top) / r.height) * 2 + 1; };
    // 零件現在是 Group（E3 之後一個零件好幾顆 mesh），所以 raycast 要遞迴，
    // 打到的是某顆小零件 —— 往上走到帶 seg 的那一層才知道它屬於誰
    const owner = (obj) => { let x = obj; while (x && !(x.userData && x.userData.seg)) x = x.parent; return x; };
    const hit = () => {
      ray.setFromCamera(ptr, camera);
      const xs = ray.intersectObjects(picks.concat(frames), true);
      // 先找非框的零件（透過玻璃點得到裡面的托盤），一個都沒有才算點到框本身
      const inner = xs.find(x => { const g = owner(x.object); return g && !g.userData.frame; });
      const pick = inner || xs[0];
      return pick && owner(pick.object);
    };
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
      if (!m) {
        /* ★ #246：沒有 hover 的裝置（手機／平板）收不到 pointerenter，
           改成「點背景＝展開／收攏切換」。點零件仍然是選零件，兩件事不打架。選擇要記住（EXP_KEY）。*/
        if (!canHover) { setExplode(expTarget !== 1); expSave(expTarget === 1); }
        if (o.onBg) o.onBg();
      }
    };
    renderer.domElement.addEventListener('pointerup', onUp);
    // 沒抓到 pointer capture 時（少數瀏覽器）放開會落在標籤上，補一條同樣的路；
    // onUp 第一次跑完就把 downAt 清掉，所以兩邊都收到也只會處理一次。
    layer.addEventListener('pointerup', onUp);
    below.addEventListener('pointerup', onUp);      // 窄畫面時卡片在底下那一排，放開也要收得到
    renderer.domElement.addEventListener('pointermove', (e) => {
      toNdc(e); renderer.domElement.style.cursor = hit() ? 'pointer' : 'grab';
    });

    /* ---- E4：動態／靜止。
       動態＝場景緩慢自轉 ＋ 風扇轉 ＋ 指示燈呼吸；靜止＝一律不動。
       使用者一動手就先把自轉停掉（不然會跟他搶方向），放開兩秒半再接回去。*/
    let anim = o.anim !== false, userHold = false, holdT = null;
    let expAnim = null;
    const reduced = (() => { try { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) { return false; } })();

    /* ================================================================ #246：收攏 → 游標移過去才爆開
       Andy 2026-09-23：「所有 3D 圖都需要預設是收攏的，游標移動過去才會自動分開，變成爆炸圖」。
       以前（#238）是「一進來就自己拉開 1.6 秒」—— 使用者還沒看清楚它是什麼，零件就散了。
       現在：
         進場            expT = 0（組裝好的成品）
         游標移進容器    0 → 1，EXP_IN 毫秒 ease-out（慢一點，像被拆開）
         游標移開        1 → 0，EXP_OUT 毫秒（快一點，像彈回去）
         沒有 hover 的裝置（手機／平板）改成「點背景切換」，而且記在 localStorage
         動畫：關／減少動態效果  兩種狀態都切得動，但**不補間**，直接跳到目標值
       ⚠ 進出快速切換時一律**從目前的 expT 接著補間**（記 from／to），不是每次從 0 或 1 重來 ——
         重來就會看到零件瞬間跳回去再重跑一次。補間長度也照剩下的距離等比縮短，
         所以「拉開到一半就移開」收回去的速度跟「完全拉開才移開」是同一個手感。*/
    const EXP_IN = 820, EXP_OUT = 500;
    let expTarget = 0;
    /* 這台裝置有沒有「游標」。手機／平板是 (hover: none)，pointerenter 永遠不會來，
       所以那些裝置改用點一下切換。讀不到就當成有 hover（桌機是多數）。*/
    const canHover = (() => {
      try { return !(window.matchMedia && window.matchMedia('(hover: none)').matches)
               && !!(window.matchMedia && window.matchMedia('(hover: hover)').matches); } catch (e) { return true; }
    })();
    /* 記住「用點的」那種裝置上使用者最後選的狀態。hover 裝置**不記** ——
       hover 本來就是暫時的，記住它只會讓下次進來看到一張已經散掉的圖。
       key：tw.dg3d.exp（'1' ＝ 展開、其餘 ＝ 收攏）*/
    const EXP_KEY = 'tw.dg3d.exp';
    const expSaved = () => { try { return localStorage.getItem(EXP_KEY) === '1'; } catch (e) { return false; } };
    const expSave = (on) => { try { localStorage.setItem(EXP_KEY, on ? '1' : '0'); } catch (e) { /* 忽略 */ } };
    /* 切換到「展開」或「收攏」。instant＝不補間（動畫關、減少動態效果、驗收要一幀到位時用）。*/
    const setExplode = (on, instant) => {
      const to = on ? 1 : 0;
      expTarget = to;
      if (instant || !anim || reduced) { expAnim = null; applyExplode(to); return to; }
      const d = Math.abs(to - expT);
      if (d < 0.002) { expAnim = null; applyExplode(to); return to; }
      // 從目前的 t 接著補間，長度照剩下的距離等比縮短（最短 80ms，不然近距離會像瞬跳）
      expAnim = { from: expT, to, t0: performance.now(), dur: Math.max(80, (to > expT ? EXP_IN : EXP_OUT) * d) };
      markDirty();
      return to;
    };
    /* ⚠ 具名：#prod3d 這個容器是**跨 mount 重用**的（關掉 3D 再開一次是新的 view、同一個 div），
       匿名函式掛上去就拿不下來，每開一次就多一組監聽 —— 收攏／展開會被觸發好幾次。*/
    const onEnter = () => setExplode(true);
    const onLeave = () => setExplode(false);
    // 進場：收攏。沒有 hover 的裝置照它上一次的選擇（#246 第 6 點）
    applyExplode(canHover ? 0 : (expSaved() ? 1 : 0));
    expTarget = expT;
    if (canHover) {
      /* 掛在**容器**（#prod3d）上，不是畫布：標籤卡片疊在畫布上方，
         掛畫布的話游標一滑過卡片就會收回去。pointerenter／pointerleave 不會因為
         在子元素之間移動而重複觸發（mouseover 會，所以刻意不用它）。*/
      el.addEventListener('pointerenter', onEnter);
      el.addEventListener('pointerleave', onLeave);
    }
    /* ★ C6：系統層級的「減少動態效果」（prefers-reduced-motion: reduce）一律**當成動畫關掉**。
       以前 reduced 只擋住爆炸補間，零件還是在轉、粒子還是在跑 —— 那不叫尊重。
       注意鈕上的字仍然照 `anim`（使用者自己的選擇），只是實際上一格都不動。*/
    const motionOn = () => anim && !reduced;
    /* setAnim() 在色票區塊「之前」就會被呼叫一次，那時候 lastHi 還在 TDZ 裡 ——
       所以「關動畫要把顏色還原」這件事只在場景真的建好之後才做。*/
    let hiReady = false;
    const applyAuto = () => { controls.autoRotate = motionOn() && !userHold; };
    function hold() { userHold = true; if (holdT) clearTimeout(holdT); applyAuto(); }
    function release() {
      if (holdT) clearTimeout(holdT);
      holdT = setTimeout(() => { userHold = false; applyAuto(); }, 2500);
    }
    function setAnim(on) {
      anim = !!on;
      applyAuto();
      // 圖九 2-1：靜止＝電流不跑，粒子也不留在畫面上；走線本身一直都看得見
      flowAll.forEach(x => { x.visible = motionOn(); });
      if (!motionOn()) {
        /* C6：**真的完全停下來**。旗標改掉不算 ——
           要把 pulse 改過的顏色與 emissive 收回去、把位移歸零，
           否則畫面會停在「某顆零件剛好亮著、螺帽卡在半路」的那一幀。*/
        resetPulses();
        movers.forEach(mv => {
          mv.off = 0; mv.vel = 0;
          mv.groups.forEach(g => { g.userData.mv.x = g.userData.mv.y = g.userData.mv.z = 0; place(g); });
        });
        spinners.forEach(sp => { if (sp.userData.spin.sync) sp.userData.spin.speed = 0; });
        /* 動畫關掉：爆炸展開**不做過場**，直接跳到目前的目標狀態（#246）。
           以前（#238）是「一律停在拆開的狀態」—— 那是因為當時展開是進場動畫、沒有目標可言；
           現在展開與否是使用者用游標決定的，關動畫只該關掉「過場」，不該替他決定要不要展開。*/
        if (expAnim || expT !== expTarget) { expAnim = null; applyExplode(expTarget); }
        // 靜止時燈定在中間亮度；亮度基準由色票決定（soft 是 0，完全不發光）
        const lb = palNum('--dg-led', 0.55);
        leds.forEach(m => { m.emissiveIntensity = lb; });
        /* 「靜止」要立刻停住。OrbitControls 的阻尼會把剛才自轉的殘量再吐好幾秒，
           畫面看起來就是「按了關還在慢慢飄」。用 dampingFactor = 1 跑一次 update
           把殘量一次吃光並歸零（reset() 用的是同一招）。*/
        const df = controls.dampingFactor;
        controls.dampingFactor = 1; controls.update(); controls.dampingFactor = df;
        // 顏色要回到「目前選取狀態該有的樣子」（pulse 改過 color，highlight 才是權威）
        if (hiReady) highlight(lastHi.on, lastHi.color, lastHi.part);
        markDirty();
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
    /* ★ 2026-09-22 DECISIONS #238：只剩兩種模式 —— 暗色「科技」／亮色「閱讀」。
       舊的 soft／calm／casual 不再是模式，但舊的 localStorage 與還沒改版的鈕會送這些名字進來，
       一律映射（柔和、休閒 → 閱讀；沉穩 → 科技），不要讓 3D 因為一個舊名字掛掉。
       沒指定就跟著全站主題：淺色主題 → 閱讀、深色主題 → 科技。*/
    // （PALS／PAL_NAME／PAL_LEGACY／palByTheme 宣告在 mount 最前面：建零件之前就要知道模式，kit 才讀得到對的 token）
    const origCol = new Map();          // 零件的「原色」，換色票一律從這裡重算，不要疊加
    let pal = pal0;
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
      if (name) { pal = PALS.includes(name) ? name : (PAL_LEGACY[name] || 'tech'); }
      el.dataset.pal = pal;
      /* 材質色與卡片 token 讀的是 :root[data-dgpal] 那一份（2D／3D 同一份，#230）。
         industry.js 的鈕會先掛 html 的 data-dgpal 再叫 setPal；直接叫 setPal 的（驗收、console）也要對得起來，
         不然 3D 說自己是閱讀、root 還是科技 —— 板子是深色的、卡片是白的、字卻是淺色。*/
      try { if (document.documentElement.dataset.dgpal !== pal) document.documentElement.dataset.dgpal = pal; } catch (e) { /* 忽略 */ }
      const mix = palCol('--dg-mix', '#ffffff'), k = palNum('--dg-mix-k', 0), sat = palNum('--dg-sat', 1);
      // 材質手感：閱讀模式把粗糙度整組拉高、金屬度整組壓低（霧面塑膠、陶瓷、黏土）；科技模式維持原值
      const roughK = palNum('--dg-rough-k', 1), metalK = palNum('--dg-metal-k', 1);
      const glassA = palNum('--dg-glass-a', 0.3), shellA = palNum('--dg-shell-a', 0.5), flowEm = palNum('--dg-flow-em', 0), flowA = palNum('--dg-flow-a', 0.9);
      const hsl = {};
      const litC = palCol('--dg-lit', '#ffffff'), dimC = palCol('--dg-dim', '#070b14');
      byIdx.forEach(p => {
        if (!p) return;
        p.mats.forEach(m => {
          const ud = m.userData || {};
          /* 這顆材質的顏色是某個 --dg-* 來的 → 每次換模式都回去重讀。
             閱讀模式會換掉材質 token 本身，只靠 origCol 的快照會停在上一個模式的原色。
             衍生色（col(k)）用重讀到的底色再往 --dg-lit／--dg-dim 拉一次 k。*/
          const vn = ud.dgvar;
          if (vn && m.color) {
            const c0 = palColOpt(vn);
            if (c0) { const kk = ud.dgk || 0; if (kk > 0) c0.lerp(litC, kk); else if (kk < 0) c0.lerp(dimC, -kk); origCol.set(m, c0); }
          }
          if (!m.color) return;
          if (!origCol.has(m)) origCol.set(m, m.color.clone());
          const c = origCol.get(m).clone();
          c.getHSL(hsl); c.setHSL(hsl.h, hsl.s * sat, hsl.l);
          if (k > 0) c.lerp(mix, k);
          p.baseCol.set(m, c.clone());
          if (ud.rough0 != null && m.roughness != null) m.roughness = Math.min(1, ud.rough0 * roughK);
          if (ud.metal0 != null && m.metalness != null) m.metalness = Math.min(1, ud.metal0 * metalK);
          if (ud.glass) { p.baseOp.set(m, ud.shell ? shellA : glassA); }   // 機櫃外殼板（規格書一-3 准許透明的三種之一）
          // 液冷：青綠半透明，兩種模式各自的不透明度（--dg-m-cool-a）
          if (ud.cool) p.baseOp.set(m, palNum('--dg-m-cool-a', 0.62));
          if (ud.edge) p.baseOp.set(m, palNum('--dg-glass-edge-a', 0.55));    // 玻璃邊光（科技淡藍、閱讀白）
          if (ud.ao) { m.color.copy(palCol('--dg-ao', '#000000')); p.baseOp.set(m, palNum('--dg-ao-a', 0.4)); p.baseCol.set(m, m.color.clone()); }
          if (ud.glow && m.emissive) { m.emissive.copy(c); m.emissiveIntensity = flowEm * (ud.glowK || 1); }
          /* 流線的粒子：科技模式加法混色（微發光的光點）；閱讀模式普通混色＋半透明（不刺眼）*/
          if (ud.flowPts) {
            m.blending = flowEm > 0 ? THREE.AdditiveBlending : THREE.NormalBlending;
            p.baseOp.set(m, flowA); m.needsUpdate = true;
          }
          if (ud.flowLine) p.baseOp.set(m, Math.min(0.85, flowA));
        });
      });
      /* ★ 環境貼圖（規格書一-1）：兩種模式的棚色不同，所以換模式要重生一份。
         只在**模式真的換了**的時候生 —— PMREM 要畫六個面再做多階模糊，每次都生會很貴。
         envMapIntensity 走 --dg-env（科技 .9、閱讀 1.15）：閱讀模式的棚比較亮，
         金屬要反射得多一點才不會在白底上變成一塊灰。*/
      /* --dg-env 設成 0 ＝ **完全不掛 envMap**（不是只把強度歸零）：
         envMap 的成本在 fragment shader 的 textureCubeUV 取樣，強度歸零一樣要付。
         慢的裝置／要省電的情境靠這個 token 整個關掉。*/
      /* 手機（< 700）連 envMap 一起關掉。實測（容器的軟體渲染）envMap 是這一批最貴的一件事：
         8.8 fps → 2.9 fps，而陰影只吃掉 0.2。成本在 fragment shader 的 textureCubeUV 取樣
         （依粗糙度在多階之間混合），貼圖改小沒有用 —— 已經實測過 256 換 64 一樣是 2.9。
         真的 GPU 上這是 three.js 每個 PBR 場景都在走的標準路徑，成本是個位數百分比；
         但小螢幕多半也是弱裝置，而且那個尺寸下反射根本看不到，所以直接不付這個錢。*/
      const envK = (window.innerWidth || W()) >= 700 ? palNum('--dg-env', 1) : 0;
      if (envK <= 0) { scene.environment = null; envPal = ''; }
      else if (envPal !== pal || !scene.environment) { buildEnv(pal); envPal = pal; }
      byIdx.forEach(p => { if (!p) return; p.mats.forEach(m => { if (m.envMapIntensity != null) m.envMapIntensity = envK; }); });
      applyShadowMode();
      hemi.intensity = palNum('--dg-hemi', 0.62);
      hemi.color.copy(palCol('--dg-l-sky', '#ffffff')); hemi.groundColor.copy(palCol('--dg-l-gnd', '#000000'));
      key.intensity = palNum('--dg-key', 1.0); key.color.copy(palCol('--dg-l-key', '#ffffff'));
      fill.intensity = palNum('--dg-fill', 0.34); fill.color.copy(palCol('--dg-l-fill', '#ffffff'));
      bounce.intensity = palNum('--dg-bounce', 0.16); bounce.color.copy(palCol('--dg-l-fill', '#ffffff'));
      rim.intensity = palNum('--dg-rim', 0); rim.color.copy(palCol('--dg-l-rim', '#ffffff'));
      renderer.toneMappingExposure = palNum('--dg-expo', 1.0);
      shadowMat.color.copy(palCol('--dg-shadow', '#000000')); shadowMat.opacity = palNum('--dg-shadow-a', 0.4);
      /* 卡片、引線、端點、編號圓點的元件色跟著模式重算（科技拉亮、閱讀壓暗，見 calcElColor）；
         data-dgcolor 與 --c／--dg-card-c 一起換，style-system 那邊讀到的才是同一個值。*/
      byIdx.forEach(p => {
        if (!p || !p.el) return;
        const c = calcElColor(p.kit, p.role);
        p.elColor = c; p.el.dataset.dgcolor = c;
        [p.el, p.path, p.halo, p.dot, p.no].forEach(x => { if (x) { x.style.setProperty('--c', c); x.style.setProperty('--dg-card-c', c); } });
        if (p.dot) p.dot.setAttribute('stroke', c);
      });
      highlight(lastHi.on, lastHi.color, lastHi.part);     // 重新套用目前的選取狀態，顏色才會真的換掉
      bumpShadow();        // 換模式會換掉材質與燈光，陰影貼圖也要重畫一次
      return pal;
    }
    applyPal(o.pal || palByTheme());   // 一掛上去就照使用者選的模式（沒選就跟主題），不要先畫成預設再閃一下
    hiReady = true;                    // 之後「關動畫」才可以回頭叫 highlight() 把 pulse 改過的顏色收回去
    if (!motionOn()) setAnim(anim);    // 進場就是靜止（動畫關或系統要求減少動態）：把位移與 pulse 一次歸零

    /* 兩層高亮（2026-09-21 晚間）：`part` 是**被點的那一個零件**的身分，
       跟 2D 剖析圖共用同一個 key（見 SCENES 檔頭的 `part`）。
         · 被點的那一個 → 最強（emissive 拉到 --dg-part-em、標籤加粗框）
         · 同環節的其餘 → 次強（維持原本的 --dg-sel-em，多環節場景的既有外觀一個值都沒動）
         · 其餘環節     → 淡出（本來就有的行為）
       單一環節的場景多一條：次強那一層要退到 --dg-sib-o，不然三顆長得一模一樣。*/
    function highlight(on, color, part) {
      lastHi = { on, color, part: part || null };
      stickyBelow = new Set(); compactSide = { L: false, R: false };   // 選取變了：讓被點的那一顆有機會回到欄裡、全開（重新排一次）
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
        /* C6 ④：pulse 每幀都會改這些材質的顏色與 emissive，所以它得知道
           「不算 pulse 的話，這顆零件現在應該長什麼樣」——
           淡出的零件不准被硬點亮，被點的那一顆的染色也不能被 pulse 蓋掉。*/
        p.hiFade = fade;
        p.hiTint = (tint && selPart) ? tint.clone() : null;
        p.hiEm = selPart ? palNum('--dg-part-em', 0.5) : (sel ? palNum('--dg-sel-em', 0.22) : 0);
        p.mats.forEach(m => {
          const b = p.baseOp.get(m), bc = p.baseCol.get(m);
          m.opacity = fade ? Math.min(b, 0.12) : (sib ? Math.min(b, sibO) : b);
          m.transparent = fade || sib || b < 1;
          if (m.userData && m.userData.led) {
            // 圖九 2-2：指示燈的亮度基準由色票決定（soft 是 0＝完全不發光，印得出來）
            const lb = palNum('--dg-led', 0.55);
            m.emissiveIntensity = fade ? lb * 0.07 : (sel ? lb * 1.55 : lb); return;
          }
          const ud = m.userData || {};
          if (m.emissive && !ud.glow) m.emissiveIntensity = selPart ? palNum('--dg-part-em', 0.5) : (sel ? palNum('--dg-sel-em', 0.22) : 0);
          if (ud.glow) m.emissiveIntensity = fade ? 0 : palNum('--dg-flow-em', 0) * (ud.glowK || 1);
          /* ★ 2026-09-22：環節色**只**給「被點的那一顆」。
             以前同環節的全部一起染色，等於一次把七八顆零件變成同一個色相 —— 那正是「一張圖一個主色」的反面；
             從環節色標整段選起來（沒有主角）也不染：那時候「其餘淡出 ＋ 卡片亮框」已經說明了誰被選到，
             族群層級的網址一進來就是整段選著的，染下去等於預設畫面就是多色相。
             拉 0.45 而不是整顆換色：保留零件本身的材質與明暗。*/
          if (tint && selPart) m.color.copy(bc).lerp(tint, 0.45); else m.color.copy(bc);
        });
        if (p.el) {
          p.el.classList.toggle('sel', sel);
          p.el.classList.toggle('sel-part', selPart);
          p.el.classList.toggle('dim', fade);
        }
        // 引線跟著標籤一起淡出／亮起來，不然選了一個環節，畫面上還有一堆別人的線
        if (p.path) { p.path.style.opacity = fade ? 0.1 : (sel ? 1 : 0.72); p.path.classList.toggle('sel', !!sel); }
        if (p.dot) p.dot.style.opacity = fade ? 0.1 : 0.9;
        if (p.halo) p.halo.style.opacity = fade ? 0 : '';
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
    let lastMode = '';
    /* 塞不下兩欄、被排到底下那一排的卡片是**黏的**（stickyBelow）：
       自轉時零件的投影點每幀都在動，塞得下／塞不下的判定會跟著翻來覆去，
       卡片就在欄位與底下那一排之間跳（畫面閃、頁面高度抖，驗收點鈕也會因為元素不穩定而逾時）。
       所以一旦被排到底下就留在底下，直到欄寬／模式變了或選取變了（被點的那一顆要回到欄裡）才重算。*/
    // （stickyBelow 本身宣告在 mount 最前面：highlight() 會在這一段之前就被 applyPal 叫到，宣告在這裡會踩 TDZ）
    /* 換模式時把卡片搬到對的容器：lr／r 是疊在畫布上的絕對定位欄，below 是畫布底下的文件流。
       只在模式真的變了才搬（搬 DOM 會重算版面，每幀搬會卡）。*/
    function applyMode(m) {
      if (m === lastMode) return false;
      lastMode = m;
      el.classList.toggle('dgstage--lr', m === 'lr');
      el.classList.toggle('dgstage--r', m === 'r');
      el.classList.toggle('dgstage--below', m === 'below');
      lastCw = -1;
      stickyBelow = new Set(); compactSide = { L: false, R: false };
      return true;
    }
    /* 把一張卡片放進某個容器（欄或底下那一排）。放進底下那一排時清掉絕對定位的座標。
       ★ 兩欄／右欄模式下**塞不下的卡片也往底下排**，不再直接藏起來 ——
         藏起來＝那個零件的說明與台股整個消失；排到底下＋畫布上一個編號圓點，資訊一個都不少。*/
    function placeIn(p, host) {
      if (p.el.parentNode !== host) host.appendChild(p.el);
      if (host === below) { p.el.style.left = ''; p.el.style.top = ''; p.el.style.width = ''; p.el.classList.add('below'); p.el.classList.remove('compact'); }
      else { p.el.classList.remove('below'); p.el.style.width = (colW() - 12) + 'px'; }
    }
    // 底下那一排：照編號排，不然卡片的順序會跟著相機角度跳來跳去。順序已經對了就不動 DOM。
    function sortBelow() {
      const cur = [...below.children].map(k => k.dataset.dgno);
      const want = cur.slice().sort((a, b) => (+a) - (+b));
      if (cur.join(',') === want.join(',')) return;
      const kids = [...below.children].sort((a, b) => (+a.dataset.dgno) - (+b.dataset.dgno));
      kids.forEach(k => below.appendChild(k));
    }
    function layoutLabels() {
      const w = W(), h = H(), cw = colW(), m = mode();
      const modeChanged = applyMode(m);
      // 引線那張 SVG 要蓋住整個容器（below 模式時容器比畫布高）
      const hostH = Math.max(h, el.clientHeight || h);
      if (lead.__w !== w || lead.__h !== hostH) {
        lead.setAttribute('viewBox', `0 0 ${w} ${hostH}`); lead.__w = w; lead.__h = hostH;
      }
      const items = [];
      byIdx.forEach(p => {
        if (!p || !p.el) return;
        p.groups[0].getWorldPosition(vtmp); vtmp.add(p.anchor);
        const v = vtmp.clone().project(camera);
        items.push({ p, sx: (v.x + 1) / 2 * w, sy: (-v.y + 1) / 2 * h, front: v.z < 1,
          d: camera.position.distanceTo(vtmp), sel: p.el.classList.contains('sel') });
      });
      /* 底下那一排的卡片：畫布上用編號圓點標位置；引線只畫給「被選的那一顆」——
         十幾條線全部拉到底下會把模型蓋成一團。窄畫面（below 模式）全部卡片都走這裡，
         兩欄／右欄模式下只有塞不下的那幾張走這裡。*/
      const belowOnes = [];
      function layoutBelow(list) {
        if (!list.length) { below.hidden = true; return; }
        below.hidden = false;
        list.forEach(it => placeIn(it.p, below));
        sortBelow();
        const hostR = el.getBoundingClientRect();
        list.forEach(it => {
          const p = it.p;
          p.el.classList.remove('hid');
          p.no.style.display = it.front ? '' : 'none';
          p.no.setAttribute('transform', `translate(${it.sx.toFixed(1)},${it.sy.toFixed(1)})`);
          p.dot.style.display = 'none'; p.halo.style.display = 'none';
          if (it.front && p.el.classList.contains('sel-part')) {
            const r = p.el.getBoundingClientRect();
            const cx = r.left - hostR.left + 14, cy = r.top - hostR.top;
            p.path.setAttribute('d', `M${it.sx.toFixed(1)},${it.sy.toFixed(1)} L${it.sx.toFixed(1)},${(h - 8).toFixed(1)} L${cx.toFixed(1)},${cy.toFixed(1)}`);
            p.path.style.display = '';
          } else p.path.style.display = 'none';
        });
      }
      if (m === 'below') { layoutBelow(items); return; }
      byIdx.forEach(p => { if (p && p.no) p.no.style.display = 'none'; });
      // 重要度：選起來的最優先，其次是離相機近的（看得最清楚的那個）；塞不下時從最後面開始讓位
      items.slice().sort((a, b) => (b.sel - a.sel) || (a.d - b.d)).forEach((it, i) => { it.rank = i; });
      /* 卡片高度只在欄寬真的變了才重量（每幀量一次 offsetHeight 會一直逼瀏覽器重算版面）：
         量的時候先把全部卡片放進欄裡（欄寬決定折行）、量完存進 p.hh。
         之後每一幀只用快取，卡片留在原來的容器裡，決定變了才搬 —— 每 4 幀把 16 張卡片搬來搬去
         就是第一版 800px 截圖「等字型載入」卡住 30 秒的原因。*/
      if (cw !== lastCw || modeChanged) {
        colL.style.width = colR.style.width = cw + 'px';
        items.forEach(it => placeIn(it.p, colR));
        // 兩種高度都量：全開（hh）與收成一行（hhC）。之後每一幀只用快取，不碰 DOM。
        items.forEach(it => { it.p.el.classList.remove('hid', 'compact'); it.p.hh = it.p.el.offsetHeight || 42; });
        items.forEach(it => { it.p.el.classList.add('compact'); it.p.hhC = it.p.el.offsetHeight || 30; it.p.el.classList.remove('compact'); });
        lastCw = cw;
        stickyBelow = new Set(); compactSide = { L: false, R: false };
      }
      items.forEach(it => { it.p.el.classList.remove('hid'); it.hh = it.p.hh || 42; });

      const hidden = items.filter(it => !it.front);       // 轉到背面去的零件，標籤跟著收起來
      const colsBy = { L: [], R: [] };
      // 已經黏在底下那一排的，直接留在底下（正面的才畫編號圓點）
      items.filter(it => it.front && stickyBelow.has(it.p)).forEach(it => belowOnes.push(it));
      /* 分左右欄：明顯偏一邊的就放那一邊，卡在中間的（機櫃是直立的，大部分零件都在正中央）
         放到目前比較空的那一欄 —— 只照 sx < w/2 分的話，整排零件會全部擠到左欄去。*/
      items.filter(it => it.front && !stickyBelow.has(it.p)).sort((a, b) => a.sy - b.sy).forEach(it => {
        let side;
        if (m === 'r') side = 'R';
        else if (it.sx < w / 2 - w * 0.10) side = 'L';
        else if (it.sx > w / 2 + w * 0.10) side = 'R';
        else side = colsBy.L.length <= colsBy.R.length ? 'L' : 'R';
        colsBy[side].push(it);
      });
      ['L', 'R'].forEach(side => {
        const list = colsBy[side];
        /* 塞不下的第一步不是往底下丟，是把這一欄的卡片**收成一行**（標題＋英文＋兩顆晶片；被點的那一張維持全開）。
           Andy 2026-09-22：「不准掉到下面」。收了還是塞不下才往底下排（16 張以內實測不會走到那一步）。*/
        const useCompact = (on) => list.forEach(it => {
          const keep = it.p.el.classList.contains('sel-part');
          it.p.el.classList.toggle('compact', on && !keep);
          it.hh = (on && !keep) ? (it.p.hhC || it.hh) : (it.p.hh || 42);
        });
        if (!compactSide[side] && !pack(list, h)) compactSide[side] = true;   // 一旦收起來就維持（黏住），跟 stickyBelow 同一個理由
        useCompact(compactSide[side]);
        while (list.length && !pack(list, h)) {
          let worst = 0; list.forEach((it, i) => { if (it.rank > list[worst].rank) worst = i; });
          const ev = list.splice(worst, 1)[0];
          ev.p.el.classList.remove('compact');
          stickyBelow.add(ev.p); belowOnes.push(ev);       // 收了還塞不下才往底下排（而且黏住），不藏
        }
        const lx = side === 'L' ? 6 : w - cw + 6;           // 卡片在自己那一欄裡的 x（欄是 absolute 的，left 相對於欄）
        const inner = side === 'L' ? lx + cw - 12 : lx;      // 文字框朝著模型的那一邊（整個容器的座標）
        const host = side === 'L' ? colL : colR;
        list.forEach(it => {
          placeIn(it.p, host);
          it.p.el.style.left = '6px';
          it.p.el.style.top = it.ty + 'px';
          const cy = it.ty + it.hh / 2;
          const bend = side === 'L' ? inner + 14 : inner - 14;
          it.p.path.setAttribute('d', `M${it.sx.toFixed(1)},${it.sy.toFixed(1)} L${bend.toFixed(1)},${cy.toFixed(1)} L${inner.toFixed(1)},${cy.toFixed(1)}`);
          it.p.path.style.display = '';
          it.p.dot.setAttribute('cx', it.sx.toFixed(1)); it.p.dot.setAttribute('cy', it.sy.toFixed(1));
          it.p.halo.setAttribute('cx', it.sx.toFixed(1)); it.p.halo.setAttribute('cy', it.sy.toFixed(1));
          it.p.dot.style.display = ''; it.p.halo.style.display = '';
        });
      });
      hidden.forEach(it => {
        it.p.el.classList.add('hid');
        it.p.path.style.display = 'none'; it.p.dot.style.display = 'none'; it.p.halo.style.display = 'none';
      });
      layoutBelow(belowOnes);
    }

    /* 圖九 2-1：把電流粒子往前推一格。
       路徑用「段索引」參數化（每段長度相近，肉眼看不出差別），
       dir 決定方向 —— 電源由下往上、訊號由 GPU 往背板、光訊號往前面板。*/
    function stepFlows(dt) {
      flowPts.forEach(o2 => {
        const f = o2.userData.flow;
        f.age += dt;
        /* 交流／充放電：電流真的會**反向**，不是一直往同一邊跑。
           每半個週期換一次方向，看到的就是「充進去 → 放出來」。*/
        if (f.bidir) f.dir = (f.age % f.bidir) < f.bidir / 2 ? 1 : -1;
        /* 閘控：截止的時候電流是 0，所以粒子**整組藏起來而且不前進**。
           （MOSFET 閘極關、PPTC 跳脫、壓敏電阻沒突波，都是這個狀態。）*/
        if (f.gate) {
          const on = (f.age % f.gate.per) < f.gate.per * f.gate.duty;
          if (o2.visible !== on) o2.visible = on;
          if (!on) return;
        }
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

    /* ================================================================ C6 ③：陣列零件各自旋轉
       風扇牆是一個 InstancedMesh（28 片葉片、1 個 draw call）。要讓它真的在轉就得重算
       instanceMatrix —— 但只重算矩陣，幾何完全沒動，所以成本是 28 次 compose，不是 28 次重建 buffer。*/
    const _ip = new THREE.Vector3(), _iq = new THREE.Quaternion(), _ie = new THREE.Euler(),
      _is = new THREE.Vector3(1, 1, 1), _im = new THREE.Matrix4();
    function stepISpins(dt) {
      for (let n = 0; n < ispinners.length; n++) {
        const im = ispinners[n], sp = im.userData.ispin;
        sp.t += sp.speed * dt;
        const items = sp.items;
        for (let i = 0; i < items.length; i++) {
          const o2 = items[i], a = o2.a0 + sp.t;
          _ie.set(0, o2.ry || 0, a + Math.PI / 2); _iq.setFromEuler(_ie);
          _ip.set(o2.cx + Math.cos(a) * o2.r, Math.sin(a) * o2.r, o2.cz || 0);
          _im.compose(_ip, _iq, _is);
          im.setMatrixAt(i, _im);
        }
        im.instanceMatrix.needsUpdate = true;
      }
    }

    /* ================================================================ C6 ④：一組零件依序點亮
       為什麼這樣動是對的：這幾個場景裡「會動的」本來就不是零件本身，是**能量或訊號**——
       晶圓在製程站之間往前走、訊號沿 TSV 由上往下貫穿、背光由下往上穿過一層層膜、
       電容充放電。所以動的是顏色與發光，零件一動不動。

       波形刻意用窄脈衝（cos 抬到 8 次方，半高寬只有週期的 1/8）：
       同一時間只有一顆在亮，看起來像「有東西跑過去」；
       用正弦的話會變成整排一起呼吸 —— 那就是 Andy 講過三次的「螢光感太重」。

       兩個通道一起動，深淺兩個主題才都看得見：
         · emissive  —— 科技模式的主角（深底上看得到光）
         · 顏色往角色色靠 —— 閱讀模式的主角（--dg-sel-em 是 0，白紙上看得到的是變色不是發光）*/
    const _pc = new THREE.Color(), _pt = new THREE.Color(), _pb = new THREE.Color();
    let pulseAt = 0;
    function stepPulses(dt) {
      if (!pulses.length) return;
      pulseAt += dt;
      const em = palNum('--dg-part-em', 0.45);
      for (let n = 0; n < pulses.length; n++) {
        const pg = pulses[n], items = pg.items, cnt = items.length;
        _pc.set(palColOpt(pg.token) || new THREE.Color('#58C4FF'));
        for (let i = 0; i < cnt; i++) {
          const it = items[i], p = it.p;
          let u = (pulseAt / pg.period) - i / cnt + pg.phase;
          u -= Math.floor(u);
          const k = Math.pow(Math.max(0, Math.cos(u * Math.PI * 2)), pg.sharp) * pg.amp;
          it.k = k;
          if (p.hiFade) continue;      // 別的環節被選起來：這一顆本來就該淡出，不要硬把它點亮
          const mats = p.mats;
          for (let j = 0; j < mats.length; j++) {
            const m = mats[j], ud = m.userData || {};
            // 指示燈、流線、AO 墊片有自己的節奏，疊上去只會變成一團亮
            if (ud.led || ud.glow || ud.ao) continue;
            if (m.emissive) { m.emissive.copy(_pc); m.emissiveIntensity = p.hiEm + k * em * 1.15; }
            const b = p.baseCol.get(m);
            if (!b || !m.color) continue;
            _pb.copy(b); if (p.hiTint) _pb.lerp(p.hiTint, 0.45);
            m.color.copy(_pb).lerp(_pc, k * 0.4);
          }
        }
      }
    }
    /* pulse 關掉時要把零件還原 —— 「關掉動畫」必須是**畫面真的停下來而且回到常態**，
       不是停在某一顆剛好亮著的那一幀。emissive 的顏色是 pulse 自己改的，highlight() 只管強度，
       所以顏色要在這裡自己收回去（一般材質的 emissive 本來就是黑的）。*/
    function resetPulses() {
      pulses.forEach(pg => pg.items.forEach(it => {
        it.k = 0;
        it.p.mats.forEach(m => {
          const ud = m.userData || {};
          if (ud.led || ud.glow || ud.ao) return;
          if (m.emissive) m.emissive.setRGB(0, 0, 0);
        });
      }));
    }

    /* ================================================================ C6 ⑤：零件沿一軸位移
       用在「這個零件在機器運轉時真的會走」的地方：螺帽沿著螺桿前後、工作台跟著走、
       晶粒被取放、晶碇被往上提。
       ⚠ 位移**不**觸發陰影貼圖重畫（bumpShadow）：接觸陰影是一片圓盤，
         而且既有的扇葉旋轉也是這樣處理的 —— 每幀重畫陰影會把 30fps 的預算吃光。*/
    let moveAt = 0;
    function stepMoves(dt) {
      if (!movers.length) return;
      moveAt += dt;
      for (let n = 0; n < movers.length; n++) {
        const mv = movers[n];
        let u = moveAt / mv.period + mv.phase;
        u -= Math.floor(u);
        const prev = mv.off;
        // pingpong 用 -cos：兩端**減速再折返**，跟真的伺服軸一樣（線性往復會在端點硬生生彈回去）
        const sgn = mv.mode === 'saw' ? (u * 2 - 1) : -Math.cos(u * Math.PI * 2);
        mv.off = sgn * mv.amp;
        mv.vel = (mv.off - prev) / Math.max(1e-4, dt);
        for (let i = 0; i < mv.groups.length; i++) {
          const g = mv.groups[i];
          g.userData.mv[mv.axis] = mv.off;
          place(g);
        }
      }
      /* 螺桿轉多快，決定螺帽走多快 —— 反過來也一樣。
         所以「跟著某個位移」的旋轉件，轉速直接由那個位移的速度算出來：
         螺帽往右走時螺桿順時針，折返時螺桿也真的跟著反轉。
         這是「動得符合物理」的關鍵：兩個各轉各的就會看起來像兩台機器。*/
      for (let i = 0; i < spinners.length; i++) {
        const sp = spinners[i].userData.spin;
        if (!sp.sync) continue;
        const mv = movers.find(x => x.name === sp.sync);
        if (mv) sp.speed = mv.vel * (sp.base || 1);
      }
    }

    /* ---- 只在看得到、而且真的有東西變了的時候畫
       ★ 2026-09-23（DECISIONS #245）：以前是「每一幀都無條件 renderer.render()」——
         連「動畫：關、沒有人在拖曳」的狀態都在燒 CPU。加上環境貼圖之後每一幀貴了 3 倍，
         就變成整條主執行緒被佔住、工具列的鈕在 6 秒內點不下去（驗收實際紅給我看的）。
         改成三條規則：
           ① 動畫開著 → 照畫，但**最多 30fps**（把 60Hz 螢幕的成本砍一半；慢的機器本來就不到 30，不受影響）
           ② 動畫關著 → 只有「有人動過相機／狀態變了」才畫
           ③ 靜止時每 400ms 補畫一次當安全網 —— 萬一有哪個狀態變更忘了標記 dirty，
              畫面最多晚 0.4 秒跟上，不會出現「改了卻不更新」的死畫面。 */
    let raf = null, alive = true, visible = true, relayout = 0, t0 = performance.now();
    // （dirty／lastDraw／markDirty 宣告在 applyExplode 那一段：#246 的補間在建場景階段就會用到）
    controls.addEventListener('change', markDirty);
    const tick = () => {
      if (!alive) return;
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      const now0 = performance.now();
      const run = motionOn();
      if (run && now0 - lastDraw < 32) return;                   // ① 動畫上限 30fps
      const dt = Math.min(0.05, (performance.now() - t0) / 1000); t0 = performance.now();
      if (run) {
        /* C6：位移要排在旋轉**前面** —— 跟著位移走的旋轉件（螺桿）的轉速
           是這一幀的位移速度算出來的，反過來排會慢一幀，折返的瞬間看得出來。*/
        stepMoves(dt);
        spinners.forEach(s => { s.rotation[s.userData.spin.axis] += s.userData.spin.speed * dt; });
        stepISpins(dt);
        const lb = palNum('--dg-led', 0.55);
        const k = lb + lb * 0.55 * (0.5 + 0.5 * Math.sin(performance.now() / 620));
        leds.forEach(m => { if (m.emissiveIntensity > 0.02) m.emissiveIntensity = k; });
        stepFlows(dt);
        stepPulses(dt);
      }
      /* ★ #246 的爆炸補間刻意放在 `if (anim)` **外面**：
         展開／收攏是使用者用游標控制的狀態，不是「動態效果」的一部分。
         （動畫關著時 setExplode 根本不會建 expAnim，所以這裡等於不會跑到；
           放外面是為了「補間跑到一半才按關」那一瞬間也能收得乾淨。）
         applyExplode() 自己會 markDirty()，所以補間期間每一幀都真的畫得出來（#245）。*/
      if (expAnim) {
        const u = Math.min(1, (performance.now() - expAnim.t0) / expAnim.dur);
        const k = 1 - Math.pow(1 - u, 3);                // ease-out cubic：一開始快、最後慢慢停
        applyExplode(expAnim.from + (expAnim.to - expAnim.from) * k);
        if (u >= 1) expAnim = null;
      }
      controls.update();
      if (!run && !dirty && now0 - lastDraw < 400) return;       // ②③ 靜止：沒變就不畫，400ms 補一張
      renderer.render(scene, camera);
      lastDraw = now0; dirty = false;
      // 自轉時每 4 幀重排一次標籤（引線要跟得上零件）；靜止時畫一次就排一次，才不會晚半秒才對齊
      if (run) { if (++relayout % 4 === 0) layoutLabels(); } else layoutLabels();
    };
    const io = typeof IntersectionObserver !== 'undefined'
      ? new IntersectionObserver(es => { visible = es.some(x => x.isIntersecting); }, { threshold: 0.02 }) : null;
    if (io) io.observe(el);
    const onVis = () => { visible = document.visibilityState !== 'hidden'; };
    document.addEventListener('visibilitychange', onVis);
    const onResize = () => {
      camera.aspect = W() / H(); camera.updateProjectionMatrix();
      renderer.setSize(W(), H());
      // 卡片欄的模式變了（例如從兩欄變成底下一欄），模型能用的寬度也變了 → 重新取景
      const before = lastMode;
      layoutLabels();
      if (before !== lastMode) { fitCamera(); layoutLabels(); }
      // 陰影跟著寬度開關（≥960 才開）：窄畫面關掉是效能的備案，不是「壞了」
      applyShadowMode();
      fitShadow();
      applyPal(pal);      // envMap 的 <700 開關也在 applyPal 裡，寬度變了要重判一次
    };
    window.addEventListener('resize', onResize);
    tick();
    layoutLabels();

    function dispose() {
      alive = false;
      if (raf) cancelAnimationFrame(raf);
      if (holdT) clearTimeout(holdT);
      if (io) io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('resize', onResize);
      el.removeEventListener('pointerenter', onEnter);      // #246：容器是重用的，監聽一定要拆
      el.removeEventListener('pointerleave', onLeave);
      controls.dispose();
      scene.traverse(x => {
        if (x.geometry) x.geometry.dispose();
        if (x.material) (Array.isArray(x.material) ? x.material : [x.material]).forEach(m => m.dispose());
      });
      if (shadowMat.map) shadowMat.map.dispose();      // 粒子與陰影共用的那張 sprite 貼圖
      Object.keys(envByPal).forEach(k => { if (envByPal[k]) envByPal[k].dispose(); delete envByPal[k]; });
      if (pmrem) { pmrem.dispose(); pmrem = null; }
      renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
      if (layer.parentNode) layer.parentNode.removeChild(layer);
      if (below.parentNode) below.parentNode.removeChild(below);
      el.classList.remove('dgstage', 'dgstage--lr', 'dgstage--r', 'dgstage--below');
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
      const base = { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (-v.y + 1) / 2 * r.height, front: v.z < 1 };
      /* ★ 回的是「真的點得到這個環節」的座標，不是幾何中心的投影。
         MLCC 切開近角那一顆的中心正好落在兩個切面的交線上（x=0、z=0），
         射線打在稜線上會因為浮點誤差什麼都沒碰到 —— 驗收就會隨相機角度偶爾紅。
         所以以中心為起點，往外試幾個像素，找到第一個 raycast 真的打到同環節零件的點。*/
      const tries = [[0, 0]];
      for (let rr = 6; rr <= 48; rr += 6) for (let a = 0; a < 8; a++) tries.push([Math.round(Math.cos(a * Math.PI / 4) * rr), Math.round(Math.sin(a * Math.PI / 4) * rr)]);
      // 中心找不到就從錨點（零件頂端）再找一圈
      const av = new THREE.Vector3(); p.groups[0].getWorldPosition(av); av.add(p.anchor); av.project(camera);
      const anc = { x: r.left + (av.x + 1) / 2 * r.width, y: r.top + (-av.y + 1) / 2 * r.height };
      /* 機櫃框（frame）那種零件：它的中心就是機櫃內部，射線一定先打到裡面的托盤 ——
         硬要找「只打到框」的點會找到玻璃側板的邊緣，相機一動就打空。
         所以框類零件只要求「打得到東西」（點下去會選到裡面某一顆，驗收要的就是「點了有反應」）。*/
      const isFrame = !!(p.groups[0].userData && p.groups[0].userData.frame);
      for (const o0 of [base, anc]) {
        for (const [dx, dy] of tries) {
          const x = o0.x + dx, y = o0.y + dy;
          if (x < r.left + 2 || x > r.right - 2 || y < r.top + 2 || y > r.bottom - 2) continue;
          toNdc({ clientX: x, clientY: y });
          const m = hit();
          if (m && (isFrame || m.userData.seg === seg)) return { x, y, front: base.front };
        }
      }
      return base;
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
          // 流線（水路／光路）在科技模式本來就准微發光（#238：發光只給流動線與被選零件），不算進零件的自體發光
          if (m.userData && m.userData.glow) return;
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
      // glass／flowLines：兩種模式的驗收要知道「玻璃材質真的有、流線真的有」
      let glassN = 0, glowN = 0;
      byIdx.forEach(p => { if (!p) return; p.mats.forEach(m => { const u = m.userData || {}; if (u.glass) glassN++; if (u.glow || u.flowLine) glowN++; }); });
      return { drawCalls: ri.calls, triangles: ri.triangles,
        parts: byIdx.filter(Boolean).length, meshes, maxEmissive: +maxEm.toFixed(3),
        idleEmissive: +idleEm.toFixed(3), maxMetal: +maxMetal.toFixed(2), leds: ledN,
        spinners: spinners.length, spinAt: +spinAt.toFixed(3), anim, autoRotate: !!controls.autoRotate,
        /* ★ C6 的量測介面。驗「這台機器在運作」一律比**這些數字有沒有變**，
           不是比「有沒有 pulses 這個陣列」——「元素存在」從來不算驗收。
             ispinAt  ＝ 陣列風扇（風扇牆）轉到哪（弧度和）
             pulseAt  ＝ pulse 的相位時鐘，只要在跑就單調前進
             pulseK   ＝ 這一刻所有 pulse 的亮度總和（窄脈衝，所以它會上上下下）
             moveAt   ＝ 位移的相位時鐘
             moveOff  ＝ **零件真的位移了多少**（螺帽現在在哪），關掉動畫一定回到 0
             reduced  ＝ 系統要求減少動態效果（此時一格都不會動，鈕上的字仍照使用者的選擇）*/
        ispinners: ispinners.length, ispinAt: +ispinners.reduce((a, x) => a + x.userData.ispin.t, 0).toFixed(3),
        pulses: pulses.reduce((a, g) => a + g.items.length, 0), pulseAt: +pulseAt.toFixed(3),
        pulseK: +pulses.reduce((a, g) => a + g.items.reduce((b, it) => b + it.k, 0), 0).toFixed(4),
        movers: movers.length, moveAt: +moveAt.toFixed(3),
        moveOff: +movers.reduce((a, m) => a + Math.abs(m.off), 0).toFixed(3),
        reduced, motion: motionOn(),
        flows: flowPts.length, flowVisible: flowAll.filter(x => x.visible).length,
        flowAt: +flowAt.toFixed(3), flowT: +flowT.toFixed(4), pal, colorSig: colorSig(), matSig: matSig(),
        explode: +expT.toFixed(3), exploding: !!expAnim, glass: glassN, flowLines: glowN,
        /* #246：expTarget＝游標決定的目標狀態；exMove＝零件離原位最遠跑了多少
           （驗收要量「零件真的合攏／真的分開」，不是只看 expT 這個變數）；
           canHover＝這台裝置有沒有游標（沒有的話改成點背景切換）。*/
        explodeTarget: expTarget, exMove: exMove(), canHover,
        /* expFrom＝目前這段補間是「從哪個 t 開始」的。驗收用它證明
           「進出快速切換時是從目前的 t 接著補，不是每次從 0 或 1 重來」——
           這個值跟幀率無關，所以在軟體渲染的容器裡也量得準。*/
        expFrom: expAnim ? +expAnim.from.toFixed(3) : null,
        chips: el.querySelectorAll('.lbl3d .chip3d').length };
    };
    /* ★ 2026-09-22 PBR 精緻化（DECISIONS #244）的量測介面。
       stats() 量的是「畫了幾個三角形、發光多強」，量不到這一批真正要驗的四件事：
         env        ＝ scene.environment 有沒有真的掛上去（沒有 envMap 的 PBR 金屬只會變暗灰）
         shadowMap  ＝ 真陰影開了沒、有幾顆 mesh 在投影（太多會爆效能、太少等於沒做）
         transRatio ＝ 半透明 mesh 佔全部 mesh 的比例（規格書一-3 的「收透明」要量得到）
         maxMetal   ＝ 全場最高金屬度（證明「metalness 上限解除」這件事真的發生了）
       全部走 scene.traverse，量的是**真的被畫出去的那些物件**，不是設定值。*/
    const audit = () => {
      let meshTotal = 0, transN = 0, castN = 0, recvN = 0, maxMetal = 0, maxEnv = 0, opaqueN = 0;
      const byPart = {};      // 逐零件的三角形數：減面之前要先知道面在哪一個零件上
      /* ★「這張圖設計上有多透明」要量 **baseOp**（沒有選取時該有的不透明度），不是當下的 opacity。
         高亮機制會把「沒被選到的環節」壓到 0.12（DECISIONS #238），
         而多環節場景一進來就有選取 —— 直接量 opacity 會得到「68% 的 mesh 是半透明的」，
         那量到的是**高亮狀態**不是設計。2026-09-22 第一版驗收就踩到這個。*/
      const baseOf = new Map();
      byIdx.forEach(p => { if (!p || !p.baseOp) return; p.baseOp.forEach((v, m) => baseOf.set(m, v)); });
      let designN = 0, designTotal = 0;
      scene.traverse(x => {
        if (!x.isMesh) return;
        meshTotal++;
        if (x.geometry) {
          let up = x; while (up && !(up.userData && up.userData.part)) up = up.parent;
          const key = up ? up.userData.part : '(場景層)';
          const g = x.geometry;
          const nn = g.index ? g.index.count : (g.attributes.position ? g.attributes.position.count : 0);
          byPart[key] = (byPart[key] || 0) + Math.round(nn / 3) * (x.isInstancedMesh ? x.count : 1);
        }
        if (x.castShadow) castN++;
        if (x.receiveShadow) recvN++;
        const ms = Array.isArray(x.material) ? x.material : [x.material];
        let tr = false;
        ms.forEach(m => {
          if (!m) return;
          if (m.transparent && m.opacity != null && m.opacity < 0.9) tr = true;
          if (m.metalness != null) maxMetal = Math.max(maxMetal, m.metalness);
          if (m.envMapIntensity != null) maxEnv = Math.max(maxEnv, m.envMapIntensity);
        });
        if (tr) transN++; else opaqueN++;
        // 設計上的透明：用 baseOp（量不到就退回當下的 opacity）
        let dtr = false, known = false;
        ms.forEach(m => {
          if (!m) return;
          const b = baseOf.has(m) ? baseOf.get(m) : null;
          if (b != null) { known = true; if (b < 0.9) dtr = true; }
          else if (m.transparent && m.opacity != null && m.opacity < 0.9) dtr = true;
        });
        if (known || ms.some(Boolean)) { designTotal++; if (dtr) designN++; }
      });
      return {
        env: !!scene.environment, envIntensity: +maxEnv.toFixed(2),
        bg: scene.background ? (scene.background.isTexture ? 'texture' : 'color') : 'none',
        shadowMap: !!renderer.shadowMap.enabled, shadowType: renderer.shadowMap.type,
        castShadow: castN, receiveShadow: recvN,
        meshTotal, transparent: transN, opaque: opaqueN, byPart,
        transRatio: meshTotal ? +(transN / meshTotal).toFixed(3) : 0,
        // ★ 驗收要看的是這一組：設計上半透明的 mesh 佔比（跟「現在選了誰」無關）
        designTrans: designN, designTotal,
        designRatio: designTotal ? +(designN / designTotal).toFixed(3) : 0,
        maxMetal: +maxMetal.toFixed(2),
        expo: +renderer.toneMappingExposure.toFixed(3),
        lights: { hemi: +hemi.intensity.toFixed(2), key: +key.intensity.toFixed(2), fill: +fill.intensity.toFixed(2),
          bounce: +bounce.intensity.toFixed(2), rim: +rim.intensity.toFixed(2) },
      };
    };
    /* 給驗收用：每個零件「材質底色 vs 環節色 vs 現在畫出來的顏色」。
       DECISIONS #238 那一刀（零件底色不再來自環節色）要量得到：
         base    ＝ 材質族 token 讀到的底色（K.base）
         seg     ＝ 環節色（segColor）
         now     ＝ 這個零件**最大那顆 mesh** 的材質現在的顏色（#rrggbb）
         tinted  ＝ 現在有沒有被拉向環節色（點零件之後只有主角會是 true）*/
    const mats = () => byIdx.filter(Boolean).map(p => {
      let big = null, bigV = -1;
      p.meshes.forEach(x => {
        if (!x.geometry || !x.material || !x.material.color || x.material.userData.led) return;
        /* ★ 2026-09-22：掛在零件身上的**流線**（液冷水路、光路、氣流）不算它的本體色。
           以前 ag_cdu 量到的是那條紅色熱水管（TubeGeometry 橫跨半個機櫃，外接盒體積最大），
           所以「液冷模組是什麼顏色」永遠量到熱水紅 —— 量錯了東西，不是顏色錯了。*/
        let up = x; while (up) { if (up.userData && up.userData.flowOf) return; up = up.parent; }
        if (!x.geometry.boundingBox) x.geometry.computeBoundingBox();
        const s = x.geometry.boundingBox.getSize(new THREE.Vector3());
        const v = s.x * s.y * s.z * (x.isInstancedMesh ? x.count : 1) * (x.scale.x * x.scale.y * x.scale.z || 1);
        if (v > bigV) { bigV = v; big = x; }
      });
      const m = big && big.material;
      const bc = m && p.baseCol.get(m);
      return { part: p.part, seg: p.seg, fam: p.fam, role: p.role, base: p.kit.base, el: p.elColor, segHex: p.hex,
        now: m ? '#' + m.color.getHexString() : null,
        tinted: !!(m && bc && !m.color.equals(bc)) };
    });
    /* 給驗收腳本用：「這個畫面座標打得到零件嗎」。
       驗「點背景要全部恢復全亮」一定要先找到一個**真的是背景**的點 ——
       用猜的（例如畫布左上角）會踩到標籤或剛好打到零件，那一條就變成隨機紅燈。 */
    const hitAt = (x, y) => {
      toNdc({ clientX: x, clientY: y });
      const m = hit();
      return m ? (m.userData.part || m.userData.seg || '?') : null;
    };
    /* 給族群晶片列（v3 §5，style-system 那一側）用的介面：
         pointOf(id)  → 零件（part id 或 seg id）現在在**視窗**上的座標與是否在正面（畫連線的端點）
         colorOf(id)  → 那個零件的元件色（跟卡片的 data-dgcolor 同一個值）
         partsOf(seg) → 這個環節在場景裡有哪些零件 id */
    const findP = (id) => byIdx.find(x => x && (x.part === id || x.alias.indexOf(id) >= 0)) || byIdx.find(x => x && x.seg === id);
    const pointOf = (id) => {
      const p = findP(id); if (!p || !p.groups.length) return null;
      const v = new THREE.Vector3(); p.groups[0].getWorldPosition(v); v.add(p.anchor); v.project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (-v.y + 1) / 2 * r.height, front: v.z < 1, part: p.part, color: p.elColor };
    };
    const colorOf = (id) => { const p = findP(id); return p ? p.elColor : null; };
    const partsOf = (seg) => byIdx.filter(x => x && x.seg === seg).map(x => x.part);
    const view = {
      highlight, cam, screen, stats, setAnim, hitAt, mats, audit, pointOf, colorOf, partsOf,
      // 兩種模式（DECISIONS #238）：tech／read；舊名字會被映射
      setPal: (n) => applyPal(n), pal: () => pal, pals: () => PALS.slice(), palName: (n) => PAL_NAME[n] || n,
      // 爆炸拆解：讀／設 0～1（設了就把補間停掉，給驗收用）
      explode: (t) => { if (t != null) { expAnim = null; applyExplode(+t); expTarget = +t >= 0.5 ? 1 : 0; } return expT; },
      /* #246：展開／收攏的程式介面。setExplode(on)＝跟游標移進／移開同一條路（會補間）；
         setExplode(on, true)＝一幀到位。hoverExplode() 說這台裝置是不是「游標控制」。*/
      setExplode: (on, instant) => setExplode(!!on, !!instant),
      explodeTarget: () => expTarget,
      hoverExplode: () => canHover,
      /* replay()：**語意在 #246 改了**。以前它是「重播進場的爆炸動畫」（進場本來就會自己爆開）；
         現在進場一律收攏，所以它變成「先收攏、再跑一次展開補間」——
         給「我想再看一次它怎麼拆開」與驗收用。回傳值的意思不變：
         true＝真的會有過場、false＝不補間直接到位（動畫關掉或系統要求減少動態效果）。*/
      replay: () => {
        if (reduced || !anim) { setExplode(true, true); return false; }
        expAnim = null; applyExplode(0); setExplode(true); return true;
      },
      isAnim: () => anim,
      // C6：「使用者關掉動畫時畫面真的停了嗎」——比 motion() 與 stats() 裡的那幾個時鐘
      motion: () => motionOn(),
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
    const K = kit(THREE, FAMILY[kind] || 'metal', false, css);
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
