import json

from pipeline import postmarket_news as po


def _day(date="2026-10-27", n=5):
    return {"date": date, "items": [{"cat": "總經", "title": f"盤後{i}", "url": "https://x.example/a", "source": "鉅亨", "time": ""} for i in range(n)]}


def test_落點是盤後檔而不是盤前檔():
    assert po.DEFAULT_PATH.name == "postmarket.json"


def test_同日覆蓋_新到舊(tmp_path):
    p = tmp_path / "po.json"
    assert po.add_day(_day("2026-10-26"), p, today="2026-10-26")
    assert po.add_day(_day("2026-10-27"), p, today="2026-10-27")
    assert po.add_day(_day("2026-10-27", n=3), p, today="2026-10-27")
    j = json.loads(p.read_text(encoding="utf-8"))
    assert [d["date"] for d in j["days"]] == ["2026-10-27", "2026-10-26"]
    assert len(j["days"][0]["items"]) == 3
    assert j["updated"] == "2026-10-27"


def test_壞輸入不寫檔(tmp_path):
    p = tmp_path / "po.json"
    assert not po.add_day({"date": "10/27", "items": [{"cat": "總經", "title": "x"}]}, p)
    assert not po.add_day({"date": "2026-10-27", "items": [{"cat": "亂寫", "title": "x"}]}, p)
    assert not p.exists()


def test_網址只收http_且只留KEEP天(tmp_path):
    c = po.clean_day({"date": "2026-10-27", "items": [{"cat": "科技", "title": "t", "url": "javascript:alert(1)"}]})
    assert c["items"][0]["url"] == ""
    p = tmp_path / "po.json"
    import datetime as dt
    d0 = dt.date(2026, 1, 1)
    for i in range(po.KEEP + 5):
        assert po.add_day(_day((d0 + dt.timedelta(days=i)).isoformat()), p)
    assert len(json.loads(p.read_text(encoding="utf-8"))["days"]) == po.KEEP


def test_站上附的空檔格式正確():
    j = json.loads(po.DEFAULT_PATH.read_text(encoding="utf-8"))
    assert isinstance(j["days"], list)
