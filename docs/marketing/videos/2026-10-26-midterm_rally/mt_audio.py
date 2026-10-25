"""期中選舉短片：混音（配音＋底樂側鏈壓低＋輕音效≤8）與成片響度（-14 LUFS）。
用法：python mt_audio.py <silent.mp4> <輸出 mp4>
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_midterm as R
from mt_core import SCR

SR = 44100
BGM = Path("/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/hbm/bgm.wav")


def read_wav(p):
    with wave.open(str(p)) as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    return a.reshape(-1, ch), sr


def resample(a, sr, to=SR):
    if sr == to:
        return a
    idx = np.arange(0, len(a) * to / sr) * sr / to
    return np.interp(idx, np.arange(len(a)), a).astype(np.float32)


def whoosh(dur=0.34):
    n = int(dur * SR)
    rng = np.random.default_rng(7)
    x = rng.standard_normal(n).astype(np.float32)
    t = np.linspace(0, 1, n)
    # 單極低通，截止頻率由低掃到高再收（簡單的氣流聲）
    fc = 500 + 3500 * np.sin(np.pi * t) ** 1.5
    y = np.zeros(n, np.float32)
    s = 0.0
    for i in range(n):
        a = 1 - np.exp(-2 * np.pi * fc[i] / SR)
        s += a * (x[i] - s)
        y[i] = s
    env = np.sin(np.pi * t) ** 2
    y *= env
    return y / (np.abs(y).max() + 1e-9)


def tick():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 70)).astype(np.float32)


def main():
    silent, out = sys.argv[1], sys.argv[2]
    R.build_timeline()
    total = R.TOTAL
    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    speak = np.zeros(n, np.float32)
    for lid, ln in R.LINES.items():
        a = resample(ln.audio, ln.sr)
        s = int((ln.start - ln.on) * SR)
        if s < 0:
            a, s = a[-s:], 0
        e = min(n, s + len(a))
        voice[s:e] += a[:e - s]
        speak[int(ln.start * SR):int(ln.end * SR)] = 1.0
    voice *= 0.89 / (np.max(np.abs(voice)) + 1e-9)
    # 配音在說話區間的 RMS（dBFS）
    act = speak > 0
    v_rms = float(np.sqrt(np.mean(voice[act] ** 2)))
    b, sr = read_wav(BGM)
    b = np.stack([resample(b[:, 0], sr), resample(b[:, -1], sr)], axis=1)
    if len(b) < n:
        reps = int(np.ceil(n / len(b)))
        b = np.tile(b, (reps, 1))
    b = b[:n]
    b_rms = float(np.sqrt(np.mean(b ** 2)))
    k = int(0.30 * SR)
    env = np.convolve(speak, np.ones(k) / k, mode="same")
    env = np.clip(env * 1.6, 0, 1)
    duck_db = -21.0                              # 說話時：底樂比人聲低 21 dB
    gain_db = duck_db + (1 - env) * 6.0          # 沒人說話時回升 6 dB
    gain = (v_rms / b_rms) * 10 ** (gain_db / 20)
    bgm = b * gain[:, None]
    # 淡入淡出（只動音訊）
    fi, fo = int(0.5 * SR), int(0.8 * SR)
    bgm[:fi] *= np.linspace(0, 1, fi)[:, None]
    end_i = int(total * SR)
    bgm[end_i - fo:end_i] *= np.linspace(1, 0, fo)[:, None]
    mix = bgm + voice[:, None]
    # 音效（最多 8 個，峰值比配音低 ≥12 dB）
    sfx_peak = 0.89 * 10 ** (-12 / 20)
    marks = []
    sc = {s[0]: s for s in R.SCENES}
    for sid in ("B", "C", "D", "H", "I", "J", "K"):
        marks.append((sc[sid][2], "whoosh"))
    marks.append((R.LINES["S03"].at("七點六"), "tick"))
    assert len(marks) <= 8
    for (tt, kind) in marks:
        w = whoosh() if kind == "whoosh" else tick()
        w = w * sfx_peak * (0.9 if kind == "whoosh" else 0.7)
        s0 = int(max(0.0, tt - (0.05 if kind == "whoosh" else 0.0)) * SR)
        mix[s0:s0 + len(w), :] += w[:, None]
    mix = mix[:end_i]
    pre = SCR / "mix_pre.wav"
    with wave.open(str(pre), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -0.99, 0.99) * 32767).astype(np.int16).tobytes())
    # 響度：兩段式 loudnorm 到 -14 LUFS、真峰值 -1 dB
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(pre), "-af", "loudnorm=I=-14:TP=-1:LRA=7:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rindex("{"):])
    flt = (f"loudnorm=I=-14:TP=-1:LRA=7:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
           f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    post = SCR / "mix_post.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(pre), "-af", flt, "-ar", "44100", str(post)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", str(post), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    # 實測
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rindex("Integrated loudness"):]
    print(tail)
    info = {"voice_rms_dbfs": 20 * np.log10(v_rms), "bgm_gain_speech_db": duck_db, "sfx": [(round(t, 2), k) for t, k in marks],
            "loudnorm_in": js}
    (SCR / "audio_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
