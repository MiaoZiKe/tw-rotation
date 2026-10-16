# 防白嫖：精選文章分級與今日事件訪客 5 次，現在擋得住什麼、要怎麼補（2026-10-16）

> 資安與隱私專家產出。**這份只有文件，沒有改任何產品程式碼、沒有部署。**
> 核對對象：`origin/main`、`origin/preview/articles-tier`（d0ba8384）、`origin/preview/today-events-5`（b84bc695）。
> 程式事實一律是**讀原始碼**得到的（信心：高）；網路資料只來自 WebSearch 的**摘要**（沒有讀過原文），各條標信心度。
> 法律部分是風險盤點，**不是法律意見**。
>
> Andy 的問題：「非付費者用無痕視窗、清除網站資料、或關閉瀏覽器重開，次數會不會重算？」＋「需要避免被白嫖」。

---

## 〇、結論先講（給 Andy 的 6 行）

1. **關掉瀏覽器再打開：不會重算。** 次數存在 localStorage（`tw.total`），一般視窗關掉重開會保留。
2. **無痕視窗、清除網站資料、換瀏覽器、換裝置：都會從 0 開始算。** 付費的 Plus 會員也一樣：清掉資料就又有 5 篇。
3. **更嚴重的是，就算不重算也擋不住**：4 篇精選文章的全文就放在公開的網址 `articles/posts/<id>.json`，**同一份也在 public repo 裡**；今日事件的資料（`news.json`、`broker_views.json`）也是公開檔，而且原始新聞每天都 commit 進 public repo 的 `data/news/`。**前端的分級是「門檻」，不是「鎖」。**
4. **我另外撞到兩個「一鍵全開」的洞**：擋掉會員伺服器的網址、或擋掉 `quota.js` 這一支檔，分級就**自動整個放行**（程式設計成「連不到就寧可多給」）。這兩個用瀏覽器內建的開發者工具就做得到，不用寫程式。
5. **最小有效版本（建議先做，約 2.5～3.5 個工作天）**：
   ① **精選文章全文搬到會員 Worker**（只有登入且有權限的人拿得到全文，Plus 的 5 篇在伺服器端算）——這一件做完，文章就**真的**擋住了，而且**不需要訪客計數**（訪客本來就只能看標題）；
   ② 今日事件的訪客 5 次改成**伺服器端計數**（隨機訪客編號＋IP 雜湊雙鍵）；
   ③ 把「連不到就全開」改成「連不到就照訪客算」。
6. **已經公開過的 4 篇收不回來**（repo 歷史、預覽版、別人可能已存檔）。從第 5 篇起才真的受保護。

---

## 一、現況：如實說明

### 1-1 次數存在哪、什麼情況會重算

程式出處：`site/quota.js`（preview/articles-tier 與 preview/today-events-5 兩個分支各自新增的 `TwQuota.total` 區塊，內容相同）。

- 存在 **localStorage 的 `tw.total`**，依身分分開：訪客記在 `guest`、會員記在 `u:<email>`。**永遠不歸零**（不是每日）。
- localStorage 寫不進去時（少數私密模式），改存在記憶體 `TOT_MEM`：**重新整理就歸零**。
- 程式註解自己也寫了：「只擋畫面、非伺服器端……清除網站資料、換瀏覽器、無痕視窗都會從頭算」。

| 使用者做了什麼 | 次數會不會重算 | 說明（信心） |
|---|---|---|
| 一般視窗關掉瀏覽器再打開 | **不會** | localStorage 跨重開保留（高） |
| 重新整理、開新分頁 | 不會 | 同上（高） |
| 開無痕視窗 | **會，從 0 開始** | 無痕視窗有自己的一份空白儲存區，關掉就丟（高） |
| 無痕視窗關掉再開一個 | **會，又從 0 開始** | 每開一次就又有 5 次（高） |
| 清除網站資料／Cookie | **會** | localStorage 一起被清（高） |
| 換瀏覽器（Chrome → Edge） | **會** | 各瀏覽器的儲存區不共用（高） |
| 換裝置（電腦 → 手機） | **會** | 同上；**登入的 Plus 會員也一樣**，換台裝置又有 5 篇（高，程式事實：計數鍵是 email，但值存在本機） |
| 在開發者工具刪掉或改 `tw.total` | **會，而且可以改成任何數字** | 見 1-3 #5（高） |

### 1-2 為什麼「重不重算」其實是次要問題

即使次數完全不會被重算，資料本身也是公開的：

| 東西 | 放在哪 | 誰拿得到（已核對） |
|---|---|---|
| 精選文章**全文**（4 篇） | `site/articles/posts/<id>.json`；部署到 `https://miaozike.github.io/tw-rotation/articles/posts/<id>.json` 與 Cloudflare Pages 的同一路徑 | **任何人**，不用登入。單篇頁的程式在沒授權時「不去抓」全文，但網址是固定可猜的（id 就寫在 `index.json` 裡） |
| 精選文章**清單、摘要、副標** | `site/articles/index.json` | 任何人。⚠ 畫面上對沒授權的人寫「摘要與內文不會顯示」，但摘要（每篇約 170 字）就在這支公開檔裡 |
| 精選文章全文在 **public repo** | `site/articles/posts/*.json`，main 上 9 個 commit 動過它們 | 任何人瀏覽 GitHub 就能讀，含**製作中的草稿版本**（例如 `a035b6d5 精選文章（製作中）`）——**文章上架之前就已經公開了** |
| 寫作流程與選題 | `docs/articles/production_guide.md`、`docs/articles/topic_research_1014.md`、`site/articles/topics.json` | 任何人（這是方法，不是內容，但競爭者可以照抄） |
| 今日事件完整清單 | `site/data/news.json`（約 359KB）、`news_head.json`（前 30 則）、`broker_views.json` | 任何人，`/tw-rotation/data/news.json` 直接下載 |
| 今日事件的原始資料 | `data/news/year=2026/part.parquet`（1.1MB）、`data/broker_views/…`、`data/material_news/…` | **每天 commit 進 public repo** |
| 預覽版 | `preview/<名稱>/` 底下有一份完整的 `site/`（含 `articles/posts`） | 任何人；預覽版自己一律以擁有者身分放行 |

repo 目前 fork 數 0（`gh api` 查，2026-10-16 19:00 台北）。這不代表沒人複製過：clone 不會留紀錄。

### 1-3 繞過方式清單（實際核對過）

「難度」：**極低**＝一般人會做（按兩下）；**低**＝會用瀏覽器開發者工具（F12），照網路教學 5 分鐘學會；**中**＝會寫幾行程式或用指令列；**高**＝要花錢或花時間經營。
「後端計數擋得住嗎」指的是**階段 1（只做伺服器端計數、內容仍是公開檔）**；「搬到後端擋得住嗎」指的是**階段 2（內容移到受控端點）**。

| # | 繞過方式 | 對象 | 難度 | 現在擋得住？ | 階段 1 後端計數擋得住？ | 階段 2 內容搬後端擋得住？ |
|---|---|---|---|---|---|---|
| 1 | **開無痕視窗**，每次重開就有 5 次 | 今日事件（訪客）；文章（訪客本來就只有標題，無效） | 極低 | ❌ | ⚠ 大部分擋得住：靠 IP 雜湊那一鍵；換網路（手機 4G ↔ Wi-Fi）就又能拿到一份 | ⚠ 同左（訪客計數的本質限制） |
| 2 | **清除網站資料** | 同上，**以及 Plus 的 5 篇** | 極低 | ❌ | 訪客：同 #1；Plus：✅（改用帳號計數） | ✅（Plus 以帳號計） |
| 3 | **換瀏覽器／換裝置** | 同上 | 極低 | ❌ | 訪客：同 IP 擋得住、不同網路擋不住；Plus：✅ | ✅（Plus） |
| 4 | **直接打 JSON 網址**（`articles/posts/<id>.json`、`data/news.json`） | 文章全文、今日事件全清單 | 低（從網址列或 F12 的「網路」分頁看得到網址） | ❌ | ❌ **計數完全擋不住**：根本沒經過計數 | ✅ 文章；今日事件要把 `news.json` 也搬（見 2-2-4） |
| 5 | **改 localStorage**（F12 → 應用程式 → 刪 `tw.total` 或把陣列清空） | 兩者 | 低 | ❌ | ✅（計數不在本機了） | ✅ |
| 6 | **擋掉會員伺服器網址**（F12 → 網路 →「封鎖要求網址」，或廣告擋除器加一條規則） | 兩者，**直接全開** | 低 | ❌ **而且是全開**：`site/quota.js` 的 `pick()` 在權限來源是 `default`（連不到伺服器）時回「不限」；`articles.js` 的 `permReady()` 等 4 秒就放行（註解：「寧可多給，不要誤鎖」） | ⚠ 只有把「連不到＝全開」改成「連不到＝照訪客」才擋得住（見 3-1 ③） | ✅（拿不到全文就是拿不到） |
| 7 | **擋掉 `quota.js` 這一支檔** | 兩者，**直接全開** | 低 | ❌ **全開**：`articles.js` 的 `access()` 第一行 `if (!T) return { mode: 'full' }`；`app.js` 的 `evTotalT()` 回 null 就不擋 | ⚠ 同 #6，要改成「沒有計數模組＝照最嚴格的算」 | ✅ |
| 8 | **關掉 JavaScript** | — | 極低 | ✅ 本身不算繞過：整站是 JS 畫的，關掉什麼都看不到 | — | — |
| 9 | **看 public repo**（GitHub 網頁直接讀 `site/articles/posts/`、`data/news/`） | 文章全文（含草稿）、新聞原始資料 | 極低（會用 GitHub 就會） | ❌ | ❌ | ✅ 新文章；❌ 已經在歷史裡的 4 篇 |
| 10 | **讀預覽版**（`/preview/<名稱>/`） | 兩者 | 低（要知道預覽網址；網址規則寫在 public repo 的 `docs/preview.md`） | ❌ 預覽版一律以擁有者身分全開；`?demo_tier=` 只是示範 | 不適用 | ✅（全文不在預覽版的靜態檔裡） |
| 11 | **開多個 Google 帳號**（訪客 → 免費會員，每個新帳號一份） | 今日事件（註冊會員本來不受 5 次限制，所以無意義）；未來若免費會員有額度就有意義 | 中（要多個 Gmail） | 不適用 | 不適用 | ⚠ 只能用 Google 帳號限制＋同 IP 每日新帳號上限（現有 welcome 那套）降低 |
| 12 | **付費會員分享帳號** | 文章 | 極低 | ❌ | ❌ | ⚠ 階段 3 的同時裝置數與浮水印降低 |
| 13 | **付費會員複製全文轉貼** | 文章 | 極低（選取 → 複製） | ❌ | ❌ | ❌ 技術上**永遠擋不住**；只能靠浮水印追查＋條款（階段 3） |
| 14 | **寫程式自動抓**（爬蟲） | 兩者 | 中 | ❌ | ❌（JSON 公開） | ✅ 需要登入權杖＋速率限制 |
| 15 | **Wayback Machine／搜尋引擎快取** | 已公開過的 4 篇 | 低 | ❌ | ❌ | ❌ 已被存檔的收不回（我**沒查**是否已被存檔：這個容器打不開 archive.org） |

**一句話：** 階段 1 只擋得住「#1～#3、#5 的一般人」；真正擋得住「懂一點 F12 的人」要靠階段 2；#13（付費者自己轉貼）任何技術都擋不住。

---

## 二、分階段方案

先講既有家當（讀程式碼確認，信心：高），因為**大部分零件已經在了**：

| 既有東西 | 狀態 | 能拿來做什麼 |
|---|---|---|
| 會員 Worker `workers/account-api`（`tw-account`） | **推 main 就自動部署**（`deploy-account-worker.yml`）；有 Durable Object（SQLite）；已有 Google 登入、權杖、方案與功能開關、`/v1/quota/hit` 每日扣次、`/v1/articles/view` 點閱數 | 階段 1 計數、階段 2 文章全文與伺服器端扣額度 |
| 現成的「IP 只存 HMAC」做法 | `worker.js` 體驗額度區塊：`grant_ip` 表只存 `hmac('gip:'+IP)`、保存 2 天，**隱私權政策已有對應文字**（`site/legal.js` 第 215 行） | 階段 1 的 IP 雜湊鍵直接照抄 |
| 付費資料閘道 `workers/data-gw` | **寫好、測試在，但沒上線**：只能手動部署、`DATAGW_SPLIT` 沒開；需要 Andy 先開 R2 bucket 等 5 個 ★ 步驟（`docs/datagw_plan.md` 第 10 節）。`HANDOFF.md` 第 394 行：「data-gw 沒有部署」 | 階段 2 的 `news.json`；它的浮水印、限流、異常規則給階段 3 |

### 階段 1：伺服器端計數（訪客與註冊會員）

**目標**：讓「開無痕／清資料／改 localStorage」這些一般人做得到的方法失效。**內容仍是公開檔**，所以 #4、#9 照樣擋不住 —— 這一階段擋的是「一般人」，不是「懂技術的人」。

#### 1-A 計數怎麼做（雙鍵）

新端點放在**會員 Worker**（不用等 data-gw 上線）：

- `POST /v1/total/use {id:'events.total', key:<這次打開的編號>, g:<訪客編號>, t:<登入權杖，選填>}` → `{ok:true, used, limit}` 或 `{ok:false, used, limit}`
- `POST /v1/total/state {ids:[...], g, t}` → 目前各功能用了幾次（給畫面顯示「已用 3／5」）

鍵怎麼取：

| 身分 | 主鍵 | 第二鍵 | 判斷 |
|---|---|---|---|
| 登入會員 | `uid`（伺服器從權杖解出來，前端改不到） | 不需要 | `used(uid) < limit` |
| 訪客 | **訪客編號 `g`**：Worker 第一次發給他、帶 HMAC 簽章（`g1.<隨機 16 位元組>.<簽章>`），前端偽造不了 | **IP 雜湊**：`HMAC(伺服器鹽, 'tot:' + IP 網段)` | `used(g) < limit` **且** `used(IP 雜湊) < IP 上限` |

- 為什麼要第二鍵：只有訪客編號的話，開無痕＝拿到新編號＝又有 5 次。加上 IP 雜湊後，同一個網路開再多無痕視窗，加總也只到 IP 上限。
- IP 網段：IPv4 取完整位址（家用多半一戶一個），IPv6 取**前 64 位元**（同一戶的裝置共用一個 /64，只看完整位址的話換一台手機就是新的）。
- **IP 上限不能跟個人上限一樣是 5**（見 1-C 共用 IP），建議 IP 上限 = 20 次／7 天，個人 5 次累計。
- 「累計不歸零」只適用在訪客編號這一鍵；**IP 這一鍵必須有期限**（建議 7 天滾動），否則個資保存無限期、而且動態 IP 換手後會誤擋下一個人。

#### 1-B 訪客編號放 Cookie 還是 localStorage？—— 建議 localStorage＋請求標頭

Andy 原本的構想是「cookie 隨機 id」。我核對後建議改成**由 Worker 簽發、存在 localStorage、每次用請求標頭送**，理由：

1. **第三方 Cookie 的問題**：網站在 `miaozike.github.io` 與 `liguligu-puipui.com`，會員 Worker 在 `*.workers.dev`，對瀏覽器來說是**不同網站**。Safari、Firefox、Brave 預設擋或分隔第三方 Cookie（中：只有一個二手來源的摘要提到）；Chrome 在 2025 年 4 月宣布**維持**第三方 Cookie 預設可用，不再強推淘汰（中高：多個二手來源一致）。也就是 **Cookie 在 Safari（iPhone 訪客的主力）上會拿不到** → 每次都像新訪客。要讓 Cookie 可靠，得把 Worker 綁到 `api.liguligu-puipui.com`，但 `miaozike.github.io` 那一份仍然是第三方。
2. **防清除的效果一樣**：使用者「清除網站資料」會同時清掉 Cookie 與 localStorage；無痕視窗兩者都是空的。HttpOnly Cookie 只多擋了 #5（改 localStorage），但 1-A 的簽章已經擋住偽造，刪掉只會變成「新訪客」，而新訪客會被 IP 鍵接住。
3. **隱私權政策現在寫「不使用 Cookie 進行追蹤」**（`site/legal.js` 第 227 行）。用 localStorage 存編號不違反這句的字面，但**實質上仍是識別碼，一樣要在政策裡寫出來**（見 1-D）——不可以拿「我沒用 Cookie」當不告知的理由。

#### 1-C 共用 IP（公司、學校、手機網路）誤擋

| 情境 | 會發生什麼 | 緩解 |
|---|---|---|
| 公司／學校幾百人共用一個對外 IP | IP 鍵很快用完 → 同事**第一次來**就被擋 | IP 上限放寬到 20 次／7 天；**只有在「同一個 IP 出現超過 3 個新訪客編號」時才開始用 IP 鍵**（正常的同事每人只有一個編號，只有反覆開無痕的人才會一直產生新編號） |
| 手機網路（電信業者的共用位址轉換，CGNAT）多人共用 IP | 同上，而且 IP 每次連線可能不同 | IP 鍵在手機網路上本來就弱（擋不到、也比較少誤擋）；接受 |
| 浮動 IP 換到別人手上 | 前一個人的 IP 鍵用量被後一個人繼承 | 7 天滾動視窗；IP 鍵只擋「新編號」 |
| 被擋的人 | 看到「這個網路的訪客預覽已用完」 | 提示卡**不要寫「你在白嫖」**；直接給「免費註冊（Google 一鍵）」按鈕。註冊會員不受 `events.total` 限制，所以誤擋的代價只是「多按一次登入」 |

**殘餘風險（照實講）**：換網路（Wi-Fi ↔ 4G）＋無痕、或 VPN，每換一次 IP 就又有 5 次。這一層**沒辦法**在不蒐集更多個資（裝置指紋）的前提下擋住，我**不建議**做瀏覽器指紋：它在個資法上更敏感、可靠度也不高、而且跟「不追蹤」的定位衝突。對策是讓「免費註冊」比「一直換網路」更省事。

#### 1-D 隱私與個資法

- **IP 屬不屬於個資**：台灣個資法的定義是「得以直接或間接方式識別該個人之資料」。有一篇二手文章（iThome 鐵人賽）提到**國發會 2020 年以函釋表示 IP 屬個人資料**，並引用歐盟法院 2016 年 C-582/14 判決（動態 IP 在網站經營者有合法管道可結合他方資料識別時屬個資）。**信心：中**——歐盟判決有多個獨立來源一致；**國發會函釋我查了兩組關鍵字都只找到同一篇二手文章，查不到函釋字號與原文**，標「未確認」。實務結論不變：**把 IP 當個資處理**（這也是 `datagw_plan.md` 與現行隱私權政策的口徑）。
- **雜湊後還算不算個資**：用固定鹽的 HMAC，同一個 IP 永遠得到同一個值，伺服器（持有鹽的人）有能力把它跟 IP 對回來 → **我判斷仍屬「間接識別」的個資，不能說成「匿名」**（中，判斷）。所以照樣要告知、要有保存期限。
- **做法（照現有 `grant_ip` 的口徑，好跟政策一致）**：
  1. 不存原始 IP，只存 `HMAC(鹽, 'tot:'+IP)`；鹽是 Worker Secret，**不寫進 repo**；
  2. **每 7 天換一次鹽**（舊鹽丟掉 → 舊的雜湊值永久對不回 IP），IP 鍵的資料表 8 天自動刪；
  3. 訪客編號那一鍵只存「編號＋用了哪幾次」，不存 IP、不存瀏覽器資訊；**訪客編號 180 天沒出現就刪**（累計不歸零的「累計」實務上需要上限，不然個資保存無限期）；
  4. 不跟會員帳號串接（訪客登入後不把訪客編號併進帳號）；
  5. 不給第三方、不用於行銷。
- **隱私權政策要補的段落（草稿，可直接貼到 `site/legal.js` 的蒐集表與「Cookie 與本機儲存」兩節）**：

> **訪客使用次數**：為了讓未註冊的訪客能試用部分功能並限制使用次數，本網站會在您的瀏覽器儲存一組由伺服器產生的隨機訪客編號，並在伺服器上記錄該編號已使用的次數。同時，為防止同一網路以重開瀏覽器等方式重複領取，伺服器會以保密金鑰對您的連線 IP 位址進行單向運算（HMAC）後保存 **8 日**，運算金鑰每 7 日更換，舊資料無法還原為原始 IP；**本網站不保存原始 IP**。訪客編號若 **180 日**未使用即刪除。上述資料僅用於計算試用次數，不用於行銷、不與會員帳號合併、不提供予第三方（法令要求除外）。您可隨時清除瀏覽器資料以刪除本機的訪客編號；清除後，同一網路於上述期間內的使用次數仍會合併計算。

  「Cookie 與本機儲存」那一節的「不使用 Cookie 進行追蹤」維持；在 localStorage 那一條加一句「以及訪客使用次數之隨機編號（說明見上）」。
  ⚠ 政策、`account.js` 告知、Worker 實際保存期限三處要同步（DECISIONS #270-7 的規則）。

#### 1-E 階段 1 估工

| 項目 | 檔案 | 工作量 |
|---|---|---|
| 新端點 `/v1/total/use`、`/v1/total/state`、訪客編號簽發、IP 雜湊表、換鹽與清除排程（沿用每天 03:17 那個 cron） | `workers/account-api/total.js`（新，照 `articles.js` 的掛載方式）、`worker.js` 掛一行 | 0.75 天 |
| 測試（訪客 5 次、無痕＝新編號但同 IP 被接住、共用 IP 的 3 個新編號門檻、會員以 uid 計、偽造編號拒絕、換鹽後舊資料失效） | `workers/account-api/tests/total.test.mjs`（新） | 0.5 天 |
| 前端 `TwQuota.total` 改成「先問伺服器、localStorage 只當顯示快取」；**連不到伺服器時照訪客額度 0 處理**（不是全開） | `site/quota.js`、`site/app.js`（今日事件）、`site/articles.js`（Plus 篇數） | 0.5～0.75 天 |
| 隱私權政策＋告知同步 | `site/legal.js`、`site/account.js` | 0.25 天 |
| `_uitest` 對應段落改寫（現在測的是 localStorage） | `scripts/uitest_sections/20261016_*.py` | 0.25～0.5 天 |
| **合計** | | **2.25～2.75 天** |

- **新增端點**：`/v1/total/use`、`/v1/total/state`（加上 Worker Secret `TOTAL_SALT_SEED`，由 workflow 帶入，不進 repo）。
- **風險**：①Worker 免費方案每天 10 萬次請求、DO 每天 10 萬列寫入（中高：Cloudflare 官方文件摘要）——每次打開事件寫 2 列，訪客量 3 萬次/天以內沒問題，超過要升級付費方案（每月 5 美元起，未查證最新價）；②會員 Worker 掛了 → 今日事件訪客一律看不到（這是「不全開」的代價，要接受）；③誤擋共用 IP（見 1-C）。
- **擋得住**：#1、#2、#3（同網路）、#5、#6、#7（前提是一起改掉「連不到就全開」）。
- **擋不住**：#4 直接抓 JSON、#9 看 repo、#10 預覽版、#14 爬蟲、換網路或 VPN 的 #1。

### 階段 2：把內容搬到後端受控端點

#### 2-A 精選文章（**建議最先做，而且可以跳過階段 1**）

精選文章的規則是「Pro 全文、Plus 5 篇、其他只看標題」——**訪客與免費會員根本拿不到全文**，所以只要全文不在公開檔裡，就不需要任何訪客計數；Plus 的 5 篇是登入會員，**天生就能用 uid 在伺服器端計數**。這是整份文件裡 CP 值最高的一件。

做法：

1. **全文存哪**：存在會員 Worker 的 Durable Object（SQLite）新表 `articles_body (id, json, updated)`。理由：4 篇共 77KB，再多 500 篇也只有約 10MB，遠低於 5GB；**不需要 Andy 開 R2**（data-gw 卡在這一步）；會員 Worker 推 main 就自動部署。Workers KV 也可以，但要多綁一個命名空間、寫入是最終一致；R2 留給 data-gw 的大檔。
2. **新端點**：
   - `POST /v1/articles/get {id, t}` → 驗權杖 → 查方案的 `art.read.n` →（Pro／管理者）直接回；（Plus）查 `article_reads (uid, id)`，讀過的直接回、沒讀過且未滿 5 篇就記一筆再回、滿了回 `{error:'quota', used, limit}`；（訪客／免費）回 403。**扣額度在伺服器端**。
   - `POST /v1/articles/reads {t}` → 這個人讀過哪幾篇（畫面上的「已解鎖」勾勾）。
   - `POST /internal/articles/put {id, json}`（帶 `X-Internal-Key`，只給發佈流程用）。
3. **靜態站只留**：`index.json`（id、分類、標題、日期、標籤、族群）。**摘要與副標要不要留**：Andy 的規則寫「其他的只能看到標題」，而現在的畫面也寫「摘要與內文不會顯示」，但摘要其實在公開的 `index.json` 裡。建議：**摘要搬到後端（跟全文同權限）**，`index.json` 只留標題——這樣畫面講的話跟實際一致。若 Andy 想用摘要當試閱吸引升級，就保留在公開檔並把畫面那句話改掉。這一點我照 Andy 原話選了「只留標題」，他可以否決。
4. **怎麼從 public repo 移出、發佈流程怎麼改**（這是最大的改動）：
   現在的流程：Claude 寫好 → 推 `site/articles/posts/<id>.json` 到 main → Pages 部署。**全文在 commit 的那一刻就公開了**（含草稿）。
   改成：
   - 開一個 **private repo**（例如 `MiaoZiKe/tw-rotation-content`，GitHub 免費帳號可開私有庫）。全文 JSON、草稿、`topics.json`、`docs/articles/production_guide.md` 都放這裡。
   - 那個 private repo 裡放一支 workflow：推 main → 逐篇 `POST /internal/articles/put`（`INTERNAL_KEY` 存在**那個 repo 的** Secrets）→ 同時產出「只有標題」的 `index.json`，推回 public repo 的 `site/articles/index.json`（用一把只對 public repo 有寫入權的細粒度權杖）。
   - ⚠ **不要**用 public repo 的 workflow 來上傳全文：public repo 的 Actions 執行紀錄任何人都看得到，`workflow_dispatch` 的輸入值也會出現在紀錄裡。
   - Claude 要寫文章時，session 要有那個 private repo 的權限（`add_repo`）。授權跟著 session 走，每次要重驗（CLAUDE.md 開工第一件事那條）。
   - `article-jobs.yml`（排程佇列）可以留在 public repo：它只存「題目」，不存全文。但題目本身也是編輯方向，Andy 要的話一起搬。
5. **已經公開的 4 篇收不回來**：
   - 刪檔只會讓「最新版本」不見，**git 歷史裡永遠有**（9 個 commit）。改寫歷史（force push）違反 CLAUDE.md「絕不 force push」，而且 clone 過的人手上照樣有，GitHub 的快取與 fork 網路也可能保留——**不建議**。
   - 務實做法：這 4 篇**當作免費試閱文**（反正已經是了），在畫面上對所有人開放全文，當成導流；從第 5 篇起走新流程。這樣也不會出現「畫面說要 Pro、網址卻拿得到」的不一致。
   - Andy 若堅持要把 4 篇也收進付費：改寫成新版本（內容實質不同）再上架，舊版留在歷史裡當作「舊稿」。
6. **預覽版**：預覽版沒有全文（全文不在靜態檔裡了），要看全文就要用管理者帳號登入預覽版（預覽版擋的是「雲端寫入」，讀取可以——**這一點我沒有實測，要在做的時候確認**）。

| 項目 | 檔案 | 工作量 |
|---|---|---|
| Worker：全文表、`/v1/articles/get`、`/reads`、`/internal/articles/put`、伺服器端 Plus 計數 | `workers/account-api/articles.js`（擴充既有那支） | 0.75 天 |
| 測試（Pro 不限、Plus 第 6 篇被拒、重讀不扣、訪客／免費 403、偽造權杖 403、內部鑰匙錯 403） | `workers/account-api/tests/articles.test.mjs`（擴充） | 0.5 天 |
| 前端：單篇頁改向 Worker 拿全文；列表的「已解鎖／剩幾篇」改讀伺服器；拿不到就顯示鎖卡（不全開） | `site/articles.js` | 0.5 天 |
| private repo、發佈 workflow、標題版 `index.json` 回寫 public repo、權杖設定說明 | 新 repo 的 `.github/workflows/publish.yml`；public repo `docs/articles/production_guide.md` 改成指向新位置 | 0.75～1 天（含 Andy 按的步驟：開 repo、建一把細粒度權杖、設兩個 Secret，約 15 分鐘） |
| 把 4 篇改成「免費試閱」、`index.json` 拿掉摘要 | `site/articles/index.json`、`site/articles.js` | 0.25 天 |
| **合計** | | **2.75～3 天** |

- **新增端點**：`/v1/articles/get`、`/v1/articles/reads`、`/internal/articles/put`。
- **風險**：①發佈流程變複雜（兩個 repo），出錯時文章「標題上架、全文沒上」→ 發佈 workflow 要先 put 全文、成功後才回寫標題；②Claude 沒有 private repo 權限時寫不了文章 → 開工先驗；③會員 Worker 掛了時沒人讀得到全文（含 Pro）→ 接受，或之後加快取。
- **擋得住**：#2、#3、#4、#5、#6、#7、#9（新文章）、#10、#14（需要權杖＋速率限制）。
- **擋不住**：#12 帳號分享、#13 付費者轉貼、#15 已存檔的舊 4 篇。

#### 2-B 今日事件完整內容

先說清楚今日事件賣的是什麼：每一則是**別家媒體的新聞標題＋原文連結**、券商目標價摘要、公司重大訊息。單則的內容在原網站本來就公開，**我們的價值是「整理好、分好類、放在一起」**。這決定了保護的上限：

1. **`news.json`／`broker_views.json` 搬到 data-gw**：`workers/data-gw/tiers.js` 已經把 `news` 列成付費候選（`stock.news`）、`broker_views`（`stock.ai`）；`news_head`（前 30 則）是免費檔。只要 data-gw 上線並開 `DATAGW_SPLIT=1`，這兩支就會離開公開目錄。**可以重用，不用重寫**。要補的是：data-gw 現在對訪客只做「每 IP 每分鐘 120 次」限流，沒有「訪客累計 5 次」→ 要把階段 1 的 `/v1/total/use` 判斷接進 data-gw（它本來就用 service binding 呼叫會員 Worker）。估 0.5～0.75 天（不含 data-gw 上線本身）。
2. **data-gw 上線本身**：`datagw_plan.md` 第 10 節的 ★ 步驟要 Andy 按（開 R2、權杖、Secret、變數），工程面已完成；上線後前端改走 gateway 的部分也已寫好。剩下的是 Andy 的操作與觀察期，**我不估工程天數，但這是今日事件真正擋住的前提**。
3. **⚠ 原始資料在 public repo**：`data/news/`、`data/broker_views/`、`data/material_news/` 每天 commit 進 public repo。只要它們還在，懂的人下載 parquet 就有完整清單。要搬走等於改資料湖架構（`daily.yml` 寫入、`store.append()`、`build_payload` 讀取都要改成讀私有儲存），**估 3～5 天，而且會動到 CLAUDE.md「雲端是資料的權威來源」那條**——這不是我能自己拍板的，要排進 data-gw 第二階段一起決定。**我的判斷：以今日事件「整理別人公開標題」的性質，這一層值得做的程度低於文章**；先做 1、2，把 parquet 留著並寫進已知限制。

### 階段 3（可選）：浮水印、行為偵測、速率限制

| 項目 | 作法 | 現有可重用 | 工作量 | 擋什麼 |
|---|---|---|---|---|
| 文章浮水印 | `/v1/articles/get` 回傳時，在內文隨機幾段的字元間插入依 uid 計算的零寬字元或固定的同形字替換；管理區貼一段外流文字 → 反查是誰 | data-gw 的 `_wm` HMAC 與 `#admin/gw` 反查頁（概念相同，要改成文字版） | 1～1.5 天 | #13 的**追查**（不是阻止）；轉貼成截圖就失效 |
| 畫面浮水印 | 文章卡上淡淡的帳號雜湊（現在 `f55e726c` 已有「浮水印只鋪在單篇文章卡裡」，要改成依帳號產生） | 現有樣式 | 0.25 天 | 截圖外流的追查 |
| 同時裝置數 | 同一帳號 30 天內最多 2 台裝置讀全文 | data-gw 的 `devices` 表與 `MAX_DEVICES` | 0.5 天 | #12 帳號分享 |
| 速率限制與異常 | 同一帳號 1 分鐘讀超過 N 篇、同一權杖出現多個 IP 網段 → 記錄＋通知，**不自動停權**（門檻等 Andy） | data-gw 的 `burst`／`multi_ip` 規則與通知 | 0.5 天 | #14 爬蟲、大量下載 |
| 條款 | 使用條款加「付費內容不得轉載、重製、公開傳輸」 | `docs/compliance_and_tiers.md` 3-2 已有條款草稿 | 0.1 天 | #13 的**法律**依據（技術永遠擋不住，只有條款擋得住） |

- **風險**：零寬字元會在使用者複製到某些編輯器時出現怪字；同形字替換會影響搜尋。浮水印的 uid 雜湊屬個資處理，政策要寫（`security_review_1006.md` 2-5 的草稿已涵蓋「付費資料內可能嵌入與您帳號對應的識別標記」，沿用）。
- **擋不住**：截圖再打字、口述轉貼。

---

## 三、建議的優先順序與「最小有效版本」

### 3-1 最小有效版本（不大改架構，約 2.5～3.5 天）

依「每花一天能擋掉多少白嫖」排序：

| 順序 | 做什麼 | 為什麼先做 | 工作量 |
|---|---|---|---|
| ① | **2-A 精選文章全文搬到會員 Worker**（含 Plus 5 篇伺服器端計數、`index.json` 只留標題、4 篇舊文改免費試閱、private repo 發佈流程） | 文章是**我們自己寫的原創內容**，是最值錢、最容易被整篇轉走的；做完就**真的**擋住了 #4、#9、#10，而且**訪客不需要任何計數**。不用等 Andy 開 R2 | 2.75～3 天 |
| ② | **今日事件訪客 5 次改伺服器端計數**（階段 1，只套在 `events.total`） | 擋住「開無痕重來」這種一般人會做的事；`news.json` 仍公開，但那要等 data-gw | 1.5～2 天（端點與測試跟 ① 共用部分程式，合併做會比 1-E 的 2.25～2.75 天少） |
| ③ | **把「連不到就全開」改成「連不到就照訪客／照 0」**——只限 `art.read.n` 與 `events.total` 這兩個累計額度（不動全站其他功能的「寧可多給」慣例） | 這是兩個**一鍵全開**的洞（#6、#7），修法只有幾行；不修的話 ①② 做完畫面上還是可以全開（文章因為全文不在前端了不受影響，但今日事件會） | 0.25 天（含在 ② 裡） |

**如果只能做一件：做 ①。** 今日事件的內容本質是別人的公開標題，文章才是我們的東西。

### 3-2 之後

- data-gw 上線（等 Andy 按 ★ 步驟）→ 2-B 第 1 點把 `news.json` 接上訪客累計。
- 開始收費之後才做階段 3（浮水印、裝置數、異常）。
- 資料湖搬離 public repo（2-B 第 3 點）要跟 data-gw 第二階段一起由 Andy 決定。

### 3-3 不建議做的

- **瀏覽器指紋**：個資風險高、可靠度低、與「不追蹤」定位衝突。
- **改寫 git 歷史把 4 篇刪掉**：違反「絕不 force push」，而且收不回已經 clone／存檔的。
- **把付費內容「加密後」放在公開檔、前端解密**：金鑰一定要給前端，等於沒加密（看得懂 F12 就拿得到）。

---

## 四、你沒問到但我撞到的

1. **兩個「一鍵全開」**（上面 #6、#7）：`site/quota.js` 的 `pick()` 在會員伺服器連不到（`src === 'default'`）時回「不限」；`site/articles.js` 的 `access()` 在 `TwQuota` 不存在時回 `full`、`permReady()` 等 4 秒就放行；`site/app.js` 的 `evTotalT()` 拿不到 `TwQuota` 就不擋。這是「寧可多給，不要誤鎖」的全站慣例，但用在「累計額度」上就是**讓想白嫖的人自己決定要不要被擋**。任何人用瀏覽器內建的「封鎖要求網址」就能觸發。
2. **文章在上架前就公開了**：public repo 裡有「精選文章（製作中）」的 commit，草稿在 Andy 審稿之前任何人都讀得到。
3. **畫面說的跟公開檔不一致**：鎖卡寫「摘要與內文不會顯示」，但摘要在公開的 `index.json`。這不是安全漏洞，但對外的說法不實，建議 2-A 一起修。
4. **Plus 會員的 5 篇也是存在本機**：清資料或換裝置就又有 5 篇——付費會員一樣能白嫖「更高的方案」。這個只有伺服器端計數擋得住（2-A 已涵蓋）。
5. **兩個預覽分支都改了同一段 `site/quota.js`**（兩邊各自新增一份內容相同的 `TwQuota.total`），合併時第二個進 main 的會撞到。內容相同所以好解，但要記得只留一份。
6. **今日事件的原始新聞每天進 public repo**（`data/news/` 1.1MB），所以「今日事件 5 次」不管前端或後端計數，都擋不住會讀 parquet 的人。這一點應該寫進對 Andy 的已知限制，不要讓他以為做完階段 1 就擋住了。
7. **public repo 的 Actions 執行紀錄是公開的**：以後任何「把付費內容上傳到後端」的步驟，都不能放在 public repo 的 workflow 裡，也不能用 `workflow_dispatch` 的輸入值傳內容。
8. **免費方案額度**：會員 Worker 現在同時扛登入、自選、統計、點閱、額度；再加上每次打開今日事件 1 次請求、2 列寫入，量大時可能先頂到 Durable Object 免費方案每天 10 萬列寫入（中高：Cloudflare 官方文件摘要；我沒有查到目前實際用量，那要 Andy 在 Cloudflare 後台看）。
9. **隱私權政策目前寫「不使用 Cookie 進行追蹤」**：如果照原構想用 Cookie 存訪客編號，這句要改；用 localStorage 存也要在政策裡寫出來（1-D 已附草稿）。

---

## 五、出處與信心度

| 內容 | 出處 | 信心 |
|---|---|---|
| 計數存在 localStorage、無痕／清資料會重算 | `site/quota.js`（preview/articles-tier、preview/today-events-5）`TwQuota.total` 區塊與其註解 | 高（讀原始碼） |
| 連不到伺服器全開 | `site/quota.js` `pick()`、`site/articles.js` `access()`／`permReady()`、`site/app.js` `evTotalT()` | 高（讀原始碼；**沒有在瀏覽器實測**） |
| 文章與新聞是公開檔、在 repo 裡 | `git ls-tree origin/main`：`site/articles/posts/*.json`、`data/news/year=2026/part.parquet` 等 | 高 |
| data-gw 已寫好、未上線、`news` 列為付費候選 | `workers/data-gw/tiers.js`、`.github/workflows/deploy-data-gw.yml`、`HANDOFF.md` 第 394 行、`docs/confirm_ledger.md` 第 449 行 | 高 |
| IP HMAC 2 天的現行政策文字 | `site/legal.js` 第 215 行；`workers/account-api/worker.js` 體驗額度區塊 | 高 |
| IP 屬個資（歐盟 C-582/14） | WebSearch 摘要：[IAPP](https://iapp.org/news/a/cjeu-calls-ip-addresses-personally-identifiable-information-in-some-cases/)、[Osborne Clarke](https://marketinglaw.osborneclarke.com/data-and-privacy/european-court-rules-website-app-operators-must-treat-dynamic-ip-addresses-personal-data/)、[Proskauer](https://privacylaw.proskauer.com/2016/11/articles/data-privacy-laws/eu-court-rules-that-dynamic-ip-addresses-are-personal-datasometimes/) | 中高（多個獨立來源，只讀摘要） |
| 國發會 2020 年函釋認定 IP 屬個資 | 只有 [iThome 鐵人賽文章](https://ithelp.ithome.com.tw/articles/10290859) 摘要提及；查了兩組關鍵字**找不到函釋字號與原文** | **未確認** |
| Chrome 2025-04 維持第三方 Cookie | WebSearch 摘要：[Stape](https://stape.io/news/google-chrome-cookie-deprecation) 等產業部落格 | 中高（二手但多個一致） |
| Safari／Firefox／Brave 預設擋第三方 Cookie | 同上，僅一個二手來源順帶提及；沒有讀到 WebKit 官方文件 | 中 |
| Workers 免費每天 10 萬次請求；DO 免費每天 10 萬列寫入、5GB；R2 免費 10GB-月 | WebSearch 摘要：[Workers 價格](https://developers.cloudflare.com/workers/platform/pricing/)、[DO 價格](https://developers.cloudflare.com/durable-objects/platform/pricing)、[R2 價格](https://developers.cloudflare.com:2053/r2/pricing) | 中高（官方文件摘要；數字可能調整，動工前再看一次） |
| 工作量估計 | 依本 repo 既有同類工作（`articles.js` 點閱模組、`grant_ip`、data-gw 三階段各約 1 天）類推 | 中（區間估計；最大不確定在 private repo 發佈流程第一次設定） |
