#!/usr/bin/env python3
"""IG 舊 Reels 格狀版面移除清單（Andy 2026-11-20）。
API 無法把已發佈的 Reels 從主格狀版面移除，所以列出每個帳號的 REELS，讓 Andy 在手機逐支按「⋯ → 從個人檔案格狀版面移除」。
只讀（GET /me/media 或 /{ig-user-id}/media），不發文、不改任何貼文。權杖讀不到就跳過並註明原因。
輸出：docs/marketing/channels/Reels格狀版面移除清單.md
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/marketing/channels/Reels格狀版面移除清單.md"
IG_HOST, FB_HOST = "https://graph.instagram.com/v21.0", "https://graph.facebook.com/v21.0"
FIELDS = "id,media_product_type,permalink,timestamp,caption"
# (顯示名稱, 環境變數前綴)；前綴空字串＝頻道①
ACCOUNTS = [("①哩股哩股", ""), ("②科技透明圈", "TECH_"), ("③CaffAIne", "CAFFAINE_"), ("④談晴說礙", "HEALING_")]
TW = timezone(timedelta(hours=8))
SECRETS: list[str] = []


def mask(s: str) -> str:
    for t in SECRETS:
        if t:
            s = s.replace(t, "***")
    return s


def get(url: str, params: dict) -> dict:
    q = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{q}" if "?" not in url else url, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch(url: str, params: dict) -> dict:
    try:
        return get(url, params)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")[:300]
        raise RuntimeError(mask(f"HTTP {e.code} {body}"))


def tokens(pfx: str) -> list[str]:
    out = []
    for k in (f"{pfx}IG_ACCESS_TOKEN_AUTO", f"{pfx}IG_ACCESS_TOKEN"):
        v = (os.environ.get(k) or "").strip()
        if v and v not in out:
            out.append(v)
    return out


def media_base(pfx: str, tok: str) -> str:
    if not tok.startswith("EAA"):
        return f"{IG_HOST}/me/media"
    uid = (os.environ.get(f"{pfx}IG_USER_ID") or "").strip()
    if not uid:
        # 跟發文同一套探查（healing_post.resolve_uid：系統用戶權杖的多路徑找 IG 編號、依 channels.json 帳號名挑）
        sys.path.insert(0, str(ROOT / "scripts"))
        import healing_post as HP  # noqa: E402
        uid = HP.resolve_uid("ig", "", tok, pfx or None)
    if not uid:
        raise RuntimeError("EAA 權杖找不到本帳號的 IG 編號（發文用的同一套探查也找不到）")
    return f"{FB_HOST}/{uid}/media"


def list_reels(pfx: str) -> tuple[list[dict], int, str]:
    toks = tokens(pfx)
    if not toks:
        return [], 0, "沒有設定這個帳號的 IG 權杖"
    errs = []
    for tok in toks:
        SECRETS.append(tok)
        try:
            base = media_base(pfx, tok)
            rows, total = [], 0
            d = fetch(base, {"fields": FIELDS, "limit": 100, "access_token": tok})
            while True:
                for m in d.get("data", []):
                    total += 1
                    if m.get("media_product_type") == "REELS":
                        rows.append(m)
                nxt = (d.get("paging") or {}).get("next")
                if not nxt:
                    break
                d = fetch(nxt, {})
            return rows, total, ""
        except Exception as e:  # noqa: BLE001
            errs.append(mask(str(e))[:200])
    return [], 0, "權杖無法讀取貼文：" + "；".join(errs)


def tw(ts: str) -> str:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(TW).strftime("%Y-%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        return ts or ""


def head30(s: str) -> str:
    s = " ".join((s or "").split())
    return (s[:30] + "…") if len(s) > 30 else (s or "（無說明文字）")


def main() -> int:
    now = datetime.now(TW).strftime("%Y-%m-%d %H:%M")
    lines = ["# Reels 格狀版面移除清單", "",
             f"> 產生時間：{now}（台北）。Andy 2026-11-20：Reels 只放 Reels 分頁，不進主格狀版面。",
             "> 新發的 Reels 已自動帶 `share_to_feed=false`；下面是**已經發出、還在格狀版面**的舊 Reels，API 無法移除，",
             "> 請在手機逐支點進去 →「⋯」→「從個人檔案格狀版面移除」（英文介面：**Remove from profile grid**），做完打勾。", ""]
    summary = []
    for name, pfx in ACCOUNTS:
        rows, total, err = list_reels(pfx)
        lines.append(f"## {name}")
        lines.append("")
        if err:
            lines += [f"⚠️ 跳過：{err}", ""]
            summary.append(f"{name}：跳過（{err[:60]}）")
            continue
        rows.sort(key=lambda m: m.get("timestamp") or "", reverse=True)
        lines.append(f"共 {len(rows)} 支 Reels（帳號全部貼文 {total} 則）")
        lines.append("")
        for m in rows:
            lines.append(f"- [ ] {tw(m.get('timestamp'))}｜{head30(m.get('caption'))}｜{m.get('permalink', '')}")
        lines.append("")
        summary.append(f"{name}：{len(rows)} 支")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
