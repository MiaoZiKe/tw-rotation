# 「今日事件」資料串接可行性（2026-10-11 實測）

結論：**可以取得**。社群媒體部直接讀資料湖即可，不必等網站；自動化（每天產出選題清單）需要另外排工。

## 實測內容
| 資料 | 位置 | 實測 |
|---|---|---|
| 新聞（台股／科技／總經） | `data/news/year=2026/part.parquet` | 4,881 則，2026-09-10～10-11；台股 2,468／科技 1,591／總經 764；來源鉅亨 2,562／經濟日報 1,277／TechNews 1,042；欄位 title、summary、url、date、published_at、codes、category |
| 公司重大訊息（法說會等） | `data/material_news/year=2026/part.parquet` | 1,170 則，09-19～10-10；欄位 code、name、subject、occurred、detail |
| 財經／總經日程（FOMC、CPI、非農） | `pipeline/calendar/macro_events.yaml`＋FRED 發布日（資料湖 macro_calendar） | 日期為美東，查證信心中 |
| 網站前端用的 | `site/data/news.json`、`news_head.json`（部署時由 build_payload 產出，不進版控） | 本容器沒有，需本機跑 `python -m pipeline.build_payload` |

## 限制（如實）
1. **新聞再散布授權未確認**（`docs/launch_gap_legal_1009.md` F2）：社群貼文只用「自己的話整理＋來源名稱＋連結」，不整段複製標題摘要、不截圖別人的新聞全文；鉅亨 API 條款待 Andy 查。
2. 總經類新聞只占約 16%，「總經一分鐘」欄目要另外靠日程檔與 FRED 補，不能只靠新聞。
3. 重大訊息是公司公告，可用於「本週法說會」類整理，不點名個股推薦。
4. 目前沒有「每天自動產出選題清單」的程式；做法草案：每日跑一支腳本，依 category 取當日前 N 則、去重、輸出 `docs/marketing/social_unit/daily_topics/<日期>.md` 給 finance-content-editor 查證。需 CEO 排工。
5. 資料湖是 T-1／盤後更新，貼文時間建議 20:00 之後。
