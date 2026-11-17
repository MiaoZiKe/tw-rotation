// 地板防黑（2026-11-17，擁有者截圖：站長辦公室白天，部門房間之間的走道整片純黑）
// 為什麼要這支：地板（木地板底的貼圖材質、區塊模式的鋪面）一旦在某些顯示卡／瀏覽器上貼圖沒上傳、著色器沒編成，
//   畫面就是一整片黑，使用者什麼都看不出來也沒人通報。軟體繪圖環境重現不出來，所以改成「畫面自己檢查」：
//   每隔約 1 秒（牆鐘，低幀率也一樣）在剛畫完的畫面上讀 走道上約 100～200 個取樣點的真實像素，連續 3 次有 6 成以上都近黑（R、G、B 都 < 40），
//   就把地板材質換成最單純的純色材質（沒有貼圖、沒有客製著色器），並在 W.floorGuard.healed 記下次數。
//   取樣很輕：只在每 0.9 秒讀一次、約 150 個 1×1 像素，讀完不影響畫面。夜晚地板最暗也有 > 60 的亮度（見 20261117_office_night_bubbles），不會誤判。
// 驗收：scripts/uitest_sections/20261117_office_nofloorhole.py（故意把地板塗黑 → 護欄必須在幾秒內換回正常顏色）。
import * as THREE from 'three';

const NEAR_BLACK = 40, EVERY_MS = 900, NEED = 3, RATIO = 0.6;

export function createFloorGuard(W) {
  const G = { healed: 0, key: '', spots: [], last: null, bad: 0, t: 0, on: true };
  const gl = W.renderer.getContext(), v = new THREE.Vector3(), px = new Uint8Array(4);
  const rect = () => { if (W.blocks) { const f = W.blocks.floor(); return { x0: f.x0, x1: f.x1, z0: f.z0, z1: f.z1 }; } return { x0: 0, x1: W.layout.size.w, z0: 0, z1: W.layout.size.d }; };
  // 目前地板用的網格：完整辦公室＝木地板底；區塊模式＝動態鋪面
  const meshes = () => { const a = []; if (W.floorBase && W.floorBase.visible) a.push(W.floorBase); const m = W.blocks && W.blocks.floorMesh && W.blocks.floorMesh(); if (m) a.push(m); return a; };
  // 取樣點：只取「房間地板以外」的走道與空地（房間自己有色塊地板，黑了也不是這支要管的；走道才是地板底露出來的地方）
  const spots = r => { const a = [], rooms = W.layout.rooms || []; for (let i = 0; i < 24; i++) for (let j = 0; j < 18; j++) { const x = r.x0 + (r.x1 - r.x0) * (i + 0.5) / 24, z = r.z0 + (r.z1 - r.z0) * (j + 0.5) / 18; if (!rooms.some(q => x > q.x - 0.3 && x < q.x + q.w + 0.3 && z > q.z - 0.3 && z < q.z + q.d + 0.3)) a.push([x, z]); } return a; };
  G.sample = () => {                       // 讀「剛畫完的畫面」；回傳 { n: 在畫面內的取樣點數, black: 近黑點數 }
    const cam = W.camera, bw = gl.drawingBufferWidth, bh = gl.drawingBufferHeight, r = rect(), key = JSON.stringify(r) + (W.layout.rooms || []).length; cam.updateMatrixWorld();
    if (G.key !== key) { G.key = key; G.spots = spots(r); } let n = 0, black = 0;
    for (const [x, z] of G.spots) {
      v.set(x, 0.05, z).project(cam);
      if (v.z > 1 || Math.abs(v.x) > 0.98 || Math.abs(v.y) > 0.98) continue;
      gl.readPixels(Math.floor((v.x + 1) / 2 * bw), Math.floor((v.y + 1) / 2 * bh), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); n++;
      if (px[0] < NEAR_BLACK && px[1] < NEAR_BLACK && px[2] < NEAR_BLACK) black++;
    }
    return { n, black };
  };
  G.heal = () => {                         // 換成沒有貼圖、沒有客製著色器的純色材質（顏色跟原本的木地板／米色鋪面一致）
    for (const m of meshes()) { if (m.userData.floorHealed) continue; const vc = m !== W.floorBase; const old = m.material; m.material = new THREE.MeshLambertMaterial(vc ? { vertexColors: true } : { color: '#f3dcba' }); m.material.userData.healed = true; m.userData.floorHealed = true; if (old && old.dispose) old.dispose(); G.healed++; }
    G.bad = 0; W.shadowDirty && W.shadowDirty();
  };
  G.afterRender = () => {                  // main.js 在 renderer.render 後立刻呼叫（同一個工作階段內才讀得到畫面）
    const now = performance.now(); if (!G.on || now - G.t < EVERY_MS) return; G.t = now;
    const s = G.last = G.sample(); if (s.n < 12) return;
    G.bad = s.black / s.n >= RATIO ? G.bad + 1 : 0; if (G.bad >= NEED) G.heal();
  };
  return G;
}
