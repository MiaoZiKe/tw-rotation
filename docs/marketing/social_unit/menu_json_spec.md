# 每日選題 JSON 與送出格式規格（menu_json_spec）

> 2026-10-16 Andy 需求：在網站上選今日要產的主題、並能自己設定「產什麼類型、幾項、幾點、哪幾天、多久一次」。
> 頁面：管理區「社群選題」`#admin/social`（僅管理者可見，程式 `site/socialpick.js`）。
> 本部（社群媒體部）每天把選題清單 commit 成 `site/social/menu_latest.json`；網站只讀、不寫。
> `daily_menu/<日期>.md` 仍是人看的版本，兩份內容要一致（JSON 由同一份清單轉出）。

## 一、`site/social/menu_latest.json`（本部每日 commit，不是 build 產物）

```json
{
  "version": 1,
  "date": "2026-10-16",
  "example": false,
  "updated": "2026-10-16T08:30:00+08:00",
  "items": [
    {
      "id": "D1016-1",
      "kind": "最新消息",
      "title": "可直接當封面標題的題目",
      "will_cover": ["重點一", "重點二", "重點三"],
      "chart": { "has": true, "note": "網站「熱力圖」截圖" },
      "images_needed": ["比比素材：news＋magnifier", "需 GPT 生圖：流程示意圖"],
      "verified": { "status": "已查證", "who": "semi-chain-analyst" },
      "output": "Reels 30 秒＋Threads 短文",
      "flags": ["點名個股"]
    }
  ]
}
```

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `version` | 整數 | 是 | 目前 `1`。格式改版時加 1，前端遇到不認得的版本會提示而不是亂畫 |
| `date` | `YYYY-MM-DD` | 是 | 台北日期。勾選記錄以日期分開存，隔天自動是新的一份 |
| `example` | 布林 | 否 | `true`＝範例資料，頁面會掛「範例」標籤與黃字提醒。**正式清單一律省略或 `false`** |
| `updated` | ISO 時間 | 否 | 清單產出時間，顯示在頁首 |
| `items` | 陣列 | 是 | 一份 6～8 項（最新消息 2、產業延伸 2、精選文章 1～2、總經或名詞 1，見 `_template.md`）。前端最多顯示 30 項 |
| `items[].id` | 字串 | 是 | 唯一編號，只收英數、`-`、`_`（≤16 字）。日常題 `D<MMDD>-<序>`，精選文章 `A<序>` |
| `items[].kind` | 列舉 | 是 | `最新消息`｜`產業延伸`｜`精選文章`｜`總經名詞`。其他值前端會原字顯示成灰色標籤 |
| `items[].title` | 字串 | 是 | 題目（≤60 字） |
| `items[].will_cover` | 字串[3] | 是 | 「這次內文會講」三點，一點一行，白話。不足 3 點照實顯示 |
| `items[].chart` | 物件 | 是 | `has`＝有／無圖表；`note`＝哪一張（網站哪個分頁的真實截圖，或本部自製的簡單圖）；無圖表時 `note` 可寫原因 |
| `items[].images_needed` | 字串[] | 是 | 圖片需補充。比比現成素材寫素材名；要新畫的寫清楚畫什麼（交 GPT）。全部現成就給 `[]` |
| `items[].verified` | 物件 | 是 | `status`＝`已查證`｜`待查證`；`who`＝查證者（待查證時寫找誰） |
| `items[].output` | 字串 | 是 | 預估產出（形式與長度），例如「Reels 30 秒＋Threads 短文」「輪播 6 張」 |
| `items[].flags` | 字串[] | 是 | 法遵紅旗（點名個股、地緣敏感、涉及預測…）。沒有給 `[]`；有任何一項畫面就標 ⚠ |

安全：所有字串前端一律當純文字（跳脫後才放進畫面），不收 HTML。檔案缺失、JSON 壞掉、`items` 空時，頁面顯示空狀態與原因，不留黑方塊。
隱私：`site/` 是公開的，這份 JSON 任何人都能直接打開網址讀到；**只放可公開的題目與重點**，不放金鑰、未發佈的付費內容、Andy 的持股。「僅管理者可見」指頁面入口，不是檔案保密。

## 二、送出選擇（v1 零後端）：預填 GitHub 新 Issue

網站沒有寫入後端，所以「送出」＝開一個預先填好內容的 GitHub 新 Issue 頁（repo `MiaoZiKe/tw-rotation`），Andy 在 GitHub 按 **Submit new issue**（送出新問題）才算送出。

### 2-1 勾選（label `social-pick`）

- 連結：`https://github.com/MiaoZiKe/tw-rotation/issues/new?title=<>&body=<>&labels=social-pick`
- `title`：`每日選題勾選 YYYY-MM-DD`
- `body`（機器讀最後的註解行，人讀上面的清單）：

```
日期：2026-10-16
被勾 2 項（共 6 項）：
- [x] D1016-1｜最新消息｜題目一
- [x] D1016-3｜精選文章｜題目三
沒勾的不做。
<!-- social-pick {"date":"2026-10-16","picked":["D1016-1","D1016-3"]} -->
```

- 本部讀取方式：搜尋 label `social-pick` 的 Issue，解析註解行 JSON 的 `picked`。
- 「複製指令」備援＝複製等價的 `gh issue create -R MiaoZiKe/tw-rotation -t ... -b ... -l social-pick`；
  也可以直接對 CEO 說「勾 D1016-1、D1016-3」。

### 2-2 產主題設定（label `social-schedule`）

- `title`：設定排程 `每日產主題設定 YYYY-MM-DD`；立刻產一份 `立刻產主題 YYYY-MM-DD HH:mm`
- `body`：上半是人看得懂的摘要，下半是 JSON 區塊（用 `social-schedule` 圍欄方便解析）：

````
每天 21:50、22:30（台北時間）產：最新消息 2、產業延伸 2、總經名詞 1（共 5 項）。
設定會在下一個處理週期（最多數小時）生效，要立刻生效請在對話告訴 CEO。

```json social-schedule
{ ...下面的 schedule JSON... }
```
````

## 三、schedule JSON

```json
{
  "version": 1,
  "action": "set_schedule",
  "tz": "Asia/Taipei",
  "kinds": { "最新消息": 2, "產業延伸": 2, "精選文章": 0, "總經名詞": 1 },
  "times": ["21:50", "22:30"],
  "frequency": "weekly",
  "days": [1, 2, 3, 4, 5],
  "date": null,
  "created": "2026-10-16T21:40:00+08:00"
}
```

| 欄位 | 說明 |
|---|---|
| `version` | `1` |
| `action` | `set_schedule`＝設定排程（取代舊設定）；`run_now`＝立刻產一份（一次性，不改排程） |
| `tz` | 固定 `Asia/Taipei`，所有時間都是台北時間 |
| `kinds` | 四種類型各產幾項（0～9 的整數）；`0` 或缺＝不產該類型。至少一種大於 0 |
| `times` | 執行時間，`HH:mm` 24 小時制，1～6 個時段，由早到晚、不重複。`run_now` 省略 |
| `frequency` | `daily`＝每天；`workdays`＝僅工作日（週一至週五，國定假日是否略過由本部決定並在回報寫明）；`weekly`＝自訂星期；`once`＝只跑一次 |
| `days` | 只在 `frequency=weekly` 有意義：1＝週一…7＝週日，多選；其他情況為 `[]` |
| `date` | 只在 `frequency=once`：指定那一天 `YYYY-MM-DD`（不得早於今天）；其他情況為 `null` |
| `created` | 設定產生時間（ISO，台北） |

`run_now` 範例：`{"version":1,"action":"run_now","tz":"Asia/Taipei","kinds":{"最新消息":1,"產業延伸":1,"精選文章":0,"總經名詞":0},"created":"..."}`。
`once` 範例：`"frequency":"once","date":"2026-10-20","days":[]`。

### 生效時間（如實）
Issue 要等本部的下一個處理週期才會被讀取（最多數小時），**不是即時**。要立刻生效，直接在對話告訴 CEO；頁面上也明講這句。
排程目前不會自己跑：真正定時執行需要排程任務或 Actions，**建立前須 Andy 同意**（`gpt_handoff/README.md` 的 ⚠）。

## 四、v2 評估（只評估、不實作）：改存管理區 Worker

**目標**：Andy 在頁面按「儲存」就直接寫進 account Worker 的管理區儲存，本部直接讀，不必經過 GitHub Issue。

| 項目 | 內容 |
|---|---|
| 新增端點 | `POST /v1/admin/social/get`（讀目前勾選與排程）、`/v1/admin/social/put`（寫）。沿用既有 `/v1/admin/*` 命名與 CORS（只認 Origin `https://miaozike.github.io`）。本部讀取用一支唯讀端點 `GET /v1/social/pending`，以 Worker 側的服務金鑰（Secrets，不進 repo）驗證，不用 Andy 的登入權杖 |
| 儲存 | Worker 既有的 KV／D1（沿用 notices 的做法）：`social:pick:<date>`（勾選陣列）、`social:schedule`（schedule JSON，只留最新一份）。每筆帶 `updated`、`by`（管理者 email）與版本號，避免兩個裝置互相覆蓋 |
| 權限 | 寫入限 `user.admin`（同 `/v1/admin/notices/put`）；排程屬於會觸發對外動作的設定，建議再限擁有者 `owner`。本部讀取端點與「管理者登入」分開，且只回「已勾選、待處理」的最小欄位，不回 email |
| 預覽版 | `preview_boot.js` 已擋 `/v1/admin/*/put`，v2 在預覽版會自動唯讀，要測寫入須在正式站 |
| 前端改動 | `socialpick.js` 的「送出」改成呼叫端點並顯示「已存（時間）」；Issue 連結保留為備援（Worker 掛了仍可用）。localStorage 繼續當離線草稿 |
| 風險 | ① 新端點＝新攻擊面：要有大小上限（kinds/times 長度）、欄位白名單、速率限制 ② 服務金鑰外洩＝別人能讀待辦：金鑰輪替流程要寫進 Runbook ③ 排程寫進去不等於會執行，仍需本部的排程任務去讀，真正自動化還是要 Andy 同意建立排程 ④ Worker 部署與前端部署不同步時（前端先上）要 404 時退回 Issue 路線 ⑤ 資料在 Worker 就不在 repo，備份與稽核紀錄要另外處理 |
| 工作量 | Worker 端點＋測試約 0.5 天；前端接線＋_uitest 約 0.5 天；加上金鑰與權限審查，合計 1～1.5 天 |
| 建議 | 先用 v1 跑一週，確認 Andy 真的天天用、欄位穩定，再做 v2 |
