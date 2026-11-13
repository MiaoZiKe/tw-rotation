"""由 docs/ai_office/rewards_demo.json（W45，示範）展開成 site/office/world/cfg/rewards.json（近 6 週）。
用途：績效總表「切週次」要有多週資料；真資料上線（hr-officer 每週一產出）之前用這份示範。
格式：{version, demo, reasonLabels, rules, accLabels, weeks:[{week, prevWeek, range, ceo, depts[]}（新到舊）]}。
前端不重算等第／設備等級／配件，全部讀這裡的結果（rewards_design.md 8.2 設計原則）。
本機重跑：python scripts/gen_office_rewards_demo.py
"""
import json, hashlib, copy, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs/ai_office/rewards_demo.json")
DST = os.path.join(ROOT, "site/office/world/cfg/rewards.json")
d = json.load(open(SRC, encoding="utf-8"))
RULE = d["rules"]["grade"]
LV = d["rules"]["levelByGrade"]
WEEKS = ["2026-W45", "2026-W44", "2026-W43", "2026-W42", "2026-W41", "2026-W40"]
RANGES = [["2026-11-02", "2026-11-08"], ["2026-10-26", "2026-11-01"], ["2026-10-19", "2026-10-25"], ["2026-10-12", "2026-10-18"], ["2026-10-05", "2026-10-11"], ["2026-09-28", "2026-10-04"]]


def grade_of(s):
    for th, g in RULE:
        if s >= th:
            return g
    return "F"


def noise(key, i, amp):
    h = int(hashlib.md5(f"{key}|{i}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return (h * 2 - 1) * amp


def chain(key, s0, prev0):
    """s[0]=本週；s[1]=上週（用示範的 prev）；之後每週加一點可重現的雜訊。回傳 7 個分數（算 6 週的升降用）"""
    out = [s0, prev0 if prev0 is not None else s0]
    for i in range(2, 7):
        out.append(round(max(32, min(99, out[-1] + noise(key, i, 4.5))), 1))
    return out


ACC_BY = {
    "S": ["grade_chip", "ring_gold", "halo", "star_gold", "cape_gold", "glasses_gold", "nameplate_gold", "trophy"],
    "A": ["grade_chip", "ring_silver", "star_silver", "cape_silver", "glasses_silver", "scarf_satin", "nameplate_silver", "frame"],
    "B": ["grade_chip"],
    "C": ["grade_chip", "todo_stack"],
    "D": ["grade_chip", "ring_amber", "lamp_amber", "mentor_book"],
    "E": ["grade_chip", "ring_amber", "lamp_amber", "mentor_book"],
    "F": ["grade_chip", "pause_plate"],
}
ACC_LABELS = {
    "grade_chip": "等第字章", "ring_gold": "金色腳下光圈", "ring_silver": "銀色腳下光圈", "ring_amber": "琥珀腳下細環", "halo": "頭頂光環",
    "star_gold": "金星章", "star_silver": "銀星章", "cape_gold": "金邊小披風", "cape_silver": "銀色小披風", "glasses_gold": "金框眼鏡", "glasses_silver": "銀框眼鏡",
    "scarf_satin": "緞面領巾", "nameplate_gold": "金色桌牌", "nameplate_silver": "銀色桌牌", "trophy": "桌上獎盃", "frame": "桌上獎狀框", "mvp_sash": "本週最佳員工彩帶",
    "pet_rare": "稀有寵物", "sprout": "新進小綠芽", "todo_stack": "桌上待辦文件", "lamp_amber": "琥珀桌燈", "mentor_book": "栽培書本與導師名牌", "pause_plate": "暫停桌牌",
}
TASK_KEYS = ("todo", "doing", "done")


def jitter_tasks(t, key, i):
    return {k: max(0, int(round(t[k] + noise(key + k, i, 1.6)))) for k in TASK_KEYS}


def jitter_rate(v, key, i, amp=0.07):
    return round(max(0.02, min(1.0, v + noise(key, i, amp))), 2)


def jitter_ratio(v, key, i, amp=0.08):
    return round(max(0.5, v + noise(key, i, amp)), 2)


def make_week(wi):
    wk = copy.deepcopy(d) if wi == 0 else None
    base = copy.deepcopy(d)
    out = {"week": WEEKS[wi], "prevWeek": WEEKS[wi + 1] if wi + 1 < len(WEEKS) else "", "range": RANGES[wi]}

    def row(key, src, scores, dept_level=None, flag_src=None):
        r = copy.deepcopy(src)
        if wi:
            if src.get("grade") is None:
                pass
            else:
                r["score"] = scores[wi]
                r["prev"] = scores[wi + 1]
                r["delta"] = round(scores[wi] - scores[wi + 1], 1)
                if r["delta"] == 0:
                    r["delta"] = 0
                r["grade"] = grade_of(r["score"])
                if "tasks" in r:
                    r["tasks"] = jitter_tasks(r["tasks"], key, wi)
                for k in ("done_rate", "ontime", "reject_rate"):
                    if k in r:
                        r[k] = jitter_rate(r[k], key + k, wi)
                for k in ("token_ratio", "time_ratio"):
                    if k in r:
                        r[k] = jitter_ratio(r[k], key + k, wi)
                if "acc" in r:
                    r["acc"] = list(ACC_BY[r["grade"]])
                r["streak"] = max(0, r.get("streak", 0) - wi) if r["grade"] in ("S", "A") else 0
                if r["grade"] in ("S", "A", "B"):
                    r["top_loss"] = r["top_loss"] if r.get("top_loss") in ("speed", "token") else ""
                    r["advice"] = r["advice"] if r["top_loss"] else ""
        # 上週等第（篩選「本週降級」用）：由上週分數套同一組門檻，產生資料時就算好，前端不再重算
        if r.get("grade") is not None and r.get("prev") is not None:
            r["prevGrade"] = grade_of(r["prev"])
        return r

    ceo_scores = chain("ceo", base["ceo"]["score"], base["ceo"]["prev"])
    ceo = row("ceo", base["ceo"], ceo_scores)
    ceo["level"] = LV[ceo["grade"]] if wi else ceo["level"]
    out["ceo"] = ceo
    depts = []
    for dp in base["depts"]:
        ds = chain(dp["id"], dp["score"], dp["prev"])
        r = row(dp["id"], dp, ds)
        r["id"] = dp["id"]
        r["members"] = {}
        for mid, m in dp["members"].items():
            ms = chain(mid, m["score"], m["prev"]) if m.get("grade") is not None else None
            r["members"][mid] = row(mid, m, ms)
        if wi:
            r["level"] = LV[r["grade"]]
            r.pop("levelPending", None)
            if r["grade"] in ("D", "E", "F"):
                r["flag"] = dp["flag"] or {"text": "待加強", "reason": dp.get("top_loss") or "quality"}
                r["top_loss"] = (r["flag"] or {}).get("reason", "quality")
                r["advice"] = dp.get("advice") or "補強建議：先看成員清單中標示加強的人"
            else:
                r["flag"] = None
        depts.append(r)
    depts.sort(key=lambda x: -x["score"])
    out["depts"] = depts
    return out


# ceo 的 dims 在每週都保留（總表展開看六個面向）
weeks = [make_week(i) for i in range(len(WEEKS))]
data = {
    "version": 1,
    "demo": True,
    "note": "示範資料（全是假的）。真資料由 hr-officer 每週一產出，格式見 docs/ai_office/rewards_design.md 第八節。",
    "generatedAt": d["generatedAt"],
    "reasonLabels": {k: v for k, v in d["reasonLabels"].items() if k},
    "rules": d["rules"],
    "accLabels": ACC_LABELS,
    "dimLabels": {"assigned_done": "交辦完成率與證據", "rejects": "被退件與重複提醒", "honest": "回報如實", "dispatch_token": "派工效率與 Token", "deploy_stuck": "部署成功率與卡住", "proactive": "主動與維修閉環"},
    "weeks": weeks,
}
json.dump(data, open(DST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("寫出", DST, os.path.getsize(DST), "bytes；週數", len(weeks))
