"""功能介紹影片 07：熱力圖（產業）＋題材 —— 素材錄製（沿用 06 的 capture_ev.py：訪客假後端、字型、時鐘、自繪下拉、逐格鏡頭外框）。

一律「未登入訪客」的真實畫面（Andy 10-19），錄的是 origin/main 的 site/（FEAT_SITE 指到 main 的 worktree），資料用 `SKIP_INTRADAY=1 python -m pipeline.build_payload` 重算。
訪客在正式站：熱力圖「點方塊跳族群頁」（heat.link）要 Plus 以上、訪客點了安靜無效 → 本片產業熱力圖不點方塊跳頁，改示範分組切換、色階圖例篩選、懸停提示；
題材熱力圖點方塊是「同頁開下方剖析圖」（data-hmstay，不算跳頁），訪客可用 → 連點三個題材、再點剖析圖的環節卡。

法遵：只講族群與題材；剖析圖上的個股代號標籤（.scode）與個股連結一律模糊（只在錄影的瀏覽器裡，不改 site/）。

用法：FEAT_SITE=<main worktree>/site python capture_hm.py --dev d|m [--shots open,guide,ind,thm,end]
輸出（大檔，放 scratchpad）：<out>/<dev>_<鏡頭>.mp4 ＋ <out>/<dev>_<鏡頭>.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat07")
sys.path.insert(0, str(HERE.parent / "06_events_articles"))
sys.path.insert(0, str(HERE.parent / "05_fund_flow"))
import capture_ev as E  # noqa: E402  （06 的錄影器；同時載入 05 的 capture_flow）

F = E.F
C = E.C
SCR = E.SCR
SITE = E.SITE
DEVS = F.DEVS

BLUR_CSS = "a[href^='#stock/'],.scode,.__vblur{filter:blur(7px)!important}.sitefoot,.sitefoot *{visibility:hidden!important}#artQuota,#evQuota{display:none!important}"
BLUR_JS = r"""
(() => { const css = %s;
  const go = () => { const st = document.createElement('style'); st.id = '__blurco'; st.textContent = css; (document.head || document.documentElement).appendChild(st); window.__vblurReady = true; };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % json.dumps(BLUR_CSS)

class A(E.A):
    def select_show(self, sel, value, label="", ms=420):
        n0 = len(self.targets)
        ok = super().select_show(sel, value, label, ms)
        if ok and len(self.targets) > n0 and self.targets[n0].get("label") == "日期下拉":
            self.targets[n0]["label"] = f"開啟下拉：{label}"   # 06 的 select_show 把開啟那一下固定標成「日期下拉」，這裡改成實際的下拉
        return ok


DG_FOCUS = ["#themeDetail .card h3", "all:#themeDiagram g.stn"]   # 剖析圖：標題列＋五張環節卡（不含下方製作流程列；整張卡比畫面框的比例高，放不進）
HEAT_EDGES = ["ztext:#indTree", "txt:#indHeat .hmcell", "txt:#indHeat h3", "txt:#__vsel div", "txt:#indHeat .hmctl"]
THM_EDGES = ["ztext:#themeMap", "txt:#themeMapCard .hmcell", "txt:#themeMapCard h3", "txt:#themeCtl", "txt:#__vsel div", "txt:#themeDetail h3", "txt:#themeDetail small", "txt:#themeDiagram svg"]
NAV_EDGES = ["txt:#tabs .tab", "txt:#tabs .l4subtab"]

TIP_JS = r"""() => { const e = [...document.body.children].find(x => (x.getAttribute('style') || '').indexOf('9999999') >= 0 && x.getClientRects().length && getComputedStyle(x).display !== 'none' && +getComputedStyle(x).opacity > 0.05);
  if (!e) return null; const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }"""


def goto(pg, hash_, wait=4500):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(500)


def tm(a, sel, kws):
    """用 ECharts 版面找名稱含 kws 之一的方塊中心（viewport css）。"""
    for kw in ([kws] if isinstance(kws, str) else kws):
        r = a.pg.evaluate(C.TM_FIND_JS, [sel, kw])
        if r:
            return r
    a.note(f"（熱力圖找不到方塊：{kws}）")
    return None


def tm_hover(a, sel, kws, host, ms=620, hold=700, top=False):
    r = tm(a, sel, kws)
    if not r:
        return None
    x, y = r["x"] + r["w"] / 2, (r["y"] + min(14, r["h"] * 0.3) if top else r["y"] + r["h"] / 2)
    a.move(x, y, ms)
    a.wait(hold)
    tip = a.pg.evaluate(TIP_JS)
    hb = a.pg.evaluate(C.RECT_JS, host)
    if not tip:
        a.note(f"⚠ 沒出現提示框：{r['n']}")
    elif hb and (tip[0] < hb[0] - 1 or tip[1] < hb[1] - 1 or tip[0] + tip[2] > hb[0] + hb[2] + 1 or tip[1] + tip[3] > hb[1] + hb[3] + 1):
        a.note(f"⚠ 提示框超出圖表範圍：{r['n']} tip={[round(v) for v in tip]} 圖={[round(v) for v in hb]}")
    a.note(f"懸停：{r['n']}")
    return r


def tm_click(a, sel, kws, label, host, ms=520, pause=160):
    r = tm(a, sel, kws)
    if not r:
        return None
    x, y = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    a.note(f"點方塊 {label}：{r['n']}")
    a.click_xy(x, y, ms, pause, expect=host)
    tg = a.targets[-1]
    tg["label"] = label
    tg["rect_center"] = a._vpt(x, y)
    tg["measured_by"] = "ECharts 版面算出的方塊中心"
    return r


def cell_click(a, sel, label):
    return a.click(sel, ms=380, pause=150, label=label)


def heat_cam(pg, a, legend=True, label="產業熱力圖", pad=10, zoom=True, edges=None):
    sels = ["#indTree"] + (["all:#indHeat .hmcell"] if legend else [])
    a.cam(sels, pad, label, minw=F.ZMIN, edges=edges or HEAT_EDGES, zoom=zoom)


def sel_drop_rect(pg, sel, value):
    """自繪展開清單實際高度（量完就拿掉，不入鏡）→ 取景範圍要含它。"""
    pg.evaluate(E.SEL_OVERLAY_JS, [sel, value])
    ov = pg.evaluate(C.RECT_JS, "#__vsel")
    pg.evaluate("() => document.getElementById('__vsel').remove()")
    sb = pg.evaluate(C.RECT_JS, sel)
    return f"rect:{min(sb[0], ov[0]):.1f},{sb[1]:.1f},{max(sb[0] + sb[2], ov[0] + ov[2]) - min(sb[0], ov[0]):.1f},{ov[1] + ov[3] - sb[1] + 6:.1f}"


# ------------------------------------------------------------------ 網頁版（1000×600，推近 ≥1.7 倍）
def d_open(pg, a, start):
    goto(pg, "#heatmap/industry", 4500)
    a.x, a.y = 940, 120
    start()
    heat_cam(pg, a, legend=True, label="產業熱力圖（全市場）")
    a.say("錢集中在哪個族群？", "face_think_v2")
    tm_hover(a, "#indTree", ["晶圓代工", "AI 伺服器"], "#indTree")
    a.idle(300)
    a.say("哪個題材最熱？", "fire")
    tm_hover(a, "#indTree", ["PCB 載板", "CCL"], "#indTree")
    a.idle(400)
    tm_hover(a, "#indTree", ["HBM", "記憶體"], "#indTree")
    a.idle(500)
    a.settle()


def d_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    tb = pg.evaluate(C.RECT_JS, '#tabs .tab[data-view="heatmap"]')
    a.x, a.y = 600, 300
    start()
    nav = f"rect:{tb[0] - 6:.1f},{tb[1] - 1:.1f},{tb[2] + 12:.1f},106"
    a.cam([nav], 0, "推近：左側選單「熱力圖」", minw=200, edges=NAV_EDGES, zoom=True)
    a.say("左側選單「熱力圖」", "point_r_v2")
    a.hover('#tabs .tab[data-view="heatmap"]', 520)
    a.click('#tabs .tab[data-view="heatmap"]', label="選單：熱力圖")
    a.wait(1300)
    a.say("底下切產業、題材", "tap")
    a.click('.l4subtab[data-l4sub="heat-theme"]', label="子分頁：題材")
    a.wait(1300)
    a.click('.l4subtab[data-l4sub="heat-industry"]', label="子分頁：產業")
    a.wait(1100)
    a.settle()


def d_ind(pg, a, start):
    goto(pg, "#heatmap/industry", 4500)
    a.x, a.y = 940, 120
    start()
    heat_cam(pg, a, legend=True, label="推近：熱力圖方塊")
    a.say("方塊越大，成交越多", "magnifier")
    tm_hover(a, "#indTree", ["晶圓代工", "AI 伺服器"], "#indTree")
    a.idle(250)
    tm_hover(a, "#indTree", ["被動元件", "面板"], "#indTree")
    a.idle(300)
    a.say("顏色看今日漲跌", "face_nod_v2")
    tm_hover(a, "#indTree", ["PCB 載板", "玻纖布"], "#indTree")
    a.idle(400)
    # 分組下拉（原生下拉錄不到展開 → 自繪展開清單）：不分組 → 產業鏈
    drop = sel_drop_rect(pg, "#indTreeGroup", "flat")
    a.cam(["#indTreeGroup", drop, "#indTree"], 10, "推近：分組下拉＋熱力圖", minw=F.ZMIN, edges=HEAT_EDGES, zoom=True)
    a.wait(700)
    a.say("分組可以切換", "folder")
    a.select_show("#indTreeGroup", "flat", "分組：不分組")
    a.wait(1100)
    a.say("不分組，一眼比大小", "talk_explain_v2")
    a.select_show("#indTreeGroup", "chain", "分組：產業鏈")
    a.wait(900)
    heat_cam(pg, a, legend=True, label="推近：熱力圖＋色階圖例")
    a.wait(700)
    a.say("點色階，只看那一級", "spotlight")
    for b in (5, 1, 4):
        cell_click(a, f'#indHeat .hmcell[data-bin="{b}"]', f"色階：第 {b + 1} 級")
        a.wait(1000)
    cell_click(a, '#indHeat .hmcell[data-bin="4"]', "色階：取消篩選")
    a.wait(900)
    a.settle()


def d_thm(pg, a, start):
    goto(pg, "#heatmap/theme", 4500)
    a.x, a.y = 940, 420
    start()
    mp = ["#themeMapCard"]
    a.cam(mp, 4, "推近：題材資金熱力", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
    a.say("題材熱度，藍冷紅熱", "fire")
    tm_hover(a, "#themeMap", ["高階 PCB", "AI 伺服器"], "#themeMapCard", top=True)
    a.idle(250)
    tm_hover(a, "#themeMap", ["蘋果供應鏈", "AI 伺服器"], "#themeMapCard", top=True)
    a.idle(350)
    drop = sel_drop_rect(pg, "#themeColorSel", "chg")
    a.cam(mp + [drop], 4, "推近：顏色下拉＋題材熱力", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
    a.wait(700)
    a.say("切換顏色看漲跌", "face_curious")
    a.select_show("#themeColorSel", "chg", "顏色：平均漲跌")
    a.wait(1100)
    a.select_show("#themeColorSel", "heat", "顏色：熱度")
    a.wait(900)
    a.cam(mp, 4, "推近：題材資金熱力（點方塊）", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
    first = True
    for kw, lab in ((["CoWoS"], "CoWoS／先進封裝"), (["矽光子"], "矽光子／CPO"), (["高階 PCB"], "高階 PCB／CCL")):
        a.cam(mp, 4, f"推近：點方塊（{lab}）", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
        a.wait(700)
        if first:
            a.say("點方塊，展開剖析圖", "magic_frame")
        tm_click(a, "#themeMap", kw, f"題材：{lab}", "#themeMap")
        a.wait(500)
        a.cam(DG_FOCUS, [4, 3], f"推近：產品剖析圖（{lab}）", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
        if first:
            a.say("上中下游一張圖看完", "talk_explain_v2")
        a.wait(1100)
        first = False
    a.say("點環節，其他淡掉", "bulb")
    for p in ("glass", "press", "abf"):
        a.click(f'#themeDiagram g.stn[data-part="{p}"]', ms=420, pause=150, label=f"環節：{p}")
        a.wait(900)
    a.settle()


def d_end(pg, a, start):
    goto(pg, "#heatmap/theme/pcb_ccl", 5000)
    a.x, a.y = 940, 300
    start()
    a.cam(["#themeMapCard"], 4, "推近：題材資金熱力", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
    a.say("熱力圖＋題材，一站看懂", "proud_shine")
    a.move(700, 200, 900)
    a.cam(DG_FOCUS, [4, 3], "推近：產品剖析圖", minw=F.ZMIN, edges=THM_EDGES, zoom=True)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.move(500, 520, 900)
    a.settle()


# ------------------------------------------------------------------ 手機版（390×844，m4 版面；點方塊開底部面板）
M_HEAT = ["#indTree", "all:#indHeat .hmcell"]


def m_open(pg, a, start):
    goto(pg, "#heatmap/industry", 4500)
    start()
    a.cam(["#indHeat .card"], 4, "產業熱力圖（全市場）", edges=HEAT_EDGES)
    a.say("錢集中在哪個族群？", "face_think_v2")
    a.idle(1100)
    a.say("哪個題材最熱？", "fire")
    a.idle(1100)
    a.settle()


def m_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-v="heatmap"]', '.m4item[data-v="flow"]', '.m4item[data-v="industry"]'], 10, "選單抽屜", edges=[])
    a.say("點「熱力圖」", "tap")
    a.click('.m4item[data-v="heatmap"]', label="選單：熱力圖")
    a.wait(1700)
    a.cam(['button[data-sub="heat-industry"]', 'button[data-sub="heat-theme"]', "#indHeat h3"], 8, "進到熱力圖：產業／題材分頁", edges=HEAT_EDGES + ["txt:button[data-sub]"])
    a.say("上方切產業、題材", "point_dr_v2")
    a.click('button[data-sub="heat-theme"]', label="分頁：題材")
    a.wait(1100)
    a.click('button[data-sub="heat-industry"]', label="分頁：產業")
    a.wait(900)
    a.settle()


def m_ind(pg, a, start):
    goto(pg, "#heatmap/industry", 4500)
    start()
    a.cam(["#indHeat .card"], 4, "產業熱力圖", edges=HEAT_EDGES)
    a.say("方塊越大，成交越多", "magnifier")
    a.idle(700)
    a.say("點方塊，看漲跌與成交", "spotlight")
    for kw, lab in ((["晶圓代工"], "晶圓代工"), (["玻纖布", "軟板"], "AI 伺服器鏈"), (["HPC"], "HPC")):
        a.cam(["#indTree", "#mSheet"], 4, f"點方塊＋底部面板（{lab}）", edges=HEAT_EDGES + ["txt:#mSheet"])
        tm_click(a, "#indTree", kw, f"方塊：{lab}", "#indTree")
        a.wait(1300)
    a.click("#mSheetBack", label="點背景關閉面板") if pg.locator("#mSheetBack").count() else None
    a.wait(700)
    drop = sel_drop_rect(pg, "#indTreeGroup", "flat")
    a.cam(["#indHeat .card", drop], 4, "分組下拉＋熱力圖", edges=HEAT_EDGES)
    a.say("分組可以切換", "folder")
    a.select_show("#indTreeGroup", "flat", "分組：不分組")
    a.wait(1100)
    a.say("不分組，一眼比大小", "talk_explain_v2")
    a.select_show("#indTreeGroup", "chain", "分組：產業鏈")
    a.wait(900)
    a.cam(["#indHeat .card"], 4, "熱力圖＋色階圖例", edges=HEAT_EDGES)
    a.say("點色階，只看那一級", "spotlight")
    for b in (5, 1, 4):
        cell_click(a, f'#indHeat .hmcell[data-bin="{b}"]', f"色階：第 {b + 1} 級")
        a.wait(1000)
    cell_click(a, '#indHeat .hmcell[data-bin="4"]', "色階：取消篩選")
    a.wait(800)
    a.settle()


def m_thm(pg, a, start):
    goto(pg, "#heatmap/theme", 4500)
    start()
    a.cam(["#themeMapCard"], 4, "題材資金熱力", edges=THM_EDGES)
    a.say("題材熱度，藍冷紅熱", "fire")
    a.idle(900)
    drop = sel_drop_rect(pg, "#themeColorSel", "chg")
    a.cam(["#themeMapCard", drop], 4, "顏色下拉＋題材熱力", edges=THM_EDGES)
    a.say("切換顏色看漲跌", "face_curious")
    a.select_show("#themeColorSel", "chg", "顏色：平均漲跌")
    a.wait(1100)
    a.select_show("#themeColorSel", "heat", "顏色：熱度")
    a.wait(900)
    first = True
    for kw, lab in ((["CoWoS"], "CoWoS／先進封裝"), (["矽光子"], "矽光子／CPO"), (["高階 PCB"], "高階 PCB／CCL")):
        a.cam_view("捲動")
        a.scroll_to_el("#themeMapCard", 62, 600)
        a.cam(["#themeMapCard"], 4, f"點方塊（{lab}）", edges=THM_EDGES)
        if first:
            a.say("點方塊，展開剖析圖", "magic_frame")
        tm_click(a, "#themeMap", kw, f"題材：{lab}", "#themeMap")
        a.wait(500)
        a.cam_view("捲動")
        a.scroll_to_el("#themeDetail", 64, 700)
        a.cam(["#themeDetail .card"], 4, f"產品剖析圖（{lab}）", edges=THM_EDGES)
        if first:
            a.say("上中下游一張圖看完", "talk_explain_v2")
        a.wait(1100)
        first = False
    a.say("點環節，展開細節", "bulb")
    for n in (2, 3):
        a.click(f"#themeDiagram .vstep:nth-of-type({n})", label=f"環節：第 {n} 步") if pg.locator(f"#themeDiagram .vstep:nth-of-type({n})").count() else a.note(f"找不到環節 {n}")
        a.wait(900)
    a.settle()


def m_end(pg, a, start):
    goto(pg, "#heatmap/theme", 4500)
    start()
    a.cam(["#themeMapCard"], 4, "題材資金熱力", edges=THM_EDGES)
    a.say("熱力圖＋題材，一站看懂", "proud_shine")
    a.idle(1300)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.idle(1300)
    a.settle()


VP_D = {"open": (1000, 600, 2.2), "guide": (1600, 900, 4), "ind": (1000, 600, 2.2), "thm": (1000, 960, 2), "end": (1000, 960, 2)}
D_SHOTS = {"open": d_open, "guide": d_guide, "ind": d_ind, "thm": d_thm, "end": d_end}
M_SHOTS = {"open": m_open, "guide": m_guide, "ind": m_ind, "thm": m_thm, "end": m_end}


def run(dev, shots, out, port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    site_meta = json.loads((SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    reg = D_SHOTS if dev == "d" else M_SHOTS
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist"])
            for sid in shots or list(reg):
                cfg = dict(DEVS[dev])
                if dev == "d" and sid in VP_D:
                    w_, h_, k_ = VP_D[sid]
                    cfg["viewport"] = {"width": w_, "height": h_}
                    cfg["device_scale_factor"] = k_
                W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
                H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                _tpe = _dt.timezone(_dt.timedelta(hours=8))
                _now = _dt.datetime.now(tz=_tpe)
                _day = _now.date() if _now.hour >= 5 else _now.date() - _dt.timedelta(days=1)
                ctx.clock.install(time=_dt.datetime(_day.year, _day.month, _day.day, 14, 30, tzinfo=_tpe))
                F.route_fonts(ctx)
                E.guest_api(ctx)
                ctx.add_init_script(F.FONT_JS)
                ctx.add_init_script(C.PRESET)
                ctx.add_init_script(C.HIDE_B_JS)
                ctx.add_init_script(E.CLIP_JS)
                ctx.add_init_script(BLUR_JS)
                ctx.add_init_script("try{localStorage.removeItem('tw.themeColor');localStorage.removeItem('tw.hmGroup')}catch(e){}")
                if dev == "d" and sid != "guide":
                    ctx.add_init_script("try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}")
                if dev == "d" and sid in ("open", "ind"):   # 熱力圖卡片撐滿視窗高度，客服鈕（固定在右下角）會壓在方塊上 → 錄影瀏覽器裡把它挪到左下角（導覽列下方），取景框內沒有客服鈕
                    ctx.add_init_script("(() => { const go = () => { const st = document.createElement('style'); st.textContent = 'html body #supFab{right:auto!important;left:6px!important}'; document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();")
                ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                pg.evaluate("() => document.fonts.ready")
                pg.wait_for_function("() => window.__vblurReady === true", timeout=15000)
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
                a.x, a.y = (900, 500) if dev == "d" else (370, 160)
                a.dsf = cfg["device_scale_factor"]
                rec = F.Rec(pg, W, H, a)

                def start(rec=rec, a=a, sid=sid):
                    a.rec = rec
                    if a.mob:
                        a.cursor(False)
                        pg.mouse.move(*A.PARK)
                    else:
                        a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.idle(520)
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = [0, cfg["viewport"]["width"]]
                    r.update(timer_errs=getattr(rec, 'timer_errs', []), fabs=rec.fabs, edges=rec.edges, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:8], flush=True)
                except Exception as exc:  # noqa: BLE001
                    import traceback
                    traceback.print_exc()
                    rec.on = False
                    print(sid, "失敗", exc)
                    print("\n".join(a.log[-12:]))
                    shutil.rmtree(out / f".tmp_{dev}_{sid}", ignore_errors=True)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8817)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
