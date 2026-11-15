// 入口頁「建立新辦公室」的接力：網址帶 ?connect=1 進來時，自動打開接入引導（live.js 的 openGuide），不用使用者再去找按鈕。
// 為什麼獨立一支：接入引導本體在 live.js（碼只放記憶體），這裡只負責「叫它打開」，不複製引導，避免兩邊分岔。
// 另外：?office=<id> 找得到入口頁存的辦公室名稱時，把分頁標題換成那個名稱（暫代：後端還沒有多辦公室，場景內容仍是同一份）。
// 接法：world.html 載入 world/js/main.js 之後加一行 <script type="module" src="world/js/connect_link.js"></script>。
const qs = new URLSearchParams(location.search), id = qs.get('office') || '';
if (id) { try { const o = (JSON.parse(localStorage.getItem('aiOffice.offices.v1') || '[]') || []).find(x => x && x.id === id); if (o && o.name) document.title = o.name + '・AI 辦公室'; } catch (e) { /* 略 */ } }
if (qs.get('connect') === '1') {
  let n = 0; const t = setInterval(() => {
    const L = window.__world && window.__world.live;
    if (L && L.openGuide) { clearInterval(t); try { history.replaceState(null, '', location.pathname + (id ? '?office=' + encodeURIComponent(id) : '')); } catch (e) { /* 略 */ } L.openGuide(); }
    else if (++n > 200) clearInterval(t);   // 等最多 ~30 秒；辦公室載入失敗就不打擾
  }, 150);
}
