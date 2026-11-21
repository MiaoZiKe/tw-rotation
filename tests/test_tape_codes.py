"""當日時間軸快照名單（build_payload.tape_codes）：人工族群＋題材成分股、去重、上櫃標 otc、自動桶不收。"""
from pipeline.build_payload import tape_codes


def test_tape_codes_union_and_market():
    gd = {
        "g1": {"members": [{"code": "2330", "market": "TWSE"}, {"code": "3374", "market": "TPEX"}]},
        "g2": {"members": [{"code": "2330", "market": "TWSE"}]},
        "ind_x": {"members": [{"code": "9999", "market": "TWSE"}]},
    }
    th = {"themes": [{"members": [{"code": "2317"}, {"code": "3374"}]}]}
    out = tape_codes(gd, th, {"2317": "TWSE"}, "2026-10-28")
    assert out["date"] == "2026-10-28"
    assert out["codes"] == [["2330", "tse"], ["3374", "otc"], ["2317", "tse"]]
