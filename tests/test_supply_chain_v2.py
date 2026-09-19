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
