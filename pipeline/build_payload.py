"""把資料湖算成前端要的 JSON。

前端只負責畫圖，所有運算都在這裡做完 —— 這樣手機開也是秒開，
而且圖表跟數字永遠一致（不會前端算一套、後端算一套）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, indicators
from .compute import flow
from .groups import loader
from .util import store

log = logging.getLogger(__name__)


def _clean(obj):
    """NaN / numpy 型別轉成 JSON 吃得下的形式。"""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if (pd.isna(obj) or np.isinf(obj)) else round(float(obj), 4)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NaT or (isinstance(obj, float) and pd.isna(obj)):
        return None
    return obj


def _write(name: str, payload) -> None:
    path = config.SITE_DATA / f"{name}.json"
    path.write_text(json.dumps(_clean(payload), ensure_ascii=False), encoding="utf-8")
    log.info("寫出 %s（%.1f KB）", path.name, path.stat().st_size / 1024)


def build() -> None:
    price = store.read("price_daily")
    if price.empty:
        log.warning("資料湖還沒有行情資料，只產出空的 meta")
        _write("meta", {"status": "empty", "generated_at":
                        datetime.now(timezone.utc).isoformat()})
        return

    company = store.read("company_info")
    inst = store.read("inst_daily")
    margin = store.read("margin_daily")
    market = store.read("market_daily")
    valuation = store.read("valuation_daily")

    latest = str(price["date"].max())
    history_days = int(price["date"].nunique())

    # ---------------------------------------------------------- M1 資金面
    group_hist = flow.group_daily(price, company, inst, margin)
    today = (group_hist[group_hist["date"] == latest]
             if not group_hist.empty else pd.DataFrame())

    _write("groups_today", today.to_dict("records"))
    _write("rotation", flow.rotation_radar(group_hist).head(25).to_dict("records"))
    _write("concentration", flow.concentration(group_hist).tail(120).to_dict("records"))
    _write("relative_strength",
           flow.relative_strength(group_hist, market).to_dict("records"))
    _write("trust_streak", flow.trust_streak(inst).head(30).to_dict("records"))

    # ---------------------------------------------------------- 市場體溫
    heat = {"date": latest}
    if not market.empty:
        mk = market.sort_values("date")
        heat["taiex"] = _clean(mk["taiex"].iloc[-1])
        heat["change"] = _clean(mk["change"].iloc[-1])
        heat["turnover"] = _clean(mk["turnover"].iloc[-1])
        tv = pd.to_numeric(mk["turnover"], errors="coerce")
        if len(tv.dropna()) >= 20:
            heat["turnover_ma20"] = _clean(tv.tail(20).mean())
        heat["taiex_series"] = _clean(
            mk.tail(120)[["date", "taiex"]].to_dict("records"))

    day = price[price["date"] == latest].copy()
    day["prev"] = day["close"] - day["change"].fillna(0)
    day["chg_pct"] = np.where(day["prev"] > 0, day["change"] / day["prev"] * 100, np.nan)
    heat["advancers"] = int((day["chg_pct"] > 0).sum())
    heat["decliners"] = int((day["chg_pct"] < 0).sum())
    heat["unchanged"] = int((day["chg_pct"] == 0).sum())
    if not today.empty:
        heat["top5_share"] = _clean(today.nlargest(5, "turnover")["turnover_share"].sum())
    _write("market_heat", heat)

    # ---------------------------------------------------------- M4 季節性
    _write("seasonality", seasonality(price, company).to_dict("records"))

    # ---------------------------------------------------------- 個股技術面
    _write("candidates", candidates(price, valuation, company, inst, latest))

    # ---------------------------------------------------------- 新聞
    news_df = store.read("news")
    if not news_df.empty:
        recent = news_df.sort_values("published_at", ascending=False).head(80)
        _write("news", recent.to_dict("records"))
    else:
        _write("news", [])

    # ---------------------------------------------------------- 國際
    intl = store.read("intl_daily")
    if not intl.empty:
        recent = intl[intl["date"] >= (pd.Timestamp(latest) -
                                       pd.Timedelta(days=180)).date().isoformat()]
        _write("intl", recent.to_dict("records"))
    else:
        _write("intl", [])

    # ---------------------------------------------------------- meta
    last_run = {}
    lr = config.STATE / "last_run.json"
    if lr.exists():
        try:
            last_run = json.loads(lr.read_text())
        except ValueError:
            pass

    _write("meta", {
        "status": "ok",
        "data_date": latest,
        "history_days": history_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "groups_health": loader.health(),
        "table_summary": store.table_summary().to_dict("records"),
        "last_run_errors": last_run.get("errors", []),
        # 回空的來源不算「錯誤」，但一樣代表整張表沒進資料，前端要一起示警
        "last_run_empty_sources": last_run.get("empty_sources", []),
        # FinMind 免費 token 七天就過期，過期後籌碼會安靜停更
        "finmind_token_days_left": last_run.get("finmind_token_days_left"),
    })


def seasonality(price: pd.DataFrame, company: pd.DataFrame) -> pd.DataFrame:
    """族群 × 月份的歷史平均報酬、勝率、樣本數。

    刻意三個數字一起輸出 —— 只給平均報酬會讓人把 3 個樣本的巧合當成規律。
    """
    if price.empty:
        return pd.DataFrame()

    df = price.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "close"])
    m = loader.membership()
    df = df.merge(m[["code", "group_id", "group_name"]], on="code", how="inner")
    if df.empty:
        return pd.DataFrame()

    df["ym"] = df["date"].dt.to_period("M")
    monthly = (df.sort_values("date")
                 .groupby(["group_id", "group_name", "ym"])
                 .agg(first=("close", "first"), last=("close", "last"))
                 .reset_index())
    monthly["ret"] = (monthly["last"] / monthly["first"] - 1) * 100
    monthly["month"] = monthly["ym"].dt.month

    out = (monthly.groupby(["group_id", "group_name", "month"])
                  .agg(avg_return=("ret", "mean"),
                       median_return=("ret", "median"),
                       win_rate=("ret", lambda s: float((s > 0).mean() * 100)),
                       samples=("ret", "size"))
                  .reset_index())
    # 樣本數太少的直接不給結論，避免誤導
    out.loc[out["samples"] < 3, ["avg_return", "median_return", "win_rate"]] = np.nan
    return out


def _stock_name(g: pd.DataFrame, name_by_code: dict, code: str) -> str:
    """股票名稱：company_info 優先，其次價格資料裡最後一個非空值，最後退回代號。

    絕不回 NaN —— 前端拿到 null 會直接顯示空白，看起來像資料壞了。
    """
    name = name_by_code.get(code)
    if name:
        return name
    if "name" in g.columns:
        s = g["name"].dropna()
        if not s.empty:
            return str(s.iloc[-1])
    return code


def candidates(price: pd.DataFrame, valuation: pd.DataFrame,
               company: pd.DataFrame, inst: pd.DataFrame,
               latest: str, limit: int = 120) -> list[dict]:
    """當日候選股：技術分 + 同業本益比分位 + 籌碼，合成綜合分。"""
    if price.empty:
        return []

    m = loader.membership()
    day = price[price["date"] == latest]
    # 只算有題材族群、且當日成交值前段的標的，避免無謂的運算
    codes = (day.merge(m[["code"]].drop_duplicates(), on="code", how="inner")
                .nlargest(limit, "turnover")["code"].tolist())
    if not codes:
        codes = day.nlargest(limit, "turnover")["code"].tolist()

    hist = price[price["code"].isin(codes)].sort_values(["code", "date"])
    val_today = (valuation[valuation["date"] == latest]
                 if not valuation.empty else pd.DataFrame())

    # 同業本益比分位需要族群內的 PE 分布
    pe_by_group = {}
    if not val_today.empty:
        joined = val_today.merge(m[["code", "group_id"]], on="code", how="inner")
        for gid, g in joined.groupby("group_id"):
            pes = pd.to_numeric(g["pe"], errors="coerce")
            pes = pes[(pes > 0) & (pes < 200)]
            if len(pes) >= 3:
                pe_by_group[gid] = pes

    inst_today = (inst[inst["date"] == latest]
                  if not inst.empty else pd.DataFrame())

    # price_daily 的 name 只有證交所/櫃買那批有值，FinMind 回補進來的列是空的。
    # 回補資料的日期又常常比較新，所以直接取 g["name"].iloc[-1] 會拿到 NaN ——
    # 回補完成後反而變成大部分候選股都沒有名字。改用 company_info 當主要來源。
    name_by_code: dict[str, str] = {}
    if not company.empty and "name" in company.columns:
        name_by_code = (company.dropna(subset=["name"])
                               .drop_duplicates("code")
                               .set_index("code")["name"].to_dict())

    rows = []
    for code, g in hist.groupby("code"):
        if len(g) < 60:      # 資料太短算不出有意義的技術指標
            continue
        try:
            ind = indicators.compute_all(g[["date", "open", "high", "low", "close"]])
        except Exception:  # noqa: BLE001
            continue
        last = ind.iloc[-1]
        tech = indicators.technical_score(last)

        groups = m[m["code"] == code]
        gid = groups["group_id"].iloc[0] if not groups.empty else None
        gname = groups["group_name"].iloc[0] if not groups.empty else "—"

        pe = pct = None
        if not val_today.empty:
            v = val_today[val_today["code"] == code]
            if not v.empty:
                pe = _clean(v["pe"].iloc[0])
                if pe and gid in pe_by_group and pe > 0:
                    pct = float((pe_by_group[gid] < pe).mean() * 100)

        trust_net = None
        if not inst_today.empty:
            i = inst_today[inst_today["code"] == code]
            if not i.empty:
                trust_net = _clean(i["trust"].iloc[0])

        rows.append({
            "code": code,
            "name": _stock_name(g, name_by_code, code),
            "group": gname,
            "group_id": gid,
            "close": _clean(last.get("close")),
            "tech_score": round(tech, 1),
            "ma_align": int(last.get("ma_align") or 0),
            "rsi": _clean(last.get("rsi14")),
            "k": _clean(last.get("k")),
            "d": _clean(last.get("d")),
            "osc": _clean(last.get("osc")),
            "trend": int(last.get("trend") or 0),
            "bos": bool(last.get("bos")),
            "choch": bool(last.get("choch")),
            "fvg_bull": bool(last.get("fvg_bull")),
            "sweep_low": bool(last.get("sweep_low")),
            "bias20": _clean(last.get("bias20")),
            "pe": pe,
            "pe_percentile": _clean(pct) if pct is not None else None,
            "trust_net": trust_net,
            "turnover": _clean(g["turnover"].iloc[-1]),
        })

    rows.sort(key=lambda r: r["tech_score"], reverse=True)
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build()
