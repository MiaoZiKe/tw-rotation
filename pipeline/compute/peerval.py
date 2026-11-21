"""族群同業估值位階（P-1107-04，M2 的「貴不貴」）—— site/data/peer_val.json。

Andy 2026-11-09 點頭「02 05 03 04 06」。回答的問題只有一個：**同一個族群裡，這一檔的估值落在同業的哪個位置**。
只陳述位置（第幾百分位、高於／低於族群中位數），不寫「便宜可買」「高估」這類判斷（提案法遵段）。

資料（全部是 build_payload 已經算好的東西，不新增任何來源、不多抓）：
  · 本益比 pe、股價淨值比 pb、是否虧損 is_loss、營收年增 rev_yoy —— fundamental.json 那一份（compute/fundamental.valuation、
    revenue_momentum）。本益比＝收盤 ÷ 近四季 EPS（上市、上櫃同一口徑，自算；不是 BWIBBU 的值）。
  · 殖利率 dy —— explore.json 的 dy（個股頁 dividends.yield_ttm：近四次現金股利 ÷ 收盤，跟個股頁「殖利率（近四次）」同一個數）。
  · 自己的歷史位置 —— explore.json 的 pe_pct／pe_n（目前本益比在自己過去各季本益比的百分位，最多近 5 年 20 季）。
  · 族群 —— groups.yaml（loader.membership，含疊加族群）；不在任何族群的普通股，用法定產業別自動桶 `ind_<產業>`，
    桶內同業＝同產業別、也不在任何族群的普通股（跟 fundamental.group_valuation 的 ind_ 桶同一群人，個股頁基本面卡
    「同族群（塑膠・其他，n=7）」那個 n 就是它），只給個股頁小卡用。

口徑（寫死，前端照抄，不重算）：
  1. 同業百分位＝同業有效樣本裡「比它低」的檔數占比 × 100，四捨五入到整數（最低的那檔＝0；5 檔裡最高的＝80）。
     跟 compute/fundamental._pct_within（個股頁基本面卡「同業分位 N%」）同一個公式 —— 兩張卡擺在同一頁，同一個族群數字要對得上。
     （自己歷史位置沿用 explore.pe_position 的中間名次法，那是另一個概念、另一個欄位。）
  2. 有效樣本＜5 檔（MIN_N）→ 那一欄不給百分位，前端寫「同業樣本不足」。不硬算。
  3. 本益比：近四季 EPS ≤ 0 → 不給本益比、不排進分位，狀態 "loss"（前端寫「本益比不適用（虧損）」）；
     EPS 沒資料 → 狀態 "na"；本益比 < 3 或 > 200 倍 → 照印數字但不排進分位，狀態 "dist"（前端寫「失真不排名」）——
     門檻跟 fundamental.PE_MIN／PE_MAX 同一組（EPS 接近 0 時本益比會暴衝到幾百、幾千倍，排進去只會把其他人全擠到一邊）。淨值比：每股淨值 ≤ 0 或缺 → 空。殖利率：沒有近四次配息資料 → 空（不當成 0）。
  4. 方向：本益比、淨值比、營收年增是「數值越大、百分位越大」；**殖利率反過來**，存的是「殖利率由高到低」的位置
     （殖利率最高＝0）——這樣四條估值條同一個方向：0＝同業估值最低（便宜端）、100＝最高（貴端）。
     營收年增不是估值，只是「同業低→高」，前端用中性色。
  5. 自己的歷史位置：近 3 年以上（≥12 季，OWN_MIN_Q）有正本益比才給；虧損或季數不夠給空。
  6. 中位數只拿有效樣本算；樣本不足一樣不給。
"""
from __future__ import annotations

import math

import pandas as pd

from ..util.roc import is_common_stock
from .fundamental import PE_MAX, PE_MIN

MIN_N = 5          # 同業有效樣本下限（提案：樣本 < 5 檔要明確標示，不硬算）
OWN_MIN_Q = 12     # 自己歷史位置至少要幾季（3 年）；explore.pe_position 本身的下限是 8 季，這裡更嚴

COLS = ["code", "name", "pe", "pb", "dy", "yoy", "p_pe", "p_pb", "p_dy", "p_yoy", "own", "own_n", "st"]


def _num(v, nd: int | None = None):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, nd) if nd is not None else f


def peer_pct(values: list[float], v) -> int | None:
    """同業百分位（口徑 1）：比它低的檔數 ÷ 有效檔數 × 100。values 只放有效值；v 沒值或樣本＜MIN_N 回 None（口徑 2）。"""
    v = _num(v)
    if v is None or len(values) < MIN_N:
        return None
    below = sum(1 for x in values if x < v)
    return int(round(below / len(values) * 100))


def _median(values: list[float]):
    if len(values) < MIN_N:
        return None
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def stock_metrics(f: dict, ex: dict | None) -> dict:
    """一檔的四個數字＋本益比狀態＋自己的歷史位置。f＝fundamental.json 的一列，ex＝explore.json 的那一列（dict）。"""
    eps = _num(f.get("ttm_eps"))
    pe = _num(f.get("pe"))
    if f.get("is_loss") or (eps is not None and eps <= 0):
        st, pe = "loss", None
    elif pe is None or pe <= 0:
        st, pe = "na", None
    elif pe < PE_MIN or pe > PE_MAX:
        st = "dist"
    else:
        st = ""
    pb = _num(f.get("pb"))
    if pb is not None and pb <= 0:
        pb = None
    ex = ex or {}
    dy = _num(ex.get("dy"))
    if dy is not None and dy < 0:
        dy = None
    yoy = _num(f.get("rev_yoy"))
    own_n = int(_num(ex.get("pe_n")) or 0)
    own = _num(ex.get("pe_pct")) if (st in ("", "dist") and own_n >= OWN_MIN_Q) else None
    return {"pe": pe, "pe_rank": pe if st == "" else None, "pb": pb, "dy": dy, "yoy": yoy, "st": st,
            "own": int(round(own)) if own is not None else None, "own_n": own_n}


def group_block(name: str, kind: str, members: list[tuple[str, str | None, dict]]) -> dict:
    """一個族群：每檔一列（照 COLS），加上各欄有效樣本數與中位數。members＝[(代號, 名稱, stock_metrics 結果)]。"""
    vals = {k: [m["pe_rank" if k == "pe" else k] for _, _, m in members if m["pe_rank" if k == "pe" else k] is not None]
            for k in ("pe", "pb", "dy", "yoy")}
    neg_dy = [-x for x in vals["dy"]]
    rows = []
    for code, nm, m in members:
        rows.append([
            code, nm,
            _num(m["pe"], 1), _num(m["pb"], 2), _num(m["dy"], 2), _num(m["yoy"], 1),
            peer_pct(vals["pe"], m["pe_rank"]),
            peer_pct(vals["pb"], m["pb"]),
            peer_pct(neg_dy, -m["dy"] if m["dy"] is not None else None),   # 口徑 4：殖利率由高到低
            peer_pct(vals["yoy"], m["yoy"]),
            m["own"], m["own_n"], m["st"],
        ])
    rows.sort(key=lambda r: str(r[0]))   # 預設依代號（提案法遵段：不預設依估值排序，避免看起來像推薦清單）
    med = {k: _num(_median(v), 2) for k, v in vals.items()}
    return {"name": name, "kind": kind, "n": len(members),
            "nv": {k: len(v) for k, v in vals.items()}, "med": med,
            "loss": sum(1 for _, _, m in members if m["st"] == "loss"),
            "rows": rows}


def build_json(fund_rows: list[dict], explore_payload: dict | None, membership: pd.DataFrame | None,
               company: pd.DataFrame | None = None, ind_names: dict | None = None,
               asof: str | None = None) -> dict:
    """組 peer_val.json。

    groups：族群代號 → group_block；yaml 族群 kind="grp"，法定產業別自動桶 kind="ind"（只收不在任何 yaml 族群的普通股，
            桶內同業＝同產業別、也沒有 yaml 族群的普通股，跟 fundamental 的 ind_ 桶同一群）。
    stocks：代號 → [族群代號…]（yaml 族群在前；都沒有才給一個 ind 桶）。
    """
    fund = {str(r.get("code")): r for r in (fund_rows or []) if r.get("code")}
    ex = {}
    if explore_payload and explore_payload.get("cols") and explore_payload.get("rows"):
        cols = explore_payload["cols"]
        for r in explore_payload["rows"]:
            ex[str(r[0])] = dict(zip(cols, r))
    metr = {c: stock_metrics(f, ex.get(c)) for c, f in fund.items()}
    names = {c: f.get("name") for c, f in fund.items()}

    groups: dict[str, dict] = {}
    stocks: dict[str, list[str]] = {}
    if membership is not None and not membership.empty:
        for (gid, gname), g in membership.groupby(["group_id", "group_name"], sort=True):
            codes = list(dict.fromkeys(str(c) for c in g["code"]))
            mem = [(c, names.get(c), metr.get(c) or stock_metrics({}, None)) for c in codes]
            groups[str(gid)] = group_block(str(gname), "grp", mem)
            for c in codes:
                stocks.setdefault(c, []).append(str(gid))

    # 不在任何 yaml 族群的普通股：退回法定產業別（只為了個股頁小卡；族群頁表只開 yaml 族群）
    if company is not None and not company.empty and "industry" in company.columns:
        ind = company.drop_duplicates("code").set_index(company.drop_duplicates("code")["code"].astype(str))["industry"]
        ind_names = ind_names or {}
        need: dict[str, list[str]] = {}
        for c in fund:
            if c in stocks or not is_common_stock(c):     # ETF、特別股不比估值
                continue
            i = ind.get(c)
            if i is None or (isinstance(i, float) and math.isnan(i)) or not str(i).strip():
                continue
            need.setdefault(str(i), []).append(c)
        for i, orphan in need.items():
            gid = "ind_" + i
            mem = [(c, names.get(c), metr[c]) for c in sorted(orphan)]
            groups[gid] = group_block(str(ind_names.get(i, i)), "ind", mem)
            for c in orphan:
                stocks.setdefault(c, []).append(gid)

    return {"v": 1, "asof": asof, "min_n": MIN_N, "own_min_q": OWN_MIN_Q, "cols": COLS,
            "groups": groups, "stocks": stocks}
