# 需求交付清單（Andy 2026-09-23）

這份是「交付清單」頁的資料來源。**原話逐字照抄，不准改寫成我理解的版本** ——
改寫就等於把「他要什麼」換成「我以為他要什麼」，那正是這份清單要防的事。

欄位：`quote` 他的原話｜`what` 實際做了什麼｜`state` 狀態｜`ver` 哪一次部署交付｜`go` 去哪裡看

state 只有五種：`done` 已上線｜`wip` 進行中｜`next` 判斷成下一批｜`ask` 等 Andy 決定｜`drop` 他否決了

---

## 第 103 次部署（2026-09-23 12:30）

1. quote：連接器少了3D圖 請補上
   what：高速連接器補上 3D 場景，8 個零件（屏蔽籠／舌片成對金手指／壓接針／飛越纜線）
   state：done ｜ ver：103 ｜ go：#industry/ai_server/dg/ai_interconnect

2. quote：另外幫我將設定改成右上角
   what：設定列從圖的右下角移到標題那一列的右邊，並排不再浮在圖上
   state：done ｜ ver：103 ｜ go：#industry/ai_server

3. quote：AI 伺服器機櫃與 GPU 運算托盤 2D請 Follow 其他族群風格更新
   what：寫死色碼 61 處歸零，畫布 1220→700，說明外掛成卡片，右下角空白補滿
   state：done ｜ ver：103 ｜ go：#industry/ai_server/dg/ai_server

4. quote：下方成分股欄位拿掉
   what：成分股整張卡片與只服務它的程式碼移除
   state：done ｜ ver：103 ｜ go：#industry/semiconductor

5. quote：圖四圖五 族群版面格式需要Follow AI 伺服器 那樣，點擊AI 伺服器進去就直接看到第一個族群的2D圖3D圖
   what：點產業鏈直接進第一張剖析圖，族群總覽改走 /overview
   state：done ｜ ver：103 ｜ go：#industry/semiconductor

6. quote：幫我更新一般電子以及半導體內，所有族群2D圖 呈現風格都需要Follow AI Server 族群內2D圖，並且需要適當的調整及填充版面間隔，不許有空白
   what：一般電子五張＋半導體五張，畫布 980→660，說明外掛成卡片
   state：done ｜ ver：103 ｜ go：#industry/electronics

7. quote：圖一這邊的標籤只需要顯示:以前族群名稱即可後面說明在文章內有就好
   what：分頁標籤只取冒號前那一段，完整名稱收進滑鼠提示
   state：done ｜ ver：103 ｜ go：#industry/semiconductor

8. quote：軟體與資訊服務 需補上2D圖即可，不用3D格式如我所說那樣
   what：新增四張（資安防護／雲端與 MSP／企業 SaaS／電商零售）
   state：done ｜ ver：103 ｜ go：#industry/software

9. quote：分頁的這紅框處標籤都拿掉
   what：標題下那排（檔數／今日／本益比中位／返回）整排移除
   state：done ｜ ver：103 ｜ go：#industry/semiconductor

10. quote：下方的字卡也拿掉 因為上方分頁就有同樣功能了
    what：圖別選單那排大卡片整塊移除（跟分頁列是同一份資料畫兩次）
    state：done ｜ ver：103 ｜ go：#industry/semiconductor

11. quote：幫我優化長條圖以及圓餅圖，看起來太乾澀了，如圖
    what：兩張圖各自進卡片、族群名不截斷、長條圓角、圓餅改甜甜圈＋前五大引線＋其他併塊＋中心合計
    state：done ｜ ver：103 ｜ go：#industry/semiconductor/overview

12. quote：當切換明亮介面時，所有圖片會自動切換閱讀模式 同理切暗色介面時，也會切回來
    what：主題切換一律重新對齊剖析圖配色，兩個方向都做
    state：done ｜ ver：103 ｜ go：#industry/ai_server

13. quote：圖一二 兩個標籤式都需要做成下拉清單 篩選，所以他會是 族群->題材，例如 半導體，下面就會有圖三那些
    what：48 顆族群晶片改成「產業鏈 → 該鏈族群」兩層下拉；桑基那排也改（保留單選）
    state：done ｜ ver：103 ｜ go：#flow

14. quote：下方的輪動階段需要與上方的輪動時鐘合併，輪動時鐘四周的四段 需要有對應顏色 並且點擊後會出現目前該項線的股票強弱 占比
    what：四個象限標籤吃階段色、可點、展開該段族群與強弱占比；下方那塊移除
    state：done ｜ ver：103 ｜ go：#flow

15. quote：另外圖三四這個真的是即時更新嗎?多久更新一次，我看他沒有再移動
    what：查證後回答 —— 每 60 秒一輪，只在盤中＋分頁在前景才跑。看不出在動是刻意的：
          贏大盤 2% 只走 4.5 像素，而整張圖橫跨 16 點。不准為了好看放大位移
    state：done ｜ ver：103 ｜ go：#flow

---

## 第 104 次部署（2026-09-23 17:17）

16. quote：幫我將 產品剖析圖 、族群預覽 、配色拿掉、另外收合圖 移動到上方同一排
    what：三個移除，收合圖併到同一排。配色改成只跟著全站主題走
    state：done ｜ ver：104 ｜ go：#industry/ai_server

17. quote：傳產與內需 & 基礎建設與能源 2D 圖並沒有調整適當大小，請去調整，調整適當範圍，別浪費空白
    what：兩張收窄到 660，說明外掛成卡片。上一批「在框裡補小圖」的做法被否決，改成跟其餘 12 張同一套
    state：done ｜ ver：104 ｜ go：#industry/traditional

18. quote：金融麻煩也生成2D圖
    what：新增三張 —— 銀行利差引擎／壽險天平／證券三條腿
    state：done ｜ ver：104 ｜ go：#industry/financial

19. quote：IC 封裝剖析 這頁似乎沒做好，請確認
    what：六張說明卡誤掛右欄造成 244px 死白，改掛左欄（12/10）。全站 23 張只有這張這樣寫
    state：done ｜ ver：104 ｜ go：#industry/semiconductor/dg/ai_adv_packaging

20. quote：圖五 下方的關聯圖，幫我退版 回到之前的格式，但是需要將關聯圖置中，並且 Default 顯示族群相連標籤個股，點擊後才會跳出下拉清單，並且點擊股票 右側會顯示對應訊息
    what：預設就看得到個股標籤（不再只是匿名小圓點），點族群才跳清單，置中，點個股右側出資訊欄
    state：done ｜ ver：104 ｜ go：#industry/ai_server
    note：390px 手機寬度不掛個股標籤 —— 24 顆族群在那個寬度下，就算不掛標籤族群名本身就有 6 組互疊

21. quote：資金輪動已經有一個時間拉Bar 幫我合併
    what：兩條合併成一條雙把手區間桿，讀數寫成「最近 12 天 · 截止 5 天前」
    state：done ｜ ver：104 ｜ go：#flow
    note：回溯上限從 60 天變 30 天（時鐘的軌跡本來就只有 31 天）

22. quote：圖二 格式要改成 我點選領先，底下資訊是顯示在旁邊的，另外「最近 5 個交易日換階段的族群」拿掉
    what：象限展開面板移到時鐘右邊；換階段名單整排移除
    state：done ｜ ver：104 ｜ go：#flow

23. quote：估值篩選 拿掉
    what：資金流向那張整塊移除；追問後確認總覽那張「族群估值」也一起砍
    state：done ｜ ver：104 ｜ go：#flow

24. quote：漲跌幅需要 多一個"即時"Mode
    what：漲跌家數與漲跌分佈新增即時模式
    state：done ｜ ver：104 ｜ go：#market
    note：涵蓋率只有 19%（444 檔對全市場 2339 檔），而且樣本偏中大型偏電子，這三句印在畫面上

25. quote：上方分頁任務版移除
    what：導覽列拿掉，路由保留（直接貼網址仍打得開）
    state：done ｜ ver：104 ｜ go：#overview

26. quote：總覽 輪動階段 上方的"放大"移除，並且需要圓圈大一點，下方的紅框處改成昨日的資金去向 分流圖（不需要動畫，只顯示線條粗細即可，並且只顯示到族群即可。個股也不用）
    what：放大鈕移除、圓圈放大；四格階段卡改成靜態分流圖，只用線寬、只到族群層
    state：done ｜ ver：104 ｜ go：#overview

27. quote：題材這頁 將中間這兩個表格拿掉
    what：成員表與熱度走勢卡整塊移除；沒有剖析圖的三個題材改顯示說明卡不留空白
    state：done ｜ ver：104 ｜ go：#themes

28. quote：另外3D圖 幫我都做成會有動畫像是這儀器再運作，可以參考AI Server 3D圖那樣的動畫
    what：19 個場景全部加上運轉動畫。動的是零件與能量不是鏡頭。三個讓動作符合物理的旋鈕：
          反向（供電與訊號相反）、雙向（交流充放電真的會反向）、閘控（截止時電流是 0）
    state：done ｜ ver：104 ｜ go：#industry/ai_server

29. quote：題材分頁 每個題材的圖都需要優化的更細緻點，只需要提供圖片給讀者閱讀即可 → 題材 2D 圖修正 暫時 OK 先照那格式下去做
    what：18 張全部重畫。判準是「關掉文字標籤也要認得出每一格是什麼」。
          13 筆寫死色碼歸零、會呼吸的發光節點 224→0、畫布 1180→980
    state：done ｜ ver：104 ｜ go：#themes

30. quote：若缺資料網路找，CEO 安排
    what：`supply_chain.yaml` 補上軟體 5 格、金融 3 格環節與 32 家公司。
          那七張新圖掛上環節，點零件會篩出對應公司
    state：done ｜ ver：104 ｜ go：#industry/software
    note：金融刻意 0 條關係線 —— 既有四種型別表達不了「資金中介」，硬套會畫出假關係

31. quote：以後做到一個段落，就先部署，而其他未完成的繼續執行，幫我多新增一個Agent 專門部屬的
    what：新增 deployer 專職部署 Agent；CLAUDE.md 加最高優先的一條流程規則
    state：done ｜ ver：104 ｜ go：（流程，不在畫面上）

---

## 還沒結束的

32. what：12 張剖析圖收窄後，13 條結構斷言仍對不上。已從 38 條收斂到 13 條
    state：wip
    note：其中三個是真回歸，根因都已定位到行 —— 閱讀模式字級掉回 12px、
          事件抽屜開著時說明卡掉回單欄（差 12px 的算術誤差）、切主題後選取被清掉

33. what：金融鏈 20 個節點全部沒有關係線，關聯圖會出現 20 張問號卡
    state：ask
    note：資料上是誠實的，但畫面觀感要你決定。要的話改成金融鏈不畫那張關聯圖

34. what：輪動時鐘「最外圈只有一個族群」這條驗收今天紅
    state：next
    note：是資料相依的斷言 —— 今天的盤最大半徑只有 0.743，沒有任何族群跑到最外圈
