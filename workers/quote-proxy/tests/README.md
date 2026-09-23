# Worker 離線驗收

這三支是**唯一測得到 `worker.js` 的東西**，所以一定要留在 repo 裡。

## 為什麼需要它們

Claude 的容器連不出去（連 `miaozike.github.io` 與 `workers.dev` 都打不開，
出口代理回 403／`EGRESS_BLOCKED`），所以「把 Worker 部署上去再打一打」在開發當下做不到。
這三支的做法是：**用 Node 跑真的 `worker.js`**，把 `fetch`／`caches`／時鐘換成假的，
在本機把行為逐條驗出來。

2026-09-23 以前它們放在暫存區，容器一重啟就消失（那天真的重啟過一次）。
現在收進 repo。

## 怎麼跑

```
node workers/quote-proxy/tests/worker_check.mjs      # 現貨 SSE（/stream）16 條
node workers/quote-proxy/tests/worker_closed.mjs     # 非交易時段行為 4 條
node workers/quote-proxy/tests/futstream_check.mjs   # 夜盤 SSE（/futstream）29 條
```

不需要任何相依套件，也不會連外網。**改過 `worker.js` 就跑一次**。

## 它們保證什麼、不保證什麼

**保證**：邏輯層面的行為 —— 壞代號會不會擋、值沒變會不會亂推、節流有沒有生效、
多條連線會不會讓上游請求等比例暴增、非交易時段會不會空轉、
以及 **POST 的請求有沒有帶 `cf` 快取選項**（見下）。

**不保證**：真機行為。`TransformStream`、`ctx.waitUntil`、長連線的 CPU 累加
在 Cloudflare 的 workerd 上到底怎麼跑，這裡證明不了。
要確認只有兩條路：部署後開 `/health` 看 `features`，
或在 Actions 跑 `scripts/probe_sources.py`（那台 runner 連得到 Cloudflare）。

## ★ 最重要的那一條斷言：POST 不准帶 `cf` 快取選項

2026-09-23 Andy 一天之內回報三次「夜盤沒有數值」，真正的斷點是
`/fut` 與 `/futchart`（都是 **POST**）帶了 `cf: { cacheTtl, cacheEverything: true }`
—— **那組選項只對 GET 有效**，帶著它送出去會讓子請求出錯，Cloudflare 對外回 **520**。
完整病歷在 `DECISIONS.md #255`。

`futstream_check.mjs` 有一條原始碼結構掃描永久守住它，
而且**同一條也複製進 `scripts/_uitest.py` 的「夜盤推送」段落**（那份跟著前端關卡一起跑）。

⚠ 寫那條掃描時踩過一個**假綠**：用 `/\*[\s\S]*?\*\//g` 抹註解，
結果 `worker.js` 裡的 `'Accept': 'application/json, text/plain, */*'` 那個 `/*`
被當成註解開頭，一路吃掉 1.2KB 真程式碼，於是「掃不到問題」看起來像通過。
正確做法是**逐字元走一遍**，自己記住現在在字串裡還是註解裡。
