---
channel: tc
status: approved
scheduled_at: 2026-11-18T20:00+08:00
weekday: 三
platforms: ig, threads
media: video
video: tech-packaging.mp4
images: cover.jpg
title: 科技透明圈影片：先進封裝，晶片太大做不好，拆小再拼回去（tech-packaging v3）
hook_type: 反差（#2）
---
# 頻道②「科技透明圈」：影片「先進封裝：晶片太大做不好，拆小再拼回去」

- 2026-11-16（一）Andy 核准先進封裝影片（ai-mp4 的 out/tech-packaging.v3.mp4）→ status 直接寫 approved。
- 排程：2026-11-18（三）20:00（`TZ=Asia/Taipei date -d 2026-11-18 +%A` 算出 Wednesday）。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps、58 秒；只做 faststart 重新封裝（-c copy），沒有重壓。網站文章另放壓縮版（crf 26，約 9.3 MiB）。
- 封面：影片 0.3 秒畫面截圖 cover.jpg。
- 開頭（反差）：晶片有大小上限，最大的 AI 晶片卻做到上限的五倍以上。
- 內容與數字只用 ai-mp4 videos/tech-packaging/research.md 與念稿 docs/prompts/tech-packaging-旁白.txt：「五倍以上」「九成八」標廠商公布、未經第三方實測；各家技術名稱（CoWoS、EMIB、I-Cube、FOCoS、S-SWIFT）與台灣設備廠（弘塑、辛耘、均華）標媒體報導，設備廠只放出處段；不給投資建議；查證截至 2026/11/16，發布當天（11/18）要再查一次「五倍光罩量產」「良率 98%」是否有更新。
- 留言關鍵字：封裝 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-11-18-tech-packaging（dm_config post_keywords「packaging」）。
- 片尾預告：下一支「HBM：記憶體為什麼疊十二層」（11/19 20:00）。
