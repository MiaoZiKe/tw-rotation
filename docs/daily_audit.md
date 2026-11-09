# 每日三關稽核（daily_audit）

Andy 2026-11-09 原話：「CEO 需要安排人員確認每日該做的事情是否有做，以及該更新的數據是否有完成，需要至少 3 個關卡……目的是避免沒有發文以及沒更新數據」。

## 為什麼要有它

2026-11-09 上午：主站（Cloudflare）停在 11-06，盤前消息其實 08:22 已寫好、09:19 備援站也部署了。
`pages.yml` 從 11-07 起沒再跑，沒有任何地方紅燈，是 Andy 自己看出來的。

這支稽核的規則是：**每一項每天都要回答三個問題，三個答案分開記**。

| 關卡 | 問的事 | 怎麼查 |
|---|---|---|
| 一、有沒有執行 | 對應的 workflow 今天有沒有跑、結論是不是 success | GitHub Actions API（`gh api`） |
| 二、內容對不對 | 產出檔的日期是今天／應有的交易日、有內容、沒有 nan、資料日沒退回、來源沒連續壞 | 本機 `site/articles/*.json`、`data/_state/*.json`、資料湖最新日 |
| 三、有沒有發布上去 | 貼文有發布網址；網站 GitHub Pages 與 Cloudflare 主站都包含必須的 commit | `social-snaps` 的 `state/posted.json`、Deployments API、pages.yml 的 Cloudflare 步驟 |

## 狀態（四種不是失敗的狀態要跟失敗分開）

| 狀態 | 意思 | 會不會紅 |
|---|---|---|
| ✅ ok | 三關都過 | 否 |
| ❌ fail | 已過截止時間，任一關不過 | **是** |
| 🔄 pending | 還沒到截止時間 | 否（還沒到，不是失敗） |
| ⏭ skip | 今天不該做（非交易日） | 否 |
| ⏸ disabled | 功能沒開（例如 post_quota 沒開） | 否（未啟用，不是失敗） |

「查不到」（API 失敗、檔案讀不到）**不算綠**，一律當作不過。

## 清單與截止時間（台北）

| 項目 | 哪些日子 | 截止 | 關卡一（執行） | 關卡二（內容） | 關卡三（發布） |
|---|---|---|---|---|---|
| 盤前消息 | 交易日 | 08:40 | social-live 今天有成功執行 | `site/articles/premarket.json` 的 `days[0].date` ＝今天、有則數、沒有空標題／空網址 | 網站兩站包含最新 commit |
| 盤後消息 | 交易日 | 21:40 | daily.yml 今天 15:00 後有成功 | `postmarket.json` 的日期＝今天 | 網站兩站包含最新 commit |
| 每日資料更新 | 每天（看應有日） | 交易日 18:40 | daily.yml 應有日 15:00 後有成功 | 價量／法人／融資券最新日＝應有日；`last_run.json` 沒有錯誤；`source_health` 沒有來源連續失敗 2 天以上 | 網站兩站包含最新 commit |
| 頻道①盤後主貼文 | 交易日（quota 的 close 開著才檢查） | 20:35（2026-11-09 起改 19:30～20:30 發；以前 18:20） | social-live 今天 15:00 後有成功 | social-snaps `state/posted.json` 有 `close-<今天>` | 有發布網址（threads.link 或 story.link） |
| 頻道②科技透明圈 | 每天（只看 approved 且排定時間已過 30 分鐘的稿；draft 不算） | 排定時間＋30 分鐘 | tc_post.yml 今天有成功 | approved 且已到時間的稿，`post.md` 狀態是 posted | main 的 `state/tc/posted.json` 有該稿紀錄（tc_post.yml 直接 commit 到 main） |
| 頻道④談晴說礙 | 每天（只看 `docs/marketing/channels/healing/post_quota.json` 的 `live` 是 true；false＝整個停發，未啟用） | 21:40 | healing_post.yml 今天有成功 | 佇列 `queue/*/meta.json` 是 approved 且 publish_at（null＝當天 20:27 時段）已到 | `healing/state/posted.json` 每個平台都有該資料夾紀錄且未被刪 |
| Meta 權杖 | 每天 | 無（即時） | `meta_token.json` 兩天內有更新 | 各平台 ok 且剩餘 7 天以上 | 不適用 |
| 網站部署 | 每天 | 無（即時） | pages.yml 兩天內有成功 | 資料日同上 | GitHub Pages＋Cloudflare 都包含最新 commit，主站不比備援舊 |

**目前的開關狀態**：頻道①盤後主貼文看 `docs/marketing/social_unit/post_quota.json` 的 `live.close`；頻道②看同一檔的 `tc.enabled`；頻道④看 `docs/marketing/channels/healing/post_quota.json` 的 `live`（頻道④自己的開關，跟頻道①無關）。

## 排程（UTC 寫在 cron，台北時間是 +8）

| 台北 | cron（UTC） | 天 |
|---|---|---|
| 08:45 | `45 0 * * 1-5` | 週一到五 |
| 12:33 | `33 4 * * 1-5` | 週一到五 |
| 18:40 | `40 10 * * 1-5` | 週一到五 |
| 21:40 | `40 13 * * *` | 每天 |

分鐘避開 :00 與 :30，因為 GitHub 整點與半點最容易延遲或丟排程。非交易日的項目自動跳過。

## 自動補救（保底，不准只回報）

- 每一項**每天最多自動補救一次**，記在 `data/_state/daily_audit.json` 的 `remedies`。
- 補救只是「派出 workflow」，不假裝修好。下一輪稽核會再驗證。
- 補救對應：

| 失敗的項目 | 補救 |
|---|---|
| 盤前消息 | `social-live.yml` kind=premarket、dry_run=false（盤前 post_quota 是關的，只寫網站，不發文） |
| 盤後消息、每日資料 | `daily.yml` phase=full |
| 頻道①盤後主貼文 | `social-live.yml` kind=close、dry_run=false（**只有 post_quota 的 close 開著才會走到這裡**，被降量關掉的時段不補發） |
| 網站部署 | `pages.yml`（`--ref main`） |
| Meta 權杖 | `meta_token_refresh.yml` |
| 頻道④談晴說礙 | `healing_post.yml` mode=post、dry_run=false（已發的平台由 posted.json 擋重發） |
| 頻道② | **沒有自動補救**。tc_post 只發 approved 稿，沒有可以安全重派的入口；失敗時 CEO 要人工處理，不准只寫「沒發」。 |

## 紅燈的樣子

- workflow 標紅（GitHub 會寄信）。
- 開一個 issue「⚠️ 每日稽核：有項目沒完成」，裡面列出每一個 fail 項目、哪一關不過、補救了什麼。已經有就留言更新。
- 全綠時自動關掉那個 issue。
- 結果寫進 `data/_state/daily_audit.json`，由 workflow 推回 main（rebase 重試，不 force push，不動 `data/*.parquet`）。

## 怎麼在本機跑

```bash
python scripts/daily_audit.py --no-write                       # 只看結果，不寫檔
python scripts/daily_audit.py --now 2026-11-09T19:00:00+08:00   # 用指定時間重現
python -m pytest tests/test_daily_audit.py -q                  # 測試（全部用假事實，不打 API）
```

## 已知限制（照實寫）

1. 「內容對不對」只看**日期、筆數、空值、來源連續失敗**。不判斷數字本身對不對（數字對不對是 `_uitest`、官方比對 `crosscheck` 的事）。
2. 頻道②的「執行」與「內容」用的是同一份證據（`post.md` 狀態）；發布紀錄是 main 的 `state/tc/posted.json`。**如果那個檔不存在，已到時間的 approved 稿會紅燈**，這是刻意的，不准把查不到當成綠。draft 稿不會紅。
3. 頻道④的發布紀錄格式以 `scripts/healing_post.py` 為準（`posted[資料夾][平台]`）；目前 posted.json 是空的，所以今晚 20:27 的首篇（20261108_intro）若沒發，21:40 會紅燈並自動補救一次。
4. 盤後消息的截止時間 21:40 是本稽核的規定，不是該檔案的實際產出時間；若實測發現產出時間更晚，改這裡的常數並記下樣本數。
5. 補救是派出 workflow，**派出不等於做完**；下一輪稽核才是證據。
6. 網站兩站的比對用的是 GitHub Deployments 與 pages.yml 的 Cloudflare 步驟結果；Cloudflare 那一步有 `continue-on-error`，所以「步驟 success」才算數，不能只看整個 run。
