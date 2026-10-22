"""06 今日事件＋精選文章 v3：產生 storyboard.md、overlap_report.md。用法：python report_ev.py --manual-d N --manual-m N"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_ev  # noqa: E402
import report3  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--manual-d", type=int, default=0)
ap.add_argument("--manual-m", type=int, default=0)
g = ap.parse_args()
C = render_ev.CFG
cfg = dict(scr=C["scr"], here=str(HERE), no="06", title="今日事件＋精選文章", sec_d=C["sec"], sec_m=C.get("sec_m", {}),
           note="訪客在正式站看不到任何一篇文章全文（精選文章可讀全文篇數＝0、目前沒有任何一篇設為限時公開），所以只示範到事件清單、文章頁籤與關鍵字搜尋，不點進文章。")
report3.make(cfg, g.manual_d, g.manual_m, extra={"d_motion": "只有 1 次：進精選文章後單向推近約 0.7 秒（把左側圖示列推出畫面）＋頁面往下捲 60px", "m_motion": "只有進精選文章後往下捲 1 次"})
