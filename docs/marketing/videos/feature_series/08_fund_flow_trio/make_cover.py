"""功能介紹影片 08 封面（共用 make_cover8.py，來源是錄影原片的一格）。"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_cover8 as M  # noqa: E402

CFG = dict(pill="哩股哩股・功能介紹 08", words=("資金", "三合一"), sub="輪動・分流樹・法人，一次看懂",
           raw=os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat08") + "/raw",
           t=12.2, crop=(88, 66, 996, 560), bibi="spotlight", out=str(HERE))
if __name__ == "__main__":
    M.make("16x9", CFG)
    M.make("9x16", CFG)
