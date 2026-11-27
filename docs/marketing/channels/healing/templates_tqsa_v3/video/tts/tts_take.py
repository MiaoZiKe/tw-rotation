#!/usr/bin/env python3
"""談晴說礙 旁白：Gemini TTS 一次念完整篇（2026-11-15 Andy 授權直接呼叫 API）。
送法照 ai-mp4 docs/prompts/tanqing-旁白-深度報導.txt：設定句（以「直接說：」結尾）後面不換行直接接念稿，念稿整篇一段；
gemini-3.8-flash-tts、音色 Sulafat、單人、不送 languageCode。金鑰由網路代理自動帶入，程式與紀錄都不放金鑰（header 是佔位字）。
用法：python3 tts_take.py <佇列資料夾> <輸出原始 wav>   → 另寫 <輸出>.request.json（只記模型、音色、送出文字、狀態、時間，不記金鑰）"""
import json, sys, os, base64, subprocess, wave, datetime, tempfile
# 2026-11-22 四道驗證第 1 項：語速靠字數＋TTS 指令「放慢、句尾自然停頓」控制，不在句中插停頓（原「偏快 5.5 字／秒、停頓短」）
# 2026-11-27 quit 審片：句號處只有 40～50 毫秒黏口 → 指令加「句號後換一口氣、停約 0.3 秒」（其餘不變，含規則 36 平捲舌）
# 2026-11-22 晚 Andy：「速度可以在快點 並且多點起承轉合」→ 指令改「語速自然偏快、輕快」（約 5.3 字／秒）；仍不在句中插停頓；2026-11-25 規則 36：平舌捲舌要分清楚（本行已合併）
SETUP = "用台灣人平常講話的口音，平舌和捲舌要分清楚（ㄓㄔㄕ念捲舌，不要念成ㄗㄘㄙ，例如「上」不能念成「喪」、「罩」不能念成「掃」）、不兒化，用平常說話的音量和聲音。像一位做深度報導的記者，把剛查完的資料攤開來，跟觀眾一起拆解這則新聞：講數字時清楚、肯定，像在對著資料念；講到「但是」「其實」這種轉折時語氣明顯一轉、帶一點思考；講到結論時篤定收住。整體語速自然偏快、輕快，大約每秒 5.3 個字，逗號處短短停一下；每個句號、問號之後要換一口氣、停約 0.3 秒再接下一句（不要黏在一起）；句尾自然停頓，不拖尾音、不用氣音、不演，不像主播播報，也不像在講課。直接說："
MODEL, VOICE = "gemini-3.8-flash-tts", "Sulafat"
q, out = sys.argv[1], sys.argv[2]
lines = [l.split("｜", 1) for l in open(os.path.join(q, "narration.txt"), encoding="utf-8") if "｜" in l and not l.startswith("#")]
body = "".join(t.strip() for _, t in lines)
req = {"contents": [{"parts": [{"text": SETUP + body}]}], "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(req, tf, ensure_ascii=False); tf.close()
r = subprocess.run(["curl", "-sS", "--max-time", "300", "-w", "\n%{http_code}", "-H", "Content-Type: application/json", "-H", "x-goog-api-key: injected-by-proxy",
                    "--data-binary", "@" + tf.name, "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL], capture_output=True, text=True)
os.unlink(tf.name)
txt, code = r.stdout.rsplit("\n", 1)
log = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "model": MODEL, "voice": VOICE, "languageCode": None, "status": int(code), "text": SETUP + body, "narration_chars": len(body)}
if code != "200":
    log["error"] = txt[:500]; json.dump(log, open(out + ".request.json", "w"), ensure_ascii=False, indent=1); sys.exit("TTS 失敗：HTTP %s %s" % (code, txt[:300]))
d = json.loads(txt); part = [p for p in d["candidates"][0]["content"]["parts"] if "inlineData" in p][0]["inlineData"]
pcm = base64.b64decode(part["data"]); rate = int(part.get("mimeType", "rate=24000").split("rate=")[-1].split(";")[0]) if "rate=" in part.get("mimeType", "") else 24000
with wave.open(out, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
log.update({"mimeType": part.get("mimeType"), "sec": round(len(pcm) / 2 / rate, 2)}); json.dump(log, open(out + ".request.json", "w"), ensure_ascii=False, indent=1)
print("完成：%s，%.2f 秒（含可能被念出的設定句）" % (out, log["sec"]))
