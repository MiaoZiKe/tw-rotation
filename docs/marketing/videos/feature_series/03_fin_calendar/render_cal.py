"""功能介紹影片 03：財經日曆 —— 成片合成（Andy 10-21 重作版；共用 01_etf/fcore_ren.py）。

用法：python render_cal.py --dev d|m [--frames 1.0,5.5]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "01_etf"))
import fcore_ren as R  # noqa: E402

SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/03"))


def asof():
    try:
        return json.loads((R.REPO / "site" / "data" / "earnings.json").read_text(encoding="utf-8")).get("asof")
    except Exception:  # noqa: BLE001
        return None


R.configure(
    FIXED_BOX=dict(bw=1030, y0=50, card_x=233),
    SCR=SCR, RAW=Path(os.environ.get("FEAT_RAW", str(SCR / "raw"))), NAME="feat03_fin_calendar", ORDER=["main"], DATA_ASOF=asof,
    SEC={"main": ("財經日曆", "重要數據何時公布", "何時公布"), "end": ("財經日曆", "財報、法說、FED 一頁掌握", "一頁掌握")},
    NAV=[("tab", "FED 消息分頁"), ("evt", "點事件看分析"), ("more", "財報・法說")],
    END_LINES_D=["月曆・FED 數據分析・財報法說"], END_LINES_M=["月曆・FED 數據分析", "財報・法說"],
)

if __name__ == "__main__":
    R.main()
