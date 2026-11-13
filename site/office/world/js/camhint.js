// 鏡頭操作小提示（可收起，記在這台裝置）＋「回到角色」鈕（手動平移後暫停了跟隨才出現）。
// 位置：桌機放右上角；視窗太窄（工具列會換行）或手機時，放在工具列正下方，才不會跟工具列或其他面板重疊。
const KEY = 'aiOffice.camhint';
const $ = id => document.getElementById(id);
export function createCamHint(view, cam) {
  let open; try { open = localStorage.getItem(KEY) !== '0'; } catch (e) { open = true; }
  const el = document.createElement('div'); el.className = 'cm-hint'; $('app').append(el);
  const coarse = () => matchMedia('(pointer:coarse)').matches;
  function render() {
    const rot = cam.mode === 'rotate', pv = document.body.classList.contains('pov-on'), txt = pv ? (coarse() ? '單指拖曳環顧・點「視角」回原視角' : '拖曳環顧・按 V 或 Esc 回原視角') : coarse() ? (rot ? '單指拖曳旋轉・雙指縮放旋轉・雙點地面前往' : '單指拖曳移動・雙指縮放旋轉・雙點地面前往') : (rot ? '拖曳旋轉・滾輪縮放・雙擊地面前往' : '拖曳移動・滾輪縮放・雙擊地面前往');
    const ctl = `<span class="cm-ctl"><span class="cm-lab">拖曳</span><span class="cm-seg" role="group" aria-label="拖曳的功能"><button data-c="mv" class="${rot ? '' : 'on'}" aria-pressed="${!rot}">移動</button><button data-c="ro" class="${rot ? 'on' : ''}" aria-pressed="${rot}">旋轉</button></span><button class="cm-rot" data-c="rl" aria-label="向左旋轉（點一下轉一格，按住持續轉）" title="向左旋轉：點一下轉 30 度，按住持續轉">↺</button><button class="cm-rot" data-c="rr" aria-label="向右旋轉（點一下轉一格，按住持續轉）" title="向右旋轉：點一下轉 30 度，按住持續轉">↻</button></span>`;
    el.innerHTML = (open ? `<span class="cm-t">${txt}</span>` : '') + ctl + (open ? `<button class="cm-x" data-c="x" aria-label="收起鏡頭操作提示">×</button>` : `<button class="cm-q" data-c="q" aria-label="展開鏡頭操作提示">?</button>`) + `<button class="cm-back" data-c="back" hidden>回到角色</button>`;
    const b = el.querySelector('.cm-back'); if (b) b.hidden = !(view.detached && view.char);
  }
  cam.listeners.push(() => { render(); place(); });
  render();
  // 旋轉鈕：點一下轉 30 度；按住超過 0.25 秒就持續旋轉，放開停止
  let holdT = 0, held = false;
  el.addEventListener('pointerdown', e => { const b = e.target.closest('.cm-rot'); if (!b) return; const dir = b.dataset.c === 'rl' ? 1 : -1; held = false; clearTimeout(holdT); holdT = setTimeout(() => { held = true; cam.spin = dir; }, 250); b.dataset.dir = dir; });
  const rotUp = e => { const b = e.target.closest && e.target.closest('.cm-rot'); clearTimeout(holdT); if (cam.spin) { cam.spin = 0; held = true; } else if (b && !held && e.type === 'pointerup') cam.step += (+b.dataset.dir || 1) * Math.PI / 6; };
  addEventListener('pointerup', e => { if (e.target.closest && e.target.closest('.cm-hint')) rotUp(e); else { clearTimeout(holdT); cam.spin = 0; } }); addEventListener('pointercancel', () => { clearTimeout(holdT); cam.spin = 0; });
  el.addEventListener('keydown', e => { const b = e.target.closest('.cm-rot'); if (b && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); cam.step += (b.dataset.c === 'rl' ? 1 : -1) * Math.PI / 6; } });
  el.addEventListener('click', e => {
    const b = e.target.closest('[data-c]'); if (!b) return;
    if (b.dataset.c === 'mv') { cam.setMode('move'); return; } if (b.dataset.c === 'ro') { cam.setMode('rotate'); return; } if (b.dataset.c === 'rl' || b.dataset.c === 'rr') return;
    if (b.dataset.c === 'back') { view.recenter(); return; }
    open = b.dataset.c === 'q'; try { localStorage.setItem(KEY, open ? '1' : '0'); } catch (x) { /* 沒有儲存空間就只在這次有效 */ } render(); place();
  });
  function place() {
    // 頂列右邊是鏡頭提示：頂列的項目變多（電力、等你核准…）快碰到它時，改放到頂列下方，兩者不重疊
    const bar = $('bar'), r = bar.getBoundingClientRect(); let last = 0; for (const k of bar.children) if (k.offsetParent) last = Math.max(last, k.getBoundingClientRect().right);
    el.style.display = ''; const hw = el.offsetWidth || 360, crowd = last > innerWidth - 12 - hw - 12, narrow = innerWidth < 1180 || coarse() || crowd;
    if (narrow) { el.style.top = Math.round(r.bottom + 8) + 'px'; el.style.right = 'auto'; el.style.left = '12px'; } else { el.style.top = '12px'; el.style.right = '12px'; el.style.left = 'auto'; }
    document.dispatchEvent(new Event('cmhint'));   // 通知時間小字（daytime.js）：提示的位置變了，它要跟著讓開
  }
  addEventListener('resize', place); place();
  let was = null, sig = ''; setInterval(() => { const g = [...$('bar').children].map(k => k.offsetWidth).join(','); if (g !== sig) { sig = g; place(); } }, 400);   // 頂列項目變多變少時重新擺放
  let wasPov = false;
  return { tick() { const pv = document.body.classList.contains('pov-on'); if (pv !== wasPov) { wasPov = pv; render(); place(); }
    const d = !!(view.detached && view.char); if (d !== was) { was = d; const b = el.querySelector('.cm-back'); if (b) b.hidden = !d; el.classList.toggle('has-back', d); place(); } } };
}
