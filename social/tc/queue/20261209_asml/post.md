---
channel: tc
status: draft
scheduled_at: 2026-12-09T18:00+08:00
weekday: 三
platforms: ig, threads
media: video
video: tech-asml.mp4
images: cover.jpg
title: 科技透明圈影片：設備五大-1，艾司摩爾 ASML（曝光）（tech-asml v1）
hook_type: 問句（接上一支）＋反差（全世界只有一家）
---
# 頻道②「科技透明圈」：影片「設備五大-1：艾司摩爾 ASML（曝光）」

- status 寫 draft，等 Andy 回「核准」才改 approved；法遵尚未過（dm_config 的 asml 放 legal_pending，過了拿掉）。成片來源：ai-mp4 的 out/tech-asml.v1.mp4（69.4 秒、md5 前 8 碼 ced4f7f9），未重渲。⚠ lessons 第 89 條：ASML v1 被評專業度 6 分，成片 Andy 還沒說 OK，要不要重做爆炸分解版由 Andy／CEO 決定；影片換版時只換 tech-asml.mp4 與 cover.jpg。
- 排程：2026-12-09（三）18:00（`TZ=Asia/Taipei date -d 2026-12-09 +%A` 驗算＝Wednesday），照 docs/marketing/channels/tc/schedule_1203.md。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps。封面：影片 0.5 秒畫面（kicker「接上集：看曝光機」＋大字「誰做得出來？」，完整句，不是半句）。
- 內容只用 ai-mp4 videos/tech-asml/ 的 research.md、script.json（旁白為主文骨架）、optics-spec.md（只用於確認錫滴、真空、收集鏡的說法，不加沒有兩來源的數字）。不寫 research 第五節「片中不講」的項目（在台員工 5,000 人、高雄、2%）。
- 系列 2「代工的供應商」第 7 集：上一支光阻-2 講塗佈顯影機（結尾說「下一篇來看艾司摩爾」），這支講曝光機誰做。片尾預告下一支應用材料（已排 12/10）。
- 敘述銜接（因果）：上集晶圓要進曝光機→這台誰做得出來→只有一家→最難是光→極紫外光被空氣吸掉，所以抽真空用鏡子→要印滿整片，所以兩台座反向掃描、一格一格換→三家裡只有一家做得出極紫外光機→台灣的據點與供應鏈→照之前要先鋪薄膜，所以下一支看應用材料。
- 社群文不放股票代號；市占「九成以上」只有研究機構估計，不寫；帆宣、公準無 LOGO，影片用文字名牌。
- 留言關鍵字：ASML → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-12-09-tech-asml（dm_config 已登記；asml 放 legal_pending，等法遵）。
- 去 AI 味自查：第 1～12 類 0 筆；不寫「非投資建議」（#46）、段與段有因果銜接（#47）、開頭接上一支＋問句（#81）；lessons 第 76～89 條自查：#88、#89 畫面專業度不過（成片屬待 Andy 看），其餘過。

【主文】
🔍 設備五大-1：艾司摩爾，曝光機誰做得出來？

上集說，塗好光阻的晶圓要送進曝光機。這台機器誰做得出來？最先進的，全世界只有一家：荷蘭艾司摩爾（ASML）。

曝光機像一台投影機，把光罩上的電路圖縮小四倍，印到晶圓上。晶片的每一層圖案，都要先被它照過一次，這一步叫曝光。

最難的是光。雷射每秒打五萬顆錫滴，打成電漿，發出極紫外光（ASML 官網）。但這種光會被空氣吸掉，所以整台抽成真空，用碗形鏡把光收成一束。光有了，還要印滿整片晶圓，所以光罩台和晶圓台反方向同步掃過去，掃完一格，晶圓台移到下一格，一片要照好幾十格。

全世界做曝光機的主要三家：艾司摩爾、日本尼康、日本佳能。但極紫外光機只有艾司摩爾量產供貨，一台約兩億美元（媒體報導）。2025 年它出貨 48 台極紫外光機，系統營收約兩成多來自台灣（公司財報，媒體轉述）。

在台灣，艾司摩爾總部在新竹，林口在蓋新據點（媒體報導）；家登、帆宣、公準是供應鏈上的廠商（媒體報導）。

曝光機只負責照，照之前晶圓上要先鋪好薄膜，所以下一支來看鋪薄膜的應用材料。

留言「ASML」，我把完整解說回覆給你

【第 1 則留言】
出處（查證截至 2026/11/25）：
・曝光機像投影機、縮小四倍、掃描式曝光＝ASML 官網〈Lithography principles〉〈How lithography works〉、Wikipedia〈Extreme ultraviolet lithography〉
・錫滴每秒約五萬顆、打成電漿發出 13.5 奈米極紫外光＝ASML 官網〈The hottest thing about ASML machines〉（公司說法）；Wikipedia〈EUVL〉、Frontiers〈aot-2012-0125〉
・極紫外光被空氣吸掉、整台抽真空、碗形收集鏡＝Wikipedia〈EUVL〉、Frontiers 同上
・主要三家（艾司摩爾、尼康、佳能）＝36Kr〈2024 年三家出貨〉、Bits&Chips〈Nikon aims to challenge ASML in ArF immersion〉
・極紫外光機只有艾司摩爾量產供貨＝Wikipedia〈EUVL〉、Tom's Hardware（媒體報導）
・一台約兩億美元＝工商時報 2026/9/16、數位時代〈High NA EUV 一台要價 120 億〉（媒體報導；High-NA 另計，約 3.8～4 億美元）
・2025 年出貨 48 台極紫外光機＝ASML 2025 年報（eeNews Europe、heise 轉述）（公司財報）
・系統營收約 22% 來自台灣＝Nasdaq／Zacks、Tom's Hardware 轉述 ASML 財報（以系統營收計；以總營收計約 26%，口徑不同）
・新竹總部＝ASML 官網〈Locations〉（公司說法）；林口新據點＝中央社 2022/11/16、Taipei Times（媒體報導，完工時間各報不同，不寫）
・家登、帆宣、公準＝科技新報 2021/1/20、2026/9/9；工商時報 2023/8/29（媒體報導）
影片為示意動畫，非實際比例；極紫外光實際不可見。
