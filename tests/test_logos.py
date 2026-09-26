"""公司 Logo 資料端（2026-09-26）：網域抽取、圖示解析、空白／過小判定、增量、索引、build_payload 輸出。

跟 test_sources_v3.py 同一條規矩：開發環境沒有對外網路，http.get_bytes / http.get 一律 monkeypatch，
圖檔用 Pillow 當場畫。獨立成一個檔是因為 Logo 牽涉 sources、run_backfill、build_payload 三處，
塞進 test_sources_v3.py（已經 40 多個測試）會很難找。
"""
from __future__ import annotations

import io
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config  # noqa: E402
from pipeline.sources import logos as lg  # noqa: E402
from pipeline.util import http, store  # noqa: E402


def _png(size=(180, 180), bg=(0, 0, 0, 0), fg=(200, 30, 30, 255), fmt="PNG", sizes=None) -> bytes:
    """畫一張「透明底＋中間一塊色」的假 Logo。bg==fg 時就是單色空白圖。"""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", size, bg)
    w, h = size
    ImageDraw.Draw(img).rectangle([w // 4, h // 4, w * 3 // 4, h * 3 // 4], fill=fg)
    buf = io.BytesIO()
    if fmt == "ICO":
        img.save(buf, format="ICO", sizes=sizes or [(16, 16), (48, 48)])
    else:
        img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "data" / "_state")
    monkeypatch.setattr(config, "SITE_DATA", tmp_path / "site" / "data")
    for p in (config.DATA, config.STATE, config.SITE_DATA):
        p.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "LOGOS_ENABLED", True)
    return tmp_path


def _web(routes: dict, calls: list | None = None):
    """假的 http.get_bytes：routes = {網址: (狀態碼, 內容, Content-Type) 或 "down"}，沒列到的回 404。"""
    def fake(url, **kw):
        if calls is not None:
            calls.append(url)
        hit = routes.get(url)
        if hit is None:
            return (404, b"", "text/html", url)
        if hit == "down":
            return None
        return (hit[0], hit[1], hit[2], url)
    return fake


# ------------------------------------------------------------------ 網域抽取

@pytest.mark.parametrize("raw,host", [
    ("https://www.tsmc.com", "www.tsmc.com"),
    ("www.acc.com.tw", "www.acc.com.tw"),
    ("WWW.FOPCO.COM.TW", "www.fopco.com.tw"),
    ("http://www.aten.com/tw/zh/", "www.aten.com"),
    ("https://www.hiroca.co:8443/", "www.hiroca.co"),
    ("無", None), ("", None), (None, None), (float("nan"), None), ("-", None),
    ("ir@abc.com.tw", None),                                   # 電子郵件填錯欄
    ("無 ; www.abc.com.tw", "www.abc.com.tw"),                 # 取第一個像網址的
    ("http://192.168.1.1/", None),                             # IP 不是公司網域
    ("localhost", None),
])
def test_extract_domain(raw, host):
    assert lg.extract_domain(raw) == host


def test_base_domain_merges_www():
    assert lg.base_domain("www.tsmc.com") == lg.base_domain("tsmc.com") == "tsmc.com"


# ------------------------------------------------------------------ HTML 圖示連結

def test_parse_icon_links_prefers_apple_touch_and_skips_svg_and_data():
    html = """<html><head>
      <link rel="icon" href="/favicon-16.png" sizes="16x16">
      <link rel="shortcut icon" href="favicon.ico">
      <link rel="icon" type="image/svg+xml" href="/logo.svg">
      <link rel="icon" href="data:image/png;base64,AAAA">
      <link rel="icon" href="/fav-96.png" sizes="96x96">
      <link rel="apple-touch-icon" href="https://cdn.x.com/apple.png" sizes="180x180">
      <link rel="stylesheet" href="/a.css">
    </head></html>"""
    got = lg.parse_icon_links(html, "https://www.x.com.tw/tw/index.html")
    urls = [g["url"] for g in got]
    assert urls[0] == "https://cdn.x.com/apple.png"
    assert urls[1] == "https://www.x.com.tw/fav-96.png"
    assert "https://www.x.com.tw/tw/favicon.ico" in urls        # 相對路徑照最終網址解
    assert not any(u.endswith(".svg") or u.startswith("data:") or u.endswith(".css") for u in urls)


def test_parse_icon_links_respects_base_tag_and_bad_html():
    got = lg.parse_icon_links('<base href="https://s.x.com/assets/"><link rel=icon href="i.png"><<<',
                              "https://www.x.com/")
    assert [g["url"] for g in got] == ["https://s.x.com/assets/i.png"]


# ------------------------------------------------------------------ 圖檔正規化與空白判定

def test_normalize_image_to_64_png_keeps_aspect():
    from PIL import Image
    png, orig = lg.normalize_image(_png((200, 100)))
    img = Image.open(io.BytesIO(png))
    assert img.format == "PNG" and img.size == (64, 64) and orig == (200, 100)
    assert img.getpixel((32, 2))[3] == 0          # 橫長圖上下補透明邊，沒有被拉伸成正方形


def test_normalize_image_rejects_too_small_16px_globe():
    with pytest.raises(lg.LogoReject) as e:
        lg.normalize_image(_png((16, 16)))
    assert e.value.reason == "too_small"


@pytest.mark.parametrize("bg,fg", [
    ((0, 0, 0, 0), (0, 0, 0, 0)),                  # 全透明
    ((255, 255, 255, 255), (255, 255, 255, 255)),  # 全白
    ((240, 240, 240, 255), (242, 242, 242, 255)),  # 幾乎單色
])
def test_normalize_image_rejects_blank(bg, fg):
    with pytest.raises(lg.LogoReject) as e:
        lg.normalize_image(_png((64, 64), bg=bg, fg=fg))
    assert e.value.reason == "blank"


def test_white_logo_on_transparent_is_not_blank():
    """白色 Logo＋透明底：白底上看不見，但黑底上看得到 —— 不是空白。"""
    png, _ = lg.normalize_image(_png((64, 64), fg=(255, 255, 255, 255)))
    assert png


def test_normalize_image_ico_uses_largest_frame_and_bad_bytes():
    _png_bytes, orig = lg.normalize_image(_png((48, 48), fmt="ICO", sizes=[(16, 16), (48, 48)]))
    assert orig == (48, 48)
    with pytest.raises(lg.LogoReject) as e:
        lg.normalize_image(b"not an image")
    assert e.value.reason == "bad_image"


# ------------------------------------------------------------------ 抓單一家

def test_fetch_logo_site_apple_touch_icon(monkeypatch):
    html = b'<link rel="apple-touch-icon" href="/apple.png">'
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/": (200, html, "text/html"),
        "https://www.x.com.tw/apple.png": (200, _png(), "image/png"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "site:apple-touch-icon" and got["png"]


def test_fetch_logo_soft_404_then_google_backup(monkeypatch):
    """/favicon.ico 回 200＋HTML（軟 404）不能當圖；最後由 Google s2 補上。"""
    s2 = config.LOGO_GOOGLE_S2.format(domain="www.x.com.tw")
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/": (200, b"<html>no icons</html>", "text/html"),
        "https://www.x.com.tw/favicon.ico": (200, b"<!doctype html><html>", "text/html"),
        s2: (200, _png((64, 64)), "image/png"),
    }))
    got = lg.fetch_logo("https://www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "google_s2"


def test_fetch_logo_google_404_globe_is_none(monkeypatch):
    s2 = config.LOGO_GOOGLE_S2.format(domain="www.x.com.tw")
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/": (200, b"<html></html>", "text/html"),
        s2: (404, _png((16, 16)), "image/png"),                 # 找不到：404 附地球
    }))
    assert lg.fetch_logo("www.x.com.tw")["status"] == "none"


def test_fetch_logo_tiny_icons_everywhere_is_too_small(monkeypatch):
    s2 = config.LOGO_GOOGLE_S2.format(domain="www.x.com.tw")
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/": (200, b"<html></html>", "text/html"),
        "https://www.x.com.tw/favicon.ico": (200, _png((16, 16), fmt="ICO", sizes=[(16, 16)]), "image/x-icon"),
        s2: (200, _png((16, 16)), "image/png"),
    }))
    assert lg.fetch_logo("www.x.com.tw")["status"] == "too_small"


def test_fetch_logo_robots_disallow_skips_google_too(monkeypatch):
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/robots.txt": (200, b"User-agent: *\nDisallow: /\n", "text/plain"),
    }, calls))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "robots"
    assert calls == ["https://www.x.com.tw/robots.txt"]          # 不准拿 Google 繞 robots


def test_fetch_logo_robots_blocks_icon_directory_only(monkeypatch):
    """robots 只擋 /images/：那個目錄的圖示不抓，改用 /favicon.ico。"""
    calls = []
    html = b'<link rel="apple-touch-icon" href="/images/apple.png">'
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/robots.txt": (200, b"User-agent: *\nDisallow: /images/\n", "text/plain"),
        "https://www.x.com.tw/": (200, html, "text/html"),
        "https://www.x.com.tw/images/apple.png": (200, _png(), "image/png"),
        "https://www.x.com.tw/favicon.ico": (200, _png((48, 48), fmt="ICO", sizes=[(48, 48)]), "image/x-icon"),
    }, calls))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["url"] == "https://www.x.com.tw/favicon.ico"
    assert "https://www.x.com.tw/images/apple.png" not in calls


def test_fetch_logo_site_down_uses_google(monkeypatch):
    s2 = config.LOGO_GOOGLE_S2.format(domain="www.x.com.tw")
    monkeypatch.setattr(http, "get_bytes", _web({
        "https://www.x.com.tw/robots.txt": "down", "https://www.x.com.tw/": "down",
        "http://www.x.com.tw/robots.txt": "down", "http://www.x.com.tw/": "down",
        s2: (200, _png((64, 64)), "image/png"),
    }))
    assert lg.fetch_logo("www.x.com.tw")["src"] == "google_s2"


def test_fetch_logo_never_raises(monkeypatch):
    def boom(url, **kw):
        raise RuntimeError("意外")
    monkeypatch.setattr(http, "get_bytes", boom)
    assert lg.fetch_logo("www.x.com.tw")["status"] == "error"
    assert lg.fetch_logo("無")["status"] == "no_website"


# ------------------------------------------------------------------ 一輪：增量、索引、預設圖

def _seed_company(rows):
    store.append("company_info", pd.DataFrame(rows))


def _ok_fetcher(calls, png_of=None):
    def f(website, host):
        calls.append(host)
        png = (png_of or {}).get(host) or lg.normalize_image(_png(fg=(len(host) * 7 % 255, 90, 20, 255)))[0]
        return {"status": "ok", "domain": host, "src": "site:icon", "url": f"https://{host}/i.png",
                "png": png, "orig": [180, 180]}
    return f


def test_run_writes_png_index_and_state(sandbox):
    _seed_company([
        {"code": "2330", "name": "台積電", "market": "TWSE", "industry": "半導體業", "website": "https://www.tsmc.com"},
        {"code": "0050", "name": "元大台灣50", "market": "TWSE", "industry": "ETF", "website": "www.yuanta.com"},
        {"code": "1101", "name": "台泥", "market": "TWSE", "industry": "水泥工業", "website": None},
    ])
    calls = []
    s = lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher(calls))
    assert calls == ["www.tsmc.com"]                      # ETF 與沒網址的不抓
    assert (config.DATA / "logos" / "2330.png").exists()
    idx = json.loads((config.DATA / "logos" / "_index.json").read_text())
    rec = idx["items"]["2330"]
    assert rec["status"] == "ok" and rec["fetched"] == "2026-09-26" and len(rec["sha1"]) == 40
    assert rec["src"] == "site:icon" and rec["domain"] == "www.tsmc.com"
    st = json.loads((config.STATE / "logo_progress.json").read_text())
    assert st["done"] is True and st["have"] == 1 and st["next_due"] == "2026-12-25"
    assert s["pending"] == 0


def test_run_incremental_skips_fresh_and_refreshes_due(sandbox):
    _seed_company([{"code": c, "name": c, "market": "TWSE", "industry": "x", "website": f"www.c{c}.com"}
                   for c in ("1111", "2222", "3333", "4444", "5555")])
    (config.DATA / "logos").mkdir(parents=True, exist_ok=True)
    (config.DATA / "logos" / "_index.json").write_text(json.dumps({"version": 1, "items": {
        "1111": {"status": "ok", "domain": "www.c1111.com", "fetched": "2026-09-01", "sha1": "a"},   # 25 天：不重抓
        "2222": {"status": "ok", "domain": "www.c2222.com", "fetched": "2026-06-01", "sha1": "b"},   # 117 天：重抓
        "3333": {"status": "none", "domain": "www.c3333.com", "fetched": "2026-09-16"},              # 失敗 10 天：先不試
        "4444": {"status": "none", "domain": "www.c4444.com", "fetched": "2026-08-01"},              # 失敗 56 天：再試
        "5555": {"status": "ok", "domain": "www.old5555.com", "fetched": "2026-09-20", "sha1": "c"},  # 網域換了：重抓
    }}))
    calls = []
    lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher(calls))
    assert sorted(calls) == ["www.c2222.com", "www.c4444.com", "www.c5555.com"]


def test_run_limit_priority_and_domain_dedupe(sandbox):
    _seed_company([
        {"code": "2881", "name": "富邦金", "market": "TWSE", "industry": "金融", "website": "www.fubon.com"},
        {"code": "2882", "name": "國泰金", "market": "TWSE", "industry": "金融", "website": "www.cathay.com.tw"},
        {"code": "9999", "name": "同網域", "market": "TWSE", "industry": "金融", "website": "https://fubon.com/"},
        {"code": "1000", "name": "一般", "market": "TWSE", "industry": "x", "website": "www.a1000.com"},
    ])
    calls = []
    s = lg.run(limit=3, today=date(2026, 9, 26), fetcher=_ok_fetcher(calls), priority=["2882", "2881"])
    # 上限 3：族群成分股 2882、2881 先，第三個是代號最小的 1000；9999 留到下一輪
    assert sorted(calls) == ["www.a1000.com", "www.cathay.com.tw", "www.fubon.com"]
    assert s["pending"] == 1 and s["done"] is False
    calls.clear()
    lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher(calls))
    assert calls == ["fubon.com"]
    # 同一輪裡同網域（www.fubon.com 與 fubon.com）只抓一次，兩個代號都有圖
    calls.clear()
    (config.DATA / "logos" / "_index.json").unlink()
    lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher(calls))
    assert sorted(calls) == ["www.a1000.com", "www.cathay.com.tw", "www.fubon.com"]
    assert (config.DATA / "logos" / "9999.png").exists()


def test_run_marks_generic_same_image_across_domains(sandbox):
    _seed_company([{"code": c, "name": c, "market": "TWSE", "industry": "x", "website": f"www.g{c}.com"}
                   for c in ("1001", "1002", "1003", "1004")])
    same = lg.normalize_image(_png(fg=(10, 120, 240, 255)))[0]
    png_of = {f"www.g{c}.com": same for c in ("1001", "1002", "1003")}
    lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher([], png_of))
    idx = lg.read_index()["items"]
    assert [idx[c]["status"] for c in ("1001", "1002", "1003")] == ["generic"] * 3
    assert idx["1004"]["status"] == "ok"
    assert not (config.DATA / "logos" / "1001.png").exists()
    assert set(lg.usable_codes(lg.read_index())) == {"1004"}


def test_generic_counts_domains_not_codes():
    """金控與子公司共用同一個官網、同一張圖是正常的，不能判成預設圖。"""
    items = {c: {"status": "ok", "sha1": "same", "domain": d}
             for c, d in (("2881", "www.fubon.com"), ("2882", "fubon.com"), ("5555", "www.fubon.com"))}
    assert lg.generic_hashes(items) == set()


def test_run_keeps_old_logo_when_refetch_fails(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x",
                    "website": "www.tsmc.com"}])
    lg.run(today=date(2026, 6, 1), fetcher=_ok_fetcher([]))
    lg.run(today=date(2026, 9, 26),
           fetcher=lambda w, h: {"status": "error", "domain": h, "detail": "逾時"})
    rec = lg.read_index()["items"]["2330"]
    assert rec["status"] == "ok" and rec["last_fail"] == "error" and rec["fetched"] == "2026-09-26"
    assert (config.DATA / "logos" / "2330.png").exists()


def test_run_unchanged_logo_does_not_rewrite_file(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x",
                    "website": "www.tsmc.com"}])
    lg.run(today=date(2026, 6, 1), fetcher=_ok_fetcher([]))
    f = config.DATA / "logos" / "2330.png"
    before = f.stat().st_mtime_ns
    lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher([]))       # 到期重抓、圖一樣
    assert f.stat().st_mtime_ns == before


def test_run_records_failures_in_state(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x",
                    "website": "www.tsmc.com"}])
    s = lg.run(today=date(2026, 9, 26),
               fetcher=lambda w, h: {"status": "too_small", "domain": h, "detail": "16x16"})
    st = json.loads((config.STATE / "logo_progress.json").read_text())
    assert st["failures"][0]["status"] == "too_small" and s["counts"] == {"too_small": 1}
    assert not (config.DATA / "logos" / "2330.png").exists()
    assert st["next_due"] == "2026-10-26"                  # 失敗的 30 天後再試


def test_run_disabled_does_not_fetch(sandbox, monkeypatch):
    monkeypatch.setattr(config, "LOGOS_ENABLED", False)
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x",
                    "website": "www.tsmc.com"}])
    calls = []
    s = lg.run(fetcher=_ok_fetcher(calls))
    assert calls == [] and s["skipped"] == "disabled"
    st = json.loads((config.STATE / "logo_progress.json").read_text())
    assert st["skipped"] == "disabled"                     # backfill.yml 守門看這個不放行


def test_removed_status_is_never_refetched(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x",
                    "website": "www.tsmc.com"}])
    (config.DATA / "logos").mkdir(parents=True, exist_ok=True)
    (config.DATA / "logos" / "_index.json").write_text(json.dumps({"items": {
        "2330": {"status": "removed", "domain": "www.tsmc.com", "fetched": "2020-01-01"}}}))
    calls = []
    s = lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher(calls))
    assert calls == [] and s["done"] is True and s["next_due"] is None


def test_run_never_raises_on_broken_fetcher(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x",
                    "website": "www.tsmc.com"}])

    def boom(w, h):
        raise RuntimeError("壞掉")
    s = lg.run(fetcher=boom)
    assert s["attempted"] == 0 and s["done"] is False


def test_run_time_budget_stops_early(sandbox, monkeypatch):
    _seed_company([{"code": f"{1000 + i}", "name": "x", "market": "TWSE", "industry": "x",
                    "website": f"www.t{i}.com"} for i in range(20)])
    monkeypatch.setattr(config, "LOGO_WORKERS", 1)
    s = lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher([]), time_budget=0)
    assert s["deadline_hit"] is True and s["attempted"] < 20 and s["pending"] > 0


# ------------------------------------------------------------------ 上櫃／興櫃網址

def test_parse_company_websites_chinese_and_english_keys():
    zh = [{"出表日期": "1150925", "公司代號": "6488", "公司簡稱": "環球晶", "網址": "www.sas-globalwafers.com"},
          {"出表日期": "1150925", "公司代號": "8069", "網址": "無"}]
    en = [{"SecuritiesCompanyCode": "3105", "CompanyName": "穩懋", "WebAddress": "https://www.winfoundry.com"}]
    a = lg.parse_company_websites(zh, "TPEX", "openapi.twse.com.tw", "2026-09-26")
    b = lg.parse_company_websites(en, "TPEX", "www.tpex.org.tw", "2026-09-26")
    assert a.to_dict("records") == [{"code": "6488", "website": "www.sas-globalwafers.com", "market": "TPEX",
                                     "src": "openapi.twse.com.tw", "asof": "2026-09-25"}]
    assert b.iloc[0]["code"] == "3105" and b.iloc[0]["asof"] == "2026-09-26"
    # 欄位改名：名字裡有「網址／web」的欄位也認得
    c = lg.parse_company_websites([{"公司代號": "5347", "公司網址": "www.vis.com.tw"}], "TPEX", "x", "d")
    assert c.iloc[0]["website"] == "www.vis.com.tw"


def test_company_websites_failure_logs_head_and_returns_empty(monkeypatch, caplog):
    monkeypatch.setattr(http, "get", lambda url, **kw: {"message": "欄位整個改掉了" * 50})
    with caplog.at_level("WARNING"):
        df = lg.company_websites()
    assert df.empty
    assert "回應前 200 字" in caplog.text and "欄位整個改掉了" in caplog.text


def test_company_websites_first_candidate_wins(monkeypatch):
    urls = []

    def fake(url, **kw):
        urls.append(url)
        if url.endswith("/opendata/t187ap03_O"):
            return [{"公司代號": "6488", "網址": "www.sas-globalwafers.com"}]
        return None
    monkeypatch.setattr(http, "get", fake)
    df = lg.company_websites()
    assert df["code"].tolist() == ["6488"]
    assert not any("tpex.org.tw" in u for u in urls)          # 上櫃拿到了就不再打櫃買（常擋雲端 IP）
    assert any(u.endswith("t187ap03_R") for u in urls)          # 興櫃照樣試


def test_websites_merges_company_website_table_without_touching_company_info(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x", "website": "www.tsmc.com"},
                   {"code": "6488", "name": "環球晶", "market": "TPEX", "industry": "x", "website": None}])
    store.append("company_website", pd.DataFrame([
        {"code": "6488", "website": "www.sas-globalwafers.com", "market": "TPEX", "src": "t", "asof": "2026-09-25"},
        {"code": "2330", "website": "www.other.com", "market": "TWSE", "src": "t", "asof": "2026-09-25"}]))
    w = lg.websites().set_index("code")["website"].to_dict()
    assert w == {"2330": "www.tsmc.com", "6488": "www.sas-globalwafers.com"}   # 上市以 company_info 為準
    info = store.read("company_info").set_index("code")
    assert info.loc["6488", "name"] == "環球晶"                                 # company_info 沒被蓋掉


# ------------------------------------------------------------------ build_payload 輸出

def test_export_logos_empty_outputs_empty_object(sandbox):
    from pipeline import build_payload
    assert build_payload.export_logos() == {}
    assert json.loads((config.SITE_DATA / "logos.json").read_text()) == {}
    assert not (config.SITE_DATA / "logos").exists()


def test_export_logos_copies_usable_only_and_clears_stale(sandbox):
    from pipeline import build_payload
    d = config.DATA / "logos"
    d.mkdir(parents=True)
    for c in ("2330", "2317"):
        (d / f"{c}.png").write_bytes(_png((64, 64)))
    (d / "_index.json").write_text(json.dumps({"version": 1, "items": {
        "2330": {"status": "ok", "domain": "www.tsmc.com", "sha1": "a", "fetched": "2026-09-26"},
        "2317": {"status": "generic", "domain": "www.foxconn.com", "sha1": "b", "fetched": "2026-09-26"},
        "1101": {"status": "ok", "domain": "www.taiwancement.com", "sha1": "c", "fetched": "2026-09-26"},  # 檔案不在
    }}))
    stale = config.SITE_DATA / "logos"
    stale.mkdir(parents=True)
    (stale / "9999.png").write_bytes(b"old")
    got = build_payload.export_logos()
    assert got == {"2330": "data/logos/2330.png"}
    assert (config.SITE_DATA / "logos" / "2330.png").read_bytes() == (d / "2330.png").read_bytes()
    assert not (config.SITE_DATA / "logos" / "9999.png").exists()             # 舊輸出清掉
    assert json.loads((config.SITE_DATA / "logos.json").read_text()) == got


def test_export_logos_disabled_switch(sandbox, monkeypatch):
    from pipeline import build_payload
    d = config.DATA / "logos"
    d.mkdir(parents=True)
    (d / "2330.png").write_bytes(_png((64, 64)))
    (d / "_index.json").write_text(json.dumps({"items": {"2330": {"status": "ok", "domain": "a.com", "sha1": "a"}}}))
    monkeypatch.setattr(config, "LOGOS_ENABLED", False)
    assert build_payload.export_logos() == {}
    assert not (config.SITE_DATA / "logos").exists()


# ------------------------------------------------------------------ 回補串接

def test_backfill_logos_only_mode_skips_finmind(sandbox, monkeypatch):
    from pipeline import run_backfill
    monkeypatch.setattr(run_backfill, "PROGRESS", config.STATE / "backfill_progress.json")
    seen = {}
    monkeypatch.setattr(lg, "company_websites", lambda: pd.DataFrame([
        {"code": "6488", "website": "www.sas-globalwafers.com", "market": "TPEX", "src": "t", "asof": "2026-09-25"}]))

    def fake_run(limit=None, **kw):
        seen["run"] = kw
        return {}
    monkeypatch.setattr(lg, "run", fake_run)

    def no_finmind(prog):
        raise AssertionError("logos 模式不該碰 FinMind")
    monkeypatch.setattr(run_backfill, "finmind_reachable", no_finmind)
    monkeypatch.setattr(sys, "argv", ["run_backfill", "--datasets", "logos"])
    assert run_backfill.main() == 0
    assert "run" in seen
    assert store.read("company_website")["code"].tolist() == ["6488"]
    prog = json.loads((config.STATE / "backfill_progress.json").read_text())
    assert prog["complete"]["company_website"]["rows"] == 1

    # 30 天內不重抓網址清單
    def no_refetch():
        raise AssertionError("30 天內不該重抓網址清單")
    monkeypatch.setattr(lg, "company_websites", no_refetch)
    run_backfill.backfill_logos(run_backfill._progress())
