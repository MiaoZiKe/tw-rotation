"""Meta（Threads／IG）長效權杖自動續期（2026-11-01）。

Andy 原話：「幫我看看 Buffer 這個網站 好像可以幫忙免費自動發文 不用 60 天後 重新申請權杖一次」。
結論：不用 Buffer；Meta 長效權杖本來就能自己續（見 docs/security/20261101_meta_token_refresh.md）。

做的事（每週一次，.github/workflows/meta_token_refresh.yml）：
  1. 讀權杖：先讀 <平台>_ACCESS_TOKEN_AUTO（本程式寫回的新值），沒有才退回 Andy 原本設的 <平台>_ACCESS_TOKEN。
  2. 呼叫官方 refresh 端點（Threads：th_refresh_token；IG（Instagram 登入）：ig_refresh_token），再延 60 天。
  3. 回傳的字串若跟原本不同：先用新權杖打一次 /me 驗證，再用 META_SECRETS_PAT（只限本 repo、只有 Secrets 讀寫）
     寫回 <平台>_ACCESS_TOKEN_AUTO。Andy 原本那把 Secret 永遠不動（壞了還有退路）。
  4. 狀態寫 data/_state/meta_token.json（只有日期、天數、成功與否，絕不含權杖），網站資料狀態燈會讀。
  5. 任何一個平台續期失敗 → exit 1（run 紅燈）；到期前 10 天內仍沒成功（或到期日未知）→ alert，工作流開 issue 提醒。

--dry-run：只用 /me 驗證權杖還能用，不呼叫 refresh、不寫回、不寫狀態檔（手動觸發預設就是這個）。

權杖只從環境變數讀；任何輸出先過 redact，並對 GitHub 印 ::add-mask::。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "_state" / "meta_token.json"
HTTP_TIMEOUT = 30
ALERT_DAYS = 10        # 到期前幾天仍未成功就告警
PAT_ALERT_DAYS = 14    # 寫回用 PAT 到期前幾天提醒

PLATFORMS = {
    "threads": {
        "env": "THREADS_ACCESS_TOKEN",
        "refresh": "https://graph.threads.net/refresh_access_token",
        "grant": "th_refresh_token",
        "me": "https://graph.threads.net/v1.0/me",
        "me_fields": "id",
    },
    "ig": {
        "env": "IG_ACCESS_TOKEN",
        "refresh": "https://graph.instagram.com/refresh_access_token",
        "grant": "ig_refresh_token",
        "me": "https://graph.instagram.com/v24.0/me",
        "me_fields": "user_id",
    },
}
# 2026-11-08 頻道④「談晴說礙」（Andy：「開通自動發文，這部分幫我想辦法自動化」）：同一套續期，權杖分開。
# 沒設 HEALING_* 的時候狀態是 missing（不算失敗、不告警）。
# （healing_threads／healing_ig 改在下面多頻道迴圈一起定義）
# 2026-11-08 頻道②「科技透明圈」（Andy：「開通自動發文，這部分幫我想辦法自動化」）：另一組 TC_* 權杖，
# 由 scripts/tc_token_intake.py 收件寫回 TC_*_ACCESS_TOKEN_AUTO。規則與頻道一相同（AUTO 優先、告警照舊）；
# 還沒收件（沒有任何 TC 權杖）→ 安靜略過，不紅燈、不告警。
PLATFORMS["tc_threads"] = dict(PLATFORMS["threads"], env="TC_THREADS_ACCESS_TOKEN", optional=True, intake="threads")
PLATFORMS["tc_ig"] = dict(PLATFORMS["ig"], env="TC_IG_ACCESS_TOKEN", optional=True, intake="ig")
TC_INTAKE_PATH = STATE_PATH.parent / "tc_token.json"
# 2026-11-09 多頻道（Andy：「talk_01010909 已經好了 幫忙協助其他頻道 一起建立 Tech_01010909 Shrimp_01010909 caffaine.ai」）：
# 名稱照 docs/marketing/channels/accounts.md（TECH_／CAFFAINE_）。沒設＝missing（不紅燈、不告警）。
# exchange=True：Threads 續期失敗（多半是 Andy 貼了 1 小時短效）而且有共用的 THREADS_APP_SECRET → 自動換成 60 天長效再寫回 *_AUTO。
for _ch in ("HEALING", "TECH", "CAFFAINE"):   # 水下蝦米不接（Andy 11-09：「Shrimp_01010909 不用」，繼續用 Buffer）
    _k = _ch.lower()
    PLATFORMS[f"{_k}_threads"] = dict(PLATFORMS["threads"], env=f"{_ch}_THREADS_ACCESS_TOKEN", exchange=True)
    PLATFORMS[f"{_k}_ig"] = dict(PLATFORMS["ig"], env=f"{_ch}_IG_ACCESS_TOKEN")
THREADS_EXCHANGE = "https://graph.threads.net/access_token"

_SECRETS: list[str] = []


def mask(tok: str) -> None:
    if tok and tok not in _SECRETS:
        _SECRETS.append(tok)
        print("::add-mask::" + tok, flush=True)


def redact(s) -> str:
    s = str(s)
    for t in _SECRETS:
        if t:
            s = s.replace(t, "***")
    return s


def log(*a) -> None:
    print(redact(" ".join(str(x) for x in a)), flush=True)


def http_get(url: str, params: dict) -> dict:
    """單一出口，方便測試 mock。錯誤訊息只留狀態碼與 Meta 的錯誤說明，不帶網址（網址含權杖）。"""
    try:
        r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise RuntimeError(f"連線失敗：{type(e).__name__}") from None
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or (isinstance(data, dict) and data.get("error")):
        err = data.get("error") if isinstance(data, dict) else None
        msg = err.get("message", "") if isinstance(err, dict) else str(err or "")
        raise RuntimeError(redact(f"HTTP {r.status_code} {msg}".strip()))
    return data if isinstance(data, dict) else {}


def check_me(platform: str, token: str) -> bool:
    p = PLATFORMS[platform]
    try:
        d = http_get(p["me"], {"fields": p["me_fields"], "access_token": token})
    except Exception as e:  # noqa: BLE001
        log(f"[{platform}] /me 驗證失敗：{redact(e)}")
        return False
    return bool(d.get("id") or d.get("user_id"))


def refresh(platform: str, token: str) -> tuple[str, int | None]:
    p = PLATFORMS[platform]
    d = http_get(p["refresh"], {"grant_type": p["grant"], "access_token": token})
    new = str(d.get("access_token") or "")
    if not new:
        raise RuntimeError("回應裡沒有 access_token")
    mask(new)
    try:
        exp = int(d.get("expires_in")) if d.get("expires_in") is not None else None
    except (TypeError, ValueError):
        exp = None
    return new, exp


def exchange(platform: str, token: str, secret: str) -> tuple[str, int | None]:
    """Threads 短效（1 小時）→ 長效（60 天）：th_exchange_token，要 app secret（共用 THREADS_APP_SECRET）。"""
    d = http_get(THREADS_EXCHANGE, {"grant_type": "th_exchange_token", "client_secret": secret, "access_token": token})
    new = str(d.get("access_token") or "")
    if not new:
        raise RuntimeError("換長效回應裡沒有 access_token")
    mask(new)
    try:
        exp = int(d.get("expires_in")) if d.get("expires_in") is not None else None
    except (TypeError, ValueError):
        exp = None
    return new, exp


def save_secret(name: str, value: str, repo: str, pat: str) -> bool:
    """用 gh 把新權杖寫回 Secret；值走 stdin，不出現在指令列或 log。"""
    env = dict(os.environ, GH_TOKEN=pat)
    env.pop("GITHUB_TOKEN", None)
    try:
        r = subprocess.run(["gh", "secret", "set", name, "-R", repo], input=value, text=True,
                           capture_output=True, env=env, timeout=60)
    except Exception as e:  # noqa: BLE001
        log(f"寫回 {name} 失敗：{type(e).__name__}")
        return False
    if r.returncode != 0:
        log(f"寫回 {name} 失敗：{redact((r.stderr or '').strip())[:200]}")
        return False
    return True


def pat_status(pat: str, repo: str) -> dict:
    """PAT 能不能用、什麼時候到期（GitHub 回應標頭 github-authentication-token-expiration）。"""
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                         headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
                         timeout=HTTP_TIMEOUT)
    except requests.RequestException as e:
        return {"present": True, "ok": False, "error": f"連線失敗：{type(e).__name__}"}
    out = {"present": True, "ok": r.status_code == 200}
    if r.status_code != 200:
        out["error"] = f"HTTP {r.status_code}"
    exp = r.headers.get("github-authentication-token-expiration")
    if exp:
        out["expires_at"] = exp
    return out


def _parse(ts):
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(str(ts).replace(" UTC", "+00:00").replace("Z", "+00:00"))
    except ValueError:
        try:
            d = datetime.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def days_left(expires_at, now: datetime):
    d = _parse(expires_at)
    return None if d is None else round((d - now).total_seconds() / 86400, 1)


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def run(env: dict, now: datetime, dry_run: bool, state_path: Path = STATE_PATH, saver=save_secret,
        pat_checker=pat_status, intake_path: Path | None = None) -> tuple[int, dict]:
    repo = env.get("GITHUB_REPOSITORY", "MiaoZiKe/tw-rotation")
    pat = (env.get("META_SECRETS_PAT") or "").strip()
    mask(pat)
    app_secret = (env.get("THREADS_APP_SECRET") or "").strip()
    mask(app_secret)
    prev = load_state(state_path)
    intake = (load_state(intake_path or state_path.parent / TC_INTAKE_PATH.name).get("platforms")) or {}
    st = {"updated_at": now.isoformat(timespec="seconds"), "mode": "dry-run" if dry_run else "refresh",
          "platforms": {}, "alert": False, "alert_reasons": []}
    failed = False

    for name, p in PLATFORMS.items():
        auto = (env.get(p["env"] + "_AUTO") or "").strip()
        orig = (env.get(p["env"]) or "").strip()
        mask(auto)
        mask(orig)
        token, source = (auto, "auto") if auto else (orig, "original")
        old = dict((prev.get("platforms") or {}).get(name) or {})
        ik = intake.get(p.get("intake") or "") or {}
        if ik.get("intake_at") and (not old.get("last_ok_at") or str(ik["intake_at"]) > str(old.get("last_ok_at"))):
            # 收件剛換過長效權杖 → 當作一次成功續期（24 小時內不再續、到期日用收件時算的）
            exp_on = _parse(ik.get("expires_on"))
            old.update(ok=True, last_ok_at=ik["intake_at"], source_after="auto",
                       expires_at=exp_on.isoformat(timespec="seconds") if exp_on else old.get("expires_at"))
        ps = {"source": source, "ok": False, "last_ok_at": old.get("last_ok_at"),
              "expires_at": old.get("expires_at")}
        if not token:
            ps.update(status="missing", error="沒有設定權杖 Secret")
            log(f"[{name}] 沒有權杖，略過" + ("（頻道② 還沒收件，不告警）" if p.get("optional") else ""))
            st["platforms"][name] = ps
            continue

        if dry_run:
            ok = check_me(name, token)
            ps.update(ok=ok, status="dry-run-ok" if ok else "dry-run-fail")
            log(f"[{name}] dry-run：權杖（{source}）{'可以用' if ok else '驗證失敗'}；沒有續期、沒有寫回")
            failed |= not ok
            st["platforms"][name] = ps
            continue

        # 2026-11-08：Meta 規定權杖要滿 24 小時才能再續；排程常晚跑好幾小時，
        # 若剛剛手動續過，排程那次會被 Meta 拒絕而誤亮紅燈。24 小時內續過且成功 → 跳過。
        last = _parse(old.get("last_ok_at"))
        if old.get("ok") and last is not None and now - last < timedelta(hours=24):
            ps.update(ok=True, status="recent-skip", source=old.get("source_after") or source)
            log(f"[{name}] 24 小時內已續期成功，這次跳過（Meta 規定滿 24 小時才能再續）")
            ps["days_left"] = days_left(ps.get("expires_at"), now)
            st["platforms"][name] = ps
            continue

        try:
            try:
                new, exp = refresh(name, token)
            except Exception as e:  # noqa: BLE001
                if not (p.get("exchange") and app_secret):
                    raise
                log(f"[{name}] 續期失敗（{redact(e)}），可能是 1 小時短效 → 用 THREADS_APP_SECRET 換長效")
                new, exp = exchange(name, token, app_secret)
                ps["exchanged"] = True
        except Exception as e:  # noqa: BLE001
            ps.update(status="refresh-failed", error=redact(e)[:200])
            log(f"[{name}] 續期失敗：{redact(e)}")
            failed = True
        else:
            new_exp = (now + timedelta(seconds=exp)).isoformat(timespec="seconds") if exp else None
            if new == token:
                ps.update(ok=True, status="refreshed", saved="unchanged", last_ok_at=now.isoformat(timespec="seconds"),
                          expires_at=new_exp or ps["expires_at"])
                log(f"[{name}] 續期成功，字串不變（Secrets 不用動），約 {exp // 86400 if exp else '?'} 天")
            elif not check_me(name, new):
                ps.update(status="new-token-invalid", saved="not_saved", error="新權杖驗證失敗，沒有寫回")
                failed = True
            elif not pat:
                ps.update(status="needs-writeback", saved="not_saved",
                          error="Meta 回傳新字串，但沒有 META_SECRETS_PAT 可寫回")
                log(f"[{name}] 續期回傳新字串，但沒有 META_SECRETS_PAT，無法寫回（舊字串到原到期日前仍可用）")
                failed = True
            elif saver(p["env"] + "_AUTO", new, repo, pat):
                ps.update(ok=True, status="refreshed", saved="written", source_after="auto",
                          last_ok_at=now.isoformat(timespec="seconds"), expires_at=new_exp)
                log(f"[{name}] 續期成功，新權杖已寫回 {p['env']}_AUTO，約 {exp // 86400 if exp else '?'} 天")
            else:
                ps.update(status="writeback-failed", saved="not_saved", error="寫回 Secret 失敗")
                failed = True

        dl = days_left(ps.get("expires_at"), now)
        ps["days_left"] = dl
        if not ps["ok"] and (dl is None or dl <= ALERT_DAYS):
            st["alert"] = True
            st["alert_reasons"].append(
                f"{name} 權杖續期失敗，" + ("到期日未知" if dl is None else f"剩 {dl} 天到期"))
        st["platforms"][name] = ps

    if pat:
        pst = pat_checker(pat, repo)
        pdl = days_left(pst.get("expires_at"), now)
        pst["days_left"] = pdl
        if not pst.get("ok"):
            st["alert"] = True
            st["alert_reasons"].append("寫回用 META_SECRETS_PAT 無法使用（可能已到期或權限不對）")
        elif pdl is not None and pdl <= PAT_ALERT_DAYS:
            st["alert"] = True
            st["alert_reasons"].append(f"寫回用 META_SECRETS_PAT 剩 {pdl} 天到期，請重建")
        st["pat"] = pst
    else:
        st["pat"] = {"present": False}

    st["status"] = "bad" if st["alert"] else ("warn" if failed else "ok")
    if not dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(redact(json.dumps(st, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8")
    return (1 if failed else 0), st


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Meta 長效權杖自動續期")
    ap.add_argument("--dry-run", action="store_true", help="只驗證權杖能用，不續期、不寫回、不寫狀態檔")
    a = ap.parse_args(argv)
    rc, st = run(dict(os.environ), datetime.now(timezone.utc), a.dry_run)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"alert={'1' if st['alert'] else '0'}\n")
            f.write("reasons=" + "；".join(st["alert_reasons"]).replace("\n", " ") + "\n")
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(f"### Meta 權杖續期（{st['mode']}）：{st['status']}\n\n| 平台 | 狀態 | 剩幾天 | 來源 |\n|---|---|---|---|\n")
            for k, v in st["platforms"].items():
                f.write(f"| {k} | {v.get('status')} | {v.get('days_left', '')} | {v.get('source')} |\n")
            for r in st["alert_reasons"]:
                f.write(f"\n- ⚠️ {r}")
            f.write("\n")
    log(f"結果：{st['status']}；告警：{'；'.join(st['alert_reasons']) or '無'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
