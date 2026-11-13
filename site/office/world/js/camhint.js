// 鏡頭操作小提示（可收起，記在這台裝置）＋「回到角色」鈕（手動平移後暫停了跟隨才出現）。
// 位置：桌機放右上角；視窗太窄（工具列會換行）或手機時，放在工具列正下方，才不會跟工具列或其他面板重疊。
const KEY = 'aiOffice.camhint';
const $ = id => document.getElementById(id);
export function createCamHint(view) {
  let open; try { open = localStorage.getItem(KEY) !== '0'; } catch (e) { open = true; }
  const el = document.createElement('div'); el.className = 'cm-hint'; $('app').append(el);
  const coarse = () => matchMedia('(pointer:coarse)').matches;
  function render() {
    const txt = coarse() ? '單指旋轉・雙指平移縮放・雙點地面移動' : '左鍵拖曳旋轉・右鍵拖曳平移・滾輪縮放・雙擊地面移動';
    el.innerHTML = open ? `<span>${txt}</span><button class="cm-x" data-c="x" aria-label="收起鏡頭操作提示">×</button>` : `<button class="cm-q" data-c="q" aria-label="展開鏡頭操作提示">鏡頭操作</button>`;
    el.innerHTML += `<button class="cm-back" data-c="back" hidden>回到角色</button>`;
  }
  render();
  el.addEventListener('click', e => {
    const b = e.target.closest('[data-c]'); if (!b) return;
    if (b.dataset.c === 'back') { view.recenter(); return; }
    open = b.dataset.c === 'q'; try { localStorage.setItem(KEY, open ? '1' : '0'); } catch (x) { /* 沒有儲存空間就只在這次有效 */ } render(); place();
  });
  function place() {
    const bar = $('bar'), r = bar.getBoundingClientRect(), narrow = innerWidth < 1180 || coarse();
    if (narrow) { el.style.top = Math.round(r.bottom + 8) + 'px'; el.style.right = 'auto'; el.style.left = '12px'; } else { el.style.top = '12px'; el.style.right = '12px'; el.style.left = 'auto'; }
  }
  addEventListener('resize', place); place();
  let was = null;
  return { tick() { const d = !!(view.detached && view.char); if (d !== was) { was = d; const b = el.querySelector('.cm-back'); if (b) b.hidden = !d; place(); } } };
}
