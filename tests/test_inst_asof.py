"""法人連買賣的資料日只看法人表自己（compute/inst_asof.py）。

事故（2026-11-09）：價量上市那半沒進湖，build_payload／social_close_payload 把法人表跟著切回 11-06，
盤後貼文的連買賣卡標 11-06，而同日的法人買賣超日報卡標 11-09。這裡鎖住三件事：
1. 價量落後不影響法人的資料日；2. 法人自己上市沒到齊時，停在前一天並寫出原因；3. 連買賣不混入舊代號。
"""
import pandas as pd

from pipeline.compute import inst_asof


def _inst(date, codes, f=1000):
    return pd.DataFrame([{"date": date, "code": c, "foreign_total": f, "trust": 0, "dealer": 0,
                          "inst_total": f} for c in codes])


def _price(date_codes, markets):
    rows = []
    for d, cs in date_codes.items():
        for c in cs:
            rows.append({"date": d, "code": c, "market": markets[c], "close": 10.0})
    return pd.DataFrame(rows)


TWSE = [str(1000 + i) for i in range(20)]     # 上市 20 檔（縮小版）
TPEX = [str(5000 + i) for i in range(10)]     # 櫃買 10 檔
MK = {**{c: "TWSE" for c in TWSE}, **{c: "TPEX" for c in TPEX}}


def _days(days_codes_map):
    """法人表：每天給一組代號。"""
    return pd.concat([_inst(d, cs) for d, cs in days_codes_map.items()], ignore_index=True)


def test_價量落後_法人到齊時資料日仍是法人最新一天():
    # 價量 11-09 只有櫃買（上市沒進湖），法人 11-09 上市櫃都齊
    inst = _days({"2026-11-06": TWSE + TPEX, "2026-11-09": TWSE + TPEX})
    price = _price({"2026-11-06": TWSE + TPEX, "2026-11-09": TPEX}, MK)
    ia = inst_asof.as_of(inst, price)
    assert ia["date"] == "2026-11-09"
    assert ia["reason"] == ""


def test_法人上市只到一半_停在前一天並寫明原因():
    # 法人 11-09 上市只有 8 檔（最多 20 檔）→ 不算到齊，連買賣停在 11-06，原因要講得出來
    inst = _days({"2026-11-06": TWSE + TPEX, "2026-11-09": TWSE[:8] + TPEX})
    price = _price({"2026-11-06": TWSE + TPEX, "2026-11-09": TPEX}, MK)
    ia = inst_asof.as_of(inst, price)
    assert ia["date"] == "2026-11-06"
    assert ia["last"] == "2026-11-09"
    assert "2026-11-09" in ia["reason"] and "未達" in ia["reason"]


def test_沒有市場欄位時全部代號一起算():
    inst = _days({"2026-11-06": TWSE + TPEX, "2026-11-09": TWSE + TPEX})
    ia = inst_asof.as_of(inst, pd.DataFrame({"date": ["2026-11-09"], "code": ["1000"], "close": [1.0]}))
    assert ia["date"] == "2026-11-09"


def test_連買排行只留資料日當天有資料的代號():
    # 9999 最後一筆停在 11-04，不是今天 → 不得出現在 11-09 的連買排行
    inst = pd.concat([
        _inst("2026-11-04", ["1000", "9999"]),
        _inst("2026-11-05", ["1000", "9999"]),
        _inst("2026-11-06", ["1000", "2000"]),
        _inst("2026-11-09", ["1000", "2000"]),
    ], ignore_index=True)
    cut = inst_asof.cut(inst, "2026-11-09")
    df = inst_asof.streaks(cut, "foreign", "buy", "2026-11-09")
    assert set(df["code"]) == {"1000", "2000"}
    assert set(df["date"].astype(str)) == {"2026-11-09"}


def test_停在11_06時連買排行日期也是11_06_不是混著舊日():
    inst = _days({"2026-11-05": TWSE + TPEX, "2026-11-06": TWSE + TPEX})
    inst = pd.concat([inst, _inst("2026-11-09", TWSE[:8])], ignore_index=True)
    ia = inst_asof.as_of(inst, _price({"2026-11-06": TWSE + TPEX}, MK))
    assert ia["date"] == "2026-11-06"
    df = inst_asof.streaks(inst_asof.cut(inst, ia["date"]), "foreign", "buy", ia["date"])
    assert not df.empty and set(df["date"].astype(str)) == {"2026-11-06"}
