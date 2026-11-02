# 爆文共通點與觸及診斷研調（Threads／IG）— 2026-11-02

> 起因：Andy 2026-11-02 原話：「我的 Thread & IG 流量一直都非常低，我也有一直自動發文，但始終沒人註冊買會員……請專業人員找尋文章會有流量的共通點是什麼，包含發文時間，發文內容，是否與消息等等有關。」
> 搭配讀：`data_snapshot.md`（我們帳號實測）、`../hot_posts_research_1028.md`（上次研調，查過的關鍵字不重複）。

## 0. 先講限制（誠實聲明）

1. 本環境只有 WebSearch，點不進原文（WebFetch 對 techcrunch.com、help.instagram.com 都連不上，本次實測，網域不在 session 允許清單）。所以**所有引用都是搜尋摘要，不是我讀過全文**；官方原文（Instagram 部落格、Meta 創作者頁）只能從二手轉述核對。
2. 「一個月 1 萬粉、內容只是 AI 圖」這類帳號，**查不到任何可驗證的個案或數據**，查到的幾乎全是課程、工具商行銷。第 F 節只能給「機制推論＋哪些做法有風險」，不能給「他們做了什麼」的事實。
3. 台灣 Threads／IG 爆文的量化研究幾乎沒有，台灣最像樣的是 QSearch 的時段數據（一般主題、非財經）。其餘多為媒體評論與個人經驗。
4. 我們自己的數字（第 8 節）樣本小（Threads 45 則有觀看數），且與「手動期 vs 自動期」「發文日期」混在一起，只能當線索，不能當因果。

信心度：高＝兩個以上獨立來源一致且至少一個為官方或大樣本研究；中＝一個大樣本研究或多個一致的二手報導；低＝單一來源、廠商部落格、個人經驗或我的推論。

---

## A. 台灣 Threads／IG 爆文共通點

### A1 題材：職場／薪資／租房／奇聞容易紅，這是台灣 Threads 的文化
| 結論 | 證據 | 信心 |
|---|---|---|
| 台灣 Threads 在缺乏熱門議題時，演算法大量推播容易觸及與互動的內容，例如職場、租房、跨國婚姻與奇聞逸事。 | 台灣事實查核中心評論 https://tfc-taiwan.org.tw/?p=105994 ；經濟日報黃哲斌專欄（經 Bnext 目錄轉述）：獵奇、虐心、公審、廢文成爆款主流，職場、租房等議題特別有熱度 https://www.bnext.com.tw/article/81784/threads-engage-strategy | 中（皆為評論，非量化） |
| 職場爭議、薪資話題在 Threads 上確實一再成為新聞素材與高留言貼文（遲到一分鐘扣一小時事假、薪水小偷、主計總處薪資數據被網友自嘲）。 | 風傳媒 https://www.storm.mg/article/11102914 ；遠見 gvm Threads 標籤頁 https://www.gvm.com.tw/tags/Threads?page=1 | 中 |
| 台積電等科技業薪資／分紅，是台灣媒體與社群反覆出現的題材，網友個人分享數字是主要內容形式（職等、分紅月數、與 Google 比較），報導自己都註明「網路流傳數字僅供個案參考」。 | 財報狗 https://statementdog.com/news/17537 ；ETtoday https://finance.ettoday.net/news/2917242 ；TechNews https://technews.tw/2022/12/03/secret-of-tsmc-bonus/ | 中（證明需求存在，非證明某貼文為何爆） |
| Dcard 活躍用戶近一年 66.7% 讀過工作相關文章；年輕世代常問「我的薪水和同業比合理嗎」。 | Dcard 數據經 104 部落格轉述 https://blog.104.com.tw/the-disaster-of-salary-transparency/ ；資料來源為二手 | 低～中 |

**為什麼「薪資／職場內幕」會爆（原因推論，查不到直接研究）**：
- 比較心理：留言多半是「拿自己跟同事、同業比」，每個讀者都有代入的數字（Dcard 薪資透明討論案例，https://blog.104.com.tw/the-disaster-of-salary-transparency/）。
- 資訊不對稱：公司不公開，所以「業內人士講真話」稀缺；PTT／Dcard 討論裡反覆出現「被蒙在鼓裡」的感受。
- 留言有東西可補：每個人都能補自己公司的行情，貼文天然是「待補全的清單」，留言多、回覆多，這正是 Threads 看重的訊號（見 D）。
- 信心：低（推論，無對照實驗）。

### A2 寫法：第一人稱、真實經驗、可被補充
| 結論 | 證據 | 信心 |
|---|---|---|
| 第一人稱的生活觀察與真實經驗較易引發互動；留言回覆會影響演算法判斷。 | 搜尋整合摘要；Bnext 追蹤破萬經營攻略（作者自述 120 → 1 萬追蹤、十幾篇 1000–3000 讚，數字為自述未驗證）https://www.bnext.com.tw/article/81784/threads-engage-strategy | 低（個人經驗） |
| 擴散來源有兩種：追蹤者、以及對特定主題（職場、廢文、自介）有偏好的人群；追蹤數高不代表貼文會推給多數追蹤者。 | 同上 Bnext | 低 |
| 欠罵文／憤怒誘餌在 Threads 容易紅，Meta 自己承認有 engagement bait 問題，並說要壓低。 | Engadget https://www.engadget.com/social-media/meta-is-working-to-fix-threads-engagement-bait-problem-173135011.html ；Business Insider 實測轉述 https://businessinsider.in/tech/news/metas-head-of-threads-shares-advice-about-how-and-when-to-post-as-the-debate-swirls-around-engagement-bait/amp_articleshow/114227410.cms | 中 |
| Threads 單則上限 500 字，超過用「新增到串文」接續。 | TechBang https://www.techbang.com/posts/116794-is-it-crispy-today-decrypt-thread-features | 中 |

**查不到**：台灣爆文的最佳字數、第一句寫法的實證。Bnext 有一篇「開頭 0.2 秒決定一切」只拿到標題，內文未讀。

### A3 圖文 vs 純文字
| 結論 | 證據 | 信心 |
|---|---|---|
| Buffer 的 Threads 分析（約 73 萬則）：圖片互動率最高（5.17%）、影片次之（5.14%）、連結 3.78%、純文字 3.23%；另一轉述說圖片比純文字多約 60%。 | 以第三方轉述，未讀到 Buffer 原文：https://onlinemarketing.de/social-media-marketing/threads-beste-posting-zeiten-buffer-analyse ；Buffer 2026 新版 250 萬則時段研究 https://buffer.com/resources/the-best-time-to-post-on-threads/ | 低～中 |
| 另有行銷部落格自己測，也說有圖片的串文在「為你推薦」觸及較好。 | https://postory.io/blog/what-works-on-threads-2026 | 低 |
| 國際資料不等於台灣；台灣最大爆文（廣達）本身就是**輪播圖＋長文字**混合（`media_type=CAROUSEL_ALBUM`、約 480 字），不是純圖。 | 我們自己的 catalog | 高（只是這則的事實） |

---

## B. 發文時間

| 結論 | 證據 | 信心 |
|---|---|---|
| 台灣 Threads：QSearch 追蹤 2025 全年 3,600 萬則貼文，互動高峰在**週中晚間 20–22 點**，前三名是週四 20 點、週四 21 點、週三 20 點；週日最低；與國際「週四早上 9 點」相反。 | Bnext https://www.bnext.com.tw/article/90152/threads-posting-timing-2026 ；The News Lens https://www.thenewslens.com/article/265026（兩篇為同一資料源，視為單一來源） | 中 |
| 國際：Buffer 2026-02 以 250 萬則分析，最佳為週四早上 9 點；其他部落格說平日 7–11 點。 | https://buffer.com/resources/the-best-time-to-post-on-threads/ ；https://www.eclincher.com/articles/best-time-to-post-on-threads-in-2026 | 中 |
| Meta 官方說：週末多發可能有助互動。 | Meta 創作者頁轉述 https://creators.instagram.com/threads ；https://about.fb.com/news/2024/10/find-your-community-with-new-threads-educational-insights/ | 中（二手） |
| IG：沒有台灣專屬數據；通用建議週二到週四上午 9–11 點、晚上 7–9 點，週日最低；台灣的 SNS Helper 建議看自己 Insights 的「追蹤者活躍時間」。 | https://snshelper.com/tw/blog/optimal-instagram-posting-times ；https://meetedgar.com/blog/best-time-to-post-on-instagram | 低 |
| **財經類有沒有特別時段（盤前、盤後）：查不到任何數據。** | 查過：「Instagram 台灣 最佳發文時間 2026 台灣用戶 時段 財經」「Threads 最佳發文時間 台灣 2026 QSearch 晚上」 | — |

**對照我們自己的資料**：最大爆文發在**週五凌晨 05:29**（台北），不在上述任何「最佳時段」。所以時間不是決定因素，最多是 2～3 成的調味料；內容與是否引發回覆才是主因。（見第 8 節）

---

## C. 與時事／新聞的關係

| 結論 | 證據 | 信心 |
|---|---|---|
| Meta Threads 負責人的建議之一：「讓討論聚焦在當下、及時、相關的話題，會很有幫助」。 | Business Insider（Emily Dalton Smith，2024-10）轉述 https://businessinsider.in/tech/news/metas-head-of-threads-shares-advice-about-how-and-when-to-post-as-the-debate-swirls-around-engagement-bait/amp_articleshow/114227410.cms | 低～中（只有一句二手摘要） |
| Threads 在台灣測試／首發「趨勢話題」功能（2026-04-01 說法），台灣流量占全球約 21%。 | 單一部落格 https://rar.design/posts/threads-traffic-window-2026-designer | 低（需向 Meta 官方查證） |
| 台灣 Threads 爆紅事件多與時事綁定（2024 總統大選），行銷文章說趨勢更新很快、跟風有效。 | MIT Technology Review https://www.technologyreview.com/2024/04/02/1090518/threads-taiwan-election-politics-popular/ ；動腦 https://www.bnext.com.tw/article/81606/threads-marketing | 中（大選）／低（行銷文） |
| 「要多快」：**查不到** Threads／IG 搭熱點的速度量化研究。只查到 Twitter 客服回應時間（不適用）與廠商未驗證數字。 | 查過：「Threads real-time news trending topics newsjacking brands speed of response study」 | — |

**判讀**：搭熱點只有在「我們有別人沒有的角度」時才有意義。媒體已經寫過的新聞，我們用 3 分鐘整理成卡片，沒有稀缺性。我們實測中，Andy 本人談記憶體／HBM 的個人看法（786／566／491 觀看）比自動新聞卡（14～148）好，也是同一個方向（見第 8 節）。信心：低（推論＋n 小）。

---

## D. 發文頻率與官方對原創／聚合的說法

### D1 Threads
| 結論 | 證據 | 信心 |
|---|---|---|
| Meta 官方創作者建議：**每週至少 2–5 則**；「發文頻率越高，每則的觀看越高」；回覆約占 Threads 近一半觀看，所以要到別人串文下回覆；頂尖創作者發「專為 Threads 做的原創內容」。 | Meta 官方公告 https://about.fb.com/news/2024/10/find-your-community-with-new-threads-educational-insights/ ；創作者頁 https://creators.instagram.com/threads ；Social Media Today https://www.socialmediatoday.com/news/meta-shares-tips-grow-threads-presence/730488/ | 高（官方原文＋多個報導一致） |
| **沒有官方說法證實「Threads 每天發太多會被降觸及」**；Buffer 的相關性分析顯示發越多、追蹤成長越快（有遞減）。 | Buffer（IG 版）https://buffer.com/resources/how-often-to-post-on-instagram/ ；Threads 版為二手摘要，未讀原文 | 中（相關性，非因果） |
| Mosseri 2024-11：Threads 重排「為你推薦」，更優先顯示你追蹤的人，未追蹤帳號的推薦減少。我們只有 ~200 追蹤，意味著**能透過推薦摸到的人更少**。 | TechNews https://technews.tw/2024/11/22/threads-is-rebalancing-ranking-to-prioritize-content-from-people-you-follow/ | 中 |
| Threads 對外連結：Mosseri 曾說不特別重視連結，後來說連結排序已調整、表現好很多；但實際點擊仍很低。 | Engadget https://www.engadget.com/social-media/threads-users-still-barely-click-links-170139103.html ；TechNews https://technews.tw/2025/07/16/threads-users-still-barely-click-links/ ；Influencer Marketing Hub https://influencermarketinghub.com/adam-mosseri-links-on-threads-are-performing-better/ | 中 |
| Threads 話題標籤：一則只能一個；是否有效有爭議。 | TechCrunch／Engadget 2023 https://www.engadget.com/metas-threads-is-getting-searchable-topics-just-dont-call-them-hashtags-191915209.html | 中 |
| 沒有找到 Threads 專屬的「聚合帳號降權」官方政策。 | 查過：「Threads 演算法 官方 Mosseri 原創內容 聚合帳號 降低推薦 2025」 | — |

**判讀（重要）**：我們從手動期（每天 1～5 則、中位 355～1,130）到自動期（每天 4～9 則、中位 13～133）觀看崩落，**官方與研究都不支持「發太多」是主因**。更可能的原因是：自動內容樣板化、沒有回覆互動、也沒有人的觀點。但「很多低互動貼文是否拖累帳號整體評分」查不到官方說明，信心低。

### D2 Instagram
| 結論 | 證據 | 信心 |
|---|---|---|
| **2026-04-30 起，Instagram 把「降低聚合／轉貼帳號推薦資格」從 Reels 擴大到照片與輪播**：滾動 30 天，若帳號發布的內容多數不是自己創作，就失去推薦（Explore、Reels、動態推薦）資格；原創定義為「完整創作或有實質編輯」，浮水印、加速等不算；粉絲仍看得到，但推薦面看不到。 | TechCrunch 2026-04-30 https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/ ；PetaPixel https://petapixel.com/2026/04/30/new-instagram-policies-target-reposted-content/ ；Planoly https://planoly.com/blog/instagram-updates-its-original-content-policy ；Engadget（2024 Reels 版）https://www.engadget.com/instagrams-algorithm-overhaul-will-reward-original-content-and-penalize-aggregators-130018977.html | 中高（多個媒體一致，**但我讀不到官方原文**） |
| 門檻細節不一致：有說「30 天內 10 次以上」、有說「多數貼文」；**未取得官方確切數字**。 | Gigazine https://www.gigazine.net/gsc_news/en/20240502-instagram-updated-algorithm-prioritizes-original-content ；Pulse.bot 報導 | 低（細節） |
| 2024-04 Mosseri 宣布：轉貼內容在推薦中以原創者版本取代，並加註原創者標示。2022 年也有「原創優先」調整。 | Gizmodo 2022 https://gizmodo.com.au/2022/04/instagram-wants-to-make-your-feed-more-original/ ；Tubefilter https://www.tubefilter.com/2024/04/30/instagram-meta-threads-original-content-algorithm-bonus-program-monetization/amp/ | 中高 |
| Mosseri 2025-12-31 長文「Authenticity after abundance」：AI 圖越來越難分辨，方向是「標示 AI、驗證真實、**改進原創度排名**」；**查不到已上線的具體降權規則**，屬於意圖。 | Tom's Guide https://www.tomsguide.com/ai/instagram-says-ai-killed-the-curated-feed-now-its-scrambling-to-prove-whats-real ；Engadget https://www.engadget.com/social-media/instagram-chief-ai-is-so-ubiquitous-it-will-be-more-practical-to-fingerprint-real-media-than-fake-media-202620080.html | 中 |
| 發文頻率：Mosseri 公開說法是「重品質、別為量燒盡」，未給硬性每日上限；Buffer 約 210 萬則 IG 貼文（10.2 萬帳號）分析：每週 3–5 則可讓追蹤成長率約多一倍，10+ 則仍略高但遞減。**不含限動**。 | Buffer https://buffer.com/resources/how-often-to-post-on-instagram/ ；Social Media Today https://www.socialmediatoday.com/news/study-shows-posting-more-instagram-leads-to-more-reach/757633/ ；Routenote（Mosseri Reel 轉述）https://routenote.com/blog/how-often-you-should-post-on-instagram/ | 中（Buffer）／低（Mosseri 原話為二手） |
| Mosseri 2025-01：排名最重要訊號為觀看時長、讚／觸及、**分享（sends）／觸及**；對**非追蹤者**，分享比讚更關鍵。 | 二手整理 https://posteverywhere.ai/blog/how-the-instagram-algorithm-works ；https://www.inro.social/guides/instagram-algorithm-guide（「3–5 倍權重」的比例找不到原話，不採用） | 中（三個訊號）／低（倍數） |
| **限動對零粉絲帳號：** 追蹤者占限動觸及 91%、非追蹤者 9%（Fanpage Karma，600 萬+帳號，2026-04）；限動主要觸及已追蹤的人。 | https://www.fanpagekarma.com/insights/?p=16960 | 低～中（單一來源；比例是組成，非總量） |
| Mosseri 曾說「一般創作者在動態（Feed）比限動觸及多得多」。 | 搜尋摘要轉述，原話未取得 | 低 |

---

## E. IG 觸及幾乎為 0：可能原因與 Andy 自己的檢查步驟

### E1 可能原因（依我的判斷由高到低）
| # | 原因 | 證據 | 信心 |
|---|---|---|---|
| 1 | **帳號沒有受眾訊號**：新帳號、幾乎無追蹤者，內容也沒有被推薦出去；社群回報新帳號極低觸及很普遍。我們的 IG 一則動態 reach 0～1，是這一類最典型的樣子。 | Reddit 社群回報（低品質來源）；Mosseri 對非追蹤者以分享為主要訊號 | 低～中 |
| 2 | **推薦資格被判不可推薦**（帳號或個人檔案違反推薦準則、過去內容被移除、或被判為聚合型）。不可推薦時，「所有內容都不會推薦給非追蹤者，追蹤者仍看得到」。 | Instagram 官方說明 https://help.instagram.com/653964212890722 、https://help.instagram.com/539126347315373 （搜尋摘要） | 高（機制）／**我們是否被標：未知，需 Andy 自己查** |
| 3 | **聚合型判定風險**：我們的新聞卡、盤前盤後卡若被看作「重組他人新聞」，2026-04-30 新規適用照片與輪播。我們的圖表是用公開資料自行計算，應屬原創，但新聞整理類需自查。 | 同 D2 | 中（政策）／低（我們是否被判） |
| 4 | **互追（follow-for-follow）／「雙追不退」**：沒有 Meta 一手文件說這會被降權；但（a）追蹤者與目標受眾無關，互動率被稀釋；（b）部分文章認為協調式互動會被降權。 | 摘要：Meltwater https://www.meltwater.com/en/blog/influencer-pods ；TechCrunch pods https://techcrunch.com/?p=1981660 ；其他皆為部落格。 | 低 |
| 5 | **API 自動發文**：未找到大樣本證明會降觸及；廠商測試多數說不影響，也有 1 家廠商說原生發文較好。 | Kontentino https://www.kontentino.com/blog/does-scheduling-instagram-posts-hurt-reach/ ；Ayrshare https://www.ayrshare.com/docs/help-center/product/does_using_an_api_affect_post_views_or_engagement.md | 低（證據弱、各方有利益） |
| 6 | **文案放網址**：IG 內文網址不能點、也無證據顯示降權；Threads 內放網址則有「點擊極低」的事實。 | Engadget 同上 | 低 |
| 7 | **Hashtag 濫用**：IG 自 2025-12 起**每則限 5 個**；Mosseri 說 hashtag 幫助分類與搜尋，不會自動擴大觸及；Fanpage Karma 分析超過 5 個者觸及約低 3%。我們的 Threads 貼文帶 8 個 `#`，IG 文案是否也這樣需自查。 | Social Media Today https://www.socialmediatoday.com/news/instagrams-implementing-new-limits-on-hashtag-use/808309/ ；Business Today https://www.businesstoday.in/technology/news/story/no-more-hashtag-stuffing-instagram-limits-hashtag-usage-to-just-5-per-reel-and-post-507444-2025-12-19 ；Fanpage Karma https://www.fanpagekarma.com/insights/?p=3917 | 中高（限制）／低（-3%） |
| 8 | **買粉／假粉**：沒有一手證據；案例多為廠商或舊資料（2018–2019），一致說法是互動率被稀釋。 | AdEspresso https://adespresso.com/blog/buy-instagram-followers-experiment/amp/ ；Mediakix 轉述 | 低 |

### E2 Andy 在 IG App 自己檢查（以官方說明為準，介面會變動；找不到就在設定的搜尋欄打「帳號狀態」）
| 步驟 | 點哪裡 | 要看什麼 | 回報給我什麼 |
|---|---|---|---|
| 1 | 打開 IG App，右下角點自己的頭像進個人檔案 | 先確認帳號是**專業帳號**（個人檔案上方有「專業主頁」或「洞察報告」按鈕）。若沒有，到 設定和隱私 → 帳號類型和工具 → 切換為專業帳號（因為官方說明提到推薦資格這一欄對專業帳號才看得到） | 有沒有「洞察報告」按鈕 |
| 2 | 右上角三條線 → **設定和隱私** → 往下找**帳號**或**帳號狀態**（官方路徑：Settings → Account → Account Status；iPhone 版說明寫在「更多資訊和支援」下方） | 看有沒有一行寫**「你的內容可以被推薦」**或**「不符合推薦資格」**，以及有沒有被移除的內容、功能限制 | 截圖整頁 |
| 3 | 若寫不符合推薦資格 | 點進去看原因，可「要求審查」 | 截圖原因 |
| 4 | 個人檔案 → 公開／私人 | 必須是**公開**帳號，推薦才適用 | 是否公開 |
| 5 | 個人檔案頭像、簡介、個人檔案連結 | 官方說明：頭像或簡介若違反推薦準則也會被判不可推薦 | 簡介全文（我來檢查） |
| 6 | 洞察報告 → 觸及的觀眾 | 看「追蹤者／非追蹤者」比例 | 截圖 |
| 7 | 洞察報告 → 內容 → 最近 30 天 | 看哪一則觸及最高、是否為 Reels | 截圖 |

官方說明頁（連結）：
- 帳號狀態：https://help.instagram.com/539126347315373
- 推薦資格說明：https://help.instagram.com/653964212890722
- Instagram 創作者推薦資格部落格：https://creators.instagram.com/blog/instagram-recommendations-eligibility-tips-creators

**重要提醒**：就算帳號狀態乾淨、「可被推薦」，也不保證會被推薦；帳號狀態乾淨且觸及仍近 0，最可能原因是**沒有受眾訊號**（原因 1），不是被罰。信心：中（官方說明「資格不保證推薦」）。

---

## F. 「一個月 1 萬粉、內容就是 AI 圖」的帳號怎麼做到

**事實層（查得到的）**：
- 查不到任何可驗證的台灣個案。搜到的「破萬粉」「一個月漲粉」全是課程、付費懶人包或工具商自述（例：「200 則貼文 115 次爆紅」之類的付費清單，數字無法驗證）。 https://theenotionbuddy.gumroad.com/l/viralthreads ；Contra 案例（AI 工具公司自述 1K 粉）https://contra.com/p/LPg6vWEM-grew-to-1-k-ig-followers-with-0-ads-0-effort-just-ai-magic 。信心：高（「查不到」這件事本身）。
- 有一位台灣創業者自述 Threads 約兩個月 120 → 1 萬追蹤、24 小時賣出 100 張票。數字為自述，且是個人經驗型，不是 AI 圖量產。 https://www.bnext.com.tw/article/81784/threads-engage-strategy 。信心：低。
- Meme／AI 影片 IG 帳號「一個月 1.7 萬粉」的自述，伴隨一句「一換內容形式互動就掉」。 https://icepack.notion.site/How-to-Hack-Instagram-Reel-Views-and-Followers-132fd0b60699800aa69ad18911422cdf 。信心：低。

**機制層（推論，標低信心）：常見手法與可持續性**
| 手法 | 為什麼可能有效 | 可持續？風險 | 信心 |
|---|---|---|---|
| 迷因／共鳴型內容 | 「說中我了」→ 被分享給朋友（sends 是對非追蹤者的關鍵訊號） | 可持續但要持續出新梗；同溫層 | 低～中（sends 機制有二手證據） |
| 懶人包／清單 | 收藏與轉傳（輪播的收藏優勢有 Buffer／Socialinsider 研究） | 可持續；需要資訊真的有用 | 中 |
| 蹭熱點 | 搜尋與討論量集中 | 需快；內容無差異化則被淹沒；不可造假 | 低 |
| 互動誘導（留言 +1、抽獎） | 短期互動數 | Meta 持續壓低 engagement bait（2017 起 Facebook 已降權，Threads 2024 表態處理）；吸到的不是目標客群 | 中 |
| 搬運／轉貼他人內容 | 低成本 | **2026-04-30 新規專打這一類，IG 推薦資格會被拿掉**（D2） | 中高 |
| 互追、互動群組（pods） | 短期漲粉 | 無一手文件，但業界認為會被稀釋或降權；吸到無關粉絲 | 低 |
| 買粉 | 數字好看 | 互動率稀釋（案例 7% → 1.4% 屬單一軼事）；對「註冊買會員」毫無幫助 | 低 |
| 合作（共同創作、Collab） | 借對方受眾 | 可持續；需有可交換的價值 | 低 |

**對 Andy 看到的那個帳號的判斷**：「只是把東西丟給 AI 處理產幾張圖片」只是我們看得到的表面。**未被看到的部分**可能包含：它的題材是否極度具體的分眾（如某個族群的共鳴）、是否有真人故事或固定角色、是否靠他人轉發、是否買了互動。**要證實，需要有人打開該帳號最近 30 篇逐篇看（讚數、留言、張數、發文時間、是否有轉發痕跡）**，我這邊做不到。建議 Andy 把那個帳號的連結貼給我們，由能開瀏覽器的 session 逐篇記錄。

---

## G. 先做產品還是先做內容（audience-first／build in public）

| 結論 | 證據 | 信心 |
|---|---|---|
| 「先累積受眾再做產品」的案例多為電子報或創作者課程（Ajenda 免費電子報 → 90 天 75 萬美元；Creator MBA 200K+ 訂閱者 → 6 天 160 萬美元；CodeFast 首週 20 萬美元）。**多為平台行銷案例或轉述，且有倖存者偏差**。 | beehiiv 案例 https://www.beehiiv.com/case-studies/ajenda ；整理頁 https://onepage-research.sliplane.app/lessons/launch/launch-p10 | 低 |
| 共通結構：**受眾進到自己擁有的名單（email、LINE）才轉換**，而不是靠社群追蹤數；有文章稱超過八成首發營收來自名單。 | 同上；Echai https://echai.ventures/startingup/launching/how-do-i-build-up-an-audience-before-i-launch-so-it-s-not-just-crickets | 低 |
| Threads 要變現，穩定的創作者「把 Threads 當入口，導到電子報／付費產品」。 | Routenote https://routenote.com/blog/?p=99318 | 低 |
| 另一方面，Threads 用戶很少點連結（Engadget／TechNews），所以社群 → 官網註冊的漏斗天生損耗大。 | https://www.engadget.com/social-media/threads-users-still-barely-click-links-170139103.html | 中 |

**對我們**：我們**已經有產品**（網站），缺的是受眾與轉換路徑。Andy 現在 Threads ~203 追蹤、IG 幾乎 0，這個量級連「看過網站」都不夠，更別說註冊付費。「先建立受眾」不是替代做產品，而是把目標改為：**先把 Threads 做到可重複產生 1,000+ 觀看的貼文，再談導流**。信心：低～中（證據弱，但與我們實測方向一致：Threads 唯一有效的是人寫的內容）。

---

## 8. 我們自己的數據對照（來源：`data_snapshot.md`、`posts_catalog.json`，Threads 45 則有觀看數）

| 切法 | 則數 | 中位數觀看 | 平均觀看 | 備註 |
|---|---|---|---|---|
| 內文含網址（liguligu-puipui.com） | 21 | 73 | 474 | 自動貼文全帶網址 |
| 內文不含網址 | 24 | 121 | 3,131 | 含廣達（拉高平均） |
| 含問句 | 33 | 178 | 473 | 混有手動期 |
| 不含問句 | 12 | 55.5 | 5,789 | 廣達在這組 |
| 輪播 | 33 | 191 | 2,557 | |
| 單圖 | 7 | 69 | 71 | |
| 純文字 | 5 | 42 | 39 | |
| 內文 > 400 字 | 25 | 154 | 3,173 | |
| 內文 ≤ 400 字 | 20 | 69 | 288 | |

**怎麼讀這張表**：中位數差距都不大且都混著「手動期 vs 自動期」「廣達這個離群值」，**不能說「問句有用」或「網址有害」**。能說的只有：（1）廣達一則占 Threads 總觀看 81%（68,947／85,085）；（2）其餘 44 則的總觀看約 16,100，平均約 366；（3）廣達**分享數 463 ≈ 讚數 450**，是被大量轉傳（分享出去）的貼文，符合「對非追蹤者，分享是關鍵訊號」的機制（信心：中）；（4）華碩是同系列但只有 4,010 觀看、4 讚，**同格式不保證複製**，單一爆文不能當公式，需要重複驗證。

---

## 對我們帳號的 10 條具體建議

每條都對應實測數據與研調結論。**這些是建議，需用 4 週實驗驗證**（見第 10 條）。

1. **把自動貼文量降下來，先求「每則有觀點」，不求量。**
   實測：10-27 起每天 Threads 4～9 則、中位數從 355～1,130 掉到 13～133；官方（Meta）說每週 2–5 則即可、頻率與每則觀看正相關，所以**問題不是量，是自動內容沒有互動**。建議：自動新聞卡、盤前盤後類 Threads 每天合計不超過 2 則，且每則必須含一個「我們的判斷」或「一個可以被補充的問題」；其餘時間省下來做第 2、3 條。依據：D1（高）、第 8 節。

2. **複製廣達格式：做「公司行情／職場內幕」系列，並且每則都是『待補全』的清單。**
   實測：廣達 68,947 觀看、54 回覆、分享 463；它的特徵是：具體數字（職等、碩畢薪資、分紅月數）、個人口吻、結尾邀請「業界朋友補充，讓大家知道自己的行情」。A1 研調說明台灣職場／薪資是 Threads 的高互動題材（中）。建議：每週 1～2 則，主題換公司（聯發科、緯創、鴻海、台達電、聯電…，依 Andy 的產業知識取材），結尾固定放「你的公司呢？留言補一條」。**注意：**數字須標「網友或業內分享、僅供參考」，避免點名指控、避免洩漏機密，這類內容有法律風險，需 Andy 自己把關。同時要記得華碩只有 4,010，所以要追蹤每則是否重現。依據：A1／A2、第 8 節。

3. **留言要回、要主動去別人串文下回覆。**
   官方：回覆占 Threads 近一半觀看（高）；Buffer 128K 則分析說回覆自己貼文下的留言可使互動提升約 42%（低，二手）。實測：廣達 54 則回覆是它能持續擴散的原因；自動貼文回覆 0～2。建議：自動貼文後 2 小時內，Andy 或指定帳號真人回覆每一則留言；每天到 5～10 則台灣財經／科技大帳號串文下留有觀點的回覆（不貼網址）。依據：D1。

4. **停止 IG 限動自動發文，把力氣放在少量動態輪播。**
   實測：IG 100 則總觀看 196，限動 72 則 reach 0～3；研調：限動 91% 觸及追蹤者、非追蹤者僅 9%，我們幾乎沒有追蹤者。建議：IG 暫停自動限動；IG 每週只發 3 則自製輪播（Buffer：3–5 則最划算，且輪播收藏優勢有研究支持），內容用「可存起來／傳給朋友」的清單（例：看財報必看 3 個欄位）。依據：D2（中）。

5. **先做 Andy 的 IG 帳號狀態檢查（E2 七步），並做一次『原生發文』對照。**
   實測：IG 帳號 reach 每天 0～4、follower_count 回 null、一則 Reels 才 47。必須先排除「不可推薦」。建議：Andy 照 E2 截圖回報；同時手動（不透過 API）發 3 則同類輪播，與 API 發的比較觸及，用資料判斷 API 是否有影響，不靠猜。依據：E（機制高、我們狀態未知）。

6. **IG 與 Threads 文案砍 hashtag、砍免責長段。**
   IG 2025-12 起限 5 個、Threads 一則只有一個話題標籤；我們 Threads 貼文常帶 8 個 `#` 與「本內容為公開資料整理，不構成任何投資建議」。實測：含免責貼文雖中位數 868，但 5 則全在手動期，無法歸因，所以我不建議以此為由改，只建議：IG 最多 3 個相關標籤、Threads 最多 1 個話題標籤；免責放個人檔案簡介或最後一行，不占首屏。依據：E1 第 7 項（中高）。

7. **不要再發互追類內容；也不要用互追買追蹤者。**
   實測：「海巡 Day1 雙追不退」73 觀看但 7 則回覆（回覆比例高），這顯示互追能製造互動，但對象不是財經受眾，**對註冊買會員沒有用**；另外 Meta 對協調式互動沒有一手說法，風險不明（低）。建議：刪除這類計畫，追蹤者品質優先。依據：E1 第 4 項、F。

8. **控制「聚合比例」：IG 上要有 70% 以上是我們用自己資料算的圖。**
   2026-04-30 起，IG 推薦資格看 30 天內是否多數為原創（中高）。我們的資金輪動圖、題材熱度、產業鏈屬原創；「新聞卡」「財報／總經知識卡」是改寫他人資訊的風險區。建議：IG 上新聞類最多占 30%，並加入我們自己的計算（例：新聞 + 我們的輪動數據），把「改寫新聞」改成「我們的數據對這則新聞的補充」；在後台記錄每 30 天的原創比例。依據：D2。

9. **每則貼文設計成『會被傳給別人』。**
   實測：廣達分享數 463（≈讚數）；研調：對非追蹤者，分享（sends）是 IG 與 Threads 擴散的關鍵（中）。建議：每則最後一句改成「傳給你同事／朋友對照」、或做成可轉傳的清單；避免「留言 +1」「分享抽獎」之類 engagement bait（Meta 持續壓，信心中）。依據：D2、第 8 節。

10. **先量測、再要求註冊：建 4 週實驗與追蹤（本地沒有會員事件數據）。**
    實測缺口：容器讀不到註冊事件與進站來源（snapshot §5）。Threads 上連結點擊本來就很低（中），所以不能用觀看數推註冊。建議：（a）所有社群連結加 UTM，註冊事件記來源；（b）把 Threads 個人檔案的 5 個連結用滿，貼文內不放網址（放最底一行亦可，但不要把它當主要轉換）；（c）提供一個免費的小東西換 LINE／email（例：週報），因為 audience-first 案例的共同結構是「轉入自己擁有的名單」（低）；（d）每週一固定看四個指標：Threads 中位數觀看、回覆數／則、分享數／則、追蹤淨增；及格線 4 週後暫定 Threads 中位數 ≥ 300、至少 2 則 ≥ 1,500；未達就改格式，不增加量。依據：G、第 8 節。

---

## 查過的關鍵字（避免重複查）

**中文**
Threads 台灣 爆文 共通點 2026 觀看 薪資 職場 貼文｜Threads 演算法 官方 Mosseri 原創內容 聚合帳號 降低推薦 2025｜Threads 一天發幾則 發太多 降低觸及 演算法 經營｜Threads 爆文 流量 暴增 追蹤 個人經驗 第一人稱 分享 台灣 創作者｜Threads 新手 一個月 破萬粉 經驗 內容 AI 圖 懶人包 蹭熱點｜Threads 最佳發文時間 台灣 2026 QSearch 晚上｜Instagram 台灣 最佳發文時間 2026 台灣用戶 時段 財經｜Threads 貼文 放連結 降低觸及 外部連結｜Instagram 帳號狀態 可被推薦 檢查 設定｜薪水 薪資透明 社群 為什麼 引起共鳴｜台積電 薪水 年薪 分紅 Threads 爆紅｜財經 Threads 帳號 追蹤數 成長 變現｜IG 圖文帳號 一個月 破萬 AI 生成｜Threads 熱門話題 趨勢 台灣 蹭熱度｜Threads 經營 技巧 台灣 內容 第一句 留言引導 字數

**英文**
Instagram original content aggregator accounts demoted Mosseri｜PetaPixel new Instagram policies reposted content 2026｜Instagram reach zero new account "Account Status" recommendable｜Instagram Mosseri posting frequency quality over quantity｜Instagram API auto publishing reach｜Instagram follow for follow engagement pods penalized｜Meta Threads creators hub tips replies posting frequency｜Threads algorithm 2026 replies text-only vs images｜Instagram hashtags limit 5 2025｜Instagram Stories reach non-followers small accounts｜Connor Hayes / Threads head advice engagement bait｜Threads newsjacking speed｜audience first build in public case study｜Instagram engagement bait demoted｜Instagram AI slop Mosseri authenticity｜buying followers fake followers reach penalty｜Mosseri 2026 creator tips｜help.instagram.com Account Status steps｜meme account 10k followers one month｜Buffer Threads study posting frequency｜Buffer Instagram frequency 2 million posts｜Buffer Threads 730,000 posts｜Threads topic tag｜Instagram Reels sends per reach

**來源類型**：官方／平台說明（Meta 公告、Instagram 說明中心、Buffer 研究）、研究與數據平台（QSearch、Fanpage Karma、Buffer、Socialinsider）、媒體與創作者（Bnext、TechNews、風傳媒、遠見、TechCrunch、Engadget、PetaPixel、Social Media Today、Business Insider）。

**查不到、需有人開瀏覽器補的**
1. 該「1 萬粉 AI 圖」帳號的實際內容與互動（Andy 提供連結後逐篇看）。
2. Instagram 2026-04-30 新規的**官方原文與確切門檻**（Instagram 創作者部落格）。
3. 財經類帳號的發文時段數據（台灣）。
4. 廣達貼文為何擴散：有沒有被大帳號轉發或引用？（Threads 貼文頁可看「引用」與「轉發」來源，Andy 在 App 內點該則的數據即可。）
