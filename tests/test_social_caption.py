"""社群文案：4 行全滿時實際字元數要 ≤ 480（Threads 上限 500）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_snap as ss  # noqa: E402


def _shots():
    long3 = ["石化與塑膠產業", "PCB 硬板製造", "CCL 銅箔基板"]
    return [
        {"name": "rotation", "ok": True, "lines": [["領先", long3], ["落後", ["晶圓代工", "ETF", "HPC 與網通 IC"]]]},
        {"name": "sankey", "ok": True, "notes": [["流入前五", long3], ["流出前五", ["ETF", "晶圓代工", "HPC 與網通 IC"]]]},
        {"name": "heat", "ok": True, "heat": [["軟板", 9.7], ["玻纖布", 9.4], ["電阻與被動保護", -4.4], ["AR VR XR 光學", -2.7], ["其他", 0.1]]},
        {"name": "market-breadth", "ok": True, "breadth": {"up": "1,507", "down": "577"}},
    ]


def test_caption_full_four_lines_within_480():
    txt = ss.build_text("intraday", "10/20 12:34", _shots(), "2026-10-20", "20261020")
    assert len(txt) <= 480, len(txt)
    assert txt.splitlines()[0].startswith("台股資金地圖｜10/20 12:34")
    assert "utm_medium" not in txt and "即時" not in txt
    assert "utm_campaign=intraday_1020" in txt


def _mf(d="2026-10-21", ratio=168.2, partial=False, rank_d=None, short_d=None):
    return {"margin": {"rows": [{"d": "2026-10-20", "ratio": 170.0}, {"d": d, "ratio": ratio, "partial": partial}],
                       "rank": {"d": rank_d or d, "rows": []}, "short_rank": {"d": short_d or d, "rows": []}}}


def test_盤後融資_資料到齊才發():
    meta = {"data_date": "2026-10-21", "inst_date": "2026-10-21"}
    assert ss.credit_ready(meta, _mf()) == (True, "2026-10-21", "")
    # 整體市場融資還停在前一天（10/21 22:13 那輪實際狀況）
    ok, d, why = ss.credit_ready(meta, _mf(d="2026-10-20"))
    assert not ok and d == "2026-10-20" and "還沒更新" in why
    # 整體市場到了、個股融資還沒到 → 維持率算不出來
    assert not ss.credit_ready(meta, _mf(ratio=None))[0]
    assert not ss.credit_ready(meta, _mf(partial=True))[0]
    assert not ss.credit_ready(meta, _mf(rank_d="2026-10-20"))[0]
    assert not ss.credit_ready(meta, _mf(short_d="2026-10-20"))[0]      # 2026-10-26 第三張融券排行也要同一天
    assert not ss.credit_ready(meta, {})[0]
    # 隔天清晨（價量還沒換天）照樣可以發前一天的融資；隔天 15:30 價量換天後就不再發
    assert ss.credit_ready({"data_date": "2026-10-21"}, _mf())[0]
    assert not ss.credit_ready({"data_date": "2026-10-22"}, _mf())[0]


def test_盤後融資文案_獨立一篇():
    shots = [{"name": "credit-ratio", "ok": True, "read": {"ratio": "168.20", "chg": "−1.35"}},
             {"name": "credit-rank", "ok": True, "read": {"up": ["長榮", "華邦電", "群創"], "down": ["台積電", "聯電", "鴻海"]}},
             {"name": "credit-short", "ok": True, "read": {"up": ["友達", "力積電", "南亞科"], "down": ["英業達", "廣達", "緯創"]}}]
    txt = ss.build_text("credit", "10/22 05:10", shots, "2026-10-21", "20261022")
    L = txt.splitlines()
    assert L[0] == "台股融資籌碼｜10/21"
    assert "上市融資維持率（估算）168.20%（較前日 -1.35pp）" in txt and "#market/credit" in txt
    assert "融資增加 長榮、華邦電、群創；融資減少 台積電、聯電、鴻海" in txt
    assert "融券增加 友達、力積電、南亞科；融券減少 英業達、廣達、緯創" in txt
    assert "utm_campaign=credit_1022" in txt and L[-1].startswith("#台股 #融資")
    assert len(txt) <= 480
    # 盤後法人那篇不再帶融資
    close = ss.build_text("close", "10/21 17:20", shots, "2026-10-21", "20261021")
    assert "融資" not in close


def test_融資卡歸盤後融資那篇():
    kinds = {t["name"]: t["kind"] for t in ss.TARGETS}
    assert kinds["credit-ratio"] == kinds["credit-rank"] == "credit"
    assert all(kinds[n] == "close" for n in ("inst-today", "streak-foreign", "streak-trust", "fut-oi", "retail-ratio"))
