// 新手引導 5 步（2026-11-16，遊戲基礎設定第 7 項）：第一次進辦公室跳出聚光燈式引導，可跳過，可從頂列「?」重看。
//   ① 這是你的辦公室（鏡頭怎麼動）　② 點員工看資訊卡　③ 按住不放拎起員工　④ 對話框對員工下指令　⑤ 總覽面板看誰卡住
//
// 是否自動跳出：
//   · localStorage「aiOffice.game.tour」有值（看完或跳過）就不再自動跳；沒有值才跳。
//   · 自動化瀏覽器（navigator.webdriver）預設不跳，不然所有驗收段落都會被這層蓋住點不到；驗收要看它時網址加 ?tour=1（等於「當真人」，其餘規則不變）。
//   · ?tour=0 強制不跳；?connect=1（從入口頁剛建好辦公室、正在開接入引導）先不跳，免得兩個引導疊在一起，下次進來再跳。
// 做法：整頁蓋一層擋點擊的透明層（不讓人誤點 3D 場景），目標處用一個圓角框「挖洞」（box-shadow 把洞外變暗），說明卡貼在洞的上方或下方。
//   手機（≤640）說明卡固定貼在畫面上緣或下緣，不跟著洞跑，免得蓋住目標。
// 文案禁用字：價格、NT$、付費、升級、訂閱、方案、Plus、Pro、免費、右鍵。
const KEY = 'aiOffice.game.tour';
const $ = id => document.getElementById(id);
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗：只在這次有效 */ } };

const STEPS = [
  { id: 'office', title: '這是你的辦公室', body: '每一個小人都是你的一位 Claude 同事，他們會在這裡工作、休息、聊天。\n拖曳畫面可以移動視角，滾輪（手機用兩指）可以放大縮小，頂列的「俯瞰」看整間。', target: () => null },
  { id: 'card', title: '點一下員工，看他的資訊卡', body: '點任何一位同事，畫面下方會出現他的資訊卡：現在在做什麼、心情、做過哪些事。\n資訊卡上也有摸摸、餵食、讓他休息等按鈕。', target: () => person() },
  { id: 'grab', title: '按住不放，可以拎起員工', body: '在員工身上按住不放（手機用手指按住），他就被拎起來了；放開，他會掉回地上。\n把他放到別的區域，他會有反應，小心別放到火上。', target: () => person() },
  { id: 'chat', title: '用對話框下指令', body: '畫面下方的對話框可以對 CEO 或指定的同事說話、交代工作。\n送出之後會顯示對方有沒有收到、做得怎麼樣。', target: () => rectOf('#chatForm') || rectOf('#chatPanel') },
  { id: 'overview', title: '總覽面板，看誰卡住', body: '按頂列的「總覽」，每位員工一列：工作中、閒置、卡住、著火、疲累。\n點一列鏡頭就飛過去；完成、卡住、著火、升等的消息會收在「通知」，有未讀會亮紅點。', target: () => rectOf('#ovBtn'), last: true },
];

function rectOf(sel) { const e = document.querySelector(sel); if (!e || e.hidden) return null; const r = e.getBoundingClientRect(); return r.width && r.height ? { x: r.left, y: r.top, w: r.width, h: r.height, r: 14 } : null; }
let W = null;
// 找一位在畫面裡看得到的員工（先找 CEO）：用名牌的螢幕座標（main.js 每幀寫在 c._sx／c._sy）
function person() {
  const vw = innerWidth, vh = innerHeight, ok = c => c && c._sx > 20 && c._sx < vw - 20 && c._sy > 70 && c._sy < vh - 60;
  let c = W.chars.get('ceo'); if (!ok(c)) { c = null; for (const q of W.chars.values()) if (!q.spec.pet && !q.absent && ok(q)) { c = q; break; } }
  if (!c) return null;
  return { x: c._sx - 46, y: c._sy - 38, w: 92, h: 110, r: 46, who: c.spec.id };
}

export function startTour(world, opts = {}) {
  W = world || W || window.__world;
  if (document.getElementById('trOv')) return null;
  const T = { i: 0, steps: STEPS };
  const ov = document.createElement('div'); ov.id = 'trOv'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('aria-label', '新手引導');
  ov.innerHTML = `<div class="tr-hole" id="trHole"></div>
    <div class="tr-card" id="trCard"><button class="tr-skip" id="trSkip" type="button">跳過</button>
      <div class="tr-step" id="trStep"></div><h3 id="trTitle"></h3><p id="trBody"></p>
      <div class="tr-dots" id="trDots"></div>
      <div class="tr-act"><button class="btn" id="trPrev" type="button">上一步</button><button class="btn on" id="trNext" type="button">下一步</button></div></div>`;
  (document.getElementById('app') || document.body).append(ov);
  if (W.ui && W.ui.closePops) W.ui.closePops();
  const prevFocus = document.activeElement;

  function finish(how) {
    lsSet(KEY, how === 'skip' ? 'skip' : 'done'); cancelAnimationFrame(T.raf); ov.remove(); document.removeEventListener('keydown', onKey, true);
    T.on = false; if (prevFocus && prevFocus.focus) try { prevFocus.focus({ preventScroll: true }); } catch (e) { /* 略 */ }
    if (opts.onEnd) opts.onEnd(how);
  }
  function layout() {
    const s = STEPS[T.i], t = s.target(), hole = $('trHole'), card = $('trCard'), vw = innerWidth, vh = innerHeight, mob = vw <= 640;
    ov.classList.toggle('nohole', !t);
    if (t) { const pad = 6; hole.style.cssText = `left:${Math.round(t.x - pad)}px;top:${Math.round(t.y - pad)}px;width:${Math.round(t.w + pad * 2)}px;height:${Math.round(t.h + pad * 2)}px;border-radius:${t.r + pad}px`; }
    const cw = Math.min(mob ? vw - 24 : 340, vw - 24), ch = card.offsetHeight || 220; card.style.width = cw + 'px';
    let x = (vw - cw) / 2, y = (vh - ch) / 2;
    if (t) {
      const below = vh - (t.y + t.h) - 14, above = t.y - 14;
      if (mob) y = t.y + t.h / 2 < vh / 2 ? vh - ch - 12 : 12 + 0;                       // 手機：目標在上半就把卡放最下面，反之放最上面
      else if (below >= ch) y = t.y + t.h + 14; else if (above >= ch) y = t.y - ch - 14; else y = Math.max(12, Math.min(vh - ch - 12, t.y < vh / 2 ? vh - ch - 12 : 12));
      if (!mob) x = Math.max(12, Math.min(vw - cw - 12, t.x + t.w / 2 - cw / 2));
      if (mob && y < 70 && y === 12) y = 64;                                              // 手機頂列在最上面，卡片放上緣時要讓開
    }
    card.style.left = Math.round(x) + 'px'; card.style.top = Math.round(Math.max(8, y)) + 'px';
  }
  function show(i) {
    T.i = Math.max(0, Math.min(STEPS.length - 1, i)); const s = STEPS[T.i];
    $('trStep').textContent = `第 ${T.i + 1}／${STEPS.length} 步`; $('trTitle').textContent = s.title;
    $('trBody').innerHTML = s.body.split('\n').map(l => `<span>${l.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]))}</span>`).join('');
    $('trDots').innerHTML = STEPS.map((_, k) => `<i class="${k === T.i ? 'on' : k < T.i ? 'past' : ''}"></i>`).join('');
    $('trPrev').hidden = T.i === 0; $('trNext').textContent = s.last ? '開始使用' : '下一步'; $('trSkip').hidden = !!s.last;
    layout(); $('trNext').focus({ preventScroll: true });
  }
  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); finish('skip'); }
    else if (e.key === 'ArrowRight' || e.key === 'Enter') { if (e.target && e.target.id === 'trSkip') return; e.preventDefault(); e.stopPropagation(); $('trNext').click(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); e.stopPropagation(); if (T.i > 0) show(T.i - 1); }
    else if (e.key === 'Tab') { const f = [...ov.querySelectorAll('button:not([hidden])')]; if (!f.length) return; const a = document.activeElement, k = f.indexOf(a); e.preventDefault(); f[(k + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus(); }
  }
  $('trNext').onclick = () => { if (T.i >= STEPS.length - 1) finish('done'); else show(T.i + 1); };
  $('trPrev').onclick = () => show(T.i - 1);
  $('trSkip').onclick = () => finish('skip');
  document.addEventListener('keydown', onKey, true);
  // 目標（員工）會走動、視窗會改大小：每 100 毫秒重量一次
  let last = 0; const loop = t => { if (!T.on) return; if (t - last > 100) { last = t; layout(); } T.raf = requestAnimationFrame(loop); };
  T.on = true; T.show = show; T.finish = finish; T.layout = layout; W.tour = T;
  show(0); T.raf = requestAnimationFrame(loop);
  return T;
}

// ───────── 自動啟動與「?」重看 ─────────
function boot(w) {
  W = w;
  const qs = new URLSearchParams(location.search), q = qs.get('tour');
  const auto = q !== '0' && !lsGet(KEY) && qs.get('connect') !== '1' && (!navigator.webdriver || q === '1');
  // 「?」說明裡加一顆「重看新手引導」（ui.js 在建說明時已經把 #helpPop 準備好）
  const pop = $('helpPop');
  if (pop && !$('tourAgain')) {
    const b = document.createElement('button'); b.className = 'btn tr-again'; b.id = 'tourAgain'; b.type = 'button'; b.textContent = '重看新手引導';
    b.onclick = () => { if (W.ui && W.ui.closePops) W.ui.closePops(); else pop.hidden = true; startTour(W); };
    pop.append(b);
  }
  W.tourStart = () => startTour(W);
  if (auto) setTimeout(() => { if (!lsGet(KEY) && !$('trOv')) startTour(W); }, 900);
}
{ let n = 0; const t = setInterval(() => { const w = window.__world; if (w && w.ready && w.chars && w.ui) { clearInterval(t); try { boot(w); } catch (e) { console.error('新手引導載入失敗', e); } } else if (++n > 600) clearInterval(t); }, 150); }
