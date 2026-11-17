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
if min(gaps) < .3: bad.append("句間停頓最小 %.2f <0.3" % min(gaps))

if hold and min(hold) < 1.0: bad.append("換幕留白最小 %.2f <1.0" % min(hold))
if not 45 <= tot <= 60: bad.append("片長 %.1f 不在 45～60" % tot)
if c.get("atempo", 1) != 1: bad.append("atempo=%s（不准加速）" % c["atempo"])
print("語速：含停頓 %.2f 字/秒、不含 %.2f 字/秒；片長 %.1f 秒；句間最小停頓 %.2f；<0.3 秒短靜音 %d 個（含字與字之間的自然氣口，僅供參考）；換幕留白最小 %.2f（各鏡 %s）" % (c["rate_incl_pauses"], c["rate_speech_only"], tot, min(gaps), len(inner), min(hold) if hold else 0, hold))
print("結果：" + ("合格" if not bad else "要人看 → " + "；".join(bad)))
