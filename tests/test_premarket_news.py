import json

from pipeline import premarket_news as pm


def _day(date="2026-10-27", n=5):
    return {"date": date, "items": [{"cat": "科技", "title": f"標題{i}", "url": "https://x.example/a", "source": "鉅亨", "time": ""} for i in range(n)]}


def test_add_and_overwrite_same_day(tmp_path):
    p = tmp_path / "pm.json"
    assert pm.add_day(_day("2026-10-26"), p, today="2026-10-26")
    assert pm.add_day(_day("2026-10-27"), p, today="2026-10-27")
    assert pm.add_day(_day("2026-10-27", n=3), p, today="2026-10-27")   # 同日重跑＝覆蓋
    j = json.loads(p.read_text(encoding="utf-8"))
    assert [d["date"] for d in j["days"]] == ["2026-10-27", "2026-10-26"]
    assert len(j["days"][0]["items"]) == 3


def test_reject_bad_input(tmp_path):
    p = tmp_path / "pm.json"
    assert not pm.add_day({"date": "10/27", "items": [{"cat": "科技", "title": "x"}]}, p)
    assert not pm.add_day({"date": "2026-10-27", "items": [{"cat": "亂寫", "title": "x"}]}, p)
    assert not p.exists()


def test_url_sanitized_and_keep(tmp_path):
    d = clean = pm.clean_day({"date": "2026-10-27", "items": [{"cat": "總經", "title": "t", "url": "javascript:alert(1)"}]})
    assert clean["items"][0]["url"] == ""
    p = tmp_path / "pm.json"
    import datetime as dt
    base = dt.date(2026, 1, 1)
    for i in range(pm.KEEP + 5):
        pm.add_day(_day((base + dt.timedelta(days=i)).isoformat()), p)
    assert len(json.loads(p.read_text(encoding="utf-8"))["days"]) == pm.KEEP


def test_簡短敘述_解實體與換行():
    from pipeline import premarket_news as pn
    d = pn.clean_day({"date": "2026-10-27", "items": [{"cat": "科技", "title": "T", "desc": "第一句&#10;第二句 [&#8230;]"}]})
    assert d["items"][0]["desc"] == "第一句；第二句"
