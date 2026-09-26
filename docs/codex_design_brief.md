# 給 Codex 的設計任務說明（新版介面 UI v2）

> 這份是給**另一個 AI（OpenAI Codex）**接手做視覺設計用的。寫於 2026-09-26（台北）。
> ⚠ 根目錄的 `AGENTS.md` 與 `CLAUDE.md` 是本專案另一套 AI 團隊（Claude）的分工與規矩，
> 裡面「推上 main」「部署」那些流程**不適用於這個任務**。這個任務以本檔為準。

## 1. 這是什麼網站

「台股資金輪動儀表板」：每天盤後自動抓免費合規資料 → 算指標 → 產出**純靜態網站**（沒有後端、沒有框架、沒有打包工具）。
回答四個問題：**錢往哪個族群跑、那個族群貴不貴、什麼時候進場、有沒有理由不進場。**

- 正式網站（舊介面，**不要動**）：<https://miaozike.github.io/tw-rotation/>
- 新版介面在分支 `claude/elegant-pasteur-ggwgnb`：左側導覽、頁首說明、「本頁功能」跳轉列、新配色、命名提案〈輪輪〉。
  四個命名提案（SVG 與提案圖）在 `docs/brand/`。

## 2. 你要做的事

在**不改任何功能**的前提下，讓新版介面更好看、更親切、第一眼就知道每一頁的功能在哪裡。
擁有者 Andy 的原話：「版面看起來舒服，功能都很單一，一頁就知道這頁功能在哪裡，版面色調都需要調整好看，
功能不要動到，只會動到 UI 的版面」。對標網站：<https://www.stockintelli.com/>、<https://assetmetra.com/demo?view=rrg>。

## 3. 分支規則

- **從 `claude/elegant-pasteur-ggwgnb` 開一條新分支**（例如 `codex/ui-design`），做完開 PR **合回 `claude/elegant-pasteur-ggwgnb`**。
- **絕不推 `main`、絕不 force push。** `main` 一推就會部署正式網站。
- 不要改 `data/`（資料湖，雲端每天會寫）、`pipeline/`（資料計算）、`.github/`（部署流程）。

## 4. 環境設定（Codex 的 setup script，這一段有網路）

```bash
pip install -r requirements.txt playwright
python -m playwright install --with-deps chromium
# 前端要吃的 JSON 不在 git 裡（site/data/ 是 gitignore），要從 repo 內的資料湖算出來。
# SKIP_INTRADAY=1 會跳過唯一一個要連外（Yahoo 分 K）的步驟；其他步驟只讀 data/*.parquet。約 5～10 分鐘。
SKIP_INTRADAY=1 python -m pipeline.build_payload
```

算完之後 `site/` 就是一個完整的網站：

```bash
python -m http.server 8000 -d site      # 開 http://localhost:8000/#overview
python scripts/_show.py --view overview --width 1440,390   # 截圖到 docs/_show/（不進版控）
```

## 5. 檔案地圖：哪些可以改

| 檔案 | 可不可以改 | 說明 |
|---|---|---|
| `site/ui2.css` | ✅ 主要改這支 | 新版的全部樣式。規則都掛在 `:root.ui2` 底下（`<html class="ui2">`），拿掉 class 就是舊版外觀 |
| `site/ui2.js` | ✅ | 頁首、「本頁功能」跳轉列、導覽收合、事件浮層。**只讀畫面、只加裝飾**，不准碰路由與資料 |
| `site/icons/lunlun.svg`、`docs/brand/*` | ✅ | 命名提案〈輪輪〉的圖示 |
| `site/index.html` | ⚠ 只改標記 | 可以加 class、調順序；**所有 id、`data-*` 屬性、`.tab[data-view]` 一個都不能改名或刪掉**（JS 與驗收靠它們） |
| `site/app.js`、`industry.js`、`chart.js`、`market3.js`、`live.js`、`mobile3.js`… | ❌ 不要改邏輯 | 真的非改不可（例如版面改了導致某個計算位置的程式失效），只做最小的相容修正，並在 PR 說明為什麼 |
| `site/vendor/` | ❌ | ECharts、Lightweight Charts、three.js，內建於 repo |
| `pipeline/`、`data/`、`.github/`、`tests/` | ❌ | 資料與部署，跟這個任務無關 |

## 6. 設計規則（這些是硬規則）

1. **紅漲綠跌**（台股慣例，跟國外相反）。`--rise` 是紅、`--fall` 是綠，不准對調。
2. **不准用 CDN、外部字型、外部圖片**。Andy 公司的網路擋 CDN（Google Fonts 也會逾時）。字型只能用系統字：
   `"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif`。
3. **色彩變數名稱不要改**：`--cyan` 雖然叫 cyan，其實是「主色」；`app.js` 的 `refreshPalette()` 照這些名字把顏色讀進圖表。
   改值可以，改名字圖表就讀不到。深色在 `:root.ui2:not([data-theme="light"])`，淺色在 `:root.ui2[data-theme="light"]`。
4. **兩個主題都要做**（右下角「明亮／深色」切換）。文字對底色對比 ≥ 4.5:1，字級下限 12px，數字用 `tabular-nums`。
5. **桌機（≥821px）與手機（≤820px）是兩套版面。** 手機版有「一屏看完」的高度預算與底部分頁列（`mobile3.js`），
   這一版**手機只換配色**。要改手機版面，先在 PR 裡講清楚，並跑手機的驗收。
6. 不要為了好看拿掉任何按鈕、篩選、圖表。可以改位置、改樣式、收進選單，但功能要還在、按得到。
7. 熱力圖的 7 格色階（`--hm-*`）與剖析圖的材質色（`--dg-*`）是調過對比的，要改就兩個主題一起改並量對比。

## 7. 頁面地圖（hash 路由）

| 網址 | 頁面 | 這頁回答什麼 |
|---|---|---|
| `#overview` | 總覽 | 今天大盤、錢集中在哪幾個族群、題材與法人 |
| `#flow` | 資金流向 | 資金輪盤（輪動四象限）、流向排行、資金去向 |
| `#heatmap` | 熱力圖 | 全市場與題材的冷熱 |
| `#industry`、`#industry/ai_server` | 產業地圖 | 產業鏈強弱、上下游、剖析圖 |
| `#stock/2330` | 個股 | K 線、多週期、營收、籌碼、除權息 |
| `#market` | 市場明細 | 漲跌分佈、站上均線、排行名單 |
| `#season` | 週期統計 | 族群 × 月份的歷史表現 |
| `#delivery` | 交付清單 | Andy 的需求清單 |

## 8. 驗收（PR 之前一定要跑，結果貼在 PR 裡）

```bash
python scripts/_preview.py          # 真圖表庫走過所有頁面：抓文字重疊、多寬度溢出。必須最後印「所有分頁與個股頁正常」
python scripts/_uitest.py --sections 新版介面UI2,總覽,資金流向,產業,個股,熱力圖v2,季節性,市場明細,淺色主題,手機 --workers 1
```

- `_uitest.py` 是「真人操作」驗收：真的點每顆按鈕、驗畫面真的變了。**不要為了變綠去改斷言**；
  斷言跟新設計衝突時，在 PR 裡寫「哪一條、為什麼、你怎麼證明功能還在」。
- 已知一條紅：`個股` 的「切到 1w 之後價格軸有重新貼合」。功能是好的（實測切週線後範圍＝週線的自然範圍），
  是門檻寫成「比拉開時窄 10%」而新版 K 線較窄剛好差在 94%。詳見 `HANDOFF.md` 最上面那段。
- PR 附截圖：1440、1100、390 三種寬度 × 深色、淺色，至少總覽、資金流向、產業地圖、個股四頁，**改前改後並排**。

## 9. 交付

- 一個 PR（`codex/ui-design` → `claude/elegant-pasteur-ggwgnb`），標題與說明用**繁體中文**。
- 說明裡寫：改了什麼、為什麼這樣改、驗收結果（哪幾段跑了、幾個問題）、截圖、你覺得 Andy 可能不同意的地方。
