#!/usr/bin/env python3
"""v8 切段（通用版，不再寫死每篇的錨點字）：一次念完的原始旁白 → 切掉被念出的設定句與尾端雜訊 → 每鏡一段 → 成品 wav＋.cut.json（make_segments.py 接著產 segments.json）。
1. 設定句結尾：ASR 找「直接」那個詞之後的最長靜音，念稿起點＝靜音結尾（往前留 0.2 秒，起音不切）。
2. 每鏡分界：在念稿範圍內找所有 ≥0.12 秒的靜音；依每段字數算出預期分界時間，用動態規劃挑出依序、最接近預期、且越長越好的靜音當分界（切在靜音裡，不切字）。
2b.（2026-11-16 修）分界只能選「靜音之後的第一個辨識字＝下一行第一個字」的那段靜音（ASR 是簡體且可能少一兩字，用簡繁小對照＋前 4 字位置比對）；比不到的靜音（逗號後）重罰，整個分界都比不到才退回舊邏輯並印警告。環境變數 BOUNDS="47.3,51.6,,60.0" 可直接指定每個分界在原始錄音的秒數（空白＝不指定），作為保底。
3. 核對：每段範圍內的 ASR 文字印出來，人工對照念稿（數字寫法不同不算錯）。
4. 念稿結尾：最後一個 ASR 字所在的有聲段結尾，之後的聲音（模型尾端雜訊）不收。
5. 停頓（2026-11-16 Andy 新規，剪輯插靜音、不放慢語速）：句間實際停頓下限 MINGAP（預設 0.3 秒），原本自然停頓較長的保留到 MAXGAP（預設 0.45 秒）；narration.txt 有空行處＝段落分界，停頓固定 PARA（預設 0.7 秒）。沒有空行＝全部同一段。字幕／鏡頭時序（make_segments.py → gen_v8.py）讀的是切完後的時間點，自動跟著新停頓走。
用法：python3 cut_take_v8.py <原始 wav> <asr.json> <佇列資料夾> <輸出 wav> [atempo] [maxgap=0.45] [mingap=0.30] [para=0.70]（環境變數 PRE_LAST＝片尾那句前的停頓秒數）"""
import json, sys, wave, re, subprocess, os
import numpy as np
raw, asrp, q, out = sys.argv[1:5]; F = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0; MAXGAP = float(sys.argv[6]) if len(sys.argv) > 6 else 0.45
MINGAP = float(sys.argv[7]) if len(sys.argv) > 7 else 0.30; PARA = float(sys.argv[8]) if len(sys.argv) > 8 else 0.70
LEAD = 0.2
w = wave.open(raw); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
hop = int(SR * .01); n = len(x) // hop
rms = np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(n)]); db = 20 * np.log10(rms)
thr = max(-48.0, db.max() - 40); voiced = db > thr
W = json.load(open(asrp)); words = [(a["w"].strip(), a["s"], a["e"]) for a in W]
lines = []; para_after = []   # para_after[i]＝第 i 句後面有空行（段落分界）
for l in open(os.path.join(q, "narration.txt"), encoding="utf-8"):
    if "｜" in l and not l.startswith("#"): lines.append(l.split("｜", 1)); para_after.append(False)
    elif not l.strip() and lines: para_after[-1] = True
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
# 簡→繁小對照（ASR 輸出簡體；只列常見字，沒列到的字退成「同字才算對」）
S2T = dict(zip("这买内统计负担级过体户总资贷还价来为让们说话时间开关长发动经济务观点现实后场产业对车电会发联结约论题际环项报导记错须从样别两种应该钱让儿虽无节数据备选",
               "這買內統計負擔級過體戶總資貸還價來為讓們說話時間開關長發動經濟務觀點現實後場產業對車電會發聯結約論題際環項報導記錯須從樣別兩種應該錢讓兒雖無節數據備選"))
def norm(t): return "".join(S2T.get(c, c) for c in re.sub(r"[，。、；：？！「」（）\s\d%.]", "", t))
def match_frac(m, k):
    # 候選靜音 m 之後的辨識字，對下一行（第 k+1 行）開頭的符合比例；允許 ASR 少掉第一個字（要求其餘全對）
    a_, b = cand[m]; nxt = "".join(norm(ww) for ww, s0, e0 in words if e0 > (a_ + b) / 2 + .02)[:6]   # ASR 字詞時間會漂（字起點常落在靜音裡），所以用「字結尾在靜音中點之後」當「靜音後的字」
    ln = norm(texts[k + 1])[:4]
    if not ln or not nxt: return 0.0
    n0 = min(4, len(ln)); f0 = sum(1 for i in range(min(n0, len(nxt))) if nxt[i] == ln[i]) / n0
    f1 = 0.0
    if len(ln) >= 3: n1 = min(3, len(ln) - 1); f1 = (1.0 if all(i < len(nxt) and nxt[i] == ln[i + 1] for i in range(n1)) else 0.0) * .9
    return max(f0, f1)
frac = [[match_frac(m, k) for m in range(M)] for k in range(K)]
force = [None] * K
if os.environ.get("BOUNDS"):
    for k, v in enumerate(os.environ["BOUNDS"].split(",")[:K]):
        if v.strip(): force[k] = float(v)
INF = 1e9; cost = [[INF] * M for _ in range(K)]; back = [[-1] * M for _ in range(K)]
def c1(k, m):
    a, b = cand[m]; L = b - a
    if force[k] is not None: return abs((a + b) / 2 - force[k]) * 10 - 1.2 * min(L, .6)
    return abs((a + b) / 2 - exp[k]) - (3.0 if frac[k][m] >= .5 else 1.2) * min(L, .6) + 8 * (1 - frac[k][m])   # 比得到下一行開頭的靜音：越長越好（避開靜音旁邊的小氣音）
for m in range(M): cost[0][m] = c1(0, m)
for k in range(1, K):
    best, bi = INF, -1
    for m in range(M):
        if m - 1 >= 0 and cost[k - 1][m - 1] < best: best, bi = cost[k - 1][m - 1], m - 1
        if best < INF: cost[k][m] = best + c1(k, m); back[k][m] = bi
m = min(range(M), key=lambda j: cost[K - 1][j]); pick = [m]
for k in range(K - 1, 0, -1): m = back[k][m]; pick.append(m)
bounds = [cand[i] for i in reversed(pick)]
pickm = list(reversed(pick))
for k in range(K):
    f = frac[k][pickm[k]]
    if force[k] is not None: print("分界 %s：指定 %.2f 秒 → 靜音 %.2f–%.2f" % (ids[k + 1], force[k], *bounds[k]))
    elif f < .5:
        print("警告：分界 %s 沒有「後面第一個字＝下一行開頭」的靜音（最佳符合 %.2f，取 %.2f–%.2f，之後聽到「%s」），請人工核對或用 BOUNDS 指定" % (ids[k + 1], f, bounds[k][0], bounds[k][1], "".join(ww for ww, s0, e0 in words if e0 > sum(bounds[k]) / 2 + .02)[:6]), file=sys.stderr)
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
    # g＝實際停頓目標（含前後各留的 0.09 秒底噪，下面再扣掉）：段落 PARA；句間 clamp(自然停頓, MINGAP, MAXGAP)
    if i >= len(pieces) - 1: g = .15
    elif para_after[i]: g = PARA
    else: g = min(max(p["src_gap_after"] / F, MINGAP), MAXGAP)
    if i == len(pieces) - 2: g = max(g, float(os.environ.get("PRE_LAST", "0")))
    g = max(0, g - .09 / F); outv.append(np.zeros(int(g * SR), np.float32))
    wo = [round(st + (a - p["src_start"]) / F, 3) for ww, a, b in words if a >= p["src_start"] - .05 and b <= p["src_end"] + .1 and ww.strip()]   # 每個字詞在成品裡的起音時間（字幕／重拍對準旁白用）
    segj.append({"id": p["id"], "text": p["text"], "words": wo, "heard": p["heard"], "start": round(st if i else 0.0, 3), "speech_start": round(st + .03 / F, 3), "end": round(t, 3), "src": [p["src_start"], p["src_end"]], "gap_after": round(g, 3)}); t += g
y = np.concatenate(outv)
with wave.open(out, "wb") as w2: w2.setnchannels(1); w2.setsampwidth(2); w2.setframerate(SR); w2.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
chars = sum(ch); speech = sum(s["end"] - s["speech_start"] for s in segj); total = len(y) / SR - LEAD
rep = {"source": os.path.basename(raw), "tail_noise_dropped": (tail_noise[0], tail_noise[-1]) if tail_noise else None, "preamble_cut_sec": round(on0 - LEAD, 3), "narration_onset_in_raw": on0, "voiceLeadIn": LEAD, "atempo": F, "maxgap": MAXGAP, "mingap": MINGAP, "para_gap": PARA, "chars": chars,
       "dur_total": round(total, 2), "rate_incl_pauses": round(chars / total, 2), "rate_speech_only": round(chars / speech, 2), "segments": segj}
json.dump(rep, open(out + ".cut.json", "w"), ensure_ascii=False, indent=1)
print("設定句切掉 %.2f 秒；念稿 %d 字、%.2f 秒 → 含停頓 %.2f 字/秒、扣停頓 %.2f 字/秒" % (on0 - LEAD, chars, total, chars / total, chars / speech))
for s in segj: print(s["id"], s["start"], s["end"], s["text"], "｜聽到：", s["heard"])
