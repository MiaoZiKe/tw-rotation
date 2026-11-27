# 【最新】12/3 最低工資、12/5 年終 兩支有旁白影片（2026-11-27 台北，總編輯；分支 healing/video-1203-1205，不推 main）
- Andy 11-27 親自核准排程：20261203v_minwage（12/3 20:27）、20261205v_bonus（12/5 20:27）；meta 皆 awaiting_andy＋await_andy:true。
- 已做：script.json（8 鏡＋片尾 @FIXED）、新插圖 6 個（paystub、yearcoins、deduct、bonusenv、taxline、taxreturn，已登記 index.json／ILLUSTRATIONS.md／素材登記.md）、caption／threads／threads_reply／sources／article.json（已跑 healing_article → site/articles/healing/2026-12-03-…、2026-12-05-…）、video_review.md（主旨、起承轉合、tts 全文）、retro.md 初稿。
- TTS 各 1 次（minwage 念稿 228 字、旁白 48.68 秒、純念稿 5.04 字／秒；bonus 230 字、46.86 秒、5.13 字／秒）。raw_keep 一段、句中 0 插入；pace_check「要人看」＝句間自然停頓最短 0.12／0.07 秒（聽感要特別聽黏口）。
- 注意：bonus 片 head_onset 誤停在「直接｜說」中間（成品開頭殘留「說」）→ 已改用 ASR 副本重裁，首字起音 46.77，前 2.5 秒 ASR 從「年」開始。head_onset 這個缺陷還沒修程式（見 retro.md）。
- **渲染：推 `_render_request.txt`（`20261203v_minwage,20261205v_bonus`、jobs=8 chunk=60 writeback=1）觸發 healing_render；run id 見下一行（推送後補）。容器沒有渲染。**
- **渲完要四道驗證＋審片**（審查者，不是製作者）：① 句中 0 停頓／③ 停頓密度＋audio-check（數位靜音／斷音／硬起音 0）；② Gemini 聽感＋平捲舌＋黏口＋ASR 逐字＋前 1.5 秒 ASR（不得有「直接說」）；④ frames_1s.png 逐格看重疊與空白；五項打分 ≥7 寫 video_review.md。過了才 SendUserFile 給 Andy（附排程、片長、念稿、主旨、出處、分數、已知問題），他 OK 才改 approved 推 main。

---
# 【最新】11/28 平均月薪、11/29 離職 審片不合格修片（2026-11-27 台北，影片製作棒）
- 審片紀錄：`20261128v_avgwage/video_review.md`、`20261129v_quit/video_review.md` 最上面（獨立審片 commit 309cf42e6 已挑進本分支）。兩支都因片頭殘留設定句尾「直接說」不合格；quit 另有句間黏口與 s7 換幕落後聲音 0.7 秒。
- avgwage：**沒有重配 TTS**。原始錄音重裁頭（念稿首字起音 40.42 秒，裁頭起點 40.15 秒＋0.15 秒同錄音底噪墊），旁白 46.32 秒（≥45.5）；純念稿 5.41 字／秒。
- quit：**重配 TTS 1 次**（念稿只改 s7「所以，答案是」；TTS 指令加「每個句號、問號後換一口氣、停約 0.3 秒」，保留平捲舌指令）。新旁白 51.65 秒；純念稿 4.95、含停頓 4.54 字／秒（句號後停頓加長，語速比 5.3 慢，仍在 ≤5.5 內）；句間最小停頓 0.32 秒（舊的 0.04～0.05）；ASR 與念稿只差 2 字（難→南、一→醫，小模型聽錯）。
- 共同：旁白檔尾端接 1 秒該錄音底噪（填掉旁白結束到片尾音效之間的 −96 dB 數位靜音）；`raw_keep.py` 重跑 → `make_segments.py` → `pace_check.py` 已跑。
- verify4.py 新增兩條自動檢查（前 1.5 秒單獨 ASR、換幕不得晚於下一句第一字起音）；拿舊 quit 驗證：抓得到「直接說」與 s7 落後；兩支新片本機 `verify4.py --no-sheet` 皆 pass_auto=true。
- **渲染已推 `_render_request.txt`（兩支、jobs=8 chunk=60 writeback=1）觸發 healing_render；run id **45924286707**（https://github.com/MiaoZiKe/tw-rotation/actions/runs/45924286707，commit 711020810，推送時 queued）；成品由 workflow 推回本分支與 renders/healing，pull 後驗收。渲完要重跑四道驗證**：① 句中 0 停頓／③ 停頓密度＋audio-check（數位靜音 0）；② Gemini 聽感＋平捲舌＋ASR 前 1.5 秒；④ 1 秒抽格逐格看重疊與空白；再補審查分數（≥7）。meta 維持 awaiting_andy，不推 main。
- 未處理（審片附帶項，聲音以外）：標籤入場旋轉框與標題 ≥8 px、quit 字幕下緣貼邊 1 px，程式重疊報告各剩 1 筆，渲完看報告再處理。

---
# 【最新】分段渲染改版＋第一次比對（2026-11-27 台北，影片製作棒）
- 照頻道②架構改好 `healing_render.yml`（matrix 分段、每支 8 台、段 60 幀；接段＋配音＋檢查；成品推 `renders/healing`；工作分支只回寫小檔，video.mp4 ≤20MiB 才回寫）。`render_video.js` 加 `--from/--to/--chunk/--job/--jobs/--seg/--assemble`（不帶參數＝舊行為，已在容器只抽 30 幀驗過段檔可用）；`autofix.py` 加 `HEALING_SEGDIR` 接段模式。
- 比對：已推 `_render_request.txt`＝`20261127v_food`（writeback=0），run id **45917047985**（https://github.com/MiaoZiKe/tw-rotation/actions/runs/45917047985；排在舊 run 45916208874 後面，同一 concurrency 組）；跑完還差：① 取 renders/healing 的 `20261127v_food.<sha>.mp4` ② `python3 v9/compare_render.py queue/20261127v_food/video.mp4 <新片>`（片長 ≤0.05 秒、逐秒平均差 ≤2%）③ 結果填進 `render_check_20261127.md`。比對沒過之前，本流程不算正式啟用。
- 注意：舊 run 45916208874（avgwage、quit）用的是舊單機版，讓它跑完；這兩支之後若要用新流程重渲，把 `_render_request.txt` 改回 `20261128v_avgwage,20261129v_quit` 再推。

---
# 談晴說礙 11/28 平均月薪、11/29 離職 影片重配＋渲染（2026-11-27 台北，影片製作棒）
- 分支 **healing/video-1128-1129**（從 main 開，不推 main）。已合併舊存檔 wip/healing-1128-1129 的工具改動（含 main 的規則 36 平捲舌指令，並採 5.3 字／秒語速）、`raw_keep.py`、`make_video.sh --render-only`。
- TTS：avgwage 1 次、quit 1 次（Gemini 額度各只用 1 次，沒有重送）。avgwage 「八十一」這次念對（ASR medium 聽到 48,981），整份念稿一次重配（235 字）；quit 念稿 233 字。兩支旁白＋時間戳（narration.wav、segments.json、pace_check.txt）都已定稿：avgwage 純念稿 5.31 字／秒、旁白 47.1 秒；quit 5.15 字／秒、47.3 秒。
- 新增 `.github/workflows/healing_render.yml`（workflow_dispatch：folder 可逗號多個、branch）：每個資料夾一台機器，跑 `bash v9/make_video.sh queue/<名> --render-only`（autofix 渲染≤3 輪＋check_v8＋final_check＋video_sheet＋verify4 停頓圖／ASR／1 秒抽格），成品 commit 回該分支。
- 狀態：workflow_dispatch 試過 404（workflow 檔不在 main 叫不動）→ 改用 push 觸發：推 queue/_render_request.txt 即觸發 healing_render（run id 45916208874，https://github.com/MiaoZiKe/tw-rotation/actions/runs/45916208874；成品會 commit 回本分支，pull 後驗收）；容器沒有渲染。
- 渲完還沒做的四道驗證（meta 維持 awaiting_andy＋await_andy:true）：
  1. ③ 停頓密度＋audio-check（數位靜音／斷音／硬起音 0）：verify4.json 看停頓；audio-check.py 不在這個 repo，要用 ai-mp4 的。
  2. ② 聽感：Gemini 聽整片（斷續／字被切）＋人工聽前 15 秒＋平捲舌（ㄓㄔㄕ vs ㄗㄘㄙ）；ASR 與念稿逐字比對。
  3. ④ 畫面：frames_1s.png 逐格看重疊、空白 >1 秒、下半部空洞、字太小；寫「重疊檢查：程式 N 幀 0 筆；人工 M 格 0 筆」。
  4. 審查 ≥7（art-director／animation-director 正式打分）＋ video_review.md 補起承轉合標註、「前 15 秒聽過，無斷續」。
- 已知：換幕自然停頓很短（句間最小 0.04～0.06 秒，pace_check 標「要人看」），是規則 32「快一點」＋規則 33「不插停頓」的結果，聽感驗證時特別確認不黏口。quit 的「一一一一」念四個一（時間戳確認），字幕為「1111」。舊的 video.mp4／frames／final_check 是舊聲音的產物，渲完會被覆蓋。

---
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

---
# 談晴說礙 11/27～11/30 四支影片＋兩篇輪播（2026-11-22 總編輯，每週檢討日）
- 已推 main：輪播 20261129_quit、20261130_grade1（approved，dfe6bef33）；影片 20261127v_food（b70087c85）、20261128v_avgwage（24603827c）、20261129v_quit（d4cb1b691）、20261130v_grade1（53cddceb2），meta 全是 awaiting_andy＋await_andy:true。
- 四道驗證：句中停頓 0、聽感（Gemini）0 處（avgwage 6 次中 2 次有標、不重現，判誤報）、audio-check 0／0／0、程式重疊 0（avgwage s2 滾輪數字已知誤報）；片長 51.1／50.2／49.2／49.8 秒。
- 還沒做：① art-director／animation-director 正式打分（外部模型分數 6.2～6.6，同方法審已核准的 11/26 出生數＝5.8～6.6，分數不能直接對 ≥7）；② Andy 聽過說 OK → 改 approved → `python3 scripts/healing_post.py --prepare`、`python -m scripts.healing_article <資料夾>`；③ 同批錄音 queue/_batch_11220754 只在本機（未推）。
- Gemini：gemini-3-flash-preview 免費額度（每日 20 次、四頻道共用）11-22 已用完，到 11-23 約 15:00 才恢復；gemini-3.5-flash 還能用。TTS（gemini-3.8-flash-tts）今天用了 2 次（同批 1＋外食重配 1）。
