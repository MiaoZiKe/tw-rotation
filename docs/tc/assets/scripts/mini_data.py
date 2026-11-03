"""只產出剖析圖頁面開站需要的最小資料（完整 build_payload 在這個容器會 OOM／磁碟滿）。"""
import json, os, sys
os.chdir("/home/user/tw-rotation/.claude/worktrees/agent-a269082c5aeb4fe8e")
sys.path.insert(0, os.getcwd())
import pandas as pd
import pipeline.build_payload as bp
from pipeline import config
from pipeline.groups import loader
config.SITE_DATA.mkdir(parents=True, exist_ok=True)
im = bp.industry_map(pd.DataFrame(), {}, [], pd.DataFrame(), "2026-11-03", {})
bp._write("industry_map", im)
bp._write("supply_chain", loader.supply_chain())
bp._write("link_index", bp.link_index(im, loader.supply_chain()))
bp._write("meta", {"status": "ok", "generated_at": "2026-11-03T18:00:00+08:00", "latest": "2026-11-03", "date": "2026-11-03"})
print(sorted(os.listdir(config.SITE_DATA)))
