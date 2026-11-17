---
channel: tc
status: approved
scheduled_at: 2026-11-21T20:00+08:00
weekday: 六
platforms: ig, threads
media: video
video: tech-cooling.mp4
images: cover.jpg
title: 科技透明圈影片：液冷，風扇吹不走的熱（tech-cooling v3）
hook_type: 反差（#2）
---
# 頻道②「科技透明圈」：影片「液冷：一櫃 AI 伺服器吃 120 千瓦，風扇吹不走」

- 11-17 Andy 核准液冷 v3（ai-mp4 的 out/tech-cooling.v4.mp4，61 秒；v4＝v3 只修熱交換器剖面卡標籤）→ status 直接寫 approved。
- 排程：2026-11-21（六）20:00（`TZ=Asia/Taipei date -d 2026-11-21 +%A` 為 Saturday）。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps、61 秒；只做 faststart 重新封裝（-c copy）。網站文章另放壓縮版（crf 26）。封面：影片 0.3 秒畫面截圖 cover.jpg。
- 開頭（反差）：一整櫃 AI 伺服器吃 120 千瓦，電最後都變成熱，風扇吹得走嗎？
- 內容與數字只用 ai-mp4 videos/tech-cooling/research.md：120 千瓦＝廠商公布；水對空氣 3,400 多倍＝物性計算；冷板帶走約 8～9 成＝業界說法；台灣廠商（奇鋐、雙鴻、台達電、高力，快接頭另有富世達）＝媒體報導，只說產業分工。社群文不放股票代號。查證截至 2026/11/17，發布當天（11/21）要再查一次機櫃功耗與台灣廠商。
- 留言關鍵字：液冷 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-11-21-tech-cooling（dm_config post_keywords「cooling」）。
- 片尾預告：下一支「八百伏特」（11/22 20:00）。
- 敘述銜接（去 AI 味第 12 類、因果）：吹不走→因為水的熱容大→所以改用水→冷板不是全包→機櫃更耗電，所以下一支看八百伏特。去 AI 味自查：第 1～12 類 0 筆。
