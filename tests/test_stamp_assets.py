"""版本戳：部署完之後重新整理就要拿到新的 JS，不用按 Ctrl+F5。

2026-09-14 實際發生過：部署明明成功了，瀏覽器還在用快取裡 124,428 bytes 的舊
`app.js`（伺服器上是 125,114），Andy 因此回報「我沒看到最新資訊」。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stamp_assets", ROOT / "scripts" / "stamp_assets.py")
sa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa)


def test_自家的js會被加戳():
    html = '<script src="app.js"></script>'
    out, n = sa.stamp_html(html, "abc123")
    assert out == '<script src="app.js?v=abc123"></script>'
    assert n == 1


def test_vendor不加戳():
    """ECharts、three.js 這些一個好幾百 KB 又幾乎不變，每次部署重抓是白白浪費頻寬。"""
    html = '<script src="vendor/echarts.min.js"></script>'
    out, n = sa.stamp_html(html, "abc123")
    assert out == html
    assert n == 0


def test_外部網址不動():
    html = ('<link href="https://fonts.googleapis.com/x.css" rel="stylesheet">'
            '<script src="//cdn.example.com/a.js"></script>')
    out, n = sa.stamp_html(html, "abc123")
    assert out == html and n == 0


def test_重複執行會換掉舊戳而不是疊加():
    """工作流可能重跑，戳兩次不能變成 app.js?v=a?v=b。"""
    once, _ = sa.stamp_html('<script src="app.js"></script>', "aaa")
    twice, n = sa.stamp_html(once, "bbb")
    assert twice == '<script src="app.js?v=bbb"></script>'
    assert n == 1


def test_css也會被加戳():
    out, n = sa.stamp_html('<link rel="stylesheet" href="style.css">', "v1")
    assert 'href="style.css?v=v1"' in out and n == 1


def test_實際的index_html每一支自家js都被戳到():
    """釘住真檔案：漏掉任何一支，那一支就會繼續吃快取。"""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    out, n = sa.stamp_html(html, "zzz")
    assert n >= 6, f"只戳到 {n} 個，index.html 的 script 標籤是不是改了"
    for f in ("app.js", "live.js", "industry.js", "chart.js"):
        assert f'src="{f}?v=zzz"' in out, f"{f} 沒有被戳到"
    # vendor 的一支都不能被動到
    assert 'src="vendor/echarts.min.js?v=' not in out


def test_戳記本身不含問號或引號():
    """戳記會被塞進屬性值裡，帶了奇怪字元會把 HTML 弄壞。"""
    v = sa.stamp_value()
    assert v and '"' not in v and "?" not in v and "&" not in v


# ---------------------------------------------------------------- 給人看的版號
# Andy 2026-09-16：「我現在對網頁以沒有更新這事情不清楚，每次說有更新，
# 但打開來網頁確跟原本的一樣，所以網頁需要新增版號，確認是否更新」。
# 上面那個 ?v= 是給瀏覽器看的（人看不到），這一組是給人看的。

from datetime import datetime, timezone  # noqa: E402


def test_版號是西元日期加今天第幾版():
    """Andy 2026-09-18：「版號用西元＋日期，以及第幾次改動命名」。

    以前寫 commit 前 7 碼 —— 對得上 GitHub，但人看不出「這是今天第幾版」，
    也看不出兩個版本誰新誰舊（sha 是亂碼、沒有順序）。
    """
    label = sa.build_label(datetime(2026, 9, 18, 3, 15, tzinfo=timezone.utc), sha="1b28dfcd5a02", seq=3)
    assert label == "2026-09-18 第 3 版|11:15", label     # UTC 03:15 → 台北 11:15


def test_日期用台北不是UTC():
    """台北 2026-09-19 07:00 換算 UTC 還是 09-18 23:00，日期寫錯就會差一天。"""
    label = sa.build_label(datetime(2026, 9, 18, 23, 0, tzinfo=timezone.utc), sha="abc1234", seq=1)
    assert label.startswith("2026-09-19 "), label


def test_數不出第幾版就只寫日期():
    """淺 clone 或沒有 git 的環境數不出來；那也要有版號，不能整個掛掉。"""
    label = sa.build_label(datetime(2026, 9, 18, 3, 15, tzinfo=timezone.utc), sha="abc1234", seq=0)
    assert label == "2026-09-18|11:15", label


def test_沒有commit就標local():
    """看到 local 就知道這不是部署出來的版本，而是誰在本機開的。"""
    assert "local" in sa.build_label(datetime(2026, 9, 18, 3, 15, tzinfo=timezone.utc), sha="", seq=2)


def test_meta標籤真的被換掉():
    html = '<meta name="tw:build" content="dev|"><meta name="tw:commit" content="">'
    out, _ = sa.stamp_html(html, "x", datetime(2026, 9, 18, 3, 15, tzinfo=timezone.utc),
                           sha="abcdef1234", seq=2)
    assert '<meta name="tw:build" content="2026-09-18 第 2 版|11:15">' in out
    # commit 短碼沒有丟掉，只是換個地方放（徽章的連結與 tooltip 還要用）
    assert '<meta name="tw:commit" content="abcdef1">' in out


def test_同一天再部署一次版號也會變():
    """不然重跑一次部署，Andy 會以為又沒更新。"""
    a = sa.build_label(datetime(2026, 9, 18, 3, 15, tzinfo=timezone.utc), sha="1b28dfcd", seq=2)
    b = sa.build_label(datetime(2026, 9, 18, 9, 40, tzinfo=timezone.utc), sha="1b28dfcd", seq=3)
    assert a != b


def test_重複戳不會疊起來():
    html = '<meta name="tw:build" content="dev|">'
    once, _ = sa.stamp_html(html, "x", sha="aaaaaaa1", seq=1)
    twice, _ = sa.stamp_html(once, "x", sha="bbbbbbb2", seq=2)
    assert twice.count('name="tw:build"') == 1 and "第 2 版" in twice and "第 1 版" not in twice


def test_實際的index_html有版號與commit兩個meta標籤():
    """漏掉就不會顯示版號，或是徽章連不到 GitHub —— 兩個都是 Andy 要的東西。"""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert 'name="tw:build"' in html and 'name="tw:commit"' in html
    out, _ = sa.stamp_html(html, "zzz", datetime(2026, 9, 18, 3, 15, tzinfo=timezone.utc),
                           sha="feedface", seq=5)
    assert 'content="2026-09-18 第 5 版|11:15"' in out
    assert 'content="feedfac"' in out
