# HANDOFF.md — 目前進度（接手先讀這份）

**最後更新：2026-09-11 23:40（台北）** by Claude（session 01GzXbt3…）
**最新程式 commit：`dd1a014` v3 全量推上 main**（31 個檔、移除 166 個舊 `site/data/*.json`）＋ 本次交接文件 commit（含一個資料日期 bug 修正，見第 3 節 #0）。
**線上已驗證**：v3 前端已部署（LightweightCharts／Industry 都載入、`flow_v3`/`themes`/`industry_map`/`seasonality_v3` JSON 都在），
Yahoo 分 K 在 Actions 上正常（6179：15 分 1059 根、60 分 1800 根、240 分 800 根），排程（cron）已開始自動跑。

圖例：✅ 已完成（程式＋本機驗證）｜🚧 進行中／已寫但未在線上驗證｜⬜ 未開始

---

## 0. 接手後第一件要做的事（「下一步」）

1. `git pull`，讀完 `AGENTS.md`、`DECISIONS.md`。
2. **驗證本次 commit 觸發的「部署網站」run 成功後，個股頁對上市股恢復正常**：
   打開 <https://miaozike.github.io/tw-rotation/#stock/2330>（Ctrl+F5）要能看到台積電的分 K／多週期／營收等分頁，
   `data/candidates.json` 要同時有上市與上櫃（之前 130 檔全是上櫃，見第 3 節 #0）；`#overview` 的族群統計
   日期應為 2026-09-10（上市資料到齊的最後一天），而不是只有櫃買的 09-11。
3. **逐頁走一次線上 v3**（這是唯一還沒做的人工驗收）：`#overview` → `#flow` → `#industry` → 點一條產業鏈 →
   點一檔股票 → 分 K 切 15m/1H/4H/1D/1W/1M、勾 RSI、滾輪縮放價格軸、多週期 SMC 格、下方營收／獲利／除權息／
   籌碼／基本資料分頁 → `#themes` → `#season`；再用手機寬（DevTools 390px）走一次。
   有 console 錯誤或空白頁就是 bug，記到本檔第 3 節再修。
4. 看隔天（09-14 週一）的每日管線是否拿到 09-11 與 09-14 兩天的上市資料（`data/_state/last_run.json` 的
   `twse.price_daily` stored 應 > 0）。若證交所 OpenAPI 持續給前一天，要把每日管線改成「18:30 跑一次、
   若上市資料仍是前一天則 21:30 再跑一次」。
5. 提醒 Andy 做兩件安全事（本檔第 5 節）。
6. 做完以上才開始第 4 節「還沒做」的項目；每次結束前更新本檔並 push。

---

## 1. v3 需求逐條狀態

### 技術分析（個股頁上半）
| # | 需求 | 狀態 | 備註 |
|---|---|---|---|
| 1 | K 線更人性化、參考元大／TradingView | ✅ | 換成 TradingView Lightweight Charts 5.2.1（`site/vendor/`，Apache-2.0，LICENSE 同目錄） |
| 2 | 時間週期 15 分／1 時／4 時／日／週／月 | ✅ | 日／週／月本機驗證 OK；15m/1H/4H 走 Yahoo，Actions 上已驗證有資料（線上 6179.json intraday 15m/60m/240m 都有） |
| 3 | 指標可勾選、參數可調（MA/KD/MACD/RSI/BOLL） | ✅ | 瀏覽器端算（`chart.js` 的 `KInd`），設定存 localStorage `tw.kcfg` |
| 4 | 滾輪縮放價格軸（像 TradingView） | ✅ | price scale `setVisibleRange` |
| 5 | 四個時間週期同看 + SMC 支撐壓力統整 | ✅ | `compute/mtf.py`：無分 K 時改「週線 vs 日線」並明講 |
| 6 | 主力（券商分點家數差） | ✅ 替代 | 無免費合規來源 → 集保千張大戶增減＋法人動向，頁面有註明 |

### 個股資訊（個股頁下半）
| # | 需求 | 狀態 | 備註 |
|---|---|---|---|
| 7 | 大戶散戶持有狀況 | 🚧 | 程式完成（`stockpage.holder_series`）；**每日 `tdcc.shareholding` 步驟目前失敗**，歷史靠 FinMind 回補計畫第 3 步（尚未跑到） |
| 8 | 法人買賣（日、20/60 日累計、外資／投信） | ✅ | 回補 inst 已 401 檔 |
| 9 | 資券 | 🚧 | 程式完成；FinMind 融資券歷史在回補第 3 步，尚未跑到 |
| 10 | 營收 YoY／MoM／累計 YoY／每月／5 年年度走勢＋累計 | 🚧 | 程式完成；FinMind 月營收歷史只回補到 **44 檔**（402 限流即停），其餘靠每小時排程續補 |
| 11 | 獲利 5 年：毛利／淨利／EPS／累計 EPS | 🚧 | 依法只有季報（頁面註明）；財報歷史同樣只有 ~45 檔 |
| 12 | 近 5 年每季營收／EPS／本益比 | 🚧 | `pe_history` 完成；資料量同上 |
| 13 | 基本資料、除權息、籌碼、財務 | 🚧 | 除權息（含填息天數、現金股利 TTM、殖利率）在回補第 2 步；**每日 `twse.dividend` 步驟目前失敗** |

### 產業鏈／族群／題材
| # | 需求 | 狀態 | 備註 |
|---|---|---|---|
| 14 | 個股與產業鏈合併，點股票時上方產業鏈同步高亮 | ✅ | `site/industry.js`：地圖 → 單鏈 → 個股三層 |
| 15 | 產業鏈要有本益比（環節中位數） | ✅ | `industry_map.segments_pe` |
| 16 | 產業鏈可進出、資訊更豐富 | ✅ | |
| 17 | 族群板塊 ETF／其他電子看不到個股（bug） | 🚧 | `group_detail` 改用 `flow._attach_groups` 已修，本機 OK；線上 `groups_detail.json` 已含 `ind_*` 族群，**點擊下鑽未人工驗** |
| 18 | 題材資金熱力圖 | ✅ | `compute/themes.py` + `groups/themes.yaml`（18 個題材，量能不拆分） |
| 19 | 市占產品剖析圖（找不到就自己畫動畫 SVG） | 🚧 | 已畫 AI 伺服器托盤、CoWoS 剖面（`site/diagrams.js`）；其他產業鏈 ⬜ |

### 其他頁面與整體
| # | 需求 | 狀態 | 備註 |
|---|---|---|---|
| 20 | 資金流向不要直條圖 | ✅ | RRG／桑基／河流（`compute/rrg.py`） |
| 21 | 季節性 2000 年起、可切觀察期、超額報酬 | 🚧 | 程式完成（all/10y/5y/3y、相對大盤）；**價量回補到 2000 年是計畫第 4 步，尚未跑到**，目前只有 2016 起 |
| 22 | 整體風格科技／AI／專業、字體加大 | ✅ | |
| 23 | 檢查文字重疊、排版、手機 | 🚧 | `scripts/_preview.py` 本機 0 重疊、390px OK；**真機未驗** |
| 24 | 下方資訊可視化（不只表格） | ✅ | |
| 25 | `site/data/` 不進版控，由工作流產出 | ✅ | 已 gitignore；`pages.yml`（12:34 UTC）與 `daily.yml`（14:33 UTC 排程）都成功 build＋部署 |
| 26 | 先 Yahoo 分 K，之後 Fugle 即時 | ⬜ Fugle | 等 Andy 給 Fugle key；設計是前端 WebSocket 直連 + Cloudflare Workers 藏 key |

---

## 2. 已完成的基礎（v1／v2，別重做）

資料湖（Parquet append-only，16 張表）、TWSE OpenAPI／FinMind／集保／櫃買／新聞／FRED 抓取層、
指標庫（無未來函數測試）、M1 資金面、M2 基本面（TTM EPS、自算 PE、族群分位 pb_roe/ps 口徑、月營收動能）、
M3 規則引擎（多源交集區間、A/B/觀望/不要碰、停損與測量目標）、新聞三分類與券商目標價引述、
GitHub Actions 三條工作流、145 個測試。

---

## 3. 已知 bug 與尚未驗證的部分

0. **（已修，待部署驗證）最新交易日只有櫃買到齊 → 上市股全部被算漏**：09-11 的每日管線裡證交所 OpenAPI 仍回 09-10
   的資料（`twse.price_daily` stored 0），櫃買回了 09-11；`build_payload` 用 `max(date)` 當最新日，結果
   `candidates.json` 130 檔全是上櫃、`#stock/2330` 等上市個股頁 404、族群統計只剩上櫃。
   修法：`build_payload.last_complete_date()`（只看上市檔數、近 10 日最大值的 60% 為門檻）＋各日表裁到同一天；
   `tests/test_latest_date.py` 5 個測試。本次 commit 會觸發「部署網站」重算；接手第一件事就是驗證（第 0 節第 2 點）。
1. ~~cron 排程從未觸發過~~ **已解決**：09-11 12:50 UTC「歷史回補」、14:33 UTC「每日盤後管線」都是 `event=schedule`
   成功跑完。每日管線比 cron 的 10:30 晚了 4 小時，GitHub 免費層延遲屬正常（DECISIONS #45）。
2. **每日管線兩步驟失敗**（`data/_state/last_run.json`）：`twse.dividend` ok=false（20 秒逾時）、
   `tdcc.shareholding` ok=false。管線設計成可失敗所以其他資料照常，但除權息與大戶散戶就沒有新資料。
   要看 `sources/twse.py`／`sources/tdcc.py` 的端點是否改了。
3. **FinMind 回補進度**：12:50 UTC 的排程回補已推 `867c03a`（財報／資產負債 2016 起繼續補）。看
   `data/_state/backfill_progress.json` 的 `done` 計數與 `complete` 旗標；每小時會自動接續直到 `plan:default` 完成。
4. ~~Yahoo 分 K 在 Actions 上未驗證~~ **已驗證**（線上個股頁 intraday 15m/60m/240m 有資料）。
5. **線上 v3 頁面只驗了資料檔與程式載入**，分頁互動與手機寬還沒人工走過（第 0 節第 3 點）。
6. **從 Andy 瀏覽器推 GitHub API 會間歇 `Failed to fetch`**（公司 proxy）：推送腳本已改成
   背景工作 + 重試 8 次（見 SETUP.md「Claude 怎麼推程式碼」）；別再用逐檔同步等待的寫法。
   另外 Claude 桌面版的內建瀏覽器窗格在連線重連後會反覆回「No browser pane is open」；這時改用 Claude in Chrome
   （Andy 的 Chrome 分頁）執行同一份腳本即可，本次交接 commit 就是這樣推上去的。
7. `docs/*.png` 在 `.gitignore`，所以截圖只在本機；要給 Andy 看截圖得用對話附件。
8. 季節性、RS 在 2000 年價量補齊前不準（頁面有標樣本數）。

---

## 4. 還沒做（依優先序）

1. ⬜ 盯著每小時排程把 `--plan default` 跑完（財報 → 股利 → 資券／集保 → 2000 年價量）；完成後季節性與 RS 才準。
2. ⬜ 修 `twse.dividend`、`tdcc.shareholding` 兩個每日步驟（bug #2）；並確認證交所 OpenAPI 給前一天資料時的重跑策略（第 0 節第 4 點）。
3. ⬜ Fugle 即時層（等 key）：前端 WebSocket + Cloudflare Workers。
4. ⬜ M4 事件面計算：新聞歸戶到個股／族群、新聞量異常、國際連動係數。
5. ⬜ 綜合評分：M1/M2/M3/M4 依 `config.SCORE_WEIGHTS` 合成。
6. ⬜ walk-forward 檢驗 `technical_score()`：結果不好要誠實寫在頁面，不調參數湊。
7. ⬜ `build_groups.py`：從產業價值鏈平台／MoneyDJ 產「建議新增／移除」報告（只產報告，不改 YAML）。
8. ⬜ `supply_chain.yaml` 市占率補來源與日期；其他產業鏈的產品剖析動畫 SVG。
9. ⬜ Andy 校訂 `groups.yaml` / `themes.yaml` / `supply_chain.yaml`。

---

## 5. 要提醒 Andy 的安全事項

- 這次對話裡 Andy 貼過一組 GitHub fine-grained PAT（用來讓 Claude 推程式碼）。**穩定後請到 GitHub → Settings →
  Developer settings → Fine-grained tokens 重新產生一組**，舊的作廢；新的只給 `tw-rotation` 的 Contents / Workflows / Actions 讀寫。
- FinMind token 曾出現在截圖裡，建議到 FinMind 會員頁重置，再更新 GitHub Secret `FINMIND_TOKEN`。
- 兩者都**不要**貼進 repo 任何檔案；只放 GitHub Secrets 與 Claude 當次對話。
