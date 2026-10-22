"""07 熱力圖＋題材 v3：產生 storyboard.md、overlap_report.md。用法：python report_hm.py --manual-d N --manual-m N"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "06_events_articles"))
import render_hm  # noqa: E402
import report3  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--manual-d", type=int, default=0)
ap.add_argument("--manual-m", type=int, default=0)
g = ap.parse_args()
C = render_hm.CFG
cfg = dict(scr=C["scr"], here=str(HERE), no="07", title="熱力圖＋題材", sec_d=C["sec"], sec_m=C.get("sec_m", {}),
           note="產業熱力圖在正式站「點方塊跳族群頁」要 Plus 以上（訪客點了無效），所以本片不點方塊跳頁，改示範分組與色階篩選；題材熱力圖點方塊是同頁開剖析圖，訪客可用。")
report3.make(cfg, g.manual_d, g.manual_m, extra={"d_motion": "只有 1 次：點題材方塊後單向推近約 0.7 秒（把左側圖示列推出畫面）＋頁面往下捲到剖析圖", "m_motion": "點題材方塊後網站自己往下捲到剖析圖 1 次"})
