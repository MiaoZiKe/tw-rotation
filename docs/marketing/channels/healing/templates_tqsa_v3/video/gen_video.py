#!/usr/bin/env python3
"""談晴說礙 數據短影音產生器 v0（2026-11-15，Andy：「目前這平台影片才能吸引人，所以需要以影片為主、輪播為輔助」）。
規格：1080×1920、30fps、15–30 秒、晝版；數字動畫（count-up）＋圖表生長＋字幕；LOGO 左上；每一段圖上一行出處；
頁序同輪播：發生什麼 → 資料從哪來與統計 → 數字背後（晴）→ 提問。不用「我／我們」、不放叫人做事的話。
Reels 介面安全區：上 220px、下 420px 不放重點（出處行與字幕都在 1500 以上）。
用法：python3 gen_video.py <佇列資料夾名>  → html/<名>.html；再 node render_video.js <名> → queue/<名>/video.mp4（＋cover.jpg、overlap_report_video.json）
新題目：在 VIDEOS 加一筆（scenes 由 scene 型別組成：title_rings / bars / numbers / ask），不改渲染器。"""
import json, os, sys, html
B = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(B, "..", "src")
PAL = json.load(open(os.path.join(SRC, "palette.json"), encoding="utf-8"))["晝版"]
LOGO = os.path.abspath(os.path.join(SRC, "logo_tight_晝版.png"))
QUEUE = os.path.abspath(os.path.join(B, "..", "..", "queue"))

VIDEOS = {
 "20261116_marriage": {
  "fps": 30, "dur": 24.0,
  "scenes": [
   {"type": "title_rings", "t0": 0, "t1": 6.2,
    "title": ["10年來，", "結婚登記少了近3成"],
    "n": 10, "fade": 3, "big": {"from": 0, "to": 29.4, "fmt": "−{:.1f}%", "label": "2016 → 2025 結婚登記對數"},
    "sub": "2016 年到 2025 年，全年結婚登記對數的變化",
    "src": "資料：內政部戶政司結婚登記 2016、2025 年"},
   {"type": "bars", "t0": 6.2, "t1": 14.2,
    "title": ["資料從哪來"], "lead": "內政部戶政司・全年結婚登記",
    "bars": [{"lab": "2016 年", "v": 147861}, {"lab": "2025 年", "v": 104376, "hi": True}], "vmax": 160000,
    "note": "少 43,485 對（−29.4%）",
    "sub": "統計單位是「結婚登記對數」，不是結婚人數",
    "src": "資料：內政部戶政司結婚登記 2016、2025 年"},
   {"type": "numbers", "t0": 14.2, "t1": 20.6,
    "title": ["數字背後"],
    "cards": [{"lab": "2025 年總生育率", "to": 0.695, "dec": 3, "unit": ""}, {"lab": "2026 年新生兒推估", "to": 9.4, "dec": 1, "unit": " 萬人", "pre": "約 "}],
    "sub": "結婚與出生一起往下，正發生在這一代身上",
    "src": "資料：內政部；國發會人口推估（2026/8）"},
   {"type": "ask", "t0": 20.6, "t1": 24.0,
    "ask": "成家這件事，", "ask2": "離日常多遠？",
    "sub": "", "src": "資料：內政部戶政司；國發會"},
  ]},
}

def build(name):
    v = VIDEOS[name]
    css = ":root{" + ";".join("--%s:%s" % (k, val) for k, val in PAL.items()) + "}"
    page = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:var(--bg);overflow:hidden;font-family:'Noto Sans CJK TC',sans-serif;color:var(--text)}
.abs{position:absolute}
#logo{left:96px;top:236px;height:64px}
.src{left:96px;top:1452px;font-size:32px;line-height:44px;color:var(--sub);white-space:nowrap}
.sub{left:96px;width:888px;top:1360px;font-size:38px;line-height:52px;color:var(--text);text-align:center;font-weight:700}
.title{left:96px;width:888px;font-weight:700;letter-spacing:.02em}
</style></head><body>
<img id="logo" data-o="logo" class="abs" src="file://%s">
<div id="stage"></div>
<script>const V=%s;</script>
<script src="file://%s"></script>
</body></html>""" % (css, LOGO, json.dumps(v, ensure_ascii=False), os.path.join(B, "video_runtime.js"))
    os.makedirs(os.path.join(B, "html"), exist_ok=True)
    p = os.path.join(B, "html", name + ".html"); open(p, "w", encoding="utf-8").write(page)
    return p

if __name__ == "__main__":
    for n in sys.argv[1:] or list(VIDEOS):
        print(build(n))
