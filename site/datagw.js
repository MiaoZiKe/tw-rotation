/* 付費資料閘道的前端（docs/datagw_plan.md 第二階段；後端 workers/data-gw/worker.js）
   ----------------------------------------------------------------------------
   什麼時候生效：同時滿足兩件事才會改走 gateway，否則一律照舊讀 data/*.json（正式站目前就是這樣）：
     ① window.TW_ACCOUNT.gw 有網址（部署時 pages.yml 依 Secret DATA_GW_URL 寫進 account_config.js；repo 裡永遠是空的）
     ② data/datagw_index.json 存在（pipeline/split_paid.py 搬完付費檔才會寫；沒搬就沒有）
   所以「設了網址但檔案還在公開目錄」或「搬了但沒設網址」都不會讓畫面壞掉 —— 後者會讓付費檔 404，所以 pages.yml 兩件事一起開。
   權杖：拿登入權杖（account.js）去 /v1/session 換一張 5 分鐘的資料權杖，綁這台裝置的隨機 id（localStorage tw.gw.dev）；
         到期前 30 秒或回 401 時自動重換一次。沒登入 → 不帶權杖，由 gateway 依「訪客」範本判斷。
   浮水印：gateway 會在 JSON 裡加 _wm；這裡解析後刪掉，免得前端用 Object.keys 走訪對照表時多一個怪鍵。
   ============================================================================ */
(function () {
  'use strict';
  const K_DEV = 'tw.gw.dev';
  const gwUrl = () => String((window.TW_ACCOUNT_OVERRIDE || window.TW_ACCOUNT || {}).gw || '').replace(/\/$/, '');
  let idxP = null, sess = null, sessP = null;

  function devId() {
    let d = null;
    try { d = localStorage.getItem(K_DEV); } catch (e) { /* 私密視窗 */ }
    if (!d || !/^[A-Za-z0-9_-]{16,64}$/.test(d)) {
      const b = crypto.getRandomValues(new Uint8Array(24));
      d = btoa(String.fromCharCode.apply(null, b)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
      try { localStorage.setItem(K_DEV, d); } catch (e) { /* 這次瀏覽有效 */ }
    }
    return d;
  }
  function index() {
    if (!gwUrl()) return Promise.resolve(null);
    return idxP || (idxP = fetch('data/datagw_index.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null)).then((j) => (j && Array.isArray(j.paid) ? j.paid.map((t) => (t.re ? new RegExp(t.re) : t.p)) : null))
      .catch(() => null));
  }
  async function isPaid(name) {
    const ix = await index();
    return !!ix && ix.some((t) => (typeof t === 'string' ? t === name : t.test(name)));
  }
  const loginTok = () => (window.TwAccount && window.TwAccount.tok ? window.TwAccount.tok() : null);
  async function token() {
    const lt = loginTok();
    if (!lt) { sess = null; return null; }
    if (sess && sess.lt === lt && sess.exp * 1000 - Date.now() > 30000) return sess.tok;
    if (sessP) return sessP;
    sessP = (async () => {
      try {
        const r = await fetch(gwUrl() + '/v1/session', { method: 'POST', headers: { 'content-type': 'text/plain' }, credentials: 'omit',
          body: JSON.stringify({ t: lt, d: devId() }) });
        const j = r.ok ? await r.json() : null;
        sess = j && j.tok ? { tok: j.tok, exp: j.exp, lt } : null;
      } catch (e) { sess = null; }
      return sess ? sess.tok : null;
    })().finally(() => { sessP = null; });
    return sessP;
  }
  function strip(d) {
    if (d && typeof d === 'object') {
      if (!Array.isArray(d)) delete d._wm;
      else if (d[0] && typeof d[0] === 'object') delete d[0]._wm;
    }
    return d;
  }
  /* 從 gateway 拿一支付費檔。回 { data, txt }；失敗丟 Error，err.status＝HTTP 狀態（401 login／403 plan／429 rate）*/
  async function get(name) {
    for (let i = 0; i < 2; i++) {
      const tok = await token();
      const h = { 'X-Device': devId() };
      if (tok) h.Authorization = 'Bearer ' + tok;
      const r = await fetch(gwUrl() + '/v1/data/' + name, { headers: h, credentials: 'omit', cache: 'no-store' });
      if (r.status === 401 && tok && i === 0) { sess = null; continue; }   // 權杖剛好過期或被換掉：重換一次
      if (!r.ok) { const e = new Error(String(r.status)); e.status = r.status; throw e; }
      const txt = await r.text();
      return { data: strip(JSON.parse(txt)), txt };
    }
    const e = new Error('401'); e.status = 401; throw e;
  }
  /* 給沒走 App.load 的地方（chart.js 的 hist、mobile3.js）：付費走 gateway、免費照舊；失敗回 null */
  async function json(name, init) {
    try {
      if (await isPaid(name)) return (await get(name)).data;
      const r = await fetch('data/' + name + '.json', init || {});
      return r.ok ? await r.json() : null;
    } catch (e) { return null; }
  }
  window.TwGw = { on: () => !!gwUrl(), isPaid, get, json, reset: () => { sess = null; idxP = null; } };
})();
