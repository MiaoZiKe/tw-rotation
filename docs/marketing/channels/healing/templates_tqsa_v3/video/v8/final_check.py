#!/usr/bin/env python3
"""有旁白成片的最後驗證：python3 v8/final_check.py <名> <佇列資料夾> → 印出並寫 <佇列>/final_check.json
起音（開頭 300ms 每 20ms）、響度（人聲、片尾、全片 true peak）、語速、字幕同步 5 處（10 個時間點）、程式檢查（overlap 報告＋check_v8）。"""
import sys, json, subprocess, os, re
B = os.path.dirname(os.path.abspath(__file__)); name, q = sys.argv[1:3]
au = json.load(open(os.path.join(q, "video_audio.json"))); ov = json.load(open(os.path.join(q, "overlap_report_video.json")))
ck = json.load(open(os.path.join(q, "check_v8.json"))); sg = json.load(open(os.path.join(q, "segments.json")))
sync = json.loads(subprocess.run(["node", os.path.join(B, "sync_check.js"), name], capture_output=True, text=True).stdout)
cap = json.loads(subprocess.run(["node", os.path.join(B, "caption_check.js"), name], capture_output=True, text=True).stdout)   # 字幕四項：孤字、行首標點、關鍵詞拆行、字級 ≥64px
def meas(ss, t):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(ss), "-t", str(t), "-i", os.path.join(q, "video.mp4"), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", o)[-1]), float(re.findall(r"Peak:\s+(-?[\d.inf]+) dBFS", o)[-1])
ot = au["outro_t0"]; dur = au["dur"]; vI, vP = meas(0.2, ot - 0.2); oI, oP = meas(ot, dur - ot); fI, fP = meas(0, dur)
r = {"start_rms_db_20ms": au["start_rms_db_20ms"], "start_ok": au["start_ok"], "voice_region_lufs": vI, "outro_lufs": oI, "full_lufs": fI, "true_peak_dbtp_max": max(vP, oP, fP),
     "rate_speech_only": sg.get("rate_speech_only"), "rate_incl_pauses": sg.get("rate_incl_pauses"), "dur": dur,
     "overlap": len(ov["overlap"]), "oob": len(ov["oob"]), "edge": len(ov.get("edge", [])), "coText": len(ov.get("coText", [])), "panelChanged": ov.get("panelChangedScenes"),
     "logoGapMin": ov.get("logoGapMin"), "gapTopMax": ov.get("gapTopMax"), "gapBotMax": ov.get("gapBotMax"),
     "static_runs_gt_1_2s": ck["static_runs_gt_1_2s"], "static_max_s": ck["static_max_s"], "emphasis_min_px": min([e["min_px"] for e in ck["emphasis"]] or [None]), "emphasis_fail": ck["emphasis_fail"],
     "sync": sync, "sync_ok": all(x["ok"] for x in sync), "captions": cap["captions"], "caption_bad": cap["bad"]}
r["pass"] = bool(r["start_ok"] is True and r["overlap"] == 0 and r["oob"] == 0 and r["edge"] == 0 and r["coText"] == 0 and not r["panelChanged"] and not r["static_runs_gt_1_2s"] and not r["emphasis_fail"] and r["sync_ok"] and not r["caption_bad"] and r["true_peak_dbtp_max"] <= -1.0)
json.dump(r, open(os.path.join(q, "final_check.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in r.items() if k not in ("sync", "captions")}, ensure_ascii=False)); print("同步抽查：", [(x["id"], x["t"], x["ok"]) for x in sync])
