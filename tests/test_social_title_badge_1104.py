"""2026-11-04 CEO 追加兩件：
1. 新聞短標題被數字裡的逗號截斷（11-03 盤後實發「Marvell 擬以 1：Marvell 擬以 1,150 億美元」）→ 數字中間的逗號、冒號不是斷句。
2. 社群圖卡標題列左上角還是比比頭像（icon-192.png）→ 11-02 Andy「比比以後不會出現在貼文上」：改純文字字標「哩股哩股」。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import social_live_news as ln  # noqa: E402
import social_premarket as sp  # noqa: E402
import social_theme as TH  # noqa: E402

MARVELL = "Marvell 擬以 1,150 億美元收購 Lumentum，調研：雷射光源供應成競爭關鍵"


def test_數字中的逗號冒號不斷句():
    for f in (lambda t: sp._clause(t, 30), lambda t: ln.short_title(t, 30)):
        assert f("台積電10月營收3,000億元，年增30%") == "台積電10月營收3,000億元"
        assert f("非理性賣壓釋放！台股終場跌 1612.60 點") == "非理性賣壓釋放"
        assert f("美股 09:30 開盤前，期指走高") in ("美股 09:30 開盤前", "")      # 時間的冒號不斷
        out = f(MARVELL)
        assert not out.endswith(("1", "擬以")), out                           # 11-03 實例：不准切在「1,150」的逗號
    assert sp._clause("外資大賣台積電：今天賣超", 30) == "外資大賣台積電"                          # 一般冒號照斷


def test_Marvell那則不會再出現半個數字():
    x = sp.news_line({"title": MARVELL, "summary": ""}, 30, 40, short=ln.short_title(MARVELL, 30))
    assert "擬以 1：" not in x and not x.startswith("Marvell 擬以 1")


def test_標題列不放比比頭像():
    h = TH.header_html("close", "外資個股買賣超排名", "11/04")
    assert "<img" not in h and "data:image" not in h and TH.BRAND_TEXT in h and "data-box=logo" in h
    assert "<img" not in TH.header_html("premarket", "t", "d", logo="")
    assert TH.BRAND_TEXT not in TH.header_html("premarket", "t", "d", logo="")
    import base64
    svg = base64.b64decode(TH.logo_uri().split(",", 1)[1]).decode()      # 舊範例腳本用的方形字標：文字，不是比比
    assert TH.logo_uri().startswith("data:image/svg+xml") and "哩股" in svg and "<image" not in svg


def test_社群圖卡程式不引用比比與吉祥物圖檔():
    for f in ("social_theme.py", "social_snap.py", "social_premarket.py", "social_native.py", "social_numcard.py"):
        src = (ROOT / "scripts" / f).read_text(encoding="utf-8")
        assert '"icon-192.png"' not in src and "brand/bibi" not in src and "bibi_library" not in src, f


def test_開頭專欄名與日期欄頭不當短標題():
    assert sp.strip_column("《價值型投資 最新產業研究報告》臻鼎-KY 高階板放量") == "臻鼎-KY 高階板放量"
    assert sp.strip_column("11月3日盤前／油價回落降低通膨壓力") == "油價回落降低通膨壓力"
    assert sp.strip_column("【快訊】台積電漲停") == "台積電漲停"
    assert not ln.short_title("《價值型投資 最新產業研究報告》臻鼎-KY (4958-TW) 人工智慧高階板加速放量，八億美元籌資擴大產能", 30).startswith("《")


def test_數字被吃掉的年字不留在標籤():
    x = sp.news_line({"title": "AI 需求推升！華邦電 2026 年第三季毛利率飆至 70.6%，單季 EPS 7.58 元", "summary": ""}, 30, 40,
                     short=ln.short_title("AI 需求推升！華邦電 2026 年第三季毛利率飆至 70.6%，單季 EPS 7.58 元", 30))
    assert "：年第" not in x and "、年第" not in x
