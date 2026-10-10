"""哩股哩股 1010 宣傳片配樂＋音效（numpy 從零合成，無版權疑慮）。

120 BPM、G 大調、明亮流行：木琴旋律＋撥弦和弦＋拍手＋輕鼓組＋貝斯；無人聲。
結構（主版）：0–3 秒只有上升音＋撥弦 → 3.0 秒全編制 → 34.5 秒副歌（最滿）→ 51 秒回主歌 → 75 秒收尾和弦 → 78 秒退成長音，
警語段音量 ≤ 平常一半並淡出。短版另有自己的結構（--cut short）。
音效（點擊「滴」、轉場「咻」、「叮」、「噗」…）讀 render_1010.py --cues 輸出的時間表，比音樂低約 6dB。

用法：python make_music_1010.py --cues cues.json --out bgm.wav [--cut main|short]
"""
from __future__ import annotations

import argparse
import json
import wave

import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(1010)


def hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_ad(n, a=0.004, d=4.0):
    t = np.arange(n) / SR
    e = np.exp(-t * d) * np.clip(t / a, 0, 1)
    r = min(n, int(0.03 * SR))
    e[-r:] *= np.linspace(1, 0, r)
    return e


def marimba(f, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 18) + 0.1 * np.sin(2 * np.pi * 10 * f * t) * np.exp(-t * 40)
    return s * env_ad(n, 0.002, 5.5) * vel


def pluck(f, dur, vel):
    """Karplus–Strong 撥弦。"""
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    return out * vel * env_ad(n, 0.001, 1.5)


def bass(f, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    return np.tanh(s * 1.5) * env_ad(n, 0.005, 3.0) * vel


def kick():
    t = np.arange(int(0.3 * SR)) / SR
    f = 48 + 90 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10) * 0.9


def clap():
    t = np.arange(int(0.2 * SR)) / SR
    nz = rng.standard_normal(t.size); nz = np.diff(nz, prepend=0)
    e = np.exp(-t * 25) + 0.6 * np.exp(-np.maximum(t - 0.012, 0) * 30) * (t > 0.012) + 0.4 * np.exp(-np.maximum(t - 0.024, 0) * 30) * (t > 0.024)
    return nz * e * 0.22


def hat(open_=False):
    t = np.arange(int((0.18 if open_ else 0.05) * SR)) / SR
    nz = np.diff(rng.standard_normal(t.size), prepend=0)
    return nz * np.exp(-t * (20 if open_ else 90)) * 0.07


def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 300 + 1500 * (t / dur) ** 2
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) * 0.12


def add(buf, sig, start, pan=0.0, gain=1.0):
    i = int(start * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(sig))
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[: j - i] * l * gain
    buf[i:j, 1] += sig[: j - i] * r * gain


# ── 音效 ──
def sfx(kind):
    t = lambda d: np.arange(int(d * SR)) / SR
    if kind in ("tap", "blip"):
        x = t(0.12); f = 1760 if kind == "tap" else 1320
        return np.sin(2 * np.pi * f * x) * np.exp(-x * 40) * 0.35
    if kind in ("whoosh", "swish"):
        x = t(0.35); nz = rng.standard_normal(x.size)
        k = np.ones(8) / 8; nz = np.convolve(nz, k, "same")
        e = np.sin(np.pi * x / 0.35) ** 2
        return nz * e * (0.25 if kind == "whoosh" else 0.2)
    if kind == "ding":
        x = t(0.8)
        return (np.sin(2 * np.pi * 2093 * x) + 0.5 * np.sin(2 * np.pi * 3136 * x)) * np.exp(-x * 5) * 0.22
    if kind in ("boop", "pop", "thud"):
        x = t(0.18); f0 = {"boop": 520, "pop": 700, "thud": 160}[kind]
        f = f0 * (1 + 0.8 * np.exp(-x * 30))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 22) * 0.35
    if kind == "chirp":
        x = t(0.15); f = 1800 + 1600 * x / 0.15
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 15) * 0.2
    if kind == "rise":
        return riser(0.6) * 1.5
    return None


PROG = [(43, [67, 71, 74]), (40, [64, 67, 71]), (36, [64, 67, 72]), (38, [66, 69, 74])]  # G Em C D
MEL = [[(0, 79, 1), (1, 81, .5), (1.5, 83, 1), (3, 79, 1)],
       [(0, 76, 1), (1.5, 79, .5), (2, 83, 1), (3, 81, 1)],
       [(0, 79, .5), (.5, 81, .5), (1, 84, 1), (2.5, 83, .5), (3, 81, 1)],
       [(0, 78, 1), (1, 81, 1), (2, 86, 1.5)]]


def music(total, plan):
    """plan: list of (t0, t1, level) level: 0=intro 1=verse 2=chorus 3=outro-hold."""
    buf = np.zeros((int(total * SR) + SR, 2))
    nbars = int(total / BAR) + 1
    K, C = kick(), clap()
    for b in range(nbars):
        t0 = b * BAR
        lv = 0
        for a, z, l in plan:
            if a <= t0 + 1e-6 < z:
                lv = l
        if lv == -1:
            continue
        root, ch = PROG[b % 4]
        if lv == 3:     # 收尾長音
            for k, nn in enumerate([55, 62, 67, 71, 74]):
                add(buf, marimba(hz(nn), 4.0, 0.12) * np.linspace(1, 0.6, int(4.0 * SR)), t0 + k * 0.03, 0.2 - 0.1 * k)
            continue
        # 撥弦和弦：八分音符
        for e in range(8):
            for k, nn in enumerate(ch):
                add(buf, pluck(hz(nn), 0.35, 0.10 if lv else 0.08), t0 + e * BEAT / 2 + k * 0.008, -0.35 + 0.1 * k)
        if lv >= 1:
            for e in range(4):
                add(buf, bass(hz(root), BEAT * 0.9, 0.35), t0 + e * BEAT)
            for e in range(4):
                add(buf, K, t0 + e * BEAT, 0, 0.9 if lv == 2 else 0.7)
            add(buf, C, t0 + BEAT, 0.1); add(buf, C, t0 + 3 * BEAT, 0.1)
            for e in range(8):
                add(buf, hat(open_=(lv == 2 and e % 2 == 1)), t0 + e * BEAT / 2, 0.35)
            for beat, nn, d in MEL[b % 4]:
                add(buf, marimba(hz(nn), d * BEAT * 1.2, 0.20 if lv == 2 else 0.15), t0 + beat * BEAT, 0.25)
                if lv == 2:
                    add(buf, marimba(hz(nn + 12), d * BEAT, 0.07), t0 + beat * BEAT + 0.01, 0.4)
    return buf[: int(total * SR)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cut", default="main")
    a = ap.parse_args()
    cj = json.load(open(a.cues))
    total = cj["total"]
    shots = {sid: (t0, d) for sid, t0, d in cj["shots"]}
    if a.cut == "main":
        plan = [(0, 3.0, 0), (3.0, 34.5, 1), (34.5, 51.0, 2), (51.0, 75.0, 1), (75.0, 79.0, 3), (79.0, 999, -1)]
        disc_t0 = shots["40"][0]
    else:
        plan = [(0, 1.5, 0), (1.5, 13.0, 2), (13.0, 17.0, 3), (17.0, 999, -1)]
        disc_t0 = shots["s9"][0]
    m = music(total, plan)
    # 3D 副歌前的上升音
    if a.cut == "main":
        add(m, riser(1.0), 33.5, 0, 1.0)
        add(m, riser(1.5), 1.5, 0, 0.8)
    # 片尾警語：音量降到一半以下並淡出
    i0 = int(disc_t0 * SR)
    g = np.ones(len(m))
    g[i0:] = np.linspace(0.45, 0.0, len(m) - i0) ** 1.3
    # 收尾和弦前 0.3 秒漸弱
    m *= g[:, None]
    m = np.tanh(m * 1.2)
    m /= np.max(np.abs(m)) + 1e-9
    m *= 0.62
    # 音效（約 -6dB 相對音樂峰值）
    fx = np.zeros_like(m)
    for t, kind in cj["cues"]:
        s = sfx(kind)
        if s is not None:
            add(fx, s, t, 0.0, 1.0)
    if np.max(np.abs(fx)) > 0:
        fx = fx / np.max(np.abs(fx)) * 0.31
    out = m + fx
    fi = int(0.05 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out = np.clip(out, -0.98, 0.98)
    pcm = (out * 32767).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("寫出", a.out, round(total, 2), "秒")


if __name__ == "__main__":
    main()
