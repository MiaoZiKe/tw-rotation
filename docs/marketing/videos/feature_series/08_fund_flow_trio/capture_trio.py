"""功能介紹影片 08 資金流向三合一（資金輪動＋資金分流樹＋族群×法人）—— 一口氣錄完（1.0 倍速、一鏡到底）。

Andy 10-24：「資金輪動＋資金分流樹＋族群×法人 組成一起做一隻影片，節奏太快了，點擊步驟不用那麼多……步調正常，真的有使用功能的感覺」。
CEO 裁示：① 訪客的時間列是反灰（flow.play 對訪客關）→ 照原樣入鏡，不示範拉桿與回放，改用「切產業鏈」示範兩圖同步變；
② 不勾族群下拉（族群→公司卡片會蓋排行）；選完產業鏈自動彈出的族群清單錄影端隱藏；③ 零模糊；④ 字級盡量 ≥20px。

錄法：vidlib8.py（逐格算圖、每格記錄所有文字外框／浮層外框，游標只落在不壓字的空白處）；一律未登入訪客真實畫面。
用法：FEAT_SITE=<main worktree>/site python capture_trio.py --dev d|m [--dry]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vidlib8 as V  # noqa: E402

F, C = V.F, V.C
SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat08"))
SITE = Path(os.environ.get("FEAT_SITE", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat06/main_wt/site"))
OVERLAYS = ['.ddpanel:not([hidden])', '.twms-pan', '#__vsel', '[role=dialog]', '.toast', '#howPop', '.qcov', '.qcard', '.fttip.on', '#lgBanner', '#lgReAccept']
ELS = {
    "navflow": '#tabs .tab[data-view="flow"]', "subsankey": '.l4subtab[data-l4sub="flow-sankey"]', "subinst": '.l4subtab[data-l4sub="flow-inst"]',
    "clock": "#rotClock", "rank": "#rankFlow", "slider": "#rotBack", "chainr": '#flowRotFilter .rotdd[data-dd="chain"] .ddbtn',
    "sk": "#sankey", "sklist": "#sankeyPanel", "skchain": '#flowSankeyCard .rotdd[data-dd="chain"] .ddbtn',
    "inst": "#instGroups", "instleg": "#instLegend", "instchain": '#flowInstCard .rotdd[data-dd="chain"] .ddbtn', "instdays": "#instDays",
    "burger": "#m4Burger", "m4flow": '.m4item[data-v="flow"]', "tabsk": '.m4subtabs button[data-sub="flow-sankey"]', "tabinst": '.m4subtabs button[data-sub="flow-inst"]', "tabrot": '.m4subtabs button[data-sub="flow-rotation"]',
}
# 錄影專用樣式（只在錄影的瀏覽器裡，不改 site/）：
#   · 族群下拉清單一律隱藏（CEO：不勾族群；選完產業鏈自動彈出的那一次也不入鏡）
#   · 頂欄改不透明（內容從頂欄下面捲過時不會透出字）
EXTRA_CSS = ("#v-overview .ovmain,#v-overview .ovlow,#v-overview .m3~*{display:none!important}"
             "@media (min-width:900px){#tabs .l4subtab[data-l4sub=\"flow-inst\"]~*{display:none!important}.rotright{height:640px!important;max-height:640px!important;align-self:start!important}}"   # 網頁：排行欄縮到畫面框放得下（15 條長條＋座標軸全部完整入鏡，下緣不再切到最後一條）
             "div[style*=\"border-style: solid\"]{transition:none!important}.rotdd .ddpanel{display:none!important}.rotnums{display:none!important}"
             "header.topbar,#l4Head{background:#f8fbfd!important}"
             "#ovSumTrack>.osc:nth-child(4),.ovsum-nav{display:none!important}"   # 總覽摘要列第 4 張卡（熱門題材）在右緣被站內輪播切半，與本片無關，錄影端不放
             ".sitefoot,.sitefoot *{visibility:hidden!important}")
EXTRA_CSS_M = EXTRA_CSS + "@media (max-width:640px){#m3c-TSE{height:210px!important;min-height:0!important}.plknote{display:none!important}}main{margin-top:calc(var(--vo, 0px) * -1)!important}body.__vhide #rankFlow,body.__vhide #instGroups{opacity:0!important}"   # 手機：「Plus 以上可調整」那行小字在捲動後會飄到排行長條的列標上（網站本身的排版問題），錄影端隱藏；時間列仍是反灰原樣
PARK_R = (560, 208, 90, 48)    # 資金輪動：時間列右側、輪盤上方的空白（游標不經過排行長條，下拉清單才不會被圖表連動重畫收掉）
PARK_S = (540, 78, 140, 26)      # 資金分流樹：卡片標題列中間的空白（不在畫布上，不會觸發節點提示與代表股展開）
PARK_I = (530, 190, 35, 380)     # 族群×法人：長條圖右側空白欄

# 錄影端補丁（只在錄影的瀏覽器裡，不改 site/）
FOCUS_JS = ("(() => { const p = () => { const F = window.FlowTopo; if (!F || F.__np8) return; const of = F.focus; "
            "F.focus = function (h, g, d) { return of.call(this, h, g, d ? Math.max(d, 0.72) : d); }; F.__np8 = 1; }; setInterval(p, 30); })();")   # 點節點後其他分支的淡化提高到 0.72 以上，字都讀得到
NOLEAF_JS = ("(() => { const p = () => { const F = window.FlowTopo; if (!F || F.__nl8) return; const orig = F.render; "
             "F.render = function (host, tree, opts) { try { if (tree && tree.children) tree = Object.assign({}, tree, { children: tree.children.map(c => Object.assign({}, c, "
             "{ children: (c.children || []).map(g => Object.assign({}, g, { children: [] })) })) }); } catch (e) {} return orig.call(this, host, tree, opts); }; F.__nl8 = 1; }; setInterval(p, 30); })();")   # 手機：不畫代表股那一欄，族群名稱才不被截成「晶…」
TT_JS = ("(() => { const patch = () => { const E = window.echarts; if (!E || E.__tt8) return; const oi = E.init; E.init = function (...a) { const c = oi.apply(this, a); const so = c.setOption; "
         "c.setOption = function (o, ...r) { try { if (o && typeof o === 'object' && !Array.isArray(o)) { o.animation = false; const d0 = c.getDom(); if (d0 && d0.id === 'instGroups' && o.xAxis) { (Array.isArray(o.xAxis) ? o.xAxis : [o.xAxis]).forEach(x => { x.axisLabel = Object.assign({}, x.axisLabel || {}, { showMaxLabel: false, hideOverlap: true }); }); } } } catch (e) {} try { if (o && typeof o === 'object' && !Array.isArray(o) && o.tooltip && !Array.isArray(o.tooltip)) { o.tooltip.transitionDuration = 0; "
         "const dom = c.getDom(); if (dom && dom.id === 'rankFlow') { o.tooltip.extraCssText = 'white-space:normal;width:122px;box-sizing:border-box;'; "
         "o.tooltip.position = function (pt, p, el, rect, size) { const ax = c.convertToPixel({ xAxisIndex: 0 }, 0); const H = size.viewSize[1], ch = size.contentSize[1]; "
         "let y = Math.min(pt[1] - 20, H - ch - 52); return [ax + 8, Math.max(4, y)]; }; } else { o.tooltip.position = function (pt, p, el, rect, size) { "
         "const W = size.viewSize[0], H = size.viewSize[1], cw = size.contentSize[0], ch = size.contentSize[1]; let x = pt[0] + 14; if (x + cw > W - 2) x = pt[0] - cw - 14; "
         "let y = pt[1] + 12; if (pt[1] > H * 0.55) y = pt[1] - ch - 12; return [Math.max(2, x), Math.max(2, y)]; }; } } } catch (e) {} return so.call(this, o, ...r); }; return c; }; E.__tt8 = 1; }; setInterval(patch, 30); })();")   # 排行的提示框：縮窄、放在座標軸右側的空白欄（負值那幾列的右半邊沒有任何字）；其他圖放在游標旁、不被畫面框下緣切到

CHAIN_LAB = {"semiconductor": "半導體", "ai_server": "AI 伺服器", "electronics": "一般電子"}

# 看得到的圖表長條（排行／族群×法人）：頁面座標
BARS_JS = r"""(sel) => { const el = document.querySelector(sel); const c = el && window.echarts && echarts.getInstanceByDom(el); if (!c) return [];
  const o = c.getOption(); const ya = o.yAxis[0].data, sd = o.series[0].data; const b = el.getBoundingClientRect(); const out = [];
  const step = ya.length > 1 ? Math.abs(c.convertToPixel({ yAxisIndex: 0 }, ya[1]) - c.convertToPixel({ yAxisIndex: 0 }, ya[0])) : 30;
  for (let i = 0; i < ya.length; i++) { const nm = String(ya[i]).replace(/\s*\d*[↑↓]?\s*$/, '').replace(/\s+\d+(\.\d+)?%$/, '').trim();
    const py = c.convertToPixel({ yAxisIndex: 0 }, ya[i]); const x0 = c.convertToPixel({ xAxisIndex: 0 }, 0);
    let v = sd[i] && typeof sd[i] === 'object' && !Array.isArray(sd[i]) ? sd[i].value : sd[i]; if (Array.isArray(v)) v = v[0];
    out.push({ name: nm, v, x0: b.left + x0, x1: b.left + c.convertToPixel({ xAxisIndex: 0 }, v), y: b.top + py, h: step }); }
  return out; }"""
SK_JS = r"""
window.__vsk = () => { const out = []; const host = document.querySelector('#sankey');
  if (!host || !window.FlowTopo || !FlowTopo.has(host) || !host.getClientRects().length) return out;
  const cv = host.querySelector('canvas.ftlab'); if (!cv) return out; const b = cv.getBoundingClientRect(); let p; try { p = FlowTopo.probe(host); } catch (e) { return out; }
  for (const n of p.nodes) { if (!n.lab || n.vis < 0.3) continue; const l = Math.max(b.left, b.left + n.lab.x), t = Math.max(b.top, b.top + n.lab.y), r = Math.min(b.right, b.left + n.lab.x + n.lab.w), bt = Math.min(b.bottom, b.top + n.lab.y + n.lab.h);
    if (r - l < 1 || bt - t < 1) continue; const hy = (t + bt) / 2, hx = (l + r) / 2; if (hx < 0 || hy < 0 || hx >= innerWidth || hy >= innerHeight) continue;
    const e2 = document.elementFromPoint(hx, hy); if (e2 && !host.contains(e2)) continue; out.push(['sk', l, t, r - l, bt - t, 0, 0, 0]); }
  return out; };
"""


class A8(V.A3):
    next_vo = None

    def click_xy(self, x, y, ms=600, pause=400, expect=None):
        """手機換頁：點下去的前一刻把「新頁面內容的起始偏移」設好（等同新頁一出現就已經捲到不切字的位置，不出現未定位的幀、也不用藏頁面）。"""
        if self.next_vo is not None:
            self.pg.evaluate("(v) => document.body.style.setProperty('--vo', v + 'px')", self.next_vo)
            self.next_vo = None
        return super().click_xy(x, y, ms, pause, expect)

    def bars(self, sel):
        return self.pg.evaluate(BARS_JS, sel)

    def bar(self, sel, name):
        for b in self.bars(sel):
            if b["name"] == name:
                return b
        return None

    def row_rect(self, sel, b, hh=11, xmax=None):
        """被 hover 的那一列（含列標、長條、數值）的外框：提示框不可蓋到它（提示框離游標下緣 ≥12px，列高取 ±11px）。"""
        r = self.pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.right]; }", sel)
        return [r[0], b["y"] - hh, (xmax if xmax else r[1]) - r[0], 2 * hh]

    def set_hov(self, row):
        self.pg.evaluate("(r) => { window.__vhov = r; }", row)

    def clear_hov(self):
        self.pg.evaluate("() => { window.__vhov = null; }")

    def sk_nodes(self):
        self.until("() => { try { return !!FlowTopo.probe(document.querySelector('#sankey')) && FlowTopo.probe(document.querySelector('#sankey')).nodes.length > 3; } catch (e) { return false; } }", 8000)
        _dbg = (str(self.pg.evaluate("() => [location.hash, !!document.querySelector('#sankey'), !!(document.querySelector('#sankey') && document.querySelector('#sankey')._ft), scrollY, document.querySelector('#sankey') ? document.querySelector('#sankey').getBoundingClientRect().top : null]")))
        return self.pg.evaluate("() => { const h = document.querySelector('#sankey'); const p = FlowTopo.probe(h); return p.nodes.map(n => ({ key: n.key, lv: n.lv, text: n.text, x: n.cx, y: n.cy, r: n.r })); }")

    def hover_xy(self, x, y, label, hold_ms, pre=260, row=None):
        """游標緩移到 (x,y)（路徑不壓字）並停住（hover，不點）；記錄成一次 hover 目標。"""
        self.cursor(False)   # 游標先收起、在目標處再出現（不從任何字上掃過）
        self.wait(110)
        self._put(x, y)
        self.x, self.y = x, y
        self.cursor(True)
        self.wait(pre)
        self.note(f"hover {label}")
        self.record_target(x, y, "hover", label=label)
        if row:
            self.pg.evaluate("(r) => { window.__vhov = r; }", row)
        self.wait(hold_ms)
        self.pg.evaluate("() => { window.__vhov = null; }")

    def press_xy(self, x, y, label, hold_ms):
        """手機：手指按住（細圈＋滑鼠按下），停 hold_ms 後放開。"""
        self.cursor(False)
        self._put(x, y)
        self.x, self.y = x, y
        self.cursor(True)
        self.wait(220)
        self.note(f"按住 {label}")
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.record_target(x, y, "click", label=label)
        self.pg.mouse.move(x - 2, y - 2)   # 只移動不按下（族群×法人的長條一按就跳去產業地圖頁）
        self.pg.mouse.move(x, y)
        self.frame()
        self.cursor(False)
        self.wait(hold_ms)
        self.pg.mouse.move(*self.PARK)
        self.x, self.y = self.PARK


def edge_ink(pg, crop, x0=135, x1=None):
    """畫面框上、下緣各 3px 橫帶裡的「深色或有色像素」數（字、長條、線都算；背景近白不算）。用來抓 DOM 外框量不到的圖表字被框邊切到的細縫。"""
    import io
    from PIL import Image
    cx, cy, cw, ch = crop
    x1 = x1 or (cx + cw - 8)
    tot = 0
    for yy in (cy + 1, cy + ch - 4):
        try:
            im = Image.open(io.BytesIO(pg.screenshot(clip={"x": x0, "y": max(0, yy), "width": max(8, x1 - x0), "height": 3}))).convert("RGB")
        except Exception:  # noqa: BLE001
            continue
        for r, g, b in im.getdata():
            if min(r, g, b) < 150:
                tot += 1
    return tot


def straddles(texts, crop, m=0):
    """文字外框跟畫面框相交、但沒有整個落在畫面框內（外縮 2.6px，同合成端的慢漂邊界）的個數＝框緣切字。"""
    cx, cy, cw, ch = crop
    n = 0
    for z in texts:
        x, y, w, h = z[:4]
        inter = x < cx + cw and x + w > cx and y < cy + ch and y + h > cy
        inside = x >= cx + 2.1 + m and y >= cy + 2.1 + m and x + w <= cx + cw - 2.1 - m and y + h <= cy + ch - 2.1 - m
        if inter and not inside:
            n += 1
    return n


def best_scroll(a, pg, y0, crop, span=36, step=2, margin=6):
    """y0 附近找「畫面框上下緣不切過任何文字」的捲動位置（instant 捲動，量完還原）。回傳 (y, 切字數)。"""
    sy = pg.evaluate("() => scrollY")
    best = None
    for d in range(-span, span + 1, step):
        y = max(0, y0 + d)
        pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", y)
        pg.wait_for_timeout(30)
        n = straddles(a.texts(), crop, margin)
        sc = (n, abs(d))
        if best is None or sc < best[0]:
            best = (sc, y)
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", sy)
    return best[1], best[0][0]


def set_chain_js(pg, card, c):
    """量測用（不錄影）：用程式把產業鏈切到 c（空字串＝全部）。"""
    pg.evaluate("(card) => document.querySelector(card + ' .rotdd[data-dd=chain] .ddbtn').click()", card)
    pg.wait_for_timeout(350)
    pg.evaluate("([card, c]) => document.querySelector(card + ` .rotdd[data-dd=chain] .ddopt[data-c='${c}']`).click()", [card, c])
    pg.wait_for_timeout(1800)
    pg.evaluate("() => document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))")
    pg.wait_for_timeout(500)


def survey_web(a, pg):
    """錄影前先量：把網頁版會出現的每個頁面狀態各抓一次（文字外框＋畫面框上下緣像素），每一頁各自挑一個「框的上下緣切到字／圖最少」的 y。"""
    def grab(inkon):
        t = a.texts()
        ink = {y: edge_ink(pg, (0, y, 1100, 627)) for y in range(60, 174, 2)} if inkon else {}
        return t, ink
    pool = {}
    F.goto(pg, "#flow/rotation", 5000)
    pool["rot"] = [grab(True)]
    for c in ("ai_server", "semiconductor"):
        set_chain_js(pg, "#flowRotFilter", c)
        pool["rot"].append(grab(True))
    set_chain_js(pg, "#flowRotFilter", "")
    F.goto(pg, "#flow/sankey", 5000)
    pool["sk"] = [grab(False)]
    try:   # 點下「半導體」節點後的狀態也量（其他枝淡掉、名單面板長出來）
        nd = pg.evaluate("() => { const p = FlowTopo.probe(document.querySelector('#sankey')); const n = p.nodes.find(n => n.lv === 1 && n.text.startsWith('半導體')); return n ? [n.cx, n.cy] : null; }")
        if nd:
            pg.mouse.click(nd[0], nd[1])
            pg.wait_for_timeout(1500)
            pool["sk"].append(grab(False))
    except Exception:  # noqa: BLE001
        pass
    F.goto(pg, "#flow/inst", 5000)
    pool["inst"] = [grab(True)]
    set_chain_js(pg, "#flowInstCard", "semiconductor")
    pool["inst"].append(grab(True))
    set_chain_js(pg, "#flowInstCard", "")
    out = {}
    for page, sts in pool.items():
        res = []
        for y in range(60, 142):
            yy = y - (y % 2)
            cost = 0
            for t, ink in sts:
                cost += straddles(t, (0, y, 1100, 627), 4) * 5000 + ink.get(yy, 0)
            res.append((cost, abs(y - 138), y))
        res.sort()
        out[page] = (res[0][2], res[0][0])
        if page == 'rot':
            out[page] = (131, 0)   # 實測（邊緣像素量測）131 時上下緣最乾淨；排行欄已縮短，下緣落在卡片外
        print("推近目標", page, res[:4], flush=True)
    return out


STRIP_JS = r"""([opts, x, y, cols, cw, ch]) => { const d = document.createElement('div'); d.id = '__vsel';
  d.style.cssText = `position:fixed;left:${x}px;top:${y}px;display:grid;grid-template-columns:repeat(${cols},${cw}px);grid-auto-rows:${ch}px;gap:2px;padding:4px;z-index:2147483600;background:#fff;border:1px solid #c9d3e0;border-radius:8px;box-shadow:0 2px 8px rgba(15,23,42,.14);font:13px/1 'Noto Sans TC',sans-serif;color:#1f2937;white-space:nowrap`;
  d.innerHTML = opts.map(o => `<div data-v="${o.v}" style="display:flex;align-items:center;padding:0 8px;border-radius:6px;${o.on ? 'background:#e8f0fb;color:#1d4ed8;font-weight:700' : ''}">${o.t}</div>`).join('');
  const st = document.createElement('style'); st.textContent = '#__vsel .hv{background:#2563eb!important;color:#fff!important}'; d.appendChild(st); document.body.appendChild(d); }"""


def find_blank(a, region, w, h, prefer, pad=14, step=4):
    """region（css）內找一塊 w×h 的空白（外擴 pad 都不碰任何文字／控制項）；回傳離 prefer 最近的左上角，找不到回 None。"""
    boxes = a.texts() + a.ui_boxes()
    rx, ry, rw, rh = region
    best = None
    y = ry
    while y + h <= ry + rh + 0.1:
        x = rx
        while x + w <= rx + rw + 0.1:
            r = (x - pad, y - pad, w + 2 * pad, h + 2 * pad)
            if all(V._ov(r, b[:4]) == 0 for b in boxes):
                d = (x - prefer[0]) ** 2 + (y - prefer[1]) ** 2
                if best is None or d < best[0]:
                    best = (d, x, y)
            x += step
        y += step
    return (best[1], best[2]) if best else None


def strip_pick(a, pg, card, chain, label, region, size, prefer, hold_open=1100, hold_after=2200, cols=1, cw=100, ch=26, park=None, post=None):
    """自繪清單（照 05 v3）：站上的下拉面板在錄影端隱藏；游標點鈕後，清單畫在空白處（不蓋任何字），游標到選項點下，再真的選值。"""
    a.tap(f'{card} .rotdd[data-dd="chain"] .ddbtn', "產業鏈下拉鈕")
    if park and not a.mob:
        a.park(region=park, ms=300)
    opts = pg.evaluate("(card) => [...document.querySelectorAll(card + ' .rotdd[data-dd=\"chain\"] .ddopt')].map(e => ({ v: e.getAttribute('data-c') || '', t: e.textContent.trim().replace(/\s*\d+\s*$/, '').replace(/（.*$/, '') }))", card)
    cur = pg.evaluate("(card) => { const e = document.querySelector(card + ' .rotdd[data-dd=\"chain\"] .ddbtn'); return e ? e.textContent : ''; }", card)
    for o in opts:
        o["on"] = bool(o["v"]) and o["t"] in cur or (not o["v"] and "全部" in cur)
    n = len(opts)
    rows = -(-n // cols)
    W, H = cols * cw + (cols - 1) * 2 + 10, rows * ch + (rows - 1) * 2 + 10
    pos = find_blank(a, region, W, H, prefer)
    if pos is None:
        a.warns.append(f"{a.t:.1f}s 找不到放自繪清單的空白（{label}）")
        pos = (region[0], region[1])
    pg.evaluate(STRIP_JS, [opts, pos[0], pos[1], cols, cw, ch])
    a.wait(hold_open)
    vsel = [o for o in opts if o["v"] == chain][0]
    ob = pg.locator(f'#__vsel [data-v="{chain}"]').first.bounding_box()
    texts = a.texts()
    tx, ty, ov = a.clear_point([ob["x"], ob["y"], ob["width"], ob["height"]], texts, None)
    a.glide(tx, ty, texts)
    pg.evaluate("(v) => { const e = document.querySelector('#__vsel [data-v=\"' + v + '\"]'); if (e) e.classList.add('hv'); }", chain)
    a.wait(220)
    a.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [tx, ty])
    a.record_target(tx, ty, "click", expect=f'#__vsel [data-v="{chain}"]')
    tg = a.targets[-1]
    tg["label"] = label
    tg["rect_center"] = a._vpt(tx, ty)
    tg["measured_by"] = "自繪清單選項內的落點"
    a.frame()
    pg.evaluate("() => { const e = document.getElementById('__vsel'); if (e) e.remove(); }")
    pg.evaluate("([card, c]) => document.querySelector(card + ` .rotdd[data-dd=chain] .ddopt[data-c='${c}']`).click()", [card, chain])
    pg.evaluate("() => document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))")
    if post:
        post()   # 版面一變就立刻（同一幀之前）捲到不切字的位置
        pg.evaluate("() => document.body.classList.add('__vhide')")   # 圖表重排的那 2 幀（約 0.07 秒）內容暫時透明，不讓重排中的字出現在畫面框邊
        for _ in range(14):
            a.frame()
        pg.evaluate("() => document.body.classList.remove('__vhide')")
        post()
    a.frame()
    if park and not a.mob:
        a.park(region=park, ms=300)
    a.wait(hold_after)


def _rect(pg, sel):
    return pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", sel)


def sp_web(a, pg, card, chain, label, park):
    """網頁：自繪清單放在排行（或族群×法人長條圖）左側的空白欄。"""
    if card == '#flowRotFilter':
        r = _rect(pg, '#rankFlow')
        region, prefer = (r[0] + 160, r[1] + 20, 128, 430), (r[0] + 160, r[1] + 60)
    else:
        r = _rect(pg, '#instGroups')
        region, prefer = (r[0] + 150, r[1] + 6, 180, 360), (r[0] + 160, r[1] + 10)
    strip_pick(a, pg, card, chain, label, region, None, prefer, cols=1, cw=104, ch=26, park=park)


def sp_mob(a, pg, card, chain, label, hold_after=3000):
    """手機：自繪清單（4 欄 2 列）放在篩選列下方的空白處。"""
    b = _rect(pg, f'{card} .rotdd[data-dd="chain"] .ddbtn')
    region, prefer = (30, b[1] + b[3] + 2, 480, 190), (330, b[1] + b[3] + 6)
    strip_pick(a, pg, card, chain, label, region, None, prefer, cols=3, cw=104, ch=30, hold_after=hold_after, post=lambda: snap(a, pg, instant=True))


def open_chain_and_pick(a, pg, card, chain, label, hold_open=1100, hold_after=2200, park=None, mob=False):
    """點產業鏈鈕 → 清單開著停一下 → 點選項 → 清掉自動彈出的族群清單（錄影端本來就隱藏，這裡再保險點一次空白）→ 結果停 hold_after。"""
    sel = f'{card} .rotdd[data-dd="chain"] .ddbtn'
    a.tap(sel, "產業鏈下拉鈕")
    a.park(region=park, ms=320) if (park and not mob) else None
    a.wait(hold_open)
    opt = f'{card} .rotdd[data-dd="chain"] .ddopt[data-c="{chain}"]'
    a.tap(opt, label)
    pg.evaluate("() => document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))")
    if park and not mob:
        a.park(region=park, ms=300)
    a.wait(hold_after)


def run_d(pg, a, start):
    CROP = V.CROP0["d"]
    pg2 = pg.context.new_page()   # 量測在另一個分頁做（不碰錄影用的頁面狀態；做完關掉）
    pg2.goto(pg.url.split("#")[0] + "#overview", wait_until="networkidle")
    pg2.wait_for_timeout(2500)
    a.pg = pg2
    pans, = [survey_web(a, pg2)]
    pg2.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    pg2.evaluate(C.PRESET)   # 錄影的預設值（同意紀錄等，不讓同意橫幅入鏡）
    pg2.evaluate("() => { try { localStorage.setItem('tw.layout4.nav', 'mini'); } catch (e) {} }")   # 量測用掉的免費額度（網站對訪客的使用次數）一併清掉，錄影用的頁面維持第一次來的狀態
    a.pg = pg
    pg2.close()
    F.goto(pg, "#overview", 3500)
    ov_y, ov_cut = 8, 0   # 總覽只往下 8px：卡片標題列留在頂欄下面、下緣的卡片標題整個在畫面框內（用 24px 時標題列會被頂欄切掉半截）
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", ov_y)
    pg.wait_for_timeout(400)
    a.extra = {"pans": [{"dur": 0.03, "click": "選單：資金流向", "y": pans["rot"][0], "cut": pans["rot"][1]}, {"dur": 0.03, "click": "子選單：資金分流樹", "y": pans["sk"][0], "cut": pans["sk"][1]}, {"dur": 0.03, "click": "子選單：族群×法人", "y": pans["inst"][0], "cut": pans["inst"][1]}], "ov_scroll": ov_y, "ov_cut": ov_cut}
    a.note(f"量測：各頁框位置 {pans}；總覽捲動 {ov_y}（切字 {ov_cut}）")
    a.crop = CROP
    a.x, a.y = 700, 330
    a.park(region=(260, 12, 300, 30))
    start()
    # 開場：需求（泡泡 1）
    a.set_stage(1, "需求")
    a.say("錢到底往哪個族群跑？", "face_think", ("navflow",))
    a.idle(3000)
    a.set_stage(2, "三頁")
    a.say("三頁接著看，就有答案", "face_curious", ("navflow",))
    a.idle(1500)
    # 導覽：點左側「資金流向」
    a.set_stage(3, "導覽")
    a.say("點選單，進資金輪動", "point_r", ("navflow",))
    a.wait(300)
    a.tap('#tabs .tab[data-view="flow"]', "選單：資金流向")
    a.park(region=PARK_R, ms=300, prefer=(a.x, a.y))
    a.until("() => !!document.querySelector('#rotClock canvas') && !!document.querySelector('#rankFlow canvas')", 10000)
    pg.evaluate("() => scrollTo({ top: 0, behavior: 'instant' })")
    a.park(region=PARK_R, ms=400)
    a.wait(1500)
    # 功能一：資金輪動
    a.set_stage(4, "看強弱")
    a.say("輪盤看強弱，排行看流入", "magnifier", ("clock", "rank"))
    a.idle(3300)
    a.settle()
    a.set_stage(5, "滑過長條")
    a.say("滑過長條，看占比變化", "spotlight", ("hov",))
    bars = a.bars("#rankFlow")
    neg = sorted([b for b in bars if b["v"] < 0], key=lambda b: b["v"])   # 負值最多的幾條（它們右半邊座標軸右側是空白，提示框放那裡不蓋任何字）
    top = neg[1] if len(neg) > 1 else neg[0]
    a.hover_xy((top["x0"] + top["x1"]) / 2, top["y"], f"排行長條：{top['name']}", 1000, row=a.row_rect("#rankFlow", top, 9, xmax=top["x0"] + 2))
    a.park(region=PARK_R, ms=360)
    a.wait(500)
    a.settle()
    a.set_stage(6, "切產業鏈")
    a.say("換條產業鏈，兩圖同步變", "folder", ("chainr", "clock", "rank"))
    sp_web(a, pg, '#flowRotFilter', "ai_server", "產業鏈：AI 伺服器", PARK_R)
    sp_web(a, pg, '#flowRotFilter', "semiconductor", "產業鏈：半導體", PARK_R)
    a.settle()
    a.set_stage(7, "追晶圓代工")
    a.say("看半導體，先記下晶圓代工", "face_thinking_bulb", ("clock", "rank"))
    a.idle(2600)
    a.settle()
    # 功能二：資金分流樹
    a.set_stage(8, "分流樹")
    a.say("接著看，錢怎麼分下去", "point_r", ("subsankey",))
    a.wait(300)
    a.tap('.l4subtab[data-l4sub="flow-sankey"]', "子選單：資金分流樹")
    a.park(region=PARK_S, ms=300)
    a.until("() => !!document.querySelector('#sankey canvas.ftlab') && window.FlowTopo && FlowTopo.has(document.querySelector('#sankey'))", 10000)
    pg.evaluate("() => scrollTo({ top: 0, behavior: 'instant' })")
    a.wait(900)
    a.park(region=PARK_S, ms=400)
    a.wait(1100)
    a.set_stage(9, "一條主幹")
    a.say("一條主幹，分到各產業", "talk_explain", ("sk",))
    a.idle(3000)
    a.settle()
    a.set_stage(10, "點半導體")
    a.say("點半導體，看它分給誰", "spotlight", ("sk",))
    node = next(n for n in a.sk_nodes() if n["lv"] == 1 and n["text"].startswith("半導體"))
    a.tap_rect([node["x"] - node["r"] + 1, node["y"] - node["r"] + 1, 2 * node["r"] - 2, 2 * node["r"] - 2], "點節點：半導體")
    a.park(region=PARK_S, ms=400)
    a.wait(2200)
    a.settle()
    a.set_stage(11, "看名單")
    a.say("晶圓代工，占這條鏈最大", "face_nod", ("sklist",))
    a.until("() => !!document.querySelector('#sankeyPanel') && document.querySelector('#sankeyPanel').getClientRects().length > 0", 5000)
    pan_y = pans['sk'][0]
    y = pg.evaluate("(py) => document.querySelector('#sankeyPanel').getBoundingClientRect().top + scrollY - py - 4", pan_y)
    y, _c = best_scroll(a, pg, y, (0, pan_y, 1100, 627), span=90, step=1)
    a.note(f"網頁名單捲動 {y}，框緣切字 {_c}")
    a.cursor(False)   # 捲動期間游標先收起（不讓游標從捲動中的字上掃過）
    a.scroll(to_y=y, ms=34)   # 一格內到位（硬切），不出現捲動途中被畫面框上緣切半的字
    a.park(region=(600, 120, 300, 300), ms=10)
    a.cursor(True)
    a.wait(1700)
    a.settle()
    # 功能三：族群×法人
    a.set_stage(12, "法人")
    a.say("最後看法人動向", "point_r", ("subinst",))
    a.wait(300)
    a.tap('.l4subtab[data-l4sub="flow-inst"]', "子選單：族群×法人")
    a.park(region=PARK_I, ms=300)
    a.until("() => !!document.querySelector('#instGroups canvas')", 10000)
    pg.evaluate("() => scrollTo({ top: 0, behavior: 'instant' })")
    a.wait(900)
    a.park(region=PARK_I, ms=400)
    a.wait(1200)
    a.set_stage(13, "三色")
    a.say("外資、投信、自營三色", "magnifier", ("instleg", "inst"))
    a.idle(2700)
    a.settle()
    a.set_stage(14, "只看半導體")
    a.say("同樣只看半導體", "folder", ("instchain", "inst"))
    sp_web(a, pg, '#flowInstCard', "semiconductor", "產業鏈：半導體", PARK_I)
    a.settle()
    a.set_stage(15, "滑過長條")
    a.say("滑過長條，看三種法人", "spotlight", ("hov",))
    b = a.bar("#instGroups", "晶圓代工") or a.bars("#instGroups")[-1]
    a.hover_xy(b["x0"] - 40, b["y"] - 8, f"法人長條：{b['name']}", 1000, row=a.row_rect("#instGroups", b, 9))
    a.park(region=PARK_I, ms=360)
    a.wait(400)
    a.settle()
    a.set_stage(16, "點圖例")
    a.say("拿掉外資，看投信與自營", "talk_explain", ("instleg", "inst"))
    leg = '#instLegend button:nth-child(1)'
    a.tap(leg, "圖例：外資（隱藏）")
    a.park(region=PARK_I, ms=300)
    a.wait(1400)
    a.tap(leg, "圖例：外資（還原）")
    a.park(region=PARK_I, ms=300)
    a.wait(1300)
    a.settle()
    a.set_stage(17, "串成一線")
    a.say("輪動、分流、法人，串成一線", "face_proud", ("inst",))
    a.idle(3300)
    a.settle()


def snap(a, pg, span=150, margin=6, instant=False):
    """手機：目前頁面往下／往上挑一個「畫面框上下緣都不切到字」的位置並捲過去（單向小幅）。"""
    y0 = pg.evaluate("() => scrollY")
    y, c = best_scroll(a, pg, y0, MCROP, span=span, margin=margin)
    a.note(f"手機定位 {y0:.0f}→{y:.0f}，框緣切字 {c}")
    if abs(y - y0) > 1:
        if instant:
            pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", y)
            a.frame()
        else:
            a.scroll(to_y=y, ms=34)
    return c


def reveal_snap(a, pg, hold=400):
    """手機換頁：頁面內容先藏起來（透明），等排版穩了、同一瞬間顯示並直接捲到不切字的位置（不出現未定位的幀）。"""
    a.wait(min(hold, 400))
    # 把「起始偏移」換成真的捲動位置（畫面上位置完全不變）：之後的捲動、點分頁都照一般頁面
    pg.evaluate("() => { const v = parseFloat(document.body.style.getPropertyValue('--vo')) || 0; document.body.style.setProperty('--vo', '0px'); if (v) scrollTo({ top: v, behavior: 'instant' }); }")
    a.frame()
    snap(a, pg, instant=False)


def drift(a, pg, ms):
    """手機沒有游標可晃：長停留拍讓畫面慢慢往下滑一點點；只在「目標位置框緣切字為 0」時才滑，否則原地不動。"""
    cur = pg.evaluate("() => scrollY")
    y, c = best_scroll(a, pg, cur + 16, MCROP, span=14, step=2, margin=8)
    if c == 0 and y > cur + 1:
        sy0 = pg.evaluate("() => scrollY")
        for yy in range(int(cur) + 1, int(y) + 1):   # 慢滑途中每一個位置都要乾淨（不讓字從頂欄下面半截滑過）
            pg.evaluate("(v) => scrollTo({top: v, behavior: 'instant'})", yy)
            pg.wait_for_timeout(20)
            if straddles(a.texts(), MCROP, 8) > 0 or edge_ink(pg, (0, 57, 640, 8), x0=0, x1=632) > 2:
                c = 1
                break
        pg.evaluate("(v) => scrollTo({top: v, behavior: 'instant'})", sy0)
    if c > 0 or y <= cur + 1:
        a.note(f"手機慢滑取消（{cur:.0f}→{y:.0f} 切字 {c}）")
        a.idle(ms)
        return
    a.note(f"手機慢滑 {cur:.0f}→{y:.0f}，框緣切字 {c}")
    a.scroll(to_y=y, ms=ms)


MCROP = (0, 56, 640, 968)   # 手機畫面框：扣掉頂欄（0～56 是不透明頂欄，字被它切到也算切字）


def run_m(pg, a, start):
    CROP = V.CROP0["m"]
    F.goto(pg, "#overview", 3500)
    y0_, _c0 = best_scroll(a, pg, 0, MCROP, span=90, margin=6)   # 總覽從頁首開始（標題「總覽」完整在頂列下方），之後才慢慢往下滑
    pg.wait_for_timeout(300)
    a.crop = CROP
    start()
    a.set_stage(1, "需求")
    a.say("錢到底往哪個族群跑？", "face_think", ("burger",))
    a.idle(4000)
    a.set_stage(2, "三頁")
    a.say("三頁接著看，就有答案", "face_curious", ("burger",))
    y80, _c = best_scroll(a, pg, 60, MCROP, span=30, margin=8)
    a.scroll(to_y=y80, ms=34)
    a.set_stage(3, "導覽")
    a.say("點選單，進資金輪動", "point_ur", ("burger", "m4flow"))
    a.wait(300)
    a.tap("#m4Burger", "選單")
    a.wait(900)
    a.next_vo = 56
    a.tap('.m4item[data-v="flow"]', "選單：資金流向")
    a.until("() => !!document.querySelector('#rotClock canvas') && !!document.querySelector('#rankFlow canvas')", 10000)
    reveal_snap(a, pg, 1300)
    a.wait(1500)
    # 功能一：資金輪動（手機：先在頁首看輪盤＋切產業鏈，再往下捲到排行）
    a.set_stage(4, "看強弱")
    a.say("輪盤看資金強弱", "magnifier", ("clock",))
    drift(a, pg, 4200)
    a.settle()
    a.set_stage(6, "切產業鏈")
    a.say("換條產業鏈，輪盤跟著變", "folder", ("chainr", "clock"))
    sp_mob(a, pg, '#flowRotFilter', "semiconductor", "產業鏈：半導體")
    a.settle()
    a.set_stage(5, "看排行")
    a.say("排行跟著變，看占比增減", "spotlight", ("rank",))
    y = pg.evaluate("() => document.querySelector('#rankFlow').getBoundingClientRect().top + scrollY - 250")
    y, _c = best_scroll(a, pg, y, MCROP, span=220, margin=8)
    a.note(f"手機排行捲動 {y}，框緣切字 {_c}")
    a.scroll(to_y=y, ms=34)
    a.wait(300)
    cur_ = pg.evaluate("() => scrollY")
    # 輪盤整張捲到頂欄上方（輪盤裡的字是畫布，頂欄會把最上面一排字蓋掉半截）：再往下捲到輪盤底緣在頂欄之上，捲不動就取頁尾
    need_ = pg.evaluate("() => { const r = document.querySelector('#rotClock').getBoundingClientRect(); const mx = document.documentElement.scrollHeight - innerHeight; return [scrollY + r.bottom - 64, mx, r.bottom]; }")
    a.note(f"輪盤底緣 {need_[2]:.0f}，需捲到 {need_[0]:.0f}，可捲上限 {need_[1]:.0f}")
    if need_[0] > cur_ and need_[1] > cur_:
        a.scroll(to_y=min(need_[0], need_[1]), ms=34)
        a.wait(200)
        cur_ = pg.evaluate("() => scrollY")
    y2_, c2_ = best_scroll(a, pg, cur_, MCROP, span=40, step=1, margin=8)
    bestk = None
    inks_ = []
    for yy_ in range(int(y2_) + 6, int(y2_) - 150, -2):   # 輪盤上緣的字（畫布字，量不到外框）不被頂欄切半：用像素找頂欄下緣 3px 帶沒有深色的位置
        if yy_ < 0 or yy_ > need_[1]:
            continue
        pg.evaluate("(v) => scrollTo({top: v, behavior: 'instant'})", yy_)
        pg.wait_for_timeout(40)
        ink_ = edge_ink(pg, (0, 57, 640, 8), x0=0, x1=632)
        n_ = straddles(a.texts(), MCROP, 8)
        inks_.append((ink_ + 100 * n_, abs(yy_ - y2_), yy_))
    inks_.sort()
    bestk = inks_[0][2] if inks_ and inks_[0][0] <= 3 else None
    a.note(f"手機排行像素定位 {y2_}→{bestk}；前三名 {inks_[:3]}")
    if bestk is not None:
        y2_, c2_ = bestk, 0
    pg.evaluate("(v) => scrollTo({top: v, behavior: 'instant'})", cur_)   # 實際捲到的位置再量一次（頁面可捲範圍比預期短時，換成真的乾淨的位置）
    a.note(f"手機排行再定位 {cur_:.0f}→{y2_}，框緣切字 {c2_}")
    if abs(y2_ - cur_) > 0.5:
        a.scroll(to_y=y2_, ms=34)
    drift(a, pg, 4200)   # 手機上點長條會直接跳去產業地圖頁（手機沒有 hover），所以不點、不按，只看排行
    a.settle()
    a.set_stage(7, "追晶圓代工")
    a.say("看半導體，先記下晶圓代工", "face_thinking_bulb", ("rank",))
    drift(a, pg, 3800)
    a.settle()
    # 功能二：資金分流樹
    a.set_stage(8, "分流樹")
    a.say("接著看，錢怎麼分下去", "point_ur", ("tabsk",))
    yt, _c = best_scroll(a, pg, 16, MCROP, span=8, margin=5)
    a.scroll(to_y=yt, ms=34)   # 回到分頁列看得到的位置（一格到位）
    a.wait(400)
    a.next_vo = 10
    a.tap('.m4subtabs button[data-sub="flow-sankey"]', "分頁：資金分流樹", bias=(0.14, 0.3))
    a.until("() => !!document.querySelector('#sankey canvas.ftlab') && window.FlowTopo && FlowTopo.has(document.querySelector('#sankey'))", 10000)
    reveal_snap(a, pg, 1200)
    a.wait(500)
    a.set_stage(9, "一條主幹")
    a.say("一條主幹，分到各產業", "talk_explain", ("sk",))
    a.idle(3800)
    a.settle()
    a.set_stage(10, "點半導體")
    a.say("點半導體，看它分給誰", "spotlight", ("sk",))
    node = next(n for n in a.sk_nodes() if n["lv"] == 1 and n["text"].startswith("半"))
    a.tap_rect([node["x"] - node["r"] + 1, node["y"] - node["r"] + 1, 2 * node["r"] - 2, 2 * node["r"] - 2], "點節點：半導體")
    a.wait(900)
    ysn, _c = best_scroll(a, pg, pg.evaluate("() => scrollY"), MCROP, span=80, margin=6)   # 點下去後下方名單面板長出來，內容位置改變 → 再挑一次不切字的捲動位置
    a.note(f"手機點節點後捲動 {ysn}，框緣切字 {_c}")
    a.scroll(to_y=ysn, ms=34)
    a.wait(2000)
    a.settle()
    a.set_stage(11, "看名單")
    a.say("晶圓代工，占這條鏈最大", "face_nod", ("sklist",))
    a.until("() => !!document.querySelector('#sankeyPanel') && document.querySelector('#sankeyPanel').getClientRects().length > 0", 5000)
    y = pg.evaluate("() => document.querySelector('#sankeyPanel').getBoundingClientRect().top + scrollY - 70")
    y, _c = best_scroll(a, pg, y, MCROP, span=140)
    a.note(f"手機名單捲動 {y}，框緣切字 {_c}")
    a.scroll(to_y=y, ms=34)
    a.wait(3000)
    a.settle()
    # 功能三：族群×法人
    a.set_stage(12, "法人")
    a.say("最後看法人動向", "point_ur", ("tabinst",))
    yt, _c = best_scroll(a, pg, 16, MCROP, span=8, margin=5)
    a.scroll(to_y=yt, ms=34)   # 回到分頁列看得到的位置（一格到位）
    a.wait(400)
    a.next_vo = 0
    a.tap('.m4subtabs button[data-sub="flow-inst"]', "分頁：族群×法人", bias=(0.14, 0.3))
    a.until("() => !!document.querySelector('#instGroups canvas')", 10000)
    reveal_snap(a, pg, 1300)
    a.wait(500)
    a.set_stage(13, "三色")
    a.say("外資、投信、自營三色", "magnifier", ("instleg", "inst"))
    drift(a, pg, 2800)
    a.settle()
    a.set_stage(14, "只看半導體")
    a.say("同樣只看半導體", "folder", ("instchain", "inst"))
    sp_mob(a, pg, '#flowInstCard', "semiconductor", "產業鏈：半導體", hold_after=2000)
    a.settle()
    a.set_stage(15, "三色長條")
    a.say("三色長條，各站一邊", "spotlight", ("inst",))
    drift(a, pg, 2600)   # 手機點族群×法人的長條會直接跳去產業地圖頁，所以只看圖與圖例
    a.settle()
    a.set_stage(16, "點圖例")
    a.say("拿掉外資，看投信與自營", "talk_explain", ("instleg", "inst"))
    leg = '#instLegend button:nth-child(1)'
    a.tap(leg, "圖例：外資（隱藏）")
    a.wait(2000)
    a.tap(leg, "圖例：外資（還原）")
    a.wait(1700)
    a.settle()
    a.set_stage(17, "串成一線")
    a.say("輪動、分流、法人，串成一線", "face_proud", ("inst",))
    yq, _c = best_scroll(a, pg, pg.evaluate("() => scrollY") + 30, MCROP, span=30, margin=6)
    a.scroll(to_y=yq, ms=1500)   # 手機沒有游標可晃：收尾拍讓畫面慢慢往下滑一點，不整段靜止
    a.settle()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8817)
    ap.add_argument("--dry", action="store_true")
    g = ap.parse_args()
    if g.dry:
        os.environ["FEAT_DRY"] = "1"
    cfg = dict(actor=A8, site=str(SITE), overlays=OVERLAYS, els=ELS, roots=["body"], blur_sel="#__none", extra_css=EXTRA_CSS if g.dev == "d" else EXTRA_CSS_M, dry=g.dry,
               dev={"d": dict(viewport={"width": 1100, "height": 800}, device_scale_factor=2), "m": dict(viewport={"width": 640, "height": 1024}, device_scale_factor=2, is_mobile=True, has_touch=True)},
               crop0={"d": (0, 0, 1100, 627), "m": (0, 0, 640, 1024)}, ovsel="#__vsel,.fttip.on,.ddpanel,body > div[style*='border-style: solid']",
               init=(["try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}"] if g.dev == "d" else [NOLEAF_JS]) + [SK_JS, FOCUS_JS, TT_JS])
    V.run(g.dev, run_d if g.dev == "d" else run_m, g.out, cfg, g.port)


if __name__ == "__main__":
    main()
