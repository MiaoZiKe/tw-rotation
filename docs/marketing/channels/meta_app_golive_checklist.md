# Meta 應用程式「一次做完」清單（讓 IG 留言自動私訊對一般讀者也能用）

> 建立 2026-11-20。對象：Andy。目的：App「LIGULIGU Aito Post」（App ID 993014640153379）目前是**開發模式**，讀不到非 App 角色者的留言、也私訊不到一般讀者。做完下面 6 個部分後，四個帳號（①哩股哩股 ②科技透明圈 ③CaffAIne ④談晴說礙）都能對一般讀者運作。
> 規矩（CLAUDE.md 11-10）：**畫面上沒有的按鈕不准我亂寫**。標「📷 先截圖」的步驟，請你做到那一步就截圖貼給我，我對過畫面再給下一步。Meta 後台改版很勤，下面的選單名稱以官方文件與你當下畫面為準。
> 英文說明與錄影腳本在 `docs/marketing/channels/app_review_4accounts/`（兩個檔，直接複製貼上）。

## 〇、先講清楚：為什麼一定要做這幾件事（查證結論）

| 事實 | 依據 | 信心 |
|---|---|---|
| Standard Access（開發模式預設）只能對「有 App 角色的人」運作；一般使用者要 **Advanced Access**，要先完成 App Review | [Meta：Instagram 平台 App Review](https://developers.facebook.com/documentation/instagram-platform/app-review) | 高 |
| 要 Advanced Access 的 App，必須連到**已完成商家驗證（Business Verification）**的商家 | [Meta 廣告與商務文件](https://developers.facebook.com/documentation/ads-commerce/marketing-api/brand-safety-and-suitability/brand-safety-partners)；論壇多則回報「商家驗證卡住就無法送審」 | 中高 |
| 送審要有「至少 1 次成功的 API 呼叫」＋每個權限一支錄影（端到端、登入鈕要看得到） | 同上 App Review 頁 | 高 |
| 收 comments／messages 的 Webhook 要 App 為 Live；Meta 兩頁對「先 Live 還是審完才 Live」寫法不一致 | 第三方整理，未在官方頁證實 | 低，所以第 4 步我們**先截圖確認畫面** |
| 錄影細節（留言權限要示範建立／更新／刪除留言；訊息權限要示範同意與真實私訊往返）| [Meta 權限參考](https://developers.facebook.com/docs/permissions)、第三方整理 | 中，送審前以後台當下提示為準 |
| 審查時間：第三方回報訊息權限約 3～5 個工作日，商家驗證常 3～14 天、有人卡 20 個工作日以上 | [Meta 社群論壇：商家驗證卡住案例](https://communityforums.atmeta.com/questions-discussions-38/business-verification-stuck-in-review-since-sep-30-20-business-days-portfolio-id-1784447062870108-180959)、[第三方 2026 指南](https://singhamandeep.com/instagram-messaging-api-approval-getting-instagram_business_manage_messages-2026/) | 中低（以 Meta 通知為準） |

## 一、先決條件快速自查（5 分鐘，不用做任何設定）

| # | 檢查項目 | 你要做的 | 回我什麼 |
|---|---|---|---|
| 1 | 四個 IG 帳號都是「專業帳號（Business 或 Creator）」且公開 | IG App → 設定 → 帳號類型；看到「商家」或「創作者」即可 | 四個帳號各回「是商家／創作者／個人」 |
| 2 | 你是這個 App 的管理員 | 開 <https://developers.facebook.com/apps/993014640153379/> 能進去就是 | 能進回「可以」；進不去回截圖 |
| 3 | 商家名「ADY」目前未驗證（你已確認） | 不用動 | 無 |

## 二、第 1 部分：商家驗證（Business Verification）— 最慢，先送，只能你本人

| 項目 | 內容 |
|---|---|
| 進入連結 | <https://business.facebook.com/settings/security>（商家設定 → 安全中心）。也可先開 <https://business.facebook.com/settings/info> 確認商家名是「ADY」 |
| 📷 先截圖 | 打開後**先截圖給我**（要看到「商家驗證」那一塊與按鈕名）。我對過畫面才寫逐格；官方各國流程不同，**台灣個人事業與公司要的文件不一樣，我不猜** |
| 一般會問的欄位（預填） | 法定名稱：與你的證明文件**完全一致**（ADY 若只是簡稱，要填文件上的正式名稱）；網站：`https://liguligu-puipui.com/`；電話、地址：與文件一致；驗證方式：依 Meta 畫面提供（簡訊／電話／網域驗證／email 擇一） |
| 要準備的文件 | 營業登記或公司登記、水電或電信帳單（需與商家名、地址一致）— 以畫面列的為準 |
| 網域驗證（若畫面要求） | 要在網域 DNS 加 TXT 記錄，或在網站放 meta 標籤。我可以代勞在網站加 meta 標籤（你把 Meta 給的那串貼給我即可） |
| 做完回我 | 「商家驗證已送出，狀態：XXX」（截圖更好） |
| 擋不擋別的事 | **擋**第 3 部分的送審（沒驗證不能申請進階存取）。所以最先做。審查期間可以同時做第 2、4（部分）、5 部分 |
| 預估你花的時間 | 15～30 分鐘（拍照／上傳文件）；Meta 審查 3～14 天，可能更久 |

## 三、第 2 部分：App 基本資料（15 分鐘，可與第 1 部分同時做）

入口：<https://developers.facebook.com/apps/993014640153379/settings/basic/>（應用程式設定 → 基本資料，**App settings → Basic**）。📷 進去後先截圖給我，我對過畫面再確認格子名稱。預填值如下：

| 欄位（英文名以畫面為準） | 填什麼 |
|---|---|
| 顯示名稱（Display name） | 不用動（LIGULIGU Aito Post） |
| 應用程式網域（App Domains） | `liguligu-puipui.com` |
| 聯絡人電子郵件（Contact email） | 客服信箱（與網站隱私權政策「聯絡方式」同一個；網站上顯示的那個） |
| 隱私權政策網址（Privacy Policy URL） | `https://liguligu-puipui.com/#privacy` |
| 使用者資料刪除（User data deletion）→ 選「資料刪除說明網址」 | `https://liguligu-puipui.com/#data-deletion` |
| 類別（Category） | 選最接近的（例如「商業與頁面」或「訊息」）；畫面沒有的類別不用硬選 |
| 應用程式圖示（App icon, 1024×1024） | 上傳站上 LOGO（不放比比；11-02 規定貼文不放比比，App 圖示用文字 LOGO） |
| 其餘 | 不用動 |
| 按 | 儲存變更（Save changes） |

**網址實際錨點（已對過 `site/legal.js`，main 45ff9eba2）**：
- 隱私權政策：`https://liguligu-puipui.com/#privacy`（路由 `privacy`）
- 資料刪除說明：`https://liguligu-puipui.com/#data-deletion`（隱私權政策頁內的「資料刪除說明」段，`id="data-deletion"`；程式另接受 `#privacy/data-deletion`，兩種都會捲到該段）。**用 `#data-deletion` 這個，不要用後者**。
- 同頁另有「社群自動回覆（Instagram／Threads）」段，已寫明只存雜湊、30 天自動刪除，審核員會看。
- 注意：這是單頁應用，網址 `#` 後面是前端路由；Meta 的網址檢查器可能只驗證網站可連線。若儲存時報「網址無效」，📷 截圖給我，我改做獨立網址（例如 `/privacy.html`）。

做完回我：「基本資料存好了」。

## 四、第 3 部分：App Review 申請進階存取（等第 1 部分驗證通過後）

入口：<https://developers.facebook.com/apps/993014640153379/app-review/permissions/>（App Review → 權限與功能，**Permissions and Features**）。

先決（我先處理，你不用做）：送審前 App 必須**已有成功的 API 呼叫**——四個帳號權杖產好後我會用程式各打幾次（讀媒體、讀留言），這步我做。

| # | 做什麼 | 填什麼 |
|---|---|---|
| 1 | 找到 `instagram_business_manage_comments`，按**申請進階存取（Request advanced access）** | 英文說明貼 `app_review_4accounts/permissions_en.md` 第 2 節；錄影上傳該檔第 4 節的影片 |
| 2 | 找到 `instagram_business_manage_messages`，同上 | 英文說明貼第 3 節；錄影同一支或第 2 支 |
| 3 | `instagram_business_basic`（若要求一併申請） | 貼第 1 節 |
| 4 | 若 Meta 另要「資料處理說明（Data Handling Questions）」「資料使用條款（Allowed Usage）」 | 📷 先截圖，我對過再填；原則照實：資料不賣、不給第三方、只存雜湊 30 天 |
| 5 | 按送出審查**Submit for Review**（送出審查） | 送審前我會用 inspector 逐項對過；錄影由你錄（腳本在 `app_review_4accounts/screencast_script.md`） |

📷 **這一步必須先截圖**：打開權限頁後，把「instagram_business_manage_messages」那一列（含按鈕）截圖給我。
擋不擋別的事：不擋第 4～5 部分；但審過前，一般讀者的留言讀取與私訊不會通。
預估你花的時間：看錄影 1 支約 20 分鐘（錄＋剪）＋填表 20 分鐘。

## 五、第 4 部分：四個帳號用同一個 App 產 IGAA 權杖（可立刻做，不用等審查）

目標：②③④ 各產一個「Instagram 登入」權杖（IGAA 開頭）；① 已有，不用動。開發模式下，**只有 App 角色是 Instagram 測試人員（Instagram Tester）的帳號**才能產權杖。

| # | 做什麼 | 連結／填什麼 |
|---|---|---|
| 1 | 把 ②③④ 加成 Instagram 測試人員 | <https://developers.facebook.com/apps/993014640153379/roles/roles/>（App 角色 → 角色）→ 新增使用者（Add People）→ 角色選「Instagram 測試人員（Instagram Tester）」→ 輸入 IG 帳號名 `Tech_01010909`、`caffaine.ai`、`talk_01010909`（一個一個加）。📷 先截圖角色頁給我 |
| 2 | 在**各帳號的 IG App** 接受邀請 | 該帳號的 IG App/網頁 → 設定 → 網站與應用程式（Apps and Websites）→「測試人員邀請（Tester Invites）」→ 接受。**四帳號各做一次** |
| 3 | 開 API 設定頁 | <https://developers.facebook.com/apps/993014640153379/instagram-business/API-setup/>（若連結 404，從左側「Instagram → 使用 Instagram 登入的 API 設定（API setup with Instagram login）」進）。📷 **先截圖這頁**，我確認「Generate access tokens」區塊的實際按鈕名 |
| 4 | 在「產生存取權杖（Generate access tokens）」區塊按「新增帳號（Add account）」→ 用該 IG 帳號登入 → 同意權限 → 按「產生權杖（Generate token）」 | 一次一個帳號，權杖**只顯示一次**，立刻複製 |
| 5 | 權杖放進 GitHub 密碼（不貼在聊天室） | 連結 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions> → New repository secret：名稱照 `docs/marketing/channels/accounts.md`（② `TECH_IG_ACCESS_TOKEN`、③ `CAFFAINE_IG_ACCESS_TOKEN`、④ `HEALING_IG_ACCESS_TOKEN`），值貼權杖。已存在的先**不要覆蓋**，我先確認舊權杖是不是同一個 App 產的 |
| 6 | 回我 | 「②③④ 權杖放好了」，各一行（不貼權杖本身） |

注意與已知坑（來源：[Meta 建立 Instagram App](https://developers.facebook.com/documentation/development/create-an-app/other-app-types/instagram-apis)、第三方整理）：
- 帳號必須是專業帳號且公開。
- 若 IG 帳號隸屬的商家與 App 擁有者商家相同，有人回報**無法加成測試人員**。若遇到，📷 截圖錯誤給我，我換路（例如改在該商家內將 IG 帳號指派給 App）。
- 「Add account」按了沒跳窗：關廣告攔截、換無痕視窗再試，仍不行就截圖。
- 權杖約 60 天；系統每週自動續期（accounts.md 已說明），你不用管。

## 六、第 5 部分：切換為上線（Live）

入口：App 後台最上方的「應用程式模式（App Mode）」開關，或 <https://developers.facebook.com/apps/993014640153379/dashboard/>。

| 項目 | 內容 |
|---|---|
| 切換前條件 | 第 2 部分（隱私權政策網址、資料刪除網址、圖示、類別）都填好 |
| 時機 | 官方兩頁寫法不一致（見〇）：我們**先送審，把 Live 開關當下的畫面截圖給我**，由畫面提示決定先切或審完才切。不猜 |
| 📷 必須先截圖 | 後台首頁（含 App 模式開關與它旁邊任何警告），截圖給我 |
| 切換後 | 開發模式角色限制解除，但**未通過進階存取的權限仍只對有角色者生效**，所以必須搭配第 3 部分 |
| 做完回我 | 「已切 Live」或截圖畫面的錯誤 |

## 七、第 6 部分：Webhook 回呼設定（等同事交付網址與驗證碼）

| 欄位 | 值 |
|---|---|
| 待填：Webhook 網址 | **（待填，同事完成後貼在這裡）** |
| 待填：驗證碼（Verify token） | **（待填；不寫進 repo，Andy 貼給 CEO 或存 GitHub 密碼）** |
| 入口 | 同第 5 部分的 API 設定頁，往下找「設定 Webhooks（Configure webhooks）」區塊。📷 先截圖，我確認區塊與欄位名 |
| 填法 | 回呼網址（Callback URL）貼 Webhook 網址；驗證碼（Verify token）貼驗證碼；按「驗證並儲存（Verify and save）」 |
| 訂閱欄位 | `comments`（留言）、`messages`（私訊）；其餘不用動。驗證成功後才能訂閱（[Meta Webhooks 文件](https://developers.facebook.com/documentation/instagram-platform/webhooks)） |
| 每個帳號 | 四個帳號都要「訂閱」（subscribed_apps），這步我在權杖產好後用程式做，你不用點 |
| 失敗訊息 | 若出現「回呼網址或驗證碼無法驗證」：網址必須公開、HTTPS、收到 GET 時原樣回傳 challenge；📷 截圖，我請同事查 |
| 擋不擋別的事 | 不擋送審；沒有 Webhook 時系統用輪詢，只是延遲 15 分鐘 |

## 八、你總共要做幾步、花多久、哪些一定先截圖

| 部分 | 你的步驟數 | 你的時間 | 能不能同時做 | 一定先截圖 |
|---|---|---|---|---|
| 1 商家驗證 | 3（開頁截圖、填表傳文件、回報） | 15～30 分 | 先做 | ✔ 開頁後 |
| 2 App 基本資料 | 2 | 15 分 | 與 1 同時 | ✔ 開頁後 |
| 3 送審進階存取 | 4（填 2 權限、傳錄影、送出） | 40 分（含錄影） | 要等 1 通過 | ✔ 權限頁 |
| 4 IGAA 權杖 | 6（加角色 3 帳號、接受邀請 3 次、產 3 權杖、放密碼） | 40～60 分 | 立刻可做 | ✔ 角色頁、API 設定頁 |
| 5 切 Live | 1 | 5 分 | 看畫面 | ✔ 儀表板 |
| 6 Webhook | 2 | 10 分 | 等同事 | ✔ 設定區塊 |
| **合計** | **約 18 步** | **約 2.5～3 小時（分兩三次）；不含 Meta 等待** | | **共 6 個畫面要先截圖** |

建議順序：**1 → 2（同時）→ 4（等待商家驗證期間做）→ 錄影 → 3（驗證通過後）→ 5 → 6**。

## 九、時程與風險

| 項目 | 估計（以 Meta 通知為準） |
|---|---|
| 商家驗證 | 3～14 個日曆天；偶有卡 20 個工作日以上的案例 |
| App Review（訊息／留言進階存取） | 約 3～10 個工作日；退件重送再 +3～5 天 |
| 全部一次過的最快情況 | 約 1.5～2 週；有退件約 3～4 週 |
| 審查期間 | 發文、Threads 回覆照常；IG 私訊對有角色的測試帳號可先實測；一般讀者暫時收不到 |

### 常見退件原因與預防

| 退件原因 | 預防（我們怎麼做） |
|---|---|
| 錄影看不到登入流程或真實往返 | 腳本逐段含 Instagram 登入授權畫面、留言→私訊→回覆全程，不剪掉關鍵段 |
| 錄影語言／字幕看不懂 | 全程加英文字幕（腳本旁白已附） |
| 說明與錄影不一致 | 說明只寫錄影裡有示範的功能；不夾帶沒用到的權限 |
| 要的權限超過實際用途 | 只申請 comments、messages、basic 三項 |
| 隱私權政策打不開或沒提到 Meta 資料 | 網址已可開；「社群自動回覆」段已寫明資料範圍與保存 30 天；送審前 inspector 再核對一次 |
| 資料刪除網址不可用 | `#data-deletion` 已上線；送審前我用瀏覽器驗證能捲到該段 |
| 審核員無法測試 | 在送審備註放「測試帳號與步驟」：給審核員測試用 IG 帳號（Andy 另建、不放主帳號密碼），並寫明如何觸發（留言關鍵字） |
| 看起來像群發／促銷 | 說明強調：只回覆對方先留言或先私訊，不主動推播；每人每日上限 |
| 商家資料與文件不符 | 填表照文件原文；ADY 簡稱需確認與文件一致 |
| 四帳號用同一 App，審核員疑惑 | 說明明寫「同一營運者擁有四個品牌帳號」，錄影示範 1 個帳號即可，另附四帳號清單 |

## 十、官方與參考來源

- [Instagram 平台 App Review（Meta）](https://developers.facebook.com/documentation/instagram-platform/app-review)
- [建立 Instagram 用 Meta App（Meta）](https://developers.facebook.com/documentation/development/create-an-app/other-app-types/instagram-apis)
- [Instagram Webhooks（Meta）](https://developers.facebook.com/documentation/instagram-platform/webhooks)
- [權限參考（Meta）](https://developers.facebook.com/docs/permissions)
- 第三方（較不可靠，僅供參考）：[Instagram Messaging API 審查指南 2026](https://singhamandeep.com/instagram-messaging-api-approval-getting-instagram_business_manage_messages-2026/)、[Instagram API 設定與審查](https://www.outstand.so/docs/configurations/instagram)
- 本 repo 舊稿：`docs/marketing/channels/tc/app_review/README.md`

## 十一、備註（誠實揭露）

- 帳號清單中 App 名稱：`accounts.md` 寫「liguligu-social」，你說的是「LIGULIGU Aito Post」，App ID 相同（993014640153379），以 ID 為準。
- Meta 後台逐格畫面我在此環境**打不開**（出口被擋），本清單的按鈕名來自官方文件摘要與第三方整理，所以才有 6 個「先截圖」關卡。
- 第 5 部分「先 Live 還是審完才 Live」官方兩頁說法不一致，未能證實，故以你的畫面為準。
