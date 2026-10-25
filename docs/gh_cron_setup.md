# 準時派工（Cloudflare Worker `tw-gh-cron`）設定步驟

**為什麼要做**：GitHub Actions 的 `schedule` 不準（10/20～10/23 每日管線台北 15:37／18:37 兩輪完全沒觸發；盤中貼文被延後約 5 小時，跑時已收盤）。
改成 Cloudflare 的排程每分鐘醒一次，在準確的台北時間呼叫 GitHub 去啟動 workflow。GitHub 原本的排程保留當備援。

**你只需要做兩件事**（約 5 分鐘）：① 建立一把 GitHub 金鑰　② 把金鑰貼進 repo 的 Secret。
其他（部署、寫進 Cloudflare）都是自動的。Cloudflare 的 `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID` 已經設好，**不用再動**。

> 擋不擋其他工作：**不擋**。沒做這兩件事，網站與其他功能照常；只是準時派工還沒啟動，資料與盤中貼文仍靠 GitHub 原本不準的排程。

---

## 步驟 1：建立 GitHub 金鑰

打開連結：<https://github.com/settings/personal-access-tokens/new>（用 MiaoZiKe 帳號登入；若跳出密碼確認就輸入密碼）。

| 欄位（畫面上的英文） | 填什麼 |
|---|---|
| **Token name**（金鑰名稱） | `tw-gh-cron` |
| **Expiration**（到期日） | 選 **Custom**（自訂）→ 日期選一年後（例如 2027-10-25）。到期前一個月要回來重做（見最下面「到期提醒」） |
| **Description**（說明） | 不用填（想填可寫 `Cloudflare Worker 準時啟動 workflow`） |
| **Resource owner**（擁有者） | 保持 **MiaoZiKe**，不用動 |
| **Repository access**（可存取的 repo） | 選 **Only select repositories**（只限選定的 repo）→ 下拉選單選 **MiaoZiKe/tw-rotation**。**不要**選 All repositories |
| **Permissions**（權限） | 按 **Add permissions**（新增權限）展開 → 在 **Repository permissions**（repo 權限）裡找 **Actions** → 右邊改成 **Read and write**（讀寫）。**其他全部不要勾**（畫面會自動帶上 Metadata: Read-only，那是必備的，不用動它） |
| 其他區塊（Account permissions 等） | 全部不用動 |

按頁面最下面綠色按鈕 **Generate token**（產生金鑰）。→ 彈出確認框再按一次 **Generate token**。

畫面會顯示一串以 `github_pat_` 開頭的長字串，**只會顯示這一次**。按右邊的複製圖示複製起來，先**不要關掉這個分頁**，直接做步驟 2。

⚠ **不要把這串金鑰貼到聊天室、截圖、或任何檔案裡。**（repo 是公開的，貼出去等於送人。）

## 步驟 2：把金鑰加到 repo Secret

打開連結：<https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new>

| 欄位 | 填什麼 |
|---|---|
| **Name**（名稱） | `GH_DISPATCH_TOKEN`（全大寫，一個字都不能錯；底線是下底線） |
| **Secret**（內容） | 貼上步驟 1 複製的那串 `github_pat_...`（前後不要多空格或換行） |

按綠色按鈕 **Add secret**（新增）。完成後頁面會回到 Secrets 清單，看得到 `GH_DISPATCH_TOKEN`。

這時可以關掉步驟 1 的分頁了。

## 步驟 3：讓它部署（通常自動；沒自動就手動按一下）

程式推上 main 後，會自動部署 Worker 並把金鑰寫進 Cloudflare。**如果你是在程式已經上線之後才做步驟 2**，需要手動觸發一次部署：

1. 打開 <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/deploy-gh-cron.yml>
2. 右上角按 **Run workflow**（執行）→ **Branch: main** 不用動 → 再按綠色的 **Run workflow**。
3. 等約 1 分鐘，重新整理，最新一列出現綠色勾勾就成功。點進去看 **Summary**（摘要）：寫「gh-cron 已部署，GH_DISPATCH_TOKEN 已寫入 Worker」＝完成；寫「⚠ GH_DISPATCH_TOKEN 還沒設」＝步驟 2 的名稱或內容有誤，回頭檢查。

## 做完回 CEO 什麼

只回一句：**「金鑰和 Secret 都設好了」**。（不要貼金鑰。）
CEO 會接著確認：Worker 部署成功、第一次準時派出的 workflow 有出現在 <https://github.com/MiaoZiKe/tw-rotation/actions>（執行來源標示為 workflow_dispatch，時間準點）。

---

## 派工時間表（全部台北時間；只在台股交易日，週一到週五且非休市日）

| 時間 | 派什麼 | 備註 |
|---|---|---|
| 05:07（週二到週六） | 每日管線 `phase=news` | 新聞、國際盤、總經；不看休市日 |
| 08:20 | 社群貼文 `kind=premarket`（盤前） | **預留、預設關閉**，另一位同事的盤前功能合併後，把 `workers/gh-cron/wrangler.toml` 的 `ENABLE_PREMARKET` 改成 `"1"` |
| 09:33、11:03、13:03 | 社群貼文 `kind=intraday`（盤中）`dry_run=false` | 真的發不發，仍由 repo 的總開關檔決定 |
| 15:38 | 每日管線 `phase=price` | 價量 |
| 16:16、16:46、17:16 | 每日管線 `phase=inst` | 搶當天三大法人；沒資料約 1 分鐘收工 |
| 18:38、21:38 | 每日管線 `phase=full` | 完整一輪 |

休市日清單來自 `pipeline/calendar/tw_holidays.yaml`（2026 年；已含 10/26 光復節補假）。2027 年證交所公告後，更新該 YAML 並跑 `python scripts/gen_gh_cron_holidays.py`，兩個檔一起 commit（測試會檢查兩邊同步）。

## 颱風假等臨時休市：Worker 不猜

Worker 只認「週一到週五＋已知休市表」。颱風假這類臨時休市（例如 10/23 颱風全日休市）休市表事先不會有，Worker 會照常派工，**多派一次無害**：

| 誰 | 臨時休市日怎麼處理 |
|---|---|
| 每日管線（daily.yml） | 重跑以主鍵 append 去重，不會多出資料列 |
| 社群貼文（social-live） | 程式用資料自己判斷（即時報價的成交日不是今天、法人資料日不是今天、不在盤中時段）→ 不發，結束碼 10 正常收工 |

所以不需要為颱風假去改休市表；只有「事先公告的休市日」才加進 YAML。

## 備援與防重複

- GitHub 原本的排程**全部保留**當備援。每日管線重跑安全（資料寫入以主鍵去重）。
- 盤中貼文的防重複紀錄把盤中分成 09／11／13 三個時段：Worker 準時發了，GitHub 晚到的備援即使跨整點也算同一時段，**不會重複發**。
- 提醒：每日管線同一時間只會排一個等候，Worker 準點派的與備援撞在一起時，後到的會排隊等前一輪跑完。

## 出問題怎麼看

| 現象 | 去哪看 | 可能原因 |
|---|---|---|
| 到點沒有新的執行 | Cloudflare：從 <https://dash.cloudflare.com/> 進去 → 左邊 **Workers & Pages** → 點 **tw-gh-cron** → **Logs**（記錄） | log 寫「GH_DISPATCH_TOKEN 未設定」＝步驟 2 沒做；寫「HTTP 401／403」＝金鑰過期或權限不是 Actions: Read and write；寫「HTTP 422」＝派的 workflow 輸入選項不存在 |
| 部署 workflow 變紅 | <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/deploy-gh-cron.yml> | 點進去看紅色那一步 |

## 到期提醒

金鑰一年後到期（GitHub 到期前會寄信）。到期前重做步驟 1，到 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions> 找到 `GH_DISPATCH_TOKEN` 右邊的鉛筆圖示（**Update**，更新）貼上新金鑰，再做步驟 3 的手動部署。
