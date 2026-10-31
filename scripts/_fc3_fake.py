"""流向驗證 v3 的假資料產生器（只給 _uitest／截圖用，不進 site/data、不進正式站）。

為什麼：本機與 CI 沒有 data/flowcheck/（工作流才會產出），驗收又要真的點、真的拖。
資料來源是設計總監原型 docs/design/20261101_flowcheck_v3/proto_f.html 內嵌的 2026-09-14～10-30 真資料
（30 個交易日、83 個族群），轉成 flowcheck.run() 實際輸出的欄位名（share／dshare／chg／rel／m_x／m_y／m_quadrant…），
所以前端讀的是跟線上一模一樣的格式。next_wave.json 則依 docs/research/20261101_next_wave_signals.md 第九節的欄位造縮小版。
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "docs" / "design" / "20261101_flowcheck_v3" / "proto_f.html"


def proto_data() -> dict:
    s = PROTO.read_text(encoding="utf-8")
    m = re.search(r"const D=(\{.*?\});\n", s, re.S)
    return json.loads(m.group(1))


def build() -> dict[str, object]:
    """回傳 {相對 data/flowcheck 的路徑: JSON 物件}。"""
    D = proto_data()
    dates = D["dates"]
    files: dict[str, object] = {}
    mk = D["mkt"]
    groups = []
    for g in D["groups"]:
        groups.append({"gid": g["gid"], "name": g["name"], "chain": g["chain"], "tier": "downstream",
                       "members": [], "is_bucket": False})
    files["index.json"] = {
        "schema": 1, "latest": dates[-1], "updated_at": "2026-10-30T12:00:00+00:00", "dates": dates,
        "layers": {d: ["daily"] for d in dates}, "groups": groups, "baseline": {"all": {"agree": 55}},
        "market": {}, "closed_days": [], "missing_days": [], "missing_intraday": [], "params": {},
        "chains": D["chains"],
    }
    for i, d in enumerate(dates):
        gs = {}
        for g in D["groups"]:
            gs[g["gid"]] = {
                "share": g["share"][i], "dshare": g["dshare"][i], "rot": g["rot"][i], "chg": g["chg"][i], "rel": g["rel"][i],
                "adv": 0, "dec": 0, "tv": round((g["share"][i] or 0) * 100, 1), "rs_x": g["mx"][i], "rs_y": g["my"][i],
                "quadrant": g["q"][i], "rs_x_site": g["mx"][i], "rs_y_site": g["my"][i], "quadrant_site": g["q"][i],
                "m_x": g["mx"][i], "m_y": g["my"][i], "m_quadrant": g["q"][i], "inst": [0, 0, 0], "div": g["div"][i]}
        files[f"day/{d}.json"] = {"schema": 1, "date": d, "mkt_chg": mk[i], "mkt_src": "close", "mkt_site": mk[i], "crash": False,
                                  "agree": 55, "div_params": {}, "granularity": "daily", "groups": gs, "members": {},
                                  "signals": [], "news": []}
    for g in D["groups"]:
        c = 100.0; m = 100.0; idx = []; rel = []
        for i in range(len(dates)):
            c *= 1 + (g["chg"][i] or 0) / 100; m *= 1 + mk[i] / 100
            idx.append(round(c, 3)); rel.append(round(c / m * 100, 3))
        files[f"series/{g['gid']}.json"] = {"gid": g["gid"], "dates": dates, "idx": idx, "idx_rel": rel, "share": g["share"], "dshare": g["dshare"], "chg": g["chg"], "rel": g["rel"], "top": []}
    return files


def next_wave(real_path: str | None = None) -> dict:
    """縮小版 next_wave.json；有真檔路徑就直接用真檔（截圖用）。"""
    if real_path and Path(real_path).exists():
        return json.loads(Path(real_path).read_text(encoding="utf-8"))
    st = lambda spread, hit, net, n: {"n_dates": n, "n_eff": n, "spread": spread, "spread_ci": [spread - .4, spread + .4],
                                      "hit": hit, "hit_ci": [hit - .1, hit + .1], "net": net, "ic": .05, "p_holm": .02}
    cases = [
        {"date": "2026-03-12", "level": "group", "code": "pre_equip", "name": "前段製程設備", "method": "group-A", "period": "樣本外",
         "fwd": {"5": 7.5, "20": 66.5, "60": 31.2}},
    ]
    return {
        "meta": {"latest": "2026-10-30", "test_start": "2024-01-01", "disclaimer": "統計研究輔助，不是買賣建議；歷史表現不代表未來。",
                 "limits": ["樣本約 6.8 年，沒有完整的空頭樣本外"], "untestable": [{"id": "HOLD", "name": "集保大戶持股比例變化", "why": "資料只有約 8 週，無法回測"}]},
        "methods": [{"id": "INST10", "level": "group", "name": "三大法人（外資＋投信）10 日淨買超占成交量", "verdict": "pass",
                     "verdict_text": "樣本外有效", "passed_horizons": [5, 10],
                     "stats": {"5": {"test": st(.543, .596, .073, 136)}, "10": {"test": st(.982, .652, .512, 135)}}}],
        "cases": cases,
        "case_stats": [{"method": "group-A", "label": "綜合分數A", "period": "樣本外", "n": 414, "mean5": .57, "mean20": 1.28,
                        "median20": -.86, "mean60": 2.42, "win20": .459, "win20_ci": [.412, .507]}],
        "robust": [{"method": "group-INST10", "h": 20, "regime": {"多頭(大盤60日≥0)": {"n_dates": 224, "spread": 1.1}, "空頭(大盤60日<0)": {"n_dates": 92, "spread": -.15}}}],
        "latest": {"date": "2026-10-30", "candidates": [
            {"level": "group", "method": "group-INST10", "code": "telecom", "name": "電信服務", "score": 1.72},
            {"level": "group", "method": "group-INST10", "code": "bank", "name": "銀行金融", "score": 1.65},
            {"level": "group", "method": "group-INST10", "code": "shipping_container", "name": "貨櫃航運", "score": 1.62},
            {"level": "group", "method": "group-REVYOY", "code": "hbm", "name": "HBM 高頻寬記憶體", "score": 1.62}]},
    }


def materialize(out_dir: str, real_nw: str | None = None) -> None:
    """把檔案寫到 out_dir（＝某個 site/data/flowcheck）。"""
    out = Path(out_dir)
    for rel, obj in build().items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    (out / "next_wave.json").write_text(json.dumps(next_wave(real_nw), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    import sys
    materialize(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
