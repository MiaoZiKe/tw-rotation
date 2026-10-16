# 防白嫖「最小有效版本」：部署順序、回滾、擋得住與擋不住（2026-10-16）

對應評估：`docs/security/anti_freeload_1016.md`（在分支 `origin/claude/wonderful-bardeen-kg2wg4`）。Andy 10-16 批准、並決定：**已公開的 4 篇維持原狀**（不改成免費試閱、不刪、不改寫歷史）。
預覽分支：`preview/anti-freeload`（**Worker 尚未部署**；預覽看得到什麼、看不到什麼見最後一節）。

## 做了什麼（一頁版）

| 項目 | 怎麼做 | 檔案 |
|---|---|---|
| ① 新文章全文只在後端 | 全文存 Worker（`article_body`）；公開索引只留標題等欄位＋`src:"api"`；單篇要登入後 `POST /v1/articles/get`。訪客／註冊會員 403、Plus 累計 5 篇**伺服器**計（`article_reads`，重讀不重複計）、第 6 篇 402、Pro／管理者不限 | `workers/account-api/articles.js`、`site/articles.js` |
| ② 今日事件訪客 5 次 | Worker 簽發訪客編號（存 localStorage 的 `tw.gid`、用標頭 `X-Tw-Guest` 送，不用 Cookie）＋IP 單向雜湊（每週換鹽、8 天刪）雙鍵；`/v1/total/use`、`/v1/total/state` | `articles.js`、`site/quota.js`、`site/app.js` |
| ③ fail-closed | `art.read.n`、`events.total` 連不到會員伺服器／權限沒載入／`quota.js` 沒載入 → 照訪客算（5 次／0 篇），不再全開；其他全站功能的「寧可多給」不動 | `site/quota.js`、`site/articles.js`、`site/app.js` |
| ④ 隱私權政策 | 補「訪客使用次數」「精選文章閱讀紀錄」兩列、補一段說明、Cookie 與本機儲存補 `tw.gid`；「不使用 Cookie 進行追蹤」維持（訪客編號放 localStorage，與實作一致） | `site/legal.js` |
| ⑤ 發佈流程 | `scripts/article_publish.py`：全文傳 Worker → 確認 → 才寫「僅標題」索引；公開檔洩漏檢查＋pytest | `scripts/article_publish.py`、`docs/articles/production_guide.md` |
| ⑥ 最小權限鑰匙 | 新增選用 Secret `ARTICLE_PUT_KEY`：只能上傳／刪除／列出全文，Claude 雲端環境用它（不放整庫匯出的 `BACKUP_TOKEN`） | `articles.js`、`deploy-account-worker.yml` |

## 部署順序（**Worker 先、前端後**；中間任何一步都不會壞版）

1. **Worker 先部署**（推 main 會自動部署；`deploy-account-worker.yml` 會先跑 `anti_freeload.test.mjs`，紅了不准部署）。
   此時線上前端還是舊的：舊前端不認識 `src:"api"`、不會呼叫新路由，所以**什麼都沒變**。新路由只是多了，沒有人用。
   確認：開 `<Worker 網址>/health` 回 `{"ok":true…}`；管理區照常登入。
2. **前端跟著推 main**（同一次合併，Pages 部署）。因為 Worker 先到（同一個 push 兩條工作流各自跑，Pages 通常比 Worker 快——**若不放心，先只推 `workers/` 的變更、確認 ✅ 再推 `site/`**）：
   - 前端新版＋Worker 舊版（萬一 Worker 部署失敗）：今日事件訪客呼叫 `/v1/total/use` 回 404 → **fail-closed＝訪客一律看到「已用完」提示卡**（註冊會員不受影響）。這是這次改動刻意的代價（評估 4-2：「會員 Worker 掛了 → 今日事件訪客一律看不到」）。所以**順序不能反**。
3. **一次性設定**（Andy，約 5 分鐘，見 `docs/articles/production_guide.md`「一次性設定」）：
   `ARTICLE_PUT_KEY`（repo Secret ＋ Claude 環境變數）、`ACCOUNT_API_URL`（Claude 環境變數）、Worker 網域加進 Claude 環境的 Allowed domains；再手動跑一次「部署 Worker」。
   **沒做這步之前，新文章無法上架**（舊 4 篇不受影響；已經有的文章照常讀）。
4. 上架第一篇新文章（`scripts/article_publish.py`），用 Plus 與訪客各看一次，確認：訪客只有標題、Plus 能讀、Plus 第 6 篇鎖。

## 回滾

| 想回到 | 做法 | 副作用 |
|---|---|---|
| 只退前端（Worker 保留） | `git revert` 前端那個 commit → 推 main | 新文章（`src:"api"`）舊前端只會顯示標題、點進去「暫時讀不到」（不會壞版、不會洩漏）；今日事件回到本機計數 |
| 退 Worker | `git revert` `workers/account-api/` 變更 → 推 main（自動部署） | 新路由消失；**`article_body`（新文章全文）資料表不會被刪**（程式不再讀它，資料仍在 Durable Object，備份也在）。前端若同時沒退，訪客今日事件會全擋（見上，順序不能反） |
| 緊急關掉訪客今日事件的擋 | 管理區範本把訪客的 `events.total` 設成不限（999）→ 伺服器與前端都當不限 | 不用改程式、即時生效 |
| 緊急讓 Plus 暫時多讀 | 管理區範本把 Plus 的 `art.read.n` 調高 | 同上 |
| 全部新文章下架 | 把索引裡 `src:"api"` 的項目拿掉並推 main；Worker 裡的全文可用機器路由 `del_body` 刪 | 全文在 Worker 與每日備份，不在 repo——**刪之前先確認備份有**（`article_body` 在匯出清單） |

**新文章全文的備份**：因為不在 repo，唯一副本是 Worker 資料庫與筆電每日備份（`tools/laptop/README.md`）。請確認筆電備份有跑（`BACKUP_TOKEN` 已設），否則 Durable Object 出事就沒有第二份。

## 擋得住什麼／仍擋不住什麼（照實講）

| 繞過方式 | 結果 |
|---|---|
| 直接打新文章的網址／在 repo 找新文章全文 | ✅ 擋住：全文不在靜態檔、不在 repo；沒權杖 401、註冊會員 403 |
| Plus 清除網站資料／換瀏覽器／換裝置／改 localStorage 想多讀 | ✅ 擋住：篇數記在伺服器（以帳號計），本機快取只是顯示用 |
| 擋掉會員伺服器網址、擋掉 `quota.js`（開發者工具「封鎖要求網址」） | ✅ 文章：沒有後端就沒有全文；今日事件：畫面閘改 fail-closed（訪客看到「已用完」卡）。⚠ 但今日事件的**資料檔本身是公開的**（見下） |
| 訪客清除網站資料／開無痕（同一個網路） | ⚠ **部分擋住**：前 3 個新編號各有 5 次，同一個 IP 這週出現第 4 個編號起吃總量（5×4＝20 次）、第 5 個編號起第一次就被擋。換句話說，**同一個網路一週最多約 20 次**，不是 5 次 |
| 換網路（Wi-Fi ↔ 4G）或 VPN 後再開無痕 | ❌ 擋不住：每換一個 IP 就多一份。不做瀏覽器指紋（個資風險高、與「不追蹤」衝突）。對策是讓「免費註冊」比一直換網路更省事 |
| **今日事件的資料檔**（`site/data/news.json`、`broker_views.json`）與 public repo 的 `data/news/*.parquet` | ❌ 擋不住：那是公開檔，直接開網址或讀 parquet 就拿得到。要擋得等 data-gw 上線並把這兩個檔搬走（評估 2-B，需要 Andy 的 ★ 步驟；原始新聞進 public repo 要不要搬走是另一個決定） |
| 已公開的 4 篇文章 | ❌ 維持原狀：全文就在 repo 歷史裡。畫面分級（本機計數）仍在，但只擋一般人 |
| 封鎖 `account_config.js`（讓前端以為會員系統沒開） | ⚠ 今日事件的畫面閘會被當成「系統未開」而放行（前端分不出「沒設定」與「被擋掉」）；**文章不受影響**（全文在後端）。同上，今日事件資料本來就是公開檔 |
| 付費會員分享帳號、截圖轉貼 | ❌ 擋不住（評估階段 3：浮水印、同時裝置數；開始收費後再做） |
| 共用 IP（公司、學校） | ⚠ 前 3 個訪客編號不受 IP 總量影響；之後的人若被擋，提示是「這個網路的訪客預覽次數已用完」＋「免費註冊」，註冊會員不受此限 |

## 預覽（preview/anti-freeload）看得到什麼、看不到什麼

- **預覽版的資料與 Worker 是正式站的**；這次的 Worker 新路由**還沒部署**，所以預覽上**看不到新文章的後端流程**（索引裡也沒有 `src:"api"` 的文章，沒有東西可看）。
- 預覽版一律是擁有者全開；加 `?demo_tier=guest|free|plus|pro` 才看得到限制，而且**示範身分是純本機計數**（預覽版不碰伺服器、不寫正式資料）：
  今日事件第 6 次（`?demo_tier=guest`）、舊 4 篇的 Plus 5／6 篇分級都看得到。
- 新路徑（全文向後端取、伺服器計數、fail-closed、IP 雜湊）的驗證在**本機真的 Worker**（`_uitest --sections 防白嫖後端1016`＋ `node --test workers/account-api/tests/anti_freeload.test.mjs`），截圖附在回報。
