# 用 Claude 桌面版＋Andy 的 Chrome 讀 Dcard（科技透明圈補樣本）

為什麼：雲端容器連 Dcard 會被 Cloudflare 擋（10-25 實測 403），我們不繞過防護。
改由 Andy 自己電腦上的 Chrome（他本人登入的瀏覽器），透過「Claude in Chrome」擴充功能，像人一樣逐篇打開文章閱讀。

## 規矩（開工前讀）
- 一篇一篇開，像人在看：每篇停留讀完再開下一篇，一小時不超過約 60 篇；不用程式大量抓、不自動翻頁掃整站。
- 只記：發文日期（頁面上的發文時間）、公司、單位、職位、年資、學歷、底薪、分紅、年薪、工時、加班、出差、自己寫的一句摘要、網址。
- 不截圖、不複製原文、不記發文者帳號。
- 只收 2025-01-01 之後的文章（Andy 10-25 改：2025/01 至今）；格式照 docs/tc/schema.md「逐筆樣本」，date_confirmed=true（頁面上親眼看到日期）。

## 給桌面版 Claude 的開工指令（Andy 貼上即可）
> 請用 Claude in Chrome 在我的 Chrome 開新分頁，到 Dcard 科技業版（https://www.dcard.tw/f/tech_job）搜尋「台積電 offer」「聯發科 offer」等關鍵字，
> 照 https://github.com/MiaoZiKe/tw-rotation/blob/claude/adoring-turing-zpjqap/docs/tc/desktop_dcard_runbook.md 的規矩逐篇閱讀，
> 每讀完 20 篇，把樣本整理成 JSON 陣列貼在對話裡給我（格式見同一個 repo 的 docs/tc/schema.md「逐筆樣本」）。
> 我會把它轉貼回雲端那個對話，由雲端的 CEO 併進 site/tc/json/。
