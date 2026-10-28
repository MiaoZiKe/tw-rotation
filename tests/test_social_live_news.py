"""盤中／盤後貼文的「📰 新聞焦點」段（scripts/social_live_news.py）：全部用假資料，不連網、不開瀏覽器。
2026-10-29 Andy：「盤前、盤中、盤後……除了基本的盤面解讀之外，還需要搭配當下的一些新聞消息，三到五個主題」。"""
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_live_news as LN
import social_snap as ss

TPE = ZoneInfo("Asia/Taipei")
NOW_ID = datetime(2026, 10, 29, 12, 0, tzinfo=TPE)
NOW_CL = datetime(2026, 10, 29, 16, 30, tzinfo=TPE)


def _news(rows):
    return pd.DataFrame([{"news_id": f"n{i}", "published_at": t, "source": s, "category": c, "title": ti, "keywords": k,
                          "url": f"https://x/{i}", "summary": sm} for i, (t, s, c, ti, k, sm) in enumerate(rows)])


ROWS = [
    # 窗外（盤中窗 07:30 起；這則 06:00）
    ("2026-10-29T06:00:00+08:00", "cnyes", "科技", "清晨舊聞：美光財報亮眼", "美光", "美光公布財報，營收創高。"),
    # 盤中窗內
    ("2026-10-29T08:10:00+08:00", "cnyes", "科技", "輝達 GB300 出貨放量！供應鏈營收衝高", "輝達,gb300", "輝達 GB300 本季出貨放量，台廠組裝與散熱同步受惠。"),
    ("2026-10-29T08:40:00+08:00", "technews", "科技", "GB300 放量 散熱廠接單滿", "gb300,散熱", "散熱模組廠第四季訂單滿載，產能利用率拉高。"),
    ("2026-10-29T09:05:00+08:00", "cnyes", "總經", "美債殖利率急跌，Fed 降息預期升溫", "美債,fed", "根據外媒報導，十年期美債殖利率跌破 4%，市場押注年底再降息。"),
    ("2026-10-29T09:30:00+08:00", "udn", "台股", "外資連三賣，台股成交量萎縮", "", "外資連續三日賣超台股，成交量降到兩個月低點。"),
    ("2026-10-29T10:00:00+08:00", "cnyes", "事件", "川普宣布對墨西哥加徵關稅，汽車零組件股承壓", "關稅", "美方宣布加徵 25% 關稅，北美車用零組件供應鏈受衝擊。"),
    # 相似標題（同一件事，不同媒體）→ 只留一則
    ("2026-10-29T10:05:00+08:00", "udn", "事件", "川普宣布對墨西哥加徵關稅 汽車零組件股承壓", "", "同一件事的另一家報導。"),
    # 業配／活動 → 排除
    ("2026-10-29T10:10:00+08:00", "cnyes", "台股", "野村亞洲雙ETF 11/3起限時募集", "etf", "募集訊息。"),
    ("2026-10-29T10:20:00+08:00", "cnyes", "台股", "AI 投資講座開放報名", "", "講座。"),
    # 盤前已用過（同網址）→ 排除
    ("2026-10-29T08:00:00+08:00", "cnyes", "科技", "台積電法說會前夕，外資喊買", "台積電", "台積電明日法說。"),
    # 盤後窗內（11:30 起）
    ("2026-10-29T13:40:00+08:00", "cnyes", "新聞", "聯發科強彈逾6%！創意、智原漲停", "聯發科,asic", "ASIC 族群今天強彈，聯發科收高逾 6%。"),
    ("2026-10-29T14:10:00+08:00", "technews", "科技", "穩懋 Q3 淨利 19.3 億元，EPS 4.55 元", "穩懋", "穩懋公布第三季財報，光通訊產品帶動獲利。"),
    ("2026-10-29T15:00:00+08:00", "udn", "台股", "個人放款餘額達22.9兆元創新高", "", "央行統計，全台個人放款餘額創史上新高。"),
]


def _used(tmp_path):
    p = tmp_path / "premarket.json"
    p.write_text(json.dumps({"days": [{"date": "2026-10-29", "items": [{"title": "台積電法說會前夕，外資喊買", "url": "https://x/9"}]}]},
                            ensure_ascii=False), "utf-8")
    return p


def test_window_by_kind():
    assert LN.window("intraday", NOW_ID) == (datetime(2026, 10, 29, 7, 30, tzinfo=TPE), NOW_ID)
    assert LN.window("close", NOW_CL)[0] == datetime(2026, 10, 29, 11, 30, tzinfo=TPE)


def test_pick_window_skip_dedupe_and_premarket_used(tmp_path):
    s, e = LN.window("intraday", NOW_ID)
    got = LN.pick(_news(ROWS), s, e, LN.premarket_used("2026-10-29", _used(tmp_path)))
    titles = [g["title"] for g in got]
    assert "清晨舊聞：美光財報亮眼" not in titles                                   # 窗外
    assert not any("募集" in t or "講座" in t for t in titles)                      # 業配／活動
    assert not any("台積電法說" in t for t in titles)                               # 盤前已用過
    assert sum("墨西哥加徵關稅" in t for t in titles) == 1                           # 相似標題只留一則
    assert not any("聯發科" in t for t in titles)                                   # 盤後的新聞不進盤中
    assert 3 <= len(got)


def test_focus_lines_format():
    s, e = LN.window("intraday", NOW_ID)
    L = LN.lines(LN.pick(_news(ROWS), s, e, []))
    assert L[0] == "📰 新聞焦點：" and 3 <= len(L) - 1 <= 5
    assert all(x.startswith("・") and "https://" not in x and "…" not in x for x in L[1:])
    assert "・美債殖利率急跌：十年期美債殖利率跌破 4%，市場押注年底再降息" in L                          # 摘要開頭「根據外媒報導」不當描述
    assert "・輝達 GB300 出貨放量：輝達 GB300 本季出貨放量，台廠組裝與散熱同步受惠" in L


def test_short_title_does_not_split_mixed_language_space():
    assert LN.short_title("招聘工程師使 OpenAI 採購 GoogleTPU 進入實質階段，OpenAI 與輝達關係恐受影響", 30) == ""
    assert LN.short_title("SK海力士財報出爐！第三季營益衝83.3兆韓元超預期", 30) == "SK海力士財報出爐"
    assert LN.strip_attr("AI 模型商申請 IPO，據媒體統計。後段") == "AI 模型商申請 IPO。後段"


TEXT = "\n".join(["盤中3分鐘", "盤面分析：", "・族群漲多跌少", "🎡 資金輪盤：", "・領先 半導體、PCB；", "・落後 航運、鋼鐵",
                  ss.HASHTAGS["intraday"], "👉 更多詳細資料可以點擊以下連結：", "https://liguligu-puipui.com/?u=th-id-20261029"])


def test_merge_inserts_before_hashtag_and_link_stays_last(tmp_path):
    r = LN.for_post("intraday", TEXT, NOW_ID, ss.HASHTAGS["intraday"], ss.THREADS_MAX, news=_news(ROWS), used_path=_used(tmp_path), log=lambda *a: None)
    L = r["text"].splitlines()
    i, h = L.index("📰 新聞焦點："), L.index(ss.HASHTAGS["intraday"])
    assert L.index("・落後 航運、鋼鐵") < i < h and all(x.startswith("・") for x in L[i + 1:h])     # 盤面解讀之後、hashtag 之前
    assert L[-1].startswith("https://") and r["text"].count("https://") == 1                   # 網址只在最底一行
    assert r["reply"] == "" and r["alert"] == "" and 3 <= r["n"] <= 5 and len(r["text"]) <= ss.THREADS_MAX


def test_merge_moves_to_reply_when_main_too_long(tmp_path):
    long_ = TEXT.replace("・族群漲多跌少", "・" + "族群漲多跌少，" * 48)
    assert len(long_) < ss.THREADS_MAX
    r = LN.for_post("intraday", long_, NOW_ID, ss.HASHTAGS["intraday"], ss.THREADS_MAX, news=_news(ROWS), used_path=_used(tmp_path), log=lambda *a: None)
    assert r["text"] == long_ and r["reply"].startswith("📰 新聞焦點：") and "https://" not in r["reply"] and "#台股" not in r["reply"]
    assert len(r["reply"]) <= ss.THREADS_MAX and r["n"] >= 3


def test_too_few_news_still_posts_with_alert(tmp_path):
    few = _news([r for r in ROWS if r[0] >= "2026-10-29T13"][:1])
    r = LN.for_post("close", TEXT.replace("intraday", "close"), NOW_CL, ss.HASHTAGS["close"], ss.THREADS_MAX, news=few, used_path=_used(tmp_path), log=lambda *a: None)
    assert r["n"] == 1 and "📰 新聞焦點：" in r["text"] and "只有 1 則" in r["alert"]
    none_ = LN.for_post("close", TEXT, NOW_CL, ss.HASHTAGS["close"], ss.THREADS_MAX, news=_news([]), used_path=_used(tmp_path), log=lambda *a: None)
    assert none_["text"] == TEXT and none_["n"] == 0 and "不放新聞那段" in none_["alert"]


def test_errors_never_block(tmp_path):
    r = LN.for_post("intraday", TEXT, NOW_ID, ss.HASHTAGS["intraday"], ss.THREADS_MAX, news="壞掉的資料", used_path=_used(tmp_path), log=lambda *a: None)
    assert r["text"] == TEXT and r["reply"] == "" and r["alert"]
    assert LN.for_post("credit", TEXT, NOW_ID, "#x", 480, news=_news(ROWS))["text"] == TEXT       # 融資融券篇不加


def test_empty_summary_uses_rest_of_title():
    L = LN.lines([{"title": "SK海力士財報出爐！第三季營益衝83.3兆韓元超預期，記憶體漲價威力顯現", "summary": ""}])
    assert L == ["📰 新聞焦點：", "・SK海力士財報出爐：第三季營益衝83.3兆韓元超預期，記憶體漲價威力顯現"]
