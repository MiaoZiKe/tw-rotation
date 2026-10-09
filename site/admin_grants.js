/* 管理區：體驗額度（#admin/grants）—— 2026-10-09，docs/launch_gap_payment_1009.md 第 3 節
   ----------------------------------------------------------------------------
   Andy 10-09：「我部分付費功能他們看不到，兩個方式開放給他們用，但是有期限且限制次數…重點是得要有曝光」。
   這一頁三塊：
     ① 體驗活動清單：名稱、種類（上市體驗週 promo／新會員體驗 welcome）、期間、功能與次數、已發人數、已用次數、開關（撥了立刻生效）、編輯
     ② 新增／編輯：種類、名稱、功能多選（每項各自的次數）、期間合計／每天、welcome 天數、promo 起訖日（臺北日期，含頭含尾）、對象、開關
     ③ 查單一會員：拿過哪些體驗、每項用了幾次、最近用量；可手動延長 N 天（客服用）
   ★ 不能放進體驗的功能（法遵 docs/launch_gap_legal_1009.md 2-3）：今日關注完整名單、選股完整名單、AI 分析、券商觀點、盤中即時、四週期同看 ——
     清單裡根本不列（Worker 也擋：GRANT_BAN，存了回 400）。上限類（自選頁數／檔數）不是「次數」，也不列。
   API：account-api /v1/admin/grants/defs/{list,put,del}、/v1/admin/grants/user（只有管理者；這一頁只是排版）。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const DAY = 86400000;
  const tpeYmd = (ms) => new Date(ms + 8 * 3600000).toISOString().slice(0, 10);
  const tpeHm = (ms) => (ms ? new Date(ms + 8 * 3600000).toISOString().slice(0, 16).replace('T', ' ') : '—');
  const fromYmd = (s) => Date.parse(s + 'T00:00:00+08:00');
  /* 跟 worker.js GRANT_BAN 同一份（Worker 回的 ban 為準，這裡只是 Worker 還沒回來時的備用）*/
  const BAN0 = ['mkt.cand', 'mkt.cand.n', 'explore.list', 'explore.list.n', 'stock.ai', 'stock.mtf', 'live.tick', 'stock.k_min'];
  const ERR = { banned: '含不能放進體驗的功能', bad_feats: '至少要勾一個功能', bad_m: '每項次數要是 1～999 的整數', bad_time: '起訖日不對（結束要在開始之後）',
    bad_days: '新會員天數要是 1～60', bad_name: '請填名稱（20 字內）', bad_id: '代號只能用小寫英數、- 與 _', kind_fixed: '已建立的活動不能改種類', too_many: '活動最多 50 個', forbidden: '不是管理者' };
  const S = { d: null, edit: null, ban: BAN0 };
  function feats() {
    const F = window.TwFeatures; if (!F) return [];
    return F.list.filter((f) => f.kind === 'bool' && !f.adminOnly && f.cat !== 'grp' && !S.ban.includes(f.id));
  }
  const fname = (k) => { const F = window.TwFeatures, f = F && F.byId(k); return f ? f.name : k; };
  function css() {
    T().css('agrCss', `
#v-subadm .agr [hidden]{display:none!important}
#v-subadm .agr h3{margin:0 0 6px;font-size:16px}
#v-subadm .agr .muted{color:var(--ink-2);font-size:13px;line-height:1.6;margin:0 0 10px}
#v-subadm .agr .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
#v-subadm .agr .hd .sp{flex:1}
#v-subadm .agr table{width:100%;border-collapse:collapse;font-size:13.5px}
#v-subadm .agr th,#v-subadm .agr td{padding:8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
#v-subadm .agr th{color:var(--ink-2);font-weight:600;font-size:12.5px;white-space:nowrap}
#v-subadm .agr .tw{overflow-x:auto}
#v-subadm .agr .kd{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-2);white-space:nowrap}
#v-subadm .agr .kd.promo{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 45%,transparent)}
#v-subadm .agr td{white-space:nowrap}
#v-subadm .agr td.fl{font-size:12.5px;line-height:1.55;color:var(--ink-2);white-space:normal;min-width:260px;max-width:420px}
#v-subadm .agr button{height:32px;padding:0 12px;border-radius:8px;border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer;font-size:13.5px;white-space:nowrap}
#v-subadm .agr button.pri{background:var(--cyan);color:#04121a;border-color:transparent;font-weight:700}
#v-subadm .agr button.danger{color:var(--rise,#e5484d)}
#v-subadm .agr .sw{position:relative;display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;white-space:nowrap}
#v-subadm .agr .sw input{width:36px;height:20px;appearance:none;-webkit-appearance:none;border-radius:999px;background:var(--line-2);position:relative;cursor:pointer;margin:0;flex:none;transition:background .15s}
#v-subadm .agr .sw input::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:var(--panel);transition:left .15s}
#v-subadm .agr .sw input:checked{background:var(--cyan)}
#v-subadm .agr .sw input:checked::after{left:18px}
#v-subadm .agr .frm{display:grid;grid-template-columns:120px minmax(0,1fr);gap:10px 14px;align-items:center;margin-top:8px}
#v-subadm .agr .frm>label{font-size:13px;color:var(--ink-2)}
#v-subadm .agr .frm input[type=text],#v-subadm .agr .frm input[type=number],#v-subadm .agr .frm input[type=date],#v-subadm .agr .frm select,#v-subadm .agr .row input{
  background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:6px 10px;font:inherit;font-size:14px;min-width:0;box-sizing:border-box}
#v-subadm .agr .frm .inl{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#v-subadm .agr .fg{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px 14px;max-height:340px;overflow:auto;padding:8px;border:1px solid var(--line);border-radius:10px}
#v-subadm .agr .fg .cat{grid-column:1/-1;font-size:12px;font-weight:700;color:var(--ink-3);margin-top:4px}
#v-subadm .agr .fg label{display:flex;align-items:center;gap:6px;font-size:13.5px;min-width:0}
#v-subadm .agr .fg label span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v-subadm .agr .fg input[type=number]{width:62px;padding:3px 6px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:6px;font:inherit;font-size:13px}
#v-subadm .agr .fg input[type=number]:disabled{opacity:.4}
#v-subadm .agr .ban{font-size:12.5px;color:var(--ink-3);margin:6px 0 0}
#v-subadm .agr .st{font-size:13px;min-height:18px;margin-top:8px}
#v-subadm .agr .st.bad{color:var(--rise,#e5484d)}#v-subadm .agr .st.ok{color:var(--fall,#2fbf71)}
#v-subadm .agr .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
#v-subadm .agr .row input{flex:1 1 220px}
#v-subadm .agr .act{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;flex-wrap:wrap}
@media (max-width:640px){
  #v-subadm .agr .frm{grid-template-columns:minmax(0,1fr);gap:4px}
  #v-subadm .agr .frm>label{margin-top:8px}
  #v-subadm .agr .fg{grid-template-columns:minmax(0,1fr);max-height:300px}
  #v-subadm .agr th,#v-subadm .agr td{padding:6px;font-size:12.5px}
  /* 手機：活動清單改成一張張小卡（開關｜名稱｜編輯 一行，下面依序種類、期間、功能、已發已用），不橫向捲 */
  #v-subadm #agrList .tw{overflow:visible}
  #v-subadm #agrList table,#v-subadm #agrList tbody{display:block!important;width:100%}
  #v-subadm #agrList thead{display:none!important}
  #v-subadm #agrList tbody tr[data-id]{display:grid!important;grid-template-columns:auto minmax(0,1fr) auto;gap:4px 10px;align-items:center;padding:10px 0;border-bottom:1px solid var(--line)}
  #v-subadm #agrList tbody tr[data-id]>td{display:block!important;grid-column:2/-1;padding:0!important;border:0!important;min-width:0;max-width:none;white-space:normal;height:auto!important;max-height:none!important;line-height:1.5!important;overflow:visible!important}
  #v-subadm #agrList tbody tr[data-id]>td:first-child{grid-column:1;grid-row:1}
  #v-subadm #agrList tbody tr[data-id]>td:nth-child(2){grid-column:2;grid-row:1}
  #v-subadm #agrList tbody tr[data-id]>td:last-child{grid-column:3;grid-row:1}
  #v-subadm #agrList tbody tr[data-id]>td:nth-child(6)::before{content:"已發 "}
  #v-subadm #agrList tbody tr[data-id]>td:nth-child(7)::before{content:"已用 "}
  #v-subadm #agrList tbody tr[data-id]>td:is(:nth-child(6),:nth-child(7)){display:inline-block!important;grid-column:auto;color:var(--ink-2)}
  #v-subadm #agrList tbody tr[data-id]>td:nth-child(6){grid-column:2}
  #v-subadm #agrList tbody tr[data-id]>td:nth-child(7){grid-column:3}
  #v-subadm .agr button{height:36px}
}`);
  }
  const period = (d) => (d.kind === 'promo' ? `${tpeYmd(d.t0)} ～ ${tpeYmd(d.t1 - 1)}` : `註冊後 ${d.days} 天${d.t0 ? `（${tpeYmd(d.t0)}～${tpeYmd(d.t1 - 1)} 註冊的）` : ''}`);
  const live = (d) => { const now = Date.now(); return d.on && (d.kind === 'welcome' ? (!d.t0 || (d.t0 <= now && d.t1 > now)) : d.t0 <= now && d.t1 > now); };
  async function render(v) {
    css();
    v.innerHTML = '<div class="card agr"><p class="muted">載入中…</p></div>';
    const j = await T().call('/v1/admin/grants/defs/list', {});
    if (!(location.hash || '').startsWith('#admin/grants')) return;
    if (!j || j._s !== 200) { v.innerHTML = `<div class="card agr"><h3>體驗額度</h3><p class="muted">${j && j._s === 403 ? '這個帳號不是管理者。' : '讀不到體驗活動（' + esc(j ? j._s : '連不到會員伺服器') + '）。'}</p></div>`; return; }
    S.d = j; if (Array.isArray(j.ban)) S.ban = j.ban;
    paint(v);
  }
  function paint(v) {
    const defs = S.d.defs || [];
    v.innerHTML = `<div class="card agr" id="agrList"><div class="hd"><h3>體驗活動</h3><span class="sp"></span><button type="button" class="pri" id="agrNew">＋ 新增活動</button></div>
      <p class="muted">開關撥開就生效（會員重新整理後看到）；關掉時已發出去的也一起暫停。上市體驗週：活動期間登入的會員自動拿到；新會員體驗：第一次用 Google 登入的人自動拿到。
      畫面上一律叫「體驗額度」，免綁卡、到期不扣款、自動回原等級；次數由伺服器計。</p>
      <div class="tw"><table><thead><tr><th>開關</th><th>名稱</th><th>種類</th><th>期間（臺北）</th><th>功能與次數</th><th>已發</th><th>已用</th><th></th></tr></thead><tbody>
      ${defs.map((d) => `<tr data-id="${esc(d.id)}"><td><label class="sw" title="${d.on ? '開著' : '關著'}"><input type="checkbox" data-on="${esc(d.id)}"${d.on ? ' checked' : ''} aria-label="${esc(d.name)} 開關"></label></td>
        <td><b>${esc(d.name)}</b><br><small class="muted">${esc(d.id)}${live(d) ? '・<span style="color:var(--fall,#2fbf71)">進行中</span>' : d.on ? '・未在期間內' : ''}</small></td>
        <td><span class="kd ${d.kind}">${d.kind === 'promo' ? '上市體驗週' : '新會員體驗'}</span></td>
        <td>${esc(period(d))}</td>
        <td class="fl">${Object.entries(d.feats).map(([k, m]) => `${esc(fname(k))} ${m} 次`).join('、')}${d.per === 'day' ? '（每天）' : '（期間合計）'}${d.audience === 'member' ? '・所有會員' : '・只給免費會員'}</td>
        <td>${d.issued || 0} 人</td><td>${d.used || 0} 次</td>
        <td><button type="button" data-edit="${esc(d.id)}">編輯</button></td></tr>`).join('') || '<tr><td colspan="8" class="muted">還沒有活動</td></tr>'}
      </tbody></table></div><div class="st" id="agrSt" role="status"></div></div>
      <div class="card agr" id="agrForm" style="margin-top:12px" hidden></div>
      <div class="card agr" id="agrUser" style="margin-top:12px"><h3>查會員的體驗使用量</h3>
        <p class="muted">輸入會員的 Google 信箱，看他拿過哪些體驗、每項用了幾次；客服需要時可以手動延長。</p>
        <div class="row"><input type="text" id="agrMail" placeholder="name@gmail.com" aria-label="會員信箱" autocomplete="off"><button type="button" id="agrMailGo">查詢</button></div>
        <div id="agrUserOut" style="margin-top:10px"></div></div>`;
    const st = (m, bad) => { const e = v.querySelector('#agrSt'); if (e) { e.textContent = m; e.className = 'st ' + (bad ? 'bad' : 'ok'); } };
    v.querySelectorAll('input[data-on]').forEach((inp) => {
      inp.onchange = async () => {
        const d = defs.find((x) => x.id === inp.dataset.on); if (!d) return;
        inp.disabled = true;
        const r = await T().call('/v1/admin/grants/defs/put', { id: d.id, kind: d.kind, name: d.name, feats: d.feats, per: d.per, days: d.days, t0: d.t0, t1: d.t1, audience: d.audience, on: inp.checked });
        if (r && r._s === 200) { S.d = r; paint(v); st(`「${d.name}」已${inp.checked ? '打開' : '關閉'}`); if (window.TwGrants) window.TwGrants.refresh(); }
        else { inp.checked = !inp.checked; inp.disabled = false; st('沒有成功：' + (ERR[r && r.error] || (r ? r._s : '連不到')), true); }
      };
    });
    v.querySelector('#agrNew').onclick = () => form(v, null);
    v.querySelectorAll('button[data-edit]').forEach((b) => { b.onclick = () => form(v, defs.find((x) => x.id === b.dataset.edit)); });
    const go = v.querySelector('#agrMailGo');
    go.onclick = () => user(v, v.querySelector('#agrMail').value.trim().toLowerCase());
    v.querySelector('#agrMail').onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); go.click(); } };
  }
  function form(v, d) {
    const box = v.querySelector('#agrForm'); if (!box) return;
    const isNew = !d;
    const today = tpeYmd(Date.now());
    d = d || { id: '', kind: 'promo', name: '上市體驗週', feats: {}, per: 'total', days: 7, t0: fromYmd(today), t1: fromYmd(today) + 14 * DAY - 1, audience: 'free', on: false };
    const F = window.TwFeatures, cats = (F && F.cats) || [];
    const list = feats();
    const m0 = Object.values(d.feats)[0] || (d.kind === 'welcome' ? 3 : 5);
    const groups = cats.map((c) => [c, list.filter((f) => f.cat === c.id)]).filter(([, a]) => a.length);
    box.hidden = false;
    box.innerHTML = `<h3>${isNew ? '新增體驗活動' : '編輯：' + esc(d.name)}</h3>
      <div class="frm">
        <label for="agrKind">種類</label><select id="agrKind"${isNew ? '' : ' disabled'}><option value="promo"${d.kind === 'promo' ? ' selected' : ''}>上市體驗週（活動期間全體會員）</option><option value="welcome"${d.kind === 'welcome' ? ' selected' : ''}>新會員體驗（註冊後 N 天）</option></select>
        <label for="agrName">名稱</label><input type="text" id="agrName" maxlength="20" value="${esc(d.name)}">
        <label for="agrId">代號</label><input type="text" id="agrId" maxlength="24" value="${esc(d.id)}" placeholder="例如 promo-1013"${isNew ? '' : ' disabled'}>
        <label class="w-promo" for="agrT0">活動日期</label><div class="inl w-promo"><input type="date" id="agrT0" value="${esc(tpeYmd(d.t0 || fromYmd(today)))}" aria-label="開始日期"> 到 <input type="date" id="agrT1" value="${esc(tpeYmd((d.t1 || fromYmd(today) + 14 * DAY) - 1))}" aria-label="結束日期"><small class="muted" style="margin:0">（臺北時間，開始日 00:00 到結束日 23:59）</small></div>
        <label class="w-wel" for="agrDays">有效天數</label><div class="inl w-wel"><input type="number" id="agrDays" min="1" max="60" value="${esc(d.days || 7)}" style="width:90px"> 天（從註冊那一刻算）</div>
        <label for="agrPer">次數算法</label><select id="agrPer"><option value="total"${d.per !== 'day' ? ' selected' : ''}>期間合計（整段期間每項 M 次）</option><option value="day"${d.per === 'day' ? ' selected' : ''}>每天（每天每項 M 次）</option></select>
        <label for="agrAud">對象</label><select id="agrAud"><option value="free"${d.audience !== 'member' ? ' selected' : ''}>只給免費會員</option><option value="member"${d.audience === 'member' ? ' selected' : ''}>所有登入會員（付費會員本來就能用，不會被扣）</option></select>
        <label for="agrM">每項次數</label><div class="inl"><input type="number" id="agrM" min="1" max="999" value="${esc(m0)}" style="width:90px"><button type="button" id="agrMAll">套用到已勾的功能</button></div>
        <label>功能</label><div><div class="fg" id="agrFeats">${groups.map(([c, a]) => `<div class="cat">${esc(c.name)}</div>` + a.map((f) => {
          const on = Object.prototype.hasOwnProperty.call(d.feats, f.id);
          return `<label title="${esc(f.desc || '')}"><input type="checkbox" data-fk="${esc(f.id)}"${on ? ' checked' : ''}><span>${esc(f.name)}</span><input type="number" min="1" max="999" data-fm="${esc(f.id)}" value="${esc(on ? d.feats[f.id] : m0)}"${on ? '' : ' disabled'} aria-label="${esc(f.name)} 次數"></label>`; }).join('')).join('')}</div>
          <p class="ban">不能放進體驗（法遵）：今日關注完整名單、選股完整名單、AI 分析、券商觀點、盤中即時、四週期同看 —— 清單裡不列，存了也會被伺服器擋下。</p></div>
        <label for="agrOn">開關</label><label class="sw"><input type="checkbox" id="agrOn"${d.on ? ' checked' : ''}> 存檔後立刻生效</label>
      </div>
      <div class="st" id="agrFSt" role="status"></div>
      <div class="act">${isNew ? '' : '<button type="button" class="danger" id="agrDel">刪除這個活動</button><span style="flex:1"></span>'}<button type="button" id="agrCancel">取消</button><button type="button" class="pri" id="agrSave">儲存</button></div>`;
    const $ = (s) => box.querySelector(s);
    const kindSync = () => { const k = $('#agrKind').value; box.querySelectorAll('.w-promo').forEach((e) => { e.hidden = k !== 'promo'; }); box.querySelectorAll('.w-wel').forEach((e) => { e.hidden = k !== 'welcome'; });
      if (isNew && !$('#agrId').dataset.touched) $('#agrId').value = k === 'welcome' ? 'welcome-' + $('#agrT0').value.replace(/-/g, '').slice(4) : 'promo-' + $('#agrT0').value.replace(/-/g, '').slice(4);
      if (isNew && !$('#agrName').dataset.touched) $('#agrName').value = k === 'welcome' ? '新會員體驗' : '上市體驗週'; };
    $('#agrKind').onchange = kindSync; $('#agrT0').onchange = kindSync;
    $('#agrId').oninput = () => { $('#agrId').dataset.touched = '1'; }; $('#agrName').oninput = () => { $('#agrName').dataset.touched = '1'; };
    kindSync();
    box.querySelectorAll('input[data-fk]').forEach((c) => { c.onchange = () => { const n = box.querySelector(`input[data-fm="${c.dataset.fk}"]`); if (n) n.disabled = !c.checked; }; });
    $('#agrMAll').onclick = () => { const m = $('#agrM').value; box.querySelectorAll('input[data-fk]:checked').forEach((c) => { const n = box.querySelector(`input[data-fm="${c.dataset.fk}"]`); if (n) n.value = m; }); };
    $('#agrCancel').onclick = () => { box.hidden = true; box.innerHTML = ''; };
    const st = (m, bad) => { const e = $('#agrFSt'); e.textContent = m; e.className = 'st ' + (bad ? 'bad' : 'ok'); };
    $('#agrSave').onclick = async () => {
      const kind = $('#agrKind').value, fs = {};
      box.querySelectorAll('input[data-fk]:checked').forEach((c) => { fs[c.dataset.fk] = parseInt(box.querySelector(`input[data-fm="${c.dataset.fk}"]`).value, 10); });
      const body = { id: $('#agrId').value.trim(), kind, name: $('#agrName').value.trim(), feats: fs, per: $('#agrPer').value, audience: $('#agrAud').value, on: $('#agrOn').checked };
      if (kind === 'promo') { const a = $('#agrT0').value, b = $('#agrT1').value; if (!a || !b) { st('請選活動日期', true); return; } body.t0 = fromYmd(a); body.t1 = fromYmd(b) + DAY - 1; }
      else { body.days = parseInt($('#agrDays').value, 10); if (!isNew && d.t0) { body.t0 = d.t0; body.t1 = d.t1; } }
      $('#agrSave').disabled = true;
      const r = await T().call('/v1/admin/grants/defs/put', body);
      $('#agrSave').disabled = false;
      if (r && r._s === 200) { S.d = r; paint(v); const s2 = v.querySelector('#agrSt'); if (s2) { s2.textContent = `已儲存「${body.name}」${body.on ? '（開著）' : '（關著）'}`; s2.className = 'st ok'; } if (window.TwGrants) window.TwGrants.refresh(); return; }
      st('沒有存進去：' + (ERR[r && r.error] || (r ? r._s : '連不到')) + (r && r.k ? `（${fname(r.k)}）` : ''), true);
    };
    const del = $('#agrDel');
    if (del) del.onclick = () => {
      const D = T().dialog;
      D(`<h3>刪除「${esc(d.name)}」？</h3><p>刪掉之後，已經發給會員的這份體驗會立刻失效（用量紀錄保留給統計）。只是想暫停的話，用清單上的開關就好。</p>
        <div class="row2"><button type="button" data-close>取消</button><button type="button" class="pri" id="agrDelGo">確定刪除</button></div>`, (dl) => {
        dl.querySelector('#agrDelGo').onclick = async () => { dl.hidden = true; const r = await T().call('/v1/admin/grants/defs/del', { id: d.id }); if (r && r._s === 200) { S.d = r; paint(v); } else st('刪除失敗', true); };
      });
    };
    box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  async function user(v, email, extend) {
    const out = v.querySelector('#agrUserOut'); if (!out) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { out.innerHTML = '<p class="st bad">請輸入正確的 email</p>'; return; }
    out.innerHTML = '<p class="muted">查詢中…</p>';
    const j = await T().call('/v1/admin/grants/user', extend ? { email, extend_days: extend } : { email });
    if (!j || j._s !== 200) { out.innerHTML = `<p class="st bad">查詢失敗（${esc(j ? j.error || j._s : '連不到')}）</p>`; return; }
    if (!j.known) { out.innerHTML = '<p class="muted">查不到這個會員（還沒登入過）。</p>'; return; }
    const rows = j.grants.map((g) => `<tr><td><b>${esc(g.name)}</b><br><small class="muted">${esc(g.gid)}</small></td><td>${esc(tpeHm(g.start))}<br>～ ${esc(tpeHm(g.end - 1))}</td>
      <td>${g.active ? '<span style="color:var(--fall,#2fbf71)">有效</span>' : '已失效'}</td>
      <td class="fl">${g.feats ? Object.entries(g.feats).map(([k, x]) => `${esc(fname(k))} ${x.used}/${x.max}`).join('、') : '—'}</td></tr>`).join('');
    out.innerHTML = `<p class="muted" style="margin:0 0 6px">${esc(j.name || '')}（${esc(j.email)}）・註冊 ${esc(tpeHm(j.created))}</p>
      <div class="tw"><table id="agrUTbl"><thead><tr><th>體驗</th><th>期間（臺北）</th><th>狀態</th><th>已用／上限</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="muted">沒有拿過體驗額度</td></tr>'}</tbody></table></div>
      ${j.hits.length ? `<p class="muted" style="margin:10px 0 4px">最近用量（${j.hits.length} 筆）：${j.hits.slice(0, 12).map((h) => `${esc(h.day.slice(5))} ${esc(fname(h.k))}・${esc(h.key)}`).join('、')}</p>` : ''}
      ${j.grants.length ? `<div class="row"><span class="muted" style="margin:0">手動延長</span><input type="number" id="agrExt" min="1" max="60" value="3" style="flex:0 0 80px" aria-label="延長天數"> 天 <button type="button" id="agrExtGo">延長這個人的所有體驗</button></div>` : ''}`;
    const b = out.querySelector('#agrExtGo');
    if (b) b.onclick = () => user(v, email, parseInt(out.querySelector('#agrExt').value, 10));
  }
  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'grants' || !T()) return null;
    const v = T().view('v-subadm'); if (!v) return null;
    render(v);
    return 'v-subadm';
  });
  window.TwAdminGrants = { render };
})();
