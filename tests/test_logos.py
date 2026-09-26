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
        # 第 4 欄：轉址測試用（allow_redirects=False 時 get_bytes 在這一欄放 Location 的下一跳）
        return (hit[0], hit[1], hit[2], hit[3] if len(hit) > 3 else url)
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
        # 失敗 10 天、而且是用目前這一版策略判的：先不試（舊策略判的另有「立刻重試」規則，見下面的測試）
        "3333": {"status": "none", "domain": "www.c3333.com", "fetched": "2026-09-16", "strategy": config.LOGO_STRATEGY},
        "4444": {"status": "none", "domain": "www.c4444.com", "fetched": "2026-08-01", "strategy": config.LOGO_STRATEGY},  # 失敗 56 天：再試
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


# ================================================================== 第二版取圖策略（2026-09-26）
# 第一輪 300 家：台積電、聯電、瑞昱、聯詠、廣達、緯穎被判「太小」（只有 16px favicon），
# 欣興、旺宏、南亞電路板被判「找不到」。下面每一個測試對應一種救回來的路。

X = "https://www.x.com.tw/"
S2 = config.LOGO_GOOGLE_S2.format(domain="www.x.com.tw")


def _tiny_ico():
    return _png((16, 16), fmt="ICO", sizes=[(16, 16)])


def _noise(size=(400, 300)) -> bytes:
    """隨機雜訊 ＝ 色彩極多的「照片」。"""
    import os
    from PIL import Image
    img = Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _svg(w=200, h=100) -> bytes:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
            f'<rect x="10" y="10" width="{w // 2}" height="{h // 2}" fill="#c33"/></svg>').encode()


def _alpha_rows(png: bytes):
    """每一列的最大不透明度：用來驗「上下補透明邊、沒有被拉伸」。"""
    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert("RGBA")
    a = img.getchannel("A")
    return [max(a.getpixel((x, y)) for x in range(img.width)) for y in range(img.height)]


def test_s2_url_asks_for_128():
    assert "sz=128" in config.LOGO_GOOGLE_S2


def test_multiple_icon_candidates_pick_largest_not_first(monkeypatch):
    """宣告跟實際不一樣時，照實際尺寸取最大：apple-touch 其實只有 50px，宣告 32 的那個其實是 120px。"""
    html = b'''<link rel="apple-touch-icon" href="/apple.png">
               <link rel="icon" sizes="16x16" href="/f16.png">
               <link rel="icon" sizes="32x32" href="/f32.png">'''
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "apple.png": (200, _png((50, 50)), "image/png"),
        X + "f16.png": (200, _png((16, 16)), "image/png"),
        X + "f32.png": (200, _png((120, 120)), "image/png"),
    }, calls))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["url"] == X + "f32.png" and got["orig"] == [120, 120]
    assert S2 not in calls                        # 官網已經有 ≥48px 的，不必問 Google


def test_early_stop_on_big_square_official_icon(monkeypatch):
    """找到 ≥64px 的正方形官方圖示就停，不再下載其他候選（對官網客氣一點）。"""
    html = b'<link rel="apple-touch-icon" sizes="180x180" href="/a.png"><link rel="icon" href="/f.ico">'
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"), X + "a.png": (200, _png(), "image/png"),
    }, calls))
    assert lg.fetch_logo("www.x.com.tw")["src"] == "site:apple-touch-icon"
    assert X + "f.ico" not in calls and X + "favicon.ico" not in calls


def test_scan_page_collects_all_icon_kinds():
    html = """<head>
      <link rel="icon" href="/f.ico">
      <link rel="icon" sizes="any" type="image/svg+xml" href="/i.svg">
      <link rel="mask-icon" href="/pin.svg" color="#c00">
      <link rel="apple-touch-icon" href="/apple.png">
      <link rel="manifest" href="/site.webmanifest">
      <meta property="og:image" content="/img/og-logo.png">
      <meta property="og:image:width" content="600"><meta property="og:image:height" content="300">
    </head>"""
    sc = lg.scan_page(html, X)
    kinds = {c["url"]: (c["kind"], c["px"], c["svg"]) for c in sc["icons"]}
    assert kinds[X + "f.ico"] == ("icon", 0, False)
    assert kinds[X + "i.svg"] == ("icon", 512, True)            # sizes="any" 的 SVG 當 512
    assert kinds[X + "pin.svg"] == ("mask-icon", 0, True)
    assert kinds[X + "apple.png"] == ("apple-touch-icon", 180, False)   # 沒寫 sizes 照慣例當 180
    assert sc["manifest"] == X + "site.webmanifest"
    assert sc["og"] == {"url": X + "img/og-logo.png", "w": 600, "h": 300}


def test_plan_candidates_order():
    sc = {"icons": [{"url": X + "f16.ico", "kind": "icon", "px": 16, "svg": False},
                    {"url": X + "pin.svg", "kind": "mask-icon", "px": 0, "svg": True},
                    {"url": X + "i.svg", "kind": "icon", "px": 512, "svg": True},
                    {"url": X + "a.png", "kind": "apple-touch-icon", "px": 180, "svg": False}],
          "imgs": [{"url": X + "logo.png", "kind": "header-img", "px": 0, "svg": False}],
          "og": {"url": X + "og-logo.png", "w": None, "h": None}}
    man = [{"url": X + "m512.png", "kind": "manifest", "px": 512, "svg": False}]
    kinds = [c["url"].rsplit("/", 1)[1] for c in lg.plan_candidates(sc, X, man)]
    assert kinds == ["m512.png", "a.png", "i.svg", "apple-touch-icon.png", "logo.png", "og-logo.png",
                     "f16.ico", "favicon.ico", "pin.svg"]


def test_manifest_icons_parse_largest_relative_and_skip_monochrome():
    raw = json.dumps({"icons": [
        {"src": "icons/192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icons/512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icons/mono.png", "sizes": "1024x1024", "purpose": "monochrome"},
        {"src": "icons/48.png", "sizes": "48x48"},
        "垃圾",
    ]}).encode()
    got = lg.parse_manifest_icons(raw, "https://www.x.com.tw/static/manifest.json")
    assert [g["url"] for g in got] == ["https://www.x.com.tw/static/icons/512.png",
                                       "https://www.x.com.tw/static/icons/192.png"]
    assert all(g["kind"] == "manifest" for g in got)
    assert lg.parse_manifest_icons(b"{not json", X) == []
    assert lg.parse_manifest_icons(b'{"icons": "x"}', X) == []


def test_fetch_logo_uses_manifest_icon_when_only_16px_favicon(monkeypatch):
    html = b'<link rel="icon" href="/favicon.ico"><link rel="manifest" href="/manifest.json">'
    man = json.dumps({"icons": [{"src": "/m192.png", "sizes": "192x192"},
                                {"src": "/m512.png", "sizes": "512x512"}]}).encode()
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "favicon.ico": (200, _tiny_ico(), "image/x-icon"),
        X + "manifest.json": (200, man, "application/manifest+json"),
        X + "m192.png": (200, _png((192, 192)), "image/png"),
        X + "m512.png": (200, _png((512, 512)), "image/png"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "site:manifest" and got["url"] == X + "m512.png"


def test_manifest_blocked_by_robots_is_not_fetched(monkeypatch):
    html = b'<link rel="manifest" href="/private/manifest.json">'
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        X + "robots.txt": (200, b"User-agent: *\nDisallow: /private/\n", "text/plain"),
        X: (200, html, "text/html"),
    }, calls))
    lg.fetch_logo("www.x.com.tw")
    assert X + "private/manifest.json" not in calls


@pytest.mark.parametrize("og,ok", [
    ({"url": X + "images/logo_share.jpg", "w": 1200, "h": 200}, True),   # 路徑含 logo：收（下載後仍擋照片）
    ({"url": X + "share.jpg", "w": 1200, "h": 630}, True),               # 1.9:1 在 1:1～4:1 內：下載後再判
    ({"url": X + "share.jpg", "w": 1200, "h": 200}, False),              # 6:1 橫幅：連下載都省了
    ({"url": X + "share.jpg", "w": 300, "h": 600}, False),               # 直式：不像 Logo
    ({"url": X + "share.jpg", "w": None, "h": None}, True),              # 沒宣告：下載後再判
    (None, False),
])
def test_og_candidate_judgement(og, ok):
    got = lg.og_candidate(og)
    assert (got is not None) == ok
    if got:
        assert got["kind"] == "og-image" and got["logo_named"] == ("logo" in og["url"])


def test_og_image_photo_is_rejected(monkeypatch):
    """og:image 是活動照片（色彩極多）：不當 Logo；只剩 16px favicon 與 16px s2 → 太小。"""
    html = b'<meta property="og:image" content="/share.png"><link rel="icon" href="/favicon.ico">'
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "share.png": (200, _noise(), "image/png"),
        X + "favicon.ico": (200, _tiny_ico(), "image/x-icon"),
        S2: (200, _png((16, 16)), "image/png"),
    }))
    assert lg.fetch_logo("www.x.com.tw")["status"] == "too_small"


def test_og_image_without_logo_name_checks_real_aspect(monkeypatch):
    """沒宣告寬高、路徑也沒有 logo：下載後長寬比 4.5:1 → 不收。"""
    html = b'<meta property="og:image" content="/banner.png">'
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "banner.png": (200, _png((450, 100)), "image/png"),
    }))
    assert lg.fetch_logo("www.x.com.tw")["status"] == "none"


def test_og_image_flat_logo_is_used_when_nothing_else(monkeypatch):
    html = b'<meta property="og:image" content="/assets/og.png"><link rel="icon" href="/favicon.ico">'
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "assets/og.png": (200, _png((400, 200), bg=(255, 255, 255, 255)), "image/png"),
        X + "favicon.ico": (200, _tiny_ico(), "image/x-icon"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "site:og-image" and got["orig"] == [400, 200]


def test_scan_page_header_logo_img_rules():
    html = """<body>
      <header class="site-header"><a class="navbar-brand" href="/">
        <img src="/img/brand.png" srcset="/img/brand.png 1x, /img/brand@2x.png 2x" alt="某某科技"></a></header>
      <div class="banner"><img src="/img/hero.jpg" alt="新廠房"></div>
      <section class="partners"><img src="/img/partner-logo-intel.png" alt="Intel logo"></section>
      <img src="/img/iso-logo.png">
      <footer><img src="/img/logo-footer-white.png" alt="logo"></footer>
      <div class="logo-wrap"><img src="/img/second.png"></div>
    </body>"""
    urls = [c["url"] for c in lg.scan_page(html, X)["imgs"]]
    assert urls[0] == X + "img/brand@2x.png"                  # 頁首＋navbar-brand，srcset 取最大
    assert X + "img/second.png" in urls                       # 包在 class 含 logo 的元素裡
    assert not any(k in u for u in urls for k in ("hero", "partner", "iso", "footer"))
    assert len(urls) <= 2


def test_scan_page_lazy_img_and_unclosed_tags():
    html = '<div id="header"><div><span><img class="logo lazy" data-src="/l.png" src="data:image/gif;base64,R0">'
    assert [c["url"] for c in lg.scan_page(html, X)["imgs"]] == [X + "l.png"]


def test_fetch_logo_header_img_rescues_16px_site_and_pads_not_crops(monkeypatch):
    """台積電那一型：只宣告 16px favicon，但頁首有 Logo 圖 → 用頁首圖，橫長的上下補透明邊。"""
    html = b'''<link rel="icon" href="/favicon.ico">
               <header><div class="logo"><a href="/"><img src="/images/logo.png" alt="X"></a></div></header>'''
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "favicon.ico": (200, _tiny_ico(), "image/x-icon"),
        X + "images/logo.png": (200, _png((300, 100), fg=(20, 60, 160, 255)), "image/png"),
        S2: (200, _png((16, 16)), "image/png"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "site:header-img" and got["orig"] == [300, 100]
    rows = _alpha_rows(got["png"])
    assert len(rows) == 64 and rows[0] == 0 and rows[-1] == 0 and max(rows[28:36]) > 0


def test_square_icon_beats_wide_wordmark():
    """「最大」看縮進方框後的有效尺寸：64px 正方形圖示 > 300×100 字標 > 32px 圖示 > …"""
    assert lg.effective_px(180, 180) == 64
    assert lg.effective_px(32, 32) == 32
    assert round(lg.effective_px(300, 100)) == 21
    sq = {"eff": lg.effective_px(64, 64), "kind": "icon", "orig": (64, 64)}
    wide = {"eff": lg.effective_px(1200, 400), "kind": "header-img", "orig": (1200, 400)}
    assert lg._score(sq) > lg._score(wide)
    big_og = {"eff": 64, "kind": "og-image", "orig": (1200, 1200)}
    assert lg._score(sq) > lg._score(big_og)                  # 一樣大時官方圖示優先


def test_normalize_pads_tall_and_rejects_too_wide():
    from PIL import Image
    png, orig = lg.normalize_image(_png((100, 300)))
    img = Image.open(io.BytesIO(png))
    assert img.size == (64, 64) and orig == (100, 300)
    assert img.getpixel((1, 32))[3] == 0 and img.getpixel((62, 32))[3] == 0   # 左右補透明邊
    with pytest.raises(lg.LogoReject) as e:
        lg.normalize_image(_png((600, 100)))                    # 6:1 橫條
    assert e.value.reason == "too_wide"


def test_is_photo():
    from PIL import Image
    for strict in (False, True):
        assert lg.is_photo(Image.open(io.BytesIO(_noise())), strict=strict)
        assert not lg.is_photo(Image.open(io.BytesIO(_png((300, 100)))), strict=strict)


def test_jpeg_noisy_logo_is_not_photo_in_lenient_mode():
    """色數很多（壓縮雜訊）但平塗底色仍佔大半：寬鬆模式（頁首圖）不算照片，嚴格模式（裸 og:image）算。

    對應實例：3289 宜特的 Logo 是 JPEG，5 bit 色數 1,566，但前 8 種顏色佔 42%。
    """
    import os
    from PIL import Image
    img = Image.new("RGB", (64, 64), (255, 255, 255))
    noise = Image.frombytes("RGB", (64, 26), os.urandom(64 * 26 * 3))   # 下方 40% 是雜訊
    img.paste(noise, (0, 38))
    assert not lg.is_photo(img)
    assert lg.is_photo(img, strict=True)


def test_s2_128_still_16px_is_too_small(monkeypatch):
    """Google 對只有小圖的網站就算要 128 也回 16px：照實際尺寸判太小，不收。"""
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, b'<link rel="icon" href="/favicon.ico">', "text/html"),
        X + "favicon.ico": (200, _tiny_ico(), "image/x-icon"),
        S2: (200, _png((16, 16)), "image/png"),
    }, calls))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "too_small"
    assert S2 in calls and "sz=128" in S2


def test_s2_used_when_site_best_is_small(monkeypatch):
    """官網最好的只有 32px，Google 有 128px → 取 Google 的（比較之後取大）。"""
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, b'<link rel="icon" href="/f32.png">', "text/html"),
        X + "f32.png": (200, _png((32, 32)), "image/png"),
        S2: (200, _png((128, 128)), "image/png"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "google_s2" and got["orig"] == [128, 128]


@pytest.mark.parametrize("a,b,same", [
    ("www.aoet.com.tw", "www.aoet.com", True),        # 同品牌換頂級網域
    ("www.x.com.tw", "x.com.tw", True),
    ("www.x.com.tw", "ir.x.com.tw", True),
    ("tw.msi.com", "www.msi.com", True),
    ("www.x.com.tw", "x.wixsite.com", False),         # 架站商
    ("www.gbm.com.tw", "www.hannstar.com", False),    # 別的品牌（集團母公司）
    ("www.avc.co", "avc.co", True),
    (None, "a.com", False),
])
def test_same_company(a, b, same):
    assert lg.same_company(a, b) == same


A = "https://www.acme.com.tw/"      # 轉址測試用品牌長一點（same_company 要求品牌段 ≥ 3 個字）


def test_homepage_redirect_same_company_followed_and_recorded(monkeypatch):
    """首頁 301 到同公司另一個網域：跟過去、讀新網域的 robots，並把新網域記在 site。"""
    Y = "https://www.acme.com/"
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        A: (301, b"", "text/html", Y),
        Y: (200, b'<link rel="apple-touch-icon" href="/a.png">', "text/html"),
        Y + "a.png": (200, _png(), "image/png"),
    }, calls))
    got = lg.fetch_logo("www.acme.com.tw")
    assert got["status"] == "ok" and got["url"] == Y + "a.png" and got["site"] == "www.acme.com"
    assert Y + "robots.txt" in calls


def test_homepage_redirect_to_other_company_not_followed(monkeypatch):
    calls = []
    park = "https://parked.example-host.com/"
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (302, b"", "text/html", park),
        "http://www.x.com.tw/": (302, b"", "text/html", park),
        "https://x.com.tw/": (302, b"", "text/html", park),
        S2: (200, _png((128, 128)), "image/png"),
    }, calls))
    got = lg.fetch_logo("www.x.com.tw")
    assert park not in calls and park + "robots.txt" not in calls
    assert got["src"] == "google_s2" and "site" not in got


def test_homepage_redirect_target_robots_respected(monkeypatch):
    Y = "https://www.acme.com/"
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        A: (301, b"", "text/html", Y),
        Y + "robots.txt": (200, b"User-agent: *\nDisallow: /\n", "text/plain"),
    }, calls))
    got = lg.fetch_logo("www.acme.com.tw")
    assert got["status"] == "robots" and Y not in calls
    assert not any("google.com/s2" in u for u in calls)


def test_redirect_loop_gives_up(monkeypatch):
    Y = "https://www.x.com.tw/a"
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (302, b"", "text/html", Y), Y: (302, b"", "text/html", X),
        "http://www.x.com.tw/": (302, b"", "text/html", Y),
        "https://x.com.tw/": (302, b"", "text/html", Y),
    }))
    assert lg.fetch_logo("www.x.com.tw")["status"] in ("none", "error")


def test_robots_detail_says_403_vs_disallow(monkeypatch):
    monkeypatch.setattr(http, "get_bytes", _web({X + "robots.txt": (403, b"", "text/html")}))
    assert "403" in lg.fetch_logo("www.x.com.tw")["detail"]


def test_homepage_404_tries_bare_domain(monkeypatch):
    """欣興那一型：申報 www.x.com.tw 但首頁 404 → 改試 https://x.com.tw/。"""
    B = "https://x.com.tw/"
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (404, b"not found", "text/html"),
        "http://www.x.com.tw/": (404, b"not found", "text/html"),
        B: (200, b'<link rel="apple-touch-icon" href="/a.png">', "text/html"),
        B + "a.png": (200, _png(), "image/png"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["url"] == B + "a.png" and got["site"] == "x.com.tw"


def test_homepage_404_on_bare_domain_tries_www(monkeypatch):
    W = "https://www.y.com.tw/"
    monkeypatch.setattr(http, "get_bytes", _web({
        W: (200, b'<link rel="apple-touch-icon" href="/a.png">', "text/html"),
        W + "a.png": (200, _png(), "image/png"),
    }))
    got = lg.fetch_logo("y.com.tw")
    assert got["status"] == "ok" and got["url"] == W + "a.png"


def test_homepage_candidates_www_toggle():
    assert lg.homepage_candidates("x.com.tw", "x.com.tw") == [
        "https://x.com.tw/", "http://x.com.tw/", "https://www.x.com.tw/"]
    assert lg.homepage_candidates("http://www.x.com", "www.x.com") == [
        "http://www.x.com/", "https://www.x.com/", "https://x.com/"]
    assert lg.homepage_candidates("ir.x.com.tw", "ir.x.com.tw") == [
        "https://ir.x.com.tw/", "http://ir.x.com.tw/"]              # 子網域不亂加 www


def test_homepage_403_does_not_hammer_alternatives(monkeypatch):
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({X: (403, b"denied", "text/html")}, calls))
    lg.fetch_logo("www.x.com.tw")
    assert "https://x.com.tw/" not in calls and "http://www.x.com.tw/" not in calls


svg_ok = pytest.mark.skipif(not lg.svg_supported(), reason="沒有 cairosvg／libcairo")


@svg_ok
def test_svg_header_logo_rendered_keeping_aspect(monkeypatch):
    html = b'<link rel="icon" href="/favicon.ico"><header><img class="logo" src="/logo.svg"></header>'
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"),
        X + "favicon.ico": (200, _tiny_ico(), "image/x-icon"),
        X + "logo.svg": (200, _svg(200, 100), "image/svg+xml"),
        S2: (200, _png((16, 16)), "image/png"),
    }))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and got["src"] == "site:header-img" and got["orig"] == [256, 128]
    rows = _alpha_rows(got["png"])
    assert rows[0] == 0 and rows[-1] == 0                       # 2:1 → 上下補邊，不拉伸


@svg_ok
def test_svg_too_big_or_broken_is_rejected(monkeypatch):
    monkeypatch.setattr(config, "LOGO_SVG_MAX_BYTES", 50)
    with pytest.raises(lg.LogoReject) as e:
        lg.normalize_image(_svg())
    assert e.value.reason == "bad_image"
    monkeypatch.setattr(config, "LOGO_SVG_MAX_BYTES", 500_000)
    with pytest.raises(lg.LogoReject):
        lg.normalize_image(b"<svg xmlns='http://www.w3.org/2000/svg'><rect")


def test_svg_skipped_without_cairosvg(monkeypatch):
    """沒有 cairosvg／libcairo 的環境：SVG 候選直接跳過（不下載），其他候選照常。"""
    monkeypatch.setattr(lg, "svg_supported", lambda: False)
    html = b'<link rel="icon" type="image/svg+xml" href="/i.svg"><link rel="apple-touch-icon" href="/a.png">'
    calls = []
    monkeypatch.setattr(http, "get_bytes", _web({
        X: (200, html, "text/html"), X + "a.png": (200, _png((120, 120)), "image/png"),
    }, calls))
    got = lg.fetch_logo("www.x.com.tw")
    assert got["status"] == "ok" and X + "i.svg" not in calls


def test_html_is_not_an_image():
    with pytest.raises(lg.LogoReject) as e:
        lg.normalize_image(b"<!doctype html><html><body>not an icon</body></html>")
    assert e.value.reason == "none"


def test_get_bytes_no_follow_returns_location(monkeypatch):
    """allow_redirects=False：3xx 的第 4 欄是 Location 解析後的下一跳，內容是空的。"""
    class R:
        status_code = 301
        headers = {"Location": "/tw/index.html", "Content-Type": "text/html"}
        url = "https://www.x.com.tw/"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def iter_content(self, n):
            return iter([b"moved"])

    class S:
        def get(self, url, **kw):
            assert kw["allow_redirects"] is False
            return R()
    got = http.get_bytes("https://www.x.com.tw/", sess=S(), allow_redirects=False)
    assert got == (301, b"", "text/html", "https://www.x.com.tw/tw/index.html")


# ------------------------------------------------------------------ 策略升級：太小／找不到的立刻重試

def test_retry_on_upgrade_rule():
    v = config.LOGO_STRATEGY
    assert lg.retry_on_upgrade({"status": "too_small"})
    assert lg.retry_on_upgrade({"status": "none", "strategy": v - 1})
    assert not lg.retry_on_upgrade({"status": "none", "strategy": v})
    for st in ("ok", "robots", "blank", "generic", "error", "removed"):
        assert not lg.retry_on_upgrade({"status": st})


def test_run_retries_old_failures_first_and_keeps_good_logos(sandbox):
    _seed_company([{"code": c, "name": c, "market": "TWSE", "industry": "x", "website": f"www.c{c}.com"}
                   for c in ("2330", "2303", "3037", "3227", "1101", "9999")])
    (config.DATA / "logos").mkdir(parents=True, exist_ok=True)
    good = lg.normalize_image(_png(fg=(1, 2, 3, 255)))[0]
    (config.DATA / "logos" / "1101.png").write_bytes(good)
    (config.DATA / "logos" / "_index.json").write_text(json.dumps({"version": 1, "items": {
        "2330": {"status": "too_small", "domain": "www.c2330.com", "fetched": "2026-09-25"},   # 昨天才判：照樣重試
        "2303": {"status": "too_small", "domain": "www.c2303.com", "fetched": "2026-09-25"},
        "3037": {"status": "none", "domain": "www.c3037.com", "fetched": "2026-09-25"},
        "3227": {"status": "robots", "domain": "www.c3227.com", "fetched": "2026-09-25"},      # 對方不准：不重試
        "1101": {"status": "ok", "domain": "www.c1101.com", "fetched": "2026-09-25", "sha1": lg.sha1(good)},
    }}))
    calls = []
    colors = {f"www.c{c}.com": lg.normalize_image(_png(fg=(i * 40, 90, 200 - i * 30, 255)))[0]
              for i, c in enumerate(("2330", "2303", "3037", "3227", "1101", "9999"))}
    lg.run(limit=3, today=date(2026, 9, 26), fetcher=_ok_fetcher(calls, colors))
    # 上限 3：三家重試的全部排在沒抓過的 9999 前面
    assert sorted(calls) == ["www.c2303.com", "www.c2330.com", "www.c3037.com"]
    idx = lg.read_index()["items"]
    assert idx["2330"]["status"] == "ok" and idx["2330"]["strategy"] == config.LOGO_STRATEGY
    assert (config.DATA / "logos" / "1101.png").read_bytes() == good      # 好圖沒被動
    assert idx["1101"] == {"status": "ok", "domain": "www.c1101.com", "fetched": "2026-09-25",
                           "sha1": lg.sha1(good)}
    # 下一輪：重試過的不再重試，只剩沒抓過的
    calls.clear()
    lg.run(today=date(2026, 9, 26), fetcher=_ok_fetcher(calls, colors))
    assert calls == ["www.c9999.com"]


def test_run_retry_that_fails_again_waits_30_days(sandbox):
    _seed_company([{"code": "2330", "name": "台積電", "market": "TWSE", "industry": "x", "website": "www.tsmc.com"}])
    (config.DATA / "logos").mkdir(parents=True, exist_ok=True)
    (config.DATA / "logos" / "_index.json").write_text(json.dumps({"version": 1, "items": {
        "2330": {"status": "too_small", "domain": "www.tsmc.com", "fetched": "2026-09-25"}}}))
    calls = []

    def still_small(website, host):
        calls.append(host)
        return {"status": "too_small", "domain": host, "detail": "16x16"}
    lg.run(today=date(2026, 9, 26), fetcher=still_small)
    lg.run(today=date(2026, 9, 27), fetcher=still_small)
    assert calls == ["www.tsmc.com"]                              # 第二輪不再重試（已是新策略的結論）
    assert lg.read_index()["items"]["2330"]["strategy"] == config.LOGO_STRATEGY


def test_run_records_redirect_site(sandbox):
    _seed_company([{"code": "3362", "name": "先進光", "market": "TWSE", "industry": "x", "website": "www.aoet.com.tw"}])

    def redirected(website, host):
        return {"status": "ok", "domain": host, "site": "www.aoet.com", "src": "site:icon",
                "url": "https://www.aoet.com/i.png", "png": lg.normalize_image(_png())[0], "orig": [180, 180]}
    lg.run(today=date(2026, 9, 26), fetcher=redirected)
    rec = lg.read_index()["items"]["3362"]
    assert rec["domain"] == "www.aoet.com.tw" and rec["site"] == "www.aoet.com"
