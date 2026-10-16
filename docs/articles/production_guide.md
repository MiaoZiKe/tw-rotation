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

## 自動排隊：產貼文頻率設定（2026-10-16，Andy：「先都不要填，它為可動開關……開啟後，會依據我設定的週期、時段進行生產對應類別文章」）

管理區 `#admin/articles` →「文章主題」最下面「產貼文頻率設定」。設定存在會員 Worker（`article_schedule` 表，只有管理者能存），
`article-jobs.yml` 每小時同步成 **`data/_state/article_schedule.json`**：

```json
{ "enabled": true, "slots": {"1": ["09:50", "20:50"], "5": ["14:50"]}, "cats": {"news": 1, "intro": 0, "know": 2}, "updated": "2026-10-16 18:00" }
```

- `slots`：key＝星期（1 週一…7 週日，**台北時間**），value＝那天要跑的輪次（現有三輪 09:50／14:50／20:50；日後增加輪次＝改 Worker `SCH_TIMES` 與 Claude 排程時間）。
- `cats`：每一輪每個類別要產幾篇（0～3）；news＝比比快訊、intro＝比比產業鏈、know＝比比知識。
- **Claude 排程每輪醒來時**（`git pull` 後，先讀 `article_jobs.json` 再讀這支）：
  1. 檔案不存在、`enabled` 不是 `true` → **一律不排**（Andy 關著就是關著）。
  2. 取台北現在的星期與輪次（09:50／14:50／20:50 其中之一）；`slots[星期]` 不含這一輪 → 不排。
  3. 對 `cats` 裡每個大於 0 的類別，從 `site/articles/topics.json` 挑該類別**還沒上架、也還沒在佇列**的最高分主題，依篇數各挑 N 個，用 `scripts/article_jobs.py` 同一套 Worker 機器路由排進佇列（`kind=article`），再照下面流程處理。**同一輪同一個主題不重複排**。
  4. 候選主題不夠就少排，不要硬湊；在回報裡寫「該類別候選不足」。
- 關掉開關 → 下一次同步後 `enabled=false`，之後的輪次不再排；**已經在佇列的項目照常處理**（要停請到「產出進度」按取消）。
- 設定生效最久約：每小時同步（:41）＋排程到點，頁面上也寫明這一點。

## 標狀態

用 GitHub Actions 手動觸發 `article-jobs.yml`（`workflow_dispatch`）：

| 參數 | 值 |
|---|---|
| `mark_id` | 請求編號 |
| `mark_status` | `working`（開工）／`done`（完成）／`failed`（做不出來） |
| `result` | 完成時填文章 id 或影片路徑；失敗時填一句原因 |

開工前先標 `working`（管理區會顯示「撰寫中」，Andy 也不能再取消）。

## 寫一篇精選文章

- 格式：照 `site/articles/posts/*.json` 既有幾篇（區塊型別：h、p、ul、callout、table、stocks、kpi、chart、flow、stack、steps、compare）。
- **★ 3 分鐘看完（Andy 10-16：「不用太多，但需要重點 且直觀看得懂 3min 內可以看完」）**，每篇都照這幾條：
  1. **字數上限**：內文（h／p／ul／callout，不含圖表、表格、相關台股、來源、免責）**約 700～900 個中文字以內**；連圖表裡的字一起算，全篇控制在約 1,300 字。`reading_min` 寫實際值，**必須 ≤ 3**。
  2. **三句話重點**：第一個區塊固定是 `{"t":"h","text":"三句話重點"}` ＋ 三條的 `ul`；只看這三句就要懂這篇在講什麼（含最關鍵的數字）。
  3. **結論先行**：每個小節標題本身就是結論（例如「要看季、不看月：第三季創新高」），第一句話也是結論，理由放後面。不寫「前言」「先從名字拆起」這種鋪陳。
  4. **圖表上限**：圖（chart／flow／stack／steps／compare）**每篇最多 3 張**，挑最能講清楚重點的；數字卡（kpi）最多 2 組、對照表（table）最多 1 張。同一件事不要用圖、表、段落各講一次。
  5. **圖說一句話**：`note` 只寫一句（口徑或「不代表個別訂單」這種必要警語）。
  6. 能用數字卡、圖、流程圖、對照表講的，就不要寫成長段落；段落一段 ≤ 120 字。
  7. 刪減時只能刪次要數字，**不能改值、不能新增沒有來源的數字**；`sources` 與免責聲明一律保留。
- `site/articles/index.json` 新增一筆，**一定要帶 `"topic": "<主題 id>"`**（自動標完成就靠它），以及 `groups`（相關族群）。
- **自訂主題（Andy 10-16：「也需要我填寫主題 產文章，例如 今天新聞 馬斯克飛天電動車介紹」，管理區有「自訂主題」欄）**：
  佇列裡 `topic_id` 開頭是 `c-<news|intro|know>-<時間碼>` 的，是 Andy 自己填的主題 ——
  類別取 id 中間那段（news／intro／know），標題與主題就是請求的 `title`（補充看 `note`）；
  `topics.json` 裡查不到這個 id 是正常的，不要當成錯誤跳過，要**從頭查證撰寫**。
  `index.json` 一樣要帶 `"topic": "<這個 topic_id>"`，才會自動標完成。同樣照上面「3 分鐘看完」的規則寫。
- id 格式：`<YYYY-MM-DD>-<news|intro|know>-<英文短名>`；類別依主題的 `cat`。
- 數字一律用資料湖（`data/`）或公司公告；查證規矩照 CLAUDE.md「有疑問先上網查」—— 只能用 WebSearch，摘要是線索不是事實，兩個獨立來源對得上才寫；來源日期寫原文日期，不寫查詢日。
- 不寫投資建議、不寫目標價；結尾保留免責。
- Andy 的補充（`note`）要照做；補充跟查證衝突時以證據為準，並在文末寫明。
- 驗收：`python scripts/_uitest.py --sections 精選文章1014 --workers 1`、`python scripts/_preview.py`；自己看 1440 與 390 截圖。
- 推 main → `python scripts/deploy_wait.py --branch main` 印出 ✅ → 標 `done`（result＝文章 id）。

## 做一支短影片

- 規格與不重疊規矩：`docs/marketing/video_1010/layout_rules.md`（回報要有「重疊檢查：程式 N 幀 0 筆；人工 M 格 0 筆」）。
- 成品放 `docs/marketing/videos/<YYYY-MM-DD>-<主題 id>/`（直式 1080×1920 MP4＋封面），標 `done`（result＝資料夾路徑）。

## 傳給 GPT（IG 貼文／影片；純前端，不經佇列）

已上架文章每列有「傳給 GPT・IG 貼文」「傳給 GPT・影片」（手機＝下拉選類型＋一顆送出）。按下去＝**Andy 決定這篇要交接**：
前端（`site/gpthandoff.js`）讀該篇文章 JSON，組成 Markdown，開預填的 GitHub 新 Issue（label `social-handoff` 加 `gpt-ig-post` 或 `gpt-video`，
標題 `[社群交接] 日期｜IG 貼文｜文章標題`／`…｜影片｜…`），Andy 在 GitHub 按 Submit new issue 才算送出。不排隊、不碰 Worker、Claude 排程不處理這個。
內容只放文章已公開的部分；網址超過 8 KB 會自動省略站內連結／關鍵數據／來源，完整內容用頁面上的「複製完整交接內容」。

## 安全

- `data/_state/article_jobs.json` 在 public repo：管理區的補充欄已提示「請勿填個資」；寫入的欄位不含會員 uid／email。
- 機器鑰匙 `ARTICLE_BOT_KEY`＝`sha256("tw-article-jobs|" + CLOUDFLARE_API_TOKEN)` 前 48 字，兩支工作流各自算，不進 repo、不進 log（`::add-mask::`）。換 Cloudflare 權杖後要重跑「部署 Worker」。
