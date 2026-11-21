# 藍新金流（NewebPay）串接規格：訂閱制會員（免費試用暫不提供）

> ★ **2026-10-09 18:1x Andy 決定（退款問題 1 選 C）：先不提供免費試用，只保留 7 天退款保證（`legal_config.REFUND_DAYS`）。**
> 下面 2-4「試用 30 天」整節與按鈕文字「開始 30 天免費試用」是**舊規劃、暫緩不做**，留著只供日後若開試用時參考；
> 屆時試用與退款保證合計一次（使用條款、退款頁「防止濫用」已這樣寫）。前端不准出現「1 個月／30 天免費試用」字樣。

> payments-billing，2026-10-06（台北）。**只是規格，沒有寫任何程式碼。**
> 查證方式：只有 WebSearch 摘要（出口代理擋 WebFetch，藍新官方技術手冊 PDF 打不開）。
> 下面每一條事實都標了來源與信心度；**標「未確認」的不准當成定論**，要等 Andy 拿到藍新後台與正式技術手冊再核對。
> 金鑰（HashKey／HashIV）一律不寫進這份文件或 repo。

---

## 0. 給 Andy 的白話摘要（先看這節就好）

1. **藍新做得到我們要的事**：信用卡「定期定額」＝每月自動扣款的訂閱制，有修改／暫停／終止委託的 API，付款結果用背景通知（NotifyURL）打回我們的 Worker。（信心：中，來源是第三方 SDK 與教學摘要，不是藍新原文）
2. **但有一個前提擋在最前面：收費本身的法遵風險還沒解。** `docs/compliance_and_tiers.md` 的結論是「現在這個站原封不動收 399／799 是高風險」。金流串得再好，這件事沒處理就不能開收。見第 6 節。
3. **第二個前提：付費牆目前擋不住人。** DECISIONS #288 與 `docs/security_review_1006.md` D3 都寫了：付費資料還在公開 JSON 裡，「收費前一定要做」改走 Worker 發放（4～6 天）。金流可以先做，但**不能在 D3 之前正式收錢**。
4. **藍新要統編。** 摘要指出個人開發者要用藍新「需要能開統編（商業登記或工作室）」（信心：中低，單一第三方來源）。藍新另有「個人會員」收款，但能不能用在定期定額、能不能開發票，**未確認**。我的建議是**直接登記行號**，理由在 0-1。
5. **我們這邊能先做的（不用等你）**：規格（本文件）、Worker 端點骨架、用藍新**測試環境**的公開測試流程與測試卡號先打通加解密。**必須等你拿到商店帳號**才能做的列在第 9 節。

### 0-1 Andy 要自己辦的事

| # | 事情 | 步驟 | 預估天數 | 備註 |
|---|---|---|---|---|
| A1 | **先問律師／legal-compliance 收費路徑**（第 6 節） | 拿 `docs/compliance_and_tiers.md` 去諮詢 | 1～3 週 | 不解決不能開收；**其他事可以平行做** |
| A2 | **登記行號（獨資）或公司** | 到縣市政府商業處申請商業登記 → 國稅局稅籍登記，取得統編 | 約 1～2 週（**未確認**，依各縣市） | 要統編才好申請藍新企業會員與開發票。稅法門檻見 0-2 |
| A3 | **申請藍新企業會員＋開商店** | 藍新官網註冊 → 上傳登記文件、負責人身分證、銀行帳戶封面 → 開商店 → 申請啟用信用卡、**另外申請「信用卡定期定額」** | **未確認**；`commercialization_plan.md` 估 1～3 週 | 文件清單與審核天數 WebSearch 查不到原文，以藍新客服為準。審核時網站要有：服務說明、價格、退款政策、隱私權政策、客服聯絡方式（業界常見要求，**未確認**藍新具體清單） |
| A4 | **申請 ezPay 電子發票** | 用同一個藍新帳號啟用 ezPay 電子發票、購買發票字軌／額度 | **未確認** | 摘要：「開立發票要購買發票額度，測試環境也要」（信心：中） |
| A5 | **取得測試環境商店** | 藍新測試站 `ccore.newebpay.com` 註冊測試商店，拿測試用 MerchantID／HashKey／HashIV | 0.5 天 | **不用等 A2、A3**，可以現在做 |
| A6 | 把 HashKey／HashIV 設進 Cloudflare Worker Secret | `wrangler secret put NEWEBPAY_HASH_KEY` 等（或我給你指令，你在 Cloudflare 後台貼） | 10 分鐘 | **不要貼在對話或任何檔案** |
| A7 | 藍新後台、ezPay 後台開 2FA、不共用帳號 | — | 15 分鐘 | `commercialization_plan.md` 安全第 6 條 |

### 0-2 稅務門檻（給 A2 的依據）

- 財政部：個人透過網路銷售**勞務**，月銷售額達起徵點要辦稅籍登記；**自 114 年 1 月 1 日起起徵點調為貨物 10 萬、勞務 5 萬**（台財稅字第 11304677940 號令，信心：中，來源為 etax 與媒體摘要）。訂閱制屬勞務還是數位貨物，**未確認**，交給記帳士判斷。
- 但即使在起徵點以下，**藍新企業會員要統編**、**開統一發票要營業人身分** → 實務上要收訂閱費就要登記。（推論，信心：中）
- 個人行號 vs 公司（稅率、小規模營業人免開發票的條件）→ **未確認，交記帳士**。這裡不下結論。

---

## 1. 藍新查證結果

| 項目 | 查到的 | 信心 | 來源（查證 2026-10-06） |
|---|---|---|---|
| 申請資格 | 個人開發者要能開統編（商業登記或工作室）；有月租型方案 | 中低（單一第三方） | ithelp 10396944 |
| 個人會員能否開定期定額 | **未確認** | — | 查不到 |
| 申請文件、審核天數 | **未確認**（摘要建議洽客服） | — | 查不到 |
| 信用卡費率 | 2.8% 起 | 中低（第三方） | ithelp 10396944 |
| 行動支付（Apple Pay／Google Pay 等） | 2.8%～3% | 中低（第三方） | 同上 |
| 超商代收 | 15 元／筆 | 中低（第三方） | 同上 |
| ATM 轉帳費率 | **未確認** | — | 查不到 |
| 撥款週期 | **未確認** | — | 查不到 |
| 支援付款方式 | 信用卡、網路 ATM、ATM 櫃員機、超商代碼／條碼、Apple Pay、Google Pay、LINE Pay 等 | 中 | wordpress.org newebpay-payment 外掛頁、ithelp |
| 信用卡定期定額 | 有；可修改委託狀態（暫停／終止／重新啟用）、修改委託內容（金額、週期 D/W/M/Y、扣款日、期數、卡片效期） | 中（第三方 SDK 說明） | packagist fall1600/newebpay、violetshih/laravel-newebpay |
| 首期 0 元／延後首扣（試用） | SDK 有 `PeriodStartType` 參數（檢查卡號模式）；**「延後到 30 天後才首扣」能否做到、參數值為何：未確認** | 低 | packagist fall1600/newebpay |
| 退款 | 有「信用卡取消授權」「退款」API | 中（第三方 SDK 功能列表） | packagist laravel-newebpay |
| 電子發票 | ezPay（藍新系加值中心），用藍新帳號登入取商店代號與 HashKey／HashIV；要買發票額度 | 中 | skills.sh tw-ecom-invoice-ezpay、docs.wpsite.pro、packagist agriweather/laravel-ezpay-invoice |
| 幕前 MPG | 表單送 MerchantID、TradeInfo（AES 加密）、TradeSha（SHA256）、Version 2.x | 中 | ithelp 10254517、npm newebpay |
| 測試／正式網址 | 測試 `ccore.newebpay.com`；正式 `core.newebpay.com/MPG/mpg_gateway` | 中 | 同上 |
| 測試信用卡 | 4000-2211-1111-1111 | 中 | 同上 |
| 定期定額端點路徑、通知欄位（例如 PeriodNo、AuthTimes） | **未確認**（只在 SDK 函式名看到 PeriodNo） | 低 | packagist |

⚠ App 內購（IAP）的 15～30% 抽成：本站目前是網頁，付款在瀏覽器完成，不走 App Store。若之後照 `docs/mobile_release_plan.md` 上架 App 並在 App 內引導付款，蘋果／Google 的規則會改變實收 —— **這次沒查，未確認，上架 App 前要另外查。**

---

## 2. 串接架構

```
訂閱頁「訂閱」（舊規劃為「開始 30 天免費試用」，2026-10-09 起暫緩）
  → POST /v1/pay/checkout（帶會員權杖、方案 id、月繳／年繳）
  → Worker 建訂單（狀態 pending）、組定期定額參數、AES 加密、算檢查碼
  → 回傳一個自動送出的表單 → 瀏覽器跳藍新付款頁（卡號只在藍新頁面輸入）
  → 藍新背景 POST /v1/pay/notify（每一期授權結果都會來）
  → Worker 驗檢查碼 → 解密 → 冪等檢查 → 更新 perm.plan／perm.expires
  → 藍新把使用者導回 ReturnURL（/v1/pay/return → 302 到站上的 #account/pay-result）
```

### 2-1 Worker 新端點（`workers/account-api`）

| 端點 | 誰能打 | 做什麼 |
|---|---|---|
| `POST /v1/pay/checkout` | 已登入會員 | 驗權杖 → 查 `plans` 的 price／period（價格**只從伺服器讀**，不信前端）→ 寫 `pay_orders`（pending）→ 回藍新表單欄位 |
| `POST /v1/pay/notify` | 藍新（不帶會員權杖） | 驗檢查碼 → 解密 → 冪等 → 比對金額與訂單 → 更新會員方案 → 回藍新要求的成功字串（**格式未確認**） |
| `POST /v1/pay/return` | 使用者瀏覽器 | **只導頁、不改任何狀態**（ReturnURL 可被偽造），302 到結果頁 |
| `POST /v1/pay/cancel` | 已登入會員 | 呼叫藍新「修改委託狀態＝終止」，本地標記 `cancel_at_period_end`；到期日不變 |
| `GET /v1/pay/me` | 已登入會員 | 回自己的訂閱狀態（方案、到期日、下次扣款日、是否已取消） |
| `/v1/admin/pay/*` | 只有 ADMIN_EMAILS | 查訂單、手動退款標記、補發通知重處理 |

### 2-2 資料表（同一個 Durable Object 的 SQLite，沿用既有寫法）

- `pay_orders(order_no PK, email, plan, period, amount, status, period_no, created, updated)`
  - `order_no`：自產、唯一、只含英數底線（藍新長度上限**未確認**，先以 ≤ 20 字設計）
  - `status`：pending／active／past_due／canceled／ended／refunded
- `pay_events(event_key PK, order_no, raw_status, amount, auth_time, received)` —— **冪等表**
  - `event_key` = `order_no + 期數（或藍新交易序號）`；INSERT 撞主鍵 ＝ 已處理過，直接回成功
- **不存任何卡號**；只存藍新回的末四碼（若有）方便客服。

### 2-3 接既有會員範本（DECISIONS #288、admin-v2b）

- 已存在：`perm(email, plan, over, updated, expires)`、`plans(id, name, feats, price, period)`。
- 通知成功時：`perm.plan = 訂單方案`、`perm.expires = max(現有 expires, 本期起算) + 1 個週期 + 寬限 3 天`。
  - **保留 `over`（個別微調）不動**，跟 #288「方案被刪退回免費、保留微調」同一原則。
- 到期判斷沿用 `effective(email)`：`expires` 過了 → 當成 `free`。**降級不靠排程刪資料，靠讀取時判斷**，所以 Worker 不需要 cron 也不會漏。
- 管理區手動設的方案（例如 Andy 送朋友）與金流設的方案共用欄位 → 加一欄 `perm.source`（manual／newebpay），金流通知**不覆寫** manual 且未到期的人（避免把送的永久方案改成月繳）。

### 2-4 試用 30 天怎麼跟定期定額接（★ 2026-10-09 起暫緩：目前不提供試用）

兩種做法，**哪一種藍新支援要等正式手冊確認**：

| 做法 | 怎麼做 | 好處 | 風險 |
|---|---|---|---|
| **甲（優先）藍新延後首扣** | 建委託時就綁卡，指定首期扣款日 = 今天 + 30 天；建委託時只做卡片驗證（不扣款） | 試用結束自動扣，轉換率高；全部規則在藍新 | 「延後首扣／只驗卡」參數**未確認** |
| **乙（備案）自己給試用、到期才建委託** | 註冊時 `perm.plan=paid, expires=+30 天, source=trial`；第 25 天站內提示「綁卡續用」→ 綁卡當下建委託並立即扣第一期 | 不依賴藍新特殊參數 | 使用者要回來第二次，轉換率較低 |

共同規則：
- **每個 email 只能試用一次**（`trials(email PK, started)`），刪帳號再註冊也不重給（只存 email 雜湊即可，隱私權政策要加一列）。
- 試用期間取消 → 到第 30 天自然降回免費，**不扣任何錢**。
- 試用開始與第 27 天各通知一次（站內公告 `notices`，email 通知**未做、另案**）。

### 2-5 扣款失敗、重試、到期降級

- 藍新每期授權失敗會不會自動重試、重試幾次：**未確認**。
- 我們這邊的規則（不依賴藍新）：
  1. 收到失敗通知 → `status=past_due`，**不立即降級**；`expires` 本來就含 3 天寬限。
  2. 站內提示「扣款失敗，請更新信用卡」→ 更新卡片＝藍新「修改委託內容」（是否能換卡號**未確認**；不行就終止舊委託、建新委託）。
  3. 寬限過了還沒成功 → `effective()` 自動當 free；資料（自選清單等）**保留不刪**。
- 升降級（399 ↔ 799）：第一版**不做比例換算**。規則：升級＝終止舊委託、新方案立即建委託並扣全額、舊方案剩餘天數**依日數比例退款或折抵（二選一，待 Andy 定）**；降級＝下期生效（改委託金額）。

### 2-6 退款與取消

- 取消：只停下一期，當期用到 `expires`。
- 退款：藍新有「取消授權」（未請款前）與「退款」（已請款）API（第三方 SDK 功能列表，信心中）。第一版**後台手動**做，Worker 只記錄 `refunded` 並立即把 `expires` 設回現在。
- 退款條款（7 天鑑賞期是否適用數位訂閱）→ **交 legal-compliance**，不在這裡決定。

### 2-7 電子發票（ezPay）

- 每一期授權成功後，Worker 呼叫 ezPay 開立 B2C 電子發票（載具：會員 email 或手機條碼）。
- 開立失敗不影響開通，記進 `invoice_queue` 讓管理區可重送。
- 退款要作廢或折讓 → 同樣後台手動第一版。
- ezPay 有獨立的商店代號與 HashKey／HashIV（摘要），一樣只放 Worker Secret。

---

## 3. 前端

- **訂閱頁**（`#account/plans` 或沿用既有申請訂閱頁 `sub_requests` 那一塊）：三張方案卡（免費／399／799，價格讀 `/v1/admin/plans` 公開版或 `/v1/pay/me`）、按鈕「訂閱」（2026-10-09 起不提供試用；舊規劃為「開始 30 天免費試用」）；未登入先導去 Google 登入。
- 按下後：呼叫 `/v1/pay/checkout` → 用回傳欄位動態產生 `<form method=post action=藍新網址>` 自動送出。**卡號欄位永遠不在我們的頁面上。**
- **結果頁**（`#account/pay-result`）：不相信網址參數，一律打 `/v1/pay/me` 輪詢最多 30 秒看狀態變 active；超過就顯示「付款處理中，稍後會自動開通」。
- 帳號頁：顯示方案、到期日、下次扣款日、「取消訂閱」鈕（二次確認）、扣款失敗時的紅色提示。
- 頁尾連結：服務條款、退款政策、隱私權政策（藍新審核通常需要，**未確認**清單）。

---

## 4. 安全

1. **HashKey／HashIV、ezPay 金鑰只放 Cloudflare Worker Secret**，不進 repo、不進 `wrangler.toml`、不進前端；push 前照 CLAUDE.md 掃一次。
2. `/v1/pay/notify` **一定驗檢查碼**（TradeSha＝對 TradeInfo 做 SHA256 並轉大寫，前後夾 HashKey／HashIV，**組字規則以正式手冊為準**），驗不過回 400 並記錄。
3. 解密後**再比對**：MerchantID 是我們的、訂單存在、金額等於訂單金額、方案存在。任何不符 → 不開通、記異常。
4. **冪等**：`pay_events` 主鍵擋重複；同一筆通知來兩次只處理一次、第二次直接回成功。
5. ReturnURL 不改狀態；狀態只由 NotifyURL 決定。
6. 價格只從伺服器 `plans` 讀；前端送來的金額一律忽略。
7. 通知端點不走 CORS 白名單（藍新是伺服器打來），但**也不帶任何會員權限**；限流（同 IP 每分鐘上限）。藍新來源 IP 白名單**未確認**是否公開。
8. 藍新後台、ezPay、Cloudflare 都開 2FA（S14）。
9. 測試卡號、測試商店金鑰同樣不進 repo（測試金鑰也是金鑰）。

---

## 5. 測試計畫

| 階段 | 內容 | 需要 |
|---|---|---|
| T1 本機單元 | AES 加解密、檢查碼用藍新手冊的官方範例向量比對；冪等（同一通知送兩次）；金額竄改、檢查碼錯、未知訂單都拒絕 —— 沿用 `workers/account-api/tests` 的允許／拒絕寫法 | 手冊範例（等 A5） |
| T2 測試環境 | `ccore.newebpay.com` 用測試卡 4000-2211-1111-1111 走完：建委託 → 首期通知 → 會員變 paid → 取消 → 到期降 free | A5 測試商店 |
| T3 失敗路徑 | 授權失敗卡號（測試卡清單**未確認**）、通知延遲、通知重送 | A5 |
| T4 前端驗收 | `_uitest.py` 新段落「金流訂閱」：按試用 → 表單欄位齊全 → 模擬通知 → 帳號頁顯示到期日 → 取消 → 顯示「將於 X 到期」 | — |
| T5 正式小額 | 正式商店開一個 NT$1 測試方案、Andy 自己刷一次再退款 | A3 |

---

## 6. 法遵：引用既有文件，不自己下結論

- `docs/compliance_and_tiers.md`：現站原封不動收 399／799「高風險，且不是灰色地帶」；投顧法 §4 定義「直接或間接取得報酬＋對有價證券提供分析意見或推介建議」，§107 未經許可經營可處刑責；並引了一件「線上平台、訂閱／會員制」被判非法投顧的相似案例（見該文件 1-1）。
- 同文件②三層分層：族群層級資金流向等「可以收錢」，個股層級建議／買賣點類高風險，`broker_views.json`（券商目標價）列為高風險。
- `docs/commercialization_plan.md`：收費前要律師諮詢、全站免責聲明。
- **金流這邊的推論（不是結論）**：金流一接上，「直接取得報酬」這個要件就成立。所以**開收的開關（把免費範本關掉）必須在法遵確認之後才按**；金流本身可以先做到測試環境為止。

### 交給 legal-compliance 的缺口
1. 各付費功能逐項過一次投顧法（現有分層表是否已足夠）。
2. 數位訂閱的退款／7 天鑑賞期規定與退款政策文字。
3. 試用自動轉付費的告知義務（消保法、定型化契約）—— 頁面上要寫到什麼程度。
4. 定期定額授權書／服務條款需新增的條文。
5. 「僅資訊工具、非投顧」聲明在付款頁與發票品名上的寫法（品名寫「資料工具訂閱」之類，**未確認**是否有影響）。

---

## 7. 工作量估計與先後順序

| 順序 | 工作 | 天數 | 要等誰 |
|---|---|---|---|
| 1 | 本規格 | 完成 | — |
| 2 | Worker：資料表、`/v1/pay/checkout`、`/notify`、`/return`、`/me`、加解密、冪等、測試（T1） | 2～3 | 加解密向量要 A5 測試商店／手冊 |
| 3 | 試用機制（做法乙先做，甲等手冊）＋到期判斷接 `effective()` | 1 | — |
| 4 | 前端訂閱頁、結果頁、帳號頁訂閱區塊＋`_uitest` 段落 | 1.5～2 | — |
| 5 | 測試環境整合（T2、T3） | 1～1.5 | **A5** |
| 6 | 取消、扣款失敗、升降級、後台訂單管理 | 1.5～2 | 升級折抵規則待 Andy 定 |
| 7 | ezPay 電子發票串接 | 1.5～2 | **A4** |
| 8 | 正式商店切換、小額實刷（T5） | 0.5 | **A3**、法遵 A1 |
| 9 | 付費資料改走 Worker（security D3，另案） | 4～6 | 收費前必做 |
| | **金流本身合計** | **約 9～13 個工作天** | 不含 D3 與等待審核 |

### 必須等 Andy 拿到帳號才能做的
- **A5 測試商店**：第 2 步的加解密實測、第 5 步整合測試。（A5 不需要統編，最快可以先做）
- **A3 正式商店＋定期定額開通**：第 8 步；以及確認試用「做法甲」的參數。
- **A4 ezPay**：第 7 步。
- **A1 法遵**：真正開收（關掉免費範本）。

### 不用等、可以先做的
第 2～4 步的程式骨架（加解密依手冊公開規格先寫、待 A5 驗證）、第 6 步的本地規則、前端頁面。

---

## 8. 未確認清單（拿到藍新正式手冊後逐條核對）

1. 個人會員能否申請定期定額、能否開發票。
2. 申請文件清單、審核天數。
3. ATM、超商、Apple Pay、Google Pay 的正式費率；撥款週期。
4. 定期定額的端點路徑、參數名、首期延後／只驗卡的做法（試用做法甲）。
5. 每期授權通知的欄位、成功回應字串、失敗是否自動重試。
6. 委託能否換卡。
7. 訂單編號長度與字元限制。
8. 藍新通知來源 IP 是否公開。
9. App 上架後 IAP 規則（另案）。
10. 行號 vs 公司、勞務起徵點適用（交記帳士）。

## 來源（查證日期 2026-10-06，均為 WebSearch 摘要，未讀原文）
- ithelp 10396944（藍新費率、個人需統編）：https://ithelp.ithome.com.tw/articles/10396944
- ithelp 10254517（MPG、測試／正式網址、測試卡）：https://ithelp.ithome.com.tw/articles/10254517
- npm newebpay：https://npmjs.com/package/newebpay
- WordPress 藍新外掛（支援付款方式）：https://wordpress.org/plugins/newebpay-payment/
- packagist fall1600/newebpay（定期定額、PeriodStartType）：https://packagist.org/packages/fall1600/newebpay
- packagist violetshih/laravel-newebpay（修改委託狀態／內容、退款）：https://packagist.org/packages/violetshih/laravel-newebpay
- ezPay 發票：https://www.skills.sh/asgard-ai-platform/skills/tw-ecom-invoice-ezpay 、https://docs.wpsite.pro/wp/chuan-jie-jin-liu-wu-liu-dian-zi-fa-piao/lan-xin-jin-liu-wu-liu-dian-zi-fa-piao-ezpay 、https://root.packagist.org/packages/agriweather/laravel-ezpay-invoice
- 財政部網路銷售起徵點：https://www.etax.nat.gov.tw/etwmain/tax-info/network-transaction-taxtation-area/press/3EYDDZV 、https://www.inside.com.tw/article/18799-E-commerce-tax
