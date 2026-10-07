# 「可更改網站的功能」盤點與管理者限定（2026-10-07）

Andy（10-07 14:50）：「拖曳功能，只有帳號可以使用，任何可更改功能都只有我這帳號可以，其他帳號我沒有新增管理者情況下不行，這點非常重要!!! 管理那邊需要新增一個誰擁有管理權限」

## 結論先講

- **管理者是誰**：擁有者＝Worker Secret `ADMIN_EMAILS`（就是 Andy；email 不寫進 public repo）＋擁有者在 `#admin/admins` 加的人。
  判定只在 Worker（`workers/account-api/worker.js`「管理權限區塊」），前端只讀 `/v1/me` 回的 `admin`／`owner` 旗標決定畫面長相。
- **伺服器端總閘**：所有 `POST /v1/admin/*`（匯出／還原兩條另有備份權杖規則，除外）在進到各自的處理函式前先驗「權杖有效且是管理者」，不是就 403。
  各端點原本自己的檢查照留，所以是兩道；以後新增 admin 端點忘了寫檢查也擋得住。`tests/admins.test.mjs` 逐支打 25 條路徑（含一條不存在的），訪客／一般會員／假權杖全部 403。
- **付費資料閘道（workers/data-gw）**的管理端點（`/v1/admin/alerts`、`/wm`、`/devices/reset`）一律回頭問 account-api 的 `/v1/me` 拿 `admin` 旗標，所以自動吃到同一份名單（被加的人能用、被移除的人不能用）。
- **分頁拖曳**：只有管理者看得到、拖得動；非管理者不掛拖曳（沒有提示、沒有抓取游標、Alt+←→ 與右鍵還原都不作用），已存的個人排序開頁就清掉回預設。

## 盤點表

「範圍」：全站＝改了別人也看得到；本機＝只改自己這台瀏覽器；個人雲端＝存在 Worker 但只有本人讀寫。

| 功能 | 在哪 | 改前誰能用 | 改後誰能用 | 範圍 | 伺服器端檢查 |
|---|---|---|---|---|---|
| 分頁拖曳排序（各頁 `.nbsw`／`.subtabs`／`role=tablist` 分頁列） | `site/tabdrag.js` | 所有人 | **只有管理者** | 本機（localStorage `tw.tabs.*`） | 不適用（不打 Worker）。非管理者已存的排序自動清除 |
| 管理區頂層分頁拖曳（流量觀測分頁順序） | `site/admin.js` `#trTabs` | 管理者 | 管理者 | 本機 | 頁面本身只給管理者 |
| 付費範本頁籤拖曳排序 | `site/admin.js` → `/v1/admin/plans/sort` | 管理者 | 管理者 | **全站**（訂閱頁順序） | ✅ 端點自己檢查＋總閘 |
| 會員權限／功能開關（每個 email、每個範本的開關與次數） | `#admin/perm` → `/v1/admin/perm/put`、`/v1/admin/plans/put` | 管理者 | 管理者 | **全站** | ✅ 兩道 |
| 方案建立／改名／定價／刪除 | `#admin/perm` → `/v1/admin/plans/put` | 管理者 | 管理者 | **全站** | ✅ 兩道 |
| 公告發佈／下架／刪除 | `#admin/notices` → `/v1/admin/notices/*` | 管理者 | 管理者 | **全站** | ✅ 兩道 |
| 意見反饋處理（標記／刪除） | `#admin/feedback` → `/v1/admin/feedback/*` | 管理者 | 管理者 | 全站（後台） | ✅ 兩道 |
| 線上人數公開開關 | `#admin/traffic` → `/v1/admin/settings` | 管理者 | 管理者 | **全站** | ✅ 兩道 |
| 停權解除、uid 查詢 | `#admin/gw` → `/v1/admin/susp/*`、`/v1/admin/uids` | 管理者 | 管理者 | 全站（後台） | ✅ 兩道 |
| 異常、浮水印反查、裝置重設 | `#admin/gw` → data-gw `/v1/admin/*` | 管理者 | 管理者 | 全站（後台） | ✅ data-gw 問 account-api 的 admin 旗標 |
| **管理者名單新增／移除（新）** | `#admin/admins` → `/v1/admin/admins/add｜del` | — | **只有擁有者** | **全站** | ✅ 兩道＋擁有者檢查（一般管理者 403） |
| 會員資料匯出／還原 | `/v1/admin/export`、`/import` | 管理者或備份權杖 | 同左 | 全站 | ✅ 原規則（備份權杖＝Worker Secret） |
| 盤中即時層（開關） | `site/livegate.js` | 管理者 | 管理者（含被加的人） | 本機 | 前端閘門；報價代理本身是公開資料 |
| 網站內容、資料、YAML、程式 | GitHub repo `main` | Andy＋Claude（GitHub 權限） | 同左 | 全站 | GitHub 權限，跟網站帳號無關 |
| 自選清單（新增／刪除／排序清單分頁 `#wpTabs`） | `site/watchpage.js` → `/v1/lists/put` | 每個登入者 | 每個登入者（**沒改**） | 個人雲端 | ✅ R1：只能寫權杖本人那一份 |
| 意見反饋送出、訂閱申請 | `/v1/feedback`、`/v1/subscribe/request` | 所有人 | 所有人（沒改） | 送進管理者後台，不改別人看到的內容 | ✅ 格式與頻率限制 |
| 使用統計、心跳、每日額度扣次 | `/v1/track/batch`、`/v1/beat`、`/v1/quota/hit` | 所有人 | 所有人（沒改） | 只能遞增白名單計數 | ✅ R2 |
| 外觀（深淺色）、側欄收合、圖表畫線、K 線週期等個人設定 | `theme4.js`、`layout4.js`、`drawtools.js`… | 所有人 | 所有人（沒改） | 本機 | 不適用 |

## 判斷過、Andy 可以否決的地方

1. **自選清單的分頁拖曳沒有鎖。** 那是會員自己的清單資料（跟「加一檔股票」同一類），改了只影響本人；鎖掉等於自選功能壞一半。若 Andy 要連這個也只限管理者，改 `watchpage.js` 一行 `draggable` 判斷即可。
2. **深淺色、側欄收合、畫線等個人顯示設定沒有鎖。** 不會改到全站，也不是拖曳。
3. **只有擁有者能新增／移除管理者**（一般管理者不行）。理由：否則任何一個被加進來的人都能再加人、或把別人拔掉，權限會在擁有者不知情時擴散。代價：擁有者不在時沒人能加人 —— 一人經營的站可以接受。
4. **擁有者用既有的 `ADMIN_EMAILS` Secret，不把 email 寫死在程式裡。** repo 是 public，寫死等於把 Andy 的 email 公開；效果相同（Secret 裡的人永遠是管理者、頁面上沒有移除鈕、Worker 對擁有者的移除回 409）。

## 已知限制（照實寫）

- 分頁拖曳是本機設定，前端擋住的是「正常使用」。會改自己瀏覽器程式碼的人能讓自己那台瀏覽器的分頁換位置 —— 但那只影響他自己那台，**不會改到任何人看到的東西**，也沒有任何伺服器寫入。
- 被移除的管理者：Worker 每次請求即時查名單，所以他「下一個請求」就失去權限；同時換掉他的權杖版本（`users.tv + 1`），要重新登入，之後只是一般會員。
- 擁有者名單要改（例如換 email）＝改 Cloudflare 的 `ADMIN_EMAILS` Secret，不在網頁上。

## 稽核紀錄

`admin_log` 表（append-only：每次新增／移除都是新的一列，舊列不改不刪）。`#admin/admins` 頁面下方列最近 200 筆：時間（台北）、動作、對象、操作者。
會員資料匯出（`/v1/admin/export`）會一起帶出這張表。

## 驗收

- `node --test workers/account-api/tests/admins.test.mjs`：總閘（25 條路徑 × 訪客／會員／假權杖）、擁有者新增、一般管理者不能加人或拔人、擁有者不能被移除、移除後舊權杖失效、重新登入只是一般會員、稽核紀錄 append-only。
- `_uitest --sections 管理權限1007`：非管理者看不到拖曳把手、模擬拖曳順序不變、已存排序被清掉、進 `#admin/admins` 被擋；擁有者可拖曳、擁有者那列沒有移除鈕；新增確認框寫「此人將能修改全站」；被加的人重新整理後進得了管理區、可拖曳、看不到新增鈕；移除後失去權限、不能再拖。
- `分頁拖曳1006` 改成在「已登入管理者」環境下跑（原本的九項拖曳行為照驗）。

## 2026-10-07 15:45 追加：擁有者限定（Andy：「管理權限 移動到 會員權限上方，並且旁邊的分頁 有在權限內的帳號也可以進行拖曳 但不能刪除」）

| 操作 | 擁有者 | 一般管理者（被加入的） | 非管理者 | 伺服器端 |
|---|---|---|---|---|
| 側欄「管理區」子項拖曳排序（管理權限／會員權限／流量觀測／意見反饋；預設管理權限在最上） | ✅ | ✅ | 看不到這一區 | 本機 `tw.l4.admOrd`，不打 Worker |
| 各頁分頁拖曳（tabdrag.js） | ✅ | ✅ | ❌ | 本機 |
| 付費範本頁籤拖曳排序（`/v1/admin/plans/sort`） | ✅ | ✅ | ❌ | 管理者 |
| **刪除付費範本頁籤（× ／ `plans/put del:true`）** | ✅ | ❌ 看不到 ×，硬打 403 `owner_only` | ❌ | **擁有者限定** |
| 新增／移除管理者 | ✅ | ❌ 看不到按鈕，硬打 403 | ❌ | **擁有者限定** |

側欄與頂層導覽本身沒有「刪除分頁」的操作；全站可拖曳的分頁也都沒有刪除。

## 2026-10-07 16:30 追加：擁有者豁免所有限制（Andy：「將我把 kcq01010909 帳號設為最高管理權限，他不會需要被限制」）

擁有者＝`ADMIN_EMAILS`（Andy 的帳號）。判定在 Worker，前端讀 `/v1/me` 的 `owner` 旗標。

| 項目 | 原本怎麼判定 | 擁有者現在 | 一般管理者現在 | 檔案 |
|---|---|---|---|---|
| 功能開關鎖頭（範本關掉的功能） | perm.js 照 `/v1/perm/me` 的 feats 上鎖，**沒有任何管理者判定** ← Andy 被鎖的原因 | ✅ 豁免（前端 `owner()` 一律可用；Worker `/v1/perm/me` 對擁有者回全開） | ❌ 照範本 | site/perm.js、worker.js 檔尾 |
| 族群觀測（grp.*） | perm.js | ✅ 豁免 | ❌ 照範本 | site/perm.js |
| 每項功能每日次數（lims） | quota.js 讀 `TwPerm.lim`；伺服器 `/v1/quota/hit` | ✅ 豁免（前端 Infinity；伺服器原本就跳過管理者） | 伺服器豁免、前端照範本（**待 CEO 決定**） | site/quota.js、site/perm.js、worker.js |
| 全站每日額度 quota.all（dq）與剩餘次數圓圈 | 同上＋圓圈在 all＝Infinity 時隱藏 | ✅ 豁免、圓圈不顯示 | 同上（待決定） | site/quota.js |
| 自選分頁數／每頁檔數 | watchlists.js 讀 `TwPerm.limit`；伺服器 `/v1/lists/put` 依範本 | ✅ 豁免（前端給最大值；伺服器原本就給管理者硬上限 50 頁／200 檔） | 伺服器豁免、前端照範本（待決定） | site/watchlists.js、worker.js（watch-v2） |
| data-gw 每日額度／功能權杖 | 換權杖時讀 `/v1/perm/me`；`me.user.admin` 不收 dq／lims | ✅ 豁免（perm/me 全開＋原本的管理者豁免） | ✅ 原本就豁免 dq／lims；feats 照範本 | workers/data-gw/worker.js |
| data-gw 裝置數上限 | `!me.user.admin` 才檢查 | ✅ 豁免 | ✅ 豁免（原本） | workers/data-gw/worker.js |
| 異常停權（/internal/suspend） | `isAdmin(u)` → 409 不停 | ✅ 豁免 | ✅ 豁免（原本） | worker.js（停權區塊） |
| 限流 | 心跳每 IP 每分鐘 240 次（全站共用），沒有針對個人的其他限流 | 不影響正常使用（沒改） | 同左 | worker.js `RATE_PER_MIN` |
| 盤中即時閘門 | livegate.js：`admin === true` | ✅ | ✅（原本） | site/livegate.js |
| 管理區導覽 | `admin` 旗標 | ✅ | ✅ | site/layout4.js |

驗收：`node --test`（擁有者在「功能全關＋額度 0＋自選 1 頁 1 檔」範本下 perm/me 全開、quota/hit 不 over、lists/put 200；一般會員同範本被擋）；`_uitest 管理權限1007` ⑥（擁有者 TwPerm 全可用、圓圈不顯示；一般管理者對照組照樣上鎖）。
