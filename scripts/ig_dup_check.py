#!/usr/bin/env python3
"""IG 重複發文檢查（Andy 2026-11-24：「IG有嚴重重複發文問題幫我檢查並處理 避免發生」）。
只讀：列四個帳號最近 N 天的 IG 貼文，把「文案開頭相同」的歸成一組，同組 >1 則＝重複發文。
輸出 docs/marketing/channels/IG重複發文檢查.md（不刪任何貼文；刪除要 Andy 決定）。
用法：python scripts/ig_dup_check.py [--days 10]
"""
import argparse, re, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ig_reels_grid_list as L  # noqa: E402  共用權杖、帳號清單、遮蔽

OUT = L.ROOT / "docs/marketing/channels/IG重複發文檢查.md"
FIELDS = "id,media_type,media_product_type,permalink,timestamp,caption"


def key(caption: str) -> str:
    """文案正規化後取前 40 字當指紋（去空白、標點、hashtag）。"""
    s = re.sub(r"#\S+", "", caption or "")
    s = re.sub(r"[\s　，。、！？：；「」『』（）()…・\-—|｜,.!?:;\"']", "", s)
    return s[:40]


def recent(pfx: str, days: int) -> tuple[list[dict], str]:
    toks = L.tokens(pfx)
    if not toks:
        return [], "沒有設定這個帳號的 IG 權杖"
    since = datetime.now(timezone.utc) - timedelta(days=days)
    errs = []
    for tok in toks:
        L.SECRETS.append(tok)
        try:
            base = L.media_base(pfx, tok)
            rows = []
            d = L.fetch(base, {"fields": FIELDS, "limit": 50, "access_token": tok})
            while True:
                stop = False
                for m in d.get("data", []):
                    ts = datetime.strptime(m["timestamp"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    if ts < since:
                        stop = True
                        break
                    rows.append(m)
                nxt = (d.get("paging") or {}).get("next")
                if stop or not nxt:
                    return rows, ""
                d = L.fetch(nxt, {})
        except Exception as e:  # noqa: BLE001
            errs.append(L.mask(str(e))[:200])
    return [], "權杖無法讀取貼文：" + "；".join(errs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=10)
    a = ap.parse_args()
    now = datetime.now(L.TW).strftime("%Y-%m-%d %H:%M")
    lines = [f"# IG 重複發文檢查（{now} 台北，最近 {a.days} 天）", "",
             "只讀檢查；同一段文案開頭出現 2 次以上＝重複。刪除與否由 Andy 決定（刪除在 IG App：貼文右上「⋯」→「刪除」）。", ""]
    total_dup = 0
    for name, pfx in L.ACCOUNTS:
        rows, err = recent(pfx, a.days)
        lines.append(f"## {name}")
        if err:
            lines += [f"⚠️ {err}", ""]
            print(f"{name}：{err}")
            continue
        g = defaultdict(list)
        for m in rows:
            g[key(m.get("caption", ""))].append(m)
        dups = {k: v for k, v in g.items() if k and len(v) > 1}
        n = sum(len(v) - 1 for v in dups.values())
        total_dup += n
        lines.append(f"最近 {a.days} 天共 {len(rows)} 則，重複 {len(dups)} 組、多出 {n} 則。")
        print(f"{name}：{len(rows)} 則，重複 {len(dups)} 組、多出 {n} 則")
        for k, v in sorted(dups.items(), key=lambda kv: kv[1][-1]["timestamp"]):
            v = sorted(v, key=lambda m: m["timestamp"])
            lines += ["", f"### 「{k[:24]}…」共 {len(v)} 則（保留最早一則，其餘是重複）", "",
                      "| # | 發布時間（台北） | 類型 | 連結 |", "|---|---|---|---|"]
            for i, m in enumerate(v, 1):
                lines.append(f"| {i}{'（保留）' if i == 1 else ''} | {L.tw(m['timestamp'])} | "
                             f"{m.get('media_product_type') or m.get('media_type')} | {m.get('permalink', '')} |")
        lines.append("")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"合計多出 {total_dup} 則；報告 {OUT.relative_to(L.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
