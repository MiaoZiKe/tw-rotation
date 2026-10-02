# 確認帳本（監察委員維護；CEO 每次回報都要附「待 Andy 確認」最新一版）

最後更新：2026-10-03 04:25（台北）｜監察委員第 2 次稽核（CEO 04:17 回報）
查證依據：`git log origin/main`（頂端 17b6d13）、`git ls-remote`（preview/layout-v2＝175a5a2、preview/ov-all-live＝c205742、claude/ov-all-live＝c205742）、
GitHub Actions `pages.yml` run 252（37059203358，deploy-pages「Created deployment for faae730 → Reported success!」，**部署產物同時含 `preview/layout-v2/` 與 `preview/ov-all-live/`**，監察委員從 job 日誌親自讀到）／251／250／249／248 全 success。
⚠ 這個容器打不開正式站，「上線」都是用 Actions 推算的；肉眼確認一律在下表等 Andy。
⚠ 稽核紀錄：CEO 04:17 那則回報**沒有先派監察委員**就送出（違反 CLAUDE.md 2026-10-03 第 2 條），這是事後補稽核。

## 待 Andy 確認

| # | 項目 | 要看什麼 | 去哪看 | 等待起點 |
|---|---|---|---|---|
| 1 | 版面 V2 上正式站（電腦版 >820） | 側欄導覽、頁面排法與預覽一致；手機版不變 | https://miaozike.github.io/tw-rotation/ （04:56 推 main） | 10-03 04:56 |

> 10-03 04:50 Andy：「待你確認 OK 有問題跟你說」→ 先前第 1～23 項全部視為已確認，移到下方「已確認」。

## CEO 待辦（逾 60 分鐘無動靜即判卡住）

| 項目（需求） | 分支／位置 | 實際狀態（04:20 查） | 缺什麼 |
|---|---|---|---|
| 回報前先派監察委員 | 流程 | **04:17 回報違規**（沒先派） | 下一則回報起一律先派，回報最後附本表「待 Andy 確認」 |
| 回報漏列台指期 15 秒 | 待 Andy 確認第 22 項 | 已上線但 04:17 回報沒提 | 下一則回報補講 |
| `_uitest`「個股」#drawBar 不可見的偶發紅 | `scripts/_uitest.py` 個股段 | 根因未明（CEO 自承） | 追根因或加等待；不追就是下次再假紅、再重跑浪費時間 |
| 修「總覽摘要卡即時」驗收依賴本機資料日期的 2 條假紅 | `scripts/_uitest.py` | **未開始**（上一輪就列了） | 指派人做 |
| HANDOFF 過時段落 | HANDOFF.md「台指期 15 秒」「市場明細兩欄」兩節 | 仍寫「未推 main」，實際 318dd32、c6bb484 已合併、run 251 部署 | 改成已上線並寫 run 251 |
| 總覽每張卡即時開關（7） | claude/ov-all-live c205742，已推遠端＋preview | **完成到預覽**，刻意不上 main | 等 Andy 第 19、23 項 |
| 版面 V2 電腦版（13） | origin/claude/layout-v2-desktop＝preview/layout-v2（175a5a2） | **完成到預覽** | 等 Andy 第 13 項；未合併 main |
| 大戶散戶 3 個月（1） | — | 卡在付費決定 | 等 Andy 第 15 項 |
| 停擺的髒 worktree | taifex-deno、stock-tick-live、stock-layout（未 commit 改動）、agent-abe017（`_perf_jank.py` 02:31 起沒動，未 commit）、design-v4-2b／mobile-onescreen-fix（暫存區有 backfill.yml 改動） | 停擺 | 逐一確認已被 main 取代再清；`_perf_jank.py` 那份要決定保留（推 wip）或丟 |
| wip-* 遠端分支（branch-preview、fut-15s、market-2col、ov-all-live、perf-jank、perf-jank2、stock-layout、layout-mobile） | origin | 對應工作多已合併 | 確認後刪，免得下一個人誤接 |

## 已確認

10-03 04:50 Andy 一次確認：夜盤 Deno、個股總覽三欄、卡頓、個股頁五項、大戶散戶、繪圖、小走勢、頂部標籤、分時即時、摘要卡即時、會員權限、Google 登入、版面 V2 預覽、推播法遵、FinMind 方案、子網域、市場明細、#303、總覽即時開關預覽、詢問信、富果永豐、日盤 15 秒、中央推播（以上「有問題他會再說」）。

## 已上線（最近；依 pages.yml 部署推算）

| 項目 | 推 main（台北） | 部署 |
|---|---|---|
| 個股總覽三欄等高、本益比（每季）虧損灰格／極端值 ▲、獲利分頁並排（#303） | 10-03 04:13 | run 252 success（04:15） |
| 市場明細兩欄並排、TPEX→上櫃（#300） | 10-03 03:49 | run 251 success |
| 台指期日盤 5 秒→15 秒（#299） | 10-03 03:43 | 隨 run 251 部署 |
| 分支預覽機制（#301） | 10-03 03:43 | run 250 success |
| 大戶散戶區間鈕只留兩顆（#302） | 10-03 03:18 | run 249 success |
| 全站卡頓五項＋個股總覽三欄／AI 分頁籤／指標左右並排 | 10-03 02:43 | run 248 success（02:56） |
| 營收／獲利／籌碼分頁並排 | 10-02 22:53 | run 247 success |
| 總覽四張摘要卡即時 | 10-02 20:54 | run 246 success |
| 個股分時一路即時 | 10-02 20:14 | run 245 success |
| 個股頁頂部版面 | 10-02 19:09 | run 244 success |
| 台指期改走 Deno | 10-02 19:00 | run 243 success |
| 個股總覽小圖、融資對帳、指標方塊 | 10-02 18:20 | run 242 success |
| K 線繪圖工具 | 10-02 16:28 | 已部署（後續 run 241 success） |
| 迷你走勢精確化 | 10-02 15:42 | 已部署 |
| 會員功能權限開關 | 10-02 15:07 | 已部署；會員 Worker run 5 success |
| 專家模型分配 | 10-02 15:11 | 只改設定，不需部署 |
