"""etf_freq.json（配息頻率徽章小檔）＝ etf.json 每檔的 freq 原封不動（2026-10-07 開頁速度第二輪）。"""
from pipeline import build_payload as bp


def test_etf_freq_copies_freq_verbatim():
    out = {"items": [{"code": "0056", "freq": "季配", "name": "x"},
                     {"code": "00878", "freq": "季配"},
                     {"code": "00929", "freq": "月配"},
                     {"code": "0050", "freq": "半年配"},
                     {"code": "00981A", "freq": None},
                     {"code": "00900"}]}
    assert bp.etf_freq(out) == {"0056": "季配", "00878": "季配", "00929": "月配", "0050": "半年配"}


def test_etf_freq_empty_input():
    assert bp.etf_freq({}) == {}
    assert bp.etf_freq(None) == {}
