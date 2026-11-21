"""scripts/social_topics.py 的測試：全部用小型假資料，不讀真實資料湖。"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import social_topics as st  # noqa: E402

T = date(2026, 10, 11)


def _news(rows):
    base = {"source": "cnyes", "published_at": "2026-10-11T10:00:00+08:00", "summary": "全文不該出現", "codes": "", "keywords": ""}
    return pd.DataFrame([{**base, **r} for r in rows])


STRUCT = {
    "groups": {"foundry_g": {"name": "晶圓代工族群", "chain": "semiconductor", "codes": ["2330"]}},
    "supply": {"segments": [{"id": "foundry", "name": "晶圓代工", "chain": "semiconductor"}],
               "companies": [{"ticker": "2330", "name": "台積電", "segment": "foundry"}]},
    "macro_cfg": {"fomc": {"meetings": [{"start": "2026-10-13", "end": "2026-10-14", "sep": False, "minutes": "2026-11-04"}]},
                  "releases": {"cpi": {"dates": [{"date": "2026-10-09", "ref": "9月"}, {"date": "2026-10-20", "ref": "10月"}]}}},
}


def test_dedupe_by_similar_title_and_same_codes():
    items = [
        {"title": "台積電法說會登場 市場關注先進製程", "source": "a", "url": "u1", "codes": "2330", "category": "科技"},
        {"title": "台積電法說會登場，市場關注先進製程！", "source": "b", "url": "u2", "codes": "", "category": "科技"},
        {"title": "完全不同的新聞標題甲乙丙", "source": "c", "url": "u3", "codes": "2330", "category": "科技"},
        {"title": "另一個毫不相干的題目丁戊己庚", "source": "d", "url": "u4", "codes": "2454", "category": "科技"},
    ]
    out = st.dedupe(items)
    assert [x["source"] for x in out] == ["a", "d"]       # b 標題相似、c 同 codes 都併入 a
    assert len(out[0]["also"]) == 2


def test_pick_news_window_and_category():
    df = _news([
        {"title": "美國通膨降溫帶動債市", "category": "總經", "date": "2026-10-11", "url": "u1"},
        {"title": "日本央行調整殖利率政策", "category": "總經", "date": "2026-10-10", "url": "u2"},
        {"title": "歐元區景氣指標回升", "category": "總經", "date": "2026-10-08", "url": "u3"},
        {"title": "今天科技", "category": "科技", "date": "2026-10-11", "url": "u4"},
    ])
    got = st.pick_news(df, "總經", T, 8)
    assert [x["title"] for x in got] == ["美國通膨降溫帶動債市", "日本央行調整殖利率政策"]
    assert len(st.pick_news(df, "總經", T, 1)) == 1


def test_company_match_and_extension_topics():
    idx = st.build_company_index(STRUCT)
    assert st.find_companies("台積電擴產", "", idx) == ["2330"]
    assert st.find_companies("無關", "2330,US-NVDA", idx) == ["2330"]
    ext = st.extension_topics({"title": "台積電擴產", "codes": ""}, idx, "B")
    assert "晶圓代工族群" in ext["groups"] and 3 <= len(ext["topics"]) <= 5
    none = st.extension_topics({"title": "與台股無關", "codes": ""}, idx, "A")
    assert none["groups"] == [] and len(none["topics"]) == 3


def test_stoplist_prevents_generic_name_match():
    s = {"groups": {}, "supply": {"segments": [], "companies": [{"ticker": "5347", "name": "世界", "segment": "x"}]}}
    idx = st.build_company_index(s)
    assert st.find_companies("世界各國央行", "", idx) == []


def test_macro_schedule_window():
    cal = pd.DataFrame([{"date": "2026-10-09", "release": "cpi", "release_id": 10, "fetched": "2026-10-11"}])
    ev = st.macro_schedule(STRUCT, cal, T)
    kinds = {(e["kind"], e["date_et"]): e["phase"] for e in ev}
    assert kinds[("cpi", "2026-10-09")] == "已過公布日"
    assert ("fomc", "2026-10-14") in kinds and kinds[("fomc", "2026-10-14")] == "未來"
    assert ("cpi", "2026-10-20") not in kinds        # FRED 有資料時 YAML 退回值不採用；且超過 7 天


def test_lectures():
    mat = pd.DataFrame([
        {"code": "2330", "name": "台積電", "subject": "公司召開法人說明會", "occurred": "2026-10-15"},
        {"code": "1101", "name": "台泥", "subject": "法人說明會", "occurred": "2026-12-01"},
        {"code": "2317", "name": "鴻海", "subject": "更正法說會日期", "occurred": "2026-10-13"},
        {"code": "2454", "name": "聯發科", "subject": "董事會決議", "occurred": "2026-10-13"},
    ])
    got = st.lectures(mat, T)
    assert [x["code"] for x in got] == ["2330"]


def test_build_warning_and_no_fulltext(tmp_path):
    df = _news([{"title": "科技新聞", "category": "科技", "date": "2026-10-07", "url": "u1"}])
    r = st.build({"news": df, "material_news": pd.DataFrame(), "macro_calendar": pd.DataFrame(),
                  "company_info": pd.DataFrame()}, STRUCT, T, 8)
    assert r["data_date"] == "2026-10-07" and "落後" in r["warning"]
    fresh = _news([{"title": "科技新聞", "category": "科技", "date": "2026-10-11", "url": "u1"}])
    r2 = st.build({"news": fresh}, STRUCT, T, 8)
    assert r2["warning"] == ""
    assert "全文不該出現" not in json.dumps(r2, ensure_ascii=False)
    assert all(n["confidence"] == "待查證" and n["key_point"] == "" for n in r2["track_b"]["news"])
    md, js = st.write_outputs(r2, tmp_path)
    assert md.name == "2026-10-11.md" and js.exists()
    assert "待查證" in md.read_text(encoding="utf-8")
    assert "全文不該出現" not in md.read_text(encoding="utf-8")


def test_empty_news_does_not_crash():
    r = st.build({"news": pd.DataFrame()}, STRUCT, T, 8)
    assert r["warning"] and r["track_a"]["news"] == []
