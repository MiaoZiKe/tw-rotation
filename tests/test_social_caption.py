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
