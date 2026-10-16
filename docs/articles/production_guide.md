# 精選文章／短影片「產出佇列」作業手冊（2026-10-16）

Andy 10-16：「claude 指負責產出文章，內容……下方是我有功能可以點選清單內主題，點選後我可以再次點選產生精選文章，或是短影片」。

## 流程

1. Andy 在管理區 `#admin/articles` →「主題候選清單」點一列 → 按「產生精選文章」或「產生短影片」（可附補充）。
2. 請求排進會員 Worker 的 `article_jobs` 表（`workers/account-api/articles.js`），狀態 `queued`。
3. `.github/workflows/article-jobs.yml` 每小時 :41 把未完成的請求同步成 **`data/_state/article_jobs.json`**（只有編號、主題 id、種類、標題、補充、狀態、時間）。
4. Claude 排程（台北 09:50、14:50、20:50）`git pull` 後讀這支檔：
   - 空的 → 什麼都不做，直接結束。
   - 有 `queued` → 一次處理一筆（先文章後影片、編號小的先），步驟見下。
5. 文章推上 main 後，`article-jobs.yml`（`site/articles/index.json` 有變就跑）看到 index 裡有同一個 `topic` → 自動標 `done`。

## 標狀態

用 GitHub Actions 手動觸發 `article-jobs.yml`（`workflow_dispatch`）：

| 參數 | 值 |
|---|---|
| `mark_id` | 請求編號 |
| `mark_status` | `working`（開工）／`done`（完成）／`failed`（做不出來） |
| `result` | 完成時填文章 id 或影片路徑；失敗時填一句原因 |

開工前先標 `working`（管理區會顯示「撰寫中」，Andy 也不能再取消）。

## 寫一篇精選文章

- 格式：照 `site/articles/posts/*.json` 既有三篇（區塊型別：h、p、ul、callout、table、stocks、kpi、chart、flow、stack、steps、compare）。
- `site/articles/index.json` 新增一筆，**一定要帶 `"topic": "<主題 id>"`**（自動標完成就靠它），以及 `groups`（相關族群）。
- id 格式：`<YYYY-MM-DD>-<news|intro|know>-<英文短名>`；類別依主題的 `cat`。
- 數字一律用資料湖（`data/`）或公司公告；查證規矩照 CLAUDE.md「有疑問先上網查」—— 只能用 WebSearch，摘要是線索不是事實，兩個獨立來源對得上才寫；來源日期寫原文日期，不寫查詢日。
- 不寫投資建議、不寫目標價；結尾保留免責。
- Andy 的補充（`note`）要照做；補充跟查證衝突時以證據為準，並在文末寫明。
- 驗收：`python scripts/_uitest.py --sections 精選文章1014 --workers 1`、`python scripts/_preview.py`；自己看 1440 與 390 截圖。
- 推 main → `python scripts/deploy_wait.py --branch main` 印出 ✅ → 標 `done`（result＝文章 id）。

## 做一支短影片

- 規格與不重疊規矩：`docs/marketing/video_1010/layout_rules.md`（回報要有「重疊檢查：程式 N 幀 0 筆；人工 M 格 0 筆」）。
- 成品放 `docs/marketing/videos/<YYYY-MM-DD>-<主題 id>/`（直式 1080×1920 MP4＋封面），標 `done`（result＝資料夾路徑）。

## 安全

- `data/_state/article_jobs.json` 在 public repo：管理區的補充欄已提示「請勿填個資」；寫入的欄位不含會員 uid／email。
- 機器鑰匙 `ARTICLE_BOT_KEY`＝`sha256("tw-article-jobs|" + CLOUDFLARE_API_TOKEN)` 前 48 字，兩支工作流各自算，不進 repo、不進 log（`::add-mask::`）。換 Cloudflare 權杖後要重跑「部署 Worker」。
