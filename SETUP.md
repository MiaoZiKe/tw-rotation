# SETUP.md — 新電腦環境建置

目標：在一台全新的電腦（或全新的 Claude session）上，20 分鐘內能跑測試、本機預覽、推程式碼、手動觸發 Actions。
**這裡只列環境變數的名稱、用途、取得方式；任何實際的 token／key 值都不寫進 repo。**

---

## 1. 需要安裝的工具

| 工具 | 版本 | 用途 | 備註 |
|---|---|---|---|
| Git | 2.30+ | 版本控制 | Windows 裝 Git for Windows |
| Python | **3.12**（3.11 也可） | 管線、測試、產 JSON | Actions 用 3.12（`setup-python`），本機對齊最好 |
| pip 套件 | `requirements.txt` | pandas / numpy / pyarrow / requests / PyYAML / feedparser / yfinance / duckdb / pytest | `pip install -r requirements.txt` |
| Playwright + Chromium | 最新 | `scripts/_preview.py` 本機預覽驗證（真圖表庫走頁面、抓文字重疊、手機寬） | `pip install playwright && playwright install chromium` |
| GitHub CLI `gh` | 2.x | 手動觸發 Actions、設 Secrets（選用；網頁 UI 也能做） | `gh auth login` |
| 瀏覽器 | Chrome/Edge | 看網站；Claude 的瀏覽器窗格也用來推程式碼（見第 5 節） | |

不需要 Node.js（前端是純靜態，圖表庫已 vendored 在 `site/vendor/`）。
不需要 TA-Lib（決策：指標自己算）。

## 2. 取得程式碼

```bash
git clone https://github.com/MiaoZiKe/tw-rotation.git
cd tw-rotation
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install playwright && playwright install chromium   # 只有要跑預覽驗證才需要
```

Windows 初次安裝也可以直接雙擊 `setup.bat`（→ `setup.ps1`，可重複執行）：檢查工具、`gh` 登入、
輸入 FinMind token 寫進 GitHub Secrets、確認 repo／Pages／Actions 權限、觸發第一次管線與回補。
`update.bat` 是不觸發回補的版本；`backfill-financials.bat` 只觸發財報回補。

## 3. 環境變數與 Secrets（只列名稱）

### GitHub repo Secrets（Settings → Secrets and variables → Actions）
| 名稱 | 用途 | 取得方式 | 必要 |
|---|---|---|---|
| `FINMIND_TOKEN` | FinMind API（歷史價量、法人、財報、股利、資券、股權分散）。註冊會員 600 req/hr，未註冊 300 | <https://finmindtrade.com> 註冊並驗證 email → 會員頁複製 token | 必要 |
| `FRED_API_KEY` | 美國總經指標（FRED） | <https://fred.stlouisfed.org/docs/api/api_key.html> 免費申請 | 選用 |

### 本機執行時的環境變數（程式讀 `os.environ`，見 `pipeline/config.py`）
| 名稱 | 用途 | 預設 |
|---|---|---|
| `FINMIND_TOKEN` | 同上，本機跑 `run_daily` / `run_backfill` 需要 | 空（會用未註冊額度） |
| `FRED_API_KEY` | 同上 | 空（跳過） |
| `UNIVERSE_SIZE` | 個股歷史回補檔數 | 500 |
| `BACKFILL_START` | 回補起始日（不用 plan 時） | 2016-01-01 |
| `SKIP_INTRADAY` | 設 `1` 時 `build_payload` 跳過 Yahoo 分 K（本機無法連 Yahoo 時用） | 未設 |
| `GH_TOKEN` | 只給 `scripts/gh_push.py` 用（產生瀏覽器推送腳本），或放 repo 根目錄 `.ghtoken`（已 gitignore） | — |
| `GH_REPO` | 推送目標，預設 `MiaoZiKe/tw-rotation` | — |

### 給 Claude 推程式碼用的 GitHub PAT（不是 Secret，不進 repo）
- 類型：**Fine-grained personal access token**，只授權 `tw-rotation` 一個 repo。
- 權限：Repository permissions → **Contents: Read and write**、**Workflows: Read and write**、**Actions: Read and write**。
- 取得：GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token。
- 存放：只貼給 Claude 當次對話（Claude 存在暫存區 `.ghtoken` 或環境變數），用完建議重新產生。

## 4. 在本機跑起來

```bash
# 測試（156 個，約 50 秒）
pytest tests/ -q

# 只算前端 JSON（從 repo 內的 data/ 資料湖，約 8 分鐘；本機連不到 Yahoo 就加 SKIP_INTRADAY=1）
SKIP_INTRADAY=1 python -m pipeline.build_payload      # Windows PowerShell: $env:SKIP_INTRADAY=1; python -m pipeline.build_payload

# 開網站
python -m http.server 8000 -d site      # 打開 http://localhost:8000/

# 預覽驗證（起 server、用真 ECharts + Lightweight Charts 走過每個分頁與個股頁、偵測文字重疊、手機寬）
python scripts/_preview.py              # 截圖輸出到 docs/*.png（gitignore）

# 每日管線（需要 FINMIND_TOKEN；會 append 到 data/，本機跑完不要 push data/，雲端才是權威）
python -m pipeline.run_daily

# 歷史回補（可重跑；402 限流即停）
python -m pipeline.run_backfill --plan default
python -m pipeline.run_backfill --datasets price+inst --limit 50
```

## 5. 怎麼把程式碼推上 GitHub

**優先**：執行環境連得到 `api.github.com` 就直接 `git push`（用 PAT 當密碼或 `gh auth`）。

**Claude 的雲端容器連不到 GitHub 時**（本專案目前的狀況：proxy 回 403，但 `git fetch` 可以）：
用「瀏覽器窗格推送」— 讓 Andy 電腦上的瀏覽器窗格（已開 <https://miaozike.github.io>）替 Claude 打 GitHub API。

```bash
# 1. 在 Claude 容器產生腳本（token 從 GH_TOKEN 或 .ghtoken 讀）
python scripts/gh_push.py --rm-prefix site/data/ "commit 訊息" path/a.py path/b.js ...
#    → .gh_push/push_1.js … push_N.js（每段 ≤ 22 KB，檔案 gzip+base64）

# 2. 把 push_1.js … push_N.js 依序貼到瀏覽器窗格的 javascript 工具執行（同一個分頁）
#    每段只是把 blob 上傳排進背景工作（window.__twJobs）立刻回傳，不會被工具逾時卡住；
#    最後一段多排一個 __commit 工作：等全部上傳完成 → 建 tree（含刪除）→ commit → 更新 main（force:false）
# 3. 查進度：貼 .gh_push/status.js；有 error 就貼 ({retried: window.__twRetry()}) 重送失敗的檔
```

注意：Andy 公司 proxy 會間歇讓 `fetch` 失敗，腳本已內建重試 8 次（3s 遞增）；大檔（例如 vendored 圖表庫）
可以改在瀏覽器裡 `fetch` jsDelivr 再上傳 blob（jsDelivr 在瀏覽器連得到）。
推完在容器 `git fetch origin && git reset --hard origin/main` 讓本機對齊（先把 `site/data/` 備份，reset 會清掉未追蹤的舊檔）。

## 6. 手動觸發 GitHub Actions

網頁：repo → **Actions** → 左側選工作流 → **Run workflow**（分支 main）。
- **每日盤後管線**（`daily.yml`）：輸入 `skip_finmind`（true＝不動用 FinMind 額度）。跑完會自己 commit `data/` 並部署網站。
- **歷史回補**（`backfill.yml`）：`datasets` 選 `plan`（跑 `--plan default`）或指定資料集；`limit` 留空＝用剩餘額度補到滿。
  額度用完（402）會停下寫進度，下一次接續。
- **部署網站**（`pages.yml`）：只重算 JSON 並部署，不寫 repo；`site/**`／`pipeline/**` 有 push 會自動跑。

CLI（需 `gh auth login`）：
```bash
gh workflow run daily.yml
gh workflow run backfill.yml -f datasets=plan
gh workflow run backfill.yml -f datasets=revenue+financial+balance -f limit=400 -f start_date=2016-01-01
gh workflow run pages.yml
gh run list --limit 10
gh run watch            # 盯著最新一個 run
```

Repo 設定確認（第一次才需要）：Settings → Pages → Source＝**GitHub Actions**；
Settings → Actions → General → Workflow permissions＝**Read and write**。

## 7. 常見問題

- **網站是舊版**：看 Actions「部署網站」最新 run 是否成功；兩條部署線共用 `pages` group 且不取消，等它跑完。瀏覽器 Ctrl+F5。
- **回補一直 Fail**：多半是與每日管線同時 push 衝突 → 已用 `tw-rotation-data-write` 排隊；或 FinMind 402 → 正常，下一小時接續。
- **本機 `build_payload` 卡在 Yahoo**：加 `SKIP_INTRADAY=1`。
- **櫃買抓不到**：Actions 共用 IP 被反爬，設計成可失敗，資料備援走 FinMind。
- **排程沒跑**：見 HANDOFF.md 已知 bug #1。
