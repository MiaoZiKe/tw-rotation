/* Service Worker —— 台股資金輪動儀表板（PWA 第一步）
 * 新增於 2026-09-24（台北）。設計原則只有一條：**寧可不快取，也不准給他看到昨天的數字。**
 *
 * ┌── 為什麼要有這支 ──────────────────────────────────────────────┐
 * │ ① PWA 的三條路（PWA／WebView 包裝／原生）共用同一個底：manifest ＋ SW。 │
 * │   連 Capacitor 包裝也是包這個網站，所以這支做好，三條路都受惠。          │
 * │ ② 沒有 SW 就沒有離線，iOS 也拿不到 Web Push（iOS 16.4+ 的 Web Push    │
 * │   只在「加到主畫面」的 PWA 裡才有，而那需要 manifest ＋ SW）。          │
 * └──────────────────────────────────────────────────────────────┘
 *
 * ★★ 最重要的一條規則：`data/**` 與任何 .json 一律不進快取。
 *    那是每天盤後重算的資料。快取住 ＝ 他打開 App 看到的是昨天的數字，
 *    **這比沒有 PWA 還糟**（沒有 PWA 至少每次都是新的）。
 *    程式上的做法是：符合這個條件就**直接 return、不呼叫 respondWith**，
 *    讓瀏覽器照原本的方式走，這支 SW 連碰都不碰它。
 *
 * ★ 版本化與「新版真的換掉舊的」是怎麼做到的：
 *    index.html 註冊的是 `sw.js?v=<版號>`，版號取自 <meta name="tw:build">，
 *    而那個 meta 每次部署都由 scripts/stamp_assets.py 換成新值。
 *    所以 **每次部署 ＝ 一個新的 SW 腳本網址 ＝ 一個新的 SHELL 快取名稱**，
 *    activate 時把不在白名單裡的快取全部刪掉 —— 舊版自動消失，不需要有人記得改常數。
 *    ⚠ 這條會成立的前提是「導覽一律網路優先」（見下面 ②）：
 *    如果 index.html 是從快取拿的，版號永遠是舊的，就會鎖死在舊版再也更新不了。
 *
 * ★ vendor/ 另外放一個不跟著版號跑的快取：
 *    ECharts＋Lightweight Charts 約 1.2MB，而且 stamp_assets.py 刻意不給 vendor 加版本戳
 *    （它們幾乎不會變）。如果跟著 SHELL 一起每天換名字，等於每天叫他重抓 1.2MB。
 *    **升級 vendor 的函式庫時，把 VENDOR_CACHE 的尾碼 v1 加一**，否則使用者會停在舊版。
 */

'use strict';

// 版號：由註冊時的 ?v= 帶進來（見 index.html 的註冊片段）。本機直接開檔沒有就當 dev。
const BUILD = new URL(self.location.href).searchParams.get('v') || 'dev';
const SHELL_CACHE = 'tw-shell-' + BUILD;
const VENDOR_CACHE = 'tw-vendor-v1';   // ← 換 vendor 函式庫時把 v1 加一
const KEEP = [SHELL_CACHE, VENDOR_CACHE];

// SW 所在目錄（GitHub Pages 上是 /tw-rotation/，本機預覽是 /）。
const SCOPE_PATH = new URL('./', self.location.href).pathname;

// 安裝時只預先抓「小而關鍵」的殼：index.html ＋ manifest ＋ 圖示（合計約 45KB）。
// **刻意不預抓那 40 支自家 JS（約 2.7MB）與 vendor（1.2MB）** ——
// 安裝時就灌 4MB 在手機網路上是不禮貌的，而且那些檔案第一次用到時自然會被快取起來。
const PRECACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL_CACHE);
    // cache:'reload' ＝ 繞過 HTTP 快取。不加的話可能把「瀏覽器手上的舊 index.html」存進來。
    await Promise.all(PRECACHE.map(async (url) => {
      try { await cache.add(new Request(url, { cache: 'reload' })); }
      catch (err) { /* 單一檔案失敗不該讓整個安裝失敗（例如離線時重裝） */ }
    }));
    // 立刻接手：導覽是網路優先，所以頁面拿到的 HTML 永遠是新的，接手不會讓他卡在舊版。
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.map((n) => {
      // 只刪自己的（tw- 開頭），不要誤殺別人放在同一個 origin 的快取
      if (n.startsWith('tw-') && KEEP.indexOf(n) === -1) return caches.delete(n);
      return Promise.resolve(false);
    }));
    await self.clients.claim();
  })());
});

// 留一個手動催更新的門（之後若要在設定面板加「立即更新」鈕就用得上）
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

/** 這個網址是不是「每天會變的資料」？是的話這支 SW 完全不碰。 */
function isLiveData(url) {
  const p = url.pathname;
  const rel = p.startsWith(SCOPE_PATH) ? p.slice(SCOPE_PATH.length) : p;
  if (rel === 'data' || rel.indexOf('data/') === 0) return true;  // site/data/** —— 每日重算
  if (p.indexOf('/data/') !== -1) return true;                    // 保險：換了掛載路徑也擋得住
  if (p.toLowerCase().endsWith('.json')) return true;             // 任何 JSON 一律視為資料
  return false;
}

function isVendor(url) {
  const p = url.pathname;
  const rel = p.startsWith(SCOPE_PATH) ? p.slice(SCOPE_PATH.length) : p;
  return rel.indexOf('vendor/') === 0;
}

function isNavigation(request, url) {
  if (request.mode === 'navigate') return true;
  const p = url.pathname;
  const rel = p.startsWith(SCOPE_PATH) ? p.slice(SCOPE_PATH.length) : p;
  return rel === '' || rel === 'index.html';
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;                    // POST 之類完全不管

  let url;
  try { url = new URL(req.url); } catch (e) { return; }

  // 跨網域一律不碰：即時報價走的是 Cloudflare Worker 代理與 mis.twse，
  // 那些每分鐘就過期，而且快取 opaque response 只會浪費配額。
  if (url.origin !== self.location.origin) return;

  // ① 每天會變的資料 —— 這支 SW 連碰都不碰（最重要的一條）
  if (isLiveData(url)) return;

  // ② 導覽／index.html —— **網路優先**。
  //    這條同時是「版本能不能換掉」的關鍵：HTML 是新的，裡面的版號才是新的。
  if (isNavigation(req, url)) { event.respondWith(networkFirst(req)); return; }

  // ③ vendor 函式庫 —— 快取優先，放在不跟版號跑的快取裡
  if (isVendor(url)) { event.respondWith(cacheFirst(req, VENDOR_CACHE)); return; }

  // ④ 其餘 app shell（自家 JS／CSS／圖示／字型）—— 快取優先。
  //    這些的網址都被 stamp_assets.py 加過 ?v=<版號>，等於「內容一變網址就變」，
  //    所以快取優先不會拿到過期的東西。
  event.respondWith(cacheFirst(req, SHELL_CACHE));
});

async function networkFirst(req) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const res = await fetch(req);
    if (res && res.ok && res.status === 200 && res.type === 'basic') {
      cache.put(req, res.clone()).catch(() => {});
    }
    return res;
  } catch (err) {
    // 真的沒網路才走到這裡
    const hit = (await cache.match(req, { ignoreSearch: true })) ||
                (await cache.match('./index.html')) ||
                (await cache.match('./'));
    if (hit) return hit;
    throw err;
  }
}

async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  // 只存 200 的同源正常回應：206（部分內容）與 opaque 存了只會製造難查的怪象
  if (res && res.ok && res.status === 200 && res.type === 'basic') {
    cache.put(req, res.clone()).catch(() => {});
  }
  return res;
}
