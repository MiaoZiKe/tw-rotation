"""族群同業估值位階（P-1107-04，pipeline/compute/peerval.py）：百分位口徑、負 EPS、缺值、樣本不足、殖利率方向、自己歷史位置。"""
import pandas as pd

from pipeline.compute import peerval as pv


def _f(code, pe=None, pb=None, eps=1.0, yoy=None, loss=False, name=None):
    return {"code": code, "name": name or code, "pe": pe, "pb": pb, "ttm_eps": eps, "rev_yoy": yoy, "is_loss": loss}


def _ex(rows):
    cols = ["code", "pe_pct", "pe_n", "dy"]
    return {"cols": cols, "rows": [[c, p, n, d] for c, p, n, d in rows]}


def _mem(gid, codes, name="測試族群"):
    return pd.DataFrame({"code": codes, "group_id": gid, "group_name": name})


def _row(d, gid, code):
    cols = d["cols"]
    r = next(x for x in d["groups"][gid]["rows"] if x[0] == code)
    return dict(zip(cols, r))


def test_peer_pct_formula():
    vals = [10, 20, 30, 40, 50]
    assert pv.peer_pct(vals, 10) == 0           # 最低＝0
    assert pv.peer_pct(vals, 50) == 80          # 5 檔裡最高＝80（比它低的 4 檔）
    assert pv.peer_pct(vals, 30) == 40
    assert pv.peer_pct([10, 10, 20, 30, 40], 10) == 0   # 同值不算「比它低」
    assert pv.peer_pct(vals, None) is None
    # 跟 fundamental._pct_within（個股頁基本面卡「同業分位」）同一個公式
    import pandas as _pd
    from pipeline.compute import fundamental
    assert pv.peer_pct(vals, 30) == round(fundamental._pct_within(_pd.Series(vals), 30))


def test_thin_sample_no_percentile():
    assert pv.peer_pct([1, 2, 3, 4], 2) is None          # < 5 檔不硬算
    fund = [_f(c, pe=10 + i, pb=1 + i) for i, c in enumerate(["1101", "1102", "1103", "1104"])]
    d = pv.build_json(fund, None, _mem("g", ["1101", "1102", "1103", "1104"]))
    g = d["groups"]["g"]
    assert g["nv"]["pe"] == 4 and g["med"]["pe"] is None
    assert all(r[d["cols"].index("p_pe")] is None for r in g["rows"])


def test_negative_eps_excluded_and_flagged():
    codes = ["2001", "2002", "2003", "2004", "2005", "2006"]
    fund = [_f(c, pe=10 * (i + 1)) for i, c in enumerate(codes[:5])] + [_f("2006", pe=None, eps=-0.5, loss=True)]
    d = pv.build_json(fund, None, _mem("g", codes))
    r = _row(d, "g", "2006")
    assert r["st"] == "loss" and r["pe"] is None and r["p_pe"] is None
    assert d["groups"]["g"]["nv"]["pe"] == 5 and d["groups"]["g"]["loss"] == 1
    # 虧損那檔不進分母：最高那檔仍是 80（4/5），不是 4/6
    assert _row(d, "g", "2001")["p_pe"] == 0 and _row(d, "g", "2005")["p_pe"] == 80
    # EPS 浮點殘差 0 也算虧損（不給本益比）
    assert pv.stock_metrics(_f("x", pe=5e17, eps=0.0), None)["st"] == "loss"


def test_missing_values_na():
    codes = ["3001", "3002", "3003", "3004", "3005", "3006"]
    fund = [_f(c, pe=10 + i, pb=1 + i, yoy=i) for i, c in enumerate(codes[:5])] + [_f("3006", pe=None, pb=None, eps=None)]
    d = pv.build_json(fund, None, _mem("g", codes + ["3007"]))     # 3007 連基本面都沒有
    r6, r7 = _row(d, "g", "3006"), _row(d, "g", "3007")
    assert r6["st"] == "na" and r6["pe"] is None and r6["p_pb"] is None and r6["p_yoy"] is None
    assert r7["st"] == "na" and r7["name"] is None
    assert d["groups"]["g"]["n"] == 7 and d["groups"]["g"]["nv"]["pb"] == 5


def test_yield_direction_high_yield_is_low_position():
    codes = ["4001", "4002", "4003", "4004", "4005"]
    fund = [_f(c, pe=10) for c in codes]
    ex = _ex([(c, None, 0, dy) for c, dy in zip(codes, [1.0, 2.0, 3.0, 4.0, 8.0])])
    d = pv.build_json(fund, ex, _mem("g", codes))
    assert _row(d, "g", "4005")["p_dy"] == 0      # 殖利率最高 → 便宜端（0）
    assert _row(d, "g", "4001")["p_dy"] == 80
    assert d["groups"]["g"]["med"]["dy"] == 3.0


def test_own_history_needs_three_years_and_profit():
    m = pv.stock_metrics(_f("x", pe=12), {"pe_pct": 33, "pe_n": 12, "dy": None})
    assert m["own"] == 33 and m["own_n"] == 12
    assert pv.stock_metrics(_f("x", pe=12), {"pe_pct": 33, "pe_n": 11})["own"] is None   # < 12 季
    assert pv.stock_metrics(_f("x", eps=-1, loss=True), {"pe_pct": 33, "pe_n": 20})["own"] is None


def test_default_sort_by_code_and_stock_index_and_ind_fallback():
    codes = ["5005", "5001", "5003", "5002", "5004"]
    fund = [_f(c, pe=50 - i) for i, c in enumerate(codes)] + [_f("6001", pe=9), _f("6002", pe=11), _f("0050", pe=20)]
    comp = pd.DataFrame({"code": ["6001", "6002", "5001", "0050"], "industry": ["水泥工業", "水泥工業", "水泥工業", "ETF"]})
    d = pv.build_json(fund, None, _mem("g", codes), company=comp, ind_names={"水泥工業": "水泥"})
    assert [r[0] for r in d["groups"]["g"]["rows"]] == sorted(codes)
    assert d["stocks"]["5001"] == ["g"]
    # 不在 yaml 族群的普通股退回產業別；桶內同業＝同產業別、也沒有族群的普通股（5001 已在族群 g，不算；跟 fundamental 的 ind_ 桶同一群）
    assert d["stocks"]["6001"] == ["ind_水泥工業"]
    gi = d["groups"]["ind_水泥工業"]
    assert gi["kind"] == "ind" and gi["name"] == "水泥" and gi["n"] == 2 and [r[0] for r in gi["rows"]] == ["6001", "6002"]
    assert "0050" not in d["stocks"]         # ETF 不比估值


def test_distorted_pe_shown_but_not_ranked():
    codes = ["7001", "7002", "7003", "7004", "7005", "7006", "7007"]
    fund = [_f(c, pe=10 + i) for i, c in enumerate(codes[:5])] + [_f("7006", pe=850.0, eps=0.01), _f("7007", pe=2.1)]
    d = pv.build_json(fund, _ex([("7006", 90, 20, None)]), _mem("g", codes))
    r6, r7 = _row(d, "g", "7006"), _row(d, "g", "7007")
    assert r6["st"] == "dist" and r6["pe"] == 850.0 and r6["p_pe"] is None and r6["own"] == 90
    assert r7["st"] == "dist" and r7["p_pe"] is None
    assert d["groups"]["g"]["nv"]["pe"] == 5 and _row(d, "g", "7005")["p_pe"] == 80
