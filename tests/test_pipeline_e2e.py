"""端到端煙霧測試：用合成資料把「資料湖 → 計算 → 前端 JSON」整條跑一次。

這條測試的價值在於，開發環境連不到證交所（企業 egress 政策），
真實 API 只有在 GitHub Actions 上才打得到。所以本機能驗證的是
「拿到符合契約的資料後，後面每一步都不會爆」—— 而那正是最容易寫壞的部分。
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CODES = {
    "2330": "foundry", "2303": "foundry", "3711": "osat", "2311": "osat",
    "2317": "ai_server_odm", "2382": "ai_server_odm", "3017": "server_thermal",
    "2881": "finance", "2882": "finance", "2603": "shipping",
}


@pytest.fixture()
def lake(tmp_path, monkeypatch):
    """把資料湖與網站輸出都導到暫存目錄。"""
    from pipeline import config
    data, site = tmp_path / "data", tmp_path / "site"
    (data / "_state").mkdir(parents=True)
    site.mkdir(parents=True)

    monkeypatch.setattr(config, "DATA", data)
    monkeypatch.setattr(config, "SITE_DATA", site)
    monkeypatch.setattr(config, "STATE", data / "_state")

    from pipeline.util import store
    importlib.reload(store)
    monkeypatch.setattr(store.config, "DATA", data)
    return store, site


def _synth(days: int = 300, seed: int = 7):
    """造一段 10 檔股票、300 個交易日的行情，族群之間刻意給不同的走勢。"""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2025-06-02", periods=days).strftime("%Y-%m-%d").tolist()

    price_rows, inst_rows, val_rows, margin_rows = [], [], [], []
    for i, (code, group) in enumerate(CODES.items()):
        # 科技股給正漂移、傳產給負漂移，且訊號要明顯大於雜訊，
        # 否則 20 日 RS 排序會被隨機波動主導，測試本身就變得不可靠
        drift = 0.004 if group in ("foundry", "osat", "ai_server_odm",
                                   "server_thermal") else -0.004
        steps = rng.normal(drift, 0.008, days)
        close = 100 * (1 + i * 0.3) * np.exp(np.cumsum(steps))
        prev = np.concatenate([[close[0]], close[:-1]])
        high = close * (1 + np.abs(rng.normal(0, 0.01, days)))
        low = close * (1 - np.abs(rng.normal(0, 0.01, days)))
        vol = rng.integers(5_000_000, 80_000_000, days)

        for j, d in enumerate(dates):
            price_rows.append({
                "date": d, "code": code, "name": f"股{code}", "market": "TWSE",
                "open": float(prev[j]), "high": float(high[j]),
                "low": float(low[j]), "close": float(close[j]),
                "change": float(close[j] - prev[j]),
                "volume": int(vol[j]),
                "turnover": float(vol[j] * close[j]),
                "transactions": int(vol[j] / 1000),
            })
            inst_rows.append({
                "date": d, "code": code,
                "foreign": float(rng.normal(0, 3e6)),
                "foreign_dealer": 0.0,
                "foreign_total": float(rng.normal(0, 3e6)),
                "trust": float(rng.normal(5e5 if drift > 0 else -5e5, 8e5)),
                "dealer_self": 0.0, "dealer_hedge": 0.0,
                "dealer": float(rng.normal(0, 5e5)),
                "inst_total": float(rng.normal(0, 4e6)),
            })
            margin_rows.append({
                "date": d, "code": code,
                "margin_balance": int(rng.integers(1000, 50000)),
                "margin_change": int(rng.integers(-2000, 2000)),
                "short_balance": int(rng.integers(0, 5000)),
                "short_change": int(rng.integers(-500, 500)),
            })

        val_rows.append({
            "date": dates[-1], "code": code,
            "pe": float(rng.uniform(8, 40)),
            "pb": float(rng.uniform(0.8, 6)),
            "dividend_yield": float(rng.uniform(0.5, 6)),
        })

    market_rows = []
    taiex = 20000 * np.exp(np.cumsum(rng.normal(0.0006, 0.012, days)))
    for j, d in enumerate(dates):
        market_rows.append({
            "date": d, "volume": int(rng.integers(4e9, 9e9)),
            "turnover": float(rng.uniform(3e11, 6e11)),
            "transactions": int(rng.integers(1e6, 3e6)),
            "taiex": float(taiex[j]),
            "change": float(taiex[j] - (taiex[j - 1] if j else taiex[0])),
        })

    company = pd.DataFrame([
        {"code": c, "name": f"股{c}", "market": "TWSE",
         "industry": "半導體業" if g in ("foundry", "osat") else "其他",
         "industry_code": "24"}
        for c, g in CODES.items()
    ])

    return (pd.DataFrame(price_rows), pd.DataFrame(inst_rows),
            pd.DataFrame(val_rows), pd.DataFrame(margin_rows),
            pd.DataFrame(market_rows), company)


@pytest.fixture()
def populated(lake):
    store, site = lake
    price, inst, val, margin, market, company = _synth()
    store.append("price_daily", price)
    store.append("inst_daily", inst)
    store.append("valuation_daily", val)
    store.append("margin_daily", margin)
    store.append("market_daily", market)
    store.append("company_info", company)
    return store, site, price.copy()


# ------------------------------------------------------------------ 族群對照表

def test_groups_yaml_is_valid():
    from pipeline.groups import loader
    cfg = loader.load()
    assert cfg.get("groups"), "groups.yaml 沒有任何族群"

    m = loader.membership(cfg)
    assert not m.empty
    bad = [c for c in m["code"] if not (c.isdigit() and len(c) == 4)]
    assert not bad, f"這些代號格式不對：{bad[:10]}"

    # chains 裡引用的族群一定要真的存在，否則畫關聯圖時會缺角
    gids = set(cfg["groups"])
    for chain, spec in (cfg.get("chains") or {}).items():
        missing = [g for g in spec.get("order", []) if g not in gids]
        assert not missing, f"chain {chain} 引用了不存在的族群：{missing}"

    for gid in (cfg.get("benchmarks") or {}):
        assert gid in gids, f"benchmarks 引用了不存在的族群：{gid}"


def test_groups_health_reports_staleness():
    from pipeline.groups import loader
    h = loader.health()
    assert h["group_count"] > 0 and h["code_count"] > 0
    assert not h["empty_groups"], f"有空的族群：{h['empty_groups']}"
    assert "is_stale" in h


# ------------------------------------------------------------------ M1

def test_group_daily_aggregates(populated):
    from pipeline.compute import flow
    store, _, price = populated
    company = store.read("company_info")
    inst = store.read("inst_daily")
    margin = store.read("margin_daily")

    g = flow.group_daily(price, company, inst, margin)
    assert not g.empty

    latest = g["date"].max()
    today = g[g["date"] == latest]
    total_share = today["turnover_share"].sum()
    assert abs(total_share - 100) < 0.01, f"族群成交值佔比應加總為 100，實得 {total_share}"
    assert (today["constituents"] > 0).all()

    # 多族群股（2317 同屬 AI 伺服器與手機供應鏈）的量能必須被拆分，
    # 不能兩邊各算一次完整金額
    day_price = price[price["date"] == latest]
    market_turnover = float(day_price["turnover"].sum())
    grouped_turnover = float(today["turnover"].sum())
    assert grouped_turnover <= market_turnover * 1.001, \
        f"族群加總 {grouped_turnover:.0f} 超過市場總量 {market_turnover:.0f}，量能被重複計算"


def test_rotation_radar_ranks(populated):
    from pipeline.compute import flow
    store, _, price = populated
    g = flow.group_daily(price, store.read("company_info"))
    r = flow.rotation_radar(g)
    assert not r.empty
    assert r["rotation"].is_monotonic_decreasing, "輪動雷達必須由強到弱排序"
    assert len(r) == r["group_id"].nunique(), "每個族群只能出現一次"


def test_concentration_bounds(populated):
    from pipeline.compute import flow
    store, _, price = populated
    g = flow.group_daily(price, store.read("company_info"))
    c = flow.concentration(g, top_n=3)
    assert not c.empty
    assert c["top_share"].between(0, 100.01).all()


def test_relative_strength_beats_market(populated):
    from pipeline.compute import flow
    store, _, price = populated
    g = flow.group_daily(price, store.read("company_info"))
    rs = flow.relative_strength(g, store.read("market_daily"))
    assert not rs.empty
    assert rs["rs"].is_monotonic_decreasing

    # 合成資料裡科技股是正漂移、傳產是負漂移，
    # 所以每個傳產族群都必須排在所有科技族群後面
    order = rs["group_id"].tolist()
    laggards = {"finance", "shipping"}
    tech_positions = [i for i, g in enumerate(order) if g not in laggards]
    lag_positions = [i for i, g in enumerate(order) if g in laggards]
    assert lag_positions, "測試資料應包含傳產族群"
    assert max(tech_positions) < min(lag_positions), \
        f"強弱排序不符預期：{order}"


def test_trust_streak(populated):
    from pipeline.compute import flow
    store, _, _ = populated
    s = flow.trust_streak(store.read("inst_daily"), min_days=1)
    if not s.empty:
        assert (s["streak_days"] >= 1).all()
        assert s["streak_days"].is_monotonic_decreasing


# ------------------------------------------------------------------ 前端輸出

def test_build_payload_end_to_end(populated):
    from pipeline import build_payload
    _, site, _ = populated
    build_payload.build()

    expected = ["meta", "market_heat", "groups_today", "rotation",
                "concentration", "relative_strength", "seasonality",
                "candidates", "news", "intl", "trust_streak"]
    for name in expected:
        f = site / f"{name}.json"
        assert f.exists(), f"缺少 {name}.json"
        json.loads(f.read_text(encoding="utf-8"))   # 必須是合法 JSON

    meta = json.loads((site / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "ok"
    assert meta["history_days"] == 300

    heat = json.loads((site / "market_heat.json").read_text(encoding="utf-8"))
    assert heat["advancers"] + heat["decliners"] + heat["unchanged"] == len(CODES)

    cands = json.loads((site / "candidates.json").read_text(encoding="utf-8"))
    assert cands, "候選股清單不該是空的"
    assert all(0 <= c["tech_score"] <= 100 for c in cands)
    scores = [c["tech_score"] for c in cands]
    assert scores == sorted(scores, reverse=True), "候選股必須依技術分排序"


def test_payload_has_no_nan_literals(populated):
    """JSON 裡不能出現 NaN / Infinity —— 那不是合法 JSON，前端 fetch 會直接掛掉。"""
    from pipeline import build_payload
    _, site, _ = populated
    build_payload.build()
    for f in site.glob("*.json"):
        raw = f.read_text(encoding="utf-8")
        assert "NaN" not in raw, f"{f.name} 含有 NaN"
        assert "Infinity" not in raw, f"{f.name} 含有 Infinity"


def test_seasonality_suppresses_thin_samples(populated):
    """樣本數不足 3 的月份必須留白，不能給出看似有效的平均值。"""
    from pipeline import build_payload
    store, _, price = populated
    s = build_payload.seasonality(price, store.read("company_info"))
    assert not s.empty
    thin = s[s["samples"] < 3]
    if not thin.empty:
        assert thin["avg_return"].isna().all(), "樣本不足時不該給平均報酬"
    assert s["win_rate"].dropna().between(0, 100).all()


def test_build_payload_survives_empty_lake(lake):
    """資料湖全空時（第一天上線）不能整個爆掉。"""
    from pipeline import build_payload
    _, site = lake
    build_payload.build()
    meta = json.loads((site / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "empty"
