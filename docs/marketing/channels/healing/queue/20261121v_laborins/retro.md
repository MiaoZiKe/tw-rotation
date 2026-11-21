# 20261121v_laborins 改動紀錄（2026-11-21）
- 改 s4 第一詞「所以」→「對此」（因果不成立）。narration.txt、script.json 同步。
- 花費：Gemini TTS 1 次請求（全頻道日額 10 次之 1）；重渲染 1 次成片（中途一次誤開兩個渲染撞車，已停掉重跑，未多花 TTS）。
- 教訓：重跑 cut_take_v8 因 ASR 重辨識字詞時間，插入停頓不同、總長超過 60 秒；改為只替換成品旁白的 s4 區段並平移後段時間，其餘片段不變。勿同時開兩個 make_video／autofix。
- narration_take*.wav 不進版控。
