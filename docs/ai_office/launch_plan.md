# AI Office System 上線計畫書（提案，2026-11-12）

性質：提案文件，不排工期、不開工。先把功能做完（階段 0～5），再回來決定本書。
標記：【事實】有來源；【判斷】我的建議；信心度 高／中／低。

## 1. 客群與定位

| 項目 | 內容 |
|---|---|
| 客群 | 同時跑多個 Claude Code 子 agent 的獨立開發者、小團隊 |
| 痛點 | 子 agent 在終端機裡看不到誰在做什麼、花多少 Token |
| 定位 | 把你的 AI 團隊變成看得見、養得起來的可愛 3D 辦公室 |

## 2. 競品（WebSearch 查證，摘要只是線索）

| 名稱 | 做法／價格 | 我們的差異 | 信心 |
|---|---|---|---|
| [Pixel Agent Desk](https://github.com/Mgpixelart/pixel-agent-desk)、[Claude Office Visualizer](https://cdn.jsdelivr.net/gh/paulrobello/claude-office@main/README.md)、Pixel Agents、Backstage、PixelPulse | 開源，吃 hooks 或對話檔，2D 像素風，多為本機；皆免費 | 3D 可愛風、雲端多裝置、績效與稽核、寵物 | 中（僅摘要） |
| [Langfuse／LangSmith](https://costbench.com/compare/langfuse-vs-langsmith/) | 觀測平台；Langfuse $0/$29/$199，LangSmith Plus $39/席（第三方彙整，各站不一） | 它們給工程師看 trace，我們給人看「團隊感」 | 中低 |
| [Gather](https://support.gather.town/hc/en-us/articles/39590892978196) | 虛擬辦公室，每人每月 $15（月繳）／$12（年繳） | 它是真人社交；我們是 AI 員工 | 中高（官方頁） |

【事實】競品最大威脅是免費開源的 2D 像素版；付費付的是便利與好看，不是功能。未查到：3D 且收費的同類產品（查過「pixel office」「virtual office」「agent visualization」，不代表不存在）。

## 3. 方案提案（免費 ≤3 agent 為既定）

| | 免費 | 方案 B（建議）Plus | 方案 C Pro |
|---|---|---|---|
| Agent 數 | 3 | 12 | 不限（45+） |
| 專案數 | 1 | 3 | 不限 |
| 歷史保存 | 7 天 | 90 天 | 1 年＋匯出 |
| 績效 S～F／稽核 | 只看當週等第 | 完整報表 | 完整＋週報信 |
| 整修／寵物 | 基本款 | 全部 | 全部＋搶先 |
| 月費／年費 | 0 | NT$149～249／US$5～8；年繳約 8 折 | NT$449～699／US$15～22 |

依據【判斷】：觀測類 $29 起、Gather $12～15 是上限參考；個人開發者願付額低於此。定太高：會輸給免費開源 2D；太低：付不起金流與客服成本。
分層原則：以「規模與時間」分，不砍功能；免費版的績效也能用較慢方法（手動看當週）。
裝飾單次購買：適合（寵物、皮膚 NT$30～90），因不影響核心、可當第一次付費入口；但需先確認金流支援單次收款。

## 4. 成本估算

| 項目 | 數字 | 來源／信心 |
|---|---|---|
| Cloudflare Workers 付費 | 每帳號每月 US$5 起；SQLite 型 Durable Object 含 100 萬請求、25B 列讀 | [官方文件](https://developers.cloudflare.com/durable-objects/platform/pricing)，高（免費方案是否可用 DO，來源互相矛盾，待確認） |
| 儲存 | 約 5GB 內含，超過約 $0.2/GB（第三方，低） | 低 |
| 網域 | 已有 liguligu-puipui.com，子網域 $0 | 高 |

【假設】每位免費使用者每天 8 小時、事件每分鐘約 10 筆、WebSocket 常駐：每月約 40 萬請求。粗估每人每月 US$0.01～0.1（WebSocket 持續時間費是最大未知，需實測）。
損益平衡：固定成本 US$5＋金流抽成約 3%（台灣平台 2.4～3%，來源低信心）。若免費者 1,000 人、成本約 US$50，需約 10 位 Plus（US$5/月）打平。轉換率假設 2～5%。

## 5. 上線前必備（法遵／金流只列要點，須由 legal-compliance、payments-billing 細查）

| 項目 | 要點／待查 |
|---|---|
| 使用條款、隱私權政策 | 會存別人的 agent 對話與回報內容；需資料刪除、保存期限、勿上傳機敏資料警語；個資法適用待查 |
| 金流 | 【事實，信心低】Stripe 對台灣個人說法不一；MoR（Paddle、LemonSqueezy）據稱個人可申請但抽成高；[歐付寶](https://roo.cash/blog/stripe-guide)、藍新、綠界、Recur（封測）待實際核對 |
| 發票與稅 | 個人／公司身分、跨境數位服務營業稅、電子發票：未查到，待細查 |
| 素材授權 | 角色全自製原創；骨架動作用 CC0；音效、字型逐一留授權紀錄 |
| 商標名稱 | 檢索智慧財產局與 USPTO；名稱不得含 Claude／Anthropic |
| Anthropic 相容 | 【事實，信心中】[商標規範](https://www.anthropic.com/legal/trademark-guidelines)摘要：可事實陳述「相容 Claude Code」，不得放進產品名、logo，不得暗示官方或合作；不得提供 claude.ai 登入。全文我未讀到，需細查 |

## 6. 推廣路徑

| 步驟 | 內容 |
|---|---|
| 一行安裝 | 本機外掛兩行裝好，免註冊先看示範 |
| 展示影片 | 30 秒：開會爭執、被打、寵物，走社群短影片 |
| 社群 | GitHub 開源接入包、Hacker News Show HN、Claude Code 相關社群、Threads |
| 底線 | 文案不暗示官方產品 |

## 7. 需要 Andy 決定

| # | 題目 | 選項 | 我的建議 |
|---|---|---|---|
| 1 | 方案數 | A 免費＋一付費／B 免費＋兩付費 | A，先驗證有人付 |
| 2 | 免費上限 | 2／3 agent | 3（CEO 另計，感受較好） |
| 3 | 裝飾單次購買 | 做／不做 | 第二波再做 |
| 4 | 收款身分 | 個人＋MoR／台灣公司 | 先個人＋MoR，有營收再設公司 |
| 5 | 接入包開源 | 開源／閉源 | 開源（對抗免費競品、利於推廣），服務端閉源 |
| 6 | 產品名稱 | 之後提 3 個候選 | 先檢索再定 |

## 8. 沒查到／不確定

3D 收費同類產品；各金流對台灣個人的官方條款；稅務；Anthropic 商標全文；Durable Object 實際用量成本（需實測）；轉換率純假設。
