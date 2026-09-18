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


def test_版號是commit前7碼加台北建置時間():
    label = sa.build_label(datetime(2026, 9, 16, 3, 15, tzinfo=timezone.utc), sha="1b28dfcd5a02")
    assert label == "1b28dfc|09-16 11:15", label      # UTC 03:15 → 台北 11:15


def test_沒有commit就寫local():
    """看到 local 就知道這不是部署出來的版本，而是誰在本機開的。"""
    assert sa.build_label(datetime(2026, 9, 16, 3, 15, tzinfo=timezone.utc), sha="").startswith("local|")


def test_meta標籤真的被換掉():
    html = '<meta name="tw:build" content="dev|">'
    out, _ = sa.stamp_html(html, "x", datetime(2026, 9, 16, 3, 15, tzinfo=timezone.utc), sha="abcdef1234")
    assert out == '<meta name="tw:build" content="abcdef1|09-16 11:15">'


def test_同一個commit再部署一次版號也會變():
    """不然重跑一次部署，Andy 會以為又沒更新。"""
    a = sa.build_label(datetime(2026, 9, 16, 3, 15, tzinfo=timezone.utc), sha="1b28dfcd")
    b = sa.build_label(datetime(2026, 9, 16, 9, 40, tzinfo=timezone.utc), sha="1b28dfcd")
    assert a != b


def test_重複戳不會疊起來():
    html = '<meta name="tw:build" content="dev|">'
    once, _ = sa.stamp_html(html, "x", sha="aaaaaaa1")
    twice, _ = sa.stamp_html(once, "x", sha="bbbbbbb2")
    assert twice.count("content=") == 1 and "bbbbbbb" in twice and "aaaaaaa" not in twice


def test_實際的index_html有版號的meta標籤():
    """漏掉這個標籤，頁面上就不會顯示版號 —— 而那正是 Andy 要的東西。"""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert 'name="tw:build"' in html
    out, _ = sa.stamp_html(html, "zzz", sha="feedface")
    assert 'content="feedfac|' in out
