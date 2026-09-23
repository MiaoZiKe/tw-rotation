"""交付清單的轉換（`docs/delivery_log.md` → `site/data/delivery.json`）。

這份清單存在的理由是「Andy 自己驗得了我有沒有如實交付」，所以**解析錯一個欄位
比整條管線掛掉更危險** —— 畫面上會長出一句他沒講過的話，而他無從分辨。
這裡守住三件事：原話逐字沒被動過、一行多欄切得對、沒有畫面的項目不會生出死連結。
"""
from pathlib import Path

from pipeline import delivery_log

ROOT = Path(__file__).resolve().parents[1]


def _data():
    return delivery_log.build(ROOT)


def test_原話逐字照抄_沒有被正規化():
    items = {i["n"]: i for i in _data()["items"]}
    # 他打的是半形問號、沒有空格，解析不准「順手修好」
    assert items[15]["quote"] == "另外圖三四這個真的是即時更新嗎?多久更新一次，我看他沒有再移動"
    assert items[1]["quote"] == "連接器少了3D圖 請補上"


def test_一行三欄切得開():
    it = {i["n"]: i for i in _data()["items"]}[1]
    assert it["state"] == "done"
    assert it["ver"] == "103"
    assert it["go"] == "#industry/ai_server/dg/ai_interconnect"


def test_部署編號對得到日期時間():
    """畫面上要寫「第 N 次部署 · 日期 時間」，那是跟右上角版號徽章對照的唯一依據。"""
    d = _data()
    assert {x["ver"]: x["at"] for x in d["deploys"]}["104"] == "2026-09-23 17:17"
    assert {i["n"]: i for i in d["items"]}[16]["at"] == "2026-09-23 17:17"


def test_沒有畫面的項目不給連結():
    it = {i["n"]: i for i in _data()["items"]}[31]
    assert it["go"] == ""                       # 點了沒反應的鈕比沒有鈕更糟
    assert it["go_text"] == "（流程，不在畫面上）"


def test_續行併回同一個欄位():
    it = {i["n"]: i for i in _data()["items"]}[15]
    assert it["what"].endswith("不准為了好看放大位移")
    assert "贏大盤 2%" in it["what"]


# 筆數原本寫死 34，結果每補一批需求就紅一次（2026-09-23 補到 43 時把
# daily.yml 的「跑指標庫測試」擋掉了 —— 那一步排在抓取前面，紅了整條每日
# 管線就停擺）。這個測試真正要守的是「三個數字對得起來、而且清單不會變短」，
# 不是「剛好幾筆」。所以改成：三邊一致 ＋ 不得少於下面這個地板。
# 補了新需求就把地板往上調，永遠只准往上。
_FLOOR = 43


def test_狀態只有五種_而且沒有筆數掉了():
    d = _data()
    assert d["meta"]["total"] == len(d["items"]) >= _FLOOR
    assert set(i["state"] for i in d["items"]) <= set(delivery_log.STATES)
    assert sum(d["meta"]["counts"].values()) == d["meta"]["total"]


def test_檔案不在時回空的_不要讓管線死掉(tmp_path):
    assert delivery_log.build(tmp_path) == {}
