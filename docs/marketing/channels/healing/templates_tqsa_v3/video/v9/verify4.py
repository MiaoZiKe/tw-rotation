#!/usr/bin/env python3
"""交件前四道驗證的程式部分（2026-11-22 Andy：「請你務必確實檢查影片是否丟問題…請重做」；規則 video_logic.md 最後一節）。
用法：python3 v9/verify4.py <佇列資料夾> [--wav narration.wav] [--video video.mp4] [--no-asr] [--no-sheet]
做三件事（Gemini 聽感另跑 v9/gemini_listen.py）：
 ③ 停頓密度：narration.wav 每 10ms 能量 < max(−48, 峰值−40) dB 連續 ≥0.25 秒＝一處停頓；依 cut.json 分成「換幕／句號後／句內」。
    合格：句內 0、全片停頓數 ≤ 句數＋2、換幕停頓 0.6～0.8 秒且 ≤6 處。輸出停頓圖 pause_chart.png。
 ② ASR：faster-whisper 辨識成品旁白，與念稿逐字比對（中文數字換阿拉伯、簡轉繁後 difflib），列出不一致的字。
 ④ 抽格：video.mp4 每 1 秒抽一格拼成 frames_1s.png（人工逐格看重疊、空白、下半部空洞、字太小）。
 ⑤ 流暢度（2026-11-27 Andy：「看起來感覺卡卡的 幫我避免」）：v9/smooth_check.py —— 時間戳（PTS 不准倒退／重複、幀距固定 1/fps、幀數＝片長×fps）
    ＋逐幀畫面變化量（動態中途的孤立停格、顯示順序倒退、每 chunk 幀的段接縫變化量異常）。結果寫 verify4.json 的 smooth。
結果寫 verify4.json。"""
import json, os, re, subprocess, sys, wave, difflib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "tts"))
from punct_align import punct_boundaries, canon_chars
a = sys.argv[1:]; q = os.path.abspath(a[0])
def cz(s_): return "".join(c for c, _ in canon_chars([(c, i) for i, c in enumerate(s_)]))
def opt(k, d):
    return a[a.index(k) + 1] if k in a else d
WAV = os.path.join(q, opt("--wav", "narration.wav")); VID = os.path.join(q, opt("--video", "video.mp4"))
cut = json.load(open(WAV + ".cut.json")); segs = cut["segments"]
w = wave.open(WAV); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
hop = SR // 100; n = len(x) // hop
db = 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9); thr = max(-48.0, db.max() - 40); v = db > thr
speech_end = segs[-1]["end"]
runs = []; i = int(cut.get("voiceLeadIn", .35) * 100) + 5
while i < n:
    if not v[i]:
        j = i
        while j < n and not v[j]: j += 1
        if (j - i) >= 25 and j / 100 < speech_end - .05: runs.append((i / 100, j / 100))
        i = j
    else: i += 1
# 每段的句號位置（用念稿去掉逗號後對 ASR 詞）
asr = json.load(open(os.path.join(q, "narration_take.asr.json"))); AW = [(t["w"].strip(), t["s"], t["e"]) for t in asr]
pauses = []
for t0, t1 in runs:
    mid = (t0 + t1) / 2; kind = None
    for k, s in enumerate(segs[:-1]):
        if s["end"] - .3 <= mid <= segs[k + 1]["speech_start"] + .1: kind = "換幕"; at = s["id"] + "→" + segs[k + 1]["id"]
    if kind is None:
        s = max([s for s in segs if s["speech_start"] - .05 <= mid], key=lambda s: s["speech_start"], default=segs[0])
        a_, b_ = s["src"]; ws = [w_ for w_ in AW if w_[1] >= a_ - .05 and w_[2] <= b_ + .1 and w_[0]]
        wo = s["words"]; tx = re.sub(r"[，、；：,;:]", "", s["text"])
        ends = punct_boundaries(tx, [w_[0] for w_ in ws]) if len(ws) == len(wo) and re.search(r"[。？！?!]", tx[:-1]) else set()
        k = max([i for i in range(len(wo)) if wo[i] < mid], default=0)
        ke = [e for e in ends if e + 1 < len(wo) and wo[e] - .05 <= mid <= wo[e + 1] + .35]   # ASR 詞起點常漂進靜音，放寬 0.35 秒
        allp = punct_boundaries(s["text"], [w_[0] for w_ in ws]) if len(ws) == len(wo) else set()
        kc = [e for e in allp if e + 1 < len(wo) and wo[e] - .05 <= mid <= wo[e + 1] + .35]
        if ke: k = ke[0]
        elif kc: k = kc[0]
        kind = "句號後" if ke else ("逗號" if kc and t1 - t0 <= .45 else "句內")
        if kind == "句內":   # 2026-11-27：ASR 聽錯字（例：難→南）會讓標點對位失敗，真正的句號停頓被誤判成句內；改用「停頓前聽到的字」與「念稿各標點前的字」做模糊比對
            _raw0 = cut.get("raw_range", [0])[0]; hp_ = cz("".join(w_[0] for w_ in ws if w_[1] < t0 + _raw0 - .02)); tx_ = s["text"]
            for m_ in re.finditer(r"[。？！?!，、；：,;:]", tx_[:-1]):
                rp_ = cz(tx_[:m_.start()]); kk = difflib.SequenceMatcher(None, rp_[-4:], hp_[-4:]).ratio()
                if abs(len(rp_) - len(hp_)) <= 3 and kk >= .5:
                    kind = "句號後" if m_.group() in "。？！?!" else ("逗號" if t1 - t0 <= .45 else "句內"); break   # 2026-11-22 定義：逗號處 TTS 自然 ≤0.45 秒不算句中停頓、不計總數
        at = "%s「%s｜%s」" % (s["id"], ws[k][0] if k < len(ws) else "", ws[k + 1][0] if k + 1 < len(ws) else "")
    pauses.append({"t0": t0, "t1": t1, "dur": round(t1 - t0, 2), "kind": kind, "at": at})
nsent = sum(len(re.findall(r"[。？！?!]", s["text"])) or 1 for s in segs)
SG = float(cut.get("scene_gap", .7)); GLO, GHI = round(SG - .15, 2), round(SG + .15, 2)   # 2026-11-22 晚 Andy「速度可以在快點」：換幕停頓改 0.5 秒 → 合格範圍跟著 cut.json 的 scene_gap（±0.15）
for p in pauses:
    if p["kind"] == "換幕" and p["dur"] < GLO: p["kind"] = "換幕短"   # 沒有補到 0.6～0.8 的換幕（GAP_OVERRIDE），不算「補停頓」那 6 處
inner = [p for p in pauses if p["kind"] == "句內"]; scene = [p for p in pauses if p["kind"] == "換幕"]; comma = [p for p in pauses if p["kind"] == "逗號"]
npc = len(pauses) - len(comma)   # 計入上限的停頓數（逗號自然停頓不算）
bad = []
if inner: bad.append("句內停頓 %d 處" % len(inner))
if npc > nsent + 2: bad.append("停頓 %d 處 > 句數 %d＋2" % (npc, nsent))
if len([p for p in scene if p["dur"] >= .55]) > 6: bad.append("換幕補停頓（≥0.55 秒）%d 處 >6" % len([p for p in scene if p["dur"] >= .55]))   # 2026-11-22 晚：「≤6 處」限的是補長的 0.6～0.8 停頓；換幕改 0.5 秒後與句號後自然停頓同長，不再算補停頓（總數仍受「≤ 句數＋2」限制）
for p in scene:
    if cut.get("raw_keep"): break   # 聲音先定（規則 33）：換幕用原始錄音的自然停頓，不檢查補停頓長度
    if not GLO <= p["dur"] <= GHI: bad.append("換幕停頓 %s %.2f 秒不在 %.2f～%.2f" % (p["at"], p["dur"], GLO, GHI))
res = {"sentences": nsent, "pauses": pauses, "n_pauses": len(pauses), "n_inner": len(inner), "n_scene": len(scene), "narr_dur": round(len(x) / SR, 2)}
# 停頓圖
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ("/root/.fonts/NotoSansCJKtc-Regular.otf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
    if os.path.exists(f): font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
fig, ax = plt.subplots(figsize=(22, 4.5), dpi=80); tt = np.arange(n) / 100
ax.plot(tt, np.maximum(db, -80), lw=.6, color="#555"); ax.axhline(thr, color="#999", ls=":", lw=.8)
col = {"換幕": "#2a9d8f", "換幕短": "#8ecae6", "逗號": "#f4a261", "句號後": "#457b9d", "句內": "#e63946"}
for p in pauses:
    ax.axvspan(p["t0"], p["t1"], color=col[p["kind"]], alpha=.35); ax.text((p["t0"] + p["t1"]) / 2, -76, "%.2f" % p["dur"], ha="center", fontsize=8)
for s in segs: ax.text(s["speech_start"], -5, s["id"], fontsize=9, color="#222")
ax.set_ylim(-80, 0); ax.set_xlim(0, tt[-1]); ax.set_xlabel("秒")
ax.set_title("停頓圖（≥0.25 秒）：綠＝換幕 %d、藍＝句號後 %d、紅＝句內 %d；共 %d 處／句數 %d（上限 %d）" % (len(scene), len(pauses) - len(scene) - len(inner), len(inner), len(pauses), nsent, nsent + 2))
plt.tight_layout(); plt.savefig(os.path.join(q, "pause_chart.png")); plt.close()
# ASR 比對
if "--no-asr" not in a:
    jp = os.path.join(q, "verify4_asr.json")
    subprocess.run([sys.executable, os.path.join(HERE, "..", "tts", "asr.py"), WAV, jp], check=True, capture_output=True)
    hw = "".join(t["w"] for t in json.load(open(jp)))
    def cz(s): return "".join(c for c, _ in canon_chars([(c, i) for i, c in enumerate(s)]))
    ref = cz("".join(s["text"] for s in segs)); hyp = cz(hw); diffs = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if op != "equal": diffs.append("%s 念稿「%s」→聽到「%s」（念稿第 %d 字）" % (op, ref[i1:i2], hyp[j1:j2], i1))
    res["asr_heard"] = hw; res["asr_diffs"] = diffs; res["asr_ratio"] = round(difflib.SequenceMatcher(None, ref, hyp, autojunk=False).ratio(), 3)
# ── 2026-11-27 新增兩條自動檢查（avgwage／quit 審片：片頭殘留設定句「直接說」、s7 換幕晚於聲音 0.7 秒；之後每支有旁白的片都要過）──
# ⑤ 裁頭後前 1.5 秒單獨 ASR：出現念稿以外的字（尤其「直接說」）＝不合格
if "--no-asr" not in a:
    import tempfile
    tmpw = os.path.join(tempfile.mkdtemp(), "head.wav"); k15 = int(1.5 * SR)
    with wave.open(tmpw, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x[:k15], -1, 1) * 32767).astype("<i2").tobytes())
    hj = os.path.join(q, "verify4_head_asr.json")
    subprocess.run([sys.executable, os.path.join(HERE, "..", "tts", "asr.py"), tmpw, hj], check=True, capture_output=True)
    hh = "".join(t["w"] for t in json.load(open(hj))); hyp = cz(hh); ref = cz(segs[0]["text"])[:len(hyp) + 3]
    extra = []
    if hyp:
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
            if op in ("insert", "replace") and j1 == 0: extra.append(hyp[j1:j2])   # 開頭多出念稿沒有的字
    setup = [w_ for w_ in ("直接說", "直接说", "直接", "子爹說") if w_ in hh]
    ratio = difflib.SequenceMatcher(None, ref, hyp, autojunk=False).ratio() if hyp else 1.0
    res["head_asr"] = {"heard_first_1_5s": hh, "script_start": ref, "extra_leading": extra, "setup_words": setup, "ratio": round(ratio, 3)}
    if setup or extra or ratio < .5: bad.append("裁頭後前 1.5 秒單獨 ASR 出現念稿以外的字：聽到「%s」，念稿開頭「%s」%s" % (hh, ref, "（含設定句「%s」）" % "、".join(setup) if setup else ""))
# ⑥ 換幕不准晚於下一句第一字起音 0.15 秒（2026-11-27 quit 的 s7 換幕落後聲音 0.7 秒）。
#    ASR 的逐字時間戳會漂 0.3 秒以上，不能拿來量秒數，所以只用「辨識出的字」：每個換幕點 st，從 st−0.15 秒起切 1.6 秒單獨 ASR；
#    聽到的開頭應該是下一句的第 1 個字（或還在念上一句的尾巴）。若開頭已經是下一句的第 3 個字以後＝這句開頭的字在換幕前就念掉了（≥約 0.4 秒）＝換幕太晚。
#    第 2 個字（k=1）可能只是 ASR 漏掉首字，只記在報告裡不判錯。
sgj = json.load(open(os.path.join(q, "segments.json")))["segments"]
if "--no-asr" not in a and len(sgj) == len(segs):
    import tempfile
    chk = []; late = []; td = tempfile.mkdtemp()
    for i in range(1, len(segs)):
        st = sgj[i]["start"]; t0_ = max(0.0, st - .15); pw = os.path.join(td, "w%d.wav" % i); pj = os.path.join(td, "w%d.json" % i)
        with wave.open(pw, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x[int(t0_ * SR):int((t0_ + 1.6) * SR)], -1, 1) * 32767).astype("<i2").tobytes())
        subprocess.run([sys.executable, os.path.join(HERE, "..", "tts", "asr.py"), pw, pj], check=True, capture_output=True)
        hw_ = "".join(t["w"] for t in json.load(open(pj))); hy = cz(hw_); rf = cz(segs[i]["text"]); tail = cz(segs[i - 1]["text"])[-5:]
        k = None
        for kk in range(0, 10):
            if hy[:2] and rf[kk:kk + 2] == hy[:2]: k = kk; break
        if k is None and hy[:1]:
            for kk in range(0, 10):
                if rf[kk:kk + 1] == hy[:1]: k = kk; break
        in_tail = bool(hy[:2]) and hy[:2] in tail
        if in_tail: k = -1   # 窗口一開始還在念上一句的尾巴＝換幕沒落後
        item = {"id": segs[i]["id"], "scene_start": st, "heard_from_scene_start_minus_0_15": hw_, "script_start": rf[:8], "first_char_index": k}
        if k is None: item["note"] = "聽到的字與這句開頭對不上，無法判定"
        elif k >= 2: late.append("%s 換幕 %.2f 秒時，聽到的已是這句第 %d 個字（「%s」）＝這句開頭的字在換幕前就念了（約晚 %.1f 秒以上）" % (segs[i]["id"], st, k + 1, hw_, k * .19))
        chk.append(item)
    res["scene_vs_onset"] = chk
    if late: bad.append("換幕晚於下一句第一字起音：" + "；".join(late))
# 1 秒抽格拼圖
if "--no-sheet" not in a and os.path.exists(VID):
    od = os.path.join(q, "_frames1s"); os.makedirs(od, exist_ok=True)
    for f in os.listdir(od): os.remove(os.path.join(od, f))
    subprocess.run(["ffmpeg", "-v", "error", "-i", VID, "-vf", "fps=1,scale=270:-1,drawtext=text='%{eif\\:t\\:d}s':x=6:y=6:fontsize=22:fontcolor=red:box=1:boxcolor=white", os.path.join(od, "f%03d.png")], check=True)
    fs = sorted(os.listdir(od)); cols = 10; rows = (len(fs) + cols - 1) // cols
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(od, "f%03d.png"), "-vf", "tile=%dx%d:padding=4:color=black" % (cols, rows), "-frames:v", "1", os.path.join(q, "frames_1s.png")], check=True)
    res["frames"] = len(fs)
# ⑤ 流暢度
if os.path.exists(VID):
    sys.path.insert(0, HERE); from smooth_check import smooth_check
    sm = smooth_check(VID, chunk=int(opt("--chunk", "60"))); res["smooth"] = sm; bad += sm["bad"]
    print("流暢度：幀數 %d／應有 %d；PTS 倒退 %d；幀距異常 %d；動態中孤立停格 %d；順序倒退 %d；接縫異常 %d" % (sm["frames"], sm["expect"], sm["pts_back"], sm["pts_gap"], sm["stall"], sm["reverse"], len(sm["seam_bad"])))
res["pass_auto"] = not bad; res["bad"] = bad
json.dump(res, open(os.path.join(q, "verify4.json"), "w"), ensure_ascii=False, indent=1)
print("停頓：計入 %d（換幕 %d、句號後 %d、句中 %d）＋逗號自然 %d（不計）／句數 %d；%s" % (npc, len(scene), npc - len(scene) - len(inner), len(inner), len(comma), nsent, "；".join("%s %.2f %s" % (p["kind"], p["dur"], p["at"]) for p in pauses)))
if "asr_diffs" in res: print("ASR 相似度 %.3f；不一致 %d：%s" % (res["asr_ratio"], len(res["asr_diffs"]), "；".join(res["asr_diffs"])))
print("自動檢查：" + ("合格" if not bad else "不合格 → " + "；".join(bad)))
