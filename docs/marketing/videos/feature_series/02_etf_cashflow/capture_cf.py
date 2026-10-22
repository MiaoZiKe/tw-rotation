"""功能介紹影片 02：ETF 現金流試算（月配試算表 → 複利試算表）素材錄製，Andy 2026-10-21 重作版。

主線（一口氣、單向往下走）：
  需求一句 → 左側選單點「ETF」→「現金流試算」→ 設目標（月領＋金額，直條跟著變）→ 看「要買幾張」結果
  → 篩月配、勾選／取消（直條跟著變）→ 切組合 A／B／C（圓餅、時鐘一起換）→ 切到複利試算表 → 切 1／3／5 年（表格同步）。
一律「未登入訪客」真實畫面；ECharts 提示框關掉；原生下拉不錄（不遮擋）；開著的面板那一拍不講圖。

用法（repo 根目錄，先 SKIP_INTRADAY=1 python -m pipeline.build_payload）：
    python docs/marketing/videos/feature_series/02_etf_cashflow/capture_cf.py --dev d|m
輸出（大檔，放 scratchpad）：<out>/<dev>_main.mp4 ＋ <out>/<dev>_main.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_etf"))
import fcore_cap as F  # noqa: E402
from fcore_cap import goto, tap_slice  # noqa: E402,F401

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/02"))
F.CFG.update(scr=SCR, vp_d={"width": 1680, "height": 900})
F.DEVS["d"] = dict(viewport={"width": 1680, "height": 900}, device_scale_factor=2)

SUBTAB = '#tabs .l4subtab[data-l4sub="etf-inc"]'
SIDE_JS = r"""(sel) => { const e = document.querySelector(sel); if (!e) return null;
  let p = e.parentElement; while (p && p !== document.body) { const cs = getComputedStyle(p); if (/(auto|scroll)/.test(cs.overflowY) && p.scrollHeight > p.clientHeight + 2) break; p = p.parentElement; }
  if (!p || p === document.body) return null; const r = e.getBoundingClientRect(), pr = p.getBoundingClientRect();
  const need = r.bottom + 24 - Math.min(pr.bottom, innerHeight); if (!p.id) p.id = '__vside'; return need > 0 ? ['#' + p.id, p.scrollTop + need] : null; }"""


# ------------------------------------------------------------------ 網頁版
def d_main(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("需求：總覽首頁")
    a.say("想每月都有現金流？", "face_think_v2")
    a.idle(1900)
    a.cam_view("側欄捲動")
    a.side_mid('#tabs .tab[data-view="etf"]', 0.42, 400)
    a.cam(['#tabs .tab[data-view="etf"]'], 6, "選單：ETF", minw=270)
    a.say("選單點「ETF」", "point_r_v2")
    a.idle(400)
    a.click('#tabs .tab[data-view="etf"]', label="選單：ETF")
    a.wait(1200)
    a.cam_view("側欄捲動")
    a.side_mid(SUBTAB, 0.42, 400)
    a.cam([SUBTAB], 4, "選單：現金流試算", minw=270)
    a.say("再點「現金流試算」", "magnifier")
    a.idle(300)
    a.click(SUBTAB, label="選單：現金流試算")
    a.wait(1500)
    pg.evaluate("() => scrollTo(0, 0)")
    # 設目標：月領＋金額（下方直條跟著變）
    a.step("set")
    a.cam(["#incMode", "#incAmtSeg"], 6, "目標列", also=["#incBar"])
    a.say("設目標：月領＋金額", "calc")
    a.idle(300)
    a.click('#incMode button[data-v="m"]', label="月領", keep=True)
    a.wait(800)
    a.click('#incAmtSeg button[data-v="10000"]', label="金額：1 萬", keep=True)
    a.wait(800)
    a.click('#incAmtSeg button[data-v="30000"]', label="金額：3 萬")
    a.wait(600)
    # 結果：要買幾張、每月入帳直條（頁面往下捲一小段，清單整張在客服鈕上方）
    a.cam_view("捲動")
    a.scroll(by=130, ms=500)
    sq = F.text_rect(pg, "#incSQ") or "#incSQ"
    a.cam([sq], 4, "要買幾張", also=["#incSQ", "#incChips", "#incBar"])
    a.say("直條＝每月入帳金額", "surprise_jump")
    a.idle(1500)
    # 勾選／取消（直條跟著變）
    a.step("pick")
    lb = pg.evaluate("() => { const r = document.querySelector('#incListBox').getBoundingClientRect(); return [r.left, r.top, r.width]; }")
    a.cam([f"rect:{lb[0]:.0f},{lb[1]:.0f},{lb[2]:.0f},300"], 4, "右側清單", also=["#incListBox", "#incBar"])
    a.say("取消、勾選，直條跟著變", "calendar")
    a.idle(300)
    a.click("#incList input[type=checkbox]:checked", label="取消一檔", keep=True)
    a.wait(800)
    a.click("#incList input[type=checkbox]:checked", label="再取消一檔", keep=True)
    a.wait(800)
    a.click("#incList input[type=checkbox]:not(:checked):not(:disabled)", label="勾選一檔")
    a.wait(700)
    # 組合 A／B／C（圓餅、時鐘一起換）
    a.step("combo")
    a.cam(['#incTabs button[data-i="0"]', '#incTabs button[data-i="1"]', '#incTabs button[data-i="2"]'], 6, "組合分頁")
    a.say("切組合，圓餅時鐘一起換", "happy_spin")
    a.idle(300)
    a.click('#incTabs button[data-i="0"]', label="組合 A", keep=True)
    a.wait(500)
    a.cam(['#incTabs button[data-i="0"]', '#incTabs button[data-i="1"]', '#incTabs button[data-i="2"]', "#incCdn", "#incClk"], 6, "組合：圓餅＋時鐘", settle=False)
    a.wait(500)
    a.click('#incTabs button[data-i="1"]', label="組合 B", keep=True)
    a.wait(800)
    a.click('#incTabs button[data-i="2"]', label="組合 C")
    a.wait(600)
    a.cam(["#incClk", "#incCTbl"], 6, "時鐘＋各檔明細")
    a.say("點時鐘某月，標出那檔", "clock")
    a.idle(300)
    F.tap_slice(a, "#incClk", 0, "時鐘第 1 格", keep=True)
    a.wait(800)
    F.tap_slice(a, "#incClk", 4, "時鐘第 5 格", keep=True)
    a.wait(800)
    F.tap_slice(a, "#incClk", 8, "時鐘第 9 格")
    a.wait(700)
    # 複利試算表：切 1／3／5 年
    a.step("cx")
    a.cam(["#incMain [role=tablist]"], 6, "分頁：複利試算表")
    a.say("再看「複利試算表」", "point_r_v2")
    a.idle(300)
    a.click('button[role=tab][data-v="x"]', label="分頁：複利試算表")
    a.wait(1300)
    a.cam(["#cxQuick", "#cxTbl"], 6, "年數與期末資產表", also=["#cxChart"])
    a.say("切 1、3、5 年，表跟著變", "face_thinking_bulb")
    a.idle(300)
    a.click("#cxQuick button:nth-child(1)", label="1 年", keep=True)
    a.wait(800)
    a.click("#cxQuick button:nth-child(2)", label="3 年", keep=True)
    a.wait(800)
    a.say("試算，不代表未來報酬", "face_wink")
    a.click("#cxQuick button:nth-child(3)", label="5 年")
    a.wait(600)
    a.settle()
    a.idle(300)


# ------------------------------------------------------------------ 手機版
def m_main(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("需求：總覽首頁")
    a.say("想每月都有現金流？", "face_think_v2")
    a.idle(1900)
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單", hold=300)
    a.wait(800)
    a.cam(["#m4Drawer"], 0, "選單抽屜", exact=2)
    a.say("再點「ETF」", "point_r_v2")
    a.idle(400)
    a.click('.m4item[data-v="etf"]', label="選單：ETF")
    a.wait(1400)
    a.cam(['.m4subtabs button[data-sub="etf-inc"]', '.m4subtabs button[data-sub="etf-list"]'], 8, "上方分頁")
    a.say("上方點「月配試算」", "magnifier")
    a.idle(300)
    a.click('.m4subtabs button[data-sub="etf-inc"]', label="分頁：月配試算")
    a.wait(1600)
    pg.evaluate("() => scrollTo(0, 0)")
    # 設定抽屜（面板開著只講面板，選完立刻關掉再看圖）
    a.step("set")
    a.cam(["#m4EtfSet-inc"], 8, "設定列")
    a.say("設目標：月領＋金額", "calc")
    a.idle(300)
    a.on_down = lambda: a.cam_view("面板開啟", settle=False)
    a.click("#m4EtfSet-inc", label="設定列", keep=True)
    a.cam(["#mSheet .msheetbody"], 0, "設定抽屜", exact=True, settle=False)
    a.away(150)
    a.wait(500)
    a.click('#mSheet button[data-g="mode"][data-v="m"]', label="目標：月領", keep=True)
    a.wait(700)
    a.click('#mSheet button[data-g="amt"][data-v="10000"]', label="金額：1 萬", keep=True)
    a.wait(700)
    a.click('#mSheet button[data-g="amt"][data-v="20000"]', label="金額：2 萬")
    a.wait(500)
    a.pg.keyboard.press("Escape")
    a.cam_view("面板收起")
    a.wait(700)
    # 看結果：要買幾張、每月入帳
    a.scroll_to_el("#incSQ", 150, 700)
    a.cam(["#incSQ"], 6, "要買幾張", also=["#incBar"])
    a.say("直條＝每月入帳金額", "surprise_jump")
    a.idle(1500)
    # 組合 A／B／C
    a.step("combo")
    a.cam_view("捲動")
    a.scroll(to_y=0, ms=600)
    a.cam(["#incTabs"], 4, "組合分頁")
    a.say("切組合，圓餅時鐘一起換", "happy_spin")
    a.idle(300)
    a.click('#incTabs button[data-i="0"]', label="組合 A", keep=True)
    a.wait(500)
    a.hscroll("#incTabs", by=140, ms=300)
    a.click('#incTabs button[data-i="1"]', label="組合 B", keep=True)
    a.wait(600)
    a.click('#incTabs button[data-i="2"]', label="組合 C")
    a.wait(500)
    a.cam_view("捲動")
    a.scroll_to_el("#incCdn", 130, 700)
    a.cam(["#incCdn"], 6, "圓餅")
    a.idle(1200)
    # 複利試算
    a.step("cx")
    a.cam_view("捲動")
    a.scroll(to_y=0, ms=600)
    a.cam(['.m4subtabs button[data-sub="etf-cx"]', '.m4subtabs button[data-sub="etf-inc"]'], 8, "上方分頁")
    a.say("再看「複利試算」", "point_r_v2")
    a.idle(300)
    a.click('.m4subtabs button[data-sub="etf-cx"]', label="分頁：複利試算")
    a.wait(1400)
    a.cam_view("捲動")
    a.scroll_to_el("#cxChart", 120, 700)
    a.cam(["#cxChart"], 6, "報酬曲線與圖例")
    a.say("點圖例，曲線與表跟著變", "face_thinking_bulb")
    a.idle(300)
    F.legend_click(a, "#cxChart", 3, "圖例：只領現金", keep=True)
    a.wait(700)
    F.legend_click(a, "#cxChart", 4, "圖例：只看價格", keep=True)
    a.wait(700)
    F.legend_click(a, "#cxChart", 1, "圖例：再投入 0050")
    a.wait(600)
    a.say("試算，不代表未來報酬", "face_wink")
    a.idle(300)
    a.settle()
    a.idle(500)


D_SHOTS = {"main": d_main}
M_SHOTS = {"main": m_main}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8801)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    F.run(g.dev, [s for s in g.shots.split(",") if s], out, g.port, D_SHOTS if g.dev == "d" else M_SHOTS, "#v-etf")


if __name__ == "__main__":
    main()
