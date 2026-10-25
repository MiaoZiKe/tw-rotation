# 科技透明圈 資料格式（site/tc/data/<產業id>.json）

一個產業一個檔，收集單位各寫自己的檔，前端只讀不改。

```json
{
  "industry": "foundry", "name": "IC 晶圓代工", "updated": "2026-10-25",
  "window": "2025-10-25～2026-10-25",
  "companies": [{
    "name": "台積電", "code": "2330", "heat": "Dcard 熱度：高／中／低",
    "benefits": "福利重點一句", "stock_plan": "員工認股／持股信託說明",
    "bonus_timing": "分紅發放月份", "culture": "風氣一句（評價摘要）",
    "interview": "面試流程一句",
    "roles": [{
      "unit": "單位（例：晶圓廠 Fab / 研發 R&D）", "role": "職位",
      "degree": "碩士", "years": "0-2",
      "base_month_k": [55, 65],      "bonus_months": [8, 12],
      "annual_months": [20, 26],     "annual_total_wan": [150, 200],
      "weekly_hours": 50, "overtime": "經常／偶爾／幾乎不",
      "travel": "需要／偶爾／不用", "n": 12,
      "note": "落差 1～2 萬疑為學士已排除等",
      "sources": [{"site": "GoodJob", "url": "...", "date": "2026-09"}],
      "confidence": "高／中／低"
    }]
  }]
}
```
規則：只收近一年（2025-10-25 後）、以碩士為主；數字一律區間；每筆至少一個來源；
GoodJob 為主、Dcard／PTT／其他做交叉比對，對不起來就寫進 note 並降信心度。
只寫「整理後的統計區間」，不轉貼原文、不放發文者帳號。
