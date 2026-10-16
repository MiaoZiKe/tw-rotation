"""新精選文章的發佈（2026-10-16 防白嫖，docs/articles/production_guide.md「發佈：全文上傳＋僅標題索引」）。

為什麼有這支：新文章的全文**只能存在會員 Worker**（site/articles/posts/ 是公開檔、repo 是 public，全文推上去就等於公開）。
Claude 寫完文章後不再把全文推進 repo，而是：
  ① 全文 JSON 放在 repo 以外的地方（例如暫存區）；
  ② python scripts/article_publish.py <全文.json> —— 用機器鑰匙（ARTICLE_BOT_KEY）把全文傳到 Worker（op:put_body），
     再用 list_bodies 確認真的存進去了，**確認之後才**把「僅標題」的索引項目寫進 site/articles/index.json；
  ③ 把 index.json 推上 main（索引只有標題、分類、日期、topic、族群、reading_min，加 src:'api'）。
  失敗（沒金鑰、連不到、沒存進去）→ 不寫索引、離開代碼非 0。**不要退而求其次把全文推進 repo。**

其他指令：
  --check                檢查公開檔有沒有洩漏：src:'api' 的索引項目不得帶 summary／subtitle／tags／blocks 等內容欄位，
                         而且 site/articles/posts/<id>.json 不得存在（pytest 與 CI 會跑，見 tests/test_article_public_guard.py）
  --index-only <全文.json>   不上傳，只依全文 JSON 產出索引項目（Worker 已經有這篇時用；會先確認 Worker 真的有）
環境變數：ACCOUNT_API_URL、ARTICLE_BOT_KEY（或 BACKUP_TOKEN）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from scripts import article_jobs as aj

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "site" / "articles" / "index.json"
POSTS = ROOT / "site" / "articles" / "posts"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{4,80}$")
# 公開索引允許的欄位：不含任何內文（摘要、副標、標籤都算內文）
PUBLIC_KEYS = ("id", "cat", "title", "date", "topic", "groups", "reading_min", "src", "status")
# src:'api' 的索引項目一律不得出現的欄位
LEAK_KEYS = ("summary", "subtitle", "tags", "blocks", "sources", "site_links", "confidence")


def public_entry(post: dict, topic: str | None = None) -> dict:
    """由全文 JSON 產出公開索引項目（只留 PUBLIC_KEYS；src 固定 'api'）。缺必要欄位直接丟 ValueError。"""
    pid = str(post.get("id") or "")
    if not ID_RE.match(pid):
        raise ValueError(f"文章 id 不合格：{pid!r}")
    if post.get("cat") not in ("news", "intro", "know"):
        raise ValueError("cat 必須是 news／intro／know")
    if not post.get("title") or not re.match(r"^\d{4}-\d\d-\d\d$", str(post.get("date") or "")):
        raise ValueError("需要 title 與 date（YYYY-MM-DD）")
    if not isinstance(post.get("blocks"), list) or not post["blocks"]:
        raise ValueError("全文沒有 blocks")
    t = topic or post.get("topic")
    if not t:
        raise ValueError("缺 topic：沒有 topic 就不會自動標完成（見 production_guide.md）")
    groups = [{"id": g["id"], "name": g["name"]} for g in (post.get("groups") or []) if isinstance(g, dict) and g.get("id") and g.get("name")]
    return {"id": pid, "cat": post["cat"], "title": post["title"], "date": post["date"], "topic": t, "groups": groups,
            "reading_min": int(post.get("reading_min") or 3), "src": "api"}


def leaks(index_path: Path | None = None, posts_dir: Path | None = None) -> list[str]:
    """公開檔洩漏檢查：回傳問題清單（空＝乾淨）。只管 src:'api' 的新文章；舊的 4 篇維持原狀不查。"""
    index_path, posts_dir = index_path or INDEX, posts_dir or POSTS     # 呼叫時才取預設（測試會換掉模組的 INDEX）
    out: list[str] = []
    try:
        arts = json.loads(index_path.read_text(encoding="utf-8")).get("articles") or []
    except (OSError, ValueError):
        return [f"讀不到 {index_path}"]
    for a in arts:
        if a.get("src") != "api":
            continue
        bad = [k for k in LEAK_KEYS if k in a]
        if bad:
            out.append(f"{a.get('id')}：索引帶了內容欄位 {','.join(bad)}（新文章的索引只能有標題、分類、日期等）")
        if (posts_dir / f"{a.get('id')}.json").exists():
            out.append(f"{a.get('id')}：公開的 site/articles/posts/{a.get('id')}.json 存在（新文章全文不得放進 repo）")
    return out


def add_to_index(entry: dict, index_path: Path | None = None) -> None:
    index_path = index_path or INDEX
    d = json.loads(index_path.read_text(encoding="utf-8"))
    arts = [a for a in (d.get("articles") or []) if a.get("id") != entry["id"]]
    arts.insert(0, entry)
    d["articles"] = arts
    d["updated"] = entry["date"] if entry["date"] > str(d.get("updated") or "") else d.get("updated")
    index_path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("post", nargs="?", help="全文 JSON（放在 repo 以外）")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--index-only", action="store_true")
    ap.add_argument("--topic", default="")
    a = ap.parse_args(argv)
    if a.check:
        bad = leaks()
        for b in bad:
            print("✗ " + b)
        print("公開檔乾淨" if not bad else f"共 {len(bad)} 個問題")
        return 1 if bad else 0
    if not a.post:
        ap.error("需要全文 JSON 路徑")
    src = Path(a.post).resolve()
    if ROOT in src.parents:
        print(f"✗ 全文檔 {src} 在 repo 裡面；請放到 repo 以外的地方（repo 是 public）。")
        return 2
    post = json.loads(src.read_text(encoding="utf-8"))
    try:
        entry = public_entry(post, a.topic or None)
    except ValueError as e:
        print("✗ " + str(e))
        return 2
    base = os.environ.get("ACCOUNT_API_URL", "").strip()
    token = (os.environ.get("ARTICLE_BOT_KEY") or os.environ.get("BACKUP_TOKEN") or "").strip()
    if not base or len(token) < 16:
        print("✗ 沒有 ACCOUNT_API_URL／ARTICLE_BOT_KEY：無法把全文傳到會員 Worker。\n"
              "  不要把全文推進 repo；把這個請求標成 failed（原因：沒有機器鑰匙），等 Andy 設好環境金鑰再做。")
        return 3
    if not a.index_only:
        r = aj.call(base, token, {"op": "put_body", "id": entry["id"], "json": {**post, "id": entry["id"]}})
        if not r.get("ok"):
            print(f"✗ 上傳全文失敗：{r.get('error')}")
            return 4
        print(f"✓ 全文已存入 Worker：{entry['id']}（{r.get('bytes')} 字元）")
    lst = aj.call(base, token, {"op": "list_bodies"})
    if not any(b.get("id") == entry["id"] and (b.get("bytes") or 0) > 50 for b in (lst.get("bodies") or [])):
        print("✗ Worker 的清單裡找不到這篇的全文；不寫索引（避免「標題上架、全文沒上」）。")
        return 4
    add_to_index(entry)
    bad = leaks()
    if bad:
        print("\n".join("✗ " + b for b in bad))
        return 5
    print(f"✓ 索引已加入 site/articles/index.json（僅標題）：{json.dumps(entry, ensure_ascii=False)}\n  下一步：git add site/articles/index.json → 推 main → deploy_wait → 標 done。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
