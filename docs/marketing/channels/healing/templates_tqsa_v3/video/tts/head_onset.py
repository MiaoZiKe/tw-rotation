#!/usr/bin/env python3
"""找「念稿第一個字」在原始錄音裡的真正起音（2026-11-27 avgwage／quit 審片：成品開頭殘留設定句尾巴「直接說」）。
ASR 的逐字時間戳在設定句後常漂（首字時間落在「說」或靜音裡，差 0.3～0.6 秒），不能直接拿來裁頭。
做法：ASR 找最後一個「直接」→ 它起音之後第一段 ≥0.15 秒的安靜（每 10ms 能量 < −38 dBFS；設定句「說」的尾音落在這之前）→ 安靜的結尾＝念稿第一個字起音。
回傳 {"sil_start","onset"}（原始錄音秒數）；找不到「直接」或安靜段回 None（呼叫端退回舊法並印警告）。
用法（單獨看）：python3 head_onset.py <原始 wav> <asr.json>"""
import json, sys, wave
import numpy as np

def script_onset(x, SR, asr, thr_db=-38.0, min_sil=.15):
    hop = int(SR * .01); n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop).astype(np.float64) ** 2).mean(1)) + 1e-9)
    ks = [i for i, a in enumerate(asr) if "直接" in a["w"]]
    if not ks: print("警告：ASR 找不到「直接」，無法定位設定句結尾", file=sys.stderr); return None
    t0 = asr[ks[-1]]["s"]; quiet = db < thr_db
    i = int(max(0, t0 + .25) * 100)   # ASR 的「直接」起音常比真的早 0.15～0.2 秒，往後 0.25 秒才確定在「直接說」裡面，避開它前面的安靜
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if j - i >= int(min_sil * 100) and j < n: return {"sil_start": i / 100, "onset": j / 100}
            i = j
        else: i += 1
    print("警告：「直接」之後找不到 ≥%.2f 秒的安靜" % min_sil, file=sys.stderr); return None

if __name__ == "__main__":
    w = wave.open(sys.argv[1]); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
    print(script_onset(x, SR, json.load(open(sys.argv[2]))))
