"""rrg_lite.json（總覽輪盤小檔）＝ flow_v3 的 date／rrg／sankey 原封不動（2026-10-04 首頁瘦身第二階段）。"""
import json
import re
from pathlib import Path

from pipeline import build_payload as bp

ROOT = Path(__file__).resolve().parents[1]


def _f3():
    return {
        "date": "2026-10-02",
        "rrg": {"date": "2026-10-02", "trail_days": 5, "live_params": {"n": 10},
                "points": [{"group_id": "mlcc", "x": 101.2, "y": 99.5, "quadrant": "weakening",
                            "trail": [["2026-10-01", 101.0, 99.9]], "live_state": {"codes": ["2327"]}}]},
        "sankey": {"nodes": [{"name": "台股成交值"}], "links": [{"source": "台股成交值", "target": "半導體", "value": 1.0}]},
        "share": {"dates": ["x"], "series": []},
        "inst_daily": {"dates": ["x"] * 120, "groups": []},
        "share_daily": {"dates": [], "groups": []},
        "periods": {"5": []},
    }


def test_rrg_lite_payload_keeps_overview_fields_verbatim():
    f3 = _f3()
    lite = bp.rrg_lite(f3)
    assert set(lite) == {"date", "rrg", "sankey"}
    # 原封不動（含盤中續算要用的 live_state／live_params 與軌跡）
    assert lite["rrg"] == f3["rrg"] and lite["sankey"] == f3["sankey"] and lite["date"] == f3["date"]


def test_rrg_lite_payload_drops_flow_page_only_fields():
    lite = bp.rrg_lite(_f3())
    for k in ("inst_daily", "share_daily", "share", "periods"):
        assert k not in lite
    assert len(json.dumps(lite)) < len(json.dumps(_f3()))


def test_rrg_lite_payload_written_by_build_and_read_by_overview():
    src = (ROOT / "pipeline" / "build_payload.py").read_text(encoding="utf-8")
    assert re.search(r'_write\("rrg_lite",\s*rrg_lite\(f3\)\)', src)
    js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert "load('rrg_lite'" in js and "return load('flow_v3')" in js   # 讀不到要退回 flow_v3
