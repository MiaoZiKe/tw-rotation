# 結帳與付款（綠界＋銀行轉帳）— 2026-10-11

> Andy 10-11：「訂閱畫面，點擊訂閱後需要跳出金流服務，我已經申請綠界科技了，但還需要新增帳戶匯款，並且是需要有紀錄清單的，他如果適用帳戶匯款我是可以看到清單，為了以後確認會員資訊用，這部分都幫我處理好，需要一個完整介面…所以會有兩種方式可以進行」
> 追加：「這邊先查證，若是手動匯款，是否有辦法達成訂閱每月扣款」（→ 第 7 節：做不到）
> 追加：「當確認他付款後，會紀錄他付款時間，他訂閱多久，多久後會自動取消等等，總之我需要清單，並且客戶付款後會開放功能，千萬不要發生付款後還沒開放…一定要仔細確認，並且退款機制我是否能快速退款等等」

程式：`workers/account-api/pay.js`（伺服器，由 `worker.js` 檔尾 `installPay()` 接上）、`site/checkout.js`（結帳面板、我的訂單、到期提醒）、`site/admin_pay.js`（管理區「付款與訂單」）。
測試：`workers/account-api/tests/pay.test.mjs`（部署前必跑）、`_uitest --sections 結帳與付款1011 --workers 1`。決策：DECISIONS #356。

---

## 1. 流程

```
#pricing「升級 Plus」
   │ 沒登入 → 記住要買的方案 → Google 登入 → 回來自動重開結帳
   ▼
結帳面板（方案／月繳・年繳／金額＝伺服器價／訂單編號）
   ├─ 分頁①「信用卡／ATM／超商」（綠界）
   │    ├─ 信用卡每月（每年）自動扣款＝定期定額（另外勾「同意自動續扣」）
   │    └─ 單次付款（信用卡／ATM／超商）
   │    → POST /v1/pay/ecpay/create（伺服器產生參數＋CheckMacValue）→ 瀏覽器自動送出表單到綠界 AioCheckOut/V5
   │    → 使用者付款
   │       ├─ 綠界 → ReturnURL（/v1/pay/ecpay/notify，伺服器對伺服器）：驗章、RtnCode=1、金額相符 → 開通 → 回「1|OK」     【保險 1】
   │       ├─ 使用者被導回 OrderResultURL（/v1/pay/ecpay/result）→ 伺服器主動 QueryTradeInfo/V5 查單（驗章）→ 開通 → 303 回 #orders/<單號>【保險 2】
   │       ├─ 每 10 分鐘排程：3 天內未開通的綠界單逐筆查單；定期定額用 QueryCreditCardPeriodInfo 補漏掉的期數                  【保險 3】
   │       └─ 付款完成頁 #orders/<單號> 每 1.5～3 秒輪詢 /v1/pay/order（順手查單）→ 開通後 TwPerm.refresh()，功能當場解鎖       【保險 4】
   │       定期定額第 2 期起：綠界 → PeriodReturnURL（/v1/pay/ecpay/period）→ 子訂單 <單號>P<期數>，每期延長 1 個月（年繳 1 年）
   └─ 分頁②「銀行轉帳」（預付制）
        → POST /v1/pay/bank/create（產生待付款單；同方案同週期 3 天內沿用同一張）→ 顯示收款資訊＋「請於 3 天內轉帳」
        → 會員填 轉出末 5 碼／日期／金額／備註 → /v1/pay/bank/report → 「待確認」
        → 管理者在 #admin/pay「待確認的轉帳」按「確認入帳並開通」→ 開通（或「退回」寫原因）
        → 到期前 7 天與 1 天：頁首一行提醒＋帳號鈕紅點＋「再匯一期」（開新的轉帳單）
異常（已付款沒開通、開通出錯、金額不符）→ 管理區頁首紅色「異常 N」＋一鍵「補開通」                                       【保險 5】
```

**開通規則（冪等，保險 6）**：每筆訂單 `applied=1` 之後永遠不再加期間。起算日＝同方案且還沒到期 → 從目前到期日；否則（沒方案、已到期、換方案、退款降級後再買）→ 從現在。月繳 +1 個月、年繳 +12 個月（台北日曆，1/31 +1 月＝2/28）。每筆記錄開通期間 `grant_from～grant_to` 與開通來源（notify／result／sweep／poll／admin…）。

**到期降級**：權限一律以伺服器 `perm.expires` 為準（`effective()` 每次讀取時判斷，不靠排程，不會漏）；排程與每小時 alarm 另外寫一筆 `plan_events` 「到期降級」紀錄。

## 2. 資料表（Durable Object SQLite，全部進備份 EXPORT_TABLES）

| 表 | 用途 | 主要欄位 |
|---|---|---|
| `orders` | 訂單（綠界＋轉帳；定期定額每一期一筆子訂單） | id（LG＋台北時間 12 碼＋4 碼，≤20＝綠界 MerchantTradeNo）、uid、email、plan、plan_name、period、amount（伺服器價）、method（ecpay／bank）、recur、parent、period_n、period_state（active／cancelled）、status、trade_no、gwsr、pay_type、pay_info（ATM 帳號／超商代碼）、rtn_msg、from_last5、xfer_date、xfer_amount、note、admin_note、reject_reason、applied、grant_from、grant_to、act_src、act_err、anomaly、refunded、test、back、consent、created、paid_at、confirmed_at、cancel_at、last_sync |
| `refunds` | 退款（含失敗的嘗試） | id（確認框產生的一次性編號 rid＝冪等鍵）、oid、email、amount、kind（ecpay／manual）、action（N／C／R／E）、status（running／done／failed）、perm（now／end）、acct_last5、rdate、note、msg（綠界原因）、by |
| `plan_events` | 方案異動（開通、延長、到期降級、退款降級、取消自動續訂） | email、kind、plan、at、ref、detail（email＋kind＋ref 唯一） |
| `pay_events` | 綠界原始事件（通知、查單、退刷回應）：對帳與查問題 | at、oid、kind、detail（保留 400 天） |
| `kv.pay_bank` | 收款帳號（銀行名稱、代碼、帳號、戶名） | 管理區設定；**不寫在 repo** |

狀態：`pending` 待付款／`review` 待確認／`paid` 已入帳（還沒開通＝異常）／`active` 已開通／`failed` 失敗／`rejected` 已退回／`expired` 已逾期（轉帳 3 天、綠界 8 天沒付）／`refunded` 已退款（部分退款維持 active，記 refunded 金額）／`cancelled`。

## 3. API（account-api Worker）

會員（JSON、Origin 白名單、權杖）：`/v1/pay/quote`（金額＋收款帳號；只有登入會員拿得到帳號）、`/v1/pay/ecpay/create`、`/v1/pay/bank/create`、`/v1/pay/bank/report`、`/v1/pay/my`（我的訂單＋到期提醒 renew）、`/v1/pay/order`（付款完成頁輪詢）、`/v1/pay/period/cancel`（取消自動續訂）。
管理者（/v1/admin/* 總閘）：`pay/list`（訂單、退款、會員訂閱、異常、即將到期、方案異動）、`pay/confirm`、`pay/reject`、`pay/note`、`pay/reactivate`（補開通；force＝強制）、`pay/sync`（查單／對帳）、`pay/refund_quote`、`pay/refund`、`pay/period_cancel`、`pay/bank/get`、`pay/bank/put`。
綠界打進來（form-urlencoded、不檢查 Origin、一律驗 CheckMacValue）：`/v1/pay/ecpay/notify`（ReturnURL＋PaymentInfoURL）、`/v1/pay/ecpay/period`（PeriodReturnURL）、`/v1/pay/ecpay/result`（OrderResultURL）。
排程：`wrangler.toml` cron `*/10 * * * *` → `paySweep()`；每天 `17 19 * * *` 照舊清比對碼。

★ 金額一律由伺服器 `plans` 算（月＝period=month 的 price；年＝price_year，或 period=year 的 price）；前端送來的金額不採信。價格 0／待定的方案沒有線上結帳，維持舊的「訂閱申請」。

## 4. 綠界參數（AioCheckOut V5）

`MerchantID, MerchantTradeNo, MerchantTradeDate(yyyy/MM/dd HH:mm:ss 台北), PaymentType=aio, TotalAmount, TradeDesc, ItemName, ReturnURL, ChoosePayment(ALL／Credit), EncryptType=1, ClientBackURL, OrderResultURL, NeedExtraPaidInfo=Y`；
單次另加 `PaymentInfoURL`（ATM／超商取號通知）；定期定額另加 `PeriodAmount, PeriodType(M／Y), Frequency=1, ExecTimes(月 99／年 9), PeriodReturnURL`。

**CheckMacValue**：參數依名稱 A→Z（不分大小寫）排序 → `HashKey=…&` ＋ `k=v&…` ＋ `&HashIV=…` → .NET 風格 URL encode（空白→+、`- _ . ! * ( )` 不編碼）→ 轉小寫 → SHA256 → 轉大寫。
驗算：官方附錄範例（特店 3002607、ecpay20230312153023、TotalAmount 30000、ReturnURL https://www.ecpay.com.tw/receive.php…）算出 `6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840`，`pay.test.mjs` 第一條就是它。

**測試環境**（三個 Secret 都沒設就自動用）：`https://payment-stage.ecpay.com.tw`、特店 `3002607`、HashKey `pwFHCqoQZGmho4w6`、HashIV `EkRm7iFT261dpevs` —— 綠界官方「測試環境／Test Information」頁公開的「模擬銀行 3D 驗證」測試商店（官方註明不可用在正式環境）。結帳畫面與管理區標「測試模式」。

## 5. 退款（管理區每筆訂單的「退款」）

確認框：可退金額、試算（首次付款 7 天內且沒用過退款保證＝全額；其他＝依這筆開通期間未使用日數比例；可手改）、退款後權限（**立即降級**〔預設〕／到期才停）。
- **信用卡**：判斷階段 → 還在授權（當天 20:00 自動關帳前）全額＝放棄 `N`、部分＝改關帳金額 `C`；已關帳＝退刷 `R`；要關帳（有設 `ECPAY_CREDIT_CHECK_CODE` 才查得到）全額＝`E`＋`N`。綠界回 RtnCode=1 才標已退款；失敗顯示綠界原因、不改任何狀態。
  ⚠ **綠界測試環境不提供這支退刷 API**（官方文件註明）→ 測試模式下按退款會請你改「登記人工退款」。
- **定期定額**：退款時同時 `CreditCardPeriodAction Action=Cancel`，停掉之後的扣款。
- **ATM／超商／銀行轉帳**：沒有 API → 「登記人工退款」：退款帳號末 5 碼、金額、日期、備註；畫面提醒「請到網銀把錢匯回」。
- 冪等：確認框打開時產生一次性 rid，同一個 rid 重按只回上一次結果；同一筆有退款處理中時擋下；退款合計不能超過訂單金額。
- 退款寫進訂單明細、會員「我的訂單」（已退款 NT$ X）、退款紀錄分頁、三份 CSV；同時把 `bill_flags.refund_used` 設起來（七天保證用過了）。

## 6. 查證來源與信心度（WebSearch 摘要；WebFetch 連不到綠界網域）

| 項目 | 來源 | 信心 |
|---|---|---|
| CheckMacValue 演算法 | developers.ecpay.com.tw 附錄「檢查碼機制」(?p=16623、/32236/)、support.ecpay.com.tw/?p=16800；iThome 文章引官方範例值，**本機算出完全相同的值** | 高 |
| 測試商店 3002607／HashKey／HashIV、payment-stage 網址 | developers.ecpay.com.tw/49114/、/22867/、?p=22696 | 高 |
| AioCheckOut/V5 網址、必填參數、MerchantTradeNo ≤20 碼唯一 | developers.ecpay.com.tw/2864/、/2874/ | 高 |
| ReturnURL 要回 `1|OK`、RtnCode=1 才算成功、沒回 1|OK 會 5～15 分鐘重送、SimulatePaid=1 不改狀態、只支援 80／443 埠 | developers.ecpay.com.tw/45907/、?p=5631、support.ecpay.com.tw/?p=16395 | 高 |
| 定期定額 PeriodAmount／PeriodType／Frequency／ExecTimes／PeriodReturnURL；首期送 ReturnURL、之後送 PeriodReturnURL | developers.ecpay.com.tw/2900/、?p=16470、/5631/ | 中高（ExecTimes 上限兩版文件不一致：月 99 或 999、年 9 或 99；取保守的 99／9） |
| CreditCardPeriodAction（Action=Cancel、TimeStamp、終止後不能重新啟用） | developers.ecpay.com.tw/2900/、ecpay FAQ nID=1202 | 高 |
| QueryTradeInfo/V5（MerchantID、MerchantTradeNo、TimeStamp 3 分鐘內、太頻繁 403）；TradeStatus=1＝已付款 | developers.ecpay.com.tw/2890/、/45927/ | 中（TradeStatus 代碼表摘要被截斷，1＝已付款是慣例） |
| QueryCreditCardPeriodInfo（TotalSuccessTimes、ExecStatus 0 終止／1 執行中／2 完成、回 JSON） | developers.ecpay.com.tw/2892/ | 中高（ExecLog 子欄位沒查到，所以只用 TotalSuccessTimes 補期數） |
| 信用卡退款：先查單判斷階段；N 放棄（授權）、C 關帳、E 取消關帳、R 退刷（已關帳）；20:00 自動關帳；**測試環境不能用** | developers.ecpay.com.tw/45919/、ecpay_012.pdf、iThome 10223383 | 中（form 版 `payment.ecpay.com.tw/CreditDetail/DoAction` 的欄位 MerchantID／MerchantTradeNo／TradeNo／Action／TotalAmount 來自舊版規格，新版文件改成 JSON 版 ecpayment 網域；**正式上線前用 1 元訂單實測**） |

## 7. 為什麼銀行轉帳不能每月自動扣款（Andy 10-11 查證題）

結論：**手動匯款做不到自動扣款**，所以本站的銀行轉帳是**預付制**（一次付一個月或一年），到期前 7 天與 1 天在網站內提醒（帳號鈕紅點＋頁首一行字，不寄信），一鍵「再匯一期」開新的待確認訂單；想要自動續扣的會員請用信用卡定期定額。
- 綠界的「定期定額」**只支援信用卡**（PeriodType／Frequency／ExecTimes；首期 ReturnURL、之後每期 PeriodReturnURL；可用 API 終止）：developers.ecpay.com.tw/2900、/2892、/2872。
- 綠界 ATM 虛擬帳號是**單筆**（每次取號、繳一次），不能週期扣款。
- 銀行「ACH 代收／約定扣款」要**公司統編**跟銀行簽約，約 30 個工作日，**個人目前不適用**。
（以上是 CEO 10-11 用 WebSearch 查證的結論，轉述於此。）

## 8. Andy 要做的事（一步一步）

1. **確認綠界合約有開通「信用卡定期定額」**：打綠界客服或在廠商後台看「信用卡定期定額」有沒有開；**沒開的話定期定額付款會失敗**（單次付款不受影響）。
2. **取得正式金鑰**：綠界廠商後台 → 系統開發管理 → 系統介接設定，抄下 **特店編號（MerchantID）、HashKey、HashIV**。不要貼在對話或任何檔案裡。
3. **放進 GitHub Secrets**：<https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions> → New repository secret，名稱分別是
   `ECPAY_MERCHANT_ID`、`ECPAY_HASH_KEY`、`ECPAY_HASH_IV`（選用：`ECPAY_CREDIT_CHECK_CODE`＝後台的信用卡商家檢查碼，退款時查授權／關帳階段用）。
   三個都設好後到 Actions 手動跑一次「部署 Worker（會員登入與使用統計）」（<https://github.com/MiaoZiKe/tw-rotation/actions/workflows/deploy-account-worker.yml> → Run workflow）。沒設齊時 Worker 自動走測試環境，工作流摘要會列出缺哪個。
4. **綠界後台要填的網址**（我們每筆訂單都會帶，但後台有欄位時填一樣的）：
   - 付款結果通知（ReturnURL）：`https://tw-account.kcq01010909.workers.dev/v1/pay/ecpay/notify`
   - 定期定額每期通知（PeriodReturnURL）：`https://tw-account.kcq01010909.workers.dev/v1/pay/ecpay/period`
   - 付款完成導回（OrderResultURL）：`https://tw-account.kcq01010909.workers.dev/v1/pay/ecpay/result`
   - 若之後換自有網域，網站網址（ClientBackURL）會自動跟著，Worker 網址不變就不用改綠界。
5. **收款帳號**：網站 #admin/pay →「收款帳號設定」填銀行名稱、代碼、帳號、戶名 → 儲存（確認框再核對一次）。這組資料只存在 Worker 設定，不在 repo。
6. **正式上線前實測一次**：把 Plus 價格暫時設 NT$ 1（或開一個隱藏方案）→ 自己用信用卡單次付 1 元 → 看「我的訂單」已開通 → 管理區按「退款」走一次 → 確認綠界後台也退了。再用定期定額付一次 → 取消自動續訂。

## 9. 待辦／判斷

- **電子發票**：綠界有電子發票服務，**這次沒串**（沒有統編不能開統一發票，見 `launch_gap_payment_1009.md`）。有統編後接綠界電子發票 API：付款成功 → 開立；退款 → 作廢／折讓。
- **寄信**：付款收據、續扣前通知、扣款失敗通知仍然寄不出去（Worker 沒有寄信能力）；這次的到期提醒只在網站內。
- **刪除帳號**：訂單與退款是交易紀錄（對帳、稅務），刪帳號時**不刪**，只把 uid 斷開（email 保留）。隱私權政策（site/legal.js）還沒寫這一句 → 交法遵補。
- **換方案**：買不同方案（例如 Plus → Pro）時從今天起算新方案，舊方案剩餘天數不折抵（第一版人工處理）。
- **ExecTimes**：月繳 99 期（約 8 年）、年繳 9 期；到期前要會員重新訂一次。

## 10. 測試方式

- `node --test workers/account-api/tests/pay.test.mjs`：CheckMacValue 官方範例、存取控制、金額以伺服器為準、B1 ReturnURL、驗章錯誤／模擬付款／金額不符不開通＋異常補開通、B6 重複通知不重複延長、B2 導回查單、B3 排程查單、B4 輪詢、定期定額每期＋對帳補期＋取消、B7 到期降級＋降級後再付款從今天起算、轉帳開單／回報／確認／退回／每日 5 筆、到期提醒、退款（人工、部分、到期才停、重複 rid、DoAction N／R、失敗原因、定期定額同時終止）、刪帳號保留交易紀錄＋備份。
- `python scripts/_uitest.py --sections 結帳與付款1011 --workers 1`：本機真的 worker.js＋假綠界（`devserver.mjs` 的 `/Cashier/*`，一樣驗章／簽章），瀏覽器實際操作整條流程（含 ReturnURL 漏送 → 查單補開通 → 功能解鎖、退款降級、異常一鍵補開通、到期提醒、到期降級、手機 390、淺色主題對比）。截圖：`TW_PAY_SHOTS=<資料夾>`。
