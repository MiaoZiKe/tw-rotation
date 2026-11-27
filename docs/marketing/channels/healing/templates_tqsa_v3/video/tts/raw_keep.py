#!/usr/bin/env python3
"""聲音先定（2026-11-22 Andy：「修正後的影片 要馬是影片正常 旁白斷續，或是影片斷續 旁白正常，幫我處理到好」；video_logic.md 最後一節「聲音先定、畫面跟聲音」）。
原始錄音只裁頭（被念出的設定句）、裁尾（念完後的雜訊）、片頭 0.3 秒淡入；中間一刀不切、不插停頓、不拉伸。
先用 cut_take_v8.py（atempo 1.0、INNER_MAX=9 不壓句內停頓）找出每鏡在原始錄音的位置，再由本程式把成品換成「原始錄音連續一段」，
並把 cut.json 的每鏡時間改成原始錄音的時間（換幕＝句號後的自然停頓）。之後照常跑 make_segments.py → 畫面依這份時間戳排。
用法：python3 raw_keep.py <原始 wav> <cut.json（cut_take_v8 產出）> <輸出 wav>"""
import json, sys, wave
import numpy as np
raw, cj, out = sys.argv[1:4]
c = json.load(open(cj)); S = c["segments"]
w = wave.open(raw); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
lead = S[0]["speech_start"]                       # 成品第一個字的時間（同 cut_take_v8：LEAD＋段首預留）
off = S[0]["src"][0] - lead                        # 原始錄音裡對應成品 0 秒的位置（cut_take_v8 的 speech_start ↔ 原始 src[0]）
# 裁頭校正（2026-11-22 quit：ASR 把第一個字標早了 0.5 秒，片頭留 1 秒空白＋設定句尾音）：用能量找真正開口（≥ −30 dB），首字固定在 lead 秒
_h = int(SR * .01); _db = lambda t: 20 * np.log10(np.sqrt((x[int(t * SR):int(t * SR) + _h] ** 2).mean()) + 1e-9)
onset = next((t for t in np.arange(S[0]["src"][0] - .1, S[0]["src"][0] + 1.5, .01) if _db(t) > -30 and _db(t + .03) > -30), S[0]["src"][0])
off0 = off; off = onset - .04 - lead if onset - .04 > S[0]["src"][0] + .1 else off
tail = S[-1]["src"][1] + 0.15
a, b = int(round(off * SR)), int(round(tail * SR))
y = x[max(0, a):b].copy()
if a < 0: y = np.concatenate([np.zeros(-a, np.float32), y])
k = int(.3 * SR); y[:k] *= np.sin(np.linspace(0, np.pi / 2, k, dtype=np.float32))   # 片頭淡入（唯一允許的處理）
n = int(.08 * SR); y[-n:] *= np.cos(np.linspace(0, np.pi / 2, n, dtype=np.float32))  # 尾端 80ms 淡出＝裁尾，避免爆音
with wave.open(out, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
NS = []
for i, s in enumerate(S):
    sp_new = s["src"][0] - off; sh = sp_new - s["speech_start"]
    if i == 0 and off != off0: sp_new = lead; sh = (s["src"][0] - off) - s["speech_start"]   # 首鏡開口＝校正後的 lead；字的時間照原始位置平移
    NS.append(dict(s, speech_start=round(sp_new, 3), start=round(sp_new - (s["speech_start"] - s["start"]) if i else 0.0, 3), end=round(s["end"] + sh, 3),
                   words=[round(t + sh, 3) for t in s.get("words", [])], inserts=0, ins_at=[]))
for i in range(len(NS) - 1): NS[i]["gap_after"] = round(NS[i + 1]["speech_start"] - NS[i]["end"], 3)
NS[-1]["gap_after"] = round(len(y) / SR - NS[-1]["end"], 3)
chars = c.get("chars"); tot = len(y) / SR - lead; sp = sum(s["end"] - s["speech_start"] for s in NS)
c.update({"segments": NS, "atempo": 1.0, "raw_keep": True, "raw_range": [round(off, 3), round(tail, 3)], "inner_cuts": [], "dur_total": round(len(y) / SR, 3),
          "rate_incl_pauses": round(chars / tot, 2) if chars else c.get("rate_incl_pauses"), "rate_speech_only": round(chars / sp, 2) if chars else c.get("rate_speech_only")})
json.dump(c, open(out + ".cut.json", "w"), ensure_ascii=False, indent=1)
print("原始錄音 %.2f～%.2f 秒連續一段 → %s（%.2f 秒）；換幕自然停頓：%s" % (off, tail, out, len(y) / SR, [s["gap_after"] for s in NS[:-1]]))
