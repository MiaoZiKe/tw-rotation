---
channel: tc
status: draft
scheduled_at: 2026-11-10T20:30+08:00
platforms: ig, threads
images: 1_cover.jpg, 2_fields.jpg
title: 廣達碩畢待遇（代號肉鬆）
source_branch: tc/post-quanta 7b2841539（docs/marketing/channels/tc/posts/20261105_quanta/）
---
# 頻道②「科技透明圈」：廣達碩畢待遇

- 狀態：**draft（草稿，等 Andy 核准）**。只有 Andy 說「核准」後把上面 `status: draft` 改成 `status: approved`，程式才會發。
- 排定時間：`scheduled_at` 先填 2026-11-10 20:30（台北）；Andy 要別的時間就改這一行。核准時若時間已過，下一輪（15 分鐘內）就發。
- 平台：IG 發 2 張輪播（ig.txt 當說明文字）；Threads 主文帶同 2 張圖（threads.txt【主文】），發出後再發【第 1 則留言】。
- 圖：`1_cover.jpg`、`2_fields.jpg` 由 tc/post-quanta 分支的 `1_cover.png`、`2_fields.png` 轉成 JPEG（IG 只收 JPEG，quality 92，1080×1350）。
- 文案：ig.txt、threads.txt 原樣取自 tc/post-quanta 分支最新版（commit 7b2841539）。

## 核准前還沒完成的事（來源：分支上的 legal_review.md、image_sources.md）
1. 美編審查（ai_review.md，2026-11-08，結論退回兩項）：
   - 退回第 1 項：封面照片解析度不足 → **待 Andy 提供原圖**（官網原檔，寬 ≥ 1032px）。
   - 退回第 2 項：地圖點位 → **已修，經緯度投影換算**（2026-11-09 設計總監重出 2_fields.jpg，同時改 61K）。
2. 封面照片原始網址待 Andy 確認（文案寫「待確認原始頁面」）。
3. ~~法遵要求的資料口徑重算~~ **已完成（2026-11-09 CEO 定案）**：全部採 D 篩選＋排除重複。ig.txt、threads.txt（主文與第 1 則留言）已改：中位約 62K → 61K、加班 171 筆 → 165 筆、58% → 57%（週工時中位 48 不變）；Threads 主文 494 字。crosscheck.md 在 tc/post-quanta 更正（commit 2bb406fc5）。第 2 張圖（2_fields.jpg）已由設計總監重出（61K＋地圖修正），已 commit。
4. ~~Threads 主文超長~~ **已處理（2026-11-09）**：threads.txt 主文刪掉 4 個裝飾表情符號（🥩、😂、🖥️、👇），數字與聲明一字未動；現在 494 字（同一套算法，上限 500），格式檢查通過。ig.txt 沒動。佇列這份 threads.txt 已和 tc/post-quanta 分支版本不同，以佇列為準。
5. ~~待確認 BU9~~ **已定案（2026-11-09 Andy）**：第 2 頁只放括號外內容、標題「待遇透明圈」不加括號。原註：新版第 2 張圖的表頭寫「待遇透明圈（BU9）」。crosscheck.md 與法遵審查都寫過「文案一律改『伺服器事業群』、不用內部代號（BU9）」，圖上這個代號要不要拿掉，請 CEO／法遵決定。

6. **2026-11-09 文案改用 Andy 親寫版**（Andy：「從現在開始的幾篇文章我會親自做」），ig.txt、threads.txt 照原文；出處一行放 Threads 第 1 則留言與 IG 文末。發文方式筆記：docs/marketing/channels/tc/andy_style.md。第 2 頁圖改 4 列（碩畢、整包、加班、出差），設計總監重出中。
