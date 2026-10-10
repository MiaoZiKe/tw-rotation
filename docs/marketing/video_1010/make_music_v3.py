"""哩股哩股宣傳片第 3 版配樂＋柔和音效（numpy 從零合成，無版權疑慮）。

可愛輕快、配合吉祥物比比：約 100 BPM、F 大調；木琴主旋律＋鐵琴點綴＋烏克麗麗刷弦＋輕拍手＋沙鈴＋軟貝斯；
沒有電子快拍、沒有人聲。結構：前奏（只有烏克麗麗＋鐵琴）→ 主歌 → 副歌（木琴＋鐵琴八度）→ 間奏 → 主歌 → 副歌 → 尾奏，
最後一小節回到主和弦（I）延音自然收尾，不是硬淡出。

音效（柔和版）：
- tap   踩按鈕：木魚感「啵」（低通短正弦，帶一點點木頭泛音）
- draw  框線描出：鐵琴三音上行（輕）
- zoom  推近：柔和氣音上揚（低通雜訊＋淡淡的上行音）
- pop / ding / swish：比比出場、片尾、轉場，都比 v1 輕、短、低頻

用法：
  python make_music_v3.py --length 150 --out bgm_150.wav
  python make_music_v3.py --length 110 --out bgm_110.wav --cues cues.json   # cues.json：{"cues": [[秒, 種類], ...]}
"""
from __future__ import annotations

import argparse
import json
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(1011)


def hz(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def _env(n, a, d, rel=0.03):
    t = np.arange(n) / SR
    e = np.exp(-t * d) * np.clip(t / max(a, 1e-4), 0, 1)
    r = min(n, int(rel * SR))
    if r > 0:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def marimba(f, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * 3.9 * f * t) * np.exp(-t * 20)
         + 0.06 * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t * 45))
    return s * _env(n, 0.003, 4.2) * vel


def glock(f, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 6) + 0.2 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t * 12)
    return s * _env(n, 0.001, 2.2) * vel


def uke(f, dur, vel):
    """Karplus–Strong 尼龍弦（較圓、較快衰減）。"""
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    buf = np.convolve(buf, np.ones(3) / 3, "same")
    out = np.zeros(n)
    idx = 0
    for i in range(n):
        out[i] = buf[idx]
        nxt = (idx + 1) % p
        buf[idx] = 0.5 * (buf[idx] + buf[nxt]) * 0.993
        idx = nxt
    return out * vel * _env(n, 0.002, 2.4)


def bass(f, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(2 * np.pi * 2 * f * t)
    return s * _env(n, 0.01, 3.0, 0.05) * vel


def clap():
    t = np.arange(int(0.16 * SR)) / SR
    nz = np.convolve(rng.standard_normal(t.size), np.ones(4) / 4, "same")
    e = np.exp(-t * 30) + 0.5 * np.exp(-np.maximum(t - 0.011, 0) * 32) * (t > 0.011)
    return nz * e * 0.12


def shaker():
    t = np.arange(int(0.07 * SR)) / SR
    nz = np.diff(rng.standard_normal(t.size), prepend=0)
    return nz * np.sin(np.pi * t / 0.07) ** 2 * 0.035


def softkick():
    t = np.arange(int(0.25 * SR)) / SR
    f = 55 + 45 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.45


def add(buf, sig, start, pan=0.0, gain=1.0):
    i = int(start * SR)
    if i >= len(buf) or i < 0:
        return
    j = min(len(buf), i + len(sig))
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[: j - i] * l * gain
    buf[i:j, 1] += sig[: j - i] * r * gain


# F 大調：F – Dm – B♭ – C（I vi IV V），烏克麗麗開放把位感（高音域）
PROG = [(41, [65, 69, 72, 77]), (38, [62, 65, 69, 74]), (34, [62, 65, 70, 74]), (36, [64, 67, 72, 76])]
# 旋律（拍, 音, 長度）— 五聲為主、跳進少，可愛但不吵
MEL_A = [[(0, 72, 1), (1, 74, .5), (1.5, 77, 1.5), (3, 76, 1)],
         [(0, 74, 1.5), (1.5, 72, .5), (2, 69, 2)],
         [(0, 70, 1), (1, 74, 1), (2, 77, 1), (3, 79, 1)],
         [(0, 76, 2), (2, 74, 1), (3, 72, 1)]]
MEL_B = [[(0, 77, 1), (1, 79, .5), (1.5, 81, 1.5), (3, 79, .5), (3.5, 77, .5)],
         [(0, 74, 1.5), (1.5, 77, .5), (2, 81, 2)],
         [(0, 82, 1), (1, 81, .5), (1.5, 79, 1), (2.5, 77, .5), (3, 74, 1)],
         [(0, 76, 1), (1, 79, 1), (2, 77, 2)]]


def sfx(kind):
    t = lambda d: np.arange(int(d * SR)) / SR
    if kind in ("tap", "blip"):
        x = t(0.16); f = 880 if kind == "tap" else 1175
        s = np.sin(2 * np.pi * f * x) * np.exp(-x * 38) + 0.25 * np.sin(2 * np.pi * f * 2.3 * x) * np.exp(-x * 70)
        return s * 0.28
    if kind == "draw":
        out = np.zeros(int(0.7 * SR))
        for k, n in enumerate([84, 88, 91]):
            g = glock(hz(n), 0.55, 0.16)
            i = int(k * 0.11 * SR); out[i:i + len(g)] += g[: len(out) - i]
        return out
    if kind == "zoom":
        x = t(0.6); nz = np.convolve(rng.standard_normal(x.size), np.ones(40) / 40, "same")
        e = np.sin(np.pi * x / 0.6) ** 2
        f = 500 + 400 * x / 0.6
        return (nz * 1.6 + 0.12 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * e * 0.22
    if kind in ("whoosh", "swish"):
        x = t(0.4); nz = np.convolve(rng.standard_normal(x.size), np.ones(30) / 30, "same")
        return nz * np.sin(np.pi * x / 0.4) ** 2 * 0.5
    if kind in ("pop", "boop", "thud"):
        x = t(0.14); f = 620 * (1 + 0.4 * np.exp(-x * 40))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 26) * 0.26
    if kind in ("ding", "chirp", "chord", "chord_end"):
        out = np.zeros(int(1.2 * SR))
        for k, n in enumerate([77, 81, 84]):
            g = glock(hz(n), 1.1, 0.12)
            i = int(k * 0.03 * SR); out[i:i + len(g)] += g[: len(out) - i]
        return out
    return None


def music(total, bpm):
    beat = 60 / bpm
    bar = beat * 4
    nbars = int((total - 1.5) // bar)          # 留 ≥1.5 秒給最後的延音
    end_t = nbars * bar
    buf = np.zeros((int((total + 0.5) * SR), 2))
    K, C, S = softkick(), clap(), shaker()
    # 段落：前奏 2 小節、之後 8 小節一循環（主歌 4＋副歌 4），尾奏 = 最後 2 小節
    for b in range(nbars):
        t0 = b * bar
        intro = b < 2
        outro = b >= nbars - 2
        chorus = (not intro) and ((b - 2) % 8 >= 4)
        root, ch = PROG[b % 4]
        # 烏克麗麗刷弦：下 下上 上下上（島嶼刷法）
        pattern = [(0, 1, .9), (1, 1, .7), (1.5, -1, .5), (2.5, -1, .5), (3, 1, .7), (3.5, -1, .5)]
        for bt, d, v in pattern:
            notes = ch if d > 0 else ch[::-1]
            for k, nn in enumerate(notes):
                add(buf, uke(hz(nn), beat * 1.2, 0.09 * v * (0.8 if outro else 1)), t0 + bt * beat + k * 0.012, -0.3 + 0.12 * k)
        if intro:
            add(buf, glock(hz(ch[-1] + 12), 1.0, 0.07), t0 + 2 * beat, 0.4)
            continue
        for e in (0, 2):
            add(buf, bass(hz(root), beat * 1.7, 0.30), t0 + e * beat)
        add(buf, K, t0, 0, 0.8); add(buf, K, t0 + 2 * beat, 0, 0.6)
        add(buf, C, t0 + beat, 0.15); add(buf, C, t0 + 3 * beat, 0.15)
        for e in range(8):
            add(buf, S, t0 + e * beat / 2 + (0.02 if e % 2 else 0), 0.45, 1.2 if e % 2 else 0.8)
        mel = (MEL_B if chorus else MEL_A)[b % 4]
        for bt, nn, d in mel:
            add(buf, marimba(hz(nn), d * beat * 1.3, 0.17 if chorus else 0.14), t0 + bt * beat, 0.2)
            if chorus:
                add(buf, glock(hz(nn + 12), d * beat, 0.045), t0 + bt * beat + 0.012, 0.45)
    # 收尾：主和弦（F add9）延音
    for k, nn in enumerate([41, 53, 65, 69, 72, 77, 79]):
        add(buf, uke(hz(nn), total - end_t + 0.4, 0.10) if nn > 60 else bass(hz(nn), 2.0, 0.3), end_t + k * 0.025, -0.3 + 0.1 * k)
    add(buf, glock(hz(84), 2.0, 0.10), end_t + 0.2, 0.3)
    add(buf, marimba(hz(77), 1.5, 0.14), end_t, 0.2)
    buf = buf[: int(total * SR)]
    # 尾端 0.6 秒才收到 0（延音本身已經衰減，聽起來是自然收）
    fo = int(0.6 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return buf


# ───────────────────────── 專業版（--style pro） ─────────────────────────
def piano(f, dur, vel):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2.003 * f * t) * np.exp(-t * 1.5)
         + 0.2 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 3) + 0.08 * np.sin(2 * np.pi * 4.02 * f * t) * np.exp(-t * 5))
    return s * _env(n, 0.004, 1.3, 0.12) * vel


def pad(freqs, dur, vel):
    """柔和弦樂鋪底：多個微失諧鋸齒波低通＋慢起音。"""
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for f in freqs:
        for dt in (-0.12, 0.0, 0.11):
            ph = 2 * np.pi * f * (1 + dt / 100) * t
            s += sum(np.sin(k * ph) / k for k in range(1, 6))
    k = int(SR / 2500)
    s = np.convolve(s, np.ones(k) / k, "same")
    a = np.clip(t / 0.8, 0, 1)
    r = np.clip((dur - t) / 0.6, 0, 1)
    return s * a * r * vel / len(freqs)


def pulse(f, dur, vel):
    """輕合成器脈衝：短方波低通。"""
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * f * t))
    k = int(SR / 1800)
    s = np.convolve(s, np.ones(k) / k, "same")
    return s * _env(n, 0.003, 9.0) * vel


def rim():
    t = np.arange(int(0.06 * SR)) / SR
    return (np.sin(2 * np.pi * 1700 * t) * 0.5 + np.diff(rng.standard_normal(t.size), prepend=0) * 0.3) * np.exp(-t * 90) * 0.18


# C 大調：Am – F – C – G（vi IV I V），專業、穩、略帶推進感
PRO_PROG = [(45, [57, 60, 64, 69]), (41, [57, 60, 65, 69]), (48, [55, 60, 64, 67]), (43, [55, 59, 62, 67])]
PRO_MEL = [[(0, 76, 1.5), (1.5, 72, .5), (2, 74, 2)], [(0, 72, 1), (1, 69, 1), (2, 72, 2)],
           [(0, 76, 1), (1, 79, 1), (2, 76, 1), (3, 74, 1)], [(0, 74, 2), (2, 71, 1), (3, 74, 1)]]


def music_pro(total, bpm):
    beat = 60 / bpm
    bar = beat * 4
    nbars = int((total - 2.0) // bar)
    end_t = nbars * bar
    buf = np.zeros((int((total + 0.5) * SR), 2))
    K = softkick()
    for b in range(nbars):
        t0 = b * bar
        intro = b < 2
        outro = b >= nbars - 2
        peak = (not intro) and ((b - 2) % 8 >= 4)
        root, ch = PRO_PROG[b % 4]
        add(buf, pad([hz(n) for n in ch], bar + 0.4, 0.10 if peak else 0.075), t0, 0.0)
        # 鋼琴分解和弦（八分音符）
        arp = [ch[0], ch[2], ch[1], ch[3], ch[2], ch[1], ch[3], ch[2]]
        for e, nn in enumerate(arp):
            add(buf, piano(hz(nn), beat * 1.4, 0.07), t0 + e * beat / 2, -0.25 + 0.06 * e)
        if intro:
            continue
        add(buf, bass(hz(root), bar * 0.95, 0.26), t0)
        for e in range(8):
            add(buf, pulse(hz(root + 24), beat / 2 * 0.9, 0.035 * (1.2 if e % 2 else 1)), t0 + e * beat / 2, 0.3)
        add(buf, K, t0, 0, 0.55); add(buf, K, t0 + 2 * beat, 0, 0.45)
        if peak:
            add(buf, K, t0 + 2.5 * beat, 0, 0.3)
        add(buf, rim(), t0 + beat, 0.1); add(buf, rim(), t0 + 3 * beat, 0.1)
        for bt, nn, d in PRO_MEL[b % 4]:
            add(buf, piano(hz(nn), d * beat * 1.4, 0.15 if peak else 0.12 * (0.8 if outro else 1)), t0 + bt * beat, 0.1)
    for k, nn in enumerate([48, 55, 60, 64, 67, 72]):
        add(buf, piano(hz(nn), total - end_t + 0.4, 0.11), end_t + k * 0.02, -0.2 + 0.08 * k)
    add(buf, pad([hz(60), hz(64), hz(67)], total - end_t + 0.3, 0.08), end_t)
    buf = buf[: int(total * SR)]
    fo = int(0.8 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return buf


def sfx_pro(kind):
    t = lambda d: np.arange(int(d * SR)) / SR
    if kind in ("tap", "blip"):
        x = t(0.05)
        return np.sin(2 * np.pi * (2400 if kind == "tap" else 1900) * x) * np.exp(-x * 120) * 0.18
    if kind == "draw":
        x = t(0.35); f = 900 + 900 * x / 0.35
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x / 0.35) ** 2 * 0.05
    if kind in ("zoom", "whoosh", "swish"):
        x = t(0.45); nz = np.convolve(rng.standard_normal(x.size), np.ones(60) / 60, "same")
        return nz * np.sin(np.pi * x / 0.45) ** 2 * 0.9
    if kind in ("ding", "chord", "chord_end", "chirp", "pop", "boop", "thud"):
        x = t(0.6)
        return (np.sin(2 * np.pi * 1318.5 * x) + 0.4 * np.sin(2 * np.pi * 1975.5 * x)) * np.exp(-x * 7) * 0.08
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--length", type=float, required=True)
    ap.add_argument("--bpm", type=float, default=0, help="預設 cute=100、pro=114")
    ap.add_argument("--style", choices=["cute", "pro"], default="cute")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cues", default="")
    ap.add_argument("--duck", default="", help="從這一秒起音量降到一半以下（警語段），例如 140.5")
    a = ap.parse_args()
    bpm = a.bpm or (114 if a.style == "pro" else 100)
    a.bpm = bpm
    m = music_pro(a.length, bpm) if a.style == "pro" else music(a.length, bpm)
    if a.duck:
        i0 = int(float(a.duck) * SR)
        g = np.ones(len(m)); g[i0:] = 0.45
        ramp = min(len(m) - i0, int(0.4 * SR))
        g[i0:i0 + ramp] = np.linspace(1, 0.45, ramp)
        m *= g[:, None]
    m = np.tanh(m * 1.3)
    m /= np.max(np.abs(m)) + 1e-9
    m *= 0.6
    if a.cues:
        fx = np.zeros_like(m)
        for t, kind in json.load(open(a.cues))["cues"]:
            s = sfx_pro(kind) if a.style == "pro" else sfx(kind)
            if s is not None:
                add(fx, s, t)
        if np.max(np.abs(fx)) > 0:
            fx = fx / np.max(np.abs(fx)) * (0.18 if a.style == "pro" else 0.3)   # cute 約低 6dB、pro 約低 10dB
        m = m + fx
    m[: int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))[:, None]
    pcm = (np.clip(m, -0.98, 0.98) * 32767).astype(np.int16)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("寫出", a.out, a.length, "秒", a.bpm, "BPM")


if __name__ == "__main__":
    main()
