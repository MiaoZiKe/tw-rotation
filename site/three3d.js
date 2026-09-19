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
     每個零件：{ seg, name, note, kind, box:[w,h,d], at:[x,y,z], n:重複幾個, gap, axis }
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
        { seg: 'assembly', name: '機櫃與機構件', note: '19吋機櫃、滑軌、鈑金；整櫃出貨前做燒機與水路壓測',
          kind: 'rack', box: [52, 84, 40], at: [0, 42, 0], frame: true },
        { seg: 'switch', name: 'NVLink 銅背板', note: '機櫃內把 72 顆 GPU 連成一台（scale-up）；走銅不走光',
          kind: 'backplane', box: [46, 52, 3], at: [0, 44, -17] },
        { seg: 'switch', name: 'NVSwitch 托盤', note: 'NVLink 交換晶片，9 台夾在運算托盤之間',
          kind: 'tray', box: [44, 2.2, 30], at: [0, 62, 1], n: 3, gap: 6, axis: 'y' },
        { seg: 'adv_pkg', name: '運算托盤 · GPU 模組', note: 'CoWoS-L 封裝：邏輯晶粒（SoIC 堆疊）＋ HBM 放在中介層上',
          kind: 'gpu', box: [9, 2.6, 9], at: [0, 34, 2], n: 4, gap: 10, axis: 'x' },
        { seg: 'foundry', name: 'CPU（Grace / x86）', note: '與 GPU 同板 C2C 連接，負責排程與資料搬運',
          kind: 'chip', box: [7, 2, 7], at: [0, 34, -11], n: 2, gap: 34, axis: 'x' },
        { seg: 'hbm', name: 'HBM4 記憶體', note: '12–16 層 DRAM 用 TSV 打通；base die 改用邏輯製程、由晶圓代工做',
          kind: 'hbm', box: [3, 3.2, 3], at: [0, 34.4, 9], n: 4, gap: 10, axis: 'x' },
        { seg: 'abf_pcb', name: '主機板 高階 PCB / 載板', note: '托盤底板；載板（欣興/南電/景碩）與伺服器主機板（金像電）供應商不同',
          kind: 'pcb', box: [46, 1.2, 32], at: [0, 31, 0], n: 6, gap: 8, axis: 'y' },
        { seg: 'ccl', name: 'CCL 銅箔基板', note: 'M8/M9 以上超低損耗板材，Df ≤ 0.002 @10GHz；PCB 的原料',
          kind: 'laminate', box: [46, 0.5, 32], at: [0, 30.2, 0] },
        { seg: 'thermal', name: '液冷冷板 / CDU', note: '冷板貼晶片 → UQD 快接頭 → manifold 分歧管 → CDU → 機房一次側',
          kind: 'cdu', box: [4.5, 64, 4.5], at: [31, 38, 0] },
        { seg: 'thermal', name: 'UQD 快接頭 / manifold', note: '漏液是 2026 年最被盯的品質風險；OCP 有規格',
          kind: 'uqd', box: [4, 3, 4], at: [24, 20, 12], n: 3, gap: 14, axis: 'y' },
        /* 2026-09-18 新增：Andy 舉的例子就是「風扇有扇片」。真的機櫃後門本來就有風扇牆，
           原本的場景整個漏掉這一段，等於把散熱只畫了液冷那一半。*/
        { seg: 'thermal', name: '後門風扇模組', note: '液冷之外仍要帶走記憶體與電源的熱；風扇牆掛在後門',
          kind: 'fan', box: [13, 13, 5], at: [0, 24, 19], n: 3, gap: 15, axis: 'x' },
        { seg: 'power', name: '電源櫃 PSU', note: '今天是 415V AC 進 PSU → 機櫃內 DC busbar；800V HVDC 是下一世代',
          kind: 'psu', box: [22, 5, 30], at: [0, 13, 0], n: 3, gap: 6, axis: 'y' },
        { seg: 'power', name: 'BBU 電池 / 超級電容', note: '掉電到柴發接手之間撐住；超電處理 GPU 毫秒級功率突波',
          kind: 'battery', box: [18, 4, 26], at: [0, 4, 0] },
        { seg: 'optical', name: '光模組 / CPO', note: '800G–1.6T 前面板可插拔；CPO 把光引擎搬到交換 ASIC 旁',
          kind: 'optic', box: [2.4, 1.4, 8], at: [0, 72, 15], n: 8, gap: 4.4, axis: 'x' },
        { seg: 'switch', name: 'ToR 交換器', note: '跨機櫃那張網（scale-out）：InfiniBand 或 Ethernet',
          kind: 'switch', box: [46, 4, 30], at: [0, 76, 0] },
        { seg: 'hyperscaler', name: '雲端業者 / Neocloud', note: '終端需求：CSP、主權 AI、Neocloud',
          box: [26, 4, 18], at: [0, 90, 0], ghost: true },
      ],
    },
    semiconductor: {
      title: 'CoWoS-L 先進封裝剖面',
      sub: '由下往上：載板 → RDL 有機重佈線 ＋ LSI 矽橋 → 晶粒與 HBM → 上蓋；灰色是台廠切不進去的部分',
      camera: [50, 34, 52], target: [0, 8, 0], fit: 1, hk: 0.46,
      parts: [
        { seg: 'abf_pcb', name: 'ABF 載板', note: 'core + 增層，雷射盲孔電鍍銅；把幾萬個接點扇出到主機板',
          kind: 'substrate', box: [44, 3, 34], at: [0, 1.5, 0] },
        { seg: 'abf_pcb', name: 'BGA 錫球', note: '載板連到主機板',
          kind: 'balls', box: [2, 1.6, 2], at: [0, -0.4, -12], n: 6, gap: 7.2, axis: 'x' },
        { seg: 'adv_pkg', name: 'RDL 重佈線層（CoWoS-L）', note: '2026 主力是 L 不是 S：有機 RDL ＋ 局部矽橋，不是一整片矽中介層',
          kind: 'rdl', box: [36, 1.6, 26], at: [0, 3.8, 0] },
        { seg: 'adv_pkg', name: 'LSI 局部矽橋', note: '只埋在晶粒交界處，負責 die-to-die 的高密度連線',
          kind: 'bridge', box: [6, 1, 10], at: [0, 5.2, 0], n: 2, gap: 12, axis: 'x' },
        { seg: 'foundry', name: 'GPU 晶粒（SoIC 堆疊）', note: '先 SoIC 混合鍵合疊兩顆（銅對銅無凸塊），再進 CoWoS-L',
          kind: 'die', box: [14, 2.4, 14], at: [0, 6.6, 0] },
        { seg: 'foundry', name: 'SoIC 上層晶粒', note: '3D 堆疊的第二顆，台積電差異化的核心',
          kind: 'die', box: [12, 1.8, 12], at: [0, 8.8, 0] },
        { seg: 'hbm', name: 'HBM4 堆疊', note: '12–16 層 DRAM ＋ TSV ＋ base die（邏輯製程，台廠位置在這）',
          kind: 'hbm', box: [7, 5.4, 11], at: [0, 8, 0], n: 2, gap: 26, axis: 'x' },
        { seg: 'adv_pkg', name: 'Underfill / MUF', note: '底填膠，撐住凸塊並分散應力；日商為主',
          box: [34, 0.8, 24], at: [0, 5.6, 0], ghost: true },
        { seg: 'adv_pkg', name: 'Stiffener 補強環', note: '大尺寸封裝防翹曲',
          box: [42, 2, 3], at: [0, 6, 0], n: 2, gap: 30, axis: 'z' },
        { seg: 'osat_test', name: '探針卡 / 測試座', note: 'CP 晶圓測試與 FT 成品測試；AI 晶片測試時間長，是良率成本大宗',
          kind: 'probe', box: [10, 1.2, 10], at: [24, 3, 16] },
        { seg: 'adv_pkg', name: '散熱上蓋 + TIM', note: 'TIM1 在晶粒↔上蓋、TIM2 在上蓋↔冷板',
          box: [40, 2.2, 30], at: [0, 12.4, 0], ghost: true },
      ],
    },
  };

  function hasScene(id) { return !!SCENES[id]; }

  /* ================================================================ E3：零件建造函式
     每支拿到 (T, p, K)：T 是 THREE、p 是零件資料、K 是這個零件專屬的材質工具箱。
     一律「畫在自己的局部座標、以 box 的中心為原點」，擺位交給外面統一處理。
     K.mat(明暗, 選項) 回傳材質：明暗 > 0 偏亮、< 0 偏暗，同一組參數會共用同一顆材質，
     highlight() 才有辦法一次把整個零件變透明。led:true 的是指示燈（E2 唯一准發光的東西）。 */
  function kit(THREE, hex, ghost) {
    const base = new THREE.Color(hex);
    const white = new THREE.Color(0xffffff), dark = new THREE.Color(0x070b14);
    const cache = {}, all = [];
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
      cache[key] = m; all.push(m);
      return m;
    }
    // 邊線用的 LineBasicMaterial 不是從 mat() 來的，要自己登記，highlight 才吃得到它
    const reg = (m) => { all.push(m); return m; };
    return { mat, col, reg, mats: all };
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
      for (let r = -1; r <= 1; r++) for (let c = -2; c <= 2; c++) {
        g.add(put(box(w * 0.1, h * 0.14, d * 0.9, cm), c * w * 0.18, r * h * 0.26, d * 0.35));
      }
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

    // 主機板：板子 ＋ 線路層 ＋ 幾顆 IC ＋ 插槽 ＋ 電容
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
      for (let i = -4; i <= 4; i++) for (let j = -1; j <= 1; j += 2) {
        const c = cyl(w * 0.02, d * 0.06, hole, 6);
        c.rotation.x = Math.PI / 2;              // 圓柱預設立著，要放倒才會是「面對前面板的孔」
        g.add(put(c, i * w * 0.08, j * h * 0.22, d / 2));
      }
      g.add(put(box(w * 0.26, h * 0.16, d * 0.05, K.mat(0.3, { metal: 0.5 })), -w * 0.3, 0, d / 2 + d * 0.02));
      g.add(put(box(w * 0.05, h * 0.16, d * 0.03, K.mat(0, { led: true })), w * 0.38, 0, d / 2 + d * 0.02));
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
      for (let i = -2; i <= 3; i++) for (let j = -1; j <= 1; j += 2) {
        g.add(put(cyl(w * 0.055, h * 0.8, cellM, 10), (i - 0.5) * w * 0.15, h * 0.06, j * d * 0.24));
      }
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

    // ABF 載板：core ＋ 上下增層 ＋ 表面的細線路
    function substrate(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h * 0.5, d, K.mat(-0.3, { rough: 0.8, metal: 0.06 })));
      [-1, 1].forEach(s => g.add(put(box(w * 0.99, h * 0.22, d * 0.99, K.mat(-0.05, { rough: 0.6 })), 0, s * h * 0.36, 0)));
      const tr = K.mat(0.45, { metal: 0.7, rough: 0.3 });
      for (let i = -7; i <= 7; i++) g.add(put(box(w * 0.9, h * 0.06, d * 0.012, tr), 0, h * 0.48, i * d * 0.06));
      return g;
    }

    // BGA 錫球：球就是球，方塊看起來像腳墊
    function balls(p, K) {
      const g = new T.Group();
      const [w, h] = p.box;
      const m = K.mat(0.35, { metal: 0.6, rough: 0.35 });
      for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) {
        g.add(put(ball(Math.min(w, h) * 0.42, m), i * w * 0.9, 0, j * w * 0.9));
      }
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

    // 晶粒：矽片 ＋ 表面功能區塊格
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
      return g;
    }

    // 探針卡：基板 ＋ 一叢探針
    function probe(p, K) {
      const g = new T.Group();
      const [w, h, d] = p.box;
      g.add(box(w, h, d, K.mat(-0.15, { rough: 0.7 })));
      const pin = K.mat(0.45, { metal: 0.8, rough: 0.25 });
      for (let i = -2; i <= 2; i++) for (let j = -2; j <= 2; j++) {
        g.add(put(cyl(w * 0.012, h * 1.6, pin, 6), i * w * 0.16, -h * 0.9, j * d * 0.16));
      }
      return g;
    }

    return { plain, rack, backplane, tray, gpu, chip, hbm, pcb, laminate, cdu, uqd, fan, psu, battery,
      optic, switch: switchBox, substrate, balls, rdl, bridge, die, probe };
  }

  /* ---------------------------------------------------------------- 建場景 */
  async function mount(el, sceneId, opts) {
    const spec = SCENES[sceneId];
    if (!el || !spec || !supported()) return null;
    const o = Object.assign({ color: () => '#8ea0c4', onSeg: null, anim: true }, opts || {});
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
    scene.add(new THREE.HemisphereLight(0x99a7c2, 0x0b1120, 0.62));
    const key = new THREE.DirectionalLight(0xffffff, 1.0); key.position.set(60, 90, 70); scene.add(key);
    const fill = new THREE.DirectionalLight(0xc7d2e6, 0.34); fill.position.set(-70, 40, -60); scene.add(fill);
    const bounce = new THREE.DirectionalLight(0x8fa0bd, 0.16); bounce.position.set(0, -60, 20); scene.add(bounce);

    const root = new THREE.Group(); scene.add(root);
    const picks = [];            // 可以點的 group
    const byIdx = [];            // 每個零件的所有 mesh + 材質，highlight 時用
    const spinners = [];         // E4：會自己轉的東西（風扇葉輪）
    const leds = [];             // E4：會呼吸的指示燈材質
    let labelDown = null;        // 這次按下去是從某個標籤開始的（可能只是想轉視角）

    spec.parts.forEach((p, idx) => {
      const hex = o.color(p.seg) || '#8ea0c4';
      const K = kit(THREE, hex, p.ghost);
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
        g.userData = { seg: p.seg, idx, name: p.name, note: p.note };
        g.traverse(x => {
          if (x.isMesh) meshes.push(x);
          if (x.userData && x.userData.spin) spinners.push(x);
        });
        root.add(g); groups.push(g);
        if (!p.frame) picks.push(g);
      }
      K.mats.forEach(m => { if (m.userData && m.userData.led) leds.push(m); });
      byIdx[idx] = {
        seg: p.seg, groups, meshes, hex, ghost: !!p.ghost, name: p.name, note: p.note,
        mats: K.mats.slice(),
        baseOp: new Map(K.mats.map(m => [m, m.opacity])),
        baseCol: new Map(K.mats.map(m => [m, m.color.clone()])),
        // 引線接在零件頂端中央：接在中心的話線會插進零件裡看不到
        anchor: new THREE.Vector3(0, p.box[1] / 2, 0),
      };

      // 標籤：DOM 疊上去，不是畫進畫布，所以選得起來、也還驗得到文字重疊
      const d = document.createElement('div');
      d.className = 'lbl3d';
      d.innerHTML = `<b></b><i></i>`;
      d.querySelector('b').textContent = p.name;
      d.querySelector('i').textContent = p.note || '';
      d.dataset.seg = p.seg;
      d.style.setProperty('--c', hex);     // 文字框左邊那條色帶＝環節色，一眼對得上零件
      // 標籤本身也要可以點：機櫃裡的小零件（UQD、光模組）用滑鼠很難精準打到，
      // 點名字是最直覺的路。父層 pointerEvents 是 none，這裡個別開回來。
      d.style.pointerEvents = 'auto';
      d.style.cursor = 'pointer';
      d.title = p.note || p.name;
      d.addEventListener('pointerdown', (e) => {
        labelDown = { seg: p.seg, data: { seg: p.seg, idx, name: p.name, note: p.note } };
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
      if (m && o.onSeg) o.onSeg(m.userData.seg, m.userData);
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
      if (!anim) {
        leds.forEach(m => { m.emissiveIntensity = 0.55; });   // 靜止時燈定在中間亮度
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
    function highlight(on, color) {
      const has = on && on.size > 0;
      const tint = color ? new THREE.Color(color) : null;
      byIdx.forEach(p => {
        if (!p) return;
        const sel = has && on.has(p.seg);
        const fade = has && !sel;
        p.mats.forEach(m => {
          const b = p.baseOp.get(m), bc = p.baseCol.get(m);
          m.opacity = fade ? Math.min(b, 0.12) : b;
          m.transparent = fade || b < 1;
          if (m.userData && m.userData.led) { m.emissiveIntensity = fade ? 0.04 : (sel ? 0.85 : 0.55); return; }
          if (m.emissive) m.emissiveIntensity = sel ? 0.22 : 0;
          // 套族群色時只把原色往那個方向拉一半，保留零件本身的明暗結構
          if (sel && tint) m.color.copy(bc).lerp(tint, 0.55); else m.color.copy(bc);
        });
        if (p.el) {
          p.el.classList.toggle('sel', sel);
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

    // ---- 只在看得到的時候畫
    let raf = null, alive = true, visible = true, relayout = 0, t0 = performance.now();
    const tick = () => {
      if (!alive) return;
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      const dt = Math.min(0.05, (performance.now() - t0) / 1000); t0 = performance.now();
      if (anim) {
        spinners.forEach(s => { s.rotation[s.userData.spin.axis] += s.userData.spin.speed * dt; });
        const k = 0.55 + 0.3 * (0.5 + 0.5 * Math.sin(performance.now() / 620));
        leds.forEach(m => { if (m.emissiveIntensity > 0.1) m.emissiveIntensity = k; });
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
      return { parts: byIdx.filter(Boolean).length, meshes, maxEmissive: +maxEm.toFixed(3),
        idleEmissive: +idleEm.toFixed(3), maxMetal: +maxMetal.toFixed(2), leds: ledN,
        spinners: spinners.length, spinAt: +spinAt.toFixed(3), anim, autoRotate: !!controls.autoRotate };
    };
    const view = {
      highlight, cam, screen, stats, setAnim,
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

  global.Rack3D = { supported, hasScene, mount, SCENES, current: null };
})(window);
