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
    L = txt.splitlines()
    assert L[0] == "盤中消息" and L[1] == "資金輪盤：" and L[2].startswith("・領先 ") and L[3].startswith("・落後 ")   # 2026-10-26 Andy 指定格式
    assert "資金分流樹：" in L and "熱力圖：" in L and L[-2].startswith("#台股") and "資料：" not in txt   # 盤中文案不放免責／來源
    assert L[-1].startswith("https://") and txt.count("https://") == 1 and " → " not in txt   # Andy：「連結只需要附在最底下就好」
    assert "#heatmap" not in txt
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
    assert L[0] == "盤後融資融券" and L[1] == "融資維持率："      # 2026-10-26 Andy 盤中格式套用到盤後
    assert "・上市（估算）168.20%，較前日 -1.35pp" in L
    assert L[L.index("融資：") + 1] == "・增加 長榮、華邦電、群創；" and L[L.index("融資：") + 2] == "・減少 台積電、聯電、鴻海"
    assert L[L.index("融券：") + 1] == "・增加 友達、力積電、南亞科；" and L[L.index("融券：") + 2] == "・減少 英業達、廣達、緯創"
    assert L[-2].startswith("#台股 #融資") and L[-1].endswith("#market/credit") and "utm_campaign=credit_1022" in L[-1]
    assert txt.count("https://") == 1 and ss.DISCLAIMER not in txt      # 網址只在最底下、不放免責
    assert len(txt) <= 480
    # 盤後法人那篇不再帶融資
    close = ss.build_text("close", "10/21 17:20", shots, "2026-10-21", "20261021")
    assert "融資" not in close


def test_盤後文案_照盤中格式():
    shots = [{"name": "inst-today", "ok": True, "read": [["外資", "−815.8億"], ["投信", "+94.9億"], ["自營商", "−273.8億"], ["三大法人合計", "−994.7億"]]},
             {"name": "streak-foreign", "ok": True, "read": {"buy": ["緯穎", "廣達"], "sell": ["台積電", "聯發科"]}},
             {"name": "fut-oi", "ok": True, "read": "外資 -87,297 投信 +83,601 自營商 +3,260"}]
    txt = ss.build_text("close", "10/22 17:20", shots, "2026-10-22", "20261022")
    L = txt.splitlines()
    assert L[0] == "盤後消息" and L[1] == "三大法人買賣超：" and L[2] == "・外資 -815.8億、投信 +94.9億；" and L[3] == "・自營 -273.8億、合計 -994.7億"
    assert "外資：" in L and "・買超 緯穎、廣達；" in L and "台指期法人淨未平倉：" in L
    assert L[-2].startswith("#台股") and L[-1].endswith("#market/inst") and txt.count("https://") == 1
    assert " → " not in txt and ss.DISCLAIMER not in txt and len(txt) <= 480


def test_融資卡歸盤後融資那篇():
    kinds = {t["name"]: t["kind"] for t in ss.TARGETS}
    assert kinds["credit-ratio"] == kinds["credit-rank"] == "credit"
    assert all(kinds[n] == "close" for n in ("inst-today", "streak-foreign", "streak-trust", "fut-oi", "retail-ratio"))
