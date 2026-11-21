# 規則 28（2026-11-20 Andy）：旁白結尾不放自編關鍵字。重切 narration_take.wav（不重送 TTS）：原始錄音 句號後的靜音之後的 s9「想看完整資料，留言XX。」整句丟掉，切點在上一句句號後的靜音。
export DROP_AFTER=76.38
export PRE_LAST=0
export HOLD=1.05
export GAP_OVERRIDE="s4=0.4"   # 2026-11-22 四道驗證：8 鏡有 7 個換幕，補停頓限 6 處 → s4→s5（「去年只剩八個。」→「而且不只去年」語意連續）只留 0.4 秒
export SCENE_GAP=0.75   # 2026-11-22 主控：換幕停頓拉到上限（量測約 0.8 秒）；片尾卡 outro.dur 5.6→6.2 讓成品 45.5～46.5 秒（不加字）
