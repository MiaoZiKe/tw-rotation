---
channel: tc
status: posted
scheduled_at: 2026-11-17T20:00+08:00
weekday: 二
platforms: ig, threads
media: video
video: tech-yield.mp4
images: cover.jpg
title: 科技透明圈影片：晶圓良率，大晶片為什麼比較吃虧（tech-yield v4）
hook_type: 反差（#2）
urls_ig: https://www.instagram.com/reel/Df15k0dirNN/
ids_ig: 18044758631839311
verified_ig: VIDEO
urls_threads: https://www.threads.com/@tech_01010909/post/Df15rCuPiLZ
ids_threads: 18004500078043152
ids_threads_reply: 18110404727251730
verified_threads: VIDEO
urls_threads_reply: https://www.threads.com/@tech_01010909/post/Df15yWIG9zn
done: ig, threads
urls: https://www.instagram.com/reel/Df15k0dirNN/ https://www.threads.com/@tech_01010909/post/Df15rCuPiLZ https://www.threads.com/@tech_01010909/post/Df15yWIG9zn
posted_at: 2026-11-17T20:10+08:00
error: 
---
# 頻道②「科技透明圈」：影片「晶圓良率：晶片越大，能用的比例越低」

- 2026-11-16（一）Andy 核准晶圓良率影片 v4（out/tech-yield.v4.mp4）→ status 直接寫 approved。
- 排程：2026-11-17（二）20:00（星期用 `TZ=Asia/Taipei date -d 2026-11-17 +%A` 算出 Tuesday）。同日 12:15 是 20261117_offer：post_quota.json tc 區塊每天上限 2 篇、間隔 ≥6 小時，12:15→20:00 隔 7 小時 45 分，不衝突；tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：ai-mp4 的 out/tech-yield.v4.mp4（1080×1920、30fps、56.4 秒、22.6MB）；只做 faststart 重新封裝（-c copy），沒有重壓。網站文章另放壓縮版（crf 26，約 8.8 MiB）。
- 封面：影片 0.3 秒畫面截圖 cover.jpg（第 0 幀附近，「9 成／不到一半」大字已完整）。
- 內容與數字只用 ai-mp4 videos/tech-yield/research.md 與念稿 docs/prompts/tech-yield-旁白.txt：「九成／不到一半」標估算（簡化模型）、缺陷密度標廠商公布 2020、不提任何公司的實際良率、不給投資建議；查證截至 2026/11/17。
- 留言關鍵字：良率 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-11-17-tech-yield（dm_config post_keywords「yield」）。
- 片尾預告：下一支「先進封裝」（大晶片拆小再拼回去；尚未排進 weekly_plan，由 CEO 排）。
