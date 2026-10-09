# 上線前資安與營運缺口清單（2026-10-09，security-privacy）

> 對應 Andy 2026-10-09：「預計下禮拜要上線網路使用…你幫我確認是否有哪些我該做但沒注意到的」。
> 查證時間：2026-10-09 22:35（台北）。**每一條「現況」都附查證方式**（git、程式碼、GitHub API 查到的 Actions 紀錄）。
> 查不到的（GitHub 的 Secret／變數值、Cloudflare 與 Google 後台）一律標「⚠ 查不到，要 Andy 看一眼」，不推測。
> 前一份是 `docs/security_review_1006.md`（S1～S21）；第二節逐條對照它的現況。
> 這是資安與營運的風險盤點，不是法律意見；法律相關的那幾條寫明「請律師看」。

---

## 零、一句話結論

**照現在的設定下禮拜上線，有四件事一定會出問題：**

1. **付費內容還是任何人都下載得到。** 付費資料閘道（data-gw）的程式碼已經在 main，但**一次都沒有部署過**，正式站也還沒切過去。
2. **26 個預覽網址把所有鎖頭都打開了。** 預覽版一律比照擁有者，全部功能不鎖。這 26 份同時發佈在 github.io 和 pages.dev，任何人都看得到。
3. **任何人寫一支腳本，就能讓全站登入停擺到隔天早上 8 點。** Cloudflare 免費方案每天 10 萬次請求，是整個帳號共用的。報價代理只檢查 Origin，而 Origin 可以偽造；額度打滿之後，會員 Worker 也會一起回 1027 錯誤。
4. **會員資料從來沒有備份過。** 會員 Worker 最近一次部署時，「寫入 BACKUP_TOKEN」那一步是 skipped，代表筆電抓不到會員資料。

另外，壞掉的時候不會有人知道：唯一的監控（報價代理那條）最近 30 次裡有 12 次紅燈，沒有人去處理。

---

## 一、上線前必做 Top 10

標記：**【Andy】**＝只有 Andy 能按（帳號、付款、後台設定）；**【工程】**＝我們做；**【兩邊】**＝Andy 先按，我們接著做。

| # | 事情 | 誰 | 估時 | 對應條目 |
|---|---|---|---|---|
| 1 | Cloudflare 升級 Workers 付費方案（每月 5 美元），同時設預算警示 | 【Andy】 | 15 分 | G3 |
| 2 | 買自有網域，交給 Cloudflare 管；Cloudflare Pages 綁上這個網域；用 Email Routing 開 support@ 客服信箱 | 【兩邊】Andy 買＋按；工程改設定 | Andy 30 分＋工程 0.5 天 | G4、G9 |
| 3 | 切換付費資料閘道：建 R2、加權杖權限、設 4 個 Secret → 工程部署 data-gw → 開 DATAGW_SPLIT=1 | 【兩邊】 | Andy 30 分＋工程 1 天（含驗收） | G1 |
| 4 | 預覽網址不再對外全開：正式上線前刪掉不用的 preview 分支；工程改成預覽版不再比照擁有者，或只部署到 GitHub Pages | 【兩邊】 | 工程 0.5 天、Andy 10 分（在 GitHub 刪分支） | G2 |
| 5 | 報價代理改成要帶會員權杖，並且限流（S4，到現在還沒做） | 【工程】 | 0.5～1 天 | G3 |
| 6 | 會員資料備份接通，並且在測試用 Worker 上做一次還原演練 | 【兩邊】Andy 設 BACKUP_TOKEN、裝筆電；工程做演練 | Andy 20 分＋工程 0.5 天 | G6 |
| 7 | Google 登入：發布狀態確認是「正式版」；新網域加進「已授權來源」；支援信箱改成客服信箱；用新網域送品牌驗證 | 【Andy】（工程給逐步點擊） | 30 分＋等 Google 審核 2～3 個工作天 | G5 |
| 8 | 監控：外部探測主站、會員 Worker、data-gw，壞了寄信或推播給 Andy；處理 worker-watch 的紅燈 | 【兩邊】Andy 註冊監控服務 10 分；工程 0.5 天 | — | G10 |
| 9 | 隱私權政策與條款：換客服信箱、補齊實際用到的第三方、把 `enabled` 改成 true（現在是 false，頁面掛「草稿」） | 【工程】改，【Andy】說「可以開」 | 0.5 天 | G11 |
| 10 | 寫好事件應變小抄（停權、全員登出、換金鑰、關站、個資外洩通報），並先演練一次「全員登出」 | 【工程】寫，【Andy】讀一次 | 0.5 天 | G8 |

依賴順序：**1 → 2 → 7、9**（網域先有，OAuth 和政策裡的網址才填得進去）；**3 和 5 可以平行做**；4、6、8、10 跟其他項目都不相干，可以馬上開始。

---

## 二、10-06 清單現在做到哪（逐條查證）

| # | 10-06 的項目 | 現在的真實狀態 | 怎麼查到的 |
|---|---|---|---|
| D1／S2 | repo 要不要藏起來 | **還是 public**。拆 repo 只有草稿（分支 `claude/repo-split` fb3a5341，10-06 之後沒有新 commit），沒有執行 | `gh api repos/MiaoZiKe/tw-rotation` → `visibility: public`；`git ls-remote` |
| D3／S3 | 付費資料改走 Worker | 程式碼 10-07 已經進 main（`workers/data-gw/`、`site/datagw.js`、`pipeline/split_paid.py`），**但沒有部署、也沒有切換** | `deploy-data-gw.yml` 的 runs 是 **0 筆**；最新一次 pages.yml（run 37942314342）「付費資料分流到 R2」這一步是 **skipped**（也就是 `DATAGW_SPLIT` 不是 1） |
| D4／S14 | 三個帳號開兩步驟驗證 | ✅ Andy 10-07 回報完成 | `docs/confirm_ledger.md` 第 485 行 |
| D5 | 異常通知寄到哪 | 已決定寄到 Andy 的 Gmail；**但 data-gw 沒部署，所以實際上沒有任何通知在跑** | 同上 |
| S1 | Secret scanning＋Push protection | ⚠ 查不到（API 回的 `security_and_analysis` 是 null，權限不夠）。**要 Andy 看一眼** | — |
| S4 | 報價代理只看 Origin | **沒做**。`workers/quote-proxy/worker.js` 沒有任何權杖檢查，只有 `ALLOW_ORIGINS` | grep `Authorization\|Bearer` 0 筆 |
| S7 | 管理者權杖縮短、「登出所有裝置」 | **沒做**。`TOKEN_DAYS = 60`，沒有「登出所有裝置」的端點 | `worker.js:42`；grep `logout_all\|登出所有` 0 筆 |
| S9 | CSP | **沒做**。`index.html` 沒有 CSP，也沒有 `_headers` | grep 0 筆 |
| S11 | 客服信箱和管理者帳號分開 | **沒做**。`support.js`、`legal.js`、`legal_config.js`、`account.js` 用的都還是個人 Gmail（Andy 10-09 說「後面會更改」）；Worker 網址 `*.kcq01010909.workers.dev` 也露出帳號名 | grep |
| S17 | 第三方 action 釘 SHA | **沒做**。`cloudflare/wrangler-action@v3` 4 處、`denoland/setup-deno@v2` 1 處 | grep `uses:` |
| S18 | Dependabot、requirements 釘版本 | **沒做**。沒有 `.github/dependabot.yml`；`requirements.txt` 全是 `>=` | ls、head |
| S19 | Cloudflare 權杖最小範圍 | ⚠ 查不到。要 Andy 在 Cloudflare 後台看 | — |
| S21 | 內部用語出現在畫面 | 未逐條重查（不在這次範圍） | — |
| 搬家 | 雙部署到 Cloudflare Pages | 最新一次 pages.yml 的「雙部署」步驟是 success。⚠ 這一步缺 Secret 時也會以 success 收尾，**實際有沒有部署成功要看那次 run 的摘要**（我們的容器讀不到 log） | jobs API |
| 備份 | 會員資料匯出 | 端點已經上線，**但 BACKUP_TOKEN 沒設**，筆電抓不到 | 最新一次 deploy-account-worker（10-08 23:41 UTC）「寫入 BACKUP_TOKEN」這一步是 **skipped** |

---

## 三、缺口逐條

格式：**現況（證據）→ 風險（攻擊情境 → 影響）→ Andy 要做的（點哪裡）→ 工程要做的 → 優先序**。
優先序分三級：**上線前必做**／**一個月內**／**可延後**。

### G1 repo 公開與付費內容保護（data-gw 切換）

- **現況**：見第二節的 D1、D3。正式站 `site/data/*.json` 全部是公開網址；`perm.js`、`quota.js` 的鎖頭和次數只在前端。`legal.js` 的「安全紀錄」段落要 `TW_ACCOUNT.gw` 有值才會出現，而它現在沒有值。
- **風險**：
  - 付費會員（或任何人）打開 F12 →「網路」，就看得到 JSON 網址，寫爬蟲一次抓完。付費價值歸零，而且**沒有任何紀錄**。
  - repo 公開代表 `workers/data-gw/tiers.js` 裡寫的「哪些檔付費」、限流門檻也公開。這點可以接受，因為安全靠的是 Secret 和伺服器端檢查，不靠藏程式碼；但 `CLAUDE.md`、`DECISIONS.md` 裡 Andy 的原話和商業規劃仍然公開。
- **Andy 要做的**（`docs/confirm_ledger.md` 10-06 20:35 的切換清單）：
  1. Cloudflare 後台 → **R2** → Create bucket → 名稱 `tw-rotation-paid` → **不要**開 Public access。
  2. Cloudflare → 右上頭像 → **My Profile → API Tokens** → 編輯 GitHub 用的那把 → 加上 **Account → Workers R2 Storage → Edit** 和 **Account → Cloudflare Pages → Edit**。
  3. R2 → **Manage R2 API Tokens** → Create → Object Read & Write，範圍只限這個 bucket → 把兩把 key 存成 GitHub Secret（名稱照 `pages.yml` 第 135～158 行的 `R2_*`）。
  4. GitHub → repo → **Settings → Secrets and variables → Actions** → New repository secret：`DATA_GW_SECRET`、`DATAGW_INTERNAL_KEY`、`DATAGW_ALERT_EMAIL`（填收通知的信箱）、`RESEND_API_KEY`（要寄信才需要；到 resend.com 免費註冊）。值用密碼管理器產生 48 字以上的亂數。
  5. 部署成功後，Secret 再加 `DATA_GW_URL`，**Variables** 頁籤加 `DATAGW_SPLIT=1`。
- **工程要做的**：手動觸發 `deploy-data-gw.yml` → `/health` 回 `configured:true` → 設 `DATA_GW_URL` → 開 `DATAGW_SPLIT` → 跑 `_uitest` 的「沒權限拿不到、有權限拿得到」那幾段 → **在正式網址實測**：沒登入直接開一支付費 JSON 必須 404 或 401。
  ⚠ `workers/data-gw/wrangler.toml` 的 `ALLOWED_ORIGINS`、`ACCOUNT_ORIGIN` **只有 `https://miaozike.github.io`**，沒有 `tw-rotation.pages.dev`，也沒有新網域。不補的話，搬家之後付費內容全部打不開。會員 Worker 的 `ALLOWED_ORIGINS` 也要加新網域。
- **repo 要不要改 private**：不擋上線。data-gw 切換之後，公開的程式碼不會讓人拿到付費資料。改 private 的成本（Actions 分鐘數，實測約 1.2 萬分鐘／月，遠超過私人 repo 免費的 2,000 分鐘）仍然要等 Andy 選。
- **優先序**：**上線前必做**（只要有任何付費方案在賣）。如果下禮拜只開免費會員、不收費，可以延到收費前，但第 G2 條還是要做。

### G2 預覽網址把付費功能全開（新發現）

- **現況**：`scripts/preview_inject.py` 在 main 的每一次部署，把**所有 `preview/*` 分支**放進 `site/preview/<名稱>/`，並注入 `window.TW_PREVIEW`。`site/perm.js` 第 47 行 `owner()` 遇到 `TW_PREVIEW` 一律回 true，也就是**無鎖頭、不計次、上限給最大**（DECISIONS #343）。目前有 **26 個** preview 分支。同一份 `site/` 也上傳到 Cloudflare Pages，所以 `tw-rotation.pages.dev/preview/<名稱>/` 同樣打得開。
- **風險**：上線之後，只要有人發現網址規則（規則就寫在公開 repo 的 `CLAUDE.md` 和 `docs/preview.md`），把 `/preview/xxx/` 分享到社群，人人都能免費用 Plus／Pro 的畫面。data-gw 切換之後資料會擋住，但畫面功能（篩選、不限次數）仍然全開。另外，預覽版的頁首會顯示內部名稱和黃色橫幅，看起來很不專業。
- **Andy 要做的**：GitHub → repo → **Branches** → 刪掉不用的 `preview/*`（10-07 帳本第 11 項列過 12 支可以直接刪；容器的 git 代理擋刪除，所以要 Andy 在網頁按）。
- **工程要做的**（擇一，建議 a）：
  - (a) 正式網域（Cloudflare Pages）的部署包排除 `site/preview/`，預覽只留在 GitHub Pages。
  - (b) 預覽版改成「只有管理者登入時才比照擁有者」，訪客看到的權限跟正式站一樣。
  - 兩個都做最好。另外加一行 `<meta name="robots" content="noindex">` 給預覽頁。
- **優先序**：**上線前必做**。

### G3 Cloudflare 額度、帳單與「一支腳本打掛全站」

- **現況**：
  - Andy 10-06 決定「Cloudflare 付費方案先不辦，維持免費」（帳本第 444 行）。
  - Cloudflare 免費方案每天 10 萬次請求，**整個帳號共用**（官方文件：workers.dev 的請求和網域的請求算在同一個額度裡）。超過之後**請求直接失敗，回 1027 錯誤，到 UTC 午夜（台北早上 8 點）才恢復**。
  - 共用這個額度的 Worker 有：`tw-quote`（報價）、`tw-account`（會員、登入）、之後的 `tw-data-gw`。
  - 報價代理只看 Origin（S4 沒做）。
- **風險**：
  - **攻擊情境**：有人用 `curl -H "Origin: https://miaozike.github.io"` 迴圈打 `/quote` 10 萬次，大約幾十分鐘就打滿 → 當天所有人**不能登入、自選清單讀不到、付費資料打不開** → 一直到隔天早上 8 點。成本接近零，也不需要任何技術門檻。
  - **正常成長也會撞到**：`docs/hosting_cost_plan.md` 估每日開頁約 8,000 次，會員系統就到頂。
  - 升級付費方案之後沒有請求上限，風險**從當機變成帳單**：Cloudflare 的預算警示只通知、不會自動停（官方文件原文：informational only, do not pause or cap usage），而且是**隔天**才寄。
- **Andy 要做的**：
  1. Cloudflare → **Workers & Pages → Plans**（或 Manage Account → Billing）→ 升級 **Workers Paid（每月 5 美元）**，綁信用卡。
  2. **Manage Account → Billing → Billable Usage → Create budget alert**，門檻建議 **10 美元**；另外在 **Notifications → Add** 加一條 Workers 用量通知。收件人填 Andy 的 Gmail。
  3. 信用卡用**有單筆或月額上限的卡**（或虛擬卡），當作最後一道保險。
- **工程要做的**：
  - S4：`/quote`、`/stream`、`/fut*` 要求會員權杖（或至少 data-gw 那種短效權杖），而且每個 IP、每個帳號都限流。0.5～1 天。
  - 會員 Worker 的 `rateOk` 目前是每個 IP 每分鐘 60 次，計數只放在記憶體。這對單一 IP 夠用，但擋不住分散的 IP。網域上線後加一條 Cloudflare **Rate Limiting 規則**（免費方案有 1 條），套在 `/v1/*`。
  - 把三支 Worker 都改成綁在自有網域的路由（例如 `api.網域`），之後才能套 WAF 規則；workers.dev 子網域套不到網域規則。這條可以晚一點做。
- **優先序**：升級付費方案、預算警示、S4 都是**上線前必做**；Rate Limiting 和 WAF 是**一個月內**。

### G4 自有網域與 HTTPS

- **現況**：沒有網域（repo 裡沒有 `CNAME`）。正式站有兩份：`miaozike.github.io/tw-rotation/` 和 `tw-rotation.pages.dev`。帳本第 8 項「d 換網域」從 10-03 起還在等 Andy 決定。
- **風險**：
  1. GitHub Pages 的條款**不准拿來經營商業網站**（`docs/hosting_cost_plan.md` §一）。開始收費之後繼續用 github.io，帳號可能被停。
  2. 沒有網域就沒辦法通過 Google 品牌驗證（G5），也開不出 `support@` 信箱（G9），主站壞了也沒辦法切到備援（hosting_cost_plan §三）。
  3. 兩份正式站同時存在：使用者會分成兩群，localStorage 也分成兩邊（自選清單的本機副本、同意紀錄各存各的）。搜尋引擎會判成重複內容。
  4. 網址露出個人帳號名（`miaozike`、`kcq01010909.workers.dev`）。
- **Andy 要做的**：
  1. Cloudflare → **Domain Registration → Register Domains** → 買網域（`.com` 一年約 10～15 美元，以成本價出售；**這個價格沒有查證**）。DNS 自動交給 Cloudflare 管。
  2. Cloudflare → **Workers & Pages → tw-rotation（Pages 專案）→ Custom domains → Set up a custom domain** → 填網域。HTTPS 憑證會自動發。
  3. 網域的 **SSL/TLS → Edge Certificates** → 打開 **Always Use HTTPS**；確認一週沒問題之後再開 **HSTS**（開了很難關，所以放後面）。
- **工程要做的**：
  - 改 `ALLOWED_ORIGINS`：三支 Worker 各一份，加新網域。
  - 改 `preview_inject.py` 的 `PROD_URL`、`docs/preview.md`。
  - 隱私權政策裡的 hosting 欄位，從「GitHub Pages」改成 Cloudflare Pages。
  - 上線後 github.io 改成一頁「已搬家」並自動轉址（`<meta http-equiv="refresh">` 加上 canonical），pages.dev 也導到新網域。
  - **做完之後，github.io 的部署要停**，不然那裡會一直留著一份完整的站。
- **優先序**：**上線前必做**（只要會收費，或要讓 Google 登入畫面顯示站名，就躲不掉）。

### G5 Google OAuth：正式網域、同意畫面、品牌驗證

- **現況**：
  - `worker.js` 只要求 `openid email profile`（第 282 行）。`docs/login_setup.md` 第 47 行寫了「發布應用程式」的步驟，但 ⚠ **現在是「測試中」還是「正式版」查不到**，要 Andy 看一眼。
  - 重新導向 URI 在 `tw-account.kcq01010909.workers.dev/auth/callback`。
- **查證**（Google 官方說明，WebSearch 摘要）：
  - 只要求 openid／email／profile 的 App **不受 100 人上限限制**，也**不會出現紅色的「未經驗證」警告**。100 人上限只套用在要求敏感或受限範圍、又沒通過驗證的 App；「測試中」狀態則是最多 100 位測試使用者。
  - 但是：**沒通過品牌驗證，同意畫面不會顯示 App 名稱和 Logo**。品牌驗證要求在 Search Console 驗證網域擁有權，首頁和隱私權政策網址也要放在那個網域上。`workers.dev`、`github.io` 都不是 Andy 的網域，**驗證不了**。
  - 我們的推論（沒有親眼看到畫面）：沒有品牌驗證的話，使用者在 Google 登入畫面看到的會是網域，例如「繼續使用 kcq01010909.workers.dev」，**也就是 Andy 的 Gmail 帳號名**，看起來也像釣魚網站。
- **風險**：
  - 登入轉換率低，客訴「是不是詐騙」。
  - 個人信箱曝光，跟 S11 是同一個問題。
  - 如果還在「測試中」：第 101 個人登不進來（雖然上面那份 Google 說明寫基本範圍不受白名單限制，這點跟我們手上的 `login_setup.md` 不一致，**以 Andy 在後台看到的為準**）。
- **Andy 要做的**（Google Cloud Console → 選 tw-rotation 那個專案）：
  1. **Google Auth Platform → 目標對象（Audience）**：發布狀態必須是「**正式版／In production**」。
  2. **品牌（Branding）**：App 名稱「哩股哩股」、上傳 Logo、**使用者支援電子郵件**改成客服用的 Google 群組或別名（這一格會顯示給所有使用者看；Google 規定只能填自己的信箱或自己管理的 Google 群組）、App 首頁和隱私權政策和服務條款都填**新網域**的網址、**已授權網域**加新網域。
  3. **Search Console**（search.google.com/search-console）→ 新增資源 → 網域 → 用 Cloudflare DNS 加一筆 TXT 驗證。
  4. **用戶端（Clients）→ 那支 Web 用戶端**：「已授權的 JavaScript 來源」加 `https://新網域`；重新導向 URI 改成新網域下的 Worker 路由（如果 Worker 也搬到 `api.新網域`）。舊的先留著，搬完一週後再刪。
  5. 回到 **品牌** 頁按 **提交驗證**。品牌驗證通常 2～3 個工作天（這個時間是一般經驗，沒有查證）。**所以要比上線早幾天送出**。
- **工程要做的**：上架當天給 Andy 逐步點擊步驟（帳本第 453 行的規定）。Worker 改走自有網域路由之後，回跳網址也要跟著改。新網域要放得出可以公開瀏覽的首頁、`#privacy`、`#terms`（Google 會檢查首頁不能要求先登入）。
- **優先序**：「正式版」狀態和來源網址是**上線前必做**；品牌驗證**上線前送出**，審核結果可以在上線後才拿到。

### G6 會員資料備份與還原演練

- **現況**：
  - `/v1/admin/export` 和 `/v1/admin/import?confirm=RESTORE-INTO-EMPTY-DB` 已經上線，有測試（`workers/account-api/tests/export.test.mjs`）。
  - **BACKUP_TOKEN 沒設**：最新一次部署「寫入 BACKUP_TOKEN」那一步是 skipped。
  - 帳本第 14 項「筆電裝監控＋備份」從 10-07 起一直在等。
  - `docs/BACKUP_RUNBOOK.md` 第 2 節「第二份雲端備份選哪個：尚未選」。
  - **從來沒有做過還原**。
- **風險**：會員 Durable Object 是唯一的一份（hosting_cost_plan §三：「沒有第二家可以接手」）。誤刪（管理區按錯）、程式 bug 把資料表清掉（migration 寫錯）、Cloudflare 帳號被停，都會讓付費會員的方案、到期日、自選清單**全部消失**，而收過錢的證據只剩藍新那邊。另外，**沒有演練過的備份不能算有備份**：簽章金鑰不對、欄位對不上，都要真的還原一次才會發現。
- **Andy 要做的**：
  1. 用密碼管理器產生 48 字的亂數 → GitHub **Settings → Secrets → Actions** → 新增 `BACKUP_TOKEN` → 到 **Actions → 部署 Worker（會員）→ Run workflow** 重跑一次。
  2. 照 `tools/laptop/README.md` 在筆電安裝（第 7 步用同一個值設 `cmdkey`）。
  3. 選第二份雲端備份：A 是 Google Drive，B 是 R2。**建議 A**，因為 R2 跟 Worker 在同一個 Cloudflare 帳號，帳號出事會一起不見。
  4. ⚠ BACKUP_TOKEN 的值另外存一份在密碼管理器。值不一樣，舊備份的簽章就驗不過。
- **工程要做的**：
  - 建一支**演練用 Worker**（`tw-account-drill`，用另一個 DO 名稱，空資料庫）→ 把筆電的最新備份匯入 → 比對筆數、抽 3 個帳號的方案和自選 → 寫一份演練紀錄到 `docs/` → 刪掉這支演練 Worker。
  - **絕對不在正式 Worker 上演練**（`import` 只准空資料庫，就是為了防這件事）。
  - 之後每月演練一次。
- **優先序**：備份接通是**上線前必做**；第一次還原演練要在**上線前或上線第一週內**完成。

### G7 管理後台權限

- **現況**：
  - 伺服器端做得正確：`/v1/admin/*` 一律先驗證管理者（`worker.js` 第 2073 行之後那一段）。只有 `ADMIN_EMAILS` 裡的擁有者能新增或移除管理者，`admin_log` 只增不改。被移除的人 `tv+1`，舊權杖立刻失效。
  - **但是**：
    - 管理者權杖跟一般會員一樣有效 **60 天**，存在 localStorage（S7 沒做）。
    - 沒有 CSP（S9 沒做）。
    - 前端還有一些地方沒有經過 `esc()` 就塞進 innerHTML（S8，只抽查過）。
    - 管理者也沒有「登出所有裝置」的按鈕。
- **風險**：只要出現一個 XSS，或 Andy 在公用電腦登入，攻擊者就能拿著管理者權杖 60 天：改任何人的方案、匯出全部會員 email（個資外洩，需要通報）。
- **Andy 要做的**：
  - 管理工作只在自己的電腦、單獨一個瀏覽器設定檔做。
  - 上線前到 `#admin/admins` 看一眼，確認除了自己沒有別人。
  - GitHub Secret `ACCOUNT_ADMIN_EMAILS` 只放自己的信箱。
- **工程要做的**：
  - 管理者權杖改成 7 天、不滑動續期（0.5 天）。
  - 加「登出所有裝置」：遞增自己的 `tv`。管理區也加一顆「讓某個會員全部登出」。
  - CSP 用 `<meta>` 先上，搬到 Cloudflare Pages 之後改用 `_headers`（0.5～1 天加上全站驗收）。
  - S8 全面掃一次（1 天）。
- **優先序**：權杖縮短和「登出所有裝置」是**上線前必做**（第 10 條演練要用到）；CSP 和 S8 是**一個月內**。

### G8 事件應變（出事了怎麼辦）

- **現況**：沒有應變文件。所有分散的機制都已經存在，只是沒有整理成一張表：
  - `tv` 可以讓單一帳號的權杖失效。
  - data-gw 有停權機制（`AUTO_SUSPEND=0`，只記錄）。
  - 金鑰都在 Secrets。
- **風險**：真的出事（帳號被盜、金鑰外洩、資料外流、服務整天掛掉）時，Andy 不知道第一步按哪裡。個資外洩依《個人資料保護法》第 12 條，**查明後要通知當事人**；而且付費服務出事時，客訴和退款會一起湧進來（`legal_config.js` 的 `REFUND_OUTAGE_DAYS=7`，代表連續 7 天無法提供核心功能就要按比例退款）。
- **工程要做的**：寫 `docs/incident_runbook.md`，一頁，每一種情況寫「第一步按哪裡、第二步通知誰、怎麼恢復」：
  - ① 某個會員權杖被盜：管理區讓他全部登出。
  - ② 管理者帳號被盜：Google 改密碼、撤銷所有工作階段 → GitHub 改 `ACCOUNT_ADMIN_EMAILS` → 重新部署（會員 Worker 部署時重讀 Secret）。
  - ③ 金鑰外洩：清單裡每一把金鑰寫「去哪裡撤銷、去哪裡換」。換 `GW_SECRET` 會讓所有資料權杖失效；換 kv 的 hmac 會讓**全站所有人登出**。
  - ④ 服務停擺：維護公告怎麼發（`notices` 已經有）、怎麼切到備援。
  - ⑤ 個資外洩：通報時限與範本（這一項請律師看）。
  - ⑥ 收到爬蟲或外流的檢舉：用浮水印查是哪個帳號流出去的。
  - 上線前先演練 ①（在測試帳號上）。
- **Andy 要做的**：讀一遍，把裡面「Andy 的帳號密碼和復原碼在哪裡」那一格自己填好（不進 repo，存在密碼管理器）。
- **優先序**：**上線前必做**（一頁就好，不必完美）。

### G9 客服信箱

- **現況**：客服、法律聯絡、個資刪除申請、Google 同意畫面的支援信箱，全部是 Andy 的個人 Gmail，同一個也是 `ADMIN_EMAILS` 的擁有者帳號（S11）。Andy 10-06 決定「另開」，10-09 說「後面會更改」。
- **風險**：
  - 攻擊者知道**要釣哪一個帳號**：客服信箱就是管理者帳號。
  - 客訴、退款、個資申請跟私人信混在一起，容易漏掉。法定期限（例如退款 14 天、個資 15 天）一漏就違約。
- **Andy 要做的**：有網域之後最省事的做法是 Cloudflare → 網域 → **Email → Email Routing** → 建立 `support@網域`，轉寄到一個**新的 Gmail**（不是管理者那個），回信用 Gmail 的「以這個地址寄信」。免費。
- **工程要做的**：換掉 `support.js`、`legal.js`、`legal_config.js`、`account.js` 和文件裡的信箱，一次改完。
- **優先序**：**上線前必做**（條款裡的聯絡信箱一旦發佈出去就很難收回）。

### G10 上線後監控（壞掉誰知道）

- **現況**：
  - `worker-watch.yml` 每兩小時打報價代理三支端點。**最近 30 次裡 12 次失敗**（最近一次失敗是 10-09 09:11 UTC，也就是台北 17:11），沒有人處理，也就是說**紅燈已經沒人看了**。
  - **會員 Worker、data-gw、主站本身、Cloudflare Pages，完全沒有外部監控。**
  - 筆電監控（`tools/laptop`）還沒安裝（帳本第 14 項）。
  - 排程工作流失敗時，GitHub 只會寄信給「最後改過那支工作流排程的人」，而那個人不一定是 Andy。
- **風險**：登入掛掉、資料沒更新、付費資料打不開，都是**付費使用者先發現**、先客訴（9-23 夜盤事件就是使用者先發現的，`worker-watch.yml` 檔頭有寫）。
- **Andy 要做的**：
  1. 註冊一個免費的外部監控服務（例如 UptimeRobot，免費方案每 5 分鐘探測一次；**方案細節沒有查證**）。加 3 個 HTTP 監測：主站首頁、`tw-account…/health`（或新網域的 api）、`tw-data-gw…/health`。通知設 Email 加手機 App 推播。
  2. GitHub → 右上頭像 → **Settings → Notifications → Actions**：勾選「只在失敗時通知」，寄到 Andy 的信箱。
- **工程要做的**：
  - 先查清楚 worker-watch 那 12 次紅燈是不是誤報。是誤報就修斷言（「天天紅燈就再也沒人看紅燈」，那支工作流自己的檔頭就這樣寫）。
  - 新增一支每小時的「全站健康檢查」：主站、會員 Worker 的 `/health`、data-gw 的 `/health`，加上資料新鮮度（`data/_state/last_run.json` 超過 26 小時沒更新就算壞）。失敗時開一張 GitHub Issue 並 @Andy（Issue 一定會寄信），而不是只讓 run 變紅。
- **優先序**：**上線前必做**。

### G11 隱私權政策、條款、Google Analytics 一致性

- **現況**：
  - 站上**沒有** Google Analytics 或任何第三方追蹤碼（grep `googletagmanager|gtag|G-…` 0 筆），統計全部是自家會員 Worker 做的不具名彙總。隱私權政策也明寫「不使用 Cookie 進行追蹤，不裝設廣告追蹤器」（`legal.js` 第 221 行），**兩邊目前一致**。
  - 但是：
    - `legal_config.js` 的 `enabled: false` → 條款頁頂端掛「草稿，尚未生效」，同意橫幅也不出現。
    - `hosting` 欄位只列了 GitHub Pages、Cloudflare Workers、Deno、Google，**少了**：Cloudflare Pages（已經在雙部署）、R2（data-gw 開了之後）、Resend（寄異常通知，會帶到帳號識別碼）、之後的藍新金流。
    - 聯絡信箱是個人 Gmail（G9）。
- **風險**：
  - 如果 Andy 打算上線時加 GA：GA 會設 Cookie、把 IP 和行為資料送給 Google，直接跟「不使用 Cookie 追蹤」那句話衝突，而且要加同意機制。**建議不要加 GA**；需要看流量的話，用 Cloudflare Web Analytics（不用 Cookie，網域綁上 Pages 之後在後台就能開），但 hosting 那一欄還是要寫上它。
  - 條款沒啟用就開始收費：使用者沒有同意過任何條款，退款和責任限制都沒有依據。
  - 條款的「服務提供者」只寫「哩股哩股」，`tax_id: '尚未辦理'`。對付費服務來說，消費者要知道「跟誰交易」（通訊交易的資訊揭露），**請律師看要揭露到什麼程度**（`docs/launch_standard.md` 第 4 項本來就要找律師）。
- **Andy 要做的**：
  - 決定「上線時加不加 GA」。我們建議不加。
  - 條款和政策定稿後說「可以開」。
- **工程要做的**：
  - 改 hosting 清單、信箱、網址 → `enabled: true`。
  - 三處同步規則（DECISIONS #270-7）：`legal.js`、`account.js` 的告知、`worker.js` 的保存期限，三處要一致。
  - data-gw 開了之後，確認「安全紀錄」段落真的出現（它看的是 `TW_ACCOUNT.gw`）。
- **優先序**：**上線前必做**。

### G12 濫用防護（灌帳號、爬蟲、速率限制）

- **現況**：
  - 註冊只能用 Google 帳號（要求 `email_verified`）。
  - 會員 Worker 每個 IP 每分鐘 60 次，計數放記憶體。
  - data-gw 已經寫好每帳號限流、裝置上限 2 台、多 IP 偵測、浮水印，**但沒部署**（G1）。
  - 沒有註冊數異常的警示。
  - 公開 JSON 沒有任何保護。
- **風險**：
  - **灌帳號**：免費會員的每日額度比訪客多（訪客每天 3 次）。開一堆 Google 帳號就能把額度乘以 N，或者大量註冊讓會員表變大。單一個人的成本不高。
  - **爬蟲**：現在整站 JSON 都能直接抓（G1）。切換之後，免費部分仍然公開，這是設計上接受的。
- **工程要做的**：
  - data-gw 上線後，把 `AUTO_SUSPEND` 維持 0，觀察兩週再定門檻（已拍板）。
  - 會員 Worker 加「每小時新註冊數超過 N 就寄信」（0.5 天）。
  - 網域上線後開 Cloudflare **Bot Fight Mode**（免費），加一條 Rate Limiting 規則。
  - 註冊加 Cloudflare Turnstile（免費的人機驗證）可以**延後**；Google 登入本身已經是一道門檻。
- **優先序**：data-gw 跟 G1 一起做；註冊警示和 Bot Fight Mode 是**一個月內**；Turnstile **可延後**。

### G13 供應鏈與 GitHub 帳號設定

- **現況**：S17（第三方 action 沒釘 SHA）、S18（沒有 Dependabot、requirements 沒釘版本）都沒做。S1 的 Secret scanning 狀態查不到。main 分支有沒有保護查不到（API 回 403）。
- **風險**：`cloudflare/wrangler-action` 被人動了標籤 → 偷走 `CLOUDFLARE_API_TOKEN` → 改寫會員 Worker、讀走全部會員資料（2025 年 tj-actions 事件就是同一種手法）。public repo 被誤 push 金鑰 → 幾分鐘內就被機器人掃走。
- **Andy 要做的**（GitHub → repo → **Settings**）：
  1. **Code security** → 打開 **Secret scanning** 和 **Push protection**、**Dependabot alerts**。
  2. **Rules → Rulesets → New branch ruleset** → 目標 `main` → 只勾 **Block force pushes** 和 **Restrict deletions**。不要勾「需要 PR」，不然 Claude 直接推 main 的流程會斷掉。
  3. Cloudflare API 權杖只給需要的權限（S19）：Workers Scripts、R2、Pages 的 Edit，範圍限定這個帳號，**不要用 Global API Key**。
- **工程要做的**：5 處第三方 action 改用 40 碼 SHA 並在後面註解版本號；加 `.github/dependabot.yml`（github-actions＋pip）。30 分鐘。
- **優先序**：Andy 的三個開關是**上線前必做**（各 2 分鐘）；釘 SHA 是**上線前必做**（30 分鐘，而且直接保護到金鑰）；requirements 釘版本是**一個月內**。

### G14 金鑰清單與 TRIAL_HMAC_KEY

- **現況**：`TRIAL_HMAC_KEY` 沒有接進 `deploy-account-worker.yml`，只能手動 `wrangler secret put`。`wrangler.toml` 寫明「上線前就要設；設了之後不要換」。沒設的話，Worker 會退回用站內簽章金鑰，`/v1/billing/me` 回 `hk:'fallback'`。
- **風險**：上線之後才設，等於中途換金鑰，之前記下的「7 天退款保證」比對碼全部對不上 → 同一個人可以重複領退款保證。
- **Andy 要做的**：在密碼管理器產生一把亂數，存成 GitHub Secret `TRIAL_HMAC_KEY`。
- **工程要做的**：把它接進部署工作流的 secrets 清單（跟 BACKUP_TOKEN 一樣「有設才寫」）；上線前確認 `/v1/billing/me` 回的是 `hk:'secret'`；`BACKUP_RUNBOOK.md` 的金鑰名稱表補上 `TRIAL_HMAC_KEY`、`DATA_GW_SECRET`、`DATAGW_INTERNAL_KEY`、`RESEND_API_KEY`、`R2_*`。
- **優先序**：**上線前必做**（只要退款保證有對外寫出來）。

---

## 四、一個月內與可延後

| 條目 | 內容 | 優先序 |
|---|---|---|
| G3 | Worker 改走自有網域路由，加 WAF 規則 | 一個月內 |
| G7 | CSP（`_headers`）、S8 XSS 全掃 | 一個月內 |
| G12 | 註冊異常警示、Bot Fight Mode | 一個月內 |
| G13 | requirements 釘版本 | 一個月內 |
| S21 | 畫面上的內部用語清掉；移除 `#tasks` 路由 | 一個月內 |
| D1 | repo 改 private 或拆 repo（Actions 分鐘數的成本等 Andy 選） | 可延後（data-gw 切換之後就不影響付費內容） |
| G12 | 註冊加 Turnstile | 可延後 |
| — | 報價改成推播、心跳改 2 分鐘（省 Worker 請求，見 hosting_cost_plan §五） | 可延後（等實際用量出來） |

---

## 五、來源（WebSearch，2026-10-09；只引用摘要，原文點不進去）

- Google OAuth 使用者上限與發布狀態：[Manage App Audience（support.google.com/cloud/answer/15549945）](https://support.google.com/cloud/answer/15549945?hl=zh-Hant)、[OAuth production readiness overview](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview)
- Google 品牌驗證：[Submit for brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification?authuser=0)、[Sensitive scope verification](https://developer.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification)
- Cloudflare Workers 免費額度與 1027：[Workers limits](https://developers.cloudflare.com/workers/platform/limits)
- Cloudflare 預算警示：[Budget alerts](https://developers.cloudflare.com/billing/manage/budget-alerts/)
