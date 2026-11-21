#!/usr/bin/env python3
"""v8 切段（通用版，不再寫死每篇的錨點字）：一次念完的原始旁白 → 切掉被念出的設定句與尾端雜訊 → 每鏡一段 → 成品 wav＋.cut.json（make_segments.py 接著產 segments.json）。
1. 設定句結尾：ASR 找「直接」那個詞之後的最長靜音，念稿起點＝靜音結尾（往前留 0.2 秒，起音不切）。
2. 每鏡分界：在念稿範圍內找所有 ≥0.12 秒的靜音；依每段字數算出預期分界時間，用動態規劃挑出依序、最接近預期、且越長越好的靜音當分界（切在靜音裡，不切字）。
2b.（2026-11-16 修）分界只能選「靜音之後的第一個辨識字＝下一行第一個字」的那段靜音（ASR 是簡體且可能少一兩字，用簡繁小對照＋前 4 字位置比對）；比不到的靜音（逗號後）重罰，整個分界都比不到才退回舊邏輯並印警告。環境變數 BOUNDS="47.3,51.6,,60.0" 可直接指定每個分界在原始錄音的秒數（空白＝不指定），作為保底。
3. 核對：每段範圍內的 ASR 文字印出來，人工對照念稿（數字寫法不同不算錯）。
4. 念稿結尾：最後一個 ASR 字所在的有聲段結尾，之後的聲音（模型尾端雜訊）不收。
5. 停頓（2026-11-16 Andy 新規，剪輯插靜音、不放慢語速）：句間實際停頓下限 MINGAP（預設 0.3 秒），原本自然停頓較長的保留到 MAXGAP（預設 0.45 秒）；narration.txt 有空行處＝段落分界，停頓固定 PARA（預設 0.7 秒）。沒有空行＝全部同一段。字幕／鏡頭時序（make_segments.py → gen_v8.py）讀的是切完後的時間點，自動跟著新停頓走。
用法：python3 cut_take_v8.py <原始 wav> <asr.json> <佇列資料夾> <輸出 wav> [atempo] [maxgap=0.60] [mingap=0.45] [para=0.80]（環境變數 HOLD＝說完到換鏡留白，預設 1.0；>60 秒自動降 0.7）（環境變數 PRE_LAST＝片尾那句前的停頓秒數）"""
import json, sys, wave, re, subprocess, os
import numpy as np
raw, asrp, q, out = sys.argv[1:5]; F = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0; MAXGAP = float(sys.argv[6]) if len(sys.argv) > 6 else 0.60
MINGAP = float(sys.argv[7]) if len(sys.argv) > 7 else 0.45; PARA = float(sys.argv[8]) if len(sys.argv) > 8 else 0.80
HOLD = float(os.environ.get("HOLD", "1.0")); PUNCT_GAP = 0.35   # v9（2026-11-17 Andy「語速太快」）：HOLD＝說完到換鏡至少留白秒數；句內標點處自然間隙 <0.3 補到 PUNCT_GAP；數字片語前後緊貼補到 NUM_GAP
LEAD = 0.2
w = wave.open(raw); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
hop = int(SR * .01); n = len(x) // hop
rms = np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop] ** 2)) + 1e-9 for i in range(n)]); db = 20 * np.log10(rms)
thr = max(-48.0, db.max() - 40); voiced = db > thr
W = json.load(open(asrp)); words = [(a["w"].strip(), a["s"], a["e"]) for a in W]
if os.environ.get("DROP_AFTER"): words = [w_ for w_ in words if w_[1] < float(os.environ["DROP_AFTER"])]   # 2026-11-20（規則 28）：原始錄音尾端不要的句子（例如片尾自編關鍵字）整句丟掉；切點在上一句句號之後的靜音
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
# 簡→繁小對照（ASR 輸出簡體；只列常見字，沒列到的字退成「同字才算對」）
S2T = dict(zip("这买内统计负担级过体户总资贷还价来为让们说话时间开关长发动经济务观点现实后场产业对车电会发联结约论题际环项报导记错须从样别两种应该钱让儿虽无节数据备选",
               "這買內統計負擔級過體戶總資貸還價來為讓們說話時間開關長發動經濟務觀點現實後場產業對車電會發聯結約論題際環項報導記錯須從樣別兩種應該錢讓兒雖無節數據備選"))
def norm(t): return "".join(S2T.get(c, c) for c in re.sub(r"[，。、；：？！「」（）\s\d%.]", "", t))
# 前導判定（2026-11-17 修）：切點只能在「念稿第 1 行開頭字」在 ASR 的位置之前，不准把第一行內容當前導剪掉。
# 「直接」之後找第一個和念稿第 1 行前 4 字對得上（≥3 字，允許 ASR 同音誤辨或漏第一字）的位置 j；起點＝j 之前最後一段靜音的結尾；對不上就報錯停下（不退回舊的「最長靜音」邏輯）。
k0 = max(i for i, (ww, s, e) in enumerate(words) if "直接" in ww)
def first_line_start():
    ln = norm(texts[0])[:4]
    for j in range(k0 + 1, min(len(words), k0 + 12)):
        if words[j][0].strip() in ("說", "说"): continue   # 2026-11-20：「直接說」的「說」不是念稿第一字（ASR 常把「平均」的平漏掉，變成「說均」）
        nx = "".join(norm(ww) for ww, s0, e0 in words[j:j + 6])[:4]
        if len(nx) >= 3 and sum(1 for p_, q_ in zip(nx, ln) if p_ == q_) >= 3: return j
        if len(nx) >= 3 and sum(1 for p_, q_ in zip(nx, ln[1:]) if p_ == q_) >= 3: return j
    # 2026-11-20：念稿第 1 行以中文數字開頭（例「二十五到二十九歲」），ASR 回阿拉伯數字（「25到29歲」）時，norm 會把數字吃掉而對不上 → 退而求其次：「直接」之後第一個以數字開頭的詞
    if texts[0][:1] in "〇一二三四五六七八九十":
        for j in range(k0 + 1, min(len(words), k0 + 12)):
            if re.match(r"\d", words[j][0].strip()): return j
    return None
j0 = first_line_start()
if j0 is None: sys.exit("前導判定失敗：「直接」之後 12 個字內找不到念稿第 1 行開頭「%s」（ASR 聽到：%s）。不切，請人工看 ASR 或用 ON0 環境變數指定起點。" % (texts[0][:6], "".join(w_[0] for w_ in words[k0:k0 + 12])))
_sil = [z for z in runs_in(words[j0][1] - 1.5, words[j0][1] + .3, 6) if z[1] / 100 <= words[j0][1] + .3]
on0 = float(os.environ["ON0"]) if os.environ.get("ON0") else (_sil[-1][1] / 100 - .1 if _sil else max(0.0, words[j0][1] - .1))
if on0 > words[j0][1] + .3: sys.exit("前導判定錯誤：起點 %.2f 在第 1 行開頭字 %.2f 之後" % (on0, words[j0][1]))
le = int((words[-1][2] - .05) * 100)
while le < n and voiced[le]: le += 1
last = le / 100 + .01; tail_noise = [round(i / 100, 2) for i in range(le, n) if voiced[i]]
# 候選靜音（≥0.12 秒）與預期分界
cand = [(a / 100, b / 100) for a, b in runs_in(on0 + .3, last - .3, 12)]
ch = [cc(t) for t in texts]; tot = sum(ch); exp = []; acc = 0
for c in ch[:-1]: acc += c; exp.append(on0 + (last - on0) * acc / tot)
K, M = len(exp), len(cand)
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
    for kv in os.environ.get('TRIM', '').split(','):   # TRIM=s6=78.35：某句只取前半（刪掉同一段錄音裡後面的句子，不重送 TTS）
        if '=' in kv and kv.split('=')[0] == sid: e = min(e, float(kv.split('=')[1]))
    heard = "".join(ww for ww, a, b in words if a >= s - .05 and b <= e + .1)
    pieces.append({"id": sid, "text": texts[i], "heard": heard, "src_start": round(s, 3), "src_end": round(e, 3), "src_gap_after": round(gap, 3)})
CUTS = []   # 環境變數 CUTS="40.95-42.16>0.35,..."（2026-11-17）：原始錄音裡某段句內靜音 a–b 壓成 keep 秒（從中間刪，不重送 TTS、不放慢）
for kv in os.environ.get("CUTS", "").split(","):
    if ">" in kv and "-" in kv:
        ab, kp = kv.split(">"); a_, b_ = [float(v) for v in ab.split("-")]; kp = float(kp)
        if b_ - a_ > kp: CUTS.append((a_ + kp / 2, b_ - kp / 2))
def seg_audio(a, b, pa=.03, pb=.06):
    y = x[int(max(0, a - pa) * SR):int((b + pb) * SR)]
    if abs(F - 1) < 1e-3: return y
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", "atempo=%.4f" % F, "-f", "f32le", "-"], input=y.tobytes(), capture_output=True).stdout
    return np.frombuffer(p, np.float32)
# 句內補停頓點（2026-11-21 規則 29 重寫）：只在「念稿逗號／句號」位置、且與 ASR 逐字對上（punct_align.py：中文數字先轉阿拉伯、difflib 逐字對）才插；對不上不插。
# 不再有數字前後停頓（NUM_GAP 拿掉）；插點前後 30ms 的音量要 < −40 dBFS，否則不插；插點兩側 15ms 淡出淡入。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from punct_align import punct_boundaries
QUIET_DB = -40.0; WIN = int(.03 * SR); FADE = int(.015 * SR)
def _wdb(a, b):
    seg = x[max(0, a):max(a + 1, b)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else -120.0
def quiet_point(b, nxt):
    """在 ASR 字詞間隙（前後各放寬 50ms，因 ASR 時間會漂）找前後 30ms 都 < −40 dBFS 的插點；取兩側都最安靜者，找不到回 None。"""
    best = None
    t = b - .05
    while t <= nxt + .05:
        i = int(t * SR); lo = _wdb(i - WIN, i); hi = _wdb(i, i + WIN); m = max(lo, hi)
        if m < QUIET_DB and (best is None or m < best[0]): best = (m, t)
        t += .005
    return best[1] if best else None
SKIPPED = {"align": 0, "loud": 0}
def inserts_for(p):
    ws = [(ww, a, b) for ww, a, b in words if a >= p["src_start"] - .05 and b <= p["src_end"] + .1 and ww.strip()]
    if len(ws) < 2: return []
    bset = punct_boundaries(p["text"], [w_[0] for w_ in ws]); out = []
    nP = len(re.findall(r"[，、；：]", p["text"][:-1]))
    SKIPPED["align"] += max(0, nP - len([k for k in bset if k < len(ws) - 1]))
    for k in sorted(bset):
        if k >= len(ws) - 1: continue
        nat = ws[k + 1][1] - ws[k][2]
        if nat >= .3 + 1e-9 or nat >= PUNCT_GAP: continue
        tq = quiet_point(ws[k][2], ws[k + 1][1])
        if tq is None: SKIPPED["loud"] += 1; continue
        out.append((tq, PUNCT_GAP - max(nat, 0)))
    return out
def assemble(hold):
    outv = [np.zeros(int(LEAD * SR), np.float32)]; t = LEAD; segj = []
    for i, p in enumerate(pieces):
        rem = [(ra, rb) for ra, rb in CUTS if p["src_start"] <= ra and rb <= p["src_end"]]
        ins = inserts_for(p)
        ev = sorted([(r_[0], "cut", r_[1]) for r_ in rem] + [(q_[0], "ins", q_[1]) for q_ in ins])
        y_parts = []; cur = p["src_start"]; first = True; fin = False
        def _fi(a_):
            if fin and len(a_) > FADE: a_ = a_.copy(); a_[:FADE] *= np.linspace(0, 1, FADE, dtype=np.float32)
            return a_
        for tt, kind, v_ in ev:
            if tt < cur: continue
            seg_ = _fi(seg_audio(cur, tt, .03 if first else 0, .0)); fin = False; first = False
            if kind == "ins" and len(seg_) > FADE: seg_ = seg_.copy(); seg_[-FADE:] *= np.linspace(1, 0, FADE, dtype=np.float32)
            y_parts.append(seg_)
            if kind == "cut": cur = v_
            else: y_parts.append(np.zeros(int(v_ / F * SR), np.float32)); cur = tt; fin = True
        y_parts.append(_fi(seg_audio(cur, p["src_end"], .03 if first else 0, .06))); y = np.concatenate(y_parts)
        st = t; t += len(y) / SR; outv.append(y)
        if i >= len(pieces) - 1: g = .15
        elif para_after[i]: g = PARA
        else: g = min(max(p["src_gap_after"] / F, MINGAP), MAXGAP)
        if i < len(pieces) - 1: g = max(g, hold + .3)   # 每鏡說完後畫面落定：下一鏡在下句開口前 0.25 秒換，所以間隔至少 hold＋0.3
        if i == len(pieces) - 2: g = max(g, float(os.environ.get("PRE_LAST", "0")))
        g = max(0, g - .09 / F); outv.append(np.zeros(int(g * SR), np.float32))
        def shift(a): return sum(v2 / F for tt, kd, v2 in ev if kd == "ins" and tt <= a and tt >= p["src_start"]) - sum(rb - ra for ra, rb in rem if a >= rb) - sum(max(0, a - ra) for ra, rb in rem if ra < a < rb)
        ins_at = [round(st + (tq_ - p["src_start"]) / F + shift(tq_) - v2 / F, 3) for tq_, kd, v2 in ev if kd == "ins"]
        wo = [round(st + (a - p["src_start"]) / F + shift(a), 3) for ww, a, b in words if a >= p["src_start"] - .05 and b <= p["src_end"] + .1 and ww.strip()]
        segj.append({"id": p["id"], "text": p["text"], "words": wo, "heard": p["heard"], "start": round(st if i else 0.0, 3), "speech_start": round(st + .03 / F, 3), "end": round(t, 3), "src": [p["src_start"], p["src_end"]], "gap_after": round(g, 3), "inserts": len(ins), "ins_at": ins_at}); t += g
    return outv, segj, t - LEAD
outv, segj, tl = assemble(HOLD)
if tl > 60 and HOLD > .7: print("總長 %.1f 秒 >60：HOLD 1.0 → 0.7 重組" % tl); HOLD = .7; outv, segj, tl = assemble(HOLD)
if tl > 60:
    print("警告：HOLD 降到 0.7 仍 %.1f 秒 >60，建議刪（字數最多的句子，請人工決定、不自動刪）：" % tl, file=sys.stderr)
    for i in sorted(range(len(texts)), key=lambda i: -ch[i])[:3]: print("  %s（%d 字）%s" % (ids[i], ch[i], texts[i]), file=sys.stderr)
y = np.concatenate(outv)
with wave.open(out, "wb") as w2: w2.setnchannels(1); w2.setsampwidth(2); w2.setframerate(SR); w2.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
chars = sum(ch); speech = sum(s["end"] - s["speech_start"] for s in segj); total = len(y) / SR - LEAD
rep = {"source": os.path.basename(raw), "tail_noise_dropped": (tail_noise[0], tail_noise[-1]) if tail_noise else None, "preamble_cut_sec": round(on0 - LEAD, 3), "narration_onset_in_raw": on0, "voiceLeadIn": LEAD, "atempo": F, "maxgap": MAXGAP, "mingap": MINGAP, "para_gap": PARA, "hold": HOLD, "chars": chars, "ins_skipped": dict(SKIPPED),
       "dur_total": round(total, 2), "rate_incl_pauses": round(chars / total, 2), "rate_speech_only": round(chars / speech, 2), "segments": segj}
json.dump(rep, open(out + ".cut.json", "w"), ensure_ascii=False, indent=1)
print("設定句切掉 %.2f 秒；念稿 %d 字、%.2f 秒 → 含停頓 %.2f 字/秒、扣停頓 %.2f 字/秒" % (on0 - LEAD, chars, total, chars / total, chars / speech))
for s in segj: print(s["id"], s["start"], s["end"], s["text"], "｜聽到：", s["heard"])
