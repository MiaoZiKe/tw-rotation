"""供應鏈資料的形狀（2026-09-19 查證後大改，這幾條是防止改壞的護欄）。

Andy 2026-09-19：「請科技業專家協助回答…請查明確實填寫」。
三位 industry-analyst 查證後，環節重新分類、補了 45 條有出處的邊、
刪掉查不到出處的市占數字。這裡守住四件會讓前端畫錯或誤導的事：

1. **每一條邊的兩端都要存在** —— 指到不存在的 id，前端 `coPos[e.from]` 查不到就整條丟掉，
   畫面上看起來是「連線漏畫」，而不是報錯。這正是 2026-09-19 早上圖十的根因之一。
2. **competes 不可以留在 edges 裡** —— 圖十不畫競爭關係（那不是上下游，會被讀成供貨），
   留著只會讓之後讀 YAML 的人以為圖上有。改放 competitors 區塊，而且要送到前端。
3. **有數字就要有出處** —— CLAUDE.md：「市占率要標來源與日期，沒有來源就不要寫數字」。
4. **role 只准是 material / equipment** —— 前端據此決定線的樣式，打錯字會安靜地失效。
"""
from __future__ import annotations

from pipeline.groups import loader


def _sc():
    return loader.supply_chain()


def test_每條邊的兩端都存在():
    sc = _sc()
    ids = {c["id"] for c in sc["companies"]} | {p["id"] for p in sc["products"]}
    bad = [(e["from"], e["to"]) for e in sc["edges"] if e["from"] not in ids or e["to"] not in ids]
    assert not bad, f"邊指到不存在的節點（前端會整條丟掉、看起來像漏畫）：{bad}"


def test_每家公司的環節都存在():
    sc = _sc()
    segs = {s["id"] for s in sc["segments"]}
    bad = [c["id"] for c in sc["companies"] if c.get("segment") not in segs]
    assert not bad, f"公司指到不存在的環節：{bad}"


def test_競爭關係不在edges裡而且有送到前端():
    sc = _sc()
    assert not [e for e in sc["edges"] if e.get("rel") == "competes"], \
        "competes 不可以留在 edges —— 圖十不畫競爭關係，留著會被誤讀成供貨"
    assert sc.get("competitors"), "競爭關係要放在 competitors 區塊並送到前端（公司面板要講得出同業是誰）"
    ids = {c["id"] for c in sc["companies"]}
    for x in sc["competitors"]:
        assert x["a"] in ids and x["b"] in ids, f"競爭關係指到不存在的公司：{x}"


def test_有市占數字就一定要有來源與日期():
    sc = _sc()
    bad = []
    for c in sc["companies"]:
        for sh in c.get("share") or []:
            has_num = sh.get("value_pct") is not None or sh.get("value_pct_range") or sh.get("value")
            if has_num and not (sh.get("source") and sh.get("as_of")):
                bad.append((c["id"], sh))
    assert not bad, f"有數字卻沒有來源或日期（CLAUDE.md 明文禁止）：{bad}"


def test_role只准是材料或設備():
    sc = _sc()
    bad = [s["id"] for s in sc["segments"] if s.get("role") not in (None, "material", "equipment")]
    assert not bad, f"role 打錯字前端會安靜地失效：{bad}"
    roles = {s["id"]: s.get("role") for s in sc["segments"]}
    assert roles.get("pkg_equipment") == "equipment", "封裝設備環節要標 equipment（灰細線）"
    assert roles.get("test_interface") == "equipment", "測試介面環節要標 equipment"
    assert roles.get("ccl") == "material", "CCL 是材料"


def test_設備商不可以再掛在先進封裝環節():
    """弘塑／辛耘／萬潤是設備商不是封裝廠 —— 這是 2026-09-19 查證抓到的分類錯誤。"""
    sc = _sc()
    seg = {c["id"]: c.get("segment") for c in sc["companies"]}
    for cid in ("gpt", "scientech", "allring"):
        assert seg[cid] == "pkg_equipment", f"{cid} 應該在 pkg_equipment，實際 {seg[cid]}"
    assert seg["wineai"] == "test_interface", "穎崴是測試介面（治具耗材），不是封測服務"
    assert seg["gce"] == "hdi_pcb", "金像電不做 ABF 載板，它是高層數 PCB"


def test_載板環節屬於半導體鏈():
    """這一改，載板三雄在半導體鏈上孤立的問題才會解決。"""
    sc = _sc()
    chain = {s["id"]: s.get("chain") for s in sc["segments"]}
    assert chain["abf_pcb"] == "semiconductor"
    assert chain["hdi_pcb"] == "ai_server"


def test_已知寫錯的那條邊已經刪掉():
    """台光電 → 欣興：欣興的 ABF 載板用的是味之素 ABF 膜＋三菱瓦斯 BT core，
    不是台光電的高速 CCL。兩位分析師獨立判定這條會誤導。"""
    sc = _sc()
    assert not [e for e in sc["edges"] if e["from"] == "emc" and e["to"] == "unimicron"]
    assert [e for e in sc["edges"] if e["from"] == "emc" and e["to"] == "gce"], "台光電→金像電 才是主線"


def test_查證補上的關鍵邊都在():
    """這幾條是專家點名「圖上最明顯的洞」，掉了要立刻知道。"""
    sc = _sc()
    have = {(e["from"], e["to"]) for e in sc["edges"]}
    for pair, why in [
        (("broadcom", "accton"), "交換器晶片：兩個節點都在、中間卻沒邊"),
        (("tsmc", "marvell"), "cowos 的需求分配已寫 marvell 8%，卻沒有這條邊"),
        (("tsmc", "gud"), "設計服務是向晶圓廠買產能，方向是 tsmc→gud"),
        (("umc", "faraday"), "智原是聯電陣營，不是台積電"),
        (("allring", "ase"), "日月光採購含稅 10.86 億、約萬潤全年營收 20.2%"),
        (("wistron", "hyperscaler"), "緯創原本有上游沒下游，圖上是斷尾"),
        (("delta", "wiwynn"), "緯穎原本完全沒上游，圖上是斷頭"),
    ]:
        assert pair in have, f"{pair} 這條邊掉了 —— {why}"


def test_委外與指定料號的方向不可以被改成供貨():
    """兩條最容易被『順手改回去』的邊。"""
    sc = _sc()
    e = [x for x in sc["edges"] if x["from"] == "lpc" and x["to"] == "luxnet"]
    assert e and e[0]["rel"] == "outsources_to", \
        "聯亞→華星光 是委外代工（錢是聯亞付給華星光），不是供貨"
    spec = [x for x in sc["edges"] if x.get("rel") == "designated_by"]
    assert spec, "終端指定料號（AVL）要用 designated_by，不可以畫成 supplies"


def test_推論一定要寫原因並附佐證連結():
    """Andy 2026-09-19：「若是事實可以不上相關連結，若是你的推論也記得補上，並說明原因」。

    事實錯了是來源錯，**推論錯了是我錯** —— 所以推論必須把推理過程攤開：
    `note` 要寫「推論依據：…。缺的是：…」，而且要附支撐推論的那篇 `source_url`。
    """
    sc = _sc()
    bad = []
    for e in sc["edges"]:
        if e.get("confidence") != "estimated":
            continue
        note = e.get("note") or ""
        if "推論依據" not in note or "缺的是" not in note:
            bad.append((e["from"], e["to"], "note 沒寫『推論依據 / 缺的是』"))
        if not str(e.get("source_url", "")).startswith("https://"):
            bad.append((e["from"], e["to"], "沒有附 source_url"))
    assert not bad, f"推論沒有攤開推理過程：{bad}"


def test_事實不強迫附連結但推論強迫():
    """反過來也要成立 —— 不可以為了『看起來嚴謹』把事實也標成推論。"""
    sc = _sc()
    ok_conf = {"verified", "reported", "estimated"}
    bad = [(e["from"], e["to"], e.get("confidence")) for e in sc["edges"]
           if e.get("rel") != "produced_by" and e.get("confidence") not in ok_conf]
    assert not bad, f"confidence 只准是 verified / reported / estimated：{bad}"


def test_預估值也會過期(monkeypatch):
    """`_stale()` 原本對 F 結尾的 as_of 直接 `return False` —— 永遠不算過期。

    那等於「一筆 2026 年初的法人預估，到 2028 年還是綠的」，
    CLAUDE.md「超過 180 天沒更新的數字會自動變灰」對所有預估值完全沒生效。
    預估也會過期：2026F 講的是 2026 這一年，就以年底當基準算。
    """
    import datetime as _dt
    from pipeline.groups import loader as _loader

    class _Fake(_dt.date):
        @classmethod
        def today(cls):
            return cls(2027, 9, 1)          # 2026 年底 + 244 天 > 180

    monkeypatch.setattr(_loader, "date", _Fake)
    sc = _loader.supply_chain()
    pens = [p for pr in sc["products"] for p in (pr.get("penetration") or [])
            if str(p.get("as_of", "")).endswith("F")]
    assert pens, "這份資料裡本來就要有預估值，不然這條測試沒有意義"
    assert all(p["stale"] for p in pens), \
        "2027-09 回頭看 2026F 的預估，應該要標成過期（以前永遠是新的）"


def test_預估值要標出來是預估():
    """過期與否是一回事，「這是預估不是實績」是另一回事，畫面上要分得開。"""
    sc = _sc()
    pens = [p for pr in sc["products"] for p in (pr.get("penetration") or [])]
    for p in pens:
        assert "forecast" in p, "penetration 要帶 forecast 旗標"
        assert p["forecast"] == str(p.get("as_of", "")).endswith("F")
    for c in sc["companies"]:
        for sh in c.get("share") or []:
            assert "forecast" in sh, f"{c['id']} 的 share 要帶 forecast 旗標"


def test_as_of不要只寫年份():
    """只寫年份的話，過期判斷只能拿年中當基準，誤差半年。一律寫到月（或季）。"""
    sc = _sc()
    bad = []

    def walk(o, path=""):
        if isinstance(o, dict):
            a = o.get("as_of")
            if a is not None and len(str(a).rstrip("F")) == 4:
                bad.append((path, a))
            for k, v in o.items():
                walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk({k: v for k, v in sc.items() if k != "meta"})
    # 預估值可以只寫年份（2026F 講的就是一整年），實績不行
    bad = [x for x in bad if not str(x[1]).endswith("F")]
    assert not bad, f"as_of 只寫年份，過期判斷會差半年：{bad}"


def test_散熱族群三個檔要對得起來():
    """2026-09-19 查證撞到的真錯誤：`groups.yaml` 的 server_thermal 沒有健策 3653，
    但 `themes.yaml` 的散熱題材與 `supply_chain.yaml` 的 thermal 環節都有它。

    **M1 的族群量能吃的是 groups.yaml** —— 等於健策的資金流根本沒被算進伺服器散熱。
    市場口徑固定是「散熱三雄＝奇鋐＋雙鴻＋健策」，而且 2026-05-06 一則封裝層級的
    均熱片降價傳言讓三家同步重挫，資金流事實上是同向的。三個檔必須對得起來。
    """
    import yaml
    from pipeline.groups import loader as _loader
    root = _loader.CHAIN_PATH.parent
    g = yaml.safe_load((root / "groups.yaml").read_text(encoding="utf-8"))
    t = yaml.safe_load((root / "themes.yaml").read_text(encoding="utf-8"))
    sc = _sc()

    grp = set(g["groups"]["server_thermal"]["codes"])
    thm = set(t["themes"]["thermal"]["codes"])
    chain = {c["ticker"] for c in sc["companies"]
             if c.get("segment") == "thermal" and c.get("tw_code")}

    missing = chain - grp
    assert not missing, (
        f"supply_chain 的散熱環節有 {sorted(missing)}，但 groups.yaml 的 server_thermal 沒有 —— "
        "M1 族群量能會漏算它們")
    assert chain <= thm, (
        f"supply_chain 的散熱環節有 {sorted(chain - thm)}，但 themes.yaml 的散熱題材沒有")


def test_台股代號的格式與唯一性():
    """2026-09-19 差點把竑騰寫成 6428（那是台灣淘米，遊戲／文創股）。

    代號錯了不會報錯 —— 網站的個股頁會去抓完全另一家公司的股價與營收，
    而且看起來完全正常。這裡至少守住格式與唯一性這兩件機器驗得到的事。
    """
    import collections
    sc = _sc()
    tw = [c["tw_code"] for c in sc["companies"] if c.get("tw_code")]
    bad = [t for t in tw if not (t.isdigit() and len(t) == 4)]
    assert not bad, f"台股代號要是 4 碼數字：{bad}"
    dup = [k for k, v in collections.Counter(tw).items() if v > 1]
    assert not dup, f"同一個代號出現在兩家公司上：{dup}"
    # 外商不可以有 tw_code
    foreign = [c["id"] for c in sc["companies"] if c.get("foreign") and c.get("tw_code")]
    assert not foreign, f"標成外商卻有台股代號：{foreign}"


def test_竑騰的代號是7751():
    """這一條是釘死一個具體的錯。6428 是台灣淘米（遊戲／文創），不是竑騰。

    來源：鉅亨 https://www.cnyes.com/twstock/7751 、工商時報 2025-08-26 上櫃報導、
    Goodinfo 個股基本資料（7751 竑騰，2025/08/26 上櫃，半導體業）。
    """
    sc = _sc()
    hta = [c for c in sc["companies"] if c.get("name") == "竑騰"]
    if not hta:
        return                      # 還沒加進來就跳過
    assert hta[0]["tw_code"] == "7751", "竑騰是 7751；6428 是台灣淘米（遊戲／文創股）"
