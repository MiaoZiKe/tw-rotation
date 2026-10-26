# 自動發文格式（Auto Post）—— 以後一律照這份

> 2026-10-26 Andy：「盤中貼文格式都確認 OK，幫我寫進 Auto Post .md 檔案，以後 Follow 這格式」。
> 程式：`scripts/social_snap.py`（盤中／盤後／融資融券）、`scripts/social_premarket.py`（盤前）、`scripts/social_publish.py`（發文）。
> 圖的版型（亮色 HUD、色票、安全邊距）另見 `post_design_system.md`；這份管「發什麼、什麼順序、文案怎麼寫、連結放哪」。
> 改格式要同時改程式與 `tests/test_social_caption.py`，並在這份記一行 Andy 原話。

## 一、四個時段

| 時段 | 發文時間（台北） | Threads 輪播（順序固定） | IG 限動 | 狀態 |
|---|---|---|---|---|
| 盤前 | 08:20 | 美股收盤、台指期＋台積電 ADR、事件與消息、總結 | 同左＋結尾頁 | 版型確認中 |
| 盤中 | **12:00 固定**（資料抓 12:00 那一刻） | ① 資金輪盤 ② 資金分流樹 ③ 資金排行 ④ 熱力圖（**只有這 4 張**） | 同左 4 張＋結尾頁 | ✅ Andy 10-26 確認 |
| 盤後 | 法人資料當天到齊那輪 | ① 三大法人買賣超 ② 外資連續買賣超 ③ 投信連續買賣超 ④ 台指期法人未平倉 ⑤ 散戶多空比 ⑥ 大盤走勢 ⑦ 漲跌家數 | 同左＋結尾頁 | 審核中 |
| 融資融券 | 同一晚、融資資料當天到齊那輪 | ① 融資維持率 ② 融資增減排行 ③ 融券增減排行 | 同左＋結尾頁 | 審核中 |

- 盤中**不放**漲跌家數、大盤走勢（移到盤後）。
- 資料不是當天的就不發（`social_gate.py` 把關；颱風假、補假照 `pipeline/calendar/tw_holidays.yaml`）。

## 二、圖（Threads 與限動共用規則）

1. **滿版**：Threads 1080×1350，外圍只留 20px；限動 1080×1920，上 200px、下 170px 是 IG 介面蓋住的區域，不放字。
2. **圖上不放備註、資料來源、網址、免責**（`andy_ui_rules.md` 第 18 條）。日期只在標題列。
3. 盤中標題列日期寫「MM/DD 12:00」。
4. 元素兩兩不得重疊，程式逐張檢查（`layout_report.json`），有一張重疊就不發。

## 三、Threads 文案（Andy 指定格式）

```
盤中消息
資金輪盤：
・領先 ○○、○○；
・落後 ○○、○○
資金分流樹：
・流入 ○○、○○；
・流出 ○○、○○
熱力圖：
・漲最多 ○○ +x.x%、○○ +x.x%；
・跌最多 ○○ -x.x%、○○ -x.x%
#台股 #資金流向 #熱力圖 #族群輪動
https://liguligu-puipui.com/?utm_source=threads&utm_campaign=intraday_MMDD#flow/rotation
```

規則（盤中、盤後、融資融券一體適用）：
1. 第一行是標題：「盤中消息」「盤後消息」「盤後融資融券」，不帶日期。
2. 每段一行「段名：」，底下每點用「・」開頭；同一段的第一點結尾用「；」。
3. 每點列 **2 個**名稱（盤中）；字數超過 480 字時程式自動縮短。
4. **網址只放最底下一行，整篇只有一個**（10-26 Andy：「連結只需要附在最底下就好」）。網址帶 `utm_source=threads&utm_campaign=<時段>_<MMDD>` 方便看成效。
   - 盤中 → `#flow/rotation`；盤後 → `#market/inst`；融資融券 → `#market/credit`。
5. hashtag 一行，放在網址上面。
6. **不放**「資料：證交所／櫃買公開資料整理，僅供參考，不構成投資建議」這行（10-26 Andy：「底下資訊不用」）。免責放個人簡介與網站。

### 盤後範本
```
盤後消息
三大法人買賣超：
・外資 -815.8億、投信 +94.9億；
・自營 -273.8億、合計 -994.7億
外資：
・買超 ○○、○○；
・賣超 ○○、○○
投信：
・買超 ○○、○○；
・賣超 ○○、○○
台指期法人淨未平倉：
・外資 -87,297 口、投信 +83,601 口；
・自營商 +3,260 口
散戶多空比：
・大台 +0.37%、小台 +33.81%；
・微台 +47.79%
大盤：
・加權收盤 47,111.26（+141.39 +0.30%）；
・上漲 1507 家、下跌 577 家
#台股 #法人買賣超 #投信 #外資
https://liguligu-puipui.com/?utm_source=threads&utm_campaign=close_MMDD#market/inst
```

### 融資融券範本
```
盤後融資融券
融資維持率：
・上市（估算）168.20%，較前日 -1.35pp
融資：
・增加 ○○、○○、○○；
・減少 ○○、○○、○○
融券：
・增加 ○○、○○、○○；
・減少 ○○、○○、○○
#台股 #融資 #融券 #融資維持率 #信用交易
https://liguligu-puipui.com/?utm_source=threads&utm_campaign=credit_MMDD#market/credit
```

## 四、IG 限動

1. **只發圖，沒有文案**（IG 自動發文介面不能替限動加文字）。
2. **不能自動加連結貼紙**：IG 自動發文介面只收圖片或影片，不收連結、投票、提及這類互動貼紙（2026-10-26 查證，見文末來源）。
3. 所以照 Andy 10-26 選的 **C 方案**：每組限動**最後多一張結尾頁**「看完整資料／點個人簡介的連結，進入網站看即時更新」（`social_native.py` 的 `outro`），圖上不印網址。
   個人簡介的連結要設成 `https://liguligu-puipui.com`。
4. 張數與順序跟 Threads 輪播一樣，再加結尾頁。

## 五、發文開關與防重複

- 真的發文要 `docs/marketing/social_unit/LIVE_ENABLED` 這個檔存在；**Andy 說「開始發」才建**。
- 同一時段只發一次：`social-snaps` 分支 `state/posted.json`，盤中鍵 `intraday-YYYY-MM-DD`。
- 準時觸發靠 Cloudflare 排程（`workers/gh-cron`，設定見 `docs/gh_cron_setup.md`）；GitHub 內建排程只當備援。

## 修改紀錄

- 2026-10-26：盤中 4 張與文案格式 Andy 確認；網址只放最底下；限動用 C 方案結尾頁；同一格式套到盤後與融資融券。

來源（IG 限動不能用自動發文介面加連結貼紙）：
- https://storrito.com/resources/instagram-story-api/
- https://support.agorapulse.com/en/articles/9694913-workaround-instagram-stories-with-link-stickers
