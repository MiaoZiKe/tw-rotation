"""剖析圖覆蓋普查：所有 2D／3D 剖析圖的「文字被蓋、文字蓋圖、文字互疊、文字超出格子」量測。

為什麼有這支（Andy 2026-09-26）
--------------------------------
> 「請檢查所有 2D 3D 圖說明有沒有覆蓋現象」
他抓到的例子：第三代半導體 → 展開「① 另外兩種做法」→ 左格「溝槽閘：把閘極挖進去」的三行說明
被正下方的溝槽閘剖面圖蓋住（剖面頂部的金屬層壓在第 2～3 行字上）。
那是「兩段各自畫對、疊在一起才錯」的錯 —— 眼睛掃過去不一定看得到，所以要用量的。

量什麼（容許 ≤ 2px）
--------------------
2D（SVG ＋ 外掛成 HTML 的說明卡）
  · 文字被圖形蓋住：畫在文字**之後**的圖形（rect／path／polygon…）真的塗到文字上。
    用 `isPointInFill`／`isPointInStroke` 對文字框內的格點逐點打 —— 量的是**圖形真正塗到的地方**，
    不是外框（一條 L 形引線的外框會蓋住半張圖，用外框量會誤報一大堆）。
  · 文字跨在圖形邊緣：畫在文字**之前**的圖形只墊到文字的一部分（兩邊都 > 2px）——
    字一半在色塊上、一半在外面。整段字都在色塊上（標籤印在零件上）是設計，不算。
  · 文字互疊：兩個文字的字身框（字級高、不是含行距的外框）交疊。
  · 文字超出所屬格子：字的中心在某個 `rect.frame`／`rect.bg` 裡，字框卻伸出去。
  · 文字超出畫布：伸出 SVG 可見範圍（會被切掉）。
  · 說明卡：卡片互蓋、卡片蓋到畫布、卡片裡的字伸出卡片、圖頭蓋到畫布。
  · 手機（≤640px）的編號鈕：鈕與鈕互蓋。
3D
  · 說明卡互蓋、卡片裡的字伸出卡片。
  · 說明卡蓋到畫布裡**看得見的零件**：先把標籤層藏起來截一張畫布，跟背景色差夠大的像素＝零件，
    再數每張卡片底下壓了多少零件像素。

用法
----
    python scripts/_dg_overlap.py                          # 全部：所有鏈與題材 × 1440,1100,800,390 × 2D／3D
    python scripts/_dg_overlap.py --only wide_bandgap      # 只量某幾張（逗號分隔，子字串比對）
    python scripts/_dg_overlap.py --width 1440,800 --no-3d
    python scripts/_dg_overlap.py --pal read               # 閱讀模式（字大一階；預設 tech,read 兩種都量）

輸出在 `docs/_dg_overlap/`（gitignore 同 docs/_show）：`report.json`、`report.md`、每個問題一張放大截圖。
**這支不進 pytest**（它要瀏覽器）；`scripts/_uitest.py` 的「剖析圖覆蓋普查」段落 import 這裡的 `audit()`。
白名單寫在下面的 `WHITELIST`，每一條都要寫理由。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = Path(os.environ.get("TW_DGOV_SITE") or (ROOT / "site"))       # 量修改前的快照時指到別的資料夾
OUT = Path(os.environ.get("TW_DGOV_OUT") or (ROOT / "docs" / "_dg_overlap"))
PORT = int(os.environ.get("TW_DGOV_PORT", "8793"))
TOL = 2.0

# ★ 白名單：真的無法避免、而且判斷過「不是錯」的，寫在這裡並寫理由。
#   鍵＝(圖 id, 問題種類, 元素 a 的描述開頭)。描述開頭用子字串比對。
WHITELIST: list[tuple[str, str, str, str]] = [
    # (圖 id, 種類, a 描述的子字串, 理由)
]

# --------------------------------------------------------------------------- 頁內量測（2D）
AUDIT2D_JS = r"""(opt) => {
  const TOL = opt.tol;
  const host = document.querySelector(opt.host);
  if (!host) return { err: 'no host ' + opt.host };
  const issues = [];
  const sx = window.scrollX, sy = window.scrollY;
  const R = (r) => ({ x: r.left + sx, y: r.top + sy, w: r.right - r.left, h: r.bottom - r.top });
  const inter = (a, b) => { const x0 = Math.max(a.left, b.left), x1 = Math.min(a.right, b.right), y0 = Math.max(a.top, b.top), y1 = Math.min(a.bottom, b.bottom);
    return (x1 > x0 && y1 > y0) ? { left: x0, right: x1, top: y0, bottom: y1, width: x1 - x0, height: y1 - y0 } : null; };
  const union = (a, b) => ({ left: Math.min(a.left, b.left), top: Math.min(a.top, b.top), right: Math.max(a.right, b.right), bottom: Math.max(a.bottom, b.bottom),
    width: Math.max(a.right, b.right) - Math.min(a.left, b.left), height: Math.max(a.bottom, b.bottom) - Math.min(a.top, b.top) });
  const clip = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n) + '…' : s; };
  const secOf = (n) => { const f = n.closest && n.closest('[data-fold]'); if (!f) return '主畫面';
    const id = f.getAttribute('data-fold'); const bar = host.querySelector(`g.dgfold[data-fold="${id}"] .hd`);
    return bar ? clip(bar.textContent, 18) : id; };
  const partOf = (n) => { const p = n.closest && n.closest('[data-part]'); return p ? p.getAttribute('data-part') : ''; };
  const descShape = (n) => { const c = (n.getAttribute('class') || '').trim(); const pt = partOf(n);
    return `<${n.tagName}${c ? '.' + c.split(/\s+/).join('.') : ''}>${pt ? ' @' + pt : ''}`; };
  const descText = (n) => '「' + clip(n.textContent, 26) + '」';
  const SKIP_ANC = 'defs,clipPath,mask,marker,pattern,symbol,title,.lrow.ext,text';
  function shown(n, svg) {
    for (let p = n; p && p !== svg.parentNode; p = p.parentNode) {
      if (p.nodeType !== 1) continue;
      if (p.getAttribute && p.getAttribute('display') === 'none') return false;
      const cs = getComputedStyle(p);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    }
    return true;
  }
  function opac(n, svg) { let o = 1; for (let p = n; p && p !== svg; p = p.parentNode) { if (p.nodeType !== 1) continue; const v = parseFloat(getComputedStyle(p).opacity); if (Number.isFinite(v)) o *= v; } return o; }
  const out = { issues, texts: 0, shapes: 0, svgs: 0 };
  const svgs = [...host.querySelectorAll('svg.dg')].filter(s => !s.closest('.xmini') && s.getBoundingClientRect().width > 0);
  const allTexts = [];
  svgs.forEach((svg) => {
    out.svgs++;
    const svr = svg.getBoundingClientRect();
    // 可見範圍：SVG 本身 ∩ 捲動容器（.dgcanvas 在窄畫面會左右捲）—— 捲到外面的不算「超出畫布」，那是捲動
    const texts = [...svg.querySelectorAll('text')].filter(t => t.textContent.trim() && !t.closest(SKIP_ANC.replace(',text', '')) && shown(t, svg) && opac(t, svg) > 0.2)
      .map(t => {
        const r = t.getBoundingClientRect(); if (!r.width || !r.height) return null;
        const m = t.getScreenCTM(); const k = m ? Math.hypot(m.a, m.b) : 1;
        const fs = parseFloat(getComputedStyle(t).fontSize) * k;
        // 字身框：外框含上下行距（約 1.17 倍字級），量互疊與覆蓋時收到字級高（置中）
        const pad = Math.max(0, (r.height - fs) / 2);
        const tight = { left: r.left + 0.5, right: r.right - 0.5, top: r.top + pad, bottom: r.bottom - pad };
        tight.width = tight.right - tight.left; tight.height = tight.bottom - tight.top;
        return { el: t, r, tight };
      }).filter(Boolean);
    out.texts += texts.length;
    texts.forEach((t) => allTexts.push(t));          // 錨點號碼也算：別條引線從隔壁編號中間穿過，號碼一樣被劃掉
    const SHAPES = 'rect,path,circle,ellipse,polygon,polyline,line,image,use';
    const W0 = svr.width * svr.height;
    const shapes = [...svg.querySelectorAll(SHAPES)].filter(s => !s.closest(SKIP_ANC) && !s.querySelector('animateMotion,animate') && shown(s, svg))
      .map(s => {
        const r = s.getBoundingClientRect(); if (!r.width && !r.height) return null;
        if (r.width * r.height > W0 * 0.85) return null;               // 整張畫布的底色
        const cs = getComputedStyle(s);
        const o = opac(s, svg);
        const fo = parseFloat(cs.fillOpacity), so = parseFloat(cs.strokeOpacity);
        const clear = (v) => !v || v === 'none' || v === 'transparent' || /rgba\([^)]*,\s*0\)$/.test(v);   // 透明色＝沒塗
        // 顏色本身帶的透明度（rgba 的第四個數）也要乘進去：柔陰影（.fxsh，blur 過的 18% 黑）不算「蓋住字」
        const alpha = (v) => { const m = /rgba\([^)]*,\s*([\d.]+)\)$/.exec(v || ''); return m ? parseFloat(m[1]) : 1; };
        const fill = !clear(cs.fill) && fo * o * alpha(cs.fill) > 0.3;
        const sw = parseFloat(cs.strokeWidth) || 0;
        const stroke = !clear(cs.stroke) && sw > 0 && so * o * alpha(cs.stroke) > 0.3;
        const geo = typeof s.isPointInFill === 'function';
        if (!fill && !stroke && s.tagName !== 'image' && s.tagName !== 'use') return null;
        return { el: s, r, fill, stroke, geo, sw };
      }).filter(Boolean);
    out.shapes += shapes.length;
    const pt = svg.createSVGPoint ? svg.createSVGPoint() : null;
    const STEP = 1.5;
    function hitGrid(sh, box) {
      // 回傳 box 內格點「被 sh 塗到」的統計
      const m = sh.el.getScreenCTM && sh.el.getScreenCTM(); const inv = m ? m.inverse() : null;
      let hx0 = 1e9, hy0 = 1e9, hx1 = -1e9, hy1 = -1e9, nx0 = 1e9, ny0 = 1e9, nx1 = -1e9, ny1 = -1e9, hit = 0, tot = 0;
      for (let y = box.top + STEP / 2; y < box.bottom; y += STEP) {
        for (let x = box.left + STEP / 2; x < box.right; x += STEP) {
          tot++;
          let h = false;
          if (sh.geo && inv && pt) {
            pt.x = x; pt.y = y; const q = pt.matrixTransform(inv);
            try { h = (sh.fill && sh.el.isPointInFill(q)) || (sh.stroke && sh.el.isPointInStroke(q)); } catch (e) { h = false; }
          } else {
            h = x >= sh.r.left && x <= sh.r.right && y >= sh.r.top && y <= sh.r.bottom;
          }
          if (h) { hit++; if (x < hx0) hx0 = x; if (x > hx1) hx1 = x; if (y < hy0) hy0 = y; if (y > hy1) hy1 = y; }
          else { if (x < nx0) nx0 = x; if (x > nx1) nx1 = x; if (y < ny0) ny0 = y; if (y > ny1) ny1 = y; }
        }
      }
      const dh = hit ? Math.min(hx1 - hx0, hy1 - hy0) + STEP : 0;
      const dn = (tot - hit) ? Math.min(nx1 - nx0, ny1 - ny0) + STEP : 0;
      return { hit, tot, dh, dn, hbox: hit ? { left: hx0, top: hy0, right: hx1, bottom: hy1, width: hx1 - hx0, height: hy1 - hy0 } : null };
    }
    const FOLLOW = Node.DOCUMENT_POSITION_FOLLOWING;
    texts.forEach((T) => {
      const tb = T.tight;
      // ① 圖形 vs 文字
      const below = [];
      shapes.forEach((S) => {
        if (S.el.contains(T.el) || T.el.contains(S.el)) return;
        const I = inter(tb, S.r); if (!I || I.width <= TOL || I.height <= TOL) return;
        const above = !!(T.el.compareDocumentPosition(S.el) & FOLLOW);   // S 在 T 之後 → 畫在上面
        const g = hitGrid(S, above ? I : tb);
        if (!g.hit) return;
        if (above) {
          if (g.dh > TOL) issues.push({ kind: '文字被圖形蓋住', sec: secOf(T.el), a: descText(T.el), b: descShape(S.el), px: +g.dh.toFixed(1), rect: R(union(T.r, g.hbox)) });
        } else below.push({ S, g });
      });
      /* 底下的圖形：由上往下看，碰到第一塊「整段字都墊在上面」的實心底圖就停 ——
         它下面的東西被它整個隔開了（編號圓點印在零件上、標籤框印在剖面上，都是這種）。*/
      // 編號圓點裡的號碼：它的底就是自己那顆圓（可能被調淡），圓點之間互蓋另外由 ⑤ 量，這裡不再拿底下的零件比
      if (T.el.classList.contains('non')) below.length = 0;
      below.sort((p, q) => (p.S.el.compareDocumentPosition(q.S.el) & FOLLOW) ? 1 : -1);   // 上面（後畫）的排前面
      for (const { S, g } of below) {
        if (S.fill && g.dn <= TOL) break;
        /* 圓形底（編號圓點、圓形標籤）：矩形字框的四個角本來就一定在圓外 —— 字寬塞得進直徑、
           圓蓋住字框六成以上，就當成「字印在圓上」，跟實心底圖同一種處理。*/
        const tg = S.el.tagName;
        if (S.fill && (tg === 'circle' || tg === 'ellipse') && g.hit / g.tot >= 0.6 && tb.width <= S.r.width + TOL) break;
        if (S.fill) {
          if (g.dh > TOL && g.dn > TOL) issues.push({ kind: '文字跨在圖形邊緣', sec: secOf(T.el), a: descText(T.el), b: descShape(S.el), px: +Math.min(g.dh, g.dn).toFixed(1), rect: R(union(T.r, S.r.width * S.r.height < 4 * T.r.width * T.r.height ? S.r : T.r)) });
        } else if (S.sw > TOL + 0.5 && g.dh > TOL) {
          issues.push({ kind: '文字壓在粗線上', sec: secOf(T.el), a: descText(T.el), b: descShape(S.el), px: +g.dh.toFixed(1), rect: R(T.r) });
        }
      }
      // ② 所屬格子：字的中心落在哪個 frame／bg 裡（取最小的那個），字框就不准伸出去
      const cx = (tb.left + tb.right) / 2, cy = (tb.top + tb.bottom) / 2;
      let box = null;
      shapes.forEach((S) => { const c = S.el.classList; if (S.el.tagName !== 'rect' || !(c.contains('frame') || c.contains('bg') || c.contains('fbar') || c.contains('row'))) return;
        if (S.el.contains(T.el)) return;
        const r = S.r; if (cx < r.left || cx > r.right || cy < r.top || cy > r.bottom) return;
        if (!box || r.width * r.height < box.r.width * box.r.height) box = S; });
      if (box) {
        const r = box.r; const over = Math.max(r.left - tb.left, tb.right - r.right, r.top - tb.top, tb.bottom - r.bottom);
        if (over > TOL) issues.push({ kind: '文字超出所屬格子', sec: secOf(T.el), a: descText(T.el), b: descShape(box.el), px: +over.toFixed(1), rect: R(union(T.r, r.width * r.height < 6 * T.r.width * T.r.height ? r : T.r)) });
      }
      // ③ 超出畫布（會被切掉）
      const over = Math.max(svr.left - tb.left, tb.right - svr.right, svr.top - tb.top, tb.bottom - svr.bottom);
      if (over > TOL) issues.push({ kind: '文字超出畫布', sec: secOf(T.el), a: descText(T.el), b: '<svg>', px: +over.toFixed(1), rect: R(T.r) });
    });
    // ⑤ 編號圓點互蓋（兩顆圓點的圓心距離小於兩個半徑和）
    const dots = [...svg.querySelectorAll('g.anc circle.anchor.no')].filter(c => shown(c, svg)).map(c => ({ el: c, r: c.getBoundingClientRect() })).filter(d => d.r.width);
    for (let i = 0; i < dots.length; i++) for (let j = i + 1; j < dots.length; j++) {
      const a = dots[i].r, b = dots[j].r;
      const ov = (a.width + b.width) / 2 - Math.hypot((a.left + a.right - b.left - b.right) / 2, (a.top + a.bottom - b.top - b.bottom) / 2);
      const na = (dots[i].el.parentNode.querySelector('.non') || {}).textContent || '', nb = (dots[j].el.parentNode.querySelector('.non') || {}).textContent || '';
      if (ov > TOL) issues.push({ kind: '編號圓點互蓋', sec: secOf(dots[i].el), a: '編號 ' + na, b: '編號 ' + nb, px: +ov.toFixed(1), rect: R(union(a, b)) });
    }
    // ④ 文字互疊
    for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
      const I = inter(texts[i].tight, texts[j].tight);
      if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '文字互疊', sec: secOf(texts[i].el), a: descText(texts[i].el), b: descText(texts[j].el), px: +Math.min(I.width, I.height).toFixed(1), rect: R(union(texts[i].r, texts[j].r)) });
    }
  });
  // ---------------- 引線（.dglead：卡片 → 畫布邊 → 錨點，HTML 疊在畫布上）穿過畫布裡的字 ----------------
  // 引線是 1px 左右的細線，照「重疊深度」算永遠 ≤ 2px；但它整條橫著劃過一行字，讀起來就是一道刪除線 ——
  // 所以這一項改量「穿過字身的長度」：橫線落在字身框內（上下各內縮 2px）且橫跨 > 6px 就算。
  host.querySelectorAll('svg.dglead').forEach((ld) => {
    const lr = ld.getBoundingClientRect();
    ld.querySelectorAll('path').forEach((pth) => {
      const d = pth.getAttribute('d') || ''; const tok = d.match(/[MHVL]|-?[\d.]+/g) || [];
      let x = 0, y = 0, i = 0; const segs = [];
      while (i < tok.length) {
        const c = tok[i++];
        if (c === 'M') { x = +tok[i++].replace(',', ''); y = +tok[i++]; }
        else if (c === 'H') { const nx = +tok[i++]; segs.push([x, y, nx, y]); x = nx; }
        else if (c === 'V') { const ny = +tok[i++]; segs.push([x, y, x, ny]); y = ny; }
        else if (c === 'L') { const nx = +tok[i++], ny = +tok[i++]; segs.push([x, y, nx, ny]); x = nx; y = ny; }
      }
      segs.forEach(([x1, y1, x2, y2]) => {
        const X1 = lr.left + Math.min(x1, x2), X2 = lr.left + Math.max(x1, x2), Y1 = lr.top + Math.min(y1, y2), Y2 = lr.top + Math.max(y1, y2);
        allTexts.forEach((T) => {
          const b = T.tight;
          if (Y1 === Y2) {                                   // 橫線
            if (Y1 <= b.top + 2 || Y1 >= b.bottom - 2) return;
            const len = Math.min(X2, b.right) - Math.max(X1, b.left); if (len <= 6) return;
            issues.push({ kind: '引線穿過文字', sec: secOf(T.el), a: descText(T.el), b: '引線（橫）', px: +len.toFixed(1), rect: R({ left: Math.max(X1, b.left) - 20, right: Math.min(X2, b.right) + 20, top: b.top - 6, bottom: b.bottom + 6, width: 0, height: 0 }) });
          } else if (X1 === X2) {                            // 直線
            if (X1 <= b.left + 2 || X1 >= b.right - 2) return;
            const len = Math.min(Y2, b.bottom) - Math.max(Y1, b.top); if (len <= 6) return;
            issues.push({ kind: '引線穿過文字', sec: secOf(T.el), a: descText(T.el), b: '引線（直）', px: +len.toFixed(1), rect: R({ left: b.left - 6, right: b.right + 6, top: Math.max(Y1, b.top) - 20, bottom: Math.min(Y2, b.bottom) + 20, width: 0, height: 0 }) });
          }
        });
      });
    });
  });
  // ---------------- HTML 說明卡（v2 外掛）----------------
  const vis = (e) => { if (!e || !e.getClientRects().length) return false; const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const clipBy = (e, r) => { // 被捲動容器切掉的部分不算
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p); if (/(auto|scroll|hidden)/.test(cs.overflowY + cs.overflowX)) { const pr = p.getBoundingClientRect(); r = inter(r, pr); if (!r) return null; }
    }
    return r;
  };
  const cards = [...host.querySelectorAll('.dgc')].filter(vis).map(c => ({ el: c, r: clipBy(c, c.getBoundingClientRect()) })).filter(c => c.r && c.r.width > 2 && c.r.height > 2);
  const cdesc = (c) => { const n = c.querySelector('.no'), b = c.querySelector('.bd b'); return `卡片 ${n ? n.textContent + ' ' : ''}${clip(b ? b.textContent : c.textContent, 18)}`; };
  out.cards = cards.length;
  for (let i = 0; i < cards.length; i++) for (let j = i + 1; j < cards.length; j++) {
    const I = inter(cards[i].r, cards[j].r);
    if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '說明卡互蓋', sec: '說明卡', a: cdesc(cards[i].el), b: cdesc(cards[j].el), px: +Math.min(I.width, I.height).toFixed(1), rect: R(union(cards[i].r, cards[j].r)) });
  }
  const canvas = host.querySelector('.dgcanvas');
  if (canvas && vis(canvas)) {
    const cr0 = clipBy(canvas, canvas.getBoundingClientRect());
    const svg0 = canvas.querySelector('svg.dg');
    const cr = cr0 && svg0 ? inter(cr0, svg0.getBoundingClientRect()) : cr0;
    if (cr) cards.forEach((c) => { const I = inter(c.r, cr); if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '說明卡蓋到畫布', sec: '說明卡', a: cdesc(c.el), b: '.dgcanvas', px: +Math.min(I.width, I.height).toFixed(1), rect: R(union(c.r, I)) }); });
    const hd = host.querySelector('.dghead');
    if (hd && vis(hd) && cr) { const I = inter(hd.getBoundingClientRect(), cr); if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '圖頭蓋到畫布', sec: '圖頭', a: clip(hd.textContent, 26), b: '.dgcanvas', px: +Math.min(I.width, I.height).toFixed(1), rect: R(hd.getBoundingClientRect()) }); }
  }
  cards.forEach((c) => {
    const cr = c.el.getBoundingClientRect();
    [...c.el.querySelectorAll('b,i,a,s,.no')].filter(vis).forEach((e) => {
      const r = e.getBoundingClientRect(); if (!r.width) return;
      const over = Math.max(cr.left - r.left, r.right - cr.right, cr.top - r.top, r.bottom - cr.bottom);
      if (over > TOL) issues.push({ kind: '卡片文字超出卡片', sec: '說明卡', a: cdesc(c.el), b: clip(e.textContent, 20), px: +over.toFixed(1), rect: R(union(cr, r)) });
    });
    if (c.el.scrollWidth > c.el.clientWidth + TOL && getComputedStyle(c.el).overflowX !== 'visible') issues.push({ kind: '卡片文字超出卡片', sec: '說明卡', a: cdesc(c.el), b: '橫向溢出', px: c.el.scrollWidth - c.el.clientWidth, rect: R(cr) });
  });
  // ---------------- 手機編號鈕 ----------------
  const nums = [...host.querySelectorAll('.mnumlayer .mnum')].filter(vis).map(e => ({ el: e, r: e.getBoundingClientRect() }));
  for (let i = 0; i < nums.length; i++) for (let j = i + 1; j < nums.length; j++) {
    const a = nums[i].r, b = nums[j].r;
    const d = Math.hypot((a.left + a.right - b.left - b.right) / 2, (a.top + a.bottom - b.top - b.bottom) / 2);
    const ov = (a.width + b.width) / 2 - d;
    if (ov > TOL) issues.push({ kind: '編號鈕互蓋', sec: '編號鈕', a: '編號 ' + nums[i].el.textContent, b: '編號 ' + nums[j].el.textContent, px: +ov.toFixed(1), rect: R(union(a, b)) });
  }
  out.nums = nums.length;
  return out;
}"""

# --------------------------------------------------------------------------- 頁內量測（3D）
AUDIT3D_JS = r"""(opt) => {
  const TOL = opt.tol;
  const stage = document.querySelector('#prod3d.dgstage, #prod3d .dgstage');
  if (!stage) return { err: 'no .dgstage' };
  const cv = stage.querySelector('canvas');
  const sx = window.scrollX, sy = window.scrollY;
  const R = (r) => ({ x: r.left + sx, y: r.top + sy, w: r.width, h: r.height });
  const inter = (a, b) => { const x0 = Math.max(a.left, b.left), x1 = Math.min(a.right, b.right), y0 = Math.max(a.top, b.top), y1 = Math.min(a.bottom, b.bottom);
    return (x1 > x0 && y1 > y0) ? { left: x0, right: x1, top: y0, bottom: y1, width: x1 - x0, height: y1 - y0 } : null; };
  const union = (a, b) => ({ left: Math.min(a.left, b.left), top: Math.min(a.top, b.top), right: Math.max(a.right, b.right), bottom: Math.max(a.bottom, b.bottom),
    width: Math.max(a.right, b.right) - Math.min(a.left, b.left), height: Math.max(a.bottom, b.bottom) - Math.min(a.top, b.top) });
  const clip = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n) + '…' : s; };
  const vis = (e) => { if (!e || !e.getClientRects().length) return false; const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity) > 0.2; };
  const clipBy = (e, r) => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p); if (/(auto|scroll|hidden)/.test(cs.overflowY + cs.overflowX)) { const pr = p.getBoundingClientRect(); r = inter(r, pr); if (!r) return null; } } return r; };
  const issues = [];
  const cards = [...stage.querySelectorAll('.lbl3d')].filter(e => !e.classList.contains('hid') && vis(e)).map(e => ({ el: e, r: clipBy(e, e.getBoundingClientRect()) })).filter(c => c.r && c.r.width > 2);
  const cdesc = (c) => { const n = c.querySelector('.no,.n'); const b = c.querySelector('b'); return `3D 卡片 ${n ? n.textContent + ' ' : ''}${clip(b ? b.textContent : c.textContent, 18)}`; };
  for (let i = 0; i < cards.length; i++) for (let j = i + 1; j < cards.length; j++) {
    const I = inter(cards[i].r, cards[j].r);
    if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '3D 說明卡互蓋', sec: '3D', a: cdesc(cards[i].el), b: cdesc(cards[j].el), px: +Math.min(I.width, I.height).toFixed(1), rect: R(union(cards[i].r, cards[j].r)) });
  }
  cards.forEach((c) => {
    const cr = c.el.getBoundingClientRect();
    [...c.el.querySelectorAll('b,i,a,s,small,span,p')].filter(vis).forEach((e) => {
      const r = e.getBoundingClientRect(); if (!r.width) return;
      const over = Math.max(cr.left - r.left, r.right - cr.right, cr.top - r.top, r.bottom - cr.bottom);
      if (over > TOL) issues.push({ kind: '3D 卡片文字超出卡片', sec: '3D', a: cdesc(c.el), b: clip(e.textContent, 20), px: +over.toFixed(1), rect: R(union(cr, r)) });
    });
  });
  // 手機（≤640）的 3D：卡片收掉、畫面上疊編號鈕 —— 鈕與鈕不准互蓋
  const nums = [...stage.querySelectorAll('.mnumlayer .mnum')].filter(vis).map(e => ({ el: e, r: e.getBoundingClientRect() }));
  for (let i = 0; i < nums.length; i++) for (let j = i + 1; j < nums.length; j++) {
    const a = nums[i].r, b = nums[j].r;
    const ov = (a.width + b.width) / 2 - Math.hypot((a.left + a.right - b.left - b.right) / 2, (a.top + a.bottom - b.top - b.bottom) / 2);
    if (ov > TOL) issues.push({ kind: '3D 編號鈕互蓋', sec: '3D', a: '編號 ' + nums[i].el.textContent, b: '編號 ' + nums[j].el.textContent, px: +ov.toFixed(1), rect: R(union(a, b)) });
  }
  // 2026-09-26 起「拖曳／重設視角」那組鈕浮在 3D 畫面框內右上角（#dg3dCtl）：卡片與編號鈕都不准壓到它
  const ctl = document.querySelector('#dg3dCtl');
  if (ctl && vis(ctl)) {
    [...ctl.querySelectorAll('button')].filter(vis).forEach((bt) => {
      const br = bt.getBoundingClientRect();
      cards.forEach((c) => { const I = inter(c.r, br);
        if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '3D 說明卡蓋到視角鈕', sec: '3D', a: cdesc(c.el), b: '鈕 ' + clip(bt.textContent, 10), px: +Math.min(I.width, I.height).toFixed(1), rect: R(union(c.r, br)) }); });
      nums.forEach((n) => { const I = inter(n.r, br);
        if (I && I.width > TOL && I.height > TOL) issues.push({ kind: '3D 編號鈕蓋到視角鈕', sec: '3D', a: '編號 ' + n.el.textContent, b: '鈕 ' + clip(bt.textContent, 10), px: +Math.min(I.width, I.height).toFixed(1), rect: R(union(n.r, br)) }); });
    });
  }
  const cvr = cv ? cv.getBoundingClientRect() : null;
  return { issues, nums: nums.length, cards: cards.map(c => ({ d: cdesc(c.el), r: { left: c.r.left, top: c.r.top, right: c.r.right, bottom: c.r.bottom } })),
           canvas: cvr ? { left: cvr.left, top: cvr.top, width: cvr.width, height: cvr.height } : null, sx, sy };
}"""

EXPAND_FOLDS_JS = r"""(sel) => { const h = document.querySelector(sel); if (!h) return 0; let n = 0;
  h.querySelectorAll('g.dgfold[data-fold]').forEach(g => { if (!g.classList.contains('open')) { g.dispatchEvent(new MouseEvent('click', { bubbles: true })); n++; } });
  return n; }"""

LIST_JS = r"""() => { const S = window.DiagramSlots; const out = [];
  if (S) { const seen = new Set();
    ['semiconductor','ai_server','electronics','traditional','infrastructure','financial','software','biotech','consumer','shipping','auto'].forEach(ch => {
      if (S.chainDefault(ch)) { out.push({ kind: 'industry', ch, id: ch, scene: S.scene(ch) }); seen.add(ch); }
      S.groupsOf(ch).forEach(g => { if (!seen.has(g)) { out.push({ kind: 'industry', ch, id: g, scene: S.scene(g) }); seen.add(g); } }); });
    Object.keys(window.Diagrams || {}).forEach(k => { if (!seen.has(k) && S.has(k)) { const ch = S.chainOf(k); out.push({ kind: 'industry', ch, id: k, scene: S.scene(k) }); seen.add(k); } });
  }
  Object.keys(window.ThemeDiagrams || {}).filter(k => k !== 'fit' && typeof window.ThemeDiagrams[k] === 'function').forEach(k => out.push({ kind: 'theme', ch: 'themes', id: k, scene: null }));
  return out; }"""


class _Srv(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # noqa: D102  換頁時瀏覽器中斷連線（BrokenPipe）不是錯
        pass


def _url(base: str, t: dict) -> str:
    if t["kind"] == "theme":
        return f"{base}#heatmap/theme/{t['id']}"
    return f"{base}#industry/{t['ch']}/dg/{t['id']}"


def _host(t: dict) -> str:
    return "#themeDiagram" if t["kind"] == "theme" else "#prodDiagram"


def _whitelisted(dg: str, it: dict) -> str:
    for d, kind, sub, why in WHITELIST:
        if d == dg and kind == it["kind"] and sub in it.get("a", ""):
            return why
    return ""


def _layout(w) -> tuple[int, str]:
    """寬度欄位可以寫 1440（今日事件抽屜開著＝預設）或 1440c（抽屜關，卡片左右夾著畫布的三欄版面）。"""
    s = str(w).strip()
    return (int(s[:-1]), "0") if s.endswith("c") else (int(s), "1")


def _prep(pg, base: str, t: dict, w, mode: str, pal: str) -> None:
    """設好 localStorage 再進那張圖。閱讀模式連全站主題一起切成淺色（使用者實際看到閱讀模式就是這個組合）。"""
    width, side = _layout(w)
    ls = {"tw.dg3d": "1" if mode == "3d" else "0", "tw.dgOpen": "1", "tw.dganim": "0", "tw.side": side,
          "tw.dg3d.pal": pal, "tw.theme": "light" if pal == "read" else "dark"}
    pg.set_viewport_size({"width": width, "height": 950})
    origin = base.rsplit("/", 1)[0]
    if not pg.url.startswith(origin):          # 第一次：先進同源頁面才寫得到 localStorage
        pg.goto(base + "#overview", wait_until="domcontentloaded")
    pg.evaluate("(ls) => { try { Object.entries(ls).forEach(([k, v]) => localStorage.setItem(k, v)); } catch (e) {} }", ls)
    pg.goto("about:blank")
    pg.goto(_url(base, t), wait_until="networkidle")
    pg.evaluate("(ls) => { try { Object.entries(ls).forEach(([k, v]) => localStorage.setItem(k, v)); } catch (e) {} }", ls)


def _wait_2d(pg, host: str) -> bool:
    for _ in range(40):
        ok = pg.evaluate("(h) => { const e = document.querySelector(h); return !!e && !!e.querySelector('svg.dg') && e.getBoundingClientRect().width > 0; }", host)
        if ok:
            pg.wait_for_timeout(700)      # externalize 的 300ms 補排、字型
            return True
        pg.wait_for_timeout(150)
    return False


def _shot(pg, rect: dict, path: Path, pad: int = 36) -> None:
    """放大截圖：以問題範圍為中心、四周多留 pad，窄於 900px 的放大兩倍（字才看得清楚）。
    ⚠ 不用 full_page：Chromium 的整頁截圖會把視窗暫時撐成整頁高，ResizeObserver 一動，
      卡片欄與畫布就重排 —— 截到的是另一個版面（第一版就這樣截歪了）。改成捲到那裡、截可視範圍。"""
    try:
        from PIL import Image
        vw, vh = pg.viewport_size["width"], pg.viewport_size["height"]
        pg.evaluate("(y) => window.scrollTo({ top: Math.max(0, y), behavior: 'instant' })", rect["y"] - pad - 60)
        pg.wait_for_timeout(150)
        sx, sy = pg.evaluate("() => [window.scrollX, window.scrollY]")
        x = max(0, rect["x"] - sx - pad)
        y = max(0, rect["y"] - sy - pad)
        w = max(20, min(rect["w"] + 2 * pad, vw - x))
        h = max(20, min(rect["h"] + 2 * pad, vh - y))
        pg.screenshot(path=str(path), clip={"x": x, "y": y, "width": w, "height": h}, animations="disabled")
        im = Image.open(path)
        if im.width < 900:
            im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
        im.save(path)
    except Exception as exc:  # noqa: BLE001
        print("  截圖失敗", path.name, str(exc)[:80])


def _silhouette_overlap(pg, info: dict, tol: float) -> list[dict]:
    """畫布裡「看得見的零件」在哪些像素：標籤層藏起來各截一張「有畫布」與「畫布藏起來」，兩張的差＝零件。
    three3d 的 renderer 是 alpha:true、場景沒有 background —— 畫布本身是透明的，
    所以把畫布藏起來截到的就是它底下的底色（含漸層、暗角），相減之後剩下的只有模型本身
    （深色側面也抓得到；只跟「底色」比的第一版把黑色側面整片漏掉）。"""
    from io import BytesIO

    import numpy as np
    from PIL import Image
    cv = info.get("canvas")
    if not cv or not info.get("cards"):
        return []
    S3 = "#prod3d.dgstage, #prod3d .dgstage"
    hide = """(o) => { const s = document.querySelector(o.sel); if (!s) return;
      [...s.children].forEach(c => { const isCv = c.tagName === 'CANVAS'; if (isCv && !o.cv) return;
        if (c.dataset.ovHide == null) c.dataset.ovHide = c.style.visibility || '-'; c.style.visibility = 'hidden'; }); }"""
    show = """(sel) => { const s = document.querySelector(sel); if (!s) return;
      [...s.children].forEach(c => { if (c.dataset.ovHide != null) { c.style.visibility = c.dataset.ovHide === '-' ? '' : c.dataset.ovHide; delete c.dataset.ovHide; } }); }"""
    # 畫布可能比視窗高、或上緣捲到視窗外：只截看得到的那一塊（卡片座標一律換算到這塊的原點）
    vw, vh = pg.viewport_size["width"], pg.viewport_size["height"]
    x0, y0 = max(0.0, cv["left"]), max(0.0, cv["top"])
    x1, y1 = min(float(vw), cv["left"] + cv["width"]), min(float(vh), cv["top"] + cv["height"])
    if x1 - x0 < 20 or y1 - y0 < 20:
        return []
    clip = {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}
    cv = {"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}
    try:
        pg.evaluate(hide, {"sel": S3, "cv": False})
        pg.wait_for_timeout(80)
        with_cv = pg.screenshot(clip=clip)
        pg.evaluate(hide, {"sel": S3, "cv": True})
        pg.wait_for_timeout(80)
        no_cv = pg.screenshot(clip=clip)
    finally:
        pg.evaluate(show, S3)
    im = np.asarray(Image.open(BytesIO(with_cv)).convert("RGB")).astype(np.int16)
    bg = np.asarray(Image.open(BytesIO(no_cv)).convert("RGB")).astype(np.int16)
    H, W, _ = im.shape
    diff = np.abs(im - bg).sum(axis=2)
    mask = diff > 24
    # ★ 模型底下那片「柔和接觸陰影」（three3d 的 radial sprite 圓盤、黑色、不透明度 ≤ .4）不是零件，
    #   但在閱讀模式的淺底上它跟底色的差值有 26～31，會被當成零件 —— 卡片壓到陰影外圈就被判成「蓋到零件」
    #   （2026-09-26 CNC 工具機／閱讀模式實測）。黑色半透明疊上去＝底色的每個色版乘上同一個 (1−a)，
    #   所以「三個色版都變暗、而且變暗的比例一樣（差 < .03）、比例在 .58 以上」的像素就是陰影，從零件裡扣掉。
    #   有顏色的零件三個比例不會一樣；灰色零件疊在略帶色調的底上也對不齊，所以不會被誤扣。
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = im / np.maximum(bg, 1)
    darker = (im <= bg).all(axis=2)
    rmin, rmax = ratio.min(axis=2), ratio.max(axis=2)
    shadow = darker & (rmax - rmin < 0.03) & (rmin >= 0.58)
    mask &= ~shadow
    # 陰影、反鋸齒邊這種細碎的東西：開運算去掉 3px 以下的點線
    m2 = mask.copy()
    m2[1:-1, 1:-1] = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
    mask = m2
    if os.environ.get("DGOV_DEBUG"):            # 除錯：把「當成零件」的像素存成黑白圖，眼睛對一次
        OUT.mkdir(parents=True, exist_ok=True)
        Image.fromarray((mask * 255).astype("uint8")).save(OUT / f"_mask-{int(cv['width'])}.png")
    out = []
    for c in info["cards"]:
        r = c["r"]
        x0, x1 = int(max(0, r["left"] - cv["left"])), int(min(W, r["right"] - cv["left"]))
        y0, y1 = int(max(0, r["top"] - cv["top"])), int(min(H, r["bottom"] - cv["top"]))
        if x1 - x0 < 3 or y1 - y0 < 3:
            continue
        sub = mask[y0:y1, x0:x1]
        n = int(sub.sum())
        if os.environ.get("DGOV_DEBUG") and n:
            dd = diff[y0:y1, x0:x1]
            print("   除錯", c["d"][:24], "差值 max", int(dd.max()), "p90", int(np.percentile(dd[sub], 90)), "p50", int(np.percentile(dd[sub], 50)))
        if n < 30:
            continue
        ys, xs = np.nonzero(sub)
        depth = float(min(xs.max() - xs.min(), ys.max() - ys.min()) + 1)
        if depth <= tol:
            continue
        out.append({"kind": "3D 說明卡蓋到零件", "sec": "3D", "a": c["d"], "b": f"零件像素 {n}", "px": round(depth, 1),
                    "rect": {"x": r["left"] + info["sx"], "y": r["top"] + info["sy"], "w": r["right"] - r["left"], "h": r["bottom"] - r["top"]}})
    return out


def _shots(pg, t: dict, mode: str, w: int, pal: str, issues: list[dict], shots: Path, nshot: int) -> int:
    done: dict = {}
    for it in issues:
        if not it.get("rect") or _whitelisted(t["id"], dict(it, dg=t["id"])):
            continue
        k = (it["kind"], it["a"], it.get("sec", ""), it["b"] if "互" in it["kind"] else "")
        if k in done:                               # 同一段字只拍一張（併成一條的那幾塊圖形共用）
            it["shot"] = done[k]
            continue
        nshot += 1
        fn = f"{nshot:03d}-{t['id']}-{mode}-{w}-{pal}.png"
        _shot(pg, it["rect"], shots / fn)
        it["shot"] = fn
    return nshot


def _one(pg, base: str, t: dict, w: int, mode: str, pal: str, shots, nshot: int, log) -> tuple[list[dict], int]:
    """量一張圖的一種狀態（寬度 × 模式 × 配色）。"""
    found: list[dict] = []
    host = _host(t)
    _prep(pg, base, t, w, mode, pal)
    tag = f"{t['id']}/{mode}/{w}/{pal}"
    if mode == "2d":
        if not _wait_2d(pg, host):
            found.append({"dg": t["id"], "ch": t["ch"], "mode": mode, "w": w, "pal": pal, "kind": "畫不出來", "sec": "", "a": "", "b": "", "px": 0, "rect": None})
            return found, nshot
        states = [("收合", False), ("全部展開", True)]
        res_all = []
        for st, expand in states:
            if expand:
                n = pg.evaluate(EXPAND_FOLDS_JS, host)
                if not n:
                    continue
                pg.wait_for_timeout(500)
            r = pg.evaluate(AUDIT2D_JS, {"host": host, "tol": TOL})
            if r.get("err"):
                log(f"  {tag} {r['err']}")
                continue
            for it in r["issues"]:
                it["state"] = st
            res_all.append((st, r))
            if shots is not None:
                nshot = _shots(pg, t, mode, w, pal, r["issues"], shots, nshot)
        # 收合狀態看到的問題，展開後一定還在 → 以「全部展開」為準，收合只補它獨有的
        seen = set()
        issues = []
        for st, r in reversed(res_all):
            for it in r["issues"]:
                k = (it["kind"], it["a"], it["b"])
                if k in seen:
                    continue
                seen.add(k)
                issues.append(it)
        stat = res_all[-1][1] if res_all else {}
    else:
        ok = False
        for _ in range(60):
            ok = pg.evaluate("() => { const s = document.querySelector('#prod3d.dgstage, #prod3d .dgstage'); return !!s && !s.closest('[hidden]') && !!s.querySelector('canvas') && s.querySelectorAll('.lbl3d').length > 0; }")
            if ok:
                break
            pg.wait_for_timeout(200)
        if not ok:
            found.append({"dg": t["id"], "ch": t["ch"], "mode": mode, "w": w, "pal": pal, "kind": "3D 畫不出來", "sec": "", "a": "", "b": "", "px": 0, "rect": None})
            return found, nshot
        pg.evaluate("() => { const s = document.querySelector('#prod3d'); if (s) s.scrollIntoView({ block: 'center', behavior: 'instant' }); }")
        pg.wait_for_timeout(2600)       # 爆炸拆解 1.6 秒＋標籤排版
        r = pg.evaluate(AUDIT3D_JS, {"host": host, "tol": TOL})
        if r.get("err"):
            log(f"  {tag} {r['err']}")
            return found, nshot
        issues = r["issues"] + _silhouette_overlap(pg, r, TOL)
        if shots is not None:
            nshot = _shots(pg, t, mode, w, pal, issues, shots, nshot)
        stat = {"cards": len(r.get("cards") or []), "nums": r.get("nums", 0)}
    # 同一段字被好幾塊圖形蓋到（玻璃方塊是 前面＋頂面＋陰影 三塊）→ 併成一條，B 欄列出全部
    kept, idx = [], {}
    for it in issues:
        it.update({"dg": t["id"], "ch": t["ch"], "mode": mode, "w": w, "pal": pal})
        if _whitelisted(t["id"], it):
            continue
        k = (it["kind"], it["a"], it.get("sec", ""))
        if k in idx and it["kind"] not in ("文字互疊", "說明卡互蓋", "3D 說明卡互蓋", "編號鈕互蓋", "編號圓點互蓋", "3D 編號鈕互蓋"):
            o = idx[k]
            if it["b"] not in o["b"]:
                o["b"] += "、" + it["b"]
            o["px"] = max(o["px"], it["px"])
            continue
        idx[k] = it
        kept.append(it)
    found.extend(kept)
    log(f"  {tag:<44} 問題 {len(kept):>3}  " + " ".join(f"{k}={v}" for k, v in stat.items() if k in ("svgs", "texts", "shapes", "cards", "nums")))
    return found, nshot


def audit(pg, base: str, targets: list[dict] | None = None, widths=(1440, 1100, 800, 390), modes=("2d", "3d"),
          pals=("tech",), shots: Path | None = None, only: str = "", log=print) -> list[dict]:
    """量一輪，回傳問題清單（已扣掉白名單）。pg＝已開好的 Playwright 頁面；base＝…/index.html。"""
    if targets is None:
        pg.goto(base + "#overview", wait_until="networkidle")
        targets = pg.evaluate(LIST_JS)
    if only:
        keys = [k.strip() for k in only.split(",") if k.strip()]
        targets = [t for t in targets if any(k in t["id"] for k in keys)]
    found: list[dict] = []
    nshot = 0
    for t in targets:
        for pal in pals:
            for w in widths:
                for mode in modes:
                    if mode == "3d" and not t.get("scene"):
                        continue
                    try:
                        got, nshot = _one(pg, base, t, w, mode, pal, shots, nshot, log)
                        found.extend(got)
                        if shots is not None and got:     # 邊量邊寫：一輪要跑很久，中途就能先看已經量到的
                            with open(shots / "report.jsonl", "a", encoding="utf-8") as fh:
                                for it in got:
                                    fh.write(json.dumps(it, ensure_ascii=False) + "\n")
                    except Exception as exc:  # noqa: BLE001  一張圖量壞了不要讓整輪停掉
                        log(f"  {t['id']}/{mode}/{w}/{pal} 量測失敗：{str(exc)[:160]}")
                        found.append({"dg": t["id"], "ch": t["ch"], "mode": mode, "w": w, "pal": pal, "kind": "量測失敗", "sec": "", "a": str(exc)[:80], "b": "", "px": 0, "rect": None})
    return found


def _report(found: list[dict]) -> str:
    lines = ["# 剖析圖覆蓋普查", "", f"問題 {len(found)} 處", ""]
    if not found:
        lines.append("（清單是空的）")
        return "\n".join(lines)
    lines.append("| 鏈 | 圖 | 段落 | 模式 | 寬 | 配色 | 種類 | 元素 A | 元素 B | 重疊 px | 截圖 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for it in found:
        lines.append("| {ch} | {dg} | {sec} | {mode} | {w} | {pal} | {kind} | {a} | {b} | {px} | {shot} |".format(
            **{k: str(it.get(k, "")).replace("|", "／") for k in ("ch", "dg", "sec", "mode", "w", "pal", "kind", "a", "b", "px", "shot")}))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只量這幾張（圖 id 子字串，逗號分隔）")
    ap.add_argument("--width", default="1440,1440c,1100,1100c,800,390",
                    help="逗號分隔；尾巴加 c＝今日事件抽屜關（三欄版面），不加＝抽屜開（預設狀態）")
    ap.add_argument("--pal", default="tech,read", help="tech（科技，深底）／read（閱讀，字大一階）")
    ap.add_argument("--no-3d", action="store_true")
    ap.add_argument("--no-2d", action="store_true")
    ap.add_argument("--no-shots", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(ROOT))
    from playwright.sync_api import sync_playwright

    from scripts._show import _preset_consent, _Quiet
    _preset_consent()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    srv = _Srv(("127.0.0.1", PORT), partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}/index.html"
    modes = tuple(m for m in ("2d", "3d") if not (m == "3d" and args.no_3d) and not (m == "2d" and args.no_2d))
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
            pg = b.new_page(viewport={"width": 1440, "height": 950})
            found = audit(pg, base, widths=[x.strip() for x in args.width.split(",") if x.strip()], modes=modes,
                          pals=tuple(x.strip() for x in args.pal.split(",") if x.strip()),
                          shots=None if args.no_shots else OUT, only=args.only)
            b.close()
    finally:
        srv.shutdown()
    (OUT / "report.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "report.md").write_text(_report(found), encoding="utf-8")
    print(f"\n問題 {len(found)} 處 → {OUT / 'report.md'}")
    by = {}
    for it in found:
        by.setdefault((it["dg"], it["kind"]), 0)
        by[(it["dg"], it["kind"])] += 1
    for (dg, k), n in sorted(by.items()):
        print(f"  {dg:<22} {k:<12} {n}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
