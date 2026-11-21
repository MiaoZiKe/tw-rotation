"""重大訊息 parser（`pipeline/sources/mops.py`）。

這支測試刻意**用 Andy 2026-09-14 真的跑出來的 fixture** 當輸入，不自己編假資料 ——
整件事拖了五天的原因就是沒有人回頭看那份 fixture，所以測試要釘住「照 fixture 寫」這件事。

守住三個會安靜出錯的點：
1. `主旨` 的鍵名**尾端有一個空白**（`"主旨 "`）。用 `row["主旨"]` 拿不到東西，
   而且不會報錯 —— 只會整批被 `if not subject: continue` 丟掉，資料表永遠是空的。
2. `發言時間` 是 `70003` 這種**沒有補零**的字串，直接切會變成 70:00:3。
3. 民國日期要轉西元。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.sources import mops  # noqa: E402

FIXTURE = Path(__file__).resolve().parent.parent / "docs" / "fixtures" / "material_news_probe.json"


def _fixture_rows() -> list[dict]:
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for r in d["results"]:
        if r.get("id") == "twse_t187ap04_L" and isinstance(r.get("sample"), list):
            return r["sample"]
    raise AssertionError("fixture 裡找不到 twse_t187ap04_L 的 sample")


def test_fixture_還在而且是那天跑的():
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert d["probe"] == "material_news"
    assert d["at"].startswith("2026-09-14"), "這份 fixture 是 Andy 按下 Run workflow 那次的產物"
    ids = {r["id"]: r.get("status") for r in d["results"]}
    assert ids.get("twse_t187ap04_L") == 200, "端點當時是通的，所以沒有理由再等他按一次"


def test_主旨的鍵名尾端有空白():
    """這是整支 parser 最容易安靜出錯的地方，單獨釘一條。"""
    rows = _fixture_rows()
    assert any("主旨 " in r for r in rows), "fixture 的鍵名應該帶尾端空白"
    # 用沒有空白的鍵去拿會拿不到 —— 這正是會讓整張表永遠是空的那個寫法
    assert all(r.get("主旨") is None for r in rows)


def test_解析真實fixture():
    df = mops._parse(_fixture_rows(), "TWSE")
    assert not df.empty, "真實 fixture 應該解得出東西"
    assert set(["news_id", "code", "name", "date", "time", "market",
                "subject", "clause", "occurred", "detail"]) <= set(df.columns)
    r = df.iloc[0]
    assert r["code"].isdigit() and len(r["code"]) == 4
    assert r["date"].startswith("202"), f"民國要轉西元，拿到 {r['date']}"
    assert len(r["subject"]) > 2, "主旨不可以是空的（鍵名帶空白那個坑）"
    assert r["market"] == "TWSE"


def test_發言時間會補零():
    assert mops._hhmmss("70003") == "07:00:03", "5 碼要先補零，不然會變成 70:00:3"
    assert mops._hhmmss("143012") == "14:30:12"
    assert mops._hhmmss(None) == ""


def test_沒有主旨或日期的列會被丟掉():
    df = mops._parse([
        {"公司代號": "2330", "發言日期": "1150913", "主旨 ": "測試", "發言時間": "90000"},
        {"公司代號": "2330", "發言日期": "1150913", "主旨 ": "   "},   # 主旨空白
        {"公司代號": "2454", "主旨 ": "沒有日期"},                      # 沒日期
        {"發言日期": "1150913", "主旨 ": "沒有代號"},                   # 沒代號
    ], "TWSE")
    assert len(df) == 1


def test_同一則不會重複():
    row = {"公司代號": "2330", "發言日期": "1150913", "主旨 ": "測試", "發言時間": "90000"}
    df = mops._parse([row, dict(row)], "TWSE")
    assert len(df) == 1, "news_id 要能去重"


def test_說明會截斷但不砍主旨():
    df = mops._parse([{"公司代號": "2330", "發言日期": "1150913",
                       "主旨 ": "短主旨", "說明": "x" * 5000, "發言時間": "90000"}], "TWSE")
    assert len(df.iloc[0]["detail"]) == 800
    assert df.iloc[0]["subject"] == "短主旨"


def test_抓不到一律回空而不是炸掉(monkeypatch):
    monkeypatch.setattr(mops.http, "get", lambda *a, **k: None)
    out = mops.material_news()
    assert isinstance(out, pd.DataFrame) and out.empty
