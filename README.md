# 台股資金輪動儀表板

每天盤後自動抓資料、算指標、產出一頁式儀表板，回答四個問題：
**錢往哪個族群跑、那個族群現在貴不貴、什麼時候可以進場、有沒有理由不進場。**

- 資料源全部免費且合規（不碰證交所官網禁爬條文）
- 跑在 GitHub Actions，本機不用開機
- 網站掛 GitHub Pages，手機也能看

---

## 上線步驟

### 1. 建 repo 並推上去

```bash
cd tw-rotation
git init
git add -A
git commit -m "初始版本：資料層、指標庫、每日管線、儀表板"
gh repo create tw-rotation --public --source=. --push
# 或手動：到 github.com 開一個 public repo，再 git remote add origin ... && git push -u origin main
```

### 2. 拿 FinMind token

到 <https://finmindtrade.com> 註冊並**驗證 email**（未註冊每小時只有 300 次，
註冊後 600 次，歷史回補時差很多），在會員頁複製 token。

### 3. 設定 Secrets

Repo → Settings → Secrets and variables → Actions → New repository secret：

| 名稱 | 值 | 必要性 |
|---|---|---|
| `FINMIND_TOKEN` | FinMind 會員頁的 token | 必要（歷史與法人籌碼靠它） |
| `FRED_API_KEY` | <https://fred.stlouisfed.org/docs/api/api_key.html> 免費申請 | 選用（總經指標） |

### 4. 開啟 GitHub Pages

Repo → Settings → Pages → Source 選 **GitHub Actions**。

### 5. 開啟 Actions 寫入權限

Repo → Settings → Actions → General → Workflow permissions
選 **Read and write permissions**（管線要把資料 commit 回 repo）。

### 6. 跑第一次

Actions → 「每日盤後管線」→ Run workflow。
跑完之後 Pages 網址就會有東西了（首次部署約 1–2 分鐘）。

### 7. 回補歷史（重要，越早越好）

Actions → 「歷史回補」→ Run workflow，`limit` 填 `400`、`datasets` 選 `price+inst`。

> **為什麼這件事不能拖**：證交所開放資料只有「最新一天的快照」，沒有任何歷史。
> 季節性、相對強弱、技術指標全都需要歷史。FinMind 是目前唯一能免費補回十年的途徑。
> 額度是每小時 600 次，一輪跑不完就再按一次，它會自動從沒補到的地方接續。

---

## 手機

Pages 網址就是一般網址，手機瀏覽器直接開。版面對窄螢幕做過調整：

- 市場體溫改成兩欄，圖表高度縮小
- **候選股改成卡片版** —— 桌機的 15 欄表格在手機上要一直左右拉，
  所以窄螢幕改成一檔一張卡，每張把技術分、均線、SMC 結構、RSI/KD、
  同業本益比分位、投信買超收在一眼看得完的範圍內
- 卡片一次 20 檔，按「再顯示」載入下一批
- 表頭點不到，所以另外給一個排序下拉選單

iOS 用 Safari 開 → 分享 → **加入主畫面**，之後點圖示會全螢幕開啟、沒有網址列，
用起來就像 App。Android Chrome 是選單 → 加到主畫面。

> repo 設成 public 的話，Pages 網址是公開的 —— 任何拿到網址的人都看得到。
> 裡面全是公開市場資料所以沒差，但**持股部位與成本價這類東西絕對不要放進 repo**。

## 在兩台電腦上開發

repo 本身就是同步機制：

```bash
git clone https://github.com/<你的帳號>/tw-rotation.git
cd tw-rotation
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/ -q
```

改完 `git push`，雲端下一輪就照新的邏輯跑。
懶得裝環境的話，在 repo 頁按 `.` 或開 **Codespaces**，瀏覽器裡直接改。

本機要看畫面：

```bash
python -m scripts.make_demo     # 產生示範資料（不會碰到真實的 data/）
python -m http.server -d site 8000
```

---

## 專案結構

```
pipeline/
  config.py             所有路徑、端點、參數
  indicators.py         MA / MACD / RSI / KD / SMC（附單元測試）
  run_daily.py          每日盤後管線
  run_backfill.py       歷史回補（可重複執行）
  build_payload.py      算成前端要的 JSON
  util/
    roc.py              民國日期、千元單位、空值處理
    http.py             重試退避 + FinMind 額度管理
    store.py            Parquet append-only 資料湖
  sources/
    twse.py             證交所 OpenAPI（每日增量主力）
    finmind.py          歷史回補 + 三大法人
    tdcc.py             集保股權分散（每週）
    tpex.py             上櫃（可失敗，有備援）
    news.py             鉅亨 API + 經濟日報 RSS
    macro.py            yfinance 國際指數 + FRED 總經
  compute/
    flow.py             M1 資金面：族群彙總、輪動雷達、集中度、RS
  groups/
    groups.yaml         ★ 族群對照表（唯一需要人工維護的檔案）
    loader.py           讀取與健康檢查
site/
  index.html            儀表板（ECharts）
  data/                 管線產出的 JSON
data/                   Parquet 資料湖（append-only，不要手動改）
tests/                  60 個測試，CI 跑不過就不會寫資料
```

---

## 資料源

| 來源 | 拿到什麼 | 歷史 | 備註 |
|---|---|---|---|
| 證交所 OpenAPI | 全市場日行情、PE/PB/殖利率、融資券、類股指數、月營收、EPS、股利 | 無，僅 T-1 快照 | 免 key、無限速、屬政府開放資料 |
| FinMind 免費版 | 日 K 歷史、**三大法人**、融資券、財報、PER | 完整 | 600 req/hr，回補主力 |
| 集保結算所 | 股權分散、千張大戶比例 | 每週累積 | CSV，零阻礙 |
| 櫃買中心 | 上櫃行情 | 無 | **有反爬，可能失敗** → 自動改走 FinMind |
| 鉅亨網 API | 新聞，含 `market`（股票代號）與 `keyword`（題材） | — | 非官方端點 |
| 經濟日報 RSS | 新聞備援 | — | 標準 RSS |
| yfinance / FRED | SOX、NDX、DXY、VIX、台幣、美債、CPI | 數十年 | 免費 |

**刻意不用**：FinLab 免費版（資料停在 2021）、TradingEconomics（無真正免費層）、
Goodinfo（JS 渲染＋反爬）、`fugle-realtime`（2023 停更）、`fredapi`（2024 停更）。

### 合規說明

證交所使用條款明文禁止以爬蟲抓取**官網**資料，但明確排除提供給政府資料開放平臺的內容。
所以這個專案只打 `openapi.twse.com.tw`，不碰 `www.twse.com.tw/rwd/...` 的官網端點。
代價是拿不到官網才有的個股別三大法人與當日（非 T-1）資料 —— 前者改走 FinMind，
後者接受延遲一天（這是波段工具，不是當沖工具）。

---

## 族群對照表怎麼維護

`pipeline/groups/groups.yaml` 是全案唯一需要人工照顧的檔案，也是最有價值的一份 ——
抓得到的資料大家都有，族群怎麼切才是自己的判斷。

規則：

1. 一檔股票可以屬於多個族群（鴻海既是 AI 伺服器也是手機供應鏈）。
   它的成交值會**依所屬族群數平均拆分**，不會兩邊各算一次完整金額。
2. `tier` 標上中下游，`chains` 定義供應鏈順序，用來看「上游先漲，下游會不會跟」。
3. `meta.reviewed` 是上次人工檢視日期。超過 100 天，儀表板頂端會出現提醒。
4. 寧缺勿濫：放進來的每一檔都要是實際受惠者，不是「新聞提過一次」就算。

參考來源：官方[產業價值鏈資訊平台](https://ic.tpex.org.tw/)（上中下游骨架）、
[MoneyDJ 概念股](https://www.moneydj.com/Z/ZG/ZGE/ZGE.djhtm?a=E&b=E)（熱門題材）。

---

## 已知限制

| 限制 | 現況 |
|---|---|
| **歷史冷啟動** | 開放資料無歷史，靠 FinMind 一次性回補。回補前季節性與 RS 都不準 |
| **T-1 延遲** | 走開放資料就是慢一天。要當日資料只能碰禁爬條款，不做 |
| **族群表會老化** | 每季要人工檢視一次，儀表板會提醒 |
| **排程會靜默失效** | Actions 免費層 cron 會延遲；repo 連續 60 天沒 commit 會自動停用排程。每輪成功都會 commit，兼作 keepalive；頁面頂端顯示資料日期，超過 4 天變紅字 |
| **季節性樣本少** | 十年 = 每月 10 個樣本。熱力圖強制同時顯示平均報酬、勝率、樣本數，且樣本 < 3 一律留白 |
| **生存者偏差** | 用今天的成分股回推歷史會高估績效。目前是「標示已知偏差」而非消除 |
| **綜合評分未經驗證** | `indicators.technical_score` 的權重是起始假設。階段 4 的 walk-forward 檢驗會回頭調它 |

**這是決策輔助工具，不是交易系統。** 不接下單、不自動執行，只輸出候選與判斷依據。

---

## 常用指令

```bash
python -m pytest tests/ -q                          # 全部測試
python -m pipeline.run_daily --skip-finmind         # 只跑不耗額度的來源
python -m pipeline.run_backfill --limit 200 --datasets price+inst
python -m pipeline.build_payload                    # 只重算前端 JSON
python -m scripts.make_demo                         # 產生示範資料
```

執行紀錄在 `data/_state/last_run.json`：每個步驟的成敗、列數、耗時、
FinMind 剩餘額度、各表最新日期。Actions 的 Summary 頁也會印同一份摘要。
