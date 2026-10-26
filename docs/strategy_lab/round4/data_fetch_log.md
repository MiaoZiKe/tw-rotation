# 第 4 項：補 VIX、事件日曆、更長的法人期貨歷史——小量驗證紀錄

結論先講：**這個開發環境抓不到，所以這一輪沒有補任何資料，也沒有動 data/ 與 config.TABLES。** 回測沒有使用新資料。

| 項目 | 驗證方式 | 結果 | 原因 |
|---|---|---|---|
| VIX（FRED VIXCLS） | `curl https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS` | 失敗：`CONNECT tunnel failed, response 403` | 出口代理拒絕連線到 fred.stlouisfed.org（此工作階段未放行）；環境變數也沒有 FRED_API_KEY |
| 事件日曆歷史發布日（FRED release dates） | 同上，同一主機 | 失敗，同上 | 同上 |
| 更長的法人／期貨／資券（FinMind） | `curl https://api.finmindtrade.com/api/v4/data?dataset=TaiwanFuturesInstitutionalInvestors...` | 失敗：403 代理拒絕 | api.finmindtrade.com 未放行；環境也沒有 FINMIND_TOKEN |
| Yahoo（SOX／VIX 備援） | `curl query1.finance.yahoo.com/v8/finance/chart/^VIX` | 失敗（000） | 與 CLAUDE.md 記載一致：容器擋 Yahoo |

沒有放棄，已準備好「在有網路與金鑰的環境一鍵補」的腳本：`scripts/backfill_round4_data.py`
- 全部走既有的 `store.append()`（只增不改、依 key 去重），不覆寫 parquet。
- VIX 直接寫進既有 `macro` 表（key=date+series，label 取自 `config.FRED_SERIES`，沒有的會用代號），**不需要改 config.TABLES**；事件日曆寫進既有 `macro_calendar`；法人／期貨／資券走 `mktfut.collect`（已含 402 即停）。
- 先 `python scripts/backfill_round4_data.py --dry-run` 看各表抓到幾列，再 `--apply`。
- **此腳本沒有在開發環境實測過**（連不到外網），第一次請在 GitHub Actions 或 Andy 有金鑰的環境用 --dry-run 驗證。
- 預期效益：VIX 自 1990、法人期貨自 2016 起，讓子項檢驗含 2018 與 2020 崩盤。FinMind 免費額度與歷史起點仍待實測（見 round3/history_sources.md）。
