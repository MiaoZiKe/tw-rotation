"""把 pipeline/calendar/tw_holidays.yaml 轉成 workers/gh-cron/src/holidays.js（Worker 判斷交易日用）。
用法：python scripts/gen_gh_cron_holidays.py　（改了休市日 YAML 就重跑，兩個檔一起 commit；tests/test_gh_cron.py 會檢查兩邊同步）"""
from pathlib import Path

import yaml

root = Path(__file__).resolve().parent.parent
doc = yaml.safe_load((root / "pipeline/calendar/tw_holidays.yaml").read_text(encoding="utf-8"))
days = sorted(str(d) for d in doc["days"])
lines = ["// 由 scripts/gen_gh_cron_holidays.py 從 pipeline/calendar/tw_holidays.yaml 產生，請勿手改。",
         "export const HOLIDAYS = new Set(["]
lines += [f"  '{d}'," for d in days]
lines += ["]);", ""]
(root / "workers/gh-cron/src/holidays.js").write_text("\n".join(lines), encoding="utf-8")
print("寫入", len(days), "天")
