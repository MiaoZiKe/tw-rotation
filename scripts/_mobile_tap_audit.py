"""手機按鈕普查：全站每一顆看得見的可點元素，用觸控真的點一次，驗「點得到、有反應、收得回來」。

為什麼有這支（Andy 2026-09-27）
--------------------------------
> 「手機版介面 幫我確實驗證所有按鈕功能，我發現有部分功能無法點選」

既有的手機段落（手機、手機v3、手機一屏…）都是**點名驗**：驗收寫的人知道哪幾顆鈕，就點那幾顆。
沒被點名的鈕壞掉沒有人會知道 —— 這支反過來，**先把畫面上所有可點的東西列出來，再一顆一顆點**。

環境
----
Playwright `is_mobile=True`、`has_touch=True`、DPR2，寬度 390×844 與 360×780 各一輪；點一律用
`touchscreen.tap(x, y)`（觸控），不是滑鼠 click。

列哪些元素
----------
看得見的 `button`、`a[href]`、`summary`、`label`、`[role=button|tab|link|switch|checkbox|option|menuitem]`、
`[onclick]`，以及**計算後 cursor:pointer 而且父層不是 pointer 的元素**（委派監聽器那種：li、svg 的 g…）。
「看得見」＝ checkVisibility 通過、寬高 ≥ 1、沒有被 overflow:hidden 的祖先整個切掉。
同一種長相的元素（同標籤＋同 class＋同祖先 id）只抽前 SAMPLE 顆 —— 100 列排行不必點 100 次，
但只要有一顆紅，那一組就全部點過。

每一顆驗三件事
--------------
a) 點得到：捲到畫面中央之後，中心點 `elementFromPoint` 打到的是它自己或子孫；被蓋住就記「被誰蓋住」。
   觸控目標 < 40×40 的另外列一張表（**不算紅燈**，見 MIN_TOUCH 的說明）。
b) 有反應：點之前掛一個 MutationObserver，點之後以下任何一項改變就算有反應 ——
   DOM 變了（排除點之前 700ms 就自己在跳的節點）、網址變了、localStorage 寫入、
   表單值／勾選變了、視窗或任何捲動容器的捲動位置變了、焦點換了。
   已選取的那顆（.on／.sel／aria-selected=true／aria-current…）點了不變是正常，不算紅。
c) 收得回來：點完如果冒出新的浮層（position:fixed 或 role=dialog 的新元素），
   先普查浮層裡面的鈕（一層），再用 ×／關閉／取消 關掉；沒有就點外面（挑一個沒有可點元素的點）。
   關完浮層必須消失，而且畫面上不准留下蓋住版面的透明層。

輸出
----
    python scripts/_mobile_tap_audit.py                    # 390 與 360 全部
    python scripts/_mobile_tap_audit.py --width 390        # 只跑 390
    python scripts/_mobile_tap_audit.py --only stock       # 只跑名稱含 stock 的畫面

`docs/_mobile_tap/report.md`、`report.json`（gitignore 同 docs/_show）。
`scripts/_uitest.py` 的「手機按鈕普查」段落 import 這裡的 `run_audit()`，問題數必須是 0。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("TW_MTAP_OUT") or (ROOT / "docs" / "_mobile_tap"))

SAMPLE = 2            # 同一種長相的元素抽幾顆
MIN_TOUCH = 40        # 觸控目標下限（列表用，不算紅燈 —— 密集晶片 36px 是 2026-09-23 手機規矩允許的，
#                       而且把幾百顆小鈕放大是視覺改版的事，這一輪只修功能）
REACT_MS = 1500       # 點下去之後等多久還沒反應才算沒反應（非同步畫圖的最長等待；兩種寬度同時跑時 CPU 較忙，給寬一點）
VIEWPORTS = {390: (390, 844), 360: (360, 780)}

# ★ 白名單：判斷過「點了不變是設計」的元素。鍵＝選擇器（matches），值＝理由。每一條都要寫理由。
EXEMPT: dict[str, str] = {
    # 品牌列 onclick 是 location.hash='#overview'：在總覽上點本來就不會變；其他每一頁都會點到它、驗到換頁。
    "body:has(#v-overview.on) .brand": "在總覽點品牌列＝回總覽，不變是正常",
    # K 線圖右下角的「重設縮放」：圖沒有被縮放時按下去本來就沒有東西可以重設（畫在 canvas 上，DOM 也不會變）。
    # 「先縮放、再按，真的回到全覽」這一條在 _uitest.py「手機按鈕普查」段落的 ①b 用觸控另外驗。
    "button.kfit": "K 線沒縮放時按「重設縮放」不會變是正常（縮放後再按由 ①b 另外驗）",
    # ★ 2026-10-06（既有紅字清理）：兩個純表單欄位的下拉 —— 換選項本來就不會改畫面，要按旁邊的送出／新增才生效。
    #   普查對 <select> 的「有反應」是看畫面有沒有跟著變，這兩顆的設計就是「不變」，所以列白名單；
    #   「送出／新增之後真的生效」由 訂閱與客服1005、個股的自訂週期各自的段落驗。
    "select#fbCat": "客服表單的「類別」下拉：只是表單欄位，選了不變是正常（送出才有反應）",
    "select#tfU": "自訂週期的「單位」下拉：只是表單欄位，選了不變是正常（按新增才生效）",
}

# ---------------------------------------------------------------------------- 瀏覽器端的量測
# 列出範圍內（整頁或某個浮層）所有看得見的可點元素。元素存在 window.__taEls（不掛屬性，見 _get 的說明）。
ENUM_JS = r"""
(scope) => {
  const root = scope === '__layer__' ? (window.__taLayer && window.__taLayer.isConnected ? window.__taLayer : null)
             : scope ? document.querySelector(scope) : document.body;
  if (!root) return [];
  const path = (e) => {
    const seg = [];
    for (let n = e; n && n !== document.body; n = n.parentElement) {
      if (n.id) { seg.unshift('#' + CSS.escape(n.id)); return seg.join(' > '); }
      if (!n.parentElement) return '';
      const k = [...n.parentElement.children].indexOf(n) + 1;
      seg.unshift(n.tagName.toLowerCase() + ':nth-child(' + k + ')');
    }
    return 'body > ' + seg.join(' > ');
  };
  const INTER = 'button,a[href],summary,label,select,[role=button],[role=tab],[role=link],[role=switch],'
              + '[role=checkbox],[role=menuitem],[role=option],[role=radio],[onclick],'
              + 'input[type=checkbox],input[type=radio],input[type=button],input[type=submit]';
  const STATE = /^(on|off|sel|selected|active|cur|current|open|opened|dim|hover|hl|hit|focus|pressed|is-.*|m3on|show|shown|hide|hidden|lit|pick|picked|chosen|done|up|dn|down|pos|neg|flat)$/;
  const vis = (e) => {
    if (e.checkVisibility && !e.checkVisibility({opacityProperty: true, visibilityProperty: true})) return null;
    let r = e.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return null;
    // 被 overflow:hidden/clip 的祖先切掉的部分不算看得見（auto/scroll 捲得到，所以不切）
    let x0 = r.left + scrollX, y0 = r.top + scrollY, x1 = r.right + scrollX, y1 = r.bottom + scrollY;
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      const ox = cs.overflowX, oy = cs.overflowY;
      if (ox === 'visible' && oy === 'visible') continue;
      const pr = p.getBoundingClientRect();
      const px0 = pr.left + scrollX, py0 = pr.top + scrollY, px1 = pr.right + scrollX, py1 = pr.bottom + scrollY;
      if (ox === 'hidden' || ox === 'clip') { x0 = Math.max(x0, px0); x1 = Math.min(x1, px1); }
      if (oy === 'hidden' || oy === 'clip') { y0 = Math.max(y0, py0); y1 = Math.min(y1, py1); }
      if (x1 - x0 < 1 || y1 - y0 < 1) return null;
    }
    // 整顆在視窗左右外面、而且沒有任何可以橫向捲的祖先 ＝ 收在畫面外的抽屜（transform 推出去），不算看得見
    if (r.right <= 0 || r.left >= innerWidth) {
      let sc = false;
      for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if ((ox === 'auto' || ox === 'scroll') && p.scrollWidth > p.clientWidth + 1) {
          // 捲動容器自己也要在畫面裡（收在畫面外的抽屜本身就是可以橫捲的，不能因此算看得見）
          const pr = p.getBoundingClientRect();
          if (pr.right > 0 && pr.left < innerWidth) { sc = true; break; }
        }
      }
      if (!sc) return null;
    }
    return {w: r.width, h: r.height};
  };
  // 觸控範圍＝外框 ∪ 擴大點擊區的偽元素（::before／::after 絕對定位、負的 inset）。
  // 瀏覽器命中測試本來就算偽元素（點在偽元素上＝點在它的元素上），所以「28px 圓點＋inset:-8px」真的是 44px 可點；
  // 只看 getBoundingClientRect 會把這種刻意做大的點擊區誤列成「觸控目標不足」（2026-09-28 設計 v4 第二批）。
  // 偽元素被 overflow 非 visible 的祖先切掉的部分點不到，一併夾回來。
  const hitBox = (e) => {
    const r = e.getBoundingClientRect();
    let x0 = r.left, y0 = r.top, x1 = r.right, y1 = r.bottom;
    if (!(e instanceof HTMLElement) || getComputedStyle(e).position === 'static') return {tw: Math.round(r.width), th: Math.round(r.height)};
    for (const ps of ['::before', '::after']) {
      const cs = getComputedStyle(e, ps);
      if (!cs || cs.content === 'none' || cs.content === 'normal' || cs.display === 'none'
          || cs.position !== 'absolute' || cs.pointerEvents === 'none' || cs.visibility === 'hidden') continue;
      const t = parseFloat(cs.top), l = parseFloat(cs.left), rr = parseFloat(cs.right), b = parseFloat(cs.bottom);
      if (Number.isFinite(t)) y0 = Math.min(y0, r.top + t);
      if (Number.isFinite(b)) y1 = Math.max(y1, r.bottom - b);
      if (Number.isFinite(l)) x0 = Math.min(x0, r.left + l);
      if (Number.isFinite(rr)) x1 = Math.max(x1, r.right - rr);
    }
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
      const pr = p.getBoundingClientRect();
      if (cs.overflowX !== 'visible') { x0 = Math.max(x0, Math.min(r.left, pr.left)); x1 = Math.min(x1, Math.max(r.right, pr.right)); }
      if (cs.overflowY !== 'visible') { y0 = Math.max(y0, Math.min(r.top, pr.top)); y1 = Math.min(y1, Math.max(r.bottom, pr.bottom)); }
    }
    return {tw: Math.round(x1 - x0), th: Math.round(y1 - y0)};
  };
  const cands = [];
  const all = root.querySelectorAll('*');
  for (const e of all) {
    if (e.closest('[data-ta-skip]')) continue;
    let c = e.matches(INTER);
    if (!c) {
      const cs = getComputedStyle(e);
      if (cs.cursor === 'pointer' && cs.pointerEvents !== 'none') {
        const p = e.parentElement; c = !p || getComputedStyle(p).cursor !== 'pointer';
      }
    }
    if (!c) continue;
    if (e.tagName === 'CANVAS' || e.tagName === 'HTML' || e.tagName === 'BODY') continue;
    if (e.matches('label') && !e.querySelector('input,select') && !e.htmlFor && getComputedStyle(e).cursor !== 'pointer') continue;
    if (e.disabled || e.getAttribute('aria-disabled') === 'true' || e.closest('fieldset[disabled]')) continue;
    // label 裡面的 input：點 label 就好（input 多半被藏起來）
    if (e.matches('input') && e.closest('label')) continue;
    const v = vis(e); if (!v) continue;
    cands.push(e);
  }
  const out = [];
  window.__taEls = cands; window.__taSet = new Set(cands); window.__taPaths = cands.map(path);
  cands.forEach((e, i) => {
    const cls = [...e.classList].filter(c => !STATE.test(c)).sort().join('.');
    let host = e.parentElement, hid = '';
    while (host && host !== document.body) { if (host.id) { hid = host.id; break; } host = host.parentElement; }
    const r = e.getBoundingClientRect();
    const txt = ((e.getAttribute('aria-label') || e.innerText || e.textContent || e.getAttribute('title') || '') + '')
                  .replace(/\s+/g, ' ').trim().slice(0, 28);
    const id = e.id ? '#' + e.id : '';
    const tag = e.tagName.toLowerCase();
    const sel = tag + id + (cls ? '.' + cls.split('.').slice(0, 3).join('.') : '')
              + (e.dataset && Object.keys(e.dataset).filter(k => k !== 'ta').slice(0, 2).map(k => `[data-${k.replace(/[A-Z]/g, m => '-' + m.toLowerCase())}="${String(e.dataset[k]).slice(0, 24)}"]`).join('') || '');
    const selected = e.matches('.on,.sel,.selected,.active,.cur,.current,[aria-selected=true],[aria-pressed=true],[aria-current]:not([aria-current=false]),[aria-checked=true]')
                   || (tag === 'a' && e.getAttribute('href') && e.getAttribute('href').startsWith('#')
                       && decodeURIComponent(e.getAttribute('href')) === decodeURIComponent(location.hash));
    const href = tag === 'a' ? (e.getAttribute('href') || '') : '';
    out.push({i, sel, txt, host: hid, hasSel: tag === 'select' || (tag === 'label' && !!e.querySelector('select, input[type=range]')),
              tbl: tag === 'th' || tag === 'tr', chrome: !!e.closest('header, #tabs, .topbar, .sitefoot, aside#side'),
              // .mnext（「下一步：④ … ›」）也是換分段：點完不帶回原本那一段的話，後面的鈕是在「別的分段」被點到的，
              // 之後要重開它們開出來的浮層時回到原本那一段就找不到開它的鈕（2026-09-27：總覽「看全部 N 則事件」就是這樣）
              seg: !!e.closest('.mspine, .mpager, .mnext, #mbTabs, .mbseg, #stockTabs, .mseg, [role=tablist]'), sig: tag + '|' + cls + '|' + hid + '|' + (e.getAttribute('role') || '')
                   // 沒有 class 的鈕（分段列、步驟列）光看標籤分不出來：再加父層的標籤與 class、data 屬性名稱
                   + '|' + (e.parentElement ? e.parentElement.tagName + '.' + [...e.parentElement.classList].filter(c => !STATE.test(c)).sort().join('.') : '')
                   + '|' + Object.keys(e.dataset || {}).filter(k => k !== 'ta').sort().join(','),
              w: Math.round(r.width), h: Math.round(r.height), ...hitBox(e), selected,
              href, target: e.getAttribute('target') || '', download: e.hasAttribute('download'),
              exp: e.getAttribute('aria-expanded')});
  });
  return out;
}
"""

# 捲到元素中央、回報「點得到嗎」。回傳中心點座標、被誰蓋住。
REACH_JS = r"""
(i) => {
  const __get = (i) => { const a = window.__taEls || [], e = a[+i]; if (e && e.isConnected) return e; const p = (window.__taPaths || [])[+i]; try { return p ? document.querySelector(p) : null; } catch (x) { return null; } };
  const e = __get(i);
  if (!e || !e.isConnected) return {gone: true};
  try { e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'}); } catch (x) { e.scrollIntoView(); }
  return {gone: false};
}
"""

POINT_JS = r"""
(i) => {
  const __get = (i) => { const a = window.__taEls || [], e = a[+i]; if (e && e.isConnected) return e; const p = (window.__taPaths || [])[+i]; try { return p ? document.querySelector(p) : null; } catch (x) { return null; } };
  const e = __get(i);
  if (!e || !e.isConnected) return {gone: true};
  const desc = (n) => {
    if (!n) return '（沒有元素）';
    const id = n.id ? '#' + n.id : '';
    const cls = n.classList && n.classList.length ? '.' + [...n.classList].slice(0, 3).join('.') : '';
    return (n.tagName || '').toLowerCase() + id + cls;
  };
  const rects = [...e.getClientRects()].filter(r => r.width >= 1 && r.height >= 1);
  const r = rects.length ? rects[0] : e.getBoundingClientRect();
  // 被 overflow:hidden 的祖先切掉的部分不能點：中心點取「看得見的那一塊」的中心
  let x0 = r.left, y0 = r.top, x1 = r.right, y1 = r.bottom;
  for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
    const cs = getComputedStyle(p);
    if (cs.overflowX === 'visible' && cs.overflowY === 'visible') continue;
    const pr = p.getBoundingClientRect();
    x0 = Math.max(x0, pr.left); x1 = Math.min(x1, pr.right); y0 = Math.max(y0, pr.top); y1 = Math.min(y1, pr.bottom);
  }
  x0 = Math.max(x0, 0); y0 = Math.max(y0, 0); x1 = Math.min(x1, innerWidth); y1 = Math.min(y1, innerHeight);
  if (x1 - x0 < 1 || y1 - y0 < 1) return {gone: false, off: true, rect: [r.left, r.top, r.width, r.height].map(Math.round)};
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const hitAt = (x, y) => { const h = document.elementFromPoint(x, y); return {h, ok: !!h && (h === e || e.contains(h))}; };
  const c = hitAt(cx, cy);
  // 中心被蓋住時，再看四個內縮角落有沒有一點點得到（給修法參考，不改判定）
  let anyOk = c.ok, ax = cx, ay = cy;
  if (!c.ok) {
    // 5×5 格點找一個「打得到它自己」的點
    outer: for (let gy = 1; gy <= 5; gy++) for (let gx = 1; gx <= 5; gx++) {
      const px = x0 + (x1 - x0) * gx / 6, py = y0 + (y1 - y0) * gy / 6;
      if (hitAt(px, py).ok) { anyOk = true; ax = px; ay = py; break outer; }
    }
  }
  // 母框：中心被「畫在它裡面的另一個可點元件」蓋住（例如剖析圖的 MSP 外框裡疊著兩格子零件）——
  //   那是設計，不是被透明層蓋住；只要露出來的地方點得到，就改點那裡。
  let nested = false;
  if (!c.ok && anyOk && c.h) {
    let bl = c.h; for (let n = c.h; n; n = n.parentElement) if (window.__taSet && window.__taSet.has(n)) { bl = n; break; }
    const br = bl.getBoundingClientRect();
    const inside = br.left >= r.left - 1 && br.right <= r.right + 1 && br.top >= r.top - 1 && br.bottom <= r.bottom + 1;
    const interactive = bl !== c.h || (window.__taSet && window.__taSet.has(c.h)) || !!c.h.closest('button, a[href], [role=button]') || getComputedStyle(c.h).cursor === 'pointer';
    nested = inside && interactive;
  }
  // SVG 群組：外框中心可能剛好是群組裡的空白（例如長條＋左邊一行字，中心落在兩者中間），
  //   打到的是「畫在它前面、被它壓在下面」的底框 —— 那不是被蓋住，是點在空白處；改點群組真正畫到的地方。
  if (!c.ok && !nested && anyOk && c.h && e instanceof SVGElement && c.h instanceof SVGElement
      && (c.h.contains(e) || (c.h.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_FOLLOWING))) nested = true;
  // 剖析圖手機版的編號鈕（.mnum）疊在零件上：如果那顆編號就是「這個零件自己的」，點編號＝點它（開它的說明與台股），
  //   那是設計（手機剖析圖只留編號）；是別的零件的編號才算被蓋住。
  // 剖析圖手機版（圖上掛了編號層 .mnumlayer）：入口是編號（2026-09-24 拍板「剖析圖只留編號」）。
  //   零件本身被疊圖（別的零件、材質紋路、別人的編號）壓住時，只要**它自己的編號**在圖上而且點得到，
  //   它的功能（說明＋台股）就拿得到 —— 記成備註（報告另外列一張表），不算點不到。
  //   它自己沒有編號、又整個點不到的，才算紅。
  let ownNo = '';
  const dgHost = (e.dataset && e.dataset.part && e.closest) ? e.closest('.mnum2d, .mnum3d') : null;
  if (!c.ok && !nested && c.h && dgHost && dgHost.querySelector('.mnumlayer')) {
    const cards = [...dgHost.querySelectorAll('.dgcards .dgc')];
    const noOf = (card) => { const n = card && card.querySelector('.no'); return n ? n.textContent.trim() : ''; };
    const nb = c.h.closest && c.h.closest('.mnum');
    const coverCard = nb ? cards.find(x => noOf(x) === nb.dataset.no) : null;
    if (nb && coverCard && coverCard.dataset.part === e.dataset.part) { nested = true; ownNo = nb.dataset.no; }
    else {
      const mine = cards.find(x => x.dataset.part === e.dataset.part && noOf(x));
      const myNo = mine ? noOf(mine) : '';
      const myBtn = myNo && [...dgHost.querySelectorAll('.mnum')].find(b => b.dataset.no === myNo);
      const who = nb ? ('別的零件的編號 ' + nb.dataset.no) : desc(c.h);
      if (myBtn) {
        const br = myBtn.getBoundingClientRect();
        const bx = br.left + br.width / 2, by = br.top + br.height / 2;
        const inView = bx > 0 && bx < innerWidth && by > 0 && by < innerHeight;
        const hitMine = !inView || (() => { const h = document.elementFromPoint(bx, by); return !!h && (h === myBtn || myBtn.contains(h)); })();
        if (hitMine) { nested = true; ownNo = '~' + myNo + '|' + who; }
        else ownNo = '!' + who + '；它自己的編號 ' + myNo + ' 也被蓋住';
      } else {
        // 沒有編號的零件：如果整組都刻意設成不能點（襯景），那不是壞掉
        const shapes = [...e.querySelectorAll('*')].filter(x => x instanceof SVGGraphicsElement);
        const inert = getComputedStyle(e).pointerEvents === 'none' || (shapes.length > 0 && shapes.every(x => getComputedStyle(x).pointerEvents === 'none'));
        if (inert) { nested = true; ownNo = '='; }
        else ownNo = '!' + who + '；它沒有自己的編號';
      }
    }
  }
  // 蓋住它的是不是它的祖先（＝它自己 pointer-events:none，點下去由祖先接）
  const anc = !c.ok && c.h && c.h.contains(e);
  return {gone: false, off: false, x: nested ? ax : cx, y: nested ? ay : cy, ok: c.ok || nested, nested, ownNo, anyOk, anc, by: c.ok ? '' : desc(c.h),
          byPe: (!c.ok && c.h) ? getComputedStyle(c.h).pointerEvents : '',
          byOp: (!c.ok && c.h) ? getComputedStyle(c.h).opacity : '',
          w: Math.round(r.width), h: Math.round(r.height)};
}
"""

# 點之前：記狀態、掛 MutationObserver（排除點之前自己就在跳的節點）
ARM_JS = r"""
(me) => {
  window.__taMe = me;
  const scrollers = [];
  if (!window.__taScrollers) {
    document.querySelectorAll('*').forEach(e => {
      if (scrollers.length > 80) return;
      if ((e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1)) {
        const cs = getComputedStyle(e); if (/(auto|scroll)/.test(cs.overflowX + cs.overflowY)) scrollers.push(e);
      }
    });
  }
  window.__taScrollers = scrollers.length ? scrollers : (window.__taScrollers || []);
  const snap = () => {
    let ls = []; try { for (let k = 0; k < localStorage.length; k++) { const kk = localStorage.key(k); if (!/^tw\.live/.test(kk)) ls.push(kk + '=' + localStorage.getItem(kk)); } } catch (x) {}
    const inp = [...document.querySelectorAll('input,select,textarea')].map(n => (n.type === 'checkbox' || n.type === 'radio') ? n.checked : n.value).join('|');
    const ae = document.activeElement;
    const __get = (i) => { const a = window.__taEls || [], e = a[+i]; if (e && e.isConnected) return e; const p = (window.__taPaths || [])[+i]; try { return p ? document.querySelector(p) : null; } catch (x) { return null; } };
    const me = window.__taMe != null && window.__taMe !== '-1' ? __get(window.__taMe) : null;
    const self = ae && me && (ae === me || me.contains(ae) || ae.contains(me));
    const act = (!ae || ae === document.body || self) ? '' : (ae.tagName + '#' + ae.id + '.' + String(ae.className));
    const sc = window.__taScrollers.filter(e => e.isConnected).map(e => Math.round(e.scrollLeft) + ',' + Math.round(e.scrollTop)).join(';');
    return {href: location.href, ls: ls.sort().join('\n'), inp, act, sy: Math.round(scrollY), sx: Math.round(scrollX), sc};
  };
  window.__taSnap = snap;
  window.__taBefore = snap();
  window.__taMut = []; window.__taMutNodes = [];
  if (window.__taObs) window.__taObs.disconnect();
  const noise = new Set(window.__taNoise || []);
  window.__taObs = new MutationObserver((ms) => {
    for (const m of ms) {
      if (m.type === 'attributes' && /^data-ta/.test(m.attributeName)) continue;
      if (m.type === 'attributes' && m.target.getAttribute(m.attributeName) === m.oldValue) continue;
      if (m.type === 'characterData' && m.target.data === m.oldValue) continue;
      const t = m.target.nodeType === 1 ? m.target : m.target.parentElement;
      if (!t) continue;
      if (noise.has(t)) continue;   // 只排除「自己就在跳的那個節點」本身，不排除它的子孫（不然 body 一改 style 整頁都被當雜訊）
      window.__taMut.push(m.type + ':' + (t.id || t.className || t.tagName));
      window.__taMutNodes.push(t);
    }
  });
  window.__taObs.observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true,
                                                     attributeOldValue: true, characterDataOldValue: true});
  return true;
}
"""

REACT_JS = r"""
() => {
  const a = window.__taBefore || {}, b = window.__taSnap ? window.__taSnap() : {};
  const why = [];
  if (a.href !== b.href) why.push('網址');
  if (a.ls !== b.ls) why.push('localStorage');
  if (a.inp !== b.inp) why.push('表單值');
  if (a.sy !== b.sy || a.sx !== b.sx) why.push('視窗捲動');
  if (a.sc !== b.sc) why.push('容器捲動');
  if (a.act !== b.act) why.push('焦點');
  if ((window.__taMut || []).length) why.push('DOM×' + window.__taMut.length);
  return why;
}
"""

# 量「點之前自己就在跳的節點」（時鐘、動畫、輪播），之後的 DOM 變化排除它們
NOISE_JS = r"""
(ms) => new Promise(res => {
  const set = new Set();
  const o = new MutationObserver((mm) => { for (const m of mm) { const t = m.target.nodeType === 1 ? m.target : m.target.parentElement; if (t && !(m.type === 'attributes' && m.attributeName === 'data-ta')) set.add(t); } });
  o.observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
  setTimeout(() => { o.disconnect(); window.__taNoise = [...set]; res([...set].slice(0, 12).map(t => (t.id ? '#' + t.id : '') + (t.className && t.className.baseVal === undefined ? '.' + String(t.className).split(' ')[0] : t.tagName))); }, ms);
})
"""

BLANK_JS = r"""
() => {
  const INTER = 'button,a[href],summary,label,select,input,textarea,[role=button],[role=tab],[role=link],[onclick]';
  for (let y = 120; y < innerHeight - 90; y += 31) for (let x = 6; x < innerWidth - 4; x += 23) {
    const h = document.elementFromPoint(x, y); if (!h) continue;
    if (h.closest(INTER) || h.closest('header,#tabs,nav,svg,canvas')) continue;
    let p = false; for (let n = h; n; n = n.parentElement) { if (getComputedStyle(n).cursor === 'pointer') { p = true; break; } }
    if (p) continue;
    return {x, y};
  }
  return null;
}
"""

BLANK_NOISE_JS = r"""
() => { const add = new Set(window.__taNoise || []);
  (window.__taMutNodes || []).forEach(n => add.add(n)); window.__taNoise = [...add];
  return (window.__taMutNodes || []).map(n => n.id || String(n.className).slice(0, 20) || n.tagName); }
"""

# 浮層：position:fixed 看得見的元素、role=dialog、[aria-modal]、以及幾個已知的彈出框
LAYERS_JS = r"""
() => {
  const out = [];
  const known = '#howPop,#morePop,#mSheet,#sugg,.morepop,.msheet,[role=dialog],[aria-modal=true],.popover,.drawer,.modal';
  const seen = new Set();
  const add = (e) => {
    if (seen.has(e)) return; seen.add(e);
    if (e.checkVisibility && !e.checkVisibility({opacityProperty: true, visibilityProperty: true})) return;
    const r = e.getBoundingClientRect(); if (r.width < 4 || r.height < 4) return;
    if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) return;
    const cs = getComputedStyle(e);
    if (!e.matches(known) && (e.matches('button,a,input,label,[role=button]') || r.width * r.height < 5000)) return;
    out.push({key: (e.id ? '#' + e.id : '') + '|' + e.tagName + '|' + String(e.className && e.className.baseVal === undefined ? e.className : ''),
              id: e.id, x: r.left, y: r.top, w: r.width, h: r.height, pe: cs.pointerEvents, op: +cs.opacity,
              bg: cs.backgroundColor, big: r.width * r.height > innerWidth * innerHeight * 0.5});
  };
  document.querySelectorAll(known).forEach(add);
  document.querySelectorAll('body *').forEach(e => { const p = getComputedStyle(e).position; if (p === 'fixed') add(e); });
  return out;
}
"""

MARK_LAYER_JS = r"""
(key) => {
  const id = key.split('|')[0];
  if (id && id.startsWith('#')) { const byId = document.getElementById(id.slice(1)); if (byId) { window.__taLayer = byId; return true; } }
  const all = [...document.querySelectorAll('body *')];
  const e = all.find(n => ((n.id ? '#' + n.id : '') + '|' + n.tagName + '|' + String(n.className && n.className.baseVal === undefined ? n.className : '')) === key);
  if (!e) return null;
  window.__taLayer = e;
  return true;
}
"""

# 被撐出去的可點元素：抽樣只點每一種長相的前兩顆，所以另外把「全部」掃一遍（不點，只量位置）——
# 一個本來只該上下捲的面板（抽屜、卡片）被裡面的東西撐寬，右邊的鈕整顆跑到面板外面，
# 要先橫向拖整塊面板才看得到。刻意做成橫捲的窄條（分頁列、晶片列，高度 < 120px）不算。
PUSHED_JS = r"""
() => {
  const out = [];
  (window.__taEls || []).forEach((e, i) => {
    if (!e.isConnected) return;
    const r = e.getBoundingClientRect();
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (!/(auto|scroll)/.test(cs.overflowX) || p.scrollWidth <= p.clientWidth + 8) continue;
      const pr = p.getBoundingClientRect();
      if (pr.height < 120) break;                              // 刻意的橫捲窄條
      // 刻意做成可以左右滑的寬表格／剖析圖（有淡出＋「左右滑」提示的那幾種，見 mobile3.js 的 SWIPE_SEL）
      if (p.matches('.hsc, .tw, .dgwrap, .m3-grid, #themeDiagram, #chainSwitch, #dgPick, #dgTools, #stockTabs, #skTools, .mpager')
          || (p.nextElementSibling && p.nextElementSibling.classList.contains('swipetip'))
          || (p.previousElementSibling && p.previousElementSibling.classList.contains('swipetip'))) break;
      if (r.left >= pr.right - 4 || r.right > pr.right + 24) {
        out.push({i, host: (p.id ? '#' + p.id : p.tagName.toLowerCase() + '.' + String(p.className).split(' ')[0]),
                  sw: p.scrollWidth, cw: p.clientWidth, x: Math.round(r.left - pr.left)});
      }
      break;
    }
  });
  return out;
}
"""

# 標記的浮層現在是不是開著（還在 DOM、看得見、而且在畫面裡 —— 收起來的抽屜多半只是被推到畫面外或 hidden）
LAYER_ON_JS = r"""
() => { const L = window.__taLayer; if (!L || !L.isConnected) return false;
  if (L.checkVisibility && !L.checkVisibility({visibilityProperty: true, opacityProperty: true})) return false;
  const r = L.getBoundingClientRect();
  return r.width > 4 && r.height > 4 && r.right > 0 && r.left < innerWidth && r.bottom > 0 && r.top < innerHeight; }
"""

# 找浮層裡的關閉鈕（×／關閉／取消／收起）
CLOSER_JS = r"""
() => {
  const L = window.__taLayer && window.__taLayer.isConnected ? window.__taLayer : null; if (!L) return null;
  // 關閉鈕通常在浮層裡；搜尋列這種「清單＋旁邊一顆取消」的，取消在浮層的父層（不找到 body 去）
  const scope = [L]; if (L.parentElement && L.parentElement !== document.body && L.parentElement !== document.documentElement) scope.push(L.parentElement);
  const bs = scope.flatMap(S => [...S.querySelectorAll('button,[role=button],a,.x,.close')]).filter(b => {
    const t = ((b.getAttribute('aria-label') || '') + ' ' + (b.textContent || '') + ' ' + (b.title || '')).trim();
    if (/刪除|移除|清除|delete|remove/i.test(t)) return false;      // 「刪掉這一筆」的 × 不是關浮層
    return /^[×✕✖╳xX]$|關閉|取消|收起|close/i.test(t.trim()) || /^[×✕✖╳]/.test((b.textContent || '').trim());
  }).filter(b => { const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  if (!bs.length) return null;
  // 寫明「關閉／取消／收起」的優先，光一個 × 的排後面（× 有時是「刪掉這一筆」）
  const pri = (b) => /關閉|取消|收起|close/i.test((b.getAttribute('aria-label') || '') + (b.textContent || '')) ? 0 : 1;
  bs.sort((a, b) => pri(a) - pri(b));
  const r = bs[0].getBoundingClientRect();
  return {x: r.left + r.width / 2, y: r.top + r.height / 2, t: (bs[0].textContent || bs[0].getAttribute('aria-label') || '').trim().slice(0, 8)};
}
"""

# 點外面：在浮層外找一個點，點下去不會碰到任何可點元素（避免「關浮層」變成「按了別的鈕」）
OUTSIDE_JS = r"""
() => {
  const L = window.__taLayer && window.__taLayer.isConnected ? window.__taLayer : null; if (!L) return null;
  const lr = L.getBoundingClientRect();
  // 浮層本身就是整片的背板（例如只量到 #howBack、氣泡在它上面）：點背板露出來的地方就是「點外面」
  if (lr.width >= innerWidth * 0.9 && lr.height >= innerHeight * 0.5 && /back|scrim|mask|shade|overlay/i.test(String(L.className) + L.id)) {
    for (let y = 70; y < innerHeight - 70; y += 37) for (let x = 8; x < innerWidth - 4; x += 29) {
      const h = document.elementFromPoint(x, y);
      if (h === L) return {x, y, on: (L.id ? '#' + L.id : '') + '.' + String(L.className).split(' ')[0]};
    }
    return null;
  }
  const INTER = 'button,a[href],summary,label,select,input,textarea,[role=button],[role=tab],[role=link],[onclick]';
  const isCand = (h) => { for (let n = h; n; n = n.parentElement) if (window.__taSet && window.__taSet.has(n)) return true; return false; };
  const pts = [];
  for (let y = 70; y < innerHeight - 70; y += 37) for (let x = 8; x < innerWidth - 4; x += 29) pts.push([x, y]);
  for (const [x, y] of pts) {
    if (x >= lr.left - 4 && x <= lr.right + 4 && y >= lr.top - 4 && y <= lr.bottom + 4) continue;
    const h = document.elementFromPoint(x, y); if (!h) continue;
    if (L.contains(h)) continue;
    // 背板（scrim：整片蓋住頁面、點了就關浮層的那一層）本身常常是 cursor:pointer，也會被列進可點元素 ——
    //   它就是「外面」，一定要能點；其他可點元素都跳過，免得「關浮層」變成「按了別的鈕」。
    const scrim = /back|scrim|mask|shade|overlay/i.test(String(h.className) + h.id) && h.getBoundingClientRect().width >= innerWidth * 0.9;
    if (!scrim && (h.closest(INTER) || isCand(h))) continue;
    if (!scrim && getComputedStyle(h).cursor === 'pointer') continue;
    // 不要點在 header／底部導覽上
    if (h.closest('header,.topbar,#tabs,nav')) continue;
    return {x, y, on: (h.id ? '#' + h.id : '') + '.' + String(h.className).split(' ')[0]};
  }
  return null;
}
"""


# ---------------------------------------------------------------------------- 畫面清單
def _stock_code() -> str:
    return os.environ.get("TW_MTAP_CODE", "2330")


def states(code: str | None = None) -> list[dict]:
    """要普查的畫面。每一個 = (名字, 網址 hash, 載入後依序要點的選擇器)。

    分段（總覽四步、各頁的 `.mpager` 分段、個股頁的分頁與分段）不在這裡手寫 ——
    `expand_states()` 載入每一頁之後自己去找分段列，一段一個畫面，網站加一段這裡自動跟上。"""
    code = code or _stock_code()
    base = [
        {"name": "總覽", "hash": "#overview"},
        {"name": "資金流向", "hash": "#flow"},
        {"name": "產業地圖", "hash": "#industry"},
        {"name": "熱力圖", "hash": "#heatmap"},
        {"name": "題材", "hash": "#themes"},
        {"name": "市場明細", "hash": "#market"},
        {"name": "週期統計", "hash": "#season"},
        {"name": "交付清單", "hash": "#delivery"},
        # ★ 2026-09-28：自選獨立成一頁（#watch，手機在「更多」裡；DECISIONS #274）—— 新的一頁要一起被普查
        {"name": "自選", "hash": "#watch"},
        {"name": f"個股{code}", "hash": f"#stock/{code}"},
        # ★ 2026-10-08 手機 v2（docs/mobile_v2_plan.md）：手機也走側欄子分頁 —— #flow／#heatmap 只會進第一個子頁，
        #   其他子頁與抽屜新開的入口（選股策略、財經日曆、ETF 三個子頁）要各自列進來，不然整頁沒被點過
        {"name": "資金分流樹", "hash": "#flow/sankey"},
        {"name": "族群×法人", "hash": "#flow/inst"},
        {"name": "財經日曆", "hash": "#earnings"},
        {"name": "選股策略", "hash": "#explore"},
        {"name": "ETF配息行事曆", "hash": "#etf/cal"},
        {"name": "ETF總覽", "hash": "#etf/list"},
        {"name": "ETF現金流試算", "hash": "#etf/inc"},
    ]
    for cid, nm in (("semiconductor", "半導體"), ("ai_server", "AI伺服器"), ("electronics", "一般電子"),
                    ("software", "軟體"), ("financial", "金融"), ("traditional", "傳產"),
                    ("infrastructure", "基礎建設")):
        base.append({"name": f"產業鏈-{nm}", "hash": f"#industry/{cid}"})
    return base


# 分段列：總覽的四步（.mspine）、每頁的分段（.mpager）、個股頁的分頁（#mbTabs）與分段（.mbseg）、
# 市場明細／大盤的分段（.mseg）、桌機個股分頁（#stockTabs）、以及任何 role=tablist。
# 每一列回傳一個唯一的選擇器與每顆鈕的 nth-child，呼叫端據此一段展開成一個畫面。
SEG_JS = r"""
() => {
  const path = (e) => {
    const seg = [];
    for (let n = e; n && n !== document.body; n = n.parentElement) {
      if (n.id) { seg.unshift('#' + CSS.escape(n.id)); return seg.join(' > '); }
      // 優先用「兄弟裡唯一的 class」—— 分段列是動態插進去的，nth-child 的位置每次載入可能不一樣
      const sib = [...n.parentElement.children];
      const uc = [...n.classList].find(c => !/^(on|sel|active|cur|open|mp-off)$/.test(c) && sib.filter(x => x.classList.contains(c)).length === 1);
      if (uc) { seg.unshift(n.tagName.toLowerCase() + '.' + CSS.escape(uc)); continue; }
      const k = sib.indexOf(n) + 1;
      seg.unshift(n.tagName.toLowerCase() + ':nth-child(' + k + ')');
    }
    return 'body > ' + seg.join(' > ');
  };
  const seen = new Set(), bars = [];
  document.querySelectorAll('.mspine, .mpager, #mbTabs, .mbseg, #stockTabs, .mseg, [role=tablist]').forEach((bar) => {
    if (seen.has(bar)) return; seen.add(bar);
    if (bar.closest('#mSheet, #howPop, #morePop, header, #tabs')) return;
    if (bar.checkVisibility && !bar.checkVisibility({visibilityProperty: true, opacityProperty: true})) return;
    const kids = [...bar.children];
    const bs = kids.map((b, i) => ({b, nth: i + 1})).filter(({b}) => b.matches('button,a,[role=tab]') && b.getBoundingClientRect().width > 0);
    if (bs.length < 2) return;
    const labels = bs.map(({b}) => (b.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 14));
    bars.push({sel: path(bar), key: (bar.id || bar.className) + '|' + labels.join(','),
               btns: bs.map(({b, nth}, i) => ({nth, label: labels[i],
                     on: b.matches('.on,.sel,.selected,.active,.cur,[aria-selected=true],[aria-current]:not([aria-current=false])')}))});
  });
  return bars;
}
"""


# ---------------------------------------------------------------------------- 主流程
class Auditor:
    def __init__(self, browser, base: str, width: int, log=print):
        self.b = browser
        self.base = base
        self.W, self.H = VIEWPORTS.get(width, (width, 844))
        self.rows: list[dict] = []        # 每一顆點過的元素一列
        self.small: list[dict] = []       # 觸控目標不足
        self.log = log
        self.errors: list[str] = []
        self.pg = None
        self.opened_layers: set[str] = set()
        self.states_done: list[dict] = []
        self.chrome_seen: dict[str, int] = {}   # 頂欄、底部導覽、頁尾、事件抽屜每一頁都一樣：全站只抽樣一次
        self.page_memo: dict[str, dict] = {}
        self.visited: set[str] = set()
        self.fps: set[str] = set()
        self.roots: set[str] = set()

    # ------------------------------------------------------------ 瀏覽器
    def new_page(self):
        if self.pg:
            try:
                self.pg.close()
            except Exception:  # noqa: BLE001
                pass
        pg = self.b.new_page(viewport={"width": self.W, "height": self.H}, device_scale_factor=2,
                             is_mobile=True, has_touch=True)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        pg.on("pageerror", lambda e: self.errors.append(f"{self.W}px pageerror @ {pg.url}: {e}"))
        # 每次整頁載入都把 localStorage 清回同一個起點（只留同意書、導覽、關掉即時輪詢）。
        # 不清的話，前一個畫面點過的分段會被網站記住（例如總覽記住停在第 ④ 步），
        # 下一個畫面一載入就不是它該有的樣子，分段列的選擇器也跟著對不上。
        pg.add_init_script("try{localStorage.clear();localStorage.setItem('tw.live.on','0');"
                           "localStorage.setItem('tw.consent',JSON.stringify({v:'*',at:'test'}));"
                           "localStorage.setItem('tw.tour','*');}catch(e){}")
        self.pg = pg
        return pg

    def load(self, st: dict, fresh: bool = True):
        pg = self.pg
        if fresh:
            pg.goto("about:blank")
            pg.goto(self.base + st["hash"], wait_until="networkidle")
        else:
            pg.evaluate("(h) => { location.hash = h; }", st["hash"])
        pg.wait_for_timeout(1800 if fresh else 900)
        for sel in st.get("steps", []):
            try:
                loc = pg.locator(sel).first
                loc.scroll_into_view_if_needed(timeout=3000)
                box = loc.bounding_box()
                if box:
                    pg.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                pg.wait_for_timeout(900)
            except Exception as e:  # noqa: BLE001
                self.errors.append(f"{self.W}px 畫面「{st['name']}」切不到分段 {sel}：{type(e).__name__}")
        pg.evaluate("() => { window.scrollTo({top: 0, behavior: 'instant'}); }")
        st["cur"] = pg.evaluate("() => location.hash")
        self.baseline()

    def baseline(self):
        """量雜訊：① 什麼都不做 600ms 內自己在跳的節點 ② 點一下空白處會被碰到的節點。
        之後點鈕時這些節點的變化不算「這顆鈕的反應」。每次載入（含換頁回來）都重量 —— 節點換新了。"""
        try:
            self.pg.evaluate(NOISE_JS, 600)
            bp = self.pg.evaluate(BLANK_JS)
            if bp:
                self.pg.evaluate(ARM_JS, "-1")
                self.pg.touchscreen.tap(bp["x"], bp["y"]); self.pg.wait_for_timeout(450)
                self.pg.evaluate(BLANK_NOISE_JS)
        except Exception:  # noqa: BLE001
            pass

    def walk(self, st: dict, depth: int = 0, used: frozenset = frozenset()):
        """載入一個畫面 → 記下它的分段列 → 普查這個畫面 → 每一段各自往下走（最多兩層）。
        一個畫面只載入一次（先找分段再普查，普查會改動畫面狀態）。"""
        self.load(st)
        cur = st.get("cur", st["hash"])
        # 分段鈕如果其實是「換到另一個網址」（產業地圖的鏈別晶片 → #industry/<鏈>），
        # 那個網址本身就是清單裡的一頁、或已經走過了，不要在這裡再走一次（白白重複又拖時間）
        if depth > 0 and cur != st.get("parent_cur") and (cur in self.visited or cur in self.roots):
            return
        fp = cur + "|" + self.pg.evaluate("""() => { const v = document.querySelector('main .view.on') || document.body;
            const t = (v.innerText || '').replace(/\\s+/g, ' '); return t.length + ':' + t.slice(0, 1500); }""")
        if depth > 0 and fp in self.fps:
            return
        self.fps.add(fp)
        self.visited.add(cur)
        bars = self.pg.evaluate(SEG_JS)
        t0 = time.time(); n0 = len(self.rows)
        try:
            self.run_state(st, loaded=True)
        except Exception as e:  # noqa: BLE001
            self.errors.append(f"{self.W}px 普查「{st['name']}」中途爆掉：{type(e).__name__} {e}")
            self.new_page()
        bad = [r for r in self.rows[n0:] if r["blocked"] or r["noreact"] or r["noclose"]]
        self.log(f"  [{self.W}px] {st['name']}：點了 {len(self.rows) - n0} 顆，{len(bad)} 顆有問題（{time.time() - t0:.0f}s）")
        if os.environ.get("TW_MTAP_VERBOSE"):
            for r in bad:
                self.log(f"      ✗ {r['page']}｜{r['txt']}｜{r['sel']}｜{r['blocked']}{'｜沒反應' if r['noreact'] else ''}{'｜' + r['noclose'] if r['noclose'] else ''}")
        self.states_done.append({"w": self.W, "name": st["name"], "n": len(self.rows) - n0, "bad": len(bad)})
        here = used | {b["key"] for b in bars}
        for bar in bars:
            if bar["key"] in used:
                continue
            for bt in bar["btns"]:
                if bt["on"]:
                    continue
                s2 = {"name": f"{st['name']}／{bt['label']}", "hash": st["hash"], "parent_cur": cur,
                      "steps": st.get("steps", []) + [f"{bar['sel']} > :nth-child({bt['nth']})"]}
                if depth < 2:
                    self.walk(s2, depth + 1, here)

    def expand(self, st: dict, depth: int = 0, used: frozenset = frozenset()) -> list[dict]:
        """載入一頁，把它的每一個分段各展開成一個畫面（往下最多兩層：步驟 → 分段 → 子分段）。"""
        self.load(st)
        bars = self.pg.evaluate(SEG_JS)
        out = [st]
        here = used | {b["key"] for b in bars}
        for bar in bars:
            if bar["key"] in used:
                continue
            for bt in bar["btns"]:
                if bt["on"]:
                    continue
                s2 = {"name": f"{st['name']}／{bt['label']}", "hash": st["hash"],
                      "steps": st.get("steps", []) + [f"{bar['sel']} > :nth-child({bt['nth']})"]}
                if depth < 2:
                    out.extend(self.expand(s2, depth + 1, here))
                else:
                    out.append(s2)
        return out

    # ------------------------------------------------------------ 一顆
    def tap_one(self, st: dict, it: dict, depth: int = 0) -> dict:
        pg = self.pg
        row = {"page": st["name"], "w": self.W, "sel": it["sel"], "txt": it["txt"], "size": f"{it['w']}×{it['h']}",
               "blocked": "", "noreact": False, "noclose": "", "react": "", "note": ""}
        # 外部連結／下載：不點（點了會離開本站或開新分頁），驗 href 有值
        href = it.get("href") or ""
        if href and not href.startswith("#") and not href.startswith("javascript"):
            row["react"] = "外部連結（不點，href 有值）" if href.strip() else ""
            if not href.strip():
                row["noreact"] = True
            return row
        r0 = pg.evaluate(REACH_JS, it["i"])
        if r0.get("gone"):
            row["note"] = "重畫後不在了（略過）"
            return row
        pg.wait_for_timeout(120)
        p = pg.evaluate(POINT_JS, it["i"])
        if p.get("gone"):
            row["note"] = "重畫後不在了（略過）"
            return row
        if p.get("off"):
            row["blocked"] = f"捲不進畫面（位置 {p.get('rect')}）"
            return row
        if p.get("nested"):
            ow = str(p.get("ownNo") or "")
            row["note"] = ((f"剖析圖零件本身被 {ow.split('|', 1)[1]} 壓住；它自己的編號 {ow[1:].split('|')[0]} 在圖上點得到（手機剖析圖以編號為入口）" if ow.startswith("~") else
                            "剖析圖的襯景：整組刻意設成不能點（pointer-events:none），不是按鈕" if ow == "=" else
                            f"疊在上面的是它自己的編號 {ow}（點編號＝開它的說明與台股）") if ow else
                           f"外框中心不在它身上（母框裡疊著子零件，或 SVG 群組中心是空白；打到 {p['by']}），改點它真正畫到的地方")
        if not p["ok"]:
            if p.get("anc"):
                row["blocked"] = f"自己 pointer-events:none，點下去落在祖先 {p['by']}"
            else:
                row["blocked"] = f"被 {p['by']} 蓋住（pointer-events:{p['byPe']}，opacity:{p['byOp']}）" + ("；角落點得到" if p.get("anyOk") else "") + (f"（{p['ownNo'][1:]}）" if str(p.get("ownNo", "")).startswith("!") else "")
        tw, th = it.get("tw", it["w"]), it.get("th", it["h"])
        if tw < MIN_TOUCH or th < MIN_TOUCH:
            sz = f"{it['w']}×{it['h']}" + (f"（觸控 {tw}×{th}）" if (tw, th) != (it["w"], it["h"]) else "")
            self.small.append({"page": st["name"], "w": self.W, "sel": it["sel"], "txt": it["txt"], "size": sz})
        layers0 = {L["key"] for L in pg.evaluate(LAYERS_JS)}
        pg.evaluate(ARM_JS, it["i"])
        url0 = pg.url
        if it.get("hasSel"):
            # 下拉選單：手機點下去開的是系統原生選單（不在 DOM 裡、Playwright 也看不到），
            # 所以「點得到」照上面驗中心點，「有反應」改成真的選另一個選項，看畫面有沒有跟著變。
            pg.evaluate("""(i) => { const __get = (i) => { const a = window.__taEls || [], e = a[+i]; if (e && e.isConnected) return e; const p = (window.__taPaths || [])[+i]; try { return p ? document.querySelector(p) : null; } catch (x) { return null; } }; let s = __get(i); if (s && s.tagName !== 'SELECT') s = s.querySelector('select, input[type=range]');
                if (!s) return;
                if (s.type === 'range') { const lo = +s.min || 0, hi = +(s.max || 100); s.value = (+s.value >= (lo + hi) / 2) ? lo : hi;
                  s.dispatchEvent(new Event('input', {bubbles: true})); s.dispatchEvent(new Event('change', {bubbles: true})); return; }
                if (s.options.length < 2) return;
                s.selectedIndex = (s.selectedIndex + 1) % s.options.length;
                s.dispatchEvent(new Event('input', {bubbles: true})); s.dispatchEvent(new Event('change', {bubbles: true})); }""", it["i"])
        else:
            pg.touchscreen.tap(p["x"], p["y"])
        why: list[str] = []
        t_end = time.time() + REACT_MS / 1000
        while time.time() < t_end:
            pg.wait_for_timeout(80)
            try:
                why = pg.evaluate(REACT_JS)
            except Exception:  # noqa: BLE001 —— 換頁途中
                why = ["網址"]
            if it.get("hasSel"):
                why = [w for w in why if w != "表單值"]
            if why:
                break
        pg.wait_for_timeout(150)
        try:
            why = pg.evaluate(REACT_JS) or why
        except Exception:  # noqa: BLE001
            pass
        if it.get("hasSel"):
            why = [w for w in why if w != "表單值"]      # 選項是我們自己換的，換了不算反應；要看畫面有沒有跟著變
        if not why and not it.get("hasSel") and not it.get("selected") and not it.get("tbl") and not row["blocked"]:
            # 沒反應先再點一次（剛載入的圖可能還在初始化；真的壞掉的鈕點兩次一樣沒反應）
            pg.wait_for_timeout(400)
            pg.evaluate(REACH_JS, it["i"]); pg.wait_for_timeout(120)
            p2 = pg.evaluate(POINT_JS, it["i"])
            if not p2.get("gone") and not p2.get("off") and p2.get("ok"):
                pg.evaluate(ARM_JS, it["i"])
                pg.touchscreen.tap(p2["x"], p2["y"])
                t_end = time.time() + REACT_MS / 1000
                while time.time() < t_end:
                    pg.wait_for_timeout(100)
                    try:
                        why = pg.evaluate(REACT_JS)
                    except Exception:  # noqa: BLE001
                        why = ["網址"]
                    if why:
                        row["note"] = "第一次點沒反應、第二次有（剛載入還在初始化）"
                        break
        row["react"] = "、".join(why)
        if not why:
            if it.get("selected"):
                row["note"] = "已選取的那顆（點了不變是正常）"
            elif any(pg.evaluate("(s) => { const __get = (i) => { const a = window.__taEls || [], e = a[+i]; if (e && e.isConnected) return e; const p = (window.__taPaths || [])[+i]; try { return p ? document.querySelector(p) : null; } catch (x) { return null; } }; const e = __get(s[0]); return !!e && e.matches(s[1]); }", [it["i"], k]) for k in EXEMPT):
                row["note"] = "白名單"
            elif it.get("tbl"):
                # 全站 CSS 給每一個 th 與 tbody tr 都掛了 cursor:pointer（桌機的樣式），但大部分表格沒有綁動作。
                # 手機看不到游標，這些格子長得就是一般表格，不是按鈕 —— 記下來、不算紅燈。
                row["note"] = "表格表頭／列（只有全站游標樣式，沒有綁動作，手機上不是按鈕）"
            elif not row["blocked"]:
                row["noreact"] = True
        # ---- 收得回來 ----
        self.settle()
        try:
            layers1 = pg.evaluate(LAYERS_JS)
        except Exception:  # noqa: BLE001
            layers1 = []
        new = [L for L in layers1 if L["key"] not in layers0]
        # 同一層只挑最大那塊（抽屜本體），背板另外處理
        body = [L for L in new if not L.get("big")] or [L for L in new if L.get("big") and L["pe"] != "none"]
        if pg.url != url0 and "#" in pg.url and pg.url.split("#")[1] != url0.split("#")[1]:
            row["react"] = row["react"] or "網址"
            row["_nav"] = True
        elif body:
            L = max(body, key=lambda z: z["w"] * z["h"])
            pg.evaluate(MARK_LAYER_JS, L["key"])
            row["react"] += f"；開了浮層 {L['key'].split('|')[0] or L['key'].split('|')[2][:20]}"
            if depth == 0 and L["key"] not in self.opened_layers:
                self.opened_layers.add(L["key"])
                row["_layer"] = L["key"]
            row["noclose"] = self.close_layer(L, layers0) or ""
        return row

    def settle(self, ms: int = 1500):
        """等畫面上的轉場動畫跑完（抽屜滑進來、淡入）。還在滑的抽屜位置不對，會量錯「開了什麼、外面在哪」。
        無限循環的動畫（掃描線、呼吸燈）不等。"""
        try:
            self.pg.wait_for_function("""() => !document.getAnimations().some(a => {
                if (a.playState !== 'running') return false;
                const t = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming() : null;
                return !(t && t.iterations === Infinity); })""", timeout=ms, polling=60)
        except Exception:  # noqa: BLE001 —— 逾時就照當下的畫面量
            pass

    def close_layer(self, L: dict, layers0: set) -> str:
        """回傳空字串＝關得掉；否則回傳原因。
        先按浮層裡的 ×／關閉／取消；按了還在（那顆 × 可能是「刪掉這一筆」而不是關浮層），再點外面。
        兩條路都關不掉才算「收不回來」。"""
        pg = self.pg
        tried = []

        def still_open() -> bool:
            pg.wait_for_timeout(200)
            self.settle()
            left = [x for x in pg.evaluate(LAYERS_JS) if x["key"] not in layers0]
            return any(x["key"] == L["key"] for x in left) and pg.evaluate(LAYER_ON_JS)

        c = pg.evaluate(CLOSER_JS)
        if c:
            pg.touchscreen.tap(c["x"], c["y"]); tried.append(f"按「{c['t']}」")
            if not still_open():
                return self._leftover(layers0, tried[-1])
        o = pg.evaluate(OUTSIDE_JS)
        if o:
            pg.touchscreen.tap(o["x"], o["y"]); tried.append(f"點外面（{o['on']}）")
            if not still_open():
                return self._leftover(layers0, tried[-1])
        if not tried:
            return "找不到可以點的外面，也沒有 × 鈕"
        return "、".join(tried) + "之後浮層還在"

    def _leftover(self, layers0: set, how: str) -> str:
        """浮層關了，但畫面上不准留下蓋住版面的一層（例如背板沒收）。"""
        left = [x for x in self.pg.evaluate(LAYERS_JS) if x["key"] not in layers0]
        cover = [x for x in left if x.get("big") and x["pe"] != "none"]
        if cover:
            return f"{how}之後留下蓋住版面的一層 {cover[0]['key']}"
        return ""

    # ------------------------------------------------------------ 一個範圍（整頁或浮層）
    @staticmethod
    def _keys(items: list[dict]) -> list[str]:
        cnt: dict[str, int] = {}
        out = []
        for it in items:
            # ★ 2026-10-06（既有紅字清理）：按鈕字裡的計數（「指標 ▾ （已開 2）」）會隨浮層裡點的東西變（開 2 → 3），
            #   重開浮層是用「這顆鈕的 key」去找它，字變了就找不到 → 「浮層重新打開失敗」（網站沒壞，是 key 跟著計數變）。
            #   key 一律把「已開 N」的數字抹成 N（只影響配對，不改報表上顯示的字）。
            k0 = it["sig"] + "|" + re.sub(r"已開 \d+", "已開 N", it["txt"])
            cnt[k0] = cnt.get(k0, 0) + 1
            out.append(k0 + "|" + str(cnt[k0]))
        return out

    def audit_scope(self, st: dict, scope: str | None, depth: int, restore, budget: int = 260):
        """一顆一顆點。每點完一顆就重新列一次（頁面常整段重畫，舊編號會掉）。
        restore()：把畫面帶回這個範圍可以繼續點的狀態（換頁了、浮層被關了都靠它）。"""
        pg = self.pg
        # 同一頁（同一個網址 hash）的各分段共用計數：每一段都看得到的元素（總覽的輪盤、事件區…）一頁只抽樣一次；
        # 只有這一段才有的元素照樣會被點到。浮層裡（depth 1）各自計數。
        pk = (st["hash"] if depth == 0 else "layer:" + st["name"])
        memo = self.page_memo.setdefault(pk, {"tested": set(), "sigcnt": {}, "sigbad": set()})
        tested: set[str] = memo["tested"]
        sigcnt: dict[str, int] = memo["sigcnt"]
        sigbad: set[str] = memo["sigbad"]
        retry: dict[str, int] = {}
        pushed_done: set[str] = memo.setdefault("pushed", set())
        first = True
        for _ in range(budget):
            if scope and not (pg.evaluate(LAYER_ON_JS) if scope == "__layer__" else pg.evaluate("(s) => !!document.querySelector(s)", scope)):
                if not restore():
                    self.errors.append(f"{self.W}px「{st['name']}」浮層重新打開失敗，裡面沒點完")
                    return
            items = pg.evaluate(ENUM_JS, scope)
            if first:
                first = False
                keys = self._keys(items)
                for q in pg.evaluate(PUSHED_JS):
                    it0, k0 = items[q["i"]], keys[q["i"]]
                    if k0 in pushed_done:
                        continue
                    pushed_done.add(k0)
                    self.rows.append({"page": st["name"], "w": self.W, "sel": it0["sel"], "txt": it0["txt"],
                                      "size": f"{it0['w']}×{it0['h']}", "react": "", "note": "", "noreact": False, "noclose": "",
                                      "blocked": f"被撐到 {q['host']} 右邊外面（內容 {q['sw']}px／面板 {q['cw']}px），要先橫向拖整塊才點得到"})
            nxt = None
            for it, k in zip(items, self._keys(items)):
                if k in tested:
                    continue
                cnt = self.chrome_seen if (it.get("chrome") and depth == 0) else sigcnt
                ck = it["sig"] + ("|" + it["txt"] if cnt is self.chrome_seen else "")
                c = cnt.get(ck, 0)
                lim = SAMPLE + (12 if it["sig"] in sigbad else 0)
                if c >= lim:
                    continue
                nxt = (it, k); break
            if not nxt:
                self._reach_sweep(st, items, tested, memo)
                return
            it, k = nxt
            cnt = self.chrome_seen if (it.get("chrome") and depth == 0) else sigcnt
            ck = it["sig"] + ("|" + it["txt"] if cnt is self.chrome_seen else "")
            tested.add(k); cnt[ck] = cnt.get(ck, 0) + 1
            _t = time.time()
            row = self.tap_one(st, it, depth)
            if os.environ.get("TW_MTAP_DEBUG"):
                print(f"        · {time.time() - _t:4.1f}s d{depth} {it['sel'][:60]}｜{it['txt'][:16]}｜{row['react'][:40]}｜{row['blocked'][:40]}{'｜沒反應' if row['noreact'] else ''}{row['noclose']}", flush=True)
            if row["note"].startswith("重畫後不在了") and retry.get(k, 0) < 2:
                retry[k] = retry.get(k, 0) + 1
                tested.discard(k); cnt[ck] -= 1
                continue
            if row["blocked"] or row["noreact"] or row["noclose"]:
                sigbad.add(it["sig"])
            layer = row.pop("_layer", None)
            nav = row.pop("_nav", False)
            row.pop("_open", None)
            self.rows.append(row)
            if layer and depth == 0:
                # 浮層裡面的鈕：重新打開它，普查一層
                opener_key = k
                def reopen(opener_key=opener_key, layer=layer):
                    return self._reopen(st, opener_key, layer)
                if reopen():
                    lst = dict(st); lst["name"] = st["name"] + "／浮層「" + (it["txt"] or it["sel"])[:12] + "」"
                    self.audit_scope(lst, "__layer__", 1, reopen, budget=60)
                    # 普查完把浮層關掉（關不掉的已經在上面那一列記過了）
                    if pg.evaluate(LAYER_ON_JS):
                        L = {"key": layer}
                        self.close_layer(L, set())
                pg.evaluate("() => { window.__taLayer = null; }")
                restore()
            elif nav:
                restore()
            elif it.get("seg") and row["react"] and depth == 0:
                restore(force=True)

    def _reach_sweep(self, st: dict, items: list[dict], tested: set, memo: dict, cap: int = 40):
        """抽樣沒點到的其他元素：不點，只量「捲到中央之後中心點打不打得到它」。
        同一種長相只點前兩顆是為了時間，但「被別的東西蓋住」是一顆一顆不一樣的（例如剖析圖上某個零件剛好被別人的編號壓住），
        所以位置每一顆都量；只有點不到的才記一列。"""
        pg = self.pg
        swept: set[str] = memo.setdefault("swept", set())
        per: dict[str, int] = {}
        for it, k in zip(items, self._keys(items)):
            if k in tested or k in swept or it.get("href", "").startswith(("http", "mailto", "tel")):
                continue
            if it.get("chrome"):
                continue
            per[it["sig"]] = per.get(it["sig"], 0) + 1
            if per[it["sig"]] > cap:
                continue
            swept.add(k)
            if pg.evaluate(REACH_JS, it["i"]).get("gone"):
                continue
            p = pg.evaluate(POINT_JS, it["i"])
            if p.get("gone"):
                continue
            ow = str(p.get("ownNo") or "")
            if p.get("ok") and ow.startswith("~"):
                # 零件本身被壓住、但它自己的編號點得到：不算紅，記一列備註（報告另外列一張表，讓人看得到有哪些）
                self.rows.append({"page": st["name"], "w": self.W, "sel": it["sel"], "txt": it["txt"], "size": f"{it['w']}×{it['h']}",
                                  "react": "", "noreact": False, "noclose": "", "blocked": "",
                                  "note": f"剖析圖零件本身被 {ow.split('|', 1)[1]} 壓住；它自己的編號 {ow[1:].split('|')[0]} 在圖上點得到（手機剖析圖以編號為入口）"})
                continue
            if p.get("ok"):
                continue
            if p.get("off"):
                why = f"捲不進畫面（位置 {p.get('rect')}）"
            elif p.get("anc"):
                why = f"自己 pointer-events:none，點下去落在祖先 {p['by']}"
            else:
                why = (f"被 {p['by']} 蓋住（pointer-events:{p['byPe']}，opacity:{p['byOp']}）" + ("；角落點得到" if p.get("anyOk") else "")
                       + (f"（{p['ownNo'][1:]}）" if str(p.get("ownNo", "")).startswith("!") else ""))
            self.rows.append({"page": st["name"], "w": self.W, "sel": it["sel"], "txt": it["txt"], "size": f"{it['w']}×{it['h']}",
                              "react": "", "note": "只量位置（同一種長相已經點過）", "noreact": False, "noclose": "", "blocked": why})

    def _reopen(self, st: dict, opener_key: str, layer: str) -> bool:
        """在整頁範圍裡找到開這個浮層的那顆鈕，再點一次，把浮層標起來。"""
        pg = self.pg
        for attempt in range(2):
            if attempt:
                self.load(st)
            if pg.evaluate(LAYER_ON_JS):
                return True
            items = pg.evaluate(ENUM_JS, None)
            for it, k in zip(items, self._keys(items)):
                if k == opener_key:
                    pg.evaluate(REACH_JS, it["i"]); pg.wait_for_timeout(120)
                    p = pg.evaluate(POINT_JS, it["i"])
                    if p.get("gone") or p.get("off"):
                        break
                    pg.touchscreen.tap(p["x"], p["y"]); pg.wait_for_timeout(300); self.settle()
                    if pg.evaluate(MARK_LAYER_JS, layer) and pg.evaluate(LAYER_ON_JS):
                        return True
                    if attempt and os.environ.get("TW_MTAP_DEBUG"):   # 第一次沒重新載入（可能還停在別頁），失敗是預期的
                        print(f"        ↻ 重開浮層 {layer} 失敗（第 {attempt + 1} 次）：點了 {opener_key[:50]}，浮層沒出現", flush=True)
                    break
            else:
                if attempt and os.environ.get("TW_MTAP_DEBUG"):
                    print(f"        ↻ 重開浮層 {layer} 失敗（第 {attempt + 1} 次）：找不到開它的那顆 {opener_key[:60]}；"
                          f"同一種的有 {[k for k in self._keys(items) if k.rsplit('|', 2)[0] == opener_key.rsplit('|', 2)[0]][:3]}", flush=True)
        return False

    def run_state(self, st: dict, loaded: bool = False):
        if not loaded:
            self.load(st)

        def restore(force: bool = False):
            cur = "#" + self.pg.url.split("#", 1)[1] if "#" in self.pg.url else ""
            if force or cur != st.get("cur", st["hash"]):
                self.load(st, fresh=bool(st.get("steps")) or force)
            return True
        self.audit_scope(st, None, 0, restore)


def _plog(*a, **k):
    print(*a, **k, flush=True)


def run_audit(browser, base: str, widths=(390, 360), only: str = "", log=_plog, code: str | None = None):
    res = {"rows": [], "small": [], "errors": [], "states": []}
    for w in widths:
        a = Auditor(browser, base, w, log=log)
        a.new_page()
        a.roots = {x["hash"] for x in states(code)}
        for st in states(code):
            if only and only not in st["name"]:
                continue
            try:
                a.walk(st)
            except Exception as e:  # noqa: BLE001
                a.errors.append(f"{w}px 走訪「{st['name']}」失敗：{type(e).__name__} {e}")
                a.new_page()
        res["states"] += a.states_done
        res["rows"] += a.rows; res["small"] += a.small; res["errors"] += a.errors
        try:
            a.pg.close()
        except Exception:  # noqa: BLE001
            pass
    return res


def is_dg_part(r: dict) -> bool:
    """剖析圖上的零件圖形（SVG 的 g[data-part]）。

    手機版剖析圖的入口是**編號鈕**（Andy 2026-09-24：「2D 3D 圖那麼多說明可以使用編號顯示就好，
    想知道再點編號，編號就會給出答案」；docs/mobile_v3_spec.md「剖析圖只留編號」）。
    零件圖形本身在手機上沒有任何「可以點」的外觀（沒有游標、沒有框），它能不能點是桌機的互動；
    所以零件被疊圖／別人的編號壓住、或點了沒反應，**記在報告的另一張表，不算紅燈**。
    編號鈕（button.mnum）本身照樣是一顆一顆嚴格驗：點得到、點了開得出說明、關得掉。"""
    sel = r.get("sel") or ""
    return sel.startswith("g") and "[data-part=" in sel


def problems(res: dict) -> list[dict]:
    return [r for r in res["rows"] if (r["blocked"] or r["noreact"] or r["noclose"]) and not is_dg_part(r)]


def write_report(res: dict, path: Path = OUT):
    path.mkdir(parents=True, exist_ok=True)
    (path / "report.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    P = problems(res)
    L = ["# 手機按鈕普查", "", f"點過 {len(res['rows'])} 顆；有問題 {len(P)} 顆；觸控目標 < {MIN_TOUCH}px 的 {len(res['small'])} 顆。", ""]
    L += ["## 有問題的", "", "| 頁面 | 按鈕文字／選擇器 | 寬度 | 點不到的原因 | 沒反應 | 收不回來 |", "|---|---|---|---|---|---|"]
    for r in P:
        L.append(f"| {r['page']} | {r['txt']}　`{r['sel']}` | {r['w']} | {r['blocked']} | {'是' if r['noreact'] else ''} | {r['noclose']} |")
    G = [r for r in res["rows"] if is_dg_part(r) and (r["blocked"] or r["noreact"] or r["noclose"])]
    L += ["", f"## 剖析圖零件圖形：點不到或點了沒反應（{len(G)} 列，不算紅燈 —— 手機剖析圖的入口是編號，見 is_dg_part）", "",
          "| 頁面 | 零件 | 寬度 | 點不到的原因 | 沒反應 |", "|---|---|---|---|---|"]
    for r in G:
        L.append(f"| {r['page']} | {r['txt']}　`{r['sel']}` | {r['w']} | {r['blocked']} | {'是' if r['noreact'] else ''} |")
    D = [r for r in res["rows"] if r["note"].startswith("剖析圖零件本身被")]
    L += ["", f"## 剖析圖零件本身被壓住、但它自己的編號點得到（{len(D)} 列，不算紅燈）", "",
          "手機剖析圖的入口是編號（2026-09-24 拍板）；這些零件直接點圖形會點到上面那一層，點它的編號才拿得到說明與台股。", "",
          "| 頁面 | 零件 | 寬度 | 說明 |", "|---|---|---|---|"]
    for r in D:
        L.append(f"| {r['page']} | `{r['sel']}` | {r['w']} | {r['note']} |")
    T = [r for r in res["rows"] if r["note"].startswith(("表格表頭", "白名單", "剖析圖的襯景", "第一次點沒反應"))]
    L += ["", f"## 點了不變、判斷為不是按鈕或設計如此（{len(T)} 列）", "", "| 頁面 | 元素 | 寬度 | 理由 |", "|---|---|---|---|"]
    for r in T:
        L.append(f"| {r['page']} | {r['txt']}　`{r['sel']}` | {r['w']} | {r['note']} |")
    L += ["", f"## 觸控目標 < {MIN_TOUCH}px（列表，不算紅燈）", "", "| 頁面 | 按鈕 | 寬度 | 大小 |", "|---|---|---|---|"]
    seen = set()
    for s in res["small"]:
        k = (s["sel"], s["w"])
        if k in seen:
            continue
        seen.add(k)
        L.append(f"| {s['page']} | {s['txt']}　`{s['sel']}` | {s['w']} | {s['size']} |")
    if res["errors"]:
        L += ["", "## 執行錯誤", ""] + [f"- {e}" for e in res["errors"]]
    (path / "report.md").write_text("\n".join(L), encoding="utf-8")


def run_parallel(base: str, widths=(390, 360), only: str = "", code: str | None = None, log=_plog) -> dict:
    """每種寬度各開一個子行程同時跑（各自一個 Chromium），跑完合併。
    一種寬度一輪 30～60 分鐘，兩種依序跑要兩倍；同時跑只多吃一個瀏覽器的記憶體。
    ⚠ 呼叫端要自己持有 /tmp/claude-0/browser.lock（子行程不再搶鎖，不然會自己卡死自己）。"""
    import subprocess
    import tempfile
    procs = []
    tmpd = Path(tempfile.mkdtemp(prefix="mtap_"))
    for w in widths:
        out = tmpd / f"{w}.json"
        cmd = [sys.executable, str(Path(__file__).resolve()), "--width", str(w), "--base", base, "--json", str(out),
               "--code", code or _stock_code()]
        if only:
            cmd += ["--only", only]
        lf = open(tmpd / f"{w}.log", "w", encoding="utf-8")
        procs.append((w, out, subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, cwd=str(ROOT)), lf))
    res = {"rows": [], "small": [], "errors": [], "states": []}
    for w, out, pr, lf in procs:
        pr.wait(); lf.close()
        try:
            r = json.loads(out.read_text(encoding="utf-8"))
            for k in res:
                res[k] += r.get(k, [])
        except Exception as e:  # noqa: BLE001
            tail = (tmpd / f"{w}.log").read_text(encoding="utf-8", errors="replace")[-1500:]
            res["errors"].append(f"{w}px 子行程沒有交回結果（{type(e).__name__}）：{tail}")
        log(f"  [{w}px] 子行程結束：log 在 {tmpd / f'{w}.log'}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", default="390,360")
    ap.add_argument("--only", default="")
    ap.add_argument("--code", default="2330")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--base", default="", help="已經在跑的網站（子行程用）；空的就自己起一個本機伺服器")
    ap.add_argument("--json", default="", help="把結果寫到這個檔（子行程用），不印總結")
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    widths = tuple(int(x) for x in args.width.split(","))
    srv = None
    from scripts import _uitest as U
    if args.base:
        base = args.base
    else:
        if os.environ.get("TW_MTAP_SITE"):          # 量「修改前」的快照：指到另一份 site/
            U.SITE = Path(os.environ["TW_MTAP_SITE"])
        srv = U.serve(); time.sleep(0.3)
        base = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    t0 = time.time()
    if len(widths) > 1:
        res = run_parallel(base, widths, args.only, args.code)
    else:
        from playwright.sync_api import sync_playwright
        U._preset_consent()
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", headless=not args.headed)
            res = run_audit(b, base, widths, args.only, code=args.code)
            b.close()
    if srv:
        srv.shutdown()
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        return 0
    write_report(res)
    P = problems(res)
    print(f"\n===== 手機按鈕普查（{time.time() - t0:.0f} 秒）：點過 {len(res['rows'])} 顆，{len(P)} 顆有問題，"
          f"觸控目標不足 {len(res['small'])} 顆 =====")
    for r in P:
        print(f"  - [{r['w']}] {r['page']}｜{r['txt']}｜{r['sel']}｜{r['blocked']}{'｜沒反應' if r['noreact'] else ''}{'｜' + r['noclose'] if r['noclose'] else ''}")
    for e in res["errors"]:
        print("  ! " + e)
    print(f"報告：{OUT / 'report.md'}")
    return 1 if P or res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
