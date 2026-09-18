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
