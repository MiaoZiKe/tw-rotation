"""第四輪補資料（需要網路與金鑰；在 GitHub Actions 或有 FRED_API_KEY／FINMIND_TOKEN 的環境執行）。

只走 store.append（只增不改、依 key 去重），不覆寫 parquet。第四輪開發環境連不到 FRED／FinMind（出口代理 403），
所以這支「沒有在開發環境實測過」，執行前請加 --dry-run 先看抓到幾列。
  python scripts/backfill_round4_data.py --dry-run
  python scripts/backfill_round4_data.py --apply
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.sources import macro, mktfut  # noqa: E402
from pipeline.util import store  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--vix-start", default="1990-01-01")
    ap.add_argument("--fut-start", default="2016-01-01")
    a = ap.parse_args()
    apply = a.apply and not a.dry_run
    # 1) VIX：FRED VIXCLS 走既有 macro 表（key=date+series），不必改 config.TABLES
    vix = macro.fred_series("VIXCLS", start=a.vix_start)
    print("VIXCLS 列數", len(vix), vix.attrs.get("error", ""))
    if apply and not vix.empty:
        print("macro append", store.append("macro", vix))
    # 2) 事件日曆歷史發布日（CPI／非農／GDP／PCE）
    cal = macro.release_calendar(days_back=3650, days_ahead=0)
    print("release_calendar 列數", len(cal), cal.attrs.get("error", ""))
    if apply and not cal.empty:
        print("macro_calendar append", store.append("macro_calendar", cal))
    # 3) 更長的法人／期貨／資券歷史（FinMind；402 即停，不要 wait）
    got = mktfut.collect(a.fut_start, a.vix_start and "2020-12-31", wait=False)
    for t, df in got.items():
        print(t, "列數", len(df))
        if apply and not df.empty:
            print(t, "append", store.append(t, df))


if __name__ == "__main__":
    main()
