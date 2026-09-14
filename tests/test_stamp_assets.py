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
