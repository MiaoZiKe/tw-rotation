"""功能介紹影片 06 今日事件＋精選文章 v3 —— 一口氣錄完（單一鏡頭、不換頁、只允許一次單向推近）。

主線（一條因果線）：新聞太多 → 點鈴鐺開「今日事件」→ 切分類只看那一類 → 想深入看題材 → 點書本進「精選文章」
→ 點頁籤挑類別 → 搜關鍵字找到文章。訪客一篇全文都看不到（art.read.n＝0，且目前沒有任何一篇設為限時公開），所以只示範到清單、頁籤與搜尋。

錄法：vidlib3.py（逐格算圖、每格記錄所有文字外框／浮層外框，游標只落在不壓字的空白處）。
一律未登入訪客的真實畫面；錄的是 origin/main 的 site/（FEAT_SITE），資料用 `SKIP_INTRADAY=1 python -m pipeline.build_payload` 重算。
法遵：今日事件不點「券商」分類（券商目標價列模糊）；標題含上市櫃公司名稱或代號的模糊；個股連結模糊。會員額度字樣不入鏡。
用法：FEAT_SITE=<main worktree>/site python capture_ev.py --dev d|m
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vidlib3 as V  # noqa: E402

F, C = V.F, V.C
SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat06"))
SITE = Path(os.environ.get("FEAT_SITE", str(SCR / "main_wt" / "site")))
OVERLAYS = ['.ddpanel:not([hidden])', '.twms-pan', '#__vsel', '[role=dialog]', '.toast', '#howPop', '.qcov', '.qcard']
ELS = {"evbell": "#evToggle", "navart": '#tabs .tab[data-view="articles"]', "evcats": "#evFilters", "evlist": "#evList", "drawer": "#side.open",
       "artcats": "#artCats", "artq": "#artQ", "artflt": ".artflt", "artlist": "#artList", "burger": "#m4Burger",
       "m4ev": '.m4item[data-act="events"]', "m4art": '.m4item[data-v="articles"]'}
# 網頁錄影：每組文章只露第一排卡（取景下緣落在乾淨的空白處）、不開「全文需 Plus」字樣
EXTRA_CSS_D = "#side{width:740px!important;max-width:none!important}#artList .artgrid .artc:nth-child(n+4){display:none!important}body.__vnb #l4NavBtn{visibility:hidden!important}body.__vnb .topbar,body.__vnb .topbar *,body.__vnb #l4Head,body.__vnb #l4Head *{opacity:0!important;visibility:hidden!important;background:transparent!important}"
EXTRA_CSS_M = "#artList .artgrid .artc:nth-child(n+3){display:none!important}"
ZOOM_D = (72, 0, 928, 529)   # 單向推近的目標畫面框（css，視窗座標）：把左側圖示列推出畫面（頁面先往下捲 60px，卡片下緣落在框內）


def warm_articles(pg):
    """錄影開始前先開一次文章頁（索引進快取）再回總覽：錄影時鐘是逐格推進的，第一次載入會在畫面上停 3 秒「載入中…」。"""
    F.goto(pg, "#articles", 3500)
    pg.wait_for_function("() => document.querySelectorAll('#v-articles .artc').length > 3", timeout=15000)


def head_region(pg):
    r = pg.evaluate(C.RECT_JS, "#side .side-h")
    return (r[0] + 4, r[1] + 4, r[2] - 8, r[3] - 8)


def run_d(pg, a, start):
    warm_articles(pg)
    F.goto(pg, "#overview", 3500)
    pg.evaluate("() => scrollTo(0, 24)")   # 往下 24px：總覽圖表的 x 軸字落在畫面框內，下緣落在卡片間的空白
    pg.wait_for_timeout(400)
    a.crop = V.CROP0["d"]
    a.x, a.y = 600, 300
    a.park(region=(300, 300, 400, 280))
    start()
    # 1 需求
    a.set_stage(1, "需求")
    a.say("新聞多到看不完？", "face_sweat", ("evbell",))
    a.idle(1100)
    # 2 引導：點鈴鐺
    a.set_stage(2, "引導")
    a.say("點鈴鐺，開今日事件", "point_r_v2", ("evbell",))
    a.wait(300)
    a.fit = [["#evList .ev"], 568]   # 抽屜一出現清單就只留放得進畫面框的列（不在滑入時露出被切到的半截字）
    a.tap("#evToggle", "選單：事件（鈴鐺）")
    a.wait(150)
    a.park(ms=300, prefer=(a.x + 40, a.y + 40))   # 點完游標離開按鈕（往右下找空白）
    a.until("() => document.querySelectorAll('#evList .ev').length > 3", 8000)
    a.fit = [["#evList .ev"], 568]
    a.wait(500)
    a.park(region=head_region(pg))
    a.wait(300)
    # 3 分類：連點台股、科技、總經
    a.set_stage(3, "分類")
    a.say("選分類，只看那一類", "folder", ("evcats", "evlist"))
    for c in ("科技", "總經", "all"):
        a.tap(f'#evFilters button[data-c="{c}"]', f"分類：{c if c != 'all' else '全部'}")
        a.wait(250)
        a.park(region=head_region(pg))
        a.wait(800)
    a.settle()
    # 4 想深入看題材 → 點書本進精選文章
    a.set_stage(4, "題材")
    a.say("想深入看題材？", "face_curious", ("navart",))
    a.wait(300)
    a.tap('#tabs .tab[data-view="articles"]', "選單：精選文章（書本）")
    a.wait(150)
    a.park(ms=300, prefer=(a.x + 60, a.y + 60))
    a.until("() => document.querySelectorAll('#v-articles .artc').length > 3", 8000)
    a.fit = None
    a.crop = V.CROP0["d"]
    a.wait(300)
    # 5 頁籤：快訊、知識、產業鏈（單向推近，把左側圖示列推出畫面）
    a.set_stage(5, "頁籤")
    a.crop = ZOOM_D
    pg.evaluate("() => document.body.classList.add('__vnb')")   # 推近後左側圖示列已在畫面外，把展開鈕也藏掉（只在錄影時）
    a.say("點頁籤，挑文章類別", "magnifier", ("artcats", "artlist"))
    a.scroll(to_y=60, ms=600)
    a.fit = [["#artList .artc", "#artList .artsech"], 518]
    a.wait(900)
    a.park(region=ZOOM_D, prefer=(900, 120))
    for cat, lab in (("news", "快訊"), ("know", "知識"), ("intro", "產業鏈")):
        a.tap(f'#artCats>button[data-cat="{cat}"]', f"頁籤：比比{lab}")
        a.wait(250)
        a.park(region=ZOOM_D, prefer=(900, 100))
        a.wait(900)
    a.settle()
    # 6 搜尋
    a.set_stage(6, "搜尋")
    a.say("搜關鍵字，快速找到", "bulb", ("artq", "artlist"))
    a.tap("#artQ", "搜尋框")
    a.park(region=ZOOM_D, prefer=(900, 100), ms=300)   # 游標離開輸入框再打字（不蓋住打出來的字）
    a.type_text("#artQ", "散熱")
    a.wait(900)
    a.park(region=ZOOM_D, prefer=(900, 100))
    a.idle(900)
    a.settle()


def run_m(pg, a, start):
    warm_articles(pg)
    F.goto(pg, "#overview", 3500)
    a.crop = V.CROP0["m"]
    start()
    a.set_stage(1, "需求")
    a.say("新聞多到看不完？", "face_sweat", ("burger",))
    a.idle(1100)
    a.set_stage(2, "引導")
    a.say("點選單，開今日事件", "point_ur_v2", ("burger", "m4ev"))
    a.wait(300)
    a.tap("#m4Burger", "選單")
    a.wait(800)
    a.tap('.m4item[data-act="events"]', "選單：事件")
    a.until("() => document.querySelectorAll('#evList .ev').length > 3", 8000)
    a.fit = [["#evList .ev"], 852]
    a.wait(700)
    a.set_stage(3, "分類")
    a.say("選分類，只看那一類", "folder", ("evcats", "evlist"))
    for c in ("科技", "總經", "all"):
        a.tap(f'#evFilters button[data-c="{c}"]', f"分類：{c if c != 'all' else '全部'}")
        a.wait(1000)
    a.settle()
    a.set_stage(4, "題材")
    a.say("想深入看題材？", "face_curious", ("burger", "m4art"))
    a.wait(300)
    a.tap("#m4Burger", "選單")
    a.wait(800)
    a.tap('.m4item[data-v="articles"]', "選單：精選文章")
    a.until("() => document.querySelectorAll('#v-articles .artc').length > 3", 8000)
    a.fit = None
    a.wait(60)
    y = pg.evaluate("() => document.querySelector('#artCats').getBoundingClientRect().top + scrollY - 66")
    a.scroll(to_y=y, ms=700)
    a.fit = [["#artList .artc"], 760]
    a.set_stage(5, "頁籤")
    a.say("點頁籤，挑文章類別", "magnifier", ("artcats", "artlist"))
    for cat, lab in (("news", "快訊"), ("know", "知識"), ("intro", "產業鏈")):
        a.tap(f'#artCats>button[data-cat="{cat}"]', f"頁籤：比比{lab}")
        a.wait(1000)
    a.settle()
    a.set_stage(6, "搜尋")
    a.say("搜關鍵字，快速找到", "bulb", ("artq", "artlist"))
    a.tap("#artQ", "搜尋框")
    a.park(region=ZOOM_D, prefer=(900, 100), ms=300)   # 游標離開輸入框再打字（不蓋住打出來的字）
    a.type_text("#artQ", "散熱")
    a.wait(1200)
    a.settle()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8816)
    ap.add_argument("--dry", action="store_true")
    g = ap.parse_args()
    if g.dry:
        os.environ["FEAT_DRY"] = "1"
    cfg = dict(site=str(SITE), overlays=OVERLAYS, els=ELS, roots=["body"], blur_sel="#evList .ev > a, .artc .tt, .artbc, #v-articles h1, #v-articles h2",
               extra_css=EXTRA_CSS_D if g.dev == "d" else EXTRA_CSS_M, dry=g.dry,
               init=["try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}"] if g.dev == "d" else [])
    V.run(g.dev, run_d if g.dev == "d" else run_m, g.out, cfg, g.port)


if __name__ == "__main__":
    main()
