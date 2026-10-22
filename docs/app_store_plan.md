# 哩股哩股 上架 Google Play 與 App Store 計畫（2026-10-22 版）

> Andy 原話：「我需要將手機上架 APP Play 商店 以及 APP Store」。
> 這份是 `docs/mobile_release_plan.md`（2026-09-24）的**更新版**。那份寫的時候網站還沒有自己的網域、還沒有登入、還沒有收費；
> 現在三樣都有了（`liguligu-puipui.com`、Google 登入、銀行轉帳＋綠界訂閱），**收費這件事讓整個上架題目變了**，所以重寫一份。
> 舊文件的條文整理仍然有效，本文件引用時寫「舊文件 4-1」這種形式。

**標示方式**：〔事實〕＝查到的，附來源編號（文末來源清單）；〔判斷〕＝我的推論。
信心度：**高**（官方頁面摘要，或兩個以上獨立來源）／**中**（單一可靠來源）／**低**（只有二手摘要）／**未確認**（查不到，不准當成可以）。

⚠ 查證限制：這個容器只放行 `WebSearch`（只拿得到摘要，點不進原文）；Apple、Google 的官方頁面都打不開。
下面引用的條文都是**搜尋摘要轉述**，不是我親眼讀到的原文。真的送審前，Andy 打開官方頁面看一眼最新版（網址在來源清單）。

---

## 摘要（先看這 12 條）

1. **建議路線**：**Android 用 TWA（Bubblewrap）、iOS 用 Capacitor ＋ 一層真的原生功能。** 原生重寫不做。
   Android 這條幾乎不用改網站，**這批已經把設定檔與打包工作流做好了**（第 ⑥ 節）；iOS 那條是真的要寫程式的。
2. **先上 Android、後上 iOS。** Android 卡的是「12 位測試者連續 14 天」的等待（花錢買不到），iOS 卡的是審查員（4.2、4.8、3.1.1）。兩條可以平行跑。
3. **★ 最大的變數是「App 裡要不要賣訂閱」。** 兩家商店都規定：**在 App 裡賣數位訂閱就必須用商店自己的金流**（Apple IAP、Google Play Billing），
   而且**台灣不在 Google「使用者選擇帳單」或 Apple「外部付款連結」的開放地區**（信心：中，第 ③ 節）。
   我們現在的銀行轉帳、綠界結帳頁**在 App 裡出現就是違規**。
4. **〔判斷〕第一版建議：App 只做免費版，App 內看不到價格、方案、結帳、任何「去網站付費」的字與連結。** 付費仍然只在網站上賣。
   第二版再決定要不要接 IAP（抽 15%，299 元實收約 254 元）。第 ⑧ 節有三個選項的比較。
5. **⚠ 這代表網站要能分辨「我現在是在 App 裡」並把付費相關畫面藏起來** —— 那是 `site/**` 的改動，這批**沒有做**（任務限制），列為下一步第一件事。
6. **Apple 4.2（最低功能性）一定會被拿來檢查。** 只包網站幾乎必退；推播、Face ID、分享這種「加一兩個原生零件」也有被判不夠的案例（信心：中）。
   〔判斷〕最有說服力的組合是：**價格／族群警示推播（真的用到我們的資料）＋ 主畫面小工具（今日資金流向前 3 名）＋ 原生分頁列 ＋ 離線可開**。
7. **Apple 4.8：我們只有 Google 登入 → iOS 版一定要加「Sign in with Apple」（或同等級的隱私登入）。** 這要動 Worker（`workers/account-api`）。
8. **Google 登入在 iOS 的 WebView 裡會被 Google 擋掉**（`disallowed_useragent`，2021 起，信心：高）。iOS 版的登入要改走系統瀏覽器（ASWebAuthenticationSession）再跳回 App。Android TWA 跑在 Chrome 裡，不受影響。
9. **刪除帳號：已經有**（桌機與手機帳號選單、`POST /v1/delete`、輸入「刪除」確認、立即刪除）。符合 Apple 5.1.1(v)。加了 Sign in with Apple 之後，刪帳號時要多呼叫 Apple 的撤銷權杖 API。
10. **金融類審查：Apple 3.2.1(viii) 規定「金融交易、投資、資金管理」App 要由金融機構提交**；5.1.1(ix) 規定高度監管領域應由法人提交。
    我們不交易、不碰錢，定位寫成「行情與產業資訊工具」，但**全站還有「進場」35 處、「買進」9 處、「目標價」9 處、「今日關注」48 處**這類字（`grep` 實數）。
    〔判斷〕App 送審前要先把審查員第一眼會看到的那幾頁改成資訊工具語氣（第 ④ 節）。
11. **費用**：Google US$25 一次、Apple US$99／年，合計第一年約 **NT$4,000**。不需要買 Mac（iOS 在 GitHub Actions 的 macOS 機器上建置，public repo 免費）。
12. **時程**：**第一版能上架 ≈ Android 4～6 週、iOS 5～8 週**（日曆時間）；**完整體驗（IAP、推播警示、小工具）再 4～8 週**。第 ⑤ 節有每一段。

---

## ① 現況：我們手上已經有什麼（今天在 repo 裡讀到、驗到的）

| 項目 | 狀態 | 依據 |
|---|---|---|
| Web App Manifest | ✅ 已有：`site/manifest.webmanifest`，名稱／短名「哩股哩股」、`display: standalone`、`start_url: ./index.html`、192／512 一般與 maskable 圖示、深色主題色 `#070b16` | 讀檔 |
| Service Worker | ✅ 已有：`site/sw.js`，**`data/**` 與所有 `.json` 完全不碰**、導覽網路優先、版號跟著 `tw:build` 換 | 讀檔 |
| Chrome 可安裝檢查 | ✅ 今天在 360／390／430 三種手機寬度都 0 錯誤（`Page.getInstallabilityErrors`） | 第 ⑥ 節驗收段 |
| 自有網域 | ✅ `liguligu-puipui.com`（GitHub Pages，前面是 Cloudflare） | 任務說明 |
| 登入 | Google OAuth，**伺服器端整頁轉址**（`workers/account-api/worker.js` 的 `GOOGLE_AUTH`），不是彈窗 | 讀檔 |
| 刪除帳號 | ✅ 桌機 `site/account.js`、手機 `site/acctm4.js`；`POST /v1/delete`；訂單只斷開 uid 保留對帳（`workers/account-api/pay.js:1161`） | 讀檔 |
| 收費 | 月 299／549（年 2,990／5,268），銀行轉帳已開、綠界審核中（`site/checkout.js:181`） | 讀檔 |
| 免責聲明 | ✅ `site/legal.js`：「不提供投資建議、不推介任何有價證券、不代客操作……付費方案所提供者為工具與功能之使用權」 | 讀檔 |
| 使用行為紀錄 | 有自家的 `/v1/track/batch`（頁面瀏覽／互動，每日換一組裝置代碼） | 讀檔 —— **資料安全表單要據實填** |

---

## ② 包裝路線：每個商店選一條

### Android：TWA（Bubblewrap／PWABuilder） vs Capacitor

| | **TWA（Bubblewrap）** ← 建議 | Capacitor |
|---|---|---|
| 本質 | 用使用者手機上的 **Chrome** 全螢幕開我們的網站，沒有網址列 | 自帶一個 Android WebView，網站可以打包進 App 或指到線上網址 |
| 要寫的程式 | **幾乎 0**（設定檔＋簽章） | 一個 Android 專案＋外掛 |
| 網站更新 | 推 main 就更新，**不用重新送審** | 若網站打包進 App，每次改版都要送審；指到線上網址則同 TWA |
| Google 登入 | ✅ 照常（就是 Chrome） | ❌ WebView 會被 Google 擋，要改原生登入外掛 |
| 推播 | Web Push 透過 Chrome 的通知委派（我們目前沒有 Web Push） | 原生 FCM 外掛 |
| Play Billing | 可以：Bubblewrap 有 `playBilling` 功能＋網頁的 Digital Goods API | 原生外掛 |
| 驗證網站所有權 | 要放 `/.well-known/assetlinks.json`（**已做好範本**） | 不需要 |
| Google 的態度 | 官方支援的做法（Chrome 團隊的工具） | 一般 App |
| 缺點 | 手機沒有 Chrome（或太舊）時退回 Custom Tab，會看到網址列 | 兩份程式碼要維護 |

PWABuilder 的 Android 打包**底層就是 Bubblewrap**，差別只在它是網頁介面。我們不用本機操作，所以直接用 Bubblewrap CLI 在 GitHub Actions 跑（第 ⑥ 節）。

### iOS：Capacitor／WKWebView vs PWABuilder iOS

| | **Capacitor** ← 建議 | PWABuilder iOS 套件 |
|---|---|---|
| 本質 | WKWebView ＋ 成熟的外掛生態（推播、生物辨識、分享、IAP、小工具橋接） | 產生一個 Swift 的 WKWebView 專案，指到線上網址 |
| 4.2 的應對能力 | **強**：要加原生功能都有現成外掛或可以寫 Swift 外掛 | 弱：只提供基本殼，原生功能要自己改 Swift |
| 維護 | npm 套件、文件多 | 產生一次之後就是自己的 Xcode 專案 |
| 建置 | 都要 macOS ＋ Xcode（用 GitHub Actions macOS runner） | 同左 |

〔判斷〕iOS 一定要加原生層才過得了 4.2，PWABuilder iOS 只省了第一天的工，之後每一項原生功能都比 Capacitor 難做，所以選 Capacitor。

### 為什麼不原生重寫
一個人維護的網站已經有幾十支前端檔、上百個圖表與互動；重寫成 Swift＋Kotlin 等於**同一套功能維護三份**，
而每天盤後的資料、圖表規則（紅漲綠跌、KD/RSI 口徑）都要再對一次。商店要的「原生價值」只需要在殼上補幾項，不需要整個重寫。

---

## ③ 商店規則（2026 年 10 月查）

### Google Play

| 題目 | 結論 | 信心 | 來源 |
|---|---|---|---|
| 開發者帳號費 | **US$25 一次付清**（約 NT$800），沒有年費 | 中高（第三方指南一致，舊文件也查過；本次沒撈到 Google 官方頁寫金額） | [G6][G7] |
| 身分驗證 | 帳號資料要驗證才能發布；聯絡資訊用一次性密碼驗證；**法定名稱、地址、聯絡方式會公開顯示** | 高 | [G6] |
| 收費 App 的地址公開 | **有付費下載或 App 內購（商家帳號）時，必須在 Play 上顯示完整地址**，取自 Google 付款資料 | 高 | [G8] |
| 組織帳號 | **必須有 D-U-N-S 編號**（免費，最長約 30 天），Google 不給豁免 | 高 | [G6] |
| ★ 新個人帳號的封閉測試 | **2023-11-13 之後開的個人帳號：至少 12 位測試者、連續 14 天加入封閉測試**，才能申請正式版；在那之前「正式版」「預先註冊」都鎖住。組織帳號不受此限 | 高（官方說明頁） | [G1][G2] |
| 測試人數若中途掉到 12 以下會不會重算 | 第三方說會從第 0 天重算；官方頁沒這樣寫 | **未確認** | [G3] |
| 目標 API 等級 | **2026-08-31 起，新 App 與更新要 target Android 16（API 36）**；可申請延到 2026-11-01 | 高 | [G4][G5] |
| 我們的工具符不符合 | Bubblewrap 1.27.0 的範本是 `targetSdkVersion 36`／`compileSdkVersion 36`（我讀了套件原始碼並實際產生過專案） | 高 | 實測 |
| 資料安全表單（Data safety） | 必填，**要跟隱私權政策一致**；不一致會被退 | 高 | 舊文件 4-7 |
| 財務功能聲明 | **所有 App 都要填**（沒有財務功能也要聲明「沒有」）；包含封閉測試軌道。含「投資相關、個人化建議」的 App 要遵守目標國家的在地規定（例如必要揭露） | 高 | [G9][G10] |
| 台灣投資資訊 App 的特別要求 | Google 有針對某些國家列出要證照的金融類別（例如個人貸款）；**我查不到台灣「投資資訊」需要上傳證照的清單** | **未確認** | [G9] |
| 數位訂閱的金流 | **App 內賣數位內容／訂閱必須用 Google Play Billing**；App 內不准連到其他付款方式，也不准用文字鼓勵去外面買。可以放「帳號管理、隱私權政策、客服」這種行政連結，但那頁不能再導到付款 | 高 | [G11] |
| 台灣能不能用其他金流 | 2026-06 新的「billing choice」計畫只開放**英國、歐洲經濟區、美國**；之前「使用者選擇帳單」試行地區是 EEA、日本、澳洲、印度、印尼。**兩次都沒有台灣** | 中（官方部落格摘要；但部落格底部的全球時程表我讀不到） | [G12][G13][G14] |
| Play 抽成 | 訂閱 **15%**（第一天起） | 中 | 舊文件 5-1 |

### Apple

| 題目 | 結論 | 信心 | 來源 |
|---|---|---|---|
| Developer Program 年費 | **US$99／年**，「依地區以當地貨幣顯示」。台灣實際新台幣金額我查不到（網路傳 NT$3,400，**未確認**） | 高（US$99）／未確認（NT$ 金額） | [A1][A2] |
| 個人 vs 組織 | 有限公司／股份有限公司等法人**不能用個人身分註冊**；**獨資或一人公司必須用個人身分**。組織要 D-U-N-S（免費，最多 5 個工作天），不接受營業名稱、分公司 | 高（Apple 台灣說明頁） | [A1][A3] |
| 個人帳號的顯示名稱 | 個人帳號在 App Store 顯示的是本人姓名 | 中 | 舊文件 ③ |
| ★ 4.2 最低功能性 | 條文：「App 應包含讓它超越重新包裝網站的功能、內容與介面」；不夠有用、獨特或像 App 的不收 | 高（多處引用同一句） | [A4][A5] |
| 4.2 實際退件 | 有 Capacitor App 被退，審查員明說「推播、定位、分享**本身不夠**」；另一案加了自寫 Swift 外掛仍因「核心流程靠第三方網頁」被退 | 中（開發者論壇） | [A5][A6] |
| 4.2 常見被接受的方向 | 原生導覽（分頁列）、離線可用、推播管理、生物辨識、原生分享、與系統整合（小工具） | 低～中（廠商部落格） | [A7][A8] |
| ★ 3.1.1 內購 | App 內解鎖功能、訂閱**必須用 IAP**；不可在 App 內放其他購買機制或導購 | 高 | [A9] |
| 3.1.3(b) 多平台服務 | 可以讓使用者在 App 裡使用在別處買的訂閱，**但前提是同樣的東西在 App 裡也有 IAP 可買**；有案例「只在網站賣、App 裡不賣」被以 3.1.1 退件 | 中 | [A9] |
| 3.1.3(f) 免費獨立 App | 「作為付費網頁工具之免費獨立配套」的免費 App 可以不用 IAP，前提是**App 內沒有購買、也沒有導向外部購買的呼籲**；條文舉例是 VoIP、雲端儲存、Email、主機 —— 是不是只限這幾類**沒有官方答案** | 中（條文）／低（適用範圍） | [A10] |
| 閱讀器 App 外部連結權限 | 只給「雜誌、報紙、書籍、音訊、音樂、影片」為主要功能的 App；用了就不能有 IAP。**我們不是這類** | 高 | [A11] |
| 台灣有沒有外部付款例外 | 搜到的放寬都是歐盟、美國（Epic 禁制令）、日本；**沒有台灣** | 中（找不到≠沒有，但三組關鍵字都沒有） | [A12][A13] |
| 小型企業方案 | 年收入 < US$100 萬可申請 **15%** 抽成（要主動申請） | 高 | 舊文件 5-1 |
| ★ 4.8 登入服務 | 主要帳號用第三方登入（我們的 Google）時，**必須另外提供一個同等的登入選項**：只蒐集姓名與 email、可以隱藏 email、不拿互動資料做廣告。Apple 回覆裡點名 Sign in with Apple 符合 | 中高（論壇＋Apple 回覆一致；新舊版條文措辭不同） | [A14][A15] |
| ★ 5.1.1(v) 刪除帳號 | 能建帳號就要能**在 App 內**發起刪除；只停用不算；非高度監管行業不准要求打電話／寄信才能刪 | 高（Apple 說明頁） | [A16] |
| 5.1.1(ix) 高度監管領域 | 銀行與金融服務等高度監管領域，應由提供服務的**法人**提交，不是個人開發者 | 中（舊文件查到；本次是刪帳號說明頁順帶提到這條） | [A16] |
| ★ 3.2.1(viii) 金融 App | 「用於金融交易、投資或資金管理的 App，應由執行這些服務的金融機構提交」；2021 年拿掉了「使用金融機構公開 API」的替代路徑；論壇回報實務上主要用在借貸 App | 中 | [A17][A18] |
| 「5.2」 | 5.2 是**智慧財產權**（不是金融條文）：審查員可以問我們「資料有沒有授權」。證交所／櫃買 OpenAPI 是政府開放資料；**Yahoo 分 K 明文禁止商業用途**（舊文件 4-6） | 中 | 舊文件 4-6 |
| 隱私權營養標示 | 每個 App 都要填（App Store Connect → App 隱私權）；要跟實際蒐集一致 | 高 | 舊文件 4-7 |
| 截圖尺寸 | iPhone 6.9 吋 **1320×2868**（或 1290×2796）、iPad 13 吋 **2064×2752**（App 支援 iPad 才要）；Apple 會從最大尺寸自動縮給小螢幕 | 中（廠商整理，非 Apple 原頁） | [A19] |
| 2026 年的條文異動 | 2026-06-09 與 2026-10-16 有改版（低品質 App、UGC、提交清單格式）；沒看到跟我們直接相關的金融或 4.2 改動 | 低（第三方追蹤站） | [A20] |

### 台灣法規角度

- 〔事實〕《證券投資信託及顧問法》：未經許可、以收取報酬方式對不特定人提供證券分析意見或推介建議，屬非法經營投顧業務（舊文件 4-1、`docs/product_strategy.md`，信心：高）。
- 〔事實〕金管會的查處實務是透過平台通報下架詐騙與非法招攬（截至某年 5 月 19 日通報 Google／Meta 1,720 件、已下架 1,363 件）；常見態樣是「推介飆股」「保證獲利」（信心：中）[T1]。
- 〔判斷〕我們有收費，所以「報酬」要件存在；能站得住的理由是「付費買的是工具與功能使用權，不是推介的對價」（`site/legal.js` 已這樣寫）。
  **商店審查員看不到這層論證，只看畫面**。所以 App 版要比網站更保守：審查員一定會點開的頁面（總覽、個股頁、今日關注）不能出現「進場」「買進」「目標價」「推薦」這種字。
- 〔判斷〕`docs/launch_standard.md` 第一節「B 個股評分／排行先免費、C 明確買賣建議永遠不做」這條在 App 上一樣適用。

---

## ④ 送審前網站要改的字（下一步，這批沒動 `site/**`）

全站實數（`grep -o` 計次，2026-10-22）：「進場」35、「推薦」10、「買進」9、「賣出」38、「目標價」9、「今日關注」48、「選股」65。
很多是說明文字或圖例（例如「賣出」在籌碼的「外資賣出」是事實描述，沒問題）。要處理的是**當成建議語氣出現**的地方：

1. 「進場時機」→「技術面條件」；「目標價」→「計算參考價位（非建議）」或乾脆在 App 版藏起來。
2. 「今日關注」→「今日符合條件」，卡片固定一行「依公開資料計算之條件篩選結果，不是推薦」（B 類頁頂那行小字已經有了，確認 App 版看得到）。
3. 首次打開 App 的免責聲明（`legal_config.js` 的法律同意橫幅，上架標準第 9 條「上架再開」）**送審前一定要打開**。

---

## ⑤ 步驟清單：誰做什麼、多少錢、多久、誰卡誰

匯率以 US$1 ≈ NT$32 估。「日曆時間」是含等待的實際天數。

### Android（Google Play）

| # | Andy 要做的 | Claude 可以做的 | 費用 | 日曆時間 | 卡住誰 |
|---|---|---|---|---|---|
| A1 | 決定**個人或組織**帳號（見文末問題 1）。組織要先申請 D-U-N-S | 準備 D-U-N-S 申請所需資料清單 | D-U-N-S 免費 | 組織：D-U-N-S 最長約 30 天 | 卡 A2 |
| A2 | 開 Google Play 開發者帳號、付費、完成身分驗證（身分證件、可能要用 Android 手機驗證） | — | **US$25（約 NT$800）一次** | 驗證 1～3 天（**未確認**） | 卡 A5 |
| A3 | 產生上傳金鑰、放三個 Secret＋一個變數（照 `app/android/README.md`，約 20 分鐘）；**另外備份金鑰** | 寫好步驟（已完成） | 0 | 半天 | 卡 A4 |
| A4 | 按一下「Run workflow」 | 打包工作流（**已完成，預設關閉**） | 0（Actions 對 public repo 免費） | 15～30 分鐘 | 卡 A5 |
| A5 | 在 Play Console 建 App、上傳 AAB 到**封閉測試** | 準備商店文案、說明、截圖（1080×1920 以上手機截圖 2～8 張、512×512 圖示、1024×500 主題圖）、資料安全表單草稿、財務功能聲明草稿 | 0 | 1～2 天 | 卡 A6 |
| A6 | 把 Play 的「應用程式簽署金鑰 SHA-256」貼給 Claude（不是秘密，可以公開） | 填進 `site/.well-known/assetlinks.json`、推上線、驗證 200 | 0 | 半天 | 不填就會有網址列 |
| A7 | **找 12 位測試者**（要有 Google 帳號與 Android 手機），請他們加入並安裝，**連續 14 天不退出**；個人帳號才需要 | 準備邀請文案與加入步驟 | 0 | **14 天以上（最長的一段）** | 卡 A8 |
| A8 | 在 Play Console 申請正式版存取權（會問測試情形） | 幫忙寫回答 | 0 | 審核約 7 天（舊文件，信心：中） | 卡 A9 |
| A9 | 送正式版審查 | — | 0 | 1～7 天 | — |
| A10 | （先做第 ④ 節的字與「App 內藏付費畫面」之後才送）確認畫面 | 改網站：偵測「在 App 裡」→ 藏價格／方案／結帳／升級按鈕 | 0 | 2～3 天工 | **卡 A5 送審** |

**Android 第一版合計：NT$800；日曆 4～6 週**（個人帳號；組織帳號省掉 A7，約 2～3 週，但 D-U-N-S 可能多等）。

### iOS（App Store）

| # | Andy 要做的 | Claude 可以做的 | 費用 | 日曆時間 | 卡住誰 |
|---|---|---|---|---|---|
| I1 | 決定個人或組織（**獨資行號只能個人**；有限公司才能組織，要 D-U-N-S） | — | 0 | 組織 D-U-N-S ≤ 5 個工作天＋Apple 審核 | 卡 I2 |
| I2 | 加入 Apple Developer Program（Apple ID 開兩步驟驗證、付費） | — | **US$99／年（約 NT$3,200，台灣實價未確認）** | 個人 1～2 天；組織 1～2 週（信心：低） | 卡 I5 |
| I3 | 在 App Store Connect 建 API 金鑰（.p8）放 GitHub Secrets，讓 Actions 能簽章上傳 | 寫逐步點擊說明 | 0 | 半天 | 卡 I5 |
| I4 | — | 建 Capacitor 專案（`app/ios/`）、GitHub Actions macOS 建置（public repo 免費） | 0 | 3～5 天工 | 卡 I5 |
| I5 | — | **原生層**：推播（價格／族群警示，要 Worker 送 APNs）、主畫面小工具、原生分頁列、離線頁 | 0（APNs 含在年費） | 2～3 週工 | 卡 I7 |
| I6 | 在 Apple 後台開 Sign in with Apple 的 Service ID 與金鑰 | Worker 加 Apple 登入、iOS 登入改走 ASWebAuthenticationSession、刪帳號時撤銷 Apple 權杖 | 0 | 3～5 天工 | **卡 I7（4.8 必退）** |
| I7 | 在自己的 iPhone 裝 **TestFlight** 試用（免費，不用 Mac） | 傳 TestFlight 版 | 0 | 1～3 天 | 卡 I8 |
| I8 | 填隱私權營養標示、年齡分級、出口合規（只有 HTTPS 可選豁免） | 準備每一格的答案草稿、截圖（6.9 吋 1320×2868）、給審查員的說明（不交易、不碰錢、資料來源、測試帳號） | 0 | 1 天 | 卡 I9 |
| I9 | 送審；被退時把退件訊息貼給 Claude | 依退件理由改、寫申覆 | 0 | 每輪 1～3 天，**預期 1～3 輪** | — |

**iOS 第一版合計：約 NT$3,200／年；日曆 5～8 週**（可以跟 Android 的 14 天測試期平行）。

### 選購（不是必要）

| 項目 | 何時需要 | 估價 |
|---|---|---|
| 二手或入門 Android 手機 | Andy 手上沒有 Android 時（驗證帳號、自己測） | NT$3,000～5,000 |
| Mac | **不需要**（GitHub Actions macOS 建置＋TestFlight 測試）。只有想在本機用 Xcode 除錯才要 | Mac mini 約 NT$19,000 起（未確認當前售價） |
| 雲端 Mac（MacinCloud 等） | 同上，不需要 | 約 US$25～50／月（**未確認**） |
| 律師諮詢 | 上架標準第 4 條本來就要做；App 版的付費設計可以一起問 | NT$3,000～10,000（〔判斷〕估） |

### 里程碑

| 里程碑 | 內容 | 開發工 | 日曆時間 |
|---|---|---|---|
| **第一版能上架** | Android TWA ＋ iOS Capacitor（推播警示＋小工具＋Apple 登入），**App 內只有免費功能、沒有任何付費入口** | Claude 約 4～5 週工 | Android 4～6 週、iOS 5～8 週 |
| **完整體驗** | App 內購（Apple IAP＋Play Billing）、Worker 驗證收據並跟網站會員同步權限、更多警示類型 | 再 3～5 週工 | 再 4～8 週（含兩家內購審查） |

---

## ⑥ 這批已經做好的（repo 端，分支 `appprep`）

| 檔案 | 內容 |
|---|---|
| `app/android/twa-manifest.json` | Bubblewrap 設定。套件名稱提案 **`com.liguligu.app`**、網域 `liguligu-puipui.com`、啟動頁 `/index.html`、圖示用 `brand/icon-512.png` 與 maskable、深色 `#070B16`、三個捷徑（資金／產業／題材）、`minSdkVersion 23`。用 `@bubblewrap/core@1.27.0` 的 `TwaManifest.validate()` 驗過 0 錯誤，並實際產生過 Android 專案（`targetSdkVersion 36`、`applicationId com.liguligu.app`） |
| `app/android/README.md` | 金鑰怎麼產生、怎麼放 Secrets、怎麼建置、assetlinks 怎麼填 |
| `app/android/.gitignore`、根目錄 `.gitignore` | 擋 `*.keystore`、`*.jks` |
| `site/.well-known/assetlinks.json` | Digital Asset Links 範本，格式跟 Bubblewrap 自己產生的一致；指紋是 `REPLACE_WITH_...` 佔位字 |
| `site/.nojekyll` | 保險用（見下） |
| `.github/workflows/android-twa.yml` | **手動觸發**；沒設變數 `ANDROID_TWA_ENABLED=true` 就整個略過；缺 Secret 第一步就停。產物只放 Artifacts 7 天、不回寫 repo；建完印出上傳金鑰 SHA-256 |
| `scripts/uitest_sections/20261022_pwa_install.py` | 驗收段「PWA可安裝1022」 |

**沒有改**：`site/manifest.webmanifest`、`site/sw.js`、`site/index.html` —— 檢查後都已符合可安裝條件，不需要動；預覽版橫幅、版號徽章完全沒碰。

**`.well-known` 會不會被 GitHub Pages 丟掉？** 我把 `actions/upload-pages-artifact@v3` 的原始碼拉下來看：打包只排除 `.git` 與 `.github`，**`.well-known` 會被帶上**。
部署走 Actions（不是分支部署），不跑 Jekyll，所以 `.nojekyll` 其實不需要，放著只是保險。
⚠ **將來把 upload-pages-artifact 升到 v4 時要加 `include-hidden-files: true`**，否則點開頭的資料夾會被排除、App 會突然冒出網址列（v4 改了預設，信心：中 [G15]）。
⚠ Cloudflare 若開 Bot Fight Mode 或挑戰頁，要對 `/.well-known/*` 放行；檔案必須直接回 200、不能轉址。
⚠ SW 對所有 `.json` 都不介入，所以 `assetlinks.json` 不會被快取住舊的指紋。

**驗收**：「PWA可安裝1022」在 360／390／430（is_mobile、has_touch）各跑一次，量 ① Chrome 可安裝檢查 0 錯誤 ② manifest 解析 0 錯誤、名稱／顯示模式／圖示齊 ③ SW 接手 ④ 用手指點分頁換頁後 SW 仍接手 ⑤ 快取裡沒有任何 `data/` 或 `.json` ⑥ `/.well-known/assetlinks.json` 回 200、套件名稱正確 ⑦ 無頁面例外；另外用**一般（非無痕）設定檔**在 390 再量一次可安裝檢查 0 錯誤、`beforeinstallprompt` 真的觸發。
2026-10-22 結果：**0 個問題（25 秒）**。⚠ Playwright 一般的測試視窗是無痕模式，Chrome 會固定回 `in-incognito`，那是測試環境不是網站問題，所以三種寬度那一輪把它濾掉、另用一般設定檔驗真的 0 錯誤。
桌機守門1008：**0 個問題（314 秒）**。

**沒驗到的**：Android AAB 的實際建置（這個容器沒有 Android SDK，而且沒有金鑰）——工作流寫好了但**沒有在 Actions 上跑過**，第一次跑時可能要修一兩個小地方（例如 SDK 授權）。

---

## ⑦ 風險表

| # | 風險 | 機率 | 影響 | 緩解 |
|---|---|---|---|---|
| R1 | **Apple 4.2 以「重新包裝的網站」退件** | 只包網站：高（〔判斷〕約 90%）；加了推播警示＋小工具＋原生分頁列＋離線：中（約 25～40%） | 卡住 iOS | 原生功能要**用到我們自己的資料**（警示、小工具），不要只是放推播權限；給審查員的說明寫清楚；截圖秀資訊密度 |
| R2 | **App 內出現網站付費入口被判違反 3.1.1／Play 付款政策** | 不處理：**幾乎一定**（網站到處有升級鈕） | 退件，嚴重可能停權 | 網站偵測 App 環境（TWA 的 `document.referrer` 是 `android-app://com.liguligu.app`；iOS 由殼注入旗標）→ 藏起價格、方案、結帳、升級按鈕與「去網站付費」字樣（第 ④ 節之後的第一件事） |
| R3 | **付費會員在 App 裡看得到付費功能（網站買的）被判 3.1.3(b) 沒有 IAP** | 中 | iOS 退件 | 選項 A（App 只給免費功能）完全避開；選項 B 靠 3.1.3(f) 申辯，有不確定性；選項 C 接 IAP（第 ⑧ 節） |
| R4 | **4.8 沒有 Sign in with Apple 被退** | 不加：高 | iOS 退件 | iOS 版加 Apple 登入（I6） |
| R5 | Google 登入在 iOS WebView 被擋（使用者登不進去） | 不處理：**一定**（Google 2021 起的政策） | 審查員也登不進去 → 退件 | 登入改走 ASWebAuthenticationSession＋Universal Link 回 App |
| R6 | **3.2.1(viii)／5.1.1(ix) 金融類要由金融機構／法人提交** | 中（實務多用在借貸，但我們有「進場」「目標價」字樣） | iOS 退件，個人帳號可能根本過不了 | 改字（第 ④ 節）；給審查員說明「資訊工具、不交易、不碰錢」；若被以此退件，改用組織帳號重送（要有限公司） |
| R7 | 12 人 × 14 天湊不到或中途有人退出 | 中 | Android 晚 2～4 週 | 先找 15～20 人留餘裕；或用組織帳號（免此規定）；**不要買測試者服務**（Google 會查真實使用） |
| R8 | Play 財務功能聲明被判不實 | 低～中 | Android 退件 | 勾「投資資訊／市場資料」這類、不勾交易或顧問；描述寫清楚不交易 |
| R9 | 資料授權被問（5.2／Play 智慧財產） | 低～中（收費 App 較高） | 退件或下架 | 收費前拔掉 Yahoo 分 K（舊文件 4-6）；說明頁列出資料來源與授權 |
| R10 | GitHub Pages 使用條款不允許商業站 | 中（現在已經在收費） | 網站本身的風險，App 跟著受影響 | `pages.yml` 已並行部署到 Cloudflare Pages（DECISIONS #339），網域切到 Cloudflare Pages 即可 |
| R11 | 上傳金鑰遺失 | 低 | 無法更新 App | Play App Signing（Google 保管正式簽署金鑰）＋上傳金鑰另外備份 |
| R12 | assetlinks 指紋填錯或被轉址 | 中（最常見的 TWA 問題） | App 頂端出現網址列（不至於退件，但難看） | 兩把指紋都填；部署後實測 200；升 v4 記得加 `include-hidden-files` |
| R13 | 個人帳號公開本名／地址 | 一定（收費 App 必須顯示地址） | 隱私 | 用組織帳號；或第一版不在 App 內收費（不是商家帳號就不用公開地址，信心：中） |

---

## ⑧ 付費方案怎麼辦：三個選項

| | A. App 只有免費版（**建議第一版**） | B. App 不賣，但網站付費會員登入後可用 | C. 接 App 內購 |
|---|---|---|---|
| 做法 | App 內看不到價格、方案、結帳、升級鈕；付費功能在 App 裡不出現 | 同 A，但付費會員登入後解鎖付費功能 | Apple IAP＋Play Billing，Worker 驗證收據、跟網站會員權限同步 |
| Apple | 最安全 | 靠 3.1.3(f)「免費配套 App」申辯，**有退件風險**（3.1.3(b) 要求同時有 IAP） | 合規 |
| Google | 安全 | 一般可以（只要 App 內沒有購買流程與導購），信心：中 | 合規 |
| 收入 | 不變（網站照收） | 不變 | 299 月費：Apple 小型企業 15% → 實收約 **254**；Google 15% → 約 **254**；網站綠界約 3% → 約 **290** |
| 工 | 2～3 天（藏畫面） | 同 A | 3～5 週（兩家內購、收據驗證、退款與續訂同步、對帳） |
| 附帶 | — | — | Google 收費 App 要公開地址；投顧法「報酬」與 App 商店收款綁在一起 |

〔判斷〕先 A，上架後看 App 的使用量再決定 C。B 看起來兩全，但 iOS 審查的不確定性最大，**不建議當第一版**。

### 原生價值候選（給 4.2 用，依「有用程度」排）

1. **價格／族群資金警示推播**（例如「半導體族群資金由流出轉流入」「自選股跌破設定價」）——用到我們自己的資料，最有說服力。要 Worker 排程＋APNs／FCM。
2. **主畫面小工具**：今日資金流向前 3 族群、自選清單漲跌。要原生 Swift（WidgetKit）。
3. **原生分頁列**＋原生返回手勢。
4. **離線打得開**：最後一次的盤後摘要存一份在 App 裡，沒網路也看得到（標明資料日期）。⚠ 跟「不准看到昨天的數字」那條要一起設計：一定要清楚標日期。
5. Face ID 鎖自選清單（加分項，單獨不夠）。

---

## ⑨ 只有 Andy 能回答的問題

1. **個人還是組織帳號？** 名下有沒有**有限公司**？（獨資行號在 Apple 只能用個人；Google 組織帳號要 D-U-N-S、但免 12 人×14 天、也不會公開個人地址。）
2. **App 裡要不要賣訂閱？** 我建議第一版不賣（選項 A）；如果要賣，第一版就要做 IAP，iOS 多 3～5 週。
3. **套件名稱 `com.liguligu.app` 可以嗎？** 第一次上傳後永遠不能改（App 名稱可以改）。
4. **找得到 12 位以上有 Android 手機的測試者嗎？**（個人帳號才需要）
5. **你自己有沒有 Android 手機與 iPhone 可以測？**
6. **iOS 的原生功能要做哪幾個？** 我建議「推播警示＋小工具＋原生分頁列＋離線」四個一起做；只做推播被退的機率高。
7. **送審前要不要先找律師**看 App 版的付費設計與字眼（上架標準第 4 條本來就要做）。

---

## 附：來源清單

Google Play
- [G1] Google Play Console 說明：新個人帳號的測試要求 — https://support.google.com/googleplay/android-developer/answer/14151465
- [G2] Android Authority：Play 測試要求由 20 人降為 12 人 — https://androidauthority.com/google-play-app-testing-requirement-3510580
- [G3] Choicely：12 位測試者規則整理 — https://www.choicely.com/blog/google-play-12-tester-rule
- [G4] Android Developers：目標 API 等級要求 — https://developer.android.com/google/play/requirements/target-sdk
- [G5] Play Console 說明：目標 API 等級 — https://support.google.com/googleplay/android-developer/answer/11926878
- [G6] Play Console 說明：建立個人開發者帳號／D-U-N-S — https://support.google.com/googleplay/android-developer/answer/13628312
- [G7] Tapcart：建立 Google Play 開發者帳號 — https://help.tapcart.com/en/articles/13800708-how-to-create-a-google-play-developer-account
- [G8] Play Console 說明：開發者地址公開 — https://support.google.com/googleplay/android-developer/answer/13634081
- [G9] Play Console 說明：財務功能聲明 — https://support.google.com/googleplay/android-developer/answer/13849271
- [G10] Play 政策：金融服務 — https://support.google.com/googleplay/android-developer/answer/9876821
- [G11] Play 政策：付款 — https://support.google.com/googleplay/android-developer/answer/10281818 、https://play.google.com/about/monetization-ads/payments
- [G12] Android Developers Blog（2026-06）：billing choice — https://android-developers.googleblog.com/2026/06/play-expanded-billing.html
- [G13] Play Console 說明：billing choice 開放市場 — https://support.google.com/googleplay/android-developer/answer/17161464
- [G14] iThome：使用者選擇帳單試行地區 — https://www.ithome.com.tw/news/152916
- [G15] upload-pages-artifact／upload-artifact 隱藏檔預設 — https://zenn.dev/kou_pg_0131/articles/gh-actions-upload-artifact-hidden-files （v3 行為我直接讀 action.yml 確認）
- Bubblewrap：https://github.com/GoogleChromeLabs/bubblewrap ；TWA 指紋：https://developer.chrome.com/docs/android/trusted-web-activity/android-for-web-devs

Apple
- [A1] Apple 開發者（台灣）：計畫註冊 — https://developer.apple.com/tw/help/account/membership/program-enrollment
- [A2] Apple 開發者（台灣）：年費豁免 — https://developer.apple.com/tw/help/account/membership/fee-waivers
- [A3] Apple 開發者（台灣）：D-U-N-S — https://developer.apple.com/tw/support/D-U-N-S/
- [A4] MobiLoud：WebView 包裝與審查準則 — https://www.mobiloud.com/blog/app-store-review-guidelines-webview-wrapper
- [A5] Apple 開發者論壇：4.2 退件（推播／定位／分享不夠） — https://developer.apple.com/forums/thread/812889
- [A6] Apple 開發者論壇：4.2 退件討論 — https://developer.apple.com/forums/thread/816069
- [A7] Capgo：把網站 App 上架 App Store — https://capgo.app/blog/how-to-put-a-web-app-on-the-app-store/
- [A8] technetexperts：4.2 最低功能性 — https://www.technetexperts.com/guideline-4-2-minimum-functionality/
- [A9] Apple 開發者論壇：3.1.1 與 3.1.3(b) — https://developer.apple.com/forums/thread/740710 、https://developer.apple.com/forums/thread/811018
- [A10] Apple 開發者論壇：3.1.3(f) — https://developer.apple.com/forums/thread/781935 ；Michael Tsai：閱讀器 App 新準則 — https://mjtsai.com/blog/2020/09/11/new-apple-store-guidelines-for-reader-apps
- [A11] Apple：閱讀器 App 外部連結 — https://developer.apple.com/support/reader-apps
- [A12] 數位時代：媒體類 App 免抽成 — https://www.bnext.com.tw/article/64853/apple-media-app-tax-reduce-
- [A13] 鉅亨：美國外部支付手續費裁定 — https://m.cnyes.com/news/id/6011656
- [A14] Apple 開發者論壇：4.8 登入服務 — https://developer.apple.com/forums/thread/762647 、https://developer.apple.com/forums/thread/765145
- [A15] OpenStreetMap 開發信（2025-05 Apple 審查回覆） — https://lists.openstreetmap.org/pipermail/rails-dev/2025-May/040605.html
- [A16] Apple App Review 說明：5.1.1(v) 刪除帳號 — https://developer.apple.com/help/app-review/guideline-reference/5-1-1-account-deletion
- [A17] Apple 開發者論壇：3.2.1(viii) — https://developer.apple.com/forums/thread/704470 、https://developer.apple.com/forums/thread/775803
- [A18] IT Finanzmagazin：2021 拿掉公開 API 路徑 — https://www.it-finanzmagazin.de/open-banking-zieht-apple-den-stecker-fuer-psd2-co-117334/
- [A19] 截圖尺寸整理 — https://screenhance.com/blog/app-store-screenshot-dimensions-2026
- [A20] ConductAtlas：審查準則異動追蹤 — https://conductatlas.com/change/2026-06-09-apple-apple-app-store-review-guidelines-2759/

其他
- Google OAuth 擋嵌入式 WebView — https://developers.googleblog.com/upcoming-security-changes-to-googles-oauth-20-authorization-endpoint-in-embedded-webviews/ 、https://auth0.com/blog/google-blocks-oauth-requests-from-embedded-browsers
- iOS PWA 限制（Web Push 需加到主畫面、無背景同步） — https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide
- Epic 與 Google 和解（費率分級、分地區推出） — https://www.iclarified.com/101291/google-opens-play-store-to-alternative-payments-under-epic-settlement
- [T1] 金管會詐騙通報下架數字 — https://www.cna.com.tw/news/afe/202305250313.aspx
