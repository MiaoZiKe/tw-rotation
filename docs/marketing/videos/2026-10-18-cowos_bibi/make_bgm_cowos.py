"""CoWoS 比比短影音配樂：沿用 docs/marketing/video/make_music.py 的自製音樂（numpy 從零合成，無版權疑慮）。

make_music.py 固定 45 秒、16 小節；這支片長由配音決定（約 60～75 秒），所以這裡直接用它的音色與鼓
（ep_note、kick、snare、hat、add），只把小節數改成依片長計算，其餘和弦進行、旋律、鼓型、收尾照原樣。

用法：python docs/marketing/videos/2026-10-18-cowos_bibi/make_bgm_cowos.py <輸出 wav> <秒數>
"""
from __future__ import annotations

import importlib.util
import sys
import wave
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("make_music", REPO / "docs" / "marketing" / "video" / "make_music.py")
mm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mm)
SR, BEAT, BAR = mm.SR, mm.BEAT, mm.BAR


def compose(out: str, total: float) -> None:
    n = int(total * SR)
    buf = np.zeros((n, 2))
    chords = [(36, [60, 64, 67, 71]), (45, [57, 60, 64, 67]), (41, [57, 60, 64, 65]), (43, [59, 62, 65, 67])]
    bars = max(8, int((total - 3.0) / BAR))
    for b in range(bars):
        root, notes = chords[b % 4]
        t0 = b * BAR
        mm.add(buf, mm.ep_note(mm.midi_hz(root), BAR, 0.32), t0, -0.1)
        mm.add(buf, mm.ep_note(mm.midi_hz(root + 12), BAR * 0.5, 0.12), t0 + BEAT * 2, -0.1)
        for k, nn in enumerate(notes):
            mm.add(buf, mm.ep_note(mm.midi_hz(nn), BAR * 0.95, 0.13), t0 + k * 0.025, 0.2 - 0.12 * k)
        for k, nn in enumerate(notes[1:]):
            mm.add(buf, mm.ep_note(mm.midi_hz(nn), BEAT * 1.5, 0.06), t0 + BEAT * 2.5 + k * 0.02, 0.15)
    phrases = [
        [(0.0, 76, 1.0), (1.5, 79, 0.5), (2.0, 81, 1.5)],
        [(0.5, 79, 1.0), (2.0, 76, 1.0), (3.0, 74, 1.0)],
        [(0.0, 72, 1.0), (1.0, 74, 0.5), (1.5, 76, 1.0), (3.0, 79, 1.0)],
        [(0.0, 81, 1.5), (2.0, 79, 1.0), (3.0, 74, 1.0)],
    ]
    for b in range(2, bars - 1):
        for beat, note, d in phrases[b % 4]:
            mm.add(buf, mm.ep_note(mm.midi_hz(note), d * BEAT * 1.4, 0.16), b * BAR + beat * BEAT, 0.3)
    mm.add(buf, mm.ep_note(mm.midi_hz(84), BEAT * 2, 0.08), BEAT * 6, 0.3)
    K, S, H = mm.kick(), mm.snare(), mm.hat()
    for b in range(2, bars - 1):
        t0 = b * BAR
        mm.add(buf, K, t0)
        mm.add(buf, K * 0.7, t0 + BEAT * 2.5)
        mm.add(buf, S, t0 + BEAT, 0.05)
        mm.add(buf, S, t0 + BEAT * 3, 0.05)
        for e in range(8):
            swing = 0.06 if e % 2 else 0.0
            mm.add(buf, H * (0.9 if e % 2 else 1.2), t0 + e * BEAT / 2 + swing, -0.3)
    end_t = bars * BAR
    for k, nn in enumerate([48, 60, 64, 67, 71, 74]):
        mm.add(buf, mm.ep_note(mm.midi_hz(nn), total - end_t, 0.13), end_t + k * 0.04, 0.2 - 0.08 * k)
    rng = np.random.default_rng(1018)
    crackle = np.zeros(n)
    idx = rng.integers(0, n, size=int(total * 6))
    crackle[idx] = rng.standard_normal(idx.size) * 0.05
    buf[:, 0] += crackle
    buf[:, 1] += np.roll(crackle, 37)
    fi = int(0.6 * SR)
    buf[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo = int(3.0 * SR)
    buf[-fo:] *= (np.linspace(1, 0, fo) ** 1.5)[:, None]
    buf = np.tanh(buf * 1.1)
    buf /= np.max(np.abs(buf)) + 1e-9
    buf *= 0.8
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    print(f"寫出 {out}：{total:.2f} 秒、{bars} 小節")


if __name__ == "__main__":
    compose(sys.argv[1], float(sys.argv[2]))
