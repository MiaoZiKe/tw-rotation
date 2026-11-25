---
channel: tc
status: approved
scheduled_at: 2026-12-07T18:00+08:00
weekday: 一
platforms: ig, threads
media: video
video: tech-resist1.mp4
images: cover.jpg
title: 科技透明圈影片：光阻-1，照到光就會變的膠（tech-resist1 v5）
hook_type: 問句（接上一支）＋冷知識（#1）
---
# 頻道②「科技透明圈」：影片「光阻-1：照到光就會變的膠」

- 11-25 Andy 確認成片 OK（光罩-2、光阻-1、光阻-2 都說 OK）；文案 Andy 還沒看過 → status 寫 draft，等 Andy 回「核准」才改 approved。成片來源：ai-mp4 的 out/tech-resist1.v5.mp4（md5 前 8 碼 3548c9a6），未重渲。
- 排程：2026-12-07（一）18:00（`TZ=Asia/Taipei date -d 2026-12-07 +%A` 已驗算星期），照 docs/marketing/channels/tc/schedule_1203.md。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps；佇列放成片原檔。封面：影片 0.5 秒畫面截圖 cover.jpg。
- 內容只用 ai-mp4 videos/tech-resist1/research.md 與 script.json（旁白為主文骨架），不加 research 沒有的數字。查證截至 2026/11/24。
- 系列 2「代工的供應商」第 5 集：上一支光罩-2 講光罩送進曝光機，這支講圖案印在哪一層膠上。
- 片尾預告：下一支光阻-2（塗佈顯影機，已排 12/8）。
- 敘述銜接（因果）：光打下去圖案印在膠上→這層膠叫光阻，照到光分子變質→正型洗掉照光處、負型相反→線越細光不夠用，所以化學放大→到極紫外光光子剩十四分之一，所以線條隨機斷→所以試金屬氧化物光阻→供應以日本廠為主、台灣有合資廠計畫→膠要塗得又薄又平，所以下一支看塗佈顯影機。
- 社群文不放股票代號；日本廠占比各家說法不一（約 75～91%）、個別公司市占兩來源對不上，不寫（research 第五節）；捷時雅雲林廠標「媒體報導」，發布當天要再查進度。
- 留言關鍵字：光阻 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-12-07-tech-resist1（dm_config post_keywords「resist1」已登記；文章與回覆文字尚未建立）。
- 去 AI 味自查：第 1～12 類 0 筆；不寫「非投資建議」（#46）、段與段有因果銜接（#47）、開頭接上一支＋問句（#81）；lessons 第 76～87 條自查全過（#85 節奏屬成片，成片 Andy 已 OK）。

【主文】
🔍 光阻-1：照到光就會變的膠

上集光罩送進了曝光機，光一打，圖案印在哪？印在一層膠上，它照到光就會變。

這層膠叫光阻，是感光的高分子，薄薄塗在晶圓上。光穿過光罩，照到的地方，分子會斷開、變質。正型光阻，變質的被顯影液洗掉，留下沒照到的；負型相反，照到的連成網，洗完反而留下。

但線越畫越細，光不夠用，所以要用化學放大型光阻：照到光，光酸產生劑放出一點酸，再烘烤，一個酸能連續反應幾百次。到了極紫外光，同樣能量，光子只剩十四分之一。光子少，落點不均，線條會隨機斷掉、黏在一起，所以業界在試吸光更強的金屬氧化物光阻。

這些光阻以日本廠為主，捷時雅還找夥伴，在雲林合資蓋廠，最快 2028 年投產（媒體報導）。但膠要塗得又薄又平，需要一台專門的機器，下一支來看塗佈顯影機。

留言「光阻」，我把完整解說回覆給你

【第 1 則留言】
出處（查證截至 2026/11/24）：
・光阻是感光高分子、正型與負型＝EPFL CMi〈Introduction to Photolithography〉、Wevolver〈Positive vs. Negative Photoresist〉
・化學放大（光酸產生劑、一個酸催化數百次反應）＝IBM Research Report RJ10223、NIST／Schmid SPIE 5376（2004）
・極紫外光光子數約為 ArF 的 1/14（同樣能量）＝arXiv 2405.11717、USPTO 11940728；隨機缺陷＝JM3 17(4) 041003、Semiconductor Engineering
・金屬氧化物光阻＝Semiconductor Engineering、RSC Chemical Science 2026；JSR 收購 Inpria＝JSR 新聞稿 2025/9/16
・供應商以日本廠為主＝Mizuho 產業報告、TechNews 轉日經（2026/5/5）；占比說法不一，不寫
・捷時雅雲林廠最快 2028 年投產＝TechNews 轉日經 2026/5/5、Tom's Hardware（媒體報導）
影片為示意動畫，非實際比例。
