"""link_index.json（開站對照表小檔）：industry_map／supply_chain 的骨架，順序一律照原檔（2026-10-07 開頁速度第二輪）。

前端 L.init 的族群色＝族群在清單中的位置、環節色＝color_idx（缺就用位置）、族群取「第一個」環節色，
所以順序變了全站顏色就會洗掉。這裡釘住：順序、color_idx、公司→環節／族群的先後都跟原檔一致。"""
from pipeline import build_payload as bp


def _im():
    return {"chains": [{"id": "semiconductor", "name": "半導體", "turnover": 1,
                        "groups": [{"id": "foundry", "name": "晶圓代工", "members": [{"code": "2330"}], "valuation": {}},
                                   {"id": "osat", "name": "封測", "members": []}]},
                       {"id": "ai_server", "name": "AI 伺服器", "groups": [{"id": "ai_server_odm", "name": "組裝"}]}],
            "industries": [{"id": "ind_ETF", "name": "ETF", "members": [{"code": "0050"}]}],
            "segments_pe": {"x": 1}}


def _sc():
    return {"segments": [{"id": "b", "color_idx": 5, "name": "B"}, {"id": "a", "name": "A"}, {"id": "c", "color_idx": 0}],
            "companies": [{"code": "1", "segment": "b", "groups": ["封測"]},
                          {"code": "2", "segment": "a", "groups": ["封測", "晶圓代工"]},
                          {"code": "3", "segment": "b", "groups": ["封測"]},
                          {"code": "4", "segment": None, "groups": ["封測"]},
                          {"code": "5", "segment": "c", "groups": []}],
            "edges": [1, 2], "products": [3]}


def test_link_index_keeps_order_and_drops_heavy_fields():
    li = bp.link_index(_im(), _sc())
    assert [c["id"] for c in li["chains"]] == ["semiconductor", "ai_server"]
    assert li["chains"][0]["groups"] == [{"id": "foundry", "name": "晶圓代工"}, {"id": "osat", "name": "封測"}]
    assert li["industries"] == [{"id": "ind_ETF", "name": "ETF"}]
    assert li["segments"] == [{"id": "b", "color_idx": 5}, {"id": "a", "color_idx": 1}, {"id": "c", "color_idx": 0}]
    # 先後照原檔、完全重複的去掉、沒環節或沒族群的不列
    assert li["companies"] == [{"segment": "b", "groups": ["封測"]}, {"segment": "a", "groups": ["封測", "晶圓代工"]}]
    assert set(li) == {"chains", "industries", "segments", "companies"}


def test_link_index_empty_inputs():
    assert bp.link_index({}, {}) == {"chains": [], "industries": [], "segments": [], "companies": []}
    assert bp.link_index(None, None)["chains"] == []
