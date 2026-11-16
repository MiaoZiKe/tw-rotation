#!/usr/bin/env python3
"""談晴說礙 v8 影片產生器（2026-11-16 總編輯；範本＝結婚登記 v7）。
每篇一份規格（specs_v8.py 的 VIDEOS[名]），插圖在 v8/ill_<篇>.js（量身，不跨篇），鏡型在 video_runtime_v8.js（v8/build_runtime.py 產生）。
用法：
  python3 v8/gen_v8.py <名> [--nv]      → html/<名>.html（--nv＝無旁白版：不讀 segments.json，時長依字數估）
  node render_video.js <名>             → queue/<篇>/<out>.mp4＋封面＋overlap 報告（render_video.js 的 v6/v7 檢查對 v8 一樣開）
時間軸、字幕、旁白對齊沿用 gen_video.py 的 apply_segments（segments.json 存在就照旁白時間戳，否則照字數估）。"""
import os, sys, json, copy
B = os.path.dirname(os.path.abspath(__file__)); VD = os.path.dirname(B)
sys.path.insert(0, VD); sys.path.insert(0, B)
import gen_video as G
from specs_v8 import VIDEOS

def build(name, nv=False):
    v = copy.deepcopy(VIDEOS[name]); v["name"] = name
    v.update({"runtime": "video_runtime_v8.js", "edge60": True, "sfx": True, "paper": "file://" + os.path.join(VD, "assets", "paper_day.jpg")})
    v.setdefault("voice_lufs", -16.0); v.setdefault("outro_lufs", -12.5); v.setdefault("fps", 30)
    if nv:
        v["out"], v["cover"], v["report"] = "video_nv.mp4", "video_nv_cover.jpg", "overlap_report_nv.json"; seg = None
    else:
        seg = os.path.join(G.QUEUE, v["queue"], "segments.json")
        assert os.path.exists(seg), "沒有 segments.json（先配旁白）"
    G.apply_segments(v, seg)
    if seg:   # v8.1（動畫導演 11-16：每秒一拍像節拍器）：主體輕跳對準旁白字詞起音——1.6 秒後的字詞起音，間隔 ≥0.7 秒；兩拍相隔 >1.1 秒就補一拍（靜止段 ≤1.2 秒）
        W = {x["id"]: x.get("words", []) for x in json.load(open(seg, encoding="utf-8"))["segments"]}
        for sc in v["scenes"]:
            if sc["type"] == "outro" or not W.get(sc["id"]): continue
            d = sc["t1"] - sc["t0"]; cand = sorted(w - sc["t0"] for w in W[sc["id"]] if 1.6 <= w - sc["t0"] <= d - .25); bt = []
            for w in cand:
                if not bt or w - bt[-1] >= .7: bt.append(round(w, 3))
            full = []; prev = 1.0
            for b in bt + [d - .1]:
                while b - prev > 1.1: prev = round(prev + .9, 3); full.append(prev)
                if b < d - .2: full.append(b)
                prev = b
            sc["beats"] = full
    if nv: G.write_narration(v)
    css = ":root{" + ";".join("--%s:%s" % (k, val) for k, val in G.PAL.items()) + "}"
    ill = os.path.join(B, "ill_%s.js" % v["ill"])
    page = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:var(--bg);overflow:hidden;font-family:'Noto Sans CJK TC',sans-serif;color:var(--text)}
.abs{position:absolute}
#logo{left:96px;top:56px;height:64px}%s%s%s</style></head><body>
<img id="logo" data-o="logo" class="abs" src="file://%s">
<div id="stage"></div>
<script>const V=%s;</script>
<script src="file://%s"></script>
<script src="file://%s"></script>
</body></html>""" % (css, G.V2CSS, G.V3CSS, G.V5CSS, G.LOGO, json.dumps(v, ensure_ascii=False), ill, os.path.join(VD, "video_runtime_v8.js"))
    p = os.path.join(VD, "html", name + ".html"); open(p, "w", encoding="utf-8").write(page)
    print("時間軸：", v["timing"], "總長 %.2f 秒" % v["dur"], [(s["id"], round(s["t1"] - s["t0"], 2)) for s in v["scenes"]])
    return p

if __name__ == "__main__":
    a = sys.argv[1:]; nv = "--nv" in a; a = [x for x in a if x != "--nv"]
    for n in a: print(build(n, nv))
