"""功能介紹影片 03：財經日曆（月曆＋分類篩選 → 點事件看分析）素材錄製，Andy 2026-10-21 重作版。

主線（一口氣、單向往下走）：
  需求一句 → 左側選單點「財經日曆」→ 點「FED 消息」分頁 → 連點三個事件（右側面板同步換成那項數據的說明）
  → 面板往下看「近期數值走勢」→ 再往下看「關注點與多空規則」。
一律「未登入訪客」真實畫面；ECharts 提示框關掉；個股名稱照舊模糊（本支主角是 FED 數據，不點公司）。

用法（repo 根目錄，先 SKIP_INTRADAY=1 python -m pipeline.build_payload）：
    python docs/marketing/videos/feature_series/03_fin_calendar/capture_cal.py --dev d|m
輸出（大檔，放 scratchpad）：<out>/<dev>_main.mp4 ＋ <out>/<dev>_main.json
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_etf"))
sys.path.insert(0, str(HERE))
import fcore_cap as F  # noqa: E402
from fcore_cap import goto  # noqa: E402,F401

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/03"))
F.CFG.update(scr=SCR, vp_d={"width": 1280, "height": 600}, init=[F.HIDE_FAB_JS])
F.DEVS["d"] = dict(viewport={"width": 1280, "height": 600}, device_scale_factor=2)


def chip(k):
    return f'#earnGrid .chip[data-k="{k}"]'


PANEL_Y = r"""([s, o]) => { const p = document.getElementById('earnPanel'), e = p && p.querySelector(s); if (!e) return null;
  return p.scrollTop + e.getBoundingClientRect().top - p.getBoundingClientRect().top - o; }"""


def panel_to(a, sel, off=6, ms=600):
    y = a.pg.evaluate(PANEL_Y, [sel, off])
    if y is None:
        a.note(f"面板找不到 {sel}")
        return False
    a.scroll(to_y=y, ms=ms, el="#earnPanel")
    return True


# ------------------------------------------------------------------ 網頁版（10-22 改版：視窗 1280×660，取景框固定尺寸；引導後框在功能卡上）
def d_main(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("需求：總覽首頁")
    a.say("重要數據哪天公布？", "face_think_v2")
    a.idle(1250)
    a.side_mid('#tabs .tab[data-view="earnings"]', 0.42, 400)
    a.cam(['#tabs .tab[data-view="earnings"]'], 6, "選單：財經日曆")
    a.say("選單點「財經日曆」", "point_r_v2")
    a.idle(400)
    a.click('#tabs .tab[data-view="earnings"]', label="選單：財經日曆")
    a.wait(1500)
    pg.evaluate("() => scrollTo(0, 0)")
    # 功能卡第一個畫面：三個分頁＋月曆＋右欄，一起出現
    a.step("tab")
    a.cam(['#earnFilt button[data-v="fed"]', '#earnFilt button[data-v="conf"]', "#earnPanel .ph"], 8, "功能卡：分頁＋月曆＋右欄")
    a.say("再點「FED 消息」分頁", "calendar")
    a.idle(300)
    a.click('#earnFilt button[data-v="fed"]', label="分頁：FED 消息")
    a.wait(900)
    a.step("evt")
    a.say("點事件，右側出現分析", "point_r_v2")
    a.idle(300)
    a.cam([chip("nfp"), chip("minutes"), chip("cpi"), "#earnPanel .ph"], 8, "月曆事件＋右欄分析", settle=False)
    a.click(chip("nfp"), label="事件：非農", keep=True)
    a.wait(800)
    a.click(chip("minutes"), label="事件：FOMC 紀要", keep=True)
    a.wait(800)
    a.click(chip("cpi"), label="事件：CPI")
    a.wait(500)
    a.say("是什麼、怎麼看、影響", "talk_explain_v2")
    a.cam(["#earnPanel .ph", "#earnPanel .fcard"], 8, "CPI 說明卡")
    a.idle(450)
    a.cam_view("面板捲動")
    panel_to(a, "[data-sec=spark]", 58, 600)
    a.say("近期數值走勢一看就懂", "magnifier")
    a.cam(["#earnPanel [data-sec=spark]"], 8, "近期數值走勢")
    a.idle(450)
    a.cam_view("面板捲動")
    panel_to(a, "[data-sec=rule]", 260, 600)
    a.say("關注點、多空規則寫好", "bulb")
    a.cam(["#earnPanel [data-sec=rule]"], 8, "關注點與多空規則")
    a.idle(450)
    a.step("more")
    a.say("公司財報、法說也在這", "news")
    a.cam(['#earnFilt button[data-v="rep"]', '#earnFilt button[data-v="conf"]', '#earnFilt button[data-v="fed"]'], 8, "公司財報、法說分頁")
    a.idle(300)
    a.click('#earnFilt button[data-v="rep"]', label="分頁：公司財報", keep=True)
    a.wait(600)
    a.say("財報、法說、FED 一頁掌握", "proud_shine")
    a.click('#earnFilt button[data-v="conf"]', label="分頁：公司法說")
    a.wait(500)
    a.settle()
    a.idle(300)


# ------------------------------------------------------------------ 手機版
def m_main(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("需求：總覽首頁")
    a.say("重要數據哪天公布？", "face_think_v2")
    a.idle(1900)
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單", hold=300)
    a.wait(800)
    a.cam_view("選單抽屜")   # 用整頁取景：點「財經日曆」換頁時取景框不必再變，不會切到新頁面的字
    a.say("再點「財經日曆」", "point_r_v2")
    a.idle(400)
    a.click('.m4item[data-v="earnings"]', label="選單：財經日曆")
    a.wait(1500)
    pg.evaluate("() => scrollTo(0, 0)")
    a.step("tab")
    a.cam(['#earnFilt button[data-v="fed"]'], 8, "分頁：FED 消息")
    a.say("再點「FED 消息」分頁", "calendar")
    a.idle(300)
    a.click('#earnFilt button[data-v="fed"]', label="分頁：FED 消息")
    a.wait(900)
    # 連點三個事件：日曆格與下方面板標題同框
    a.step("evt")
    a.cam_view("捲動")
    a.scroll(by=240, ms=600)
    a.cam([chip("nfp"), chip("minutes"), chip("cpi")], 8, "事件標籤＋下方面板", frame="rect:0,62,390,770", also=["#earnPanel .ph"])
    a.say("點事件，下方出現分析", "point_dr_v2")
    a.idle(300)
    a.click(chip("nfp"), label="事件：非農", keep=True)
    a.wait(800)
    a.click(chip("minutes"), label="事件：FOMC 紀要", keep=True)
    a.wait(800)
    a.click(chip("cpi"), label="事件：CPI")
    a.wait(800)
    # 面板：是什麼／怎麼看／影響 → 近期數值走勢 → 關注點與多空規則
    a.cam_view("捲動")
    a.scroll_to_el("#earnPanel", 90, 700)
    a.cam(["#earnPanel .ph", "#earnPanel .fcard"], 6, "CPI 說明卡")
    a.say("是什麼、怎麼看、影響", "talk_explain_v2")
    a.idle(1500)
    a.cam_view("面板捲動")
    panel_to(a, "[data-sec=spark]", 64, 600)
    a.cam(["#earnPanel [data-sec=spark]"], 6, "近期數值走勢")
    a.say("近期數值走勢一看就懂", "magnifier")
    a.idle(1500)
    a.cam_view("面板捲動")
    panel_to(a, "[data-sec=rule]", 200, 600)
    a.cam(["#earnPanel [data-sec=rule]"], 6, "關注點與多空規則")
    a.say("關注點、多空規則寫好", "bulb")
    a.idle(1500)
    a.step("more")
    a.cam_view("捲動")
    a.scroll(to_y=0, ms=600)
    a.cam(['#earnFilt'], 8, "分頁：公司財報、公司法說")
    a.say("公司財報、法說也在這", "news")
    a.idle(300)
    a.click('#earnFilt button[data-v="rep"]', label="分頁：公司財報", keep=True)
    a.wait(600)
    a.say("財報、法說、FED 一頁掌握", "proud_shine")
    a.click('#earnFilt button[data-v="conf"]', label="分頁：公司法說")
    a.wait(500)
    a.settle()
    a.idle(300)


D_SHOTS = {"main": d_main}
M_SHOTS = {"main": m_main}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8805)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    F.run(g.dev, [s for s in g.shots.split(",") if s], out, g.port, D_SHOTS if g.dev == "d" else M_SHOTS, "#v-earnings")


if __name__ == "__main__":
    main()
