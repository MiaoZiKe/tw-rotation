"""科技透明圈「沒有台股代號」公司的 Logo（外商、未上市），以官網網域為鍵。Andy 2026-10-27：
「科技透明圈還是很多外商沒有 LOGO，確保 8 成都有」。DECISIONS #364。

為什麼另開一條，不塞進 logos.py 的代號流程
------------------------------------------
- 個股 Logo 以台股代號為鍵（data/logos/<代號>.png），外商沒有代號。前端原本只能臨時向 Google s2 要 16～32px 小圖示，
  `<64px` 被退成字標，所以科技透明圈大量沒圖。
- 抓圖本體（官網首頁 icon／apple-touch-icon／manifest／頁首 Logo／SVG、robots 規則、預設圖雜湊、Google s2）完全沿用
  `logos.fetch_logo()`，不重寫、白名單與 robots 規矩一條都沒放寬 —— 只是輸入從「代號＋官網」換成「網域」。

來源順序（每個網域，要求原圖長邊 ≥ `config.TC_LOGO_MIN_PX`＝64，SVG 算向量不受限）
-----------------------------------------------------------------------------------
1. 官網（logos.fetch_logo）：首頁 icon／apple-touch-icon／manifest／頁首 Logo／og:image。
2. Wikimedia Commons（logo_wikimedia.fetch_by_website）：公司英文名搜尋 Wikidata、**官方網站網域對得上**才收，
   授權只收 PD／CC0（CC BY 要等前端有署名連結，見 LOGO_WIKIMEDIA_ALLOW_BY）。
3. Google s2 `sz=256`：只在官網沒有 robots 禁止、也沒有「對方擋雲端存取」時才問（同 #264／#267：不繞過對方的存取控制）。
   不用 DuckDuckGo、Clearbit 等任何商用 API。

三個來源都拿不到 ≥64px 就判失敗（不存 16／32px 小圖：Andy 要的是清楚的 LOGO，小圖前端本來就會退字標）。

存放（DECISIONS #155、只增不改的精神）
--------------------------------------
- `data/logos/tc/<網域>.png`：`config.TC_LOGO_PX`（128）見方的透明底 PNG，等比縮放置中、不裁不拉不改色。
- `data/logos/tc/_index.json`：網域 → 狀態、來源、原圖尺寸、雜湊、抓取日、公司名、各來源失敗原因。
- `data/logos/tc/ATTRIBUTION.md`：Wikimedia 來源的出處。
- `data/_state/tc_logo_progress.json`：每輪摘要、失敗清單、下一次到期日。
有圖 90 天才重抓（雜湊一樣不寫檔，git 不多版本）、沒抓到 30 天再試；已經有圖、這次沒抓到就保留舊圖。
build_payload 只讀湖、輸出 `site/data/tc_logos.json`（{網域: 相對路徑}），見 build_payload.export_tc_logos()。
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .. import config
from . import logos as lg

log = logging.getLogger(__name__)

DOMAINS_FILE = Path(__file__).resolve().parent.parent / "groups" / "tc_logo_domains.json"


# ------------------------------------------------------------------ 路徑（每次呼叫才算，測試可以換 config.DATA）

def tc_dir() -> Path:
    return lg.logo_dir() / config.TC_LOGO_SUBDIR


def index_path() -> Path:
    return tc_dir() / "_index.json"


def state_path() -> Path:
    return config.STATE / "tc_logo_progress.json"


def png_name(domain: str) -> str:
    return f"{domain}.png"


# ------------------------------------------------------------------ 清單與索引

def load_domains(path: Path | None = None) -> list[dict]:
    """[{domain, names, en}]。清單壞了回空並記 log（不拖垮整個 Logo 步驟）。"""
    p = path or DOMAINS_FILE
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("科技透明圈網域清單讀不進來（%s）：%s", p, exc)
        return []
    out, seen = [], set()
    for r in (raw.get("domains") if isinstance(raw, dict) else raw) or []:
        d = str((r or {}).get("domain") or "").strip().lower()
        if not d or d in seen or not lg._HOST_RE.match(d):
            continue
        seen.add(d)
        out.append({"domain": d, "names": list(r.get("names") or []), "en": str(r.get("en") or "").strip()})
    return out


def read_index() -> dict:
    p = index_path()
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("items"), dict):
                return d
        except (ValueError, OSError) as exc:
            log.warning("科技透明圈 Logo 索引讀不進來（%s），當成空的重建", exc)
    return {"version": 1, "items": {}}


def write_index(idx: dict) -> None:
    tc_dir().mkdir(parents=True, exist_ok=True)
    idx["version"] = 1
    idx["updated_at"] = datetime.now(timezone.utc).isoformat()
    idx["items"] = dict(sorted(idx.get("items", {}).items()))
    index_path().write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


def usable(idx: dict | None = None) -> dict[str, str]:
    """{網域: 檔名}：狀態 ok 且檔案真的在。build_payload 只輸出這些。"""
    idx = idx if idx is not None else read_index()
    out = {}
    for dom, rec in idx.get("items", {}).items():
        if rec.get("status") == "ok" and (tc_dir() / png_name(dom)).exists():
            out[dom] = png_name(dom)
    return out


def _days(rec: dict) -> int:
    return config.LOGO_REFRESH_DAYS if rec.get("status") == "ok" else config.LOGO_RETRY_DAYS


def _due(rec: dict, today: date) -> bool:
    try:
        last = date.fromisoformat(str(rec.get("fetched"))[:10])
    except ValueError:
        return True
    return (today - last).days >= _days(rec)


def next_due(rec: dict) -> str | None:
    try:
        last = date.fromisoformat(str(rec.get("fetched"))[:10])
    except ValueError:
        return None
    return (last + timedelta(days=_days(rec))).isoformat()


def select_todo(domains: list[dict], idx: dict, today: date, limit: int) -> list[dict]:
    """沒抓過的先，其次到期的（舊的先）。已抓到的好圖不因為策略升級而重抓。"""
    items = idx.get("items", {})
    new = [d for d in domains if d["domain"] not in items]
    old = [d for d in domains if d["domain"] in items and _due(items[d["domain"]], today)]
    old.sort(key=lambda d: str(items[d["domain"]].get("fetched") or ""))
    return (new + old)[:limit]


# ------------------------------------------------------------------ 抓一個網域

@contextmanager
def _px(px: int):
    """暫時把 Logo 輸出邊長改成 px。整個 tc 步驟（含執行緒池）結束才還原，且只有這一步會改它。"""
    old = config.LOGO_PX
    config.LOGO_PX = px
    try:
        yield
    finally:
        config.LOGO_PX = old


def big_enough(res: dict) -> bool:
    """成功、且原圖長邊 ≥ 64（SVG 的 orig 是我們自己算繪的 256，天然過關）。"""
    return res.get("status") == "ok" and bool(res.get("png")) and max(res.get("orig") or [0]) >= config.TC_LOGO_MIN_PX


def s2_allowed(site_res: dict) -> bool:
    """官網禁止（robots）或明講擋雲端存取時，不請 Google 代抓 —— 同 logos.py 的規矩，不繞過對方的存取控制。"""
    if site_res.get("status") == "robots":
        return False
    return "Google 備援都不抓" not in str(site_res.get("detail") or "") and "尊重它" not in str(site_res.get("detail") or "")


def _site(entry: dict, reject, fetcher) -> dict:
    dom = entry["domain"]
    try:
        return fetcher(f"https://{dom}", dom, reject=reject, names=tuple(entry.get("names") or ()) + ((entry["en"],) if entry.get("en") else ()))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "domain": dom, "detail": str(exc)[:200]}


def _google256(dom: str, reject) -> dict:
    url = config.TC_LOGO_S2.format(domain=dom)
    got = lg._try_image(url, "google_s2")
    if isinstance(got, lg.LogoReject):
        return {"status": "none" if got.reason != "too_small" else "too_small", "domain": dom,
                "detail": f"{got.reason} {got.detail}"[:200]}
    png, orig = got
    if lg.sha1(png) in reject:
        return {"status": "generic", "domain": dom, "detail": f"預設圖 {url}"}
    return {"status": "ok", "domain": dom, "src": "google_s2", "url": url, "png": png, "orig": list(orig)}


def resolve(entries: list[dict], reject, deadline: float, *, site_fetcher=None, wiki_fetcher=None,
            s2_fetcher=None) -> dict[str, dict]:
    """依序試官網 → Wikimedia → Google s2 256，回 {網域: 最終結果}。各 fetcher 可注入（測試不打網路）。
    每個結果多一個 `tried`：{來源: 一句話原因}，失敗時記進索引，下一個人查「為什麼這家沒圖」用。"""
    site_fetcher = site_fetcher or lg.fetch_logo
    wiki_fetcher = wiki_fetcher
    if wiki_fetcher is None:
        from . import logo_wikimedia as wm
        wiki_fetcher = wm.fetch_by_website if config.LOGO_WIKIMEDIA_ENABLED else (lambda rows, reject, deadline: {})
    s2_fetcher = s2_fetcher or _google256

    out: dict[str, dict] = {}
    sites: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max(1, config.LOGO_WORKERS)) as ex:
        futs = {e["domain"]: ex.submit(_site, e, reject, site_fetcher) for e in entries}
        for dom, fu in futs.items():
            try:
                sites[dom] = fu.result()
            except Exception as exc:  # noqa: BLE001
                sites[dom] = {"status": "error", "domain": dom, "detail": str(exc)[:200]}

    need_wiki = []
    for e in entries:
        dom, res = e["domain"], sites[e["domain"]]
        tried = {"site": _brief(res)}
        if big_enough(res):
            out[dom] = {**res, "tried": tried}
        else:
            out[dom] = {"status": "pending", "domain": dom, "tried": tried, "_site": res}
            if e["en"]:
                need_wiki.append(e)

    # ② Wikimedia（序列、有間隔，遵守 Commons／Wikidata 的流量規範）
    if need_wiki and time.time() < deadline:
        got = wiki_fetcher([{"domain": e["domain"], "en": e["en"]} for e in need_wiki], reject, deadline) or {}
        for e in need_wiki:
            w = got.get(e["domain"])
            if w is None:
                continue
            out[e["domain"]]["tried"]["wikimedia"] = _brief(w)
            if big_enough(w):
                out[e["domain"]] = {**w, "tried": out[e["domain"]]["tried"]}

    # ③ Google s2 256（官網沒禁止才問）
    for e in entries:
        dom = e["domain"]
        cur = out[dom]
        if cur["status"] != "pending":
            continue
        if time.time() >= deadline:
            cur["tried"]["google_s2"] = "時間到，下一輪"
            continue
        site_res = cur["_site"]
        if not s2_allowed(site_res):
            cur["tried"]["google_s2"] = "官網禁止或擋雲端存取，不問 Google"
            continue
        g = s2_fetcher(dom, reject)
        cur["tried"]["google_s2"] = _brief(g)
        if big_enough(g):
            out[dom] = {**g, "tried": cur["tried"]}

    for dom, cur in out.items():
        if cur["status"] == "pending":
            site_res = cur.pop("_site", {})
            # 失敗原因：官網的狀態最有資訊量（robots／too_small／none／error）；官網其實 ok 但太小 → too_small
            st = site_res.get("status", "none")
            if st == "ok":
                st = "too_small"
            out[dom] = {"status": st if st in ("robots", "too_small", "blank", "generic", "error") else "none",
                        "domain": dom, "detail": str(site_res.get("detail") or "")[:200], "tried": cur["tried"]}
        else:
            cur.pop("_site", None)
    return out


def _brief(res: dict) -> str:
    st = res.get("status", "?")
    if st == "ok":
        return f"ok {res.get('orig')}"
    return f"{st} {str(res.get('detail') or '')[:90]}".strip()


# ------------------------------------------------------------------ 一輪

def _save_png(dom: str, png: bytes, old_sha: str | None) -> str:
    h = lg.sha1(png)
    f = tc_dir() / png_name(dom)
    if h != old_sha or not f.exists():
        f.write_bytes(png)      # 只有圖真的變了才寫（git 不多版本）；永遠不碰 data/logos/<代號>.png
    return h


def write_attribution(items: dict) -> None:
    rows = []
    for dom, rec in sorted(items.items()):
        a = rec.get("attribution")
        if rec.get("status") != "ok" or rec.get("src") != "wikimedia" or not a:
            continue
        lic = a.get("license", "") + (f" <{a['license_url']}>" if a.get("license_url") else "")
        rows.append(f"| {dom} | [{a.get('file', '')}]({a.get('page', '')}) | {a.get('artist') or '—'} | {lic} |")
    f = tc_dir() / "ATTRIBUTION.md"
    if not rows:
        if f.exists():
            f.unlink()
        return
    text = ("# 科技透明圈外商 Logo 出處（來自 Wikimedia Commons 的圖）\n\n"
            "只收公有領域、CC0（CC BY／BY-SA 需前端署名後才開）。著作權授權不代表商標授權：各 Logo 之商標權屬各該公司所有，"
            "本站僅用於識別，不代表任何合作或背書關係。本檔由 `pipeline/sources/tc_logos.py` 自動產生，請勿手改。\n\n"
            "| 網域 | Commons 檔案 | 作者 | 授權 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    if not f.exists() or f.read_text(encoding="utf-8") != text:
        f.write_text(text, encoding="utf-8")


def run(limit: int | None = None, *, today: date | None = None, time_budget: float | None = None,
        domains: list[dict] | None = None, site_fetcher=None, wiki_fetcher=None, s2_fetcher=None) -> dict:
    """抓一輪科技透明圈外商 Logo。回摘要 dict 並寫 data/_state/tc_logo_progress.json。絕不拋例外。"""
    summary: dict = {"at": datetime.now(timezone.utc).isoformat()}
    if not config.LOGOS_ENABLED:
        summary.update(done=True, skipped="disabled")
        return summary
    try:
        return _run(summary, limit, today, time_budget, domains, site_fetcher, wiki_fetcher, s2_fetcher)
    except Exception as exc:  # noqa: BLE001 —— 科技透明圈 Logo 是裝飾，壞了不能拖垮回補
        log.warning("科技透明圈 Logo 步驟失敗（不影響其他步驟）：%s", exc)
        summary.update(done=False, error=str(exc)[:200])
        _write_state(summary)
        return summary


def _run(summary, limit, today, time_budget, domains, site_fetcher, wiki_fetcher, s2_fetcher) -> dict:
    today = today or lg._today()
    domains = load_domains() if domains is None else domains
    idx = read_index()
    items = idx.setdefault("items", {})
    todo = select_todo(domains, idx, today, 10 ** 9 if limit is None else limit)
    real = site_fetcher is None
    if real:
        lg._pil()
    t0 = time.time()
    deadline = t0 + (config.TC_LOGO_BUDGET_SEC if time_budget is None else time_budget)
    reject = frozenset(lg.known_generic(lg.read_index()))     # 個股那邊已確認的預設圖（地球、架站商圖示）一律跳過
    log.info("科技透明圈 Logo：清單 %d 個網域、已有紀錄 %d、這輪抓 %d", len(domains), len(items), len(todo))

    results: dict[str, dict] = {}
    if todo:
        tc_dir().mkdir(parents=True, exist_ok=True)
        with _px(config.TC_LOGO_PX):
            results = resolve(todo, reject, deadline, site_fetcher=site_fetcher, wiki_fetcher=wiki_fetcher,
                              s2_fetcher=s2_fetcher)
    names = {d["domain"]: d["names"] for d in domains}
    stamp, counts, failures = today.isoformat(), {}, []
    for dom, res in results.items():
        st = res.get("status", "error")
        old = items.get(dom) or {}
        rec = {"status": st, "fetched": stamp, "names": names.get(dom, []), "tried": res.get("tried", {})}
        if st == "ok":
            rec.update(src=res.get("src"), url=res.get("url"), orig=res.get("orig"),
                       sha1=_save_png(dom, res["png"], old.get("sha1")))
            if res.get("attribution"):
                rec["attribution"] = res["attribution"]
        else:
            rec["detail"] = res.get("detail", "")
            failures.append({"domain": dom, "status": st, "tried": rec["tried"]})
            if old.get("status") == "ok" and (tc_dir() / png_name(dom)).exists():
                rec = {**old, "fetched": stamp, "last_fail": st, "tried": rec["tried"]}    # 有舊圖就留著，只延後重抓
                st = "kept"
        items[dom] = rec
        counts[st] = counts.get(st, 0) + 1
    if results:
        write_index(idx)
        write_attribution(items)
    want = {d["domain"] for d in domains}
    have = sum(1 for k, r in items.items() if k in want and r.get("status") == "ok")
    left = select_todo(domains, idx, today, 10 ** 9)
    dues = [d for d in (next_due(r) for k, r in items.items() if k in want) if d]
    summary.update(done=not left, pending=len(left), attempted=len(results), counts=counts,
                   domains=len(domains), have=have, coverage=round(have / len(domains), 3) if domains else None,
                   next_due=min(dues) if dues else None, seconds=round(time.time() - t0, 1), failures=failures[:100])
    _write_state(summary)
    log.info("科技透明圈 Logo：這輪 %s，現在 %d／%d 個網域有圖", counts, have, len(domains))
    return summary


def _write_state(summary: dict) -> None:
    try:
        state_path().parent.mkdir(parents=True, exist_ok=True)
        state_path().write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        log.warning("科技透明圈 Logo 狀態檔寫不進去：%s", exc)
