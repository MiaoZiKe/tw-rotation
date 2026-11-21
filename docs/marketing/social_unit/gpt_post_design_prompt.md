# 給 GPT 的社群貼文設計提示詞（2026-10-26，Andy：「GPT 對於貼文設計這塊有比較好的優勢，所以給我提示詞…風格企業專業點，顏色可以稍微豐富點，並且文字不能歪七扭八」）

- 建議要 GPT 用「單一 HTML＋內嵌 CSS／SVG」產出版型（文字清楚、可直接移植到 scripts/social_snap.py／social_premarket.py）；直接畫圖時中文常變形。
- 自動發文仍由本站管線負責（GPT 不能每天抓資料、發文）；GPT 只負責版型與範例。
- 完整提示詞內容見當日對話（CEO 回覆 Andy 的兩段：HTML 版、圖片版）；硬性規則：亮色 HUD、紅漲綠跌、時段色（盤前琥珀／盤中藍／盤後紫）、圖上不放備註來源網址、日期只在標題列、最小字 24px、限動 1080×1920（上 250／下 230 安全區）、Threads 1080×1350、數字等寬靠右。

## 2026-10-26 補：資料來源段落（Andy：「你也必須告訴他你獲取數據來源是哪裡 怎麼獲取 他才會知道」）
提示詞第五節：盤前（yfinance 美股／ADR／匯率 → intl.json；期交所逐筆＋FinMind 台指期 → index_ohlc／index_intraday；鉅亨 API＋科技新報／udn RSS → news.json；FRED 總經日曆；技術指標自算）、盤中（mis 即時報價經 Cloudflare 代理；rotation／sankey_daily／flow_v3／market_heat／themes／index_intraday／updown）、盤後（FinMind 三大法人首次公布版 → inst_market；個股法人 → inst_today／inst_streak／trust_streak；期交所未平倉與散戶多空比 → market_fut／fut_oi／retail_ratio；證交所融資融券 → market_fut；logos.json）、發布流程（Cloudflare 排程 → GitHub Actions → Playwright 截 HTML → Threads API／IG Graph API）。
