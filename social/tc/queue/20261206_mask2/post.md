---
channel: tc
status: draft
scheduled_at: 2026-12-06T20:00+08:00
weekday: 日
platforms: ig, threads
media: video
video: tech-mask2.mp4
images: cover.jpg
title: 科技透明圈影片：光罩-2，誰做光罩、怎麼運送（tech-mask2 v5）
hook_type: 問句（接上一支）＋數字（#1，26 萬道）
---
# 頻道②「科技透明圈」：影片「光罩-2：誰做光罩、怎麼運送」

- 11-25 Andy 確認成片 OK（光罩-2、光阻-1、光阻-2 都說 OK）；文案 Andy 還沒看過 → status 寫 draft，等 Andy 回「核准」才改 approved。成片來源：ai-mp4 的 out/tech-mask2.v5.mp4（md5 前 8 碼 5db174eb），未重渲。
- 排程：2026-12-06（日）20:00（`TZ=Asia/Taipei date -d 2026-12-06 +%A` 已驗算星期），照 docs/marketing/channels/tc/schedule_1203.md。tc_post 照 scheduled_at 發，再套 per_day／min_gap_hours 順延。
- 影片：1080×1920、30fps；佇列放成片原檔。封面：影片 0.5 秒畫面截圖 cover.jpg。
- 內容只用 ai-mp4 videos/tech-mask2/research.md 與 script.json（旁白為主文骨架），不加 research 沒有的數字。查證截至 2026/11/24。
- 系列 2「代工的供應商」第 4 集：上一支光罩-1 講光罩是什麼，這支講誰做、怎麼運送。
- 片尾預告：下一支光阻-1（已排 12/7）。
- 敘述銜接（因果）：先進光罩晶圓廠自己做，因為改版最快→其他交給專業光罩廠→怎麼做：電子束寫入→線路越細一道太慢，所以多束一起寫→寫完要檢查，因為一個瑕疵每次曝光都印→光罩盒雙層，因為極紫外光罩很難加保護膜→光罩到了還要膠接住圖案，所以下一支看光阻。
- 社群文不放股票代號；專業光罩廠與自有光罩廠的市占、各家名次兩來源對不上或口徑不同，不寫（research 第 4、5、17 列）；台灣光罩「主力成熟製程」標公司說法。
- 留言關鍵字：光罩盒 → 回覆隱藏文章 https://liguligu-puipui.com/#article/2026-12-06-tech-mask2（dm_config post_keywords「mask2」已登記；文章與回覆文字尚未建立）。
- 去 AI 味自查：第 1～12 類 0 筆；不寫「非投資建議」（#46）、段與段有因果銜接（#47）、開頭接上一支＋問句（#81）；lessons 第 76～87 條自查全過（#85 節奏屬成片，成片 Andy 已 OK）。

【主文】
🔍 光罩-2：誰做光罩、怎麼運送

上集說光罩是晶片的底片，這張底片誰做？怎麼送進曝光機？

最先進的光罩，台積電、英特爾、三星自己做，因為自己做改版最快。其他公司交給專業光罩廠，主要是日本兩家、美國一家。台灣有台灣光罩，主力是成熟製程光罩（公司說法）。

怎麼做？先在鍍鉻的石英板上塗光阻，再用電子束把電路一筆筆寫上去。但線路越細，一道一道寫太慢，所以最先進的寫入機用二十六萬道電子束一起寫（廠商公布）。寫完還要檢查，因為光罩上一個瑕疵，每次曝光都會印上去。

做好的光罩要裝進光罩盒。極紫外光用的是兩層：外盒擋灰塵，內盒是金屬。因為極紫外光罩很難加保護膜，所以內盒要到真空機台裡才打開。最早通過曝光機大廠認證的，是美國英特格和台灣家登（2018 年報導）。

光罩送到了，還要一層膠接住圖案，這層膠照到光就會變，下一支來看。

留言「光罩盒」，我把完整解說回覆給你

【第 1 則留言】
出處（查證截至 2026/11/24）：
・自有光罩廠、專業光罩廠（日本兩家、美國一家）＝Semiconductor Engineering〈Merchant Photomask Makers Remain Relevant〉、Photronics FY2024 10-K、台灣光罩總經理受訪（遠見／鏡週刊 2023/10/31）
・台灣光罩主力成熟製程＝公司說法（Money Weekly 專訪、遠見／鏡週刊 2023/10/31）
・鍍鉻石英板、電子束寫入＝USPTO 7220531、Wikipedia〈Photomask〉
・26 萬道＝IMS MBMW-101（512×512＝262,144 道）產品頁與 BACUS 2016 論文（廠商公布）；Semiconductor Engineering〈Multi-Beam Market Heats Up〉
・瑕疵每次曝光重複印出、同波長檢測＝SPIE Proc. 12751（Lasertec）、Semiconductor Engineering〈Finding Defects In EUV Masks〉
・雙層光罩盒、內盒真空內才開＝Entegris 1010 EUV Pod 產品頁、SEMATECH／ASML／Entegris 2009 海報；很難加保護膜＝USPTO 7477358、SPIE（TNO／SUSS）
・光罩盒認證＝Entegris 新聞稿 2018/8/2、中央社 2018/12/11；市占兩來源對不上，不寫
影片為示意動畫，非實際比例。
