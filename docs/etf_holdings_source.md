# ETF 成分股與權重：資料來源查證與實測（2026-10-07 改寫）

## 結論

**一手來源＝各發行投信官網每日公告的申購買回清單（PCF）／基金持股明細**，這是投信依
《ETF 發行人應行注意事項》每個營業日都要公告、給投資人取用的公開資訊。官網頁面背後都是投信自家的 JSON API，
`pipeline/sources/etf_pcf.py` 直接打那幾支，每天傍晚那輪進資料湖 `etf_holdings`（只增不改），
`build_payload` 產出 `site/data/etf_holdings.json`，前端 `site/industry.js` tabHoldings 不用改就會畫出清單＋甜甜圈。

10-07 13:55 前的版本寫「目前沒有接上任何來源、建議申請 Fugle 金鑰」—— **那是錯的**：只查了證交所與 FinMind，
沒有去查投信自己的公告。Andy 指出之後實測，八家投信都有可直接取用的公開 API。

## 實測結果（GitHub Actions，2026-10-07 台北 14:30～15:02，`.github/workflows/probe-etf-pcf.yml`）

自我測試（`mode=selftest`，跑 `python -m pipeline.sources.etf_pcf`，不寫湖）：**8 家投信、108 檔 ETF、8,049 列成分**。

| 投信 | 端點（官網前端自己在打的那支） | 回應 | 權重 | 實測檔數 | 信心度 |
|---|---|---|---|---|---|
| 元大 | `GET www.yuantaetfs.com/tradeInfo/pcf/{代號}`（Nuxt SSR，資料在 `window.__NUXT__`） | `.FundWeights.StockWeights[{code,name,weights,qty}]`；實物申贖型另有 `.InKind.FundComposition` | 有（%） | 21（0050 50 檔、0056、00713、00940、00850…） | 高 |
| 國泰 | `GET cwapi.cathaysite.com.tw/api/ETF/GetETFList`（CurrentPage／PerPageCount）→ `GetETFAssets?FundCode=`（preDate）→ `GetETFDetailStockList?FundCode=&SearchDate=` | `result[{stockCode,stockName,volumn,weights}]` | 有 | 20（00878、00881、00922…） | 高 |
| 中國信託 | `POST www.ctbcinvestments.com.tw/API/home/AuthToken` → `etf/ETFList` → `etf/ETFHoldingWeight {FID, StartDate}` | `FundAssetsDetail[Code=STOCK].Data[{code_,name_,qty_,weights_}]`、`FundAssets.資料日期` | 有 | 23（**00896 50 檔**、00891、00934…） | 高 |
| 群益 | `POST www.capitalfund.com.tw/CFWeb/api/etf/list` → `etf/buyback {fundId}` | `data.stocks[{stocNo,stocName,weight,share}]`、`pcf.date2`（淨值日） | 有 | 12（00919、00923、00927、00982A…） | 高 |
| 復華 | `GET www.fhtrust.com.tw/api/fundList` → `api/assets?fundID=ETFxx&qDate=` | `result[0].detail[ftype=股票]{stockid,stockname,qshare,prate_addaccint}` | 有 | 10（00929、00991A、00731…） | 高 |
| 統一 | `GET www.ezmoney.com.tw/ETF/Transaction/PCF`（頁內基金代碼）→ `POST GetPCF {fundCode,date(民國),specificDate}` | `asset[AssetName=股票].Details[{DetailCode,DetailName,NavRate,Share}]` | 有 | 7（00981A、00403A、00939…） | 高 |
| 凱基 | `GET www.kgifund.com.tw/Fund/RedemptionList`（隱藏欄 AllFundName）→ `POST Fund/RedemptionVC fundID=&queryDate=`（HTML 片段） | `<tr name="content">` 代號／名稱／股數／權重 | 有 | 6（009816、00407A、00915…） | 中（日期取片段第一個日期，可能是公告日 T 而不是淨值日 T-1） |
| 野村 | `POST www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets {FundID, SearchDate:null}` | `Table[股票].Rows[[代號,名稱,股數,權重]]`、`FundAsset.NavDate` | 有 | 9（00935、00980A…） | 高 |

### 00896（Andy 點名）

中信投信官網 `etf/ETFHoldingWeight`（FID=E0019）實測：資料日期 2026/10/06、50 檔、股票合計 98.46%，
前三大 台積電 11.46%、南亞 7.70%、鴻海 7.11%。**自動來源已接上，不需要人工手抄**。

> **2026-10-07 晚更新**：富邦、台新（含原新光）、華南永昌、第一金、聯博已接上，上櫃 ETF 也納入；
> 覆蓋率 108 → 175／311。最新的缺漏清單、端點與補不上的原因一律看 `docs/etf_holdings_coverage.md`，下面這張表是更新前的紀錄。

### 還沒接上（前端寫「此檔發行投信（X 投信）資料尚未接上」）

| 投信 | 狀況 | 影響的大檔 |
|---|---|---|
| 富邦 | `websys.fsit.com.tw/FubonETF/Trade/Pcf.aspx?stkId=` 頁面 200，但 HTML 與 XHR 都找不到成分股（可能在表單回傳或另一支端點），未追完 | 006208、0052、00692、00662、00900、00405A |
| 大華銀 | 官網網域未查到（`dahuasitc.com.tw`、`dahsitc.com.tw` 都解析不到） | 00918 |
| 永豐、兆豐、第一金、新光、台新、聯博、摩根、街口、富蘭克林、安聯… | 尚未探測 | 00888 等 |

上市股票型 ETF 規模前 30 大（etf.json 的 size 排序，排除債券／槓反）＋00896：**接上 25 檔**，缺 006208、0052、00692、00662（富邦）、00918（大華）。

## 證交所與第三方網站的結論

- **證交所 OpenAPI**（openapi.twse.com.tw）：實測 swagger 225 個 path，沒有任何 ETF 成分／PCF 端點。櫃買 OpenAPI 只有 `tpex_opfund_*`（基金概況）。
- **證交所官網 ETF e 添富、`www.twse.com.tw/rwd`、`mis.twse.com.tw` 的 ETF 淨值揭露專區**：依 DECISIONS #1（A.1「絕不碰 www.twse.com.tw/rwd」）
  與 #265（「官網網頁＝比照 www.twse.com.tw/rwd，不用」）不碰；mis 只有 `getStockInfo.jsp` 在白名單（#108），淨值揭露專區不是。
  證交所「ETF 申贖資訊及即時淨值揭露專區介接格式說明」（dsp.twse.com.tw）載明是**投信提供固定 URL、以 JSON 揭示**——資料的源頭就是投信，所以直接取投信公告。
- **口袋證券 pocket.tw**：WebSearch 只拿到它的免責聲明頁（footer）摘要——寫明「彙整、引用或轉載其他資訊提供者之資訊」，
  也就是它本身是第三方彙整、資料來自投信。沒有找到明文允許程式抓取的條款，**不作為抓取來源**；只拿來人工對照（信心度：中）。
- **Fugle、CMoney、MoneyDJ、WantGoo**：第三方，不採用（Fugle 需金鑰與付費方案）。

## 合規判斷（依據與限制）

- 打的都是投信官網**前端頁面自己在呼叫的公開 API**、不需登入、不繞驗證碼；每檔每天一次、整輪約 3 分鐘一百多個請求，負載與一般使用者瀏覽相當。
- 只存「代號、名稱、權重、股數、資料日期」這些事實資料，頁面註明「X 投信公告」與資料日期，不轉載投信的文字內容。
- 限制：各投信官網的使用條款**沒有逐家查到明文**（WebSearch 拿不到全文）。若某家投信明文禁止程式取用，
  應把那家從 `fetch_all()` 拿掉、改走 `pipeline/etf/holdings_manual.yaml` 人工整理。

## 前端吃的格式（site/data/etf_holdings.json）

```json
{ "asof": "2026-10-06", "source": "各發行投信官網每日公告之申購買回清單（PCF）／基金持股明細",
  "connected": ["中國信託", "元大", "…"],
  "issuers": { "006208": "富邦", "00896": "中國信託" },
  "etfs": { "00896": { "asof": "2026-10-06", "issuer": "中國信託", "src": "https://…/ETFHoldingWeight", "est": false,
                       "items": [ { "code": "2330", "name": "台灣積體電路製造", "w": 11.46, "shares": 638000 } ] } } }
```
- `w`＝占淨值 %；`est=true` 表示投信只給股數（元大實物申贖型），權重是 build_payload 用股數×收盤價推算的占股票部位比例。
- `manual=true`＝來自 `pipeline/etf/holdings_manual.yaml`（人工整理，前端標「人工整理・資料日期 X」）。
- 非台股成分 `code` 寫原代號（例如 `NVDA US`、`600519.CH`），前端不給連結。

## 怎麼再驗一次

Actions → 「ETF 成分股來源探測」→ Run workflow：`mode=selftest` 實抓全部投信並印每檔前三大；
`mode=requests`＋`extra` 打單一網址；`mode=browser`＋`extra=網址@@要點的文字` 用真瀏覽器記錄 XHR。

來源：<https://dsp.twse.com.tw/public/static/downloads/tradingDepartment/ETF%20申贖資訊及即時淨值揭露專區介接格式說明_20250109142554.pdf>、
<https://www.yuantaetfs.com/tradeInfo/pcf/0050>、<https://www.ctbcinvestments.com/Etf/88231049/Combination>、
<https://www.capitalfund.com.tw/etf/product/detail/399/portfolio>、<https://www.fhtrust.com.tw/ETF/etf_detail/ETF23>、
<https://www.ezmoney.com.tw/ETF/Transaction/PCF>、<https://www.kgifund.com.tw/Fund/RedemptionList>、
<https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00935&tab=Shareholding>、<https://www.pocket.tw/footer/>
