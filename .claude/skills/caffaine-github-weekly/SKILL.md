---
name: caffaine-github-weekly
description: CaffAIne（頻道③ caffaine.ai）的「資訊差」發文技能：每週抓 GitHub 前 10 名熱門 repo → 收集相關討論（Grok／WebSearch／GitHub issues）→ 統合成爆文格式＋做圖 → 每天晚上 19:13 固定發。Andy 說「GitHub 熱門」「本週新豆」「資訊差」「搬運 GitHub」「幫 CaffAIne 做這週的貼文」「AI 頻道要發文」時使用。產出放 docs/marketing/channels/caffaine/queue/，走既有 channel_post.yml 發文。
---

# CaffAIne｜GitHub 每週熱門「資訊差」發文技能

> Andy 2026-11-14 原話：「想要衝粉絲的手段之一：『搬運』／每週找 前10 的 GitHub repo／用 grok 爬相關的討論建立貼文／用 ChatGpt 統合成爆文形式+做圖／然後每天晚上固定發文／恭喜學會『資訊差』／幫我將這技巧寫在 AI 內，以後需要發文用的技能」

**一句話**：英文圈（GitHub、X、Reddit、Hacker News）已經在討論的工具，台灣上班族還不知道 → 我們先整理成看得懂的中文，這就是資訊差。

欄目名稱：**☕ 本週新豆**（新鮮的豆子＝這週剛冒出來的工具；跟試飲報告／手沖教室／本週三杯／這杯有點苦同一套咖啡菜單）。Andy 要換名字就改這裡與 `opening_closing.md`。

---

## 〇、先看這三條紅線（違反就不准發）

1. **「搬運」只搬資訊，不搬別人的作品。** 不貼別人的推文截圖、不整段翻譯別人的文章、不拿 README 的圖當自己的圖。IG 2026 起把「轉貼／聚合帳號」降權，原文照搬一定會被壓（`docs/marketing/channels/ai_intro/research.md` 第 51 列）。每篇一定要有**我們自己加的東西**：中文白話、適合誰、不適合誰、跟熟悉的工具比、要注意什麼。
2. **沒試過的不說「好用」**（CaffAIne 三原則之一）。沒親手跑過 → 文中寫「還沒實測」，只講「它做什麼、多少人關注、大家在討論什麼」。親手跑過 → 才可以下評價，而且可以升級成「☕ 試飲報告」。
3. **每個數字都寫出處與日期**（Andy 2026-11-10：「主題可以聳動，但內文必須有確實的佐證」）。星星數寫「截至 11/14 台北，GitHub 數字」；引用討論寫「X 上 @某某 說…（11/12）」或「Reddit r/LocalLLaMA 討論串」。

⚠ 11-02 的教訓（`docs/marketing/diagnosis_1102/`）：**自動摘要一天十幾則 → 單則觀看崩到幾十**。所以這套**每天最多 1 則**、每篇都要有上面第 1 條的「自己加的東西」，不准變成機器量產的清單文。

---

## 一、一週節奏（每天晚上 19:13 自動發，保底 20:43）

| 星期 | 發什麼 | 張數 |
|---|---|---|
| 週日 | **本週新豆 Top 10 總表**：10 個 repo 各一行（名稱＋一句中文＋星星數） | 輪播 5～7 張 |
| 週一、三、五、六 | **單篇深入**：從 Top 10 挑 4 個最適合上班族的，一天一個 | 輪播 5～7 張 |
| 週二、四 | 留給影片（`video_plan.md`：週二手沖教室、週四試飲報告）；沒影片才用新豆補位 | — |

- 一天只有 1 個名額（`docs/marketing/channels/caffaine/post_quota.json` 的 `per_day: 1`）；不補發、不一天兩則。
- 時段由 `channels.json` 決定（台北 19:13），本技能不改時段。

---

## 二、步驟

### 步驟 1｜選出本週 Top 10（每週六晚上或週日早上做）

**主要來源：GitHub 搜尋 API**（這個容器只能用 `gh` 做搜尋，見系統說明）：

```bash
# 過去 7 天新建、星星最多的 30 個（多抓，篩完剩 10）
SINCE=$(TZ=Asia/Taipei date -d '7 days ago' +%F)
gh api -X GET search/repositories -f q="created:>$SINCE stars:>100" \
  -f sort=stars -f order=desc -f per_page=30 \
  --jq '.items[]|[.full_name,.stargazers_count,.forks_count,.license.spdx_id,.created_at,.description]|@tsv'

# 補充：AI 主題、這週有更新、星星多的老專案（例如大版本更新）
gh api -X GET search/repositories -f q="topic:llm pushed:>$SINCE stars:>2000" -f sort=updated -f per_page=20 --jq '...同上...'
```

輔助來源（換關鍵字用 `WebSearch` 查）：「GitHub trending this week」「trending repositories AI agent」、Hacker News「Show HN」。GitHub Trending 頁面本身這個容器打不開，用 WebSearch 摘要當線索，數字一律以 `gh api` 抓到的為準。

**篩選規則（照順序）**

| # | 規則 | 不符合 → |
|---|---|---|
| 1 | **跟受眾有關**：AI 工具、工作效率、寫程式、自動化、筆記會議、簡報設計、創業工具 | 剔除（例如 iOS 系統修改工具、遊戲） |
| 2 | **排除灰色**：破解、盜版、越獄、模擬器加「自備金鑰」、繞過付費／驗證、偷帳號、色情、加密幣發幣、惡意程式、偵察個人資料 | 一律剔除，不寫 |
| 3 | **看得懂、有在動**：README 有說明、有授權（`license` 不是空的）、最近 7 天有 commit | 剔除或降順位 |
| 4 | **刷星檢查**：星星很多但 fork 極少、issue 0、作者帳號剛建 → 可疑 | 剔除 |
| 5 | **台灣上班族用得到**：不用 GPU 叢集、不用寫程式也能試（或有線上 demo） | 排後面，總表可以放、深入篇不選 |

產出：`docs/marketing/channels/caffaine/weekly_github/<YYYYMMDD>/top10.md`：表格欄位＝排名、repo、中文一句話、星星數（附抓取時間）、授權、為什麼入選、剔除了誰、為什麼剔除。

### 步驟 2｜收集討論（Grok／WebSearch／GitHub）

- **Andy 自己用 Grok 的話**（Grok 能搜 X 即時貼文；這個容器沒有 Grok 金鑰），請他貼這段提示詞，把結果貼回來：

```
請搜尋 X（Twitter）過去 7 天關於 GitHub 專案「<owner/repo>」的討論。
列出：1) 最多人按讚或轉發的 5 則貼文（作者帳號、日期、重點一句、連結）
2) 大家最稱讚的 3 個點 3) 大家最擔心或批評的 3 個點
4) 有沒有人拿它跟其他工具比較（跟誰比、結論）
不要編造，找不到就寫「找不到」。每一點都要附連結。
```

- **Claude 自己做**（不等 Andy）：
  - `WebSearch`：「<repo 名> review」「<repo 名> reddit」「<repo 名> hacker news」「<repo 名> vs <相似工具>」，至少 3 組關鍵字。
  - `gh api repos/<owner>/<repo>/issues?state=all&sort=comments&per_page=10`：留言最多的 issue＝使用者真正卡住的地方（這是「要注意什麼」最好的素材）。
  - `gh api repos/<owner>/<repo>/releases?per_page=3`：這週到底更新了什麼。
- ⚠ WebSearch 的摘要會自己「補」對應關係（CLAUDE.md 有兩次事故）。**數字與「誰說的」都要第二個來源對得上**才寫進文案；對不上就不寫。
- 產出：`weekly_github/<YYYYMMDD>/<repo>_討論.md`（每條附連結與日期、信心度高／中／低）。

### 步驟 3｜統合成爆文（ChatGPT 或 Claude 都可以，規則一樣）

文案規則照 `docs/marketing/social_unit/threads_rules.md` 與 `docs/marketing/channels/ai_intro/opening_closing.md`。

**爆文骨架（單篇深入，輪播 5～7 張）**

| 張 | 內容 | 範例 |
|---|---|---|
| 1 封面 | `☕ 本週新豆｜` ＋ 一句完整、有反差的鉤子（≤ 20 字大字） | ☕ 本週新豆｜一週 1,300 顆星：會議記錄不用再上雲端了！ |
| 2 | 它是什麼（一句白話，不用術語）＋ 星星數與日期 | 開源的 AI 會議筆記，資料只存在你自己電腦。GitHub 1,353 顆星（截至 11/14） |
| 3 | 為什麼大家在討論（引 2～3 則討論重點，附出處） | Reddit 上最多人說：「終於不用把公司會議丟到別人伺服器」 |
| 4 | 適合誰／不適合誰 | 適合：會議多、公司不准用雲端錄音的人／不適合：不想自己安裝軟體的人 |
| 5 | 要注意什麼（來自 issue 與批評） | 目前只支援 Mac 晶片加速，Windows 版很慢（GitHub issue #12） |
| 6 | 我們的判斷：「還沒實測」或「試飲過：…」＋ 收尾句 | 還沒實測，下週試飲報告開箱給你看。咖啡涼之前，先存起來！ |

**總表（週日 Top 10）**：封面「☕ 本週新豆｜GitHub 這週最紅的 10 個工具，上班族用得到的有這 4 個！」→ 每張 2～3 個 repo（名稱、一句中文、星星數）→ 最後一張「這週會深入哪 4 個」。

**caption.txt**：第一句＝封面那句；中間 3～5 行重點；最後一行收尾句（從 `opening_closing.md` 第三節輪替，14 天內不重複）；repo 連結放最後；#標籤 3～5 個（#AI工具 #GitHub #CaffAIne #本週新豆）。Threads 版連結放在留言，不放主文。

**給 ChatGPT 的提示詞（Andy 要自己用 ChatGPT 時貼這段，Claude 也照這段寫）**：

```
你是 IG／Threads 的繁體中文（台灣）AI 工具帳號編輯，帳號叫 CaffAIne，口號「一杯咖啡的時間，看懂一個 AI 新知」，讀者是台灣上班族。
請把下面的 repo 資料與討論整理成 6 張輪播的文字：
規則：1) 第一句就講完整一件事，要有反差或數字，不准「大家好」「你知道嗎」
2) 每張 ≤ 40 字，不用英文術語，必要的專有名詞第一次出現寫「中文（原文）」
3) 每個數字後面括號寫出處與日期 4) 不准寫「最強」「必裝」「保證」「免費賺錢」
5) 我們沒親手試過，所以不准說「好用」，要寫「還沒實測」
6) 結尾不准「歡迎留言／謝謝收看」，用「！」或「…」收
資料：<貼上 top10.md 那一列＋討論.md>
```

### 步驟 4｜做圖

- **首選：CaffAIne 版型產圖**（`docs/marketing/channels/ai_intro/layouts_caffaine/gen.js`，1080×1350，LOGO 07 八位元衝框色系），文字由程式排，保證不重疊、字級一致。
- repo 的「身分卡」用我們自己畫的卡片（repo 名、星星、授權、語言），**不直接貼 README 的圖或 demo 影片截圖**；真的要用（例如介面長相是重點）→ 只截 GitHub 頁面一小塊、角落寫「圖：GitHub <owner/repo>」。
- **AI 生圖**（容器可以呼叫 OpenAI 產圖）只能當背景或插圖：不畫成真實產品介面（會誤導）、不放比比、不仿任何公司 LOGO（10 月 art-director 抓過「像 Adobe Illustrator」「像 Gemini 四角星」）。
- 每張圖都要：
  1. **重疊檢查**：程式量每個文字框兩兩不相交、間距 ≥ 24px，回報寫「重疊檢查：程式 N 張 0 筆；人工 N 張 0 筆」。
  2. 有 AI 生圖 → 派 `art-director` 審，資料夾留 `ai_review.md`（沒有不准 `approved`）。發文時開 IG 的「AI 資訊」標籤。

### 步驟 5｜放進佇列（照 `docs/marketing/channels/auto_post_all.md` 第 2 節）

```
docs/marketing/channels/caffaine/queue/<YYYYMMDD>_gh_<短名>/
  1.png … 7.png
  caption.txt
  meta.json   {"title": "本週新豆｜<repo>", "platforms": ["ig","threads"], "status": "draft", "publish_at": "<YYYY-MM-DD>T19:13+08:00"}
  ai_review.md（有 AI 圖才要）
  sources.md（這篇每個數字、每句引用的出處連結）
```

- **先放 `draft`**。前 2 週每篇都先給 Andy 看（推 `preview/` 或直接傳圖），他說 OK 才改 `approved`。Andy 說「之後不用給我看」後，改成 `inspector` 對照下面清單通過就 `approved`。
- 一次可以排好一週（每篇寫自己的 `publish_at`），工作流一天只發 1 則。
- 發完證據：`docs/marketing/channels/caffaine/state/posted.json` 有網址才算發出。沒發 → 照 `auto_post_all.md` 第 7 節處理到發出為止。

---

## 三、發文前檢查清單（缺一不准 `approved`）

| # | 項目 |
|---|---|
| 1 | repo 通過篩選規則 1～4（不是灰色、不是刷星） |
| 2 | 每個數字有出處＋日期；每句引用有連結，在 `sources.md` |
| 3 | 有「我們自己加的東西」（適合誰、不適合誰、要注意什麼），不是翻譯 |
| 4 | 沒實測就寫「還沒實測」；沒有「最強／必裝／保證」 |
| 5 | 沒貼別人的推文截圖、沒整段翻譯別人文章 |
| 6 | 第一句講完整、收尾句 14 天內沒用過、Threads 連結在留言 |
| 7 | 重疊檢查兩行都 0 筆；AI 圖有 `ai_review.md`；沒有比比 |
| 8 | 全部繁體中文（專有名詞例外） |
| 9 | 有業配一定標明（GitHub 專案作者找上門也算） |

## 四、成效與調整（4 週後檢討）

- 看 `docs/marketing/channels/caffaine/state/insights/`：每篇觸及、收藏、分享、新增粉絲。
- 比較：總表 vs 單篇深入；「還沒實測」 vs「試飲過」。收藏高的題目 → 下週做成手沖教室或試飲報告。
- 停損：連 2 週單篇觀看中位數 < 200 → 先檢查是不是變成清單文、鉤子太弱，**不加量**。
- CaffAIne 的每週檢討由頻道③自己排（頻道④ 11-10 已不再涵蓋 caffaine）。

## 五、修改紀錄

- 2026-11-14：Andy 原話建立本技能（每週 GitHub 前 10 → 收集討論 → 爆文＋做圖 → 每天晚上固定發）。CEO 加上原創性、出處、灰色 repo 篩選與 11-02 降量教訓的護欄。
