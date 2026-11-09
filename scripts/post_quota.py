"""發文名額開關（2026-11-02 Andy：「同意降量」）。

唯一的設定檔：docs/marketing/social_unit/post_quota.json。所有會真的呼叫 Meta API 的程式
（social_publish.py、threads_post.py、ig_post.py）以及排稿／監工（social_news.py、ig_news_check.py、
social-live.yml、social_news.yml）在動手前都問這裡。關掉的：印「降量模式：略過」並以成功結束
（不是失敗、不寄失敗信、不觸發補發）。要放量只改那個 JSON。

  live.<kind>.<threads|ig_story>   社群即時貼文（social-live.yml → social_publish.py）；kind＝premarket／intraday／close／credit／close_inst
                                   close_inst＝盤後法人補充貼文（鍵 close-inst-<日期>，2026-10-29 保底後補發的那一則）。
                                   ★ 2026-11-09：它是「另一則貼文」，不吃 close 的開關（11-06 就是吃了 close=true 多發一則）；
                                     開關檔沒寫 → 用 DEFAULT（關）。要開只能 Andy 說了，在 JSON 的 live 底下加 close_inst。
  queue.news.<threads|ig>          social_news.py 自動產生的主題文章（佇列檔名 <日期>_news-<段>-<n>.md）
  queue.manual.<threads|ig>        其他佇列檔（手寫、手動加發；仍須人工把 status 改成 approved 才會發）

只用標準函式庫（social-live.yml 在裝 Python 套件之前就要讀）。
用法（給工作流程用）：python3 scripts/post_quota.py any <premarket|intraday|close|credit|news|manual>
  → 印 on（至少一個平台開著）或 off；結束碼一律 0。
設定檔讀不到或格式壞掉 → 用下面的 DEFAULT（＝11-02 降量規格），並印警告。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUOTA_FILE = ROOT / "docs" / "marketing" / "social_unit" / "post_quota.json"
SKIP_MSG = "降量模式：略過"

DEFAULT = {
    "live": {
        "premarket": {"threads": False, "ig_story": False},
        "intraday": {"threads": False, "ig_story": False},
        "close": {"threads": True, "ig_story": False},
        "credit": {"threads": False, "ig_story": False},
        "close_inst": {"threads": False, "ig_story": False},      # 2026-11-09：法人補充貼文另計一則，降量模式不發
    },
    "queue": {
        "news": {"threads": False, "ig": False},
        "manual": {"threads": True, "ig": True},
    },
}

_AUTO_NEWS = re.compile(r"_news-[a-z0-9]+-\d+(\.md)?$")
_REEL = re.compile(r"_reel-[a-z0-9_-]+(\.md)?$")      # ig_reels_weekly.py 產的 IG 短影片佇列檔（2026-11-09）


def path() -> Path:
    p = os.environ.get("POST_QUOTA_FILE", "").strip()
    return Path(p) if p else QUOTA_FILE


def load(p: Path | str | None = None) -> dict:
    p = Path(p) if p else path()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or not isinstance(d.get("live"), dict) or not isinstance(d.get("queue"), dict):
            raise ValueError("缺 live／queue")
        return d
    except (OSError, ValueError) as e:
        print(f"::warning::發文名額開關檔讀不到（{p}：{e}）→ 用內建降量規格", flush=True)
        return DEFAULT


def _flag(q: dict, section: str, group: str, platform: str) -> bool:
    v = ((q.get(section) or {}).get(group) or {}).get(platform)
    if v is None:      # 沒寫到的 kind／平台 → 看內建規格；內建也沒有 → 關（降量模式寧可少發）
        v = ((DEFAULT.get(section) or {}).get(group) or {}).get(platform, False)
    return v is True


def live_kind(m: dict) -> str:
    """manifest → 名額開關用的 kind。盤後法人補充貼文（kind=close＋supplement）是另一則貼文 → close_inst。"""
    kind = (m or {}).get("kind") or "intraday"
    return "close_inst" if kind == "close" and (m or {}).get("supplement") else kind


def live_allowed(kind: str, platform: str, q: dict | None = None) -> bool:
    """社群即時貼文：kind＝premarket／intraday／close／credit；platform＝threads／ig_story。"""
    return _flag(q if q is not None else load(), "live", kind or "intraday", platform)


def is_auto_news(filename: str) -> bool:
    """social_news.py 自動產生的主題文章佇列檔（<日期>_news-<段>-<n>.md）。"""
    return bool(_AUTO_NEWS.search(Path(str(filename)).name))


def group_allowed(group: str, platform: str, q: dict | None = None) -> bool:
    """佇列類別：group＝news／manual；platform＝threads／ig。"""
    return _flag(q if q is not None else load(), "queue", group, platform)


def is_reel(filename: str) -> bool:
    return bool(_REEL.search(Path(str(filename)).name))


def reels_enabled(q: dict | None = None) -> bool:
    """IG 每週短影片（Andy 11-09 同意）：ig.reels_weekly；沒寫＝開（Andy 已同意放量），明寫 false 才關。"""
    v = ((q if q is not None else load()).get("ig") or {}).get("reels_weekly")
    return v is not False


def reels_need_review(q: dict | None = None) -> bool:
    """第一支正式發布前 CEO 先看樣片：ig.reels_need_review＝true 時佇列檔只寫 draft，不自動發。沒寫＝需要審。"""
    v = ((q if q is not None else load()).get("ig") or {}).get("reels_need_review")
    return v is not False


def queue_allowed(platform: str, filename: str, q: dict | None = None) -> bool:
    """佇列發文（threads_post.py／ig_post.py）：platform＝threads／ig。"""
    if platform == "ig" and is_reel(filename):      # 短影片有自己的開關，不吃 queue.manual.ig
        return reels_enabled(q)
    return group_allowed("news" if is_auto_news(filename) else "manual", platform, q)


def any_on(group: str, q: dict | None = None) -> bool:
    q = q if q is not None else load()
    if group in ("news", "manual"):
        return any(_flag(q, "queue", group, p) for p in ("threads", "ig"))
    return any(_flag(q, "live", group, p) for p in ("threads", "ig_story"))


def main(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[1] == "any":
        print("on" if any_on(argv[2]) else "off")
        return 0
    print(json.dumps(load(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
