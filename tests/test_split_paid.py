"""data-gw 第二階段：付費檔分流（pipeline/split_paid.py）。"""
import json

from pipeline import split_paid


def _mk(p, rel, obj):
    f = p / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(obj), encoding="utf-8")


def test_paid_moved_out_free_kept(tmp_path):
    src, dst = tmp_path / "data", tmp_path / "paid"
    for rel in ["meta.json", "stocks.json", "flow_v3.json", "stock/2330.json", "m60/2330.json",
                "hist/index.json", "hist/2330/p0.json", "explore.json", "unknown_new.json"]:
        _mk(src, rel, {"x": 1})
    r = split_paid.split(src, dst)
    # 付費候選：公開目錄一份都不准留
    for rel in ["flow_v3.json", "stock/2330.json", "m60/2330.json", "hist/2330/p0.json", "explore.json"]:
        assert not (src / rel).exists(), rel
        assert (dst / rel).exists(), rel
    # 免費與不在表上的：留在公開目錄（不在表上的 gateway 也不發，所以不搬）
    for rel in ["meta.json", "stocks.json", "hist/index.json", "unknown_new.json"]:
        assert (src / rel).exists(), rel
    assert r["moved"] == 5
    idx = json.loads((src / "datagw_index.json").read_text(encoding="utf-8"))
    assert {"p": "flow_v3"} in idx["paid"]
    assert any(t.get("re", "").startswith("^stock") for t in idx["paid"])
    assert {"p": "meta"} not in idx["paid"]


def test_tiers_regex_fullmatch():
    t = split_paid.load_tiers()
    assert split_paid.is_paid("stock/2330", t)
    assert not split_paid.is_paid("stock/2330x/../a", t)
    assert not split_paid.is_paid("meta", t)
    assert not split_paid.is_paid("delivery", t)
