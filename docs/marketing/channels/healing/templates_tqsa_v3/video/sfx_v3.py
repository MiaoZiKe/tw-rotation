#!/usr/bin/env python3
"""談晴說礙 影片音軌 v3（2026-11-15）：程式合成音效＋（有的話）旁白 → 限幅 → AAC；片尾招牌音（卡林巴）。
- 音色只用乾淨的正弦類（卡林巴＝基音＋兩個衰減較快的泛音），不加噪音、不用現成音檔、不模仿任何品牌旋律。參數固定，每支片同一段招牌音。
- 每個音效的起音落在畫面事件的同一幀（事件時間由 video_runtime_v3.js 的 window.sfxEvents() 給，片尾全用整數幀）。
- 片尾目標：約 −11.5 LUFS、true peak ≤ −1 dBTP（AAC 編碼後量）；限幅器 alimiter latency=1（補回延遲，不讓音效晚到）。
- 旁白起音（plan.md「2026-11-15 旁白開頭不可被截」）：旁白音檔不切、不加長淡入；量開頭 300 毫秒（每 20 毫秒一格）寫進報告。
用法：python3 sfx_v3.py <events.json> <總長秒> <片尾起點秒> <輸出 m4a> <報告 json> [旁白音檔] [片尾音效 mp3]"""
import json, subprocess, sys, re, os, tempfile
import numpy as np
SR = 48000
C5 = 523.25

def note(n): return C5 * 2 ** (n / 12)

def kal(f, g=1.0, dur=2.6):
    t = np.arange(int(SR * dur)) / SR
    att = 1 - np.exp(-t / 0.0025)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.95)
    x += 0.22 * np.sin(2 * np.pi * 2.0 * f * t) * np.exp(-t / 0.22)
    x += 0.07 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t / 0.06)
    return g * att * x

def pop(g=.22):
    t = np.arange(int(SR * .2)) / SR
    return g * (1 - np.exp(-t / .001)) * (np.sin(2 * np.pi * 1180 * t) * np.exp(-t / .02) + .5 * np.sin(2 * np.pi * 590 * t) * np.exp(-t / .045))

def bloom(ns, g=1.0):
    """落定那一下（為之一亮，但溫和）：卡林巴和弦＋高八度柔和的光暈長音（80ms 漸亮、慢慢消失）。"""
    x = sum(kal(note(n), .55, 3.0) for n in ns)
    t = np.arange(int(SR * 3.0)) / SR
    env = (1 - np.exp(-t / .08)) * np.exp(-t / 1.1)
    x = x + .16 * env * sum(np.sin(2 * np.pi * note(n + 12) * t + i) for i, n in enumerate(ns[:3]))
    return g * x


# ── v4 新增音色（全部正弦合成，無噪音）：物件動作音（tick 翻頁／thump 落地／glide 滑過）與片尾招牌音（bell 鈴音、click 啪、sparkle 閃、shimmer 收束上行音）──
def T_(dur): return np.arange(int(SR * dur)) / SR
def tick(g=.16):
    t = T_(.06); return g * (1 - np.exp(-t / .0006)) * (np.sin(2 * np.pi * 1900 * t) * np.exp(-t / .008) + .4 * np.sin(2 * np.pi * 760 * t) * np.exp(-t / .02))
def thump(g=.5):
    t = T_(.28); f = 62 + 80 * np.exp(-t / .03); ph = 2 * np.pi * np.cumsum(f) / SR
    return g * (1 - np.exp(-t / .002)) * np.sin(ph) * np.exp(-t / .07)
def glide(f0, f1, dur, g=.15):
    t = T_(dur); f = f0 * (f1 / f0) ** (t / dur); ph = 2 * np.pi * np.cumsum(f) / SR
    return g * np.sin(ph) * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
def bell(f, g=.5, dur=2.4):
    t = T_(dur); att = 1 - np.exp(-t / .002)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in [(1, 1, 1.1), (2.76, .35, .5), (5.4, .14, .2), (8.9, .05, .08)])
    return g * att * x * .6
def click(g=.2):
    t = T_(.05); return g * (1 - np.exp(-t / .0004)) * np.sin(2 * np.pi * 2600 * t) * np.exp(-t / .006)
def spark(f, g=.2):
    t = T_(.5); return g * (1 - np.exp(-t / .001)) * (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t / .12)

def pad(dur, g=1.0):
    """片尾底墊：C4–E4–G4 正弦長音，0.5 秒漸入、最後 0.6 秒漸出（讓片尾音量穩定，不突兀）。"""
    t = np.arange(int(SR * dur)) / SR
    env = np.clip(t / .5, 0, 1) * np.clip((dur - t) / .6, 0, 1)
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(261.63, .5), (329.63, .35), (392.0, .35), (523.25, .15)])
    return g * env * x * (1 + .04 * np.sin(2 * np.pi * .5 * t))

def synth(events, dur, outro_t0, og):
    L = np.zeros(int(SR * (dur + 0.05))); R = L.copy()
    def put(x, t, pan=0.0):
        i = int(round(t * SR)); j = min(len(L), i + len(x))
        if j <= i: return
        L[i:j] += x[:j - i] * (1 - pan) ; R[i:j] += x[:j - i] * (1 + pan)
    for e in events:
        t, k = e["t"], e["type"]; inout = t >= outro_t0 - 1e-6; gg = og if inout else 1.0
        if k == "pop": put(pop(), t)
        elif k == "chime": put(kal(note(12), .2) + kal(note(19), .12), t)
        elif k == "kal":
            for i, n in enumerate(e["n"] if isinstance(e["n"], list) else [e["n"]]): put(kal(note(n), .5 * e.get("g", 1.0) * gg), t, pan=(.15 if n % 2 else -.15))
        elif k == "bloom": put(bloom(e["n"], gg), t)
        elif k == "pad": put(pad(e["dur"], .16 * gg), t)
        elif k == "whoosh": put(glide(700, 260, .16, .05), t)
        elif k == "tick": put(tick(.16 * e.get("g", 1.0)), t)
        elif k == "thump": put(thump(e.get("g", .5) * gg), t)
        elif k == "glide": put(glide(e["f0"], e["f1"], e["dur"], e.get("g", .15) * gg), t)
        elif k == "click": put(click(.2 * gg), t)
        elif k == "bell":
            for n in e["n"]: put(bell(note(n), e.get("g", .5) * gg), t, pan=(.2 if n % 2 else -.2))
        elif k == "sparkle":
            for n in e["n"]: put(spark(note(n), .16 * e.get("g", 1.0) * gg), t)
        elif k == "shimmer":
            for i, n in enumerate(e["n"]): put(spark(note(n), .12 * e.get("g", 1.0) * gg), t + i * .045, pan=(-.3 + .12 * i))
    # 很短的早期反射，讓卡林巴有空間感（乾淨、不糊）
    for d, a in [(.031, .2), (.053, .15), (.079, .1), (.113, .07)]:
        n = int(d * SR); L[n:] += a * L[:-n].copy(); R[n:] += a * R[:-n].copy()
    return np.stack([L, R], 1)

def wav(path, x):
    import wave
    y = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())

def measure(path, ss, t):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(ss), "-t", str(t), "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1]); tp = re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", o)
    return I, float(tp[-1]) if tp else None

def main():
    ev_p, dur, ot0, out, rep_p = sys.argv[1:6]; narr = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None
    mp3 = sys.argv[7] if len(sys.argv) > 7 else None
    dur, ot0 = float(dur), float(ot0); events = json.load(open(ev_p))
    tmp = tempfile.mkdtemp(); og = 1.0; hist = []
    for it in range(4):
        sfx = synth(events, dur, ot0, og); sp = os.path.join(tmp, "sfx.wav"); wav(sp, sfx)
        ins = ["-i", sp] if not narr else ["-i", narr, "-i", sp]
        fc = ("[0:a]apad,atrim=0:%.4f[a]" % dur) if not narr else ("[0:a]aresample=48000,apad,atrim=0:%.4f[n];[n][1:a]amix=inputs=2:normalize=0:duration=longest,atrim=0:%.4f[a]" % (dur, dur))
        fc += ";[a]alimiter=limit=0.86:level=0:latency=1:attack=5:release=60,alimiter=limit=0.85:level=0:latency=1[o]"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[o]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out], check=True)
        I, tp = measure(out, ot0, dur - ot0); hist.append({"gain": round(og, 3), "lufs": I, "tp": tp})
        if abs(I + 11.5) <= 0.4 and tp is not None and tp <= -1.0: break
        og *= 10 ** ((-11.5 - I) / 20)
        if tp is not None and tp > -1.0: og *= 10 ** ((-1.2 - tp) / 20) if I > -12.5 else 1
    # 開頭起音：前 300 毫秒每 20 毫秒的音量
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", out, "-t", "0.3", "-ac", "1", "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(pcm, "<f4"); w = int(.02 * 48000)
    rms = [round(float(20 * np.log10(np.sqrt(np.mean(a[i:i + w] ** 2)) + 1e-9)), 1) for i in range(0, len(a) - w + 1, w)]
    rep = {"outro_t0": ot0, "dur": dur, "outro_lufs": hist[-1]["lufs"], "outro_true_peak_dbtp": hist[-1]["tp"], "tune": hist,
           "limiter": "alimiter limit 0.86/0.85, latency=1", "narration": narr or "（還沒有旁白，靜音＋音效）",
           "start_rms_db_20ms": rms, "start_ok": (rms[0] < max(rms) - 6) if narr else "無旁白：開頭 300 毫秒只有靜音（第 1 格非滿音量）",
           "events": events}
    json.dump(rep, open(rep_p, "w"), ensure_ascii=False, indent=1)
    if mp3:   # 片尾音效單獨一份（只有音效，含底墊）
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(ot0), "-i", out, "-t", str(dur - ot0), "-c:a", "libmp3lame", "-b:a", "192k", mp3], check=True)
    print("片尾 LUFS %.1f、true peak %s dBTP；調整紀錄 %s" % (hist[-1]["lufs"], hist[-1]["tp"], hist))

if __name__ == "__main__":
    main()
