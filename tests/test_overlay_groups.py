"""疊加族群（groups.yaml 的 `overlay: true`，矽光子／CPO 題材分頁）的護欄。

為什麼要有這些測試（2026-10-24）：
  M1 資金面把一檔股票的成交值平均分給它所屬的每個族群。若把台積電、日月光、聯發科掛進 12 個新的題材族群，
  晶圓代工、封測、IC 設計的資金佔比會被攤薄 —— 而且不會報錯，只會讓「錢往哪個族群跑」悄悄失真。
  所以題材分頁用疊加族群：不進 M1，只在產業地圖分頁顯示。這裡守住四件事：
    1. 疊加族群不進 membership() 預設，flow 的拆分權重不受影響
    2. 12 組的 id／順序固定（2D／3D 剖析圖的掛載點會用到）、每檔都有階段與信心標記
    3. 載板／PCB／材料那組：CCL 不能被標成受益
    4. 產業地圖 payload 把整條鏈標 overlay、成交值不拆分、不給資金佔比
"""
from __future__ import annotations

import pandas as pd

from pipeline.groups import loader

SIPH_IDS = ["siph_laser", "siph_els", "siph_foundry", "siph_design", "siph_pkg", "siph_fiber",
            "siph_test", "siph_equip", "siph_analysis", "siph_switch", "siph_module", "siph_substrate"]


def test_疊加族群不進預設成分表_要抓價量的地方才帶旗標():
    m = loader.membership()
    assert not m["group_id"].isin(SIPH_IDS).any(), "疊加族群不可以進 M1 的預設成分表（會攤薄原族群的資金佔比）"
    m2 = loader.membership(include_overlay=True)
    assert set(SIPH_IDS) <= set(m2["group_id"]), "include_overlay=True 要收得到疊加族群（回補價量用）"
    assert set(loader.overlay_ids()) == set(SIPH_IDS)


def test_台積電的資金拆分權重不受疊加族群影響():
    from pipeline.compute import flow
    price = pd.DataFrame({"date": ["2026-10-23"] * 2, "code": ["2330", "3711"],
                          "turnover": [100.0, 40.0], "close": [1.0, 1.0], "change": [0.0, 0.0]})
    company = pd.DataFrame({"code": ["2330", "3711"], "industry": ["半導體業", "半導體業"]})
    df = flow._attach_groups(price, company)
    assert not df["group_id"].astype(str).str.startswith("siph_").any()
    w = df[df["code"] == "2330"]["weight"]
    n_primary = len(loader.membership().query("code == '2330'"))
    assert abs(float(w.iloc[0]) - 1.0 / max(1, n_primary)) < 1e-9


def test_十二組id與順序固定_每檔都有階段與信心():
    cfg = loader.load()
    assert cfg["chains"]["siph_cpo"]["order"] == SIPH_IDS, "12 組的 id／順序是剖析圖的掛載點，不可改"
    for gid in SIPH_IDS:
        g = cfg["groups"][gid]
        assert g.get("chain") == "siph_cpo" and g.get("overlay") is True, gid
        assert g.get("note") and g.get("codes"), f"{gid} 要有 note 與成員"
        tags = g.get("member_tags") or {}
        codes = [str(c) for c in g["codes"]]
        assert set(tags) == set(codes), f"{gid} 的 member_tags 要逐檔都有（缺／多：{set(tags) ^ set(codes)}）"
        for c, t in tags.items():
            assert t.get("conf") in ("高", "中高", "中", "中低", "低"), (gid, c, t)
            assert t.get("stage"), (gid, c)
        assert len(codes) == len(set(codes)), f"{gid} 同一族群內代號重複"


def test_載板PCB材料那組_CCL與可插拔光模組板不可標成受益():
    g = loader.load()["groups"]["siph_substrate"]
    tags = g["member_tags"]
    assert all(t.get("stance") in ("受益", "中性", "風險") for t in tags.values())
    # 台燿 6274、台光電 2383、聯茂 6213＝CCL（2026-09-17 降規傳言）；華通 2313、臻鼎 4958＝可插拔光模組板（CPO 是替代風險）
    for code in ("6274", "2383", "6213", "2313", "4958"):
        assert tags[code]["stance"] == "風險", f"{code} 在 CPO 題材是風險，不可畫成受益"
    assert "受益" not in {t["stance"] for t in tags.values()}, "這一組沒有任何一檔有『CPO 專用料號已出貨』的證據"


def test_搬家的兩檔不在舊族群_昇達科進低軌衛星():
    groups = loader.load()["groups"]
    assert "3491" not in groups["silicon_photonics"]["codes"], "昇達科主力是低軌衛星毫米波元件，查證明說無 CPO"
    assert "3491" in groups["satellite"]["codes"]
    assert "7717" not in groups["optical_module"]["codes"], "萊德光電-KY 不是光模組廠"


def test_產業地圖payload把疊加鏈標overlay_成交值不拆分且不給佔比():
    from pipeline import build_payload as bp
    odetail = {"siph_foundry": [
        {"code": "2330", "name": "台積電", "turnover": 300.0, "chg_pct": 2.0, "foreign": 10.0, "trust": 1.0},
        {"code": "2303", "name": "聯電", "turnover": 100.0, "chg_pct": -2.0, "foreign": -4.0, "trust": None},
    ]}
    im = bp.industry_map(pd.DataFrame(), {}, [], pd.DataFrame(), "2026-10-23", odetail)
    ch = {c["id"]: c for c in im["chains"]}
    assert ch["siph_cpo"]["overlay"] is True and ch["siph_cpo"]["turnover"] == 0
    assert not ch["ai_server"].get("overlay") and not ch["semiconductor"].get("overlay")
    g = next(x for x in ch["siph_cpo"]["groups"] if x["id"] == "siph_foundry")
    assert g["overlay"] is True and g["n"] == 2
    assert g["turnover"] == 400.0 and g["turnover_share"] is None, "成交值＝成員完整金額加總，不算佔比"
    assert abs(g["chg_pct"] - (2.0 * 300 + -2.0 * 100) / 400) < 1e-9, "漲跌幅用成交值加權"
    assert g["foreign"] == 6.0 and g["trust"] == 1.0


def test_供應鏈_降級與新增的邊方向正確():
    sc = loader.supply_chain()
    e = {(x["from"], x["to"]): x for x in sc["edges"]}
    assert e[("lpc", "coherent")]["confidence"] == "estimated", "查不到任何來源，不可標 reported"
    assert e[("luxnet", "accton")]["confidence"] == "estimated"
    assert e[("lpc", "truelight")]["rel"] == "outsources_to", "聯亞付錢給光環（後段代工），不是光環供貨給聯亞"
    assert e[("nvidia", "ase")]["rel"] == "outsources_to", "CPO 封裝是 NVIDIA 委外給日月光，錢是 NVIDIA 付的"
    assert ("tsmc", "gud") in e and ("tsmc", "alchip") in e, "設計服務向晶圓廠買產能：tsmc → 創意／世芯"
    assert ("gud", "tsmc") not in e and ("alchip", "tsmc") not in e
    assert e[("umc", "silith")]["rel"] == "supplies"
    # 設備／測試／分析→客戶 查不到具名客戶，不畫邊（『指標龍頭』不等於台積電）
    equip = {"chroma", "huite", "taisheng", "yinneng", "guangyan", "msscorps", "matek"}   # 本次新增的設備／分析節點（旺矽、穎崴、萬潤的舊邊不在此列）
    bad = [(a, b) for (a, b) in e if a in equip and b in {"tsmc", "ase", "nvidia", "broadcom"}]
    assert not bad, f"設備／分析廠不可以憑空連到具名客戶：{bad}"
