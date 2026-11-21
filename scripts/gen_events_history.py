"""產生 pipeline/groups/events_history.yaml 的初稿（只在第一次建檔或要整批重算規則型事件時跑）。

為什麼有這支：資料湖的 macro_calendar 只有近期，事件分析需要十幾年的歷史日期。
這份 yaml 之後是「人工維護」的唯一來源，每筆都有 src（出處）與 conf（信心度）：
  高 ＝ 官方公布的固定日期（選舉日、聯準會公布的日程）
  中 ＝ 依公開日程整理、尚未逐筆對官網（FOMC、台積電法說會日期）
  低 ＝ 規則推算（非農＝每月第一個週五、台指期結算＝每月第三個週三，遇假日未調整）
  資料 ＝ 由資料湖統計得出（除權息旺季＝該年除權息檔數最多的那一天）
lag：事件發生在美國時間時，台股要隔天才反應，事件窗從「日期＋lag 之後的第一個交易日」起算。
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline" / "groups" / "events_history.yaml"

FOMC = """2013: 01-30 03-20 05-01 06-19 07-31 09-18 10-30 12-18
2014: 01-29 03-19 04-30 06-18 07-30 09-17 10-29 12-17
2015: 01-28 03-18 04-29 06-17 07-29 09-17 10-28 12-16
2016: 01-27 03-16 04-27 06-15 07-27 09-21 11-02 12-14
2017: 02-01 03-15 05-03 06-14 07-26 09-20 11-01 12-13
2018: 01-31 03-21 05-02 06-13 08-01 09-26 11-08 12-19
2019: 01-30 03-20 05-01 06-19 07-31 09-18 10-30 12-11
2020: 01-29 03-03 03-15 04-29 06-10 07-29 09-16 11-05 12-16
2021: 01-27 03-17 04-28 06-16 07-28 09-22 11-03 12-15
2022: 01-26 03-16 05-04 06-15 07-27 09-21 11-02 12-14
2023: 02-01 03-22 05-03 06-14 07-26 09-20 11-01 12-13
2024: 01-31 03-20 05-01 06-12 07-31 09-18 11-07 12-18
2025: 01-29 03-19 05-07 06-18 07-30 09-17 10-29 12-10
2026: 01-28 03-18 04-29 06-17 07-29 09-16 10-28 12-09"""

TSMC = """2013: 01-17 04-16 07-18 10-17
2014: 01-16 04-17 07-17 10-16
2015: 01-15 04-16 07-16 10-15
2016: 01-14 04-14 07-14 10-13
2017: 01-12 04-13 07-13 10-12
2018: 01-18 04-19 07-19 10-18
2019: 01-17 04-18 07-18 10-17
2020: 01-16 04-16 07-16 10-15
2021: 01-14 04-15 07-15 10-14
2022: 01-13 04-14 07-14 10-13
2023: 01-12 04-20 07-20 10-19
2024: 01-18 04-18 07-18 10-17
2025: 01-16 04-17 07-17 10-16
2026: 01-15 04-16 07-16 10-15"""

US_PRES = ["2000-11-07", "2004-11-02", "2008-11-04", "2012-11-06", "2016-11-08", "2020-11-03", "2024-11-05"]
US_MID = ["2002-11-05", "2006-11-07", "2010-11-02", "2014-11-04", "2018-11-06", "2022-11-08", "2026-11-03"]
TW_PRES = ["2000-03-18", "2004-03-20", "2008-03-22", "2012-01-14", "2016-01-16", "2020-01-11", "2024-01-13"]
TW_LOCAL = ["2014-11-29", "2018-11-24", "2022-11-26", "2026-11-28"]


def parse(block: str, t: str, name: str, src: str, conf: str, lag: int):
    out = []
    for line in block.splitlines():
        y, rest = line.split(":")
        for md in rest.split():
            out.append({"d": f"{y}-{md}", "t": t, "name": name, "src": src, "conf": conf, "lag": lag})
    return out


def nth_weekday(y: int, m: int, wd: int, n: int) -> dt.date:
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def main():
    ev = []
    ev += parse(FOMC, "fomc", "FOMC 利率決議", "聯準會 FOMC 日程 https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm（決議日＝會期第二天；2020-03 兩次為臨時會議）", "中", 1)
    ev += parse(TSMC, "tsmc", "台積電法說會", "台積電投資人關係 https://investor.tsmc.com/chinese/quarterly-results（每季第二個月中旬週四）", "中", 0)
    for d in US_PRES:
        ev.append({"d": d, "t": "us_pres", "name": "美國總統大選", "src": "美國聯邦選舉委員會，11 月第一個週二之後的第一個週二", "conf": "高", "lag": 1})
    for d in US_MID:
        ev.append({"d": d, "t": "us_mid", "name": "美國期中選舉", "src": "美國聯邦選舉委員會，11 月第一個週二之後的第一個週二", "conf": "高", "lag": 1})
    for d in TW_PRES:
        ev.append({"d": d, "t": "tw_pres", "name": "台灣總統大選", "src": "中央選舉委員會 https://www.cec.gov.tw", "conf": "高", "lag": 0})
    for d in TW_LOCAL:
        ev.append({"d": d, "t": "tw_local", "name": "台灣地方選舉", "src": "中央選舉委員會 https://www.cec.gov.tw（2026 為公告日期）", "conf": "高", "lag": 0})
    for y in range(2000, 2027):
        for m in range(1, 13):
            if y == 2026 and m > 12:
                continue
            ev.append({"d": str(nth_weekday(y, m, 4, 1)), "t": "nfp", "name": "美國非農就業", "src": "規則推算：每月第一個週五（BLS 實際發布日偶有調整，未逐月核對）", "conf": "低", "lag": 1})
            ev.append({"d": str(nth_weekday(y, m, 2, 3)), "t": "settle", "name": "台指期月結算", "src": "規則推算：每月第三個週三（遇假日順延，未逐月核對）https://www.taifex.com.tw", "conf": "低", "lag": 0})
    # 除權息旺季：每年除權息檔數最多的那一天（資料湖 dividend_results）
    try:
        import glob
        df = pd.concat([pd.read_parquet(f) for f in glob.glob(str(ROOT / "data" / "dividend_results" / "**" / "*.parquet"), recursive=True)])
        df["y"] = df["date"].astype(str).str[:4]
        for y, g in df.groupby("y"):
            if int(y) < 2009:
                continue
            c = g.groupby("date").size()
            ev.append({"d": str(c.idxmax()), "t": "exdiv", "name": "除權息旺季（當年除權息檔數最多的一天）", "src": f"資料湖 dividend_results 統計，當天 {int(c.max())} 檔", "conf": "資料", "lag": 0})
    except Exception as exc:  # noqa: BLE001
        print("除權息統計失敗：", exc)
    ev = [e for e in ev if e["d"] <= "2026-12-31"]
    ev.sort(key=lambda e: (e["d"], e["t"]))
    doc = {
        "types": {
            "fomc": "FOMC 利率決議", "nfp": "美國非農", "us_pres": "美國總統大選", "us_mid": "美國期中選舉",
            "tw_pres": "台灣總統大選", "tw_local": "台灣地方選舉", "tsmc": "台積電法說會", "settle": "台指期結算日", "exdiv": "除權息旺季",
        },
        "events": ev,
    }
    OUT.write_text("# 交易練習室事件表（人工維護；每筆有 src 出處與 conf 信心度，說明見 scripts/gen_events_history.py）\n" + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(ev), "筆 →", OUT)


if __name__ == "__main__":
    main()
