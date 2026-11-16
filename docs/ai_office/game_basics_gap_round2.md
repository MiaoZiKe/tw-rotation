# AI Office 第二輪參考研究：經營遊戲、虛擬寵物、虛擬辦公室、AI Agent 可視化（2026-11-16）

> 接續 `game_basics_gap.md`（第一輪）。第一輪前 10 項（已在實作）：①專長 ②體力壓力 ③個性 ④等級 ⑤自動派工 ⑥每日結算＋短期目標 ⑦新手引導 ⑧總覽通知 ⑨雲端存檔 ⑩用量預算。
> 本輪**只講機制**，不抄名稱、角色、美術。來源只引 WebSearch 摘要內容（點不進原文），社群 wiki／廠商自述標註信心度。
> 工時為粗估（1 人日＝一位 agent 約 6 小時），以現有 `site/office/` 架構為前提。

## 一、研究摘要（重點）

- **Pixel Agents**（開源 VS Code 擴充）：讀 Claude Code 的 JSONL 對話紀錄，依工具呼叫切換角色動畫（寫檔＝打字、搜尋＝閱讀、等輸入＝冒泡泡）；子 agent 顯示成跟父角色相連的獨立角色；辦公室佈置跨視窗保存。README 自承「與終端連線不夠穩、會不同步」。→ 是 AI Office 最直接的競品，**我們的差異點必須是「可下指令＋經營層」**，以及把它的痛點（不同步）做穩。
- **AI Town／Generative Agents**：記憶存在模型外，每筆有描述、時間、重要度、最後存取；檢索看「近期＋重要＋相關」；定期「反思」把近 100 筆記憶濃縮成高層洞見寫回記憶。
- **ChatDev**：角色（CEO／CTO／程式／審查／測試）照「階段鏈」協作（需求→寫碼→測試→手冊）；可視化工具分「即時紀錄」「重播」「流程鏈檢視」三種模式；重播只放自然語言對話、不放除錯紀錄。
- **RimWorld**：心情＝基準＋所有「想法」加總，心情條以有上限的速度朝目標移動；想法來自需求與事件，有過期時間；長期低落會離開。
- **Software Inc.**：每位員工兩個個性特質影響數值；團隊個性相容性；玩家抱怨「技能不太會因做專案成長」、學習曲線陡。
- **Prison Architect**：藍圖式規劃（先畫後蓋）、管理深度受好評，但選單複雜、教學不足被批評。
- **Neko Atsume／Tamagotchi**：「約定時間回來」機制；Neko Atsume 是「離開時也有進展」，回來看誰來過、留下禮物；懲罰很輕（碗空了貓就不來），不靠罪惡感。
- **Habitica**：小隊共打 Boss，靠完成每日任務扣血；有人漏做全隊受傷；免費＋約 5 美元／月付費。評論：新手花太多時間搞懂系統。
- **WorkAdventure／Kumospace／Gather 類**：空間式辦公室（走近就能對話、區域＝會議室）、白板、螢幕分享；Kumospace 2022 年募得 2,100 萬美元 A 輪 —— 證明「虛擬辦公室」是有人付費的品類。

## 二、參考對象 × 可搬機制

圖例：重複＝與第一輪前 10 項重疊（僅列補強點）；優先度 高／中／低；販售價值：留＝留存、付＝付費理由、碑＝口碑／社群傳播。

### A. 遊戲

| 參考 | 機制 | 對 AI Office 的意義 | 重複? | 優先 | 工時 | 販售價值 |
|---|---|---|---|---|---|---|
| Game Dev Tycoon／Mad Games Tycoon（同類共通機制，Game Dev Tycoon 本身未查到摘要，信心低） | 成品「評分卡」 | 每件派工完成後給一張成績單（花費 token、耗時、測試是否通過、被退回次數），累積成角色履歷 | 新（⑥結算是日彙總，這是單件） | 高 | 1.5 | 留、碑（可截圖分享） |
| 同上 | 研究點／科技樹 | 完成任務得點數，解鎖新家具、新工作站（＝新的 skill／工具權限捷徑） | 新 | 中 | 3 | 留、付 |
| Software Inc. | 團隊相容性 | 把常合作的兩位 agent 排同組有加成（實際意義：同一條任務鏈共用上下文，降低重複說明成本），畫面上顯示「默契值」 | 補強③個性 | 中 | 2 | 留 |
| Software Inc.（反面教材） | 技能要隨做事成長 | 玩家抱怨技能不成長；④等級要綁「實際完成的該類任務數」，不是時間 | 補強④ | 高 | 0.5 | 留 |
| Prison Architect | 藍圖先規劃後執行 | 使用者先在辦公室裡「畫」一條任務流程（誰→誰→誰），確認後才真正派給 Claude 執行；可存成範本 | 新 | 高 | 4 | 付（範本＝進階功能） |
| Prison Architect（反面教材） | 選單太複雜 | 進階設定一律收在第二層，第一屏只有「派工」「看進度」 | 補強⑦ | 中 | 0.5 | 留 |
| RimWorld | 心情＝想法加總、有過期時間 | 壓力不是單一數字，而是一串可讀的原因（「連續被退件 −8，剩 2 小時」「剛完成大任務 +5」），使用者看得懂為什麼 | 補強② | 高 | 1.5 | 留、碑 |
| RimWorld | 數值漸變、不瞬跳 | 心情／體力條以上限速率移動，畫面更自然、避免閃爍 | 補強② | 低 | 0.3 | — |
| RimWorld | 敘事者／隨機事件 | 每天一則小事件（「咖啡機壞了」「有人生日」），純表演不影響真實派工，增加回訪話題 | 新 | 中 | 2 | 留、碑 |
| Oxygen Not Included（本輪未查到摘要，依一般認知，信心低） | 優先度格子表 | 一張表：橫軸 agent、縱軸工作類型，格子 1～9 調優先 —— 給⑤自動派工一個看得見、可手調的面板 | 補強⑤ | 高 | 2 | 付（重度使用者） |
| Big Pharma（未查摘要，信心低） | 產線串接 | 任務輸出自動流向下一位 agent（寫碼→審查→測試），與 Prison 藍圖合併做 | 併入藍圖 | — | — | — |
| Theme Hospital／雙點醫院類 | 房間＝功能 | 「會議室」放兩位以上＝開審查會、「測試室」＝跑驗收；房間決定 agent 做什麼 | 新 | 中 | 3 | 碑 |
| Tamagotchi | 約定時間回來 | 長任務預估完成時間，到點推播「XX 做好了，來驗收」 | 補強⑧ | 高 | 1 | 留 |
| Neko Atsume | 離線也有進展＋回來看禮物 | 使用者離開期間完成的任務，回來時用「桌上的成品包」呈現，一個一個打開看（附評分卡） | 新 | 高 | 1.5 | 留、碑 |
| Neko Atsume | 輕懲罰 | 太久沒來不會「角色死掉」，只是辦公室變安靜；避免罪惡感型留存（付費產品長期口碑較好） | 設計原則 | 高 | 0 | 碑 |
| Neko Atsume | 收集圖鑑 | 稀有「訪客」或角色姿勢隨條件出現（例如連續 7 天交付），圖鑑可分享 | 新 | 低 | 2 | 碑、付（外觀） |
| Habbo（未查摘要，信心低） | 房間裝潢＋外觀商店 | 家具與外觀是最自然的付費點，不碰功能公平性 | 新 | 中 | 3 | 付 |

### B. 專案／產品

| 參考 | 機制 | 對 AI Office 的意義 | 重複? | 優先 | 工時 | 販售價值 |
|---|---|---|---|---|---|---|
| Pixel Agents | 依工具呼叫切動畫 | 讀 Claude 的對話紀錄把「讀檔／寫檔／跑指令／等輸入」對應到角色動作 —— 這是「真實派工可視化」的核心，必須做到 | 新（核心） | 高 | 3 | 留、碑 |
| Pixel Agents | 子 agent 連線顯示 | 主 agent 派出子 agent 時，畫面長出新角色並以線連回主角色，結束後走回去 | 新 | 高 | 2 | 碑 |
| Pixel Agents（痛點） | 同步不穩 | 做「連線健康燈」與自動重連；不同步時角色顯示「失聯」而不是假裝在工作 | 新 | 高 | 1.5 | 付（穩定是付費理由） |
| AI Town／Generative Agents | 記憶串流＋重要度 | 每位 agent 有「記事本」：自動摘要做過什麼，使用者可看、可釘選重要記憶，下次派工帶入 | 新 | 中 | 3 | 付 |
| AI Town | 反思 | 每天把當日工作濃縮成 3 句「心得」顯示在角色頭上／日報 | 補強⑥ | 中 | 1 | 留、碑 |
| ChatDev | 階段鏈 | 任務照「需求→實作→審查→測試」走，畫面顯示目前在哪一站 | 併入藍圖 | 高 | 含藍圖 | 付 |
| ChatDev | 重播模式 | 任務做完可「重播」：角色依時間軸重演，只放自然語言摘要不放雜訊紀錄 | 新 | 中 | 2.5 | 碑（可錄影分享） |
| ChatDev | 流程鏈檢視 | 一張流程圖看整條任務鏈與每站耗時 | 新 | 低 | 1.5 | 付 |
| Gather／WorkAdventure／Kumospace | 空間互動＝走近即對話 | 使用者的化身走到某 agent 桌邊就開啟對話框下指令，比選單直覺 | 新 | 中 | 2 | 碑 |
| 同上 | 多人同空間 | 團隊方案：同一間辦公室多位真人看同一批 agent（唯讀＋擁有者可下指令） | 新 | 中 | 5 | 付（團隊方案主力） |
| 同上 | 白板／公告欄 | 辦公室牆上的待辦白板＝任務佇列，可拖拉排序 | 補強⑤ | 中 | 1.5 | 留 |
| Habitica | 小隊共打 Boss | 把一個大專案包裝成「Boss」，各 agent 完成子任務就扣血；進度條直觀、好截圖 | 新 | 中 | 1.5 | 留、碑 |
| Habitica（反面教材） | 新手被系統淹沒 | 遊戲化層要能一鍵關閉（「純工作模式」），給只想派工的付費用戶 | 補強⑦ | 高 | 0.5 | 付（降低流失） |
| Habitica | 免費＋小額月費 | 基本免費、月費解鎖外觀與進階面板，定價可參考 | 定價參考 | — | — | 付 |
| GitHub 貢獻圖（未查摘要，依一般認知） | 連續交付熱力圖 | 辦公室入口一張「每日交付格子圖」，連續天數＝輕量連續紀錄 | 新 | 中 | 1 | 留、碑 |

## 三、第二批建議前 10 名

依「核心差異 > 留存 > 付費理由 > 工時」排序，均不與第一輪前 10 項重複（補強項另列在第四節）。

| 名次 | 項目 | 來源參考 | 為什麼 | 工時 |
|---|---|---|---|---|
| 1 | 真實工具呼叫 → 角色動作對應 | Pixel Agents | 「看得到 Claude 真的在做什麼」是產品本體；競品已有，沒有就沒得賣 | 3 |
| 2 | 子 agent 長出新角色並連線 | Pixel Agents | 多 agent 是我們的賣點，最有畫面感 | 2 |
| 3 | 連線健康燈＋失聯顯示＋自動重連 | Pixel Agents 痛點 | 競品自承不同步；穩定就是付費理由 | 1.5 |
| 4 | 單件成績單（耗時／token／退件／測試） | Game Dev Tycoon 類 | 每次交付都有回饋，可分享 | 1.5 |
| 5 | 離開期間的成品包＋到點提醒 | Neko Atsume／Tamagotchi | 最強的回訪理由，且不靠罪惡感 | 2.5 |
| 6 | 藍圖式任務流程（階段鏈）＋存範本 | Prison Architect／ChatDev | 從「看」升級成「規劃」，進階付費主力 | 4 |
| 7 | 優先度格子表（agent × 工作類型） | Oxygen Not Included | 讓自動派工可手調、可理解 | 2 |
| 8 | 可讀的壓力／心情原因清單（會過期） | RimWorld | 把數值變成故事，使用者看得懂 | 1.5 |
| 9 | 任務重播（自然語言時間軸） | ChatDev | 可錄影分享＝口碑；也是除錯工具 | 2.5 |
| 10 | 「純工作模式」一鍵關遊戲化 | Habitica 反面教材 | 防止重度付費用戶嫌吵而流失 | 0.5 |

合計約 21 人日。次選（下一批）：團隊多人同空間（5）、agent 記事本記憶（3）、外觀／家具商店（3）、Boss 化專案進度（1.5）、每日小事件（2）、交付熱力圖（1）。

## 四、對第一輪前 10 項的補強建議（不另開項目）

- ②體力壓力：改成「原因清單＋過期時間」，數值漸變（RimWorld）。
- ③個性：加「團隊默契」（Software Inc.）。
- ④等級：必須綁該類任務實際完成數，不綁時間（Software Inc. 玩家抱怨）。
- ⑤自動派工：配優先度格子表與白板佇列。
- ⑥每日結算：加「今日 3 句心得」（AI Town 反思）。
- ⑦新手引導：進階設定收第二層（Prison Architect、Habitica 都被批複雜）。
- ⑧總覽通知：加長任務到點提醒（Tamagotchi）。
- 設計原則：輕懲罰、不靠罪惡感（Neko Atsume）。

## 五、查過的關鍵字與來源

關鍵字（8 組）：
1. Pixel Agents VS Code extension Claude Code animated characters office
2. Software Inc game employee mechanics skills specialization review
3. AI Town generative agents a16z memory reflection replay
4. RimWorld mood thoughts mechanic Oxygen Not Included priorities stress morale
5. Neko Atsume Tamagotchi retention mechanics come back later gifts
6. Habitica gamified todo streaks party boss review
7. Gather WorkAdventure Kumospace virtual office features
8. Game Dev Tycoon review score feedback research points Prison Architect reports planning
9. ChatDev MetaGPT visualization agents company roles chat chain replay

來源類型：
- 官方／一手：github.com/pablodelucca/pixel-agents、Steam 商店頁（Software Inc.）、softwareinc.coredumping.com（開發者更新）、workadventu.re FAQ、kumospace.com blog、ChatDev repo wiki、IBM ChatChain 教學。
- 媒體／資料平台：deeplearning.ai The Batch（Generative Agents）、a16z podcast、gamedeveloper.com（約定時間機制）、TechCrunch（Kumospace 募資）、OpenCritic／Gamepressure（Prison Architect）、TechRadar／MakerStack（Habitica）、MobyGames、ucstrategies.com（Pixel Agents 報導）。
- 玩家／使用者評論與社群：rimworldwiki.com（心情、想法）、TV Tropes（Neko Atsume）、reddit r/nekoatsume、Steam 使用者評論（Software Inc.）、Metacritic 使用者分數。

查不到／低信心：Game Dev Tycoon、Oxygen Not Included、MetaGPT、Big Pharma、Habbo、Startup Company 本輪搜尋摘要沒有回到，表中相關機制依一般認知撰寫、已標低信心，實作前宜再查。
