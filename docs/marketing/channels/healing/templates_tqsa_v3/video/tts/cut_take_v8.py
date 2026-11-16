#!/usr/bin/env python3
"""v8 切段（通用版，不再寫死每篇的錨點字）：一次念完的原始旁白 → 切掉被念出的設定句與尾端雜訊 → 每鏡一段 → 成品 wav＋.cut.json（make_segments.py 接著產 segments.json）。
1. 設定句結尾：ASR 找「直接」那個詞之後的最長靜音，念稿起點＝靜音結尾（往前留 0.2 秒，起音不切）。
2. 每鏡分界：在念稿範圍內找所有 ≥0.12 秒的靜音；依每段字數算出預期分界時間，用動態規劃挑出依序、最接近預期、且越長越好的靜音當分界（切在靜音裡，不切字）。
3. 核對：每段範圍內的 ASR 文字印出來，人工對照念稿（數字寫法不同不算錯）。
4. 念稿結尾：最後一個 ASR 字所在的有聲段結尾，之後的聲音（模型尾端雜訊）不收。
用法：python3 cut_take_v8.py <原始 wav> <asr.json> <佇列資料夾> <輸出 wav> [atempo] [maxgap]（環境變數 PRE_LAST＝片尾那句前的停頓秒數）"""
import json, sys, wave, re, subprocess, os
import numpy as np
raw, asrp, q, out = sys.argv[1:5]; F = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0; MAXGAP = float(sys.argv[6]) if len(sys.argv) > 6 else 0.32
LEAD = 0.2
w = wave.open(raw); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
hop = int(SR * .01); n = len(x) // hop
rms = np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(n)]); db = 20 * np.log10(rms)
thr = max(-48.0, db.max() - 40); voiced = db > thr
W = json.load(open(asrp)); words = [(a["w"].strip(), a["s"], a["e"]) for a in W]
lines = [l.split("｜", 1) for l in open(os.path.join(q, "narration.txt"), encoding="utf-8") if "｜" in l and not l.startswith("#")]
ids = [i for i, _ in lines]; texts = [t.strip() for _, t in lines]
cc = lambda s: len(re.sub(r"[，。、；：？！「」（）\s]", "", s))
def runs_in(t0, t1, mn=0):
    a, b = int(max(0, t0) * 100), int(min(n / 100, t1) * 100); r = []; i = a
    while i < b:
        if not voiced[i]:
            j = i
            while j < n and not voiced[j]: j += 1
            if j - i >= mn: r.append((i, j))
            i = j
        else: i += 1
    return r
k0 = max(i for i, (ww, s, e) in enumerate(words) if "直接" in ww)
r = max(runs_in(words[k0][2] - .1, words[k0][2] + 2.5), key=lambda z: z[1] - z[0]); on0 = r[1] / 100
le = int((words[-1][2] - .05) * 100)
while le < n and voiced[le]: le += 1
last = le / 100 + .01; tail_noise = [round(i / 100, 2) for i in range(le, n) if voiced[i]]
# 候選靜音（≥0.12 秒）與預期分界
cand = [(a / 100, b / 100) for a, b in runs_in(on0 + .3, last - .3, 12)]
ch = [cc(t) for t in texts]; tot = sum(ch); exp = []; acc = 0
for c in ch[:-1]: acc += c; exp.append(on0 + (last - on0) * acc / tot)
K, M = len(exp), len(cand)
INF = 1e9; cost = [[INF] * M for _ in range(K)]; back = [[-1] * M for _ in range(K)]
def c1(k, m): a, b = cand[m]; L = b - a; return abs((a + b) / 2 - exp[k]) - 1.2 * min(L, .6)
for m in range(M): cost[0][m] = c1(0, m)
for k in range(1, K):
    best, bi = INF, -1
    for m in range(M):
        if m - 1 >= 0 and cost[k - 1][m - 1] < best: best, bi = cost[k - 1][m - 1], m - 1
        if best < INF: cost[k][m] = best + c1(k, m); back[k][m] = bi
m = min(range(M), key=lambda j: cost[K - 1][j]); pick = [m]
for k in range(K - 1, 0, -1): m = back[k][m]; pick.append(m)
bounds = [cand[i] for i in reversed(pick)]
pieces = []
for i, sid in enumerate(ids):
    s = on0 if i == 0 else bounds[i - 1][1]; e = bounds[i][0] if i < len(bounds) else last
    gap = (bounds[i][1] - bounds[i][0]) if i < len(bounds) else 0
    heard = "".join(ww for ww, a, b in words if a >= s - .05 and b <= e + .1)
    pieces.append({"id": sid, "text": texts[i], "heard": heard, "src_start": round(s, 3), "src_end": round(e, 3), "src_gap_after": round(gap, 3)})
def seg_audio(a, b):
    y = x[int(max(0, a - .03) * SR):int((b + .06) * SR)]
    if abs(F - 1) < 1e-3: return y
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", "atempo=%.4f" % F, "-f", "f32le", "-"], input=y.tobytes(), capture_output=True).stdout
    return np.frombuffer(p, np.float32)
outv = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD; segj = []
for i, p in enumerate(pieces):
    y = seg_audio(p["src_start"], p["src_end"]); st = t; t += len(y) / SR; outv.append(y)
    g = min(p["src_gap_after"] / F, MAXGAP) if i < len(pieces) - 1 else .15
    if i == len(pieces) - 2: g = max(g, float(os.environ.get("PRE_LAST", "0")))
    g = max(0, g - .09 / F); outv.append(np.zeros(int(g * SR), np.float32))
    wo = [round(st + (a - p["src_start"]) / F, 3) for ww, a, b in words if a >= p["src_start"] - .05 and b <= p["src_end"] + .1 and ww.strip()]   # 每個字詞在成品裡的起音時間（字幕／重拍對準旁白用）
    segj.append({"id": p["id"], "text": p["text"], "words": wo, "heard": p["heard"], "start": round(st if i else 0.0, 3), "speech_start": round(st + .03 / F, 3), "end": round(t, 3), "src": [p["src_start"], p["src_end"]], "gap_after": round(g, 3)}); t += g
y = np.concatenate(outv)
with wave.open(out, "wb") as w2: w2.setnchannels(1); w2.setsampwidth(2); w2.setframerate(SR); w2.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
chars = sum(ch); speech = sum(s["end"] - s["speech_start"] for s in segj); total = len(y) / SR - LEAD
rep = {"source": os.path.basename(raw), "tail_noise_dropped": (tail_noise[0], tail_noise[-1]) if tail_noise else None, "preamble_cut_sec": round(on0 - LEAD, 3), "narration_onset_in_raw": on0, "voiceLeadIn": LEAD, "atempo": F, "maxgap": MAXGAP, "chars": chars,
       "dur_total": round(total, 2), "rate_incl_pauses": round(chars / total, 2), "rate_speech_only": round(chars / speech, 2), "segments": segj}
json.dump(rep, open(out + ".cut.json", "w"), ensure_ascii=False, indent=1)
print("設定句切掉 %.2f 秒；念稿 %d 字、%.2f 秒 → 含停頓 %.2f 字/秒、扣停頓 %.2f 字/秒" % (on0 - LEAD, chars, total, chars / total, chars / speech))
for s in segj: print(s["id"], s["start"], s["end"], s["text"], "｜聽到：", s["heard"])
