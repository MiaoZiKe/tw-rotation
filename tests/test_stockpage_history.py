"""③ 歷史無限回溯的分頁切法（`stockpage.history_chunks`）。

這幾條擋的是「前端拖到底停不下來」與「接縫接錯」兩種錯：
p0 一定是最新的一段、最舊那一段的 prev 一定是 None、每一根都只出現一次、
而且**順序不能被打亂**（前端是直接把 bars 接到現有 K 棒前面的，順序錯就是一張亂圖）。
"""
from pipeline.compute import stockpage


def _bars(n, start=1):
    return [[f"2020-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", 10.0 + i, 11.0 + i, 9.0 + i, 10.5 + i, 100 * i]
            for i in range(start, start + n)]


def test_空的歷史回空清單():
    assert stockpage.history_chunks([]) == []


def test_不滿一段就只有一段_而且是最早的一段():
    ch = stockpage.history_chunks(_bars(5), chunk=10)
    assert len(ch) == 1
    assert ch[0]["page"] == 0
    assert ch[0]["prev"] is None          # 前端看到 None 才會停下來
    assert len(ch[0]["bars"]) == 5


def test_p0是最新的一段_往下越來越舊():
    bars = _bars(25)
    ch = stockpage.history_chunks(bars, chunk=10)
    assert [c["page"] for c in ch] == [0, 1, 2]
    assert [c["prev"] for c in ch] == ["p1", "p2", None]
    # p0 的最後一根＝整段歷史的最後一根（也就是最接近個股頁那一段的那一根）
    assert ch[0]["bars"][-1] == bars[-1]
    assert ch[-1]["bars"][0] == bars[0]
    # 每一段的 from/to 要跟自己的第一根與最後一根對得起來
    for c in ch:
        assert c["from"] == c["bars"][0][0]
        assert c["to"] == c["bars"][-1][0]


def test_每一根只出現一次而且順序不變():
    bars = _bars(37)
    ch = stockpage.history_chunks(bars, chunk=10)
    back = []
    for c in reversed(ch):                 # 由最舊的一段往回接，就是前端接的順序
        back.extend(c["bars"])
    assert back == bars


def test_剛好整除時不會多出一段空的():
    ch = stockpage.history_chunks(_bars(20), chunk=10)
    assert len(ch) == 2
    assert all(len(c["bars"]) == 10 for c in ch)
