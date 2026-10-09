"""哩股哩股宣傳影片背景音樂（自行合成，無版權疑慮）。

用 numpy 從零合成：電鋼琴和弦（Cmaj7 → Am7 → Fmaj7 → G7）＋簡單五聲音階旋律＋輕鼓點（大鼓、小鼓、腳踏鈸）＋極淡黑膠底噪。
90 BPM、長度 42 秒；前兩小節只有琴（痛點開場），第三小節起進鼓；最後一個 Cmaj7 延音並淡出，不會突然斷掉。

用法：python docs/marketing/video/make_music.py <輸出 wav 路徑>
"""
from __future__ import annotations

import sys
import wave

import numpy as np

SR = 44100
BPM = 90
BEAT = 60 / BPM
BAR = BEAT * 4
TOTAL = 42.0
rng = np.random.default_rng(1009)


def midi_hz(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def ep_note(freq: float, dur: float, vel: float = 0.5) -> np.ndarray:
    """電鋼琴音色：幾個泛音＋指數衰減＋一點點顫音。"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 300))
    rel = int(0.08 * SR)
    if n > rel:
        env[-rel:] *= np.linspace(1, 0, rel)
    trem = 1 + 0.04 * np.sin(2 * np.pi * 4.5 * t)
    sig = (np.sin(2 * np.pi * freq * t)
           + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 3)
           + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 6)
           + 0.05 * np.sin(2 * np.pi * 4.01 * freq * t) * np.exp(-t * 9))
    return sig * env * trem * vel


def add(buf: np.ndarray, sig: np.ndarray, start: float, pan: float = 0.0) -> None:
    i = int(start * SR)
    if i >= buf.shape[0]:
        return
    j = min(buf.shape[0], i + sig.shape[0])
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[: j - i] * l
    buf[i:j, 1] += sig[: j - i] * r


def kick() -> np.ndarray:
    t = np.arange(int(0.35 * SR)) / SR
    f = 50 + 70 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * 0.9


def snare() -> np.ndarray:
    t = np.arange(int(0.22 * SR)) / SR
    noise = rng.standard_normal(t.size)
    # 簡單低通，讓小鼓軟一點（lo-fi）
    k = np.ones(6) / 6
    noise = np.convolve(noise, k, mode="same")
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)
    return (noise * np.exp(-t * 18) * 0.35 + body * 0.25)


def hat() -> np.ndarray:
    t = np.arange(int(0.05 * SR)) / SR
    noise = rng.standard_normal(t.size)
    noise = np.diff(noise, prepend=0)  # 高通
    return noise * np.exp(-t * 90) * 0.08


def main(out: str) -> None:
    n = int(TOTAL * SR)
    buf = np.zeros((n, 2))
    # C 大調：Cmaj7 / Am7 / Fmaj7 / G7（低音＋三個內聲部）
    chords = [
        (36, [60, 64, 67, 71]),
        (45, [57, 60, 64, 67]),
        (41, [57, 60, 64, 65]),
        (43, [59, 62, 65, 67]),
    ]
    bars = 15
    for b in range(bars):
        root, notes = chords[b % 4]
        t0 = b * BAR
        add(buf, ep_note(midi_hz(root), BAR, 0.32), t0, -0.1)
        add(buf, ep_note(midi_hz(root + 12), BAR * 0.5, 0.12), t0 + BEAT * 2, -0.1)
        for k, nn in enumerate(notes):  # 輕微琶音（lo-fi 的「懶」手感）
            add(buf, ep_note(midi_hz(nn), BAR * 0.95, 0.13), t0 + k * 0.025, 0.2 - 0.12 * k)
        # 第二拍半再碰一次和弦（輕）
        for k, nn in enumerate(notes[1:]):
            add(buf, ep_note(midi_hz(nn), BEAT * 1.5, 0.06), t0 + BEAT * 2.5 + k * 0.02, 0.15)

    # 旋律：C 大調五聲音階，每小節一個小樂句；前兩小節較稀疏
    pent = [72, 74, 76, 79, 81, 84]
    phrases = [
        [(0.0, 76, 1.0), (1.5, 79, 0.5), (2.0, 81, 1.5)],
        [(0.5, 79, 1.0), (2.0, 76, 1.0), (3.0, 74, 1.0)],
        [(0.0, 72, 1.0), (1.0, 74, 0.5), (1.5, 76, 1.0), (3.0, 79, 1.0)],
        [(0.0, 81, 1.5), (2.0, 79, 1.0), (3.0, 74, 1.0)],
    ]
    for b in range(2, 14):
        for beat, note, d in phrases[b % 4]:
            if note not in pent:
                continue
            add(buf, ep_note(midi_hz(note), d * BEAT * 1.4, 0.16), b * BAR + beat * BEAT, 0.3)
    # 開頭兩小節只有一聲輕輕的提示音
    add(buf, ep_note(midi_hz(84), BEAT * 2, 0.08), BEAT * 6, 0.3)

    # 鼓：第 3 小節到第 14 小節；最後一小節只剩和弦
    K, S, H = kick(), snare(), hat()
    for b in range(2, 14):
        t0 = b * BAR
        add(buf, K, t0)
        add(buf, K * 0.7, t0 + BEAT * 2.5)
        add(buf, S, t0 + BEAT, 0.05)
        add(buf, S, t0 + BEAT * 3, 0.05)
        for e in range(8):
            swing = 0.06 if e % 2 else 0.0  # 搖擺八分音符
            add(buf, H * (0.9 if e % 2 else 1.2), t0 + e * BEAT / 2 + swing, -0.3)

    # 結尾：第 15 小節後再壓一個 Cmaj7（加九音）長延音
    end_t = bars * BAR
    for k, nn in enumerate([48, 60, 64, 67, 71, 74]):
        add(buf, ep_note(midi_hz(nn), TOTAL - end_t, 0.13), end_t + k * 0.04, 0.2 - 0.08 * k)

    # 極淡黑膠底噪（偶發的小爆音）
    crackle = np.zeros(n)
    idx = rng.integers(0, n, size=int(TOTAL * 6))
    crackle[idx] = rng.standard_normal(idx.size) * 0.05
    buf[:, 0] += crackle
    buf[:, 1] += np.roll(crackle, 37)

    # 整體淡入淡出、正規化
    fade_in = int(0.6 * SR)
    buf[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    fade_out = int(3.5 * SR)
    buf[-fade_out:] *= (np.linspace(1, 0, fade_out) ** 1.5)[:, None]
    buf = np.tanh(buf * 1.1)  # 軟限幅
    buf /= np.max(np.abs(buf)) + 1e-9
    buf *= 0.8
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"寫出 {out}：{TOTAL} 秒")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bgm_1009.wav")
