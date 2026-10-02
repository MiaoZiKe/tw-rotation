/* 分支預覽的開機腳本（DECISIONS #301，2026-10-03）。
 *
 * ★ 這支只會出現在 `preview/<名稱>/` 底下，正式站永遠不會載入它。
 *   部署時由 scripts/preview_inject.py 複製進每一份預覽，並插在 index.html 的 <head> 最前面
 *   （比主題那兩段讀 localStorage 的 inline script 還早），所以下面的換殼一定先生效。
 *
 * 做四件事：
 *   ① localStorage／sessionStorage 換成「加前綴的殼」：所有鍵實際存成 `twpv:<名稱>:<原鍵>`。
 *      預覽版的設定、自選、手繪線因此跟正式站（同一個網域 miaozike.github.io）完全分開，
 *      正式站的鍵預覽版讀不到也寫不到。不同預覽之間也互相分開（名稱不同、前綴就不同）。
 *   ② 資料一律讀正式站：fetch 到 `<預覽>/data/...` 時改寫成 `/tw-rotation/data/...`。
 *      資料（約 130MB）因此不必每份預覽各複製一份（Pages 上限 1GB）。
 *      logos.json 裡的相對路徑 `data/logos/x.png` 也一併改成絕對路徑，否則公司圖示會 404。
 *   ③ 會員 API 的「寫入」在預覽版一律擋下（自選上傳、刪帳號、後台設定、使用統計）：
 *      登入是同一個帳號，不擋的話預覽版的操作會直接改到正式站的雲端自選。讀取（登入、讀清單、權限）照常。
 *   ④ 不註冊 Service Worker（同網域的快取名稱都是 tw- 開頭，兩邊的 SW 會互刪對方的快取），
 *      並在頁面最上方掛一條醒目的橫幅，附連回正式站的連結。
 */
(function () {
  'use strict';
  var C = window.TW_PREVIEW || {};
  var NAME = String(C.name || 'preview');
  var PREFIX = 'twpv:' + NAME + ':';

  /* ---------------------------------------------------------------- ① 儲存空間加前綴 */
  function wrapStorage(real) {
    function keys() {
      var out = [];
      for (var i = 0; i < real.length; i++) {
        var k = real.key(i);
        if (k && k.indexOf(PREFIX) === 0) out.push(k.slice(PREFIX.length));
      }
      return out;
    }
    var api = {
      getItem: function (k) { return real.getItem(PREFIX + String(k)); },
      setItem: function (k, v) { real.setItem(PREFIX + String(k), String(v)); },
      removeItem: function (k) { real.removeItem(PREFIX + String(k)); },
      clear: function () { keys().forEach(function (k) { real.removeItem(PREFIX + k); }); },
      key: function (i) { var a = keys(); return (i >= 0 && i < a.length) ? a[i] : null; }
    };
    /* Proxy 是為了 `localStorage['tw.sse']`、`localStorage.foo = '1'` 這種屬性寫法也走前綴。*/
    return new Proxy(api, {
      get: function (t, p) {
        if (p === 'length') return keys().length;
        if (typeof p === 'symbol' || Object.prototype.hasOwnProperty.call(t, p)) return t[p];
        var v = real.getItem(PREFIX + p);
        return v === null ? undefined : v;
      },
      set: function (t, p, v) {
        if (typeof p === 'symbol' || Object.prototype.hasOwnProperty.call(t, p)) return true;
        real.setItem(PREFIX + p, String(v)); return true;
      },
      deleteProperty: function (t, p) { if (typeof p !== 'symbol') real.removeItem(PREFIX + p); return true; },
      has: function (t, p) { return p in t || p === 'length' || (typeof p !== 'symbol' && real.getItem(PREFIX + p) !== null); },
      ownKeys: function () { return keys(); },
      getOwnPropertyDescriptor: function (t, p) {
        if (typeof p === 'symbol') return undefined;
        var v = real.getItem(PREFIX + p);
        return v === null ? undefined : { value: v, writable: true, enumerable: true, configurable: true };
      }
    });
  }
  function shim(name) {
    var d = Object.getOwnPropertyDescriptor(window, name) ||
            (window.Window && Object.getOwnPropertyDescriptor(Window.prototype, name));
    if (!d || !d.get) return;
    var cache = null;
    try {
      Object.defineProperty(window, name, {
        configurable: true, enumerable: true,
        // 原本的 getter 在私密視窗會丟例外 —— 照樣丟，行為跟正式站一樣（各處都有 try/catch）
        get: function () { var real = d.get.call(window); return cache || (cache = wrapStorage(real)); }
      });
    } catch (e) { console.warn('[預覽] 無法隔離 ' + name + '，預覽版會讀寫到正式站的設定', e); }
  }
  shim('localStorage');
  shim('sessionStorage');

  /* ---------------------------------------------------------------- ② 資料讀正式站 */
  var BASE = new URL('./', location.href).pathname;                       // /tw-rotation/preview/<名稱>/
  var DATA = new URL(C.dataRoot || '../../data/', location.href).pathname; // /tw-rotation/data/
  var LOCAL_DATA = BASE + 'data/';
  function toProdData(u) {
    var x;
    try { x = new URL(u, location.href); } catch (e) { return null; }
    if (x.origin !== location.origin || x.pathname.indexOf(LOCAL_DATA) !== 0) return null;
    x.pathname = DATA + x.pathname.slice(LOCAL_DATA.length);
    return x.href;
  }

  /* ---------------------------------------------------------------- ③ 會員 API 寫入擋下 */
  var WRITES = ['/v1/lists/put', '/v1/delete', '/v1/beat', '/v1/admin/settings',
                '/v1/admin/perm/put', '/v1/admin/plans/put'];
  function isBlockedWrite(u) {
    try {
      var x = new URL(u, location.href);
      return x.origin !== location.origin && WRITES.indexOf(x.pathname) !== -1;
    } catch (e) { return false; }
  }

  var realFetch = window.fetch;
  if (realFetch) {
    window.fetch = function (input, init) {
      var url = (typeof input === 'string') ? input : (input && input.url) || String(input);
      var method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
      if (method === 'POST' && isBlockedWrite(url)) {
        console.info('[預覽] 擋下會員 API 寫入（預覽版不改正式站的雲端資料）：' + url);
        return Promise.resolve(new Response(JSON.stringify({ error: 'preview_readonly' }),
          { status: 403, headers: { 'content-type': 'application/json' } }));
      }
      var fixed = toProdData(url);
      if (!fixed) return realFetch.apply(this, arguments);
      var req = (typeof input === 'string' || input instanceof URL) ? fixed : new Request(fixed, input);
      var p = realFetch.call(this, req, init);
      if (/\/logos\.json(\?|$)/.test(fixed)) {
        p = p.then(function (r) {
          if (!r.ok) return r;
          return r.clone().json().then(function (m) {
            if (!m || typeof m !== 'object') return r;
            Object.keys(m).forEach(function (k) {
              if (typeof m[k] === 'string' && m[k].indexOf('data/') === 0) m[k] = DATA + m[k].slice(5);
            });
            return new Response(JSON.stringify(m), { status: r.status, headers: { 'content-type': 'application/json' } });
          }).catch(function () { return r; });
        });
      }
      return p;
    };
  }
  if (navigator.sendBeacon) {
    var realBeacon = navigator.sendBeacon.bind(navigator);
    navigator.sendBeacon = function (url, body) { return isBlockedWrite(url) ? true : realBeacon(url, body); };
  }

  /* ---------------------------------------------------------------- ④ 不註冊 SW ＋ 橫幅 */
  if (navigator.serviceWorker) {
    try {
      navigator.serviceWorker.register = function () { return Promise.reject(new Error('預覽版不註冊 Service Worker')); };
    } catch (e) { /* 略 */ }
  }
  function banner() {
    if (document.getElementById('twPreviewBanner')) return;
    var b = document.createElement('div');
    b.id = 'twPreviewBanner';
    b.setAttribute('role', 'status');
    b.style.cssText = 'position:sticky;top:0;z-index:2147483000;display:flex;flex-wrap:wrap;gap:4px 12px;' +
      'align-items:center;justify-content:center;padding:6px 16px;background:#ffd400;color:#111;' +
      'font:600 14px/1.4 system-ui,"Noto Sans TC",sans-serif;border-bottom:2px solid #111;text-align:center';
    var t = document.createElement('span');
    t.textContent = '預覽版：' + NAME + '（分支 ' + (C.sha || '?') + '），不是正式站';
    var a = document.createElement('a');
    a.href = C.prod || '../../';
    a.textContent = '回正式站 →';
    a.style.cssText = 'color:#111;text-decoration:underline';
    b.appendChild(t); b.appendChild(a);
    document.body.insertBefore(b, document.body.firstChild);
    document.documentElement.setAttribute('data-preview', NAME);
    if (document.title.indexOf('［預覽') !== 0) document.title = '［預覽 ' + NAME + '］' + document.title;
  }
  if (document.body) banner(); else document.addEventListener('DOMContentLoaded', banner);
})();
