# 科技透明圈 資料格式（site/tc/json/<產業id>.json）

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

## mops 欄位（每家公司，2026-10-25 加，法遵：第一版以合法公開來源為主）

```json
"mops": {"year": "114年度", "avg_wan": 446.5, "median_wan": 355.2, "n": null,
         "source": "公開資訊觀測站 非擔任主管全時員工薪資（經媒體報導）", "url": "...", "note": "..."}
```
- 口徑：非擔任主管的全時員工薪資，排除經理人與部分工時；單位萬元／年。不可跟財報「全體員工薪酬」混用。
- 查不到填 null，note 寫查過什麼。`n` 為員工人數，報導沒寫就 null。
- 平台數字（GoodJob 為主，Dcard／PTT 交叉比對）可統計使用，不截圖、不轉貼原文；confidence 依筆數與交叉比對：≥2 筆且近一年＝中，≥5 筆＋兩平台吻合＝高，否則低。mops 當對照。
