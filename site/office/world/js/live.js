// 即時模式（2026-11-14，擁有者原話：「目前看起來還是 Demo 版本，我想實際串接我的專案」）
//
// 有接入碼（或擁有者用網站登入身分）時，每 15 秒讀一次 AI Office 收件端（workers/ai-office-bridge）的
// GET /v1/office/<id>/state，把「你的 Claude 真的發生的事」餵進同一個狀態層（state.emit），演出全部沿用 jobs.js／power.js：
//   · 每個工作階段一位 CEO：最近在動的那個是本尊，其他同時開著的在 CEO 桌旁當「分身」（最多 3 位，超過寫 +N）
//   · 子 Agent 類型對應到名冊上的同事；名冊沒有的類型（general-purpose、Explore…）自動坐進後備座位；座位滿了由現有同事兼任
//   · 派工 → 領任務 → 工具類別小動作 → 交件；等你核准／等你回答；回合結束；額度（有回報才顯示）
// 一個專案一間辦公室（2026-11-15）：網址 ?project=<專案雜湊> 指定只看哪個專案（收件端依它過濾事件、角色、分身）；
//   CEO 名牌與「CEO 辦公室」門牌加上專案名（「tw-rotation CEO」），左上角改成「← 專案名 ▾」（回專案清單、下拉切換專案）。
//   專案名稱沒意義（user／root／tmp…，雲端工作階段沒掛儲存庫時的資料夾名）一律顯示「雲端工作階段」。
// 規矩：
//   · 收不到資料就寫「尚未收到回報」，不拿示範資料充數；資訊卡、績效總表、名牌字章在即時模式下只用真實事件算的數字，
//     資料不夠就寫「樣本不足」或「未評等」。示範資料改成可手動切換的「展示模式」。
//   · 分頁在背景時暫停讀取，回到前景立刻讀一次。
//   · 接入碼不長期存放（2026-11-15）：只在記憶體，領碼視窗關掉就清掉，觀看改用網站登入身分（X-AIO-Session）；localStorage 只留網址、模式、專案。
//     不放進網址列（#aio=… 會被讀走後立刻清掉）。舊版存在儲存裡的碼，第一次載入時搬進記憶體並清除。
import { hhmm } from './state.js';
import { textTexture } from './kit.js';
import { createToolAnim } from './toolanim.js';   // 2026-11-16 第二批第 1 項：真實工具呼叫 → 角色動作＋頭上小圖示
import { createLinks } from './links.js';         // 第 2 項：子 Agent 與派工者之間的連線
import { createHealth } from './health.js';       // 第 3 項：頂列連線健康燈＋自動重連

const LS = 'aiOffice.live.v1', ACCT_TOK = 'tw.acct.tok';
const POLL_MS = 15000;
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const short = (t, n) => { t = String(t || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const lsGet = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
const lsSet = (k, v) => { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); return true; } catch (e) { return false; } };
const hash = s => { let h = 0; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };
// Claude Code 內建的子 Agent 類型 → 暱稱與物種（名冊裡沒有的類型才用得到）
const BUILTIN = { 'general-purpose': ['通才', 'bird'], Explore: ['探路', 'snail'], Plan: ['規劃', 'note'], 'statusline-setup': ['設定', 'robo'], 'claude-code-guide': ['導覽', 'bulb'], 'output-style-setup': ['樣式', 'pencil'] };
const TO_RE = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/;   // 跟收件服務 worker.js 的 TO_RE 一致（指令的 to 欄位格式）
const POOL = ['bird', 'snail', 'robo', 'bulb', 'note', 'cloud', 'mug', 'star', 'seal', 'octo', 'folder', 'stamp'];
const STATE_CATS = new Set(['read', 'write', 'search', 'test', 'deploy', 'wait', 'other']);
const SESS_TEXT = { working: '工作中', idle: '待命中', ended: '已結束', error: '遇到錯誤' };
const isFail = s => /^(失敗|錯誤)[:：]/.test(s || '');
// ───────── 接入引導：提示詞與圖片版位（可設定的常數） ─────────
// 提示詞是「貼到 Claude 聊天室」的，所以絕對不含接入碼（聊天紀錄會保存）；接入碼只在安全表單卡片裡貼。
// {HOST}＝收件端主機名稱（由實際收件端網址帶入）。設定腳本採「候選乙」：直接把掛鉤寫進使用者層級設定檔（理由見 docs/ai_office/bridge_test_report.md 第九節與交件說明）。
const GUIDE_REPO = 'https://github.com/MiaoZiKe/tw-rotation';
const GUIDE_PLUGIN_DIR = 'tools/ai_office_bridge/plugin/ai-office-bridge';
const GUIDE_PROMPT = `請你幫我把這個雲端環境接上「AI 辦公室」，讓我在辦公室網頁即時看到你和子 Agent 做事的進度。全程用繁體中文，每一步先告訴我「我要按什麼」再動手。

安全規矩：接入碼是祕密。請用「安全表單卡片」向我要，不要請我把接入碼貼在聊天室。

第 1 步：用安全表單向我要網路金鑰
・主機：{HOST}
・標頭：Authorization　前綴：Bearer
・名稱：AI 辦公室接入碼
我會把接入碼貼進卡片的值那一格並按儲存。

第 2 步：把接入元件裝到這個雲端環境，之後每個新工作階段都自動送事件
請用環境工具提出一份設定腳本，讓我按同意。腳本只做這三件事，而且不含任何金鑰：
・用 git clone --depth 1 從公開儲存庫 ${GUIDE_REPO} 取得 ${GUIDE_PLUGIN_DIR} 這個資料夾，放到 /opt/ai-office-bridge
・執行 python3 /opt/ai-office-bridge/scripts/install_hooks.py --settings ~/.claude/settings.json
・建立 ~/.ai-office/config.json，內容 {"AIO_URL": "https://{HOST}"}
提出前請先在你的容器逐行跑過，確認每一步都成功；如果網路擋住 github.com，請告訴我並提出加入允許清單。

第 3 步：送一筆測試事件
金鑰與設定腳本都完成後，用 curl 對 https://{HOST}/v1/events 送出 POST（Content-Type: application/json），內容：
{"events":[{"event":"SessionStart","session_id":"aio-test","project_name":"接入測試"},{"event":"SessionEnd","session_id":"aio-test"}]}
把回應回報給我；回應有 "ok":true 就代表接上了。若回 401 或被擋，等一分鐘再試一次，仍失敗就告訴我原因。最後提醒我：設定腳本只在「新的」雲端工作階段生效，請開一個新的工作階段試試。`;
// 操作圖片：實測後把截圖放進 site/office/guide/shots/，再把該筆 ready 改成 true（沒檔案就不發請求，避免主控台出現 404）
const GUIDE_SHOTS = {
  1: { file: 's1_copy.png', ready: false, alt: '按「複製提示詞」，到 Claude 對話框貼上送出' },
  2: { file: 's2_paste.png', ready: false, alt: 'Claude 跳出表單卡片時，把接入碼貼進「值」那一格，按儲存' },
};
const EMPTY_BASE = { nDone: 0, nDoing: 0, nTodo: 0, list: [], eta: '未提供', etaMin: '—', opt: '', lastDone: '—', lastDoing: '—', nextTodo: '' };

function loadCfg() { try { const o = JSON.parse(lsGet(LS) || 'null'); return o && typeof o === 'object' ? o : {}; } catch (e) { return {}; } }

export function createLive(W, X) {
  const { state: S, ui, sim } = X, R = X.rewards || W.rewards, qs = new URLSearchParams(location.search);
  const L = { mode: 'demo', status: 'off', cfg: loadCfg(), seq: 0, pollMs: Math.max(500, +qs.get('live_poll') || POLL_MS), polls: 0, timer: 0, inflight: false, data: null, lastOk: 0, fails: 0,
    project: null, primary: null, clones: [], typeMap: new Map(), extras: new Map(), fallbackNick: new Map(), seen: new Set(), sharedNoted: new Set(), revealCode: null, code: null, msg: '', lastQuota: '', url: '',
    guide: { open: false, step: 1, showPrompt: false, fix: false, busy: false, owner: 'unknown', eye: false, base: null, done: false, copied: '', codeExists: false, sig: '' } };
  W.live = L;
  // 專案：網址的 project（專案雜湊）、office（辦公室代號）。office 以 o_ 開頭的是伺服器上的辦公室（收件端用 view 套每間 5 位 Agent 的上限）
  const AP = window.AIOProj || { label: n => (n && !/^(user|root|home|tmp)$/i.test(n) ? n : '雲端工作階段'), trunc: (t, n) => (Array.from(t).length > n ? Array.from(t).slice(0, n - 1).join('') + '…' : t) };
  L.qProject = /^[0-9a-f]{16}$/.test(qs.get('project') || '') ? qs.get('project') : null;
  L.qOffice = /^[A-Za-z0-9_-]{1,40}$/.test(qs.get('office') || '') ? qs.get('office') : null;
  L.qView = /^o_[A-Za-z0-9_-]{6,30}$/.test(L.qOffice || '') ? L.qOffice : null;
  L.projName = null;
  // 接入碼不長期存放（2026-11-15 規格第五節第 3 點）：只放記憶體（L.code），關掉視窗／重新整理就沒有；存進 localStorage 的只有網址、模式、專案這些設定。
  // 觀看改用登入身分（X-AIO-Session）。舊版曾把碼存在這台裝置：第一次載入時搬進記憶體並從儲存清掉。
  const save = () => { const o = { ...L.cfg }; delete o.code; lsSet(LS, JSON.stringify(o)); };
  if (L.cfg.code) { L.code = L.cfg.code; delete L.cfg.code; save(); }
  const emit = (name, o = {}) => S.emit({ hook_event_name: name, live: true, ...o });
  const C = id => W.chars.get(id);

  // 網址 #aio=<接入碼>：讀走、存起來、立刻從網址列清掉（不留在瀏覽紀錄）
  { const m = /(?:^#|&)aio=([A-Za-z0-9_-]{8,200})/.exec(location.hash || ''); if (m) { L.code = m[1]; L.cfg.office = L.cfg.office || 'main'; delete L.cfg.show; save(); try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { /* 略 */ } } }
  if (qs.get('aio_url')) { L.cfg.url = qs.get('aio_url').replace(/\/+$/, ''); save(); }

  // ───────── 收件端網址：設定 → 從會員 API 網址推（tw-account. → tw-ai-office-bridge.） ─────────
  function loadScript(src) { return new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = () => res(); setTimeout(res, 4000); document.head.append(s); }); }
  async function resolveUrl() {
    if (L.cfg.url) return L.cfg.url;
    if (L.url) return L.url;
    if (!window.TW_ACCOUNT) await loadScript('../account_config.js');
    const api = window.TW_ACCOUNT && window.TW_ACCOUNT.api;
    if (api && /\/\/tw-account\./.test(api)) L.url = api.replace('//tw-account.', '//tw-ai-office-bridge.').replace(/\/+$/, '');
    return L.url;
  }
  L.resolveUrl = resolveUrl;
  const loginTok = () => lsGet(ACCT_TOK);
  function authHeaders() {
    if (L.code) return { Authorization: 'Bearer ' + L.code };
    const t = loginTok(); if (L.cfg.login && t) return { 'X-AIO-Session': t };
    return null;
  }
  const hasCred = () => !!(L.code || (L.cfg.login && loginTok()));

  // ───────── 樣式（只加新檔，不動既有 css） ─────────
  const css = document.createElement('style'); css.id = 'aioCss';
  css.textContent = `
.btn.aio-b{gap:6px}.btn.aio-b i.dot{width:8px;height:8px;border-radius:50%;background:#b9aca2;flex:none}
.btn.aio-b.live i.dot{background:#35b36b;box-shadow:0 0 0 3px rgba(53,179,107,.18)}.btn.aio-b.warn i.dot{background:#f2a93b}.btn.aio-b.bad i.dot{background:#c2590c}
.btn.aio-b.demo{color:var(--sub)}.btn.aio-b .s{display:none}
.aio-pop{width:340px;line-height:1.55;font-size:14px}.aio-pop h4{font-size:15px;color:var(--ink);margin:2px 4px 6px}
.aio-pop p{margin:4px 4px 8px;font-size:13px;color:var(--sub)}.aio-pop .st{color:var(--ink);font-weight:700}
.aio-pop .row{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px}.aio-pop .row .btn{box-shadow:none;border:1px solid var(--line);height:34px;padding:0 12px}
.aio-pop .row .btn.on{background:var(--on);border-color:var(--on);color:#fff}
.aio-pop input,.aio-pop select{font:inherit;font-size:14px;border:1px solid var(--line);border-radius:12px;padding:6px 10px;background:#fff;min-width:0;flex:1}
.aio-pop label{display:block;font-size:12px;color:var(--sub);margin:6px 4px 2px}
.aio-pop ul{list-style:none;margin:4px 0 8px;padding:0}.aio-pop li{display:flex;flex-wrap:wrap;gap:2px 6px;align-items:baseline;padding:5px 4px;border-bottom:1px solid var(--line);font-size:13px}
.aio-pop li b{flex:none}.aio-pop li span{flex:1 1 7.5em;min-width:7.5em;color:var(--sub);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.aio-pop li em{font-style:normal;font-size:12px;color:var(--sub)}
.aio-code{display:flex;gap:6px;align-items:center;background:var(--on2);border-radius:12px;padding:8px;margin:4px 0 6px}
.aio-code code{flex:1;min-width:0;word-break:break-all;font-size:12.5px}
.aio-pop details summary{cursor:pointer;font-size:13px;color:var(--sub);margin:4px}
#aioLedger{right:12px;top:64px;width:min(760px,calc(100vw - 24px));z-index:22}
#aioLedger h3{margin:0 0 6px;font-size:16px;display:flex;align-items:center;gap:8px;padding-right:36px;flex-wrap:wrap}
#aioLedger .chip2{font-size:12px;font-weight:600;color:var(--sub);background:var(--on2);border-radius:999px;padding:2px 8px}
#aioLedger table{width:100%;border-collapse:collapse;font-size:13px}#aioLedger th,#aioLedger td{padding:6px 6px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
#aioLedger th:first-child,#aioLedger td:first-child{text-align:left;white-space:normal}#aioLedger th{color:var(--sub);font-weight:600;font-size:12px}
#aioLedger .na{color:var(--sub);font-size:12px}#aioLedger .help{font-size:12px;color:var(--sub);margin:6px 0 0}
#aioLedger .empty{padding:18px 4px;color:var(--sub);font-size:14px}#aioLedger .ceo{margin:2px 0 8px;font-size:13px;background:var(--on2);border-radius:12px;padding:6px 10px}
.rw.aio-rw{font-size:13px;line-height:1.6}.rw.aio-rw b{font-size:13px}.rw.aio-rw .na{color:var(--sub)}
body.aio-live :is(#demoBtn,#simBtn,#rwTip){display:none!important}
@media (max-width:640px){
  #bar #aioBadge{order:3}.btn.aio-b .l{display:none}.btn.aio-b .s{display:inline}
  .aio-pop{width:auto}
  #aioLedger{left:8px!important;right:8px!important;width:auto;top:auto!important;bottom:8px!important;max-height:56dvh}
  #aioLedger thead{display:none}#aioLedger tr{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px 8px;padding:6px 0;border-bottom:1px solid var(--line)}
  #aioLedger td{border:0;padding:1px 0;text-align:left;white-space:normal}#aioLedger td:first-child{grid-column:1/-1;font-weight:700}
  #aioLedger td[data-l]:before{content:attr(data-l) " ";color:var(--sub);font-size:11px}
}`;
  css.textContent += `
.btn.aio-b{position:relative}
.btn.aio-b.hint:after{content:"";position:absolute;top:3px;right:3px;width:10px;height:10px;border-radius:50%;background:#e8590c;border:2px solid var(--card);box-sizing:content-box;animation:aioPulse 1.8s ease-out infinite}
@keyframes aioPulse{0%{box-shadow:0 0 0 0 rgba(232,89,12,.5)}70%{box-shadow:0 0 0 8px rgba(232,89,12,0)}100%{box-shadow:0 0 0 0 rgba(232,89,12,0)}}
@media (prefers-reduced-motion:reduce){.btn.aio-b.hint:after{animation:none}}
.aio-g{position:fixed;inset:0;z-index:60;display:flex;align-items:center;justify-content:center;padding:12px}
.aio-g[hidden]{display:none}
.aio-gbk{position:absolute;inset:0;background:rgba(74,58,50,.45)}
.aio-gp{position:relative;width:min(640px,100%);max-height:calc(100dvh - 24px);display:flex;flex-direction:column;background:var(--card);border-radius:var(--r);box-shadow:var(--sh);color:var(--ink);outline:0}
.aio-gp header{display:flex;align-items:center;gap:8px;padding:14px 16px 6px}.aio-gp h3{margin:0;font-size:17px;flex:1}
.aio-gx{width:36px;height:36px;border-radius:50%;border:0;background:var(--on2);color:var(--ink);font-size:20px;line-height:1;padding:0}
.aio-steps{list-style:none;display:flex;gap:6px;margin:0;padding:6px 16px 10px}
.aio-steps li{flex:1;min-width:0}
.aio-steps button{width:100%;min-height:44px;display:flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--line);background:#fff;border-radius:14px;padding:4px 6px;font:inherit;font-size:13px;font-weight:600;color:var(--sub)}
.aio-steps b{flex:none;width:22px;height:22px;border-radius:50%;background:var(--on2);color:var(--sub);display:inline-flex;align-items:center;justify-content:center;font-size:12px}
.aio-steps .on button{border-color:var(--on);color:var(--ink);background:var(--on2)}.aio-steps .on b{background:var(--on);color:#fff}
.aio-steps .ok b{background:#35b36b;color:#fff}
.aio-gbody{padding:4px 16px 8px;overflow:auto;flex:1;min-height:0;font-size:14px;line-height:1.65}
.aio-gbody p{margin:4px 0 8px;color:var(--sub);font-size:13px}.aio-gbody p.k{color:var(--ink)}
.aio-prompt{margin:6px 0 8px;max-height:min(40dvh,260px);overflow:auto;background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:12.5px;line-height:1.6;white-space:pre-wrap;word-break:break-word;font-family:inherit;color:var(--ink)}
.aio-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}
.aio-gp .btn{box-shadow:none;border:1px solid var(--line);height:40px;text-decoration:none;color:var(--ink);justify-content:center}
.aio-gp .btn.big{height:48px;font-size:15px;padding:0 22px;background:var(--on);border-color:var(--on);color:#fff}
.aio-gp .btn.warn{border-color:#c2590c;color:#c2590c;background:#fff}
.aio-mask{flex:1;min-width:0;display:flex;align-items:center;gap:6px;background:var(--on2);border-radius:12px;padding:6px 6px 6px 12px}
.aio-mask code{flex:1;min-width:0;word-break:break-all;font-size:13px}
.aio-gp .btn.sq{width:40px;padding:0;flex:none}
.aio-shot{margin:8px 0;border:1px dashed var(--line);border-radius:12px;background:#f1ece6;overflow:hidden}
.aio-shot img{display:block;width:100%;height:auto}
.aio-shot .ph{display:flex;align-items:center;justify-content:center;min-height:84px;padding:10px;text-align:center;color:var(--sub);font-size:13px}
.aio-shot figcaption{padding:6px 10px;font-size:12px;color:var(--sub);background:#fff}
.aio-box{background:var(--on2);border-radius:12px;padding:10px 12px;margin:8px 0;font-size:13px}.aio-box.ok{background:#e6f6ec;color:#17683a;font-weight:700;font-size:15px}
.aio-box.lock{background:#f1ece6;color:var(--ink);font-size:14px;font-weight:600}
.aio-wait{display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;margin:6px 0}
.aio-wait i{width:12px;height:12px;border-radius:50%;background:var(--on);animation:aioPulse 1.4s ease-out infinite;flex:none}
.aio-gbody ol.fix{margin:6px 0 8px;padding-left:20px;font-size:13px;color:var(--ink)}.aio-gbody ol.fix li{margin:3px 0}
.aio-gbody details{margin:8px 0;font-size:13px}.aio-gbody summary{cursor:pointer;color:var(--sub);min-height:32px;display:flex;align-items:center}
.aio-gbody input{font:inherit;font-size:14px;border:1px solid var(--line);border-radius:12px;padding:6px 10px;background:#fff;min-width:0;flex:1;height:40px}
.aio-gbody label{display:block;font-size:12px;color:var(--sub);margin:6px 0 2px}
.aio-gp footer{display:flex;gap:8px;align-items:center;padding:8px 16px 14px;border-top:1px solid var(--line)}.aio-gp footer .sp{flex:1}
.aio-msg{margin:4px 0;font-size:13px;color:var(--ink);font-weight:700}
.aio-gp{width:min(780px,100%)}
.aio-cards{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:6px 0 10px}
.aio-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px;min-width:0;display:flex;flex-direction:column;gap:2px}
.aio-card h4{margin:0 0 2px;font-size:15px;color:var(--ink)}.aio-card p{margin:2px 0 4px;font-size:13px;color:var(--sub);line-height:1.5}
.aio-card .aio-row{margin:6px 0 2px}
.aio-gbody code.aio-mask{display:block;flex:1;min-width:0;background:var(--on2);border-radius:12px;padding:10px 12px;font-size:13px;word-break:break-all}
.aio-lk{background:none;border:0;padding:0 2px;min-height:32px;display:inline-flex;align-items:center;font:inherit;font-size:13px;color:var(--on);text-decoration:underline;cursor:pointer;width:fit-content}
.aio-lk.warnlk{color:#c2590c}
.aio-cap{margin:4px 0 0;font-size:12px;color:var(--sub)}
.aio-gbody details#aioHelp{margin:6px 0 10px}
@media (max-width:640px){.aio-cards{grid-template-columns:1fr}}
@media (max-width:640px){
  .aio-g{padding:0;align-items:stretch}.aio-gp{width:100%;max-height:none;height:100dvh;border-radius:0}
  .aio-gp header{padding-top:max(14px,env(safe-area-inset-top))}.aio-gp footer{padding-bottom:max(14px,env(safe-area-inset-bottom))}
  .aio-steps{gap:4px;padding:6px 10px 8px}.aio-steps button{font-size:12px;gap:4px;padding:4px}.aio-gbody{padding:4px 12px 8px}
  .aio-prompt{max-height:36dvh}
}`;
  css.textContent += `
.ttl.pj{padding-left:4px;gap:2px}.ttl.pj .q{width:34px;height:34px;flex:none}
.aio-pjn{display:inline-flex;align-items:center;min-width:0}.aio-pjn[hidden]{display:none}
.aio-pjn .pjb,.aio-pjn .pjn{font:inherit;color:var(--ink);background:none;border:0;display:inline-flex;align-items:center;justify-content:center;min-height:40px;cursor:pointer;text-decoration:none;font-weight:800;font-size:16px;border-radius:999px}
.aio-pjn .pjb{min-width:40px;font-size:20px}
.aio-pjn .pjn{gap:6px;padding:0 10px 0 6px;min-width:0;max-width:min(52vw,230px)}.aio-pjn .pjn span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.aio-pjn .pjn i{font-style:normal;color:var(--on);font-size:14px;flex:none}
.aio-pjn .pjb:hover,.aio-pjn .pjn:hover,.aio-pjn .pjb:focus-visible,.aio-pjn .pjn:focus-visible{background:var(--on2);outline:0}
.aio-pjm{position:fixed;z-index:40;background:var(--card);border-radius:18px;box-shadow:var(--sh);padding:6px;min-width:220px;max-width:calc(100vw - 16px);max-height:60dvh;overflow:auto;display:flex;flex-direction:column;gap:2px}
.aio-pjm button,.aio-pjm a{font:inherit;color:var(--ink);background:none;border:0;border-radius:12px;min-height:44px;padding:0 12px;display:flex;align-items:center;justify-content:space-between;gap:10px;cursor:pointer;text-align:left;text-decoration:none;font-size:14px}
.aio-pjm button:hover,.aio-pjm a:hover,.aio-pjm button:focus-visible,.aio-pjm a:focus-visible{background:var(--on2);outline:0}
.aio-pjm em{font-style:normal;font-size:12px;color:var(--sub);flex:none}.aio-pjm .cur{background:var(--on2)}
.aio-pjm .all{border-top:1px solid var(--line);border-radius:0 0 12px 12px;margin-top:4px;color:var(--sub);justify-content:center}
/* 手機：整個膠囊要夠窄（約 170px 內），頂列第一排才放得下「膠囊＋視角＋更多」、第二排放得下「即時＋電力＋績效總表」；按鈕高 44px、寬 34px（名稱字級 14px，過長以…截斷） */
@media (max-width:640px){.ttl.pj{height:44px;padding:0 5px 0 2px;gap:0}.ttl.pj .q{width:34px;height:34px;font-size:15px}.aio-pjn .pjb,.aio-pjn .pjn{min-height:44px}.aio-pjn .pjb{min-width:34px;padding:0}.aio-pjn .pjn{max-width:80px;padding:0 3px 0 2px;gap:2px;font-size:14px}.aio-pjn .pjn i{font-size:11px}}`;
  document.head.append(css);

  // ───────── 頂列標章＋說明框 ─────────
  const bar = $('bar'), badge = document.createElement('button'); badge.className = 'btn aio-b demo'; badge.id = 'aioBadge'; badge.setAttribute('aria-haspopup', 'dialog'); badge.setAttribute('aria-expanded', 'false');
  bar.insertBefore(badge, $('pwBtn') || $('editBtn'));
  const pop = document.createElement('div'); pop.className = 'pop aio-pop'; pop.id = 'aioPop'; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '連接我的 Claude'); $('app').append(pop);
  const placePop = () => { const r = badge.getBoundingClientRect(), w = pop.offsetWidth; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px'; };
  // 還沒接上（或已設碼但沒收到回報）→ 開三步驟引導；已接上或展示模式 → 原本的說明框
  const wantsGuide = () => (L.mode !== 'live' ? !(hasCred() && L.cfg.show) : L.status === 'nodata' || L.status === 'setup');
  badge.onclick = () => { if (wantsGuide()) { pop.hidden = true; badge.setAttribute('aria-expanded', 'false'); openGuide(); return; } const was = pop.hidden; ui.closePops && ui.closePops(); closeLedger(); pop.hidden = !was; badge.setAttribute('aria-expanded', String(was)); if (was) { renderPop(); placePop(); } };
  document.addEventListener('pointerdown', e => { if (!pop.hidden && !e.target.closest('#aioPop') && !e.target.closest('#aioBadge')) { pop.hidden = true; badge.setAttribute('aria-expanded', 'false'); } });
  addEventListener('resize', () => { if (!pop.hidden) placePop(); });

  function badgeState() {
    if (L.mode !== 'live') return hasCred() && L.cfg.show ? ['展示模式', 'demo', '展示模式：目前顯示示範資料，點這裡回到即時', '展示模式'] : ['連接我的 Claude', 'demo', '目前是示範資料：點這裡連接你的 Claude', '連接 Claude'];
    switch (L.status) {
      case 'ok': return [`即時・最後更新 ${hhmm(L.lastOk)}`, 'live', '即時：資料來自你的 Claude', `即時 ${hhmm(L.lastOk)}`];
      case 'nodata': return ['即時・尚未收到回報', 'live warn', '已連上，但還沒收到你的 Claude 送來的任何消息', '尚未收到回報'];
      case 'error': return ['即時・連不上，重試中', 'live bad', '辦公室暫時連不上收件端，正在重試', '連不上'];
      case 'auth': return ['接入碼失效', 'live bad', '這組接入碼失效了，請重新取得', '接入碼失效'];
      case 'setup': return ['即時・尚未設定', 'live warn', '還缺收件端網址或接入碼', '尚未設定'];
      default: return ['即時・連線中…', 'live', '正在連線', '連線中'];
    }
  }
  function render() {
    const [t, cls, aria, ts] = badgeState();
    const hint = !hasCred() || (L.mode === 'live' && (L.status === 'nodata' || L.status === 'setup'));   // 尚未接上：頂列加醒目小點，接上後消失
    badge.className = 'btn aio-b ' + cls + (hint ? ' hint' : ''); badge.innerHTML = `<i class="dot" aria-hidden="true"></i><span id="aioTxt" class="l">${esc(t)}</span><span class="s" aria-hidden="true">${esc(ts)}</span>`; badge.setAttribute('aria-label', aria); badge.title = aria;
    document.body.classList.toggle('aio-live', L.mode === 'live');
    renderBrand();
    if (!pop.hidden) { renderPop(); placePop(); }
    if (ledgerEl && !ledgerEl.hidden) renderLedger();
    guideRender();
  }
  L.render = render;

  // 說明框內容：示範時＝「連接我的 Claude」；即時＝狀態、專案、工作階段、展示模式、中斷連接
  // ───────── 專案名稱：名牌、門牌、左上角「← 專案名 ▾」 ─────────
  // 名牌文字由 main.js 的 setTag 問 W.tagName；只有 CEO 與分身加專案名，其他同事不動。
  // 名牌用「任務簡稱」（Claude 開工時自己取的 6～12 字，外掛 set_task_name.py 送來的 task_name）：同一專案的多個工作階段各用各的簡稱；
  // 沒有簡稱就退回專案名（projname.js 規則，專案名沒意義時是「雲端工作階段」）。超過 12 字用「…」截斷，免得名牌塞不下。
  function taskOf(sid) { const s = sid && L.data && L.data.sessions && L.data.sessions.find(x => x.id === sid); const t = s && typeof s.task_name === 'string' ? s.task_name.replace(/\s+/g, ' ').trim() : ''; return t || null; }
  function nameOfSid(sid) { return AP.trunc(taskOf(sid) || L.projName || '', 12); }
  W.tagName = c => {
    if (L.mode !== 'live' || !L.projName || !c || !c.spec) return null;
    const sp = c.spec, clone = L.clones.find(x => x.ch === c);
    if (!(sp.isCeo || clone || /^ceo-clone-/.test(sp.id || ''))) return null;
    return nameOfSid(clone ? clone.sid : L.primary) + ' ' + sp.nick;
  }
  // 名牌用到的簡稱有變（換了工作階段、Claude 剛取好簡稱）就重畫；用簽名比對，沒變就不動
  function nameSig() { return [L.primary, ...L.clones.map(x => x.sid)].map(id => id ? id + '=' + (taskOf(id) || '') : '').join('|'); }
  function refreshNames() { const sg = nameSig(); if (sg === L._nameSig) return; L._nameSig = sg; applyProjectNames(); }
  function retitleSign() {
    if (!W.scene) return;
    const want = L.mode === 'live' && L.projName ? nameOfSid(L.primary) + ' CEO 辦公室' : 'CEO 辦公室';
    W.scene.traverse(o => {
      if (!(o.userData && o.userData.roomText === 'CEO 辦公室' && o.material)) return;
      if (o.userData.signNow === want) return; o.userData.signNow = want;
      const old = o.material.map, pw = 768, w = o.userData.roomW || 2.16;
      o.material.map = textTexture(want, { pw, ph: Math.round(pw * 0.42 / w), bg: '#fffaf2', px: 140, radius: 72 }); o.material.needsUpdate = true;
      if (old && old.dispose && old !== o.material.map) old.dispose();
    });
  }
  function applyProjectNames() {
    if (W.setTag) for (const c of [C('ceo'), ...L.clones.map(x => x.ch)]) if (c && c._lab) { try { W.setTag(c); } catch (e) { /* 名牌重畫失敗不影響其他 */ } }
    retitleSign(); renderBrand();
    try { document.title = L.mode === 'live' && L.projName ? L.projName + '・AI 辦公室' : 'AI 辦公室'; } catch (e) { /* 略 */ }
  }
  L.applyProjectNames = applyProjectNames;
  // 切換專案＝重新載入頁面（網址換 project）：場景、分身、後備座位的同事一次乾淨重來，不會留下上一個專案的角色
  function goProject(h) {
    if (!/^[0-9a-f]{16}$/.test(h || '')) return;
    const u = new URLSearchParams(location.search); u.set('project', h); u.delete('connect');
    location.assign(location.pathname + '?' + u.toString());
  }
  L.goProject = goProject;
  const ttl = bar.querySelector('.ttl'), brandA = ttl && ttl.querySelector('a'), pjNav = document.createElement('span'); pjNav.className = 'aio-pjn'; pjNav.hidden = true;
  if (ttl) ttl.insertBefore(pjNav, ttl.firstChild);
  let pjMenu = null;
  const closePjMenu = () => { if (pjMenu) { pjMenu.remove(); pjMenu = null; } const b = pjNav.querySelector('.pjn'); if (b) b.setAttribute('aria-expanded', 'false'); };
  function backHref() { return 'index.html?office=' + encodeURIComponent(L.qOffice || 'main') + '#pick'; }
  function renderBrand() {
    const on = !!(ttl && L.mode === 'live' && L.project && L.projName), sig = on ? L.projName + '|' + L.qOffice : '';
    if (pjNav._sig === sig) return; pjNav._sig = sig; closePjMenu();
    pjNav.hidden = !on; ttl && ttl.classList.toggle('pj', on); if (brandA) brandA.hidden = on;
    if (!on) { pjNav.textContent = ''; return; }
    pjNav.innerHTML = `<a class="pjb" href="${esc(backHref())}" aria-label="回專案清單" title="回專案清單">←</a><button class="pjn" type="button" aria-haspopup="listbox" aria-expanded="false" aria-label="目前專案：${esc(L.projName)}，按一下切換專案"><span>${esc(AP.trunc(L.projName, 14))}</span><i aria-hidden="true">▾</i></button>`;
  }
  function openPjMenu(btn) {
    closePjMenu();
    const ps = (L.data && L.data.projects) || [], m = document.createElement('div'); m.className = 'aio-pjm'; m.setAttribute('role', 'listbox'); m.setAttribute('aria-label', '切換專案');
    m.innerHTML = (ps.length ? ps : [{ hash: L.project, name: L.projName, active: 0 }]).map(p => { const nm = AP.label(p.name), cur = p.hash === L.project; return `<button type="button" role="option" aria-selected="${cur}" data-h="${esc(p.hash)}" class="${cur ? 'cur' : ''}"><b>${cur ? '✓ ' : ''}${esc(AP.trunc(nm, 18))}</b><em>${p.active ? p.active + ' 個進行中' : AP.ago(p.last)}</em></button>`; }).join('') + `<a class="all" href="${esc(backHref())}">看全部專案</a>`;
    document.body.append(m); pjMenu = m; btn.setAttribute('aria-expanded', 'true');
    const r = btn.getBoundingClientRect(); m.style.top = (r.bottom + 8) + 'px'; m.style.left = Math.max(8, Math.min(innerWidth - m.offsetWidth - 8, r.left)) + 'px';
    const f = m.querySelector('.cur,button'); if (f) f.focus({ preventScroll: true });
  }
  pjNav.addEventListener('click', e => { const b = e.target.closest('.pjn'); if (!b) return; if (pjMenu) closePjMenu(); else { ui.closePops && ui.closePops(); openPjMenu(b); } });
  document.addEventListener('click', e => { if (!pjMenu) return; const o = e.target.closest('.aio-pjm button[data-h]'); if (o) { const h = o.dataset.h; if (h === L.project) closePjMenu(); else goProject(h); return; } if (!e.target.closest('.aio-pjm') && !e.target.closest('.pjn')) closePjMenu(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && pjMenu) { const b = pjNav.querySelector('.pjn'); closePjMenu(); if (b) b.focus(); } });
  addEventListener('resize', closePjMenu);

  function sessionsOfProject() { const d = L.data; return d ? d.sessions.filter(s => !L.project || s.project_hash === L.project) : []; }
  function renderPop() {
    const owner = !!loginTok(), d = L.data;
    let h = '';
    if (L.mode === 'live') {
      const [t] = badgeState();
      h += `<h4>即時模式</h4><p class="st" id="aioSt">${esc(t)}</p>`;
      if (L.status === 'nodata') h += '<p>還沒收到你的 Claude 送來的消息。在 Claude 開一個工作（例如請它派一位子 Agent 做件小事），15 秒內這裡會更新。</p>';
      if (L.status === 'auth') h += '<p>收件端不認得這組接入碼（可能已換新）。請重新產生或重新輸入。</p>';
      if (L.status === 'error') h += `<p>連不上收件端（${esc(L.msg || '網路問題')}）。會自動重試，間隔越來越長。</p>`;
      if (L.status === 'setup') h += '<p>還缺收件端網址或接入碼，請到下方「進階」填寫，或先中斷連接重新設定。</p>';
      if (d && d.last_event_at) h += `<p>最後一次收到消息：${hhmm(d.last_event_at)}（台北）・共 ${d.total_events} 筆</p>`;
      if (d && d.projects.length) {
        h += d.projects.length > 1 ? `<label for="aioProj">專案</label><div class="row"><select id="aioProj">${d.projects.map(p => `<option value="${esc(p.hash)}" ${p.hash === L.project ? 'selected' : ''}>${esc(p.name || '未命名專案')}</option>`).join('')}</select></div>` : `<p>專案：<b>${esc(d.projects[0].name || '未命名專案')}</b></p>`;
        const ss = sessionsOfProject();
        if (ss.length) {
          const ci = new Map(L.clones.map((c, i) => [c.sid, i]));
          h += `<ul aria-label="工作階段">${ss.slice(0, 8).map(s => { const who = s.id === L.primary ? 'CEO' : ci.has(s.id) ? `CEO（分身 ${ci.get(s.id) + 2}）` : 'CEO'; const st = s.ended ? '已結束' : s.flag === 'permission' ? '等你核准' : s.flag === 'question' ? '等你回答' : SESS_TEXT[s.state] || '待命中'; return `<li><b>${esc(taskOf(s.id) ? nameOfSid(s.id) + ' ' + who : who)}</b><span>${esc(st)}・${s.cloud ? '雲端' : s.cloud === false ? '本機' : ''}</span><em>${hhmm(s.last)}</em></li>`; }).join('')}</ul>`;
          if (L.more) h += `<p>另外還有 ${L.more} 個工作階段同時開著（畫面最多放 3 位分身）。</p>`;
        }
      }
      h += `<div class="row"><button class="btn" data-a="now">立即更新</button><button class="btn" data-a="show">展示模式</button><button class="btn" data-a="off">中斷連接</button></div><div class="row"><button class="btn" data-a="guide">接入引導</button><button class="btn" data-a="rotate" title="接入碼貼錯地方或外流了，產生新的，舊的立刻失效">我不小心外流了，換一組</button></div>`;
      h += `<details><summary>進階</summary><label for="aioUrl">收件端網址</label><div class="row"><input id="aioUrl" value="${esc(L.cfg.url || L.url || '')}" placeholder="https://tw-ai-office-bridge.….workers.dev"><button class="btn" data-a="url">儲存</button></div>${owner ? '<div class="row"><button class="btn" data-a="wipe">刪除所有紀錄</button></div>' : ''}</details>`;
    } else {
      h += `<h4>連接我的 Claude</h4><p>接好之後，辦公室顯示的是你自己的 Claude 真正在做的事；現在看到的是示範資料。</p><div class="row"><button class="btn on" data-a="guide">打開接入引導</button></div>`;
      if (hasCred() && L.cfg.show) h += `<div class="row"><button class="btn on" data-a="back">回到即時模式</button></div>`;
    }
    if (L.msg2) h += `<p class="st" role="status">${esc(L.msg2)}</p>`;
    if (h !== pop._html) { pop._html = h; pop.innerHTML = h; }
    guideRender();
  }
  pop.addEventListener('change', e => { if (e.target.id === 'aioProj') goProject(e.target.value); });
  pop.addEventListener('click', async e => {
    const b = e.target.closest('[data-a]'); if (!b) return; const a = b.dataset.a; L.msg2 = '';
    if (a === 'guide') { pop.hidden = true; badge.setAttribute('aria-expanded', 'false'); openGuide(); return; }
    if (a === 'code') { const v = ($('aioIn').value || '').trim(); if (!/^[A-Za-z0-9_-]{8,200}$/.test(v)) { L.msg2 = '接入碼格式不對（應該是 aio_ 開頭的一串英數字）'; renderPop(); return; } L.code = v; L.cfg = { ...L.cfg, office: 'main', login: !!loginTok() }; delete L.cfg.show; save(); enterLive(); return; }
    if (a === 'login') { L.cfg = { ...L.cfg, login: true, office: 'main' }; L.code = null; delete L.cfg.show; save(); enterLive(); return; }
    if (a === 'url') { const v = ($('aioUrl').value || '').trim().replace(/\/+$/, ''); if (v && !/^https?:\/\/[^\s]+$/.test(v)) { L.msg2 = '網址格式不對'; renderPop(); return; } if (v) L.cfg.url = v; else delete L.cfg.url; save(); L.msg2 = '已儲存'; if (L.mode === 'live') restartLive(); else renderPop(); return; }
    if (a === 'rotate') { pop.hidden = true; badge.setAttribute('aria-expanded', 'false'); openGuide(); await claim(true); return; }
    if (a === 'wipe') { if (!confirm('要刪除這間辦公室收到的所有紀錄嗎？（接入碼保留）')) return; await wipe(); return; }
    if (a === 'now') { poll(); return; }
    if (a === 'show') { L.cfg.show = true; save(); if (W.rosterHub && W.rosterHub.on) { location.assign(location.pathname + '?demo=1'); return; } enterDemo(); return; }   // 專案辦公室收起了示範同事：切到展示模式要整頁重載才會是完整的示範編制
    if (a === 'back') { delete L.cfg.show; save(); enterLive(); return; }
    if (a === 'off') { L.cfg = {}; L.code = null; save(); L.revealCode = null; enterDemo(); return; }
  });

  // 功能閘門（features.js 的 office.connect）：每產生一組接入碼（含換一組）算一次；用完就不再產生新的，已接好的連線與觀看不受影響。成功拿到新碼才扣次數。
  async function claim(rotate) {
    const gt = W.gate ? await W.gate.begin('office.connect') : null;
    if (gt && !gt.pass) { L.msg2 = gt.note; renderPop(); return; }
    let got = false;     // 拿到新接入碼的那一刻就扣次數（enterLive 之後的連線等待很慢，不能等它）
    try { await claimRaw(rotate, () => { got = true; if (gt) gt.done(); }); } finally { if (gt && !got) gt.cancel(); }
  }
  async function claimRaw(rotate, onGot) {
    const url = await resolveUrl(), t = loginTok();
    if (!url) { L.msg2 = '還不知道收件端網址：請到「進階」填寫'; renderPop(); return; }
    try {
      const r = await fetch(url + '/v1/claim', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ t, rotate: !!rotate }), credentials: 'omit' });
      const j = await r.json().catch(() => ({}));
      if (r.status === 403) { if (j.error === 'not_owner') L.guide.owner = 'notowner'; L.msg2 = j.error === 'not_owner' ? '這個帳號不是站長，不能產生接入碼' : '這個網站沒有被允許'; renderPop(); return; }
      if (r.status === 503) { L.msg2 = '會員登入服務還沒接上收件端，暫時不能產生接入碼'; renderPop(); return; }
      if (!r.ok) { L.msg2 = '產生失敗（' + r.status + '），請稍後再試'; renderPop(); return; }
      if (j.exists && !j.code) { L.guide.codeExists = true; L.guide.owner = 'owner'; L.msg2 = '已經產生過接入碼，但接入碼只會顯示一次、這台裝置沒有存。請按「換一組」產生新的（舊的會失效）'; L.cfg = { ...L.cfg, login: true, office: j.office || 'main' }; delete L.cfg.show; save(); enterLive(); return; }
      L.revealCode = j.code; L.code = j.code; L.cfg = { ...L.cfg, office: j.office || 'main', login: true }; delete L.cfg.show; save(); if (onGot) onGot();   // 領碼的一定是登入中的站長：關掉視窗後碼就清掉、觀看改用登入身分
      Object.assign(L.guide, { owner: 'owner', base: null, eye: false, codeExists: true, copied: '' });
      if (L.mode === 'live') restartLive(); else enterLive();
    } catch (x) { L.msg2 = '連不上收件端，請稍後再試'; renderPop(); }
  }
  async function wipe() {
    const url = await resolveUrl();
    try { const r = await fetch(`${url}/v1/office/${encodeURIComponent(L.cfg.office || 'main')}/wipe`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ t: loginTok() }), credentials: 'omit' }); L.msg2 = r.ok ? '已刪除所有紀錄' : '刪除失敗（' + r.status + '）'; if (r.ok) restartLive(); else renderPop(); }
    catch (x) { L.msg2 = '連不上收件端'; renderPop(); }
  }


  // ───────── 接入引導（三步驟面板；桌機置中對話框、手機全螢幕） ─────────
  // 步驟 1 複製提示詞（不含接入碼）貼到 Claude → 2 Claude 跳出安全表單卡片時貼上接入碼 → 3 等第一筆事件，收到就顯示「已接上」。
  const G = L.guide, gEl = document.createElement('div');
  gEl.className = 'aio-g'; gEl.id = 'aioGuide'; gEl.hidden = true;
  gEl.innerHTML = '<div class="aio-gbk" data-a="gclose"></div><section class="aio-gp" role="dialog" aria-modal="true" aria-labelledby="aioGt" tabindex="-1"><header><h3 id="aioGt">連接我的 Claude</h3><button class="aio-gx" data-a="gclose" aria-label="關閉">×</button></header><div class="aio-gbody" id="aioGb"></div></section>';
  document.body.append(gEl);
  const promptText = () => { const u = L.cfg.url || L.url || '', host = u.replace(/^https?:\/\//, '').replace(/\/.*$/, ''); return host ? GUIDE_PROMPT.replace(/\{HOST\}/g, host) : ''; };
  const maskCode = c => (c ? c.slice(0, 7) + '…（已隱藏）' : '');
  const shotsHtml = n => (GUIDE_SHOTS[n] || []).map(x => `<figure class="aio-shot" data-shot="${esc(x.file)}">${x.ready ? `<img src="guide/shots/${esc(x.file)}" alt="${esc(x.alt)}">` : `<div class="ph" role="img" aria-label="${esc(x.alt)}">操作圖片將於實測後補上</div>`}<figcaption>${esc(x.alt)}</figcaption></figure>`).join('');
  async function checkOwner() {
    if (G.owner !== 'unknown' && G.owner !== 'nologin') return;
    const tok = loginTok(); if (!tok) { G.owner = 'nologin'; guideRender(); return; }
    if (!window.TW_ACCOUNT) await loadScript('../account_config.js');
    const api = window.TW_ACCOUNT && window.TW_ACCOUNT.api;
    if (!api) { G.owner = 'unknown'; return; }                      // 查不到就先當作可以試，真的不是站長時 claim 會回 403
    try {
      const r = await fetch(api.replace(/\/+$/, '') + '/v1/me', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ t: tok }), credentials: 'omit' });
      if (r.ok) { const j = await r.json(); G.owner = j && j.user && j.user.admin ? 'owner' : 'notowner'; }
    } catch (x) { /* 略：維持 unknown */ }
    guideRender();
  }
  function openGuide() {
    G.open = true; G.eye = false; G.done = false; G.base = null; G.sig = ''; G.fix = false;
    if (L.code && G.owner === 'nologin') G.owner = 'unknown';
    gEl.hidden = false; badge.setAttribute('aria-expanded', 'false');
    resolveUrl().then(() => { guideRender(); }); guideRender(); checkOwner();
    const p = gEl.querySelector('.aio-gp'); p && p.focus({ preventScroll: true });
    if (L.mode === 'live') { clearTimeout(L.timer); poll(); }
  }
  function closeGuide() {
    G.open = false; gEl.hidden = true; clearTimeout(G.t);
    if (L.code && loginTok()) { L.cfg.login = true; save(); L.code = null; L.revealCode = null; G.copied = ''; if (L.mode === 'live') { clearTimeout(L.timer); poll(); } }   // 碼只在視窗開著時存在
 try { badge.focus({ preventScroll: true }); } catch (x) { /* 略 */ } }
  L.openGuide = openGuide; L.closeGuide = closeGuide;
  // 一個畫面、兩個動作：① 複製提示詞貼到 Claude　② Claude 跳出表單時貼接入碼（沒有就自動產生、一律遮罩）；底下一行狀態，收到第一筆事件就「已接上」
  const shotHtml = n => { const x = GUIDE_SHOTS[n]; return x.ready ? `<figure class="aio-shot" data-shot="${esc(x.file)}"><img src="guide/shots/${esc(x.file)}" alt="${esc(x.alt)}"></figure>` : `<p class="aio-cap" data-shot="${esc(x.file)}">${esc(x.alt)}</p>`; };
  function guideRender(force) {
    if (!G.open) return;
    const code = L.code || '', pr = promptText();
    const sig = JSON.stringify([!!code, G.owner, G.done, L.status, L.mode, L.msg2, G.copied, !!pr, G.showPrompt, G.fix, L.msg, L.data && L.data.total_events, G.busy]);
    if (!force && sig === G.sig) return; G.sig = sig;
    const ae = document.activeElement, keep = ae && gEl.contains(ae) && ae.tagName === 'INPUT' ? { id: ae.id, v: ae.value } : null;
    const blocked = !code && (G.owner === 'notowner' || G.owner === 'nologin');
    let h = '<div class="aio-cards">';
    h += `<section class="aio-card" id="aioC1"><h4>① 複製這段，貼到 Claude</h4><p>貼進 Claude 的對話框送出（裡面沒有接入碼）。</p>
      <div class="aio-row"><button class="btn big" data-a="cpprompt" ${pr ? '' : 'disabled'}>複製提示詞</button><a class="aio-lk" href="https://claude.ai/code" target="_blank" rel="noopener">打開 Claude</a></div>
      ${G.copied === 'prompt' ? '<p class="aio-msg" role="status">已複製，到 Claude 貼上送出。</p>' : G.copied === 'promptsel' ? '<p class="aio-msg" role="status">已選取全文，請按 Ctrl+C（手機長按）複製。</p>' : ''}
      ${pr ? `<button class="aio-lk" data-a="viewp" aria-expanded="${!!G.showPrompt}">${G.showPrompt ? '收起內容' : '看內容'}</button>` : '<p class="aio-msg">還不知道收件端網址，請展開下方「遇到問題？」填寫。</p>'}
      ${G.showPrompt && pr ? `<pre class="aio-prompt" id="aioPrompt" tabindex="0" aria-label="接入提示詞（可捲動）">${esc(pr)}</pre>` : ''}${shotHtml(1)}</section>`;
    h += `<section class="aio-card" id="aioC2"><h4>② Claude 跳出表單時，貼這個</h4>`;
    if (blocked) h += `<div class="aio-box lock" role="status">目前只開放站長使用</div>${G.owner === 'nologin' ? '<p>站長請先回<a href="../index.html">網站首頁</a>用 Google 登入。</p>' : ''}`;
    else h += `<p>貼進表單的「值」那一格，按儲存；不要貼在聊天室。</p>
      <div class="aio-row">${code ? `<code class="aio-mask" id="aioCodeMask" aria-label="接入碼（已隱藏）">${esc(maskCode(code))}</code>` : ''}<button class="btn big" data-a="cpcode" ${G.busy ? 'disabled' : ''}>複製接入碼</button></div>
      ${G.copied === 'code' ? '<p class="aio-msg" role="status">已複製，貼進 Claude 的表單就好。</p>' : G.copied === 'codesel' ? '<p class="aio-msg" role="status">接入碼已產生，請再按一次「複製接入碼」。</p>' : ''}
      ${!code && G.owner === 'owner' && G.codeExists ? '<p class="aio-msg">接入碼只在產生的當下顯示一次，這個網頁不會保存。再按一次「複製接入碼」會換一組新的（舊的失效）。</p>' : ''}${code || G.owner === 'owner' ? '<button class="aio-lk warnlk" data-a="rotate">不小心外流？換一組</button>' : ''}${shotHtml(2)}`;
    h += '</section></div>';
    h += G.done ? '<div class="aio-box ok" role="status" id="aioStat">已接上 ✓，你的辦公室正在即時更新</div>'
      : `<div class="aio-wait" role="status" id="aioStat"><i aria-hidden="true"></i>等待你的 Claude 回報…</div>${L.status === 'error' ? `<p class="aio-msg">暫時連不上收件端（${esc(L.msg || '網路問題')}），會自動重試。</p>` : ''}${L.status === 'auth' ? '<p class="aio-msg">收件端不認得這組接入碼，請按「不小心外流？換一組」。</p>' : ''}`;
    if (L.msg2) h += `<p class="aio-msg" role="status">${esc(L.msg2)}</p>`;
    h += `<details id="aioHelp" ${G.fix ? 'open' : ''}><summary>遇到問題？</summary><ol class="fix" id="aioFix"><li>Claude 的表單卡片按過「儲存」了嗎？沒有的話再按一次「複製接入碼」貼上。</li><li>Claude 請你核准設定腳本時，有按「同意」嗎？沒有就請它再提出一次。</li><li>設定腳本只在「新的」雲端工作階段生效：開一個新的工作階段，隨便交代一件小事。</li><li>請 Claude 回報測試事件結果；回應不是 "ok":true 就把原文告訴它。</li><li>接入碼貼在聊天室或貼錯：按②的「不小心外流？換一組」。</li></ol>
      <label for="aioUrl">收件端網址（通常不用填）</label><div class="aio-row"><input id="aioUrl" value="${esc(L.cfg.url || L.url || '')}" placeholder="https://tw-ai-office-bridge.….workers.dev"><button class="btn" data-a="url">儲存</button></div><label for="aioIn">已經有接入碼</label><div class="aio-row"><input id="aioIn" autocomplete="off" spellcheck="false" placeholder="aio_…"><button class="btn" data-a="code">連接</button></div><button class="btn" data-a="now">立即檢查</button></details>`;
    const body = $('aioGb'), top = body.scrollTop;
    body.innerHTML = h; body.scrollTop = top;
    if (keep && keep.id) { const e2 = $(keep.id); if (e2) { e2.value = keep.v; try { e2.focus({ preventScroll: true }); } catch (x) { /* 略 */ } } }
  }
  async function copyText(text, sel) {
    try { await navigator.clipboard.writeText(text); return true; } catch (x) { /* 退而求其次：選取文字讓使用者自己複製 */ }
    if (sel) { const r = document.createRange(); r.selectNodeContents(sel); const g = getSelection(); g.removeAllRanges(); g.addRange(r); }
    return false;
  }
  gEl.addEventListener('toggle', e => { if (e.target.id === 'aioHelp') G.fix = e.target.open; }, true);
  gEl.addEventListener('click', async e => {
    const b = e.target.closest('[data-a]'); if (!b) return; const a = b.dataset.a; L.msg2 = '';
    if (a === 'gclose') { closeGuide(); return; }
    if (a === 'viewp') { G.showPrompt = !G.showPrompt; guideRender(true); return; }
    if (a === 'cpprompt') { if (!G.showPrompt) { G.showPrompt = true; guideRender(true); } G.copied = (await copyText(promptText(), $('aioPrompt'))) ? 'prompt' : 'promptsel'; G.showPrompt = G.copied === 'promptsel'; guideRender(true); return; }
    if (a === 'cpcode') {
      if (!L.code) {                                                  // 還沒有碼：自動產生（領過但這台沒存＝直接換新的，使用者不用多按一步）
        G.busy = true; guideRender(true); await claim(false);
        if (!L.code && G.codeExists && L.guide.owner === 'owner') { L.msg2 = ''; await claim(true); }
        G.busy = false;
      }
      if (L.code) G.copied = (await copyText(L.code, null)) ? 'code' : 'codesel';
      guideRender(true); return;
    }
    if (a === 'rotate') { G.busy = true; guideRender(true); await claim(true); G.busy = false; G.copied = ''; guideRender(true); return; }
    if (a === 'now') { poll(); return; }
    if (a === 'url') { const v = ($('aioUrl').value || '').trim().replace(/\/+$/, ''); if (v && !/^https?:\/\/[^\s]+$/.test(v)) { L.msg2 = '網址格式不對'; guideRender(true); return; } if (v) L.cfg.url = v; else delete L.cfg.url; save(); L.msg2 = '已儲存'; if (L.mode === 'live') restartLive(); guideRender(true); return; }
    if (a === 'code') { const v = ($('aioIn').value || '').trim(); if (!/^[A-Za-z0-9_-]{8,200}$/.test(v)) { L.msg2 = '接入碼格式不對（應該是 aio_ 開頭的一串英數字）'; guideRender(true); return; } L.code = v; L.cfg = { ...L.cfg, office: 'main', login: !!loginTok() }; delete L.cfg.show; save(); Object.assign(G, { base: null, copied: '' }); enterLive(); guideRender(true); return; }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && G.open) { e.stopPropagation(); closeGuide(); } }, true);
  // 收到第一筆事件（比打開引導時多）就算接上：顯示成功、2.5 秒後自動關閉，辦公室本來就已經是即時模式
  function guideCheck(j) {
    if (!G.open) return;
    const n = claudeEvents(j);
    if (G.base == null) { G.base = n; return; }
    if (n > G.base && !G.done) {
      G.done = true; guideRender(true); ui.toast('已接上 Claude，辦公室正在即時更新');
      clearTimeout(G.t); G.t = setTimeout(() => { if (G.done) closeGuide(); }, 2500);
    }
  }
  const guideFast = () => G.open && !G.done;

  // ───────── 示範資料的開關：即時模式下把示範數字全部換掉 ─────────
  const rwBtn = $('rwBtn');
  const orig = { showCard: ui.showCard, adjust: W.hr && W.hr.adjust, rwClick: rwBtn && rwBtn.onclick, rwHidden: rwBtn && rwBtn.hidden,
    gradeOf: R && R.gradeOf, cardBlock: R && R.cardBlock, openLedger: R && R.openLedger };
  function patchCard() {
    const m = document.querySelector('#card .meta'); if (!m) return;
    m.innerHTML = '<dt>資料來源</dt><dd>即時：你的 Claude 回報的事件</dd><dt>預估完成</dt><dd>未提供（即時模式不推估）</dd>';
  }
  function patchDemo(on) {
    if (on) {
      if (R && R.on) { R.gradeOf = () => null; R.cardBlock = liveCardBlock; R.openLedger = () => openLedger(); if (R.refreshTags) R.refreshTags(); if (R.marks) R.marks.visible = false; if (R.ledger && R.ledger.close) R.ledger.close(); }
      if (W.hr && orig.adjust) W.hr.adjust = (spec, base) => orig.adjust(spec, { ...EMPTY_BASE, list: [] });
      ui.showCard = c => { orig.showCard(c); patchCard(c); };
      if (rwBtn) { rwBtn.hidden = false; rwBtn.onclick = () => (ledgerEl && !ledgerEl.hidden ? closeLedger() : openLedger()); }
    } else {
      if (R && R.on) { R.gradeOf = orig.gradeOf; R.cardBlock = orig.cardBlock; R.openLedger = orig.openLedger; if (R.refreshTags) R.refreshTags(); if (R.marks) R.marks.visible = true; }
      if (W.hr && orig.adjust) W.hr.adjust = orig.adjust;
      ui.showCard = orig.showCard;
      if (rwBtn) { rwBtn.onclick = orig.rwClick; rwBtn.hidden = orig.rwHidden; }
      closeLedger();
    }
    if (ui.refreshCard) ui.refreshCard();
  }

  // ───────── 狀態層歸零（切換模式時，不讓示範的狀態混進真資料，反之亦然） ─────────
  function resetState() {
    if (S.q.exhausted) S.emit({ hook_event_name: 'QuotaRecovered', source: 'reset' });
    Object.assign(S.q, { five: null, week: null, provided: false, exhausted: false, resetsAt: null, asOf: null });
    S.agents.clear(); S.byAgentId.clear(); S.flags.permission = null; S.flags.question = null; S.seen.clear(); S.log.length = 0;
    Object.assign(S.session, { active: false, startedAt: null, lastEventAt: null, hadEvent: false, forcedUnknown: false }); S.signal = 'ok';
    if (W.power && W.power.refresh) W.power.refresh(true);
    if (W.jobs && W.jobs.flagsChanged) W.jobs.flagsChanged();
    if (W.jobs && W.jobs.statusSync) W.jobs.statusSync();
    L.seq = 0; L.seen.clear(); L.primary = null; L.data = null; L.lastQuota = ''; L.more = 0; L.booted = false;
    for (const c of L.clones) c.ch.setVisible(false); L.clones.forEach(c => { c.sid = null; });
    if (W.toolanim) W.toolanim.reset(); if (W.links) W.links.reset();
  }

  // ───────── 子 Agent 類型 → 同事 ─────────
  function memberFor(type) {
    if (!type) return null;
    if (L.typeMap.has(type)) return L.typeMap.get(type);
    if (W.rosterHub && W.rosterHub.on) return rosterMember(type);
    const c = C(type);
    if (c && !c.spec.isCeo && !c.spec.pet) { L.typeMap.set(type, type); return type; }
    const id = ensureExtra(type);
    if (!id && !L.sharedNoted.has(type)) { L.sharedNoted.add(type); S.say(`座位已滿：「${short(type, 20)}」先由現有同事兼任`); }
    L.typeMap.set(type, id || type); return id || type;
  }
  // 專案辦公室（roster.js）：名冊裡有誰才讓誰露面。示範編制裡同代號的＝那位露面；其他＝新同事（依類型分配部門與座位、必要時加桌）。
  // 第一次讀到名冊（L.booted 還是 false）直接就座；之後才出現的新類型＝報到演出（從大門走進來）。
  const extraId = type => (TO_RE.test(type) && !C(type) && !L.extras.has(type) ? type : 'x-' + String(type).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40));
  // 新專案的 Agent 名牌主名：優先用派工說明（或任務簡稱）的前 8 字中文，都沒有才用類型名縮短（第二行永遠留類型名）。
  // 說明取最近一筆有中文的；英文為主的說明不拿來當名牌（那樣跟類型名一樣看不懂）。
  const CJK = /[\u4e00-\u9fff]/;
  function taskNick(d) {
    d = String(d || '').replace(/\s+/g, ' ').trim(); if (!d || !CJK.test(d)) return '';
    let seg = d.split(/[，,。；;：:（(、—\/|]/)[0].trim() || d;
    const sp = seg.indexOf(' '); if (sp >= 4) seg = seg.slice(0, sp);
    return seg.slice(0, 8);
  }
  function nickFromData(type) {
    const ag = (L.data && L.data.agents) || [];
    for (const a of ag) if (a && a.agent_type === type) { const n = taskNick(a.task || a.description); if (n) return n; }
    const dp = (L.data && L.data.dispatch) || [];
    for (const a of dp) if (a && a.type === type) { const n = taskNick(a.descr || a.description); if (n) return n; }
    return '';
  }
  function rosterMember(type) {
    const hub = W.rosterHub, arrive = !!L.booted, c0 = C(type);
    if (!W.blocks && c0 && !c0.spec.isCeo && !c0.spec.pet) { hub.reveal(type, arrive); L.typeMap.set(type, type); if (arrive) S.say(`新同事報到：${c0.spec.nick}（${short(type, 24)}）`); return type; }
    if (W.blocks && c0 && c0.absent && !c0.spec.isCeo && !c0.spec.pet) hub.purge(type);   // 區塊辦公室：跟示範編制同代號（例如 deployer）的新同事用自己的代號，不借用示範的那位（收件匣的 to 才對得上）
    const id = L.extras.has(type) ? L.extras.get(type) : extraId(type);
    if (C(id)) { L.extras.set(type, id); L.typeMap.set(type, id); return id; }
    const h = hash(type), tn = BUILTIN[type] ? '' : nickFromData(type), [nick, species] = BUILTIN[type] || [tn || short(type.replace(/[-_]+/g, ' '), 8), POOL[h % POOL.length]];
    if (!BUILTIN[type] && !tn) L.fallbackNick.set(id, type);
    const c = hub.hire({ id, nick, zh: type, species, pal: h % 4, hue: 0, acc: ['badge'], accColor: '#ffd28a', title: W.blocks ? (nickFromData(type) || nick) : undefined }, arrive);   // title：區塊辦公室的區塊名稱（任務簡稱優先，沒有才用類型名）
    if (!c) { L.typeMap.set(type, type); return type; }
    L.extras.set(type, id); L.typeMap.set(type, id);
    if (arrive) { S.say(`新同事報到：${nick}（${short(type, 24)}）`); c.emote && c.emote('star', 2); }
    return id;
  }
  // 名冊同步：收件端回來的名冊（.claude/agents 檔名 ∪ 出現過的子 Agent 類型）、目前的子 Agent、近 7 天出現過的類型，全部都該有一位同事
  function syncRoster(j) {
    const ts = new Set();
    for (const r of j.roster || []) if (r && typeof r.type === 'string') ts.add(r.type);
    for (const a of j.agents || []) if (a && typeof a.agent_type === 'string') ts.add(a.agent_type);
    for (const t of j.types || []) if (t && typeof t.agent_type === 'string') ts.add(t.agent_type);
    // 示範編制裡同代號的先露面（各自回自己原本的座位），再安排編制外的新同事：不然新同事會先搶走他們的桌子
    const list = [...ts].slice(0, 50), org = t => { const c = C(t); return c && !c.spec.isCeo && !c.spec.pet ? 0 : 1; };
    list.sort((a, b) => org(a) - org(b));
    for (const t of list) { try { memberFor(t); } catch (x) { console.warn('名冊同步失敗', t, x); } }
    // 先用類型名報到、之後才拿到派工說明的新同事：補改成任務簡稱（只改一次；已有簡稱的不再跳來跳去）
    if (W.blocks) for (const [t, id] of L.extras) { const n = nickFromData(t); if (n) W.blocks.retitle(id, n); }   // 區塊辦公室：之後才拿到派工說明的，區塊名稱補成任務簡稱
    for (const [id, t] of [...L.fallbackNick]) { const n = nickFromData(t); if (n && W.rosterHub && W.rosterHub.rename && W.rosterHub.rename(id, n)) L.fallbackNick.delete(id); }
  }
  function ensureExtra(type) {
    // 角色代號直接用子 Agent 類型本身（例如 tester）：對話框對他下指令時，收件匣的 to 就是這個代號，
    // Claude 端照 to 派給同名的 subagent_type。以前加 x- 前綴，to 變成 x-tester，Claude 找不到這位 Agent（2026-11-15 端到端實測）。
    // 只有名稱不合收件匣格式、或跟現有角色撞名（例如 ceo）時才退回 x- 前綴。
    const id = TO_RE.test(type) && !C(type) && !L.extras.has(type) ? type : 'x-' + String(type).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
    if (L.extras.has(type)) return L.extras.get(type);
    if (C(id)) return id;
    const spot = W.spots.find(q => q.name === 'reserve' && !q.taken);
    if (!spot || !W.addExtra) return null;
    const h = hash(type), [nick, species] = BUILTIN[type] || [short(type.replace(/[-_]+/g, ' '), 8), POOL[h % POOL.length]];
    let c; try { c = W.addExtra({ id, nick, zh: type, dept: 'reserve', species, pal: h % 4, hue: 0, acc: ['badge'], accColor: '#ffd28a' }); } catch (e) { console.warn('新增後備同事失敗', e); return null; }
    W.extras.splice(W.extras.indexOf(c), 1); W.chars.set(id, c);
    W.members.set(id, { id, nick, zh: type, dept: 'reserve', deptName: '後備區（自動新增）' });
    c.busy = false; spot.taken = id; c.spot = spot; c.homeSpot = spot;
    if (spot.seat) { c.sitAt(spot.seat, { instant: true }); c.atDesk = true; c.setAction('type'); c.workAt = W.time + 3; }
    L.extras.set(type, id); S.say(`新同事報到：${nick}（${short(type, 24)}，坐後備座位）`); c.emote && c.emote('star', 2);
    return id;
  }
  const typeLabel = t => (BUILTIN[t] ? BUILTIN[t][0] : (W.members.get(t) || {}).nick || t);

  // ───────── 多個工作階段：本尊＋分身 ─────────
  function clonePlace(i) {
    const s = W.spots.find(q => q.name === 'seat:ceo') || { x: 4, z: 5 }, off = [[-1.7, 1.5], [1.7, 1.5], [0, 2.4]][i] || [0, 2.4];
    const f = W.nav && W.nav.nearestFree ? W.nav.nearestFree(s.x + off[0], s.z + off[1], 14) : null; return f || { x: s.x + off[0], z: s.z + off[1] };
  }
  function syncSessions() {
    const ss = sessionsOfProject(), now = Date.now();
    const active = ss.filter(s => !s.ended && now - (s.last || 0) < 6 * 3600e3);
    // 本尊：原本那位還開著就留著；否則換成最近在動的那個
    const cur = ss.find(s => s.id === L.primary);
    if (!cur || (cur.ended && active.length)) {
      const nxt = active[0] || ss[0];
      if (nxt && nxt.id !== L.primary) { L.primary = nxt.id; if (!nxt.ended) emit('SessionStart', { uid: 'ss:' + nxt.id, ts: nxt.last || now, session_id: nxt.id }); }
    }
    const others = active.filter(s => s.id !== L.primary);
    L.more = Math.max(0, others.length - 3);
    for (let i = 0; i < 3; i++) {
      const s = others[i];
      let cl = L.clones[i];
      if (!s) { if (cl) { cl.ch.setVisible(false); cl.sid = null; } continue; }
      if (!cl && W.addExtra) {
        const base = (W.roster && W.roster.base && W.roster.base.ceo) || {};
        try { const ch = W.addExtra({ ...base, id: 'ceo-clone-' + (i + 2), nick: `CEO（分身 ${i + 2}）`, zh: '同時開著的工作階段', pet: false }); cl = L.clones[i] = { ch, sid: null }; } catch (e) { console.warn('分身建立失敗', e); continue; }
      }
      if (!cl) continue;
      if (cl.sid !== s.id) { const p = clonePlace(i); cl.ch.setVisible(true); cl.ch.standAt(p.x, p.z, Math.PI); cl.ch.setAction('tablet'); cl.sid = s.id; }
      if (s.flag === 'permission' && !cl.ch.emoteSym) cl.ch.emote('shield', 2.4);
      else if (s.flag === 'question' && !cl.ch.emoteSym) cl.ch.emote('question', 2.4);
    }
  }

  // ───────── 事件 → 狀態層 ─────────
  function sessOf(sid) { return L.data && L.data.sessions.find(s => s.id === sid); }
  function agentOf(aid) { return L.data && L.data.agents.find(a => a.agent_id === aid); }
  function startAgent(aid, type, desc, uid, tool) {
    const mid = memberFor(type);
    emit('SubagentStart', { uid, agent_id: aid, agent_type: mid || type, description: desc || typeLabel(type) + ' 的任務', ...(tool && STATE_CATS.has(tool) ? { tool_category: tool } : {}) });
    const a = agentOf(aid), ch = agentChar(aid) || (mid && C(mid));
    if (W.links && ch) W.links.open(aid, sessChar(a && a.session_id), () => agentChar(aid) || ch);
  }
  // 事件屬於哪一位角色：子 Agent＝名冊上的同事；主工作階段＝CEO（本尊）或分身
  function agentChar(aid) { const id = aid && S.byAgentId.get(aid); return id ? C(id) : null; }
  function sessChar(sid) { if (!sid || !L.primary || sid === L.primary) return C('ceo'); const cl = L.clones.find(x => x.sid === sid); return cl ? cl.ch : C('ceo'); }
  function animEvent(e) {
    const T = W.toolanim; if (!T) return;
    const at = Date.now() - Math.max(0, ((L.data && L.data.now) || 0) - (e.rcv || 0));
    if (e.event === 'PreToolUse' && e.tool_category === 'dispatch') { T.set(e.agent_id ? agentChar(e.agent_id) : sessChar(e.session_id), 'dispatch', at); return; }   // 派人＝打電話
    if (e.event === 'SubagentStop') { const ch = agentChar(e.agent_id); if (ch) T.clear(ch); if (W.links) W.links.close(e.agent_id); return; }
    T.onEvent(e, e.agent_id ? agentChar(e.agent_id) : sessChar(e.session_id), at);
  }
  function applyEvent(e) {
    if (L.seen.has(e.seq)) return; L.seen.add(e.seq);
    const ph = e.project_hash || (sessOf(e.session_id) || {}).project_hash;
    if (L.project && ph && ph !== L.project) return;
    const uid = 'e:' + e.seq, ts = e.rcv || Date.now(), sid = e.session_id, cat = e.tool_category;
    const clearFlags = () => { if (S.flags.permission || S.flags.question) emit('NotificationClear', { uid: uid + ':c', ts }); };
    switch (e.event) {
      case 'SessionStart': if (!L.primary || sid === L.primary || (sessOf(L.primary) || {}).ended) { L.primary = sid; emit('SessionStart', { uid, ts, session_id: sid }); } break;
      case 'SessionEnd': if (sid === L.primary) emit('SessionEnd', { uid, ts, session_id: sid }); break;
      case 'UserPromptSubmit': if (!e.prompt_is_system) emit('UserPromptSubmit', { uid, ts, session_id: sid }); break;
      case 'PreToolUse':
        if (cat === 'dispatch') break;
        if (cat === 'ask') { emit('Notification', { uid, ts, notification_type: 'elicitation_dialog' }); break; }
        clearFlags();
        if (e.agent_id && !S.byAgentId.has(e.agent_id)) { const a = agentOf(e.agent_id); if (!a || a.status === 'running') startAgent(e.agent_id, e.agent_type || (a && a.agent_type), a && a.description, uid + ':s', cat); }
        emit('PreToolUse', { uid, ts, tool_category: STATE_CATS.has(cat) ? cat : 'other', ...(e.agent_id ? { agent_id: e.agent_id } : {}) });
        break;
      case 'PostToolUse': if (cat === 'answered') emit('NotificationClear', { uid, ts, kinds: ['question'] }); break;
      case 'SubagentStart': { const a = agentOf(e.agent_id); startAgent(e.agent_id, e.agent_type, (a && a.description) || e.description, uid); break; }
      case 'SubagentStop': {
        const mid = memberFor(e.agent_type), a = agentOf(e.agent_id);
        if (!S.byAgentId.has(e.agent_id)) startAgent(e.agent_id, e.agent_type, a && a.description, uid + ':s');
        emit('SubagentStop', { uid, ts, agent_id: e.agent_id, agent_type: mid || e.agent_type, status: isFail(e.summary) ? 'failed' : 'completed', last_assistant_message: e.summary || '做完了' });
        break;
      }
      case 'PermissionRequest': emit('Notification', { uid, ts, notification_type: 'permission_prompt', category: e.perm_category || 'other' }); break;
      case 'Notification':
        if (e.notification_type === 'permission_prompt') emit('Notification', { uid, ts, notification_type: 'permission_prompt', category: 'other' });
        else if (e.notification_type === 'elicitation_dialog') emit('Notification', { uid, ts, notification_type: 'elicitation_dialog' });
        break;
      case 'Stop': {
        clearFlags();
        if (sid === L.primary || !L.primary) { S.say('CEO 做完了，輪到你' + (e.summary ? '：' + short(e.summary, 30) : '')); const ceo = C('ceo'); if (ceo && !ceo.piloted && !ceo.sleeping) ceo.emote('star', 1.2); }
        break;
      }
      case 'StopFailure':
        if (/rate|limit|quota|usage|overload|billing/i.test(e.error_type || '')) emit('rate_limit_event', { uid, ts, status: 'rejected' });
        else S.say('CEO 遇到錯誤，這一輪先停下來');
        break;
      case 'PreCompact': S.say('CEO 整理了一下記憶'); break;
    }
    try { animEvent(e); } catch (x) { console.warn('動作圖示處理失敗', x); }
  }
  // 「Claude 真的送來的事件」數：只算掛鉤事件（各專案的事件數加總）。total_events 還含收件匣的 InboxUpdate——
  // 站長在對話框送出／撤回指令也會寫一筆，若拿它判斷，Claude 根本沒接上時頂列就變「即時」、接入引導就誤報「已接上」（2026-11-15 端到端實測抓到）。
  const claudeEvents = j => (j.projects || []).reduce((a, p) => a + (p.events || 0), 0);
  function applySnapshot(j) {
    const inP = x => !L.project || x.project_hash === L.project;
    syncSessions();
    const p = sessOf(L.primary);
    if (p && !p.ended) { if (p.flag === 'permission') emit('Notification', { uid: 'sf:' + p.id, notification_type: 'permission_prompt', category: p.perm || 'other' }); else if (p.flag === 'question') emit('Notification', { uid: 'sf:' + p.id, notification_type: 'elicitation_dialog' }); }
    const ag = j.agents.filter(inP);
    for (const a of ag.filter(x => x.status === 'done' || x.status === 'failed').reverse()) {     // 已交件的：只記進資訊卡，不重演
      const mid = memberFor(a.agent_type); if (!mid || !C(mid)) continue; const st = S.agent(mid);
      if (a.status === 'done') st.done.unshift({ title: a.description || typeLabel(a.agent_type) + ' 的任務', t: a.ended || a.last, summary: a.summary || '' }); else st.failed++;
    }
    const run = ag.filter(x => x.status === 'running');
    run.slice(0, 12).forEach(a => startAgent(a.agent_id, a.agent_type, a.description, 'as:' + a.agent_id, a.tool));
    if (W.toolanim) {   // 連上之前就在做的事：依收件服務記的最近工具類別與時間補上圖示（已過閒置時間的不補）
      const loc = t => Date.now() - Math.max(0, (j.now || 0) - (t || 0)), fresh = t => t && (j.now || 0) - t < W.toolanim.idleMs;
      for (const s of sessionsOfProject()) if (!s.ended && s.tool && fresh(s.tool_at)) W.toolanim.set(sessChar(s.id), s.tool, loc(s.tool_at));
      for (const a of run.slice(0, 12)) if (a.tool && fresh(a.tool_at)) W.toolanim.set(agentChar(a.agent_id), a.tool, loc(a.tool_at));
    }
    for (const e of j.events) L.seen.add(e.seq);                                                    // 連上之前的事件不重演
    if (claudeEvents(j)) ui.toast(`已連上你的 Claude：${sessionsOfProject().filter(s => !s.ended).length} 個工作階段開著、${run.length} 位同事進行中`);
  }
  function applyQuota(qt) {
    if (!qt || !qt.rate_limits) return;
    const k = JSON.stringify(qt); if (k === L.lastQuota) return; L.lastQuota = k;
    emit('rate_limits', { ts: qt.at, five_hour: qt.rate_limits.five_hour, seven_day: qt.rate_limits.seven_day });
  }
  function ingest(j) {
    if (L.seq && j.seq < L.seq) { resetState(); }                                                   // 收件端被清空過：從頭來
    const first = L.seq === 0;
    L.data = j;
    const ps = j.projects || [];
    L.project = L.qProject || (L.cfg.project && ps.some(p => p.hash === L.cfg.project) ? L.cfg.project : (ps[0] || {}).hash || null);
    { const pe = ps.find(p => p.hash === L.project), nm = L.project ? (pe ? AP.label(pe.name) : '這個專案') : null; if (nm !== L.projName) { L.projName = nm; L._nameSig = null; applyProjectNames(); } }
    if (W.rosterHub && W.rosterHub.on) syncRoster(j);
    if (first) applySnapshot(j);
    else {
      const evs = (j.events || []).filter(e => !L.seen.has(e.seq));
      if (evs.length > 40) ui.toast(`補上你離線期間的 ${evs.length} 件事`);
      for (const e of evs) { try { applyEvent(e); } catch (x) { console.warn('即時事件處理失敗', x); } }
      syncSessions();
    }
    refreshNames();
    applyQuota(j.quota);
    L.seq = Math.max(L.seq, j.seq || 0);
    L.status = claudeEvents(j) ? 'ok' : 'nodata';
    L.booted = true;
    if (L.cfg.login && !L.code) L.msg = '';
    guideCheck(j);
  }

  // ───────── 讀取迴圈（分頁在背景時暫停） ─────────
  function schedule(ms) { clearTimeout(L.timer); L.timer = 0; L.nextAt = 0; if (L.mode === 'live' && document.visibilityState !== 'hidden') { const d = guideFast() ? Math.min(ms, 5000) : ms; L.nextAt = Date.now() + d; L.timer = setTimeout(poll, d); } }
  async function poll() {
    clearTimeout(L.timer); L.timer = 0;
    if (L.mode !== 'live' || L.inflight) return;
    if (document.visibilityState === 'hidden') { L.paused = true; return; }
    L.paused = false;
    const url = await resolveUrl(), hdr = authHeaders();
    if (!url || !hdr) { L.status = 'setup'; render(); return; }
    L.inflight = true; L.polls++;
    try {
      const ctl = new AbortController(), tm = setTimeout(() => ctl.abort(), 10000);
      const r = await fetch(`${url}/v1/office/${encodeURIComponent(L.cfg.office || 'main')}/state?since=${L.seq}${L.qProject ? '&project=' + L.qProject : ''}${L.qView ? '&view=' + L.qView : ''}`, { headers: hdr, cache: 'no-store', credentials: 'omit', signal: ctl.signal });
      clearTimeout(tm);
      if (L.mode !== 'live') return;
      if (r.status === 401 || r.status === 403) { L.status = 'auth'; L.fails++; render(); L.inflight = false; schedule(60000); return; }
      if (r.status === 429) throw new Error('太頻繁');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json(); L.fails = 0; L.lastOk = Date.now(); L.msg = '';
      ingest(j);
    } catch (e) { if (L.mode === 'live') { L.fails++; L.status = 'error'; L.msg = e.name === 'AbortError' ? '逾時' : String(e.message || e).slice(0, 40); } }
    finally { L.inflight = false; }
    render();
    schedule(L.fails ? Math.min(120000, L.pollMs * 2 ** Math.min(5, L.fails)) : L.pollMs);   // 斷線：指數退避（×2，最多 2 分鐘）；健康燈（health.js）顯示倒數
  }
  L.poll = poll;
  document.addEventListener('visibilitychange', () => {
    if (L.mode !== 'live') return;
    if (document.visibilityState === 'hidden') { clearTimeout(L.timer); L.timer = 0; L.paused = true; }
    else poll();
  });

  function enterLive() {
    if (L.mode !== 'live') { L.mode = 'live'; if (sim && sim.stopDay) sim.stopDay(); resetState(); patchDemo(true); }
    L.status = 'connecting'; render(); poll();
  }
  function restartLive() { resetState(); L.status = 'connecting'; render(); poll(); }
  function enterDemo() {
    clearTimeout(L.timer); L.timer = 0;
    if (L.mode === 'live') { L.mode = 'demo'; resetState(); patchDemo(false); }
    L.status = 'off'; L.projName = null; L._nameSig = null; applyProjectNames(); render();
  }
  L.enterLive = enterLive; L.enterDemo = enterDemo;

  // ───────── 績效總表（即時版）：只用真實事件算，資料不夠就寫「樣本不足」 ─────────
  let ledgerEl = null;
  const pct = (a, b) => (b >= 3 ? Math.round(a / b * 100) + '%' : null);
  const mins = ms => (ms < 60000 ? Math.max(1, Math.round(ms / 1000)) + ' 秒' : Math.round(ms / 60000) + ' 分');
  const fmtTok = n => (n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : String(n));
  const NA = '<span class="na">樣本不足</span>';
  function typeRows() { return (L.data && L.data.types) || []; }
  function renderLedger() {
    const types = typeRows(), ceo = (L.data && L.data.ceo) || {};
    const row = t => {
      const fin = (t.done || 0) + (t.failed || 0), mid = L.typeMap.get(t.agent_type) || (C(t.agent_type) ? t.agent_type : null), who = mid && W.members.get(mid) ? W.members.get(mid).nick : '（兼任）';
      return `<tr><td>${esc(who)}<br><span class="na">${esc(t.agent_type)}</span></td><td data-l="派工">${t.dispatched}</td><td data-l="完成">${t.done || 0}</td><td data-l="進行中">${t.running || 0}</td><td data-l="失敗">${t.failed || 0}</td>
        <td data-l="完成率">${pct(t.done || 0, fin) || NA}</td><td data-l="平均耗時">${t.n_dur >= 3 && t.avg_ms != null ? mins(t.avg_ms) : NA}</td><td data-l="Token">${t.n_tokens ? fmtTok(t.tokens) : '<span class="na">未提供</span>'}</td><td data-l="等第"><span class="na" title="等第要滿一週、每類至少 3 件交件，而且計分規則接上真資料之後才評">未評等</span></td></tr>`;
    };
    const ceoLine = `<p class="ceo"><b>CEO（主 Claude）</b>　工作階段 ${ceo.sessions || 0}・你下的指令 ${ceo.prompts || 0}・完成回合 ${ceo.turns || 0}・Token ${ceo.tokens ? fmtTok(ceo.tokens) : '<span class="na">未提供</span>'}・等第 <span class="na">未評等</span></p>`;
    const body = !L.data ? '<p class="empty">尚未收到回報。</p>' : !types.length && !ceo.sessions ? '<p class="empty">樣本不足：近 7 天還沒收到任何工作階段或派工。</p>'
      : `${ceoLine}${types.length ? `<div class="scroll"><table><thead><tr><th>同事</th><th>派工</th><th>完成</th><th>進行中</th><th>失敗</th><th>完成率</th><th>平均耗時</th><th>Token</th><th>等第</th></tr></thead><tbody>${types.map(row).join('')}</tbody></table></div>` : '<p class="empty">樣本不足：近 7 天還沒有派出子 Agent。</p>'}`;
    ledgerEl.innerHTML = `<button class="x" data-a="close" aria-label="關閉">×</button><h3>績效總表<span class="chip2">即時・近 7 天</span></h3>${body}
      <p class="help">數字全部來自你的 Claude 回報的事件（我方統計，不是官方額度）。完成率與平均耗時要至少 3 件交件才算；Token 只有回報裡有用量時才顯示。</p>`;
  }
  function openLedger() {
    if (!ledgerEl) { ledgerEl = document.createElement('aside'); ledgerEl.className = 'panel'; ledgerEl.id = 'aioLedger'; ledgerEl.setAttribute('role', 'dialog'); ledgerEl.setAttribute('aria-label', '績效總表（即時）'); ledgerEl.hidden = true; $('app').append(ledgerEl); ledgerEl.addEventListener('click', e => { if (e.target.closest('[data-a=close]')) closeLedger(); }); }
    pop.hidden = true; renderLedger(); ledgerEl.hidden = false; if (rwBtn) { rwBtn.classList.add('on'); rwBtn.setAttribute('aria-expanded', 'true'); }
  }
  function closeLedger() { if (ledgerEl) ledgerEl.hidden = true; if (rwBtn) { rwBtn.classList.remove('on'); rwBtn.setAttribute('aria-expanded', 'false'); } }
  L.openLedger = openLedger;
  function liveCardBlock(spec) {
    const ts = [...L.typeMap].filter(([, id]) => id === spec.id).map(([t]) => t), rows = typeRows().filter(t => ts.includes(t.agent_type));
    if (spec.id === 'ceo') { const c = (L.data && L.data.ceo) || {}; return `<div class="rw aio-rw"><b>近 7 天（真實）</b>　工作階段 ${c.sessions || 0}・指令 ${c.prompts || 0}・回合 ${c.turns || 0}</div>`; }
    if (!rows.length) return '<div class="rw aio-rw"><b>近 7 天（真實）</b>　<span class="na">樣本不足：還沒有派工紀錄</span></div>';
    const s = rows.reduce((a, t) => ({ d: a.d + t.dispatched, ok: a.ok + (t.done || 0), f: a.f + (t.failed || 0) }), { d: 0, ok: 0, f: 0 });
    return `<div class="rw aio-rw"><b>近 7 天（真實）</b>　派工 ${s.d}・完成 ${s.ok}・失敗 ${s.f}・完成率 ${pct(s.ok, s.ok + s.f) || '<span class="na">樣本不足</span>'}</div>`;
  }

  // ───────── 第二批 1～3 項：動作圖示、子 Agent 連線、連線健康燈（三支新檔，各自畫自己的圖層） ─────────
  try { createToolAnim(W, { state: S }); createLinks(W); createHealth(W, { ui }); } catch (e) { console.warn('動作圖示／連線／健康燈載入失敗', e); }

  // ───────── 開場 ─────────
  if (hasCred() && !L.cfg.show) enterLive(); else render();
  return L;
}
