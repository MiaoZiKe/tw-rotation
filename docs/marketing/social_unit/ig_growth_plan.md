# IG 熱度提升計畫（2026-11-01）

> Andy 11-01：「目前已經發布一陣子了 所以在 IG Thread 上面也需要進行優化 讓熱度提升，並且 盡量不要千篇一律的方式要有點變化」。
> 負責：social-ops-lead。原本要派 market-researcher 查，這個執行環境沒有派子 agent 的工具，改由我用 WebSearch 查（只能讀搜尋摘要、點不進原文，下面每條都標來源與信心度）。

## 一、查到的做法（來源與信心）

| # | 做法 | 依據 | 信心 |
|---|---|---|---|
| 1 | **輪播優於單圖**：多份 2025～2026 報告都是輪播互動率高於單圖（Buffer 摘要：輪播中位數 6.9%、單圖 4.4%、Reels 3.3%，按觸及算） | ProflUp 2025、Buffer（二手摘要）、Socialinsider | 中（各家算法不同，方向一致） |
| 2 | **第一張就講主題與問題**，讓人知道值不值得往下滑；選邊站／反差式標題容易引發留言 | Metricool 電子報 | 中 |
| 3 | 輪播 5～7 張表現最好，但大多數帳號只發 2～4 張 | MeetEdgar（個人測試）、Socialinsider | 低 |
| 4 | **整體自然互動在下滑**（Socialinsider 2025：年減約 28%），所以要靠格式與開頭拉 | Socialinsider 2025 基準 | 中 |
| 5 | **限動投票／測驗／連結貼紙不能用 API 加**；Meta 2026-09-28 的更新只開放「貼文／Reels 的說明文字附加投票」，而且只限 Facebook 登入版 API，我們用的 graph.instagram.com 會回 400 | Meta 開發者 changelog、Agorapulse、Iconosquare | 高 |
| 6 | 台灣社群互動高峰在**平日晚上 8～10 點**（週三、週四最高），週末明顯偏低（QSearch 對 Threads 的分析，IG 沒查到台灣財經專屬數據） | 數位時代引用 QSearch | 中（是 Threads 數據） |
| 7 | 沒查到 Mosseri 對 hashtag 數量的正式說法；業界普遍建議 3～5 個相關標籤（未查到一手來源） | — | 低 |

## 二、結合我們的現況

- IG 限動：只能發圖、不能加文字與貼紙（API 限制），**10-27 Andy 已要求不加結尾頁** → 限動維持現狀，不加頁。
- IG 動態（主題文章）：原本**單圖**＋很長的文案，第一行是 hashtag 句；文中段落標題又帶 #（一篇常 8～10 個 #）。
- 封面一律實景照片（10-29），AI 圖要 art-director 審（10-28）→ 新增的圖**不用照片、不用 AI**，純排版，免審。

## 三、立刻實作（2026-11-01 已寫進程式，11-02 起生效）

| # | 項目 | 程式 | 說明 |
|---|---|---|---|
| 1 | **主題文章改 2 張輪播** | `scripts/social_news.py`、`scripts/social_numcard.py` | 第 1 張實景封面不動；第 2 張「鉤子＋重點數字卡」（最多 3 個數字），文字框兩兩不重疊、程式檢查，有重疊就不用這張（IG 退回單張、Threads 改 0 張），不擋整篇 |
| 2 | **第二張版型 3 套輪替** | `social_numcard.LAYOUTS` | 鉤子置頂／大數字置頂／兩欄方塊，依日期＋時段輪，避免每篇長一樣；色票照 `post_design_system.md` 亮色 HUD |
| 3 | **IG 文案第一行改鉤子句** | `social_news.ig_caption_v2` | IG 摺疊前只看得到 1～2 行，原本是「#公司 EPS…」，改成跟 Threads 同一套模板庫的鉤子（對話／冷知識／反差 × 好笑／吐槽，14 天不重複） |
| 4 | **IG 標籤收斂** | 同上 | 段落標題的 # 拿掉（📊 #重點數字 → 📊 重點數字），只留開頭 2 個＋最後 1 個事件標籤，共約 3 個 |
| 5 | **成效追蹤（改版前後比）** | `scripts/news_insights.py`（多兩個維度：開頭類型、情緒）、`scripts/threads_hook_stats.py` | 每晚 23:10 social_insights 一起跑；`state/hook_stats.json` 依版本 v1／v2、開頭類型、情緒、模板列平均瀏覽與互動率 |

## 四、不能自動化或先不做（建議，等數據）

| 項目 | 為什麼現在不做 | 建議 |
|---|---|---|
| 限動投票／測驗貼紙 | API 不支援（見一、5） | 若要做，只能人工在手機上加；或未來改用 Facebook 登入版 API 在「動態」說明文字加投票 |
| Reels | 要影片；短影片另有製作流程（比比素材庫、`docs/anim/`） | 每週 1 支 15～30 秒「今天三個數字」短影片，交影片組 |
| ~~主題文章發文時段移到晚上 8～10 點~~ | **2026-11-01 Andy「OK」→ 已做（只改 IG）**：IG 20:00／20:50／21:40，Threads 維持同時間；見 `news_auto.md` | 兩週後用 `news_insights` 的時段維度比較 |
| 輪播加到 5～7 張 | 新增的每一張都要過重疊檢查；照片張數受圖池與審核限制 | 兩週後看 2 張輪播的收藏／分享再決定 |
| 第 1 張封面改「鉤子大字」 | 封面規則是實景照片＋標題（10-29、10-30），大字改動屬版面改版 | 先用第 2 張驗證鉤子效果，有效再提給 Andy 看預覽 |

來源：
- [Socialinsider 2025 Instagram Benchmarks](https://www.socialinsider.io/blog/instagram-hashtag-study/)
- [PostNitro：Instagram engagement statistics 2025](https://postnitro.ai/blog/post/instagram-engagement-statistics-2025)
- [Metricool 電子報：7 ideas to get 30k impressions](https://newsletter.metricool.com/p/7-ideas-to-get-30k-impressions-and-750-interactions)
- [MeetEdgar：Instagram carousel tips](https://meetedgar.com/blog/instagram-carousel-tips)
- [ProflUp 2025 Instagram Engagement Report（IPS News）](https://ipsnews.net/business/?p=230206)
- [Instagram carousel engagement statistics（引 Buffer）](https://blog.mean.ceo/instagram-carousel-engagement-statistics/)
- [Meta 開發者：Instagram Platform changelog](https://developers.facebook.com/documentation/instagram-platform/changelog/)
- [Agorapulse：Features not available in Instagram API](https://support.agorapulse.com/en/articles/8762520-features-not-available-in-instagram-api)
- [Iconosquare：Features not yet available through the Instagram API](https://support.iconosquare.com/features-not-yet-available-through-the-instagram-api)
- [數位時代：Threads 發文時間 2026（引 QSearch）](https://www.bnext.com.tw/article/90152/threads-posting-timing-2026)
