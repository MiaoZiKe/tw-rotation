// 空狀態與第一次使用（detail_spec E 節）：網址加 ?empty=1..4 預覽；沒有這個參數時完全不啟用，辦公室照常。
//   1 還沒接入：空辦公室（燈亮、沒人、CEO 桌上一個「待接入」牌子），中央卡片放縮小的流程圖
//   2 接入了、還沒有專案回報：空辦公室＋大門口一位帶紙箱的迎賓員（只是氣氛，不是真的 Agent），按「測試連線」真的等事件
//   3 有專案、還沒建辦公室：專案卡片（專案名、最後一次消息、事件數）＋「創立辦公室」
//   4 辦公室剛建立：只有 CEO 一人，座位上貼著半透明的名牌虛影（部門規劃，不是真人）；派出子 Agent 後同事才一位一位出現
// 規則：一頁只放一句話、一個主要按鈕；說明收進「?」；不寫「沒有資訊」，只寫下一步；不出現任何價格或方案字樣。
import { textPlane, THREE } from './kit.js';

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const STEPS = ['登入', '取得接入碼', '安裝', '驗證成功', '建立辦公室'];

export function createEmpty(W, X) {
  const { ui, state: S } = X, mode0 = +(new URLSearchParams(location.search).get('empty') || 0), E = { mode: 0, ghosts: [] };
  if (!(mode0 >= 1 && mode0 <= 4)) { E.set = () => { }; E.frame = () => { }; return E; }
  const D = W.director, C = id => W.chars.get(id), members = () => [...W.chars.values()].filter(c => !c.spec.isCeo);
  D.ambient = false;
  const card = document.createElement('section'); card.className = 'em-card'; card.id = 'emptyCard'; card.hidden = true; $('app').append(card);
  const banner = document.createElement('div'); banner.className = 'em-banner'; banner.id = 'emptyBanner'; banner.hidden = true; $('app').append(banner);
  let sign = null, greeter = null, openSteps = false, noteOpen = false, autoMake = false, testT = 0, testMsg = '', off = null;

  const hide = c => { c.away = true; c.busy = true; c.atDesk = false; c.setVisible(false); };
  const show = (c, instant = true) => { const s = W.spots.find(q => q.name === 'seat:' + c.spec.id); c.away = false; c.busy = false; c.setVisible(true); if (s && s.seat) { s.taken = c.spec.id; c.spot = s; if (instant) c.sitAt(s.seat, { instant: true }); c.atDesk = true; c.setAction('type'); c.workAt = W.time + 4; } };
  E.reveal = id => { const c = C(id); if (c && c.away) { show(c); ghostsRefresh(); return c; } return null; };

  function deskSign(on) {
    if (on && !sign) { sign = textPlane('待接入', 0.92, 0.34, { pw: 256, bg: '#fff3d6', border: '#ffb86b', borderW: 10, px: 70, radius: 30 }); sign.position.set(4, 0.93, 6.05); sign.rotation.x = -0.5; W.scene.add(sign); }
    if (sign) sign.visible = on;
  }
  function greeterOn(on) {
    if (on && !greeter && W.addExtra) { greeter = W.addExtra({ id: 'greeter', nick: '迎賓員', zh: '帶紙箱的迎賓員', species: 'bird', pal: 2, acc: ['bow'], accColor: '#ff9db6', pet: true, scale: 0.9 }); greeter.standAt(21.7, 28.3, 0); greeter.setAction('box'); }
    if (greeter) greeter.setVisible(on);
  }
  // 名牌虛影：DOM 元素貼在座位上方，半透明；只做 CEO 附近的座位，不洗版
  const labels = $('labels');
  function ghostsRefresh() {
    E.ghosts.forEach(g => g.el.remove()); E.ghosts = [];
    if (E.mode !== 4) return; const ceo = W.spots.find(s => s.name === 'seat:ceo');
    for (const s of W.spots) {
      if (!s.name.startsWith('seat:') || s.name === 'seat:ceo' || !s.seat) continue; const id = s.name.slice(5), c = C(id); if (!c || !c.away) continue;
      if (Math.hypot(s.x - ceo.x, s.z - ceo.z) > 15) continue;
      const el = document.createElement('div'); el.className = 'ghost'; el.textContent = c.spec.zh || id; labels.append(el); E.ghosts.push({ el, s });
    }
  }
  const pv = new THREE.Vector3();
  E.frame = () => {
    if (E.mode !== 4) return; const w = $('cv').clientWidth, h = $('cv').clientHeight;
    for (const g of E.ghosts) { pv.set(g.s.seat.x, 1.0, g.s.seat.z); const d = pv.distanceTo(W.camera.position); pv.project(W.camera); const on = pv.z < 1 && Math.abs(pv.x) < 1 && Math.abs(pv.y) < 1 && d < 40; g.el.style.display = on ? '' : 'none'; if (on) g.el.style.transform = `translate(${Math.round((pv.x + 1) / 2 * w)}px,${Math.round((1 - pv.y) / 2 * h)}px) translate(-50%,-50%)`; }
  };

  const flow = () => `<ol class="em-flow" aria-label="接入流程">${STEPS.map((t, i) => `<li><i>${i + 1}</i><span>${t}</span></li>`).join('')}</ol>`;
  const qBtn = txt => `<button class="q em-q" id="emQ" aria-label="這是什麼" aria-expanded="${noteOpen}">?</button><p class="em-note" ${noteOpen ? '' : 'hidden'}>${txt}</p>`;
  function render() {
    const m = E.mode; card.hidden = m === 4 || !m; banner.hidden = m !== 4;
    if (m === 1) card.innerHTML = `<p class="em-t">還沒有同事上班。接好 Claude，他們就會出現</p>${flow()}${openSteps ? `<ol class="em-steps"><li>用 Google 登入辦公室網站</li><li>取得一組接入碼</li><li>在你的 Claude 貼上兩段指令</li><li>在 Claude 隨便說一句話，等網站收到第一筆消息</li><li>把發現的專案變成辦公室</li></ol>` : ''}<div class="em-acts"><button class="btn on" id="emGo">${openSteps ? '收起步驟' : '開始接入'}</button></div>${qBtn('接入完成後，在 Claude 隨便派一個工作，回來就看得到同事動起來。')}`;
    else if (m === 2) card.innerHTML = `<p class="em-t">接好了，等第一筆消息。在 Claude 隨便開一個工作</p>${testMsg ? `<p class="em-st" role="status">${esc(testMsg)}</p>` : ''}<div class="em-acts"><button class="btn on" id="emTest">測試連線</button></div>${qBtn('按下後最多等 30 秒，收到你的 Claude 送來的第一筆消息才會顯示收到；沒收到就是沒收到，不會假裝成功。')}`;
    else if (m === 3) card.innerHTML = `<small class="em-cnt">辦公室 0／1</small><p class="em-t">發現新專案：<b>示範專案</b></p><dl class="em-proj"><dt>最後一次消息</dt><dd>11-13 10:20</dd><dt>事件數</dt><dd>128</dd></dl><label class="em-sw"><input type="checkbox" id="emAuto" ${autoMake ? 'checked' : ''}><span>自動建立新專案的辦公室</span></label><div class="em-acts"><button class="btn on" id="emMake">創立辦公室</button></div>${qBtn('創立後會先只有 CEO，派出子 Agent 之後同事才會一位一位報到。勾選「自動建立」之後，新專案出現就會直接成立辦公室。')}`;
    else if (m === 4) banner.innerHTML = `<span>辦公室成立了，目前只有 CEO</span><button class="q em-q" id="emQ" aria-label="這是什麼" aria-expanded="${noteOpen}">?</button><p class="em-note" ${noteOpen ? '' : 'hidden'}>派出子 Agent 後，同事會陸續報到。座位上半透明的名牌是部門規劃，不是真人。</p>`;
  }
  E.set = m => {
    E.mode = m; noteOpen = false; openSteps = false; off && off(); off = null;
    const ceo = C('ceo');
    for (const c of members()) hide(c); for (const p of W.pets || []) p.setVisible(false);
    if (m === 4) { show(ceo, false); for (const p of W.pets || []) if (p.spec.owner === 'ceo') p.setVisible(true); } else hide(ceo);
    deskSign(m === 1 || m === 2); greeterOn(m === 2); ghostsRefresh(); render(); document.body.dataset.empty = String(m);
    if (m === 4) off = S.on(e => { if (e.name === 'SubagentStart') { const c = E.reveal(e.agent_type) || members().find(q => q.away); if (c) { e.agent_type = c.spec.id; E.reveal(c.spec.id); } } });   // 同事陸續報到（先露面，再由派工演出接手）
  };
  card.addEventListener('click', e => {
    if (e.target.closest('#emQ')) { noteOpen = !noteOpen; render(); return; }
    if (e.target.closest('#emGo')) { openSteps = !openSteps; render(); return; }
    if (e.target.closest('#emMake')) { E.set(4); ui.toast('辦公室成立了'); return; }
    if (e.target.closest('#emTest')) {
      testMsg = '正在等第一筆消息…（最多 30 秒）'; render(); const t0 = S.count; clearTimeout(testT);
      const stop = S.on(() => { if (S.count > t0) { stop(); clearTimeout(testT); testMsg = '收到了！發現新專案'; E.set(3); } });
      testT = setTimeout(() => { stop(); testMsg = '沒有收到消息。請確認你的 Claude 已經開了一個工作，再按一次測試連線'; if (E.mode === 2) render(); }, 30000);
    }
  });
  card.addEventListener('change', e => { if (e.target.id === 'emAuto') autoMake = e.target.checked; });
  banner.addEventListener('click', e => { if (e.target.closest('#emQ')) { noteOpen = !noteOpen; render(); } });
  E.set(mode0);
  return E;
}
