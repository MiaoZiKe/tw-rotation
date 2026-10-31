"""把預覽分支挑進 Cloudflare 預覽專案（tw-rotation-preview）的部署包 cf_prev/。

Cloudflare Pages 單次部署上限 20,000 檔；GitHub Pages 沒這個上限（所有 preview/* 都裝）。
預覽專案放不下全部時：依分支最新 commit 時間由新到舊挑，直到檔數達預算為止（舊預覽只留在備援網域）。
輸出：cf_prev/<名稱>/…、cf_prev/index.html（清單）、cf_prev_included.txt（每行 `名稱@sha前7碼`，deploy_wait 讀它確認）。
用法：python scripts/cf_preview_pack.py [--budget 18000]
"""
import argparse, html, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def count_files(d: Path) -> int:
    return sum(1 for f in d.rglob("*") if f.is_file())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=18000)
    a = ap.parse_args()
    out = ROOT / "cf_prev"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    mf = ROOT / "preview_manifest.json"
    items = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else []
    items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    used, inc, skipped = 1, [], []
    for it in items:
        src = ROOT / "site" / "preview" / it["name"]
        if not src.is_dir():
            continue
        n = count_files(src)
        if used + n > a.budget:
            skipped.append(it["name"])
            continue
        shutil.copytree(src, out / it["name"])
        used += n
        inc.append(it)
    rows = "".join(f'<li><a href="{html.escape(i["name"])}/">{html.escape(i["name"])}</a>（{i["sha"][:7]}）</li>' for i in inc)
    (out / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>預覽版清單</title>'
                                    f"<h1>預覽版清單</h1><ul>{rows}</ul>", encoding="utf-8")
    (ROOT / "cf_prev_included.txt").write_text("".join(f'{i["name"]}@{i["sha"][:7]}\n' for i in inc), encoding="utf-8")
    print(f"Cloudflare 預覽包：{len(inc)} 份、{used} 檔（預算 {a.budget}）；因檔數上限未放入（仍在備援網域）：{len(skipped)} 份 {' '.join(skipped)}")


if __name__ == "__main__":
    main()
