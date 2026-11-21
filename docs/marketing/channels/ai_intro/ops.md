# 頻道③「AI 介紹頻道」發文營運規劃（草案，未啟用）

> 台北時間 2026-11-03｜撰寫：social-ops-lead｜性質：**只有規劃**。
> 這份文件**沒有**開任何自動發文、**沒有**改 `docs/marketing/social_unit/post_quota.json`、**沒有**動排程或程式。下面寫「要做」的程式與設定，都是等 Andy 拍板之後才開工的工作清單。
> 依據：`social_unit/post_quota.json`、`social_unit/auto_post.md` 第〇節（11-02 降量）、`threads_rules.md`、`ig_growth_plan.md`、`meta_api_setup.md`、`comment_dm_plan.md`，以及 `scripts/post_quota.py`、`threads_post.py`、`ig_post.py`、`social_insights.py`、`news_insights.py`、`threads_hook_stats.py` 的現況。

---

## 〇、先講結論（5 條）

1. **另開一組獨立帳號與獨立權杖**：新的 IG 專業帳號（商業類型）＋用同一個 IG 登入的 Threads。Meta App 可以**共用現有那一個**（加一組新的測試人員與權杖即可），但權杖、帳號 ID、佇列資料夾、posted 紀錄、開關檔**全部分開**，命名一律加 `AI_INTRO_` 前綴。
2. **全程人工核准制**：草稿可以自動產，但**只有 Andy 把 `status` 改成 `approved` 才會發**；預設開關全部 `false`。
3. **先只做 Threads，第 3～4 週再加 IG 輪播**；Reels 等前兩者有起色才做。依據：降量診斷顯示「量大質低」會崩觀看，新帳號沒有追蹤者，先用成本最低、純文字也能分發的平台試水溫。
4. **量的上限：每天最多 1 則、每週 3～5 則**（含手寫），從第一天就寫死在開關檔裡，不准重演 11-02 前一天十幾則。
5. **「沒發」只看「已核准但沒發出」**：沒有核准的稿子不算沒發、也不補發；已核准的到時間沒發 → 監工當下修到發出為止（照 10-29 規矩）。另外加一條「本週核准數 < 2」的提醒給 Andy（只提醒，不自動發）。

---

## 一、新帳號營運需要什麼

### 1-1 帳號

| 項目 | 建議 | 理由 |
|---|---|---|
| IG | 新開一個帳號，切成**專業帳號 → 商業（Business）類型** | API 發限動只支援商業帳號；發動態／輪播／Reels 專業帳號即可，但統一用商業類型最保險（`meta_api_setup.md` 第 0 節） |
| Threads | 用**同一個新 IG 帳號**登入開 Threads | Threads 帳號綁 IG；權杖與 user id 跟頻道一完全不同 |
| 帳號名稱與簡介 | 名稱不放 Meta 商標字樣；簡介註明「部分貼文由系統整理、人工審核後發布」，以及「含合作推廣連結時會標示」 | `meta_api_setup.md` 第 8 節「揭露自動化」；聯盟行銷要揭露（第四節） |
| 個人簡介連結 | 一個「連結頁」網址（見 4-3） | IG 主文連結不能點，導流只能靠簡介連結 |
| 頭像、封面 | 不用比比（11-02 Andy：「比比以後不會出現在貼文上」）；AI 生成的頭像／封面一律先過 `art-director` 審（10-28） | CLAUDE.md |

### 1-2 Meta App：共用現有，還是新開？

| 做法 | 優點 | 缺點 | 建議 |
|---|---|---|---|
| **A. 共用現有 App（liguligu-social）**，把新 IG／Threads 帳號加成測試人員，各產一組新權杖 | 不用重填隱私權網址、callback；Standard Access 只發自己管理的帳號就夠，免 App Review（`meta_api_setup.md` 第 1 節 G） | 同一個 App 的設定改動會兩個頻道一起受影響；App 被停權兩個頻道一起停 | **採用（先這樣）** |
| B. 新開一個 App | 完全隔離 | 多一套設定要維護、多一份權杖續期 | 等頻道③有固定量、或要申請 Advanced Access（例如 Threads webhook 自動回留言）時再分 |

不論 A 或 B，**權杖一定是新的一組**：權杖綁「App＋帳號」，新帳號必然拿到不同的權杖與 user id。頻道一的 `THREADS_ACCESS_TOKEN`、`IG_ACCESS_TOKEN` **絕對不能拿來發頻道③**（會發到頻道一的帳號上）。

### 1-3 GitHub Secrets 命名建議（只寫名稱，不寫任何值）

| Secret 名稱 | 內容 | 對應頻道一的哪一個 |
|---|---|---|
| `AI_INTRO_THREADS_USER_ID` | 新 Threads 帳號的數字 id | `THREADS_USER_ID` |
| `AI_INTRO_THREADS_ACCESS_TOKEN` | 新 Threads 長效權杖 | `THREADS_ACCESS_TOKEN` |
| `AI_INTRO_THREADS_ACCESS_TOKEN_AUTO` | 每週自動續期寫回用 | `THREADS_ACCESS_TOKEN_AUTO` |
| `AI_INTRO_IG_USER_ID` | 新 IG 帳號的數字 id | `IG_USER_ID` |
| `AI_INTRO_IG_ACCESS_TOKEN` | 新 IG 長效權杖 | `IG_ACCESS_TOKEN` |
| `AI_INTRO_IG_ACCESS_TOKEN_AUTO` | 每週自動續期寫回用 | `IG_ACCESS_TOKEN_AUTO` |

- 續期：沿用 `.github/workflows/meta_token_refresh.yml` 的做法，多跑一組 `AI_INTRO_*`（寫回 Secrets 用的 `META_SECRETS_PAT` 可共用）。
- 程式端的隔離做法（開工時才做）：發文程式加一個 `--channel ai_intro` 參數，**只在這個參數下**才去讀 `AI_INTRO_*`；不給參數時行為與現在完全相同。工作流裡把 `AI_INTRO_*` 只傳給頻道③那個 job，不傳給 social-live／social_news。
- 權杖不進 repo、不進 log、不寫檔；push 前照 CLAUDE.md 掃一次 `git grep`。

### 1-4 開關：與 `post_quota.json` 怎麼分開

**建議：另開一個開關檔 `docs/marketing/channels/ai_intro/quota.json`，不要加在 `post_quota.json` 裡。**

理由：
1. `post_quota.json` 現在 `queue.manual.threads／ig = true`。`threads_post.py`／`ig_post.py` 會把 `social/threads/queue/`、`social/ig/queue/` 裡**任何** `approved` 的非新聞稿用**頻道一的權杖**發出去。頻道③的稿子若放進那兩個資料夾，就會發到頻道一帳號上 —— 這是最大的風險，所以**資料夾、開關檔都要分開**。
2. 頻道一的開關是 Andy 11-02 拍板的降量設定，頻道③任何調整都不該有機會碰到它。
3. 一個檔一個頻道，誰開誰關一眼看得出來。

預設內容（開工時才建立，**全部 false**）：

```json
{
  "note": "頻道③ AI 介紹頻道。全部 false＝不發任何東西。要開只有 Andy 說了才改。",
  "updated": "YYYY-MM-DD",
  "enabled": false,
  "threads": {"post": false},
  "ig": {"feed": false, "carousel": false, "reels": false, "story": false},
  "limits": {"per_day": 1, "per_week": 5, "min_gap_hours": 20},
  "auto_draft": false
}
```

- `enabled` 是總開關；總開關 false 時其他全部視同 false。
- 讀不到或格式錯 → 一律視為全關（跟 `post_quota.py` 的「寧可少發」同方向，但更保守：頻道③沒有內建預設可退）。
- `limits` 是硬上限：就算 Andy 一次核准 10 篇，程式也只照 `per_day`／`per_week` 一篇一篇排出去，超過的順延，不擠在同一天。
- 若 Andy 偏好單一檔案：替代做法是在 `post_quota.json` 加 `"ai_intro": {…}` 區塊（同上內容、全部 false）；`post_quota.load()` 只檢查 `live`／`queue`，多一個區塊不會影響頻道一。但上面第 1 點的資料夾隔離仍然必做。

---

## 二、發文流程

### 2-1 流程與分工

| # | 環節 | 誰做 | 可否自動 | 產出／證據 |
|---|---|---|---|---|
| 1 | 選題（每週一次排下週 3～5 篇） | Claude 提選題清單 → Andy 勾 | 半自動 | `channels/ai_intro/calendar.md` 一週一節 |
| 2 | 寫草稿（Threads 文、IG 輪播文案與分頁腳本） | Claude | 可自動 | `social/ai_intro/queue/<日期>_<代號>.md`，`status: draft` |
| 3 | 自檢 | 程式 | 可自動 | 過 `threads_lint.py`（同一套規則：無推銷、主文無連結、鉤子三類、有情緒、≤500 字）；字數、禁用字、聯盟連結不在主文 |
| 4 | 配圖（IG 輪播） | Claude 產圖 → **art-director 審**（AI 圖）／重疊檢查程式 | 半自動 | 每篇資料夾 `ai_review.md`、`layout_report.json`；沒有審查紀錄不准排程 |
| 5 | 事實與法遵檢查 | legal-compliance 抽查；工具名稱、價格、功能以官方頁為準 | 半自動 | 稿子檔頭 `sources:` 列來源網址與查證日期 |
| 6 | **核准** | **Andy 手動** | **不可自動** | 把 `status: draft` 改成 `status: approved`（可以直接在 GitHub 網頁編輯，或回 Claude 一句「第 X 篇核准」由 Claude 代改並 commit，commit 訊息寫 Andy 原話） |
| 7 | 發文 | 程式（`--channel ai_intro`），每 15 分鐘看一次佇列 | 可自動 | 發出後回寫稿子檔頭 `urls:` |
| 8 | posted 紀錄 | 程式 | 可自動 | `state/ai_intro/posted.json`（與頻道一的 `state/posted.json` 分開） |
| 9 | 留言回覆 | Claude 擬回覆 → Andy 或 Claude 依範本回 | 半自動 | 見第四節 |
| 10 | 成效回收與週報 | 程式＋Claude | 可自動 | `channels/ai_intro/weekly/<週一日期>.md` |

### 2-2 稿子檔頭（建議欄位）

```
---
channel: ai_intro
platform: threads            # threads／ig_carousel／ig_reel
status: draft                # draft → approved → posted（只有 Andy 能改 approved）
scheduled_at: 2026-11-10T20:30+08:00
topic: 工具介紹              # 工具介紹／實測／新聞解讀／觀念／比較
hook_type: 反差
emotion: 吐槽
has_ai_image: false
affiliate: none              # none／comment／bio（見 4-3）
sources:
  - https://…（官方頁，查證日 2026-11-0X）
urls:                        # 發出後程式回寫
---
```

### 2-3 Andy 每週要花多少時間

| 事項 | 頻率 | 時間 |
|---|---|---|
| 勾下週選題 | 每週 1 次 | 5 分鐘 |
| 讀稿＋核准（3～5 篇，每篇 2～3 分鐘） | 每週 1～2 次 | 10～15 分鐘 |
| 看週報（10 行重點＋表格） | 每週 1 次 | 5 分鐘 |
| 留言：只回需要本人判斷的（Claude 標出來，通常 0～5 則） | 每週 | 5～10 分鐘 |
| **合計** | | **約 25～35 分鐘／週** |

一次性：建帳號、Meta 加測試人員、產權杖、放 6 筆 Secrets，約 40～60 分鐘（開工時另給逐格表，照 `meta_api_setup.md` 的格式）。

---

## 三、IG／Threads 分配建議

### 3-1 各平台適合放什麼

| 平台／形式 | 適合的 AI 內容 | 依據 | 每週量（穩定期） |
|---|---|---|---|
| **Threads 純文字（可 0～1 張圖）** | 「一個工具一句話講完它幹嘛」、新聞一句話解讀、反差型觀念（「大家以為 AI 會… 其實…」）、二選一提問 | Threads 純文字也有分發，`threads_rules.md` 的鉤子三類＋情緒規則已經在頻道一運作；成本最低 | 3 則 |
| **IG 輪播（5～7 張）** | 「X 個工具比較表」「三步驟教學」「提示詞範本」—— 會被**收藏**的內容 | `ig_growth_plan.md` 一、1：輪播互動中位數高於單圖與 Reels；一、3：5～7 張表現最好；收藏是 IG 對教學類內容的主要分發訊號 | 1～2 則 |
| **IG Reels（15～30 秒）** | 螢幕錄影實測（「我讓 AI 做 X，結果…」） | Reels 是 IG 觸及新帳號最主要的入口，但製作成本最高（要錄影、剪輯、字幕重疊檢查） | 第二階段起 0～1 則 |
| IG 限動 | 不做 | API 不能加投票／連結貼紙（`ig_growth_plan.md` 一、5），新帳號限動幾乎只有既有追蹤者看得到 | 0 |

### 3-2 要不要先只做一個平台：**要，先 Threads**

| 階段 | 時間 | 做什麼 | 進下一階段的條件 |
|---|---|---|---|
| 第一階段 | 第 1～2 週 | **只發 Threads**，每週 3 則，全部 Andy 核准 | 6 則都準時發出（0 則「已核准沒發」）；單則觀看中位數有數字可比（不設門檻，只要有基準） |
| 第二階段 | 第 3～4 週 | Threads 每週 3 則＋**IG 輪播每週 1 則**（同主題改寫，不是同文複製） | 輪播收藏率 ≥ 1%（收藏 ÷ 觸及）或 Andy 看完週報說繼續 |
| 第三階段 | 第 5 週起 | 視數字加 Reels 每週 1 支，或把表現差的形式砍掉 | 依第五節週報 |

理由：
1. 新帳號 0 追蹤，IG 動態與輪播的初始觸及很低；Threads 對新帳號的推薦面相對寬，先在 Threads 測哪類主題有人看，再把贏的主題做成 IG 輪播，製作成本花在已驗證的主題上。
2. 頻道一 11-02 的教訓是「量大分散」→ 新頻道一開始只維護一條線，出事好查。
3. 輪播要過 art-director 與重疊檢查，第一週就上會讓核准流程變重，Andy 的時間會超過一週 30 分鐘。

---

## 四、留言與私訊回覆規範

### 4-1 原則

1. **回覆時效**：發文後 2 小時內至少看一次（前 2 小時的互動影響分發）；之後每天 1 次。
2. **語氣**：跟主文一樣口語、像朋友；不推銷、不叫人買、不保證效果。
3. **不准在留言做的事**：不承諾「某工具一定能幫你賺錢」、不提供破解／盜版／繞過付費的方法、不代人操作帳號、不索取對方帳號密碼或 API 金鑰。
4. **要 Andy 判斷才回的**（Claude 標「待本人」）：合作邀約、負評或爭議、涉及個資、法律或金錢糾紛、問到頻道一（台股）的投資問題。
5. **Threads 沒有私訊 API**（`comment_dm_plan.md` 第三節），一律公開回覆；IG 私訊可用 Private Replies，但頻道③一開始**不做自動私訊**，等量起來再評估（自動私訊要加 webhook、Worker、KV，工時 2～3 天）。
6. 自動回留言（輪詢 `threads_read_replies`）**第一階段不開**；留言少的時候人工回比自動回更有效，也避免被判定成機器洗版。

### 4-2 常見問題回覆範本 5 則（照情境改字，不整段照貼）

| # | 對方常問 | 回覆範本 |
|---|---|---|
| 1 | 「這個工具要錢嗎？」 | 「基本功能免費可以用，進階的要訂閱，價格以官網當下為準（我查的時候是 ○○）。建議先用免費版試一週，真的天天用再考慮付費！」 |
| 2 | 「哪個 AI 最好用？」 | 「看你要做什麼 —— 寫文案、整理資料、做圖，三種答案不一樣。你最常卡在哪一種？說一個，我下一篇專門比那個…」 |
| 3 | 「有連結嗎？」／「在哪裡下載？」 | 「官方網址我放在第一則留言了（或：個人簡介的連結頁），記得認明官網，別從來路不明的地方下載！」 |
| 4 | 「這樣資料會不會外流？」 | 「好問題，公司機密、個資、客戶資料都不要貼進去。多數服務有『不拿你的對話訓練』的設定，用之前先去設定頁關掉，各家位置不一樣，以官方說明為準。」 |
| 5 | 「可以幫我做 X 嗎？」／「可以教我嗎？」 | 「沒辦法一對一代做，但你這題很多人會遇到，我記下來排進之後的教學！想先自己試的話，可以從○○這個功能開始。」 |

（遇到批評或指正：先謝謝、查證；對方對了就在留言更正並在稿子檔頭記一行 `correction:`，必要時發更正文，不刪留言。）

### 4-3 聯盟連結放哪

| 位置 | 放不放 | 說明 |
|---|---|---|
| Threads 主文 | **不放** | `threads_rules.md` 第 1 條：主文不放連結、不寫「連結在留言」；放了也會降分發 |
| IG 主文（說明文字） | **不放** | IG 說明文字的網址不能點，只會讓貼文像廣告 |
| Threads 第一則留言（reply_post） | 可以放，**每則最多 1 個** | 跟頻道一一樣放在留言；同一則加註「含合作推廣連結」 |
| IG 個人簡介連結頁 | **主要放這裡** | 簡介放一個連結頁網址，頁面依貼文編號列工具連結；IG 留言可回「連結在個人簡介的連結頁，找第 N 號」 |
| 圖片上 | 不放網址、不放 QR | 跟頻道一的圖規則一致（圖上不放網址） |

- **揭露**：只要是聯盟或業配連結，連結旁一定要寫「含合作推廣連結」（或「我會從中獲得分潤」）；簡介也寫一句。台灣公平交易委員會對網路推薦、代言有揭露要求，上線前請 legal-compliance 依現行規定再確認文字。
- 連結頁建議放在自家網域底下的一個頁面（例如 `/ai/links`，開工時再定），可以加 `?u=` 追點擊；不用第三方短網址服務，避免無法追蹤或被判垃圾連結。
- **比例**：一週最多 1～2 篇帶聯盟連結；其他篇純分享，不讓帳號變成廣告帳號。

---

## 五、成效追蹤

### 5-1 每週看哪些數字

| 指標 | 怎麼算 | 為什麼看 | 平台 |
|---|---|---|---|
| **單則觀看中位數** | 當週每則發文後 7 天的觀看數，取中位數（不用平均，避免一則爆紅掩蓋其他） | 11-02 診斷就是看這個發現崩盤 | Threads、IG |
| **收藏率** | 收藏 ÷ 觸及 | 教學類內容最重要的訊號；判斷輪播值不值得做 | IG |
| **分享率** | （分享＋轉發＋引用）÷ 觀看 | 會不會被帶出去 | Threads（reposts＋quotes＋shares）、IG（shares） |
| **互動率** | （讚＋留言＋分享＋收藏）÷ 觀看 | 跟頻道一同口徑，方便比較 | 兩邊 |
| **追蹤轉換** | 當週新增追蹤 ÷ 當週總觀看 × 1000（每千次觀看帶來幾個追蹤） | 新帳號最關鍵：內容有沒有讓人想追 | 兩邊（帳號層級） |
| **連結點擊** | 連結頁 `?u=` 進站次數；聯盟後台的點擊數 | 導流與變現 | 自家漏斗＋聯盟平台 |
| 依標籤拆 | 主題、開頭類型、情緒、形式（純文字／輪播／Reels）、時段 | 找出贏的組合 | 兩邊 |

週報格式：10 行以內重點 ＋ 一張表（本週 vs 上週 vs 第一週基準），放 `channels/ai_intro/weekly/<週一日期>.md`。

### 5-2 既有工具能不能套用

| 工具 | 現在做什麼 | 套到頻道③ | 要改什麼（開工時才改） |
|---|---|---|---|
| `scripts/social_insights.py`（每晚 23:10） | 用頻道一權杖抓帳號層級（觸及、觀看、追蹤數）與最近 10 則的 views／reach（IG）、views／likes／replies（Threads） | **可以**，換成 `AI_INTRO_*` 權杖跑第二份 | ① 加 `--channel` 參數與獨立輸出 `state/ai_intro/posts_catalog.json`；② IG 單則指標要多抓 `saved`、`shares`、`total_interactions`（現在只抓 views、reach，**算不出收藏率**）；③ Threads 單則多抓 `reposts`、`quotes`、`shares`（`threads_insights.py` 已經有這幾個，可照抄）；④ IG 帳號層級加個人簡介連結點擊（Meta 帳號洞察有相關指標，欄位名開工時以官方文件核對） |
| `scripts/news_insights.py` | 讀佇列檔頭標籤＋posts_catalog，按標籤算互動率、產週報、算權重 | **可以，邏輯幾乎照用** | 佇列路徑改成參數（目前寫死 `social/{ig,threads}/queue/*_news-*.md`）；`DIMS` 換成第 2-2 節的 `topic`、`platform`、`hook_type`、`emotion`、`affiliate`；權重收斂規則（樣本 < 3 維持 1.0、探索 20%）照用 |
| `scripts/threads_insights.py` | 定時記每則貼文的累積曲線（append-only CSV） | **可以** | 換權杖、輸出改 `social/ai_intro/insights/metrics.csv` |
| `scripts/threads_hook_stats.py` | 比 v1／v2 與各鉤子模板成效 | 部分可用 | 頻道③沒有 v1，改成只比「開頭類型 × 情緒 × 主題」即可 |
| `?u=` 漏斗 | 帳號 Worker 管理區才看得到，Actions 拿不到（`news_insights.py` 註解） | 可以 | 週報先由 Claude 從管理區讀數字手填，或照 `FUNNEL_JSON` 做法匯入 |

---

## 六、監工與保底

### 6-1 「沒發」的定義

| 狀況 | 算不算「沒發」 | 處理 |
|---|---|---|
| 稿子 `approved`、`scheduled_at` 已過 30 分鐘、`state/ai_intro/posted.json` 沒有、稿子檔頭沒有 `urls:` | **算** | 監工當下：讀 log → 修 → 推 main → 用 workflow_dispatch 補發（**不准用 force／live_test 發正式文**），修到發出為止，寫進 HANDOFF 與這份文件的修改紀錄 |
| 發出了但 IG 輪播少圖、Threads 圖沒帶上 | **算（發錯）** | 回頭兩個平台都確認；圖失敗 → 拿掉那張重發精簡版，不准整篇不發 |
| 稿子還是 `draft`（Andy 沒核准） | **不算** | 不自動發、不補發、不寄失敗信 |
| 總開關或該平台開關 `false` | **不算** | 程式印「頻道③未開啟：略過」並以成功結束 |
| 超過 `limits`（同一天第 2 篇） | **不算** | 自動順延到下一個可發時段，檔頭記 `deferred_to:` |

### 6-2 監工排程（開工時才設，現在不設）

- **只在有已核准稿子的時段檢查**：發文工作流跑完後自己查一次 posted；另外每天 21:30（台北）一次總檢查「今天到期的 approved 是否都有 `urls:`」。沒有 approved 稿子的日子，監工什麼都不做（不會因為「今天 0 篇」叫醒誰）。
- **兩平台都要回頭確認**：發出後用 API 讀回該則貼文，確認圖片數與文字開頭一致，結果寫進 posted 紀錄（`verified: true`）。
- 只有真的發不出去（權杖失效、帳號被限制）才寄信給 Andy，信裡寫清楚哪一篇、卡在哪、已做了什麼。

### 6-3 避免「10-29 沒發」也避免「11-02 前爆量」

| 風險 | 怎麼防 |
|---|---|
| Andy 忙、整週沒核准 → 帳號斷更 | 每週一 10:00 檢查「本週 approved 數 < 2」→ 在 CEO 回報裡提醒一句並附待核准清單；**手上隨時備 3 篇「常備稿」**（不綁時事的觀念、工具基本介紹，已過自檢與審圖），Andy 一句「發常備」就能核准。**不自動發常備稿** —— 頻道③是手動核准制，保底是「讓 Andy 隨時有東西可核」，不是「繞過核准」。 |
| 已核准卻因圖或 API 出錯整篇沒發 | 照頻道一鐵則：圖失敗 → 拿掉那張或改純文字（Threads）；API 失敗 → 重試 3 次（間隔 1、5、15 分鐘）；都不行才叫監工修 |
| 一次核准太多篇、同一天擠出去 | `limits.per_day = 1`、`per_week = 5`、`min_gap_hours = 20`，程式硬擋並自動順延 |
| 頻道③稿子被頻道一權杖發出 | 稿子只放 `social/ai_intro/queue/`，檔頭必有 `channel: ai_intro`；發文程式在頻道一模式下看到 `channel: ai_intro` 直接跳過並記警告（開工時加測試） |
| 自動草稿太多讓 Andy 審不完 | `auto_draft` 預設 false；開了也一週最多產 5 篇草稿 |

---

## 七、開工前要 Andy 決定的事（沒決定前什麼都不做）

| # | 問題 | 建議 |
|---|---|---|
| 1 | 要不要開這個頻道、先開哪個平台 | 先 Threads（第三節） |
| 2 | Meta App 共用或新開 | 共用（1-2） |
| 3 | 開關放新檔或 `post_quota.json` 加區塊 | 新檔 `channels/ai_intro/quota.json`（1-4） |
| 4 | 每週篇數上限 | 3～5 篇、每天最多 1 篇 |
| 5 | 聯盟連結第一階段要不要放 | 第一階段先不放，等有追蹤基礎（第 3 週後）再加，避免新帳號一開始就像廣告帳號 |

決定後的工作量估計：程式（`--channel` 參數、獨立佇列與 posted、開關檔讀取、限量順延、監工、測試）約 1～1.5 天；洞察工具改參數與補指標約 0.5 天；Andy 一次性設定 40～60 分鐘。

## 修改紀錄

- 2026-11-03 social-ops-lead：初版規劃（未啟用，未改任何程式與開關）。
