"""head_onset 回歸（2026-11-27）：念稿首字起音要與製作端人工確認的位置差 ≤0.05 秒；對不上要報錯不輸出。"""
import json, os, sys, wave
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTS = os.path.join(ROOT, "docs/marketing/channels/healing/templates_tqsa_v3/video/tts")
Q = os.path.join(ROOT, "docs/marketing/channels/healing/queue")
sys.path.insert(0, TTS)
import head_onset as H  # noqa: E402

# 人工確認的首字起音（原始錄音秒數；來源：各片 narration.wav.cut.json 的 head_onset.onset，bonus 為人工重裁的 46.77）
CASES = [("20261128v_avgwage", 40.42), ("20261129v_quit", 49.89), ("20261203v_minwage", 47.64), ("20261205v_bonus", 46.77)]


def _load(d):
    base = os.path.join(Q, d)
    need = [os.path.join(base, f) for f in ("narration_take.wav", "narration_take.asr.json", "narration.txt")]
    if not all(os.path.exists(p) for p in need): pytest.skip("缺 %s 的錄音／ASR／念稿" % d)
    w = wave.open(need[0]); SR = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
    return x, SR, json.load(open(need[1])), H.first_line(need[2])


@pytest.mark.parametrize("d,exp", CASES)
def test_regression(d, exp):
    x, SR, asr, text = _load(d)
    r = H.script_onset(x, SR, asr, text)
    assert abs(r["onset"] - exp) <= 0.05
    assert abs(r["cut_at"] - (r["onset"] - .05)) < 1e-6


def test_bonus_not_stuck_on_shuo():
    """bonus：「直接」「說」之間有 ≥0.15 秒安靜，舊法停在「說」前面。起音必須在「說」結束（45.96）之後。"""
    x, SR, asr, text = _load("20261205v_bonus")
    assert H.script_onset(x, SR, asr, text)["onset"] > 45.96


def test_text_mismatch_raises():
    x, SR, asr, _ = _load("20261205v_bonus")
    with pytest.raises(H.OnsetError): H.script_onset(x, SR, asr, "完全不相干的另外一句話")


def test_anchor_far_from_shuo_raises():
    x, SR, asr, text = _load("20261205v_bonus")
    bad = [dict(a) for a in asr]
    for a in bad:
        if a["w"] == "說" and abs(a["s"] - 45.68) < .01: a["s"], a["e"] = 30.0, 30.3   # 把「說」搬走 → 與念稿對位對不起來
    with pytest.raises(H.OnsetError): H.script_onset(x, SR, bad, text)
