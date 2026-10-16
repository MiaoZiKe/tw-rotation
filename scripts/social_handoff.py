#!/usr/bin/env python3
"""社群交接工具：建立骨架、檢查、標成 ready_for_gpt（只動 docs/social_handoff/，不碰網站與素材）。

用法：
  python scripts/social_handoff.py new 2026-10-16 tsmc-q3-call "台積電法說會"
  python scripts/social_handoff.py check docs/social_handoff/2026-10-16_tsmc-q3-call
  python scripts/social_handoff.py ready docs/social_handoff/2026-10-16_tsmc-q3-call

規則見 docs/social_handoff/README.md。`ready` 會先 check，有任何錯誤就拒絕改狀態。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFF = ROOT / "docs" / "social_handoff"
TAIPEI = timezone(timedelta(hours=8))
SCHEMA_VERSION = 1
STATUSES = ["draft", "ready_for_gpt", "processing", "completed", "needs_revision", "failed"]
CATEGORIES = {"gpt_original", "claude_original", "claude_derived", "user_provided", "author_unverified"}
DEFAULT_OUTPUTS = [
    "IG 十頁 1080x1350",
    "IG 貼文說明",
    "Threads 文案",
    "來源表",
    "素材來源清單",
]
REQUIRED_KEYS = [
    "schema_version", "job_id", "revision", "status", "topic", "created_at", "updated_at",
    "brief_path", "sources_path", "style_guide_path", "requested_outputs", "asset_references",
]
BRIEF_SECTIONS = [
    "主題", "資料截止", "一句話核心觀點", "目標讀者", "必須保留的重點", "關鍵數據",
    "已確認事實", "作者分析", "財測／預估", "未確認資訊", "專有名詞", "供應鏈關係",
    "建議討論問題", "內容限制", "建議視覺主題", "比比如何引導",
]
ASSET_KEYS = ["path", "category", "original_author", "processed_by", "provenance_evidence", "parent_path"]


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def check(folder: Path) -> list[str]:
    """回傳錯誤清單；空清單代表可標 ready_for_gpt。"""
    errs: list[str] = []
    mpath = folder / "manifest.json"
    if not mpath.exists():
        return [f"缺 manifest.json：{mpath}"]
    try:
        m = json.loads(mpath.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"manifest.json 不是合法 JSON：{e}"]
    for k in REQUIRED_KEYS:
        if k not in m:
            errs.append(f"manifest 缺欄位 {k}")
    if m.get("status") not in STATUSES:
        errs.append(f"status 不合法：{m.get('status')}")
    for k in ("brief_path", "sources_path"):
        p = m.get(k)
        if p and not (ROOT / p).exists():
            errs.append(f"{k} 指向的檔案不存在：{p}")
    src = ROOT / m.get("sources_path", "") if m.get("sources_path") else folder / "sources.md"
    if src.exists():
        rows = [ln for ln in src.read_text(encoding="utf-8").splitlines()
                if re.match(r"^\|\s*\d+\s*\|", ln)]
        if not rows:
            errs.append("sources.md 沒有任何一筆來源（第一欄為編號的資料列）")
        for ln in rows:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) < 5 or not all(cells[:5]) or not re.search(r"https?://", ln):
                errs.append(f"sources.md 來源資料不完整（需標題／發布者／日期／連結）：{ln[:60]}")
    brief = ROOT / m.get("brief_path", "") if m.get("brief_path") else folder / "brief.md"
    if brief.exists():
        text = brief.read_text(encoding="utf-8")
        for sec in BRIEF_SECTIONS:
            if sec not in text:
                errs.append(f"brief.md 缺段落：{sec}")
        if re.search(r"待補|TODO|TBD|<填寫>", text):
            errs.append("brief.md 仍有「待補／TODO／TBD／<填寫>」")
    if m.get("style_guide_status") != "present":
        errs.append("視覺規範未就緒（style_guide_status != present）；缺 LIGULIGU_IG_Threads_Style_Guide.md")
    else:
        sg = m.get("style_guide_path")
        if not sg or not (ROOT / sg).exists():
            errs.append(f"style_guide_path 指向的檔案不存在：{sg}")
    for i, a in enumerate(m.get("asset_references", [])):
        for k in ASSET_KEYS:
            if k not in a:
                errs.append(f"asset_references[{i}] 缺 {k}")
        if a.get("category") not in CATEGORIES:
            errs.append(f"asset_references[{i}].category 不合法：{a.get('category')}")
        p = a.get("path")
        if p and not (ROOT / p).exists():
            errs.append(f"asset_references[{i}] 路徑不存在：{p}")
    return errs


def cmd_new(a: argparse.Namespace) -> int:
    folder = HANDOFF / f"{a.date}_{a.slug}"
    if folder.exists():
        print(f"已存在：{folder}", file=sys.stderr)
        return 1
    (folder / "assets").mkdir(parents=True)
    (folder / "assets" / ".gitkeep").write_text("", encoding="utf-8")
    rel = folder.relative_to(ROOT).as_posix()
    brief = "# 交接單｜" + a.topic + "\n\n" + "\n\n".join(f"## {s}\n（待補）" for s in BRIEF_SECTIONS) + "\n"
    (folder / "brief.md").write_text(brief, encoding="utf-8")
    (folder / "sources.md").write_text("# 來源表\n\n| # | 標題 | 發布者 | 發布日期 | 連結 | 與本篇相關的原文摘要 |\n|---|---|---|---|---|---|\n", encoding="utf-8")
    ts = now_iso()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "job_id": f"{a.date}_{a.slug}",
        "revision": 1,
        "status": "draft",
        "topic": a.topic,
        "data_cutoff": "",
        "created_at": ts,
        "updated_at": ts,
        "brief_path": f"{rel}/brief.md",
        "sources_path": f"{rel}/sources.md",
        "style_guide_path": "docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md",
        "style_guide_status": "missing",
        "requested_outputs": DEFAULT_OUTPUTS,
        "asset_references": [],
        "blocking_items": ["視覺規範檔未提供"],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已建立 {rel}")
    return 0


def cmd_check(a: argparse.Namespace) -> int:
    errs = check(Path(a.folder).resolve())
    if errs:
        print("檢查未通過：")
        for e in errs:
            print(" -", e)
        return 1
    print("檢查通過")
    return 0


def cmd_ready(a: argparse.Namespace) -> int:
    folder = Path(a.folder).resolve()
    errs = check(folder)
    if errs:
        print("不能標成 ready_for_gpt，原因：")
        for e in errs:
            print(" -", e)
        return 1
    mpath = folder / "manifest.json"
    m = json.loads(mpath.read_text(encoding="utf-8"))
    if m["status"] not in ("draft", "needs_revision"):
        print(f"目前狀態 {m['status']}，只有 draft／needs_revision 可改成 ready_for_gpt", file=sys.stderr)
        return 1
    if m["status"] == "needs_revision":
        m["revision"] += 1
    m["status"] = "ready_for_gpt"
    m["updated_at"] = now_iso()
    m.pop("blocking_items", None)
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("已改成 ready_for_gpt；接著請把 PR 設為 ready for review（這是給 GPT 的觸發訊號）")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("date")
    n.add_argument("slug")
    n.add_argument("topic")
    n.set_defaults(fn=cmd_new)
    c = sub.add_parser("check")
    c.add_argument("folder")
    c.set_defaults(fn=cmd_check)
    r = sub.add_parser("ready")
    r.add_argument("folder")
    r.set_defaults(fn=cmd_ready)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
