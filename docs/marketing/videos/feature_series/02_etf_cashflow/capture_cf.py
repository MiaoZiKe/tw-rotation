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
F.CFG.update(scr=SCR, vp_d={"width": 1280, "height": 700}, init=[F.HIDE_FAB_JS])
F.DEVS["d"] = dict(viewport={"width": 1280, "height": 700}, device_scale_factor=2)

SUBTAB = '#tabs .l4subtab[data-l4sub="etf-inc"]'
SIDE_JS = r"""(sel) => { const e = document.querySelector(sel); if (!e) return null;
  let p = e.parentElement; while (p && p !== document.body) { const cs = getComputedStyle(p); if (/(auto|scroll)/.test(cs.overflowY) && p.scrollHeight > p.clientHeight + 2) break; p = p.parentElement; }
  if (!p || p === document.body) return null; const r = e.getBoundingClientRect(), pr = p.getBoundingClientRect();
  const need = r.bottom + 24 - Math.min(pr.bottom, innerHeight); if (!p.id) p.id = '__vside'; return need > 0 ? ['#' + p.id, p.scrollTop + need] : null; }"""


# ------------------------------------------------------------------ 網頁版（10-22 改版：視窗 1280×660，取景框固定尺寸；引導後框在功能卡上，只往下捲）
def d_main(pg, a, start):
    goto(pg, "#overview", 3500)
    # 預熱（錄影開始前）：先進一次現金流試算頁，頁面資料與圖表載入後回總覽，錄影時點進去才不會出現空白等待
    pg.evaluate("(h) => { location.hash = h; }", "#etf")
    pg.wait_for_timeout(1500)
    pg.evaluate("() => { const b = document.querySelector('[data-l4sub=etf-inc], .m4subtabs button[data-sub=etf-inc]'); if (b) b.click(); }")
    pg.wait_for_timeout(3500)
    goto(pg, "#overview", 3500)
    # 首頁走勢圖的十字線時間標籤（10:41）會壓到座標軸文字：開拍前把所有圖的提示收掉
    pg.evaluate("() => { document.querySelectorAll('div').forEach(el => { try { const c = echarts.getInstanceByDom(el); if (c) { c.dispatchAction({ type: 'updateAxisPointer', currTrigger: 'leave' }); c.dispatchAction({ type: 'hideTip' }); c.setOption({ tooltip: { show: false }, axisPointer: { show: false } }); } } catch (e) {} }); }")
    pg.mouse.move(600, 8)   # 真滑鼠移到頂欄空白處，圖上的十字線標籤才會消失
    pg.wait_for_timeout(600)
    start()
    a.cam_view("需求：總覽首頁")
    a.say("想每月都有現金流？", "face_think_v2")
    a.idle(1250)
    a.side_mid('#tabs .tab[data-view="etf"]', 0.42, 400)
    a.cam(['#tabs .tab[data-view="etf"]'], 6, "選單：ETF")
    a.say("選單點「ETF」", "point_r_v2")
    a.idle(400)
    a.click('#tabs .tab[data-view="etf"]', label="選單：ETF")
    a.wait(1200)
    a.side_mid(SUBTAB, 0.42, 400)
    a.cam([SUBTAB], 4, "選單：現金流試算")
    a.say("再點「現金流試算」", "magnifier")
    a.idle(300)
    a.on_up = lambda: a.cam(["#incMode", "#incAmtSeg"], 6, "功能卡：目標列", settle=False)   # 點下去那一格就把取景移到功能卡，不拍側欄窄框加空白
    a.click(SUBTAB, label="選單：現金流試算", keep=True)
    a.skip_ms(2200)   # 進場動畫不錄（頁面時鐘照走）
    a.away(150)
    a.wait(300)
    pg.evaluate("() => scrollTo(0, 0)")
    # 設目標：月領＋金額（整張功能卡第一個畫面：分頁、目標列、組合分頁、「要買幾張」結果一起出現）
    a.step("set")
    sq = F.text_rect(pg, "#incSQ") or "#incSQ"
    a.cam(["#incMode", "#incAmtSeg", "#incTabs", sq], 6, "目標列＋要買幾張", also=["#incMain [role=tablist]"])
    a.say("設目標：月領＋金額", "calc")
    a.idle(300)
    a.click('#incMode button[data-v="m"]', label="月領", keep=True)
    a.wait(800)
    a.click('#incAmtSeg button[data-v="10000"]', label="金額：1 萬", keep=True)
    a.wait(800)
    a.click('#incAmtSeg button[data-v="30000"]', label="金額：3 萬")
    a.wait(700)
    a.say("「要買幾張」跟著算出來", "surprise_jump")
    a.idle(1300)
    # 切組合 A／B／C（往下捲一點：組合分頁在上緣、圓餅與時鐘在下）
    a.step("combo")
    a.cam_view("捲動")
    a.scroll(by=130, ms=600)
    a.cam(['#incTabs button[data-i="0"]', '#incTabs button[data-i="1"]', '#incTabs button[data-i="2"]'], 6, "組合分頁")
    a.say("切組合，圓餅時鐘一起換", "happy_spin")
    a.idle(300)
    a.on_up = lambda: a.cam_view("捲動", settle=False)
    a.click('#incTabs button[data-i="0"]', label="組合 A", keep=True)
    a.skip_ms(1200)   # 圓餅／時鐘的進場動畫與版面長高不錄（頁面時鐘照走），避免畫面下半空白
    a.wait(300)
    a.scroll(to_y=181, ms=600)
    a.wait(900)
    a.cam(['#incTabs button[data-i="0"]', '#incTabs button[data-i="1"]', '#incTabs button[data-i="2"]', "#incCdn", "#incClk"], 0, "組合分頁＋圓餅＋時鐘", settle=False)
    a.wait(500)
    a.click('#incTabs button[data-i="1"]', label="組合 B", keep=True)
    a.wait(900)
    a.click('#incTabs button[data-i="2"]', label="組合 C")
    a.wait(700)
    a.say("點時鐘某月，標出那檔", "clock")
    a.idle(300)
    F.tap_slice(a, "#incClk", 0, "時鐘第 1 格", keep=True)
    a.wait(800)
    F.tap_slice(a, "#incClk", 4, "時鐘第 5 格", keep=True)
    a.wait(800)
    F.tap_slice(a, "#incClk", 8, "時鐘第 9 格")
    a.wait(700)
    # 回單檔 ETF：往下捲一次，直條與右側清單同屏；取消、勾選，直條跟著變
    a.step("pick")
    a.say("回單檔，取消勾選看直條", "calendar")
    a.cam_view("切回單檔")
    a.click('#incTabs button[data-v="s"]', label="單檔 ETF")
    a.wait(900)
    a.cam_view("捲動")
    a.scroll_to_el("#incBar", 141, 800)
    a.cam(["#incBar", "#incListBox > .ilhd"], 0, "直條＋右側清單", also=["#incListBox"])
    a.idle(500)
    a.click("#incList input[type=checkbox]:checked", label="取消一檔", keep=True)
    a.wait(800)
    a.click("#incList input[type=checkbox]:checked", label="再取消一檔", keep=True)
    a.wait(800)
    a.say("試算，不代表未來報酬", "face_wink")
    a.click("#incList input[type=checkbox]:not(:checked):not(:disabled)", label="勾選一檔")
    a.wait(900)
    a.settle()
    a.idle(200)


# ------------------------------------------------------------------ 手機版
def m_main(pg, a, start):
    goto(pg, "#overview", 3500)
    # 預熱（錄影開始前）：先進一次現金流試算頁，頁面資料與圖表載入後回總覽，錄影時點進去才不會出現空白等待
    pg.evaluate("(h) => { location.hash = h; }", "#etf")
    pg.wait_for_timeout(1500)
    pg.evaluate("() => { const b = document.querySelector('[data-l4sub=etf-inc], .m4subtabs button[data-sub=etf-inc]'); if (b) b.click(); }")
    pg.wait_for_timeout(3500)
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
    a.skip_ms(2200)
    a.wait(300)
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
