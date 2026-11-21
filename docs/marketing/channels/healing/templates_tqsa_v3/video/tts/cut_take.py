#!/usr/bin/env python3
"""把一次念完的原始旁白切成每鏡一段，產出成品旁白與 segments.json。
1. 本機語音辨識（faster-whisper，逐字時間戳；不花 API 請求）找出「直接說」之後念稿的第一個字，以及每鏡第一個字（錨點）。
2. 用 10 毫秒能量找靜音：念稿起點＝設定句之後那段靜音的結尾（第一個字的起音），往前留 0.2 秒（voiceLeadIn），起音不切；
   每鏡分界＝錨點前後那段最長的靜音，切在靜音裡（不切到字）。
3. 每段原音不加工（可選 atempo，倍率 ≤1.15），段與段之間的停頓沿用原錄音、但上限 MAXGAP 秒（不拖）。
用法：python3 cut_take.py <原始 wav> <asr.json> <佇列資料夾> <輸出 wav> [atempo] [maxgap]"""
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
# 錨點：設定句結尾「直接說」之後，依序找每鏡第一個詞
ANCH = {"s1": ("十",), "s2": ("內",), "s3": ("2025", "二〇二五", "二零二五", "=20"), "s4": ("常",), "s5": ("平",), "s6": ("同",), "s7": ("理",), "s8": ("下",), "s9": ("想",)}   # 「=xx」＝整個詞完全相同（2016 也以 20 開頭，不能用前綴）
hit = lambda ww, keys: any((ww == k[1:]) if k.startswith("=") else ww.startswith(k) for k in keys)
k0 = max(i for i, (ww, s, e) in enumerate(words) if "直接" in ww)
starts = []; k = k0 + 1
for sid in ids:
    while not hit(words[k][0], ANCH[sid]): k += 1
    starts.append(words[k][1]); k += 1
end_word = words[-1][2]
def runs_in(t0, t1):
    a, b = int(t0 * 100), int(t1 * 100); r = []; i = a
    while i < b:
        if not voiced[i]:
            j = i
            while j < n and not voiced[j]: j += 1
            r.append((i, j)); i = j
        else: i += 1
    return r
segs = []
# 念稿起點：「說」之後到第一個字錨點之間最長的靜音，起點＝靜音結尾
r = max(runs_in(words[k0][2] - .1, starts[0] + .3), key=lambda z: z[1] - z[0]); on0 = r[1] / 100
bounds = []
for st in starts[1:]:
    rr = runs_in(st - .8, st + .3); r = max(rr, key=lambda z: z[1] - z[0]); bounds.append((r[0] / 100, r[1] / 100))
# 念稿結尾：最後一個字（辨識時間戳）所在那段有聲的結尾；之後的聲音不收（2026-11-15 實測：模型在檔尾留了 0.2 秒滿格雜訊爆音）
le = int((words[-1][2] - .05) * 100)
while le < n and voiced[le]: le += 1
last = le / 100 + .01
tail_noise = [round(i / 100, 2) for i in range(le, n) if voiced[i]]
pieces = []
for i, sid in enumerate(ids):
    s = on0 if i == 0 else bounds[i - 1][1]; e = bounds[i][0] if i < len(bounds) else last
    gap = (bounds[i][1] - bounds[i][0]) if i < len(bounds) else 0
    pieces.append({"id": sid, "text": texts[i], "src_start": round(s, 3), "src_end": round(e, 3), "src_gap_after": round(gap, 3)})
# 組成品：每段前留 30ms、後留 60ms（都落在靜音裡），可選 atempo；段間停頓＝min(原停頓/F, MAXGAP)
def seg_audio(a, b):
    y = x[int(max(0, a - .03) * SR):int((b + .06) * SR)]
    if abs(F - 1) < 1e-3: return y
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", "atempo=%.4f" % F, "-f", "f32le", "-"], input=y.tobytes(), capture_output=True).stdout
    return np.frombuffer(p, np.float32)
outv = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD; segj = []
for i, p in enumerate(pieces):
    y = seg_audio(p["src_start"], p["src_end"]); st = t; t += len(y) / SR; outv.append(y)
    g = min(p["src_gap_after"] / F, MAXGAP) if i < len(pieces) - 1 else .15
    if i == len(pieces) - 2: g = max(g, float(os.environ.get("PRE_LAST", "0")))   # 片尾那句前的停頓（LOGO 出場時不講話）
    g = max(0, g - .09 / F); outv.append(np.zeros(int(g * SR), np.float32))
    segj.append({"id": p["id"], "text": p["text"], "start": round(st if i else 0.0, 3), "speech_start": round(st + .03 / F, 3), "end": round(t, 3), "src": [p["src_start"], p["src_end"]], "gap_after": round(g, 3)}); t += g
y = np.concatenate(outv)
with wave.open(out, "wb") as w2: w2.setnchannels(1); w2.setsampwidth(2); w2.setframerate(SR); w2.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
chars = sum(len(re.sub(r"[，。、；：？！「」（）\s]", "", p["text"])) for p in pieces)
speech = sum(s["end"] - s["speech_start"] for s in segj); total = len(y) / SR - LEAD
rep = {"source": os.path.basename(raw), "tail_noise_dropped": (tail_noise[0], tail_noise[-1]) if tail_noise else None, "preamble_cut_sec": round(on0 - LEAD, 3), "narration_onset_in_raw": on0, "voiceLeadIn": LEAD, "atempo": F, "maxgap": MAXGAP, "chars": chars,
       "dur_total": round(total, 2), "rate_incl_pauses": round(chars / total, 2), "rate_speech_only": round(chars / speech, 2), "segments": segj}
json.dump(rep, open(out + ".cut.json", "w"), ensure_ascii=False, indent=1)
print("設定句切掉 %.2f 秒；念稿 %d 字、%.2f 秒（不含開頭 0.2 秒）→ 含停頓 %.2f 字/秒、扣停頓 %.2f 字/秒" % (on0 - LEAD, chars, total, chars / total, chars / speech))
for s in segj: print(s["id"], s["start"], s["end"], s["text"])
