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
