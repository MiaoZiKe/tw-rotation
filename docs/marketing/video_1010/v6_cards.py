"""第 6 版卡片鏡（storyboard_v6_web.md 第 0、16 節）：沿用第 4／5 版卡片（v4_cards.py，不改），只加兩件事：
  ① 開場三張痛點卡整段 1.2 倍速（2.8 秒播完原本 3.36 秒的動畫，慢推照真實時間走、不停格）；
  ② 比比「兩拍」：卡片上的比比在指定秒數換成反應表情（例：鬧鐘 → 嚇一跳）。
"""
from __future__ import annotations

import v4_cards as K4


class _Proxy:
    def __init__(self, shot, k):
        self._s, self._k = shot, k

    def __getattr__(self, n):
        if n == "dur":
            return self._s.dur * self._k
        return getattr(self._s, n)


def beats(fn, seq, speed=1.0):
    """seq＝[(卡片內秒, 原素材名, 換成的素材名)]：到了那一秒就把卡片上的比比換成反應拍。speed＝動畫倍速。"""
    def w(cv, t, shot):
        tt = t * speed
        orig = K4._host

        def host(cv_, L, nm, text, t_, mode=None):
            for ts, a, b in seq:
                if nm == a and t_ >= ts:
                    nm = b
            return orig(cv_, L, nm, text, t_, mode)
        K4._host = host
        try:
            fn(cv, tt, _Proxy(shot, speed) if speed != 1.0 else shot)
        finally:
            K4._host = orig
    return w


def opening6(kind):
    react = {1: ("alarm", "face_shock"), 2: ("magnifier", "tilt"), 3: ("piggy", "face_curious")}[kind]
    return beats(K4.opening_fn(kind), [(1.2 * 1.2, react[0], react[1])], speed=1.2)


def logo6():
    return beats(K4.logo_fn(), [(1.0, "reveal", "face_proud")])


def end6():
    return beats(K4.end4_fn(), [(1.0, "celebrate", "face_laugh"), (2.0, "face_laugh", "face_bow")])
