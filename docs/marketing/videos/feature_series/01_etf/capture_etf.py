"""功能介紹影片 01：ETF（配息行事曆、總覽類型、總覽分類卡、報酬比較）素材錄製。

沿用 docs/marketing/video_1010/capture.py 的逐格算圖錄影器（page.clock 暫停、每格推進 1/30 秒再截圖，不掉格）、
假會員伺服器（Pro 範本：沒有額度條與升級卡）、錄影游標＋點擊漣漪（錄進畫面，點擊中心＝錄影當下量到的元素中心）。

本檔另外記錄：
- 每一格的「鏡頭」：目前要介紹的那一塊（選擇器聯集＋留白）在影片像素的外框 → 成片只裁這一塊放大（Andy 範本：只留介紹中的區塊）。
- 比比的台詞泡泡（一泡一句）：say() 記下出現秒數；下一句出現前，前一句至少停留 bubble_dur(字數) 秒（不夠就讓游標微動補足，不停格）。
- 點擊：capture.Act 量到的元素外框與點下座標（clicks）。

用法（repo 根目錄，先 SKIP_INTRADAY=1 python -m pipeline.build_payload）：
    python docs/marketing/videos/feature_series/01_etf/capture_etf.py --dev d     # 網頁版 1600×900 @2
    python docs/marketing/videos/feature_series/01_etf/capture_etf.py --dev m     # 手機版 390×844 @3
輸出（大檔，放 scratchpad）：<out>/<dev>_<鏡頭>.mp4 ＋ <out>/<dev>_meta.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "docs" / "marketing" / "video_1010"))
os.environ.setdefault("TW_CAP_TIER", "pro")
import capture as C  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat"))
FPS = 30
DEVS = {
    "d": dict(viewport={"width": 1600, "height": 900}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True),
}


def bubble_dur(text: str) -> float:
    """泡泡停留秒數：依字數，至少 1.6 秒（CEO 10-19）。"""
    n = len(text.replace(" ", ""))
    return max(1.8, 0.75 + 0.16 * n)


CAM_JS = r"""([sels, pad]) => {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
  for (const s of sels) { const e = document.querySelector(s); if (!e || !e.getClientRects().length) continue;
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); n++; }
  if (!n) return null;
  return [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad]; }"""


class Rec(C.Recorder):
    """逐格錄影＋每格記錄鏡頭外框（影片像素）。"""

    def __init__(self, pg, w, h, act):
        super().__init__(pg, w, h, dry=bool(os.environ.get("FEAT_DRY")))
        self.act = act
        self.cams: list = []

    def frame(self):
        super().frame()
        if not self.on:
            return
        a = self.act
        spec = a.cam_spec
        r = None
        if spec and spec[0] == "sel":
            try:
                r = self.pg.evaluate(CAM_JS, [spec[1], spec[2]])
            except Exception:  # noqa: BLE001
                r = None
        elif spec and spec[0] == "rect":
            r = spec[1]
        if r is None:
            r = [0, 0, a.vw, a.vh]
        self.cams.append([a.cam_id] + [round(v * a.dsf, 1) for v in r])


class A(C.Act):
    def __init__(self, pg, mob, vw, vh):
        super().__init__(pg, mob)
        self.vw, self.vh = vw, vh
        self.cam_spec = None
        self.cam_id = 0
        self.says: list = []
        self.marks: list = []
        self.say_t = None
        self.say_need = 0.0

    # 鏡頭：之後每一格都用這幾個元素的聯集（跟著捲動走）
    def cam(self, sels, pad=12, label=""):
        if isinstance(sels, str):
            sels = [sels]
        self.cam_spec = ("sel", list(sels), pad)
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label or ",".join(sels)])

    def cam_view(self, label="viewport"):
        self.cam_spec = None
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label])

    def idle(self, ms):
        """原地小幅移動游標（不停格），ms 毫秒。"""
        n = max(1, round(ms * FPS / 1000))
        x0, y0 = self.x, self.y
        for i in range(1, n + 1):
            k = i / n
            self._put(x0 + 10 * math.sin(k * math.pi * 2) * (1 - k * 0.3), y0 + 6 * math.sin(k * math.pi * 4))
            self.frame()
        self._put(x0, y0)

    def settle(self):
        """補足前一句泡泡的最短停留時間。"""
        if self.say_t is not None:
            rest = self.say_need - (self.t - self.say_t)
            if rest > 0.02:
                self.idle(rest * 1000)

    def say(self, text, act="talk_explain_v2"):
        self.settle()
        self.says.append({"t": round(self.t, 3), "text": text, "act": act})
        self.say_t, self.say_need = self.t, bubble_dur(text)

    def mark(self, name):
        self.marks.append([round(self.t, 3), "mark", name])

    def select(self, sel, value, label=""):
        """原生下拉在截圖裡畫不出彈出清單：游標移到下拉、漣漪、直接選值（畫面上的值與後續內容會跟著變）。"""
        b = self.box(sel)
        if not b:
            self.note(f"找不到 {sel}")
            return False
        x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        self.move(x, y, 550)
        self.wait(250)
        self.pg.evaluate("([x,y]) => window.__vcRipple && window.__vcRipple(x,y)", [x, y])
        self.record_target(x, y, "click", label or f"選 {value}", expect=sel)
        self.pg.locator(sel).first.select_option(value)
        self.frame()
        return True

    def type_text(self, text, ms_per=110):
        for ch in text:
            self.pg.keyboard.type(ch)
            self.wait(ms_per)


# ------------------------------------------------------------------ 網頁版鏡頭
def goto(pg, a, hash_, wait=3500):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(400)


def d_open(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1200)
    y = pg.evaluate("() => document.querySelector('#etfListCard').getBoundingClientRect().top + scrollY - 70")
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(600)
    start()
    a.cam(["#etfListCard"], 10, "ETF 一覽")
    a.say("台股 ETF 超過三百檔，資料分散各處", "face_think_v2")
    a.click("#etfOpenAll", label="全部展開")
    a.wait(500)
    a.cam_view("一覽捲動")
    a.move(1500, 600, 500)
    a.scroll(by=900, ms=2600)
    a.say("配息日、類型、績效，要比較得自己整理", "face_sweat")
    a.scroll(by=700, ms=2200)
    a.idle(500)
    a.scroll(to_y=0, ms=1400)
    a.cam(["#etfCatBar", "#etfTri", "#etfRetCard"], 8, "總覽全區")
    a.say("ETF 專區把這些整合在同一個頁面", "face_thinking_bulb")
    a.hover("#etfPopCard", 700)
    a.hover("#etfRetTopCard", 700)
    a.hover("#etfYldCard", 700)
    a.say("以下實際操作一次", "invite_nod")
    a.hover("#etfRetLine", 900, 0.7, 0.4)
    a.settle()
    # 收回「全部展開」，之後鏡頭的頁面高度一致
    pg.locator("#etfFoldAll").first.click()


def d_cal(pg, a, start):
    goto(pg, a, "#etf/cal", 4000)
    start()
    a.cam(["#etfCalCard"], 6, "配息行事曆")
    a.say("第一站：配息行事曆", "point_r_v2")
    a.hover('#etfCalGrid .cald.has', 800)
    a.say("格子標出當天除息的 ETF 與每單位配息", "talk_explain_v2")
    a.hover('#etfCalGrid .cald.has >> nth=1', 700)
    a.hover('#etfCalGrid .cald.today', 800)
    a.say("藍框代表今天", "face_nod_v2")
    a.idle(300)
    a.say("點有除息的日期，右側列出當天清單", "point_r_v2")
    a.click('#etfCalGrid .cald.has', label="點有除息的日期")
    a.wait(700)
    a.hover('#etfDayTbl tbody tr', 600)
    a.say("配息金額、當次殖利率、發放日一次看", "talk_explain_v2")
    a.hover('#etfDayTbl tbody tr >> nth=1', 600)
    a.hover('#etfDayTbl thead th >> nth=2', 700)
    a.cam(["#etfCalList"], 10, "右側清單")
    a.say("當次殖利率＝配息 ÷ 除息前一日收盤", "talk_explain_v2")
    a.hover('#etfDayTbl thead th >> nth=4', 900)
    a.say("填息天數：股價回到除息前收盤的交易日數", "magnifier")
    a.hover('#etfDayTbl tbody tr >> nth=0', 700, 0.85)
    a.cam(["#etfCalCard"], 6, "配息行事曆")
    a.say("切換月份，提前掌握除息時程", "calendar")
    a.click("#etfCalNext", label="下月")
    a.wait(900)
    a.hover('#etfCalGrid .cald.has', 600)
    a.click('#etfCalGrid .cald.has', label="點下個月有除息的日期")
    a.wait(600)
    a.say("想參與配息，須在除息日前一交易日持有", "face_think_v2")
    a.hover('#etfDayTbl tbody tr', 800)
    a.click("#etfCalToday", label="回本月")
    a.wait(600)
    a.settle()


def d_types(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    start()
    a.cam(["#etfCatBar", "#etfTri"], 8, "分類分頁＋三張卡")
    a.say("第二站：ETF 總覽，共分七類", "point_ur_v2")
    a.hover('#etfCatSeg button[data-v="配息型"]', 600)
    a.say("依代號、名稱與配息紀錄自動分類", "talk_explain_v2")
    for v in ("市值型", "主題型"):
        a.click(f'#etfCatSeg button[data-v="{v}"]', label=v)
        a.wait(700)
    a.say("分頁上的數字，就是每一類的檔數", "point_ur_v2")
    for v in ("主動式", "債券型"):
        a.click(f'#etfCatSeg button[data-v="{v}"]', label=v)
        a.wait(700)
    a.hover('#etfCatSeg button[data-v="債券型"] em', 700)
    a.say("切換分頁，下方卡片與圖表同步換類", "talk_explain_v2")
    a.click('#etfCatSeg button[data-v="主題型"]', label="主題型")
    a.wait(600)
    a.cam_view("整頁同步")
    a.scroll(by=420, ms=1500)
    a.say("同一類型互相比較，基準才一致", "face_nod_v2")
    a.idle(600)
    a.scroll(to_y=0, ms=1200)
    a.click('#etfCatSeg button[data-v="配息型"]', label="配息型")
    a.wait(500)
    a.settle()


def d_cards(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    start()
    a.cam(["#etfTri"], 8, "三張卡")
    a.say("上方三張卡，先看口徑再看數字", "talk_explain_v2")
    a.hover("#etfPopSub", 800)
    a.cam(["#etfPopCard"], 10, "最受歡迎")
    a.say("受益人：集保受益人數的週增加量", "point_r_v2")
    a.hover('#etfPop .rk >> nth=0', 700, 0.75)
    a.click('#etfPopSeg button[data-v="turnover"]', label="成交值")
    a.wait(500)
    a.say("成交值：近 20 個交易日平均成交金額", "talk_explain_v2")
    a.hover('#etfPop .rk >> nth=1', 700, 0.7)
    a.click('#etfPopSeg button[data-v="holders"]', label="受益人")
    a.wait(400)
    a.cam(["#etfRetTopCard"], 10, "報酬率前 5")
    a.say("報酬率前 5：依含息年化報酬排序", "point_r_v2")
    a.hover('#etfRetTop .rk >> nth=0', 700, 0.6)
    a.say("上市未滿期間的，改以上市以來計算", "talk_explain_v2")
    a.hover('#etfRetTop .rk >> nth=1', 700, 0.4)
    a.hover('#etfRetTopQ', 600)
    a.cam(["#etfYldCard"], 10, "殖利率前 5")
    a.say("殖利率＝近 12 個月現金配息 ÷ 最新收盤", "coins")
    a.hover('#etfYld .rk >> nth=0', 700, 0.7)
    a.say("平均填息天數，看配息是否被價差抵銷", "magnifier")
    a.hover('#etfYld .rk >> nth=1', 700, 0.9)
    a.hover('#etfYld .rk >> nth=2', 600, 0.9)
    a.say("以上皆為歷史資料，不代表未來表現", "face_nod_v2")
    a.idle(400)
    a.settle()


def d_ret(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    y = pg.evaluate("() => document.querySelector('#etfRetCard').getBoundingClientRect().top + scrollY - 64")
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(800)
    start()
    a.cam(["#etfRetCard .row.spread", "#etfRetBody .retcharts"], 8, "報酬比較")
    a.say("第三站：報酬比較", "point_r_v2")
    a.hover("#etfRetCard h3", 600)
    a.say("期間可選近 1、3、5、10 年或上市以來", "talk_explain_v2")
    a.select("#etfRng select", "1y", "期間：近 1 年")
    a.wait(900)
    a.select("#etfRng select", "10y", "期間：近 10 年")
    a.wait(900)
    a.select("#etfRng select", "3y", "期間：近 3 年")
    a.wait(700)
    a.say("起訖日期同步顯示，也能直接改日期", "point_ur_v2")
    # 點起始日期的「年」欄位，按方向鍵往前一年（真的改日期 → 期間自動變成「起始日期～至今」）
    b = a.box("#etfRng .rpfrom")
    if b:
        a.click_xy(b["x"] + 22, b["y"] + b["height"] / 2, 500, 250, expect="#etfRng .rpfrom")
        a.wait(300)
        pg.keyboard.press("ArrowDown")
        a.wait(900)
        a.mark("改起始日期")
    a.cam(["#etfRetCtl", "#etfCmpDD .ddpanel"], 14, "加入比較")
    a.say("打開「加入比較」，輸入代號或名稱搜尋", "point_r_v2")
    a.click("#etfCmpDD .ddbtn", label="加入比較")
    a.wait(500)
    a.click("#etfCmpDD .sndd-q", label="搜尋框")
    a.type_text("高股息", 160)
    a.wait(500)
    a.say("勾選加入，取消勾選就從圖表移除", "talk_explain_v2")
    a.click("#etfCmpDD .ddlist label:has(input:not(:checked))", label="勾選一檔")
    a.wait(500)
    a.click("#etfCmpDD .ddlist label:has(input:not(:checked))", label="再勾一檔")
    a.wait(500)
    a.click("#etfCmpDD .ddlist label:has(input:checked)", label="取消勾選")
    a.wait(600)
    a.click("#etfCmpDD .ddbtn", label="收起清單")
    a.wait(500)
    a.cam(["#etfRetBody .retcharts > div:first-child"], 10, "累積報酬走勢")
    a.say("左圖：累積報酬走勢，期初皆為 0%", "point_r_v2")
    a.hover("#etfRetLine", 500, 0.35, 0.55)
    a.move(*_rel(a, "#etfRetLine", 0.85, 0.5), 1600)
    nxt = pg.evaluate(LEGEND_NEXT_JS, "#etfRetLine")
    a.say("圖例較多時，可以翻頁查看", "face_nod_v2")
    if nxt:
        a.click_xy(nxt[0], nxt[1], 600, 300)
        a.wait(800)
        a.click_xy(nxt[0], nxt[1], 300, 200)
        a.wait(600)
    a.cam(["#etfRetBody .retcharts > div:last-child"], 10, "年化報酬率")
    a.say("右圖：並列每一檔的年化報酬率", "point_r_v2")
    a.hover("#etfRetBar", 700, 0.45, 0.3)
    a.move(*_rel(a, "#etfRetBar", 0.45, 0.75), 1000)
    a.cam(["#etfRetCtl", "#etfRetBody .retcharts"], 8, "含息切換")
    a.say("切換含息／不含息，看報酬多少來自配息", "talk_explain_v2")
    a.click('#etfBasisSeg button[data-v="price"]', label="不含息")
    a.wait(1300)
    a.click('#etfBasisSeg button[data-v="tr"]', label="含息")
    a.wait(800)
    a.say("兩者差距越大，報酬越依賴配息", "face_thinking_bulb")
    a.hover("#etfRetBar", 800, 0.5, 0.2)
    a.cam(["#etfRetTbl"], 12, "明細表")
    a.scroll_to_el("#etfRetTbl", 300, 1100)
    a.say("明細表列出計算期間、年化與殖利率", "point_dr_v2")
    a.hover("#etfRetTbl tbody tr >> nth=0", 700, 0.4)
    a.hover("#etfRetTbl tbody tr >> nth=1", 600, 0.4)
    a.say("上市未滿期間的，從上市日起算並標年數", "talk_explain_v2")
    a.hover("#etfRetTbl tbody tr >> nth=0", 700, 0.36)
    a.idle(400)
    a.settle()


def d_end(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    start()
    a.cam(["#etfCatBar", "#etfTri", "#etfRetCard"], 8, "總覽全區")
    a.say("除息時程、分類比較、報酬回測，一頁完成", "proud_shine")
    a.move(800, 300, 900)
    a.move(1200, 600, 900)
    a.say("想親自操作，搜尋「哩股哩股」", "invite_nod")
    a.move(900, 450, 900)
    a.idle(600)
    a.settle()


LEGEND_NEXT_JS = r"""(sel) => { const host = document.querySelector(sel); if (!host || !window.echarts) return null;
  const ch = echarts.getInstanceByDom(host); if (!ch) return null;
  try { const lm = ch.getModel().getComponent('legend'); const v = ch.getViewOfComponentModel(lm);
    const g = v._controllerGroup; if (!g) return null; const nx = g.childOfName('pageNext'); if (!nx || nx.invisible) return null;
    const br = nx.getBoundingRect(); const m = nx.getComputedTransform ? nx.getComputedTransform() : nx.transform;
    let cx = br.x + br.width / 2, cy = br.y + br.height / 2;
    if (m) { const x = m[0] * cx + m[2] * cy + m[4], y = m[1] * cx + m[3] * cy + m[5]; cx = x; cy = y; }
    const hr = host.getBoundingClientRect(); return [hr.left + cx, hr.top + cy]; } catch (e) { return null; } }"""


def _rel(a, sel, fx, fy):
    b = a.pg.locator(sel).first.bounding_box()
    return b["x"] + b["width"] * fx, b["y"] + b["height"] * fy


# ------------------------------------------------------------------ 手機版鏡頭（390 寬 m4 版面）
def m_scroll_to(pg, sel, off=70):
    y = pg.evaluate("([s,o]) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top + scrollY - o : 0; }", [sel, off])
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(500)


def m_open(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1200)
    m_scroll_to(pg, "#etfListCard", 60)
    start()
    a.cam(["#etfListCard"], 6, "ETF 一覽")
    a.say("台股 ETF 超過三百檔，資料分散各處", "face_think_v2")
    a.click("#etfListCard summary, #etfListCard .grp > button, #etfListCard [data-g]", label="展開分組")
    a.wait(600)
    a.cam_view("一覽捲動")
    a.scroll(by=700, ms=2400)
    a.say("配息日、類型、績效，要比較得自己整理", "face_sweat")
    a.scroll(by=600, ms=2000)
    a.idle(400)
    a.scroll(to_y=0, ms=1400)
    a.cam(["#etfSub", "#etfCatBar", "#etfTri"], 6, "總覽上半")
    a.say("ETF 專區把這些整合在同一個頁面", "face_thinking_bulb")
    a.hover("#etfPopCard", 700)
    a.say("以下實際操作一次", "invite_nod")
    a.idle(600)
    a.settle()


def m_cal(pg, a, start):
    goto(pg, a, "#etf/cal", 4000)
    start()
    a.cam(["#etfSub", "#etfCalCard .calhd", "#etfCalGrid"], 6, "配息行事曆")
    a.say("第一站：配息行事曆", "point_r_v2")
    a.hover('#etfCalGrid .cald.has', 700)
    a.say("格子標出當天除息的 ETF 與每單位配息", "talk_explain_v2")
    a.hover('#etfCalGrid .cald.today', 800)
    a.say("藍框代表今天", "face_nod_v2")
    a.idle(300)
    a.say("點有除息的日期，下方列出當天清單", "point_dr_v2")
    a.click('#etfCalGrid .cald.has', label="點有除息的日期")
    a.wait(600)
    a.cam(["#etfCalList"], 6, "當天清單")
    a.scroll_to_el("#etfCalList", 80, 1000)
    a.say("配息金額、當次殖利率、發放日一次看", "talk_explain_v2")
    a.hover('#etfDayTbl tbody tr', 700)
    a.say("當次殖利率＝配息 ÷ 除息前一日收盤", "talk_explain_v2")
    a.hover('#etfDayTbl thead th >> nth=2', 900)
    a.say("填息天數：股價回到除息前收盤的交易日數", "magnifier")
    a.hover('#etfDayTbl thead th >> nth=4', 900)
    a.scroll(to_y=0, ms=1000)
    a.cam(["#etfSub", "#etfCalCard .calhd", "#etfCalGrid"], 6, "配息行事曆")
    a.say("切換月份，提前掌握除息時程", "calendar")
    a.click("#etfCalNext", label="下月")
    a.wait(900)
    a.hover('#etfCalGrid .cald.has', 600)
    a.say("想參與配息，須在除息日前一交易日持有", "face_think_v2")
    a.idle(500)
    a.click("#etfCalToday", label="回本月")
    a.wait(600)
    a.settle()


def m_types(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    start()
    a.cam(["#etfSub", "#etfCatBar", "#etfTri"], 6, "分類分頁")
    a.say("第二站：ETF 總覽，共分七類", "point_ur_v2")
    a.say("依代號、名稱與配息紀錄自動分類", "talk_explain_v2")
    a.click('#etfCatSeg button[data-v="市值型"]', label="市值型")
    a.wait(700)
    a.click('#etfCatSeg button[data-v="主題型"]', label="主題型")
    a.wait(600)
    a.say("分頁上的數字，就是每一類的檔數", "point_ur_v2")
    a.click('#etfCatSeg button[data-v="主動式"]', label="主動式")
    a.wait(700)
    pg.evaluate("() => { const s = document.querySelector('#etfCatSeg'); if (s) s.scrollLeft = 0; }")
    a.say("切換分頁，下方卡片與圖表同步換類", "talk_explain_v2")
    a.click('#etfCatSeg button[data-v="主題型"]', label="主題型")
    a.wait(600)
    a.cam_view("整頁同步")
    a.scroll(by=500, ms=1600)
    a.say("同一類型互相比較，基準才一致", "face_nod_v2")
    a.idle(500)
    a.scroll(to_y=0, ms=1200)
    a.click('#etfCatSeg button[data-v="配息型"]', label="配息型")
    a.wait(500)
    a.settle()


def m_cards(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    start()
    a.cam(["#etfCatBar", "#etfTri"], 6, "三張卡")
    a.say("三張排行卡，先看口徑再看數字", "talk_explain_v2")
    a.hover("#etfPopSub", 800)
    a.say("受益人：集保受益人數的週增加量", "point_r_v2")
    a.hover('#etfPop .rk >> nth=0', 700, 0.75)
    a.click('#etfPopSeg button[data-v="turnover"]', label="成交值")
    a.wait(500)
    a.say("成交值：近 20 個交易日平均成交金額", "talk_explain_v2")
    a.idle(500)
    a.click('#etfPopSeg button[data-v="holders"]', label="受益人")
    a.wait(400)
    a.say("報酬率前 5：依含息年化報酬排序", "point_r_v2")
    a.click(M_TRI_TAB.format(2), label="報酬率")
    a.wait(600)
    a.say("上市未滿期間的，改以上市以來計算", "talk_explain_v2")
    a.hover('#etfRetTop .rk >> nth=0', 700, 0.5)
    a.say("殖利率＝近 12 個月現金配息 ÷ 最新收盤", "coins")
    a.click(M_TRI_TAB.format(3), label="殖利率")
    a.wait(600)
    a.say("平均填息天數，看配息是否被價差抵銷", "magnifier")
    a.hover('#etfYld .rk >> nth=0', 700, 0.85)
    a.say("以上皆為歷史資料，不代表未來表現", "face_nod_v2")
    a.idle(400)
    a.click(M_TRI_TAB.format(1), label="最受歡迎")
    a.wait(400)
    a.settle()


M_TRI_TAB = "#etfTriSeg button:nth-child({})"


def m_ret(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    m_scroll_to(pg, "#etfRetCard", 60)
    start()
    a.cam(["#etfRetCard"], 6, "報酬比較")
    a.say("第三站：報酬比較", "point_r_v2")
    a.say("期間可選近 1、3、5、10 年或上市以來", "talk_explain_v2")
    a.mark("期間（手機在篩選列）")
    a.settle()


def run(dev, shots, out, port):
    cfg = DEVS[dev]
    W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
    H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(C.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    metaf = out / f"{dev}_meta.json"
    meta = json.loads(metaf.read_text(encoding="utf-8")) if metaf.exists() else {}
    site_meta = json.loads((C.SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    import datetime as _dt
    from playwright.sync_api import sync_playwright
    reg = D_SHOTS if dev == "d" else M_SHOTS
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--disable-gpu", "--enable-unsafe-swiftshader"])
            for sid in shots or list(reg):
                ctx = b.new_context(**cfg, locale="zh-TW", timezone_id="Asia/Taipei")
                ctx.clock.install(time=_dt.datetime.now(tz=_dt.timezone.utc))
                ctx.add_init_script(C.PRESET)
                C.fake_api(ctx)
                ctx.add_init_script(C.HIDE_TIER_JS)
                ctx.add_init_script(C.NOFAB_JS)
                ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
                a.x, a.y = (4, 450) if dev == "d" else (380, 600)
                a.dsf = cfg["device_scale_factor"]
                rec = Rec(pg, W, H, a)
                state = {}

                def start(rec=rec, a=a, sid=sid, state=state):
                    a.rec = rec
                    a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")
                    state["on"] = 1

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.wait(300)
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    r.update(size=[W, H], dsf=a.dsf, says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    meta[sid] = r
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", r.get("bad")[:3], "errs:", errs[:2])
                except Exception as exc:  # noqa: BLE001
                    rec.on = False
                    print(sid, "失敗", exc)
                    meta[sid] = {"ok": False, "why": str(exc)[:300], "steps": a.log}
                    shutil.rmtree(out / f".tmp_{dev}_{sid}", ignore_errors=True)
                metaf.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
                ctx.close()
            b.close()
    finally:
        srv.shutdown()


D_SHOTS = {"open": d_open, "cal": d_cal, "types": d_types, "cards": d_cards, "ret": d_ret, "end": d_end}
M_SHOTS = {"open": m_open, "cal": m_cal, "types": m_types, "cards": m_cards, "ret": m_ret}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--out", default=str(SCR / "raw"))
    ap.add_argument("--port", type=int, default=8796)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
