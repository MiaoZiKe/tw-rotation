"""功能介紹影片 01：ETF（配息行事曆 → 總覽類型與分類卡 → 報酬比較）素材錄製，Andy 2026-10-21 重作版。

主線（一口氣、單向往下走，不在分頁間來回跳）：
  需求一句 → 左側選單點「ETF」進配息行事曆 → 連點三個日期看當天清單、點一檔看歷年配息
  → 選單點「ETF 總覽」→ 連點三個類型分頁（下方卡片同步換）→ 看報酬率／殖利率前 5 的口徑
  → 捲到報酬比較：「加入比較」搜尋勾選兩檔 → 看走勢與年化 → 含息／不含息連切。
一律「未登入訪客」真實畫面；ECharts 提示框關掉；不放任何浮層蓋住介紹中的元素（取景讓它落在旁邊，或分兩拍）。

用法（repo 根目錄，先 SKIP_INTRADAY=1 python -m pipeline.build_payload）：
    python docs/marketing/videos/feature_series/01_etf/capture_etf.py --dev d      # 網頁版 1680×900 @2
    python docs/marketing/videos/feature_series/01_etf/capture_etf.py --dev m      # 手機版 390×844 @4
輸出（大檔，放 scratchpad）：<out>/<dev>_main.mp4 ＋ <out>/<dev>_main.json
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fcore_cap as F  # noqa: E402
from fcore_cap import goto, rel, scroll_to  # noqa: E402,F401

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/01"))
# ETF 一覽的分組預設全部收起 → 頁面太短、報酬比較卡捲不上來：錄影的瀏覽器預先把各分類的分組都展開（只動 localStorage，不改 site/）
_FOLD = "try{localStorage.setItem('tw.etf.fold',JSON.stringify({'配息型':[],'市值型':[],'主題型':[],'主動式':[],'債券型':[],'槓桿反向':[],'其他':[]}))}catch(e){}"
F.CFG.update(scr=SCR, vp_d={"width": 1280, "height": 600}, init=[_FOLD, F.HIDE_FAB_JS])
F.DEVS["d"] = dict(viewport={"width": 1280, "height": 600}, device_scale_factor=2)

def cal_cell(d):
    return f'#etfCalGrid .cald[data-d="{d}"]'


HAS_JS = "() => [...document.querySelectorAll('#etfCalGrid .cald.has')].map(c => c.dataset.d)"


SUB = {"配息行事曆": '#tabs .l4subtab[data-l4sub="etf-cal"]', "ETF 總覽": '#tabs .l4subtab[data-l4sub="etf-list"]', "現金流試算": '#tabs .l4subtab[data-l4sub="etf-inc"]'}


def sub(label):
    return SUB[label]


# ------------------------------------------------------------------ 網頁版（10-22 改版：視窗 1280×660，取景框固定尺寸；引導後框在功能卡上，只往下捲）
CELLS_JS = """() => [...document.querySelectorAll('#etfCalGrid .cald.has')].map(c => { const r = c.getBoundingClientRect(); return [c.dataset.d, r.top, r.bottom]; })"""


def d_main(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    # ① 需求（側欄＋總覽左半；比比泡泡講需求）
    a.cam_view("需求：總覽首頁")
    a.say("哪天除息？哪檔配得多？", "face_think_v2")
    a.idle(1250)
    # ② 引導：側欄點「ETF」
    a.side_mid('#tabs .tab[data-view="etf"]', 0.42, 400)
    a.cam(['#tabs .tab[data-view="etf"]'], 6, "選單：ETF")
    a.say("選單點「ETF」進專區", "point_r_v2")
    a.idle(500)
    a.click('#tabs .tab[data-view="etf"]', label="選單：ETF")
    a.wait(1500)
    pg.evaluate("() => scrollTo(0, 0)")
    # ③ 配息行事曆：連點三個日期、再點一檔
    a.step("cal")
    cells = [c for c in pg.evaluate(CELLS_JS) if c[1] > 70 and c[2] < 560]
    a.note(f"取景內有除息的日期：{cells}")
    ds = [c[0] for c in cells][-4:]
    d3 = ds[:3] if len(ds) >= 3 else ds
    a.cam([cal_cell(d) for d in d3] + ["#etfCalList .ph"], 8, "配息行事曆＋清單")
    a.say("格子＝當天除息的 ETF", "calendar")
    a.idle(500)
    a.say("點日期，右側列出清單", "point_r_v2")
    for i, d in enumerate(d3):
        a.click(cal_cell(d), label=f"日期：{d}", keep=(i < len(d3) - 1))
        a.wait(800 if i < len(d3) - 1 else 600)
    a.cam(["#etfCalList .ph", "#etfDayTbl thead", "all:#etfDayTbl tbody tr:nth-child(-n+4)"], 8, "當天清單")
    a.say("點一檔，看歷年配息", "magnifier")
    a.idle(300)
    a.click("#etfDayTbl tbody tr:nth-child(2)", label="清單：一檔 ETF", keep=True)
    a.cam(["#etfCalList .ph", "#etfCalList .kpis", "#etfCalList .mini"], 8, "單檔歷年配息", settle=False)
    a.away(150)
    a.idle(1800)
    # ④ 回側欄點「ETF 總覽」（取景平移到側欄再平移回功能卡，尺寸不變）
    a.side_mid(sub("ETF 總覽"), 0.42, 400)
    a.cam([sub("配息行事曆"), sub("ETF 總覽")], 4, "選單：ETF 總覽")
    a.say("想比同類？點「ETF 總覽」", "talk_explain_v2")
    a.idle(300)
    a.click(sub("ETF 總覽"), label="選單：ETF 總覽")
    a.wait(1600)
    pg.evaluate("() => scrollTo(0, 0)")
    a.step("types")
    a.cam(["#etfCatSeg", "#etfPopCard", "#etfRetTopCard", "#etfYldCard"], 4, "類型分頁＋三張卡")
    a.say("七類分頁，卡片跟著換", "point_ur_v2")
    a.idle(300)
    a.click('#etfCatSeg button[data-v="市值型"]', label="類型：市值型", keep=True)
    a.wait(700)
    a.click('#etfCatSeg button[data-v="主題型"]', label="類型：主題型", keep=True)
    a.wait(700)
    a.click('#etfCatSeg button[data-v="配息型"]', label="類型：配息型")
    a.wait(600)
    a.say("報酬率、殖利率同步換", "face_thinking_bulb")
    a.idle(400)
    # ⑤ 報酬比較：往下捲一次，走勢線切含息／不含息（走勢標題與線都會變）
    a.step("ret")
    a.cam_view("捲動")
    a.scroll_to_el("#etfRetCard", 62, 800)
    a.cam(["#etfBasisSeg", "#etfRetLineTtl", "#etfRetLine"], 8, "報酬比較走勢")
    a.say("走勢從 0% 一起比", "point_r_v2")
    a.idle(500)
    a.say("切含息／不含息看差距", "talk_explain_v2")
    a.click('#etfBasisSeg button[data-v="price"]', label="不含息")
    a.wait(600)
    a.click('#etfBasisSeg button[data-v="tr"]', label="含息")
    a.wait(800)
    a.say("一頁完成 ETF 功課", "proud_shine")
    a.click('#etfBasisSeg button[data-v="price"]', label="不含息")
    a.wait(700)
    a.settle()
    a.idle(300)


# ------------------------------------------------------------------ 手機版（390 寬 m4 版面，單一連續錄影）
M_SUB = {"cal": '.m4subtabs button[data-sub="etf-cal"]', "list": '.m4subtabs button[data-sub="etf-list"]'}


def m_main(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    # ① 需求
    a.cam_view("需求：總覽首頁")
    a.say("哪天除息？哪檔配得多？", "face_think_v2")
    a.idle(1900)
    # ② 引導：左上選單 → 「ETF」（點下去直接進配息行事曆）
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單", hold=300)
    a.wait(800)
    a.cam(["#m4Drawer"], 0, "選單抽屜", exact=2)
    a.say("再點「ETF」進專區", "point_r_v2")
    a.idle(400)
    a.click('.m4item[data-v="etf"]', label="選單：ETF")
    a.wait(1500)
    # ③ 配息行事曆：連點三個日期（捲到後兩週，日期格與下方清單標題同框）→ 點一檔看歷年配息
    a.step("cal")
    ds = pg.evaluate(HAS_JS)
    a.note(f"有除息的日期：{ds}")
    a.cam_view("捲動")
    a.scroll_to_el(cal_cell(ds[-4]).replace("#etfCalGrid ", "#etfCalGrid "), 120, 700)
    pick = [cal_cell(d) for d in ds[-4:]]
    a.cam(pick, 8, "配息行事曆（後兩週）", frame="rect:0,100,390,620", also=["#etfCalList .ph", "#etfDayTbl thead"])
    a.say("點日期，下方列出清單", "calendar")
    a.idle(300)
    a.click(pick[0], label=f"日期：{ds[-4]}", keep=True)
    a.wait(800)
    a.click(pick[1], label=f"日期：{ds[-3]}", keep=True)
    a.wait(800)
    a.click(pick[2], label=f"日期：{ds[-2]}")
    a.wait(600)
    a.cam_view("捲動")
    a.scroll_to_el("#etfCalList", 110, 800)
    a.note(f"清單標題上緣 {pg.evaluate('() => document.querySelector(\"#etfCalList .ph\").getBoundingClientRect().top')}｜scrollY {pg.evaluate('() => scrollY')}｜頁高 {pg.evaluate('() => document.documentElement.scrollHeight')}")
    a.cam(["#etfCalList .ph", "#etfDayTbl thead", "all:#etfDayTbl tbody tr:nth-child(-n+5)"], 6, "當天清單")
    a.say("點一檔，看歷年配息", "magnifier")
    a.idle(300)
    a.click("#etfDayTbl tbody tr:nth-child(2)", label="清單：一檔 ETF", keep=True)
    a.cam(["#etfCalList .ph", "#etfCalList .kpis", "#etfCalList .mini"], 6, "單檔歷年配息", also=["#etfCodeTbl"], settle=False)
    a.away(150)
    a.scroll_to_el("#etfCalList", 110, 500)
    a.idle(1800)
    # ④ ETF 總覽：上方分頁 → 三個類型分頁 → 三張卡
    a.cam_view("捲動")
    a.scroll(to_y=0, ms=700)
    a.cam([M_SUB["cal"], M_SUB["list"]], 8, "上方分頁")
    a.say("想比同類？點「ETF 總覽」", "talk_explain_v2")
    a.idle(300)
    a.click(M_SUB["list"], label="分頁：ETF 總覽")
    a.wait(1600)
    a.step("types")
    a.cam(["#etfCatBar", ".m4trisg", "#etfPopCard"], 6, "類型分頁與卡片")
    a.say("七類分頁，卡片跟著換", "point_ur_v2")
    a.idle(300)
    a.click('#etfCatSeg button[data-v="市值型"]', label="類型：市值型", keep=True)
    a.wait(700)
    a.click('#etfCatSeg button[data-v="主題型"]', label="類型：主題型", keep=True)
    a.wait(700)
    a.click('#etfCatSeg button[data-v="配息型"]', label="類型：配息型")
    a.wait(600)
    a.say("報酬、殖利率看口徑", "face_thinking_bulb")
    a.click('.m4trisg button[data-i="1"]', label="卡片：報酬率", keep=True)
    a.wait(900)
    a.click('.m4trisg button[data-i="2"]', label="卡片：殖利率")
    a.wait(900)
    # ⑤ 報酬比較
    a.step("ret")
    a.cam_view("捲動")
    a.scroll_to_el("#etfRetCard", 100, 800)
    a.cam(["#etfRetCard .row.spread", "#etfRetCtl"], 6, "加入比較")
    a.say("挑兩檔進報酬比較", "talk_explain_v2")
    DD = ["#etfCmpDD .ddbtn", "#etfCmpDD .ddpanel"]
    a.on_up = lambda: a.cam(DD, 0, "下拉清單（只框清單）", exact=True, settle=False)
    a.click("#etfCmpDD .ddbtn", label="加入比較")
    a.wait(500)
    a.click("#etfCmpDD .sndd-q", label="搜尋框")
    a.type_text("00939", 130)
    a.wait(400)
    a.click('#etfCmpDD .ddopt[data-n^="00939"] label', label="勾選第一檔")
    a.wait(500)
    a.pg.locator("#etfCmpDD .sndd-q").first.fill("")
    a.type_text("00940", 130)
    a.wait(400)
    a.click('#etfCmpDD .ddopt[data-n^="00940"] label', label="勾選第二檔")
    a.wait(500)
    a.on_up = lambda: a.cam_view("面板收起")
    a.click("#etfCmpDD .ddbtn", label="收起清單")
    a.wait(900)
    a.cam_view("捲動")
    a.scroll_to_el("#etfRetLine", 110, 700)
    a.cam(["#etfRetLineTtl", "#etfRetLine"], 6, "累積報酬走勢")
    a.say("走勢從 0% 一起比", "point_r_v2")
    a.idle(1500)
    a.cam_view("捲動")
    a.scroll_to_el("#etfRetBar", 110, 700)
    a.cam(["#etfRetBarTtl", "#etfRetBar"], 6, "年化報酬率")
    a.say("下圖並列年化報酬", "proud_shine")
    a.idle(1500)
    a.settle()
    a.idle(500)


D_SHOTS = {"main": d_main}
M_SHOTS = {"main": m_main}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8796)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    F.run(g.dev, [s for s in g.shots.split(",") if s], out, g.port, D_SHOTS if g.dev == "d" else M_SHOTS, "#v-etf")


if __name__ == "__main__":
    main()
