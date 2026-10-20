# 盤中／盤後即時貼文（Threads＋IG 限動）：截圖、排版、排程

Andy 2026-10-20 原話：「我需要在盤中發布當下即時狀況在 Threads 上和 IG 限動：1. 需資金輪盤、分流樹即時截圖，包含旁邊的長條圖；2. 需要串接自動發布系統；3. 排版只需要提供當前狀況，大家需要看」「熱力圖都需要具備即時功能，他也是需要截圖發布的內容」「也需要在盤後提供當天即時的法人買賣超狀況」。

## 檔案
| 檔案 | 做什麼 |
|---|---|
| `scripts/social_snap.py` | 開網站、切即時、截圖、排版（限動／Threads）、檢查重疊、產 `manifest.json` |
| `.github/workflows/social-live.yml` | 排程；跑 social_snap → 推圖到 `social-snaps` 分支 → 呼叫 `scripts/social_publish.py` |
| `scripts/social_publish.py` | 發布組寫的：讀 manifest、發 Threads 與 IG 限動（沒金鑰自動 dry-run） |

## 產出（每輪一個資料夾 `snaps/<kind>-<yyyymmdd-HHMM>/`）
- `story_<名稱>.png`：IG 限動 1080×1920。上緣、下緣各留約 250px 安全區；中間一個群組＝標題＋整張截圖（等比、不裁）；下方資料來源免責一行＋網址。一張截圖一張限動。
- `threads_<名稱>.png`：1080 寬。標題列＋整張截圖＋底部一行（免責＋網址）。
- `manifest.json`：`{"kind","taken_at","data_date","threads":{"text","images"},"story"}`，圖片路徑相對於資料夾。
- `layout_report.json`：每張版面的框與重疊檢查結果；`shots.json`：每個目標有沒有截成、為什麼略過。
- `raw/`：原始截圖（2 倍解析度，不上傳）。

### 盤中（kind=intraday）
| 名稱 | 頁面 | 內容 |
|---|---|---|
| rotation | `#flow/rotation` | 資金輪盤＋右側族群資金排行長條圖（同一張卡） |
| sankey | `#flow/sankey` | 資金分流樹＋右側資金流向排名（同一張卡） |
| heat-industry | `#heatmap/industry` | 產業熱力圖（等 frontend-ui 把熱力圖改即時，沒有即時鈕前會被跳過） |
| heat-theme | `#heatmap/theme` | 題材熱力圖（同上） |

### 盤後（kind=close）
| 名稱 | 頁面 | 內容 |
|---|---|---|
| streak-trust／streak-foreign／streak-total | `#market/streak` | 法人連續買賣超：投信、外資、合計各一張（切 `#streakWho` 的按鈕） |
| inst-groups | `#flow/inst` | 族群×三大法人（網站目前沒有「單日」三大法人買賣超卡，這張是近 20 日淨買超依族群） |

## 規矩
- 亮色主題、桌機寬 1440；同意橫幅、導覽、客服比比等固定浮動元素截圖前一律藏起來，截圖保留頁面上原有的免責字樣。
- **即時沒套上就不發**：盤中那幾張要等狀態字不再是「抓取中／抓不到」才截；沒套上的略過，不拿盤後舊圖冒充。
- **非交易日看資料判斷**：盤中看即時報價回應裡的成交日 `d` 是否＝今天，並限定台北 09:00～13:35；盤後看網站 `meta.json` 的 `inst_date` 是否＝今天。不用執行當下的星期幾。
- 貼文文字 4 行：時間、重點一句（從頁面讀「資金佔比增加最多／減少最多」那行，或連買前三名，原文照抄）、免責一句、網址。
- 版面元素（標題、截圖、免責、網址）兩兩不得相交，超出畫布也不行；程式用瀏覽器量實際框與文字範圍，有一筆就結束碼 3、不發。

## 排程（台北時間；GitHub cron 用 UTC）
| 時段 | 台北 | UTC cron |
|---|---|---|
| 盤中 | 09:35 | `35 1 * * 1-5` |
| 盤中 | 11:05 | `5 3 * * 1-5` |
| 盤中 | 13:05 | `5 5 * * 1-5` |
| 盤後法人 | 接在「每日盤後管線」每一輪結束之後 | `workflow_run` |

盤後為什麼接管線而不是固定時間：三大法人傍晚才落地（`daily.yml` 台北 18:30 那輪 `phase=full` 才有，15:30 那輪只抓價量）。GitHub 排程常延遲數十分鐘，固定時間可能抓到舊資料。接在管線結束（資料已部署到網站）之後，再用 `inst_date == 今天` 把關；一天三輪都會接到，但 `social-snaps` 分支上有 `state/close-<日期>` 標記就跳過，只發一次。

## 需要的 Secrets（只放 GitHub Secrets，不進 repo）
- 發布：`THREADS_USER_ID`、`THREADS_ACCESS_TOKEN`、`IG_USER_ID`、`IG_ACCESS_TOKEN`（沒填＝自動 dry-run）。
- 截即時：`SNAP_ACCT_TOKEN`（站主或管理員的會員登入權杖）、`SNAP_ACCT_USER_JSON`（選填，預設 `{"owner":true,"admin":true}`）。原因：即時是管理者功能（`site/livegate.js`），無頭瀏覽器沒登入就看不到「即時」鈕。**這一條還沒解決，見下方「還缺什麼」。**

## 本機示範
```
python scripts/social_snap.py --kind intraday --serve site --mock-live --out /tmp/demo/intraday
python scripts/social_snap.py --kind close --serve site --force --out /tmp/demo/close
```
`--serve site` 起本機伺服器並自動開 `TW_LIVE_OVERRIDE`；`--mock-live` 用假報價（容器打不開正式站與報價代理）。需要先有 `site/data/`（`python -m pipeline.build_payload`）。

## 還缺什麼
1. 即時的存取方式：正式站的即時只給站主／管理員。需要 frontend-ui 提供一個給截圖機器人用的入口（例如帶專用金鑰的網址參數），或 Andy 提供管理者權杖放進 `SNAP_ACCT_TOKEN`。在這之前，正式站上盤中那幾張會因「沒有即時鈕」被跳過。
2. 熱力圖即時鈕與 `data-snap`／`window.TwSnapReady`：frontend-ui 上線後，`social_snap.py` 會自動優先使用 `[data-snap="<名稱>"]`；名稱以 `docs/social_snap_targets.md` 為準，不同時改 `TARGETS` 的 `name`。
3. `scripts/social_publish.py` 進 repo 後，確認它讀 `SOCIAL_IMAGE_BASE_URL`（圖片公開網址前綴，指向 `social-snaps` 分支）來組 Meta 要抓的圖片網址。
4. 要單日三大法人買賣超的話，網站需要新增那張卡。
