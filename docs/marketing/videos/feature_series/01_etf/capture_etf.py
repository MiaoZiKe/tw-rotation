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
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=4, is_mobile=True, has_touch=True),
}


def bubble_dur(text: str) -> float:
    """泡泡停留秒數：依字數，至少 1.6 秒（CEO 10-19）。"""
    n = len(text.replace(" ", ""))
    return max(1.6, 0.6 + 0.145 * n)


CAM_JS = r"""([sels, pad]) => {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
  const pick = (s) => { if (!s.startsWith('txt:')) return document.querySelector(s);
    const [css, txt] = s.slice(4).split('|'); return [...document.querySelectorAll(css)].find((x) => x.getClientRects().length && (x.innerText || '').trim() === txt) || null; };
  for (const s of sels) { const e = pick(s); if (!e || !e.getClientRects().length) continue;
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
        self.settle()   # 前一句泡泡講完（最短停留）才換鏡頭，畫面與泡泡同步
        if isinstance(sels, str):
            sels = [sels]
        self.cam_spec = ("sel", list(sels), pad)
        self.cam_id += 1
        self.marks.append([round(self.t, 3), "cam", label or ",".join(sels)])

    def cam_view(self, label="viewport"):
        self.settle()
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
    pg.locator("#etfOpenAll").first.click()
    pg.wait_for_timeout(800)
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(600)
    start()
    a.cam_view("一覽捲動")
    a.move(1500, 600, 600)
    a.say("存 ETF 最常問：哪天除息、配多少？", "face_think_v2")
    a.scroll(by=350, ms=1800)
    a.scroll(by=450, ms=2400)
    a.say("同一類有哪些？含息報酬差多少？", "tilt")
    a.scroll(by=450, ms=2400)
    a.say("ETF 超過三百檔，資料又分散各處", "face_sweat")
    a.scroll(by=350, ms=2000)
    a.idle(400)
    a.say("這支帶你一步步用 ETF 專區解決", "invite_nod")
    a.scroll(to_y=0, ms=1600)
    a.idle(500)
    a.settle()


def d_guide(pg, a, start):
    """引導：從首頁總覽，點左側選單「ETF」→ 子選單「配息行事曆」。左側導覽展開（不收成圖示列）。"""
    goto(pg, a, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("先從首頁開始，看左側選單", "point_r_v2")
    a.move(120, 300, 900)
    a.idle(400)
    a.cam(['#tabs .tab[data-view="etf"]', '#tabs .tab[data-view="industry"]'], 16, "選單：族群與個股")
    a.say("在「族群與個股」找到「ETF」", "point_r_v2")
    a.hover('#tabs .tab[data-view="industry"]', 700)
    a.click('#tabs .tab[data-view="etf"]', label="選單：ETF")
    a.wait(1600)
    a.cam(['#tabs .tab[data-view="etf"]', 'txt:#tabs .l4subtab|現金流試算'], 16, "ETF 子選單")
    a.say("子選單：配息行事曆、ETF 總覽、試算", "talk_explain_v2")
    a.hover('#tabs .l4subtab:has-text("配息行事曆")', 600)
    a.hover('#tabs .l4subtab:has-text("ETF 總覽")', 600)
    a.say("先點「配息行事曆」", "point_r_v2")
    a.click('#tabs .l4subtab:has-text("配息行事曆")', label="子選單：配息行事曆")
    a.wait(1400)
    a.cam(["#etfCalCard"], 8, "進到配息行事曆")
    a.idle(700)
    a.settle()


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
    a.cam(["#etfCalList .ph", "#etfDayTbl thead", "#etfDayTbl tbody tr:nth-child(6)"], 10, "右側清單上半")
    a.say("當次殖利率＝配息 ÷ 除息前一日收盤", "talk_explain_v2")
    a.hover('#etfDayTbl thead th >> nth=4', 900)
    a.say("填息天數：股價回到除息前收盤的交易日數", "magnifier")
    a.hover('#etfDayTbl tbody tr >> nth=0', 700, 0.85)
    a.cam(["#etfCalCard"], 6, "配息行事曆")
    a.say("切換月份，查看各月的除息時程", "calendar")
    a.click("#etfCalPrev", label="上月")
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
    a.hover("#etfPopCard h3", 700, 0.3)
    a.hover("#etfRetTopCard h3", 600, 0.3)
    a.hover("#etfYldCard h3", 600, 0.3)
    a.cam(["#etfPopCard"], 10, "最受歡迎")
    a.hover("#etfPopSub", 600, 0.4)
    a.say("受益人：集保受益人數的週增加量", "point_r_v2")
    a.idle(500)
    a.click('#etfPopSeg button[data-v="turnover"]', label="成交值")
    a.wait(500)
    a.say("成交值：近 20 個交易日平均成交金額", "talk_explain_v2")
    a.hover("#etfPopSub", 700, 0.6)
    a.click('#etfPopSeg button[data-v="holders"]', label="受益人")
    a.wait(400)
    a.cam(["#etfRetTopCard"], 10, "報酬率前 5")
    a.hover("#etfRetTopQ", 600, 0.3)
    a.say("報酬率前 5：依含息年化報酬排序", "point_r_v2")
    a.hover("#etfRetTopSub", 700)
    a.say("上市未滿期間的，改以上市以來計算", "talk_explain_v2")
    a.hover("#etfRetTopQ", 600, 0.8)
    a.cam(["#etfYldCard"], 10, "殖利率前 5")
    a.hover("#etfYldQ", 600, 0.4)
    a.say("殖利率＝近 12 個月現金配息 ÷ 最新收盤", "coins")
    a.idle(500)
    a.say("平均填息天數，看配息是否被價差抵銷", "magnifier")
    a.idle(600)
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
        a.click_xy(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, 500, 250, expect="#etfRng .rpfrom")
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


def m_sheet(a, g, v, label=""):
    """手機：點「ETF 總覽設定」摘要鈕 → 抽屜裡點選項 → 抽屜還開著就點上方空白收起。"""
    a.click("#m4EtfSet-list", label="ETF 總覽設定")
    a.wait(650)
    a.click(f'#mSheet button[data-g="{g}"][data-v="{v}"]', label=label or v)
    a.wait(600)
    if a.pg.evaluate("() => { const s = document.getElementById('mSheet'); return !!s && s.getClientRects().length > 0 && s.getBoundingClientRect().top < innerHeight - 40; }"):
        pt = a.pg.evaluate(SAFE_BACK_JS)
        if pt:
            a.click_xy(pt[0], pt[1], 400, 200)
        else:
            a.pg.keyboard.press("Escape")
        a.wait(600)


SAFE_BACK_JS = r"""() => { const bk = document.querySelector('.msheetback'), sh = document.getElementById('mSheet'); if (!bk || !sh) return null;
  const top = sh.getBoundingClientRect().top; const pe = bk.style.pointerEvents; bk.style.pointerEvents = 'none'; let best = null;
  for (let y = 120; y < top - 24; y += 12) for (let x = 40; x < innerWidth - 40; x += 12) {
    const e = document.elementFromPoint(x, y); if (!e) continue;
    if (e.closest('button,a,input,select,label,summary,[role=button],[role=tab],.cald,.rk,canvas,[_echarts_instance_],header,.m4top,.topbar')) continue;
    const d = Math.abs(y - (120 + top) / 2) + Math.abs(x - innerWidth / 2) * 0.3; if (!best || d < best[2]) best = [x, y, d]; }
  bk.style.pointerEvents = pe; return best ? [best[0], best[1]] : null; }"""


def m_open(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1200)
    pg.locator("#etfListCard .fqhd.fqc-m").first.click()
    pg.locator("#etfListCard .fqhd.fqc-q").first.click()
    pg.wait_for_timeout(800)
    m_scroll_to(pg, "#etfListCard", 70)
    start()
    a.cam_view("一覽捲動")
    a.say("存 ETF 最常問：哪天除息、配多少？", "face_think_v2")
    a.scroll(by=280, ms=1600)
    a.scroll(by=380, ms=2200)
    a.say("同一類有哪些？含息報酬差多少？", "tilt")
    a.scroll(by=380, ms=2200)
    a.say("ETF 超過三百檔，資料又分散各處", "face_sweat")
    a.scroll(by=260, ms=1800)
    a.idle(400)
    a.say("這支帶你一步步用 ETF 專區解決", "invite_nod")
    a.scroll(to_y=0, ms=1500)
    a.idle(500)
    a.settle()


def m_guide(pg, a, start):
    """引導（手機）：首頁總覽 → 左上角選單 → 「ETF」→ 上方分頁。"""
    goto(pg, a, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("先從首頁開始，點左上角選單", "point_ur_v2")
    a.idle(400)
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-v="overview"]', '.m4item[data-v="etf"]'], 10, "選單抽屜")
    a.say("在「族群與個股」點「ETF」", "point_r_v2")
    a.hover('.m4item[data-v="etf"]', 700)
    a.click('.m4item[data-v="etf"]', label="選單：ETF")
    a.wait(1800)
    a.cam([".m4subtabs", "#etfCalCard .calhd"], 6, "ETF 上方分頁")
    a.say("上方分頁：行事曆、總覽與試算", "talk_explain_v2")
    a.hover(".m4subtabs button >> nth=1", 600)
    a.hover(".m4subtabs button >> nth=0", 600)
    a.say("先看「配息行事曆」", "point_dr_v2")
    a.click(".m4subtabs button >> nth=0", label="配息行事曆")
    a.wait(800)
    a.settle()


def m_cal(pg, a, start):
    goto(pg, a, "#etf/cal", 4000)
    start()
    a.cam(["#etfCalCard .calhd", "#etfCalGrid"], 8, "配息行事曆")
    a.say("第一站：配息行事曆", "point_r_v2")
    a.hover('#etfCalGrid .cald.has', 700)
    a.say("格子標出當天除息的 ETF 與每單位配息", "talk_explain_v2")
    a.hover('#etfCalGrid .cald.today', 800)
    a.say("藍框代表今天", "face_nod_v2")
    a.idle(300)
    a.say("點有除息的日期，下方列出當天清單", "point_dr_v2")
    a.click('#etfCalGrid .cald.has', label="點有除息的日期")
    a.wait(600)
    a.cam(["#etfCalList .ph", "#etfDayTbl thead", "#etfDayTbl tbody tr:nth-child(8)"], 6, "當天清單上半")
    a.scroll_to_el("#etfCalList", 70, 1000)
    a.say("配息金額、當次殖利率、發放日一次看", "talk_explain_v2")
    a.hover('#etfDayTbl tbody tr', 700)
    a.say("當次殖利率＝配息 ÷ 除息前一日收盤", "talk_explain_v2")
    a.hover('#etfDayTbl thead th >> nth=2', 900)
    a.say("填息天數：股價回到除息前收盤的交易日數", "magnifier")
    a.hover('#etfDayTbl thead th >> nth=4', 900)
    a.scroll(to_y=0, ms=1000)
    a.cam(["#etfCalCard .calhd", "#etfCalGrid"], 8, "配息行事曆")
    a.say("切換月份，查看各月的除息時程", "calendar")
    a.click("#etfCalPrev", label="上月")
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
    a.cam(["#etfCatBar", ".m4ctlrow", ".m4trisg", "#etfTri"], 6, "分類分頁")
    a.say("第二站：ETF 總覽，共分七類", "point_ur_v2")
    a.hover('#etfCatSeg button[data-v="配息型"]', 600)
    a.say("依代號、名稱與配息紀錄自動分類", "talk_explain_v2")
    a.click('#etfCatSeg button[data-v="市值型"]', label="市值型")
    a.wait(700)
    a.click('#etfCatSeg button[data-v="主題型"]', label="主題型")
    a.wait(600)
    a.click('#etfCatSeg button[data-v="主動式"]', label="主動式")
    a.wait(500)
    a.say("分頁上的數字，就是每一類的檔數", "point_ur_v2")
    a.idle(500)
    a.say("切換分頁，下方卡片與圖表同步換類", "talk_explain_v2")
    a.click('#etfCatSeg button[data-v="主題型"]', label="主題型")
    a.wait(600)
    a.cam_view("整頁同步")
    a.scroll(by=600, ms=1800)
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
    a.cam([".m4ctlrow", ".m4trisg", "#etfTri"], 6, "三張卡")
    a.say("三張排行卡，先看口徑再看數字", "talk_explain_v2")
    a.hover("#etfPopSub", 800)
    a.say("受益人：集保受益人數的週增加量", "point_r_v2")
    a.idle(500)
    a.cam_view("設定抽屜")
    m_sheet(a, "pop", "turnover", "成交值")
    a.cam([".m4ctlrow", ".m4trisg", "#etfTri"], 6, "三張卡")
    a.say("成交值：近 20 個交易日平均成交金額", "talk_explain_v2")
    a.idle(600)
    a.click('.m4trisg button[data-i="1"]', label="報酬率")
    a.wait(500)
    a.say("報酬率前 5：依含息年化報酬排序", "point_r_v2")
    a.hover("#etfRetTopQ", 700)
    a.say("上市未滿期間的，改以上市以來計算", "talk_explain_v2")
    a.idle(500)
    a.click('.m4trisg button[data-i="2"]', label="殖利率")
    a.wait(500)
    a.say("殖利率＝近 12 個月現金配息 ÷ 最新收盤", "coins")
    a.hover("#etfYldQ", 700)
    a.say("平均填息天數，看配息是否被價差抵銷", "magnifier")
    a.idle(500)
    a.say("以上皆為歷史資料，不代表未來表現", "face_nod_v2")
    a.idle(400)
    a.click('.m4trisg button[data-i="0"]', label="最受歡迎")
    a.wait(400)
    a.settle()


def m_ret(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    m_scroll_to(pg, "#etfRetCard", 130)
    start()
    a.cam(["#etfRetCard .row.spread", "#etfRetBody .retcharts > div:first-child"], 6, "報酬比較")
    a.say("第三站：報酬比較", "point_r_v2")
    a.hover("#etfRetCard h3", 600)
    a.say("期間可選近 1、3、5、10 年或上市以來", "talk_explain_v2")
    a.scroll(by=-130, ms=700)
    a.cam_view("設定抽屜")
    m_sheet(a, "rng", "1y", "近 1 年")
    a.say("也能選「起始日期～至今」自訂區間", "point_ur_v2")
    m_sheet(a, "rng", "custom", "起始日期～至今")
    a.cam(["#etfRetCard .row.spread", "#etfRngBox", "#etfRetBody .retcharts > div:first-child"], 6, "日期列")
    b = a.box("#etfRng .rpfrom")
    if b:
        a.click_xy(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, 500, 250, expect="#etfRng .rpfrom")
        a.wait(300)
        pg.keyboard.press("ArrowDown")
        a.wait(900)
        a.mark("改起始日期")
    a.cam(["#etfRetCtl", "#etfCmpDD .ddpanel"], 8, "加入比較")
    a.say("點「已選 N 檔」，輸入代號或名稱搜尋", "point_r_v2")
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
    a.cam(["#etfRetBody .retcharts > div:first-child"], 6, "累積報酬走勢")
    a.scroll_to_el("#etfRetBody .retcharts", 120, 900)
    a.say("左圖：累積報酬走勢，期初皆為 0%", "point_r_v2")
    a.hover("#etfRetLine", 600, 0.5, 0.45)
    a.say("拖曳下方拉桿，放大想看的區段", "talk_explain_v2")
    hb = pg.evaluate(DZ_HANDLE_JS, "#etfRetLine")
    if hb:
        a.drag(hb[0], hb[1], hb[0] + 140, hb[1], 1200)
        a.wait(900)
        a.mark("拖曳拉桿")
    a.cam(["#etfRetBody .retcharts > div:last-child"], 6, "年化報酬率")
    a.scroll_to_el("#etfRetBody .retcharts > div:last-child", 120, 900)
    a.say("下圖：並列每一檔的年化報酬率", "point_dr_v2")
    a.hover("#etfRetBar", 700, 0.5, 0.3)
    a.say("切換含息／不含息，看報酬多少來自配息", "talk_explain_v2")
    a.cam_view("設定抽屜")
    m_sheet(a, "basis", "price", "不含息")
    a.cam(["#etfRetBody .retcharts > div:last-child"], 6, "年化報酬率")
    a.wait(500)
    a.say("兩者差距越大，報酬越依賴配息", "face_thinking_bulb")
    a.hover("#etfRetBar", 700, 0.5, 0.6)
    a.cam(["#etfRetTbl"], 6, "明細表")
    a.scroll_to_el("#etfRetTbl", 160, 900)
    a.say("明細表列出各檔的價格年化與含息年化", "point_dr_v2")
    a.hover("#etfRetTbl tbody tr >> nth=0", 700, 0.5)
    a.hover("#etfRetTbl tbody tr >> nth=1", 600, 0.5)
    a.idle(400)
    a.settle()


def m_end(pg, a, start):
    goto(pg, a, "#etf/list")
    pg.locator('#etfCatSeg button[data-v="配息型"]').first.click()
    pg.wait_for_timeout(1500)
    start()
    a.cam_view("總覽")
    a.say("除息時程、分類比較、報酬回測，一頁完成", "proud_shine")
    a.scroll(by=700, ms=2600)
    a.say("想親自操作，搜尋「哩股哩股」", "invite_nod")
    a.scroll(to_y=0, ms=1800)
    a.idle(500)
    a.settle()


DZ_HANDLE_JS = r"""(sel) => { const host = document.querySelector(sel); if (!host || !window.echarts) return null;
  const ch = echarts.getInstanceByDom(host); if (!ch) return null;
  try { const dz = ch.getModel().getComponent('dataZoom'); if (!dz) return null; const v = ch.getViewOfComponentModel(dz);
    const hs = v._displayables && v._displayables.handles; if (!hs || !hs[0]) return null; const h = hs[0];
    const br = h.getBoundingRect(); const m = h.getComputedTransform ? h.getComputedTransform() : h.transform;
    let cx = br.x + br.width / 2, cy = br.y + br.height / 2;
    if (m) { const x = m[0] * cx + m[2] * cy + m[4], y = m[1] * cx + m[3] * cy + m[5]; cx = x; cy = y; }
    const hr = host.getBoundingClientRect(); return [hr.left + cx, hr.top + cy]; } catch (e) { return null; } }"""


MOB_DATE_CSS = r"""(() => { const go = () => { const st = document.createElement('style');
  st.textContent = 'html.m4 .rpk .rpd{display:flex;flex-wrap:nowrap;gap:6px;align-items:center} html.m4 .rpk .rpd input[type=date]{min-width:150px;width:150px;flex:0 0 150px}';
  document.head.appendChild(st); }; document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go(); })();"""


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
                ctx.add_init_script(C.HIDE_B_JS)   # 法遵：B 類功能名稱不入鏡
                if dev == "m":   # 手機日期框太窄會截字（10/16/201…）：錄影時把寬度讓出來（只在錄影的瀏覽器裡）
                    ctx.add_init_script(MOB_DATE_CSS)
                if dev == "d" and sid != "guide":   # 桌機左側導覽收成圖示列：內容區更寬，鏡頭也不會帶到導覽文字
                    ctx.add_init_script("try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}")
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
                    content = [0, cfg["viewport"]["width"]] if sid == "guide" else pg.evaluate("() => { const e = document.querySelector('#etfCalCard:not([hidden])') || document.querySelector('#etfBody'); const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
                    r.update(size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    meta[sid] = r
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")   # 每鏡一檔（平行錄不互蓋）
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", r.get("bad")[:3], "errs:", errs[:2])
                except Exception as exc:  # noqa: BLE001
                    rec.on = False
                    print(sid, "失敗", exc)
                    meta[sid] = {"ok": False, "why": str(exc)[:300], "steps": a.log}
                    shutil.rmtree(out / f".tmp_{dev}_{sid}", ignore_errors=True)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()


D_SHOTS = {"open": d_open, "guide": d_guide, "cal": d_cal, "types": d_types, "cards": d_cards, "ret": d_ret, "end": d_end}
M_SHOTS = {"open": m_open, "guide": m_guide, "cal": m_cal, "types": m_types, "cards": m_cards, "ret": m_ret, "end": m_end}


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
