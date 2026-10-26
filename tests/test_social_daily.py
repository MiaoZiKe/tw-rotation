"""每日盤前草稿：數字格式、ADR 折溢價、夜盤對照日、推薦語氣新聞過濾、永遠 draft。"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import social_daily as sd  # noqa: E402


def intl(rows):
    return pd.DataFrame(rows, columns=["date", "symbol", "close"])


def test_fmt_sgn_pct():
    assert sd.fmt(7623.676) == "7,623.68"
    assert sd.sgn(-0.5234) == "-0.52" and sd.sgn(0.44) == "+0.44"
    assert round(sd.pct(110, 100), 2) == 10.0


def test_us_lines_and_missing_symbol_noted():
    df = intl([("2026-10-22", "^GSPC", 100.0), ("2026-10-23", "^GSPC", 99.0),
               ("2026-10-22", "^SOX", 10.0), ("2026-10-23", "^SOX", 11.0)])
    notes = []
    out = sd.us_lines(df, notes)
    assert any("標普500 99.00（-1.00%）" in x for x in out)
    assert any("費城半導體" in x and "+10.00%" in x for x in out)
    assert any("道瓊" in n for n in notes)  # 沒有的不編，只記 notes


def test_adr_premium():
    df = intl([("2026-10-22", "TSM", 190.0), ("2026-10-23", "TSM", 200.0),
               ("2026-10-22", "TWD=X", 32.0), ("2026-10-23", "TWD=X", 32.0)])
    price = pd.DataFrame([{"date": "2026-10-22", "code": "2330", "close": 1200.0}])
    notes = []
    line = sd.adr_line(df, price, notes)
    # 200*32/5 = 1280；較 1200 溢價 6.7%
    assert "1,280" in line and "溢價 6.7%" in line


def test_adr_missing_not_invented():
    notes = []
    assert sd.adr_line(intl([("2026-10-23", "^GSPC", 1.0)]), pd.DataFrame(), notes) is None
    assert any("TSM" in n for n in notes)


def test_banned_news_filtered():
    assert not sd.ok_title("16檔年底集團作帳潛力股 鴻海、長榮等法人默默吃貨")
    assert not sd.ok_title("明日必買 目標價上看")
    assert sd.ok_title("南亞科 Q3 獲利創紀錄、股價卻重挫")


def test_draft_is_never_approved(tmp_path):
    f = sd.write_draft(tmp_path, tmp_path / "q", date(2026, 10, 27), "內容", ["n1"])
    t = f.read_text(encoding="utf-8")
    assert "status: draft" in t and "status: approved" not in t
    assert "publish_at: 2026-10-27T08:00+08:00" in t


def test_expected_us_date_skips_weekend():
    assert sd.expected_us_date(date(2026, 10, 26)) == date(2026, 10, 23)   # 週一看週五
    assert sd.expected_us_date(date(2026, 10, 27)) == date(2026, 10, 26)   # 週二看週一


def test_stale_us_warns():
    df = intl([("2026-10-22", "^GSPC", 100.0), ("2026-10-23", "^GSPC", 99.0)])
    notes = []
    sd.us_lines(df, notes, date(2026, 10, 27))
    assert any("應該有 2026-10-26" in n for n in notes)
