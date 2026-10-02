# 分支預覽（DECISIONS #301）

Andy 2026-10-03：「直接開分支給我一版可操作的，以後都這樣，避免覆蓋到原版本」。

**要給 Andy 看的半成品，一律推 `preview/<名稱>`，附上預覽網址，不推 main。**

## 怎麼開一份預覽

```bash
# 把手上的分支推成預覽（名稱只用英數、-、_、.；斜線會變成 -）
git push origin <你的分支>:preview/<名稱>

# 例：版面 v2
git push origin claude/layout-v2-desktop:preview/layout-v2
```

網址：`https://miaozike.github.io/tw-rotation/preview/<名稱>/`
（例：<https://miaozike.github.io/tw-rotation/preview/layout-v2/>）

頁面最上方有一條黃色橫幅「預覽版：<名稱>（分支 <sha 前 7 碼>），不是正式站」，附「回正式站」連結；
分頁標題前面也會多「［預覽 <名稱>］」。

### ⚠ 推完沒看到更新？

`push` 事件讀的是**被推的那個分支裡的** `pages.yml`。分支如果是在這個機制上 main 之前拉出來的，
它的 `pages.yml` 沒有 `preview/**` 觸發，推了不會動。兩種解法擇一：

1. 先把 main 合進那個分支再推（之後每次推都會自動部署）；
2. 推完手動跑一次部署：Actions → 部署網站 → Run workflow（main），
   或 `gh workflow run pages.yml --ref main`。

## 怎麼收掉

```bash
git push origin --delete preview/<名稱>
```

刪除會觸發一次部署（`delete` 事件讀 main 的工作流），那份預覽就消失。
就算那次沒跑到，**下一次任何部署也會把它清掉** —— 每次部署都是整包重建，只收「當下還在的 preview/* 分支」。

## 運作方式

```
main 有 push ／ 手動執行 ／ 刪掉 preview/* 分支
  └─ pages.yml（在 main 上跑）
       ├─ 照舊：site/ ＋ site/data/（JSON）＝ 正式站
       └─ scripts/preview_inject.py：git ls-remote 找出所有 preview/* 分支，
          每個淺抓一次、把它的 site/（不含 data/）放到 site/preview/<名稱>/，並注入 preview_boot.js

preview/* 有 push
  └─ pages.yml 的 relay-preview：只做一件事 —— gh workflow run pages.yml --ref main
     （github-pages 環境只准 main 部署；真正的部署永遠在 main 上做）
```

- **資料不複製**：預覽版的 `data/...` 請求在瀏覽器端被改寫成 `/tw-rotation/data/...`（正式站那份）。
  每份預覽只多約 7.5MB（程式＋vendor），Pages 上限 1GB 不會被吃掉。
  ⚠ 代價：預覽版看的是**正式站的資料**。分支若改了 `pipeline/build_payload.py`（JSON 格式），
  預覽版看不到新格式 —— 那種改動要另外處理（例如分支裡先相容舊格式）。
- **正式站零改動**：注入只發生在 `site/preview/<名稱>/index.html`，正式站的 HTML／JS 一個字都沒動。

## 預覽版跟正式站分開的東西

| 項目 | 做法 | 結果 |
|---|---|---|
| localStorage／sessionStorage | `preview_boot.js` 在所有程式之前把 `window.localStorage` 換成加前綴的殼，實際鍵是 `twpv:<名稱>:<原鍵>` | 預覽版的設定、自選、手繪線、主題跟正式站完全分開；不同預覽之間也分開。正式站讀不到預覽的鍵 |
| 會員雲端資料 | 預覽版擋下所有寫入：`/v1/lists/put`、`/v1/delete`、`/v1/beat`、`/v1/admin/*/put`、`/v1/admin/settings` 回 403 `preview_readonly` | 預覽版可以登入、讀雲端自選，但**改不到**正式站的雲端資料，也不算進使用統計 |
| Service Worker | 預覽版不註冊（兩邊的快取都叫 `tw-*`，會互刪） | 預覽頁由正式站的 SW 管：導覽網路優先、data 不快取，不影響行為 |

已知限制：

- 預覽版要**另外登入一次**（登入權杖也存在 localStorage，被隔離了）。
- 預覽版的雲端自選若改了，**同步回雲端會失敗**（被擋）—— 這是刻意的。要測雲端寫入請在正式站測。
- 跨分頁同步（`storage` 事件）在預覽版不會觸發同分頁的更新（鍵名帶前綴）；重新整理即可。
- 登入／即時：account-api、quote-proxy（Worker）與 taifex-deno 都只看 **Origin**（`https://miaozike.github.io`），
  不看路徑，所以預覽網址下**登入與即時報價都能用**。登入回呼也是比 origin，會回到預覽頁。
