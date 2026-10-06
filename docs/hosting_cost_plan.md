# 上架主機成本與備援規劃（2026-10-06，resource-auditor）

> 查證日期：2026-10-06。價格只引用 WebSearch 摘要，原文頁面點不進去（出口代理擋 WebFetch）；正式付款前請到各家官方價目頁再看一次。

## 建議方案與每月花費

| 月活使用者 | 靜態網站 | 會員與報價 Worker | GitHub Actions | 每月合計（美元） |
|---|---|---|---|---|
| 1 千 | Cloudflare Pages 免費方案 | Workers 付費方案，月費 5 美元（盤中輪詢已超過免費方案每日 10 萬次） | 免費（public repo） | **約 5 美元** |
| 1 萬 | Cloudflare Pages 免費方案 | 5 美元月費，加上超量約 10 美元 | 免費 | **約 15 美元** |
| 10 萬 | Cloudflare Pages 免費方案（不計流量） | 5 美元月費，加上超量約 127 美元；把輪詢改成推播後約 20 美元 | 免費 | **約 135 美元（優化後約 25 美元）** |

結論：**不需要買傳統主機（VPS）**。開始收費之前，靜態網站要從 GitHub Pages 搬到 Cloudflare Pages，原因有兩個：一是 GitHub Pages 條款禁止用來經營商業或 SaaS 網站；二是它有每月 100 GB 的軟性流量上限，月活 1 萬人時就會超過。

## 一、各平台上限（附來源）

| 平台 | 重點數字 | 商業使用 | 來源 |
|---|---|---|---|
| GitHub Pages | 網站最大 1 GB；流量每月 100 GB（軟性上限）；建置每小時 10 次（用 Actions 部署不受這條限制） | **不准**當作商業、電商或 SaaS 網站的免費主機 | [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) |
| Cloudflare Pages 免費方案 | 每月 500 次建置；最多 2 萬個檔案；單檔 25 MiB；官方文件沒有寫流量上限 | 可以 | [Pages limits](https://developers.cloudflare.com/pages/platform/limits) |
| Cloudflare Workers | 免費方案每天 10 萬次請求、每次請求 10 毫秒 CPU；付費方案月費最低 5 美元，含每月 1,000 萬次請求，超過的部分每百萬次 0.30 美元，CPU 每百萬毫秒 0.02 美元 | 可以 | [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/) |
| Durable Objects | 免費方案每天 10 萬次請求、1.3 萬 GB-s；付費方案每月含 100 萬次請求（超過每百萬次 0.15 美元）與 40 萬 GB-s（超過每百萬 GB-s 12.5 美元） | 可以 | [DO pricing](https://developers.cloudflare.com/durable-objects/platform/pricing) |
| GitHub Actions | public repo 使用標準 runner 免費；大型 runner 一律收費 | — | [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) |
| Vercel | Hobby 方案 100 GB 流量，**禁止商業使用**；Pro 方案每人每月 20 美元，含 1 TB 流量 | Hobby 不可以 | [第三方比較](https://www.getmonetizely.com/articles/vercel-vs-netlify-which-developer-platform-has-better-pricing-for-your-modern-web-projects)（低信心，不是官方來源） |
| Netlify | 免費方案 100 GB 流量、允許商業使用；Pro 方案每人每月 19 美元，含 1 TB 流量 | 可以 | 同上（低信心；Netlify 近年改成點數計費，要以官方價目為準） |

## 二、流量估算（依 repo 實測）

- 自家 JS 與 CSS 共 4.5 MB；其中 `app.js` 原始大小 998 KB，gzip 後 375 KB（`gzip -c | wc -c` 實測）。JS 與 CSS 整體壓縮後估約 1.5 MB。
- `site/data/*.json` 頂層 42 支共 15.6 MB，最大一支是 fundamental.json，1.7 MB。一個人一次只會開其中幾頁，估每次瀏覽抓 2～4 MB 原始資料，gzip 後約 1 MB。
- 估算口徑：第一次開站約 2.5 MB，之後再開約 1 MB（JS 已經在快取裡）。每位使用者每月 20 次，**約 22 MB／人／月**。
  - 1 千人約 22 GB，1 萬人約 220 GB，10 萬人約 2.2 TB。換句話說，月活 5 千人左右就會頂到 GitHub Pages 的 100 GB 軟性上限。
- 報價 Worker：盤中每 5 秒一次（`site/live.js` 的 `MIS_WINDOW_MS = 5000`），每開一小時就是 720 次請求。
  假設 30% 的使用者每個交易日開 1 小時、每月 20 天：
  - 1 千人：每月約 430 萬次，每天約 21 萬次。**已經超過免費方案每天 10 萬次**，所以需要月費 5 美元的付費方案，用量仍在方案內含的 1,000 萬次以內。
  - 1 萬人：每月約 4,300 萬次，超過的部分約 10 美元。
  - 10 萬人：每月約 4.3 億次，超過的部分約 127 美元。
- 以上使用率（30%、1 小時、每月 20 次）是**假設值**，不是量測值。上線後請用 Cloudflare 後台的實際請求數重算一次。

## 三、當機怎麼辦

1. **靜態網站雙站部署**：在 `pages.yml` 增加一步，把同一份 `site/` 同時部署到 Cloudflare Pages（可以用 wrangler pages deploy）。兩邊內容一樣，平常就是兩份。
2. **自訂網域**：要買一個網域，一年大約 10～15 美元（這是一般行情，沒有查證；Cloudflare Registrar 以成本價出售）。DNS 交給 Cloudflare 管。主站當機時，把 CNAME 指到另一邊；DNS 的 TTL 設成 60～300 秒，**切換生效約 1～5 分鐘**。沒有自訂網域的話，使用者記的是 github.io 網址，就沒辦法切換。
3. **報價**：已經有 Deno 備援（`deploy-deno.yml`）。前端連不上 Worker 時會退避重試（`live.js` 的 `SSE_BACKOFF`）。
4. **會員 Worker（Durable Object）**：沒有第二家可以接手，因為資料在 DO 裡面。當機期間只能讓網站降級：唯讀瀏覽照常運作，登入暫時不能用。

## 四、流量過大怎麼辦

- **CDN 快取**：Cloudflare Pages 本身就是 CDN。JSON 每天只變一次，可以設 `Cache-Control: max-age=600` 以上；JS 已經有版本戳（`stamp_assets.py`），可以設成長期快取。
- **報價是最大的成本來源**：
  - 在 Worker 裡用 edge cache 共用 5 秒快照（`worker.js` 已經用了 `caches.default`）。但每個請求仍然算一次 Worker 請求，所以這只省得到 mis 的上游流量，省不到請求費。
  - 真正能省錢的做法是**不要每個人自己輪詢**：分頁不在前景時停止輪詢（document.hidden），或改成一條 SSE 連線推播。
  - 只有付費會員才給 5 秒更新，免費使用者改成 60 秒。這樣可以把請求數降到原本的十分之一左右。
- **Worker 限流**：用 Cloudflare 的 Rate Limiting 規則，或在 DO 內依 IP 或帳號計數，限制每人每分鐘的請求數。
- **自動擴充**：Workers 與 Pages 都是無伺服器架構，會自動擴充，不需要自己加機器。風險在帳單，不在當機。建議在 Cloudflare 後台設用量通知。
