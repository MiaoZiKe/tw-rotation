"""社群自動回覆的紀錄檔隱私檢查（2026-11-20，Meta 隱私政策／資料刪除說明對應）：
紀錄只能有雜湊鍵、時間、處理結果、是否追蹤；不准出現帳號名稱、留言全文。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "social/ig/state/comments_dm.json", ROOT / "state/tc/ig_dm.json",
         *ROOT.glob("docs/marketing/channels/*/state/comments_dm.json")]
OK_KEYS = {"at", "comment_at", "result", "kw", "follow", "intended", "tries", "post", "sent", "nf", "day", "n",
           "dm_error", "public_error", "counts", "alerts"}


def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if re.fullmatch(r"[0-9a-fu]{16,32}", str(k)):
                k = "<hash>"
            yield path + "/" + str(k), k
            yield from _walk(v, path + "/" + str(k))


def test_state_files_have_no_username_or_text():
    for f in FILES:
        if not f.exists():
            continue
        txt = f.read_text(encoding="utf-8")
        assert "@" not in txt, f
        for _, k in _walk(json.loads(txt)):
            assert k not in {"text", "username", "from", "message", "name"}, (f, k)


def test_tc_pending_is_pruned_after_keep_days():
    src = (ROOT / "scripts/tc_ig_dm.py").read_text(encoding="utf-8")
    assert "for tbl in (comments, msgs, pending):" in src
