# 化合物半導體（穩懋／宏捷科等）查證紀錄 — 2026-10-04

起因：Andy「第三類半導體最大廠 穩懋 宏捷科 怎麼都沒有，需要延伸他的關聯圖，不然不知道他是做什麼用的」；
「若不屬於半導體而是新的產業族群，就分出新的分頁，但要先查證清楚」。

## 歸類結論：留在半導體鏈，不另開分頁
- 證交所／櫃買產業別：穩懋、宏捷科、環宇、漢磊、嘉晶、全新皆屬「半導體業」（reported；建議日後用 openapi 產業別欄位機器核對）。
- PIDA／TrendForce 把化合物半導體當成半導體的子領域盤點：https://technews.tw/2021/12/23/pida-compound-semiconductor/
- 所以在半導體鏈開兩格：`compound_semi`（GaAs／InP，射頻・VCSEL）、`wide_bandgap`（SiC／GaN，功率）。

## 逐家（證據等級：WebSearch 摘要，未讀原文）
| 公司 | 環節 | 終端用途 | 具名客戶／邊 | 來源 | 信心度 |
|---|---|---|---|---|---|
| 3105 穩懋 | GaAs 代工 | 手機射頻 PA、Wi-Fi、VCSEL | Broadcom 約 2 成、Skyworks、Qorvo | https://www.cmoney.tw/notes/note-detail.aspx?nid=162625 | reported |
| 8086 宏捷科 | GaAs PA 代工 | 手機射頻 PA | Skyworks 約 5 成（曾約 8 成）；中美晶集團 | 同上、https://uanalyze.com.tw/articles/8983844633 | reported |
| 2455 全新 | GaAs／InP 磊晶片 | VCSEL、光通訊 | → 穩懋（VCSEL 磊晶認證）；終端傳為蘋果（間接，estimated） | Yahoo 股市焦點股 | reported |
| 3707 漢磊 | SiC／GaN 功率代工 | 工業 44%、車用 28%、消費 21%、綠能 7% | 查不到具名客戶 | https://www.moneyweekly.com.tw/ArticleData/Info/Article/199685/ | reported |
| 3016 嘉晶 | Si／SiC／GaN 磊晶 | 功率元件 | → 漢磊（漢民集團母子公司，主要供應漢磊） | https://blog.fugle.tw/post/episil-earnings-call-q3-2021 | reported |
| 4991 環宇-KY | GaAs／InP 代工＋光偵測器 | 光通訊 PD（自有光電 61%）、射頻 23% | 查不到 → 暫不放節點 | https://uanalyze.com.tw/articles/7064535420 | reported |
| 4971 英特磊-KY | MBE 磊晶 | VCSEL、光通訊 | 查不到（中國手機廠）→ 暫不放節點 | https://technews.tw/?p=313330 | reported |
| 8261 富鼎／2342 茂矽 | SiC 元件／代工 | 車用 | 查不到；已在 analog_power_ic 族群 | 理財周刊 235816、yam | reported |
| 6435 大中／3675 德微 | — | 查不到 SiC／GaN 實績 | 不納入 | — | — |

## 陷阱
- 搜尋摘要把穩懋寫成「Wyle」、宏捷科寫成「Transphorm」——都錯。正確英文名：WIN Semiconductors、Advanced Wireless Semiconductor（AWSC）。
- 宏捷科屬中美晶集團、嘉晶屬漢磊（漢民集團），營收不可重複加總。
- 基地台、低軌衛星、快充 GaN：查不到可點名的台股對應。AI 800V HVDC 電源只是題材，沒有具名訂單。
