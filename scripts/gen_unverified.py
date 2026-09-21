"""把 obsidian/unverified.yaml 產成人看的 Markdown（和任務板同一個模式：單一資料來源）。"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "obsidian" / "unverified.yaml"
OUT = ROOT / "obsidian" / "120-未驗證清單.md"


def main() -> int:
    d = yaml.safe_load(SRC.read_text(encoding="utf-8")) or {}
    rows = d.get("pending") or []
    meta = d.get("meta") or {}
    L = ["# 還沒驗證的改動", "",
         f"> 產生自 `obsidian/unverified.yaml`，最後更新 {meta.get('updated', '—')}。**不要手改這個檔。**", ""]
    if not rows:
        L += ["## ✅ 目前沒有待驗證的東西", "",
              "所有改動都已經跑過該跑的驗收並推上 main。", ""]
    else:
        L += [f"## 累積 {len(rows)} 筆，等 Andy 說「驗證」", "",
              "| # | 改了什麼 | 我看過了嗎 | 驗證時要跑 |", "|---|---|---|---|"]
        for r in rows:
            ok = "✅ 說對了" if r.get("ok") is True else ("❌ 要改" if r.get("ok") is False else "⬜ 還沒回")
            shown = "（還沒截圖）" if not r.get("shown") else ok
            L.append(f"| {r.get('id', '?')} | {r.get('what', '')} | {shown} | {'、'.join(r.get('gates') or []) or '—'} |")
        L += ["", "### 各筆的細節", ""]
        for r in rows:
            L += [f"#### {r.get('id', '?')}　{r.get('what', '')}", "",
                  f"- 檔案：{'、'.join(f'`{f}`' for f in (r.get('files') or [])) or '—'}",
                  f"- 驗證時要跑：{'、'.join(r.get('gates') or []) or '—'}",
                  f"- 登記時間：{r.get('at', '—')}", ""]
        # 「驗證」時要跑的聯集 —— 直接可以貼進終端機
        secs, need_pytest, need_prev = [], False, False
        for r in rows:
            for g in (r.get("gates") or []):
                if g == "pytest":
                    need_pytest = True
                elif g == "preview":
                    need_prev = True
                elif g not in secs:
                    secs.append(g)
        L += ["### 他說「驗證」時要跑的（聯集）", "", "```bash"]
        if need_pytest:
            L.append("python -m pytest tests/ -q")
        if need_prev:
            L.append("python scripts/_preview.py")
        if secs:
            L.append('python scripts/_uitest.py --only "' + ",".join(secs) + '"')
        L += ["```", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"寫出 {OUT.relative_to(ROOT)}（{len(rows)} 筆待驗證）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
