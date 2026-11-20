"""頻道①「哩股哩股」IG：留言關鍵字 → 私訊來源連結（真私訊，IGAA 權杖）。

2026-11-20 Andy：「當讀者在影片底下留下關鍵留言，我沒發現我這邊有主動私訊他提供連結」。
設定：social/ig/dm_config.json；紀錄：social/ig/state/comments_dm.json（只存留言 id 的雜湊、時間、結果）。

流程（輪詢，由 gh-cron Worker 每 4 小時派 ligu_comments.yml）：
  1. 貼文來源：social/ig/queue/*.md 裡 status: posted、有 urls（IG 連結）與 first_comment（來源文章連結）、近 lookback_days 天的檔。
  2. 用 GET /{ig-user-id}/media 把「連結的短碼」對到 IG 貼文 id，再讀每篇的主留言。
  3. 留言含關鍵字、不是自己帳號、沒處理過 → scripts/ig_login_dm.handle_comment：
       先私訊來源連結 → 成功才公開回「已經將XXX完整資訊給你囉～」（XXX＝貼文主題）；私訊失敗 → 退回公開貼連結。
  4. 每則留言最多 MAX_TRIES 輪（Meta 每則留言只准私回 1 次，成功就不再送）。
權杖只從環境變數讀（IG_ACCESS_TOKEN_AUTO 優先，其次 IG_ACCESS_TOKEN），輸出一律遮蔽；不存留言全文與使用者名稱。
用法：python scripts/ligu_comments.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ig_login_dm as DM  # noqa: E402
import social_publish as SP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "social" / "ig" / "dm_config.json"
STATE = ROOT / "social" / "ig" / "state" / "comments_dm.json"
QUEUE = ROOT / "social" / "ig" / "queue"
TAIPEI = timezone(timedelta(hours=8))
MAX_TRIES = 3
KEEP_DAYS = 30
FINAL = {"dm_ok", "dm_ok_ack_failed", "fallback_public", "skipped_old"}

DEFAULT_CFG = {"enabled": False, "keywords": [], "lookback_days": 7, "max_per_run": 20, "dm_template": "",
               "ack_text": "已經將「{topic}」完整資訊給你囉～", "fallback_template": ""}


def load_json(p: Path, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_cfg(p: Path = CONFIG) -> dict:
    cfg = dict(DEFAULT_CFG)
    cfg.update({k: v for k, v in load_json(p, {}).items() if not k.startswith("_")})
    return cfg


def h(cid) -> str:
    return hashlib.sha256(str(cid).encode("utf-8")).hexdigest()[:16]


def norm(s) -> str:
    import unicodedata
    return "".join(unicodedata.normalize("NFKC", str(s or "")).lower().split())


def match_kw(text: str, kws: list[str]) -> str:
    t = norm(text)
    return next((k for k in kws if norm(k) and norm(k) in t), "")


def parse_ts(s) -> datetime | None:
    try:
        return datetime.strptime(str(s).replace("+0000", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
    except Exception:  # noqa: BLE001
        return None


def front_matter(path: Path) -> dict:
    """只讀 --- 之間的 key: value（單行），不依賴 yaml。"""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def shortcode(url: str) -> str:
    m = re.search(r"instagram\.com/(?:reel|reels|p|tv)/([\w-]+)", url or "")
    return m.group(1) if m else ""


def first_url(text: str) -> str:
    m = re.search(r"https?://\S+", text or "")
    return m.group(0).rstrip("，。、）)") if m else ""


def topic_of(fm: dict) -> str:
    """貼文主題（公開回覆「已經將XXX完整資訊給你囉～」的 XXX）：front matter 的 topic，沒有就取 title 去掉「頻道①短影片」前綴與結尾括號。"""
    if fm.get("topic"):
        return fm["topic"].strip()
    t = re.sub(r"^頻道[①②③④]\S*\s*", "", fm.get("title", "")).strip()
    t = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", t).strip()
    return t or "這篇"


def queue_posts(now: datetime, lookback_days: int, queue: Path = QUEUE) -> dict:
    """{短碼: {url, title, file}}：近 lookback_days 天已發、有來源連結的貼文。"""
    out = {}
    for f in sorted(Path(queue).glob("*.md")):
        fm = front_matter(f)
        if fm.get("status") != "posted":
            continue
        at = parse_ts(fm.get("posted_at", "").replace("+08:00", "+0800")) or parse_ts(fm.get("posted_at", ""))
        if at is None:
            try:
                at = datetime.strptime(fm.get("posted_at", "")[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=TAIPEI)
            except ValueError:
                at = None
        if at is not None and now - at > timedelta(days=lookback_days + 1):
            continue
        url = first_url(fm.get("first_comment", ""))
        for u in re.split(r"[\s,]+", fm.get("urls", "")):
            sc = shortcode(u)
            if sc and url:
                out[sc] = {"url": url, "title": fm.get("title", ""), "topic": topic_of(fm), "file": f.name}
    return out


def media_map(uid: str, token: str, posts: dict) -> dict:
    """{IG 貼文 id: post}：用 /media 的 permalink 短碼對到佇列貼文。"""
    out = {}
    url, params = f"{DM.IG}/{uid}/media", {"fields": "id,permalink,timestamp", "limit": 50, "access_token": token}
    for _ in range(3):
        d = SP.http("GET", url, params=params)
        for m in d.get("data") or []:
            sc = shortcode(m.get("permalink", ""))
            if sc in posts:
                out[str(m["id"])] = posts[sc]
        nxt = (d.get("paging") or {}).get("next")
        if not nxt or len(out) >= len(posts):
            break
        url, params = nxt, None
    return out


def read_comments(media_id: str, token: str) -> list[dict]:
    out: list[dict] = []
    url = f"{DM.IG}/{media_id}/comments"
    params = {"fields": "id,text,timestamp,username,from{id,username}", "limit": 50, "access_token": token}
    for _ in range(5):
        d = SP.http("GET", url, params=params)
        out.extend(d.get("data") or [])
        nxt = (d.get("paging") or {}).get("next")
        if not nxt:
            break
        url, params = nxt, None
    return out


def read_comments_expanded(media_id: str, token: str) -> list[dict]:
    """備援：/comments 回空但貼文 comments_count>0 時，改用欄位展開 GET /{media}?fields=comments{...}（同一權限、不同路徑）。"""
    d = SP.http("GET", f"{DM.IG}/{media_id}", params={"fields": "comments.limit(50){id,text,timestamp,username,from{id,username}}", "access_token": token})
    return ((d.get("comments") or {}).get("data")) or []


def run(env: dict | None = None, dry_run: bool = False, now: datetime | None = None, cfg_path: Path = CONFIG,
        state_path: Path = STATE, queue: Path = QUEUE) -> tuple[int, dict]:
    env = os.environ if env is None else env
    now = now or datetime.now(timezone.utc)
    cfg = load_cfg(cfg_path)
    res = {"summary": "", "posts": 0, "comments": 0, "matched": 0, "sent": 0, "errors": []}
    if not cfg.get("enabled"):
        res["summary"] = "dm_config enabled=false，整段停用"
        return 0, res
    token = (env.get("IG_ACCESS_TOKEN_AUTO") or "").strip() or (env.get("IG_ACCESS_TOKEN") or "").strip()
    if not token:
        res["summary"] = "沒有 IG 權杖（IG_ACCESS_TOKEN），等待權杖"
        return 0, res
    SP._SECRETS.append(token)
    if token.startswith("EAA"):
        res["errors"].append("頻道①的權杖不是 IGAA，真私訊做不到（本程式只走 Instagram 登入版）")
        return 1, res
    posts = queue_posts(now, int(cfg["lookback_days"]), queue)
    res["posts"] = len(posts)
    if not posts:
        res["summary"] = "近期沒有已發且有來源連結的貼文"
        return 0, res
    try:
        me = SP.http("GET", f"{DM.IG}/me", params={"fields": "user_id,username", "access_token": token})
        uid, own = str(me.get("user_id") or me.get("id") or ""), str(me.get("username") or "").lower()
        mm = media_map(uid, token, posts)
    except Exception as e:  # noqa: BLE001
        res["errors"].append("讀帳號／貼文清單失敗：" + SP.redact(e)[:200])
        return 1, res
    state = load_json(state_path, {"comments": {}})
    seen = state.setdefault("comments", {})
    kws = [str(k) for k in cfg.get("keywords") or []]
    budget = int(cfg["max_per_run"])
    for media_id, post in mm.items():
        try:
            cs = read_comments(media_id, token)
            try:      # 診斷：貼文自己說有幾則留言（跟實際讀到的比，抓「讀得到貼文、讀不到留言」的權限問題）
                cnt = SP.http("GET", f"{DM.IG}/{media_id}", params={"fields": "comments_count", "access_token": token}).get("comments_count")
            except Exception as e:  # noqa: BLE001
                cnt = "讀不到：" + SP.redact(e)[:80]
            SP.log(f"[ligu] 貼文 …{media_id[-4:]}（{post['file']}）讀到留言 {len(cs)} 則；貼文自己的 comments_count＝{cnt}")
            if not cs and isinstance(cnt, int) and cnt > 0:
                try:
                    cs = read_comments_expanded(media_id, token)
                    SP.log(f"[ligu] 改用欄位展開讀留言：{len(cs)} 則（欄位：{sorted({k for c in cs for k in c})}）")
                except Exception as e:  # noqa: BLE001
                    SP.log("[ligu] 欄位展開也讀不到：" + SP.redact(e)[:160])
        except Exception as e:  # noqa: BLE001
            res["errors"].append("讀留言失敗：" + SP.redact(e)[:160])
            continue
        for c in cs:
            res["comments"] += 1
            cid = str(c.get("id") or "")
            if not cid or (str(c.get("username") or (c.get("from") or {}).get("username") or "").lower() == own):
                continue
            kw = match_kw(c.get("text", ""), kws)
            if not kw:
                continue
            res["matched"] += 1
            rec = seen.get(h(cid)) or {}
            if rec.get("result") in FINAL or int(rec.get("tries", 0)) >= MAX_TRIES:
                continue
            if budget <= 0:
                continue
            budget -= 1
            url = post["url"]
            r = DM.handle_comment(token, uid, cid, str(c.get("timestamp") or ""),
                                  dm_text=cfg["dm_template"].format(url=url, topic=post["topic"]),
                                  ack_text=cfg["ack_text"].format(topic=post["topic"]),
                                  fallback_text=cfg["fallback_template"].format(url=url, topic=post["topic"]), enabled=True, dry_run=dry_run)
            SP.log(f"[ligu] 留言 …{cid[-4:]} 關鍵字「{kw}」→ {r}")
            if dry_run:
                continue
            res["sent"] += 1 if r in ("dm_ok", "dm_ok_ack_failed", "fallback_public") else 0
            seen[h(cid)] = {"at": now.astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M"), "result": r, "tries": int(rec.get("tries", 0)) + 1}
            if r == "failed":
                res["errors"].append(f"留言 …{cid[-4:]} 送不出去（第 {seen[h(cid)]['tries']} 次）")
    cut = (now - timedelta(days=KEEP_DAYS)).astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M")
    state["comments"] = {k: v for k, v in seen.items() if str(v.get("at", "")) >= cut}
    if not dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    res["summary"] = (f"貼文 {len(mm)}／{res['posts']} 則對得到 IG；讀到留言 {res['comments']} 則，符合關鍵字 {res['matched']} 則，"
                      f"{'（空跑）' if dry_run else ''}本輪送出 {res['sent']} 則")
    return (1 if res["errors"] else 0), res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    code, res = run(dry_run=a.dry_run)
    md = f"## ① 哩股哩股：IG 留言關鍵字私訊\n\n- 時間（台北）：{datetime.now(TAIPEI).isoformat(timespec='seconds')}\n- 模式：{'dry-run' if a.dry_run else 'live'}\n- 摘要：{res['summary']}\n" + "".join(f"- 錯誤：{e}\n" for e in res["errors"])
    print(SP.redact(md))
    sp = os.environ.get("GITHUB_STEP_SUMMARY")
    if sp:
        with open(sp, "a", encoding="utf-8") as f:
            f.write(SP.redact(md))
    return code


if __name__ == "__main__":
    sys.exit(main())
