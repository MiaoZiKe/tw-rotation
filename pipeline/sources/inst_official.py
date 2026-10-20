"""個股三大法人「整天全市場」官方開放資料（證交所 openapi＋櫃買 openapi），一次請求一個市場。

為什麼做（Andy 2026-10-20：「確保數據每天都有更新」）：FinMind 逐檔一天要 ~1,975 次請求，每小時額度 600，
最新交易日的法人常只有幾百檔。兩個官方開放資料端點都是「一次給整個市場」，免額度、免逐檔。
白名單：openapi.twse.com.tw、www.tpex.org.tw/openapi（政府資料開放授權條款第 1 版），見
docs/source_whitelist_taifex_tpex.md。絕不碰 www.twse.com.tw/rwd 或 /fund/T86 官網端點。

端點路徑與欄位名「沒有實測 fixture」（容器連不到外網），所以：
  * 候選路徑做成清單依序試，並讀 swagger.json 把名稱含「法人」「3insti」的路徑也加進候選；
  * 欄位用關鍵字寬鬆對應（中文／英文都收），對不上就回空；
  * 每一支端點一律把「網址、HTTP 狀態、前 300 字」印進 log —— 在 daily.yml 裡跑一次就等於探測。
資料日期只用回應裡的日期欄；沒有日期欄就不收（不拿執行當下日期當交易日）。
單位：股。輸出欄位與 FinMind 逐檔一致（inst_daily）。
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, is_tradable_security, roc_to_iso, to_float

log = logging.getLogger(__name__)

TPEX_ROOT = "https://www.tpex.org.tw/openapi"
TWSE_CANDIDATES = ["/fund/T86", "/fund/TWT38U", "/fund/TWT43U", "/fund/TWT44U"]
TPEX_CANDIDATES = ["/v1/tpex_3insti_daily_trading", "/v1/tpex_3insti_trading"]
_KEYWORD = re.compile(r"法人|nstitution|3insti|3itrade|T86|TWT38U|TWT43U|TWT44U", re.I)
_HEADERS = {"Referer": "https://www.tpex.org.tw/", "Accept": "application/json, text/plain, */*"}
FIELDS = ["foreign", "foreign_dealer", "trust", "dealer_self", "dealer_hedge", "dealer"]
MIN_ROWS = 300            # 一個市場少於這個數量視為格式不對／只回一部分，不收

_cache: dict = {}


def classify(key: str) -> str | None:
    """欄位名 → 我們的欄位。只收「買賣超／Difference」那一欄（買進、賣出單欄不收）。"""
    k = re.sub(r"[\s_()（）\-]", "", str(key)).lower()
    if not any(w in k for w in ("買賣超", "difference", "netbuy", "net")):
        return None
    if "三大法人" in k or k.startswith("total"):
        return "total"
    if "投信" in k or "trust" in k:
        return "trust"
    if "外資" in k or "外陸資" in k or "foreign" in k:
        dealer = "自營" in k or "dealer" in k
        if "不含" in k or "exclud" in k or not dealer:
            return "foreign"
        return "foreign_dealer" if "包含" not in k and "includ" not in k else None
    if "避險" in k or "hedg" in k:
        return "dealer_hedge"
    if "自行" in k or "proprietary" in k or "self" in k:
        return "dealer_self"
    if "自營" in k or "dealer" in k:
        return "dealer"
    return None


def _pick(row: dict, *needles: str):
    for k, v in row.items():
        kk = str(k).lower().replace(" ", "")
        if any(n in kk for n in needles):
            return v
    return None


def parse_rows(raw: list) -> pd.DataFrame:
    """一支端點的原始 list[dict] → 長度＝檔數的 DataFrame（date, code, 有找到的欄位）。對不上回空。"""
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
        return pd.DataFrame()
    cols = {k: classify(k) for k in raw[0]}
    cols = {k: f for k, f in cols.items() if f}
    if not cols:
        return pd.DataFrame()
    rows = []
    for r in raw:
        code = clean_code(_pick(r, "代號", "code"))
        d = roc_to_iso(_pick(r, "date", "日期"))
        if not code or not d or not is_tradable_security(code):
            continue
        rec = {"date": d, "code": code}
        for k, f in cols.items():
            v = to_float(r.get(k))
            if v is not None:
                rec[f] = rec.get(f, 0.0) + v if f in rec else v
        rows.append(rec)
    return pd.DataFrame(rows)


def merge_parts(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """把一個市場的各端點（可能分外資／投信／自營三支）合成寬表，補齊欄位並算合計。"""
    parts = [p for p in parts if p is not None and not p.empty]
    if not parts:
        return pd.DataFrame()
    m = parts[0]
    for p in parts[1:]:
        new = [c for c in p.columns if c not in ("date", "code") and c not in m.columns]
        m = m.merge(p[["date", "code"] + new], on=["date", "code"], how="outer")
    have = set(m.columns)
    # 外資、投信、自營三類都要找得到才算數，否則寧可回空走 FinMind（缺一欄會讓合計默默變小）
    if "foreign" not in have or "trust" not in have or not ({"dealer", "dealer_self", "dealer_hedge"} & have):
        log.warning("官方法人欄位不齊（找到：%s），不收", sorted(have - {"date", "code"}))
        return pd.DataFrame()
    for c in FIELDS:
        if c not in m.columns:
            m[c] = 0.0
    m[FIELDS] = m[FIELDS].fillna(0.0)
    if "dealer" not in have:
        m["dealer"] = m["dealer_self"] + m["dealer_hedge"]
    m["foreign_total"] = m["foreign"] + m["foreign_dealer"]
    m["inst_total"] = m["foreign_total"] + m["trust"] + m["dealer"]
    return m[["date", "code", "foreign", "foreign_dealer", "foreign_total",
              "trust", "dealer_self", "dealer_hedge", "dealer", "inst_total"]]


def _get(url: str) -> tuple[int | None, object]:
    """打一次；回 (HTTP 狀態, JSON 或 None)。無論成敗都把網址、狀態、前 300 字印進 log（探測用）。"""
    try:
        r = http.session().get(url, headers=_HEADERS, timeout=config.HTTP_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        log.warning("官方法人 %s 連線失敗：%s", url, exc)
        return None, None
    body = r.text[:300].replace("\n", " ")
    log.info("官方法人探測 %s -> HTTP %s，前300字：%s", url, r.status_code, body)
    if r.status_code != 200:
        return r.status_code, None
    try:
        return 200, r.json()
    except ValueError:
        return 200, None


def _discover(swagger_url: str, prefix: str) -> list[str]:
    """讀 swagger.json，把路徑含法人關鍵字的也列為候選（路徑名猜錯時的自救）。"""
    st, sw = _get(swagger_url)
    if not isinstance(sw, dict):
        return []
    found = []
    for p, v in (sw.get("paths") or {}).items():
        if _KEYWORD.search(p + str(v)[:600]):
            log.info("官方法人 swagger 發現路徑：%s", p)
            found.append(p)
    return found


def _market(root: str, swagger: str, cands: list[str], label: str) -> pd.DataFrame:
    paths = list(cands)
    for p in _discover(swagger, root):
        if p not in paths and p.lstrip("/") not in [c.lstrip("/") for c in paths]:
            paths.append(p if p.startswith("/") else "/" + p)
    parts = []
    for p in paths:
        st, raw = _get(root + p)
        part = parse_rows(raw) if isinstance(raw, list) else pd.DataFrame()
        if part.empty:
            if st == 200 and isinstance(raw, list) and raw:
                log.warning("官方法人 %s 欄位對不上；欄位名：%s", p, list(raw[0])[:20])
            continue
        parts.append(part)
        # 單一端點就湊齊三類時不必再試其餘候選
        if not merge_parts(parts).empty:
            break
    df = merge_parts(parts)
    if len(df) < MIN_ROWS:
        if not df.empty:
            log.warning("官方法人 %s 只有 %d 檔（< %d），不收", label, len(df), MIN_ROWS)
        return pd.DataFrame()
    # 只收「最新那一天」：openapi 多半只給一日，混到舊日代表格式不是日報
    df = df[df["date"] == df["date"].max()]
    log.info("官方法人 %s：%s，%d 檔", label, df["date"].iloc[0], len(df))
    return df


def fetch_all(use_cache: bool = True) -> pd.DataFrame:
    """上市＋上櫃最新一日的個股三大法人。任何失敗回空（呼叫端照舊走 FinMind）。同一程序只打一次。"""
    if use_cache and "df" in _cache:
        return _cache["df"]
    frames = []
    for label, root, sw, cands in (
            ("上市", config.TWSE_OPENAPI, config.TWSE_OPENAPI + "/swagger.json", TWSE_CANDIDATES),
            ("上櫃", TPEX_ROOT, TPEX_ROOT + "/swagger.json", TPEX_CANDIDATES)):
        try:
            d = _market(root, sw, cands, label)
        except Exception:  # noqa: BLE001
            log.exception("官方法人 %s 處理失敗", label)
            d = pd.DataFrame()
        if not d.empty:
            frames.append(d)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    _cache["df"] = df
    return df
