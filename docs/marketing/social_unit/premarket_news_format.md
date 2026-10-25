# 盤前消息資料格式（社群盤前貼文 → 網站「精選文章 → 盤前消息」）

每個交易日開盤前，社群盤前貼文挑出最受關注的 5 則消息，同一份也寫進網站。

## 單日 JSON

```json
{"date": "2026-10-27",
 "items": [{"cat": "總經", "title": "標題", "url": "https://…", "source": "鉅亨", "time": "2026-10-24T08:50:02+08:00"}]}
```

- `date`：貼文對應的台股交易日（ISO）。
- `cat`：只能是 新聞／事件／科技／總經。
- `url`：http(s) 連結；沒有就留空字串（網頁顯示成純文字、複製時不附連結）。

## 寫入方式

`python -m pipeline.premarket_news <單日.json>` → 合併進 `site/articles/premarket.json`（新到舊、同日覆蓋、保留 60 天）。
寫完要 commit 該檔；網站不需要重算，Pages 部署後即可讀到。
