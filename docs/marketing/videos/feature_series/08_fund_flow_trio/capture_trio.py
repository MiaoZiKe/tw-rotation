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
EXTRA_CSS = (".rotdd[data-dd=group] .ddpanel{display:none!important}"
             "header.topbar,#l4Head{background:#f8fbfd!important}"
             ".sitefoot,.sitefoot *{visibility:hidden!important}")
EXTRA_CSS_M = EXTRA_CSS + "@media (max-width:640px){.plknote{display:none!important}}"   # 手機：「Plus 以上可調整」那行小字在捲動後會飄到排行長條的列標上（網站本身的排版問題），錄影端隱藏；時間列仍是反灰原樣
PARK_R = (560, 208, 90, 48)    # 資金輪動：時間列右側、輪盤上方的空白（游標不經過排行長條，下拉清單才不會被圖表連動重畫收掉）
PARK_S = (540, 78, 140, 26)      # 資金分流樹：卡片標題列中間的空白（不在畫布上，不會觸發節點提示與代表股展開）
PARK_I = (530, 190, 35, 380)     # 族群×法人：長條圖右側空白欄
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
    def bars(self, sel):
        return self.pg.evaluate(BARS_JS, sel)

    def bar(self, sel, name):
        for b in self.bars(sel):
            if b["name"] == name:
                return b
        return None

    def row_rect(self, sel, b, hh=11):
        """被 hover 的那一列（含列標、長條、數值）的外框：提示框不可蓋到它（提示框離游標下緣 ≥12px，列高取 ±11px）。"""
        r = self.pg.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.right]; }", sel)
        return [r[0], b["y"] - hh, r[1] - r[0], 2 * hh]

    def set_hov(self, row):
        self.pg.evaluate("(r) => { window.__vhov = r; }", row)

    def clear_hov(self):
        self.pg.evaluate("() => { window.__vhov = null; }")

    def sk_nodes(self):
        return self.pg.evaluate("() => { const h = document.querySelector('#sankey'); const p = FlowTopo.probe(h); return p.nodes.map(n => ({ key: n.key, lv: n.lv, text: n.text, x: n.cx, y: n.cy, r: n.r })); }")

    def hover_xy(self, x, y, label, hold_ms, pre=260, row=None):
        """游標緩移到 (x,y)（路徑不壓字）並停住（hover，不點）；記錄成一次 hover 目標。"""
        texts = self.texts()
        self.glide(x, y, texts, 520)
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


def straddles(texts, crop):
    """文字外框跟畫面框相交、但沒有整個落在畫面框內（外縮 2.6px，同合成端的慢漂邊界）的個數＝框緣切字。"""
    cx, cy, cw, ch = crop
    n = 0
    for z in texts:
        x, y, w, h = z[:4]
        inter = x < cx + cw and x + w > cx and y < cy + ch and y + h > cy
        inside = x >= cx + 2.1 and y >= cy + 2.1 and x + w <= cx + cw - 2.1 and y + h <= cy + ch - 2.1
        if inter and not inside:
            n += 1
    return n


def best_scroll(a, pg, y0, crop, span=36, step=2):
    """y0 附近找「畫面框上下緣不切過任何文字」的捲動位置（instant 捲動，量完還原）。回傳 (y, 切字數)。"""
    sy = pg.evaluate("() => scrollY")
    best = None
    for d in range(-span, span + 1, step):
        y = max(0, y0 + d)
        pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", y)
        pg.wait_for_timeout(30)
        n = straddles(a.texts(), crop)
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
    """錄影前先量：把網頁版會出現的每個頁面狀態各抓一次文字外框，挑一個推近目標 y，讓所有狀態下畫面框上下緣都不切過文字。"""
    pool = []
    F.goto(pg, "#flow/rotation", 5000)
    pool.append(a.texts())
    for c in ("ai_server", "semiconductor"):
        set_chain_js(pg, "#flowRotFilter", c)
        pool.append(a.texts())
    set_chain_js(pg, "#flowRotFilter", "")
    F.goto(pg, "#flow/sankey", 5000)
    pool.append(a.texts())
    F.goto(pg, "#flow/inst", 5000)
    pool.append(a.texts())
    set_chain_js(pg, "#flowInstCard", "semiconductor")
    pool.append(a.texts())
    set_chain_js(pg, "#flowInstCard", "")
    res = []
    W = [10, 4, 8, 14, 7, 13]   # 各狀態在片中停留的大約秒數（輪動全部、AI、半導體、分流樹、法人全部、法人半導體）：切字多半在久留的狀態就更要避開
    for y in range(58, 104):
        per = [straddles(t, (0, y, 1100, 627)) for t in pool]
        res.append((sum(w * n for w, n in zip(W, per)), abs(y - 78), y, per))
    res.sort()
    print("推近目標候選", [(r[2], r[3]) for r in res[:6]], flush=True)
    return res[0][2], sum(res[0][3])


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
    pan_y, pan_cut = survey_web(a, pg2)
    pg2.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    pg2.evaluate(C.PRESET)   # 錄影的預設值（同意紀錄等，不讓同意橫幅入鏡）
    pg2.evaluate("() => { try { localStorage.setItem('tw.layout4.nav', 'mini'); } catch (e) {} }")   # 量測用掉的免費額度（網站對訪客的使用次數）一併清掉，錄影用的頁面維持第一次來的狀態
    a.pg = pg
    pg2.close()
    F.goto(pg, "#overview", 3500)
    ov_y, ov_cut = 8, 0   # 總覽只往下 8px：卡片標題列留在頂欄下面、下緣的卡片標題整個在畫面框內（用 24px 時標題列會被頂欄切掉半截）
    pg.evaluate("(y) => scrollTo({top: y, behavior: 'instant'})", ov_y)
    pg.wait_for_timeout(400)
    a.extra = {"pan_y": pan_y, "pan_cut": pan_cut, "ov_scroll": ov_y, "ov_cut": ov_cut}
    a.note(f"量測：推近目標 y={pan_y}（切字 {pan_cut}）；總覽捲動 {ov_y}（切字 {ov_cut}）")
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
    top = max(bars, key=lambda b: b["v"])   # 全部族群裡占比增加最多的一條（提示框往下展開，落在較短的長條旁）
    a.hover_xy(top["x1"] - 30, top["y"], f"排行長條：{top['name']}", 2300, row=a.row_rect("#rankFlow", top))
    a.park(region=PARK_R, ms=360)
    a.wait(500)
    a.settle()
    a.set_stage(6, "切產業鏈")
    a.say("換條產業鏈，兩圖同步變", "folder", ("chainr", "clock", "rank"))
    open_chain_and_pick(a, pg, '#flowRotFilter', "ai_server", "產業鏈：AI 伺服器", park=PARK_R)
    open_chain_and_pick(a, pg, '#flowRotFilter', "semiconductor", "產業鏈：半導體", park=PARK_R)
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
    y = pg.evaluate("(py) => document.querySelector('#sankeyPanel').getBoundingClientRect().top + scrollY - py - 4", pan_y)
    y, _c = best_scroll(a, pg, y, (0, pan_y, 1100, 627), span=10, step=1)
    a.note(f"網頁名單捲動 {y}，框緣切字 {_c}")
    a.scroll(to_y=y, ms=900)
    a.park(region=(600, 120, 300, 300), ms=400)
    a.wait(1700)
    a.settle()
    # 功能三：族群×法人
    a.set_stage(12, "法人")
    a.say("最後看法人動向", "point_r", ("subinst",))
    a.wait(300)
    a.tap('.l4subtab[data-l4sub="flow-inst"]', "子選單：族群×法人")
    a.park(region=PARK_I, ms=300)
    a.until("() => !!document.querySelector('#instGroups canvas')", 10000)
    a.wait(900)
    a.park(region=PARK_I, ms=400)
    a.wait(1200)
    a.set_stage(13, "三色")
    a.say("外資、投信、自營三色", "magnifier", ("instleg", "inst"))
    a.idle(2700)
    a.settle()
    a.set_stage(14, "只看半導體")
    a.say("同樣只看半導體", "folder", ("instchain", "inst"))
    open_chain_and_pick(a, pg, '#flowInstCard', "semiconductor", "產業鏈：半導體", park=PARK_I, hold_after=2200)
    a.settle()
    a.set_stage(15, "滑過長條")
    a.say("滑過長條，看三種法人", "spotlight", ("hov",))
    b = a.bar("#instGroups", "晶圓代工") or a.bars("#instGroups")[-1]
    a.hover_xy(b["x0"] - 40, b["y"] - 7, f"法人長條：{b['name']}", 2300, row=a.row_rect("#instGroups", b))
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


MCROP = (0, 56, 540, 808)   # 手機畫面框：扣掉頂欄（0～56 是不透明頂欄，字被它切到也算切字）


def run_m(pg, a, start):
    CROP = V.CROP0["m"]
    F.goto(pg, "#overview", 3500)
    a.crop = CROP
    start()
    a.set_stage(1, "需求")
    a.say("錢到底往哪個族群跑？", "face_think", ("burger",))
    a.scroll(to_y=40, ms=3000)   # 總覽慢慢往下滑一點（手機沒有游標可晃，畫面才不會整段靜止）
    a.set_stage(2, "三頁")
    a.say("三頁接著看，就有答案", "face_curious", ("burger",))
    y80, _c = best_scroll(a, pg, 80, MCROP, span=24)
    a.scroll(to_y=y80, ms=1500)
    a.set_stage(3, "導覽")
    a.say("點選單，進資金輪動", "point_ur", ("burger", "m4flow"))
    a.wait(300)
    a.tap("#m4Burger", "選單")
    a.wait(900)
    a.tap('.m4item[data-v="flow"]', "選單：資金流向")
    a.until("() => !!document.querySelector('#rotClock canvas') && !!document.querySelector('#rankFlow canvas')", 10000)
    a.wait(1800)
    # 功能一：資金輪動（手機：先在頁首看輪盤＋切產業鏈，再往下捲到排行）
    a.set_stage(4, "看強弱")
    a.say("輪盤看資金強弱", "magnifier", ("clock",))
    a.idle(2800)
    a.settle()
    a.set_stage(6, "切產業鏈")
    a.say("換條產業鏈，輪盤跟著變", "folder", ("chainr", "clock"))
    open_chain_and_pick(a, pg, '#flowRotFilter', "ai_server", "產業鏈：AI 伺服器", mob=True, hold_after=2000)
    open_chain_and_pick(a, pg, '#flowRotFilter', "semiconductor", "產業鏈：半導體", mob=True, hold_after=2200)
    a.settle()
    a.set_stage(5, "看排行")
    a.say("排行跟著變，看占比增減", "spotlight", ("rank",))
    y = pg.evaluate("() => document.querySelector('#rankFlow').getBoundingClientRect().top + scrollY - 250")
    y, _c = best_scroll(a, pg, y, MCROP, span=40)
    a.note(f"手機排行捲動 {y}，框緣切字 {_c}")
    a.scroll(to_y=y, ms=900)
    a.idle(2800)   # 手機上點長條會直接跳去產業地圖頁（手機沒有 hover），所以不點、不按，只看排行
    a.settle()
    a.set_stage(7, "追晶圓代工")
    a.say("看半導體，先記下晶圓代工", "face_thinking_bulb", ("rank",))
    a.idle(2200)
    a.settle()
    # 功能二：資金分流樹
    a.set_stage(8, "分流樹")
    a.say("接著看，錢怎麼分下去", "point_ur", ("tabsk",))
    a.scroll(to_y=0, ms=800)
    a.wait(400)
    a.tap('.m4subtabs button[data-sub="flow-sankey"]', "分頁：資金分流樹")
    a.until("() => !!document.querySelector('#sankey canvas.ftlab') && window.FlowTopo && FlowTopo.has(document.querySelector('#sankey'))", 10000)
    a.wait(150)
    ysk, _c = best_scroll(a, pg, 0, MCROP, span=60)
    a.note(f"手機分流樹捲動 {ysk}，框緣切字 {_c}")
    a.scroll(to_y=ysk, ms=600)
    a.wait(500)
    a.set_stage(9, "一條主幹")
    a.say("一條主幹，分到各產業", "talk_explain", ("sk",))
    a.idle(3000)
    a.settle()
    a.set_stage(10, "點半導體")
    a.say("點半導體，看它分給誰", "spotlight", ("sk",))
    node = next(n for n in a.sk_nodes() if n["lv"] == 1 and n["text"].startswith("半"))
    a.tap_rect([node["x"] - node["r"] + 1, node["y"] - node["r"] + 1, 2 * node["r"] - 2, 2 * node["r"] - 2], "點節點：半導體")
    a.wait(2200)
    a.settle()
    a.set_stage(11, "看名單")
    a.say("晶圓代工，占這條鏈最大", "face_nod", ("sklist",))
    a.until("() => !!document.querySelector('#sankeyPanel') && document.querySelector('#sankeyPanel').getClientRects().length > 0", 5000)
    y = pg.evaluate("() => document.querySelector('#sankeyPanel').getBoundingClientRect().top + scrollY - 70")
    y, _c = best_scroll(a, pg, y, MCROP)
    a.note(f"手機名單捲動 {y}，框緣切字 {_c}")
    a.scroll(to_y=y, ms=900)
    a.wait(2200)
    a.settle()
    # 功能三：族群×法人
    a.set_stage(12, "法人")
    a.say("最後看法人動向", "point_ur", ("tabinst",))
    a.scroll(to_y=0, ms=800)
    a.wait(400)
    a.tap('.m4subtabs button[data-sub="flow-inst"]', "分頁：族群×法人")
    a.until("() => !!document.querySelector('#instGroups canvas')", 10000)
    a.wait(1600)
    a.set_stage(13, "三色")
    a.say("外資、投信、自營三色", "magnifier", ("instleg", "inst"))
    a.idle(2700)
    a.settle()
    a.set_stage(14, "只看半導體")
    a.say("同樣只看半導體", "folder", ("instchain", "inst"))
    open_chain_and_pick(a, pg, '#flowInstCard', "semiconductor", "產業鏈：半導體", mob=True, hold_after=2200)
    a.settle()
    a.set_stage(15, "三色長條")
    a.say("三色長條，各站一邊", "spotlight", ("inst",))
    a.idle(2600)   # 手機點族群×法人的長條會直接跳去產業地圖頁，所以只看圖與圖例
    a.settle()
    a.set_stage(16, "點圖例")
    a.say("拿掉外資，看投信與自營", "talk_explain", ("instleg", "inst"))
    leg = '#instLegend button:nth-child(1)'
    a.tap(leg, "圖例：外資（隱藏）")
    a.wait(2000)
    a.tap(leg, "圖例：外資（還原）")
    a.wait(1300)
    a.settle()
    a.set_stage(17, "串成一線")
    a.say("輪動、分流、法人，串成一線", "face_proud", ("inst",))
    a.scroll(to_y=pg.evaluate("() => scrollY") + 36, ms=2300)   # 手機沒有游標可晃：收尾拍讓畫面慢慢往下滑一點，不整段靜止
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
               dev={"d": dict(viewport={"width": 1100, "height": 720}, device_scale_factor=2)},
               crop0={"d": (0, 0, 1100, 627)}, ovsel="#__vsel,.fttip.on,.ddpanel,body > div[style*='border-style: solid']",
               init=(["try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}"] if g.dev == "d" else []) + [SK_JS])
    V.run(g.dev, run_d if g.dev == "d" else run_m, g.out, cfg, g.port)


if __name__ == "__main__":
    main()
