/* ============================================================================
   冷啟動總開關（2026-11-10，Andy 核可 docs/marketing/restart_1109/00_plan.md 決定表第 2、3、4 項；
   依據 docs/marketing/restart_1109/01_freemium.md 第 3-3 節）

   ★ 要正式開賣，只改這一個檔：把下面的 enabled 改成 false。
     綠界、結帳面板、訂單頁、訂閱申請的程式一行都沒刪，開關關掉就完整恢復原狀。

   為什麼是 .js 不是 .json（同 legal_config.js）：同步載入，第一次畫面出來前就決定；
   stamp_assets.py 會自動加版本戳，改完部署一定換得掉。

   開啟時（冷啟動期）：
     · #pricing 不顯示任何金額、年繳劃線價、月繳／年繳切換；結帳面板不從任何地方進入。
     · 所有「升級 Plus／Pro」「Plus 以上可增加」之類的字樣，訪客改「免費註冊」、已登入的會員改「預約通知」
       （額度用完則寫「明天 00:00 重置」）。實作＝下面的文字規則表＋MutationObserver 掃描，所以 features.js
       寫死的 47 處 qnote、perm.js／quota.js／acctm4.js 的字樣不必逐檔改，關掉開關就整套不生效。
     · 新會員歡迎窗不出現 Plus／Pro 字樣（promo_welcome.js 自己讀 TwCold.on()）。
   不受影響：退款與取消訂閱政策、使用條款（法律頁）、管理區、已經付費的會員的訂單頁。

   ⚠ 備援網址（*.github.io）不論 enabled 是 true 或 false，一律視為冷啟動：docs/launch_standard.md 第 10 條 ⑥
     「備援網址不放價格與結帳」。所以正式開賣後，github.io 也還是不會出現價格。
   ============================================================================ */
window.TW_COLDSTART = {
  enabled: true,   // ★ 開賣時改 false
};

(function () {
  'use strict';
  const C = window.TW_COLDSTART || {};
  const mirror = /(^|\.)github\.io$/i.test(location.hostname || '');
  const isOn = () => !!(C.enabled || mirror);

  const A = () => window.TwAccount || null;
  /* 登入了嗎：沒設定會員功能、沒登入都算訪客 */
  function isMember() {
    try { const a = A(); return !!(a && a.on && a.on() && a.user && a.user()); } catch (e) { return false; }
  }
  const cta = (member) => (member ? '預約通知' : '免費註冊');

  /* ------------------------------------------------------------------------
     文字規則（順序有意義：長的、特殊的在前）。每條 [正規式, 訪客用字, 會員用字]；$1 是括號抓到的字。
     只換「叫人付費／升級」的字樣；不碰方案本身的名字（例如目前方案徽章「Plus」）。
     ------------------------------------------------------------------------ */
  const RULES = [
    [/Plus 以上可增加/g, '免費註冊可增加', '明天 00:00 重置'],
    [/升級方案可增加每日次數，明天（台北時間 0 點）自動恢復/g, '免費註冊可增加每日次數，明天（台北時間 0 點）自動恢復', '明天（台北時間 0 點）自動恢復'],
    [/升級方案可增加每日次數/g, '免費註冊可增加每日次數', '明天 00:00 重置'],
    [/(?:Plus|Pro)\s*以上可(播放|跳轉|點擊|使用|查看|選擇|調整|增加)/g, '免費註冊可$1', '之後開放$1'],
    [/(?:Plus|Pro)\s*以上(?:才可以)?(?:的)?功能/g, '註冊會員功能', '之後開放的功能'],
    [/需\s*(?:Plus|Pro)\s*會員/g, '登入即可使用', '這項之後開放'],
    [/(?:Plus|Pro)\s*(?:會員|限定)/g, '註冊會員', '之後開放'],
    [/(\d+)\s*天\s*(?:Plus|Pro)/g, '$1 天進階額度', '$1 天進階額度'],
    [/升級\s*(?:Plus|Pro)\s*[／/]\s*(?:Plus|Pro)\s*/g, '免費註冊', '預約通知'],
    [/升級\s*(?:Plus|Pro)\s*(?:不限次數|不限|可以選更多|提高每日額度|還能使用|每天\s*\d+\s*次)/g, '免費註冊可多用', '預約開放通知'],
    [/升級\s*(?:Plus|Pro)/g, '免費註冊', '預約通知'],
    [/登入或升級方案即可使用/g, '登入即可使用', '這項之後開放'],
    [/升級方案即可使用/g, '登入即可使用', '這項之後開放'],
    [/升級(?:查看|會員)/g, '免費註冊', '預約通知'],
    [/升級可用/g, '註冊後可用', '之後開放'],
    [/升級方案/g, '免費註冊', '預約通知'],
    [/訂閱方案/g, '會員權益', '會員權益'],
    [/查看方案/g, '查看會員權益', '查看會員權益'],
    [/看方案/g, '看會員權益', '看會員權益'],
  ];
  const QUICK = /Plus|Pro\b|升級|訂閱方案|看方案|查看方案/;

  function t(s, member) {
    if (typeof s !== 'string' || !QUICK.test(s)) return s;
    const m = member === undefined ? isMember() : !!member;
    let o = s;
    for (const [re, g, mm] of RULES) { re.lastIndex = 0; o = o.replace(re, m ? mm : g); }
    return o;
  }

  /* 不掃的地方：管理區（站主在看）、法律頁（退款與取消訂閱政策、條款本文必須原樣）、程式碼 */
  const SKIP = 'script,style,textarea,input,select,code,pre,#v-admin,#v-legal,[data-cold-skip],.adm,.admin,#v-orders';
  const skip = (el) => !!(el && el.closest && el.closest(SKIP));

  function fixText(n) {
    const v = n.nodeValue;
    if (!v || !QUICK.test(v)) return;
    const p = n.parentElement; if (!p || skip(p)) return;
    const w = t(v); if (w !== v) n.nodeValue = w;
  }
  function fixAttrs(el) {
    if (!el.getAttribute || skip(el)) return;
    for (const a of ['title', 'aria-label']) {
      const v = el.getAttribute(a);
      if (v && QUICK.test(v)) { const w = t(v); if (w !== v) el.setAttribute(a, w); }
    }
  }
  function sweep(root) {
    if (!root) return;
    if (root.nodeType === 3) { fixText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9) return;
    const base = root.nodeType === 9 ? root.documentElement : root;
    if (!base || skip(base)) return;
    if (base.nodeType === 1) fixAttrs(base);
    const tw = document.createTreeWalker(base, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode(n) { return n.nodeType === 1 && /^(SCRIPT|STYLE|TEXTAREA|INPUT|SELECT)$/.test(n.tagName) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } });
    let n; while ((n = tw.nextNode())) { if (n.nodeType === 3) fixText(n); else fixAttrs(n); }
  }

  window.TwCold = { on: isOn, mirror, isMember, cta, t, sweep };
  if (!isOn()) return;   // 關閉：什麼都不裝，網站完全是原樣

  document.documentElement.classList.add('cold');
  /* 手機側欄的「Plus 限定」是 CSS 偽元素內容（perm.js），文字掃描碰不到 → 用同樣高的選擇器蓋掉 */
  const st = document.createElement('style'); st.id = 'coldCss';
  st.textContent = ':root.cold.m4 #v-flow .rbar:is(#rotBack,#sankeyDays)>.plknote::before{content:"之後開放"}'
    /* 「即將開放」大字：窄螢幕（360／390）不可被切（11-10 CEO 退件），縮字級、允許換行、不裁切 */
    + '#v-pricing .prprice.ask{font-size:clamp(20px,6vw,28px)!important;white-space:normal!important;overflow:visible!important;text-overflow:clip!important;max-width:100%;box-sizing:border-box;padding:0 4px;text-align:center;justify-content:center;word-break:keep-all}';
  document.head.appendChild(st);

  const start = () => {
    sweep(document);
    new MutationObserver((ms) => {
      for (const m of ms) {
        if (m.type === 'childList') m.addedNodes.forEach((n) => sweep(n));
        else if (m.type === 'characterData') fixText(m.target);
        else if (m.type === 'attributes') fixAttrs(m.target);
      }
    }).observe(document.documentElement, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['title', 'aria-label'] });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
