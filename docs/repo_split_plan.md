# repo 拆分計畫：私人（原始碼與備份）＋ 公開（執行用）

> 2026-10-07 台北 01:15 Andy 拍板選 A。原話：「GitHub 需要設置私人，並且他當備份用的，然後每次修改就改 GitHub 這裡，但 Cloudflare 同步」。
> 本文件只是計畫與草稿；**還沒有任何東西搬動、沒有推 main、沒有改寫歷史**。
> 分支：`claude/repo-split`。相關檔案：`scripts/build_public_tree.py`、`.github/workflows/sync-to-public.yml`、`.github/workflows/pull-data-from-public.yml`。

## 1. 一張圖

```
 Claude／人 改程式與文件
        │ push main（或 preview/<名稱>）
        ▼
┌────────────────────────────────────────────┐        ┌─────────────────────────────────────────────┐
│ 私人 repo  MiaoZiKe/tw-rotation-private    │        │ 公開 repo  MiaoZiKe/tw-rotation（現有）      │
│ ・唯一的原始碼來源 ＋ 備份                  │ ①同步  │ ・只放「執行需要」的檔案（去註解）           │
│ ・CLAUDE／DECISIONS／HANDOFF／docs／obsidian│───────▶│ ・每日管線、回補、部署、Cloudflare 照舊在這跑 │
│ ・Andy 原話、完整註解                       │ 程式碼 │ ・data/（資料湖）的權威在這裡                │
│ ・只跑 2 支輕量工作流（同步、備份資料）     │        │ ・pages.yml → GitHub Pages ＋ Cloudflare     │
│                                            │◀───────│                                             │
└────────────────────────────────────────────┘ ②備份  └─────────────────────────────────────────────┘
   sync-to-public.yml：push 觸發                 資料湖
   pull-data-from-public.yml：每天 1 次（台北 06:10）
```

方向永遠固定：**程式碼 私人→公開；資料湖 公開→私人**。兩邊互不覆蓋：同步時不碰公開 repo 的 `data/`（與 `docs/fixtures/`），備份時不碰私人 repo 的程式碼。

## 2. 允許清單與排除清單（實作在 `scripts/build_public_tree.py`，這裡是白話版）

**放進公開 repo**

| 項目 | 處理 |
|---|---|
| `pipeline/`（含 `groups/*.yaml`、`calendar/*.yaml`） | 原樣；YAML 只拿掉「整行註解」，且保證載入結果完全相同 |
| `site/`（JS／CSS／HTML） | 走 `scripts/minify_site.py`（跟 pages.yml 部署前同一套，esbuild）：註解全清、壓縮；`vendor/` 不動；`manifest.webmanifest` 的 `_註解_` 欄位拿掉 |
| `workers/`（Cloudflare Worker） | `.js`／`.mjs` 只去註解（不壓縮，格式保留）；`.ts`、`.toml` 的整行註解拿掉 |
| `tests/` | 原樣（Python 註解不處理）；少數依賴不公開檔案的測試要排除或略過，見 §3 |
| `.github/workflows/`（來源見 §5） | 只拿掉整行註解；**排除**兩支私人專用工作流 |
| `scripts/` 中 9 支：`__init__`、`stamp_assets`、`minify_site`、`preview_inject`、`preview_boot.js`、`probe_sources`、`live_rotation_probe`、`eval_news_tech_filter`、`_make_perf_fixture` | 原樣；都是工作流或 pytest 會用到的 |
| `docs/fixtures/`（10 個探測樣本） | 原樣；pytest 與 `probe.yml` 會用 |
| 根目錄 `requirements.txt`、`.gitattributes`、`.gitignore`（拿掉註解行） | |
| `README.md` | **腳本重新產生**的極簡版，不提任何內部資訊 |

**不放進公開 repo**

`CLAUDE.md`、`AGENTS.md`、`DECISIONS.md`、`HANDOFF.md`、`ROADMAP.md`、`SETUP.md`、`PUSH-README.md`、`README.md` 原檔、`docs/`（除 `docs/fixtures/`）、`obsidian/`、`.claude/`（九個專家 Agent 的設定）、`tools/`（筆電說明與腳本）、本機安裝腳本（`*.bat`、`push`、`setup.ps1`）、`scripts/` 其餘 18 支開發工具（`_uitest`、`_preview`、`_show`、`gen_*`、`_perf*`、`gh_push`、`deploy_wait`…）、任何 `*.md`、`site/data/`、`*.map`、`__pycache__`。

`data/` 不在「公開版目錄」裡：資料湖的權威在公開 repo，同步時一律不碰。

## 3. `build_public_tree.py` 實跑結果（2026-10-07，用目前這個 repo）

- 來源：git 追蹤的檔案 2,831 個。
- **公開版 259 個檔**（+ 腳本產生的 README.md）：site 96、tests 62、pipeline 49、workers 20、工作流 10、docs/fixtures 10、scripts 9、根目錄設定 3。
- **排除 2,572 個**：`data/` 1,956（資料湖，本來就不歸同步管）、`docs/` 398、各種 `.md` 163、`obsidian/` 23、scripts 開發工具 17、根目錄其他（說明文件、`.bat`）7、`tools/` 7、依賴不公開檔案的測試 1。
- 去註解：18 個 yml／yaml／toml／.gitignore 檔拿掉 1,042 行整行註解；workers JS 15 檔；site 77 檔由 esbuild 壓縮（6,350 KB → 3,006 KB）。
- **掃描結果：硬性關卡有 3 項命中，所以現在同步會被擋**（這正是關卡該做的事）。三處都是**註解／docstring 裡寫了「Andy 原話」**，要在私人 repo 搬家前改掉（只改註解文字，不影響執行）：
  1. `pipeline/compute/flow.py:365`　`# Andy 的原話：「需要有趨勢…」` → 改成 `# 需求原文：「…」`
  2. `scripts/stamp_assets.py:13`　`Andy 的原話是「這連結我沒看到最新資訊」` → 改成 `使用者回報是「…」`
  3. `tests/test_batch3_backend.py:3`　`Andy 2026-09-18 原話：` → 改成 `2026-09-18 需求：`
  （我本來要改，但這個 session 的權限機制擋下了對既有程式檔的改動，所以只列在這裡，由 CEO 處理；我沒有繞過。）
- **site 去註解後，「Andy」字樣剩 0 個**（minify 之後所有註解都清掉了，畫面字串裡也沒有）。
- **Python 註解還剩多少「Andy／原話」**（Python 的註解與 docstring 依指示先不處理，這是會留在公開 repo 的量）：

  | 位置 | 「Andy」次數 | 「原話」次數 |
  |---|---|---|
  | pipeline/（32 檔，含 groups/*.yaml 的 note 欄位） | 126 | 6 |
  | tests/ | 57 | 1 |
  | scripts/（只有公開版那 9 支） | 13 | 1 |
  | workers/ | 3 | 0 |
  | 合計 | **199 次／73 檔** | **8 次／7 檔**（其中 3 次就是上面要改的詞組） |

  另有內文提及：`DECISIONS` 104 次／51 檔、`docs/` 71 次／37 檔、`CLAUDE.md` 18 次／12 檔、`HANDOFF` 0。這些是只警告不擋；要擋就在同步工作流的建置步驟加 `--strict-mentions`。
- 測試：公開版目錄實際跑過 pytest（`SKIP_*` 都沒設）。結果與處理見 §3.1。

### 3.1 pytest 在公開版目錄的結果

在公開版目錄（已壓縮的 site／workers）跑完整 `pytest tests/ -q`：**1,043 過、13 略過、1 xfail、3 失敗，共 10 分 24 秒**（這個容器連不到期交所，網路型測試走假資料，不影響結果）。3 個失敗全部是「比對 site／workers 原始碼文字」的守門測試——公開版已去註解、壓縮，文字比對必然對不上，**不是程式壞了**：

| 測試 | 為什麼失敗 |
|---|---|
| `tests/test_delivery_guard.py::test_前端真的改吃color_idx` | 讀 `site/app.js` 原始碼找字串，壓縮後變數名與格式都變了 |
| `tests/test_rrg_lite_payload.py::test_rrg_lite_payload_written_by_build_and_read_by_overview` | 同上（找 `load('rrg_lite'`，壓縮後引號變雙引號） |
| `tests/test_probe_sources.py::test_對照組的標頭跟_Worker_逐字元相同` | 用單引號 regex 讀 `workers/quote-proxy/worker.js`；esbuild 去註解時把引號統一成雙引號 |

處理：`build_public_tree.py` 在公開版的 `tests/conftest.py` 尾端自動附加一個 `pytest_collection_modifyitems`，把這 3 條標成略過（理由寫在 skip reason）；它們在**私人 repo 仍會跑**（原始碼的權威在那裡）。附加後重跑這 3 個檔：12 過、3 略過。另外 `tests/test_delivery_log.py` 因為讀 `docs/delivery_log.md` 而整支排除（§10-2）。
其餘 1,043 條（含 `test_pipeline_e2e`、資料口徑、groups YAML 守門）在公開版目錄全過，所以**公開 repo 的 `daily.yml`「跑指標庫測試」那一步不會因為拆分而變紅**。

## 4. 同步工作流設計

### 4.1 `sync-to-public.yml`（私人 repo）

| 項目 | 設計 |
|---|---|
| 觸發 | push 到 `main` 或 `preview/**`；`paths-ignore` 掉 `docs/**`、`obsidian/**`、`*.md`、`.claude/**`、`tools/**`、`data/**`（只改文件的 commit 不觸發）；`delete`（刪 `preview/*` 分支）；手動 |
| 流程 | ① 稀疏檢出私人 repo（不下載 data/）② `npm i -g esbuild@0.28.2` ③ `build_public_tree.py` 產出公開版目錄並**掃描（失敗就停）** ④ 檢出公開 repo（稀疏，不含 `data/`）⑤ 切到同名分支（`preview/x` 在公開 repo 沒有就從 main 開）⑥ rsync 覆蓋，**排除 `/data/` 與 `/docs/fixtures/`**（fixtures 另外只增不刪）⑦ **對公開 repo 工作目錄二次掃描** ⑧ commit ⑨ push（失敗就 `pull --rebase` 重試 4 次；公開 repo 的資料管線常在 commit，所以會用到） |
| commit 訊息 | 固定 `同步 <私人 repo 的 7 碼 sha>`；**不帶**私人 commit 訊息（可能含內部文字） |
| 推送身分 | `PUBLIC_REPO_TOKEN`（見下）。用 PAT 推才會觸發公開 repo 的 `pages.yml`（GITHUB_TOKEN 推的不會觸發工作流） |
| 併發 | `group: sync-public`、`cancel-in-progress: false`：不取消跑到一半的；排隊中的只留最新一個（其餘開跑前就被取消，不計分鐘） |
| 防誤跑 | job 有 `if: github.repository == 'MiaoZiKe/tw-rotation-private'`；`PRIVATE_ONLY_WORKFLOWS` 讓這支永遠不會被同步進公開 repo。私人 repo 若不叫這個名字，改檔內三處 |
| 預覽分支 | 私人 repo 推 `preview/<名稱>` → 公開 repo 開同名分支 → 公開 repo 的 `pages.yml` 照舊裝進 `preview/<名稱>/`。刪私人分支時，`drop-preview` job 刪公開的同名分支 |

**PAT 權限（比你原本想的多一項）**：fine-grained PAT，只選公開 repo `tw-rotation`，權限 **Contents: Read and write** ＋ **Workflows: Read and write**。少了 Workflows，GitHub 會拒絕任何修改 `.github/workflows/*.yml` 的 push（同步到公開 repo 的檔案裡就有 10 支工作流）。

### 4.2 `pull-data-from-public.yml`（私人 repo）

| 項目 | 設計 |
|---|---|
| 觸發 | 每天 UTC 22:10（台北 06:10）＋手動。GitHub 排程常延遲、偶爾丟輪，沒關係：抓的是最新全量，下一天會補 |
| 流程 | 稀疏檢出私人 repo 的 `data/`、`docs/fixtures/` → 淺層 fetch 公開 repo main（**公開 repo，不需要金鑰**）→ `git checkout FETCH_HEAD -- data docs/fixtures` → 公開端已刪的檔私人端跟著刪 → commit「資料湖備份：日期 ← 公開 repo 7 碼」→ push 回私人 main（用內建 GITHUB_TOKEN，不需要 PAT） |
| 安全 | 一次要刪超過 200 檔就停下來報錯（可能公開端出事，別連備份一起清掉）；push 撞到別人推的 main 就 rebase 重推；備份 commit 不動程式碼，且 `paths-ignore` 了 `data/**`，不會反過來觸發同步 |
| 語意 | 這是**快照備份**：一天一個 commit。公開端每小時的資料變動會合併成一筆。要更細就把 cron 改成每 6 小時（用量跟著加倍） |

### 4.3 模擬驗證

兩支工作流的 git 機制我在本機用假的 repo 模擬過（容器沒有 rsync，用等價的刪除＋複製代替）：公開 repo 稀疏檢出後 **工作目錄沒有 `data/`、同步後 `data/` 追蹤的檔案一個都沒被動**、舊的 `CLAUDE.md` 與已移除的 `pipeline/old.py` 會被刪掉；備份端「公開端已刪的檔私人端跟著刪」的名單計算正確。**真正的 GitHub Actions 還沒跑過**（要等私人 repo 與 Secret 建好），所以第一次要手動 `workflow_dispatch` 看一輪。

## 5. 重要：私人 repo 裡「公開 repo 的工作流」不能放在 `.github/workflows/`

現有 10 支工作流（每日管線、回補、部署、探測…）搬進私人 repo 後，**私人 repo 也會照著 cron 與 push 去跑它們**：每日管線會在私人 repo 重跑一遍（燒額度又沒有金鑰而失敗）、`pages.yml` 會嘗試部署。所以建議：

- 私人 repo 把這 10 支放到 **`public-ci/workflows/`**（GitHub 不會執行這個目錄）；私人的 `.github/workflows/` 只留 `sync-to-public.yml`、`pull-data-from-public.yml`。
- `build_public_tree.py` 已支援：來源有 `public-ci/workflows/` 就用它，並放到公開 repo 的 `.github/workflows/`；沒有就用 `.github/workflows/`（排除兩支私人專用的）。
- 連帶要改 4 支測試（在私人 repo 裡跑 pytest 時它們讀 `.github/workflows/<檔>`）：`tests/test_backfill_market.py`（2 處）、`tests/test_preview_inject.py`、`tests/test_backfill_relay_1005.py`、`tests/test_sources_v3.py`。做法：路徑改成「`public-ci/workflows/` 存在就用它，否則用 `.github/workflows/`」。公開版目錄裡這些測試照舊通過（因為工作流被放回 `.github/workflows/`）。
- 這一步是 CEO 搬家時做（§9）。

## 6. Actions 用量估計（私人 repo 免費額度 2,000 分鐘／月）

- 重的排程（每日管線、回補、部署、Cloudflare）**全部留在公開 repo**（公開 repo 的 Actions 免費），不吃私人額度。這是這個架構成立的前提。
- 私人 repo 只有兩支輕量工作流：
  - **同步**：一次約 40～70 秒，計費進位成 1 分鐘（偶爾 2 分鐘）。上限估法：最近 30 天「碰到會同步的路徑（site／pipeline／scripts／tests／workflows／workers／requirements）」的 commit 共 **950 個**；就算每個 commit 都單獨觸發一次，上限約 950～1,900 分鐘。實際會低很多：多個 commit 同一次 push、排隊中的 run 被合併、只改文件的 commit 不觸發。我的估計是 **400～1,000 分鐘／月**。
  - **資料備份**：一次 2～4 分鐘 × 30 天 ≈ **60～120 分鐘／月**。
- **合計估計 450～1,100 分鐘／月**，極端情況（每個 commit 都單獨推、又很多 2 分鐘的輪次）可能逼近 2,000。
- 保險：(a) 在 Settings → Billing → **Spending limit 維持 $0**（預設值），超過額度時工作流只會失敗、不會多收錢；(b) 若某個月逼近 1,500，把同步改成「部署員手動 `workflow_dispatch` 觸發」（去掉 `push:`），用量降到幾乎為零，代價是「改完要多一個動作」。部署員本來就是每個段落觸發一次部署，剛好對得上。
- 私人 repo 容量：包含 `data/` 約 380 MB，之後每天備份一筆。GitHub 建議單一 repo 小於 5 GB；以目前公開 repo 的成長速度還有很長的空間，每季看一次 repo 大小即可。

## 7. git 歷史：兩個選項（**不做任何改寫歷史或 force push**）

現況：公開 repo 的歷史裡已經有 `CLAUDE.md`、`DECISIONS.md`、`docs/`、`obsidian/`、`.claude/`、含 Andy 原話的 commit 訊息與檔案內容。拆分之後它們**不再出現在新的 commit**，但舊 commit 任何人都看得到、也可能已被 fork 或快取。

### 選項 (i)：保留歷史，只保證「之後」不再出現

- 做法：公開 repo 維持現狀，從下一次同步起只放允許清單的內容。
- 優點：零停機、網址不變（<https://miaozike.github.io/tw-rotation/>）、所有 Secret／Pages／Cloudflare／OAuth 設定不用動、資料湖歷史完整。
- 代價：**舊歷史裡的內部文件與 Andy 原話永遠公開**（GitHub 不提供「只刪某些舊檔」而不改寫歷史的方法）。也就是說，這個選項**不能**達成「別人看不到我怎麼建這個網站」，只能達成「從今天起不再新增」。

### 選項 (ii)：公開 repo 換成全新、無歷史的 repo

有兩種換法：

- **(ii-a) 另開新名字**，例如 `MiaoZiKe/tw-rotation-app`：
  - 網址變成 `https://miaozike.github.io/tw-rotation-app/`；舊網址在舊 repo 還在時仍可用，舊 repo 設為私人／刪除後就失效。
- **(ii-b) 舊 repo 改名、新 repo 沿用 `tw-rotation` 這個名字**：舊 repo 先改名成 `tw-rotation-old` 再設私人（或當作私人備份的一部分）；新建的公開 `tw-rotation` 從零開始。**網址不變**。短暫的空窗（Pages 重新部署前）是 10～30 分鐘。

共通代價（兩種都一樣）：
1. **要把 `data/`（約 380 MB、約 2,000 檔）以一個 commit 搬進新 repo**；新 repo 沒有資料湖的歷史（舊版本的 parquet 只留在舊 repo／私人 repo 裡）。
2. **所有 Secret 要在新 repo 重設**：`FINMIND_TOKEN`、`FRED_API_KEY`、`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`、會員登入用的 Google／帳號 API 相關 Secret（見 `docs/login_setup.md`）…。金鑰值要 Andy 自己從各家後台重新複製（我們看不到也不該看到）。
3. GitHub Pages 要重新啟用（Settings → Pages → Source: GitHub Actions）、`github-pages` 環境要重建。
4. 任何寫死舊網址的東西要改：Cloudflare Worker 的 CORS 允許來源、Google OAuth 的授權網域／重新導向、`docs`、書籤。**(ii-b) 因為網址不變，只剩 Secret 與 Pages 設定要重做**，所以比 (ii-a) 省很多。
5. 第一次的每日管線要在新 repo 手動跑一次確認。
6. 若網站已切到 Cloudflare Pages（`tw-rotation.pages.dev`，DECISIONS #339 的計畫），GitHub Pages 網址的重要性就大幅下降，(ii) 的代價也跟著降低。

### 我的建議

**先選 (i)，在 Cloudflare 正式切換那一天順手做 (ii-b)。**
理由：(i) 現在就能動、零風險、不影響 Andy「只重新整理網頁」；而 (ii) 要一次重設一堆 Secret，最好跟網域／OAuth 的搬家合併成同一次停機。若 Andy 認為「舊歷史裡已經公開的內部文件」是現在就要處理的事，那就直接選 (ii-b)（網址不變，代價最小），並接受半天內重設 Secret。
**不論選哪個，歷史裡已經公開過的東西，都應該當作「已經外流」來看**：把裡面出現過的任何金鑰（如果有）換掉。我已掃過目前追蹤的檔案，沒有金鑰樣式；但**歷史 commit 我沒有逐一掃**，建議 (ii) 動手前先對整段歷史跑 `run_secret_scanning` 或 `git log -p | grep` 一次。

## 8. Andy 要按的步驟（一步一步）

> 全程在電腦上用瀏覽器登入 GitHub（帳號 MiaoZiKe）。**不需要打任何指令。**

### 步驟 1　建立私人 repo
1. 打開 <https://github.com/new>。
2. **Owner** 選 `MiaoZiKe`；**Repository name** 填 `tw-rotation-private`。
3. 選 **Private**（私人，不是 Public）。
4. **不要勾** 「Add a README file」、「Add .gitignore」、「Choose a license」（三個都留空、保持不勾）。
5. 按綠色的 **Create repository**。
6. 跟 Claude 說「建好了」，並告訴它實際的名稱（如果你改了名字）。

### 步驟 2　建立 fine-grained 權杖（讓私人 repo 有權限推到公開 repo）
1. 打開 <https://github.com/settings/personal-access-tokens/new>。
2. **Token name**：`tw-rotation-sync`。
3. **Expiration**：選 `90 days`（到期前 GitHub 會寄信提醒；到期後同步會失敗，重做這一步換新的就好）。
4. **Resource owner**：`MiaoZiKe`。
5. **Repository access**：選 **Only select repositories** → 在下拉選單只勾 **`tw-rotation`**（公開那個，**不是** private 那個）。
6. **Permissions** → 按 **Repository permissions** 展開：
   - **Contents**：改成 **Read and write**
   - **Workflows**：改成 **Read and write**
   - 其餘（Metadata 自動是 Read-only）不用動。
7. 按最下面綠色的 **Generate token**，**立刻複製**出現的那串（只會顯示一次，之後看不到）。
   ⚠ 這串字不要貼進聊天室、不要貼進任何檔案；只貼到下一步的欄位。

### 步驟 3　把權杖存成私人 repo 的 Secret
1. 打開 `https://github.com/MiaoZiKe/tw-rotation-private/settings/secrets/actions`（把名稱換成你實際建的）。
2. 按 **New repository secret**。
3. **Name** 填 `PUBLIC_REPO_TOKEN`（一字不差）；**Secret** 貼上剛複製的那串。
4. 按 **Add secret**。

### 步驟 4　確認私人 repo 的額度保險
1. 打開 <https://github.com/settings/billing/spending_limits>（或 Settings → Billing and plans → Spending limits）。
2. 確認 Actions 的 **Spending limit 是 $0**（預設就是）。這樣萬一額度用完，工作流只是失敗，不會被多收錢。

### 步驟 5　（之後）把私人 repo 加進 Claude 的工作範圍
**等 Andy 建好後 CEO 接手**：CEO 會用 `add_repo` 把 `tw-rotation-private` 加進 session。若 CEO 回報「沒有權限」，Andy 要到 Claude 設定（claude.ai → Settings → Connectors → GitHub）把 GitHub App 的 repo 存取範圍加上 `tw-rotation-private`——CEO 會用當下的錯誤訊息告訴你按哪裡。

### 步驟 6　（CEO 搬完之後）手動試跑一輪
1. 打開 `https://github.com/MiaoZiKe/tw-rotation-private/actions`。
2. 左邊點 **同步到公開 repo** → 右邊 **Run workflow** → **Run workflow**，等約 1 分鐘變綠色勾勾。
3. 再點 **從公開 repo 備份資料湖** → **Run workflow**，等 2～4 分鐘變綠色勾勾。
4. 然後開 <https://github.com/MiaoZiKe/tw-rotation> 看：根目錄應該只剩 `pipeline`、`site`、`workers`、`tests`、`scripts`、`docs/fixtures`、`.github`、`data`、`requirements.txt`、`README.md` 等，**沒有** `CLAUDE.md`、`obsidian`、`docs` 其他內容。
5. 如果任何一步變紅色叉叉，把那一頁的網址貼給 Claude。

## 9. 首次搬家（CEO 做；Andy 步驟 1～3 完成後）

0. 前置：把 §3 列的 3 處註解改掉；合併 `claude/repo-split` 的 `scripts/build_public_tree.py`、`docs/repo_split_plan.md`、兩支工作流到**現有 repo 的 main**之前，先確認 `build_public_tree.py` 不會讓現有公開 repo 的部署變動（它只在新 repo 用）。**注意：現有公開 repo 的 main 不要收這兩支草稿工作流**（它們有 `if: github.repository == …private` 保護，不會執行，但不該出現在公開 repo；`PRIVATE_ONLY_WORKFLOWS` 已排除，同步後會自然被清掉）。
1. 在本機完整 clone 現有 repo 後，**以鏡像方式**推進私人 repo（保留全部歷史與分支，也是備份）：`git push --mirror https://…/tw-rotation-private.git`。這不會改動公開 repo。（若 `--mirror` 帶上 `refs/pull/*` 被拒，改成 `git push private --all` 與 `git push private --tags`。）
2. 在私人 repo 的 main 上做一個 commit：
   - 把 10 支工作流 `git mv` 到 `public-ci/workflows/`，留 `sync-to-public.yml`、`pull-data-from-public.yml` 在 `.github/workflows/`；
   - 改 4 支測試的工作流路徑（§5）；
   - 確認私人 repo 的 Actions 頁沒有任何排程在跑（Settings → Actions → General 可先暫停，再手動放行那兩支）。
3. 手動執行「同步到公開 repo」一次 → 確認公開 repo 變成預期的樣子、`pages.yml` 被觸發且部署成功（`python scripts/deploy_wait.py --branch main`，注意它查的是公開 repo）。
4. 手動執行「從公開 repo 備份資料湖」一次。
5. 更新 CLAUDE.md／AGENTS.md／`.claude/agents/deployer.md`：工作 repo 改為私人、**部署流程改成「推私人 main → 看私人 repo 的『同步到公開 repo』那一輪 → 再看公開 repo 的 `pages.yml`」**；`deploy_wait.py` 要比對的 sha 是**公開 repo 的 commit**（訊息是「同步 <私人 7 碼 sha>」，用它對照）。
6. 之後所有修改只推私人 repo。**不要再直接推公開 repo 的程式碼**（下次同步會被覆蓋）；公開 repo 上只有 Actions 的資料 commit 與同步 commit。
7. 選好歷史選項後（§7）再處理。

## 10. 待 Andy 決定／已知限制

1. **歷史選項 (i) 或 (ii-a)／(ii-b)**（§7，建議 (i) 先上，Cloudflare 切換時做 (ii-b)）。
2. **「交付清單」頁**：它的資料來源 `docs/delivery_log.md` 是 Andy 原話逐字清單，所以預設**不公開**；結果是公開站的「交付清單」頁會是空的（程式碼本來就會顯示提示）。目前**線上網站已經公開著 `delivery.json`**（裡面就是這些原話）。要讓公開站維持有內容，就在 `build_public_tree.py` 把 `INCLUDE_DELIVERY_LOG = True`（等於接受原話公開）；要真的藏起來，這頁就該只在私人預覽看。請 Andy 選。
3. **Python 註解與 docstring 沒有去掉**（依指示）：公開 repo 仍可看到 199 處「Andy」字樣與 DECISIONS／docs 的編號引用（§3）。若之後要處理，做法是「把這些註解整批改寫成不含人名與決策編號的說明」，或寫一個去註解工具（Python 用 `tokenize` 可以安全去掉 `#` 註解與 docstring，風險是 docstring 有時被程式當字串使用）。
4. 公開 repo 的 `pytest` 會在每日管線前跑：§3.1 列了在公開版目錄需要略過的測試（3 條略過、1 支排除），其餘與私人 repo 相同。
5. 私人 repo 的 Claude 工作流程變更（§9 第 5 步）要同步更新 deployer 的說明，否則部署員會去公開 repo 找私人的 sha。
6. 權杖 90 天會到期（§8 步驟 2）；到期前請重做步驟 2～3。可改成 1 年，代價是外流風險窗口變長。

## 11. 回退方法

- **停掉同步**：私人 repo → Actions → 「同步到公開 repo」→ 右上 `…` → **Disable workflow**。公開 repo 立刻回到「自己獨立運作」，什麼都不會壞（程式碼停在最後一次同步的版本，資料管線與部署照舊）。
- **停掉備份**：同樣 Disable 「從公開 repo 備份資料湖」。
- **完全回到單一 repo**：公開 repo 本來就保有所有執行需要的檔案；只要把想要的文件（CLAUDE.md、docs…）從私人 repo 複製回公開 repo 的 main，並把 Claude 的工作 repo 切回公開 repo 即可。沒有任何一步是不可逆的，因為整段過程**不改寫歷史、不 force push、不覆寫 `data/`**。
- **同步搞壞了公開 repo 的檔案**：公開 repo 的每次同步都是一個普通 commit（`同步 <sha>`），`git revert` 那個 commit 就好。
- **備份搞壞了私人 repo 的 data/**：備份也是普通 commit，`git revert`；且公開 repo 才是權威，下一次備份會再抓一次。
