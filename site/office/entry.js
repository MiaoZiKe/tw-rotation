// AI 辦公室入口頁的「建立新辦公室」：空狀態、我的辦公室清單、三步驟對話框（取名字 → 連接你的 Claude → 完成進辦公室）。
// 為什麼獨立成檔：入口頁的 <script type=module> 要載入 three 畫縮圖，畫不出來不能連累建立流程，所以邏輯放在這支一般腳本。
// 辦公室清單（2026-11-15 起讀伺服器）：登入後讀寫收件端的 /v1/offices（存在登入帳號底下，換裝置也找得到；非站長 3 間、每間 5 位 Agent 由伺服器擋）。
//   伺服器暫時連不上、或沒登入／沒設收件端時，退回這個瀏覽器的 localStorage「aiOffice.offices.v1」暫存（只有名稱與狀態，絕對不放接入碼），並在清單上方寫明。
//   登入後第一次連上伺服器時，把暫存的辦公室搬到伺服器（成功一間就從暫存移除一間，失敗的留著）。
// 專案：「進入」先列專案清單（名稱、最後活動、進行中工作階段數；資料來自收件端 /v1/office/main/projects），選了才進 world.html?office=<id>&project=<專案雜湊>。
//   還沒有任何專案（沒連接或沒收到消息）時，「進入」照舊直接進辦公室。
// 接入碼：這個頁面完全不碰。「連接」一律交給 world.html 的接入引導（live.js 的 openGuide，碼只放記憶體、視窗關掉就清）；
//   這裡只把人帶過去（world.html?office=<id>&connect=1，由 world/js/connect_link.js 自動打開引導），不複製一份引導程式，避免兩邊分岔。
(function () {
  'use strict';
  var LS = 'aiOffice.offices.v1', LIVE = 'aiOffice.live.v1', TOK = 'tw.acct.tok', USR = 'tw.acct.user', MAX = 3, NAME_MAX = 20;
  var AP = window.AIOProj || { label: function (n) { return n || '雲端工作階段'; }, ago: function () { return ''; } };
  // 伺服器狀態：mode＝'server'（辦公室清單讀寫伺服器）或 'local'（退回瀏覽器暫存）
  var SRV = { mode: 'local', offices: [], projects: [], limits: null, note: '', loaded: false };
  var $ = function (id) { return document.getElementById(id); };
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 讀寫不到就只在這次有效 */ } }
  function readList() { try { var a = JSON.parse(lsGet(LS) || '[]'); return Array.isArray(a) ? a.filter(function (o) { return o && o.id && typeof o.name === 'string'; }) : []; } catch (e) { return []; } }
  function writeList(a) { lsSet(LS, JSON.stringify(a)); }
  function listAll() { return SRV.mode === 'server' ? SRV.offices : readList(); }
  function apiBase() {
    var c = null; try { c = JSON.parse(lsGet(LIVE) || 'null'); } catch (e) { c = null; }
    if (c && c.url) return String(c.url).replace(/\/+$/, '');
    var api = window.TW_ACCOUNT && window.TW_ACCOUNT.api;
    return api && /\/\/tw-account\./.test(api) ? api.replace('//tw-account.', '//tw-ai-office-bridge.').replace(/\/+$/, '') : '';
  }
  // 呼叫收件端：永遠 resolve（{ ok, status, json }；連不上 status＝0），不丟例外，畫面才不會因為伺服器掛掉就壞掉
  function call(method, path, body) {
    var base = apiBase(), tok = lsGet(TOK);
    if (!base || !tok) return Promise.resolve({ ok: false, status: 0, json: {}, none: true });
    var ctl = window.AbortController ? new AbortController() : null, tm = setTimeout(function () { if (ctl) ctl.abort(); }, 8000);
    return fetch(base + path, { method: method, headers: { 'Content-Type': 'application/json', 'X-AIO-Session': tok }, body: body == null ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit', signal: ctl ? ctl.signal : undefined })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, status: r.status, json: j || {} }; }); })
      .catch(function () { return { ok: false, status: 0, json: {} }; })
      .then(function (x) { clearTimeout(tm); return x; });
  }
  function loadServer() {
    return Promise.all([call('GET', '/v1/offices'), call('GET', '/v1/office/me/projects')]).then(function (rs) {
      var o = rs[0], p = rs[1];
      SRV.loaded = true;
      SRV.projects = p.ok && Array.isArray(p.json.projects) ? p.json.projects : [];
      if (o.ok && Array.isArray(o.json.offices)) { SRV.mode = 'server'; SRV.offices = o.json.offices; SRV.limits = o.json.limits || null; SRV.note = ''; return migrate(); }
      SRV.mode = 'local'; SRV.offices = []; SRV.limits = null;
      SRV.note = o.none ? '' : o.status === 401 || o.status === 403 ? '登入已失效，先顯示這個瀏覽器的暫存辦公室。重新登入後會同步。' : '伺服器暫時連不上，先顯示這個瀏覽器的暫存辦公室，連上後會自動同步。';
    }).then(function () { render(); });
  }
  // 暫存的辦公室搬到伺服器：一間一間送，伺服器擋下（上限、重名）就留在暫存
  function migrate() {
    var loc = readList(); if (!loc.length) return Promise.resolve();
    var chain = Promise.resolve();
    loc.forEach(function (o) {
      chain = chain.then(function () {
        if (SRV.offices.some(function (x) { return x.name === o.name; })) { writeList(readList().filter(function (x) { return x.id !== o.id; })); return; }
        return call('POST', '/v1/offices', { name: o.name }).then(function (r) { if (r.ok && r.json.office) { SRV.offices.push(r.json.office); writeList(readList().filter(function (x) { return x.id !== o.id; })); } });
      });
    });
    return chain;
  }
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

  function maxNow() { var w = who(); return SRV.mode === 'server' && SRV.limits ? SRV.limits.max : (w.owner ? Infinity : MAX); }
  function isFull(n) { return n >= maxNow(); }
  function pjText(p) { return '最後活動 ' + AP.ago(p.last) + '・' + (p.active ? p.active + ' 個進行中' : '沒有進行中的工作階段'); }
  function pjHref(oid, hash) { return 'world.html?office=' + encodeURIComponent(oid || 'main') + '&project=' + encodeURIComponent(hash); }
  function projRow(p, oid, extra) {
    var li = el('li', 'of pj'); li.dataset.h = p.hash;
    var t = el('div', 'pjt'); t.appendChild(el('span', 'nm', AP.label(p.name))); t.appendChild(el('span', 'sub', pjText(p))); li.appendChild(t);
    var acts = el('div', 'acts'); var go = el('a', 'go2', '進入'); go.href = pjHref(oid, p.hash); go.setAttribute('aria-label', '進入專案 ' + AP.label(p.name)); acts.appendChild(go);
    if (extra) acts.appendChild(extra); li.appendChild(acts); return li;
  }

  function render() {
    var server = SRV.mode === 'server', list = server ? SRV.offices : syncConnected(readList()), w = who(), full = isFull(list.length);
    $('empty').hidden = list.length > 0 || SRV.projects.length > 0;
    $('mine').hidden = list.length === 0;
    $('heroNote').textContent = w.need && !w.tok ? '建立辦公室要先登入網站帳號；也可以先看示範。' : '';
    var sn = $('srvNote'); sn.textContent = SRV.note; sn.hidden = !SRV.note;
    // 專案清單：資料來自收件端，沒有任何專案（沒連接、沒收到消息）就不顯示這一區
    var ps = SRV.projects; $('projSec').hidden = ps.length === 0;
    var pl = $('projList'); pl.textContent = ''; ps.forEach(function (p) { pl.appendChild(projRow(p, 'main')); });
    var ul = $('mineList'); ul.textContent = '';
    list.forEach(function (o) {
      var li = el('li', 'of'); li.dataset.id = o.id;
      li.appendChild(el('span', 'nm', o.name));
      if (server) li.appendChild(el('span', 'tag' + (o.projects && o.projects.length ? ' ok' : ''), o.projects && o.projects.length ? o.projects.length + ' 個專案' : '全部專案'));
      else li.appendChild(el('span', 'tag' + (o.connected ? ' ok' : ''), o.connected ? '已連接' : '尚未連接'));
      var acts = el('div', 'acts');
      var go = el('a', 'go2', '進入'); go.href = 'world.html?office=' + encodeURIComponent(o.id); go.dataset.a = 'enter'; go.dataset.id = o.id; acts.appendChild(go);
      if (!server && !o.connected) { var cb = el('button', null, '繼續連接'); cb.type = 'button'; cb.dataset.a = 'resume'; cb.dataset.id = o.id; acts.appendChild(cb); }
      var rn = el('button', null, '改名'); rn.type = 'button'; rn.dataset.a = 'rename'; rn.dataset.id = o.id; acts.appendChild(rn);
      var rm = el('button', null, '移除'); rm.type = 'button'; rm.dataset.a = 'remove'; rm.dataset.id = o.id; acts.appendChild(rm);
      li.appendChild(acts); ul.appendChild(li);
    });
    var cap = maxNow(), nd = $('newDoor'); nd.setAttribute('aria-disabled', full ? 'true' : 'false');
    $('newSub').textContent = full ? '已達 ' + cap + ' 間上限，先移除一間才能再建立' : (cap === Infinity ? '取名字、連接你的 Claude，三步完成' : '取名字、連接你的 Claude，三步完成（已建 ' + list.length + '／' + cap + ' 間）');
    $('newGo').textContent = full ? '已達上限' : '開始';
  }

  // 專案清單對話框：「進入」辦公室之前先選專案。oid＝辦公室代號（'main'＝不指定辦公室，列全部專案）
  function viewPick(oid) {
    var o = oid && oid !== 'main' ? find(oid) : null, server = SRV.mode === 'server' && o && o.projects, bound = (server ? o.projects : []).slice(), more = false;
    open(o ? '「' + o.name + '」：選一個專案' : '選一個專案', function (b) {
      var box = el('div'); b.appendChild(box);
      function draw() {
        box.textContent = '';
        var all = SRV.projects, shown = bound.length && !more ? all.filter(function (p) { return bound.indexOf(p.hash) >= 0; }) : all;
        if (!all.length) {
          box.appendChild(el('p', 'note', '還沒有收到你的 Claude 的專案。連接之後，在 Claude 開一個工作階段，這裡就會列出專案。'));
          var r0 = el('div', 'row2'); r0.appendChild(link('big', '先進辦公室看看', 'world.html?office=' + encodeURIComponent(oid || 'main'))); box.appendChild(r0); return;
        }
        var ul = el('ul', 'plist');
        shown.forEach(function (p) {
          var bb = null;
          if (server) { bb = el('button', null, bound.indexOf(p.hash) >= 0 ? '取消綁定' : '綁定到這間'); bb.type = 'button'; bb.dataset.bind = p.hash; }
          ul.appendChild(projRow(p, oid, bb));
        });
        box.appendChild(ul);
        if (!shown.length) box.appendChild(el('p', 'note', '這間辦公室綁定的專案目前沒有消息。'));
        if (bound.length && !more && all.length > shown.length) { var mb = btn('ghost', '顯示其他專案（' + (all.length - shown.length) + '）', function () { more = true; draw(); }); box.appendChild(mb); }
        if (server) box.appendChild(el('p', 'note', '綁定之後，這間辦公室預設只列綁定的專案；一個專案可以綁在不同辦公室。'));
      }
      box.addEventListener('click', function (e) {
        var bb = e.target.closest('button[data-bind]'); if (!bb) return;
        var h = bb.dataset.bind, nb = bound.indexOf(h) >= 0 ? bound.filter(function (x) { return x !== h; }) : bound.concat([h]);
        bb.disabled = true;
        call('POST', '/v1/offices/' + encodeURIComponent(o.id), { projects: nb }).then(function (r) {
          if (r.ok && r.json.office) { bound = r.json.office.projects.slice(); SRV.offices = SRV.offices.map(function (x) { return x.id === o.id ? r.json.office : x; }); o = r.json.office; render(); }
          draw();
        });
      });
      draw();
    });
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
      b.appendChild(el('p', 'note', '一個帳號最多 ' + maxNow() + ' 間辦公室，每間最多 5 位 Agent。想再建立，請先移除「我的辦公室」裡用不到的一間。'));
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
        var name = inp.value.replace(/\s+/g, ' ').trim(), list = listAll();
        if (!name) { er.textContent = '請先輸入名稱'; inp.focus(); return; }
        if (list.some(function (o) { return o.name === name; })) { er.textContent = '已經有同名的辦公室了，換一個名稱'; inp.focus(); return; }
        if (isFull(list.length)) { dlg.hidden = true; viewFull(); return; }
        if (SRV.mode === 'server') {
          nx.disabled = true;
          call('POST', '/v1/offices', { name: name }).then(function (r) {
            nx.disabled = false;
            if (r.ok && r.json.office) { SRV.offices.push(r.json.office); render(); viewConnect(r.json.office.id); return; }
            if (r.status === 409 && r.json.error === 'office_limit') { dlg.hidden = true; load2(); viewFull(); return; }
            er.textContent = r.status === 409 ? '已經有同名的辦公室了，換一個名稱' : r.status === 0 ? '伺服器暫時連不上，稍後再試' : '建立失敗，稍後再試';
            inp.focus();
          });
          return;
        }
        var o = { id: 'o' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36), name: name, created: Date.now(), connected: false };
        var l2 = readList(); l2.push(o); writeList(l2); render(); viewConnect(o.id);
      });
    });
  }
  function load2() { return loadServer(); }
  function find(id) { return listAll().filter(function (o) { return o.id === id; })[0]; }
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
      go.addEventListener('click', function () { if (SRV.mode === 'server') return; var l = readList(); l.forEach(function (x) { if (x.id === id) x.connecting = true; }); writeList(l); });
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
    var w = who(), list = listAll();
    if (w.need && !w.tok) return viewLogin();
    if (isFull(list.length)) return viewFull();
    viewName();
  }
  $('heroBtn').addEventListener('click', start);
  $('newDoor').addEventListener('click', start);
  dlg.addEventListener('click', function (e) { if (e.target.dataset && e.target.dataset.x) close(); });
  addEventListener('keydown', function (e) { if (e.key === 'Escape' && !dlg.hidden) close(); });
  function viewRename(id) {
    var o = find(id); if (!o) return;
    open('改辦公室名稱', function (b) {
      var f = el('form'); f.noValidate = true; f.style.display = 'grid'; f.style.gap = '10px';
      var lb = el('label', null, '辦公室名稱'); lb.htmlFor = 'offName';
      var inp = el('input'); inp.type = 'text'; inp.id = 'offName'; inp.maxLength = NAME_MAX; inp.value = o.name; inp.autocomplete = 'off';
      var er = el('p', 'err'); er.id = 'offErr'; er.setAttribute('role', 'alert');
      var r = el('div', 'row2'); r.appendChild(btn('ghost', '取消', close)); var sv = el('button', 'big', '儲存'); sv.type = 'submit'; r.appendChild(sv);
      f.append(lb, inp, er, r); b.appendChild(f);
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var name = inp.value.replace(/\s+/g, ' ').trim();
        if (!name) { er.textContent = '請先輸入名稱'; inp.focus(); return; }
        if (listAll().some(function (x) { return x.id !== id && x.name === name; })) { er.textContent = '已經有同名的辦公室了，換一個名稱'; inp.focus(); return; }
        if (SRV.mode === 'server') {
          sv.disabled = true;
          call('POST', '/v1/offices/' + encodeURIComponent(id), { name: name }).then(function (r2) {
            sv.disabled = false;
            if (r2.ok && r2.json.office) { SRV.offices = SRV.offices.map(function (x) { return x.id === id ? r2.json.office : x; }); close(); return; }
            er.textContent = r2.status === 409 ? '已經有同名的辦公室了，換一個名稱' : '儲存失敗，稍後再試'; inp.focus();
          });
          return;
        }
        writeList(readList().map(function (x) { if (x.id === id) x.name = name; return x; })); close();
      });
    });
  }
  $('mineList').addEventListener('click', function (e) {
    var en = e.target.closest('a[data-a=enter]');
    // 有專案可選就先列專案清單；沒有專案（還沒連接）照舊直接進辦公室
    if (en) { if (SRV.projects.length) { e.preventDefault(); opener = en; viewPick(en.dataset.id); } return; }
    var b = e.target.closest('button'); if (!b) return;
    if (b.dataset.a === 'resume') { opener = b; viewConnect(b.dataset.id); }
    else if (b.dataset.a === 'rename') { opener = b; viewRename(b.dataset.id); }
    else if (b.dataset.a === 'remove') {
      if (b.dataset.sure) {
        var id = b.dataset.id;
        if (SRV.mode === 'server') { b.disabled = true; call('POST', '/v1/offices/' + encodeURIComponent(id) + '/delete', {}).then(function (r) { if (r.ok || r.status === 404) SRV.offices = SRV.offices.filter(function (o) { return o.id !== id; }); render(); }); return; }
        writeList(readList().filter(function (o) { return o.id !== id; })); render(); return;
      }
      b.dataset.sure = '1'; b.textContent = '確定移除？'; clearTimeout(rmTimer); rmTimer = setTimeout(function () { render(); }, 4000);
    }
  });
  $('projList').addEventListener('click', function () { /* 專案列的「進入」本身就是連結，不需要攔截 */ });
  window.__officeEntry = { list: listAll, local: readList, max: MAX, srv: SRV };
  render();
  loadServer().then(function () {
    // 辦公室頁左上角「←」回來（index.html?office=<id>#pick）：直接打開專案清單
    if (location.hash === '#pick') {
      var q = /[?&]office=([A-Za-z0-9_-]{1,40})/.exec(location.search); try { history.replaceState(null, '', location.pathname); } catch (e) { /* 略 */ }
      if (SRV.projects.length) viewPick(q ? q[1] : 'main');
    }
  });
  addEventListener('pageshow', function () { render(); });   // 從連接引導按上一頁回來時，狀態要重新對
})();
