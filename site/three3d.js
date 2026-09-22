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
      pt.userData.flow = { paths, per, t: 0, dir: 1, speed: spec.speed || 0.25 };
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
      _cutSlab: cutSlab, _cutFace: cutFace, _twoSided: twoSided, _hbmLayout: hbmLayout };
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
    const applyExplode = (t) => {
      expT = Math.max(0, Math.min(1, t));
      explodable.forEach(g => {
        const b = g.userData.base, e = g.userData.ex;
        g.position.set(b.x + e[0] * expT, b.y + e[1] * expT, b.z + e[2] * expT);
      });
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
      if (anim && now0 - lastDraw < 32) return;                  // ① 動畫上限 30fps
      const dt = Math.min(0.05, (performance.now() - t0) / 1000); t0 = performance.now();
      if (anim) {
        spinners.forEach(s => { s.rotation[s.userData.spin.axis] += s.userData.spin.speed * dt; });
        const lb = palNum('--dg-led', 0.55);
        const k = lb + lb * 0.55 * (0.5 + 0.5 * Math.sin(performance.now() / 620));
        leds.forEach(m => { if (m.emissiveIntensity > 0.02) m.emissiveIntensity = k; });
        stepFlows(dt);
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
      if (!anim && !dirty && now0 - lastDraw < 400) return;      // ②③ 靜止：沒變就不畫，400ms 補一張
      renderer.render(scene, camera);
      lastDraw = now0; dirty = false;
      // 自轉時每 4 幀重排一次標籤（引線要跟得上零件）；靜止時畫一次就排一次，才不會晚半秒才對齊
      if (anim) { if (++relayout % 4 === 0) layoutLabels(); } else layoutLabels();
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
