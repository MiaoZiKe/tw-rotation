# 送審錄影腳本（四帳號版，2026-11-20）

沿用 `tc/app_review/README.md` 第三節，改為四帳號、補上 Instagram 登入授權畫面。長度約 3～4 分鐘；電腦錄螢幕（含滑鼠），全程加英文字幕。審核員要看到「**登入鈕可見、授權、留言、收到私訊、回覆、收到內容**」。
前置：帳號 B＝另一個測試用 IG 帳號（開發模式下需先加成 Instagram Tester；審過後一般帳號即可）。**錄影前 inspector 先確認每段畫面真的做得到，再錄。**
舞台帳號：A＝Tech_01010909（示範用）；其餘三個在片段 8 帶過。

| 段 | 約秒 | 畫面 | 動作 | 英文字幕 |
|---|---|---|---|---|
| 1 | 0–10 | App Dashboard → Settings → Basic | 停 3 秒，顯示 App 名稱 LIGULIGU Aito Post、隱私權政策網址、資料刪除網址 | "One app manages four Instagram accounts that we own." |
| 2 | 10–30 | API setup with Instagram login 頁 | 顯示已授權的四個帳號（不露權杖）；按「Add account」示範 Instagram 登入授權畫面，勾選權限並同意 | "The account owner logs in with Instagram Login and grants the permissions." |
| 3 | 30–50 | 帳號 B 開啟帳號 A 的貼文 | 看到貼文說明裡的關鍵字，留言該關鍵字 | "A user comments the keyword stated in our caption." |
| 4 | 50–70 | 我們的日誌（GitHub Actions run log，已遮罩） | 顯示讀到該則留言（只顯示雜湊與處理結果，無明文） | "The app reads the comment on our own media (instagram_business_manage_comments)." |
| 5 | 70–100 | 帳號 B 的 IG 私訊匣 | 收到私訊（留言私回）；回覆一句 | "The app sends one private reply; the user replies (consent)." |
| 6 | 100–130 | 帳號 B | 先不追蹤直接回 → 收到提醒；追蹤後再回 → 收到內容與網站連結 | "We check whether the user follows us, then send the requested summary." |
| 7 | 130–155 | 帳號 A 的貼文留言區與私訊 | 示範在 Instagram 原生 App 刪除該則留言（留言權限 Meta 會要求看建立／更新／刪除） | "Comment management shown in both our app log and native Instagram." |
| 8 | 155–180 | GitHub 上四個頻道的 dm_config.json | 捲過 keywords、每日上限、max_per_run | "The same logic runs for our four own accounts, with per-user limits." |
| 9 | 180–200 | https://liguligu-puipui.com/#data-deletion | 捲到資料刪除說明 | "Users can request data deletion here." |

規矩（影片也要遵守 CLAUDE.md）：畫面元素不重疊；字幕不壓住重點；**不露權杖、不露任何金鑰**。錄完存 MP4（≤ 100MB 以畫面為準），在每個權限各上傳一次（同一支可）。
送審平台若要求「留言權限示範建立／更新／刪除留言」而我們的功能不含發留言，**照實說明**並在片段 7 示範刪除（📷 送審頁的錄影要求原文請截圖給我核對）。
