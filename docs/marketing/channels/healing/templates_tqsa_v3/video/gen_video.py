#!/usr/bin/env python3
"""談晴說礙 數據短影音產生器 v0（2026-11-15，Andy：「目前這平台影片才能吸引人，所以需要以影片為主、輪播為輔助」）。
規格：1080×1920、30fps、15–30 秒、晝版；數字動畫（count-up）＋圖表生長＋字幕；LOGO 左上；每一段圖上一行出處；
頁序同輪播：發生什麼 → 資料從哪來與統計 → 數字背後（晴）→ 提問。不用「我／我們」、不放叫人做事的話。
Reels 介面安全區：上 220px、下 420px 不放重點（出處行與字幕都在 1500 以上）。
用法：python3 gen_video.py <佇列資料夾名>  → html/<名>.html；再 node render_video.js <名> → queue/<名>/video.mp4（＋cover.jpg、overlap_report_video.json）
新題目：在 VIDEOS 加一筆（scenes 由 scene 型別組成：title_rings / bars / numbers / ask），不改渲染器。
v2（快節奏＋旁白對齊）：VIDEOS 項目帶 runtime="video_runtime_v2.js"；場景型別 hook / bars / versus / ruler / card / ask / next（結構照 docs/marketing/channels/video_logic.md）。
  每段有 id 與預設 dur；queue/<資料夾>/segments.json 存在時，段長改用旁白時間戳、字幕改用旁白文字、音軌改用旁白音檔。
  旁白稿：queue/<資料夾>/narration.txt（每段一行「id｜文字」，給 TTS 用）。"""
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


# ───────── v2 快節奏（2026-11-15 Andy：「影片步調可以再快點」）─────────
# 每段 1.5–2.5 秒、硬切不淡出、數字與圖表動畫 0.4–0.6 秒、第 0 格就有標題＋大數字。
# 每段的 id 對應旁白 segments.json 的 id；有旁白時段長＝旁白時間戳（見 apply_segments）。
VIDEOS["20261116_marriage_v2"] = {
  "queue": "20261116_marriage", "out": "video_v2.mp4", "cover": "video_v2_cover.jpg", "report": "overlap_report_video_v2.json",
  "runtime": "video_runtime_v2.js", "fps": 30, "cover_t": 1.6, "asof": "2026/11/15", "edge60": True,
  # 結構照 docs/marketing/channels/video_logic.md：① s1 鉤子 → ② s2–s6 講清楚（發生什麼→大家以為 vs 數據→查證→解釋）→ ③ s7–s8 吊胃口＋下集
  # "say"＝旁白（給 TTS，也是沒有旁白時的字幕）；dur 不寫＝依旁白字數以每秒 5 字估（＋0.35 秒換氣），見 est_dur()
  "scenes": [
   {"id": "s1", "type": "hook", "title": ["10年，結婚登記", "少了近3成"], "ulw": 360,
    "big": "−29.4%", "label": "全年結婚登記對數，2016 → 2025",
    "trend": {"a": 147861, "b": 104376, "vmax": 160000, "la": "2016 年", "lb": "2025 年"},
    "tag": "已確定｜內政部統計，降幅自行計算",
    "say": "十年，結婚登記少了將近三成。", "src": "資料：內政部戶政司結婚登記 2016、2025 年"},
   {"id": "s2", "type": "bars", "stage": 1, "title": ["資料從哪來"], "tag": "官方統計｜內政部戶政司",
    "bars": [{"lab": "2016 年", "v": 147861}, {"lab": "2025 年", "v": 104376, "hi": True}], "vmax": 160000, "unit": "單位：全年結婚登記對數",
    "say": "內政部統計，二〇一六年，十四萬七千多對。", "src": "資料：內政部戶政司結婚登記 2016 年"},
   {"id": "s3", "type": "bars", "stage": 2, "title": ["資料從哪來"], "tag": "官方統計｜內政部戶政司",
    "bars": [{"lab": "2016 年", "v": 147861}, {"lab": "2025 年", "v": 104376, "hi": True}], "vmax": 160000,
    "note": "少 43,485 對", "say": "二〇二五年，只剩十萬四千多對。", "src": "資料：內政部戶政司結婚登記 2016、2025 年"},
   {"id": "s4", "type": "versus", "title": ["常說的 vs 數據"],
    "a": {"k": "常見說法（非統計）", "lines": ["年輕人", "不想結"], "foot": "說法，沒有單一統計"},
    "b": {"k": "官方統計", "lines": ["結婚", "越來越晚"], "foot": "內政部人口統計年刊"},
    "mid": "數據看得到的是「晚」，不只是「少」",
    "say": "常說是不想結；數據還看到，結婚越來越晚。", "src": "資料：內政部《2025 人口統計年刊》（2026/8）"},
   {"id": "s5", "type": "ruler", "title": ["平均初婚年齡"], "tag": "官方統計｜2025 年，內政部年刊（媒體轉述）",
    "lo": 28, "hi": 36, "pins": [{"lab": "女性", "v": 31.4}, {"lab": "男性", "v": 33.4, "hi": True}],
    "say": "平均初婚年齡，男三十三點四，女三十一點四歲。", "src": "資料：內政部《2025 人口統計年刊》（2026/8）"},
   {"id": "s6", "type": "card", "title": ["同一年的出生"], "tag": "官方統計｜內政部",
    "card": {"lab": "2025 年總生育率", "to": 0.695, "dec": 3, "ref": "0.7"},
    "say": "同一年，總生育率只有零點六九五。", "src": "資料：內政部人口統計 2025 年"},
   {"id": "s7", "type": "ask", "title": ["數字看不到的"], "tag": "還不知道｜每個人沒結、晚結的理由",
    "ask": "早點成家，還是等一等？",
    "say": "理由看不到：早點成家，還是等一等？", "src": "資料：內政部戶政司；內政部人口統計年刊"},
   {"id": "s8", "type": "next", "title": ["下一集"], "tag": "下集資料｜主計總處薪資統計（2026/9 公布）",
    "slip": "未滿 25 歲・月薪中位數", "row": "經常性薪資中位數",
    "say": "下集：剛出社會的月薪中位數。", "src": "下集資料：主計總處薪資統計（2026 年 1–7 月）"},
  ]}

# ───────── v3 素材豐富＋動畫優化（2026-11-15 Andy：「影片素材需要再豐富點」「動畫、效果等等需要優化」）─────────
# 同一題、同旁白稿與鏡頭結構（s1–s8）＋片尾卡 s9（LOGO 動畫＋卡林巴招牌音，≥3 秒）。每鏡＝量身情境插圖＋資料圖兩層；
# 背景紙紋／淡格線／光影視差；轉場用遮罩擦除、圓形展開、共用元素變形（s1 大數字飛到 s2 角落）；動畫手法見 video_runtime_v3.js 檔頭。
# 片尾卡放留言關鍵字「結婚」（2026-11-15 Andy 經主控：「放吧」；plan.md 例外條款只限影片片尾卡），s9 念稿＝念出關鍵字。
import copy as _copy
_V3 = _copy.deepcopy(VIDEOS["20261116_marriage_v2"])
_V3.update({"out": "video_v3.mp4", "cover": "video_v3_cover.jpg", "report": "overlap_report_video_v3.json", "runtime": "video_runtime_v3.js",
            "cover_t": 1.9, "paper": "file://" + os.path.join(B, "assets", "paper_day.jpg"), "sfx": True})
_sc = {s["id"]: s for s in _V3["scenes"]}
_sc["s1"]["label"] = "全年結婚登記對數"
_sc["s2"].update({"chip": "10 年 −29.4%", "morphFrom": "s1", "trans": "wipe", "unit": "單位：全年結婚登記對數"})
_sc["s3"].update({"chip": "10 年 −29.4%", "trans": "wipe", "unit": "單位：全年結婚登記對數", "note": "少 43,485 對（−29.4%）"})
_sc["s4"]["trans"] = "diag"; _sc["s5"]["trans"] = "circle"; _sc["s6"]["trans"] = "wipe"; _sc["s8"]["trans"] = "diag"
_sc["s7"].update({"trans": "up", "opt": ["早點成家", "等一等"],
  "recap": [["結婚登記（全年）", "147,861 → 104,376 對"], ["平均初婚年齡", "男 33.4・女 31.4 歲"], ["總生育率（2025）", "0.695"]]})
_V3["scenes"].append({"id": "s9", "type": "outro", "dur": 3.9, "trans": "circle", "say": "想看完整資料，留言結婚。", "keyword": "結婚",
  "slogan": "談著這一代的難，也說著晴天裡的光", "nextLine": "下一集 ▸ 剛出社會的月薪中位數", "src": "資料：內政部戶政司；內政部人口統計年刊"})
VIDEOS["20261116_marriage_v3"] = _V3

# ───────── v4 禁止慢慢放大＋素材本身動起來＋片尾 LOGO 彈入出場（2026-11-15 Andy：「不要出現圖片一直慢慢放大效果，有夠爛」「LOGO 動畫需要有吸引人的出場，配音效」）─────────
# 同題、同鏡頭結構與字幕（s1–s9）；執行期換 video_runtime_v4.js；片尾卡拉長到 5.0 秒（f0–f150：彈入→衝出→三道光→蓋印→收束光暈→標語／下一集／關鍵字）。
_V4 = _copy.deepcopy(_V3)
_V4.update({"out": "video_v4.mp4", "cover": "video_v4_cover.jpg", "report": "overlap_report_video_v4.json", "runtime": "video_runtime_v4.js", "cover_t": 1.9})
for _s in _V4["scenes"]:
    if _s["id"] == "s9": _s["dur"] = 5.0
VIDEOS["20261116_marriage_v4"] = _V4

# ───────── v5（CEO 動畫／美編兩關退件小修，見 queue/20261116_marriage/video_v4_review_*.md）─────────
_V5 = _copy.deepcopy(_V4)
_V5.update({"out": "video_v5.mp4", "cover": "video_v5_cover.jpg", "report": "overlap_report_video_v5.json", "runtime": "video_runtime_v5.js", "cover_t": 1.9, "outro_lufs": -12.5})
VIDEOS["20261116_marriage_v5"] = _V5
V5CSS = """
.tag{font-size:32px;line-height:42px}
.asof{font-size:32px;line-height:40px}
"""

# ───────── v6（v5 複審小修：鉤子大字下壓回彈、轉場 0 幀同框、s4 第二拍提前、s3 手繪圈外擴、s2 殘影、s6 軸標字級、s2／s3 底部空白收緊）─────────
_V6 = _copy.deepcopy(_V5)
_V6.update({"out": "video_v6.mp4", "cover": "video_v6_cover.jpg", "report": "overlap_report_video_v6.json", "runtime": "video_runtime_v6.js"})
VIDEOS["20261116_marriage_v6"] = _V6

# ───────── v7（Andy：「圈起來的效果很差，不喜歡那樣圈，改好看點，並且可以直接呼叫 API 完整影片」）─────────
# 拿掉所有手繪圈；有旁白（tts/tts_take.py → tts/cut_take.py → queue/<篇>/segments.json＋narration_v7.wav），每鏡長度與字幕跟著旁白走。
_V7 = _copy.deepcopy(_V6)
_V7.update({"out": "video_v7.mp4", "cover": "video_v7_cover.jpg", "report": "overlap_report_video_v7.json", "runtime": "video_runtime_v7.js", "segments": "segments.json", "voice_lufs": -16.0, "outro_lufs": -13.0})
for _s in _V7["scenes"]:
    if _s["id"] == "s3": _s["note"] = "少 43,485 對"
    if _s["id"] == "s9": _s["dur"] = 5.6   # 片尾：LOGO 出場（約 2.4 秒）做完才開口念「想看完整資料，留言結婚」，關鍵字膠囊跟著「留言」出現，之後停 ≥2 秒
VIDEOS["20261116_marriage_v7"] = _V7
V3CSS = """
.bgl{left:0;top:0;width:1080px;height:1920px}
.grid{background-image:linear-gradient(rgba(110,106,102,.07) 2px,transparent 2px),linear-gradient(90deg,rgba(110,106,102,.07) 2px,transparent 2px);background-size:72px 72px}
.layer{left:0;top:0;width:1080px;height:1920px}
.bignum{left:96px;width:888px;text-align:center;font-size:200px;line-height:220px;font-weight:700;color:var(--text);letter-spacing:-.01em}
.chip{right:96px;top:306px;font-size:38px;line-height:44px;padding:4px 18px;border-radius:999px;background:var(--lamp);color:#fff;font-weight:700;white-space:nowrap}
.flyer{width:1000px;text-align:center;font-weight:700;color:var(--text);white-space:nowrap}
#logo{z-index:5}
"""

import re as _re
def est_dur(say, rate=5.0, pause=0.35, lo=2.0):
    """沒有旁白檔時的預設時長：旁白字數（不含標點）÷ 每秒 5 字（旁白設定 4.6–5.5 字／秒的中間值）＋換氣。"""
    n = len(_re.sub(r"[，。、；：？！「」（）\s]", "", say))
    return round(max(lo, n / rate + pause), 2)

def write_narration(v):
    """旁白稿 narration.txt：每段一行「id｜文字」，給 TTS 專案用；旁白做好後產出 segments.json（id、text、start、end、audio）即可直接套。"""
    q = os.path.join(QUEUE, v["queue"]); lines = ["# %s 旁白稿（每段一行：id｜文字）。語氣照 docs/prompts/tanqing-旁白-深度報導.txt：深度報導記者、數字清楚肯定、轉折稍慢；gemini-3.8-flash-tts／Sulafat／單人；每秒約 4.6–5.5 字。" % v["queue"]]
    if v.get("narr_out", "narration.txt") is None: return
    lines += ["%s｜%s" % (s["id"], s["say"]) for s in v["scenes"] if s.get("say")]
    sep = "\n\n" if v.get("narr_para") else "\n"   # narr_para：每鏡一段，段落空行（TTS 段落停頓 0.7 秒用）
    open(os.path.join(q, "narration.txt"), "w", encoding="utf-8").write(sep.join(lines) + "\n")

def apply_segments(v, seg_path):
    """旁白對齊：segments.json＝{"audio": "narration.wav"（選填，相對於佇列資料夾）, "segments": [{"id","text","start","end"}]}。
    有對應 id 的段：t0/t1 換成旁白時間戳，字幕換成旁白文字（自動斷行）；段與段之間的空隙併給前一段（不留空畫面）；
    總長＝最後一段 end＋0.4 秒。沒有 segments.json 就用每段的 dur（預設快節奏）。"""
    sc = v["scenes"]
    if seg_path and os.path.exists(seg_path):
        sj = json.load(open(seg_path, encoding="utf-8"))
        m = {x["id"]: x for x in sj["segments"]}
        tail = [s for s in sc if not s.get("say")]; sc = [s for s in sc if s.get("say")]
        miss = [s["id"] for s in sc if s["id"] not in m]
        assert not miss, "segments.json 少了這些段：%s" % miss
        for s in sc:
            g = m[s["id"]]; s["t0"], s["t1"] = float(g["start"]), float(g["end"])
            if "speech_start" in g: s["voiceAt"] = round(float(g["speech_start"]) - float(g["start"]), 3)   # 這一鏡第幾秒開口（v7 片尾關鍵字對齊用）
            s["cap"] = s.get("capText") or g.get("text") or s.get("say", "")
        sc.sort(key=lambda s: s["t0"]); sc[0]["t0"] = 0.0
        for a, b in zip(sc, sc[1:]): a["t1"] = b["t0"]
        sc[-1]["t1"] += 0.4
        for s in tail:
            s["cap"] = ""; s["t0"] = sc[-1]["t1"]; s["t1"] = s["t0"] + s["dur"]; sc.append(s)
        v["scenes"] = sc
        if sj.get("audio"): v["audio"] = os.path.join(QUEUE, v["queue"], sj["audio"])
        v["timing"] = "narration"
    else:
        t = 0.0
        for s in sc:
            s["cap"] = s.get("capText") or s.get("say", s.get("cap", ""))
            s["t0"] = round(t, 3); t += s.get("dur") or est_dur(s.get("say", "")); s["t1"] = round(t, 3)
        v["timing"] = "default"
    fps = v.get("fps", 30); sc = v["scenes"]
    for i, s in enumerate(sc):
        if s["type"] == "outro":   # 片尾卡起點對齊整數幀（音效與畫面同一幀）；片尾卡至少 dur 秒（≥3 秒、LOGO 落定後停 ≥1 秒）
            d = max(s["t1"] - s["t0"], s.get("dur") or 0); s["t0"] = round(round(s["t0"] * fps) / fps, 4); s["t1"] = round(s["t0"] + d, 4)
            if i: sc[i - 1]["t1"] = s["t0"]
    v["dur"] = sc[-1]["t1"]
    return v

V2CSS = """
.cap{left:96px;width:888px;text-align:center;font-weight:700;color:var(--text)}
.src{left:96px;top:1806px;font-size:34px;line-height:44px;color:var(--sub);white-space:nowrap}
.foot{left:96px;top:1866px;width:888px;height:8px;border-radius:4px;background:var(--lamp);opacity:.55}
.title{left:96px;width:888px;font-weight:700;letter-spacing:.02em}
.center{text-align:center}.hint{color:var(--hint)}
.tag{left:96px;font-size:30px;line-height:40px;padding:6px 18px;border:2.5px solid var(--lamp);border-radius:999px;color:var(--text);background:var(--face3);font-weight:700;white-space:nowrap}
.asof{right:96px;top:70px;font-size:30px;line-height:38px;color:var(--sub);white-space:nowrap}
"""

def build_v2(name, seg_path=None):
    import copy
    v = copy.deepcopy(VIDEOS[name]); v["name"] = name
    seg_path = seg_path or (os.path.join(QUEUE, v["queue"], v["segments"]) if v.get("segments") else None)
    apply_segments(v, seg_path)
    write_narration(v)
    css = ":root{" + ";".join("--%s:%s" % (k, val) for k, val in PAL.items()) + "}"
    page = """<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;background:var(--bg);overflow:hidden;font-family:'Noto Sans CJK TC',sans-serif;color:var(--text)}
.abs{position:absolute}
#logo{left:96px;top:56px;height:64px}%s%s</style></head><body>
<img id="logo" data-o="logo" class="abs" src="file://%s">
<div id="stage"></div>
<script>const V=%s;</script>
<script src="file://%s"></script>
</body></html>""" % (css, V2CSS, (V3CSS + (V5CSS if v["runtime"].endswith(("v5.js", "v6.js", "v7.js")) else "")) if v["runtime"].endswith(("v3.js", "v4.js", "v5.js", "v6.js", "v7.js")) else "", LOGO, json.dumps(v, ensure_ascii=False), os.path.join(B, v["runtime"]))
    os.makedirs(os.path.join(B, "html"), exist_ok=True)
    p = os.path.join(B, "html", name + ".html"); open(p, "w", encoding="utf-8").write(page)
    print("時間軸：", v["timing"], "總長 %.2f 秒" % v["dur"], [(s["id"], round(s["t1"] - s["t0"], 2)) for s in v["scenes"]])
    return p

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
    # 用法：python3 gen_video.py <名> [--segments <segments.json>]；v2 型（有 runtime 欄位）走 build_v2
    a = sys.argv[1:]; seg = None
    if "--segments" in a: i = a.index("--segments"); seg = a[i + 1]; del a[i:i + 2]
    for n in a or list(VIDEOS):
        print(build_v2(n, seg) if VIDEOS[n].get("runtime") else build(n))
