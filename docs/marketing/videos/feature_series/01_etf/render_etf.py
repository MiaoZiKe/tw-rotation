"""功能介紹影片 01：ETF —— 成片合成（Andy 10-21 重作版；共用 fcore_ren.py：單一連續錄影＋片尾卡）。

用法：python render_etf.py --dev d|m [--frames 1.0,5.5]（只出單格）
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fcore_ren as R  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/01"))


def asof():
    try:
        return json.loads((R.REPO / "site" / "data" / "etf.json").read_text(encoding="utf-8")).get("asof")
    except Exception:  # noqa: BLE001
        return None


R.configure(
    SCR=SCR, RAW=Path(os.environ.get("FEAT_RAW", str(SCR / "raw"))), NAME="feat01_etf", ORDER=["main"], DATA_ASOF=asof,
    SEC={"main": ("ETF 專區", "挑 ETF：配息、類型、報酬", "挑 ETF"), "end": ("ETF 專區", "一頁完成 ETF 功課", "一頁完成")},
    NAV=[("cal", "配息行事曆"), ("types", "類型與分類卡"), ("ret", "報酬比較")],
    END_LINES_D=["配息行事曆・類型總覽・分類卡・報酬比較"], END_LINES_M=["配息行事曆・類型總覽", "分類卡・報酬比較"],
)

if __name__ == "__main__":
    R.main()
