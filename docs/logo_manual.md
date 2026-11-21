# 人工指定公司 Logo（第四版，DECISIONS #276）

自動取圖（官網 → Google s2 → Wikimedia Commons）救不了的公司，可以由人指定一張 Logo。
這是 Andy 2026-09-28「也可以直接去他們公司將 Logo 截圖貼上」的合規做法：**人在瀏覽器裡看過、確認是那家公司的 Logo**，
再把圖交給 CEO 放進 repo；程式不去任何網站「截圖」或搜 Google 圖片（理由見 `docs/logo_sources.md` §1.3）。

## 放哪裡

```
data/logos/manual/<代號>.png          圖檔（也收 .jpg／.jpeg／.webp／.gif／.svg；同代號多個檔時 png 優先）
data/logos/manual/manual.json         每家的來源紀錄
```

`manual.json` 長這樣（鍵是代號；可以另外寫 `"_說明"` 之類的非代號鍵，程式會略過）：

```json
{
  "8038": {"source_url": "https://www.公司官網/", "date": "2026-09-29", "note": "官網頁首的 Logo，Andy 在對話裡貼的圖"}
}
```

`source_url` 請寫**圖真正出自哪裡**（公司官網那一頁、年報 PDF 的網址）。沒寫照樣套用，但執行摘要的 `manual.missing_meta` 會列出來，要補。

## 圖要長怎樣

- 至少 16px；**長寬比不超過 5:1**（橫長字標縮進 20px 的框只剩一條線 —— 請裁成接近正方形，例如只留圖形標誌）。
- 透明底最好；程式只做等比縮放與補透明邊（不裁、不拉、不改色），所以圖本身要乾淨。
- 只放那家公司自己的 Logo；不要放搜尋引擎結果裡來源不明的圖。

## 放了之後會發生什麼

1. 推上 main 後，下一輪 backfill.yml 的排程守門看到 `data/logos/manual/` 跟索引對不上，會放行一輪 `--datasets logos`
   （也可以手動觸發「歷史回補」、資料集選 `logos`）。
2. `logos.apply_manual()` 把圖正規化存成 `data/logos/<代號>.png`，索引記 `src: manual`、`manual_sha1`、`source_url`。
3. 之後自動回補**永遠不覆寫、不重抓**這一家。換圖就直接換檔（雜湊變了會重做）。
4. 回補的 commit 只動 `data/`，不會觸發部署；要等下一次 `pages.yml` 部署網站上才看得到。

## 撤掉

刪掉 `data/logos/manual/<代號>.*` 推上去即可：下一輪索引改回 `none`、版號歸零，由自動來源重抓。
