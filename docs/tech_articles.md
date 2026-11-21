# 科技透明圈文章（隱藏分頁）怎麼新增一篇

2026-11-15 建。Andy：「影片的內容需要有內容存在……Tech 頻道的文章，且不可以顯示出來，意思是他是隱藏狀態」。

## 這個分頁是什麼

精選文章頁（`#articles`）多一個分頁「科技透明圈」（key＝`tech`），放科技透明圈每天短影片的完整文字內容。

- **永遠隱藏**：一般人、會員、預覽版訪客都看不到分頁；「全部文章」列表、搜尋、各分類篇數、側欄、熱門族群、點閱統計都不列這些文章。只有站主（管理者）看得到，樣子跟被眼睛關掉的分頁一樣（變淡、刪除線）。
- **不歸眼睛管**：這個分頁沒有眼睛，`toggleHide` 也直接擋；`hiddenNow()` 每次都把它併進隱藏名單，所以不會有人能把它「打開成公開」。也不存伺服器（`/v1/articles/tabs/put` 不送它）。
- **直接連結打得開**：`#article/<id>` 誰都能開（用來私訊給在 IG／Threads 留言關鍵字的人）。做法是文章**不進** `articles/index.json`，`showPost` 在清單找不到時才去讀 `articles/tech/<id>.json`；開這種文章不看額度、不記點閱。
- 程式在 `site/articles.js`（找 `PRIV`）。**不是**會員後端文章（沒有 `src:'api'`），也就不受 `tests/test_article_public_guard.py` 管。

## 新增一篇（每支影片一篇）要改的檔案

只動 `site/articles/tech/` 底下兩個檔，不用改程式、不用發公告（`site/notices/features.json` 不要加，這是只給站主的隱藏內容）：

1. 新增全文：`site/articles/tech/<id>.json`
2. 在 `site/articles/tech/index.json` 的 `articles` 陣列最前面加一筆清單項目（給站主在分頁裡看清單用；沒加也能用直接連結打開，只是站主分頁裡看不到）。

`<id>` 規則：只收英數、底線、點、減號，慣例 `YYYY-MM-DD-tech-<影片 slug>`，例如 `2026-11-15-tech-2nm`。直接連結＝`https://liguligu-puipui.com/#article/<id>`。

### 全文 `<id>.json` 欄位（格式同一般精選文章）

| 欄位 | 必填 | 說明 |
|---|---|---|
| `id` | 是 | 同檔名 |
| `cat` | 是 | 固定 `"tech"`（程式也會強制當 tech） |
| `title` | 是 | 標題 |
| `subtitle`、`summary` | 建議 | 導讀、一段摘要 |
| `date`、`updated` | 是 | `YYYY-MM-DD` |
| `tags` | 否 | 標籤陣列 |
| `reading_min` | 否 | 閱讀分鐘 |
| `blocks` | 是 | 內文區塊：`h`、`p`、`ul`、`callout`、`table`、`kpi`、`chart`（bar／line／barline／hbar／range）、`steps`、`compare`、`flow`、`stack`、`illus`；用法看 `site/articles.js` 開頭註解與 `site/articles/tech/2026-11-15-tech-2nm.json` |
| `sources` | 是 | 出處清單：`{title, publisher, date, url}`。**內文每個數字都要在這裡找得到出處與日期** |
| `confidence` | 否 | 一句話說明資料信心 |
| `status` | 否 | `"published"` |

### 清單 `index.json` 每筆欄位

`id`、`title`、`date`、`subtitle`、`summary`、`tags`、`reading_min`（`cat` 與 `open` 由程式補上，不用寫）。`index.json` 頂層的 `updated` 改成最新日期。

## 寫稿紀律（照影片的查證）

- 內容取自 `ai-mp4/videos/<slug>/` 的 `research.md`（查證與出處）、`narration.txt`（旁白）、`README.md`（每一鏡）。
- 「廠商目標值，非實測」「IBM 試作晶片數字，不是量產晶片」「示意，非量測」這類標示要保留；「截至 YYYY/M/D 尚未確定」照抄。
- 不給投資建議、不寫個股推薦。

## 驗收

`python scripts/_uitest.py --sections 科技透明圈文章1115`（訪客看不到分頁、全部文章不列出、站主看得到、直接連結打得開，1440 與 390）。

## 新增一個頻道分頁（ligu 哩股哩股、caffaine、healing 談晴說礙…）要改的地方

頻道分頁用 `site/articles.js` 的 **`PRIV` 設定表**管理，一個頻道一列，檔案裡已經有三列註解掉的範本。加頻道只要：

1. `site/articles.js`：在 `PRIV` 加一列 `ligu: { t: '哩股哩股', s: '哩股', col: ['#深色主題色', '#淺色主題色'] }`（`s`＝手機短名；`col` 不要用紅綠，`ic` 不寫＝沿用科技那顆晶片圖示，也可指定 `CAT_IC` 裡既有的 key）。資料路徑 `articles/<key>/index.json`、`articles/<key>/<id>.json` 由程式依 key 自動推。
2. 寫文章：`python scripts/article_publish.py <全文.json> --channel ligu`（全文 JSON 的 `cat` 寫成頻道 key 時可省略 `--channel`），它會寫 `site/articles/ligu/<id>.json` 與 `site/articles/ligu/index.json`；再 `git add site/articles/ligu` 推 main。
3. 驗收：複製 `scripts/uitest_sections/20261115_科技透明圈文章.py` 改 key 與 id（或把它的頻道清單參數化）。

不用改：Worker、`features.js`、公告、其他程式；其他頻道的分頁會在站主視角自動多一格（手機 7 格以上分頁列自動變橫向可拖，見 `site/m4/20261115-articles-tabs7.css`）。

## 隱藏怎麼做到的（程式預設，不靠伺服器清單）

- 隱藏名單＝眼睛開關的伺服器清單（`/v1/articles/tabs`）**併上** `PRIV` 的全部 key（`withPriv()`）。`PRIV` 是寫死在程式裡的，所以預設就是隱藏，伺服器清單被清空、讀不到、被竄改都不會公開。
- 這些分頁**沒有眼睛**，`toggleHide` 也擋，送去伺服器的清單會濾掉它們；要公開只能改程式（把那一列從 `PRIV` 拿掉）。
- 能不能看到分頁只看 `isAdminUser()`（連預覽版訪客也看不到）；非站主打 `#articles/<key>` 會被導回 `#articles`（有登入權杖但身分還沒回來時最多等 5 秒，免得站主重新整理被誤導走）。
- 文章不進 `articles/index.json`，所以列表、搜尋、分類篇數、側欄、熱門族群、點閱統計、站內搜尋都沒有它。直接連結 `#article/<id>` 公開可開（它本來就是靜態檔，連結沒有保密性；只是沒有任何入口列出來）。

## 2026-11-15 補：多頻道（頻道①哩股哩股 ligu 已加入）

- `loadTech()` 改成一次讀 `PRIV` 所有頻道的 `index.json`、併成一份清單（每篇帶自己的 `cat`），`filtered()` 依 `cat` 分開；`loadUnlisted()` 依 id 裡的頻道代號（`YYYY-MM-DD-<key>-…`）先找那個頻道的資料夾，其他頻道當備援。
- 頻道分頁不套日期區間（影片文章常寫隔天的上片日；只有站主看、篇數少）。
- 驗收段各頻道一支（`20261115_科技透明圈文章.py`、`20261115_哩股哩股文章.py`）；模組層級的常數名稱不要重複（各段落共用同一個命名空間，後載入的會蓋掉前面的）。科技那支改成只檢查「頻道分頁在消息分頁之後」，不再假設在最右邊。
