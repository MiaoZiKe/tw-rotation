---
channel: tc
status: approved
scheduled_at: 2026-12-05T18:00+08:00
weekday: 六
platforms: ig, threads
media: video
video: tech-mask1.mp4
images: cover.jpg
title: 科技透明圈影片：光罩-1，晶片的底片（tech-mask1 v3）
hook_type: 問句（接上一支）＋反直覺（#20）
---
# 頻道②「科技透明圈」：影片「光罩-1：晶片的底片」

- 11-25 Andy 確認成片 OK（「矽晶圓-1、矽晶圓-2、光罩-1。 都OK」）；文案 Andy 還沒看過 → status 寫 draft，等 Andy 核准才改 approved。成片來源：ai-mp4 的 out/tech-mask1.v3.mp4（md5 前 8 碼 97d229fb），未重渲。
- 排程：2026-12-05（六）18:00（`TZ=Asia/Taipei date -d 2026-12-05 +%A` 已驗算星期），照 docs/marketing/channels/tc/schedule_1203.md。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps；佇列放成片原檔。封面：影片 0.5 秒畫面截圖 cover.jpg。
- 內容只用 ai-mp4 videos/tech-mask1/research.md 與 script.json（旁白為主文骨架），不加 research 沒有的數字。查證截至 2026/11/23。
- 系列 2 第 3 集：接上一支矽晶圓-2 的片尾「電路怎麼印上去？靠光罩」。
- 片尾預告：下一支光罩-2（誰做光罩、怎麼運送，已排 12/6）。
- 敘述銜接（因果）：鉻擋光、玻璃透光→縮小四倍投影→但極紫外光被玻璃吃掉，所以改反射→吸收層畫電路→護膜擋灰塵→片數多又不能有缺陷，所以一套上千萬美元→空白光罩是白紙，白紙有了誰來畫，所以下一支看。
- 費用、片數是研究機構估計，寫「估計」；HOYA、AGC 個別市占與名次兩來源對不上，不寫；台灣誰做光罩留給光罩-2。
- 留言關鍵字：光罩 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-12-05-tech-mask1（dm_config post_keywords「mask1」已登記；文章與回覆文字尚未建立）。
- 去 AI 味自查：第 1～12 類 0 筆；不寫「非投資建議」（#46）、段與段有因果銜接（#47）、開頭接上一支＋問句（#81）。

【主文】
🔍 光罩-1：晶片的底片

上一支晶圓備好了，電路要怎麼印上去？用光照著一張底片印，這張底片叫光罩。最先進的那種，光反而穿不過去，為什麼？

傳統光罩是石英玻璃，鍍上一層鉻，電路就刻在鉻上。光照下來，鉻擋住、玻璃透光，圖案就帶下去，再經過鏡頭縮小四倍，投影到晶圓上。

但更先進的極紫外光，會被玻璃吃掉，穿不過去。所以改用反射：鉬和矽交錯疊約四十對，像鏡子把光彈回去；電路改用吸收層畫，蓋到的地方不反光，圖案就留在反射光裡。

光罩上方還繃著一層護膜。灰塵落在膜上，因為對不到焦，影子是糊的，印不出來。先進晶片要幾十片光罩，片片不能有缺陷，所以一套動輒上千萬美元（研究機構估計）。

還沒畫圖的空白光罩像一張白紙，極紫外光用的幾乎都來自日本豪雅和旭硝子。白紙有了，誰把電路畫上去？又怎麼送進工廠？下一支來看。

留言「光罩」，我把完整解說回覆給你

【第 1 則留言】
出處（查證截至 2026/11/23）：
・石英鍍鉻、縮小 4 倍投影＝USPTO 7767365、ASML《Reticle Design Manual》、Wikipedia〈Photomask〉
・極紫外光被吸收改反射、鉬矽約 40 對、吸收層＝Wikipedia〈EUV lithography〉、USPTO 11846881、12353120
・護膜讓灰塵失焦＝USPTO 11635681（ASML）、Brouns 等 2017〈EUV pellicles〉
・幾十片光罩、一套上千萬美元（估計）＝IC Knowledge（SemiWiki）、AnandTech、IBS、SemiAnalysis
・空白光罩幾乎來自 HOYA、AGC＝QYResearch、Morningstar、DigitalToday 2026；個別市占兩來源對不上，不寫
影片為示意動畫，非實際比例。
