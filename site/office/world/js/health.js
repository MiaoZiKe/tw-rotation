// 連線健康燈（2026-11-16 第二批第 3 項；Andy：「全做」）
//
// 頂列「即時」標章旁邊一顆燈，只在即時模式顯示：
//   綠＝連得上收件服務，而且 10 分鐘內收到過你的 Claude 的事件，或 Claude 端的指令收件匣 2 分鐘內來取過指令（待命在線）
//   黃＝連得上，但還沒收到任何回報／Claude 一段時間沒有動靜（不是壞掉，只是沒在做事）；或正在第一次連線
//   紅＝連不上收件服務（網路斷、逾時、伺服器錯誤）或接入碼失效 —— 明講「斷線」與幾秒後重連；CEO 頭上掛「失聯」圖示（toolanim.js），不假裝還在工作
// 重連：live.js 的讀取迴圈失敗時指數退避（間隔 ×2，最多 2 分鐘），這裡顯示倒數；按燈＝立刻重試；瀏覽器回到線上（online 事件）也立刻重試。
// 斷線與恢復各跳一則提示（同一次斷線只跳一次）。
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const ago = ms => (ms < 60000 ? Math.max(1, Math.round(ms / 1000)) + ' 秒' : ms < 3600e3 ? Math.round(ms / 60000) + ' 分' : Math.round(ms / 3600e3) + ' 小時');

export function createHealth(W, X = {}) {
  const ui = X.ui || {}, L = W.live;
  const H = { level: 'off', text: '', last: 'off', nDown: 0, nUp: 0, quietMs: 10 * 60e3, standbyMs: 120e3 };
  W.health = H;
  const gateOn = () => { try { return !W.gate || !W.gate.peek || W.gate.peek('office.liveviz').pass !== false; } catch (e) { return true; } };
  const css = document.createElement('style'); css.id = 'hlCss';
  css.textContent = `
.btn.aio-hl{gap:6px;font-size:13px;padding:0 10px}.btn.aio-hl[hidden]{display:none}
.btn.aio-hl i{width:10px;height:10px;border-radius:50%;flex:none;background:#b9aca2}
.btn.aio-hl.g i{background:#35b36b;box-shadow:0 0 0 3px rgba(53,179,107,.2)}
.btn.aio-hl.y i{background:#f2a93b;box-shadow:0 0 0 3px rgba(242,169,59,.22)}
.btn.aio-hl.r i{background:#d2452b;box-shadow:0 0 0 3px rgba(210,69,43,.22);animation:hlBlink 1.2s ease-in-out infinite}
.btn.aio-hl.r{color:#b8452a}
@keyframes hlBlink{50%{opacity:.35}}
@media (prefers-reduced-motion:reduce){.btn.aio-hl.r i{animation:none}}
@media (max-width:640px){#bar #aioHealth{order:3;padding:0 8px}.btn.aio-hl span{display:none}}`;
  document.head.append(css);
  const el = document.createElement('button'); el.id = 'aioHealth'; el.className = 'btn aio-hl'; el.hidden = true; el.type = 'button';
  el.innerHTML = '<i aria-hidden="true"></i><span id="aioHlTxt"></span>';
  const badge = $('aioBadge');
  if (badge && badge.parentNode) badge.after(el); else ($('bar') || document.body).append(el);
  el.onclick = () => { if (H.level === 'r' && L && L.poll) { ui.toast && ui.toast('正在重新連線…'); L.fails = Math.max(0, L.fails); L.poll(); } else if (ui.toast) ui.toast(H.text); };
  addEventListener('online', () => { if (L && L.mode === 'live' && H.level === 'r') L.poll(); });

  const ceos = () => { const a = []; const c = W.chars.get('ceo'); if (c) a.push(c); for (const x of (L && L.clones) || []) if (x.sid && x.ch) a.push(x.ch); return a; };
  function compute() {
    if (!L || L.mode !== 'live' || !gateOn()) return ['off', ''];
    const now = Date.now(), d = L.data;
    const retry = L.nextAt ? Math.max(0, Math.ceil((L.nextAt - now) / 1000)) : 0;
    if (L.status === 'auth') return ['r', '斷線：接入碼失效，請重新取得'];
    const stale = L.lastOk && now - L.lastOk > Math.max(45000, L.pollMs * 3) && !L.inflight && !L.paused && document.visibilityState !== 'hidden';
    if (L.status === 'error' || stale) return ['r', `斷線：連不上收件服務${L.msg ? '（' + L.msg + '）' : ''}，${retry ? retry + ' 秒後' : '正在'}自動重連`];
    if (L.status === 'connecting' || !d) return ['y', '連線中…'];
    if (L.status === 'setup') return ['y', '尚未設定'];
    const skew = (d.now || now) - (L.lastOk || now);                       // 收件服務的時鐘 − 這台的時鐘
    const sNow = now + skew, lastEv = d.last_event_at || 0, pull = d.inbox && d.inbox.last_pull;
    const standby = pull && sNow - pull < H.standbyMs;
    if (L.status === 'nodata') return [standby ? 'g' : 'y', standby ? '連線正常：Claude 待命在線，還沒有事件' : '已連線：還沒收到你的 Claude 的回報'];
    if (lastEv && sNow - lastEv < H.quietMs) return ['g', `連線正常：最後事件 ${ago(sNow - lastEv)}前`];
    if (standby) return ['g', '連線正常：Claude 待命在線'];
    return ['y', `已連線：Claude ${lastEv ? ago(sNow - lastEv) : '一段時間'}沒有動靜`];
  }
  function tick() {
    const [lv, text] = compute();
    if (lv !== H.level || text !== H.text) {
      H.level = lv; H.text = text;
      el.hidden = lv === 'off'; el.className = 'btn aio-hl ' + (lv === 'off' ? '' : lv);
      const t = $('aioHlTxt'); if (t) t.textContent = lv === 'g' ? '連線正常' : lv === 'y' ? (/連線中/.test(text) ? '連線中' : '已連線・沒有動靜') : lv === 'r' ? '斷線・重連中' : '';
      el.title = text; el.setAttribute('aria-label', '連線狀態：' + text);
    }
    // 斷線／恢復提示＋CEO 失聯圖示（只在狀態翻轉時做一次）
    if (lv === 'r' && H.last !== 'r') { H.nDown++; ui.toast && ui.toast(text.startsWith('斷線') ? text.replace(/，.*$/, '') + '，會自動重連' : text); W.toolanim && W.toolanim.lost(ceos(), true); }
    if (lv !== 'r' && lv !== 'off' && H.last === 'r') { H.nUp++; ui.toast && ui.toast('連線恢復了'); W.toolanim && W.toolanim.lost(ceos(), false); }
    if (lv === 'off' && H.last === 'r') W.toolanim && W.toolanim.lost(ceos(), false);
    H.last = lv;
  }
  H.tick = tick;
  setInterval(tick, 1000); tick();
  return H;
}
