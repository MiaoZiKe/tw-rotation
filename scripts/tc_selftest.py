"""頻道②「科技透明圈」自動測試發文（2026-11-08）。

Andy 原話：「我希望可以自動化全部，包含測試發文、還有自動刪文……」。
收件（tc_token_intake）成功後自動跑一次，也可以手動跑：.github/workflows/tc_selftest.yml

Threads（真的發，馬上刪）：
  1. 先查刪除額度（/me/threads_publishing_limit 的 delete_quota_usage）—— 查不到＝權杖沒有 threads_delete，
     **不發測試文**（發了刪不掉會留在帳號上）。
  2. 查 /me/replies（驗 threads_read_replies）。
  3. 發一則純文字測試文 → 用 /me/threads 讀回確認看得到 → DELETE → 再 GET 一次確認已刪。
IG（不發）：Instagram 登入版 API 不能刪貼文，所以只建 media container（上傳圖、建容器、等 status_code=FINISHED），
  **不呼叫 media_publish**，外面看不到。另外查 content_publishing_limit、/me/conversations（驗 instagram_business_manage_messages）、
  最近一篇貼文的留言（驗 instagram_business_manage_comments；帳號還沒有貼文就記「無貼文可測」，不算失敗）。
結果：data/_state/tc_selftest.json（日期、每一項成功與否、username；沒有權杖、沒有 id）。任何一項失敗 → 結束碼 1，工作流開 issue。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tc_post as T  # noqa: E402

STATE_PATH = ROOT / "data" / "_state" / "tc_selftest.json"
TEST_IMAGE = "social/tc/selftest.jpg"
TEST_TEXT = "（科技透明圈 系統自動測試，這則會在幾秒內自動刪除）"


def threads_checks(tok: str, ch1: str, expect: str) -> list[dict]:
    out = []

    def step(name, fn):
        try:
            v = fn()
            out.append({"check": name, "ok": True, **({"note": v} if isinstance(v, str) else {})})
            return True
        except T.PostError as e:
            out.append({"check": name, "ok": False, "error": T.redact(e)[:200]})
            return False

    uid = {}
    if not step("Threads 帳號（/me）", lambda: uid.update(zip(("id", "name"), T.preflight("threads", tok, expect, ch1))) or f"@{uid['name']}"):
        return out
    step("threads_read_replies（/me/replies）", lambda: T.api("threads", "GET", "/me/replies", tok, {"fields": "id", "limit": "1"}) and None)
    if not step("threads_delete（刪除額度）", lambda: _need(T.api("threads", "GET", "/me/threads_publishing_limit", tok,
                                                            {"fields": "quota_usage,delete_quota_usage,delete_config"}), "delete_quota_usage")):
        out.append({"check": "測試發文", "ok": False, "error": "沒有刪除權限，為了不留測試文在帳號上，這次不發"})
        return out
    mid = {}

    def publish():
        cid = T.api("threads", "POST", f"/{uid['id']}/threads", tok, {"media_type": "TEXT", "text": TEST_TEXT})["id"]
        T.SLEEP(5)
        mid["id"] = T._threads_publish(uid["id"], cid, tok)
    if not step("threads_content_publish（發測試文）", publish):
        return out

    def readback():
        rows = T.api("threads", "GET", "/me/threads", tok, {"fields": "id", "limit": "5"}).get("data") or []
        if not any(str(r.get("id")) == mid["id"] for r in rows):
            raise T.PostError("/me/threads 讀不到剛發的測試文")
    step("讀回確認發出", readback)

    def delete():
        T.api("threads", "DELETE", f"/{mid['id']}", tok)
        try:
            T.api("threads", "GET", f"/{mid['id']}", tok, {"fields": "id"})
        except T.PostError:
            return None
        raise T.PostError("刪除後回查仍然存在，請手動刪掉測試文")
    step("刪除測試文並回查", delete)
    return out


def _need(d: dict, key: str):
    rows = d.get("data") or [d]
    if not any(key in r for r in rows):
        raise T.PostError(f"回應沒有 {key}（多半是權杖沒有對應權限）")
    return None


def ig_checks(tok: str, ch1: str, expect: str) -> list[dict]:
    out = []

    def step(name, fn):
        try:
            v = fn()
            out.append({"check": name, "ok": True, **({"note": v} if isinstance(v, str) else {})})
            return True
        except T.PostError as e:
            out.append({"check": name, "ok": False, "error": T.redact(e)[:200]})
            return False

    uid = {}
    if not step("IG 帳號（/me）", lambda: uid.update(zip(("id", "name"), T.preflight("ig", tok, expect, ch1))) or f"@{uid['name']}"):
        return out
    step("instagram_business_content_publish（發文額度）",
         lambda: T.api("ig", "GET", f"/{uid['id']}/content_publishing_limit", tok, {"fields": "quota_usage"}) and None)

    def container():
        url = T.RAW + urllib.parse.quote(TEST_IMAGE)
        T.check_public(url)
        cid = T.api("ig", "POST", f"/{uid['id']}/media", tok, {"image_url": url, "caption": "selftest"})["id"]
        T._wait_ig(cid, tok)
        return "容器 FINISHED，沒有呼叫 media_publish（外面看不到）"
    step("上傳圖並建容器（不發布）", container)
    step("instagram_business_manage_messages（/me/conversations）",
         lambda: T.api("ig", "GET", "/me/conversations", tok, {"platform": "instagram", "fields": "id", "limit": "1"}) and None)

    def comments():
        rows = T.api("ig", "GET", "/me/media", tok, {"fields": "id", "limit": "1"}).get("data") or []
        if not rows:
            return "帳號還沒有貼文，留言權限等第一篇發出後再測"
        T.api("ig", "GET", f"/{rows[0]['id']}/comments", tok, {"fields": "id", "limit": "1"})
        return None
    step("instagram_business_manage_comments（讀留言）", comments)
    return out


def run(env: dict, now: datetime, state_path: Path = STATE_PATH) -> tuple[int, dict]:
    tok = T.tokens_from(env)
    for k in ("TC_THREADS_USER_ID", "TC_IG_USER_ID", "THREADS_USER_ID", "IG_USER_ID"):
        T.mask((env.get(k) or "").strip())
    st = {"updated_at": now.astimezone(T.TAIPEI).strftime("%Y-%m-%d %H:%M"), "platforms": {}}
    if not tok["threads"] and not tok["ig"]:
        T.log("沒有 TC 權杖，測試跳過（請先跑 tc_token_intake）")
        return 0, st
    for plat, fn in (("threads", threads_checks), ("ig", ig_checks)):
        if not tok[plat]:
            st["platforms"][plat] = {"ok": False, "checks": [{"check": "權杖", "ok": False, "error": "沒有 TC 權杖"}]}
            continue
        checks = fn(tok[plat], (env.get("THREADS_USER_ID" if plat == "threads" else "IG_USER_ID") or "").strip(),
                    (env.get(f"TC_{plat.upper()}_USER_ID") or "").strip())
        st["platforms"][plat] = {"ok": all(c["ok"] for c in checks), "checks": checks}
        for c in checks:
            T.log(f"[{plat}] {'✓' if c['ok'] else '✗'} {c['check']}" + (f"：{c.get('error') or c.get('note')}" if (c.get('error') or c.get('note')) else ""))
    st["ok"] = all(v["ok"] for v in st["platforms"].values())
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(T.redact(json.dumps(st, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8")
    return (0 if st["ok"] else 1), st


def main() -> int:
    rc, st = run(dict(os.environ), datetime.now(timezone.utc))
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        bad = [f"{p}：{c['check']}（{c.get('error', '')}）" for p, v in st["platforms"].items() for c in v["checks"] if not c["ok"]]
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"failed={'1' if rc else '0'}\n")
            f.write("reasons=" + T.redact("；".join(bad)).replace("\n", " ") + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
