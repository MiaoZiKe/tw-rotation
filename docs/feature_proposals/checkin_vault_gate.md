# 比比寶箱「正式版硬閘門」後端設計（草稿，2026-11-07）

> 狀態：設計＋程式草稿，**沒有接上任何東西**。這個分支（`feat/checkin-worker`）不是 `main`，也不在任何部署工作流的觸發分支裡（`deploy-account-worker.yml` 只認 `main`），推上去不會部署。
> 依據：模擬使用者實測報告 A1（寶箱全文是公開靜態檔）、A2／A3（客戶端自己說了算）。

## 一、問題一句話

預覽版的「鎖」只鎖畫面：`site/articles/vault/posts/ck-*.json` 是公開靜態檔，任何人直接開網址就拿到全文（報告阿傑：HTTP 200，6,091 字元）；
簽到天數、兌換紀錄存在使用者自己的 localStorage，改一下就多出解鎖。法遵承諾的「只能靠簽到解鎖」，只有伺服器說了算才算數。

## 二、三條原則

1. **時間以伺服器為準**：簽到的日期由 Worker 用台北時區算，用戶端傳來的日期一律不認（根治 A3）。
2. **解鎖只看伺服器的兌換紀錄**：不看方案、不看站主身分、不看用戶端自己報的天數（根治 A2、法遵）。
3. **全文不放在公開路徑，也不放在公開的 git**：Worker 驗證完兌換紀錄才回傳內文。

## 三、⚠ 一個必須先講清楚的現實：repo 是 public

目前 12 篇文章 JSON 已經進了 public repo（`site/articles/vault/posts/`），**就算之後把檔案移走，git 歷史裡仍然讀得到**。
所以「硬閘門」要有意義，只能這樣做：

| 內容 | 做法 |
|---|---|
| 現有 12 篇（教學包） | 視為「已公開」。移出 `site/`（不再由網站提供），但不假裝歷史裡看不到；它們是通用教學，不含付費內容。 |
| 之後新增的產業深度包 | **不再 commit 進 repo**。作者（Claude）寫好後，由站主用管理端上傳（`/v1/vault/admin/put`），只存在 Worker 的資料庫。 |

## 四、資料表（寫進 account Worker 的 Durable Object SQLite，跟 `feedback`、`lists` 同一個庫）

```sql
CREATE TABLE IF NOT EXISTS ci_signs  (uid TEXT, day TEXT, kind TEXT, at INTEGER, PRIMARY KEY (uid, day));      -- kind: live | makeup
CREATE TABLE IF NOT EXISTS ci_claims (uid TEXT, ym TEXT, idx INTEGER, at INTEGER, packs TEXT, PRIMARY KEY (uid, ym, idx));
CREATE TABLE IF NOT EXISTS ci_unlock (uid TEXT, article TEXT, pack TEXT, ym TEXT, at INTEGER, PRIMARY KEY (uid, article));
CREATE TABLE IF NOT EXISTS ci_points (uid TEXT, ym TEXT, pts INTEGER DEFAULT 0, used INTEGER DEFAULT 0, PRIMARY KEY (uid, ym));
CREATE TABLE IF NOT EXISTS ci_ptlog  (uid TEXT, day TEXT, n INTEGER DEFAULT 0, last INTEGER DEFAULT 0, PRIMARY KEY (uid, day));
CREATE TABLE IF NOT EXISTS vault_posts (id TEXT PRIMARY KEY, body TEXT, updated INTEGER);                         -- 全文只在這裡
```

備份：新表要加進 `EXPORT_TABLES`（跟 `articles.js` 一樣）。

## 五、端點（全部 POST JSON、帶 `t` 會員 token，格式跟其他 `/v1/*` 一樣）

| 端點 | 輸入 | 伺服器做的事 | 輸出 |
|---|---|---|---|
| `/v1/vault/state` | — | 讀本月簽到、兌換、解鎖、補簽點數 | `{today, signs, claims, unlock, pts, mk}` |
| `/v1/vault/sign` | — | `day = 台北今天（伺服器算）`；已簽回 `already`；寫 `ci_signs` | `{ok, day, total}` |
| `/v1/vault/makeup` | `{day}` | 只能補本月、今天以前 7 天內、沒簽的日子；檢查本月補簽次數＜上限、點數≥門檻；扣點 | `{ok}` |
| `/v1/vault/point` | `{kind: say\|quiz}` | 伺服器版的比比互動：3 秒內連點不算、兩次計分間隔 ≥20 秒、每天最多 4 次、本月補簽用完或沒有空白日不算 | `{counted, why, pts}` |
| `/v1/vault/claim` | `{idx}` | 算本月簽到天數≥節點才可兌；`(uid,ym,idx)` 唯一鍵確保不重領；挑下一包（同預覽版 `nextPack` 規則）寫 `ci_unlock` | `{ok, articles}` |
| **`/v1/vault/post`** | `{id}` | **只有 `ci_unlock` 有 `(uid, id)` 才回全文**；沒有就 403 `locked`，不看方案、不看站主 | `{post}` |
| `/v1/vault/admin/put` | `{id, body}` | 管理者才可；把全文寫進 `vault_posts` | `{ok}` |
| `/v1/vault/admin/grant` | `{email, day}` | 管理者測試用：替某帳號補一筆簽到（取代預覽版的「站主工具」；留審計紀錄） | `{ok}` |

## 六、前端要改什麼（`site/checkin.js` 設計時就留了儲存層轉接器）

- `load()`／`save()` 換成呼叫 `/v1/vault/state`、`/sign`、`/claim` 等；畫面程式碼不動。
- `articles.js` 的 `fetchJson('articles/vault/posts/<id>.json')` 換成 `TwAccount.call('/v1/vault/post', {id})`。
- `site/articles/vault/manifest.json` 繼續公開（只有標題、分類、篇數、節點設定，沒有內文）。
- 站主測試工具（假今天、填到 N 天）整組拿掉，換成 `/v1/vault/admin/grant`。
- 離線／未登入：寶箱只顯示鎖，不嘗試抓內文。

## 七、上線順序（每一步都可回頭）

1. 站主點頭（見第十節那一句話）。
2. 在 `workers/account-api/` 加 `vault.js`（把本草稿搬過去，`installVault(Hub, EXPORT_TABLES)` 加在 `installArticles` 旁邊）＋ `tests/vault.test.mjs`（沿用 `harness.mjs`）。
3. 預覽分支跑：簽到→兌換→讀文，直接打 `/v1/vault/post` 未解鎖 → 403。
4. 把現有 12 篇用 `/v1/vault/admin/put` 灌進去，**再**把 `site/articles/vault/posts/` 從網站移除（順序反了會有空窗）。
5. 上線後驗收：未登入／未兌換直接開舊網址 `articles/vault/posts/ck-C01.json` → 404；用另一個帳號改 localStorage 沒有任何效果。

## 八、已知取捨

- 預覽版使用者在 localStorage 的簽到紀錄**不遷移**（無法驗證真偽），正式版從 0 開始；預覽版本來就標了「資料只存在這個瀏覽器」。
- 多一次網路請求才讀得到文章；`this.json()` 本來就回 `cache-control: no-store`，全文不會被 CDN 或瀏覽器共用快取。
- Durable Object 單一實例：簽到每人每天一次、寫入量很小，在免費額度（每天 10 萬列寫入）內。

## 九、不在這次範圍

- 付費加買單篇（不是這個功能的規格）。
- 全文浮水印綁帳號（可以之後在 `/v1/vault/post` 回應裡加 `wm: <email 末碼>` 讓前端畫在文章上，嚇阻轉貼）。

## 十、需要 Andy 同意的那一句話

> 「我同意把比比寶箱的文章全文從公開網站檔案移走，改存在會員伺服器（account Worker）的資料庫、只有伺服器確認你簽到兌換過才回傳；簽到天數與兌換紀錄也改由伺服器記，這需要新增幾張資料表並部署 account Worker；現有 12 篇文章過去已公開在 GitHub 的歷史紀錄不會因此消失，之後新增的深度包才不放進 GitHub。」
