# CLAUDE.md — 入口檔（新 session 第一個讀的）

## 這是什麼

**台股資金輪動儀表板**：每天盤後在 GitHub Actions 自動抓免費合規資料 → 算指標 → 產出靜態網站，
回答四個問題：**錢往哪個族群跑、那個族群現在貴不貴、什麼時候進場、有沒有理由不進場。**
判斷順序是刻意的：M1 資金面 + M2 基本面決定方向 → M3 技術面決定時機 → M4 事件面否決。

- 線上網址：<https://miaozike.github.io/tw-rotation/>
- Repo：<https://github.com/MiaoZiKe/tw-rotation>（**public**，所以任何金鑰、持股、成本價都不能進 repo）
- 擁有者 Andy：前 ASUS EC 韌體工程師、前台積電微影製程工程師，現任科技業 Sales PM。
  半導體供應鏈不用從頭解釋；`groups.yaml` / `themes.yaml` / `supply_chain.yaml` 的成分他會自己校訂。
- Andy 的工作方式：**他只重新整理網頁、不按任何本機指令**。程式碼由 Claude 透過 GitHub API 推上 main，
  資料由 Actions 自己 commit。本機 `.bat/.ps1` 只是初次安裝用。

## 開始工作前，依序讀這三個檔

1. **`AGENTS.md`** — 九個專家 Agent 與 CEO 的分工、產出格式、審核清單（怎麼做事）
2. **`HANDOFF.md`** — 目前進度、已知 bug、**「下一步」**（從哪裡接手）
3. **`DECISIONS.md`** — 已拍板的決策（不要重新討論、不要「順手改回去」）

之後才看 `docs/v3_sources_spec.md`（資料源規格）與程式碼。

## 工作規則

- **★ 開工第一件事：先確認「推得上去」，再開始改東西。**
  `git push --dry-run origin deploy:main`。如果回 `access denied by the git proxy: ... not in this
  session's authorized repository set`，代表這個 session 沒有 repo 的寫入權限 ——
  **立刻告訴 Andy、先不要埋頭做**。原因：Andy 只看網頁，沒 push 等於他什麼都看不到；
  2026-09-13 就是這樣累積了 8 個 commit、他連續四次回報「縮放還在」，其實每一次都早就改好了。
  授權是**跟著 session 走的**，所以每開一個新 session 都要重驗一次。
- **開始前先 `git pull`**（雲端資料湖與工作流每天都在 commit；本機永遠可能落後）。
- **每次工作結束前更新 `HANDOFF.md`**（進度勾選、已知 bug、下一步、最後更新時間），**commit + push 到 main**。
  沒有 push 的工作等於沒做。
- **絕不 force push、絕不覆寫 `data/*.parquet`。** 雲端是資料的權威來源（`store.append()` 只增不改）。
- **push 前跑三件事**：`pytest tests/ -q`、`python scripts/_preview.py`（真圖表庫走過所有頁面、抓文字重疊、手機寬）、
  `python scripts/_uitest.py`（**真人操作驗收**，含全站縮放掃描）。
- **push 之後還沒完**：等 Actions 跑完，**真的打開 <https://miaozike.github.io/tw-rotation/> 確認線上版本換掉了**
  （比對右上角的**版號徽章**，那是 2026-09-16 為了這件事加的，見 DECISIONS #148），再跟 Andy 說「好了」。
  只說「推上去了」不算交付。
- **★ 每一次回報都要附上網址**（Andy 2026-09-18：「請每次都提供網址給我」）。
  他沒有辦法從對話裡判斷我說的「好了」是不是真的，所以每次交付都要給他三樣東西：
  **① 網址 ② 該看哪裡（版號徽章長什麼樣）③ 我自己已經開過線上確認的結果**。
- **★ 叫 Andy 按 .bat 之後，一定要回去確認那支 .bat 真的成功。**
  2026-09-18 踩到：`push-0918.bat` 在 `git pull --rebase` 那一步就失敗了
  （工作目錄有未提交的 `push-log-0916.txt`），完全沒推上去，而我沒有回查 ——
  Andy 打開網站看不到版號才發現。回查方法：讀他 repo 根目錄的 `push-log-*.txt`，
  或用瀏覽器看 `https://api.github.com/repos/MiaoZiKe/tw-rotation/commits`。
  **推送腳本一律用 `git pull --rebase --autostash`**，不要假設工作目錄是乾淨的。
- **★ Andy 的硬性要求：每批做完一定要「當自己是使用者，實際操作每個功能」。**
  每個按鈕真的按、每個輸入真的填、每個切換真的切、每條線真的用滑鼠拖出來，
  而且每一項都要驗**「畫面真的因此改變了」**（筆數變了／排序變了／localStorage 真的寫進去了），
  不是驗「元素存在」或「有 render」。這條規則是因為只看 render 的驗收放過了一堆錯
  （例如：切到沒資料的週期再切回日線，整張 K 線圖空白到重新整理為止）。`scripts/_uitest.py` 就是這件事的載體，
  **新功能一定要同時在裡面加一段真的操作它的驗收**。
- 註解、commit 訊息、文件一律繁體中文。
- 金鑰只放 GitHub Secrets（`FINMIND_TOKEN`、`FRED_API_KEY`）與 Claude 的暫存區；**永遠不寫進 repo 任何檔案**。
  push 前 `git grep -iE "github_pat_|ghp_|finmind.*token" -- . ':!*.md'` 掃一次（排除文件本身的說明字串）。

## 絕對不要做的事（細節與理由在 DECISIONS.md）

1. 不碰 `www.twse.com.tw/rwd/...` 官網端點（使用條款禁爬）。可用的來源：`openapi.twse.com.tw`（日收，T-1）、
   `mis.twse.com.tw/stock/api/getStockInfo.jsp`（即時報價，**2026-09-14 加入白名單**，見 DECISIONS #108）、FinMind。
2. 不覆寫 `data/` 的 Parquet；一律 `store.append()`。
3. 不用執行當下日期當交易日；用回應裡的 `Date`。
4. 不引入 TA-Lib；指標自己算（`pipeline/indicators.py`、前端 `site/chart.js` 的 `KInd`）。
5. 不把持股部位、成本價、個人損益、任何 token 放進 repo。
6. 不把 `cancel-in-progress` 改成 true（會出現「repo 已更新但網站是舊版」）。
7. 不要爬券商分點（主力家數差沒有免費合規來源，已改用集保大戶增減＋法人動向替代）。

## Repo 結構導覽

```
.github/workflows/
  daily.yml      每日盤後管線（UTC 07:30/10:30/13:30＝台北 15:30/18:30/21:30，週一~五）：
                 15:30 那輪 --phase price 只抓價量；openapi 還沒給今天就用 mis 補（暫定值）
  backfill.yml   歷史回補（每小時，避開 09:20/10:20 UTC）：跑 --plan default，補齊即跳過
  pages.yml      site/** 或 pipeline/** 有 push 就重算 JSON 並部署
pipeline/
  config.py            所有路徑、端點、參數、TABLES（新增資料表先在這裡註冊 key）
  run_daily.py         每日管線；每步可失敗，寫 data/_state/last_run.json
  run_backfill.py      歷史回補；PLAN_DEFAULT 多步驟、402 即停、進度在 data/_state/backfill_progress.json
  build_payload.py     從資料湖算出前端 JSON（site/data/，不進版控）；SKIP_INTRADAY=1 可跳過 Yahoo 分 K
  indicators.py        MA/MACD/RSI/KD/ATR/SMC + technical_score()
  sources/             twse(OpenAPI) mis(即時報價/當天補齊) finmind tdcc tpex yahoo news macro
                       —— 全部回 DataFrame，失敗回空
  compute/             flow(M1) fundamental(M2) technical(M3規則) mtf(多週期SMC) stockpage season themes rrg
  groups/              ★ groups.yaml themes.yaml supply_chain.yaml（唯一人工維護）+ loader.py
  util/                roc(民國/千元/空值) http(重試+FinMind額度) store(Parquet append-only)
site/
  index.html app.js industry.js chart.js diagrams.js   前端（深色科技風；hash 路由）
  live.js            盤中即時層（每分鐘／盤後每 30 分／手動更新鈕；只更新 [data-live] 標記過的格子）
  vendor/echarts*.js  vendor/lightweight-charts.js       內建於 repo（Andy 公司網路擋 CDN）
  data/                                                  工作流產出，gitignore
data/                  Parquet 資料湖（雲端 Actions 每天 commit；本機只讀）
scripts/_preview.py    本機預覽驗證（Playwright + 真圖表庫）
scripts/stamp_assets.py 部署前給自家 JS/CSS 加版本戳（不加就要按 Ctrl+F5 才看得到新版）
tests/                 pytest，260 個
workers/quote-proxy/   Cloudflare Worker：即時報價的 CORS 代理（部署說明在 workers/README.md）
docs/                  v3_sources_spec.md（資料源規格）、截圖
```

## 前端路由（驗收時逐一打開）

`#overview` 總覽 ｜ `#flow` 資金流向（RRG／桑基／河流）｜ `#industry` 產業地圖 → `#industry/<chain>` 單一產業鏈 →
`#stock/<code>` 個股（分 K、多週期 SMC、營收／獲利／除權息／籌碼／基本資料）｜ `#themes[/id]` 題材熱度 ｜ `#season` 季節性

## 台股慣例（跟國外套件預設不同）

紅漲綠跌；KD 9,3,3 初始 50；RSI Wilder（SMA 種子，與 TradingView 對得上）；MACD 慣稱 DIF/MACD/OSC；
民國日期、千元、全字串 → `util/roc.py`。前端 `KInd` 與 Python 端口徑必須一致，改一邊記得改另一邊。
