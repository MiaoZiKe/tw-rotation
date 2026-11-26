# 影片渲染流程與容器資源管理（ai-mp4）

> 歸檔：2026-11-26（SYSTEM_PLAYBOOK 缺口 #3、#10、#13）。
> 規則來源：tw-rotation `CLAUDE.md` 2026-11-25 那條（Andy：「以後類似渲染這類型的工作一律都使用這種方式進行，能大幅減少 Claude Loading 和 Token」）；
> 工作流程原文在 ai-mp4 **main** 的 `.github/workflows/render-chunks.yml`；腳本 `scripts/three/push-render-assets.sh`、`render-ranges.mjs`、`chunk-render.sh`、`make-tech.sh`、`render-guard.sh`（後面幾支在分支 `claude/nifty-goodall-syke8a-1548` 的 `scripts/three/`，main 只有前兩支）。
> 本檔是摘要；實際行為以上述原文為準。

## 一、鐵律（CLAUDE.md 11-25）
1. 影片渲染、大量抽格、批次產圖、長時間重算，一律寫成 GitHub Actions 工作流程（matrix 分段、多台同時跑）；Claude 只負責觸發、驗收、傳成品，不在雲端容器裡跑。
2. 素材（音檔、貼圖、成品）推到存檔分支，不留在容器。
3. 流程還沒架好的類型，先架流程再跑；架好前才准在容器跑，並在回報講明。
4. 新流程第一次用要跟容器成品比對（片長、逐格抽圖）一致才正式啟用。
事故：11-25 系列 2 三支在 4 核容器依序渲染，一支 20～50 分鐘，CEO 還要反覆盯進度。

## 二、`render-chunks.yml` 使用說明
**觸發**：GitHub Actions `workflow_dispatch`（對 ai-mp4）。輸入：

| 輸入 | 預設 | 意義 |
|---|---|---|
| `slug`（必填） | — | 片名，例如 `tech-mask2` |
| `ver` | `v1` | 版本名，例如 `v4` |
| `asset_branch` | `renders/series2` | 素材分支；其 `assets/<slug>/meta.json` 必須存在 |
| `chunk` | `40` | 每小段幾幀（交錯分給各台） |
| `jobs` | `16` | 幾台同時渲（上限 16；帳號同時上限 20 個 job，留 4 個給 tw-rotation 的部署與發文） |
| `conc` | `2` | 每台 Chrome 平行數（`THREE_CONCURRENCY`） |
| `audio` | `cloud` | `cloud`＝雲端各段帶 PCM 音軌，再照 `make-tech.sh` 4a～4c 混片尾音；`asset`＝直接用素材分支的成品音軌 `track` |
| `src_ref` | 空白 | 程式碼 commit／分支；空白＝用素材 `meta.json` 記的 commit |

**分段方式**：總幀數依 `chunk` 切段，第 k 台渲第 k、k+jobs、k+2·jobs… 段（交錯，重場景平均分散、各台差不多同時完工）；最後 concat＋配音軌。每台逾時 40 分鐘，`concurrency` 同一 slug 不重疊。不送 TTS、不用任何金鑰（只用內建 `GITHUB_TOKEN`）。

**素材上傳（渲染前，容器內做）**：`bash scripts/three/push-render-assets.sh <slug> <ver>`，推到素材分支 `assets/<slug>/`：`audio/`（`public/audio/<slug>/` 整個資料夾）、`video/`（`videos/<slug>/` 的 json 快照，timeline／storyboard 以快照為準）、`tex/`（model.json 用到的貼圖）、`meta.json`（ver、程式碼 commit、總幀數）、選用 `track.wav`／`track.m4a`。限制：`src/`、`scripts/` 不能有未 commit 改動、HEAD 必須已推到遠端。

**取成品**：artifact「`<slug>.<ver>`」在這個環境下載被代理擋掉，改從素材分支取 `renders/<slug>.<ver>.mp4`（log 會印片長與 MB，並對照素材 meta 的 `localDuration`）。取回後逐格抽圖、量片長，比對無誤才傳 Andy。

**已知坑（ch2_20261125.md）**
- `push-render-assets.sh` 遇本機 `origin/renders/series2` 參照過舊會靜默失敗：先 `git fetch origin +renders/series2:refs/remotes/origin/renders/series2`。
- 新片 Hud 卡要在 `Hud.tsx` 掛 import＋`startsWith` 分派。
- 配音後一定重跑 `genscript.py`＋validate（時間軸改變會出現關節鏈穿模）。
- 容器 11-25 重開機過兩次，背景鏈會死；停渲染要 `pkill -f "render.mjs <slug>"` 並 `pgrep -fa` 確認，否則卡 `out/.render.lock`。
- 渲染前缺貼圖檢查（`make-tech.sh`）還沒套（patch 沒推）；照 lessons #83 描述重寫。

## 三、科技片整體順序（②，ch2_20261125.md 11-26 06:00 段）
semi-chain-analyst 寫 `physics-spec.md` → video-editor 建模 → mechanical-engineer＋審片人雙審（≥9，最多 2 輪）→ `tts-pitch-take.sh` 配音 → `make-tech.sh --dry`＋`genscript` 重跑 → `push-render-assets.sh` → `render-chunks.yml`（16 台）→ tc-channel-lead 寫文案（status draft，Andy 核准才 approved）。規範全文摘要見 `tc/video_rules.md`。

## 四、容器硬碟與成片存放約定（缺口 #10）
- **成片不進 git**：ai-mp4 `out/`、`out/preview/`、`out/queue-backup/` 都不 commit；要長期保存的成片與原始配音推到 `renders/series2` 分支的 `renders/`（11-25 起）。容器回收或重開機，`out/` 會消失。
- 容器硬碟很緊（11-24 一度 0 MB）：
  - **可刪**：ai-mp4 `out/<slug>/` 的中間檔、`out/.bundle/<pid>/` 殘檔（確認該 pid 不在後）。
  - **不可刪**：已發布或待發的 `out/*.mp4`、`/root/.cache/huggingface`（模型快取，重抓很慢）。
  - 跑 still／peek／render 前先 `df -h /`，可用不到 1 GB 就先清舊中間檔（ai-mp4 CLAUDE.md）。
- tw-rotation 這邊：推 main 前確認樹檔數 >20000（11-22 曾因磁碟滿推出空樹 commit）；工作在 scratchpad 的 worktree 做；不要本機 fetch 大包。
- 渲染前清孤兒 Chrome（`scripts/three/render-guard.sh`，在 `make-tech.sh` 的 flock 內跑），耗時紀錄在 `out/render-times.tsv`，超過 60 分鐘自動警告。

## 五、ai-mp4 repo 地圖（缺口 #13 部分盤點，2026-11-26 `git ls-remote`）
- **main**：白話國際（國際白話講）頻道規範 `CLAUDE.md`（1080×1920、30fps、深藍底、元件庫、script.json 結構、`npm run still|render|studio|fonts`、TTS 看 `TTS_PROVIDER`）、`.github/workflows/render-chunks.yml`、`scripts/{fetch-fonts,lib,render,still,tts}.mjs`、`scripts/three/{push-render-assets.sh,render-ranges.mjs}`、`src/`、`videos/`。
- **claude/nifty-goodall-syke8a-1548**：② 科技透明圈與 ①哩股、④談晴說礙的 docs（`docs/channels/tech-*.md`、`liguligu*.md`、`tanqing-*.md`、`docs/layout-rules.md`、`docs/prompts/*.txt`）、完整 `scripts/three/`、`CLAUDE.md`（v2／v3 規範、停工線 07:00 與科技頻道例外、打包暫存 `out/.bundle`）。
- **claude/caffaine-ai**：③ CaffAIne 全套（`ai-daily-playbook.md`、`caffaine-*.md`，見 `caffaine/ai_daily_playbook_index.md`）。
- **renders/series2**：渲染素材與成品存檔（`assets/<slug>/`、`renders/<slug>.<ver>.mp4`）。
- 其他分支（`claude/admiring-bohr-l2z4sn`、`adoring-cori-hbpviw`、`brave-edison-7ii7os`、`gracious-cori-8tey0b`、`magical-clarke-xg52zp`、`nifty-goodall-syke8a`、`optimistic-tesla-hoasns`、`vibrant-dirac-v401gi`、`youthful-johnson-b40525`、`review/tanqing-talk-ep01`）**本次未逐一盤點內容**，不確定是否另有只存在該分支的規範；見 SYSTEM_PLAYBOOK 缺口 13 狀態。
