"""功能介紹影片 03：財經日曆 —— 素材錄製（沿用 02 的 capture_cf.py 做法，快節奏、成片整支 1.5 倍速）。

沿用 docs/marketing/video_1010/capture.py 的逐格算圖錄影器（page.clock 暫停、每格推進 1/30 秒再截圖，不掉格）、
錄影游標＋點擊漣漪（錄進畫面，點擊中心＝錄影當下量到的元素中心）。一律「未登入訪客」的真實畫面（Andy 10-19），客服鈕照常顯示、鏡頭避開。

本檔另外記錄：
- 每一格的「鏡頭」：目前要介紹的那一塊（選擇器聯集＋留白）在影片像素的外框 → 成片只裁這一塊放大。
- 比比的台詞泡泡（一泡一句、≤14 字）：say() 記下出現秒數；下一句出現前，前一句至少停留 bubble_dur 秒（原片 ≥1.45 秒）。
- 點擊：capture.Act 量到的元素外框與點下座標（clicks）；label 一律由本檔指定（不讀畫面文字，報告裡不會出現個股名稱）。

法遵（growth_plan_1018.md 9-1 第 1 條「畫面不出現個股代號／名稱當主角」）：錄影的瀏覽器裡把財經日曆頁上的
個股代號與名稱（月曆標籤、右側清單、面板標題、新聞標題裡的公司名…）逐字包成模糊（BLUR_JS，只在錄影的瀏覽器裡，不改 site/）。
FED 與美國數據（CPI、FOMC…）不是個股，照常顯示。

用法（repo 根目錄，先 SKIP_INTRADAY=1 python -m pipeline.build_payload）：
    python docs/marketing/videos/feature_series/03_fin_calendar/capture_cal.py --dev d [--shots open,guide]
    python docs/marketing/videos/feature_series/03_fin_calendar/capture_cal.py --dev m
輸出（大檔，放 scratchpad）：<out>/<dev>_<鏡頭>.mp4 ＋ <out>/<dev>_<鏡頭>.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import shutil
import sys
import threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "docs" / "marketing" / "video_1010"))
import capture as C  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat03"))
FPS = 30
DEVS = {
    "d": dict(viewport={"width": 1600, "height": 900}, device_scale_factor=2),
    "m": dict(viewport={"width": 390, "height": 844}, device_scale_factor=4, is_mobile=True, has_touch=True),
}
PACE = float(os.environ.get("FEAT_PACE", "1.0"))


def bubble_dur(text: str) -> float:
    """泡泡停留秒數：每泡 ≤14 字；成片 1.5 倍速 → 原片 ≥1.45 秒（1.5 倍後 ≥0.97 秒）。"""
    n = len(text.replace(" ", ""))
    return min(1.9, max(1.45, 0.75 + 0.08 * n))


CAM_JS = r"""([sels, pad]) => {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, n = 0;
  for (const s of sels) { const e = document.querySelector(s); if (!e || !e.getClientRects().length) continue;
    const r = e.getBoundingClientRect(); if (r.width < 2 || r.height < 2) continue;
    // 面板（內部捲動）裡的元素：只算露在面板可視範圍內的部分
    const sc = e.closest('#earnPanel'); let t = r.top, b = r.bottom;
    if (sc && e !== sc) { const pr = sc.getBoundingClientRect(); t = Math.max(t, pr.top); b = Math.min(b, pr.bottom); if (b - t < 2) continue; }
    x0 = Math.min(x0, r.left); y0 = Math.min(y0, t); x1 = Math.max(x1, r.right); y1 = Math.max(y1, b); n++; }
  if (!n) return null;
  return [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad]; }"""

FAB_JS = r"""() => { const es = [...document.querySelectorAll('#supFab, .supfab, #bibiRing, .bibiring, #bibiStage, .bibiwrap')]
  .filter(e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden' && +getComputedStyle(e).opacity > 0.05);
  if (!es.length) return null; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  es.forEach(e => { const r = e.getBoundingClientRect(); if (r.width < 2) return; x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
  return x1 > x0 ? [x0, y0, x1 - x0, y1 - y0] : null; }"""


def blur_js() -> str:
    """個股代號與名稱逐字模糊（只在錄影的瀏覽器裡）。名單＝資料湖 company_info 全部普通股＋財經日曆資料裡出現的公司。"""
    names, codes = set(), set()
    try:
        import pandas as pd
        fs = glob.glob(str(REPO / "data" / "company_info" / "**" / "*.parquet"), recursive=True)
        df = pd.concat([pd.read_parquet(f, columns=["code", "name"]) for f in fs])
        df = df[df["code"].astype(str).str.fullmatch(r"\d{4}")]
        codes |= set(df["code"].astype(str))
        # 兩字公司名裡的一般用語（新聞標題、說明文常見）不當名字模糊，免得說明文字被糊掉；
        # 真的出現在財經日曆的公司（下面 earnings.json 那段）一律加回來。
        generic = {"世界", "全國", "中華", "大陸", "數字", "介面", "互動", "統一", "全新", "大量", "地球", "光明", "幸福", "相互",
                   "時報", "典範", "冠軍", "新產", "卓越", "無敵", "正道", "必應", "有益", "有量", "立誠", "國產", "大同", "東洋",
                   "台南", "南港", "大成", "國建", "新興", "精華", "公準", "力成", "可成", "大立", "華新"}
        names |= {n for n in df["name"].astype(str) if len(n) >= 2 and n not in generic}
    except Exception:  # noqa: BLE001
        pass
    try:
        e = json.loads((C.SITE / "data" / "earnings.json").read_text(encoding="utf-8"))
        for c, v in (e.get("companies") or {}).items():
            codes.add(str(c))
            if v.get("name"):
                names.add(v["name"])
        for ev in e.get("events") or []:
            if ev.get("code"):
                codes.add(str(ev["code"]))
            if ev.get("name"):
                names.add(ev["name"])
    except Exception:  # noqa: BLE001
        pass
    import re
    names = sorted(names, key=len, reverse=True)
    names = [n.replace("*", "") for n in names]   # 公司名後綴的「*」是證交所標記，不是名字的一部分
    pat = "|".join(re.escape(n) for n in names if n) + "|" + "|".join(sorted(codes))
    return r"""
(() => {
  const RE = new RegExp('(?<![0-9A-Za-z.,/:\\-])(' + %s + ')(?![0-9.,%%/:\\-])|(?<=收盤 |市值第 )([0-9][0-9,]*(?:\\.[0-9]+)?)', 'g');   // 第二組：面板裡「收盤 X 元」的股價、「市值第 N 名」的名次也模糊（避免由價位、名次認出是哪一家）
  const SKIP = '.fcard,[data-sec=spark],[data-sec=rule],#earnFilt,.elegend,.ehd,.wd,.dn,.edisc,.__blur,script,style,.badge,.stars';
  const css = () => { const st = document.createElement('style'); st.textContent = '.__blur{filter:blur(5px)!important;display:inline-block}'; document.head.appendChild(st); };
  const sweep = (root) => {
    const v = document.getElementById('v-earnings'); if (!v) return;
    const p = document.getElementById('earnPanel'); const fedMode = p && p.dataset.mode === 'fed';
    const w = document.createTreeWalker(root && v.contains(root) ? root : v, NodeFilter.SHOW_TEXT); const hits = []; let n;
    while ((n = w.nextNode())) { const t = n.nodeValue; if (!t || !t.trim()) continue; const e = n.parentElement; if (!e || e.closest(SKIP)) continue;
      if (fedMode && e.closest('#earnPanel')) continue; RE.lastIndex = 0; if (RE.test(t)) hits.push(n); }
    for (const n of hits) { const t = n.nodeValue; RE.lastIndex = 0; const f = document.createDocumentFragment(); let last = 0, m;
      while ((m = RE.exec(t))) { if (m.index > last) f.appendChild(document.createTextNode(t.slice(last, m.index)));
        const g = m[1] || m[2]; const s = document.createElement('span'); s.className = '__blur'; s.textContent = g; f.appendChild(s); last = m.index + g.length; }
      if (last < t.length) f.appendChild(document.createTextNode(t.slice(last)));
      n.parentNode.replaceChild(f, n); }
  };
  const go = () => { css(); sweep(); new MutationObserver(() => sweep()).observe(document.body, { childList: true, subtree: true, characterData: true }); };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
})();
""" % json.dumps(pat)


# ECharts 小圖第 i 欄的中心（影片要點在長條／折線點上）
MINI_PT_JS = r"""([sel, i]) => { const host = document.querySelector(sel); if (!host || !window.echarts) return null;
  const ch = echarts.getInstanceByDom(host); if (!ch) return null;
  try { const op = ch.getOption(); const s0 = op.series[0]; const v = s0.data[i]; const val = v && typeof v === 'object' ? v.value : v;
    const isBar = s0.type === 'bar'; const p = ch.convertToPixel({ seriesIndex: 0 }, [i, isBar ? (val || 0) / 2 : (val || 0)]);
    const hr = host.getBoundingClientRect(); let y = hr.top + p[1]; if (isBar && Math.abs((val || 0)) < 1e-9) y = hr.top + hr.height * 0.5;
    if (isBar) { const pz = ch.convertToPixel({ seriesIndex: 0 }, [i, val || 0]); const p0 = ch.convertToPixel({ seriesIndex: 0 }, [i, 0]);
      if (Math.abs(pz[1] - p0[1]) < 10) y = hr.top + Math.min(pz[1], p0[1]) - 4; }
    return [hr.left + p[0], y, op.xAxis[0].data.length]; } catch (e) { return null; } }"""


class Rec(C.Recorder):
    """逐格錄影＋每格記錄鏡頭外框（影片像素）。"""

    def __init__(self, pg, w, h, act):
        super().__init__(pg, w, h, dry=bool(os.environ.get("FEAT_DRY")))
        self.act = act
        self.cams: list = []
        self.fabs: list = []

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
        if r is None:
            r = [0, 0, a.vw, a.vh]
        self.cams.append([a.cam_id] + [round(v * a.dsf, 1) for v in r])
        try:
            fb = self.pg.evaluate(FAB_JS)
        except Exception:  # noqa: BLE001
            fb = None
        self.fabs.append([round(v * a.dsf, 1) for v in fb] if fb else None)


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
        if self.say_t is not None:
            rest = self.say_need - (self.t - self.say_t)
            if rest > 0.02:
                self.idle(rest * 1000)

    def say(self, text, act="talk_explain_v2"):
        assert len(text.replace(" ", "")) <= 14, text
        self.settle()
        first = not self.says
        self.says.append({"t": round(self.t, 3), "text": text, "act": act})
        # 成片合成時：每段第一泡晚 0.25 秒出現（交叉淡化）、每泡提早 0.06 秒收 → 錄影這邊先補足，泡泡實際停留仍 ≥ bubble_dur
        self.say_t, self.say_need = self.t, bubble_dur(text) + 0.08 + (0.27 if first else 0.0)

    def click(self, sel, ms=380, pause=150, dx=0.5, dy=0.5, label=""):
        n0 = len(self.targets)
        ok = super().click(sel, ms, pause, dx, dy, label)
        if ok and label and len(self.targets) > n0:
            self.targets[-1]["label"] = label
        return ok

    def click_pt(self, x, y, label, expect=None, ms=380, pause=150, measured_by=""):
        self.click_xy(x, y, ms, pause, expect=expect)
        tg = self.targets[-1]
        tg["label"] = label
        if measured_by:   # canvas 裡的圖形：中心取自 ECharts 量到的座標
            tg.update(rect_center=list(tg["center"]), measured_by=measured_by)

    def hover(self, sel, ms=420, dx=0.5, dy=0.5):
        return super().hover(sel, ms, dx, dy)

    def wait(self, ms):
        return super().wait(ms * PACE)

    def mark(self, name):
        self.marks.append([round(self.t, 3), "mark", name])

    def mini_pt(self, sel, i):
        return self.pg.evaluate(MINI_PT_JS, [sel, i])

    def mini_hover(self, sel, idx, ms=420, hold=650, label="圖表"):
        """滑鼠（手機＝手指點一下）移到 ECharts 小圖第 i 欄：提示框＋加亮。"""
        for i in idx:
            p = self.mini_pt(sel, i)
            if not p:
                self.note(f"量不到小圖 {sel} {i}")
                continue
            if self.mob:
                self.click_pt(p[0], p[1], f"{label}第 {i + 1} 欄", ms=ms, pause=120, measured_by="echarts 欄位中心")
            else:
                self.move(p[0], p[1], ms)
            self.wait(hold)

    def panel_scroll_to(self, sel, off=46, ms=700):
        """面板（內部捲動）捲到 sel 那一段的標題（逐格）。"""
        y = self.pg.evaluate("([s, o]) => { const p = document.getElementById('earnPanel'), e = p && p.querySelector(s); if (!e) return null;"
                             " return p.scrollTop + e.getBoundingClientRect().top - p.getBoundingClientRect().top - o; }", [sel, off])
        if y is None:
            self.note(f"面板找不到 {sel}")
            return False
        self.scroll(to_y=y, ms=ms, el="#earnPanel")
        return True


# ------------------------------------------------------------------ 共用
def goto(pg, hash_, wait=3500):
    pg.evaluate("(h) => { location.hash = h; }", hash_)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => scrollTo(0, 0)")
    pg.wait_for_timeout(400)


def to_cal(pg, filt="rep", wait=4000):
    goto(pg, "#earnings", wait)
    if filt != "rep":
        pg.locator(f'#earnFilt button[data-v="{filt}"]').first.click()
        pg.wait_for_timeout(900)


def chip(k):
    return f'#earnGrid .chip[data-k="{k}"]'


def m_scroll_to(pg, sel, off=70):
    y = pg.evaluate("([s,o]) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect().top + scrollY - o : 0; }", [sel, off])
    pg.evaluate("(y) => scrollTo(0, y)", y)
    pg.wait_for_timeout(500)


FIRST_CO_JS = r"""(k) => { const c = [...document.querySelectorAll('#earnGrid .chip[data-code]')].filter(x => !k || x.dataset.k === k);
  return c.length ? `#earnGrid .chip[data-i="${c[c.length > 1 ? 1 : 0].dataset.i}"]` : null; }"""


# ------------------------------------------------------------------ 網頁版鏡頭
def d_open(pg, a, start):
    to_cal(pg, "fed")
    start()
    a.cam(["#earnFilt", "#earnBody"], 6, "財經日曆（FED 消息）")
    a.move(900, 520, 400)
    a.say("重要數據，哪天公布？", "face_think_v2")
    a.hover(chip("cpi"), 700)
    a.hover(chip("fomc"), 700)
    a.say("公布了，又代表什麼？", "tilt")
    a.hover(chip("nfp"), 700)
    a.idle(500)
    a.say("財經日曆，一頁看懂", "news")
    a.hover(chip("pce"), 700)
    a.idle(500)
    a.settle()


def d_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam(['#tabs .tab[data-view="overview"]', '#tabs .tab[data-view="earnings"]'], 16, "選單：今日市場")
    a.say("看左側「今日市場」", "point_r_v2")
    a.hover('#tabs .tab[data-view="overview"]', 600)
    a.idle(300)
    a.say("點「財經日曆」", "magnifier")
    a.hover('#tabs .tab[data-view="articles"]', 400)
    a.click('#tabs .tab[data-view="earnings"]', label="選單：財經日曆")
    a.wait(1600)
    a.cam(["#earnCalCard"], 6, "進到財經日曆")
    a.idle(500)
    a.settle()


def d_cal(pg, a, start):
    to_cal(pg, "rep")
    start()
    a.cam(["#earnFilt", "#earnLegend", ".ehd", "#earnGrid"], 8, "分類＋月曆")
    a.say("三大類，排在同一張月曆", "talk_explain_v2")
    a.hover('#earnFilt button[data-v="rep"]', 500)
    for v, lab in (("conf", "公司法說"), ("fed", "FED 消息"), ("rep", "公司財報")):
        a.click(f'#earnFilt button[data-v="{v}"]', label=lab)
        a.wait(850)
        if v == "conf":
            a.say("切分類，月曆圖例跟著換", "point_r_v2")
    a.click('#earnFilt button[data-v="fed"]', label="FED 消息")
    a.wait(700)
    a.cam(["#earnLegend", "#earnGrid"], 8, "圖例＋月曆")
    a.say("顏色分事件，紫底是休市", "calendar")
    a.hover("#earnLegend", 500, 0.25)
    a.hover('#earnGrid .ed[data-hol="1"]', 600)
    a.cam(["#earnGrid", "#earnPanel"], 6, "月曆＋右側清單")
    a.say("點日期，右邊列當天事件", "magnifier")
    for d, lab in ((29, "日期：29 日"), (2, "日期：2 日"), (28, "日期：28 日")):
        a.click(f'#earnGrid .ed[data-d$="-{d:02d}"]:not(.out) .dn', label=lab)
        a.wait(850)
    a.say("上月、下月，看其他月份", "face_nod_v2")
    a.click("#earnNext", label="下月")
    a.wait(900)
    a.click("#earnToday", label="回本月")
    a.wait(700)
    a.settle()


def d_fed(pg, a, start):
    to_cal(pg, "fed")
    start()
    a.cam([chip("cpi"), "#earnPanel"], 8, "CPI 標籤＋面板")
    a.say("點事件，右邊出現分析", "point_r_v2")
    a.click(chip("cpi"), label="事件：CPI")
    a.wait(800)
    a.cam(["#earnPanel .ph", "#earnPanel .fcard"], 8, "CPI 說明卡")
    a.say("是什麼、怎麼看、影響", "talk_explain_v2")
    a.hover("#earnPanel .fcard p:nth-of-type(1)", 450, 0.3)
    a.hover("#earnPanel .fcard p:nth-of-type(2)", 450, 0.3)
    a.hover("#earnPanel .fcard p:nth-of-type(3)", 450, 0.3)
    a.say("星越多，市場越重視", "face_thinking_bulb")
    a.hover("#earnPanel .fcard .stars", 500)
    a.hover("#earnPanel .fcard .fnum", 600)
    a.cam(["#earnPanel [data-sec=spark]"], 8, "近期數值走勢")
    a.panel_scroll_to("[data-sec=spark]", 6)
    a.say("滑過走勢看每期數值", "magnifier")
    a.mini_hover("#earnPanel [data-sec=spark] .cgmini", [3, 8, 11], label="CPI 走勢")
    a.cam(["#earnPanel [data-sec=spark]", "#earnPanel [data-sec=rule]"], 8, "關注點與多空規則")
    a.panel_scroll_to("[data-sec=rule]", 260)
    a.say("關注點、多空規則都寫好", "bulb")
    a.hover("#earnPanel [data-sec=rule] p", 600, 0.3)
    a.idle(400)
    a.cam([chip("fomc"), "#earnPanel"], 8, "FOMC 標籤＋面板")
    a.say("FOMC：利率決議", "globe")
    a.click(chip("fomc"), label="事件：FOMC")
    a.wait(800)
    a.cam(["#earnPanel [data-sec=spark]"], 8, "FOMC 相關數據走勢")
    a.panel_scroll_to("[data-sec=spark]", 6)
    a.say("通膨、就業走勢一起看", "face_nod_v2")
    sp = pg.evaluate("() => document.querySelectorAll('#earnPanel [data-sec=spark] .cgmini').length")
    for j in range(min(3, sp)):
        a.mini_hover(f"#earnPanel [data-sec=spark] .mini:nth-of-type({j + 1}) .cgmini", [10], hold=600, label=f"走勢 {j + 1} ")
    a.cam_view("捲動")
    a.scroll(by=220, ms=600)   # 面板最下面一段在客服鈕旁邊：整頁往下捲一點，面板整塊入鏡、鏡頭不必為了避開客服鈕把面板右側裁掉
    a.cam(["#earnPanel .sec:last-child"], 8, "下一次公布日")
    a.panel_scroll_to(".sec:last-child", 120)
    a.say("下一次公布日也列好", "alarm")
    a.hover("#earnPanel .sec:last-child p", 500, 0.3)
    a.idle(300)
    a.settle()


def d_co(pg, a, start):
    to_cal(pg, "rep")
    sel = pg.evaluate(FIRST_CO_JS, "")
    start()
    a.cam([sel, "#earnPanel"], 8, "公司財報標籤＋面板")
    a.say("點公司，看這次財報", "point_r_v2")
    a.click(sel, label="事件：公司財報董事會")
    a.wait(800)
    a.cam(["#earnPanel .ph", "#earnPanel .tags", "#earnPanel .sec[data-sec]"], 8, "財報重點標籤")
    a.say("先看營收、毛利的方向", "talk_explain_v2")
    a.hover("#earnPanel .tags .tag:nth-child(1)", 450)
    a.hover("#earnPanel .tags .tag:nth-child(2)", 450)
    a.hover("#earnPanel .tags .tag:nth-child(3)", 450)
    a.cam(["#earnPanel [data-sec=rev]"], 8, "月營收趨勢")
    a.panel_scroll_to("[data-sec=rev]", 6)
    a.say("月營收＋年增，滑過看", "magnifier")
    a.mini_hover("#earnPanel [data-sec=rev] .cgmini", [4, 8, 11], label="月營收")
    p = a.mini_pt("#earnPanel [data-sec=rev] .cgmini", 9)
    if p:
        a.say("點長條，選取那個月", "face_thinking_bulb")
        a.click_pt(p[0], p[1], "月營收第 10 欄（選取）", measured_by="echarts 欄位中心")
        a.wait(900)
    a.cam(["#earnPanel [data-sec=val]"], 8, "估值位置")
    a.panel_scroll_to("[data-sec=val]", 6)
    a.say("本益比在自己歷史哪裡", "calc")
    a.hover("#earnPanel [data-sec=val] .pe-track", 600)
    a.idle(400)
    a.cam(["#earnPanel [data-sec=inst]"], 8, "法人籌碼")
    a.panel_scroll_to("[data-sec=inst]", 6)
    a.say("法人 20 日買賣超", "point_r_v2")
    a.mini_hover("#earnPanel [data-sec=inst] .cgmini", [5, 12, 18], label="法人")
    a.cam(["#earnFilt", "#earnGrid"], 8, "切到公司法說")
    a.say("法說會也標在月曆上", "calendar")
    a.click('#earnFilt button[data-v="conf"]', label="公司法說")
    a.wait(700)
    sel2 = pg.evaluate(FIRST_CO_JS, "conf")
    a.cam([sel2, "#earnPanel"], 8, "法說標籤＋面板")
    a.click(sel2, label="事件：公司自辦法說")
    a.wait(800)
    a.cam(["#earnPanel .ph", "#earnPanel [data-sec=conf]"], 8, "這場法說")
    a.say("時間、地點、主題一次看", "face_nod_v2")
    a.hover("#earnPanel [data-sec=conf] dd", 500, 0.3)
    a.idle(500)
    a.settle()


def d_end(pg, a, start):
    to_cal(pg, "fed")
    start()
    a.cam(["#earnFilt", "#earnBody"], 6, "總覽")
    a.say("財報、法說、FED 一頁掌握", "proud_shine")
    a.move(700, 500, 900)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.move(1000, 600, 900)
    a.settle()


# ------------------------------------------------------------------ 手機版鏡頭（390 寬 m4 版面）
M_ROWS4 = "#earnGrid > :nth-child(35)"   # 7 格星期列＋前 4 週（第 4 週週六那一格）


def m_open(pg, a, start):
    to_cal(pg, "fed")
    m_scroll_to(pg, "#earnCalCard", 60)
    start()
    a.cam(["#earnLegend", "#earnGrid"], 6, "財經日曆（FED 消息）")   # 手機：分類鈕＋整張月曆比畫面框高，會被裁；開場只框圖例＋月曆
    a.say("重要數據，哪天公布？", "face_think_v2")
    a.hover(chip("cpi"), 700)
    a.hover(chip("fomc"), 700)
    a.say("公布了，又代表什麼？", "tilt")
    a.hover(chip("nfp"), 700)
    a.idle(500)
    a.say("財經日曆，一頁看懂", "news")
    a.hover(chip("pce"), 700)
    a.idle(500)
    a.settle()


def m_guide(pg, a, start):
    goto(pg, "#overview", 3500)
    start()
    a.cam_view("首頁總覽")
    a.say("點左上角選單", "point_ur_v2")
    a.click("#m4Burger", label="選單")
    a.wait(900)
    a.cam(['.m4item[data-v="overview"]', '.m4item[data-v="earnings"]'], 10, "選單抽屜")
    a.say("點「財經日曆」", "magnifier")
    a.hover('.m4item[data-v="overview"]', 400)
    a.click('.m4item[data-v="earnings"]', label="選單：財經日曆")
    a.wait(1500)
    a.cam(["#earnFilt", "#earnGrid"], 6, "進到財經日曆")
    a.idle(500)
    a.settle()


def m_cal(pg, a, start):
    to_cal(pg, "rep")
    m_scroll_to(pg, "#earnCalCard", 60)
    start()
    a.cam(["#earnFilt", "#earnLegend", M_ROWS4], 6, "分類＋月曆前 4 列")
    a.say("三大類，排在同一張月曆", "talk_explain_v2")
    for v, lab in (("conf", "公司法說"), ("fed", "FED 消息"), ("rep", "公司財報")):
        a.click(f'#earnFilt button[data-v="{v}"]', label=lab)
        a.wait(850)
        if v == "conf":
            a.say("切分類，月曆圖例跟著換", "point_ur_v2")
    a.click('#earnFilt button[data-v="fed"]', label="FED 消息")
    a.wait(700)
    a.cam(["#earnLegend", "#earnGrid"], 6, "圖例＋月曆")
    a.say("顏色分事件，紫底是休市", "calendar")
    a.hover('#earnGrid .ed[data-hol="1"]', 600)
    a.idle(300)
    a.cam_view("捲動")
    a.scroll_to_el('#earnGrid .ed[data-d$="-14"]:not(.out)', 100, 700)   # 月曆第 3～6 列＋下方清單同一畫面
    a.cam(['#earnGrid .ed[data-d$="-14"]:not(.out)', "#earnPanel .ph", "#earnDayList"], 6, "月曆＋下方當天清單")
    a.say("點日期，下方列當天事件", "magnifier")
    for d, lab in ((29, "日期：29 日"), (14, "日期：14 日"), (28, "日期：28 日")):
        a.click(f'#earnGrid .ed[data-d$="-{d:02d}"]:not(.out) .dn', label=lab)
        a.wait(850)
    a.cam_view("捲動")
    a.scroll_to_el("#earnCalCard", 60, 700)
    a.cam([".ehd"], 6, "月份切換")
    a.say("上月、下月，看其他月份", "face_nod_v2")
    a.click("#earnNext", label="下月")
    a.wait(900)
    a.click("#earnToday", label="回本月")
    a.wait(700)
    a.settle()


def m_panel_into_view(a, ms=800):
    a.cam_view("捲動")
    a.scroll_to_el("#earnPanel", 64, ms)


def m_fed(pg, a, start):
    to_cal(pg, "fed")
    m_scroll_to(pg, "#earnGrid", 120)
    start()
    a.cam([chip("cpi"), "#earnGrid"], 6, "CPI 標籤")
    a.say("點事件，下方出現分析", "point_dr_v2")
    a.click(chip("cpi"), label="事件：CPI")
    a.wait(500)
    m_panel_into_view(a)
    a.cam(["#earnPanel .ph", "#earnPanel .fcard"], 6, "CPI 說明卡")
    a.say("是什麼、怎麼看、影響", "talk_explain_v2")
    a.idle(500)
    a.say("星越多，市場越重視", "face_thinking_bulb")
    a.hover("#earnPanel .fcard .stars", 500)
    a.idle(400)
    a.cam(["#earnPanel [data-sec=spark]"], 6, "近期數值走勢")
    a.panel_scroll_to("[data-sec=spark]", 6)
    a.say("點走勢看每期數值", "magnifier")
    a.mini_hover("#earnPanel [data-sec=spark] .cgmini", [3, 8, 11], label="CPI 走勢")
    a.cam(["#earnPanel [data-sec=rule]", "#earnPanel .sec:has(> p + p)"], 6, "關注點與多空規則")
    a.panel_scroll_to("[data-sec=rule]", 200)
    a.say("關注點、多空規則都寫好", "bulb")
    a.idle(700)
    a.cam_view("捲動")
    a.scroll_to_el("#earnGrid", 120, 700)
    a.cam([chip("fomc"), "#earnGrid"], 6, "FOMC 標籤")
    a.say("FOMC：利率決議", "globe")
    a.click(chip("fomc"), label="事件：FOMC")
    a.wait(500)
    m_panel_into_view(a)
    a.cam(["#earnPanel [data-sec=spark]"], 6, "FOMC 相關數據走勢")
    a.panel_scroll_to("[data-sec=spark]", 6)
    a.say("通膨、就業走勢一起看", "face_nod_v2")
    sp = pg.evaluate("() => document.querySelectorAll('#earnPanel [data-sec=spark] .cgmini').length")
    for j in range(min(3, sp)):
        sel = f"#earnPanel [data-sec=spark] .mini:nth-of-type({j + 1}) .cgmini"
        if j == 2:
            a.panel_scroll_to("[data-sec=spark] .mini:nth-of-type(2)", 6, 500)
        a.mini_hover(sel, [10], hold=600, label=f"走勢 {j + 1} ")
    a.cam(["#earnPanel .sec:last-child"], 6, "下一次公布日")
    a.panel_scroll_to(".sec:last-child", 120)
    a.say("下一次公布日也列好", "alarm")
    a.idle(600)
    a.settle()


def m_co(pg, a, start):
    to_cal(pg, "rep")
    m_scroll_to(pg, "#earnGrid", 120)
    sel = pg.evaluate(FIRST_CO_JS, "")
    start()
    a.cam([sel, "#earnGrid"], 6, "公司財報標籤")
    a.say("點公司，看這次財報", "point_dr_v2")
    a.click(sel, label="事件：公司財報董事會")
    a.wait(500)
    m_panel_into_view(a)
    a.cam(["#earnPanel .ph", "#earnPanel .tags", "#earnPanel .sec[data-sec]"], 6, "財報重點標籤")
    a.say("先看營收、毛利的方向", "talk_explain_v2")
    a.idle(700)
    a.cam(["#earnPanel [data-sec=rev]"], 6, "月營收趨勢")
    a.panel_scroll_to("[data-sec=rev]", 6)
    a.say("月營收＋年增，點來看", "magnifier")
    a.mini_hover("#earnPanel [data-sec=rev] .cgmini", [4, 8, 11], label="月營收")
    p = a.mini_pt("#earnPanel [data-sec=rev] .cgmini", 11)
    if p:
        a.say("再點一下，選取那個月", "face_thinking_bulb")
        a.click_pt(p[0], p[1], "月營收第 12 欄（選取）", measured_by="echarts 欄位中心")
        a.wait(900)
    a.cam(["#earnPanel [data-sec=val]"], 6, "估值位置")
    a.panel_scroll_to("[data-sec=val]", 6)
    a.say("本益比在自己歷史哪裡", "calc")
    a.idle(700)
    a.cam(["#earnPanel [data-sec=inst]"], 6, "法人籌碼")
    a.panel_scroll_to("[data-sec=inst]", 6)
    a.say("法人 20 日買賣超", "point_r_v2")
    a.mini_hover("#earnPanel [data-sec=inst] .cgmini", [5, 12, 18], label="法人")
    a.cam_view("捲動")
    a.scroll_to_el("#earnCalCard", 60, 800)
    a.cam(["#earnFilt", M_ROWS4], 6, "切到公司法說")
    a.say("法說會也標在月曆上", "calendar")
    a.click('#earnFilt button[data-v="conf"]', label="公司法說")
    a.wait(700)
    sel2 = pg.evaluate(FIRST_CO_JS, "conf")
    a.cam([sel2, "#earnGrid"], 6, "法說標籤")
    a.click(sel2, label="事件：公司自辦法說")
    a.wait(500)
    m_panel_into_view(a)
    a.cam(["#earnPanel .ph", "#earnPanel [data-sec=conf]"], 6, "這場法說")
    a.say("時間、地點、主題一次看", "face_nod_v2")
    a.idle(900)
    a.settle()


def m_end(pg, a, start):
    to_cal(pg, "fed")
    m_scroll_to(pg, "#earnCalCard", 60)
    start()
    a.cam(["#earnLegend", "#earnGrid"], 6, "總覽")
    a.say("財報、法說、FED 一頁掌握", "proud_shine")
    a.scroll(by=120, ms=1400)
    a.say("搜尋「哩股哩股」", "invite_nod")
    a.scroll(by=-120, ms=1400)
    a.settle()


D_SHOTS = {"open": d_open, "guide": d_guide, "cal": d_cal, "fed": d_fed, "co": d_co, "end": d_end}
M_SHOTS = {"open": m_open, "guide": m_guide, "cal": m_cal, "fed": m_fed, "co": m_co, "end": m_end}


def run(dev, shots, out, port):
    cfg = DEVS[dev]
    W = int(cfg["viewport"]["width"] * cfg["device_scale_factor"])
    H = int(cfg["viewport"]["height"] * cfg["device_scale_factor"])
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(C._Quiet, directory=str(C.SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}/index.html"
    site_meta = json.loads((C.SITE / "data" / "meta.json").read_text(encoding="utf-8"))
    bjs = blur_js()
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
                ctx.add_init_script(C.HIDE_B_JS)   # 法遵：B 類功能名稱不入鏡
                ctx.add_init_script(bjs)           # 法遵：個股代號／名稱模糊
                if dev == "d" and sid != "guide":   # 桌機左側導覽收成圖示列：內容區更寬
                    ctx.add_init_script("try{localStorage.setItem('tw.layout4.nav','mini')}catch(e){}")
                ctx.add_init_script(C.CURSOR_JS % ("true" if dev == "m" else "false"))
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
                pg.goto(base + "#overview", wait_until="networkidle")
                pg.wait_for_timeout(2500)
                a = A(pg, dev == "m", cfg["viewport"]["width"], cfg["viewport"]["height"])
                a.x, a.y = (900, 500) if dev == "d" else (370, 160)
                a.dsf = cfg["device_scale_factor"]
                rec = Rec(pg, W, H, a)

                def start(rec=rec, a=a, sid=sid):
                    a.rec = rec
                    a._put(a.x, a.y)
                    rec.start(out / f".tmp_{dev}_{sid}")

                try:
                    reg[sid](pg, a, start)
                    a.settle()
                    a.idle(520)   # 最後一泡：段尾交叉淡化 0.4 秒前仍要停滿
                    mp4 = out / f"{dev}_{sid}.mp4"
                    r = rec.stop(mp4)
                    content = [0, cfg["viewport"]["width"]] if sid == "guide" else pg.evaluate("() => { const e = document.querySelector('#earnCalCard'); const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
                    r.update(fabs=rec.fabs, size=[W, H], dsf=a.dsf, content_x=[round(v * a.dsf) for v in content], says=a.says, marks=a.marks, cams=rec.cams, clicks=a.targets,
                             steps=a.log, errs=errs[:5], data_date=site_meta.get("data_date"))
                    (out / f"{dev}_{sid}.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
                    miss = [s for s in a.log if "找不到" in s or "點不到" in s or "量不到" in s or "⚠" in s]
                    print(sid, r["dur"], "秒", len(a.says), "泡泡", len(a.targets), "點擊", "bad:", (r.get("bad") or [])[:3], "errs:", errs[:2], "缺:", miss[:6])
                except Exception as exc:  # noqa: BLE001
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
    ap.add_argument("--port", type=int, default=8813)
    g = ap.parse_args()
    out = Path(g.out)
    out.mkdir(parents=True, exist_ok=True)
    run(g.dev, [s for s in g.shots.split(",") if s], out, g.port)


if __name__ == "__main__":
    main()
