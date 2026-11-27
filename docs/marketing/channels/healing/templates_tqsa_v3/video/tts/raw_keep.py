#!/usr/bin/env python3
"""聲音先定（2026-11-22 Andy：「修正後的影片 要馬是影片正常 旁白斷續，或是影片斷續 旁白正常，幫我處理到好」；video_logic.md 最後一節「聲音先定、畫面跟聲音」）。
原始錄音只裁頭（被念出的設定句）、裁尾（念完後的雜訊）、片頭 0.3 秒淡入；中間一刀不切、不插停頓、不拉伸。
先用 cut_take_v8.py（atempo 1.0、INNER_MAX=9 不壓句內停頓）找出每鏡在原始錄音的位置，再由本程式把成品換成「原始錄音連續一段」，
並把 cut.json 的每鏡時間改成原始錄音的時間（換幕＝句號後的自然停頓）。之後照常跑 make_segments.py → 畫面依這份時間戳排。
用法：python3 raw_keep.py <原始 wav> <cut.json（cut_take_v8 產出）> <輸出 wav>"""
import json, sys, wave, os
import numpy as np
raw, cj, out = sys.argv[1:4]
c = json.load(open(cj)); S = c["segments"]
w = wave.open(raw); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
lead = S[0]["speech_start"]                       # 成品第一個字的時間（同 cut_take_v8：LEAD＋段首預留）
off = S[0]["src"][0] - lead                        # 原始錄音裡對應成品 0 秒的位置（cut_take_v8 的 speech_start ↔ 原始 src[0]）
# 裁頭（2026-11-27 重寫：avgwage／quit 審片「片頭殘留設定句尾巴『直接說』」）：舊版只用能量找「開口」，會把設定句本身當成念稿開口；
# 現在先用 ASR 找「直接說」，再找它之後第一段 ≥0.15 秒的安靜，安靜的結尾才是念稿第一個字（head_onset.py）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from head_onset import script_onset
asrp = os.path.splitext(raw)[0] + ".asr.json"
on_info = None
if os.path.exists(asrp):
    on_info = script_onset(x, SR, json.load(open(asrp)))
if on_info:
    onset = on_info["onset"]                       # 念稿第一個字的起音（原始錄音秒數）
    off0 = off; off = onset - .04 - lead
else:                                              # 沒有 ASR 檔或找不到「直接說」：退回舊版能量法
    _h = int(SR * .01); _db = lambda t: 20 * np.log10(np.sqrt((x[int(t * SR):int(t * SR) + _h] ** 2).mean()) + 1e-9)
    onset = next((t for t in np.arange(S[0]["src"][0] - .1, S[0]["src"][0] + 1.5, .01) if _db(t) > -30 and _db(t + .03) > -30), S[0]["src"][0])
    off0 = off; off = onset - .04 - lead if onset - .04 > S[0]["src"][0] + .1 else off
tail = S[-1]["src"][1] + 0.15
a, b = int(round(off * SR)), int(round(tail * SR))
y = x[max(0, a):b].copy()
if a < 0: y = np.concatenate([np.zeros(-a, np.float32), y])
# 底噪：用 cut.json 記的「這份錄音自己的安靜段」（cut_take_v8.find_roomtone），裁頭補墊、片尾補長，不放純 0（音訊檢查：數位靜音 0）
rt = c.get("roomtone", {}).get("src")
if rt:
    room = x[int(rt[0] * SR):int(rt[1] * SR)].astype(np.float32); room = room - room.mean()
else:
    room = (np.random.default_rng(3).normal(0, 10 ** (-63 / 20), SR)).astype(np.float32)
X = int(.015 * SR)
def bed(n):
    out = np.zeros(n + len(room), np.float32); step = max(1, len(room) - X); th = np.linspace(0, np.pi / 2, X, dtype=np.float32); k = 0
    while k * step < n:
        t = room.copy(); t[:X] *= np.sin(th); t[-X:] *= np.cos(th); out[k * step:k * step + len(t)] += t; k += 1
    return out[:n]
head_pad = 0.0
if on_info:   # 裁頭起點落在「說」結束後的安靜裡；之前不夠長的部分用底噪墊（首字仍在 lead 秒）
    cut0 = max(off, on_info["sil_start"] + .04); head_pad = max(0.0, cut0 - off)
    ka = int(round(head_pad * SR))
    if ka > 0: y = np.concatenate([bed(ka), y[ka:]])
k = int(.3 * SR); y[:k] *= np.sin(np.linspace(0, np.pi / 2, k, dtype=np.float32))   # 片頭淡入（唯一允許的處理）
n = int(.08 * SR); y[-n:] *= np.cos(np.linspace(0, np.pi / 2, n, dtype=np.float32))  # 尾端 80ms 淡出＝裁尾，避免爆音
speech_len = len(y) / SR
TAILPAD = 1.0   # 旁白念完到片尾音效之間不留純 0（審片：0.3 秒 −96 dB）：旁白檔尾端接 1 秒底噪
y = np.concatenate([y, bed(int(TAILPAD * SR))])
with wave.open(out, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
NS = []
on_out = (onset - off) if on_info else None        # 念稿第一個字在成品裡的時間（lead＋0.04）
for i, s in enumerate(S):
    sp_new = s["src"][0] - off; sh = sp_new - s["speech_start"]
    if i == 0:
        sh = off0 - off                              # 全部字時間統一平移（cut.json 的時間 ＝ 原始錄音時間 − off0）
        if off != off0: sp_new = lead
    wd = [round(t + sh, 3) for t in s.get("words", [])]
    if i == 0 and on_info and wd:                    # ASR 把首字標得比真正起音早（「說」的尾音或靜音被算進首字）：首字時間不得早於真正起音
        j0 = 1 if len(wd) > 1 and str(s.get("heard", ""))[:1] in ("說", "说") else 0
        if wd[j0] < on_out:
            if j0: wd[0] = round(on_out - .02, 3)
            wd[j0] = round(on_out, 3)
    NS.append(dict(s, speech_start=round(sp_new, 3), start=round(sp_new - (s["speech_start"] - s["start"]) if i else 0.0, 3), end=round(s["end"] + sh, 3),
                   words=wd, inserts=0, ins_at=[]))
for i in range(len(NS) - 1): NS[i]["gap_after"] = round(NS[i + 1]["speech_start"] - NS[i]["end"], 3)
NS[-1]["gap_after"] = round(speech_len - NS[-1]["end"], 3)
chars = c.get("chars"); tot = speech_len - lead; sp = sum(s["end"] - s["speech_start"] for s in NS)
c.update({"segments": NS, "atempo": 1.0, "raw_keep": True, "raw_range": [round(off, 3), round(tail, 3)], "inner_cuts": [], "dur_total": round(speech_len, 3), "tail_room_pad": TAILPAD, "head_onset": on_info and {k_: round(v_, 3) for k_, v_ in on_info.items()}, "head_pad": round(head_pad, 3),
          "rate_incl_pauses": round(chars / tot, 2) if chars else c.get("rate_incl_pauses"), "rate_speech_only": round(chars / sp, 2) if chars else c.get("rate_speech_only")})
json.dump(c, open(out + ".cut.json", "w"), ensure_ascii=False, indent=1)
print("原始錄音 %.2f～%.2f 秒連續一段 → %s（%.2f 秒＋片尾底噪 %.1f 秒）；首字起音 %s；換幕自然停頓：%s" % (off, tail, out, speech_len, TAILPAD, on_info and round(onset, 3), [s["gap_after"] for s in NS[:-1]]))
