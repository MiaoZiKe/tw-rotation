# 資安檢查與付費內容保護方案（2026-10-06，security-privacy）

> 對應 Andy 10-06 18:30 三句話：①「F12 會有我下過的 Prompt」②「技術夠厲害還是能解鎖我的內容，怎麼避免、怎麼發現、有沒有即時機制」③「其他資安相關問題幫我想想」。
> 第 ① 件的程式改動在分支 `claude/sec-minify`（部署時壓縮＋拿掉註解），這份文件只寫第 ②③ 件與 repo 可見性的選項。

---

## 給 Andy 的白話摘要

1. **F12 那件已經修了（待 CEO 驗收後上線）**：發佈出去的程式會先壓縮、把註解全部拿掉；交付清單那份「你的原話」資料也不再發佈。repo 裡的原始碼照舊有註解。
2. **但真正的外洩不是 F12，是 GitHub 本身**：repo 是 public，`CLAUDE.md`、`DECISIONS.md`、`HANDOFF.md`、`docs/`、程式註解 —— 你所有的原話與整個建站過程，任何人到 github.com/MiaoZiKe/tw-rotation 都看得到，而且**git 歷史永遠留著**。F12 修好只是把小門關上，大門還開著。
3. **付費內容現在「擋不住」**：所有資料都是公開的 JSON 檔，權限只是在畫面上藏起來。懂技術的人直接打開 `…/data/xxx.json` 就拿得到，**而且你完全不會知道**（GitHub Pages 不給你任何存取紀錄）。
4. **要真的擋，只有一條路**：付費資料不再放在公開網站，改成「登入 → 會員 Worker 驗你的方案 → 才回資料」。有了這一層，才做得到「發現（紀錄）」與「即時阻擋（限流、停權）」。估 4～6 個工作天，Cloudflare 費用每月約 5 美元起。
5. **其他風險**：最急的是「管理者 Google 帳號要開兩步驟驗證」與「第三方 GitHub Action 改用固定版本雜湊」，都是 10 分鐘的事。

### 要 Andy 決定的事（依急迫度）

| # | 決定什麼 | 選項 | 我的建議 | 誰按 |
|---|---|---|---|---|
| D1 | repo 要不要藏起來 | (a) 改 private ＋ 付費 GitHub Pro　(b) 改 private ＋ 網站搬 Cloudflare Pages　(c) 拆兩個 repo | **(b)**：反正收費前就得搬（GitHub Pages 條款禁止商業用途，見 `docs/hosting_cost_plan.md`），一次做完 | 改可見性、加 Cloudflare 授權要你在 GitHub／Cloudflare 按 |
| D2 | 舊歷史要不要清 | 改 private 就夠／另外把公開過的內容當成「已經外流」 | 改 private 就夠；**已經被 fork 或爬走的收不回來**，不必花力氣重寫歷史 | — |
| D3 | 付費資料改走 Worker | 現在做／收費前再做 | **收費前一定要做**；在那之前先不要把真正值錢的東西放進公開 JSON | CEO 排程 |
| D4 | 管理者帳號 | 開兩步驟驗證（2FA）；客服信箱與管理者帳號分開 | 兩個都做 | 你在 Google 帳號設定按 |
| D5 | 異常通知要寄到哪 | email／手機推播（ntfy、Telegram） | email 先做（最簡單） | 給一個收件信箱 |

---

## 第 1 件補充：repo 可見性的三個選項（不動手，等 D1）

**現況證據**：`git ls-files | wc -l` 數千檔、public；`CLAUDE.md` 開頭就是 Andy 的工作方式、原話、帳號名；`DECISIONS.md` 超過 6000 行，每條都有「Andy 原話」。這些在 F12 修好之後**仍然公開**。

### (a) repo 改 private，留在 GitHub Pages
- **代價**：private repo 要用 Pages 需要付費方案 —— 個人帳號是 **GitHub Pro，約每月 4 美元（年繳約 48 美元）**（以 GitHub 價目頁為準，github.com/pricing）。網站本身仍然公開，只有原始碼藏起來。
- **副作用**：
  - Actions 分鐘數變成有額度（Pro 每月 3,000 分鐘）。目前每日管線＋每小時回補＋部署，**很可能超過**，要先看一個月的用量（Settings → Billing）。超過按分鐘計費。
  - **仍然不能商業使用**（GitHub Pages 條款），收費前還是要搬。
- **步驟**：① Andy：Settings → Billing 升級 Pro ② Andy：repo Settings → General → Danger Zone → Change visibility → Private ③ 檢查 Settings → Pages 仍是 GitHub Actions 來源 ④ 我們：跑一次 pages.yml 確認網站還在。

### (b) repo 改 private，網站改由 Cloudflare Pages 發佈（建議）
- **代價**：Cloudflare Pages 免費方案（不計流量、允許商業使用）；Actions 分鐘數同 (a) 的問題（private repo 免費帳號每月 2,000 分鐘，**大概率不夠** → 要嘛升 Pro、要嘛把每小時回補降頻）。
- **好處**：一次解決「原始碼公開」「條款禁商用」「之後要接 Worker 做付費資料」三件事；Cloudflare 有存取紀錄與 WAF。
- **步驟**：
  1. Andy：Cloudflare 後台 → Workers & Pages → 建一個 Pages 專案（Direct Upload，名字例如 `tw-rotation`）。
  2. 我們：pages.yml 最後一步改成 `wrangler pages deploy site --project-name tw-rotation`（沿用既有 `CLOUDFLARE_API_TOKEN`，Andy 要確認該 token 有 Pages 編輯權限，沒有就在 Cloudflare 重發一張）。
  3. 兩邊並行跑一週（GitHub Pages 與 Cloudflare Pages 同時發佈），確認一樣。
  4. 會員 Worker 的 `ALLOWED_ORIGINS` 加上新網域；Google OAuth 用戶端的「已授權的 JavaScript 來源」加新網域（Andy 在 Google Cloud Console 按）。
  5. Andy：repo 改 private（同 (a) ②）。GitHub Pages 會自動停（或手動關），舊網址可放一頁「已搬家」。
  - 工作量：我們這邊約 0.5～1 天。

### (c) 拆兩個 repo：私有開發 repo ＋ 公開發佈 repo
- **代價**：不用付費；但多一個 repo、多一把跨 repo 推送的權杖（一個新的高價值金鑰），流程變複雜（資料湖 commit 在哪一邊？）。
- **步驟**：① Andy 新建 public repo `tw-rotation-site`（只放壓縮後的 site/）② 現有 repo 改 private ③ 私有 repo 的 pages.yml 產出後用 deploy key 推到公開 repo ④ 公開 repo 開 Pages。
- **不建議**：Actions 分鐘數問題跟 (a)(b) 一樣存在（開發 repo 私有），卻多了一把金鑰與一個同步點；而且仍是 GitHub Pages、仍不能商用。

### 三個選項都要知道的事
- **改 private 不會讓已經公開過的東西消失**：任何 fork、搜尋引擎快取、別人 clone 下來的都還在。把 repo 至今的內容當作「已公開」處理：**目前沒有在歷史裡找到金鑰**（見第 3 件 S1），所以沒有需要撤銷的東西。
- `preview/*` 分支預覽、`docs/preview.md` 的網址規則在 (b) 要跟著改。

---

## 第 2 件：付費內容保護

### 2-1 說清楚現況
- 網站是 GitHub Pages 靜態檔。`site/data/*.json`（約 900 MB、2,300 多檔個股頁）全部是**任何人都能直接下載的網址**，不需要登入。
- `site/perm.js`／`site/features.js` 只決定「畫面要不要上鎖頭」；`site/livegate.js`（DECISIONS #326）只藏即時畫面。`workers/account-api/worker.js` 檔頭 R7 自己也寫了「這只決定前端要不要上鎖頭」。
- 即時報價代理 `tw-quote`（workers/quote-proxy）與 `tw-taifex`（deno）只檢查 Origin —— Origin 是瀏覽器以外的程式可以隨便填的。
- **偵測能力＝零**：GitHub Pages 不提供存取紀錄；就算有人把整站 JSON 抓走，你不會知道。
- 結論：**現在任何「付費限定」都只是 UX，不是保護。** 在 2-2 做完之前，不要把「真正值錢、外流會有損失」的東西放進 site/data。

### 2-2 根本解法：付費資料改由 Worker 發放

```
瀏覽器 ──(1) Google 登入──▶ account-api（已存在）──▶ 長效登入權杖（60 天，存 localStorage）
   │
   ├─(2) POST /v1/data/token  帶登入權杖 + 裝置 id
   │        account-api 查 perm（方案、到期日）→ 簽一張 5 分鐘的資料權杖（含 uid、方案、裝置 id 雜湊）
   │
   └─(3) GET  data-gw/<路徑>   帶資料權杖
            data-gw Worker：驗簽章 → 查方案能不能看這個路徑 → 限流 → 記錄 → 從 R2 讀檔回傳
            （公開資料照舊放 Pages；只有付費路徑走這裡）
```

| 要改的地方 | 內容 | 工作量 |
|---|---|---|
| `pipeline/build_payload.py` ＋ `pages.yml` | 把資料分成「公開」與「付費」兩包；付費那包不進 `site/`，改用 `wrangler r2 object put`（或 rclone）上傳到 R2 私有 bucket | 1 天 |
| 新 Worker `workers/data-gw/` | 驗權杖、路徑→方案對照、限流、記錄、讀 R2；`wrangler.toml` 綁 R2 與一個 Durable Object（計數用） | 1.5 天 |
| `workers/account-api/worker.js` | 新增 `/v1/data/token`（短效、綁裝置）；共用簽章金鑰或改用非對稱簽章（Ed25519，data-gw 只拿公鑰） | 0.5 天 |
| 前端 `site/app.js` 的 `load()` | 付費路徑改打 data-gw、帶權杖、過期自動換；拿不到時顯示升級提示（沿用 perm 的鎖頭） | 1 天 |
| 測試 | Worker 的允許／拒絕測試（沿用 account.test.mjs 的寫法）、`_uitest` 加「沒權限拿不到、有權限拿得到」 | 1 天 |
| **合計** | | **約 4～6 個工作天** |

**Cloudflare 費用影響**（價格見 `docs/hosting_cost_plan.md` §一）：
- R2：免費額度每月 10 GB 儲存、1,000 萬次讀取（Class B）；付費資料若只是一部分（例如個股頁進階欄位），應在免費額度內。**出流量不收費**。
- Workers：付費資料每次讀檔多一次 Worker 請求。1 千會員、每人每天 50 次 ≈ 每月 150 萬次，在 5 美元方案的 1,000 萬次內。
- 結論：**在既有的 5 美元月費裡**，除非會員破萬。

### 2-3 偵測（要有 2-2 才做得到）

| 偵測什麼 | 怎麼做 | 為什麼 |
|---|---|---|
| 短時間大量抓 | data-gw 對每個 uid 記「每分鐘／每小時請求數」與「不重複路徑數」，超過門檻（例如 1 小時看了 300 檔個股頁；正常人一天看不到 50 檔）就標記 | 爬蟲的形態是「廣」，真人是「深」 |
| 同一權杖多個 IP | 記 uid → 最近 24 小時的 IP 網段（/24）集合；超過 3 個網段或跨國 | 帳號分享、權杖被偷 |
| 非瀏覽器 | `User-Agent` 不是瀏覽器、沒有 `Sec-Fetch-*` 標頭、Cloudflare `cf.botManagement`（付費）或 `cf.clientTcpRtt` 異常 | 腳本 |
| 浮水印 | 付費 JSON 回傳前，在數值的「不影響閱讀的位數」或欄位順序嵌入 uid 雜湊（例如價格第 4 位小數）；另在畫面上加極淡的帳號浮水印（防截圖） | **外流之後查得出是誰流的**；這是唯一能「事後發現」的方法 |
| 通知 | 標記時寫一筆 `alerts` 表，並用 MailChannels／Resend（免費額度）寄信給 Andy，或打 ntfy.sh／Telegram Bot 推手機 | 「即時知道」 |

⚠ **隱私**：記 IP 網段與 UA ＝ 蒐集新的個資，隱私權政策要同步改（下面 2-5 有草稿），保存期限要短（建議 30 天）。

### 2-4 即時阻擋

| 機制 | 做法 | 現在就能做？ |
|---|---|---|
| 每帳號限流 | data-gw 用 DO 計數，每分鐘 60 次、每小時 600 次，超過回 429 | 要等 2-2 |
| 短效權杖＋綁裝置 | 資料權杖 5 分鐘；首次登入產生裝置 id（存 localStorage），權杖裡放它的雜湊，不符就拒絕；每帳號最多 2 台裝置 | 要等 2-2 |
| 異常自動停權 | 觸發門檻 → `perm` 表該 email 加 `suspended` 旗標，**同時遞增使用者的 `tv`（權杖版本）讓所有舊權杖立刻失效**，寄信通知 Andy；Andy 在 #admin 一鍵解除 | 要等 2-2（`tv` 機制已存在） |
| Cloudflare WAF／Bot | 免費方案可用：Bot Fight Mode、自訂 WAF 規則 5 條（例如擋沒有 UA 的請求、擋特定國家）、Rate Limiting 規則 1 條 | **網站搬到 Cloudflare（D1-b）之後才有用**；Workers 本身可先開 |
| 即時報價代理加權杖 | DECISIONS #326 已寫：`/quote` 等端點要求帶會員權杖、驗 admin 才回 | **現在就能做**（0.5～1 天） |

### 2-5 現在就能做（小、低風險） vs 搬家之後再做

**現在就能做**
1. ✅（本批已做）發佈檔壓縮、拿掉註解、不發佈交付清單原話與 source map。
2. 報價代理 `tw-quote`／`tw-taifex` 要求會員權杖（DECISIONS #326 的後續），0.5～1 天。
3. account-api 加「異常寄信」：同一 IP 每分鐘被 `rateOk` 擋掉、或 `/v1/admin/*` 回 403 時，記一筆並寄信給 Andy（有人在試管理者端點）。0.5 天。
4. 第 3 件清單裡標「現在」的項目。

**要等搬到可商用平台（D1-b）、而且要開始收費之前做**
- 2-2 整套（資料走 Worker）、2-3 偵測、2-4 限流與停權、WAF。

**隱私權政策要加的段落（做 2-3 時貼上，草稿）**

> **安全紀錄**：為了防止付費內容被大量下載或帳號被盜用，會員存取付費資料時，我們會記錄：帳號識別碼、存取時間、存取的資料項目、連線 IP 位址的前三段（例如 203.0.113.x）與瀏覽器類型。這些紀錄只用於偵測異常存取與處理爭議，不用於行銷，不提供給第三方（法令要求除外），保存 30 天後自動刪除。付費資料內可能嵌入與您帳號對應的識別標記，用於追查未經授權的轉載。

---

## 第 3 件：全面資安檢查

嚴重度：**高**＝現在就可能被利用且損失大；**中**＝有條件才發生或損失中等；**低**＝改善項。
分類：【現在】＝現在就會被打的；【收費後】＝開始收費、有帳號價值後才會被打的。

| # | 項目 | 檢查結果（證據） | 嚴重度 | 攻擊情境 → 影響 → 緩解 → 成本 |
|---|---|---|---|---|
| S1 | 金鑰外洩 | `git grep` 掃工作區：GitHub 權杖、Google API key、私鑰、JWT、OAuth client secret 樣式 **0 筆**；git 全歷史以同一組樣式掃描（見回報）。金鑰都在 GitHub Secrets（`FINMIND_TOKEN`、`FRED_API_KEY`、`CLOUDFLARE_API_TOKEN`、`GOOGLE_CLIENT_SECRET` 等）。 | 低（目前乾淨） | 【現在】有人 push 時誤把權杖寫進檔案 → public repo 幾分鐘內就被機器人掃走 → 開 GitHub「Secret scanning ＋ Push protection」（Settings → Code security，public repo 免費，**Andy 按**）→ 2 分鐘 |
| S2 | 原始碼與決策全公開 | 見第 1 件補充 | **高** | 【現在】競爭者或任何人讀 DECISIONS／HANDOFF 得到整套方法、資料源、權限設計弱點（例如 #326 自己寫了怎麼繞過）→ 商業機密外流、攻擊者拿到地圖 → D1 → 見 (a)(b)(c) |
| S3 | 付費內容只藏畫面 | 見第 2 件 | **高**【收費後】 | 付費會員把 JSON 網址分享出去或寫爬蟲 → 付費價值歸零、你不會知道 → 2-2 → 4～6 天 |
| S4 | 即時報價代理只看 Origin | `workers/quote-proxy`、`workers/taifex-deno`；DECISIONS #326 已記 | 中【現在】 | 任何人用腳本帶假 Origin 打代理 → 吃掉 Workers 每天 10 萬次免費額度（Andy 自己的即時也一起掛）、轉散布即時資料的法遵風險（`docs/legal/realtime_redistribution.md`）→ 要求會員權杖＋限流 → 0.5～1 天 |
| S5 | 管理者判斷 | `worker.js` `isAdmin()` 用 Worker Secret `ADMIN_EMAILS`，所有 `/v1/admin/*` 都在伺服器端先 `admin()` 檢查；R1～R7 有 19 條允許／拒絕測試。前端 `livegate.js` 只決定畫面。 | 低（伺服器端正確） | — 維持 |
| S6 | CORS／Origin | `ALLOWED_ORIGINS` 白名單、反射前比對、POST 檢查 Origin、OAuth 回跳網址也比對白名單 | 低 | 搬家（D1-b）時記得加新網域，**不要改成 `*`** |
| S7 | 登入權杖存在 localStorage、效期 60 天、滑動續期 | `TOKEN_DAYS = 60`；`tw.acct.tok` | 中【收費後】 | 一旦網站有任何一個 XSS，攻擊者讀走 localStorage 權杖 → 60 天內冒用該會員（若是管理者就能改所有人權限）→ ① 管理者權杖縮短到 1～7 天 ② 加「登出所有裝置」＝遞增 `tv`（機制已存在，只缺按鈕）③ 2-4 的綁裝置 → 0.5 天 |
| S8 | XSS（innerHTML 放外部字串） | 抽查：新聞、公告（`notices.js` 的 `esc()`＋只轉 http(s) 連結）、會員名字（`account.js`／`admin.js`）、族群／個股名多數經 `fmt.esc`。**仍有未跳脫的插入**：`app.js` 的 `${o.title}`、`${x.name}`，`industry.js` 圖表提示 `${c.name}`、`${p.name}` 等 —— 來源是自己的 YAML 與 FinMind 的公司名，目前不是使用者輸入。**這次只是抽查，不是全掃。** | 中【現在】 | FinMind 或新聞來源被汙染（或日後把使用者輸入接進這些欄位）→ 在訪客瀏覽器執行程式、偷 S7 的權杖 → ① 加 CSP（S9）擋住大部分 ② 用 eslint 規則掃「模板字串進 innerHTML 沒有 esc」一次清 → 1 天 |
| S9 | CSP 標頭 | `index.html` 沒有 `Content-Security-Policy`；GitHub Pages 不能自訂標頭，只能用 `<meta http-equiv>` | 中【現在】 | XSS 發生時沒有第二道防線 → 加 `<meta http-equiv="Content-Security-Policy">`：`script-src 'self'`（要先把 index.html 的 5 段內嵌 script 搬成檔案或加 hash）、`connect-src 'self' https://*.workers.dev https://*.deno.net https://mis.twse.com.tw`、`img-src 'self' data: https://*.googleusercontent.com`、`frame-ancestors` 只能用標頭（搬 Cloudflare 後用 `_headers` 檔）→ 0.5～1 天＋全站驗收 |
| S10 | 第三方腳本 | 全部在 `site/vendor/`（ECharts、Lightweight Charts、three.js、lucide），**不走 CDN**；沒有 Google Analytics 之類追蹤碼。對外連線只有自家 Worker、mis.twse、Google 登入與大頭貼。 | 低 | 維持；vendor 升版時記下版本與來源雜湊 |
| S11 | 管理者 email 出現在前端 | 客服信箱 `support.js`、`legal.js`、`account.js` 與 Worker 網址 `tw-quote.<帳號>.workers.dev` 用的都是 Andy 的個人 Gmail／帳號名；`ADMIN_EMAILS` 本身沒進 repo。 | 中【現在】 | 公開信箱＝管理者帳號 → 攻擊者知道要釣誰、要猜誰的密碼 → ① 客服改用獨立信箱（Gmail 別名或新帳號）② 管理者帳號開 2FA（S14）→ 30 分鐘（Andy 建信箱） |
| S12 | 測試裡的真實 email | 測試與驗收腳本用的是假網域（抽查 `tests/`、`workers/account-api/tests`）；真實 email 只在 S11 那幾處與 `scripts/probe_sources.py` 的 Worker 網址 | 低 | 維持 |
| S13 | Google 登入設定 | 授權碼＋PKCE（S256）＋state＋nonce＋綁瀏覽器 cookie；id_token 由 Worker 直接跟 Google 換（DECISIONS #270）。Google Cloud Console 的「已授權重新導向 URI」應只有 Worker 的 `/auth/callback` | 低 | Andy 確認 OAuth 同意畫面在「正式版」、重新導向 URI 沒有多餘網址；搬家時更新 |
| S14 | 管理者帳號被盜 | 管理者＝Google 帳號；被盜等於能改所有會員權限、看會員名單（個資） | **高**【現在】 | 釣魚或密碼重用 → 管理者權限全失、會員 email 外洩（要通報）→ **Google 帳號開兩步驟驗證（建議通行金鑰／實體金鑰），GitHub 帳號同樣開 2FA**、Cloudflare 帳號也開 → Andy 各 5 分鐘 |
| S15 | Durable Object 資料保存與個資 | 會員：名稱、email、大頭貼網址、Google 識別碼雜湊；24 個月未用自動刪；統計 13 個月；線上 3 分鐘；IP 只在記憶體做限流不落地。與 `legal.js` 隱私權政策、`account.js` 告知一致（三處同步規則 DECISIONS #270-7）。 | 低 | 做第 2 件的紀錄時要同步改三處＋貼 2-5 草稿 |
| S16 | GitHub Actions 權限 | 每支 workflow 都有頂層 `permissions:`；pages.yml 是 `contents: read`／`pages: write`／`id-token: write`，relay 工作另給 `actions: write` | 低 | 維持；寫資料的 daily／backfill 需要 `contents: write`，屬必要 |
| S17 | 第三方 action 版本 | 官方 `actions/*@v4` 等用版本標籤；**第三方 `cloudflare/wrangler-action@v3`、`denoland/setup-deno@v2` 也只用標籤**，而 wrangler-action 拿得到 `CLOUDFLARE_API_TOKEN` | 中【現在】 | 第三方 action 的標籤被移動到惡意版本（2025 年 tj-actions 事件就是這樣）→ 偷走 Cloudflare 權杖 → 改用完整 commit SHA 固定（`uses: cloudflare/wrangler-action@<40 碼 sha> # v3.x`）＋開 Dependabot 的 github-actions 更新 → 30 分鐘 |
| S18 | 依賴套件 | Python `requirements.txt`；前端無 npm 依賴（vendor 內建）；部署壓縮用的 esbuild **鎖定 0.28.2** | 低 | 開 Dependabot alerts（Andy 在 Settings → Code security 按）；`requirements.txt` 改成釘版本（`==`） |
| S19 | Cloudflare 權杖範圍 | `CLOUDFLARE_API_TOKEN` 被 3 支 workflow 共用（報價、會員、之後的 Pages） | 中 | 權杖外洩＝可改寫會員 Worker、讀 DO 會員資料 → 權杖只給「Workers Scripts 編輯＋該帳號」最小範圍，不要用 Global API Key；每年換一次 → Andy 在 Cloudflare 15 分鐘 |
| S20 | 隱私權政策與實際蒐集一致性 | 一致（見 S15）。缺：①Google 大頭貼從 googleusercontent 載入＝Google 會看到管理頁訪問 ②日後的安全紀錄（2-5） | 低 | 補一句「會員大頭貼由 Google 伺服器提供」 |
| S21 | 發佈內容裡的內部文字（本批處理） | 註解（已處理）；`delivery.json`＝Andy 原話（已不發佈）；**仍在畫面上的**：`supply_chain.yaml` 公司 `note` 會顯示在公司面板，裡面有「DECISIONS #201 的標準」「WebSearch 摘要」等內部用語；`site/tasks.js` 的標題「Andy 交代的每一件事」（頁面已無入口但路由還在）；`modules.js` 的 `note`（已在部署時剔除） | 低 | 【現在】看得到內部流程與 Andy 名字 → 文案清一輪（內容負責人改 YAML note，把「DECISIONS #」「WebSearch」換成讀者用語）；`#tasks` 路由移除 → 0.5 天 |

### 建議處理順序
1. **今天（Andy 按）**：S14 兩步驟驗證（Google／GitHub／Cloudflare）、S1 開 Secret scanning＋Push protection、S18 Dependabot。
2. **本週（我們做）**：本批 F12 修正上線；S17 第三方 action 釘 SHA；S4 報價代理加權杖；S21 文案清理；S7 管理者權杖縮短＋「登出所有裝置」。
3. **D1 決定後**：搬 Cloudflare Pages＋repo 改 private；S9 CSP 用標頭。
4. **收費前**：第 2 件 2-2～2-4 整套；隱私權政策貼 2-5 草稿。
