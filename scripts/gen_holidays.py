"""把 pipeline/calendar/tw_holidays.yaml 轉成 site/tw_holidays.json（財報日曆與 ETF 配息行事曆共用的休市日）。
用法：python scripts/gen_holidays.py　（改了 YAML 就重跑一次，兩個檔一起 commit）"""
import json
from pathlib import Path

import yaml

root = Path(__file__).resolve().parent.parent
doc = yaml.safe_load((root / "pipeline/calendar/tw_holidays.yaml").read_text(encoding="utf-8"))
out = {"verified": doc.get("verified"), "days": {d: v["n"] for d, v in doc["days"].items()}}
(root / "site/tw_holidays.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print("寫入", len(out["days"]), "天")
