# ETF 成分股與權重：資料來源查證（2026-10-07）

## 結論

**目前沒有接上任何來源**。前端版面（左個股清單＋右權重甜甜圈、無股票成分說明卡）已做好，
讀 `site/data/etf_holdings.json`；這支檔一旦由 pipeline 產出，畫面不用改就會出現。

## 根因（Andy 10-07：「ETF 點擊成分股並沒有出現對應股票」）

1. 資料湖沒有成分股表：`pipeline/config.py` 的 `TABLES` 沒有任何 ETF 持股表，`site/data/` 沒有 `etf_holdings.json`，
   個股 JSON（例如 `site/data/stock/00896.json`、`0050.json`、`00878.json`、`00679B.json`、`00981A.json`）
   也沒有成分欄位（只有 `holders`／`shareholding` 集保資料）。
2. 前端 `tabHoldings`（`site/industry.js`）10-05 上線時只寫了一行「以發行投信官網為準」，沒有畫圖的程式。
3. 手機（`site/mobile3.js` SK_TABS）根本沒有「成分股」分頁。

## 查過的來源（WebSearch 摘要，信心度：中）

| 來源 | 結果 | 能不能用 |
|---|---|---|
| 證交所 OpenAPI（openapi.twse.com.tw） | 摘要只提到 ETF 基本資料（data.gov.tw 157399：股債比例、追蹤指數，月更新），未見逐檔成分股／權重端點 | 沒有這張表 |
| 證交所 ETF e 添富（www.twse.com.tw/zh/ETFortune） | 官網網頁 | ✘ 官網端點禁爬（CLAUDE.md 絕對不做 1） |
| FinMind | 未找到 ETF 持股資料集 | 沒有 |
| Fugle 富果 API `ownership/etf-holdings` | 有每日成分（代號、名稱、股數、權重） | 需要 API 金鑰與方案，條款與免費額度未確認；要用需 Andy 申請金鑰放 GitHub Secrets |
| 各投信官網每日持股 | 有，但每家格式不同（網頁／Excel／PDF），使用條款各異 | 未逐家確認可自動擷取 |
| CMoney／MoneyDJ 等彙整站 | 有 | ✘ 第三方網頁，非開放資料 |

## 建議（擇一，需 Andy 拍板）

1. **Fugle API**：Andy 申請金鑰 → 放 `FUGLE_TOKEN` Secret → 新增 `pipeline/sources/fugle.py`、`config.TABLES['etf_holdings']`，
   每日增量 `store.append()`，`build_payload` 輸出 `etf_holdings.json`（格式見下）。
2. **投信官網逐家接**：先從規模最大的幾家（元大、國泰、群益、復華）逐家確認使用條款與下載格式。

## 前端吃的格式

```json
{ "asof": "2026-10-06", "source": "…",
  "etfs": { "0050": { "asof": "2026-10-06",
                      "items": [ { "code": "2330", "name": "台積電", "w": 55.1, "shares": 123456000 } ] } } }
```
`w`＝權重 %（占 ETF 淨值）、`shares`＝股數（前端換算成張，可為 null）、非台股成分 `code` 寫原代號（例如 `AAPL US`），前端不給連結。

來源：<https://developer.fugle.tw/docs/data/http-api/ownership/etf-holdings>、<https://data.gov.tw/dataset/157399>
