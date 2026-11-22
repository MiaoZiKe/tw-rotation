#!/usr/bin/env python3
"""語速與停頓稽核（2026-11-17 Andy「語速太快」）：python3 v9/pace_check.py <佇列資料夾>
讀 narration.wav、narration.wav.cut.json、segments.json。輸出：含／不含停頓語速、句間最小停頓、成品裡 0.12～0.3 秒的短靜音個數、每鏡說完到換鏡的留白、總長；不合格列「要人看」。標準：句間≥0.3、段落≥0.6、留白≥1.0（落定≥1.5）、片長 45～60 秒。"""
import json, sys, os, wave
import numpy as np
q = sys.argv[1]; c = json.load(open(os.path.join(q, "narration.wav.cut.json"))); sg = json.load(open(os.path.join(q, "segments.json")))["segments"]
w = wave.open(os.path.join(q, "narration.wav")); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
hop = int(SR * .01); n = len(x) // hop; db = 20 * np.log10(np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(n)])); v = db > max(-48, db.max() - 40)
runs = []; i = 0
while i < n:
    if not v[i]:
        j = i
        while j < n and not v[j]: j += 1
        runs.append((i / 100, (j - i) / 100)); i = j
    else: i += 1
inner = [d for t0, d in runs if .12 <= d < .3 and t0 > .3]
gaps = [s["gap_after"] for s in c["segments"][:-1]]
hold = [round(sg[i + 1]["start"] - c["segments"][i]["end"], 2) for i in range(len(sg) - 2)]   # 最後一鏡（片尾）前的鏡頭銜接另有規則，不算
tot = c["dur_total"]; bad = []
# 句內斷點（2026-11-21 規則 29）：每段 speech_start～最後一個字之前，≥0.15 秒且 < −80 dB 的全靜音，必須落在「念稿逗號／句號且與 ASR 逐字對上」的詞間交界；否則＝斷在詞中間（斷斷續續）。
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tts"))
from punct_align import punct_boundaries
asr = json.load(open(os.path.join(q, "narration_take.asr.json"))); AW = [(a["w"].strip(), a["s"], a["e"]) for a in asr]
hi = int(SR * .01); dbs = db   # 10ms 一格
sil = []; i = 0
while i < n:
    if db[i] < -80:
        j = i
        while j < n and db[j] < -80: j += 1
        if j - i >= 15: sil.append((i / 100, j / 100))
        i = j
    else: i += 1
breaks = []
for sgm in c["segments"]:
    a_, b_ = sgm["src"]; ws = [w_ for w_ in AW if w_[1] >= a_ - .05 and w_[2] <= b_ + .1 and w_[0]]
    wo = sgm["words"]
    if len(ws) < 2 or len(wo) != len(ws): continue
    ok = punct_boundaries(sgm["text"], [w_[0] for w_ in ws])
    for t0, t1 in sil:
        if t0 < sgm["speech_start"] + .02 or t0 >= wo[-1] - .02: continue     # 段首前導與最後一字之後（段尾／句間停頓）不算
        if not (wo[0] - .02 <= t0): continue
        if any(wo[k] - .1 <= t0 <= wo[k + 1] + .1 for k in ok if k + 1 < len(wo)): continue   # 只看靜音「起點」落在對位的詞間交界（ASR 詞起點常漂到靜音裡，不看終點）
        k = max([k for k in range(len(wo)) if wo[k] <= t0], default=0)
        breaks.append("%s %.2f–%.2f（「%s｜%s」之間）" % (sgm["id"], t0, t1, ws[k][0], ws[k + 1][0] if k + 1 < len(ws) else ""))
if breaks: bad.append("句內斷點 %d 處：%s" % (len(breaks), "；".join(breaks)))
if min(gaps) < .3: bad.append("句間停頓最小 %.2f <0.3" % min(gaps))

if c.get("newrule"):   # 2026-11-22 四道驗證：換幕停頓 0.6～0.8（取代「留白 ≥1.0」），句內補停頓 0
    _sg = float(c.get("scene_gap", .7))   # 2026-11-22 晚：範圍跟著 scene_gap（±0.2）
    if any(not _sg - .2 <= g_ + .09 <= _sg + .15 for g_ in gaps): bad.append("換幕停頓不在 %.2f～%.2f：%s" % (_sg - .2, _sg + .15, [round(g_ + .09, 2) for g_ in gaps]))
    if any(s_.get("inserts") for s_ in c["segments"]): bad.append("句內插了停頓")
elif hold and min(hold) < 1.0: bad.append("換幕留白最小 %.2f <1.0" % min(hold))
if not (38 if c.get("newrule") else 45) <= tot <= 60: bad.append("片長 %.1f 不在 45～60" % tot)   # 新規則旁白本身約 40～45 秒，成片含片尾卡另算
if c.get("atempo", 1) != 1: bad.append("atempo=%s（不准加速）" % c["atempo"])
print("語速：含停頓 %.2f 字/秒、不含 %.2f 字/秒；片長 %.1f 秒；句間最小停頓 %.2f；<0.3 秒短靜音 %d 個（含字與字之間的自然氣口，僅供參考）；換幕留白最小 %.2f（各鏡 %s）" % (c["rate_incl_pauses"], c["rate_speech_only"], tot, min(gaps), len(inner), min(hold) if hold else 0, hold))
print("句內斷點：%d 處%s" % (len(breaks), "（" + "；".join(breaks) + "）" if breaks else ""))
print("結果：" + ("合格" if not bad else "要人看 → " + "；".join(bad)))
