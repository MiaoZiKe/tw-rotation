"""私訊連結帶頻道憑證（2026-11-16）：有碼才接 ?tc=，且對得上 site/articles/unlock.json 的 sha256；公開回覆不帶。"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tc_dm_keys as K  # noqa: E402


def test_with_unlock_adds_code_to_article_link():
    t = "完整解說：https://liguligu-puipui.com/#article/2026-11-15-tech-2nm"
    assert K.with_unlock(t, "tcabc12345") == "完整解說：https://liguligu-puipui.com/?tc=tcabc12345#article/2026-11-15-tech-2nm"


def test_with_unlock_no_code_or_bad_code_unchanged():
    t = "https://liguligu-puipui.com/"
    assert K.with_unlock(t, "") == t
    assert K.with_unlock(t, "a b") == t
    assert K.with_unlock("https://liguligu-puipui.com/?tc=x1234", "tcabc12345") == "https://liguligu-puipui.com/?tc=x1234"


def test_unlock_json_has_hash_only():
    j = json.loads((ROOT / "site/articles/unlock.json").read_text(encoding="utf-8"))
    hs = j["tech"]["sha256"]
    assert hs and all(len(h) == 64 and set(h) <= set("0123456789abcdef") for h in hs)
    assert hashlib.sha256(b"tcx7k2m9").hexdigest() not in hs
