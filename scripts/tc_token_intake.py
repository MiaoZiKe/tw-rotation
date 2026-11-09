"""頻道②「科技透明圈」權杖收件（2026-11-08）。

Andy 原話：「開通自動發文，這部分幫我想辦法自動化」。
目的：Andy 只要在 GitHub Secrets 貼三個值、按一次 workflow，其餘（換長效、查帳號 id、寫回 Secrets、記狀態）全部自動。
工作流：.github/workflows/tc_token_intake.yml（只能手動 workflow_dispatch）。說明：docs/marketing/channels/tc/autopost.md

讀（環境變數，全部來自 GitHub Secrets）：
  TC_THREADS_SHORT_TOKEN   Meta 後台 Threads「User Token Generator」產的 1 小時短效權杖
  META_APP_SECRET          Threads 應用程式密鑰（App secret），換長效用；設過一次就不用再填
  TC_IG_ACCESS_TOKEN       IG 登入版後台「Generate token」產的 60 天權杖
  META_SECRETS_PAT         只限本 repo、只有 Secrets 讀寫的 PAT（寫回用，頻道一已經有）
  THREADS_USER_ID／IG_USER_ID  頻道一（股市帳號）的數字 id —— 只拿來比對，防止把頻道一的帳號收成頻道②
  EXPECT_THREADS_USERNAME／EXPECT_IG_USERNAME（選填）  Andy 在觸發畫面填的新帳號名稱，對不上就不寫回

寫回（gh secret set，值走 stdin）：
  TC_THREADS_ACCESS_TOKEN_AUTO、TC_THREADS_USER_ID、TC_IG_ACCESS_TOKEN_AUTO、TC_IG_USER_ID
狀態檔：data/_state/tc_token.json（只有日期、剩餘天數、username；沒有權杖、沒有 id）。
log：只印 username 與「成功／失敗」＋中文原因；每個權杖與密鑰先印 ::add-mask::。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import meta_token_refresh as M  # noqa: E402  共用 mask／redact／http_get／save_secret

STATE_PATH = ROOT / "data" / "_state" / "tc_token.json"
TAIPEI = timezone(timedelta(hours=8))
EXCHANGE_URL = "https://graph.threads.net/access_token"
THREADS_ME = "https://graph.threads.net/v1.0/me"
IG_ME = "https://graph.instagram.com/v24.0/me"
IG_DEFAULT_DAYS = 60   # IG 登入版後台產的權杖固定 60 天（後台不回 expires_in）

NAMES = ("TC_THREADS_SHORT_TOKEN", "META_APP_SECRET", "TC_IG_ACCESS_TOKEN", "META_SECRETS_PAT",
         "TC_THREADS_ACCESS_TOKEN_AUTO", "TC_THREADS_USER_ID", "TC_IG_ACCESS_TOKEN_AUTO", "TC_IG_USER_ID")


def explain(platform: str, err) -> str:
    """把 Meta 的英文錯誤翻成 Andy 看得懂的一句話（不含任何權杖）。"""
    s = str(err).lower()
    if platform == "threads_exchange":
        if "expired" in s or "session has expired" in s:
            return "短效權杖已過 1 小時，請重新產生（Meta 後台 → Threads 使用案例 → User Token Generator → Generate Access Token），貼到 TC_THREADS_SHORT_TOKEN 後再跑一次"
        if "client secret" in s or "client_secret" in s or "app secret" in s:
            return "META_APP_SECRET 不對：要貼「Threads 應用程式密鑰（Threads app secret）」（Meta 後台 → 應用程式設定 → 基本資料），不是 Facebook 的那一組"
        if "190" in s or "invalid" in s or "cannot parse" in s or "malformed" in s:
            return "短效權杖無效（可能複製不完整或已過期），請重新產生後再跑一次"
    if platform == "ig":
        if "expired" in s:
            return "IG 權杖已過期，請到 IG 登入版後台重新按 Generate token，貼到 TC_IG_ACCESS_TOKEN 後再跑一次"
        if "190" in s or "invalid" in s or "cannot parse" in s or "malformed" in s:
            return "IG 權杖無效（可能複製不完整），請重新按 Generate token 後再跑一次"
    if platform == "threads_me":
        return "換到的長效權杖查不到帳號，請重新產生短效權杖再跑一次"
    return "Meta 回應錯誤：" + M.redact(err)[:160]


def list_secret_names(repo: str, pat: str) -> set[str] | None:
    """用 PAT 列出本 repo 的 Secret 名稱（GitHub 不提供讀值，只有名稱）。失敗回 None。"""
    env = dict(os.environ, GH_TOKEN=pat)
    env.pop("GITHUB_TOKEN", None)
    try:
        r = subprocess.run(["gh", "secret", "list", "-R", repo, "--json", "name", "-q", ".[].name"],
                           text=True, capture_output=True, env=env, timeout=60)
    except Exception:  # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    return {x.strip() for x in r.stdout.splitlines() if x.strip()}


def _days(exp_s: int | None, now: datetime) -> tuple[float, str]:
    secs = exp_s if exp_s else IG_DEFAULT_DAYS * 86400
    return round(secs / 86400, 1), (now + timedelta(seconds=secs)).astimezone(TAIPEI).strftime("%Y-%m-%d")


def intake_threads(env: dict, now: datetime) -> dict:
    short = (env.get("TC_THREADS_SHORT_TOKEN") or "").strip()
    secret = (env.get("META_APP_SECRET") or "").strip()
    if not short:
        return {"ok": False, "skip": True, "reason": "沒有 TC_THREADS_SHORT_TOKEN，這次不處理 Threads"}
    if not secret:
        return {"ok": False, "reason": "META_APP_SECRET 還沒設定（只要設一次）：Meta 後台 → 應用程式設定 → 基本資料 → Threads 應用程式密鑰 → 顯示 → 複製"}
    try:
        d = M.http_get(EXCHANGE_URL, {"grant_type": "th_exchange_token", "client_secret": secret,
                                      "access_token": short})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": explain("threads_exchange", e)}
    long_tok = str(d.get("access_token") or "")
    if not long_tok:
        return {"ok": False, "reason": "Meta 沒有回傳長效權杖，請重新產生短效權杖再跑一次"}
    M.mask(long_tok)
    try:
        exp = int(d["expires_in"]) if d.get("expires_in") is not None else None
    except (TypeError, ValueError):
        exp = None
    try:
        me = M.http_get(THREADS_ME, {"fields": "id,username", "access_token": long_tok})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": explain("threads_me", e)}
    uid, uname = str(me.get("id") or ""), str(me.get("username") or "")
    if not uid:
        return {"ok": False, "reason": explain("threads_me", "no id")}
    days, until = _days(exp, now)
    return {"ok": True, "token": long_tok, "uid": uid, "username": uname, "days_left": days, "expires_on": until}


def intake_ig(env: dict, now: datetime) -> dict:
    tok = (env.get("TC_IG_ACCESS_TOKEN") or "").strip()
    if not tok:
        return {"ok": False, "skip": True, "reason": "沒有 TC_IG_ACCESS_TOKEN，這次不處理 IG"}
    try:
        me = M.http_get(IG_ME, {"fields": "user_id,username", "access_token": tok})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": explain("ig", e)}
    uid, uname = str(me.get("user_id") or me.get("id") or ""), str(me.get("username") or "")
    if not uid:
        return {"ok": False, "reason": "IG 權杖查不到帳號 id（帳號要是專業帳號，權杖要勾 instagram_business_basic）"}
    days, until = _days(None, now)
    return {"ok": True, "token": tok, "uid": uid, "username": uname, "days_left": days, "expires_on": until}


def guard(name: str, res: dict, ch1_id: str, expect: str) -> dict:
    """防呆：絕不能把頻道一（股市帳號）收成頻道②。"""
    if not res.get("ok"):
        return res
    if ch1_id and res["uid"] == ch1_id:
        return {"ok": False, "reason": f"這把 {name} 權杖是頻道一（股市帳號 @{res['username']}）的，不寫回；請用新帳號登入後重新產生"}
    if expect and res["username"].lstrip("@").lower() != expect.lstrip("@").lower():
        return {"ok": False, "reason": f"{name} 帳號是 @{res['username']}，跟觸發時填的 @{expect.lstrip('@')} 不一樣，不寫回"}
    return res


def run(env: dict, now: datetime, state_path: Path = STATE_PATH, saver=M.save_secret,
        lister=list_secret_names) -> tuple[int, dict]:
    for k in ("TC_THREADS_SHORT_TOKEN", "META_APP_SECRET", "TC_IG_ACCESS_TOKEN", "META_SECRETS_PAT"):
        M.mask((env.get(k) or "").strip())
    repo = env.get("GITHUB_REPOSITORY", "MiaoZiKe/tw-rotation")
    pat = (env.get("META_SECRETS_PAT") or "").strip()

    # 預檢：哪些 Secret 已經存在（只看名稱）。META_APP_SECRET 有值就直接用，Andy 不用再填。
    names = lister(repo, pat) if pat else None
    if names is not None:
        M.log("預檢（只看名稱，不讀值）：" + "、".join(f"{n}={'有' if n in names else '無'}" for n in NAMES))
    M.log("META_APP_SECRET：" + ("已設定，直接使用" if (env.get("META_APP_SECRET") or "").strip() else "未設定"))
    if not pat:
        M.log("✗ 失敗：沒有 META_SECRETS_PAT，無法寫回 Secrets（頻道一的續期也用這一把，請確認它還在）")
        return 1, {}

    results = {
        "threads": guard("Threads", intake_threads(env, now), (env.get("THREADS_USER_ID") or "").strip(),
                         (env.get("EXPECT_THREADS_USERNAME") or "").strip()),
        "ig": guard("IG", intake_ig(env, now), (env.get("IG_USER_ID") or "").strip(),
                    (env.get("EXPECT_IG_USERNAME") or "").strip()),
    }
    prefix = {"threads": "TC_THREADS", "ig": "TC_IG"}
    prev = M.load_state(state_path)
    st = {"updated_at": now.astimezone(TAIPEI).strftime("%Y-%m-%d"), "platforms": dict(prev.get("platforms") or {})}
    bad = False
    for plat, r in results.items():
        label = "Threads" if plat == "threads" else "IG"
        if r.get("skip"):
            M.log(f"[{label}] 略過：{r['reason']}")
            continue
        if not r.get("ok"):
            M.log(f"[{label}] ✗ 失敗：{r['reason']}")
            bad = True
            continue
        ok = saver(prefix[plat] + "_ACCESS_TOKEN_AUTO", r["token"], repo, pat) and \
            saver(prefix[plat] + "_USER_ID", r["uid"], repo, pat)
        if not ok:
            M.log(f"[{label}] ✗ 失敗：@{r['username']} 驗證通過，但寫回 Secrets 失敗（請確認 META_SECRETS_PAT 有 Secrets 讀寫權限）")
            bad = True
            continue
        M.log(f"[{label}] ✓ 成功：@{r['username']}，已寫回 {prefix[plat]}_ACCESS_TOKEN_AUTO／{prefix[plat]}_USER_ID，約 {r['days_left']} 天")
        st["platforms"][plat] = {"username": r["username"], "days_left": r["days_left"],
                                 "expires_on": r["expires_on"], "intake_on": st["updated_at"],
                                 "intake_at": now.isoformat(timespec="seconds")}
    if all(r.get("skip") for r in results.values()):
        M.log("✗ 失敗：三個收件 Secret 都是空的，沒有東西可以處理")
        return 1, st
    if st["platforms"]:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(M.redact(json.dumps(st, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8")
    return (1 if bad else 0), st


def main(argv=None) -> int:
    argparse.ArgumentParser(description="頻道② 科技透明圈 權杖收件").parse_args(argv)
    rc, st = run(dict(os.environ), datetime.now(timezone.utc))
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write("### 頻道② 權杖收件：" + ("成功" if rc == 0 else "有失敗，請看 log") + "\n\n| 平台 | 帳號 | 剩幾天 |\n|---|---|---|\n")
            for k, v in (st.get("platforms") or {}).items():
                f.write(f"| {k} | @{v.get('username')} | {v.get('days_left')} |\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
