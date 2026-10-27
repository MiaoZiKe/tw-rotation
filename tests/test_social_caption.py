"""社群文案：4 行全滿時實際字元數要 ≤ 480（Threads 上限 500）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_snap as ss  # noqa: E402


def _shots():
    long3 = ["石化與塑膠產業", "PCB 硬板製造", "CCL 銅箔基板"]
    return [
        {"name": "rotation", "ok": True, "lines": [["領先", long3], ["落後", ["晶圓代工", "ETF", "HPC 與網通 IC"]]]},
        {"name": "sankey", "ok": True, "notes": [["流入前五", long3], ["流出前五", ["ETF", "晶圓代工", "HPC 與網通 IC"]]]},
        {"name": "heat", "ok": True, "heat": [["軟板", 9.7], ["玻纖布", 9.4], ["電阻與被動保護", -4.4], ["AR VR XR 光學", -2.7], ["其他", 0.1]]},
        {"name": "market-breadth", "ok": True, "breadth": {"up": "1,507", "down": "577"}},
    ]


def test_caption_full_four_lines_within_480():
    txt = ss.build_text("intraday", "10/20 12:34", _shots(), "2026-10-20", "20261020")
    assert len(txt) <= 480, len(txt)
    L = txt.splitlines()
    i = L.index("🎡 資金輪盤：")
    assert L[0] == "🕛 盤中3分鐘" and L[1] == "🧭 盤面分析：" and L[i + 1].startswith("・領先 ") and L[i + 2].startswith("・落後 ")      # 10-26 晚：盤面分析放最前   # 2026-10-26 Andy 指定格式
    assert "🌳 資金分流樹：" in L and "🔥 熱力圖：" in L and L[-3].startswith("#台股") and "資料：" not in txt   # 盤中文案不放免責／來源
    assert L[-1].startswith(ss.link_url("intraday", "20261020")) and L[-1].split("#")[0] == "https://liguligu-puipui.com/?u=th-id-20261020" and txt.count("https://") == 1 and " → " not in txt   # Andy：「連結只需要附在最底下就好」＋10-26 連結改成首頁＋說明句
    assert "#heatmap" not in txt
    assert "utm_medium" not in txt and "即時" not in txt


def _mf(d="2026-10-21", ratio=168.2, partial=False, rank_d=None, short_d=None):
    return {"margin": {"rows": [{"d": "2026-10-20", "ratio": 170.0}, {"d": d, "ratio": ratio, "partial": partial}],
                       "rank": {"d": rank_d or d, "rows": []}, "short_rank": {"d": short_d or d, "rows": []}}}


def test_盤後融資_資料到齊才發():
    meta = {"data_date": "2026-10-21", "inst_date": "2026-10-21"}
    assert ss.credit_ready(meta, _mf()) == (True, "2026-10-21", "")
    # 整體市場融資還停在前一天（10/21 22:13 那輪實際狀況）
    ok, d, why = ss.credit_ready(meta, _mf(d="2026-10-20"))
    assert not ok and d == "2026-10-20" and "還沒更新" in why
    # 整體市場到了、個股融資還沒到 → 維持率算不出來
    assert not ss.credit_ready(meta, _mf(ratio=None))[0]
    assert not ss.credit_ready(meta, _mf(partial=True))[0]
    assert not ss.credit_ready(meta, _mf(rank_d="2026-10-20"))[0]
    assert not ss.credit_ready(meta, _mf(short_d="2026-10-20"))[0]      # 2026-10-26 第三張融券排行也要同一天
    assert not ss.credit_ready(meta, {})[0]
    # 隔天清晨（價量還沒換天）照樣可以發前一天的融資；隔天 15:30 價量換天後就不再發
    assert ss.credit_ready({"data_date": "2026-10-21"}, _mf())[0]
    assert not ss.credit_ready({"data_date": "2026-10-22"}, _mf())[0]


def test_盤後融資文案_獨立一篇():
    shots = [{"name": "credit-ratio", "ok": True, "read": {"ratio": "168.20", "chg": "−1.35"}},
             {"name": "credit-rank", "ok": True, "read": {"up": ["長榮", "華邦電", "群創"], "down": ["台積電", "聯電", "鴻海"]}},
             {"name": "credit-short", "ok": True, "read": {"up": ["友達", "力積電", "南亞科"], "down": ["英業達", "廣達", "緯創"]}}]
    txt = ss.build_text("credit", "10/22 05:10", shots, "2026-10-21", "20261022")
    L = txt.splitlines()
    assert L[0] == "💳 盤後融資融券" and L[1] == "🛡️ 融資維持率："      # 2026-10-26 Andy 盤中格式套用到盤後
    assert "・上市（估算）168.20%，較前日 -1.35pp" in L
    assert L[L.index("📈 融資：") + 1] == "・增加 長榮、華邦電；" and L[L.index("📈 融資：") + 2] == "・減少 台積電、聯電"
    assert L[L.index("📉 融券：") + 1] == "・增加 友達、力積電；" and L[L.index("📉 融券：") + 2] == "・減少 英業達、廣達"
    assert L[-3].startswith("#台股 #融資") and L[-2] == ss.LINK_LINES[0] and L[-1].startswith(ss.link_url("credit", "20261022")) and L[-1].split("#")[0].endswith("?u=th-mg-20261022")
    assert txt.count("https://") == 1 and ss.DISCLAIMER not in txt      # 網址只在最底下、不放免責
    assert len(txt) <= 480
    # 2026-10-26 起盤後那篇也帶融資融券（合併）
    close = ss.build_text("close", "10/21 21:40", shots, "2026-10-21", "20261021")
    assert close.splitlines()[0] == "🌙 盤後3分鐘" and "📈 融資：" not in close and close.count("https://") == 1      # 10-27 融資移到盤前


def test_盤後文案_照盤中格式():
    shots = [{"name": "inst-today", "ok": True, "read": [["外資", "−815.8億"], ["投信", "+94.9億"], ["自營商", "−273.8億"], ["三大法人合計", "−994.7億"]]},
             {"name": "streak-foreign", "ok": True, "read": {"buy": ["緯穎", "廣達", "精材"], "sell": ["台積電", "國巨*", "南亞"]}},
             {"name": "fut-oi", "ok": True, "read": "外資 -87,297 投信 +83,601 自營商 +3,260"}]
    txt = ss.build_text("close", "10/22 17:20", shots, "2026-10-22", "20261022")
    L = txt.splitlines()
    assert L[0] == "🌙 盤後3分鐘" and L[1] == "📊 台指期法人淨未平倉："      # 2026-10-26 Andy：第一頁法人未平倉
    i = L.index("🏦 三大法人買賣超：")
    assert L[i + 1] == "・外資 -815.8億、投信 +94.9億；" and L[i + 2] == "・自營 -273.8億、合計 -994.7億" and i > L.index("📊 台指期法人淨未平倉：")
    assert "🌏 外資：" in L and "・買超 緯穎、廣達、精材；" in L and "・賣超 台積電、國巨、南亞" in L and "📊 台指期法人淨未平倉：" in L   # 10-27 起買賣超列前五名（測資只有 3 個）、星號拿掉
    assert L[-3].startswith("#台股") and L[-2] == ss.LINK_LINES[0] and L[-1].startswith(ss.link_url("close", "20261022")) and L[-1].split("#")[0].endswith("?u=th-cl-20261022") and txt.count("https://") == 1
    assert " → " not in txt and ss.DISCLAIMER not in txt and len(txt) <= 480


def test_融資卡歸盤後融資那篇():
    kinds = {t["name"]: t["kind"] for t in ss.TARGETS}
    assert kinds["credit-ratio"] == kinds["credit-rank"] == "credit"
    assert all(kinds[n] == "close" for n in ("inst-today", "streak-foreign", "streak-trust", "fut-oi", "retail-ratio"))
    assert kinds["market-index"] == kinds["market-breadth"] == "off"      # 2026-10-26 Andy：大盤走勢、漲跌家數拿掉
    assert set(ss.KIND_SET["close"]) == {"close"}               # 2026-10-27 Andy：融資移到隔天盤前


def test_融資排行只列個股():
    import social_native as nat
    assert nat.is_stock("2330") and not nat.is_stock("00631L") and not nat.is_stock("0050") and not nat.is_stock("020011")
    m = {"rank": {"rows": [{"code": "00686R", "name": "反1", "chg": 9}, {"code": "2409", "name": "友達", "chg": 3},
                           {"code": "1802", "name": "台玻", "chg": -6}, {"code": "00671R", "name": "反1", "chg": -9}]}}
    up, dn = nat.credit_top(m, "rank")
    assert [r["code"] for r in up] == ["2409"] and [r["code"] for r in dn] == ["1802"]
    assert nat.clean_name("國巨*") == "國巨"


def test_法人排行只列個股():
    import social_native as nat
    j = {"all_by": {"foreign": [["2330", -100, -302.8], ["0050", -20, -49.2], ["6669", 30, 23.5], ["00631L", 5, 30.0], ["3374", 10, 20.8]]},
         "top": {"foreign": {"buy": [{"code": "6669", "name": "緯穎", "amt": 2.35e9}], "sell": [{"code": "2330", "name": "台積電", "amt": -3.0e10}]}}}
    buy, sell = nat.inst_top(j, "foreign", 10, {"3374": "精材"})
    assert [r["code"] for r in buy] == ["6669", "3374"] and [r["name"] for r in buy] == ["緯穎", "精材"]
    assert [r["code"] for r in sell] == ["2330"]       # 0050 排除


def test_盤後圖順序_未平倉第一_散戶第二():
    import inspect
    src = inspect.getsource(ss)
    assert '"close": ["fut-oi", "retail-ratio", "inst-today", "streak-foreign", "streak-trust"]' in src


def test_ETF買超含槓桿型_附張數():
    import social_native as nat
    j = {"all_by": {"foreign": [["00631L", 900, 0.5], ["00632R", 999, 0.1], ["2330", 10, 9.0], ["00687B", 16132, 4.36]]}}
    rows = nat.etf_buy(j, "foreign", 10, {})
    assert [r["code"] for r in rows] == ["00687B", "00631L", "00632R"] and rows[1]["lots"] == 900


def test_盤面分析_盤中與盤後():
    ok = {"heat": {"heat": [["A", 3.0], ["B", 2.0], ["C", -1.0], ["D", 1.5]]},
          "sankey": {"notes": [["流入前五", ["A", "C"]], ["流出前五", ["B", "晶圓代工"]]]}}
    r = ss.intraday_reads(ok)
    assert r[0].startswith("族群普漲") and "族群平均" in r[0] and any("成交比重增加且漲幅居前：A" in x for x in r) \
        and any("成交比重增加但族群走低：C" in x for x in r) and not any("收黑" in x for x in r)      # 12:00 還沒收盤
    im = {"rows": [{"d": "1", "f": 10, "t": 5}, {"d": "2", "f": -3, "t": 6}, {"d": "3", "f": -4, "t": 7}]}
    r = ss.close_reads(im, {"foreign": {"net": [-100, -150]}}, {}, {"taiex": 100, "change": -2, "advancers": 100, "decliners": 300}, [{"prod": "小台", "pct": "+25%"}], {"ratio": "170", "chg": "-1.2"})
    assert r[0].startswith("加權指數跌 2 點") and "上市櫃（含 ETF）" in r[0]
    assert "外資賣超 4.0 億，已連 2 日賣超，累計 7.0 億" in r and "投信買超 7.0 億，已連 3 日買超，累計 18.0 億" in r
    assert "外資加空台指期 50 口，未平倉淨空單升至 150 口" in r and any("（多方部位較多），與外資期貨淨空方向相反" in x for x in r)
    r2 = ss.close_reads({"rows": [{"f": -500}] * 8 + [{"f": 22}, {"f": -815.8}]}, {}, {}, {}, [], {})
    assert r2[0].startswith("外資賣超 815.8 億，近 10 日 9 日賣超")      # 前一天只小買 → 不寫「轉賣」
    assert not any(w in "".join(r + r2) for w in ("可望", "將", "建議", "布局", "明顯偏多", "收黑"))


# ---- 2026-10-27 深層連結（docs/marketing/feature_funnel_1027.md 第四節）：落點依當天內容挑，?u= 一定在 # 前面、路由走白名單
def test_pick_landing_領漲族群對應產業鏈():
    rt, why = ss.pick_landing("intraday", {"leaders": ["晶圓代工", "航運"]})
    assert rt.startswith("industry/") and ss.route_ok(rt) and "領漲" in why
    assert ss.pick_landing("intraday", {"leaders": ["不存在的族群"]})[0] == "flow/rotation"        # 沒對應 → 保底
    assert ss.pick_landing("close", {})[0] == "market/inst" and ss.pick_landing("credit", {})[0] == "market/credit"


def test_pick_landing_盤前事件與連續兩天換落點():
    assert ss.pick_landing("premarket", {"events": ["FOMC 利率決議"]})[0] == "earnings"
    assert ss.pick_landing("premarket", {"events": ["某 ETF 除息"]})[0] == "etf/cal"
    assert ss.pick_landing("premarket", {"reads": ["費半 +2%"]})[0] == "industry/semiconductor"
    assert ss.pick_landing("premarket", {})[0] == ""
    c = {"leaders": ["晶圓代工", "航運"]}
    first = ss.pick_landing("intraday", c)[0]
    assert ss.pick_landing("intraday", c, [first, first])[0] != first      # 同一落點已連 2 天 → 換下一個


def test_route_ok_白名單與網址格式():
    for r in ("flow/rotation", "market/inst", "earnings", "etf/cal", "etf/inc", "industry/semiconductor", "heatmap/industry"):
        assert ss.route_ok(r), r
    for r in ("pricing", "industry/nochain", "industry/group/xx", "stock/2330", "../x", ""):
        assert not ss.route_ok(r), r
    u = ss.link_url("intraday", "20261027", route="industry/semiconductor")
    assert u == "https://liguligu-puipui.com/?u=th-id-20261027#industry/semiconductor" and u.index("?u=") < u.index("#")
    assert ss.link_url("close", "20261027", route="pricing") == "https://liguligu-puipui.com/?u=th-cl-20261027"      # 不在白名單 → 首頁
    assert ss.link_url("premarket", "20261029", func="f3d", route="etf/cal").endswith("?u=th-f3d-20261029#etf/cal")


# ---- 2026-10-27 近幾天落點記憶：state/landing_recent.json 讓「同一落點連續 2 天就換」真正生效
def test_landing_recent_落點連兩天會換並寫檔(tmp_path):
    ss.CHOSEN.clear()
    f = tmp_path / "in.json"
    c = {"leaders": ["晶圓代工", "航運"]}
    ss.load_recent(None)
    first = ss.landing_route("intraday", "20261026", c)
    f.write_text(__import__("json").dumps({"intraday": [{"d": "20261024", "r": first}, {"d": "20261025", "r": first}]}), "utf-8")
    ss.load_recent(f)
    assert ss.RECENT["intraday"] == [first, first]
    assert ss.landing_route("intraday", "20261026", c) != first          # 已連 2 天 → 換
    ss.save_recent(tmp_path)
    saved = __import__("json").loads((tmp_path / "landing_recent.json").read_text("utf-8"))
    assert saved["intraday"][-1]["d"] == "20261026" and len(saved["intraday"]) == 3
    # 同一天重跑：今天自己那一筆不算「近幾天」
    f.write_text(__import__("json").dumps(saved), "utf-8")
    ss.load_recent(f)
    again = ss.landing_route("intraday", "20261026", c)
    assert again == saved["intraday"][-1]["r"]
    ss.save_recent(tmp_path)
    assert len(__import__("json").loads((tmp_path / "landing_recent.json").read_text("utf-8"))["intraday"]) == 3
    ss.load_recent(None)
    ss.CHOSEN.clear()
    assert ss.pick_landing("intraday", c)[0] == first                      # 清掉記憶後不受影響


def test_pick_landing_盤前熱門ETF除息導etf_cal():
    assert ss.pick_landing("premarket", {"etf_div": ["00919 群益台灣精選高息 11/03"]})[0] == "etf/cal"
    assert ss.pick_landing("premarket", {"events": ["FOMC 利率決議"], "etf_div": ["0056 x 11/03"]})[0] == "earnings"     # 總經事件優先
