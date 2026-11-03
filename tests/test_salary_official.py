"""官方非主管薪資抓取：端點用 swagger 摘要找、欄位用關鍵字比對、仟元換萬元。"""
from pipeline.sources import salary_official as so


def test_find_paths_by_summary():
    sw = {"paths": {
        "/opendata/t187ap46_L_5": {"get": {"summary": "上市公司企業ESG資訊揭露彙總資料-人力發展"}},
        "/opendata/t187ap46_O_5": {"get": {"summary": "上櫃公司企業ESG資訊揭露彙總資料-人力發展"}},
        "/opendata/t187ap46_L_1": {"get": {"summary": "上市公司企業ESG資訊揭露彙總資料-溫室氣體排放"}},
    }}
    assert so.find_paths(sw) == [("/opendata/t187ap46_L_5", "TWSE"), ("/opendata/t187ap46_O_5", "TPEX")]


def test_parse_rows_units_and_year():
    rows = [{"報告年度": "114", "公司代號": "2330", "公司名稱": "台積電",
             "非擔任主管職務之全時員工薪資平均數(仟元/人)": "4072",
             "非擔任主管之全時員工薪資中位數(仟元/人)": "3162",
             "非擔任主管職務之全時員工薪資中位數與前一年度之變動百分比": "19.55"},
            {"報告年度": "114", "公司代號": "9999", "公司名稱": "沒薪資欄"}]
    df = so.parse_rows(rows, "TWSE")
    assert len(df) == 1
    r = df.iloc[0]
    assert r.year == 2025 and r.code == "2330"
    assert r.avg_wan == 407.2 and r.median_wan == 316.2
    assert r.yoy_median_pct == 19.55
