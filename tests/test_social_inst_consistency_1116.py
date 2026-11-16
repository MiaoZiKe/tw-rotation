"""2026-11-16：盤後主貼文「三大法人買賣超」圖卡與文案必須同一口徑、同一份數字。

事故（11/13 資料乾跑 snaps/close-20261116-1050）：圖 threads_inst-today.png 寫投信 +95.4 億、合計 +452.7 億，
文案寫投信買超 82.4 億、合計 +439.7 億。原因：圖（social_native.b_inst_today）優先取晚間修訂版 rev，
文案（social_snap.close_reads／fast_read_inst）取主數字＝證交所 15:00 首次公布版（DECISIONS #363）。
修法：圖改回主數字。這裡用 11/13 真實數字（含 rev）驗三條路徑讀出來的四格一致。"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import social_native as NAT  # noqa: E402
import social_snap as S  # noqa: E402

# 資料湖 inst_market_first（首次公布）與 inst_market_daily（晚間修訂）2026-11-13 的淨額（億元）
IM = {"rows": [
    {"d": "2026-11-12", "f": -6.85, "t": 123.85, "dl": -65.41, "tot": 51.6, "tw": 43100.0, "est": False, "first": True},
    {"d": "2026-11-13", "f": 288.37, "t": 82.37, "dl": 68.92, "tot": 439.66, "tw": 43683.0, "est": False, "first": True,
     "rev": {"f": 288.37, "t": 95.39, "dl": 68.92, "tot": 452.68}},
]}


def _tiles_from_image():
    html = NAT.b_inst_today("threads", 1080, 1200, {"jget": lambda n: IM})
    pairs = re.findall(r"<div class=l>([^<]+)</div><div class=vv[^>]*>([^<]+)<u>億</u>", html)
    return {lab: float(v.replace("−", "-").replace(",", "")) for lab, v in pairs}


def test_image_uses_first_published_not_rev():
    img = _tiles_from_image()
    assert img == {"外資": 288.4, "投信": 82.4, "自營商": 68.9, "合計": 439.7}


def test_image_matches_caption_numbers():
    img = _tiles_from_image()
    # 文案「🏦 三大法人買賣超」那段的來源（fast_read_inst）
    txt = {lab: float(v.replace("億", "").replace("−", "-").replace(",", "")) for lab, v in S.fast_read_inst(IM)}
    assert txt == {"外資": img["外資"], "投信": img["投信"], "自營商": img["自營商"], "三大法人合計": img["合計"]}
    # 文案「🧭 盤面分析」與主文重點數字的來源（close_reads）
    reads = S.close_reads(IM, {}, {}, {}, [], {})
    joined = "\n".join(reads)
    assert f"外資買超 {img['外資']:,.1f} 億" in joined
    assert f"投信買超 {img['投信']:,.1f} 億" in joined
