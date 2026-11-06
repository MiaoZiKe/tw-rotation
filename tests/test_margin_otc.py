"""上櫃融資維持率（估算）＋合計＋每週官方開放檢查（2026-11-06）。

釘住的口徑：
  · 上櫃＝Σ(上櫃個股融資張數×1000×收盤) ÷ 上櫃整體融資金額(元) × 100，跟上市同一支 _caps；
  · 合計＝市值相加 ÷ 金額相加（不是比率平均），只收兩邊都有的日子；
  · 櫃買彙總表的融資金額一律換成元，範圍外整份不收；個股明細（列數多）不當總表；沒有日期不收。
"""
import json

import pandas as pd
import pytest

from pipeline import open_watch
from pipeline.compute import mktfut
from pipeline.sources import tpex_margin as tm


# ---------------------------------------------------------------- 櫃買彙總表解析
LONG_ZH = [
    {"資料日期": "115/11/05", "項目": "融資(交易單位)", "前日餘額": "2,250,000", "買進": "10", "賣出": "5", "現償": "1", "今日餘額": "2,260,000"},
    {"資料日期": "115/11/05", "項目": "融資金額(仟元)", "前日餘額": "160,000,000", "買進": "5", "今日餘額": "161,234,567"},
    {"資料日期": "115/11/05", "項目": "融券(交易單位)", "前日餘額": "40,000", "今日餘額": "41,000"},
]


def test_parse_long_zh_units_to_yuan():
    df = tm.parse_summary(LONG_ZH)
    assert len(df) == 1
    r = df.iloc[0]
    assert r["date"] == "2026-11-05"
    assert r["margin_money"] == pytest.approx(161_234_567_000)      # 仟元 ×1000
    assert r["margin_money_prev"] == pytest.approx(160_000_000_000)
    assert r["margin_lots"] == 2_260_000 and r["margin_lots_prev"] == 2_250_000
    assert r["short_lots"] == 41_000


def test_parse_long_en_and_wide():
    en = [{"Date": "1151105", "Item": "融資金額(仟元)", "PreviousDayBalance": "160000000", "TodayBalance": "161234567"},
          {"Date": "1151105", "Item": "融資(交易單位)", "PreviousDayBalance": "2250000", "TodayBalance": "2260000"}]
    assert tm.parse_summary(en).iloc[0]["margin_money"] == pytest.approx(161_234_567_000)
    wide = [{"Date": "20261105", "MarginPurchaseBalance": "2260000", "MarginPurchaseMoneyBalance": "161234567000",
             "ShortSaleBalance": "41000", "ShortSaleSell": "5", "MarginPurchaseBuy": "9"}]
    r = tm.parse_summary(wide).iloc[0]
    assert r["margin_money"] == pytest.approx(161_234_567_000)     # 已經是元，不再 ×1000
    assert r["margin_lots"] == 2_260_000 and r["short_lots"] == 41_000


def test_parse_rejects_bad_shapes():
    assert tm.parse_summary(None).empty and tm.parse_summary([]).empty and tm.parse_summary({"a": 1}).empty
    # 沒有日期欄：不拿執行當下日期頂替
    assert tm.parse_summary([{k: v for k, v in r.items() if k != "資料日期"} for r in LONG_ZH]).empty
    # 金額離譜（換算後 > 3 兆）：整份不收
    bad = [dict(LONG_ZH[1], 今日餘額="9,999,999,999")]
    assert tm.parse_summary(bad).empty
    # 個股明細（列數 > MAX_ROWS）不是總表
    many = [{"資料日期": "1151105", "代號": str(3000 + i), "項目": "融資金額(仟元)", "今日餘額": "161234567"} for i in range(tm.MAX_ROWS + 1)]
    assert tm.parse_summary(many).empty
    # 只有張數、沒有金額：分母不存在，不收
    assert tm.parse_summary([LONG_ZH[0]]).empty


def test_discover_from_swagger():
    tm.DIAG.clear()
    sw = {"paths": {"/tpex_mainboard_margin_balance": {"get": {"summary": "上櫃股票融資融券餘額"}},
                    "/tpex_margin_sum": {"get": {"summary": "上櫃信用交易餘額概況表"}},
                    "/tpex_3insti_summary": {"get": {"summary": "上櫃股票三大法人買賣金額彙總表"}}}}
    got = tm.discover(sw)
    assert "/v1/tpex_margin_sum" in got and "/v1/tpex_3insti_summary" not in got
    assert tm.discover(None) == []


# ---------------------------------------------------------------- 上櫃與合計的維持率
def _lake():
    company = pd.DataFrame({"code": ["2330", "6488", "5483"], "market": ["TWSE", "TPEX", "TPEX"], "name": ["台積電", "環球晶", "中美晶"]})
    days = ["2026-11-03", "2026-11-04", "2026-11-05"]
    md = pd.DataFrame([{"date": d, "code": c, "margin_balance": b, "margin_change": 0.0}
                       for d in days for c, b in (("2330", 100.0), ("6488", 10.0), ("5483", 20.0))])
    price = pd.DataFrame([{"date": d, "code": c, "close": p} for d in days for c, p in (("2330", 1000.0), ("6488", 500.0), ("5483", 100.0))])
    mt = pd.DataFrame({"date": days, "margin_lots": [100.0] * 3, "margin_lots_prev": [100.0] * 3, "margin_money": [50_000_000.0] * 3,
                       "margin_money_prev": [50_000_000.0] * 3, "short_lots": [1.0] * 3, "short_lots_prev": [1.0] * 3})
    otc = pd.DataFrame({"date": days[1:], "margin_lots": [30.0, 30.0], "margin_lots_prev": [30.0, 30.0], "margin_money": [4_000_000.0, 0.0],
                        "margin_money_prev": [4_000_000.0, 4_000_000.0], "short_lots": [2.0, 2.0], "short_lots_prev": [2.0, 1.0]})
    idx = pd.DataFrame({"date": days * 2, "symbol": ["TSE"] * 3 + ["OTC"] * 3, "close": [27000.0] * 3 + [300.0] * 3})
    return mt, md, company, price, otc, idx


def test_otc_ratio_same_formula_as_twse():
    mt, md, co, px, otc, idx = _lake()
    out = mktfut.build(mt, md, co, px, idx, mt_otc=otc)["margin"]
    tw = {r["d"]: r for r in out["mkts"]["twse"]}
    assert tw["2026-11-04"]["ratio"] == pytest.approx(100 * 1000 * 1000 / 50_000_000 * 100)   # 200%
    o = {r["d"]: r for r in out["mkts"]["tpex"]}
    # 上櫃市值 ＝ 10×1000×500 + 20×1000×100 ＝ 7,000,000；÷ 4,000,000 ＝ 175%
    assert o["2026-11-04"]["ratio"] == pytest.approx(175.0)
    assert o["2026-11-04"]["taiex"] == 300.0                              # 上櫃對照櫃買指數
    assert o["2026-11-05"]["ratio"] is None                               # 分母為 0：不除
    assert out["idx_name"]["tpex"] == "櫃買指數" and out["otc_from"] == "2026-11-04"
    assert out["rows"] == out["mkts"]["twse"]                             # 舊鍵不變


def test_combined_is_sum_ratio_not_average_and_intersection_only():
    mt, md, co, px, otc, idx = _lake()
    a = mktfut.build(mt, md, co, px, idx, mt_otc=otc)["margin"]["mkts"]["all"]
    days = [r["d"] for r in a]
    assert "2026-11-03" not in days                                       # 上櫃那天沒有分母：合計不收
    r = next(x for x in a if x["d"] == "2026-11-04")
    assert r["ratio"] == pytest.approx((100_000_000 + 7_000_000) / (50_000_000 + 4_000_000) * 100)   # ≈198.15，不是 (200+175)/2
    assert r["ratio"] != pytest.approx((200 + 175) / 2)
    assert r["margin_lots"] == 130 and r["short_chg"] == 0
    assert r["taiex"] == 27000.0


def test_otc_empty_inputs():
    mt, md, co, px, otc, idx = _lake()
    out = mktfut.build(mt, md, co, px, idx, mt_otc=pd.DataFrame())["margin"]
    assert out["mkts"]["tpex"] == [] and out["mkts"]["all"] == [] and out["otc_from"] is None
    assert mktfut.otc_rows(None, md, co, px) == []
    # 有分母、沒有任何上櫃個股融資 → 有列但 ratio 全 None（不外推）
    rows = mktfut.otc_rows(otc, pd.DataFrame(), co, px, idx)
    assert rows and all(r["ratio"] is None for r in rows)


# ---------------------------------------------------------------- 每週官方開放檢查
def test_is_hit_rules():
    assert open_watch.is_hit("集中市場融資融券擔保維持率")
    assert open_watch.is_hit("/v1/market_dashboard")
    assert open_watch.is_hit("信用交易追繳戶數")
    assert open_watch.is_hit("融資處分金額")
    assert not open_watch.is_hit("公司取得或處分資產公告")              # 「處分」單獨不算
    assert not open_watch.is_hit("上櫃股票融資融券餘額")


def test_run_writes_state_and_ignore(tmp_path, monkeypatch):
    monkeypatch.setattr(open_watch, "STATE_FILE", tmp_path / "w.json")
    sw_twse = {"paths": {"/exchangeReport/MI_MARGN": {"get": {"summary": "集中市場融資融券餘額"}}}}
    sw_tpex = {"paths": {"/tpex_margin_maintenance": {"get": {"summary": "上櫃整體擔保維持率"}}}}
    fm_src = 'TaiwanStockPrice = "TaiwanStockPrice"\nTaiwanStockTotalMarginPurchaseShortSale = "TaiwanStockTotalMarginPurchaseShortSale"\n'

    def fetch(url, **kw):
        if "twse" in url:
            return sw_twse
        if "tpex" in url:
            return sw_tpex
        return fm_src

    st = open_watch.run(fetch=fetch, fm_get=lambda *a, **k: None)
    assert st["open"] and "tpex_margin_maintenance" in st["msg"] and "可以接上" in st["msg"]
    assert st["sources"]["finmind"]["n_datasets"] == 2 and st["sources"]["twse"]["ok"]
    first = st["hits"][0]["first_seen"]
    # 人工確認是誤判 → 寫進 ignore，下週不再提示；first_seen 保留
    s = json.loads((tmp_path / "w.json").read_text(encoding="utf-8"))
    s["ignore"] = ["/tpex_margin_maintenance"]
    (tmp_path / "w.json").write_text(json.dumps(s), encoding="utf-8")
    st2 = open_watch.run(fetch=fetch, fm_get=lambda *a, **k: None)
    assert not st2["open"] and st2["msg"] == "" and st2["hits"][0]["first_seen"] == first
    assert open_watch.for_meta() == {"checked_at": st2["checked_at"], "open": False, "msg": "",
                                     "ok": {"twse": True, "tpex": True, "finmind": True}}


def test_run_all_sources_down(tmp_path, monkeypatch):
    monkeypatch.setattr(open_watch, "STATE_FILE", tmp_path / "w.json")
    st = open_watch.run(fetch=lambda *a, **k: None, fm_get=lambda *a, **k: [{"date": "2026-11-05", "ratio": 160}])
    assert not st["sources"]["twse"]["ok"] and not st["sources"]["finmind"]["ok"]
    assert st["open"] and any(h["src"] == "finmind" for h in st["hits"])     # 試探資料集真的有資料 → 提示
    monkeypatch.setattr(open_watch, "STATE_FILE", tmp_path / "none.json")
    assert open_watch.for_meta() == {}
