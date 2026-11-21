"""每日資料管線關卡要跑哪些 pytest 檔（白名單，2026-11-09）。

事故：「跑指標庫測試」關卡三次被跟資料管線無關的測試擋死整條盤後資料
（10-28 社群封面缺 Playwright、11-06 test_exrights 寫死本益比窗、11-09 IG 短影片缺中文字型）。
Andy 11-09：「需要避免這事情發生」。

規則：只跑「會 import pipeline 的測試檔」，再扣掉名稱屬於社群／IG／TC 的、內容用到 Playwright／中文字型的。
清單為空 → 結束碼 1（要失敗，不是退回全跑）。
daily.yml 與 tests-on-push.yml 都呼叫這支，兩邊永遠同一份清單。

用法：python scripts/daily_test_list.py        # 印出以空白分隔的檔案清單
"""
from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

IMPORT_PIPELINE = re.compile(r"^\s*(from|import)\s+pipeline", re.M)
# 名稱就屬於「非資料管線」的測試（社群貼文、IG 短影片、TC 自動發文）
EXCLUDE_NAMES = ["test_social*", "test_tc_*", "test_ig_*"]
# 內容用到這些就不能進每日關卡（daily 沒裝 Playwright、沒有中文字型）
EXCLUDE_CONTENT = re.compile(r"playwright|FONT_CANDIDATES|ImageFont", re.I)
# 一律加進清單的守門測試（它自己不 import pipeline）
ALWAYS = ["test_daily_test_scope.py"]


def select() -> list[str]:
    out = []
    for f in sorted(TESTS.glob("test_*.py")):
        if f.name in ALWAYS:
            out.append(f"tests/{f.name}")
            continue
        if any(fnmatch.fnmatch(f.name, g) for g in EXCLUDE_NAMES):
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        if not IMPORT_PIPELINE.search(txt):
            continue
        if EXCLUDE_CONTENT.search(txt):
            continue
        out.append(f"tests/{f.name}")
    return out


if __name__ == "__main__":
    files = select()
    if not files:
        print("daily_test_list：白名單是空的，拒絕放行（不退回全跑）", file=sys.stderr)
        sys.exit(1)
    print(" ".join(files))
