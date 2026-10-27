"""盤後貼文「純資料快速路徑」（scripts/social_snap.fast_targets，2026-10-26）。不連網、不開瀏覽器。

盤後各卡全部原生繪製時，不再開網站截圖，改從 site/data 的 JSON 組出文案要的 read；
這裡驗：① 啟用條件（盤中有截圖卡就不走）② read 的寫法跟網站畫面一致 ③ 組出來的 shots 餵給 build_text 正常。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_snap as ss  # noqa: E402

FUT = {"dates": ["2026-10-21", "2026-10-22"], "order": "asc",
       "foreign": {"long": [30000, 31000], "short": [60000, 72345], "net": [-30000, -41345]},
       "trust": {"long": [40000, 41234], "short": [1000, 1000], "net": [39000, 40234]},
       "dealer": {"long": [5000, 5000], "short": [4000, 6500], "net": [None, None]}}
RET = {"products": {"TX": {"dates": ["2026-10-21", "2026-10-22"], "ratio_pct": [1.0, -2.345]},
                    "MTX": {"dates": ["2026-10-21", "2026-10-22"], "ratio_pct": [3.0, 0.125]},
                    "TMF": {"dates": ["2026-10-22"], "ratio_pct": [None], "total_oi": [1000], "retail_long": [600], "retail_short": [400]}}}
IM = {"rows": [{"d": "2026-10-21", "f": 9.6, "t": 129.19, "dl": -133.11, "tot": 5.68, "rev": {"f": 22.39}},
               {"d": "2026-10-22", "f": -815.82, "t": 94.92, "dl": -273.77, "tot": -994.67}]}
MF = {"margin": {"rows": [{"d": "2026-10-20", "ratio": 170.5}, {"d": "2026-10-21", "ratio": 170.38}, {"d": "2026-10-22", "ratio": None}],
                 "rank": {"rows": [{"code": "2330", "name": "台積電", "chg": 1200}, {"code": "0050", "name": "元大台灣50", "chg": 9000},
                                   {"code": "2317", "name": "鴻海", "chg": -800}]}}}
IT = {"all_by": {"foreign": [["2330", 1000, 12.3], ["2317", -500, -3.2], ["0050", 9000, 50]],
                 "trust": [["2454", 200, 4.5], ["3008", -10, -0.4]]}}
DATA = {"fut_oi": FUT, "retail_ratio": RET, "inst_market": IM, "market_fut": MF, "inst_today": IT}


def _args(kind="close", **kw):
    return argparse.Namespace(kind=kind, only="", no_native=False, no_fast=False, from_shots="", scale=2.0, **kw)


def _wanted(kind):
    return [t for t in ss.TARGETS if t["kind"] in ss.KIND_SET[kind]]


def test_只有全部原生繪製才走快速路徑():
    assert ss.fast_eligible(_wanted("close"), _args())
    assert ss.fast_eligible(_wanted("credit"), _args("credit"))
    assert not ss.fast_eligible(_wanted("intraday"), _args("intraday"))      # 輪盤、熱力圖要網站截圖
    a = _args()
    a.no_native = True
    assert not ss.fast_eligible(_wanted("close"), a)
    a = _args()
    a.no_fast = True
    assert not ss.fast_eligible(_wanted("close"), a)


def test_read_寫法跟網站畫面一致():
    # futpages.js #fpBig3：千分位、負號用全形減號、net 缺就用 多−空
    assert ss.fast_read_fut_oi(FUT) == "外資−41,345 多 31,000／空 72,345 投信+40,234 多 41,234／空 1,000 自營商−1,500 多 5,000／空 6,500"
    # 散戶多空比：toFixed(2) 四捨五入（0.125 → 0.13，不是銀行家捨入的 0.12）；ratio_pct 缺就用 (多−空)/全市場
    assert ss.fast_read_retail(RET) == [{"pct": "-2.35%", "prod": "大台"}, {"pct": "+0.13%", "prod": "小台"}, {"pct": "+20.00%", "prod": "微台"}]
    # 三大法人：最新一列官方值（不是 rev），一位小數、千分位
    assert ss.fast_read_inst(IM) == [["外資", "−815.8億"], ["投信", "+94.9億"], ["自營商", "−273.8億"], ["三大法人合計", "−994.7億"]]
    # 融資維持率：最新一天沒有值 → 用最近一個算得出來的日子，較前日跟再前一個有值的日子比
    assert ss.fast_read_credit(MF) == {"ratio": "170.38", "chg": "-0.12"}


def test_快速路徑組出的_shots_可以直接產文案():
    shots = ss.fast_targets(_args(), lambda n: DATA.get(n, {}))
    by = {s["name"]: s for s in shots}
    assert "credit-short" not in by and "credit-ratio" not in by      # 2026-10-27 融資移到盤前
    for n in ("fut-oi", "retail-ratio", "inst-today", "streak-foreign", "streak-trust"):
        s = by[n]
        assert s["ok"], n
        assert [p["name"] for p in s["pieces_d"]] == [n] and [p["name"] for p in s["pieces_m"]] == [n]
        assert all(p.get("fast") for p in s["pieces_d"] + s["pieces_m"])
    assert by["streak-foreign"]["read"]["buy"] == ["2330"]      # 只列個股（排除 ETF）
    txt = ss.build_text("close", "10/22 18:00", shots, "2026-10-22", "20261022")
    L = txt.splitlines()
    assert L[0] == "🌙 盤後3分鐘"
    assert "・外資 -41,345 口、投信 +40,234 口；" in L and "・自營商 -1,500 口" in L
    assert "・大台 -2.35%、小台 +0.13%；" in L and "・微台 +20.00%" in L
    assert "・外資 -815.8億、投信 +94.9億；" in L
    assert "・上市（估算）170.38%，較前日 -0.12pp" not in L
    assert L[-2] == ss.LINK_LINES[0] and L[-1].startswith(ss.link_url("close", "20261022")) and txt.count("https://") == 1
