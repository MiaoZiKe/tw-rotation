"""發文包資料：把 docs/marketing/channels/<頻道>/queue/<資料夾>/ 的文案、狀態、影片封面整理成 site/articles/<頻道>/postkit.json。
給獨立閱讀站（site/c/<頻道>/）的「發文包」區用，介面上只有站主看得到（Andy 11/17：「影片放在網路上可以下載、有文案，我可以直接下載下來發布」）。
⚠ 這是靜態檔，知道網址的人讀得到原始 JSON；介面隱藏不等於加密。內容本來就是要公開發出去的貼文，所以只放文案與狀態，不放金鑰、持股或個資。
用法：python scripts/postkit_build.py   （有新排程、改狀態後重跑，再推）"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHS = ("caffaine", "healing")
ST = {"posted": "已發", "approved": "已排程", "scheduled": "已排程"}


def main() -> int:
    for ch in CHS:
        qd = ROOT / "docs/marketing/channels" / ch / "queue"
        idx = json.loads((ROOT / f"site/articles/{ch}/index.json").read_text(encoding="utf-8"))
        arts = [a["id"] for a in idx.get("articles", [])]
        kits = []
        for d in sorted(qd.iterdir()) if qd.is_dir() else []:
            mp, cp = d / "meta.json", d / "caption.txt"
            if not mp.exists():
                continue
            m = json.loads(mp.read_text(encoding="utf-8"))
            mm = re.match(r"^(\d{4})(\d{2})(\d{2})(v?)_(.+)$", d.name)
            slug = mm.group(5) if mm else d.name
            day = f"{mm.group(1)}-{mm.group(2)}-{mm.group(3)}" if mm else ""
            cand = [a for a in arts if a.endswith("-" + slug)]
            art = next((a for a in cand if a.startswith(day)), cand[0] if cand else "")
            cap = cp.read_text(encoding="utf-8").strip() if cp.exists() else ""
            med = ROOT / "site/media" / ch / d.name
            files = [{"label": "影片下載" if n == "video.mp4" else "封面圖下載", "url": f"media/{ch}/{d.name}/{n}"} for n in ("video.mp4", "cover.jpg") if (med / n).exists()]
            kits.append({"key": d.name, "article": art, "title": m.get("title") or (cap.splitlines()[0] if cap else d.name),
                         "status": ST.get(m.get("status"), "存貨"), "publish_at": m.get("publish_at") or "", "video": bool(m.get("format") == "video" or (med / "video.mp4").exists()),
                         "caption": cap, "files": files})
        out = ROOT / f"site/articles/{ch}/postkit.json"
        out.write_text(json.dumps({"kits": kits}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{ch}: {len(kits)} 組 → {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
