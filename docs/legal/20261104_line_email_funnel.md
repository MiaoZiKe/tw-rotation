# 盤後數據「IG／Threads → LINE＋Email」漏斗：可行性、法遵與平台規範評估（2026-11-04）

> 法遵與風險專家產出，2026-11-04 02:10（台北）。**這是風險盤點與待確認清單，不是法律意見。**
> 每條標：出處／信心度（高／中／低／未確認）／要不要找專業人士。
> 網路資料只來自 `WebSearch` 的**摘要**，沒有讀過任何一篇原文；費率以 LINE、Meta、Cloudflare 官方頁面當下為準，條文以全國法規資料庫為準。
> **牽涉刑責或下架（停權）風險的，一律標「必須由專業人士確認」或「必須以官方頁面確認」，本文件不拍板。**
>
> 回應 Andy 11-03 原話：「關於盤後數據 我希望改成 加入Line 群發布，而我們做的就是消息，並且我們IG文章也可以做這篇文章 但實際上有更多數據 只是 他追蹤 + 留言 才可以Mail傳給他」。
> 對應 CEO 草案 `channel_plan_1103.md` 第五節。前情不重講：`docs/legal/20261101_subscription_signals.md`（付費訊號＝高風險、期貨法 §82／§112、判決 E1～E6）、`docs/launch_gap_legal_1009.md`（D1 告知、D6 行銷信、§70-1 廣告守則）、`docs/legal_refund_1009.md`（§20 拒絕行銷）。

---

## 〇、結論（先看這段）

**一句話：免費推「已發生的盤後數據」到 LINE＋Email 可以做，但要改三個地方 ——（1）用「LINE 官方帳號」而不是個人 LINE 群組；（2）IG 不可以「追蹤才給」，留言也只能當「方便拿」的入口、不能是唯一入口；（3）收 Email 要在網頁表單上告知與勾選同意，每封信附退訂。成本上，最省的是「使用者自己按選單取今日數據」（LINE 的回覆訊息不計費），主動推播到 500 人每月約 2,300 元。內容只要碰到「買／賣／進場時機／個股推介」，或之後把這個群改成收費，就回到投信投顧法 §107、期貨交易法 §112 的刑責區，必須由專業人士確認。**

白話五點：

1. **LINE 個人「群組」不適合**：上限 500 人、成員互相看得到彼此（個資外露）、外觀跟詐騙「投資群組」一模一樣；**LINE 社群（OpenChat）**上限 5,000 人但**機器人進不去**（社群回報，官方未明說），只能人手貼 —— 違反「Andy 不動手」的工作方式。**LINE 官方帳號**是一對一、成員互不可見、可以程式推播，是唯一合適的選項。
2. **LINE 推播是按「人次」算錢**：推 1 則給 1,000 人＝1,000 則。每交易日 1 則、一個月約 21 個交易日 → 100 人就要 2,100 則，**免費的 200 則撐不到 10 個人一個月**。但**使用者傳訊息後的「回覆訊息」不計費**，所以把主路線設計成「點選單 →『今日盤後』→ 回覆完整數據」可以零成本。
3. **IG「追蹤＋留言才給」踩到 Meta 垃圾訊息政策的字面**：Meta 社群守則（垃圾訊息）明文禁止「要求使用者以按讚、分享、**追蹤或任何其他公開形式的互動**，才能取得特定的獨家內容」（like/share-gating）。追蹤閘門是最直接的違反；「留言才給」字面上也算公開互動，風險中等。**改做法：數據在 LINE 官方帳號人人可拿；留言只是「懶人入口」，不留言也拿得到。**
4. **IG 留言自動私訊做得到**：Meta 的「私人回覆」（Private Replies）API 可以對留言者發 1 則私訊，限留言後 7 天內、每則留言只能 1 則，對方回覆後才開 24 小時對話窗。**只服務自己的帳號用「標準存取」不必送 App 審查**（官方文件，中高）。**Threads 沒有私訊 API**，Threads 只能在貼文寫「到 IG／LINE 拿」。
5. **Email**：用網頁表單收（不要在 IG 私訊裡收），表單上放個資法 §8 告知＋未預設勾選的同意框，每封信附一鍵退訂。寄信用 **Cloudflare Email Service**（站上已經需要 Workers 付費方案，每月含 3,000 封、之後每千封 0.35 美元），1,000 人每天寄約每月多 6 美元。

---

## 一、可以做／要改做法才能做／不要做

### 1-1 可以做（照現在的規劃即可）

| # | 項目 | 依據 | 信心度 | 找專業人士？ |
|---|---|---|---|---|
| A1 | IG／Threads 貼文放「盤後消息與重點」（已發生的數字：漲跌、成交、法人買賣超、族群資金流向排名），免費 | 投信投顧法 §4 要件「收取報酬」不成立；內容為已發生事實，不是推介建議 | 中（判決摘要；`20261101` E1～E4） | 否（免費、事實型） |
| A2 | LINE 官方帳號免費提供「完整盤後數據包」（同樣只有已發生的數字與來源） | 同上；資料源證交所／櫃買 OpenAPI 允許商業利用 | 中（法）／高（資料授權） | 否 |
| A3 | LINE 官方帳號用 Messaging API 程式推播與回覆 | LINE Developers 官方文件：官方帳號可程式發送 push／multicast／broadcast，reply 不計費 | 高 | 否 |
| A4 | IG 留言觸發自動私訊（私人回覆 API），私訊內容是「LINE 加好友連結＋網頁訂閱表單連結」 | Meta 開發者文件 Private Replies：留言後 7 天內、每則留言 1 則 | 高（官方文件） | 否（但要守 1-2 B1） |
| A5 | Email 寄送每日盤後數據給**主動訂閱且勾選同意**的人 | 個資法 §8（告知）、§19（契約或同意） | 高（條文） | 否 |
| A6 | 數據包裡放期貨／選擇權的**已發生籌碼數字**（三大法人台指期未平倉、買賣權比） | 事實陳述，不是期貨交易的分析意見或推介 | 中 | 是（建議，見 1-3 C3） |

### 1-2 要改做法才能做

| # | Andy 原本的做法 | 問題 | 改成 | 出處 | 信心度 | 找專業人士？ |
|---|---|---|---|---|---|---|
| B1 | **「追蹤＋留言」才給完整數據** | Meta 社群守則（垃圾訊息）禁止「要求按讚、分享、追蹤或任何其他公開形式的互動才能取得特定獨家內容」。追蹤閘門直接違反；可能被降觸及、不進推薦，嚴重時帳號受限 | ① **拿掉追蹤條件**，程式也**不要**查對方有沒有追蹤；② 完整數據在 LINE 官方帳號**人人可拿**（加好友即可），留言只是「懶人入口」；③ 貼文用語寫「想要完整版可以留言『數據』，我私訊連結給你；也可以直接到 LINE 拿」—— 有不留言也拿得到的路 | Meta Transparency Center 垃圾訊息守則（中高：摘要引原文）；廠商觀察「目前主要針對『追蹤我才給連結』的文字」（低） | 中高 | **必須以 Meta 官方頁面確認**（下架／降觸及風險） |
| B2 | 「加入 LINE **群**」 | 個人群組：上限 500、成員互看、無法隱藏名單（個資外露）、外型等同詐騙投資群組；社群 OpenChat：機器人進不去 | 改用 **LINE 官方帳號**（一對一、成員互不可見、可程式推播），名稱不要用「群」，叫「每日盤後數據」官方帳號 | LINE 說明中心（群組 499＋1）；GitHub LINE SDK 議題（OpenChat 機器人不可加入，低：社群回報） | 高（群組上限）／低（OpenChat 機器人） | 否 |
| B3 | 每天主動推給所有好友 | 按人次計費：每交易日 1 則 × 人數 × 約 21 天，100 人就超過免費 200 則 | 主路線改**「使用者拉取」**：圖文選單一顆「今日盤後」→ 使用者點了才回覆（reply 不計費）；主動推播只留「每週 1 則摘要」或給願意付推播費時再開 | LINE Messaging API pricing（官方）：reply 不計入則數；push 按收件人數計 | 高 | 否 |
| B4 | 在 IG 私訊裡請對方留 Email | 個資法 §8 要在蒐集時告知 7 項；私訊內容存在 Meta、無法留同意紀錄；退訂難管理 | 私訊只給**網頁訂閱表單連結**，在表單頁完成告知＋勾選同意＋雙重確認信（點信中連結才算訂閱） | 個資法 §8、§19、§20；法務部 102 年函釋摘要 | 高（條文）／中（函釋） | 否 |
| B5 | Email 裡順便宣傳付費方案或網站功能 | 宣傳＝行銷利用，§20 要另取同意、首次行銷就要給拒絕方式；與「免費數據」目的不同 | 數據信只放數據；要寄宣傳，表單上另一個**未預設勾選**的「願意收到功能與方案通知」 | 個資法 §20 II、III；`legal_refund_1009.md` | 高 | 否 |
| B6 | IG 用 `is_user_follow_business` 判斷追蹤 | 技術上要對方**先傳過訊息**才讀得到（私人回覆送出時讀不到）；而且用了就是 B1 的追蹤閘門 | **不實作**。這個欄位可以留著做統計（追蹤者占比），但不能拿來決定給不給 | Meta User Profile API 文件（官方，高） | 高 | 否 |
| B7 | 貼文與 LINE 寫「明天看好 XX 族群」「資金流入可以布局」 | 「看好」「布局」是推介與時機，族群也擋不住（`20261101` 第二節） | 一律照 `docs/neutral_copy_1006.md` 中性用語：「XX 族群今日成交占比 18.2%，連 3 日上升」，只講已發生 | `20261101` E2（中低）；`compliance_and_tiers.md` 四維度 | 中 | **必須**（若要寫任何方向性字眼） |

### 1-3 不要做（每條附替代做法）

| # | 不要做 | 理由 | 替代做法 | 出處 | 信心度 | 找專業人士？ |
|---|---|---|---|---|---|---|
| C1 | **把 LINE 官方帳號／群組改成收費**（會員費、贊助解鎖、付費才進群），而內容含個股或族群的分析、評分、時機 | 判決裡月費 666～1,800 元的 LINE／Discord 群組都判有期徒刑 4～6 月併科罰金；不以盤中帶單為必要 | 收費只收「工具使用權」（使用者自設條件的篩選與統計），照 `20261101` 方案甲；或與持牌投顧合作由對方發布 | `20261101` E1、E3、E4（中） | 中 | **必須**（刑責） |
| C2 | 免費群做久了，再「升級 VIP 群」報明牌 | 免費導流到付費＝金管會點名的老套路；付費那一刻四要件全滿 | 同 C1；免費頻道永遠只放已發生數據 | 公視、自由時報「大萌妹子」案報導摘要（中） | 中 | **必須**（刑責） |
| C3 | 數據包寫台指期／選擇權的方向（「偏多」「留意空方」「明日支撐 XX 點」） | 期貨交易法 §82＋§112：非法經營期貨顧問事業，七年以下有期徒刑；收費才成立，但免費建立「訊號」的形象就是收費的前置 | 只列數字與昨日比較（未平倉口數、增減）；不寫方向、不寫點位 | `20261101` E5、E6（中） | 中 | **必須**（刑責） |
| C4 | 追蹤閘門、要求「標記 3 位朋友」「分享到限動」才給 | Meta 垃圾訊息守則明文（like/share-gating）；降觸及、帳號受限 | B1 的「有留言／沒留言都拿得到」 | Meta 守則（中高） | 中高 | 以官方頁面確認 |
| C5 | 用個人 LINE 帳號手動大量轉發、或用非官方工具（模擬手機、外掛）群發 | LINE 通用服務條款禁止對大量不特定用戶發送相同訊息，可不通知刪除帳號；2025 年起打詐大量停權 | 只用官方帳號＋Messaging API | TechNews 報導引 LINE 條款（中） | 中 | 否 |
| C6 | 收集對方持股、成本、券商帳號、身分證（「告訴我你持有什麼，我幫你看」） | 個資法 §5 比例原則；且「看你的持股給意見」就是一對一顧問 | 私訊自動回覆只導向數據與客服表單 | `launch_gap_legal_1009.md` D5（高） | 高 | 否 |
| C7 | 用 Yahoo 資料做 LINE／Email 數據包 | Yahoo 明文禁止商業用途；就算免費，發給大量人也是再散布 | 只用證交所／櫃買 OpenAPI、集保；FinMind 商用再散布未確認，先不要放進對外數據包 | `product_strategy.md`（中高） | 中高 | 否 |

---

## 二、建議架構

### 2-1 LINE 產品比較

| 項目 | LINE 個人群組 | LINE 社群（OpenChat） | **LINE 官方帳號（建議）** |
|---|---|---|---|
| 人數上限 | 500（建立者＋499；開自動加入時 100） | 5,000 | 好友無上限 |
| 成員互相看得到 | 看得到 | 暱稱看得到 | **看不到** |
| 程式自動發送 | 可邀官方帳號機器人進群，但按群內人數計費 | **機器人無法加入**（社群回報，官方未明說） | 可以（push／multicast／broadcast／reply） |
| 費用 | 跟官方帳號同一套則數 | 免費，但只能人手貼 | 輕用量 0 元／中用量／高用量（見 2-2） |
| 詐騙外觀 | 高（像「投資群」） | 高 | 低（官方帳號可申請認證） |
| 出處／信心度 | LINE 說明中心（高） | uptogo、gremlinworks 整理（中）；GitHub 議題（低） | LINE Developers（高） |

### 2-2 每月費用估算（LINE 主動推播；每交易日 1 則、每月 21 個交易日）

**按人次計**：1 則 × 收件人數。封鎖者不計；**回覆訊息（reply）不計**（LINE Developers 官方，高）。
方案費率**以下只有第三方整理**：輕用量 0 元／每月 200 則；中用量 3,000 則；高用量 6,000 則、加購每則 0.2 元（5 萬則內）。第三方文章稱 **2026-11-01 起中用量 800→1,000 元、高用量 1,200→1,400 元（未稅）**，官方原文**未查到**（中低）。下表用調價後數字、未稅。

| 好友數 | 每月則數 | 適用方案 | 每月費用（未稅，估） | 改成「使用者點選單拉取」 |
|---|---|---|---|---|
| 100 | 2,100 | 中用量（3,000 則） | **約 1,000 元**（未調價則 800 元） | **0 元** |
| 500 | 10,500 | 高用量 6,000＋加購 4,500 × 0.2 | **約 2,300 元**（1,400＋900） | **0 元** |
| 1,000 | 21,000 | 高用量 6,000＋加購 15,000 × 0.2 | **約 4,400 元**（1,400＋3,000） | **0 元** |
| 混合：拉取為主＋每週 1 則推播（約 4 則／月） | 400／2,000／4,000 | 輕用量撐不住 100 人以上（200 則） | 100 人：中用量 1,000 元；500 人：中用量 1,000 元；1,000 人：高用量 1,400 元 | — |

> ⚠ 中用量「不可加購」（第三方，中）：超過 3,000 則當月就推不出去，不會自動加錢。
> ⚠ 10-27 是同意新價的期限（第三方，低），已過；開帳號時看「LINE Official Account Manager」上顯示的實際價格。

**Email（Cloudflare Email Service，官方文件，高）**：寄給任意收件人要 Workers 付費方案（每月 5 美元，`hosting_cost_plan.md` 已列為 1 千人時的必要成本），每月含 3,000 封，之後每千封 0.35 美元，硬退信也計入。

| 訂閱數 | 每月封數 | 額外費用（Workers 付費方案已開時） |
|---|---|---|
| 100 | 2,100 | 0 |
| 500 | 10,500 | 約 2.6 美元（約 85 元） |
| 1,000 | 21,000 | 約 6.3 美元（約 205 元） |

備選：Resend 免費每月 3,000 封但**每日 100 封上限**（官方部落格，高）→ 超過 100 人就不夠；Brevo 免費每日 300 封（官方說明中心，高），免費版通常帶 Brevo 標誌（未確認）。**建議 Cloudflare Email Service**：跟現有 Worker 同一家、不必再交第三方個資（跨境處理少一家，隱私權政策少寫一家）。

**合計（建議架構＝LINE 拉取為主＋每週 1 推＋Email 每日）**：100 人約 1,000 元／月；500 人約 1,100 元；1,000 人約 1,600 元（不含已編列的 Workers 5 美元）。純拉取不推播則 LINE 0 元，只剩 Email 0～205 元。

### 2-3 流程（建議版）

```
Threads 貼文（盤後消息與重點，不放網址，照 channel_plan 第二節）
   └─ 結尾：「完整數據每天在 IG 與 LINE 免費拿」
IG 貼文（同上）
   ├─ 結尾：「想要完整版：留言『數據』，我私訊你連結；或點簡介 LINE 直接拿」
   └─ 有人留言含「數據」→ Webhook → Worker 呼叫私人回覆 API（7 天內、每則 1 則）
          私訊：LINE 加好友連結＋Email 訂閱表單連結（不查追蹤、不要求追蹤）
LINE 官方帳號
   ├─ 加好友 → 歡迎訊息（告知＋免責，見第三節）
   ├─ 圖文選單「今日盤後」→ 使用者點 → reply 回覆今日數據圖＋文字（不計費）
   └─ 每週一次主動推播「本週摘要」（計費，輕／中用量內）
Email 訂閱表單（Worker 頁面）
   ├─ §8 告知＋同意框（不預設勾）＋另一個行銷同意框（不預設勾）
   ├─ 雙重確認信 → 點連結才生效，存「同意時間＋告知版本」
   └─ 每交易日盤後寄數據信，信尾一鍵退訂（點了立即停）
```

技術前提（給排工參考，不是本文件範圍）：IG 帳號要是專業帳號；Meta App 只服務自己帳號 → **標準存取不必送審**；權限 `instagram_business_basic`、`instagram_business_manage_comments`、`instagram_business_manage_messages`（官方文件，中高：權限名稱以建立 App 當下為準）。

---

## 三、可以直接貼上去的草稿

### 3-1 IG 貼文結尾（取代「追蹤＋留言」）

```
完整盤後數據（族群資金流向排名、三大法人、融資融券）每天免費更新：
・留言「數據」，我私訊連結給你
・或點簡介的 LINE 直接拿（不用留言）
```

### 3-2 IG 私人回覆（自動私訊，1 則）

```
嗨，這是今天的完整盤後數據入口：
・LINE（點選單「今日盤後」就有）：<LINE 加好友連結>
・Email 每日寄送：<訂閱表單連結>
內容只有已發生的市場數據，不提供個股買賣建議。
```

### 3-3 LINE 官方帳號歡迎訊息

```
感謝加入「每日盤後數據」。
點下方選單「今日盤後」就能看到今天的完整數據。

這裡提供的是已發生的市場數據整理（資料來源：臺灣證券交易所、櫃買中心、集保結算所公開資料），
不是投資建議，也不推薦任何個股或買賣時點。投資請自行判斷並承擔風險。
不想再收到訊息，封鎖本帳號即可。
```

### 3-4 Email 訂閱表單上的告知（個資法 §8）

```
【個人資料蒐集告知】
蒐集者：<經營者名稱，與網站隱私權政策一致>
目的：寄送你訂閱的每日盤後市場數據（特定目的：其他經營合於營業登記項目或組織章程所定之業務／未確認類別代號，見未確認清單）
蒐集的資料：電子郵件地址、訂閱與退訂時間
利用期間：訂閱期間；退訂後 30 天內刪除（法令另有保存義務者除外）
利用地區與對象：僅本服務使用；寄信系統由 Cloudflare 處理（伺服器可能位於台灣以外）
你的權利：可隨時查詢、閱覽、更正、停止寄送或刪除（每封信尾可一鍵退訂，或來信 <客服信箱>）
不提供的影響：不提供電子郵件就無法寄送，但不影響你使用 LINE 或網站

□ 我已閱讀上述告知，同意以電子郵件接收每日盤後數據（必勾）
□ 我也願意收到網站功能與方案通知（可不勾，不影響訂閱）
```

### 3-5 Email 信尾

```
本信為你主動訂閱的每日盤後數據，內容為已發生的市場數據整理，不構成投資建議，不推薦任何個股或買賣時點。
資料來源：臺灣證券交易所、櫃買中心、集保結算所公開資料（政府資料開放授權條款第 1 版）。
不想再收到：<一鍵退訂連結>（點了立即停止，不必登入）
```

> 註：`docs/marketing/social_unit/auto_post.md` 規定 IG／Threads 貼文**不放免責**。這份不改它；免責放在 LINE 歡迎訊息、私訊、Email 這三個「一對一」的地方，貼文本身靠「只寫已發生數字」守住。

---

## 四、需要 Andy 決定的事

| # | 要決定什麼 | 選項 | 我的建議（依證據） | 擋不擋其他工作 |
|---|---|---|---|---|
| 1 | 「追蹤＋留言才給」要不要改 | ①照原樣（追蹤閘門）②只留「留言」入口＋LINE 人人可拿 | **②**：①直接撞 Meta 守則字面，被降觸及就跟 11-02 診斷要救的分發衝突 | **擋 IG 私訊自動化的開發**（規則決定程式怎麼寫） |
| 2 | LINE 用哪一種 | 個人群組／社群 OpenChat／官方帳號 | **官方帳號**（唯一能程式自動、成員互不可見） | **擋**：要先開帳號才能接 API；開帳號要 Andy 本人登入 LINE 帳號操作（之後另寫逐格步驟） |
| 3 | LINE 每天主動推，還是使用者點了才給 | ①每日推（100 人約 1,000 元／月起）②拉取為主＋每週 1 推（約 1,000～1,400 元）③純拉取（0 元） | **②**，好友破 500 再評估 | 不擋（先做拉取，推播開關之後再開） |
| 4 | 經營者名稱寫什麼（告知事項第一行） | 個人姓名／品牌名「哩股哩股」／公司 | 跟 `launch_gap_legal_1009.md` C3、D1 一起決定；法務部函釋要求「明確的名稱」 | **擋 Email 表單上線**（不擋 LINE） |
| 5 | 訂閱表單放哪裡 | 主站內／獨立訂閱頁 | channel_plan 第二節「網站先不公開推廣」→ 用**獨立訂閱頁**（只有表單，不導主站） | 不擋 |
| 6 | 寄信服務 | Cloudflare Email Service／Resend／Brevo | **Cloudflare**（已有付費方案、少一家第三方） | 不擋（可先 LINE 後 Email） |
| 7 | 將來 LINE／Email 會不會收費 | 永遠免費／收費 | **永遠免費**；收費走網站工具（方案甲），且收費前律師意見 | 不擋現在；**擋任何收費設計** |

---

## 五、來源與信心度

| # | 事實 | 出處 | 信心度 |
|---|---|---|---|
| S1 | LINE 群組上限：關閉自動加入可邀 499 人（含建立者 500）；開啟時 100 | [LINE 說明中心 Group basics](https://help2-o.line.me/line/desktop/categoryId/50000295/3/pc?lang=en) | 高 |
| S2 | LINE 社群上限 5,000 人 | [uptogo 整理](https://uptogo.com.tw/科技/line聊天室跟群組差別？/)、[gremlinworks](https://gremlinworks.com.tw/line社群) | 中 |
| S3 | 機器人無法加入 OpenChat | [line-bot-sdk-python issue #918](https://github.com/line/line-bot-sdk-python/issues/918)（社群回覆） | 低 |
| S4 | 官方帳號可在群組互動，需開「Allow bot to join group chats」 | [LINE Developers 群組聊天](https://developers.line.biz/en/docs/messaging-api/group-chats/index.html.md) | 高 |
| S5 | 計費按收件人數；reply 不計；封鎖者不計；push／multicast／broadcast／narrowcast 計 | [Messaging API pricing](https://developers.line.biz/en/docs/messaging-api/pricing/)、[How message counts are calculated（2026-05-28）](https://developers.line.biz/en/tips/2026/05/28/how-to-count-messages/) | 高 |
| S6 | 推到 500 人群組算 500 則 | [FIRST LINE 說明](https://help.firstline.cc/feature/channels/line/pricing) | 中 |
| S7 | 台灣方案：輕 0 元 200 則／中 3,000 則／高 6,000 則，加購 0.2 元（5 萬則內）、0.15 元（之後） | [FIRST LINE](https://help.firstline.cc/feature/channels/line/pricing)、[actgsys 2026](https://actgsys.com/zh/blog/line-bot-development-cost-guide-2026)、[Omnichat 2026](https://blog.omnichat.ai/tw/line-2-0-official-account-pricing/amp/) | 中（第三方） |
| S8 | 2026-11-01 起中用量 1,000 元、高用量 1,400 元（未稅） | [actgsys 2026](https://actgsys.com/zh/blog/line-bot-development-cost-guide-2026)（稱引自官方公告，官方原文未查到） | 中低 |
| S9 | IG 私人回覆：留言後 7 天內、每則留言 1 則，對方回覆後 24 小時內才能追加 | [Meta Private Replies](https://developers.facebook.com/docs/messenger-platform/instagram/features/private-replies)、[Instagram Platform Private Replies](https://developers.facebook.com/documentation/instagram-platform/private-replies) | 高 |
| S10 | 只服務自己帳號用標準存取、不需 App 審查；進階存取需 App 審查＋商家驗證 | [App Review for Instagram API](https://developers.facebook.com/docs/instagram-platform/app-review)、[Instagram Platform overview](https://developers.facebook.com/docs/instagram-platform/overview) | 中高 |
| S11 | `is_user_follow_business` 存在；需對方先傳訊息（或點破冰問題／選單）才取得同意、讀得到 | [Instagram User Profile API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/user-profile) | 高 |
| S12 | Meta 垃圾訊息守則禁止「要求按讚、分享、追蹤或任何其他公開形式互動以取得特定獨家內容」 | [Meta Transparency Center – Spam](https://transparency.meta.com/policies/community-standards/spam/) | 中高（摘要引原文；Instagram／Threads 版本措辭未逐字確認） |
| S13 | 執法目前多針對「追蹤我才給連結」文字與誘餌語 | [planoly](https://www.planoly.com/blog/is-comment-to-dm-allowed-on-instagram.md)、[creatorflow](https://creatorflow.so/blog/instagram-follow-gate-when-to-use/)（廠商觀察） | 低 |
| S14 | Threads API 有回覆管理（`threads_manage_replies`），沒有私訊 API | [Threads Reply Management](https://developers.facebook.com/documentation/threads/reply-management)、[Metricool](https://metricool.com/threads-dms/) | 中高（「沒有」是查不到，不是官方說沒有） |
| S15 | Cloudflare Email Service：Workers 付費方案每月含 3,000 封，之後每千封 0.35 美元；寄任意收件人需付費方案；硬退信計入 | [Cloudflare Email Service pricing](https://developers.cloudflare.com/email-service/platform/pricing/) | 高 |
| S16 | Resend 免費每月 3,000 封、每日 100 封 | [Resend blog](https://resend.com/blog/new-free-tier) | 高 |
| S17 | Brevo 免費每日 300 封 | [Brevo 說明中心](https://help.brevo.com/hc/en-us/articles/208580669) | 高 |
| S18 | 個資法 §8 告知事項、§20 目的外利用與行銷；書面同意要單獨意思表示 | [臺北市法規函釋彙整](https://laws.gov.taipei/law/Interpretation/RelatedLaw/FE263179)、[理律 Newsletter](https://www.leeandli.com/TW/Newsletters/3949.htm) | 高（條文）／中（函釋） |
| S19 | 「濫發商業電子郵件管理條例」：默示拒絕、主旨標示「廣告」 | 2008 年 NCC 草案說明（摘要） | 低（**是否已立法未確認**，我判斷多半仍是草案） |
| S20 | 無照推薦股票且取得報酬即屬非法經營投顧；免費群組導流是常見手法 | [自由時報「大萌妹子」](https://ec.ltn.com.tw/article/breakingnews/3999895)、[公視](https://news.pts.org.tw/article/826031)、[ETtoday 2026-06-18](https://www.ettoday.net/news/20260618/3185434.htm) | 中 |
| S21 | LINE 通用服務條款禁止對大量不特定用戶發送相同訊息，可不通知刪除帳號 | [TechNews](https://technews.tw/?p=1367793)（報導引條款） | 中 |
| S22 | 判決 E1～E6（月費 LINE／Discord 群判刑、期貨顧問七年以下） | `docs/legal/20261101_subscription_signals.md` 第一節 | 中 |

**查過的關鍵字**（依 CLAUDE.md 2026-10-07 規矩）：「LINE官方帳號 2026 方案 費率 免費訊息則數」「LINE官方帳號 2026年11月 調整 費率 公告」「lycbiz LINE官方帳號 方案 加購」「LINE官方帳號 高用量 加購訊息 階梯」「LINE 群組 人數上限 社群 OpenChat 機器人」「LINE OpenChat 機器人 API 不支援」「LINE Messaging API pricing group members reply free」「Instagram private replies API 7 days」「is_user_follow_business」「Meta engagement bait follow to get DM」「Meta Community Standards spam requiring users to engage」「Instagram API advanced access app review」「Threads API direct message」「Resend／Brevo／Cloudflare Email Service free tier」「Cloudflare Email Service pricing」「個資法 第8條 第20條 濫發商業電子郵件」「免費LINE群組 導流 付費群組 投顧 判決」「投顧法 間接報酬 廣告收入 導流」「LINE官方帳號 條款 投資 停權」。
三類來源：一手（LINE Developers、Meta 開發者文件與 Transparency Center、Cloudflare 文件、Resend／Brevo 官方、法規函釋）、媒體（自由時報、公視、ETtoday、TechNews）、業者整理（Omnichat、actgsys、FIRST LINE、planoly、creatorflow）。

---

## 六、未確認清單

| # | 未確認事項 | 為什麼重要 | 去哪裡確認 | 找專業人士？ |
|---|---|---|---|---|
| U1 | LINE 台灣官方帳號 2026-11 起的**正式月費與加購單價**（是否含稅） | 費用估算全靠第三方 | LINE Official Account Manager 方案頁、tw.linebiz.com 公告 | 否（開帳號時看畫面） |
| U2 | 機器人能不能加入 LINE 社群（OpenChat） | 決定社群能不能當自動頻道 | LINE Developers 更新紀錄；實測 | 否 |
| U3 | Meta 垃圾訊息守則對「留言才給」（不含追蹤）是否也算 gating；Instagram／Threads 推薦資格（Recommendations Guidelines）有無另外列 | B1 的殘餘風險 | Transparency Center 原文、Instagram 推薦資格頁、帳號狀態頁 | 以官方頁面確認 |
| U4 | 私人回覆 API 的每小時上限（第三方稱 750 次／帳號／小時） | 爆量貼文時的保底 | Meta Private Replies 文件 | 否 |
| U5 | **免費頻道若帶來「間接收益」**（導流到付費網站、廣告、業配），法院是否會認定符合投顧法「報酬」要件 | 決定免費頻道是不是真的「低風險」 | 司法院裁判書系；律師 | **必須**（刑責） |
| U6 | 「濫發商業電子郵件管理條例」是否已立法 | 若有，數據信主旨要不要標示、退訂要求 | 全國法規資料庫 | 否 |
| U7 | 個資法 114-11 修正條文施行日與新增義務（外洩通報等） | 收 Email 後就有外洩風險 | 行政院施行令（`launch_gap_legal_1009.md` D3 同） | 建議 |
| U8 | 告知事項的「特定目的」代號（個資特定目的及類別） | 表單告知第二行要填 | 法務部「個人資料保護法之特定目的及個人資料之類別」 | 否 |
| U9 | LINE 官方帳號認證（藍盾／綠盾）審查是否排除投資、股市類帳號；官方帳號條款對金融資訊有無限制 | 停權風險、信任感 | tw.linebiz.com 認證帳號審核標準、官方帳號服務條款 | 否 |
| U10 | FinMind 資料商用再散布 | 數據包欄位能不能用 FinMind 的 | FinMind 條款（`product_strategy.md` 已列） | 否 |
| U11 | Brevo 免費版是否強制帶品牌標誌 | 備選寄信服務 | Brevo 方案頁 | 否 |

---

## 七、律師問題（接續 `launch_gap_legal_1009.md` 1～9、`20261101` 問題清單）

10. 免費 LINE 官方帳號與 Email 每日提供「已發生的族群資金流向、法人買賣超、期貨未平倉數字」，**不含任何方向或時機字眼**，但同時導流到將來的付費網站工具 —— 是否可能被認定為以「間接報酬」經營證券投資顧問或期貨顧問業務？
11. 「族群資金流向排名」（依成交占比排序，非評分）是否屬「分析意見」？排名本身是否構成推介？
