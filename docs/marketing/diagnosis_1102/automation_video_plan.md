# 自動發文、半自動、手寫，以及要不要做影片（2026-11-02 台北，行銷與商業策略師）

> Andy 原話：「評估 IG & Thread 自動發文是否都不好，變相說都是可能請 Claude 做完我手動發，還是可以怎麼分類，哪種文章適合自動發文，哪種不適合，並且幫我確認自動發文在什麼情況下還能兼顧流量推播」「還有是否需要搭配影片增加流量」。
> 延伸（不重做）：`strategy_diagnosis.md`（自動文取代手寫是弱點第 1 名）、`viral_research.md`（IG 2026-04 原創／聚合降權、Threads 回覆約占觀看一半）、`channel_playbook.md`（兩頻道頻率與流程）、`etf_content_plan.md` 第五節（半自動三條判準）。
> 讀法：每個結論標「信心：高／中／低」；「事實」與「我的判斷」分開寫；最後有「Andy 可能不同意的地方」與「我沒查到的」。
> 證據限制：本容器只有 WebSearch，只拿得到摘要，**沒有讀過任何原文**；Mosseri 的說法全部是二手部落格轉述，不是他本人的貼文。摘要會自己補出原文沒有的東西，所以外部數字一律是「線索」。

---

## 〇、一頁結論（直話）

1. **自動發文「這個動作」不是問題；問題是「沒有人在場」。** 查不到任何證據顯示用 API／排程工具發文會被降權（Mosseri 被轉述說排程不影響觸及；廠商與評測沒找到懲罰）。但我們 10-27 之後掉 12 倍，原因是內容變成樣板數據摘要、沒有立場、沒人回覆，不是因為按鈕不是 Andy 按的。（信心：中——證據弱，但方向一致）
2. **所以 Andy 的直覺「變相說都是請 Claude 做完我手動發」只對一半。** 對的部分：每篇要有一個真人的立場句與發後回覆。錯的部分：那一下「手動按發」不產生價值，價值在「Andy 看過、加一句、發完在場」。**同樣的價值可以用「Claude 排程、Andy 先核准、系統用 API 發、Andy 發後回覆」做到，省下複製貼上與存圖的時間**（我們的核准佇列 `social/threads/queue/` 的 `status: approved` 機制已經存在，工程量小）。
3. **分三級（B 節有 12 類的完整表）：**
   - ① 全自動：ETF 除息週曆、盤後資金輪動（條件式）——共 2 類。
   - ② 半自動（Claude 起草＋產圖＋Andy 看過加一句再核准）：熱點、ETF 配息試算、歷史統計、產業輪動、知識迷思、新聞財報卡（升級後）、面試職涯、互動提問——共 8 類。
   - ③ 必須 Andy：科技薪資行情、留言回覆——共 2 類。
4. **自動文要兼顧流量，必須同時滿足 5 件事**（C 節）：回答一個讀者會問的問題＋有比較基準的數字＋一句（預先審過的）情境或立場＋發後 60 分鐘內有人回覆＋同質上限。這 5 件事我給了可實作的「自動文品質閘」規格（C-2），未通過的**降級進核准佇列，不是整篇不發**（符合 CLAUDE.md 10-29「不准有條件不符就整段不做」）。
5. **影片：要做，但只有「觸及型 Reels 一週一支、從第 2 週開始」，頻道二不做。** 理由：我們自己的 5 支 Reels 觸及 9～47（共 130），比 IG 動態（中位 0.5～1）高約 20 倍但**基數極小**，且那 5 支都是「功能介紹」——正是診斷說會失敗的內容型態。外部資料（Fanpagekarma，廠商）顯示小帳號 Reels 對非追蹤者觸及約為輪播的近 2 倍，輪播則收藏高；結論是兩者搭配，不是二選一。（信心：中低）
6. **Andy 不露臉可以。** 選項依序：網站螢幕錄影＋數據字卡＋台灣女聲旁白（已有產線，Andy 10-18 規定）→ 用資料湖算出來的圖做動畫（輪動時鐘 ▶ 播放、大跌後走勢線）→ Andy 只出聲音（需他自己同意與錄音）。**查不到台灣「不露臉財經帳號」成功案例的任何量化資料**（只有廠商教學），這是缺口，不是我們沒查。
7. **預期 Andy 每週時間：頻道一約 2.3 小時、頻道二約 2.8～3.5 小時，合計約 5～6.5 小時**（比 `channel_playbook.md` 的 6.5 小時略低，F 節有表）。這是估計，請他校正。

---

## A. 自動發文本身會不會被降權？

先把兩件事分開：**（1）用工具／API／排程發** vs **（2）內容像機器產生**。證據只支持第二件有風險。

### A-1 事實（外部，皆為搜尋摘要，未讀原文）

| # | 事實 | 來源 | 信心 |
|---|---|---|---|
| 1 | 部落格轉述：Mosseri 在 2025-03-29 的 Stories 問答說，使用排程工具發的貼文不會改變觸及（不增也不減）。另一篇稱他 2026-03 重申、2026-08 說排程與手動 Reels 以同樣方式進入排序（**後者只有單一來源**）。**我沒找到他本人的原貼文** | [Kontentino](https://www.kontentino.com/blog/does-scheduling-instagram-posts-hurt-reach/)、[Planoly](https://www.planoly.com/blog/does-scheduling-your-posts-affect-your-post-reach.md)、[Kontentino Q&A](https://www.kontentino.com/q-and-a/does-scheduling-instagram-posts-affect-reach/) | 中低（二手，且廠商有利益） |
| 2 | Kontentino 說回顧 2011 年起 8 份研究都沒發現懲罰；Poster.ly 稱各大平台官方發佈 API「沒有文件記載的演算法懲罰」，但承認「用戶在排程前後的行為」仍會影響（例如沒人在場互動） | [Poster.ly](https://www.poster.ly/blog/does-scheduling-hurt-reach-research) | 低（排程廠商，有立場） |
| 3 | Threads：**找不到任何獨立的 API 發文 vs App 原生發文對照研究**。一家排程廠商（MindThread）自稱 A/B 測試觸及差在 3% 內，無方法、無樣本、無原始資料；Reddit 有人說「排程文差，主因是前 20～30 分鐘沒人互動」，屬個人經驗 | [dev.to 教學](https://dev.to/ppcvote/how-to-schedule-threads-posts-set-up-daily-auto-posting-in-5-minutes-1h0f)、[Sked Social](https://skedsocial.com/blog/schedule-threads-posts.md) | 低 |
| 4 | Instagram 官方創作者頁：**不原創**的內容可能不被推薦給非追蹤者（追蹤者照看）；2026-04-30 起範圍從 Reels 擴大到照片與輪播，滾動計算，停止發不原創內容 30 天後可恢復。浮水印、加速、截圖加註來源仍算不原創 | [IG 原創內容規範](https://creators.instagram.com/original-content-guidelines/)、[IG 推薦與原創](https://creators.instagram.com/recommendations-and-originality)、[IG 官方部落格](https://creators.instagram.com/blog/rewarding-original-creators-on-instagram)、[PetaPixel](https://petapixel.com/2026/04/30/new-instagram-policies-target-reposted-content/) | 中高（官方頁面摘要，我沒讀到 Help Center 本文） |
| 5 | IG 對 AI 的立場：**沒有宣布對 AI 內容的一般性降權**；對「被偵測為 AI 角色／AI 帳號卻沒標示」的帳號，發言人說可能被限制觸及，主動標示者「不受影響」。Mosseri 被轉述：「我們排 AI 內容跟非 AI 內容一樣好嗎？大概沒有」，原因是 AI 內容常被視為低品質。日期各家不一（5 月／8 月 31 日）。**沒有官方的自動偵測文件，也沒有可信的降幅數字** | [Techwyse](https://www.techwyse.com/?p=78112)、[Dataslayer](https://www.dataslayer.ai/blog/is-instagram-penalizing-polished-content-in-2026-yes-heres-what-changed) | 低中 |
| 6 | Threads：Mosseri 被轉述「你所有回覆的總和，大約跟你所有貼文的總和一樣有價值」「想成長，回覆要比發文多」；Meta 官方 2024-10 稱回覆約占 Threads 近一半觀看（`viral_research.md` 已引） | [Postory](https://postory.io/blog/threads-algorithm)、[Meta 公告](https://about.fb.com/news/2024/10/find-your-community-with-new-threads-educational-insights/) | 中（官方＋轉述一致） |

### A-2 事實（我們自己的資料）

| # | 事實 | 信心 |
|---|---|---|
| 1 | 手寫薪資文 4 篇共 74,481 觀看（中位 2,398），自動盤前盤後 15 篇共 1,591（中位 56）；10-27 前 15 篇中位 738、之後 31 篇中位 54（`strategy_diagnosis.md`） | 高 |
| 2 | **這個比較分不開「API vs 手動」**：廣達那篇是 Andy 的文字，但**是用 API 排程發還是用 App 手動貼，我沒查證**（佇列 `social/threads/queue/` 的 manual 機制存在，發布者也是 API）。同時改變的還有內容、頻率、有無回覆。所以**我們的資料不能證明也不能否定 API 降權** | 高（邏輯） |
| 3 | 現況 `post_quota.json`：自動只剩盤後 Threads 1 則／天，手動佇列（Threads、IG）開啟；`news` 佇列關閉 | 高（讀檔） |

### A-3 我的判斷

- **用工具發不是主要風險**（信心：中低）。證據的性質是「查不到懲罰」，不是「證明沒有」；但就算有 3～10% 的差異，也遠小於我們觀察到的 12 倍落差。
- **三個真正會讓自動文變差的機制**（信心：中，皆可在 4 週內用我們的資料驗證）：
  1. **沒人在場**：排程文發出後沒有任何回覆，錯過 Threads 最看重的訊號（A-1 #6）；手動發的優勢只是「發的當下人在場」，不是演算法認得出手指。
  2. **樣板同質**：一天多則相同骨架，觀感是「資訊機器人」，個人頁一打開就看出來（診斷 Q2、Q4）。
  3. **IG 原創度與 AI 標示**：新聞改寫卡屬「重組他人內容」風險區；我們用資料湖自己算的圖屬原創（A-1 #4）。AI 生成的**圖**要不要標示 AI，我沒查到 IG 對「單張 AI 圖」有強制標示規則，只查到針對「AI 帳號／角色」的規則——**比比是卡通角色，是否被判為「AI 角色」未確認**。
- **建議的驗證（便宜）：** 第 1～4 週，同一類 ②（例如 ETF 週曆、輪動）的貼文，單週交替「核准後由 API 發」與「Andy 在 App 手動發」，兩種都由 Andy 在發後 60 分鐘內回覆。每種至少 4 則，比較觀看中位與回覆數。樣本小只能看方向；若 API 組中位低於手動組 30% 以上，就把「手動發」升為預設，否則維持 API。這也同時回答 Andy 的疑問。

---

## B. 內容分類表：全自動／半自動／必須 Andy

分級判準（沿用 `etf_content_plan.md` 5-2 並補強）：
- **① 全自動**：資料是我們獨有或整合過、讀者的問題固定、**不需要立場**、沒有法遵風險句；錯了也不會傷人。
- **② 半自動**：數字可由工具算，但**需要「所以呢」或情境**才有人回；Andy 看過、加（或改）一句、核准。
- **③ 必須 Andy**：價值來自「這個人知道別人不知道的事」或「這個人回你」；機器不能代替。

Andy 每篇分鐘＝**看稿＋加一句＋核准，不含發後回覆**（回覆另計，見 F 節）。估計值，未實測，請校正。

| # | 內容類型 | 級別 | 為什麼 | Andy 每篇分鐘 | 平台 | 信心 |
|---|---|---|---|---|---|---|
| 1 | 盤後資金輪動（現有自動盤後） | **①（條件式，降頻）** | 數據是站內獨有整合，但現實是中位 56、回覆 0。保留當作「個人頁有穩定記錄」與資料沉澱，**不指望它帶量**。升級條件：每篇自動帶出「與近 20 日比」的一個比較基準＋一句**預先審過的規則式解讀**（C-1 第 3 點），否則維持低期待。**頻率降到每週 2 則（見 F）** | 0（每週抽查 5 分鐘） | Threads | 中 |
| 2 | 熱點解讀（大跌、FOMC、Intel 等） | **②（快版）** | 讀者要「所以呢」與立場；有時效、法遵最敏感（不預測、不報明牌）。Claude 當日給數據＋歷史對照＋骨架稿，Andy 加一句看法並核對；**不能全自動**，因為沒有立場的熱點文已在 10-29／10-30 驗證會失敗（最好 458） | 10（快版）～20（深版） | Threads；IG 輪播擇優 | 中高 |
| 3 | ETF 除息週曆 | **①** | 純事實、固定欄目、讀者固定問題（「這週哪幾檔除息」）。對策：一則一個發現、預估日標「預估」、版型輪替。IG 輪播版當收藏型 | 0（每月抽查 10 分鐘） | Threads＋IG 輪播 | 中 |
| 4 | ETF 配息試算（月領 N 元要幾張） | **②** | 數字全由工具算；但「朋友問我」包裝與「不是保證月領」措辭要人看，違規句最易出現在這類 | 8 | Threads＋IG 輪播 | 中 |
| 5 | 歷史統計（大跌後走勢） | **②** | 資料湖 26 年指數，**我們自己算、讀者可重現**，是稀缺性來源；但結論句容易越過投顧法（預測），須人核對定義與措辭 | 12～15 | Threads＋IG 輪播＋影片 | 中高 |
| 6 | 產業輪動 | **②** | 網站資料帶入，但要有「我的觀察」一句才有人回 | 10 | Threads＋IG | 中 |
| 7 | 知識迷思（配息≠賺、外資買超為何還跌） | **②** | AI 起草擅長；Andy 加例子／情緒；數學要列算式讓 Andy 抽查 | 10～12 | IG 輪播（主力）＋Threads | 中 |
| 8 | 科技薪資行情 | **③** | 唯一爆文證據；資料來自 Andy 的朋友；有保密與勞動法遵風險（`legal_tech_transparency.md`）；AI 只做欄位整理與法遵檢查，**不能編** | 40（另資料收集約 30） | Threads | 高 |
| 9 | 面試職涯 | **②（但沒有真實經驗句就不發）** | AI 起草，Andy 必須補「一句真的發生過的事」；沒有就整句刪不編 | 15 | Threads | 中 |
| 10 | 新聞財報卡 | **②（升級後）；純改寫新聞＝停發** | 實測 7 則中位 94；IG 聚合降權風險。只留「新聞＋我們的數據補充」的版本（例：財報日 vs 近期資金流向），Andy 加一句 | 8 | Threads；IG 慎用（原創比例） | 中 |
| 11 | 互動提問 | **②（Claude 給 3 個候選題，Andy 挑一個改）** | 問題要具體可答（二選一或帶數字），候選題可由資料產生；挑選與口吻是人的事 | 3 | Threads | 中低 |
| 12 | 留言回覆 | **③（永遠人；Claude 只做待回覆摘要與回覆草稿建議）** | 回覆是 Threads 近一半觀看與信任來源；自動回覆會暴露機器味且我沒查 Meta 對自動回覆的政策（未確認） | 每天約 10 | 全部 | 高 |

**一句話：** 不是「能不能自動」，而是「**這篇如果沒有一個真人的句子，讀者還有沒有理由回應？**」沒有就不要靠自動衝量；有就升到 ②。

---

## C. 自動文怎麼兼顧流量

### C-1 條件清單（Threads 與 IG 共用，標註適用）

這些是**假說**，彼此一致、與 Meta 官方訊號（回覆、分享／私訊、原創）一致，但**沒有任何一份研究證明自動文照做就會恢復觸及**。4 週後用 F 節的指標判定。

| # | 條件 | 理由／依據 | 信心 |
|---|---|---|---|
| 1 | **每則有一個讀者會問的問題＋同篇給答案**（例：「外資買超 100 億為什麼還跌？」） | 診斷 Q3：自動文失敗在「讀者沒有想問的問題」；廣達是「我的公司行情多少」 | 中 |
| 2 | **至少一個有比較基準的數字**（對昨日、近 20 日、歷史百分位、同類排名），不是單一絕對值 | 診斷：「有數字但無對照，讀者不知道是多是少」 | 中 |
| 3 | **一句情境或立場，且來自預先審過的庫**：由規則式解讀產生（例：「外資賣超但融資同步增加＝散戶在接」），約 30 句，**一次性**由 Andy＋法遵審過，之後自動文可從中挑；每篇自動文必須帶一句 | 自動文沒有立場是第一弱點；規則式解讀是不用每篇審稿的折衷。**不是真人立場**，只是降低「純數字摘要」的機器味 | 低中 |
| 4 | **發後 60 分鐘內有人回覆留言**：自動文也要登記進「待回覆佇列」，系統在發後 60 分鐘檢查，沒回覆就推到 Andy 的摘要 | Meta 官方回覆約占近一半觀看；Reddit 經驗：排程文差在前 20～30 分鐘無互動 | 中 |
| 5 | **頻率與同質上限**：每平台每日自動 ≤1、自動＋手寫合計 ≤2、同欄目每週 ≤3、骨架 14 天不重複、**每天換構圖**（版型、主色、第一張內容）、同類型鉤子不連兩篇 | 診斷：一天 8～9 則同模板=資訊機器人；手動期每天 1～5 則仍有 355～1,130 中位（頻率本身不是主因） | 中 |
| 6 | **固定欄目化**：固定名稱＋固定時段＋第一行固定格式，讓讀者期待（例：「週二盤後 20:00｜這週錢往哪走」） | 讀者形成習慣才有追蹤理由；IG 上更是回訪動機。**沒有數據證明欄目化提升台灣財經帳號觸及** | 低 |
| 7 | **時段**：優先 20:00～22:00（週中互動高峰，QSearch 全年資料，非財經專屬）；盤後資料 18:30 才落地，所以自動盤後排在資料到齊後最近的 20:00 以後 | 台灣互動高峰（中）；我們 20:31 那則 458 高於 18:06（150）與 19:04（212），僅 3 則樣本 | 中低 |
| 8 | **主文不放網址**，網址只放第一則留言（現行已是） | 診斷與 `viral_research.md`：Threads 外連點擊低；階段 0 先養追蹤 | 中 |
| 9 | **IG：近 30 天內「含我們自算數字」的貼文占 70% 以上；純新聞改寫 ≤30%**，並每週記錄比例 | 官方原創政策為滾動計算；`channel_playbook.md` 已建議 | 中 |
| 10 | **失敗保底**：任一項沒過，**降級成 ② 進核准佇列（寄給 Andy），不是整篇不發**；Andy 24 小時沒處理則過期不發並記錄 | CLAUDE.md 2026-10-29「不准設計出條件不符就整段不做」 | 高（規定） |
| 11 | **績效地板**：同欄目連兩週自動文中位觀看＜50 且回覆為 0，系統自動降頻或升為 ②，並提醒 Andy | 避免「持續發沒人看的」稀釋帳號；門檻 50 是我設的（現況中位 56） | 低（門檻是判斷） |

### C-2 「自動文品質閘」規格（程式可檢查；給工程實作）

**沿用的既有檢查（不重做）：** `scripts/threads_lint.py` 規則 1～8（鉤子 30–80 字、≤500 字、禁用詞、主文無網址、1 標籤、reply 恰 1 網址、同詞重複、重述數字、條件句改寫成事實）；`scripts/social_gate.py`（資料日是否當天、交易日、盤中時窗）。以下是**新增**，以結構化欄位檢查，避免用語意判斷：

| 編號 | 檢查 | 怎麼算（可實作） | 未過時的動作 | 分類 |
|---|---|---|---|---|
| G1 | 有問答結構 | 稿件 JSON 欄位 `question`（問句，≥8 字，含「？」或「為什麼／還是／多少／哪」）與 `answer`（同篇出現，含 ≥1 數字） | 降級 ② | 新 |
| G2 | 有比較基準 | 欄位 `benchmark`：{類型: 昨日／近20日／歷史百分位／排名, 值}；主文必須出現該基準詞（「較昨日」「近 20 日」「創近 N 日」「排名第 N」等）。純單值不通過 | 降級 ② | 新 |
| G3 | 有情境或規則式解讀 | 欄位 `read_line`：必須來自 `interpretation_bank.yaml`（Andy＋法遵審過的句庫，每句有 id、適用條件、核准日）；且與數字句的字元相似度（bigram Jaccard）＜0.5，避免只是重述 | 降級 ② | 新 |
| G4 | 不同質 | 把數字與日期遮罩後，與**同欄目最近 14 天**每篇的骨架計算 bigram Jaccard，須 ＜0.6；`hook_type` 與前兩篇不同；`layout_id`（版型）與前兩篇不同 | 換模板重試最多 3 次；仍不過降級 ② | 擴充既有 `choose_hook()` |
| G5 | 頻率上限 | 讀 `posted` 紀錄：該平台當日自動已 ≥1 → 不發；當日總則數（含手動）≥2 → 不發；與前一則間隔 ＜4 小時 → 延後；同欄目本週 ≥3 → 不發 | 延後或轉 ② | 新（`post_quota.json` 擴充） |
| G6 | 時段 | 發文時間須在允許視窗（預設台北 08:00–09:00、12:00–13:00、20:00–22:30）；超窗延到下一個視窗，**不放棄** | 延後 | 新 |
| G7 | 越線詞（預測與勸誘） | 既有 `BANNED` 再加：「止跌」「見底」「反彈在即」「將會」「預期漲／跌」「有望」「必」「穩」。對**條件句**（「若…」）才可通過 | 降級 ② | 擴充既有 |
| G8 | 數字回溯 | 稿件每個數字必須在 `facts` 陣列有 `source`（檔、欄位、資料日）；主文數字不在 `facts` → 不過。避免模型幻想 | 不發＋寫 alert，降級 ② | 新 |
| G9 | 待回覆登記 | 發布成功時寫入 `reply_watch.json`：post id、發布時間、`deadline=+60min`、`owner`；Action 在 deadline 檢查回覆數＝0 → 把該貼文放進 Andy 的待回覆摘要 | 通知，不阻擋 | 新 |
| G10 | 圖：構圖輪替與重疊 | 既有重疊檢查（`layout_report.json`）；新增 `layout_id` 輪替（同 G4）；每篇圖數 0 或 1 | 精簡重畫→仍不過拿掉那張（沿用盤前規則） | 擴充 |
| G11 | IG 原創比例 | 讀近 30 天 IG 貼文旗標 `own_calc`（是否含自算數字）；比例＜70% → 當日只發 own_calc=true 的內容；`news_only` 近 30 天占比 ＞30% → 禁新增 | 擋新聞卡 | 新 |
| G12 | AI 圖審查 | 沿用 `ai_image_review.md`：AI 生成圖須有 `ai_review.md` 且狀態為通過，否則該圖不附 | 拿掉該圖 | 既有 |
| G13 | 績效地板 | 每週日計算各欄目最近 10 篇自動文的觀看中位與回覆合計；連兩週＜50 且回覆 0 → 將該欄目頻率減半或升為 ②，寫入週報 | 降頻 | 新 |

**通過規則：** G5～G8、G12 為**硬性**（不過就不發當前版本，改走降級）；G1～G4 為**降級條件**（不過就轉 ②，並寄給 Andy）；G9、G13 為**監控**（不阻擋）。**任何情況下不得出現「整段不發也不通知」**；降級後 Andy 24 小時未處理，記錄為「過期」，不補發舊資料（避免資料不是當天）。

**工程量判斷（信心：低，我沒讀 `social_snap.py`／`threads_v2.py` 程式）：** G1～G3 需要稿件模板多出 `question／benchmark／read_line` 欄位，是最大的工。G4～G7、G9、G13 在現有結構下是小到中的工。請工程自行估，第一步見 D-4。

---

## D. 「Claude 做完、Andy 手動發」的實際流程

### D-1 現有基礎設施（讀過檔，高信心）

- `social/threads/queue/*.md`、`social/ig/queue/*.md`：**只有 `status: approved` 且 `publish_at` 已到才會發**；`draft` 永遠不發；每 15 分鐘檢查（`threads_post.yml`、`ig_post.yml`）；發完自動改成 `posted`，失敗改 `error` 並寫原因。這就是「Claude 排程、Andy 先審」的現成載體。
- 盤前／盤中／盤後自動發文由 `social-live.yml` 走，`post_quota.json` 目前只留盤後。
- 倉庫 **public**：放進佇列的稿件發出前任何人都看得到（見 D-5 風險）。

### D-2 管道比較（Andy 在手機上）

| 管道 | Andy 手機上要做的事 | 優點 | 缺點 | 需要的工程 |
|---|---|---|---|---|
| **A. Gmail 草稿包** | 開信→長按文案複製→切到 Threads／IG App 貼上→從信裡存圖→改→按發。**3～4 分鐘／篇** | 立刻可用、不依賴任何新程式 | 複製貼上＋存圖最費力；發完要回信報備才不重發；忘了發沒人知道 | 幾乎無（若已有寄信機制；`social_premarket.py` 提到信件，我沒讀實作，**待工程確認**） |
| **B. GitHub Issue** | 開 GitHub App→讀 Issue→複製→貼 | 有留言與狀態可追 | 圖片管理差、不符合 Andy「只重新整理網頁」習慣 | 小 |
| **C. 佇列檔核准**（現成） | 在 GitHub 手機版／網頁開檔→把 `draft` 改 `approved`（可同時改字）→存檔。**約 1～2 分鐘／篇**，系統到點用 API 發，圖已附 | 不用複製貼上與存圖；時間精準；已有防重複與錯誤記錄 | 要操作 GitHub 編輯；改錯 YAML 欄位會出錯；Andy 是否願意編輯檔案**不確定**（他的習慣是只看網頁） | 無（現成） |
| **D. 網站管理區「今日草稿」頁**（建議第二階段） | 打開網站管理頁→看到今天要發的卡片：預覽、文案可直接編輯、圖、按鈕「核准」「退回」「改稿給 Claude」。**約 1 分鐘／篇** | 最省力；符合他「只開網頁」；可記錄核准時間、編輯幅度 | 需要工程：核准後要翻轉佇列檔的 status（Cloudflare Worker 呼叫 GitHub API，或前端直接呼叫）；**權限驗證與金鑰放哪要處理**（public repo，金鑰不能進前端）。我沒讀現有 account worker，可行性**待工程確認** | 中 |

**我的建議：** 第一週用 **C**（今天就能做，先看 Andy 能不能接受編輯檔），**同時**做 **A** 當備援（每天一封信：今日草稿清單＋佇列檔連結＋未核准提醒）；第 3～4 週視 Andy 實際使用情況，決定要不要投資 **D**。**第一步（最小）：** CEO 本週先把下週 ② 稿件用現有格式寫成 `status: draft` 佇列檔，並寄一封「本週草稿包」給 Andy；請他回答兩個問題——能不能用 GitHub 手機版改 `approved`？不能的話他願意在 App 複製貼上嗎？（這兩題他沒答過）

### D-3 每日／每週節奏（Andy 時間）

| 時間（台北） | 事件 | Andy 動作 | 分鐘 |
|---|---|---|---|
| 週日 20:00 | 收到「下週草稿包」（Mon–Sat 的 ② 稿共 7 篇：5 篇 Threads、2 篇 IG 輪播） | 一次看完、每篇加／改一句、核准（C 或 D）；資料不對的退回 | 約 45～55 |
| 週一至週五 12:00 前 | 熱點機動：Claude 依事件寄「快版草稿」（目標 90 分鐘內送到） | 看、加一句、核准 | 10～15／則，每週 0～2 則 |
| 每天發文後 | 系統在發布後 60 分鐘推「待回覆摘要」：哪幾則有留言／0 回覆 | 回覆（或請 Claude 給回覆草稿，Andy 發） | 約 10／天 |
| 週一 10:00 | 週報一頁：各欄目中位、回覆、追蹤淨增、G13 結果 | 只看結論 | 5 |

### D-4 「API 排程自動發」vs「Andy 手動發」差異與建議組合

| 面向 | API 排程發（核准後系統發） | Andy 手動在 App 發 |
|---|---|---|
| 演算法 | 查不到降權（A 節）；信心中低 | 同 |
| 發布當下在場 | 否——**用「發後 60 分鐘待回覆摘要」補** | 是，可立刻回第一批留言（真優勢） |
| 時間精準 | 高（20:30 準時） | 取決於 Andy 當時有沒有空 |
| 圖片 | 已附、版型一致 | 要存圖、貼圖，易漏 |
| 每篇成本 | 1～2 分鐘 | 3～4 分鐘 |
| 失敗模式 | 權杖 60 天到期、API 失敗（已有 error 記錄） | 忘記發、貼錯版 |
| App 專屬功能 | 通常用不到音樂／貼圖／部分互動版型（**我沒查證 IG／Threads API 的功能邊界，信心中低**） | 可用 |

**建議組合：** 預設「**核准後 API 發**」（省時、準時）；**例外手動發**：（1）熱點機動文，Andy 剛好有空時；（2）IG Reels（第一個月手動，順便做 A 節的對照）；（3）頻道二的薪資文（高風險，Andy 要在場回覆）。

### D-5 風險

- **public repo 洩稿**：`draft` 佇列檔在發出前是公開的。頻道二薪資稿（含公司待遇與保密風險）**不要進 public 倉庫**；改走 Gmail 草稿包／私人雲端，Andy 手寫或貼上後再發。頻道一稿可進佇列但不得含未公開消息（本來就不含）。（信心：高，CLAUDE.md 已規定 public）
- **Andy 24 小時未處理**：過期不發，不補（避免資料不是當天）。降頻優先於勉強。

---

## E. 影片：要不要做、做哪種、哪個平台

### E-1 證據

| # | 事實 | 來源 | 信心 |
|---|---|---|---|
| 1 | **我們自己的資料：** IG Reels 5 支，reach 9～47（共 130、中位 21）；IG 動態（輪播 14 則中位 0.5、單張 9 則中位 1）；限動 72 則共 17。→ Reels 在我們帳號上觸及約是動態的 20 倍，但**絕對值極小**，也不能排除「帳號是否可被推薦」問題（未確認，`viral_research.md` E2 需 Andy 查） | `posts_catalog.json` 重算 | 高（事實）／低（推論） |
| 2 | 那 5 支都是「網站功能介紹」，而診斷指出「產品導向的功能廣告」正是失敗型態（Q3、Q7） | `strategy_diagnosis.md` | 中高 |
| 3 | 外部：小於 1 萬追蹤的帳號，每追蹤者中位觸及 Reels 約 4.9%、單張圖 3.5%、輪播 2.6%（Reels 對非追蹤者觸及近輪播 2 倍）；輪播的收藏明顯較高（某來源稱 3～4 倍收藏率）。**這是相關性資料，不證明形式本身造成差異；廠商資料** | [Fanpagekarma](https://www.fanpagekarma.com/insights/instagram-format-reach/)、[Posteverywhere 轉述](https://posteverywhere.ai/blog/instagram-carousel-vs-reels) | 中低 |
| 4 | 較早已引：Socialinsider 2025 輪播互動 0.55%、Reels 0.52%；Buffer 400 萬則：Reels 觸及高 36%、輪播互動高 12% → 結論是 Reels 拉新、輪播養互動 | `video_1010/research.md` 1-7 | 高（方向一致，幅度不一致） |
| 5 | IG Reels：被轉述 Mosseri 2025-01 說超過 3 分鐘不推薦給非追蹤者；「每次觸及的私訊分享數」是對非追蹤者最強訊號之一，部落格稱權重為按讚的 3～5 倍（**無一手出處**） | [SocialPilot](https://www.socialpilot.co/blog/instagram-reels-algorithm)（摘要） | 低 |
| 6 | Threads 影片：**查不到 Threads 上影片 vs 純文字的量化資料**。第三方轉述 Buffer：圖片互動最高、影片次之、連結、純文字最低（5.17%／5.14%／3.78%／3.23%），為二手摘要；Threads 整體 63% 是純文字（2024，Meta） | [onlinemarketing.de 轉述 Buffer](https://onlinemarketing.de/social-media-marketing/threads-beste-posting-zeiten-buffer-analyse) | 低 |
| 7 | **我們 Threads 的 5 則功能影片文**（868、868、794、1,522、1,946 觀看）：文字與 IG Reels 說明相同，Andy 說是影片。**目錄裡這 5 則 `media_type` 記為 `CAROUSEL_ALBUM`**，我無法從資料確認它們是影片還是輪播圖，需 Andy 或工程核對。若是影片：觀看約為同期（10-17～10-21）HBM 知識輪播（491～786）的 1～2.5 倍；但同期是手動期、基準偏高（中位 355～1,130），且 1,946 那則有 4 次引用、3 次分享，分不出影片的貢獻 | `posts_catalog.json` | 低 |
| 8 | 台灣短影音背景：Reels 2022-04 開放後 iKala 數據顯示 8 月貼文量比 4 月高 971%；報導稱短影音製作成本約為長影片的 2～3 成。**沒有任何量化資料支持「不露臉／螢幕錄影／字卡」財經帳號的成效** | [Bnext iKala](https://www.bnext.com.tw/article/72691/ikala-kol-shorts-2022)、[Bnext 短影音行銷](https://www.bnext.com.tw/article/76005/shortvideo-marketing-advertising-youtube-shorts-instagram-reels-tiktok) | 中（市場）／無（財經個案） |
| 9 | 「不露臉財經 Reels」查到的全是廠商教學（螢幕錄影＋AI 旁白），自述 10 萬粉等數字無出處；廠商也說機械聲「像低品質」是意見 | [FluxNote](https://fluxnote.io/guides/how-to-make-faceless-finance-videos-with-ai-guide-2026)、[FlowShorts](https://flowshorts.app/faceless-reels/finance) | 低（廠商行銷，不採信其數字） |
| 10 | YouTube Shorts：2021 Shorts 基金拓展台灣；**查不到台灣 ETF／存股類 Shorts 帶來訂閱或導流的公開數據** | [Google 台灣](https://blog.google/intl/zh-tw/products/explore-get-answers/2021_09_youtube-shorts-fund) | 無 |

### E-2 判斷

- **要做，但角色是「拉新的觸及型」，不是主力，也不是功能廣告。** 理由：（1）外部方向一致（Reels 拉新、輪播養互動）；（2）我們的輪播與動態幾乎 0，若不做 Reels，IG 沒有任何機會被推薦給非追蹤者；（3）影片的素材（輪動時鐘 ▶ 播放、大跌後走勢線、除息月曆）是**網站最擅長、競品圖文最難複製**的動態畫面。信心：中低。
- **題材要變：** 不再介紹功能，改「回答一個問題」：例如「大跌後 1／3 個月平均怎麼走（我用 26 年資料算）」「配息 8% 為什麼不是賺 8%」「這週錢往哪個族群跑」。與 B 節 ② 的類型一一對應，影片是同一篇的視覺版，省製作也避免新增人力。
- **IG 原創性：** 官方原創政策認的是「完整創作或有實質編輯」。用**網站錄影＋我們自己算的數字＋自己配的旁白與剪輯**屬原創。避免：把別平台下載的影片重發（浮水印）、單純加速、只截他人圖加註。（信心：中高）
- **Threads 影片：不專門做。** 沒有量化證據；把 IG 同一支 Reels 偶爾（每月 1～2 支）轉發到 Threads 當對照，成本接近 0，用 4 週資料決定。（信心：低）
- **YouTube Shorts：第 1 個月不做。** 沒有台灣財經 Shorts 的證據；多一個平台等於多一個要回覆的地方，Andy 的瓶頸是回覆時間，不是檔案。**例外：** 若某支 Reels 單支 reach ≥ 500，同一檔案上傳 Shorts 只需手機 3 分鐘，屆時再做。（信心：低）
- **頻道二（薪資）：第 1 個月不做影片。** 唯一爆文是純文字長文；薪資數字加旁白／字卡的法遵風險（點名公司、洩密）高於純文字；Andy 若要做，第 5 週後把 Threads 最高那篇做成輪播，不做影片。（信心：中）

### E-3 不露臉的做法排序（針對頻道一）

| 做法 | 人味 | 成本（Andy） | 風險 | 建議 |
|---|---|---|---|---|
| 1. 網站螢幕錄影＋大字卡＋台灣女聲旁白（現有產線） | 中（旁白像 AI 的風險：Andy 10-18 已指出「聽起來就知道 AI」） | 看片 5～8 分鐘；旁白需先交 10 秒試聽讓 Andy 確認（`video_rules_1018.md`） | edge-tts 條款不明，正式發佈前換 Azure 或其他（`tts_options_1027.md`） | **預設** |
| 2. 資料動畫（輪動時鐘、走勢線，2.5D 圖表）＋字幕為主、旁白極少 | 中 | 同上 | 靜音觀看多，字幕要夠大（Adweek：Stories 約 40% 關聲音，舊數據） | 搭配 1 |
| 3. Andy 只出聲音（不露臉） | 高（有人味、像真人在講） | 錄音每支 5～10 分鐘 | 需 Andy 願意；聲音是個資 | 第 5 週後可選 |
| 4. 比比小助手（不說話，遞素材） | 中，品牌識別 | 無 | 占比要小（10-18 規則）；頻道二別用（避免兩帳號被視為同一個） | 小角色 |

### E-4 製作成本（時間）估計

**誠實標示：** repo 裡沒有三支既有影片（`video_1010/`、`videos/2026-10-18-cowos_bibi/`、`videos/2026-10-17-k_cpo/`）的實際工時紀錄，我只能估，**請 CEO 補實際耗時**。工具鏈存在：錄影 `capture.py`／`capture_cowos.py`、逐格合成 `render_*.py`（Pillow＋ffmpeg）、旁白 `.github/workflows/tts.yml`（edge-tts，輸出 mp3＋逐字時間軸）、重疊檢查 `overlap_report`。

| 項目 | Claude 工時（機器時間，非 Andy） | Andy 時間 |
|---|---|---|
| 腳本（把 ② 稿改成 20～30 秒口語腳本） | 15～20 分 | 0（併入看稿） |
| 錄影網站畫面／出資料圖 | 10～20 分 | 0 |
| 旁白（TTS）＋字幕時間軸 | 5～10 分 | 第一支 10 秒試聽確認；之後 0 |
| 合成、封面、重疊檢查 | 20～40 分（首支更長，之後有模板會短） | 0 |
| 審片 | — | 5～8 分（看片＋改字幕錯字＋核准） |
| 發布與發後回覆 | — | 3 分發（手動，第一個月）＋回覆併入每日 10 分 |
| **合計** | **約 1～1.5 小時（模板化後）** | **約 8～11 分鐘／支** |

（以上為估計，信心：低；首支會多花，模板化後才有上述水準。）

### E-5 第 1 個月影片排程（頻道一）

| 週 | 支數 | 主題 | 來源（B 節） | 備註 |
|---|---|---|---|---|
| W1 | 0 | 不做；先做 10 秒旁白試聽、確認 IG「帳號狀態」是否可被推薦（`viral_research.md` E2） | — | 若帳號被判不可推薦，影片也沒用，先解決它 |
| W2 | 1 | 「大跌後 1／3 個月平均怎麼走」（我們 26 年指數資料，走勢線 ▶ 動畫） | 歷史統計 #5 | 需法遵過稿；條件句寫法，不預測 |
| W3 | 1 | 「配息 8% 為什麼不是賺 8%」（算式動畫＋除息月曆） | 知識迷思 #7＋ETF #3／#4 | 證交所提醒的題材（中，`channel_playbook.md`） |
| W4 | 1 | 「這週錢往哪個族群跑」輪動時鐘 ▶ 播放 30 秒 | 盤後輪動 #1／產業輪動 #6 | 可變固定欄目（週五） |

第 2 個月起：若 Reels 單支 reach 中位 ≥ 150 或有任何一支 ≥ 500，加到每週 1 支＋Shorts 副本；若連 3 支仍 ＜ 50，**停做影片**，把工時換成輪播（不再增加量）。這兩個門檻是我設的（信心：低），請 Andy 校正。

---

## F. 建議組合表（第 1 個月，兩頻道 × 每週）

| 項目 | 頻道一（哩股哩股） | 頻道二（科技薪資） |
|---|---|---|
| ① 全自動（Threads） | **3 則**：ETF 週曆（週一上午）＋盤後資金輪動（週二、週四）。**通過品質閘才發，未過降級** | **0** |
| ② 半自動（Claude 起草＋產圖，Andy 看稿加句核准） | **7 則**：Threads 5（熱點 週一、知識 週二、ETF 試算 週三、輪動 週五、互動 週六）＋IG 輪播 2；另熱點機動 ≤1～2 | **2 則**：面試職涯（週四）＋機動 ≤1（時事×職涯，過法遵） |
| ③ 手寫 | 0 則（但每篇 ② 內有 Andy 的一句；留言回覆全是 Andy） | **2 則**：公司行情 1（週二，約 40 分＋收集 30）＋互動／薪資問答 1（週六，約 10 分） |
| 影片 | W2 起每週 **1 支** Reels（IG 優先；偶爾轉 Threads 對照） | **0 支** |
| 自動文分鐘 | 約 5（每週抽查） | 0 |
| ② 分鐘（看稿＋核准） | 熱點 15＋知識 12＋ETF 12＋輪動 12＋互動 3＋IG 2 篇各 5＝**約 64**；機動 0～30 | 面試 15＋機動 0～15＝**約 15～30** |
| ③ 分鐘 | 0 | 公司行情 40＋收集 30＋互動 10＝**約 80** |
| 影片分鐘 | 約 8～11 | 0 |
| 每日留言回覆 | **約 60（每天 10×週一至六）** | **約 60** |
| **Andy 每週合計** | **約 140～170 分鐘（2.3～2.8 小時；W1 無影片少約 10）** | **約 155～170 分鐘（2.6～2.8 小時）；若依手冊 7-6 的 2 篇手寫各 40 分，約 3.5 小時** |
| **兩頻道合計** | **約 5～6.5 小時／週**（`channel_playbook.md` 估 6.5 小時；本方案因 ② 的核准流程與互動題候選機制略低） | |

**不夠時間的砍法（順序）：** 先砍頻道一機動熱點→先砍 IG 輪播→先砍影片→降低自動文（G13）→最後才砍頻道二手寫文。（沿用手冊，並把影片排在 IG 輪播之後，因為影片證據最弱。）

**4 週後的判定指標（沿用 `channel_playbook.md` 第九節，補自動／半自動對照）：**
- ① 自動組 vs ② 半自動組：觀看中位、回覆／則、分享／則。若 ② 中位不到 ① 的 2 倍，代表「Andy 那一句」沒有產生差異，應重新檢討流程而不是繼續加人力。
- API 核准發 vs Andy 手動發（A-3 的對照）。
- Reels：單支 reach、私訊分享數、追蹤淨增；轉發 Threads 的對照。
- 自動文 G13 地板觸發次數。

---

## 十、Andy 可能不同意的地方（請一次否決）

1. **我說「自動發文不是主要問題」，Andy 原本可能認為自動發文本身就是問題。** 我的證據是「查不到降權」，但這是反面證據弱（信心：中低）。若他堅持，我仍建議做 A-3 的對照而不是直接全面改手動，因為差別一個月內就能量出來。
2. **我保留 2 類 ① 全自動**（ETF 週曆、盤後資金輪動）。他可能想一律改 ②。代價：每週多約 10～15 分鐘看稿；好處：不會再有「沒人看過就發出去」的事故。我選 ① 的理由是這兩類是純事實＋固定問題＋有品質閘兜底，且**我們沒有證據它們能帶量，只當記錄與基底**。
3. **我把互動提問改成 ②（Claude 給候選題），手冊原先是 Andy 手寫（10 分鐘）。** 他可能認為問題一定要自己想。
4. **規則式解讀句庫（C-1 #3）可能被認為「還是機器」。** 我同意它不是真人立場，只是降低純數字摘要的機器味，且需要他＋法遵一次性審過約 30 句。若他不想，G3 就只能降為「有比較基準即可」。
5. **影片我只建議頻道一、W2 起一週一支，頻道二 0。** 他可能想更積極（有 IG 與 Threads 影片都想做）。我的理由是證據弱、製作成本加上他的審片時間會擠到回覆時間。
6. **Andy 最省力的核准方式，我先推「佇列檔改 approved」**，他是否願意編輯 GitHub 檔案是我沒問過的事。如果不願意，就需要先做管理區頁面（D 方案），工程量變大。
7. **薪資稿不進 public 倉庫**，這會讓頻道二的流程比頻道一多一道私人管道（Gmail／雲端）。
8. **Threads 影片與 Shorts 都暫不做**，他之前有 Threads 影片介紹 800～1,900 觀看，可能覺得有效。我的看法是樣本小、基準偏高、且連它們是不是影片都無法從資料確認。

---

## 十一、我沒查到／不確定的（不要當成有證據）

1. **Mosseri 的原話**：排程不影響觸及等說法，我只讀到二手部落格摘要，沒讀到他本人貼文。
2. **Threads API 發文 vs 手動的任何獨立研究**：沒有。廠商 MindThread 自稱差 3%，無方法。
3. **廣達那篇當初是 API 發還是 App 手動發**：未確認；這決定我們的自有資料能不能回答 A。需 Andy 或發布紀錄核對。
4. **IG／Threads 的 API 能做、不能做哪些功能**（音樂、貼圖、投票等）：沒查證。
5. **IG 對「單張 AI 圖」是否強制標示／是否降權**：只查到針對 AI 角色／AI 帳號的規則；比比（卡通角色）是否被視為「AI 角色」未確認。
6. **Threads 原生排程是否存在**：兩份廠商文章說法相反（一說 2025-01 起有，一說沒有），**未確認**；若有，Andy 手動排程可以做「週日一次排完」。
7. **台灣不露臉財經帳號的量化案例**：查不到，只有廠商教學；「Reels 對財經小帳號最有效」我沒有財經專屬證據。
8. **Threads 上影片的量化表現**：查不到；我們那 5 則是否為影片未能從資料確認。
9. **三支既有影片的實際製作工時**：repo 沒有紀錄，E-4 是估計。
10. **IG 帳號是否被判「不可推薦」**：未知，需 Andy 到 IG 帳號狀態查（`viral_research.md` E2），這決定 Reels 有沒有意義。
11. **Meta 對自動回覆留言的政策**：沒查，所以建議永遠人回。
12. **現有寄信機制能不能寄「草稿包」**（`social_premarket.py` 有提到信件）：我沒讀，待工程確認。
13. **管理區頁面／Worker 能否安全翻轉佇列檔狀態**：沒讀 `deploy-account-worker.yml` 與 Worker 程式，待工程確認。

---

## 十二、做得到的第一步（Andy 一個人、沒有後端）

1. **本週（約 15 分鐘 Andy）：** 回答 4 題——（a）廣達那篇當初是 App 手動貼還是系統發的？（b）IG「帳號狀態」顯示可被推薦嗎？（c）願意用 GitHub 手機版把 `draft` 改 `approved` 嗎？不願意就走 Gmail 複製貼上；（d）他能不能接受 W2 起每週一支 Reels，以及先聽 10 秒旁白試聽。
2. **CEO 本週：** 把下週頻道一的 ② 稿（5 Threads＋2 IG）寫成 `draft` 佇列檔＋寄「本週草稿包」；頻道二稿走 Gmail，不進 public 倉庫。
3. **工程（選擇性，第 2 週後）：** 先做 G5（頻率上限）、G9（待回覆登記）、G13（績效地板）三項小工，再做 G1～G3 的稿件欄位。
4. **第 4 週：** 用 F 節的四組對照決定：自動組升降、API vs 手動、影片繼續或停。

---

## 來源（皆為 2026-11-02 WebSearch 摘要，未讀原文）

- 排程與觸及：[Kontentino](https://www.kontentino.com/blog/does-scheduling-instagram-posts-hurt-reach/)、[Kontentino Q&A](https://www.kontentino.com/q-and-a/does-scheduling-instagram-posts-affect-reach/)、[Planoly](https://www.planoly.com/blog/does-scheduling-your-posts-affect-your-post-reach.md)、[Poster.ly](https://www.poster.ly/blog/does-scheduling-hurt-reach-research)、[Vista Social](https://vistasocial.com/insights/do-scheduled-posts-get-less-views/)
- Threads API 發文：[dev.to](https://dev.to/ppcvote/how-to-schedule-threads-posts-set-up-daily-auto-posting-in-5-minutes-1h0f)、[Sked Social](https://skedsocial.com/blog/schedule-threads-posts.md)
- IG 原創與 AI：[IG 原創規範](https://creators.instagram.com/original-content-guidelines/)、[IG 推薦與原創](https://creators.instagram.com/recommendations-and-originality)、[IG 官方部落格](https://creators.instagram.com/blog/rewarding-original-creators-on-instagram)、[PetaPixel](https://petapixel.com/2026/04/30/new-instagram-policies-target-reposted-content/)、[Techwyse](https://www.techwyse.com/?p=78112)、[Dataslayer](https://www.dataslayer.ai/blog/is-instagram-penalizing-polished-content-in-2026-yes-heres-what-changed)
- Reels 與輪播：[Fanpagekarma](https://www.fanpagekarma.com/insights/instagram-format-reach/)、[Posteverywhere](https://posteverywhere.ai/blog/instagram-carousel-vs-reels)、[SocialPilot](https://www.socialpilot.co/blog/instagram-reels-algorithm)
- Threads：[Postory](https://postory.io/blog/threads-algorithm)、[Vista Social](https://vistasocial.com/insights/threads-algorithm/)、[onlinemarketing.de（Buffer 轉述）](https://onlinemarketing.de/social-media-marketing/threads-beste-posting-zeiten-buffer-analyse)、[Meta 官方](https://about.fb.com/news/2024/10/find-your-community-with-new-threads-educational-insights/)
- 台灣短影音與 YouTube：[Bnext iKala](https://www.bnext.com.tw/article/72691/ikala-kol-shorts-2022)、[Bnext 短影音行銷](https://www.bnext.com.tw/article/76005/shortvideo-marketing-advertising-youtube-shorts-instagram-reels-tiktok)、[Google 台灣 Shorts 基金](https://blog.google/intl/zh-tw/products/explore-get-answers/2021_09_youtube-shorts-fund)
- 不露臉財經（廠商，僅供參考）：[FluxNote](https://fluxnote.io/guides/how-to-make-faceless-finance-videos-with-ai-guide-2026)、[FlowShorts](https://flowshorts.app/faceless-reels/finance)
- 內部：`posts_catalog.json`（146 則）、`social/threads/README.md`、`docs/marketing/social_unit/live_posts.md`、`auto_post.md`、`scripts/threads_lint.py`、`scripts/social_gate.py`、`docs/marketing/video_1010/`、`docs/marketing/videos/video_rules_1018.md`、`docs/marketing/tts_options_1027.md`

查詢關鍵字（WebSearch，共 11 組）：Instagram scheduled posts API publishing reach penalty Mosseri 2025｜Threads API scheduled posts vs native posting reach engagement test｜Instagram AI-generated content reach penalty 2026 Mosseri original content labeling automation｜Threads 影片 觸及 圖片 純文字 比較 2026 台灣 創作者｜Instagram Reels vs carousel reach saves 2026 small accounts follower growth data｜台灣 財經 短影音 Reels Shorts 成長 案例 不露臉 螢幕錄影 字卡 理財｜YouTube Shorts 財經 台灣 頻道 訂閱 成長 ETF 存股 短影音 導流｜Instagram Reels 3 minute reach non-followers 2026 recommendation sends per reach finance account｜Threads algorithm 2026 video posts reach replies Mosseri Connor Hayes｜faceless finance Instagram Reels screen recording AI voiceover grew followers case study｜Instagram repetitive content template posts unoriginal automated accounts reach recommendation eligibility help center
