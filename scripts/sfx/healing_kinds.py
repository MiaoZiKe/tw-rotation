"""頻道④「談晴說礙」生活類音效（金錢／文書／數字動作）。由 sfx-synth.py 啟動時自動載入。
全部輕、短、不刺耳；不改②既有種類。whoosh（輕掃入場）沿用 sfx-synth.py 內建，用 params.strength 0.3~0.5 調輕。
新增種類：coin 硬幣落下｜cashier 收銀機叮｜calculator 按鍵嗶｜stamp 蓋章｜paperslide 紙張滑入｜tick 數字跳動
"""
import numpy as np


def install(S):
    SR, white, fft, norm, ef = S.SR, S.white, S.fft_filter, S.norm, S.env_fade
    rng = S.rng

    def add(y, t0, d):
        e = min(len(d), len(y) - t0)
        if e > 0: y[t0:t0 + e] += d[:e]

    def s_coin(dur=0.0, bounces=2):
        y = np.zeros(int(0.9 * SR)); t = 0.0; a = 1.0
        for i in range(bounces + 1):
            f = rng.uniform(2300, 2900)
            n = int(0.35 * SR); tt = np.arange(n) / SR
            d = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.51 * tt)) * np.exp(-tt / 0.06) * a
            add(y, int(t * SR), d); t += 0.13 * (0.65 ** i) + 0.05; a *= 0.55
        return norm(y) * 0.8

    def s_cashier(dur=0.0):
        n = int(0.8 * SR); t = np.arange(n) / SR
        y = (np.sin(2 * np.pi * 2637 * t) + 0.4 * np.sin(2 * np.pi * 3951 * t)) * np.exp(-t / 0.22)
        c = int(0.02 * SR); y[:c] += fft(white(c), 800, 4000) * 1.5 * np.exp(-np.arange(c) / (0.004 * SR))
        return norm(y) * 0.8

    def s_calculator(dur=0.0, n=4, gap=0.13):
        y = np.zeros(int((gap * n + 0.2) * SR))
        for i in range(n):
            L = int(0.05 * SR); t = np.arange(L) / SR
            f = 1700 + 90 * (i % 4)
            add(y, int(i * gap * SR), np.sin(2 * np.pi * f * t) * np.sin(np.pi * t / t[-1]) ** 0.5 * 0.9)
        return norm(y) * 0.7

    def s_stamp(dur=0.0):
        n = int(0.4 * SR); t = np.arange(n) / SR
        y = np.sin(2 * np.pi * 105 * t) * np.exp(-t / 0.05) + fft(white(n), 500, 2800) * np.exp(-t / 0.015) * 0.7
        return norm(y) * 0.9

    def s_paperslide(dur=0.0):
        n = int(0.38 * SR); u = np.arange(n) / n
        y = fft(white(n), 1500, 6500) * np.sin(np.pi * u ** 0.7) ** 2
        return norm(y) * 0.6

    def s_tick(dur=0.0, n=6, gap=0.09):
        y = np.zeros(int((gap * n + 0.1) * SR))
        for i in range(n):
            L = int(0.03 * SR); t = np.arange(L) / SR
            add(y, int(i * gap * SR), np.sin(2 * np.pi * 1300 * t) * np.exp(-t / 0.006) * (0.6 + 0.4 * rng.random()))
        return norm(y) * 0.7

    S.register('coin', s_coin, -4)
    S.register('cashier', s_cashier, -5)
    S.register('calculator', s_calculator, -6)
    S.register('stamp', s_stamp, -2)
    S.register('paperslide', s_paperslide, -5)
    S.register('tick', s_tick, -8)
