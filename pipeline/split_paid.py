"""把付費候選檔從 site/data 搬到 site_paid/（data-gw 第二階段，docs/datagw_plan.md）。

在 build_payload 之後、部署 Pages 之前跑。分級的唯一來源是 pipeline/datagw_tiers.json
（workers/data-gw/tiers.js 有一份同樣的表，workers/data-gw/tests/gw.test.mjs 會比對兩邊一致）。

- 付費候選（f 非空）→ 搬到 site_paid/<同樣的相對路徑>，之後由 pages.yml 上傳到 R2 私有 bucket。
  **site/data 裡不留任何一份**，否則公開網址照樣拿得到，等於沒擋。
- 免費檔留在 site/data（照舊走 CDN）。
- 寫 site/data/datagw_index.json：前端（site/datagw.js）據此判斷哪些檔要改走 gateway。只列規則，不列檔案內容。

只有 pages.yml 在 repo 變數 DATAGW_SPLIT=1 時才會呼叫；沒開時正式站完全不受影響。
用法：python -m pipeline.split_paid [--src site/data] [--dst site_paid]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIERS_FILE = Path(__file__).resolve().parent / "datagw_tiers.json"


def load_tiers() -> list[dict]:
    return json.loads(TIERS_FILE.read_text(encoding="utf-8"))["tiers"]


def tier_of(name: str, tiers: list[dict]) -> dict | None:
    for t in tiers:
        if ("p" in t and t["p"] == name) or ("re" in t and re.fullmatch(t["re"], name)):
            return t
    return None


def is_paid(name: str, tiers: list[dict]) -> bool:
    t = tier_of(name, tiers)
    return bool(t and t["f"])


def split(src: Path, dst: Path) -> dict:
    tiers = load_tiers()
    moved = kept = 0
    for f in sorted(src.rglob("*.json")):
        name = f.relative_to(src).with_suffix("").as_posix()
        if name == "datagw_index":
            continue
        if is_paid(name, tiers):
            out = dst / f.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(out))
            moved += 1
        else:
            kept += 1
    index = {"v": 1, "paid": [{k: t[k] for k in ("p", "re") if k in t} for t in tiers if t["f"]]}
    (src / "datagw_index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return {"moved": moved, "kept": kept}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "site" / "data"))
    ap.add_argument("--dst", default=str(ROOT / "site_paid"))
    a = ap.parse_args()
    r = split(Path(a.src), Path(a.dst))
    print(f"付費檔搬到 {a.dst}：{r['moved']} 支；留在公開目錄：{r['kept']} 支")


if __name__ == "__main__":
    main()
