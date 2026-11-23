---
channel: tc
status: posted
scheduled_at: 2026-11-22T20:00+08:00
weekday: 日
platforms: ig, threads
media: video
video: tech-800v.mp4
images: cover.jpg
title: 科技透明圈影片：八百伏特，AI 機櫃為什麼要把電壓拉高（tech-800v v2）
hook_type: 反差（#2）
urls_ig: https://www.instagram.com/reel/DgCxixuk2rZ/
ids_ig: 18660129076007417
verified_ig: VIDEO
urls_threads: https://www.threads.com/@tech_01010909/post/DgCxqghggH1
ids_threads: 18000266919102325
ids_threads_reply: 18044873867846076
verified_threads: VIDEO
urls_threads_reply: https://www.threads.com/@tech_01010909/post/DgCxx5LoD7V
done: ig, threads
urls: https://www.instagram.com/reel/DgCxixuk2rZ/ https://www.threads.com/@tech_01010909/post/DgCxqghggH1 https://www.threads.com/@tech_01010909/post/DgCxx5LoD7V
posted_at: 2026-11-22T20:10+08:00
error: 
fb_error: 
---
# 頻道②「科技透明圈」：影片「八百伏特：AI 機櫃為什麼要把電壓拉高」

- 11-18 Andy 核准（ai-mp4 的 out/tech-800v.v2.mp4）→ status 直接寫 approved。
- 排程：2026-11-22（日）20:00（`TZ=Asia/Taipei date -d 2026-11-22 +%A` 已驗算星期）。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps；佇列放成片原檔（out/tech-800v.v2.mp4）。網站文章另放壓縮版（crf 26）。封面：影片 0.5 秒畫面截圖 cover.jpg。
- 內容與數字只用 ai-mp4 videos/tech-800v/research.md：200 公斤＝廠商估算；電流與 219 倍＝算式；2027＝廠商規劃；台灣電源廠＝媒體報導，光寶時程兩說不一所以只說「也在做」。社群文不放股票代號。查證截至 2026/11/17，發布當天（11/22）要再查一次 800V 量產與出貨時程。
- 片尾預告：下一支「IC 設計為什麼沒有工廠」（11/23 18:00）。
- 敘述銜接（因果）：電壓低→所以電流大→銅排燙、越做越粗→所以改八百伏特→銅排能做細，代價是降壓次數變多。
- 留言關鍵字：供電 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-11-22-tech-800v（dm_config post_keywords「800v」）。
- 去 AI 味自查：不寫「非投資建議」（#46）、段與段有因果銜接（#47）。

- 2026-11-23：FB 試發那篇（11-23 12:40）Andy 已在 FB 上手動刪除（「試發的 800V 那篇…刪」「因為影片有順序」），post.md 與 state/tc/posted.json 的 FB 紀錄清掉，排回 FB 待補清單（social/tc/fb_backfill.json），排在 cooling 之後補發。
