# 每日選題清單 JSON 規格（`site/social/menu_latest.json`）

> 2026-10-19 起：Andy 在網站「管理區 → 社群選題」（`#admin/social`）勾選當天要做的題目，不再回編號。
> 這個檔由**社群媒體部每天 commit**，不是 build 產物（不在 `site/data/`，不會被工作流覆蓋）。
> 人看的版本仍是 `daily_menu/<日期>.md`（格式見 `daily_menu/_template.md`）；JSON 是同一份內容的機器版，兩者編號要一致。

## 位置與更新方式
- 檔案：`site/social/menu_latest.json`（網站上的網址 `social/menu_latest.json`）。
- 每天整份覆蓋；舊的留在 `docs/marketing/social_unit/daily_menu/` 的 md 就好，不另存 JSON 歷史。
- ⚠ repo 與網站都是 public：這個檔**任何人用網址都讀得到**。頁面只給管理者看，但檔案本身不是機密——
  只放「題目與內文方向」，不放金鑰、持股、成本價、未公開的合約內容。

## 欄位

| 欄位 | 型別 | 說明 |
|---|---|---|
| `date` | 字串 `YYYY-MM-DD` | 清單日期（台北）。頁面會拿它跟今天比，不是今天就提醒「這是舊清單」。 |
| `sample` | 布林，可省略 | `true`＝範例資料。頁面頂端出現「範例資料」橫幅，送出的 Issue 標題加「（範例）」。正式清單不要帶這欄。 |
| `note` | 字串，可省略 | 給管理者看的一句話（例如今天哪幾項趕時效）。 |
| `items` | 陣列，6～8 筆 | 題目清單。 |

`items[]` 每一筆：

| 欄位 | 型別 | 說明 |
|---|---|---|
| `id` | 字串 | `D` ＋ 月日 4 碼 ＋ `-` ＋ 序號，例 `D1019-3`。同一天內不重複；Issue 與指令都用它對應。 |
| `kind` | 列舉 | `最新消息`｜`產業延伸`｜`精選文章`｜`總經名詞`（對應模板的四類；一份清單約 2／2／1～2／1）。 |
| `title` | 字串 | 題目，可直接當封面標題。 |
| `will_cover` | 字串陣列，3 筆 | 「這次內文會講」三個重點，白話一行一個。 |
| `chart` | 物件 `{has:布林, note:字串}` | `has` 是否有圖表；`note` 寫哪一張（網站哪個分頁的真實截圖，或本部自製）。`has=false` 時 `note` 給空字串。 |
| `images_needed` | 字串陣列 | 圖片需補充：比比現成素材寫素材名，需要新畫的寫清楚畫什麼（交 GPT）。沒有就給 `[]`。 |
| `verified` | 物件 `{status, who}` | `status`＝`已查證`｜`待查證`；`who`＝查證人（已查證）或要找誰（待查證）。待查證的項目不算「可立即發」。 |
| `output` | 字串 | 預估產出（Reels 幾秒、輪播幾張、Threads 短文或串、站內長文字數）。 |
| `flags` | 字串陣列 | 法遵紅旗；有任何一個就在卡上標 ⚠。慣用值：`點名個股`、`地緣敏感`、`涉及價格預測`、`引用未公開消息`。沒有就給 `[]`。 |

## Andy 勾選之後的流程（v1，零後端）
1. 頁面按「送出選擇」→ 在新分頁打開預填好的 GitHub 新 Issue：
   - repo：`MiaoZiKe/tw-rotation`；標題：`每日選題勾選 YYYY-MM-DD`（範例資料時尾巴加「（範例）」）；label：`social-pick`。
   - 內文：每個被勾的項目一行 `- [x] <編號> <題目>`，最後一行 `指令：產出 <編號>、<編號>，交 GPT 交接包`。
   - Andy 在手機 GitHub 按「Submit new issue」即完成。
2. 本部用 GitHub 工具列出 label 為 `social-pick` 的 Issue，讀內文裡的編號，依 `gpt_handoff/` 產出交接包。
3. 備援：頁面的「複製指令」按鈕複製同一行指令，Andy 直接貼進對話。
4. 勾選狀態另存在 Andy 瀏覽器的 localStorage（`tw.social.pick`，依清單日期分開），重新整理不會掉；這只是方便，不是交付憑證，交付以 Issue 或對話為準。

## 前置（一次性）
- repo 要先有 label `social-pick`（沒有的話，預填連結的 label 會被 GitHub 忽略，Issue 仍可建立，只是沒標籤）。

## 排程設定 JSON（`schedule`，Issue label `social-schedule`）
> Andy：「生產的時間、日期、頻率、類型我可以上面直接設定」。頁面「產主題設定」區塊產生預填 Issue；本部讀 label 為 `social-schedule` 的**最新一則**，內文裡 ```json 區塊就是設定。

```json
{ "v": 1, "tz": "Asia/Taipei",
  "types": [{"kind": "最新消息", "n": 2}, {"kind": "產業延伸", "n": 2}],
  "freq": "daily | weekday | days | date | now",
  "days": [1, 2, 4],
  "date": "2026-10-25",
  "times": ["07:30", "21:50"] }
```
| 欄位 | 說明 |
|---|---|
| `types[]` | 要產哪些類型、各幾項（1～5）。沒列的類型不產。 |
| `freq` | `daily` 每天｜`weekday` 週一到五｜`days` 指定星期幾（看 `days`）｜`date` 只跑 `date` 那一天｜`now` 立刻產一份（「立刻產一份」鈕送出，`times` 為空）。 |
| `days` | 只在 `freq=days`：0＝週日…6＝週六。 |
| `date` | 只在 `freq=date`：`YYYY-MM-DD`（台北）。 |
| `times` | 台北時間 `HH:MM`，可多個；預設 `21:50`。 |

- 「立刻產一份」的 Issue 標題是「立刻產選題清單 YYYY-MM-DD」，本部看到就當天補產，不改既有排程。
- ⚠ 靜態站不能直接改排程：設定在**下一個處理週期（最多數小時）**才生效；要立刻生效，在對話告訴 CEO。頁面上有明講。
- 設定另存 Andy 瀏覽器 localStorage（`tw.social.sched`），只是方便，交付以 Issue 為準。
- v2：改存管理區儲存後，本部直接讀，不必靠 Issue 與人工轉達（見回報的 v2 評估）。
