# 每日額度與 Plus／Pro 方案（2026-10-07）

> Andy（10-07 01:30）：「圖二的內容當達到上限，出現的畫面參考圖三，並且可以置中，之後會分成 Plus 和更上去的 Pro。plus 目前先暫定皆可以觀看50次，pro 則是都不限次數」
> Andy（10-07）：「註冊可以自選一個分頁且10檔股票…plus 可以新增5個分頁、pro 可以不限分頁」
> 分支：`claude/quota`（從 `claude/data-gw` 開，合過 main）。預覽：`preview/quota`。**還沒上 main。**

## 1. 方案

| 方案 | 每日研究額度 | 自選分頁 | 每頁自選檔數 | 價格 |
|---|---|---|---|---|
| 訪客 | **每日共 3 次**（前端計；訪客沒有帳號，伺服器只能靠付費資料閘道的訪客範本開關） | 0（沒有自選） | 0 | — |
| 註冊會員 | **每日共 10 次** | 1 | 10 | 免費 |
| **Plus** | **每日共 50 次** | 5 | 50 | NT$249／月（年 2,490） |
| **Pro** | **不限** | 不限（硬上限 50） | 200（硬上限） | NT$499／月（年 4,990） |

> 2026-10-07 02:45 CEO 版（方案表 `docs/plan_presets_1007.json` → `site/plan_presets.js`，自選以 CEO 這版為準）。
> 上面的值要管理者在 #admin/perm 按「套用建議方案」才會寫進伺服器；沒按之前，正式站的範本維持原樣。

- **全站共用額度 `quota.all` ＝ 範本欄位 `plans.dq`**（account-api「每日額度區塊」）；空白＝不限。前端 `TwPerm.lim('quota.all')` 讀它。
  #admin/perm → 每個範本的 ⚙「全站每日額度」可以改（訪客、註冊會員的 ⚙ 只有這一欄）。
  為什麼不在 features.js 另列一個 `quota.all` 開關：管理頁會把 features.js 的每一項畫成一顆開關或一個下拉，共用額度不是「某個功能」；
  它跟價格一樣是範本本身的屬性，所以放範本欄位、在 ⚙ 裡改。
- **哪些功能吃共用額度**：features.js 標 `metered: true` 的 41 項（方案表裡訪客要計次的那些：資金流向、產業鏈、熱力圖、市場明細、週期統計、個股頁各分頁與 K 線、選股、ETF、財經日曆）。
  總覽、產業地圖首頁、事件、自選、工具類不吃（那些是鉤子或不是「看資料」）。
- **共用額度與逐功能上限兩者取較嚴**：逐功能 lims（例如註冊會員的個股頁 10）照樣算；訪客那 41 項「各 3 次」拿掉 ——
  共用 3 次已經保證每項 ≤ 3，留著只會讓管理頁一片「3/日」、改的時候要改 41 個地方。
- 範本介紹欄位（badge、tagline、fit_title、fit_desc、highlights、price_year）存在 `plans.meta`（account-api plan-meta 區塊），
  `/v1/plans/public` 攤平成同名欄位給訂閱頁讀（訂閱頁另一條分支 claude/pricing-v2 在做）。
- 自選上限是兩個功能開關 `watch.tabs`、`watch.size`（`site/features.js`，kind:limit）。預設值＝免費會員（1／10）。
- Plus／Pro 由 account-api 第一次啟動時種下（`wrangler.toml` 的 `SEED_PLANS = "plus,pro"`，只種一次；刪掉不會再長回來）。
  同一次會替**既有的付費範本**（例如「付費會員」）補上舊的自選上限 5 頁／50 檔 —— 不然預設改成 1 頁之後，他們會突然少 4 頁。
- 價格 0 ＝訂閱頁寫「價格待定」。定價後在 ⚙ 改。

## 2. 「一次」的定義（CEO 拍板）

**同一天（台北日期）、同一個單位只算一次。**

| 單位 | 怎麼認（伺服器端，看檔名） | 不另外扣的 |
|---|---|---|
| 一檔個股頁 | `stock/<代號>`、`m60/<代號>`、`hist/<代號>/p<N>` 全部是 `<代號>`（例 `2330`，跟前端 `pageKey` 同一個字串） | 個股頁裡切總覽／基本面／營收／籌碼分頁（同一支 `stock/<代號>.json`）、K 線往回翻頁、1H／4H |
| 一個付費分頁 | 其他付費檔＝它對應的第一個功能鍵 `p.<功能鍵>`（例：flow_v3、rrg_members、rotation 都是 `p.flow.rot`）。前端是「一次造訪」（`<頁>.<瀏覽器分頁>`），伺服器看不到瀏覽器分頁，退一步一天算一次（比前端寬，前端先擋） | 同一個分頁要讀的多支檔 |
| 一張產業鏈剖析圖 | 前端 `d.<鏈>.<圖>`；伺服器 `chain/<鏈>` → `c.<鏈>`（**檔案還沒拆，見第 5 節**） | — |

- 同一天重開同一檔不再扣；額度滿了之後，**今天看過的照樣能看**（已經付過的那一次不再擋）。
- 重置：台北 00:00（`tpeReset`，一律 UTC+8）。
- 免費檔（meta、stocks、logos…）不算。

## 3. 為什麼計數一定要在伺服器

前端計數（`site/quota.js` 的 localStorage）按 F12 就能改。真正的扣次放在付費資料閘道 `workers/data-gw`：

- `units` 表：`(uid, 台北日期, 單位)` 主鍵 ＝ 同一天同一單位只有一列。留 3 天。
- `/v1/session` 換資料權杖時從 account-api `/v1/perm/me` 拿 `dq`，存在 session；回應帶 `quota: {used, limit, reset}`。
- `/v1/data/<檔>`：付費檔＋session 有 dq → `charge()`：看過就放行；沒看過而且 `used >= dq` → **429 `{error:'quota', used, limit, reset, plan}`**；否則記一列。成功回應帶 `x-quota: used/limit/reset` 標頭。
- `GET /v1/quota`（同發檔的權杖）→ 目前 `{used, limit, reset, plan}`。
- **逐功能上限（範本 lims）也在 data-gw 扣**：個股檔（stock／m60／hist）單位＝代號，扣這支檔的功能鍵＋`stock.page`；滿了回 429 `{error:'quota', feat}`、上限 0 回 403。
  沒有對象的付費檔（一支檔餵整頁、所有對象共用）伺服器分不出看了幾個 → 只能前端計（限制寫在 `docs/quota_coverage.md`）。
- **account-api `/v1/quota/hit` 也照同一套規則**（quota-v2 區塊）：鍵 `quota.all` 對範本 dq、其他鍵對 lims；新單位而且已滿 → 不記、回 `{over:true}`，前端看到就蓋卡。
- 管理者、Pro（dq 空白）不限。訪客不計（沒有 uid）。
- 測試：`node --test workers/data-gw/tests/quota.test.mjs`（第 50 個放行、第 51 個擋、同單位重看不扣、台北 00:00 重置、Pro 與管理者不限）；
  `node --test workers/account-api/tests/quota.test.mjs`（dq 欄位、種子、perm/me 回 dq、自選上限）。

自選上限也在伺服器擋：account-api `/v1/lists/put`（watch-v2 區塊）依範本檢查，**只擋「變多」**（分頁數或某頁檔數超過上限、而且比雲端那份多 → 403 `watch_limit`），已經建好的不刪。

## 4. 前端

- `site/qcard.js`：共用卡片（額度用完／需開通兩種，同一個殼）。蓋在被擋住的區塊裡**水平垂直置中**；區塊比視窗高時卡片黏在視窗中間；寬 520、手機吃滿區塊。
  - 額度卡：小標「🔒 Plus 每日額度」→「今天的研究額度用完了」→ 說明 → 分段進度條（上限 > 10 固定 10 段：Plus 每段 5 次）→「今日已使用 50 / 50 次」＋「X 小時 Y 分後重置」→「升級 Pro 還能使用」清單 →「升級 Pro →」（`#pricing/plan/pro`）。免費會員用完則寫 Plus 的內容。
  - 需開通卡（取代原本的「🔒 此功能需開通／升級查看 →」）：「此功能需開通」＋功能名 →「這些方案可以使用」（讀訂閱頁的方案資料）→「升級 Plus →」（`#pricing/need/<功能鍵>`）。
  - 自選超過上限：同一款卡片浮在畫面中間（`TwQCard.modal`）。
- `site/datagw.js`：收到 429 quota → 發 `tw:quota` 事件 → qcard 蓋卡（個股頁蓋整頁、產業鏈頁蓋剖析圖、其他蓋目前這一頁）；換頁就拿掉（下一頁超過時 gateway 會再回 429）。
- **data-gw 沒開（正式站現況）→ 永遠不會有 `tw:quota` → 畫面完全照舊。**
- 示範開關（預覽站用，不寫任何資料）：`?demo=quota`（Plus 50/50）、`?demo=quota-free`（免費 5/5，**5 是示意值**，免費範本目前不限）、`?demo=lock`（剖析圖需開通）。示範時訂閱頁會補 Plus／Pro 兩張「價格待定」示意卡（後端還沒種時）。
- 驗收：`python scripts/_uitest.py --sections 額度卡片1007,自選上限1007`。

## 5. 上線前要做的事

1. **產業鏈剖析圖要拆檔**：現在所有鏈共用 `supply_chain.json`，伺服器只能算「整個產業鏈功能一次」。要「一張剖析圖一次」，`pipeline/build_payload.py` 要輸出 `chain/<鏈>.json`、`workers/data-gw/tiers.js` 白名單加 `chain/<鏈>`，前端 industry.js 改讀單鏈檔（`unitOf` 已經認 `c:<鏈>`）。
2. data-gw 第二階段上線（R2、`DATA_GW_URL`，見 `docs/datagw_plan.md`）—— 在那之前額度只有示範開關看得到。
3. account-api 合併 main 時會自動部署：**會種 Plus／Pro、會把既有付費範本補上 5 頁／50 檔、免費與訪客的自選上限會從 5 頁變 1 頁（已經建好的不刪）**。要 Andy 點頭再合。
4. 定價（Plus／Pro 目前「價格待定」）。
5. 免費會員要不要也設每日額度（目前不限）。
6. `site/quota.js`（每個功能各自的每日次數，前端計數）跟這套並存：那套是「單一功能一天幾次」，這套是「整站一天幾個單位」。上線收費後建議只留伺服器這套。

## 6. 2026-10-07 追加：套用建議方案、覆蓋稽核

- `site/plan_presets.js`（`window.TW_PLAN_PRESETS`）＝方案表＋CEO 兩點修正；#admin/perm 右上「套用建議方案」：
  先跳確認框列出四個範本各會改哪些（名稱、月費、全站額度、標籤、開關、每日次數），按「確定套用」才依序 `plans/put`。
  範本對應用 id：訪客→`guest`、註冊會員→`free`、Plus→id `plus`／名稱「Plus」／名稱含「299」、Pro→id `pro`／名稱「Pro」／名稱含「499」；都沒有才新建。
- 覆蓋稽核：`docs/quota_coverage.md`；自動掃描 `python scripts/_uitest.py --sections 次數覆蓋掃描1007`（每個功能設上限 1，第 2 個單位一定要被擋；桌機 1440＋手機 390）。
