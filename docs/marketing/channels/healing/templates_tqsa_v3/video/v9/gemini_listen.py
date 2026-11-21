#!/usr/bin/env python3
"""四道驗證②聽感：把成品音訊交 Gemini 音訊理解，逐句回報斷續／卡頓／字被切掉／停頓不自然＋時間點（2026-11-22）。
用法：python3 v9/gemini_listen.py <佇列資料夾> [音訊檔（預設 video.mp4）] [--end 秒]
金鑰由代理注入（header 帶固定字串 injected-by-proxy），不寫進任何檔案。結果寫 <資料夾>/gemini_listen.json，印出被標的句子。"""
import base64, json, os, subprocess, sys, tempfile, time
q = os.path.abspath(sys.argv[1]); src = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else os.path.join(q, "video.mp4")
end = float(sys.argv[sys.argv.index("--end") + 1]) if "--end" in sys.argv else None
lines = [l.split("｜", 1)[1].strip() for l in open(os.path.join(q, "narration.txt"), encoding="utf-8") if "｜" in l and not l.startswith("#")]
tmp = tempfile.mkdtemp(); mp3 = os.path.join(tmp, "a.mp3")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src] + (["-t", str(end)] if end else []) + ["-vn", "-ac", "1", "-ar", "24000", "-b:a", "96k", mp3], check=True)
prompt = """你是嚴格的配音品管。這是一支繁體中文短影片的旁白音訊（可能有輕微背景音效）。念稿依序如下（每行一句或一段）：
%s

請仔細聽完整段音訊，逐句檢查下列問題，任何一點點都要標出來：
1. 斷續：句子中間不該斷的地方斷開、聲音一截一截。
2. 卡頓：同一句裡有不自然的停頓或卡住。
3. 字被切掉：某個字的開頭或結尾被剪掉、聽不完整。
4. 停頓不自然：停頓太長、太短或位置不對（逗號處短停是自然的；段落之間 0.6～0.8 秒是設計的）。
5. 念錯或漏字：與念稿不同的地方（同音字不算）。
6. 語速太急：聽起來趕、喘不過氣、字黏在一起（type 用「停頓不自然」）。
只輸出 JSON，格式：{"sentences":[{"idx":1,"text":"…","start_sec":0.0,"issues":[{"type":"斷續|卡頓|字被切掉|停頓不自然|念錯","time_sec":0.0,"detail":"…"}]}],"overall":"一句話總評","score":1到10}
沒有問題的句子 issues 給空陣列。不要因為要找問題而硬找；但真的有就一定要標。""" % "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(lines))
body = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(open(mp3, "rb").read()).decode()}}, {"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}
bp = os.path.join(tmp, "b.json"); json.dump(body, open(bp, "w"))
url = "https://generativelanguage.googleapis.com/v1beta/models/" + os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview") + ":generateContent"
for k in range(4):
    r = subprocess.run(["curl", "-sS", "--max-time", "300", "-H", "x-goog-api-key: injected-by-proxy", "-H", "Content-Type: application/json", "-d", "@" + bp, url], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout); txt = j["candidates"][0]["content"]["parts"][-1]["text"]; res = json.loads(txt); break
    except Exception:
        print("第 %d 次失敗：%s" % (k + 1, (r.stdout or r.stderr)[:300]), file=sys.stderr); time.sleep(8)
else: sys.exit("Gemini 聽感驗證失敗")
res["source"] = os.path.basename(src); json.dump(res, open(os.path.join(q, "gemini_listen.json"), "w"), ensure_ascii=False, indent=1)
flag = [(s.get("idx"), s.get("text", ""), i) for s in res.get("sentences", []) for i in s.get("issues", [])]
for idx, t, i in flag: print("  第 %s 句 %s 秒 %s：%s（%s）" % (idx, i.get("time_sec"), i.get("type"), i.get("detail"), t[:16]))
print("Gemini 聽感：被標 %d 處；分數 %s；%s" % (len(flag), res.get("score"), res.get("overall")))
sys.exit(1 if flag else 0)
