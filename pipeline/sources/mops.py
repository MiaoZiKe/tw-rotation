"""公開資訊觀測站的**重大訊息**（證交所 OpenAPI t187ap04）。

Andy 的需求第 62／80 項：「資訊要定期更新，包含新聞與公司消息」。
新聞那一半 2026-09 就做完了，重大訊息一直掛著 🟡「等 Andy 在 Actions 按一次 Run workflow」——
但他 **2026-09-14 16:51 就按了**，fixture 一直躺在 `docs/fixtures/material_news_probe.json`，
端點回 200、欄位齊全。缺的從頭到尾只有這支 parser，
也就是說我們把自己的待辦寫成了他的待辦，掛了五天（DECISIONS #215）。

端點（依 fixture 實測，2026-09-14）
----------------------------------
  /opendata/t187ap04_L   上市公司每日重大訊息
  /opendata/t187ap04_O   上櫃／興櫃公司每日重大訊息

欄位（照抄 fixture，不要憑印象寫）
--------------------------------
  出表日期 / 發言日期 / 事實發生日  民國，YYYMMDD
  發言時間                          HHMMSS 但**沒有補零也沒有冒號**：
                                    fixture 裡是 `"70003"`（5 碼）＝ 07:00:03。
                                    先 zfill(6) 再切，不然會解析成 70:00:3。
  公司代號 / 公司名稱
  主旨                              ★ 真正的鍵名是 `"主旨 "`，**後面有一個空白**。
                                    直接用 row["主旨"] 會拿不到東西。這是 fixture 量到的事實，
                                    不是猜的 —— 所以兩個鍵都試。
  符合條款                          例：「第51款」
  說明                              多行，含 \\r\\n

為什麼不併進 `news` 表
----------------------
新聞是媒體寫的，重大訊息是**公司自己公告的**。M4 事件面要否決一筆進場，
靠的是後者（減資、解散、訴訟、重大處分、財報更正都在這裡），
兩者的可信度與用途都不同，混在一起會讓「有沒有理由不進場」失去意義。

跟其他來源一樣：抓不到一律回空 DataFrame，不要讓整條管線炸掉。
"""
from __future__ import annotations

import logging

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, roc_to_iso

log = logging.getLogger(__name__)

# 真正的鍵名帶尾端空白（fixture 實測），所以兩個都要試
_SUBJECT_KEYS = ("主旨 ", "主旨")


def _pick(row: dict, *names: str) -> str:
    for n in names:
        v = row.get(n)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _hhmmss(value) -> str:
    """`70003` → `07:00:03`。補零是必要的：不補會變成 70:00:3。"""
    s = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not s:
        return ""
    s = s.zfill(6)[:6]
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"


def _parse(rows: list[dict], market: str) -> pd.DataFrame:
    out = []
    for r in rows:
        code = clean_code(r.get("公司代號"))
        if not code:
            continue
        date = roc_to_iso(r.get("發言日期"))
        subject = _pick(r, *_SUBJECT_KEYS)
        if not date or not subject:
            continue
        time_s = _hhmmss(r.get("發言時間"))
        out.append({
            # news_id 要能跨天去重：同一家公司同一天可能發好幾則
            "news_id": f"mops-{code}-{date}-{time_s.replace(':', '')}",
            "code": code,
            "name": _pick(r, "公司名稱"),
            "date": date,
            "time": time_s,
            "market": market,
            "subject": subject,
            "clause": _pick(r, "符合條款"),
            "occurred": roc_to_iso(r.get("事實發生日")) or None,
            # 說明很長（fixture 裡有超過 1,000 字的），截到 800 字就夠前端摘要用；
            # 要看全文的人本來就該去公開資訊觀測站看原文。
            "detail": _pick(r, "說明")[:800],
        })
    if not out:
        return pd.DataFrame()
    df = pd.DataFrame(out)
    return df.drop_duplicates(subset=["news_id"])


def material_news() -> pd.DataFrame:
    """上市＋上櫃的當日重大訊息。任一邊失敗就只回另一邊，兩邊都失敗回空。"""
    frames = []
    for key, market in (("material_news_twse", "TWSE"), ("material_news_tpex", "TPEX")):
        url = config.TWSE_OPENAPI + config.TWSE_ENDPOINTS[key]
        data = http.get(url)
        if not isinstance(data, list) or not data:
            log.warning("重大訊息 %s 沒有資料（%s）", market, url)
            continue
        df = _parse(data, market)
        if not df.empty:
            frames.append(df)
            log.info("重大訊息 %s：%d 則", market, len(df))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["news_id"])


# ================================================================ 董監事持股（2026-09-27）
# Andy 的券商 App「大戶」分頁有一欄「內部人持股」、右上一顆「董監持股」。
# 來源：證交所 OpenAPI /opendata/t187ap11_L「上市公司董監事持股餘額明細資料」（政府資料開放平臺 資料集 22811，
# 政府資料開放授權條款第 1 版 —— 跟 t187ap03／04／05／14 同一類，見 docs/source_whitelist_taifex_tpex.md 的判準）；
# 上櫃同一份申報在櫃買 OpenAPI 叫 mopsfin_t187ap11_O。**每月一次**（次月 20 日前後公布上個月底的餘額），只給最新一個月。
# ⚠ 欄位是 WebSearch 摘要列出來的（出表日期、資料年月、公司代號、公司名稱、職稱、姓名、選任時持股、目前持股、
#   設質股數、設質股數佔持股比例、內部人關係人目前持股合計…），**容器連不到 openapi，沒有實測過**。
#   所以 parser 對鍵名寬鬆（去空白、幾個別名都試），必要欄位缺了就回空並把看到的鍵名記進 log，
#   第一次在 Actions 跑完看 log 就知道對不對 —— 回空不會弄壞任何東西（個股頁那一格顯示「尚無資料」）。
INSIDER_ENDPOINTS = [
    ("TWSE", config.TWSE_OPENAPI + "/opendata/t187ap11_L"),
    ("TPEX", config.TPEX_OPENAPI + "/mopsfin_t187ap11_O"),
]


def _num(v) -> float | None:
    s = str(v if v is not None else "").replace(",", "").strip()
    try:
        return float(s) if s not in ("", "-", "--") else None
    except ValueError:
        return None


def _norm_keys(r: dict) -> dict:
    return {str(k).strip().replace(" ", ""): v for k, v in r.items()}


def _is_director(title: str) -> bool:
    """董事（含董事長、副董事長、獨立董事、法人董事與其代表人）或監察人。經理人、大股東不算董監。"""
    t = str(title or "")
    return ("董事" in t) or ("監察人" in t)


def parse_insider(rows: list[dict], market: str) -> pd.DataFrame:
    """董監事持股明細 → **每家公司每月一列**的彙總（不存個人姓名：頁面只要合計，姓名留在官方原檔）。

    欄位：ym（YYYY-MM，資料年月）、code、market、
      director_shares  ＝ 職稱含「董事」或「監察人」的「目前持股」合計（股）
      insider_shares   ＝ 全部列的「目前持股」合計（這個資料集若含經理人／大股東，也一起算）
      director_pledged ＝ 董監的設質股數合計（股）
      n_directors、n_rows
    去重：同一家公司同一個姓名出現多列（一人兼兩個職稱）只算一次、取最大的那一列 ——
      重複計算會讓比例超過 100%（網路上已經有人踩過）。法人董事與其代表人是不同的持有人，各算各的。
    例外：資料年月、公司代號、目前持股任一個解析不出來的列丟掉；全部丟光回空 DataFrame 並把鍵名記進 log。
    """
    recs = []
    for raw in rows or []:
        if not isinstance(raw, dict):
            continue
        r = _norm_keys(raw)
        code = clean_code(r.get("公司代號") or r.get("SecuritiesCompanyCode"))
        ym = r.get("資料年月") or r.get("年月")
        cur = _num(r.get("目前持股") if r.get("目前持股") is not None else r.get("目前持股數"))
        if not code or ym is None or cur is None:
            continue
        s = "".join(ch for ch in str(ym) if ch.isdigit())
        if len(s) < 5:
            continue
        y, m = int(s[:-2]), int(s[-2:])
        if y < 1911:
            y += 1911                      # 民國年
        if not 1 <= m <= 12:
            continue
        recs.append({"ym": f"{y:04d}-{m:02d}", "code": code, "title": str(r.get("職稱") or ""),
                     "name": str(r.get("姓名") or "").strip(), "cur": cur,
                     "pledged": _num(r.get("設質股數")) or 0.0})
    if not recs:
        if rows:
            first = next((x for x in rows if isinstance(x, dict)), {})
            log.warning("董監持股 %s：%d 列都解析不出來（鍵名：%s）", market, len(rows),
                        sorted(_norm_keys(first).keys())[:20])
        return pd.DataFrame()
    d = pd.DataFrame(recs)
    d["dir"] = d["title"].map(_is_director)
    # 同名只算一次（沒寫姓名的列無法判斷是不是同一人，照列算）；兼任時董監身分優先保留
    named = d[d["name"] != ""].sort_values(["dir", "cur"]).drop_duplicates(["ym", "code", "name"], keep="last")
    d = pd.concat([named, d[d["name"] == ""]], ignore_index=True)
    out = []
    for (ym, code), g in d.groupby(["ym", "code"]):
        gd = g[g["dir"]]
        out.append({"ym": ym, "code": code, "market": market,
                    "director_shares": float(gd["cur"].sum()) if len(gd) else None,
                    "director_pledged": float(gd["pledged"].sum()) if len(gd) else None,
                    "insider_shares": float(g["cur"].sum()),
                    "n_directors": int(len(gd)), "n_rows": int(len(g))})
    return pd.DataFrame(out)


def insider_holdings() -> pd.DataFrame:
    """上市＋上櫃的董監事持股（每家公司每月一列）。任一邊失敗只回另一邊，兩邊都失敗回空。"""
    frames = []
    for market, url in INSIDER_ENDPOINTS:
        data = http.get(url)
        if not isinstance(data, list) or not data:
            log.warning("董監持股 %s 沒有資料（%s）", market, url)
            continue
        df = parse_insider(data, market)
        if not df.empty:
            frames.append(df)
            log.info("董監持股 %s：%d 家、資料年月 %s", market, len(df), sorted(df["ym"].unique())[-1])
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(["ym", "code"], keep="first")
