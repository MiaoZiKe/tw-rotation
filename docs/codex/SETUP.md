# 在 Codex 建立「社群製作部」的步驟（給 Andy）

> 對應你 10-17 的需求：在 Codex 建一套和 Claude 這邊相同分工的系統（CEO＋製作人員），專門做 IG／Threads 貼文與短影片，資料來源是網站精選文章或你給的連結，風格照三張範例圖，成品要備份。

## 先講結論
Codex 沒辦法像 Claude 這邊那樣「永遠在背景自己接單」。它是「你在專案裡開一個對話、貼一句話，CEO 就照規則開工」。所以全部規則寫成一份 `AGENTS.md` 放在專案資料夾根目錄，Codex 每次開工都會先讀它。

## 第 1 步：建立專案資料夾（約 2 分鐘）
你現在畫面停在「建立專案」視窗：
1. 專案名稱那格寫 `LIGULIGU`（你已經填了）。
2. 「來源資料夾」那一塊：選「在這台電腦上新增資料夾」→ 選一個位置（例如 `D:\` 或「文件」）→ 資料夾名稱也叫 `LIGULIGU`。
3. 按右下角黑色「建立專案」。

## 第 2 步：放進 3 樣東西（約 5 分鐘）
打開你剛建的 `LIGULIGU` 資料夾（檔案總管），照這樣建：

| 要建的 | 怎麼做 |
|---|---|
| `AGENTS.md` | 1) 打開 https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/docs/codex/AGENTS.md ；2) 按 Ctrl+A 全選、Ctrl+C 複製；3) 在 `LIGULIGU` 資料夾新增文字檔，改名 `AGENTS.md`（注意不是 `.txt`），貼上存檔 |
| `reference/style_samples/` | 新增資料夾 `reference`，裡面再建 `style_samples`，把你給我看的三張範例圖（HBM 十頁、CoWoS 海報、ASML 十頁）另存進去，檔名分別 `hbm_10p.png`、`cowos_poster.png`、`asml_10p.png` |
| `output/` | 新增一個空資料夾 `output` |

（視覺規範原文不用你下載，Codex 會自己從網址讀。）

## 第 3 步：讓 Codex 連到 GitHub（約 3 分鐘）
1. 在 Codex 左下角或設定裡找「GitHub」或「連接器／Connectors」。
2. 按連接，登入你的 GitHub 帳號 `MiaoZiKe`。
3. 授權時，選能存取 `tw-rotation` 這個 repository（讀取與寫入）。
4. 沒有這一步，Codex 讀得到公開網址，但**寫不進備份**。

## 第 4 步：第一次對話（約 2 分鐘）
1. 在 Codex 左邊按「新對話」，確認上方專案是 `LIGULIGU`。
2. 整段貼上這句，按送出：

```
請先讀專案根目錄的 AGENTS.md，再照第十節「第一次使用的自我檢查」做：先回報你有哪些工具能力（寫檔、Python、ffmpeg、圖像生成、連網、GitHub 讀寫），建立資料夾，用三句話複述任務與紅線，然後用 Issue #4 做試做題（只做第 1 頁風格校準、派工單、brief.md）。全程繁體中文。
```
3. 等它回覆，把它回的「工具能力清單」貼給我，我來判斷哪些步驟要改成手動。

## 第 5 步：日常怎麼用
| 你想做 | 你在 Codex 貼什麼 |
|---|---|
| 用網站精選文章做貼文 | `請用精選文章 <文章id 或網址> 製作 IG 貼文、Threads 與短影片，照 AGENTS.md。` |
| 用網站「傳給 GPT」按鈕產生的工單 | 在網站按「傳給 GPT」→ 送出 Issue → 貼 `請處理這個 Issue：<Issue 網址>，照 AGENTS.md。` |
| 用你自己的主題或連結 | `主題：<一句話>；參考連結：<網址>；請製作 IG 貼文與 Threads，照 AGENTS.md。` |
| 只要某一種 | 在句子後面加「只做 IG 貼文」或「只做短影片」 |

## 第 6 步：成品與備份在哪
- **本機：** `LIGULIGU\output\<日期>_<主題>\`，裡面有 10 張 PNG、貼文說明、Threads 文案、來源表、素材登錄、品管報告。
- **GitHub 備份：** repository `MiaoZiKe/tw-rotation`，路徑 `docs/social_posts/<日期>_<主題>/`，由 Codex 開 PR（標題 `[社群成品] 日期｜主題`），你不用管，PR 是公開的。
- **大檔（MP4、高解析原圖）：** 不放 GitHub，只留在本機 `output`，請你自己另存雲端硬碟。
- **總索引：** `docs/social_posts/INDEX.md`，一列一則。

## 第 7 步：你只需要做的審核
1. 看 Codex 回報的第 1 頁風格校準，OK 才讓它做全套。
2. 看成品 PNG 與文案，要改直接跟它說。
3. 滿意後，你自己手動發到 IG／Threads（Codex 不會自動發）。
4. 要我（Claude）複核事實與法遵：把 Codex 的 PR 連結貼給我。

## 常見問題
- **Codex 說讀不到網址／寫不進 GitHub：** 回到第 3 步重新授權，或把它回的錯誤貼給我。
- **Codex 生的圖中文字是亂碼：** 這是生圖模型的通病，AGENTS.md 已要求中文字後製排版；若它做不到，請它交「底圖＋文字稿」，我可以幫你合成。
- **風格偏掉：** 叫它「對照 reference/style_samples 與視覺規範重做第 N 頁」。
- **範例圖左下的第三方帳號浮水印：** AGENTS.md 已禁止複製。
