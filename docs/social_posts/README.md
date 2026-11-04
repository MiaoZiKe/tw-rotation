# 貼文專區

每篇以 `YYYY-MM-DD_slug/` 歸檔，主題與來源文章 id 記在 [INDEX.md](INDEX.md)。本機對應 `output/YYYY-MM-DD_slug/`。

```text
YYYY-MM-DD_slug/
  dispatch.md         CEO 派工與八角色安排
  brief.md            研究交接、事實／財測／本站整理／未確認
  sources.md          編號來源、日期、連結與實讀摘要
  slides/01.png …     1080×1350 正式輪播
  caption.md          IG 說明、hashtag、追蹤連結、免責
  threads.md          Threads 文案、追蹤連結、免責
  assets.json         本篇使用素材與來源、版本、父素材
  qa_report.md        逐頁製作單與逐項品管
  backup_status.md    本機、分支／PR、合併狀態、大檔位置
  video/             有要求才做；repo 只放腳本、字幕與合規小檔
```

可重用圖檔歸 [共用素材庫](../social_assets/README.md)，貼文使用 `asset_id`、版本與 repo 相對路徑引用。發文所需最終 PNG 仍留在本篇 slides/，方便一次下載。

狀態用「製作中／待校準／待品管／已通過品管／PR 待合併／已備份」等具體文字；是否已發布另記，不能由備份推定發布。

每次由最新 main 建立 `codex/social-posts-<日期>-<slug>` 分支，提交後開 PR，更新 INDEX.md 的 PR 連結。不直推 main。MP4 或單檔超過 5 MB 不放 repo，記錄本機與 Andy 雲端備份位置；不捏造雲端已備份。

只收可公開內容；金鑰、密碼、個資、持股、成本價不入庫。固定免責：「整理公開資訊，非投顧，投資請自行判斷。」
