/* 管理區：付費資料異常（#admin/gw）—— data-gw 第三階段（docs/datagw_plan.md 第 9 節）
   ----------------------------------------------------------------------------
   資料來源兩邊：
     · data-gw   POST /v1/admin/alerts（異常紀錄、標記、裝置數、目前門檻）、/v1/admin/wm（浮水印反查）、/v1/admin/devices/reset
     · account-api POST /v1/admin/uids（uid → email／名字）、/v1/admin/susp/list｜lift（停權紀錄、解除）
   兩邊都各自驗「你是不是管理者」（data-gw 也是回頭問 account-api），這一頁只是把結果排出來。
   沒設定 gateway（TwGw.on() 為 false）時，這個網址只顯示一行「尚未啟用」。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const tpe = (ms) => (ms ? new Date(ms + 8 * 3600000).toISOString().slice(0, 16).replace('T', ' ') : '—');
  const KIND = { burst: '短時間大量抓', multi_ip: '同權杖多個網段', bot_ua: '非瀏覽器', rate: '超過每分鐘上限', devices: '裝置超過上限',
    would_suspend: '達停權門檻（自動停權關閉，未停）', suspend: '已自動停權', suspend_failed: '停權呼叫失敗', notified: '已通知', notify_failed: '通知失敗' };
  const gwUrl = () => String((window.TW_ACCOUNT_OVERRIDE || window.TW_ACCOUNT || {}).gw || '').replace(/\/$/, '');
  async function gw(path, body) {
    const a = window.TwAccount; if (!a || !a.tok || !gwUrl()) return null;
    try {
      const r = await fetch(gwUrl() + path, { method: 'POST', headers: { 'content-type': 'text/plain' }, credentials: 'omit', body: JSON.stringify(Object.assign({ t: a.tok() }, body || {})) });
      const j = await r.json().catch(() => ({})); j._s = r.status; return j;
    } catch (e) { return null; }
  }
  function css() {
    T().css('agwCss', `
#v-subadm .agw h3{margin:0 0 6px;font-size:16px}
#v-subadm .agw .muted{color:var(--ink-2);font-size:13px}
#v-subadm .agw table{width:100%;border-collapse:collapse;font-size:13px}
#v-subadm .agw th,#v-subadm .agw td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
#v-subadm .agw .tw{overflow-x:auto}
#v-subadm .agw .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
#v-subadm .agw input{flex:1 1 220px;min-width:0;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:7px 10px;font:inherit}
#v-subadm .agw button{height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer}
#v-subadm .agw .kpi{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink-2)}
#v-subadm .agw .kpi b{color:var(--ink)}`);
  }
  async function render(v) {
    css();
    if (!gwUrl()) { v.innerHTML = '<div class="card agw"><h3>付費資料異常</h3><p class="muted">付費資料閘道尚未啟用（沒有設定 DATA_GW_URL）。</p></div>'; return; }
    v.innerHTML = '<div class="card agw"><p class="muted">載入中…</p></div>';
    const [al, sl] = await Promise.all([gw('/v1/admin/alerts', {}), T().call('/v1/admin/susp/list', {})]);
    if (!al || al._s !== 200) { v.innerHTML = `<div class="card agw"><h3>付費資料異常</h3><p class="muted">${al && al._s === 403 ? '不是管理者。' : '讀不到閘道（' + esc(al ? al._s : '連線失敗') + '）。'}</p></div>`; return; }
    const uids = [...new Set([...(al.alerts || []).map((r) => r.uid), ...(al.flags || []).map((r) => r.uid), ...(al.devices || []).map((r) => r.uid)])].filter((u) => u !== 'guest').slice(0, 100);
    const um = uids.length ? await T().call('/v1/admin/uids', { uids }) : null;
    const who = (u) => { const x = um && um.users && um.users[u]; return x ? `${esc(x.name || '')}<br><small class="muted">${esc(x.email)}</small>${x.susp ? ' <b style="color:var(--up)">停權中</b>' : ''}` : `<small class="muted">${esc(u)}</small>`; };
    const c = al.config || {};
    const susp = (sl && sl.rows) || [];
    v.innerHTML = `<div class="card agw" id="agwHead"><h3>付費資料異常</h3>
      <div class="kpi"><span>自動停權：<b id="agwAuto">${c.auto ? '開啟' : '關閉（只記錄）'}</b></span><span>門檻：<b>${esc(c.windowH)} 小時內 ${esc(c.after)} 次</b></span>
      <span>每帳號裝置：<b>${esc(c.maxDevices)} 台</b></span><span>每分鐘上限：<b>${esc(c.rate)}</b></span><span>大量抓：<b>${esc(c.burst)} 支／分</b></span>
      <span>通知：<b>${c.notify ? '已設定' : '未設定（只記錄）'}</b></span></div></div>
    <div class="card agw" style="margin-top:12px"><h3>浮水印反查</h3><p class="muted">貼上外流檔案裡的 <code>_wm</code>（12 碼，或整段 JSON），查是哪個帳號拿走的。</p>
      <div class="row"><input id="agwWm" placeholder="例如 Ab3dEf_hIj-k 或 {&quot;_wm&quot;:{...}}" aria-label="浮水印"><button type="button" id="agwWmGo">反查</button></div><div id="agwWmOut" class="muted" style="margin-top:8px"></div></div>
    <div class="card agw" style="margin-top:12px"><h3>標記帳號</h3><div class="tw"><table id="agwFlags"><thead><tr><th>帳號</th><th>次數</th><th>種類</th><th>最後</th><th></th></tr></thead><tbody>
      ${(al.flags || []).map((f) => `<tr data-uid="${esc(f.uid)}"><td>${who(f.uid)}</td><td>${f.n}</td><td>${f.kinds.map((k) => esc(KIND[k] || k)).join('、')}</td><td>${tpe(f.last)}</td>
        <td><button type="button" data-a="dev">清除裝置</button>${um && um.users && um.users[f.uid] && um.users[f.uid].susp ? ' <button type="button" data-a="lift">解除停權</button>' : ''}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">沒有被標記的帳號</td></tr>'}
    </tbody></table></div></div>
    <div class="card agw" style="margin-top:12px"><h3>異常紀錄（最近 300 筆，保留 30 天）</h3><div class="tw"><table id="agwAlerts"><thead><tr><th>時間</th><th>帳號</th><th>種類</th><th>細節</th></tr></thead><tbody>
      ${(al.alerts || []).map((r) => `<tr><td>${tpe(r.ts)}</td><td>${who(r.uid)}</td><td>${esc(KIND[r.kind] || r.kind)}</td><td>${esc(r.detail)}</td></tr>`).join('') || '<tr><td colspan="4" class="muted">沒有紀錄</td></tr>'}
    </tbody></table></div></div>
    <div class="card agw" style="margin-top:12px"><h3>停權紀錄</h3><div class="tw"><table id="agwSusp"><thead><tr><th>時間</th><th>帳號</th><th>動作</th><th>原因／備註</th><th>操作者</th></tr></thead><tbody>
      ${susp.map((r) => `<tr><td>${tpe(r.ts)}</td><td>${esc(r.name || '')}<br><small class="muted">${esc(r.email || r.uid)}</small></td><td>${r.act === 'suspend' ? '停權' : '解除'}</td><td>${esc(r.reason)}</td><td>${esc(r.by)}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">沒有紀錄</td></tr>'}
    </tbody></table></div></div>`;
    v.querySelector('#agwWmGo').onclick = async () => {
      const out = v.querySelector('#agwWmOut'); out.textContent = '查詢中…';
      const j = await gw('/v1/admin/wm', { wm: v.querySelector('#agwWm').value });
      if (!j || j._s !== 200) { out.textContent = j && j.error === 'bad_wm' ? '格式不對：要 12 碼的 _wm.a。' : '查詢失敗'; return; }
      if (!j.uid) { out.textContent = `查不到（比對了 ${j.checked} 個帳號；紀錄只保留 30 天）`; return; }
      const m = await T().call('/v1/admin/uids', { uids: [j.uid] }); const u = m && m.users && m.users[j.uid];
      out.innerHTML = `是 <b>${esc(u ? `${u.name || ''} ${u.email}` : j.uid)}</b>。最近取用：` + (j.last || []).slice(0, 5).map((r) => `${tpe(r.ts)} ${esc(r.name)}（${esc(r.ip)}）`).join('、');
    };
    v.querySelectorAll('#agwFlags button').forEach((b) => {
      b.onclick = async () => {
        const uid = b.closest('tr').dataset.uid;
        const j = b.dataset.a === 'dev' ? await gw('/v1/admin/devices/reset', { uid }) : await T().call('/v1/admin/susp/lift', { uid, note: '管理區解除' });
        T().toast(j && j._s === 200 ? (b.dataset.a === 'dev' ? `已清除 ${j.removed} 台裝置` : '已解除停權') : '操作失敗');
        render(v);
      };
    });
  }
  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'gw' || !T()) return null;
    const v = T().view('v-subadm'); if (!v) return null;
    render(v);
    return 'v-subadm';
  });
  window.TwAdminGw = { render };
})();
