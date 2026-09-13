/* 產品剖析圖的「真 3D」版本（Three.js）。

   Andy 要「圖片需要改成具備長寬高概念，並非 2D 平面」，而且拍板先試 Three.js。
   四條硬性驗收（做不到就退回 SVG 等角圖，不要硬上）：
     1. 可以繞著機櫃轉                      → OrbitControls
     2. 點零件仍然亮起並帶出台股清單         → Raycaster，事件接回 industry.js 原本那條路
     3. 文字標籤用 DOM 疊上去               → CSS2DRenderer（_preview.py 的文字重疊檢查才還能跑）
     4. WebGL 不能用就自動退回現有 SVG      → supported() 先問，問不到就不掛

   其他刻意的設計：
   - three.js 是**動態 import**，只有真的切到 3D 才付那 670KB；平面圖使用者完全不用載。
   - 函式庫內建在 site/vendor/（Andy 公司網路擋 CDN），OrbitControls 與 CSS2DRenderer 的
     `from 'three'` 已改成相對路徑，所以不需要 import map。
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
    const [THREE, oc, css] = await Promise.all([
      import(V + 'three.module.min.js'),
      import(V + 'OrbitControls.js'),
      import(V + 'CSS2DRenderer.js'),
    ]);
    mods = { THREE, OrbitControls: oc.OrbitControls, CSS2DRenderer: css.CSS2DRenderer, CSS2DObject: css.CSS2DObject };
    return mods;
  }

  /* ---------------------------------------------------------------- 場景資料
     單位：1 = 1 公分左右的感覺，機櫃高 42U 畫成 84。
     每個零件：{ seg, name, note, box:[w,h,d], at:[x,y,z], n:重複幾個, gap, axis }
     ★ n > 1 時 at 是**整排的中心**（程式會把整排對稱擺在 at 兩側），不是第一個的位置——
       寫成第一個的位置，整排就會整個偏出機櫃外面（第一版就是這樣，GPU 模組跑到機櫃左邊去了）。
     seg 對得上 supply_chain.yaml 的環節 id —— 點下去就能帶出該環節的台股。*/
  const SCENES = {
    ai_server: {
      title: 'AI 伺服器機櫃（NVL72 式）',
      sub: '18 個運算托盤 × 4 顆 GPU；後方是 NVLink 銅背板，前方是光模組，側邊是電源與液冷',
      camera: [86, 62, 96], target: [0, 34, 0], fit: 1,
      parts: [
        { seg: 'assembly', name: '機櫃與機構件', note: '19吋機櫃、滑軌、鈑金；整櫃出貨前做燒機與水路壓測',
          box: [52, 84, 40], at: [0, 42, 0], frame: true },
        { seg: 'switch', name: 'NVLink 銅背板', note: '機櫃內把 72 顆 GPU 連成一台（scale-up）；走銅不走光',
          box: [46, 52, 3], at: [0, 44, -17] },
        { seg: 'switch', name: 'NVSwitch 托盤', note: 'NVLink 交換晶片，9 台夾在運算托盤之間',
          box: [44, 2.2, 30], at: [0, 62, 1], n: 3, gap: 6, axis: 'y' },
        { seg: 'adv_pkg', name: '運算托盤 · GPU 模組', note: 'CoWoS-L 封裝：邏輯晶粒（SoIC 堆疊）＋ HBM 放在中介層上',
          box: [9, 2.6, 9], at: [0, 34, 2], n: 4, gap: 10, axis: 'x' },
        { seg: 'foundry', name: 'CPU（Grace / x86）', note: '與 GPU 同板 C2C 連接，負責排程與資料搬運',
          box: [7, 2, 7], at: [0, 34, -11], n: 2, gap: 34, axis: 'x' },
        { seg: 'hbm', name: 'HBM4 記憶體', note: '12–16 層 DRAM 用 TSV 打通；base die 改用邏輯製程、由晶圓代工做',
          box: [3, 3.2, 3], at: [0, 34.4, 9], n: 4, gap: 10, axis: 'x' },
        { seg: 'abf_pcb', name: '主機板 高階 PCB / 載板', note: '托盤底板；載板（欣興/南電/景碩）與伺服器主機板（金像電）供應商不同',
          box: [46, 1.2, 32], at: [0, 31, 0], n: 6, gap: 8, axis: 'y' },
        { seg: 'ccl', name: 'CCL 銅箔基板', note: 'M8/M9 以上超低損耗板材，Df ≤ 0.002 @10GHz；PCB 的原料',
          box: [46, 0.5, 32], at: [0, 30.2, 0] },
        { seg: 'thermal', name: '液冷冷板 / CDU', note: '冷板貼晶片 → UQD 快接頭 → manifold 分歧管 → CDU → 機房一次側',
          box: [4.5, 64, 4.5], at: [31, 38, 0] },
        { seg: 'thermal', name: 'UQD 快接頭 / manifold', note: '漏液是 2026 年最被盯的品質風險；OCP 有規格',
          box: [4, 3, 4], at: [24, 20, 12], n: 3, gap: 14, axis: 'y' },
        { seg: 'power', name: '電源櫃 PSU', note: '今天是 415V AC 進 PSU → 機櫃內 DC busbar；800V HVDC 是下一世代',
          box: [22, 5, 30], at: [0, 13, 0], n: 3, gap: 6, axis: 'y' },
        { seg: 'power', name: 'BBU 電池 / 超級電容', note: '掉電到柴發接手之間撐住；超電處理 GPU 毫秒級功率突波',
          box: [18, 4, 26], at: [0, 4, 0] },
        { seg: 'optical', name: '光模組 / CPO', note: '800G–1.6T 前面板可插拔；CPO 把光引擎搬到交換 ASIC 旁',
          box: [2.4, 1.4, 8], at: [0, 72, 15], n: 8, gap: 4.4, axis: 'x' },
        { seg: 'switch', name: 'ToR 交換器', note: '跨機櫃那張網（scale-out）：InfiniBand 或 Ethernet',
          box: [46, 4, 30], at: [0, 76, 0] },
        { seg: 'hyperscaler', name: '雲端業者 / Neocloud', note: '終端需求：CSP、主權 AI、Neocloud',
          box: [26, 4, 18], at: [0, 90, 0], ghost: true },
      ],
    },
    semiconductor: {
      title: 'CoWoS-L 先進封裝剖面',
      sub: '由下往上：載板 → RDL 有機重佈線 ＋ LSI 矽橋 → 晶粒與 HBM → 上蓋；灰色是台廠切不進去的部分',
      camera: [50, 34, 52], target: [0, 8, 0], fit: 1,
      parts: [
        { seg: 'abf_pcb', name: 'ABF 載板', note: 'core + 增層，雷射盲孔電鍍銅；把幾萬個接點扇出到主機板',
          box: [44, 3, 34], at: [0, 1.5, 0] },
        { seg: 'abf_pcb', name: 'BGA 錫球', note: '載板連到主機板',
          box: [2, 1.6, 2], at: [0, -0.4, -12], n: 6, gap: 7.2, axis: 'x' },
        { seg: 'adv_pkg', name: 'RDL 重佈線層（CoWoS-L）', note: '2026 主力是 L 不是 S：有機 RDL ＋ 局部矽橋，不是一整片矽中介層',
          box: [36, 1.6, 26], at: [0, 3.8, 0] },
        { seg: 'adv_pkg', name: 'LSI 局部矽橋', note: '只埋在晶粒交界處，負責 die-to-die 的高密度連線',
          box: [6, 1, 10], at: [0, 5.2, 0], n: 2, gap: 12, axis: 'x' },
        { seg: 'foundry', name: 'GPU 晶粒（SoIC 堆疊）', note: '先 SoIC 混合鍵合疊兩顆（銅對銅無凸塊），再進 CoWoS-L',
          box: [14, 2.4, 14], at: [0, 6.6, 0] },
        { seg: 'foundry', name: 'SoIC 上層晶粒', note: '3D 堆疊的第二顆，台積電差異化的核心',
          box: [12, 1.8, 12], at: [0, 8.8, 0] },
        { seg: 'hbm', name: 'HBM4 堆疊', note: '12–16 層 DRAM ＋ TSV ＋ base die（邏輯製程，台廠位置在這）',
          box: [7, 5.4, 11], at: [0, 8, 0], n: 2, gap: 26, axis: 'x' },
        { seg: 'adv_pkg', name: 'Underfill / MUF', note: '底填膠，撐住凸塊並分散應力；日商為主',
          box: [34, 0.8, 24], at: [0, 5.6, 0], ghost: true },
        { seg: 'adv_pkg', name: 'Stiffener 補強環', note: '大尺寸封裝防翹曲',
          box: [42, 2, 3], at: [0, 6, 0], n: 2, gap: 30, axis: 'z' },
        { seg: 'osat_test', name: '探針卡 / 測試座', note: 'CP 晶圓測試與 FT 成品測試；AI 晶片測試時間長，是良率成本大宗',
          box: [10, 1.2, 10], at: [24, 3, 16], ghost: true },
        { seg: 'adv_pkg', name: '散熱上蓋 + TIM', note: 'TIM1 在晶粒↔上蓋、TIM2 在上蓋↔冷板',
          box: [40, 2.2, 30], at: [0, 12.4, 0], ghost: true },
      ],
    },
  };

  function hasScene(id) { return !!SCENES[id]; }

  /* ---------------------------------------------------------------- 建場景 */
  async function mount(el, sceneId, opts) {
    const spec = SCENES[sceneId];
    if (!el || !spec || !supported()) return null;
    const o = Object.assign({ color: () => '#8ea0c4', onSeg: null }, opts || {});
    const { THREE, OrbitControls, CSS2DRenderer, CSS2DObject } = await load();

    const W = () => Math.max(320, el.clientWidth);
    // 機櫃是直立的，畫面比例太扁會把上下切掉；0.62 是讓 42U 機櫃連同標籤都塞得下的比例
    const H = () => Math.max(360, Math.round(Math.min(700, el.clientWidth * 0.62)));

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, W() / H(), 1, 2000);
    camera.position.set(spec.camera[0], spec.camera[1], spec.camera[2]);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(W(), H());
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.borderRadius = '10px';
    el.appendChild(renderer.domElement);

    const labels = new CSS2DRenderer();
    labels.setSize(W(), H());
    labels.domElement.style.position = 'absolute';
    labels.domElement.style.top = '0';
    labels.domElement.style.left = '0';
    labels.domElement.style.pointerEvents = 'none';
    el.style.position = 'relative';
    el.appendChild(labels.domElement);

    // 深色科技風的打光：底光壓暗、主光從右前上、青色補光描邊
    scene.add(new THREE.HemisphereLight(0x8ea0c4, 0x070b16, 0.55));
    const key = new THREE.DirectionalLight(0xffffff, 1.15); key.position.set(60, 90, 70); scene.add(key);
    const rim = new THREE.DirectionalLight(0x3ee0ff, 0.5); rim.position.set(-70, 40, -60); scene.add(rim);

    const root = new THREE.Group(); scene.add(root);
    const picks = [];            // 可以點的 mesh
    const byIdx = [];            // 每個零件的所有 mesh + 原始材質，highlight 時用
    let labelDown = null;        // 這次按下去是從某個標籤開始的（可能只是想轉視角）

    const mkMat = (hex, ghost) => new THREE.MeshStandardMaterial({
      color: new THREE.Color(hex), roughness: ghost ? 0.9 : 0.42, metalness: ghost ? 0.05 : 0.55,
      transparent: !!ghost, opacity: ghost ? 0.16 : 1,
      emissive: new THREE.Color(hex), emissiveIntensity: ghost ? 0.02 : 0.08,
    });

    spec.parts.forEach((p, idx) => {
      const hex = o.color(p.seg) || '#8ea0c4';
      const n = p.n || 1, gap = p.gap || 0, axis = p.axis || 'x';
      const meshes = [];
      for (let i = 0; i < n; i++) {
        let mesh;
        if (p.frame) {
          // 機櫃只畫框：實心會把裡面全擋住
          const g = new THREE.BoxGeometry(p.box[0], p.box[1], p.box[2]);
          mesh = new THREE.LineSegments(new THREE.EdgesGeometry(g),
            new THREE.LineBasicMaterial({ color: new THREE.Color(hex), transparent: true, opacity: 0.75 }));
          g.dispose();
        } else {
          mesh = new THREE.Mesh(new THREE.BoxGeometry(p.box[0], p.box[1], p.box[2]), mkMat(hex, p.ghost));
          if (p.ghost) {
            /* 透明件（上蓋、底填膠、補強環）只有半透明色塊時會糊成一片藍板，
               把底下的晶粒都洗掉。補一圈邊線，讀起來才像「外殼」而不是「一塊玻璃」。*/
            const eg = new THREE.EdgesGeometry(mesh.geometry);
            mesh.add(new THREE.LineSegments(eg, new THREE.LineBasicMaterial({
              color: new THREE.Color(hex), transparent: true, opacity: 0.55 })));
          }
        }
        const off = (i - (n - 1) / 2) * gap;
        mesh.position.set(p.at[0] + (axis === 'x' ? off : 0),
          p.at[1] + (axis === 'y' ? off : 0),
          p.at[2] + (axis === 'z' ? off : 0));
        mesh.userData = { seg: p.seg, idx, name: p.name, note: p.note };
        root.add(mesh); meshes.push(mesh);
        if (!p.frame) picks.push(mesh);
      }
      byIdx[idx] = { seg: p.seg, meshes, hex, ghost: !!p.ghost };

      // 標籤：DOM 疊上去，不是畫進畫布，所以選得起來、也還驗得到文字重疊
      const d = document.createElement('div');
      d.className = 'lbl3d';
      d.innerHTML = `<b>${p.name}</b>`;
      d.dataset.seg = p.seg;
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
      const lab = new CSS2DObject(d);
      const first = meshes[0];
      lab.position.set(first.position.x, first.position.y + p.box[1] / 2 + 2.5, first.position.z);
      root.add(lab);
      byIdx[idx].label = lab;
    });

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true; controls.dampingFactor = 0.08;
    controls.target.set(spec.target[0], spec.target[1], spec.target[2]);
    controls.maxPolarAngle = Math.PI * 0.495;      // 不要轉到地板底下

    /* 相機距離用「把整個場景包起來的球」算出來，不要寫死：
       寫死的話換一個場景、或畫面比例一變，機櫃頭尾就被切掉（第一版就是這樣）。 */
    const fitCamera = () => {
      const box = new THREE.Box3().setFromObject(root);
      const sph = box.getBoundingSphere(new THREE.Sphere());
      const size = box.getSize(new THREE.Vector3());
      const vfov = camera.fov * Math.PI / 180;
      const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
      /* 用「外接盒」而不是「外接球」算距離：球對又扁又寬的封裝剖面會多退 30%，
         畫面中間只剩一小塊。半個深度是留給轉動時最靠近相機的那一角。 */
      const halfW = Math.max(size.x, size.z) / 2, halfH = size.y / 2, halfD = Math.max(size.x, size.z) / 2;
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
    const hit = () => { ray.setFromCamera(ptr, camera); const xs = ray.intersectObjects(picks, false); return xs[0] && xs[0].object; };
    renderer.domElement.addEventListener('pointerdown', (e) => { downAt = { x: e.clientX, y: e.clientY }; });
    const onUp = (e) => {
      const from = labelDown; labelDown = null;
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
    labels.domElement.addEventListener('pointerup', onUp);
    renderer.domElement.addEventListener('pointermove', (e) => {
      toNdc(e); renderer.domElement.style.cursor = hit() ? 'pointer' : 'grab';
    });

    // ---- 高亮：和 SVG 版同一個介面（highlightSegments 會呼叫它）
    function highlight(on, color) {
      const has = on && on.size > 0;
      byIdx.forEach(p => {
        if (!p) return;
        const sel = has && on.has(p.seg);
        p.meshes.forEach(m => {
          if (!m.material) return;
          if (m.material.emissiveIntensity !== undefined) {
            m.material.emissiveIntensity = sel ? 0.65 : (p.ghost ? 0.02 : 0.08);
          }
          if (m.material.opacity !== undefined && m.material.transparent) {
            m.material.opacity = has && !sel ? 0.12 : (p.ghost ? 0.16 : 1);
          } else if (m.material.transparent !== undefined) {
            m.material.transparent = has && !sel;
            m.material.opacity = has && !sel ? 0.18 : 1;
          }
          if (sel && color && m.material.color) m.material.color.set(color);
          else if (m.material.color) m.material.color.set(p.hex);
        });
        if (p.label && p.label.element) {
          p.label.element.classList.toggle('sel', sel);
          p.label.element.classList.toggle('dim', has && !sel);
        }
      });
    }

    /* ---- 標籤避讓：轉到某些角度時零件會擠在一起，標籤就疊成一團看不懂。
       每次相機停下來重排一次：選起來的優先，其次是離相機近的（看得最清楚的那個），
       跟已保留的標籤矩形相撞就藏起來。~15 個元素、每秒最多幾次，成本可以忽略。*/
    const labelBoxes = [];
    function layoutLabels() {
      labelBoxes.length = 0;
      const v = new THREE.Vector3();
      const arr = [];
      byIdx.forEach(p => {
        if (!p || !p.label || !p.label.element) return;
        const e = p.label.element;
        e.classList.remove('hid');
        p.meshes[0].getWorldPosition(v);
        arr.push({ e, d: v.distanceTo(camera.position), sel: e.classList.contains('sel') ? 1 : 0 });
      });
      arr.sort((a, b) => (b.sel - a.sel) || (a.d - b.d));
      arr.forEach(it => {
        const r = it.e.getBoundingClientRect();
        if (!r.width) return;
        // 選起來的標籤永遠不藏：使用者剛點的那個不見了最莫名其妙
        const clash = !it.sel && labelBoxes.some(k => !(r.right < k.left - 2 || r.left > k.right + 2
          || r.bottom < k.top - 2 || r.top > k.bottom + 2));
        if (clash) it.e.classList.add('hid');
        else labelBoxes.push({ left: r.left, right: r.right, top: r.top, bottom: r.bottom });
      });
    }

    // ---- 只在看得到的時候畫
    let raf = null, alive = true, visible = true, relayout = 0;
    const tick = () => {
      if (!alive) return;
      raf = requestAnimationFrame(tick);
      if (!visible) return;
      controls.update();
      renderer.render(scene, camera);
      labels.render(scene, camera);
      // 每 8 幀重排一次標籤：轉的時候跟得上，停著的時候幾乎不花錢
      if (++relayout % 8 === 0) layoutLabels();
    };
    const io = typeof IntersectionObserver !== 'undefined'
      ? new IntersectionObserver(es => { visible = es.some(x => x.isIntersecting); }, { threshold: 0.02 }) : null;
    if (io) io.observe(el);
    const onVis = () => { visible = document.visibilityState !== 'hidden'; };
    document.addEventListener('visibilitychange', onVis);
    const onResize = () => {
      camera.aspect = W() / H(); camera.updateProjectionMatrix();
      renderer.setSize(W(), H()); labels.setSize(W(), H());
    };
    window.addEventListener('resize', onResize);
    tick();

    function dispose() {
      alive = false;
      if (raf) cancelAnimationFrame(raf);
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
      if (labels.domElement.parentNode) labels.domElement.parentNode.removeChild(labels.domElement);
    }

    // cam()／screen() 是給驗收腳本用的：驗「視角真的轉了」要比對相機座標
    // （canvas 沒開 preserveDrawingBuffer，readPixels 一律回 0，抓不到差異），
    // 驗「點零件」要知道某個零件現在在螢幕上的哪裡，才不是亂點一個座標碰運氣。
    const cam = () => [camera.position.x, camera.position.y, camera.position.z].map(v => +v.toFixed(2));
    const screen = (seg) => {
      const p = byIdx.find(x => x && x.seg === seg && x.meshes.length);
      if (!p) return null;
      const v = new THREE.Vector3(); p.meshes[0].getWorldPosition(v); v.project(camera);
      const r = renderer.domElement.getBoundingClientRect();
      return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (-v.y + 1) / 2 * r.height, front: v.z < 1 };
    };
    const view = {
      highlight, cam, screen,
      segs: () => byIdx.filter(Boolean).map(p => p.seg),
      dispose: () => { dispose(); if (global.Rack3D.current === view) global.Rack3D.current = null; },
      // 重設時先關阻尼：不然上一次拖曳殘留的慣性會讓相機停在預設視角旁邊一點點
      /* 重設視角要跟第一次進來看到的「一模一樣」。麻煩的是 OrbitControls 內部還留著
         上一次拖曳的慣性（sphericalDelta），而且關掉阻尼時 update() 會把殘留量**整份**套上去，
         相機就會停在預設視角旁邊一兩度。先用 dampingFactor = 1 跑一次 update 把殘留吃光並歸零，
         再關阻尼重新取景，結果才是精準的。*/
      reset: () => {
        const damp = controls.enableDamping, df = controls.dampingFactor;
        controls.enableDamping = true; controls.dampingFactor = 1;
        controls.update();
        controls.enableDamping = false;
        fitCamera();
        controls.enableDamping = damp; controls.dampingFactor = df;
        layoutLabels();
      },
      title: spec.title, sub: spec.sub,
    };
    global.Rack3D.current = view;     // 驗收腳本從這裡拿現場的相機與零件位置
    return view;
  }

  global.Rack3D = { supported, hasScene, mount, SCENES, current: null };
})(window);
