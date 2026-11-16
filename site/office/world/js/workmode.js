// 純工作模式＋「設定」面板（2026-11-16，第二批第 10 項；參考 Habitica 被批「遊戲元素太吵、新手被系統淹沒」的反面教材）。
// 頂列多一顆「設定」，裡面一個開關：打開之後把所有遊戲元素關掉，只留員工狀態與工作：
//   · 火焰：營火的火苗收起來、W.fire.on＝false（不生火星、不會有人碰到火、不會被燒；已經燒著的當場熄掉）
//   · 運動：不再有人自己去打球游泳（ambientOn＝false）、不接受開始新的運動；進行中的運動結束
//   · 情緒台詞：mind／成長／運動／火災那幾支產生的頭上對話與表情符號一律不顯示（工作用的對話——派工摘要、對話框回覆——照常）
//   · 等級：名牌的 Lv、資訊卡的等級與專長／個性列、頂列「今日目標」、晉級慶祝、每日結算卡、通知裡的等級
//   · 慶祝：粒子慶祝（W.fx.burst）停掉
//   · 景觀動畫：飄動的雲收起來
// 這個模式只是「不顯示、不觸發」，資料不丟：經驗、體力、壓力照常在背景累積，關掉模式後都還在，不會重算也不會歸零。
// 記住選擇：aiOffice.game.workmode＝'1'（雲端存檔會一起帶走）。載入當下就先掛 CSS 類別，不會先閃一下遊戲畫面。
import { $, esc, lsGet, lsSet, GAME, whenWorld } from './workkit.js';

const KEY = GAME + 'workmode';
const GAMEY = /(mind_feel|mind|growth|growth_ui|sports[a-z_]*|fire|phys|rewards)\.js/;   // 哪些檔案發出來的對話／表情算「情緒與遊戲」
const WM = { on: lsGet(KEY) === '1', applied: 0 };
const root = document.documentElement; root.classList.toggle('wk', WM.on);

export function createWorkMode(W) {
  W.workmode = WM; let hooked = false, keep = {};
  function wrapChar(c) {
    if (c.__wk) return; c.__wk = 1;
    for (const m of ['say', 'emote']) { const o = c[m]; if (typeof o !== 'function') continue; c[m] = function (...a) { if (WM.on) { let s = ''; try { s = new Error().stack || ''; } catch (e) { /* 略 */ } if (GAMEY.test(s)) { WM.muted = (WM.muted || 0) + 1; return; } } return o.apply(this, a); }; }
  }
  function hookOnce() {
    if (hooked) return; hooked = true;
    const fx = W.fx; if (fx && typeof fx.burst === 'function') { const o = fx.burst; fx.burst = function (...a) { if (WM.on) { WM.fxSkipped = (WM.fxSkipped || 0) + 1; return; } return o.apply(this, a); }; }
    const sp = W.sports; if (sp && typeof sp.start === 'function') { const o = sp.start; sp.start = (...a) => WM.on ? false : o(...a); }
    const u = W.growth && W.growth.ui; if (u) for (const k of ['levelUp', 'goalHit', 'gain', 'settle', 'msg']) if (typeof u[k] === 'function') { const o = u[k]; u[k] = (...a) => WM.on ? undefined : o(...a); }
  }
  // 套用（開著時每秒補一次：新來的同事、重新載入的景觀都要跟上）
  function enforce() {
    if (!WM.on) return; hookOnce(); WM.applied++;
    for (const c of [...W.chars.values(), ...(W.pets || [])]) wrapChar(c);
    const F = W.fire; if (F) { if (F.on) { F.on = false; try { F.reset && F.reset(); } catch (e) { /* 略 */ } } if (F.flame) F.flame.visible = false; if (F.pools) for (const pl of [F.pools.PA, F.pools.PS]) { if (pl && pl.live) { pl.p.length = 0; pl.size.fill(0); for (let i = 3; i < pl.col.length; i += 4) pl.col[i] = 0; pl.live = 0; } } }   // F.on＝false 之後粒子不再前進，要自己清掉，不然半空中的火星會定格
    const sp = W.sports; if (sp) { sp.ambientOn = false; if (sp.sess || sp.amb) { try { sp.endAmbient && sp.endAmbient(); } catch (e) { /* 略 */ } try { sp.sess && sp.end && sp.end('user'); } catch (e) { /* 略 */ } } }
    if (W.clouds) W.clouds.visible = false;
  }
  function restore() {
    const F = W.fire; if (F) { F.on = true; if (F.flame) F.flame.visible = true; }
    const sp = W.sports; if (sp) sp.ambientOn = keep.ambientOn !== false && new URLSearchParams(location.search).get('ambient') !== '0';
    if (W.clouds) W.clouds.visible = true;
  }
  WM.set = (v, quiet) => {
    v = !!v; if (v === WM.on && WM.applied) return WM.on; if (v && !WM.on && W.sports) keep.ambientOn = W.sports.ambientOn;
    WM.on = v; lsSet(KEY, v ? '1' : '0'); root.classList.toggle('wk', v);
    if (v) { hookOnce(); enforce(); } else restore();
    const sw = $('wkSw'); if (sw) sw.checked = v;
    if (!quiet) { try { W.ui.toast(v ? '純工作模式已開啟：遊戲元素都收起來了' : '純工作模式已關閉：遊戲元素回來了'); } catch (e) { /* 略 */ } }
    W.emit && W.emit('workmode', 'ceo', { on: v }); return v;
  };
  WM.toggle = () => WM.set(!WM.on);
  setInterval(() => { if (WM.on) enforce(); }, 1000);
  if (WM.on) { enforce(); WM.applied = Math.max(WM.applied, 1); }

  // ───────── 「設定」鈕與面板 ─────────
  const btn = document.createElement('button'); btn.className = 'btn'; btn.id = 'stBtn'; btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'stPop'); btn.innerHTML = '設定<i></i>';
  ($('bar') || document.body).append(btn);
  const pop = document.createElement('div'); pop.className = 'pop'; pop.id = 'stPop'; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '設定'); ($('app') || document.body).append(pop);
  const HELP = '純工作模式：關掉所有遊戲元素（火焰、運動、情緒對話、等級、慶祝、景觀動畫），只留員工狀態與工作。經驗、體力、壓力還是會在背景累積，關掉這個模式就都回來，不會歸零。';
  function render() {
    const has = k => !!W[k], gate = id => { const g = W.gate && W.gate.peek ? W.gate.peek(id) : null; return g && !g.pass ? g.note : ''; };
    const pr = gate('office.priority');
    pop.innerHTML = `<h4>顯示</h4>
      <label class="st-sw"><input type="checkbox" id="wkSw" role="switch"${WM.on ? ' checked' : ''}><span class="st-tx"><b>純工作模式</b><em>關掉遊戲元素，只留狀態與工作</em></span><button class="gm-q" data-st="q" aria-expanded="false" aria-label="純工作模式說明">?</button></label>
      <div class="st-help" hidden>${esc(HELP)}</div>
      <h4>工作流程</h4>
      <div class="grid"><button class="it" data-st="bp"${has('blueprint') ? '' : ' hidden'}>任務藍圖</button><button class="it" data-st="pr"${has('prio') ? '' : ' hidden'}${pr ? ' disabled' : ''}>優先度表</button></div>${pr ? `<p class="st-note">${esc(pr)}</p>` : ''}`;
  }
  const place = () => { const r = btn.getBoundingClientRect(), w = pop.offsetWidth; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px'; };
  const close = () => { pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.classList.remove('on'); };
  btn.onclick = () => { const was = pop.hidden; W.ui.closePops(); if (was) { render(); pop.hidden = false; place(); btn.setAttribute('aria-expanded', 'true'); btn.classList.add('on'); } else close(); };
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('#stPop') && !e.target.closest('#stBtn')) close(); });
  pop.addEventListener('change', e => { if (e.target.id === 'wkSw') WM.set(e.target.checked); });
  pop.addEventListener('click', e => {
    const b = e.target.closest('[data-st]'); if (!b) return; const k = b.dataset.st;
    if (k === 'q') { const h = pop.querySelector('.st-help'); h.hidden = !h.hidden; b.setAttribute('aria-expanded', !h.hidden); e.preventDefault(); }
    else if (k === 'bp') { close(); W.blueprint && W.blueprint.open(); } else if (k === 'pr') { close(); W.prio && W.prio.open(); }
  });
  WM.btn = btn; WM.pop = pop;
  return WM;
}
whenWorld(W => { if (!W.workmodeReady) { W.workmodeReady = true; createWorkMode(W); } });
