# 談晴說礙 11/17–11/22＋工時 影片批次狀態（2026-11-16 15:2x 台北，總編輯停工交接）

- 7 支無旁白版（v8.2）都過動畫導演＋美術總監複審；程式檢查全 0（重疊、出界、留白／小字、換鏡同框、面板縮放；主體靜止 ≤1.00 秒；字幕四項 0 筆）。旁白稿已依「寫稿前必做 8 條」改好，存在各資料夾 narration.txt（`python3 v8/gen_v8.py <名> --nv` 會照 v8/specs_v8.py 重寫）。
- **都還沒配旁白、沒推 main、meta 都是 draft。** 11/16 的 Gemini 3.8 額度 16:00 前已用完（429，免費 10 次／天、四頻道共用）。
- TTS 順序（每支 1 次請求）：① 20261117v_studentloan（明天 20:27 發，最優先；配好先給 Andy 看）→ ② 20261118v_minwage → ③ 20261116v_worktime（排 11/23 20:27）→ ④ 20261119v_young → ⑤ 20261120v_mortgage → ⑥ 20261121v_laborins → ⑦ 20261122v_firstmarriage。
- 一支的做法：`cd docs/marketing/channels/healing/templates_tqsa_v3/video && bash v8/voice_pipeline.sh <名>`（gen→tts_take（gemini-3.8-flash-tts／Sulafat）→asr→cut_take_v8（不加速、句間 ≤0.3 秒）→make_segments（含字詞起音，重拍對準旁白）→gen→render_video→check_v8→make_sheet→final_check）。產出：video.mp4、cover.jpg、video_sheet.png、final_check.json。
- 最後驗證要看 final_check.json 的 pass、start_ok、voice ≈ −16 LUFS、片尾 ≈ −12.5、true peak ≤ −1、sync_ok、caption_bad 空；再寫 video_review.md（主旨一句＋只聽旁白自檢結果＋字幕四項＋響度）。主旨草稿見各資料夾 video_nv_fixes_v81.md 與 CEO 訊息紀錄。
- 配完之後：meta.json 改 approved（11/17 這支要 Andy 看過或 11/17 20:00 前沒意見）→ `python3 scripts/healing_post.py --prepare`（同步 site/media）→ `python -m scripts.healing_article <資料夾>`（scripts/healing_article.py 已改成產 mp4 區塊）→ 文章截圖用 scratchpad/tools/art_shot.py（站主＋訪客）。
- 待推 main 的改動（都在工作區、還沒 commit）：templates_tqsa_v3/video/v8/（產生器、規格、7 份插圖、檢查程式）、video_runtime_v8.js、render_video.js（v8 檢查開關）、tts/asr.py、tts/cut_take_v8.py、tts/make_segments.py（words 欄）、scripts/healing_article.py（mp4 區塊）、dm_config.json（6 個關鍵字：學貸、時薪、中位數、房貸、勞保、初婚；工時那支關鍵字「工時」還沒加）、素材登記.md、plan_202611_影片為主.md（下集串接＋11/24 改 25–29 歲題）、7 個 v 資料夾（caption、sources、article.json、meta draft、審查檔）。影片檔只推 video.mp4／cover.jpg（≤20MiB），video_nv.mp4 不推。
- 注意：每日上限 2 → 輪播 12:27＋影片 20:27，但 healing_post.yml 沒有 12:27 的排程（中午靠 CEO 的 12:41 保底叫醒），否則同晚資料夾名排序會先發輪播、影片 20:43 才發。工時 article 對應 site/articles/healing/2026-11-16-healing-worktime.json（主控改過的示範篇，更新前先確認）。磁碟只剩約 7GB，渲染後要刪 templates_tqsa_v3/video/tmp/<名>。
- 2026-11-16 注意：_charts.js 的鈕輪流亮不是旗標，之後重算有 ask 鏡的片（young、mortgage、laborins、firstmarriage）會跟著亮，審片時要看。

---
# 談晴說礙 11/24～11/26 三支影片批次狀態（2026-11-20 09:06 台北，sonnet 配音剪輯渲染棒）

- 新插圖 6 個已做（v9/illustrations：rentbanner、jarpair、mixempty、stepstroller、birthcards、stairs10），已登記 ILLUSTRATIONS.md＋素材登記.md；script.json 6 鏡 subject 已改指向新主體。
- TTS 已送 1 次成功（批次 _batch_11200854，合併 562 字，163.96 秒）；原始錄音備份在 /home/user/takes_backup/docs/marketing/channels/healing/queue/。沒有再送。
- 切回時 cut_take_v8 兩處修補（tts/cut_take_v8.py）：念稿第 1 行是中文數字、ASR 回阿拉伯數字時（二十五→25）找不到起點；ASR 把「直接說」的「說」當成念稿第 1 字（平均→說均）會把設定句尾巴留進成品。
- 剪輯參數：mingap 0.45、para 0.8、maxgap 0.6、HOLD 1.05。三支念稿時長 54.3／54.5／55.3 秒（pace_check 合格另見各資料夾 pace_check.txt）。
- 渲染：/tmp/render_all.sh 依序 rent → savings → births（每支約 7～9 分鐘），狀態寫 /tmp/render_all.status；做完的 video.mp4 在各資料夾。
- 還沒做：渲染完驗證（ffprobe、ASR 第一句、重疊）、video_review.md、retro.md 補完、推 main。meta 維持 draft＋await_andy。

## 2026-11-20 追加（Andy 全頻道：結尾「留言XX」改固定內容，尚未給）
- TTS 已送，三支旁白結尾「想看完整資料，留言租屋／存款／出生。」先保留，不重送；等固定內容來再補配最後一句（只重配 s9）。
- 片尾卡關鍵字已改成參數：script.json outro.keyword＝"@FIXED" 時顯示「留言拿完整資料」（runtime v8/_outro.js、video_runtime_v8.js 已支援）；之後改成指定內容只改這個值。
- caption.txt 這 3 支還沒有；寫時結尾用「到留言區留言」不含關鍵字。
- 12:20 完成：3 支 video.mp4 已渲染、驗證、寫 video_review.md／retro.md，推 main；meta 維持 draft＋await_andy。待做：animation-director／art-director 審片打分；Andy 看過才改 approved；固定結尾內容來了補配 s9。
