"""從 `price_daily` 取「代號 → 名稱」的對照表。

為什麼要單獨一支（2026-09-20）
------------------------------
`price_daily` 的 `name` 欄是後來才加的，**只有 2026-09-09 之後的列有值**
（實測全表 98.7% 是 NaN）。而取名字的地方習慣寫成：

    px.drop_duplicates("code").set_index("code")["name"].to_dict()

`drop_duplicates` 預設留**第一筆**，而 `px` 通常已經切到最近 60 天、起點在三個月前
—— 於是每一檔拿到的都是 NaN，再被 `str()` 變成字串 `"nan"` 寫進 JSON，
使用者在畫面上看到的就是「nan 2330」。

同一行程式碼在兩個地方各寫了一次（`rrg.sankey_daily` 的資金去向桑基圖、
`flow.concentration_members` 的資金集中度成分股），所以 Andy 只回報了桑基圖那一個，
另一個是掃 JSON 才抓到的。抽成這一支就是為了**不要再有第三個地方各寫一次**。

判準：名字以**最新**那一筆為準（公司改名的話要跟著改），查不到就退回代號本身
—— 寧可顯示「2330」也不要顯示「nan」。
"""
from __future__ import annotations

import pandas as pd


def latest_names(px: pd.DataFrame) -> dict[str, str]:
    """`price_daily` 切片 → {代號: 名稱}。沒有 name 欄或全空就回空字典。"""
    if px is None or px.empty or "name" not in px.columns or "code" not in px.columns:
        return {}
    cols = ["code", "name"] + (["date"] if "date" in px.columns else [])
    nm = px[cols].dropna(subset=["name"]).copy()
    s = nm["name"].astype(str).str.strip()
    # 字串 "nan"／"none"／空字串都當成沒有名字（來源不同，三種都出現過）
    nm = nm[s.str.lower().ne("nan") & s.str.lower().ne("none") & s.ne("")]
    if nm.empty:
        return {}
    if "date" in nm.columns:
        nm = nm.sort_values("date")
    nm = nm.drop_duplicates("code", keep="last")
    return {str(k): str(v).strip() for k, v in zip(nm["code"], nm["name"])}


def name_or_code(name_of: dict, code: str) -> str:
    """查不到名字就退回代號本身。畫面上寧可是「2330」也不要是「nan」。"""
    return name_of.get(str(code)) or str(code)
