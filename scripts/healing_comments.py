"""頻道④「談晴說礙」IG：讀主留言 → 檢查有沒有追蹤 → 自動私訊（Private Replies）。

2026-11-08 Andy：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。
說明文件：docs/marketing/channels/healing/comment_dm.md

用法：
  python scripts/healing_comments.py [--dry-run]

流程（輪詢，不用 webhook）：
  1. 貼文來源：state/posted.json 近 N 天的 IG 貼文 id ＋ GET /{ig-user-id}/media（近 N 天，含手動發的）。
  2. 每則貼文 GET /{media_id}/comments?fields=id,text,timestamp,from{id,username},username（只有主留言）。
  3. 每則新留言（state/comments_dm.json 以 comment_id 雜湊去重）：
       自己帳號的留言 → 略過
       自傷關鍵字     → 不送一般私訊，改送關懷資源訊息（不看追蹤），摘要提醒 CEO（legal.md 2-7）
       查追蹤 GET /{igsid}?fields=is_user_follow_business
         true  → Private Reply：POST /{ig-user-id}/messages recipient={"comment_id": ...}
         false → 不私訊，只記錄
         查不到 → 依 dm_config.json 的 unknown_follow（預設 skip）
  4. 留言超過 7 天（Meta 私回期限）→ 記錄 expired，不送。

隱私：state 只存 comment_id 的 SHA-256 前 16 碼、時間、結果；不存留言全文、使用者名稱、使用者編號。
權杖：只從環境變數讀（HEALING_IG_ACCESS_TOKEN_AUTO 優先，其次 HEALING_IG_ACCESS_TOKEN），輸出一律過 redact。
沒有權杖：空跑、結束碼 0，摘要寫「等待權杖」。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_publish as SP  # noqa: E402  共用 http()／redact()／resolve_user_id()

ROOT = Path(__file__).resolve().parents[1]
CH = ROOT / "docs" / "marketing" / "channels" / "healing"
CONFIG = CH / "dm_config.json"
STATE = CH / "state" / "comments_dm.json"
POSTED = CH / "state" / "posted.json"
IG = SP.IG_HOST            # https://graph.instagram.com/v24.0
TAIPEI = timezone(timedelta(hours=8))
REPLY_WINDOW = timedelta(days=7)
MAX_SEND_TRIES = 3         # 私訊送出失敗最多重試幾輪（每則留言 Meta 只准私回 1 次）
KEEP_DAYS = 30             # state 只留 30 天的紀錄

DEFAULT_CFG = {
    "enabled": True, "only_followers": True, "unknown_follow": "skip", "max_per_run": 20,
    "lookback_days": 7, "message": "", "care_enabled": True, "care_message": "",
    "self_harm_keywords": [], "self_harm_exclude": [],
}


# ---------- 小工具 ----------
def load_json(p: Path, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_cfg(p: Path = CONFIG) -> dict:
    cfg = dict(DEFAULT_CFG)
    cfg.update({k: v for k, v in load_json(p, {}).items() if not k.startswith("_")})
    return cfg


def h(cid: str) -> str:
    return hashlib.sha256(str(cid).encode("utf-8")).hexdigest()[:16]


def parse_ts(s) -> datetime | None:
    if not s:
        return None
    s = str(s).replace("Z", "+00:00")
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":      # Meta 給 +0000 這種
        s = s[:-2] + ":" + s[-2:]
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def get_token(env: dict) -> str:
    return (env.get("HEALING_IG_ACCESS_TOKEN_AUTO") or "").strip() or (env.get("HEALING_IG_ACCESS_TOKEN") or "").strip()


def is_self_harm(text: str, cfg: dict) -> bool:
    t = "".join(str(text or "").split())
    for x in cfg.get("self_harm_exclude") or []:
        t = t.replace(x, "")
    return any(k and k in t for k in cfg.get("self_harm_keywords") or [])


def iso_week(d: datetime) -> str:
    y, w, _ = d.astimezone(TAIPEI).isocalendar()
    return f"{y}-W{w:02d}"


# ---------- Meta API ----------
def me(token: str) -> dict:
    d = SP.http("GET", f"{IG}/me", params={"fields": "user_id,username", "access_token": token})
    return {"id": str(d.get("user_id") or d.get("id") or ""), "username": str(d.get("username") or "")}


def recent_media(uid: str, token: str, since: datetime, posted: dict) -> list[str]:
    ids: list[str] = []
    for v in (posted or {}).values():                      # 自動發文紀錄（頻道④ healing_post.py 寫的）
        ig = v.get("ig") if isinstance(v, dict) else None
        if isinstance(ig, dict) and ig.get("id"):
            at = parse_ts(ig.get("at") or v.get("at"))
            if at is None or at >= since:
                ids.append(str(ig["id"]))
    try:                                                   # 帳號上全部貼文（含手動發的）
        url, params = f"{IG}/{uid}/media", {"fields": "id,timestamp", "limit": 25, "access_token": token}
        for _ in range(4):
            d = SP.http("GET", url, params=params)
            old = False
            for m in d.get("data") or []:
                ts = parse_ts(m.get("timestamp"))
                if ts and ts < since:
                    old = True
                    continue
                ids.append(str(m.get("id")))
            nxt = (d.get("paging") or {}).get("next")
            if old or not nxt:
                break
            url, params = nxt, None
    except Exception as e:  # noqa: BLE001
        SP.log(f"[ig] 讀貼文清單失敗，只用 posted.json：{SP.redact(e)}")
    return list(dict.fromkeys(i for i in ids if i and i != "None"))


def comments(media_id: str, token: str) -> list[dict]:
    out: list[dict] = []
    url = f"{IG}/{media_id}/comments"
    params = {"fields": "id,text,timestamp,username,from{id,username}", "limit": 50, "access_token": token}
    for _ in range(10):
        d = SP.http("GET", url, params=params)
        out.extend(d.get("data") or [])
        nxt = (d.get("paging") or {}).get("next")
        if not nxt:
            break
        url, params = nxt, None
    return out


def follows(igsid: str, token: str) -> bool | None:
    """True／False；查不到（未授權、權限不足、對方沒傳過訊息）回 None。"""
    if not igsid:
        return None
    try:
        d = SP.http("GET", f"{IG}/{igsid}", params={"fields": "is_user_follow_business", "access_token": token})
    except Exception as e:  # noqa: BLE001
        SP.log(f"[ig] 查追蹤失敗（記為無法確認）：{SP.redact(e)[:200]}")
        return None
    v = d.get("is_user_follow_business")
    return v if isinstance(v, bool) else None


def private_reply(uid: str, token: str, comment_id: str, text: str) -> dict:
    return SP.http("POST", f"{IG}/{uid}/messages", params={"access_token": token},
                   json={"recipient": {"comment_id": comment_id}, "message": {"text": text}})


# ---------- 主流程 ----------
def run(env: dict | None = None, dry_run: bool = False, now: datetime | None = None,
        cfg_path: Path = CONFIG, state_path: Path = STATE, posted_path: Path = POSTED) -> tuple[int, dict]:
    env = dict(os.environ if env is None else env)
    now = now or datetime.now(timezone.utc)
    cfg = load_cfg(cfg_path)
    res = {"at": now.astimezone(TAIPEI).isoformat(timespec="seconds"), "mode": "dry" if dry_run else "live",
           "counts": {}, "alerts": 0, "errors": [], "summary": ""}

    def bump(k):
        res["counts"][k] = res["counts"].get(k, 0) + 1

    token = get_token(env)
    if not token:
        res["mode"] = "wait_token"
        res["summary"] = "等待權杖（HEALING_IG_ACCESS_TOKEN），本輪空跑"
        return 0, res
    SP._SECRETS.append(token)
    print("::add-mask::" + token, flush=True)
    if not cfg.get("enabled"):
        res["summary"] = "dm_config.json 的 enabled=false，本輪不讀留言"
        return 0, res

    try:
        acct = me(token)
    except Exception as e:  # noqa: BLE001
        res["errors"].append(f"查自己帳號失敗：{SP.redact(e)[:200]}")
        res["summary"] = "權杖無效或權限不足（查不到自己帳號）"
        return 1, res
    uid = (env.get("HEALING_IG_USER_ID") or "").strip() or acct["id"]
    if not uid:
        res["summary"] = "查不到 IG 帳號編號"
        return 1, res
    if len(uid) >= 6:
        SP._SECRETS.append(uid)
    own = {acct["id"], uid}

    state = load_json(state_path, {})
    before = json.dumps({k: state.get(k) or {} for k in ("seen", "weekly")}, sort_keys=True, ensure_ascii=False)
    seen: dict = state.setdefault("seen", {})
    stats: dict = state.setdefault("weekly", {})
    since = now - timedelta(days=int(cfg.get("lookback_days") or 7))
    media = recent_media(uid, token, since, load_json(posted_path, {}))
    SP.log(f"[ig] 近 {cfg.get('lookback_days')} 天貼文 {len(media)} 則")
    cap = int(cfg.get("max_per_run") or 0)
    sent = 0
    capped = False

    for mid in media:
        try:
            cs = comments(mid, token)
        except Exception as e:  # noqa: BLE001
            res["errors"].append(f"讀留言失敗（貼文 …{str(mid)[-4:]}）：{SP.redact(e)[:200]}")
            continue
        for c in cs:
            cid = str(c.get("id") or "")
            if not cid:
                continue
            key = h(cid)
            rec = seen.get(key)
            if rec and rec.get("result") != "send_failed":
                continue
            if rec and rec.get("tries", 0) >= MAX_SEND_TRIES:
                continue
            frm = c.get("from") or {}
            who_id = str(frm.get("id") or "")
            who_name = str(frm.get("username") or c.get("username") or "")
            ts = parse_ts(c.get("timestamp"))
            base = {"at": res["at"], "comment_at": ts.astimezone(TAIPEI).isoformat(timespec="seconds") if ts else ""}

            if who_id in own or (acct["username"] and who_name == acct["username"]):
                result, follow, harm, text = "own", None, False, None
            elif ts and now - ts > REPLY_WINDOW:
                result, follow, harm, text = "expired", None, False, None
            else:
                harm = is_self_harm(c.get("text"), cfg)
                follow = None if harm else follows(who_id, token)
                if harm:
                    text = cfg.get("care_message") if cfg.get("care_enabled") else None
                    result = "care" if text else "care_disabled"
                    res["alerts"] += 1
                elif follow is True or (follow is None and not cfg.get("only_followers")):
                    text, result = cfg.get("message"), "dm"
                elif follow is None:
                    if cfg.get("unknown_follow") == "send":
                        text, result = cfg.get("message"), "dm_unknown_follow"
                    else:
                        text, result = None, "skip_unknown_follow"
                else:
                    text, result = None, "skip_not_follower"

            if text:
                if cap and sent >= cap:
                    capped = True
                    continue          # 不記錄，下一輪再處理（仍在 7 天內）
                if dry_run:
                    result = "dry_" + result
                else:
                    try:
                        SP.retry_once("ig-dm", lambda: private_reply(uid, token, cid, text), tries=2)
                    except Exception as e:  # noqa: BLE001
                        msg = SP.redact(e)
                        if "already" in msg.lower() or "2534" in msg:     # 已私回過 → 視為完成，不再送
                            result = result + "_already"
                        else:
                            res["errors"].append(f"私訊失敗：{msg[:200]}")
                            tries = (rec or {}).get("tries", 0) + 1
                            seen[key] = dict(base, result="send_failed", intended=result, tries=tries,
                                             self_harm=bool(harm))
                            bump("send_failed")
                            continue
                sent += 1
            entry = dict(base, result=result)
            if follow is not None:
                entry["follow"] = follow
            if harm:
                entry["self_harm"] = True
            if not dry_run:
                seen[key] = entry
            bump(result)
            wk = stats.setdefault(iso_week(now), {})
            if not dry_run:
                wk[result] = wk.get(result, 0) + 1

    # 只留 30 天紀錄
    cut = (now - timedelta(days=KEEP_DAYS)).astimezone(TAIPEI).isoformat(timespec="seconds")
    state["seen"] = {k: v for k, v in seen.items() if str(v.get("at", "")) >= cut}
    state["weekly"] = dict(sorted(stats.items())[-12:])
    after = json.dumps({k: state.get(k) or {} for k in ("seen", "weekly")}, sort_keys=True, ensure_ascii=False)
    if not dry_run and after != before:        # 沒有新結果就不寫檔（避免每 15 分鐘一個空 commit）
        state["last_change"] = {k: res[k] for k in ("at", "counts", "alerts")}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(SP.redact(json.dumps(state, ensure_ascii=False, indent=1)) + "\n", encoding="utf-8")

    parts = [f"{k} {v}" for k, v in sorted(res["counts"].items())]
    res["summary"] = (f"貼文 {len(media)} 則；" + ("、".join(parts) if parts else "沒有新留言")
                      + (f"；已達每輪上限 {cap}，其餘下一輪處理" if capped else ""))
    unknown_week = (stats.get(iso_week(now)) or {}).get("skip_unknown_follow", 0)
    if unknown_week:
        res["summary"] += f"；本週「無法確認追蹤」未私訊 {unknown_week} 則"
    return (1 if res["errors"] and not res["counts"] else 0), res


LABEL = {
    "dm": "已私訊（有追蹤）", "dm_unknown_follow": "已私訊（追蹤無法確認，設定為照樣送）",
    "care": "已送關懷資源訊息（自傷關鍵字）", "care_disabled": "自傷關鍵字（關懷訊息已關閉，未送）",
    "skip_not_follower": "沒追蹤，未私訊", "skip_unknown_follow": "追蹤無法確認，未私訊",
    "own": "自己帳號的留言", "expired": "超過 7 天，無法私回", "send_failed": "私訊失敗（下一輪重試）",
}


def summary_md(res: dict) -> str:
    lines = ["## 談晴說礙：IG 留言自動私訊", "", f"- 時間（台北）：{res['at']}", f"- 模式：{res['mode']}",
             f"- 摘要：{res['summary']}"]
    if res["counts"]:
        lines += ["", "| 結果 | 則數 |", "|---|---|"]
        for k, v in sorted(res["counts"].items()):
            base = k[4:] if k.startswith("dry_") else k
            lines.append(f"| {LABEL.get(base.replace('_already', ''), base)}{'（空跑）' if k.startswith('dry_') else ''} | {v} |")
    if res["alerts"]:
        lines += ["", f"### ⚠️ 自傷訊號 {res['alerts']} 則：請 CEO 依 legal.md 2-7 人工處理（到 IG 收件匣看原留言，評估級別、公開回範本 A、必要時檢舉）"]
    for e in res["errors"]:
        lines.append(f"- 錯誤：{e}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    code, res = run(dry_run=a.dry_run)
    md = summary_md(res)
    print(SP.redact(md))
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as f:
            f.write(SP.redact(md))
    if res["alerts"]:
        print(f"::warning::談晴說礙 IG 留言出現自傷訊號 {res['alerts']} 則，請 CEO 依 legal.md 2-7 處理")
    return code


if __name__ == "__main__":
    sys.exit(main())
