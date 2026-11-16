# AI Office 與「3D 經營／收集／冒險類遊戲」基礎設定落差清單（2026-11-16）

Andy 原話：「幫我去看看這類 3D 遊戲、冒險類的，像是幻獸帕魯，有什麼基礎設定需要具備，列清單給我，我這邊缺乏什麼」。

原則：只參考**機制類型**，不抄任何遊戲的名稱、角色、美術。
「現況」是快速掃 `site/office/world/js/` 檔名與關鍵字、`docs/ai_office/plan.md` 得出的判斷，不是逐行稽核；標「部分有」的請負責人開工前再確認。
工時是粗估（一人、含驗收），區間寫大一點。

## 一、研究摘要（只引搜尋摘要內容）

- **幻獸帕魯類（據點＋自動工作）**：角色有多種「工作適性」且各有等級，非適性工作效率大降或不做；有角色能替整個據點加成某項適性；工作會降低「理智（SAN）」，低理智會休息、拒工、暴食、生病、工作速度減半；飢餓、床位、過勞、受傷都會讓工人停工；食物品質影響休息時間與數值下降速度；被動詞條（如工匠 +50% 工作速度）疊在適性上。進度靠升級拿科技點解鎖建築的科技樹，另有繁殖。
- **Two Point Hospital（經營）**：員工有最多五個永久特質（例如暴躁：快樂 −10%；有潛力：學習 +50%），快樂度與體力以百分比顯示、滑鼠停留看精確值；休息室恢復兩者，也可用咖啡、能量飲料撐；訓練室可學技能（耐力訓練讓體力下降變慢、情緒智商永久 +10% 快樂）。
- **Stardew Valley／Animal Crossing／The Sims（生活模擬）**：核心是簡單可重複的每日循環，早期體力與時間緊，後期靠升級工具與自動化（灑水器）變順；收集圖鑑（博物館、魚蟲化石）是主要長期目標；The Sims 的核心是照顧需求（睡、吃）到智力與職涯發展；評論以自我決定理論（勝任感、自主、關係）解釋這類遊戲的吸引力。
- **Dinkum**：四季各 28 天，作物、魚、生物依季節出現，島上溫度有差異；睡覺才存檔。
- **Craftopia（同開發商）**：主打所有採集與建造都能自動化、輸送帶工廠；多人連線評價兩極（有人說穩，有人說常斷線、最佳化差）。

## 二、必備基礎設定 × AI Office 現況對照

圖例：✅ 已有｜🟡 部分有｜❌ 沒有。優先度：高／中／低。

| 類別 | 項目 | 現況 | 對 AI Office 的意義 | 優先度 | 粗估工時 |
|---|---|---|---|---|---|
| 角色與成長 | 等級／經驗值 | 🟡（績效等第 S～F、設備等級，沒有個人經驗條） | 每位 Agent 完成任務累積經驗、升級解鎖外觀或能力 | 高 | 1～2 天 |
| 角色與成長 | 工作適性（多項＋等級） | ❌ | ＝Agent 專長（寫程式／研究／美術／測試…），派工時看適性，錯配效率打折 | 高 | 2～3 天 |
| 角色與成長 | 個性詞條（永久特質） | 🟡（有情緒與台詞，未見固定詞條） | 「細心：品質＋」「急性子：速度＋品質−」，讓每隻有記憶點 | 高 | 1～2 天 |
| 角色與成長 | 體力／心情／壓力（理智）數值 | 🟡（情緒有，未見會下降、會影響效率的數值） | 連續工作壓力上升→效率降、要去泳池／運動場恢復，休閒區才有意義 | 高 | 2～3 天 |
| 角色與成長 | 飢餓／餐點 | ❌ | 茶水間、午餐時段；可做成「Token 預算＝餐點」的隱喻 | 中 | 1～2 天 |
| 角色與成長 | 訓練／技能樹 | ❌ | 訓練室提升 Agent 適性等級 | 中 | 2～3 天 |
| 工作分派與自動化 | 工作站與派工 | ✅（對話框下指令、新專案區塊、拎起員工） | 已是核心 | — | — |
| 工作分派與自動化 | 依適性自動派工／排班 | ❌ | 無指令時自動挑最適 Agent，CEO 只管例外 | 高 | 2～4 天 |
| 工作分派與自動化 | 產線／依賴鏈視覺化 | 🟡（專案區塊有，未見任務流向） | 任務從研究→開發→測試傳遞，像輸送帶看得到在誰手上 | 中 | 3～5 天 |
| 工作分派與自動化 | 據點加成角色（帶隊增益） | ❌ | 主管 Agent 在場時部門效率＋ | 低 | 1 天 |
| 收集與圖鑑 | 角色圖鑑 | 🟡（有名冊 roster、新角色 newchar） | 「已招募／未解鎖」角色圖鑑＋外觀收集 | 中 | 1～2 天 |
| 收集與圖鑑 | 配件／家具收集 | 🟡（獎勵層有配件） | 完成里程碑掉落可擺放的裝飾 | 中 | 2 天 |
| 建造與擺放 | 自由擺放家具／區塊 | 🟡（整修模式） | 補格線吸附、旋轉、復原、預覽碰撞 | 中 | 2～3 天 |
| 建造與擺放 | 科技樹解鎖建築 | ❌ | 專案完成數解鎖新設施（會議室、訓練室） | 中 | 2～3 天 |
| 世界 | 日夜 | ✅（daytime.js） | — | — | — |
| 世界 | 天氣 | ❌ | 雨天窗外下雨、晴天戶外運動場人多；純氣氛也很加分 | 中 | 1～2 天 |
| 世界 | 季節／節日 | ❌ | 每月換季裝飾、節日活動（尾牙、聖誕） | 低 | 2～3 天 |
| 世界 | 戶外／地形 | 🟡（outside.js、泳池、運動場） | — | 低 | — |
| 互動與物理 | 拎起、物理、火焰傳火 | ✅（phys.js、fire.js） | — | — | — |
| 互動與物理 | 角色之間的互動（聊天、合作、爭執） | 🟡（有台詞與會議） | 好友度、同組默契加成 | 中 | 2～3 天 |
| 經濟與資源 | 貨幣／預算 | ❌ | 用真實 Token 用量當「預算」，花在設施升級；兼具用量控管意義 | 高 | 2～3 天 |
| 經濟與資源 | 資源與庫存 | ❌ | 可省略或極簡（避免變成生存遊戲） | 低 | — |
| 任務與目標 | 主線目標／里程碑 | 🟡（專案本身是目標，沒有遊戲化里程碑） | 「本週完成 5 件」「零退件 3 天」這類短目標 | 高 | 1～2 天 |
| 任務與目標 | 每日循環（早會→工作→下班結算） | 🟡（有日夜與時間） | 每天結束一張「今日結算」卡，形成回訪理由 | 高 | 1～2 天 |
| 社交與多人 | 多人／參觀他人辦公室 | 🟡（multi.js、一專案一間辦公室） | 分享唯讀連結參觀、訪客按讚 | 中 | 3～5 天 |
| 存檔與進度 | 存檔 | 🟡（localStorage 為主，雲端未見） | 對外販售需雲端存檔、換裝置延續、版本遷移 | 高 | 3～5 天 |
| 鏡頭與操作 | 俯瞰／角色視角、提示 | ✅（pov.js、camhint.js） | 補鍵位設定、手把可選 | 低 | 1 天 |
| 音效音樂 | 背景音樂、音效 | 🟡（僅少量檔案用到聲音） | 敲鍵盤、完成任務叮一聲、日夜換曲；附音量／靜音 | 中 | 2～3 天 |
| 新手引導 | 首次教學 | ❌（只有鏡頭小提示） | 第一次進來 5 步引導：看角色→下指令→看結果→績效表→整修 | 高 | 1～2 天 |
| 成就 | 成就／徽章 | ❌ | 「第一次傳火」「首個 S 級員工」，連動公告 | 中 | 1～2 天 |
| UI/HUD | 狀態面板（數值條、名牌） | 🟡（名牌、資訊卡、績效總表） | 補「目前誰卡住／誰閒置」的總覽 HUD 與通知中心 | 高 | 1～2 天 |
| 效能與設定 | 畫質、FPS 上限、低階模式 | 🟡（有效能優化批次，未見使用者設定頁） | 設定頁：畫質三檔、陰影、粒子、聲音、語言 | 中 | 1～2 天 |
| 效能與設定 | 4 倍速／時間控制 | ✅ | 補「暫停」 | 低 | 0.5 天 |

## 三、最建議先補的前 10 項

1. **工作適性＝Agent 專長**（派工依據，整個系統的骨幹）
2. **體力／壓力數值會影響效率，休閒設施能恢復**（讓泳池、運動場從裝飾變機制）
3. **個性詞條**（每隻有固定特質，記憶點＋策略性）
4. **等級與經驗值**（長期成長感）
5. **依適性自動派工**（自動化，CEO 只處理例外）
6. **每日結算卡＋短期里程碑**（回訪理由）
7. **新手引導 5 步**（對外販售必備）
8. **總覽 HUD／通知中心**（誰卡住、誰閒置一眼看）
9. **雲端存檔與版本遷移**（付費產品必備）
10. **Token 預算當遊戲內貨幣**（同時解決用量控管）

## 四、查過的關鍵字與來源

關鍵字：
1. `Palworld base work suitability pals hunger sanity SAN mechanics`
2. `Palworld official pocketpair features base building breeding technology tree`
3. `Two Point Hospital staff traits training happiness energy mechanics`
4. `The Sims needs moods skills autonomy; Stardew Valley Animal Crossing core loop review collection museum`
5. `Dinkum Craftopia review automation seasons weather multiplayer save`

來源（官方／商店頁、wiki 與資料站、媒體與玩家評論三類都有；沒搜到 Pocketpair 官方頁面，帕魯官方以 Steam 同開發商商店頁為間接參考）：
- 官方／商店：<https://store.steampowered.com/app/1307550>（Craftopia）、<https://store.steampowered.com/app/1062520/Dinkum/>
- Wiki／資料站：<https://palworld.wiki.gg/wiki/Work_suitability>、<https://paldb.cc/Sanity>、<https://palworld.wiki.gg/wiki/Structure>、<https://two-point-hospital.fandom.com/wiki/Staff>、<https://www.ludo.guide/guide/two-point-hospital/staff-traits>、<https://guildorder.com/games/palworld/wiki/technology-tree>
- 媒體／攻略：<https://www.corrosionhour.com/palworld-how-to-manage-work-pals/>、<https://nerdschalk.com/palworld-pal-sanity-guide-worker-condition-rest-setup-and-saving-sanity/>、<https://windowscentral.com/gaming/palworld-breeding-guide-how-to-use-egg-incubators-and-create-fusion-pals>、<https://www.nintendolife.com/news/2021/03/soapbox_why_do_people_love_games_like_stardew_valley_and_animal_crossing>、<https://digitaltrends.com/gaming/best-games-like-animal-crossing/>、<https://gameplay.tips/guides/2894-two-point-hospital.html>、<https://twinfinite.net/?p=376673>
- 玩家評論：<https://vaporlens.app/app/1307550/craftopia>（Steam 評論彙整）、<https://steamcommunity.com/app/535930/discussions/0/2692512878715223333>、<https://mein-mmo.de/en/new-co-op-game-conquers-steam-with-95-positive-reviews-reminds-of-animal-crossing,854703>

信心提醒：帕魯的數值（適性等級上限、詞條百分比）各攻略說法不一，本文只取「機制存在」不取數字；The Sims 需求系統的搜尋結果偏薄。
