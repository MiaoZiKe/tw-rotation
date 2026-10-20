# Threads／IG 自動發布：Meta 串接設定（給 Andy，逐格照做）

> 2026-10-20 社群營運主管。對應程式：`scripts/social_publish.py`（截圖與排程另由 video-editor 的 `scripts/social_snap.py`、`.github/workflows/social-live.yml` 負責）。
> 畫面文字以 Meta 當下為準；標「以畫面為準，截圖給 CEO」的地方，看到跟我寫的不一樣，不要硬做，截圖回報即可。

## 0. 先看這三件事

| 問題 | 答案 |
|---|---|
| 需要先具備什麼 | ① IG 帳號必須是「專業帳號」且為**商業（Business）類型**（限動 API 目前只支援商業帳號，創作者帳號可能發不了限動，見來源 C）。IG App：設定 → 帳號類型和工具 → 切換成專業帳號 → 選「商業」。② Threads 要用**同一個 IG 帳號**登入。③ 一個 Meta 開發人員帳號（用你現有的 Facebook／IG 登入 developers.facebook.com 即可）。 |
| 擋不擋其他工作 | **不擋。** 沒設好金鑰時，程式自動 dry-run（只印出會發什麼，不真的發），截圖排程可以先跑。 |
| 要花多久 | 約 30～40 分鐘，一次做完。做完後**不用每 60 天手動換權杖**（見第 4 節）。 |

## 1. 官方做法查證結論（2026-10 查）

| 項目 | 結論 | 來源 |
|---|---|---|
| Threads 發單圖 | 兩步：`POST graph.threads.net/{threads-user-id}/threads`（`media_type=IMAGE`、`image_url`、`text`）→ 建好容器 → `POST /{id}/threads_publish`（`creation_id`）。圖片網址必須公開可下載。 | A |
| Threads 多圖輪播 | 三步：每張先建子容器（`is_carousel_item=true`）→ 建輪播容器（`media_type=CAROUSEL`、`children=子id,子id`）→ `threads_publish`。2～20 張；輪播算 1 則貼文。官方建議建好後約等 30 秒再發布，本程式改成輪詢狀態到 `FINISHED`。 | A、D |
| Threads 上限 | 24 小時滾動 250 則貼文（第三方整理，Meta 官方頁面的「rate limiting」段為準）。我們一天最多約十幾則，遠低於上限。文字上限 500 字（程式會截斷）。 | D（以官方頁為準） |
| Threads 權杖 | 短效權杖（1 小時）→ 換長效權杖（60 天）。長效權杖可延長：`GET graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=<長效權杖>`，要求權杖已滿 24 小時且未過期，延長後再 60 天。60 天沒延長就失效、只能重新授權。 | B |
| IG 限動（STORIES） | `POST graph.instagram.com/{ig-user-id}/media`（`media_type=STORIES`、`image_url`）→ 輪詢 `status_code` 到 `FINISHED`（Meta 建議每分鐘查一次、最多 5 分鐘）→ `POST /{ig-user-id}/media_publish`。限動圖須 JPEG、8MB 內、建議 9:16；**限動不能帶文字說明**，也不能用 API 加連結貼紙。 | C、E |
| IG 帳號條件 | 用「Instagram API with Instagram Login」版本：**不必連 Facebook 粉專**，用 IG 專業帳號直接登入授權；權限 `instagram_business_basic`、`instagram_business_content_publish`；限動限商業帳號。 | C、E |
| IG 上限 | 每個帳號 24 小時滾動 50 則 API 發布（在 `media_publish` 計算；可用 `content_publishing_limit` 端點查剩餘）。 | E |
| IG 權杖 | 長效 60 天；延長：`GET graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=<權杖>`，須已滿 24 小時、未過期。 | F |
| 要不要過審 | 只發**自己的帳號**（你是 app 擁有者／測試人員）：Standard Access 即可，**不用 App Review、不用企業驗證**。要替別人的帳號發才需要。 | B、G |

來源：
- A https://developers.facebook.com/docs/threads/posts/
- B https://developers.facebook.com/docs/threads/get-started/long-lived-tokens/ 、 https://developers.facebook.com/docs/threads/create-posts
- C https://developers.facebook.com/docs/instagram-platform/content-publishing/
- D https://postproxy.dev/blog/how-to-post-to-threads-via-api/ 、 https://adaptlypost.com/blog/threads-api-carousel-maximum-items
- E https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing
- F https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login
- G https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/get-started

不確定的地方（查到的來源互相矛盾，所以標出來）：(1) 有舊版文件說 Instagram Login 版不支援限動，也有 2026 年的整理文章說支援；以第 3 節最後的「測試發一張」實際結果為準。(2) 權杖延長後 Meta 回傳的字串是否與原本相同，官方文件沒寫死，程式兩種情況都處理（第 4 節）。

## 2. 步驟一：建立 Meta 應用程式（app）

| # | 在哪裡 | 點什麼／填什麼 | 備註 |
|---|---|---|---|
| 1 | 開 https://developers.facebook.com/apps/ | 右上 **Create App**（建立應用程式） | 沒註冊過會先要你按 **Get Started**（開始）並同意條款、驗證手機 |
| 2 | App name（應用程式名稱） | 填 `liguligu-social` | 不能含 Meta 商標字樣（如 Insta、Face） |
| 3 | App contact email | 填你的 Email | |
| 4 | Use cases（使用案例）畫面 | 勾 **Access the Threads API**（存取 Threads API）；**再**勾 **Manage messaging & content on Instagram**（管理 Instagram 的訊息與內容）。兩個都勾 | 若畫面只讓你選一個：先選 Threads，建好後到儀表板 **Add use case** 再加 IG。以畫面為準，截圖給 CEO |
| 5 | Business（商業資產）| 選 **I don't want to connect a business portfolio yet**（先不連結） | 只發自己帳號不需要 |
| 6 | 最後一步 | **Create app**（建立）。可能要你重輸 Facebook 密碼 | 密碼自己輸，不要貼給任何人 |
| 7 | 左側 **App settings → Basic**（應用程式設定 → 基本資料） | 填 **Privacy Policy URL**（隱私權政策網址）：`https://miaozike.github.io/tw-rotation/#privacy`；**App Icon** 隨便放一張比比圖 | 若該網址不存在，改填首頁，以畫面為準 |

## 3. 步驟二：Threads 的值（要拿 2 個）

| # | 在哪裡 | 點什麼／填什麼 | 備註 |
|---|---|---|---|
| 1 | 左側 **Use cases** → **Access the Threads API** → **Customize**（自訂） | 進到 Threads 的設定頁 | |
| 2 | **Permissions**（權限）分頁 | 確認 `threads_basic`、`threads_content_publish` 兩項後面是 **Ready for testing**（可測試）；沒有就按 **Add**（新增） | 其餘不用動 |
| 3 | **Settings**（設定）分頁 | 「Redirect Callback URLs」填 `https://miaozike.github.io/tw-rotation/`；「Uninstall callback URL」「Delete callback URL」都填同一個網址 | 這三格 Meta 要求必填，我們用不到 |
| 4 | 左側 **App roles**（應用程式角色）→ **Roles** → **Add People**（新增人員） | 選 **Threads Tester**（Threads 測試人員），輸入你的 **Threads 使用者名稱**（不含 @）→ **Add** | |
| 5 | 手機／網頁 Threads：個人檔案 → 右上設定 → **Account**（帳號）→ **Website permissions**（網站權限）→ **Invites**（邀請） | 找到剛才的邀請 → **Accept**（接受） | 以畫面為準，截圖給 CEO |
| 6 | 回 Meta：**Use cases → Access the Threads API → Customize → Settings** 的「User Token Generator」區 | 找到你的 Threads 帳號那列 → **Generate Access Token**（產生存取權杖）→ 跳出 Threads 授權視窗，按 **Continue**（繼續）| 產生的是短效權杖（1 小時），先別關頁面 |
| 7 | 把短效權杖換成 60 天長效 | 在瀏覽器網址列貼上（把三個 `<...>` 換掉）：`https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=<App secret>&access_token=<剛產生的短效權杖>`；App secret 在 **App settings → Basic → App secret → Show** | 網頁會顯示 `access_token` 一長串，**這串就是 THREADS_ACCESS_TOKEN**（立刻放進第 5 節，不要貼在聊天室）。**這步不用你輸指令，但 1 小時內要做完**；做不到就請 CEO 開「幫你換」的單 |
| 8 | 取得 THREADS_USER_ID | 瀏覽器開 `https://graph.threads.net/v1.0/me?fields=id,username&access_token=<長效權杖>` | 畫面上 `id` 後面那串數字就是 **THREADS_USER_ID**（不是使用者名稱） |

## 4. 步驟三：IG 的值（要拿 2 個）

| # | 在哪裡 | 點什麼／填什麼 | 備註 |
|---|---|---|---|
| 1 | 同一個 app，左側 **Use cases → Manage messaging & content on Instagram → Customize** | 進到 **API setup with Instagram login**（Instagram 登入版 API 設定） | 以畫面為準，截圖給 CEO |
| 2 | **Step 1 / Generate access tokens**（產生存取權杖）區 | 按 **Add account**（新增帳號）→ 用你的 IG 專業帳號登入並授權（兩個權限都要同意：基本資料、內容發布） | 授權視窗密碼／驗證碼在手機上你自己輸 |
| 3 | 加好後該帳號那列 | 按 **Generate token**（產生權杖）→ 勾「我了解」→ 複製 | 這串是 **IG_ACCESS_TOKEN**（此介面直接給長效 60 天的權杖）。立刻放進第 5 節 |
| 4 | 同一列 | 帳號名稱旁的數字 ID | 就是 **IG_USER_ID**。看不到就開 `https://graph.instagram.com/v24.0/me?fields=user_id,username&access_token=<權杖>`，用 `user_id` 那串 |
| 5 | 若 4 步驟找不到 Add account | 左側 **App roles → Roles → Add People** → 選 **Instagram Tester** → 輸入 IG 帳號 → 到 IG App：設定 → **網站權限／應用程式和網站** → **測試人員邀請** → 接受，再回第 2 步 | |

## 5. 步驟四：放進 GitHub Secrets（共 4 筆，各做一次）

網址：https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions → 綠色按鈕 **New repository secret**（新增儲存庫密碼）。每筆填兩格，然後按 **Add secret**（新增密碼）：

| 第幾筆 | Name 填 | Secret 填 |
|---|---|---|
| 1 | `THREADS_USER_ID` | 第 3 節第 8 步那串數字 |
| 2 | `THREADS_ACCESS_TOKEN` | 第 3 節第 7 步的長效權杖 |
| 3 | `IG_USER_ID` | 第 4 節第 4 步那串數字 |
| 4 | `IG_ACCESS_TOKEN` | 第 4 節第 3 步的權杖 |

Name 必須一字不差（全大寫、底線）；Secret 貼上後前後不能有空白或換行；不用動 Environment、不用動其他頁籤。

## 6. 權杖 60 天到期怎麼辦（設計）

- 程式**每次發文前**自動呼叫「延長」端點，把有效期重置成 60 天；盤中排程每天都會跑，所以權杖永遠新鮮，不需要你每 60 天去換。
- 限制：GitHub 工作流**不能把新值寫回 Secrets**（內建權限不給）。若 Meta 延長後回傳**同一串**字串，一切不用動；若回傳**新字串**，程式會在 log 提醒「需人工更新」（不印值），舊字串在原到期日前仍可用，所以最壞情況是你要每約 60 天重做一次第 3 節第 6～7 步與第 4 節第 3 步、更新兩筆 Secret。
- 最省事替代：若實測會換新字串，我們再改成「工作流用一把只有 Secrets 寫入權限的 Fine-grained PAT 自動寫回」，PAT 本身可設 1 年到期。需要時 CEO 另開單，現在不做。
- 權杖絕不進 repo、不進 log、不寫檔（測試有驗）。

## 7. 做完回報（回 CEO 一句話即可）

回：「Meta app 建好；4 筆 Secrets 已加（THREADS_USER_ID、THREADS_ACCESS_TOKEN、IG_USER_ID、IG_ACCESS_TOKEN）」。**不要貼任何值**。之後 CEO 會手動觸發一次 `social-live` 工作流，先看 dry-run 輸出，再開真發布；第一則請看 Threads 與 IG 限動是否真的出現。

## 8. 法遵（發布前提）

| 項目 | 做法 |
|---|---|
| 資料來源標示 | 每張圖左下或文末固定一行：`資料來源：臺灣證券交易所、證券櫃檯買賣中心（盤中為延遲或即時揭示報價，以官方為準）；統計時間 YYYY/MM/DD HH:MM`。盤後法人買賣超寫：`資料來源：證交所三大法人買賣超日報`。 |
| 免責 | 圖與文都要有：`本內容為公開資料整理，不構成任何投資建議，投資有風險，請自行判斷`。限動沒有文字欄，所以**免責與來源必須畫在圖上**（video-editor 的版型要留這一行，且不得與其他元素重疊）。 |
| 內容紅線 | 不喊單、不報明牌、不保證獲利、不點名個股推薦；只陳述數字（誰買超／賣超多少），不寫「建議買進」「必漲」。發布前一律過 legal-compliance。 |
| 即時資料 | 盤中截圖用的是公開的揭示資料，需註明「資料有延遲，僅供參考」；不要轉載付費即時行情供應商的畫面。 |
| 平台規範（摘要） | Meta 允許用官方 API 自動發布自己帳號的內容；禁止：用非官方方式爬取或登入自動化、買賣權杖、重複洗版、誤導或垃圾內容。官方 API 有頻率上限（Threads 約 250／24h、IG 50／24h），我們遠低於。連結／貼文若含金融內容需遵守各地法規；台灣以金管會與投信投顧法規為準（不得為未經許可的投資建議）。來源：Meta Platform Terms（https://developers.facebook.com/terms/）與 Developer Policies（https://developers.facebook.com/devpolicy/）；本表為摘要，條款全文以官方為準，我未能在查證時讀到全文，**上架前請 legal-compliance 再讀一次**。 |
| 揭露自動化 | 建議帳號簡介或固定貼文註明「部分貼文由系統自動整理發布」，降低被判定為誤導的風險。 |
