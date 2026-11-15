// AI 辦公室入口頁的「建立新辦公室」：空狀態、我的辦公室清單、三步驟對話框（取名字 → 連接你的 Claude → 完成進辦公室）。
// 為什麼獨立成檔：入口頁的 <script type=module> 要載入 three 畫縮圖，畫不出來不能連累建立流程，所以邏輯放在這支一般腳本。
// 【暫代（後端還沒有多辦公室）】辦公室清單目前只存在這個瀏覽器的 localStorage「aiOffice.offices.v1」（只有名稱與狀態，絕對不放接入碼）。
//   後端要補：① 以登入帳號為主鍵的「辦公室」清單（建立／刪除／改名）與每間 5 位 Agent 的座位數；② 每間辦公室各自的接入碼（收件端 /v1/claim 帶辦公室 id，
//   現在固定 'main'）；③ 非站長 3 間的上限改由伺服器擋（前端這裡的擋下只是介面，清 localStorage 就能繞過）。
// 接入碼：這個頁面完全不碰。「連接」一律交給 world.html 的接入引導（live.js 的 openGuide，碼只放記憶體、視窗關掉就清）；
//   這裡只把人帶過去（world.html?office=<id>&connect=1，由 world/js/connect_link.js 自動打開引導），不複製一份引導程式，避免兩邊分岔。
(function () {
  'use strict';
  var LS = 'aiOffice.offices.v1', LIVE = 'aiOffice.live.v1', TOK = 'tw.acct.tok', USR = 'tw.acct.user', MAX = 3, NAME_MAX = 20;
  var $ = function (id) { return document.getElementById(id); };
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 讀寫不到就只在這次有效 */ } }
  function readList() { try { var a = JSON.parse(lsGet(LS) || '[]'); return Array.isArray(a) ? a.filter(function (o) { return o && o.id && typeof o.name === 'string'; }) : []; } catch (e) { return []; } }
  function writeList(a) { lsSet(LS, JSON.stringify(a)); }
  function who() {
    var u = null; try { u = JSON.parse(lsGet(USR) || 'null'); } catch (e) { u = null; }
    // 會員系統沒開（repo 預設、本機預覽）＝不需要登入，照舊全放行；有開才要登入權杖
    var need = !!(window.TW_ACCOUNT && window.TW_ACCOUNT.api);
    return { need: need, tok: !!lsGet(TOK), owner: !!(u && (u.owner || u.admin)) };
  }
  // 從接入引導回來：引導成功後 live.js 會把 login 記成 true（舊的設定沒有 per-office，這是暫代）
  function syncConnected(list) {
    var live = null; try { live = JSON.parse(lsGet(LIVE) || 'null'); } catch (e) { live = null; }
    var changed = false;
    list.forEach(function (o) { if (o.connecting && live && live.login) { o.connected = true; o.connecting = false; changed = true; } });
    if (changed) writeList(list);
    return list;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }

  var dlg = $('dlg'), dlgT = $('dlgT'), dlgBody = $('dlgBody'), opener = null, rmTimer = 0;

  function render() {
    var list = syncConnected(readList()), w = who(), full = !w.owner && list.length >= MAX;
    $('empty').hidden = list.length > 0;
    $('mine').hidden = list.length === 0;
    $('heroNote').textContent = w.need && !w.tok ? '建立辦公室要先登入網站帳號；也可以先看示範。' : '';
    var ul = $('mineList'); ul.textContent = '';
    list.forEach(function (o) {
      var li = el('li', 'of'); li.dataset.id = o.id;
      li.appendChild(el('span', 'nm', o.name));
      li.appendChild(el('span', 'tag' + (o.connected ? ' ok' : ''), o.connected ? '已連接' : '尚未連接'));
      var acts = el('div', 'acts');
      var go = el('a', 'go2', '進入'); go.href = 'world.html?office=' + encodeURIComponent(o.id); acts.appendChild(go);
      if (!o.connected) { var cb = el('button', null, '繼續連接'); cb.type = 'button'; cb.dataset.a = 'resume'; cb.dataset.id = o.id; acts.appendChild(cb); }
      var rm = el('button', null, '移除'); rm.type = 'button'; rm.dataset.a = 'remove'; rm.dataset.id = o.id; acts.appendChild(rm);
      li.appendChild(acts); ul.appendChild(li);
    });
    var nd = $('newDoor'); nd.setAttribute('aria-disabled', full ? 'true' : 'false');
    $('newSub').textContent = full ? '已達 ' + MAX + ' 間上限，先移除一間才能再建立' : (w.owner ? '取名字、連接你的 Claude，三步完成' : '取名字、連接你的 Claude，三步完成（已建 ' + list.length + '／' + MAX + ' 間）');
    $('newGo').textContent = full ? '已達上限' : '開始';
  }

  function open(title, mk) {
    opener = document.activeElement; dlgT.textContent = title; dlgBody.textContent = ''; mk(dlgBody); dlg.hidden = false;
    var f = dlgBody.querySelector('input,.big,button,a'); if (f) f.focus({ preventScroll: true });
  }
  function close() { dlg.hidden = true; dlgBody.textContent = ''; if (opener && opener.focus && document.contains(opener)) { try { opener.focus({ preventScroll: true }); } catch (e) { /* 略 */ } } render(); }
  function dots(n) { var d = el('div', 'dots'); d.setAttribute('aria-label', '步驟 ' + n + '／3'); for (var i = 1; i <= 3; i++) d.appendChild(el('i', i <= n ? 'on' : '')); d.appendChild(el('span', null, '步驟 ' + n + '／3')); return d; }
  function link(cls, text, href) { var a = el('a', cls, text); a.href = href; return a; }
  function btn(cls, text, fn) { var b = el('button', cls, text); b.type = 'button'; b.addEventListener('click', fn); return b; }

  function viewLogin() {
    open('先登入再建立辦公室', function (b) {
      b.appendChild(el('p', 'note', '辦公室會記在你的網站帳號底下，換裝置登入也找得到。請先到網站首頁登入，再回到這裡。'));
      var r = el('div', 'row2'); r.appendChild(btn('ghost', '先看示範', function () { location.href = 'world.html'; })); r.appendChild(link('big', '到網站首頁登入', '../index.html')); b.appendChild(r);
    });
  }
  function viewFull() {
    open('已達辦公室上限', function (b) {
      b.appendChild(el('p', 'note', '一個帳號最多 ' + MAX + ' 間辦公室，每間最多 5 位 Agent。想再建立，請先移除「我的辦公室」裡用不到的一間。'));
      var r = el('div', 'row2'); r.appendChild(btn('big', '知道了', close)); b.appendChild(r);
    });
  }
  function viewName() {
    open('幫辦公室取個名字', function (b) {
      b.appendChild(dots(1));
      var f = el('form'); f.noValidate = true; f.style.display = 'grid'; f.style.gap = '10px';
      var lb = el('label', null, '辦公室名稱'); lb.htmlFor = 'offName';
      var inp = el('input'); inp.type = 'text'; inp.id = 'offName'; inp.maxLength = NAME_MAX; inp.placeholder = '例如：我的新專案'; inp.autocomplete = 'off';
      var er = el('p', 'err'); er.id = 'offErr'; er.setAttribute('role', 'alert');
      var r = el('div', 'row2'); var nx = el('button', 'big', '下一步'); nx.type = 'submit'; r.appendChild(nx);
      f.append(lb, inp, el('p', 'note', '通常用專案名稱就好，之後可以再改。'), er, r); b.appendChild(f);
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var name = inp.value.replace(/\s+/g, ' ').trim(), list = readList(), w = who();
        if (!name) { er.textContent = '請先輸入名稱'; inp.focus(); return; }
        if (list.some(function (o) { return o.name === name; })) { er.textContent = '已經有同名的辦公室了，換一個名稱'; inp.focus(); return; }
        if (!w.owner && list.length >= MAX) { dlg.hidden = true; viewFull(); return; }
        var o = { id: 'o' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36), name: name, created: Date.now(), connected: false };
        list.push(o); writeList(list); render(); viewConnect(o.id);
      });
    });
  }
  function find(id) { return readList().filter(function (o) { return o.id === id; })[0]; }
  function viewConnect(id) {
    var o = find(id); if (!o) return;
    open('連接你的 Claude', function (b) {
      b.appendChild(dots(2));
      b.appendChild(el('p', 'note', '接好之後，「' + o.name + '」顯示的是你自己的 Claude 真正在做的事。'));
      var ol = el('ol', 'how');
      ['複製一段提示詞，貼到你的 Claude 聊天室', 'Claude 跳出表單卡片時，貼上接入碼並按儲存', '等畫面出現「已接上」，就完成了'].forEach(function (t, i) { var li = el('li'); li.appendChild(el('span', 'n', String(i + 1))); li.appendChild(el('span', null, t)); ol.appendChild(li); });
      b.appendChild(ol);
      b.appendChild(el('p', 'note', '接入碼只會在連接視窗開著的時候出現，不會存在這個瀏覽器。'));
      var r = el('div', 'row2');
      r.appendChild(btn('ghost', '先跳過', function () { viewDone(id); }));
      var go = link('big', '開始連接', 'world.html?office=' + encodeURIComponent(id) + '&connect=1');
      go.addEventListener('click', function () { var l = readList(); l.forEach(function (x) { if (x.id === id) x.connecting = true; }); writeList(l); });
      r.appendChild(go); b.appendChild(r);
    });
  }
  function viewDone(id) {
    var o = find(id); if (!o) return;
    open('辦公室建好了', function (b) {
      b.appendChild(dots(3));
      b.appendChild(el('p', 'note', '「' + o.name + '」已經在「我的辦公室」裡。' + (o.connected ? '你的 Claude 已接上。' : '還沒連接你的 Claude，進去先看到示範內容；隨時可以按「繼續連接」。')));
      var r = el('div', 'row2'); r.appendChild(btn('ghost', '回入口', close)); r.appendChild(link('big', '進辦公室', 'world.html?office=' + encodeURIComponent(id))); b.appendChild(r);
    });
  }

  function start() {
    var w = who(), list = readList();
    if (w.need && !w.tok) return viewLogin();
    if (!w.owner && list.length >= MAX) return viewFull();
    viewName();
  }
  $('heroBtn').addEventListener('click', start);
  $('newDoor').addEventListener('click', start);
  dlg.addEventListener('click', function (e) { if (e.target.dataset && e.target.dataset.x) close(); });
  addEventListener('keydown', function (e) { if (e.key === 'Escape' && !dlg.hidden) close(); });
  $('mineList').addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    if (b.dataset.a === 'resume') { opener = b; viewConnect(b.dataset.id); }
    else if (b.dataset.a === 'remove') {
      if (b.dataset.sure) { writeList(readList().filter(function (o) { return o.id !== b.dataset.id; })); render(); return; }
      b.dataset.sure = '1'; b.textContent = '確定移除？'; clearTimeout(rmTimer); rmTimer = setTimeout(function () { render(); }, 4000);
    }
  });
  window.__officeEntry = { list: readList, max: MAX };
  render();
  addEventListener('pageshow', function () { render(); });   // 從連接引導按上一頁回來時，狀態要重新對
})();
