# Threads 排程發文

- 貼文放在 `queue/`，一個檔案一則貼文（或一串）。格式與規則見 `scripts/threads_post.py` 檔頭。
- **只有 `status: approved` 且 `publish_at` 已到的才會發。** `draft` 永遠不會被發。
- 工作流程：`.github/workflows/threads_post.yml`，每 15 分鐘檢查一次；也可在 GitHub → Actions → 「Threads 排程發文」→ Run workflow 手動發。
- 金鑰：GitHub Secret `THREADS_ACCESS_TOKEN`（約 60 天到期；到期前到 Meta 開發者後台「產生存取權杖」換新，貼回同一個 Secret）。
- 發完會自動把檔案改成 `status: posted` 並記下貼文網址；失敗會改成 `status: error` 並寫原因，不會重複發。
- 本機檢查格式：`python scripts/threads_post.py --check`
