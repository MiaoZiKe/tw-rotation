/* tasks.js — 網頁版任務板（`#tasks`）
 *
 * Andy 2026-09-20：「往後需要新增所有 Task 在 Obsidian 上面紀錄，以及這網站在做什麼、
 * 關於他每個功能在幹嘛、以及資料來源。因為很常發生我問你問題你做完，但我發現做不全，
 * 你就接續其他工作，導致很多事情都遺失沒完成。」
 *
 * 他選的方案是「在網站上多一頁」而不是同步 Obsidian —— 理由很單純：
 * 他只重新整理網頁、不跑本機指令，所以放在網站上他一定看得到。
 *
 * 資料來源是 `obsidian/tasks.yaml`（唯一一份），由 build_payload 轉成 site/data/tasks.json。
 * Obsidian 的 Markdown 則由 scripts/gen_taskboard.py 從同一份 YAML 產出。
 * 兩邊各維護一份的話第三天就會對不起來，所以刻意只留一個來源。
 */
(() => {
  const S = {
    blocked: { sym: '⛔', label: '被擋住', cls: 'st-blocked' },
    doing:   { sym: '🔵', label: '進行中', cls: 'st-doing' },
    review:  { sym: '🟡', label: '改完待驗', cls: 'st-review' },
    todo:    { sym: '⬜', label: '未開始', cls: 'st-todo' },
    done:    { sym: '✅', label: '已上線', cls: 'st-done' },
  };
  const ORDER = ['blocked', 'doing', 'review', 'todo', 'done'];

  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  /* 統計列：一眼看出「還有幾件沒好」。這一行才是 Andy 真正要的東西 ——
     他說的「我發現做不全」就是因為以前只能從對話裡一件一件回想。 */
  function summary(tasks) {
    const c = {};
    (tasks || []).forEach(t => { c[t.status] = (c[t.status] || 0) + 1; });
    return ORDER.filter(k => c[k]).map(k =>
      `<span class="pill ${S[k].cls}">${S[k].sym} ${S[k].label} ${c[k]}</span>`).join('');
  }

  function taskCard(t) {
    const st = S[t.status] || S.todo;
    const files = (t.files || []).map(f => `<code>${esc(f)}</code>`).join(' ');
    return `<div class="tk ${st.cls}">
      <div class="tk-h"><b>${esc(t.id)}</b><span class="tk-st">${st.sym} ${st.label}</span></div>
      <div class="tk-t">${esc(t.title)}</div>
      ${t.note ? `<div class="tk-n">${esc(t.note)}</div>` : ''}
      <div class="tk-f">${files || ''}${t.spent ? `<span class="tk-sp">花了 ${esc(t.spent)}</span>` : ''}</div>
    </div>`;
  }

  function render(d, el) {
    if (!d || !d.tasks) {
      el.innerHTML = `<div class="card"><h3>任務板</h3>
        <p class="hint">還沒有產出 tasks.json（下一次部署就會有）。</p></div>`;
      return;
    }
    const q = d.questions || [], b = d.blocked_on_andy || [], bl = d.backlog || [];
    const byStatus = ORDER.map(k => {
      const rows = (d.tasks || []).filter(t => t.status === k);
      if (!rows.length) return '';
      return `<div class="card" style="margin-top:14px"><h3>${S[k].sym} ${S[k].label}
        <small>${rows.length} 件</small></h3>
        <div class="tkwrap">${rows.map(taskCard).join('')}</div></div>`;
    }).join('');

    el.innerHTML = `
      <div class="card">
        <div class="row spread"><h2>任務板 <small>Andy 交代的每一件事在哪個狀態</small></h2>
          <span class="pill">更新 ${esc((d.meta || {}).updated || '')}</span></div>
        <div class="linkrow" style="margin-top:10px">${summary(d.tasks)}</div>
        <p class="hint" style="margin-top:8px">
          ★ <b>「改完但還沒上線」一律標「改完待驗」，不會標成「已上線」</b> ——
          沒有部署出去的工作等於沒做，這一條就是在防「我以為做完了但其實沒做全」。
        </p>
      </div>

      ${b.length ? `<div class="card hot" style="margin-top:14px">
        <h3>🔴 要你動手的<small>只有你能做，Claude 沒有權限</small></h3>
        ${b.map(t => `<div class="tk st-blocked">
          <div class="tk-h"><b>${esc(t.id)}</b></div>
          <div class="tk-t">${esc(t.title)}</div>
          ${t.note ? `<div class="tk-n">${esc(t.note)}</div>` : ''}
          ${t.ask ? `<div class="tk-ask">怎麼做：${esc(t.ask)}</div>` : ''}
        </div>`).join('')}</div>` : ''}

      ${q.length ? `<div class="card" style="margin-top:14px">
        <h3>⬜ 等你回答<small>回答之前我不動，免得做錯方向</small></h3>
        ${q.map(t => `<div class="tk st-todo">
          <div class="tk-h"><b>${esc(t.id)}</b></div>
          <div class="tk-t">${esc(t.title)}</div>
          ${t.note ? `<div class="tk-n">我的預設做法：${esc(t.note)}</div>` : ''}
        </div>`).join('')}</div>` : ''}

      ${byStatus}

      ${bl.length ? `<div class="card" style="margin-top:14px">
        <h3>📋 還沒排到<small>${bl.length} 件</small></h3>
        <div class="tkwrap">${bl.map(t => `<div class="tk st-todo">
          <div class="tk-h"><b>${esc(t.id)}</b></div>
          <div class="tk-t">${esc(t.title)}</div>
          ${t.note ? `<div class="tk-n">${esc(t.note)}</div>` : ''}
        </div>`).join('')}</div></div>` : ''}
    `;
  }

  window.TaskBoard = { render };
})();
