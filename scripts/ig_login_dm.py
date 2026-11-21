"""留言關鍵字 → 公開回「已經將XXX完整資訊給你囉～」→ Private Reply 私訊連結（Instagram 登入版 IGAA 權杖，2026-11-17）。

Andy 要的流程：有人在 IG 貼文下留言關鍵字 → 帳號公開回一句 → 對留言者私訊連結。各頻道共用。
官方依據（graph.instagram.com，不需要粉絲專頁）：
  · 私訊：POST /{ig-user-id}/messages，body {recipient:{comment_id}, message:{text}}，權限 instagram_business_manage_messages
  · 公開回覆：POST /{comment-id}/replies?message=…，權限 instagram_business_manage_comments
  · 限制：留言後 7 天內；每則留言只能私訊 1 次；之後要對方先回才能再傳（24 小時內）。
順序（避免說了「已私訊」卻沒送到）：先私訊 → 成功才公開回「已經將XXX完整資訊給你囉～」；私訊失敗 → 退回公開回覆貼連結。
★ 預設關閉：呼叫端要明確傳 enabled=True 且 dry_run=False 才會真的送；本檔沒有被任何 workflow 呼叫。
不印權杖；不存留言內容。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

IG = "https://graph.instagram.com/v24.0"
WINDOW = timedelta(days=7)


def _post(url: str, token: str, params: dict | None = None, body: dict | None = None) -> dict:
    q = dict(params or {})
    q["access_token"] = token
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(q), data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except Exception:
            err = {}
        raise RuntimeError(f"HTTP {e.code} code={err.get('code')} sub={err.get('error_subcode')} {str(err.get('message'))[:160]}") from None


def in_window(comment_ts: str, now: datetime | None = None) -> bool:
    try:
        t = datetime.strptime(comment_ts.replace("+0000", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return True          # 讀不到時間就讓 Meta 判斷
    return (now or datetime.now(timezone.utc)) - t <= WINDOW


def handle_comment(token: str, uid: str, comment_id: str, comment_ts: str, *, dm_text: str, ack_text: str,
                   fallback_text: str, enabled: bool = False, dry_run: bool = True, info: dict | None = None) -> str:
    """info（選填）：呼叫端傳入 dict，失敗原因（已截短、不含權杖）寫進 info["dm_error"]／info["public_error"]，供寫進 state 紀錄。
    回傳結果代號：skipped_disabled／skipped_old／dry_run／dm_ok／dm_ok_ack_failed／fallback_public／failed。"""
    if not enabled:
        return "skipped_disabled"
    if not in_window(comment_ts):
        return "skipped_old"
    if dry_run:
        print(f"[dry_run] 會私訊（{len(dm_text)} 字）並公開回「{ack_text}」；私訊失敗則公開貼連結")
        return "dry_run"
    try:
        _post(f"{IG}/{uid}/messages", token, body={"recipient": {"comment_id": comment_id}, "message": {"text": dm_text}})
    except Exception as e:  # noqa: BLE001
        print("[dm] 私訊失敗，退回公開貼連結：", str(e)[:200])
        if info is not None:
            info["dm_error"] = str(e)[:120]
        try:
            _post(f"{IG}/{comment_id}/replies", token, params={"message": fallback_text})
            return "fallback_public"
        except Exception as e2:  # noqa: BLE001
            print("[reply] 公開回覆也失敗：", str(e2)[:200])
            if info is not None:
                info["public_error"] = str(e2)[:120]
            return "failed"
    try:
        _post(f"{IG}/{comment_id}/replies", token, params={"message": ack_text})
        return "dm_ok"
    except Exception as e:  # noqa: BLE001
        print("[reply] 已私訊但公開回覆失敗（不重送私訊）：", str(e)[:200])
        if info is not None:
            info["public_error"] = str(e)[:120]
        return "dm_ok_ack_failed"


if __name__ == "__main__":
    # 只做空跑示範：python3 scripts/ig_login_dm.py <comment_id> <時間戳>；沒有權杖也能跑（不連網）
    cid = sys.argv[1] if len(sys.argv) > 1 else "0"
    ts = sys.argv[2] if len(sys.argv) > 2 else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
    print(handle_comment(os.environ.get("IG_ACCESS_TOKEN", ""), "me", cid, ts, dm_text="（連結）", ack_text="已經將「（主題）」完整資訊給你囉～",
                         fallback_text="（連結）", enabled=True, dry_run=True))
