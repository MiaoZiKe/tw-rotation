# 訂閱付款（綠界信用卡定期定額）接法規劃

> 2026-10-07 起草（CEO 派工；Andy 給的參考：對方網站接 PayUni 定期定額的付款頁 `scratchpad/plans/167.png`）。
> **只是規劃，還沒實作。** 現在訂閱頁的彈窗走「送出訂閱申請 → 客服開通」（`/v1/subscribe/request`），不收錢、不承諾自動扣款或隨時取消。

## 0. 先要確認的事（查不到就不能動工）

| 項目 | 現況 | 怎麼確認 |
|---|---|---|
| 綠界**個人會員**能不能開「信用卡定期定額」 | **查不到**。WebSearch 只拿到 API 文件（定期定額、PeriodReturnURL、ReAuth／Cancel），沒有個人會員的申請條件 | Andy 登入綠界廠商後台看「信用卡收款」可開的服務；或打客服問。若只限公司／行號，要先辦行號或改用其他金流 |
| 發票 | 個人會員通常不能開統一發票；要開電子發票得有營業登記 | 同上 |
| 條款 | `#terms` 要補「訂閱、續扣、取消、退款」條文 | 法遵／Andy 定稿後才能上「立即訂閱」 |

## 1. 流程

```
訂閱頁彈窗（勾選同意條款）
  → POST Worker /v1/checkout/create { plan, period }（帶登入權杖）
      Worker：查範本價格（後端為準，不信前端）→ 建 orders 列（status=pending）
             → 依綠界規格組 AioCheckOut 參數＋CheckMacValue（HashKey／HashIV 只放 Worker secret）
      回前端 { action, fields }
  → 前端自動送出 form 到綠界付款頁（信用卡＋定期定額）
  → 第 1 期授權結果：綠界 server POST → Worker ReturnURL（驗 CheckMacValue → orders.status=paid → perm 指定方案＋expires）
     使用者瀏覽器 → OrderResultURL／ClientBackURL 回 #pricing/done
  → 第 2 期起：綠界 POST → Worker PeriodReturnURL（成功：延長 expires；失敗：記錄、寄信、寬限 N 天後退回註冊會員）
```

- 開通權限沿用現有 `perm` 表（plan＋expires），**不另做一套**；到期退回免費會員的邏輯已經有（admin-v2）。
- 前端不改價：訂單金額只從 Worker 的 plans.price／price_year 取。

## 2. 需要的欄位

`orders`（Worker 新表，只加不改）：`id`（我方訂單號＝MerchantTradeNo，≤20 碼英數）、`uid`、`email`、`plan`、`period`（month／year）、`amount`、
`status`（pending／paid／failed／cancelled／refunded）、`gwid`（綠界 TradeNo）、`period_no`（已扣期數）、`created`、`updated`、`raw`（最後一次回傳，去掉卡號）。

送綠界的定期定額參數（依官方文件）：`PeriodAmount`、`PeriodType`（M／Y）、`Frequency`（1）、`ExecTimes`（月繳上限 99、年繳 9）、`PeriodReturnURL`。

## 3. 取消、退款、對帳

- **取消**：會員在帳號頁按「取消續訂」→ Worker 呼叫綠界定期定額訂單作業 `Cancel`（停止之後的授權）→ 已付的期間用到 expires 為止。
- **退款**：信用卡退刷走綠界後台或 API（全額／部分）；Worker 標 refunded 並把 expires 改成今天。退款規則要先寫進條款。
- **扣款失敗**：綠界提供 `ReAuth`（重新授權）；我們先寄信、保留 3 天再退回註冊會員。
- **對帳**：每天 alarm 用「定期定額訂單查詢」比對 orders 與綠界紀錄（期數、金額、狀態），不一致寫進管理區「訂閱申請」頁並標紅。

## 4. 安全

- HashKey／HashIV 放 Cloudflare Worker secret，不進 repo。
- 回傳一律驗 CheckMacValue＋金額＝orders.amount；同一 TradeNo 重送要冪等（只開通一次）。
- 回傳端點不需要 Origin 檢查，但要限制只收綠界的回傳格式。

## 5. 預估工時（不含等綠界審核）

| 項目 | 估時 |
|---|---|
| Worker：orders 表、create、ReturnURL／PeriodReturnURL、CheckMacValue、node 測試 | 6～10 小時 |
| 前端：彈窗改「立即訂閱」＋送出 form、完成頁、帳號頁取消續訂 | 3～5 小時 |
| 管理區：訂單列表、退款標記、對帳結果 | 3～4 小時 |
| 測試環境（綠界測試商店）走完首期＋續扣＋取消＋退款 | 3～4 小時 |
| **合計** | **15～23 小時** |

依據：現有訂閱申請與 perm 開通流程已經有，主要新增是訂單表與兩個回傳端點。

來源（只拿到搜尋摘要）：綠界全方位金流 API 文件 [定期定額付款結果通知](https://developers.ecpay.com.tw/?p=5631)、[信用卡定期定額訂單作業](https://developers.ecpay.com.tw/2900/)、[定期定額訂單查詢](https://developers.ecpay.com.tw/2892/)。
