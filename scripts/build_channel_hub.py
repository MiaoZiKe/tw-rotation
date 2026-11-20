"""產生 site/hub/works.json —— 「頻道作品」專區（#hub）的資料。

Andy 2026-11-20：「各頻道影片 文案 資訊可以下載，及觀看」。
資料來源（不手寫）：site/articles/<頻道>/*.json 裡有 {"t":"mp4"} 區塊的文章 ＝ 一則作品；
文案優先取 docs/marketing/channels/<頻道>/queue/<資料夾>/caption.txt（就是實際貼出去的字），
沒有就取文章裡「文案全文／念稿全文」那一段，再沒有就用標題＋摘要＋標籤組一份（caption_src 標明，介面會寫「由摘要整理」）。
影片檔不複製、不改，只記路徑與大小；下載權限由前端功能鍵管，這裡只是目錄。

用法：python scripts/build_channel_hub.py        （重寫 site/hub/works.json）
      python scripts/build_channel_hub.py --check（對不上就回 1，給 precheck 用）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = SITE / "hub" / "works.json"
CH = [  # 順序＝分頁順序（Andy 編號 ①②③④）
    ("ligu", "① 哩股哩股", "哩股"),
    ("tech", "② 科技透明圈", "透明圈"),
    ("caffaine", "③ CaffAIne", "CaffAIne"),
    ("healing", "④ 談晴說礙", "談晴"),
]
SITE_URL = "https://liguligu-puipui.com/"


def _caption(ch: str, folder: str, art: dict) -> tuple[str, str]:
    q = ROOT / "docs" / "marketing" / "channels" / ch / "queue" / folder / "caption.txt"
    if q.is_file():
        t = q.read_text("utf-8").strip()
        if t:
            return t, "queue"
    # 文章裡「文案全文／念稿全文」到下一個標題之前的段落
    paras, on = [], False
    for b in art.get("blocks", []):
        if b.get("t") == "h":
            on = b.get("text", "") in ("文案全文", "念稿全文")
            continue
        if on and b.get("t") == "p":
            paras.append(b.get("text", ""))
    if paras:
        return "\n\n".join(paras).strip(), "article"
    tags = " ".join("#" + re.sub(r"\s+", "", t) for t in art.get("tags", [])[:5])
    return "\n\n".join(x for x in [art.get("title", ""), art.get("summary", ""), tags] if x).strip(), "summary"


def build() -> dict:
    works = []
    for ch, name, short in CH:
        for p in sorted((SITE / "articles" / ch).glob("*.json")):
            if p.name == "index.json":
                continue
            a = json.loads(p.read_text("utf-8"))
            mp = next((b for b in a.get("blocks", []) if b.get("t") == "mp4"), None)
            if not mp:
                continue
            f = SITE / mp["src"]
            if not f.is_file():
                continue  # 檔案不在就不列（避免播不出來的死卡）
            folder = Path(mp["src"]).parent.name
            cap, cs = _caption(ch, folder, a)
            soc = a.get("social") or {}
            works.append({
                "id": a["id"], "ch": ch, "title": a["title"], "date": a.get("date", ""),
                "summary": a.get("summary", ""), "tags": a.get("tags", [])[:6],
                "video": mp["src"], "poster": mp.get("poster", ""), "mb": round(f.stat().st_size / 1048576, 1),
                "caption": cap, "caption_src": cs,
                "ig": soc.get("ig", ""), "threads": soc.get("threads", ""),
            })
    works.sort(key=lambda w: (w["date"], w["id"]), reverse=True)
    return {"channels": [{"id": c, "name": n, "short": s, "n": sum(1 for w in works if w["ch"] == c)} for c, n, s in CH],
            "site": SITE_URL, "works": works}


def main() -> int:
    data = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        return 0 if OUT.is_file() and OUT.read_text("utf-8") == data else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(data, "utf-8")
    d = json.loads(data)
    print("寫入", OUT.relative_to(ROOT), "；各頻道：", {c["name"]: c["n"] for c in d["channels"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
