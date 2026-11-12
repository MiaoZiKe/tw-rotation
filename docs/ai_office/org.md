# AI Office 編制與績效規則（2026-11-12 第一版）

依據：Andy 2026-11-12「部門可以縮編，就看你先依照你的方式進行」。
原則：**只調整編制，不刪任何定義檔**；被整併的人列「後備」，需要時隨時召回。

## 一、縮編結果：12 個部門 → 11 個部門；在編 43 人＋後備 3 人

| 異動 | 內容 | 理由 |
|---|---|---|
| 比比動畫部併入影音製作部 | `bibi-animator`、`bibi-illustrator`、`bibi-interaction` 編入影音製作部 | 比比 11-02 起不上社群貼文，只剩短影片與站內動畫，需求下降 |
| 3 人轉後備 | `bibi-planner`（企劃交 `animation-director`）、`bibi-review`（品管交 `reviewer`）、`bibi-efficiency`（效率交 `resource-auditor`） | 與現有職務重疊 |
| 設計審查切分 | `product-design-lead` 定方向、`visual-designer` 實作、`art-director` 只審不做 | 三人原本都在判斷好不好看 |
| 效率與資源切分 | `efficiency-planner` 管流程與優先順序；`resource-auditor` 管 Token 與額度 | 避免重複稽核 |
| 完成度核對切分 | `delivery-planner` 排程與批次表；`inspector` 只稽核 | 避免兩人做同一份核對 |
| 新增 | `hr-officer` 人資專員（監察與稽核室） | 績效計算與新人報到原本無人負責 |

## 二、編制表（★ 主管；種族與暱稱為預設，之後可在網頁上改）

| 部門 | 成員：職稱代號／中文職稱／種族／暱稱 |
|---|---|
| 總經理室 | ★ CEO（主 Claude） |
| 資料部 | ★`data-steward` 資料治理／貓頭鷹／阿梟；`data-scraper` 資料抓取／蜘蛛精／織網 |
| 量化研究部 | ★`finance-quant` 金融口徑／矮人／秤老；`smc-technical` 技術分析／精靈／K線；`strategy-backtest` 策略回測／時間旅人／回朔 |
| 產業研究部 | ★`industry-analyst` 產業分析／人類／鏈哥；`semi-chain-analyst` 半導體／機器人／矽仔；`pcb-substrate-analyst` 載板／地精／板叔；`ai-server-analyst` AI 伺服器／雪怪／液冷 |
| 前端工程部 | ★`frontend-ui` 前端／人類／阿版；`mobile-ui` 手機介面／妖精／小屏；`canvas-motion-engineer` 動效工程／光精靈／粒粒；`visual-explainer` 圖解教學／狐狸／解說狐 |
| 設計與繪圖部 | ★`product-design-lead` 設計總監／高等精靈／格線；`visual-designer` 美編／蝴蝶仙子／色票；`tech-illustrator` 機構繪圖／矮人／剖面；`art-director` 視覺審查／孔雀／鷹眼；`mechanical-engineer` 結構審查／機械人偶／螺絲 |
| 社群媒體部 | ★`social-ops-lead` 發文營運／獸人／準點；`tc-channel-lead` 科技透明圈／外星人／透明；`healing-editor` 談晴說礙／幽靈／晴晴；`finance-content-editor` 財經編輯／人類／快訊；`content-planner` 企劃／狸貓／點子；`market-researcher` 市場研調／蝙蝠／聲納 |
| 影音製作部 | ★`animation-director` 動畫導演／龍族／分鏡龍；`storyboard-artist` 分鏡／松鼠／格子；`motion-designer` 動態設計／史萊姆／去背；`video-editor` 剪輯／章魚／八爪；`bibi-animator` 比比動畫／兔子／跳跳；`bibi-illustrator` 比比插圖／倉鼠／毛筆；`bibi-interaction` 比比互動／小機器人／嗶嗶 |
| 商務與上架部 | ★`marketing-strategist` 行銷策略／人類／定價；`payments-billing` 金流／哥布林／收銀；`mobile-release` App 上架／信鴿／送審 |
| 法遵與資安部 | ★`legal-compliance` 法遵／石像鬼／條文；`security-privacy` 資安／忍者／鎖匠 |
| 營運與部署部 | ★`delivery-planner` 交付排程／人類／排排；`deployer` 部署／火箭機器人／上線；`efficiency-planner` 效率規劃／獵豹／捷徑 |
| 監察與稽核室（直屬 Andy） | ★`inspector` 監察委員／天使／明鏡；`reviewer` 審核／老龍／守門；`resource-auditor` 資源稽核／矮人／算盤；`hr-officer` 人資專員／柴犬／阿薪 |
| 後備（留職停薪，可召回） | `bibi-planner` 天竺鼠／比企；`bibi-review` 刺蝟／刺刺；`bibi-efficiency` 螞蟻／省省 |

已知缺口（先不補人，等績效數據出來再判斷）：資料部 2 人、部署 1 人、頻道③沒有負責人。

## 三、績效規則

| 面向 | 權重 | 算法 |
|---|---|---|
| 品質 | 30% | 首次驗收通過件數÷交件數；Andy 每退件一次扣 10 分 |
| 完成率 | 25% | 有完成證據（網址、commit、截圖）的件數÷派工件數 |
| 速度 | 15% | 實際工時÷預估工時的中位數；≤1 滿分，>2 得 0 分 |
| Token 效率 | 15% | 實際用量÷`docs/token_policy.md` 的預算 |
| 可靠度 | 10% | 卡住逾 60 分鐘次數、回報不實次數（不實一次，當週最高 C） |
| 協作與主動 | 5% | 交接齊全、主動抓到別人問題的件數 |

| 等第 | 分數 | 獎勵（辦公室內） | 處置 |
|---|---|---|---|
| S | ≥95 | 金色光環、稀有寵物、靠窗大座位、「本週最佳員工」 | 提示詞列為範本 |
| A | 85–94 | 銀框、寵物、雙螢幕 | 可代理主管 |
| B | 75–84 | 標準座位 | 無 |
| C | 65–74 | 桌上黃色便利貼 | 主管補一條規則 |
| D | 50–64 | 橘燈 | 重點栽培：改提示詞、補「最容易錯的三件事」，觀察兩週 |
| E | 35–49 | 紅燈、移到輔導區 | 降載、拆職責或補人 |
| F | <35 或回報不實兩次 | 座位掛「停職」牌 | 汰換（需 Andy 點頭） |

- 用絕對門檻，不做強制比例。
- 當週少於 3 件標「樣本不足」不給等第；缺資料的面向標「未量測」。
- 每週一固定評；Andy 說「審查」即時評近 7 天。
- 三方出數據：`reviewer` 品質、`resource-auditor` Token 與速度、`inspector` 完成率與不實；`hr-officer` 彙整。
- 迴避：稽核室四人互評；CEO 由 `inspector` 評並直送 Andy；主管不評自己部門。

人太少還是能力問題，依序判斷：
1. 同時在手超過 3 件，或排隊等待佔工時 40% 以上 → 人力問題，補人或拆職責。
2. 負載正常但退件集中同一類 → 規則問題，補提示詞。
3. 補過規則兩週仍 D 以下 → 換模型或汰換。
4. 錯誤來自上游交件 → 記在上游。
