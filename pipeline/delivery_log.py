"""交付清單：`docs/delivery_log.md` → `site/data/delivery.json`。

Andy 2026-09-23：「要用什麼方式可以讓你一次就知道我問的問題不會被遺忘，且如實完成」。

以前每一批的交付清單只寫在對話裡 —— **他沒有辦法驗證我列的是不是真的**。
他只重新整理網頁、不看 repo、不跑本機指令，所以清單要放到網站上他才驗得了。

★ 這支只做「搬運」，不做「詮釋」。
  `quote` 欄位是他的原話逐字照抄，解析過程**不准改寫、不准修正錯字、不准潤飾** ——
  改寫就等於把「他要什麼」換成「我以為他要什麼」，那正是這份清單要防的事。
  所以這裡只切欄位、不做任何字串正規化（除了去掉行首行尾空白與續行的縮排）。

Markdown 長這樣：

    ## 第 103 次部署（2026-09-23 12:30）

    1. quote：他的原話
       what：實際做了什麼
       state：done ｜ ver：103 ｜ go：#industry/ai_server
       note：我判斷過、他可能不同意的地方

續行（沒有 `欄位：` 開頭的縮排行）併回上一個欄位。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# 五種狀態，順序＝前端摘要列的顯示順序（等他決定的排最前面）
STATES = ("ask", "wip", "next", "done", "drop")

FIELDS = ("quote", "what", "state", "ver", "go", "note")

_H2 = re.compile(r"^##\s*第\s*(?P<n>\d+)\s*次部署\s*[（(]\s*(?P<at>[^）)]+?)\s*[）)]")
_ITEM = re.compile(r"^\s*(?P<n>\d+)\.\s*(?P<rest>.*)$")
# 全形冒號與半形都收；欄位名只認白名單，避免把內文裡的「note：」誤判成欄位
_FIELD = re.compile(r"^(?P<k>" + "|".join(FIELDS) + r")\s*[：:]\s*(?P<v>.*)$")
_SEP = re.compile(r"\s*[｜|]\s*")


def _split_fields(text: str) -> list[tuple[str, str]]:
    """把 `state：done ｜ ver：103 ｜ go：#flow` 這種一行多欄拆開。

    只有在「｜之後真的接著一個已知欄位名」時才切 —— 原話裡出現 ｜ 不該被當成分隔。
    """
    out: list[tuple[str, str]] = []
    for chunk in _SEP.split(text):
        m = _FIELD.match(chunk.strip())
        if m:
            out.append((m.group("k"), m.group("v").strip()))
        elif out:                       # ｜ 後面不是欄位名 → 還是上一個欄位的內容
            k, v = out[-1]
            out[-1] = (k, (v + " ｜ " + chunk.strip()).strip())
    return out


def parse(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    items: list[dict] = []
    deploys: list[dict] = []
    deploy_at: dict[str, str] = {}      # ver → 部署時間，給前端對照右上角版號徽章
    cur: dict | None = None
    last_key: str | None = None

    def flush() -> None:
        nonlocal cur, last_key
        if cur:
            items.append(cur)
        cur, last_key = None, None

    for raw in lines:
        line = raw.rstrip()
        h = _H2.match(line)
        if h:
            flush()
            ver, at = h.group("n"), h.group("at").strip()
            deploy_at[ver] = at
            deploys.append({"ver": ver, "at": at})
            continue
        if line.startswith("## "):      # 例如「## 還沒結束的」：沒有部署編號
            flush()
            continue
        it = _ITEM.match(line)
        if it:
            flush()
            cur = {"n": int(it.group("n"))}
            for k, v in _split_fields(it.group("rest")):
                cur[k] = v
                last_key = k
            continue
        if cur is None:
            continue
        body = line.strip()
        if not body or body.startswith("---"):
            continue
        pairs = _split_fields(body)
        if pairs:
            for k, v in pairs:
                cur[k] = v
                last_key = k
        elif last_key:
            # 續行：中文斷行不該補空白（會在句子中間多出一格），直接接上去
            cur[last_key] = (cur[last_key] + body).strip()
    flush()

    out = []
    for it in items:
        state = (it.get("state") or "").strip()
        if state not in STATES:
            state = "wip"               # 寧可標成「進行中」也不要憑空判成已完成
        go = (it.get("go") or "").strip()
        out.append({
            "n": it["n"],
            "quote": it.get("quote", ""),
            "what": it.get("what", ""),
            "state": state,
            "ver": it.get("ver", ""),
            "at": deploy_at.get(it.get("ver", ""), ""),
            # 只有真的是 hash 路由才給連結；「（流程，不在畫面上）」那種留字串給前端顯示
            "go": go if go.startswith("#") else "",
            "go_text": "" if go.startswith("#") else go,
            "note": it.get("note", ""),
        })

    counts = {s: sum(1 for x in out if x["state"] == s) for s in STATES}
    return {
        "meta": {"source": "docs/delivery_log.md", "total": len(out), "counts": counts,
                 "latest_deploy": deploys[-1] if deploys else None},
        "deploys": deploys,
        "items": out,
    }


def build(root: Path) -> dict:
    """給 build_payload 用。檔案不在（乾淨 checkout）就回空的，讓前端顯示提示而不是空白。"""
    src = root / "docs" / "delivery_log.md"
    if not src.exists():
        return {}
    try:
        return parse(src)
    except Exception:                   # noqa: BLE001 —— 一份 md 不該讓整條管線死掉
        return {}


if __name__ == "__main__":              # 本機單獨跑：python -m pipeline.delivery_log
    root = Path(__file__).resolve().parents[1]
    data = build(root)
    dest = root / "site" / "data" / "delivery.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"{dest} ← {data.get('meta', {}).get('total', 0)} 筆 {data.get('meta', {}).get('counts')}")
