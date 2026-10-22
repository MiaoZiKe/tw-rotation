"""功能介紹影片 02：ETF 現金流試算 —— 成片合成（Andy 10-21 重作版；共用 01_etf/fcore_ren.py）。

用法：python render_cf.py --dev d|m [--frames 1.0,5.5]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_etf"))
import fcore_ren as R  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/02"))


def asof():
    try:
        return json.loads((R.REPO / "site" / "data" / "etf.json").read_text(encoding="utf-8")).get("asof")
    except Exception:  # noqa: BLE001
        return None


R.configure(
    FIXED_BOX=dict(bw=1030, y0=50, card_x=233),
    SCR=SCR, RAW=Path(os.environ.get("FEAT_RAW", str(SCR / "raw"))), NAME="feat02_etf_cashflow", ORDER=["main"], DATA_ASOF=asof,
    SEC={"main": ("ETF 現金流", "月配、複利，先試算", "先試算"), "end": ("ETF 現金流", "現金流規劃一頁試算", "一頁試算")},
    NAV=[("set", "設目標"), ("pick", "勾選比較"), ("combo", "組合 A～C"), ("cx", "複利試算")],
    END_LINES_D=["月配試算・組合分頁・複利試算表"], END_LINES_M=["月配試算・組合分頁", "複利試算表"],
)

if __name__ == "__main__":
    R.main()
