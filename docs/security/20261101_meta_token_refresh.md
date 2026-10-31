# Meta（Threads／IG）長效權杖自動續期 —— 設計、比較與風險（2026-11-01）

> Andy 原話：「幫我看看 Buffer 這個網站 好像可以幫忙免費自動發文 不用 60 天後 重新申請權杖一次」。

## 1. 結論

- **不用 Buffer。** 免費方案每頻道只能排 10 則、串文同時只能排 1 則，API 不確定能發 Threads 串文；我們每天 6 篇以上、每篇 6 則串文＋IG 輪播，量不合。
- **Meta 長效權杖本來就能自己續**：權杖「已滿 24 小時、未過期」時呼叫官方 refresh 端點，就再延 60 天。
  - Threads：`GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=…`（官方文件：<https://developers.facebook.com/docs/threads/get-started/long-lived-tokens/>）
  - IG：我們用的是「Instagram 登入版」（`graph.instagram.com`，`scripts/ig_post.py`），權杖是 **IG 使用者長效權杖**（不是 Facebook 粉專權杖），續期是 `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=…`。
- **選擇：方案 A（GitHub 細粒度權杖寫回 Secret）＋「新值寫到另一個名字、舊 Secret 永遠不動」。** 每週日自動續期一次。

## 2. 現況盤點（只看名稱，沒有讀任何值）

| Secret 名稱 | 權杖類型 | 用在哪些工作流 |
|---|---|---|
| `THREADS_ACCESS_TOKEN` | Threads 使用者長效權杖（60 天） | `social-live.yml`、`threads_post.yml`、`social_insights.yml`、`meta_perm_check.yml` |
| `IG_ACCESS_TOKEN` | IG 使用者長效權杖（Instagram 登入，60 天） | `social-live.yml`、`ig_post.yml`、`social_insights.yml`、`meta_perm_check.yml` |
| `THREADS_USER_ID`／`IG_USER_ID` | 帳號編號（不是權杖） | 同上 |

已知事實：`scripts/social_publish.py` 每次發文前本來就會呼叫 refresh（2026-10-26 起），但**它沒辦法把新值寫回 Secrets**；
Meta 文件沒寫死「續期後字串是否不變」（`docs/marketing/social_unit/meta_api_setup.md` 第 6 節已標為不確定）。
所以真正缺的是兩件事：**(1) 字串變了要能存回去；(2) 要有狀態紀錄與到期告警**，不能等到哪天突然發不出去。

## 3. 存放方案比較

| | A. GitHub 細粒度權杖（PAT）寫回 Secret | B. Cloudflare Workers KV | C. 不存，只靠「字串不變」 |
|---|---|---|---|
| 做法 | 續期工作流用一把只限本 repo、只有「Secrets 讀寫」權限的 PAT，`gh secret set` 寫回 | 新權杖寫進 KV；所有發文流程改成先從 KV 讀 | 照現在：每次發文 refresh，字串不變就沒事 |
| 權杖存哪 | 仍在 GitHub Secrets（加密、log 自動遮蔽） | 多一個存放處（KV 預設明文存放，要自己加密） | GitHub Secrets |
| 外洩面 | PAT 外洩＝可改／讀本 repo 的 Secret **清單與寫入**（讀不到 Secret 值，GitHub 不提供讀值 API） | `CLOUDFLARE_API_TOKEN` 目前管 Pages 部署、Worker 部署、網域；**要再加 KV 寫入＝擴大一把已經很大的權杖**；KV 讀取要另一把權杖或 Worker 端點，多一條可被打的路徑 | 無新增 |
| 要 Andy 動手 | 建一次 PAT（約 5 分鐘），之後每年重建一次（到期前 14 天自動提醒） | 改 Cloudflare 權杖權限＋建 KV 命名空間；我無法確認現有權杖有沒有 KV 權限（只能用權杖本身去打 API 才知道，而我看不到權杖值） | 不用 |
| 要改的程式 | 只改續期工作流；發文工作流只改一個運算式 | 5 支發文工作流＋腳本都要改成讀 KV、要處理 KV 失效 | 不用 |
| 字串變了怎麼辦 | 自動寫回 | 自動寫回 | **擋不住**：舊字串到期就全停 |

**選 A。** 理由：權杖留在 GitHub Secrets 這個本來就加密、log 自動遮蔽的地方，不新增存放處；PAT 權限可以切到「只有這個 repo 的 Secrets」；
發文流程幾乎不用改。B 要把一把已經管部署與網域的 Cloudflare 權杖再放大，風險換不到好處。
C 是現況，但只要 Meta 有一次回新字串，就會在不知不覺中走到到期。

**再加一層保險（方案 A 的細節）：新值寫到另一個名字。**
- 續期程式寫回的是 `THREADS_ACCESS_TOKEN_AUTO`／`IG_ACCESS_TOKEN_AUTO`；**Andy 原本設的 `THREADS_ACCESS_TOKEN`／`IG_ACCESS_TOKEN` 永遠不被程式改動**。
- 所有發文工作流改成 `${{ secrets.THREADS_ACCESS_TOKEN_AUTO || secrets.THREADS_ACCESS_TOKEN }}`：**新的沒有就退回舊的**。
- 寫回前會先用新權杖打一次 `/me` 驗證能用，驗不過就不寫（避免把壞值寫進去蓋掉能用的）。

## 4. 實作（檔案）

| 檔案 | 作用 |
|---|---|
| `.github/workflows/meta_token_refresh.yml` | 每週日 02:23 UTC（台北 10:23）跑；手動觸發**預設 dry-run** |
| `scripts/meta_token_refresh.py` | 讀權杖（AUTO 優先）→ refresh → 字串變了就驗證＋寫回 AUTO → 寫狀態檔 → 判斷告警 |
| `data/_state/meta_token.json` | 狀態（只有日期、剩幾天、成功與否、來源是 AUTO 還是原本那把；**沒有權杖**） |
| `pipeline/build_payload.py` | `meta_payload()` 讀狀態檔；告警時算一項「更新失敗」→ 網站資料狀態燈轉紅 |
| `tests/test_meta_token_refresh.py` | mock 測試：成功（字串不變／新字串寫回）、失敗、到期前 10 天告警、PAT 快到期、dry-run、log 與狀態檔不含權杖 |
| 5 支發文工作流 | 權杖改成「AUTO 優先、沒有就退回原本」 |

行為規則：
1. 任一平台續期失敗、或拿到新字串卻寫不回 → **run 紅燈**（GitHub 會對排程失敗寄信給 repo 擁有者）。
2. 續期沒成功，而且權杖**剩 10 天內到期或到期日未知** → 狀態 `bad`：**開 issue「⚠️ Meta 權杖續期需要處理」**（已有就留言，不重複開）＋網站資料狀態燈轉紅。
3. 寫回用的 PAT 失效或剩 14 天內到期 → 同樣告警。
4. dry-run：只打 `/me` 驗證權杖能用，不呼叫 refresh、不寫回、不寫狀態檔。
5. log：每個權杖值都先印 `::add-mask::`，程式輸出一律過遮蔽；錯誤訊息只留狀態碼與 Meta 的錯誤說明，不帶請求網址（網址裡有權杖）。寫回時新值走 stdin，不出現在指令列。

## 5. 風險

| 攻擊情境／失敗情境 | 影響 | 緩解 | 成本 |
|---|---|---|---|
| PAT 外洩（例如被貼進 repo） | 可寫入本 repo 的 Secrets（例如把發文權杖換成別人的），但讀不到既有 Secret 的值 | PAT 只給本 repo、只給 Secrets 讀寫；放在 Secret 裡、不進檔案；push 前掃描；到期 1 年 | 每年重建一次 |
| 有人改 workflow 把權杖印出來 | 權杖外洩 | 只有有寫入權的人能改 main；`::add-mask::` 對直接 echo 有效，但擋不住刻意編碼後輸出 —— 這是 GitHub Secrets 共同限制 | 維持「只有 Andy 與 Claude 能推 main」 |
| Meta 改端點／權杖已過期 | 續期失敗 | run 紅燈；到期前 10 天開 issue＋狀態燈紅；最壞情況照 `meta_api_setup.md` 重新授權 | 一次約 10 分鐘 |
| Meta 回新字串、PAT 沒設 | 舊字串到原到期日就失效 | run 紅燈＋告警（到期日未知時立刻告警） | 建 PAT（第 6 節） |
| 寫回了壞值 | 發文失敗 | 寫回前先 `/me` 驗證；原本那把 Secret 不動，刪掉 AUTO 就退回原本那把 | 低 |
| 狀態檔推不上 main | 告警判斷少一次資料 | 推送重試 5 次；推不上只出警告，不影響續期本身 | 無 |

## 6. Andy 要做的事（**不擋任何東西**，可以先不做）

**什麼時候一定要做：** 只有在 Meta 續期回傳「新字串」時才需要（那時 run 會紅、會開 issue）。
字串不變的話完全不用做。建議還是先做，5 分鐘，做完之後永遠不用管。

### 步驟一：建一把只能改這個 repo Secrets 的權杖

打開 <https://github.com/settings/personal-access-tokens/new>（新增細粒度權杖頁）。

| 欄位 | 填什麼 |
|---|---|
| **Token name**（權杖名稱） | `tw-rotation-meta-secrets` |
| **Description**（說明） | `每週自動續期 Meta 權杖並寫回 Secret` |
| **Resource owner**（擁有者） | `MiaoZiKe`（預設就是，不用動） |
| **Expiration**（到期） | 選 **Custom**（自訂）→ 選一年後的日期（例如 2027-10-31）；畫面最長能選多久就選多久 |
| **Repository access**（可存取的 repo） | 選 **Only select repositories**（只限選定）→ 下拉選 `MiaoZiKe/tw-rotation` |
| **Permissions → Repository permissions**（repo 權限） | 找到 **Secrets** 那一列 → 改成 **Read and write**（讀寫）。**Metadata** 會自動變成 Read-only（唯讀），不用動。**其他全部不用動**（保持 No access） |
| **Account permissions**（帳號權限） | 全部不用動 |

按最下面綠色 **Generate token**（產生權杖）→ 再按一次確認 → 畫面出現一串 `github_pat_` 開頭的字，按旁邊的複製鈕。
**不要貼到聊天室、不要存成檔案**，直接做步驟二。

### 步驟二：把它存成這個 repo 的 Secret

打開 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new>（新增 Actions Secret 頁）。

| 欄位 | 填什麼 |
|---|---|
| **Name**（名稱） | `META_SECRETS_PAT` |
| **Secret**（值） | 貼上步驟一複製的那串 |

按 **Add secret**（新增）。完成後在 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions> 清單裡會看到 `META_SECRETS_PAT`。

**不用動的：** `THREADS_ACCESS_TOKEN`、`IG_ACCESS_TOKEN`、`THREADS_USER_ID`、`IG_USER_ID` 都不要改、不要刪。
`THREADS_ACCESS_TOKEN_AUTO`／`IG_ACCESS_TOKEN_AUTO` **不用自己建**，程式需要時會自己建。

**做完回我：** 「META_SECRETS_PAT 加好了」一句話即可（不要貼權杖內容）。

## 7. 什麼時候會跑、怎麼看結果

- 第一次自動續期：**2026-11-01（日）台北 10:23**，之後每週日同一時間。
- 結果看 <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/meta_token_refresh.yml>：綠＝成功；摘要表格列出每個平台剩幾天。
- 手動「安全試跑」：同一頁按 **Run workflow**，`dry_run` 保持打勾 → 只驗證權杖能用，不續期、不寫回。
- 現有的「12/17 Meta 權杖到期提醒」排程沒動；CEO 之後依續期結果改成「確認續期成功」。
