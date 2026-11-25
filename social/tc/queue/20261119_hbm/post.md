---
channel: tc
status: posted
scheduled_at: 2026-11-19T18:00+08:00
weekday: 四
platforms: ig, threads
media: video
video: tech-hbm.mp4
images: cover.jpg
title: 科技透明圈影片：HBM，十二層記憶體比一張信用卡還薄（tech-hbm v3）
hook_type: 反差（#2）
urls_ig: https://www.instagram.com/reel/Df61rGLlGSc/
ids_ig: 18082784426402619
verified_ig: VIDEO
urls_threads: https://www.threads.com/@tech_01010909/post/Df61w7PuBf2
ids_threads: 17948451378360739
ids_threads_reply: 18154761850545701
verified_threads: VIDEO
urls_threads_reply: https://www.threads.com/@tech_01010909/post/Df611lalqi5
done: ig, threads
urls: https://www.instagram.com/reel/Df61rGLlGSc/ https://www.threads.com/@tech_01010909/post/Df61w7PuBf2 https://www.threads.com/@tech_01010909/post/Df611lalqi5
posted_at: 2026-11-19T18:12+08:00
error: 
ids_fb: 3431957520345768
urls_fb: https://www.facebook.com/reel/3431957520345768/
fb_posted_at: 2026-11-25T18:07+08:00
fb_error: 
fb_slot: 2026-11-25T18:00+08:00
fb_via: backfill
---
# 頻道②「科技透明圈」：影片「HBM：十二層記憶體，比一張信用卡還薄」

- 2026-11-17 Andy 核准 HBM 影片（ai-mp4 的 out/tech-hbm.v3.mp4，56 秒）→ status 直接寫 approved。
- 排程：2026-11-19（四）20:00（`TZ=Asia/Taipei date -d 2026-11-19 +%A` 為 Thursday）。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps、56 秒；只做 faststart 重新封裝（-c copy）。網站文章另放壓縮版（crf 26，約 8.4 MiB）。
- 封面：影片 0.3 秒畫面截圖 cover.jpg。
- 開頭（反差）：AI 晶片旁的記憶體疊了十二層，整疊卻比一張信用卡還薄。
- 內容與數字只用 ai-mp4 videos/tech-hbm/research.md 與念稿 docs/prompts/tech-hbm-旁白.txt：720 微米只限 HBM3E 十二層（廠商公布）；2048 條資料線是 HBM4，與 HBM3E 分開寫；製程順序照真實做法（打孔→填銅→背面磨薄→逐層對位熱壓接合→填膠）；「哪些公司在做」：SK 海力士、三星、美光、台積電（新一代底層晶片）、鍵合設備韓美半導體與 ASMPT 標媒體報導；各家良率查不到；不給投資建議；社群文不放股票代號。查證截至 2026/11/16，發布當天（11/19）要再查一次市占、HBM4 底層晶片製程與鍵合設備供應名單。
- 留言關鍵字：堆疊（也收 HBM）→ 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-11-19-tech-hbm（dm_config post_keywords「hbm」）。
- 片尾預告：下一支「伺服器到底是什麼」（11/20 20:00）。
