// 第二批「經營層」四個新功能（藍圖、優先度表、壓力原因、純工作模式）共用的小工具（2026-11-16）。
// 為什麼獨立一支：這四支都是「掛上去」的新檔，不碰 main.js／ui.js／mind.js（別組同時在改），
// 它們需要同一套：範圍 id（跟 growth.js 一樣）、localStorage 讀寫（鍵一律 aiOffice.game. 開頭，雲端存檔 save.js 會一起帶走）、等辦公室準備好才啟動。
export const $ = id => document.getElementById(id);
export const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
export const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); return true; } catch (e) { return false; } };
export const jget = (k, d) => { try { const v = JSON.parse(lsGet(k) || 'null'); return v == null ? d : v; } catch (e) { return d; } };
// 範圍：專案 id／辦公室 id／示範（跟 growth.js 同一套規則，之後雲端存檔才對得起來）
export function scopeOf() {
  const qs = new URLSearchParams(location.search);
  return (/^[0-9a-f]{16}$/.test(qs.get('project') || '') ? qs.get('project') : null) || (/^[A-Za-z0-9_-]{1,40}$/.test(qs.get('office') || '') ? qs.get('office') : null) || 'demo';
}
export const GAME = 'aiOffice.game.';
// 等辦公室準備好（W.ready、有角色、有 ui）才呼叫 fn(W)；最多等 60 秒
export function whenWorld(fn, need = () => true) {
  let n = 0; const t = setInterval(() => {
    const W = window.__world;
    if (W && W.ready && W.chars && W.ui && W.state && need(W)) { clearInterval(t); try { fn(W); } catch (e) { console.error('第二批功能啟動失敗', e); } }
    else if (++n > 600) clearInterval(t);
  }, 100);
}
// 辦公室裡「同事」（不含 CEO、寵物、離職、外出）
export const members = W => [...W.chars.values()].filter(c => c && !c.spec.pet && !c.spec.isCeo && !c.jobless && !c.away);
export const nickOf = (W, id) => { const c = W.chars.get(id); return c ? c.spec.nick : id; };
