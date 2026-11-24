#!/usr/bin/env python3
"""刪除頻道④ IG 重複貼文（Andy 2026-11-24：「好 刪掉 每組留最早那則」）。
只刪下方 TARGETS 列出的 permalink（取自 docs/marketing/channels/IG重複發文檢查.md 2026-11-24 10:27 報告，
每組保留最早一則）；不在清單的一律不碰。刪前再比一次文案指紋，確認是同組重複才刪。
"""
import json, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ig_reels_grid_list as L  # noqa: E402
import ig_dup_check as D  # noqa: E402

KEEP = {"DgB8zwzDX_Q", "DgEhqhuF5tM"}
TARGETS = {
    "DgB84mYDTOE", "DgB8-Z_jbRL", "DgB-k_mla1U", "DgB-pnIFxrl", "DgB-vN2l4hB", "DgCASYeDxRh", "DgCAXg4DwZe", "DgCAdrwD7FE",
    "DgEhu2YlyiQ", "DgEh0tzjXN4", "DgEjYXQIdfJ", "DgEjdEwoUSd", "DgEji9Koc6D", "DgElF4-iblf", "DgElK9hCVHC", "DgElQ9PCTpy",
    "DgFYnI3Fxv5", "DgFYryEF2WI", "DgFYxXYF_9l", "DgFaWk6l8A6", "DgFacM8l9XX",
}


def code(link: str) -> str:
    return link.rstrip("/").split("/")[-1]


def delete(url: str, tok: str) -> str:
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode({'access_token': tok})}", method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode()[:200]
    except urllib.error.HTTPError as e:
        raise RuntimeError(L.mask(f"HTTP {e.code} {e.read().decode(errors='ignore')[:300]}"))


def main() -> int:
    dry = "--dry-run" in sys.argv
    rows, err = D.recent("HEALING_", 10)
    if err:
        print("⚠️", err)
        return 1
    keep_keys = {D.key(m.get("caption", "")) for m in rows if code(m.get("permalink", "")) in KEEP}
    import os
    tok = (os.environ.get("HEALING_IG_DELETE_TOKEN") or "").strip() or L.tokens("HEALING_")[0]   # 一次性刪除用權杖（含 instagram_manage_contents）
    L.SECRETS.append(tok)
    host = L.FB_HOST if tok.startswith("EAA") else L.IG_HOST
    try:      # 刪除需要 instagram_manage_contents（11-24 第一次刪除回 #10 權限不足）→ 先印出權杖有哪些權限
        perms = L.fetch(f"{host}/me/permissions", {"access_token": tok}).get("data", [])
        print("權杖權限：" + "、".join(f"{x.get('permission')}={x.get('status')}" for x in perms))
    except Exception as e:  # noqa: BLE001
        print(f"查權杖權限失敗：{L.mask(str(e))[:200]}")
    ok = fail = 0
    for m in rows:
        c = code(m.get("permalink", ""))
        if c not in TARGETS:
            continue
        if D.key(m.get("caption", "")) not in keep_keys:
            print(f"跳過 {c}：文案跟保留那則對不上")
            continue
        if dry:
            print(f"（試跑）會刪 {c} {L.tw(m['timestamp'])}")
            continue
        try:
            print(f"刪除 {c} {L.tw(m['timestamp'])}：{delete(f'{host}/{m['id']}', tok)}")
            ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ 刪除 {c} 失敗：{L.mask(str(e))[:300]}")
            fail += 1
    print(f"結果：刪除 {ok} 則、失敗 {fail} 則（目標 {len(TARGETS)} 則）")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
