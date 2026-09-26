# 公司 Logo 的資料來源、條款查證與風險（2026-09-26）

Andy 2026-09-26 要在**搜尋結果**與**個股頁名稱旁**顯示公司 Logo。這份文件記錄資料端的來源選擇、
查證結果、商標風險，以及**怎麼整批關掉**。程式在 `pipeline/sources/logos.py`，
回補步驟在 `pipeline/run_backfill.py` 的 `backfill_logos()`，輸出在 `pipeline/build_payload.py` 的 `export_logos()`。

> ⚠ 這是資料來源白名單的**擴充**：原本的白名單只有 openapi.twse.com.tw、mis.twse.com.tw、FinMind（加上集保、櫃買、Yahoo 分 K）。
> Logo 這條新增了「各上市櫃公司自己的官網」與「Google 的 favicon 服務」兩種主機。
> 需求來自 Andy 本人（2026-09-26），但**要在 DECISIONS.md 補一條正式登記**（由 CEO 登記，爬蟲專家不自己改 DECISIONS）。

---

## 1. 結論

| 角色 | 來源 | 為什麼 |
|---|---|---|
| **主來源** | 公司自己的官網：首頁 `<link rel="apple-touch-icon">`、`<link rel="icon">`，再退到 `/apple-touch-icon.png`、`/favicon.ico` | 這是公司**自己公開給瀏覽器顯示**的圖示，我們抓的方式跟一般人用瀏覽器打開首頁一樣；apple-touch-icon 慣例是 180px，縮到 64px 最清楚；不依賴任何第三方非官方服務，也就沒有第三方條款的問題 |
| **備援** | Google favicon 服務 `https://www.google.com/s2/favicons?domain=<網域>&sz=64` | 官網首頁是 JS 渲染、擋雲端 IP、或連線太慢時，Google 常有快取；可以直接要 64px |
| 不採用 | DuckDuckGo `https://icons.duckduckgo.com/ip3/<網域>.ico` | 只回 16／32px 的 ICO，而且只看 `/favicon.ico`、不看 `<link rel=icon>` —— 拿得到的東西是主來源那條路的子集，當備援沒有增益 |
| 不准碰 | `www.twse.com.tw/rwd`、券商網站、付費圖庫、Clearbit／Brandfetch 這類商用 Logo API | 前兩個是既有紅線；付費或商用 API 的授權條款不允許我們把圖檔存進 public repo 再公開 |

網址從哪來：
- **上市**：`company_info` 的 `website` 欄（證交所 OpenAPI `t187ap03_L` 的「網址」）。2026-09-26 資料湖實測：上市 1,354 家非 ETF 有 1,095 家有網址。
- **上櫃／興櫃**：`company_info` 走 FinMind `TaiwanStockInfo`，**沒有網址欄**（實測 1,139 家上櫃、385 家興櫃全是空值）。
  所以新增資料表 `company_website`（key `code`），依序試：
  1. `openapi.twse.com.tw/v1/opendata/t187ap03_O`（證交所 OpenAPI，同主機已在用 `t187ap04_O`；**這支沒實測過**）
  2. `www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O`（`config.TPEX_ENDPOINTS` 早就登記；櫃買常對雲端 IP 回 403）
  3. 興櫃只試 `openapi.twse.com.tw/v1/opendata/t187ap03_R`（**沒實測過**）
  解析失敗會把回應前 200 字印進 log。**不碰** `mopsfin.twse.com.tw/opendata/*.csv`（不在白名單）。
  不寫進 `company_info` 是因為 `store.append()` 同 key 會整列以後到的為準，只帶網址的列會把名稱、產業蓋成空值。

---

## 2. 條款與穩定性查證（2026-09-26，WebSearch 摘要；容器打不開原文）

| 查什麼 | 查到的 | 信心度 | 來源 |
|---|---|---|---|
| Google s2 有沒有官方文件、條款、額度 | **沒有**。非官方、無文件、無 SLA，隨時可能改或停；沒有公開的額度，大量使用會被節流 | 中（多個第三方文件一致；Google 自己沒講） | [Logo.dev：Google Favicon API](https://www.logo.dev/docs/google-favicon-api)、[DEV：hidden google API](https://dev.to/derlin/get-favicons-from-any-website-using-a-hidden-google-api-3p1e)、[Ithy：rate limiting](https://ithy.com/article/google-favicon-api-rate-limiting-dqbj5yak) |
| Google s2 找不到時回什麼 | 回預設圖（常見是 16×16 地球）；新版 `faviconV2` 找不到時回 **HTTP 404** 附預設圖 | 中 | [Logo.dev](https://www.logo.dev/docs/google-favicon-api)、[Grokipedia：faviconV2](https://grokipedia.com/page/faviconV2)、[Simplr Blog](https://blog.simplr.sh/posts/google-favicon-api/) |
| DuckDuckGo ip3 條款與行為 | 非官方、無條款、無 SLA；只抓 `/favicon.ico`、不看 `<link rel=icon>`；只給 16／32px ICO；不存在的網站回 404 | 中 | [Brandfetch：DuckDuckGo Favicon API](https://docs.brandfetch.com/comparisons/duckduckgo-favicon-api)、[Logo.dev：DuckDuckGo](https://www.logo.dev/docs/duckduckgo-favicon-api)、[Oh Dear](https://ohdear.app/news-and-updates/how-we-added-a-favicons-to-our-site-list) |
| apple-touch-icon 的慣例尺寸 | 180×180 是標準尺寸（另有 120／152／167） | 高（多個技術文件一致） | [favicon.io](https://favicon.io/html-favicon/)、[Evil Martians](https://evilmartians.com/chronicles/how-to-favicon-in-2021-six-files-that-fit-most-needs)、[Chrome Lighthouse](https://developer.chrome.com/docs/lighthouse/pwa/apple-touch-icon) |
| 台灣商標法的「指示性合理使用」 | 商標法第 36 條第 1 項第 1 款：以符合商業交易習慣之誠實信用方法表示他人商品或服務的名稱等資訊、**非作為商標使用**者，不受他人商標權效力拘束；實務承認「指示性合理使用」 | 中（法條原文未讀到，摘要一致；判決個案差異大） | [全國法規資料庫：商標法第 36 條](https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=J0070001&flno=36)、[智慧財產局：合理使用案例](https://www.tipo.gov.tw/tw/trademarks/632.html)、[巨群：111 刑智上易 18 號解析](https://www.giant-group.com.tw/law-detail-1159.html) |
| 美國法的 nominative fair use | 三要件：不用商標就難以指稱、只用必要的量、不暗示贊助或背書；**Logo 比文字名稱更容易被認為「超過必要」** | 中 | [INTA：Fair Use of Trademarks](https://www.inta.org/fact-sheets/fair-use-of-trademarks-intended-for-a-non-legal-audience/)、[Wikipedia：Nominative use](https://en.wikipedia.org/wiki/Nominative_use)、[Chase Law Group](https://chaselawmb.com/nominative-fair-use/) |
| 上櫃公司基本資料有沒有「網址」欄 | 公開資訊觀測站的 `t187ap03_O` 欄位清單有「網址」；櫃買 OpenAPI 的 JSON 欄名是英文，**「網址」對應的英文欄名沒查到** | 低（欄名要等第一次實際回應才知道；程式用候選名稱＋「欄名含 web／網址」兩層容錯） | [政府資料開放平臺：上櫃公司基本資料](https://data.gov.tw/dataset/25036)、[櫃買 OpenAPI Swagger](https://www.tpex.org.tw/openapi/) |

⚠ 以上都是 WebSearch 的摘要，原文點不進去。「Google s2 找不到時一定回 404」這點不同來源講法不一
（也有人說回 200＋預設圖），所以程式**不只靠狀態碼**：過小（< 32px）、空白、同一張圖出現在 ≥ 3 個網域，三道都會擋。

---

## 3. 用途聲明（為什麼我們認為可以放 Logo）

- **用途是「識別公司」的指稱性使用**：Logo 只出現在該公司自己的名稱旁邊（搜尋結果、個股頁標題），
  用來讓讀者一眼認出「這一列是哪家公司」，跟寫出公司名稱是同一件事。
- **不修改圖形**：只做等比縮放到 64×64、透明補邊。不裁切、不拉伸、不改色、不重繪、不加濾鏡。SVG 不處理（縮放向量檔等於重畫一次）。
- **不暗示合作或背書**：網站不以任何公司的 Logo 當作自己的標誌，也不放在「合作夥伴」「推薦」這類語境。
  前端（UI 專家）應在頁尾或資料來源說明加一句：「公司 Logo 之商標權屬各該公司所有，本站僅用於識別，不代表任何合作或背書關係。」
- **尊重網站意願**：官網 robots.txt 不允許一般爬蟲抓首頁時，**連 Google 備援都不用**（用 Google 繞過去等於繞 robots）。

---

## 4. 風險（寫在前面，讓 Andy 或 legal-compliance 可以一次否決）

1. **repo 是 public**：`data/logos/*.png` 會跟著資料湖 commit 進 public repo，等於「在 GitHub 上散布約 2,000 家公司的商標圖檔」。
   比「網頁上顯示」多一層暴露。即使之後刪檔，**git 歷史裡還在**（要徹底移除得改寫歷史，而本專案禁止 force push）。
2. **Logo 的合理使用比文字名稱窄**：美國實務上 nominative fair use 對 Logo 較嚴（「只用必要的量」—— 寫名字就能識別，放 Logo 可能被認為超過必要）。
   台灣法的指示性合理使用有判決承認，但都是個案判斷。
3. **Google s2 是非官方服務**：隨時可能改網址、改行為或開始擋；使用非官方介面本身也可能違反 Google 的一般服務條款。
   它只是備援，停掉的影響是「少一些 Logo」，不會讓管線失敗。
4. **抓錯圖**：官網的 favicon 有時是架站商、CMS 或集團母公司的圖示。三道過濾（過小、空白、跨網域重複）擋得掉大部分，擋不掉的是
   「集團共用 Logo 被掛在子公司上」—— 這在事實上通常也對（同一個品牌），但不保證。
5. **額度與禮貌**：每輪最多 300 家、最多 15 分鐘、6 條執行緒、每個網域一輪只抓一次（robots.txt＋首頁＋最多 5 個圖檔候選）。

---

## 5. 關閉方式

**整批關掉（前端全部退回字母頭像）**：把 `pipeline/config.py` 的
```python
LOGOS_ENABLED = os.environ.get("LOGOS_ENABLED", "1").strip() not in (...)
```
預設值 `"1"` 改成 `"0"`，推上 main。效果：
- 回補不再抓（`logo_progress.json` 記 `skipped: "disabled"`，排程守門不會再為 Logo 放行）。
- 下一次部署時 `build_payload` 輸出空的 `logos.json`（`{}`），並刪掉 `site/data/logos/` —— 網站上立刻看不到任何 Logo。
- 也可以只在某個 workflow 的 `env:` 設 `LOGOS_ENABLED: "0"`。

**連 repo 裡的圖檔一起移除**：關掉之後再 `git rm -r data/logos` 推上去。
⚠ git 歷史裡仍會留著（本專案禁止改寫歷史）。如果法律上要求徹底移除，這一步必須由 Andy 決定是否另外處理。

**只移除某一家**：在 `data/logos/_index.json` 把那家的 `status` 改成 `"removed"` 並刪掉 `data/logos/<code>.png`。
`usable_codes()` 只輸出 `status == "ok"` 的代號，所以下一次部署前端就不會再顯示；`select_todo()` 也會永遠跳過 `removed`，不會再重抓。

---

## 6. 資料流與檔案

```
回補（每小時；計畫補齊後只在 Logo 還有事做時跑 --datasets logos）
  backfill_logos()
    ├─ company_websites()     上櫃／興櫃網址 → store.append("company_website")，30 天重抓一次
    └─ logos.run()            每輪 ≤300 家、≤15 分鐘
         ├─ data/logos/<code>.png          64×64 PNG（雜湊沒變就不重寫）
         ├─ data/logos/_index.json         代號 → status / src / domain / fetched / sha1 / orig
         └─ data/_state/logo_progress.json 本輪摘要、失敗清單（前 200 筆）、pending、next_due
部署（pages.yml → build_payload）
  export_logos()
    ├─ site/data/logos/<code>.png          只複製 usable 的（ok、檔案在、不是預設圖）
    └─ site/data/logos.json                {"2330": "data/logos/2330.png", ...}；沒有就 {}
```

`pages.yml` 上傳的是整個 `site/`，所以 `site/data/logos/` 會跟著部署；它的 JSON 快取 key 含 `data/**`，Logo 有變就會重算。
⚠ 回補的 commit 只動 `data/`，**不會觸發** `pages.yml`：新抓到的 Logo 要等下一次部署（有人推 `site/**` 或 `pipeline/**`，
或手動觸發「部署網站」）才會出現在網站上。

`status` 的值：`ok`（有圖）／`too_small`／`blank`／`generic`（預設圖）／`robots`／`none`／`error`／`removed`（人工下架）。
增量規則：沒抓過的先（族群成分股優先）→ 網域換了的 → 到期的（`ok` 90 天、其他 30 天，最舊的先）。
之前抓到過、這次重抓失敗的，**保留舊圖**，只記 `last_fail`。
