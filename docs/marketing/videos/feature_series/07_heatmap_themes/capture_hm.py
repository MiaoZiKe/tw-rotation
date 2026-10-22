"""功能介紹影片 07 熱力圖＋題材 v3 —— 一口氣錄完（單一鏡頭、不換頁、只允許一次單向推近／往下捲）。

主線（一條因果線）：錢集中在哪個族群？→ 點「熱力圖」進產業熱力圖 → 看方塊大小與顏色 → 分組、色階一鍵篩 → 想看題材 → 點「題材」
→ 題材熱力圖點一個題材方塊 → 剖析圖展開（往下捲、推近）→ 點環節看細節。
訪客在正式站：產業熱力圖「點方塊跳族群頁」要 Plus 以上，所以不點方塊跳頁；題材熱力圖點方塊是同頁開剖析圖（訪客可用）。
法遵：只講族群與題材；剖析圖個股代號標籤與個股連結一律模糊；圖表提示框在錄影的瀏覽器裡關掉（只在錄影時，不改 site/）。
錄法：06_events_articles/vidlib3.py。用法：FEAT_SITE=<main worktree>/site python capture_hm.py --dev d|m
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "06_events_articles"))
import vidlib3 as V  # noqa: E402

F, C = V.F, V.C
SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat07"))
SITE = Path(os.environ.get("FEAT_SITE", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat06/main_wt/site"))
OVERLAYS = ['.ddpanel:not([hidden])', '.twms-pan', '#__vsel', '[role=dialog]', '.toast', '#howPop', '.qcov', '.qcard', '#mSheet:not([hidden])', '#mSheetBack:not([hidden])']
ELS = {"indtree": "#indTree", "navheat": '#tabs .tab[data-view="heatmap"]', "navthm": '.l4subtab[data-l4sub="heat-theme"]', "indcard": "#indHeat", "themecard": "#themeMapCard",
       "det": "#themeDetail", "dg": "#themeDiagram", "burger": "#m4Burger", "m4heat": '.m4item[data-v="heatmap"]', "mtabs": 'button[data-sub="heat-theme"]'}
ZCHARTS = [["ind", "#indTree"], ["thm", "#themeMap"]]
DEV = {"d": dict(viewport={"width": 1050, "height": 604}, device_scale_factor=2), "m": V.CFG_DEV["m"]}
CROP = {"d": (0, 44, 1050, 556.6), "m": (0, 0, 540, 864)}
ZOOM_D = (72, 44, 978, 518.4)
EXTRA_CSS = ".zbadge{display:none!important}@media (min-width:641px){.topbar>.brand .logo{visibility:hidden!important}}body.__vnb #l4NavBtn{visibility:hidden!important}.sitefoot{visibility:hidden!important}body.__nodg #themeDetail{visibility:hidden!important}"


def goto_overview(pg):
    F.goto(pg, "#overview", 3500)


def tm_rect(pg, sel, kws):
    for kw in ([kws] if isinstance(kws, str) else kws):
        r = pg.evaluate(C.TM_FIND_JS, [sel, kw])
        if r:
            return r
    return None


def strip_rect(pg, d=True):
    """分組下拉清單畫在卡片標題列的空白處（選單左邊）。"""
    b = pg.evaluate(C.RECT_JS, "#indTreeGroup")
    if d:
        return (b[0] - 285, b[1] - 6, 200, 28)
    return (b[0] + b[2] + 14, b[1] + 4, 200, 30)


def run_d(pg, a, start):
    goto_overview(pg)
    pg.evaluate("() => scrollTo(0, 30)")   # 往下 30px：總覽圖表的 x 軸字落在畫面框內，下緣落在卡片間的空白
    pg.wait_for_timeout(400)
    a.crop = CROP["d"]
    a.x, a.y = 600, 300
    a.park(region=(300, 250, 400, 250))
    start()
    a.set_stage(1, "需求")
    a.say("錢集中在哪個族群？", "face_think_v2", ("navheat",))
    a.idle(1100)
    a.set_stage(2, "引導")
    a.say("點熱力圖，看產業分布", "tap", ("navheat",))
    a.wait(300)
    a.tap('#tabs .tab[data-view="heatmap"]', "選單：熱力圖")
    a.wait(150)
    a.park(ms=300, prefer=(a.x + 60, a.y + 60))
    a.until("() => !!document.querySelector('#indTree canvas')", 8000)
    a.wait(700)
    a.park(region=(300, 250, 400, 250))
    # 3 看圖
    a.set_stage(3, "看圖")
    a.say("大小看成交，顏色看漲跌", "magnifier", ("indcard",))
    a.idle(1500)
    a.settle()
    # 4 篩選：分組＋色階
    a.set_stage(4, "篩選")
    a.say("分組、色階，一鍵篩選", "folder", ("indcard",))
    sr = strip_rect(pg)
    opts = [("chain", "產業鏈"), ("flat", "不分組")]
    a.strip_pick("#indTreeGroup", "flat", opts, sr, "分組：不分組")
    a.park(region=CROP["d"], ms=260)
    a.wait(800)
    a.strip_pick("#indTreeGroup", "chain", opts, sr, "分組：產業鏈")
    a.park(region=CROP["d"], ms=260)
    a.wait(500)
    for b in (5, 1):
        a.tap(f'#indHeat .hmcell[data-bin="{b}"]', f"色階：第 {b + 1} 級")
        a.wait(250)
        a.park(region=CROP["d"], ms=260)
        a.wait(700)
    a.tap('#indHeat .hmcell[data-bin="1"]', "色階：取消篩選")
    a.wait(250)
    a.park(region=CROP["d"], ms=260)
    a.wait(500)
    a.settle()
    # 5 題材
    a.set_stage(5, "題材")
    a.say("想看題材？點題材", "face_curious", ("navthm",))
    a.wait(300)
    a.tap('.l4subtab[data-l4sub="heat-theme"]', "選單：題材")
    a.wait(150)
    a.park(ms=300, prefer=(a.x + 60, a.y + 60))
    a.until("() => !!document.querySelector('#themeMap canvas')", 8000)
    a.wait(700)
    a.park(region=(300, 300, 400, 200))
    # 6 剖析：點方塊 → 往下捲＋推近 → 點環節
    a.set_stage(6, "剖析")
    a.crop = ZOOM_D
    pg.evaluate("() => document.body.classList.add('__vnb')")
    a.say("點方塊，再點環節看細節", "spotlight", ("themecard", "dg"))
    a.wait(900)
    r = tm_rect(pg, "#themeMap", ["高階 PCB", "AI 伺服器"])
    a.tap_rect([r["x"], r["y"], r["w"], r["h"]], f"題材：{r['n']}", expect="#themeMap")
    a.cursor(False)   # 頁面要往下捲：游標先淡出（不讓字從游標下滑過），捲完在空白處淡入
    a.wait(260)
    a.until("() => !!document.querySelector('#themeDiagram g.stn')", 8000)
    y = pg.evaluate("() => document.querySelector('#themeDetail').getBoundingClientRect().top + scrollY - 54")
    a.scroll(to_y=y, ms=800)
    a.wait(300)
    a.park(region=ZOOM_D, prefer=(900, 120), ms=10)
    a.cursor(True)
    a.wait(300)
    for p in ("glass", "press", "abf"):
        a.tap(f'#themeDiagram g.stn[data-part="{p}"]', f"環節：{p}")
        a.wait(250)
        a.park(region=ZOOM_D, ms=260)
        a.wait(800)
    a.settle()


def scroll_stable(a, n=6, max_ms=2800):
    """頁面捲動（含網站點方塊後自己平滑捲到剖析圖）停穩了才繼續：連續 n 格 scrollY 不變。"""
    last, same = None, 0
    for _ in range(int(max_ms * 30 / 1000)):
        y = a.pg.evaluate("() => Math.round(scrollY)")
        same = same + 1 if y == last else 0
        last = y
        if same >= n:
            return
        a.wait(33)


def run_m(pg, a, start):
    goto_overview(pg)
    a.crop = CROP["m"]
    start()
    a.set_stage(1, "需求")
    a.say("錢集中在哪個族群？", "face_think_v2", ("burger",))
    a.idle(1100)
    a.set_stage(2, "引導")
    a.say("點選單，進熱力圖", "point_ur_v2", ("burger", "m4heat"))
    a.wait(300)
    a.tap("#m4Burger", "選單")
    a.wait(800)
    a.tap('.m4item[data-v="heatmap"]', "選單：熱力圖", bias=(0.9, 0.5))
    a.until("() => !!document.querySelector('#indTree canvas')", 8000)
    a.wait(500)
    a.scroll(to_y=14, ms=300)   # 往下 14px：整張卡（含色階圖例）落在畫面框內
    a.wait(300)
    a.set_stage(3, "看圖")
    a.say("大小看成交，顏色看漲跌", "magnifier", ("indcard",))
    a.idle(1500)
    a.settle()
    a.set_stage(4, "篩選")
    a.say("分組、色階，一鍵篩選", "folder", ("indcard",))
    sr = strip_rect(pg, False)
    opts = [("chain", "產業鏈"), ("flat", "不分組")]
    a.strip_pick("#indTreeGroup", "flat", opts, sr, "分組：不分組")
    a.park(region=CROP["m"], ms=260)
    a.wait(800)
    a.strip_pick("#indTreeGroup", "chain", opts, sr, "分組：產業鏈")
    a.park(region=CROP["m"], ms=260)
    a.wait(500)
    for b in (5, 1):
        a.tap(f'#indHeat .hmcell[data-bin="{b}"]', f"色階：第 {b + 1} 級")
        a.wait(1000)
    a.tap('#indHeat .hmcell[data-bin="1"]', "色階：取消篩選")
    a.wait(700)
    a.settle()
    a.set_stage(5, "題材")
    a.say("想看題材？點題材", "face_curious", ("mtabs",))
    a.wait(300)
    pg.evaluate("() => document.body.classList.add('__nodg')")   # 題材頁預設會把某個題材的剖析圖放在地圖下方、被畫面框下緣切到字 → 點方塊前先藏起來（版面不動）
    a.tap('button[data-sub="heat-theme"]', "分頁：題材")
    a.until("() => !!document.querySelector('#themeMap canvas')", 8000)
    a.wait(800)
    a.set_stage(6, "剖析")
    a.say("點方塊，再點環節看細節", "spotlight", ("themecard", "dg"))
    a.wait(900)
    r = tm_rect(pg, "#themeMap", ["高階 PCB", "AI 伺服器"])
    a.tap_rect([r["x"], r["y"], r["w"], r["h"]], f"題材：{r['n']}", expect="#themeMap")
    pg.evaluate("() => document.body.classList.remove('__nodg')")
    a.wait(300)
    a.until("() => !!document.querySelector('#themeDiagram g.stn')", 8000)
    scroll_stable(a)
    a.wait(300)
    for k in range(3):   # 每次點「第一個還沒展開的環節」（展開後整張圖往下長，再點下一個）
        a.tap("#themeDiagram g.vstep:not(.open)", f"環節：第 {k + 2} 步")
        a.wait(1000)
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
    cfg = dict(site=str(SITE), overlays=OVERLAYS, els=ELS, roots=["body"], zcharts=ZCHARTS, blur_sel="#__none", extra_css=EXTRA_CSS, dry=g.dry, dev=DEV, crop0=CROP,
               init=["try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}"] if g.dev == "d" else [])
    V.run(g.dev, run_d if g.dev == "d" else run_m, g.out, cfg, g.port)


if __name__ == "__main__":
    main()
