"""從 `obsidian/tasks.yaml` 產出 `obsidian/100-任務板.md`。

為什麼要這一支（2026-09-20）
----------------------------
Andy 選了「在網站上多一頁任務板」，所以同一份資料要出現在兩個地方：
網站的 `#tasks` 頁（走 `site/data/tasks.json`）與 Obsidian 的 Markdown。
兩邊各維護一份，第三天就會對不起來 —— 所以 `obsidian/tasks.yaml` 是唯一的來源，
這一支只負責把它轉成人看的 Markdown。

**不要手改 `100-任務板.md`**，改了下次跑這支就會被蓋掉。要改就改 YAML。

用法：`python3 scripts/gen_taskboard.py`
"""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "obsidian" / "tasks.yaml"
OUT = ROOT / "obsidian" / "100-任務板.md"

# status → (符號, 中文, 排序權重)。權重決定表格裡誰排前面：還沒好的排前面。
STATUS = {
    "blocked": ("⛔", "被擋住", 0),
    "doing":   ("🔵", "進行中", 1),
    "review":  ("🟡", "改完待驗／待推", 2),
    "todo":    ("⬜", "未開始", 3),
    "done":    ("✅", "已上線", 4),
}


def _cell(s) -> str:
    """把多行文字壓成一格能放的樣子（表格裡不能有裸換行）。"""
    return " ".join(str(s or "").split()).replace("|", "\\|")


def _shot(name: str | None) -> str:
    return f"[[attachments/{name}\\|截圖]]" if name else "—"


def build(d: dict) -> str:
    meta = d.get("meta") or {}
    L: list[str] = []
    L.append("# 任務板")
    L.append("")
    L.append("> ⚠ **這個檔是產生出來的，不要手改。**")
    L.append("> 要改請改 `obsidian/tasks.yaml`，再跑 `python3 scripts/gen_taskboard.py`。")
    L.append(">")
    L.append("> **這是唯一的權威狀態。** 對話裡的「做完了」會被下一則訊息沖掉，這一份不會。")
    L.append("> 狀態只准五種：⬜ 未開始｜🔵 進行中｜🟡 改完待驗／待推｜✅ 已上線｜⛔ 被擋住")
    L.append("> **「改完但還沒 push」一律是 🟡，不准標 ✅。**")
    L.append("")
    L.append(f"最後更新：{meta.get('updated', '—')}　｜　網址：{meta.get('site', '')}")
    L.append("")

    if d.get("blocked_on_andy"):
        L.append("## 🔴 要 Andy 動手的（只有你能做）")
        L.append("")
        L.append("| # | 事情 | 為什麼卡著 | 怎麼做 |")
        L.append("|---|---|---|---|")
        for t in d["blocked_on_andy"]:
            L.append(f"| **{t['id']}** | {_cell(t['title'])} | {_cell(t.get('note'))} | {_cell(t.get('ask'))} |")
        L.append("")

    if d.get("questions"):
        L.append("## ⬜ 待你回答（回答之前我不動，免得做錯方向）")
        L.append("")
        L.append("| # | 問題 | 我的預設做法 |")
        L.append("|---|---|---|")
        for q in d["questions"]:
            L.append(f"| **{q['id']}** | {_cell(q['title'])} | {_cell(q.get('note'))} |")
        L.append("")

    rows = sorted(d.get("tasks") or [], key=lambda t: (STATUS.get(t.get("status"), ("", "", 9))[2], t["id"]))
    for key in ("blocked", "doing", "review", "todo", "done"):
        group = [t for t in rows if t.get("status") == key]
        if not group:
            continue
        sym, label, _ = STATUS[key]
        L.append(f"## {sym} {label}")
        L.append("")
        L.append("| # | 需求（Andy 的原話） | 檔案 | 花了多久 | 說明 | 截圖 |")
        L.append("|---|---|---|---|---|---|")
        for t in group:
            L.append(f"| **{t['id']}** | {_cell(t['title'])} | {_cell(', '.join(t.get('files') or []) or '—')} "
                     f"| {_cell(t.get('spent') or '—')} | {_cell(t.get('note'))} | {_shot(t.get('shot'))} |")
        L.append("")

    if d.get("backlog"):
        L.append("## 📋 還沒排到")
        L.append("")
        L.append("| # | 項目 | 說明 |")
        L.append("|---|---|---|")
        for t in d["backlog"]:
            L.append(f"| {t['id']} | {_cell(t['title'])} | {_cell(t.get('note'))} |")
        L.append("")

    L.append("---")
    L.append("")
    L.append("時間花在哪、為什麼慢、怎麼改，見 [[110-效率改善]]。")
    L.append("")
    return "\n".join(L)


def main() -> int:
    if not SRC.exists():
        print(f"找不到 {SRC}", file=sys.stderr)
        return 1
    d = yaml.safe_load(SRC.read_text(encoding="utf-8")) or {}
    OUT.write_text(build(d), encoding="utf-8")
    n = len(d.get("tasks") or [])
    print(f"寫出 {OUT.relative_to(ROOT)}（{n} 件任務）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
