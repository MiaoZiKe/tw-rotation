# workers/ — 即時報價代理

## 為什麼要有這一層

網站是 GitHub Pages 上的純靜態頁。盤中要每分鐘更新價格，只可能由**瀏覽器自己去抓**
（GitHub Actions 的 cron 最短 5 分鐘，而且免費層會延遲，本專案實測過延遲 4 小時）。

但瀏覽器抓不到證交所那支即時報價。2026-09-14 15:08 從 `https://miaozike.github.io` 實測：

```
fetch('https://mis.twse.com.tw/stock/api/getStockInfo.jsp?…')            → TypeError: Failed to fetch
fetch('https://mis.twse.com.tw/stock/api/getStockInfo.jsp?…', {mode:'no-cors'}) → 通
```

**連得到但讀不到 ＝ 被 CORS 擋的**，不是網路不通。所以中間要有一層 Worker
幫忙轉一手並補上 `Access-Control-Allow-Origin`。

Cloudflare Workers 免費方案：每天 10 萬次請求。盤中每分鐘一次、一天 5.5 小時 ≈ 330 次，
綽綽有餘。**不用綁信用卡。**

---

## 部署

> **2026-09-18 起已自動化，正常情況下這一節你不用看。**
> `.github/workflows/deploy-worker.yml`：`workers/quote-proxy/**` 一推上 main 就自動
> `wrangler deploy`，並驗證線上真的換成新版。只要先設好 `CLOUDFLARE_API_TOKEN`
> 與 `CLOUDFLARE_ACCOUNT_ID` 兩個 repo Secret（步驟見 `SETUP.md` 第 8 節）。
> 下面這段留著，是給「第一次還沒有 Cloudflare 帳號」與「自動部署壞掉要手動救」用的。

### 手動部署（第一次建帳號，或自動部署壞掉時）

1. 開 <https://dash.cloudflare.com/sign-up>，用 email 註冊，驗證信箱。
   （問你要不要加網域就選跳過／Skip，我們只用 workers.dev 子網域。）
2. 左側 **Compute** → **Workers & Pages** → 右上 **Create application**。
3. 在「Make something new」那張卡選 **Start with Hello World!**（地球圖示那個）。
   **不要**選 Connect GitHub／GitLab（那是從 repo 自動建置）、
   也不要選 Select a template 或 Upload your static files。我們要的是一個空的 Worker。
4. 名稱填 `tw-quote`（隨便取，但記住它）→ **Deploy**。
   問你 TypeScript 還是 JavaScript 的話選哪個都行，這支程式碼兩邊都吃。
5. 部署完成後按 **Edit code**（或 **Continue to project** → 右上 **Edit code**）。
6. 把編輯器裡原本的範例程式**全部刪掉**，貼上 `workers/quote-proxy/worker.js` 的完整內容。
7. 右上角 **Deploy**（有些版本寫 **Save and deploy**）。
8. 記下網址，長這樣：`https://tw-quote.<你的帳號名>.workers.dev`

### ★ 2026-09-23：Worker 改版了（新增 SSE 推送），**要重新貼一次程式碼**

新增了兩個端點，網站會優先用它們，連不上就自動退回原本的輪詢。
**所以不貼也不會壞，只是數字跳得比較鈍。**

| 端點 | 服務誰 | 不貼的話 |
|---|---|---|
| `/stream` | 加權／櫃買／個股的**現貨**報價（mis.twse） | 退回每分鐘輪詢 |
| `/futstream` | **台指期夜盤**（期交所，Andy：「夜盤要即時推送」） | 退回每 60 秒輪詢 |

正常情況下 `.github/workflows/deploy-worker.yml` 會自動部署，你什麼都不用做。
如果自動部署沒跑成功（或你想自己確認一次），在 Cloudflare 後台這樣點：

1. 開 <https://dash.cloudflare.com/> 登入。
2. 左側 **Compute** → **Workers & Pages**。
3. 在清單裡點 **tw-quote**（就是當初取的那個名字）。
4. 右上角 **Edit code**（有些版本是先按 **Continue to project**，再按右上的 **Edit code**）。
5. 編輯器左邊的檔案清單點 **worker.js**，把裡面的東西**全選刪掉**，
   貼上這個 repo 裡 `workers/quote-proxy/worker.js` 的完整內容。
6. 右上角 **Deploy**（有些版本寫 **Save and deploy**）。跳出來問要不要部署就按確認。
7. 等它跑完（大約 10 秒），畫面上會出現 **Success**。

**怎麼確認真的換成新版了**（不用按任何指令，用瀏覽器開一個網址就好）：

```
https://tw-quote.<你的帳號名>.workers.dev/health
```

回應裡要看得到 `"features"` 而且裡面有 `"stream"` **和 `"futstream"`**：

```json
{"ok":true,"service":"tw-rotation quote-proxy","features":["quote","chart","y","fut","futchart","stream","futstream"],"session":"trade","futSession":"night"}
```

`session` 講的是**現貨盤**（09:00–13:35），`futSession` 講的是**台指期夜盤**
（15:00–翌日 05:00）。夜間 `session` 是 `closed` 而 `futSession` 是 `night`，這是對的 ——
兩個欄位本來就在講兩件事。

**沒有 `features` 這個欄位 ＝ 還是舊版**，再貼一次。

還有一個更簡單的看法：打開 <https://miaozike.github.io/tw-rotation/>，
看右上角「更新」旁邊那一行小字：

| 小字寫什麼 | 意思 |
|---|---|
| `即時 11:22　推送（SSE）` | 走的是新的推送，值一變就跳（約 5 秒） |
| `即時 11:22　每分鐘（輪詢）` | 走的是舊的輪詢，一分鐘跳一次 |
| `收盤 13:45　每 30 分（輪詢）` | 盤後，半小時對一次 |

**看到「輪詢」不代表壞掉** —— 它只是在告訴你現在走哪條路。
非交易時段本來就會顯示輪詢（Worker 不在盤中不開推送，免得空轉）。

### 驗證它活著

瀏覽器直接開這一行（把網址換成你的）：

```
https://tw-quote.<你的帳號名>.workers.dev/quote?ex_ch=tse_2330.tw
```

看到一包含有 `"c":"2330"`、`"n":"台積電"` 的 JSON 就成功了。

### 接到網站上

打開 <https://miaozike.github.io/tw-rotation/> → 右上「更新」旁邊的 **⚙** →
把 Worker 網址貼進去 → 按 **測試** 確認通了 → 按 **儲存**。

設定存在瀏覽器裡，所以**每台電腦、每個瀏覽器各設一次**。
兩台電腦都設好之後告訴我網址，我會把它寫進 `live.js` 的 `DEFAULT_PROXY` 當預設值，
以後換裝置就不用再設。

---

## 這支 Worker 刻意做的限制（不要拿掉）

| 限制 | 為什麼 |
|---|---|
| 只轉 `mis.twse.com.tw/stock/api/getStockInfo.jsp` 一個端點 | 開放式代理會被拿去當跳板，還會連累這個網域 |
| `ex_ch` 嚴格檢查（只收 `tse_`/`otc_` 開頭、`.tw` 結尾，最多 140 個） | 不讓任意字串往上游送 |
| 只有白名單 Origin 拿得到 CORS 標頭 | 別人的網站沒辦法拿你的 Worker 當免費 API |
| 邊緣快取 10 秒 | 多個分頁、連按更新只會真的打上游一次 |
| `/stream` 每 5 秒才問一次上游，而且走同一層邊緣快取 | mis 自己就寫 `userDelay: 5000`（它 5 秒才換一次快照）。打更密只會拿到一樣的東西，純粹浪費別人家的頻寬。**多個瀏覽器訂同一組代號時，真的打到 mis 的只有一次** |
| `/stream` 只有值真的變了才推 | 沒變就一個 byte 都不送，省流量也省 CPU |
| `/stream` 一條連線最多活 4 分鐘就自己收掉 | 免費方案**每次調用只有 10ms CPU**，長連線的 CPU 是累加的。壓短＋讓前端立刻重連比較安全；重連會拿到完整快照，畫面不會有缺口 |
| 非交易時段 `/stream` 給一份快照就收線 | 不要讓幾十條連線在夜裡空轉 |
| `/futstream` 問期交所報價 **10 秒**一次、分時序列 **60 秒**一次 | 分時序列（`getChartData1M`）的 `Ticks` 是**一分鐘一根**（fixture 實證），問得比 60 秒密在物理上拿不到新的一根，只會把 34KB 重抓一遍；報價只有 4.4KB 而且是秒級在動，所以值得問得密一點。10 秒也是網站日盤那三張圖既有的節奏 |
| `/futstream` 用**模組層記憶體**共用上游，不是邊緣快取 | 期交所那兩支是 **POST**。`cf: { cacheTtl, cacheEverything }` **只對 GET 有效**，帶在 POST 上會讓子請求出錯、Cloudflare 對外回 **520** —— 那就是 2026-09-23 夜盤三次空白的斷點（DECISIONS #255 ③）。**任何 POST 的 fetch 都不准帶 cf 快取選項** |
| 非夜盤時段 `/futstream` 一個上游請求都不打 | 夜盤時段外打 `MarketType=1`，期交所回的是**日盤最後一筆**。把它推出去就是「拿日盤冒充夜盤」，那是 Andy 明講不要的 |

### `/stream` 怎麼用（除錯時才需要看）

```
GET /stream?ids=tse_2330.tw|otc_3105.tw
```

回的是 SSE（`text/event-stream`），事件有這幾種：

| 事件 | 意思 |
|---|---|
| `hello` | 剛接上。附這一段的時段（`trade`／`edge`／`closed`）與輪詢間隔 |
| `quote` | 一包報價，格式**跟 `/quote` 的回應一模一樣**（前端才能共用同一套解析） |
| `idle` | 非交易時段，接下來會收線，請改用輪詢 |
| `bye` | 連線輪替（滿 4 分鐘），請立刻重連 |
| `warn` | 這一輪問上游失敗，但連線還活著 |
| `: hb …` | 心跳（註解行），讓中間的代理不要把連線當成死的 |

### `/futstream` 怎麼用（除錯時才需要看）

```
GET /futstream?session=night&symbol=TXFJ6-M
```

`symbol` 是近月合約代號（夜盤是 `-M` 結尾）。**不給也沒關係** ——
那樣只會推報價、不推分時序列；網站自己算得出代號，所以正常情況下都會帶。

| 事件 | 意思 |
|---|---|
| `hello` | 剛接上。附 `futSession`、兩個輪詢間隔、訂的是哪一支合約 |
| `fut` | 一包台指期報價，格式**跟 `/fut` 的回應一模一樣** |
| `futchart` | 一份分時序列，格式**跟 `/futchart` 的回應一模一樣** |
| `idle` | 現在不是夜盤時段，接下來會收線，請改用輪詢 |
| `bye` | 連線輪替（滿 4 分鐘），請立刻重連 |
| `warn` | 這一輪問上游失敗（`which` 說是哪一支），但連線還活著、另一支通常還是好的 |
| `: hb …` | 心跳 |

`fut` 與 `futchart` 的格式跟輪詢那兩支**一模一樣**是刻意的：前端兩條路共用同一套解析，
「退回輪詢」才不會變成「走一條沒人驗過的路」。

要多一個網域能呼叫，改 `worker.js` 最上面的 `ALLOW_ORIGINS`。

---

## 用 wrangler 部署（選用，比較適合之後要改程式時）

```bash
npm i -g wrangler
wrangler login
cd workers/quote-proxy
wrangler deploy
```

`wrangler.toml` 已經寫好了。
