# 精選文章視覺手冊（撰寫 agent 照做，2026-10-17）

Andy 10-17：「以後內容都需要搭配圖表，需要自己發想，例如他跟過去金融海嘯差別，有沒有可以量化的數據」「觀眾大多為視覺系生物，對圖片圖表敏感度高於文字，所以需要適當的放入可視化數據與圖片輔助」。
流程、字數上限與成本照 `fast_path.md`；**這份只管「放什麼圖、數字怎麼找、標題怎麼下、怎麼評分」**。兩份衝突時，圖表數量以這份為準（`production_guide.md`「每篇最多 3 張圖」已被這份取代）。

## 0. 反面教材：#8〈費半連續下跌，是金融海嘯重演嗎？〉為什麼只有 45 分

| 問題 | 實際長相 | 應該怎麼做 |
|---|---|---|
| 0 張數據圖 | 1 組數字卡＋1 張文字表，其餘全是段落 | 至少 3 張圖，第一屏就有走勢圖 |
| 標題問了「是不是 2008」，內文沒有量化回答 | 對照表左欄 2008、右欄寫「本文查到的報導沒有…」 | 用同一把尺比：跌幅、天數、VIX、失業率、信用利差各一個數字 |
| 比較基準不同口徑 | 標普 500 −57% 對費半 −10% | 費半比費半、從高點起算比從高點起算 |
| 本站資料完全沒用 | 「對台股族群的意義」只有一段文字 | 用資料湖算半導體各族群同期漲跌＋外資買賣超，畫成兩張圖 |
| 承認「沒查到信用利差」就停 | 黃框寫「不能說風險已排除」 | 換來源再查（FRED 高收益債利差），查完畫出來 |

重做骨架示範（照這個思路發想其他題）：
1. 鉤子圖 `chart line`：費半近 60 個交易日收盤，`marks` 標 10/14「CPI 公布」→ 回答「跌了多少、從哪天開始」。
2. 核心對比 `chart hbar`：費半歷次從高點最大跌幅（2000、2008、2020、2022、本次），本次 `highlight` → 回答「這次在歷史上算多大」。
3. 核心對比 `compare` 兩欄（2008／現在），每列都是數字：VIX、美國失業率、高收益債利差、聯準會利率方向 → 回答「金融體系有沒有出事」。
4. 台股連結 `chart hbar`：本站半導體 8 個族群同期漲跌 → 回答「台股哪幾段跌最多」。
5. 結論圖 `chart bar`：外資近 6 日對各族群買賣超（張）→ 回答「錢是不是在撤」。

## 1. 視覺骨架（每篇都照這個排）

| 位置 | 放什麼 | 規則 |
|---|---|---|
| 第 1 區塊 | `h` 三句話重點＋`ul` 三條 | 沿用舊規定，三條都要帶數字，**每條 ≤ 45 字** |
| 緊接著（第一屏） | **鉤子圖**：`ul` 的下一個區塊**就是**視覺：快訊 `chart`、產業鏈 `flow`、知識 `illus`／`chart`；`kpi` 只在沒有走勢可畫時用 | 讀者滑到這裡就看到「發生什麼、多大」。中間不准夾 `h`、`p`。模板見 1-2 |
| 中段 | **核心對比圖** 1～2 張 | 回答標題的那個問題（跟過去比、跟同業比、預期與實際比） |
| 中後段 | **台股連結圖** 1 張，**必須用本站資料** | 族群漲跌、法人買賣超、營收、估值位置……這是競品沒有的 |
| 結尾前 | **結論圖**或「接下來看什麼」的時間軸（`steps`） | 收在可追蹤的日期與指標，不收在建議 |

數量與比例（不含 `kpi`、`table`、`stocks`）：

| 類型 | 數據圖（`chart`） | 其他圖（`compare`／`flow`／`steps`／`stack`／`illus`／`video`） | 合計 | 內文字數 |
|---|---|---|---|---|
| 快訊 news | **≥ 3**（建議 3～4） | 0～2 | 4～6 | ≤ 600 |
| 產業鏈／介紹 intro | **≥ 2** | ≥ 2（其中 1 張 `flow` 或 `illus`） | 4～6 | ≤ 900 |
| 知識 know | **≥ 2** | ≥ 2（`steps`／`illus`／`compare`） | 4～6 | ≤ 900 |

- **第一屏預算（2026-10-19 稽核：8 篇在 390 手機第一屏都看不到任何圖）**：頁首會依序畫標題、`subtitle`、族群膠囊、`tags`、`summary`（引言框）再到內文，所以這幾欄要短：`subtitle` ≤ 24 字、`summary` ≤ 60 字且**不重複三句話重點**（寫成一句「這篇回答什麼問題」）、`groups` ≤ 3、`tags` ≤ 4。用 5-1 自檢程式量。
- **每個 `h` 小節至少一個視覺**（圖、kpi 或表）；連續兩段 `p` 中間沒有視覺就拆。段落 ≤ 120 字。
- 圖的 `title` 寫成**一句結論**，不是名詞：寫「費半 6 天跌 10%，是 7 月以來最深」，不寫「費半走勢」。
- 每張圖只回答**一個問題**；動筆前先在草稿列「圖 → 回答的問題 → 資料來源」，答不出問題的圖不放。
- `note` 一句口徑（單位、起訖日、加權方式）；`source` 寫發布者與日期（例：「本站整理自證交所，2026-10-16」）。
- 同一件事不用兩張圖講；`kpi` 最多 1 組（4 格）、`table` 最多 1 張且要有數字，不准只有文字。
- 台股紅漲綠跌：漲跌、買賣超這種有正有負的圖一律加 `"signed": true`（正紅負綠，網站同一組 `--rise`／`--fall`）。

### 1-1 圖表一律照網站圖表庫的款式（2026-10-17，Andy：「圖表風格需要 Follow 我網頁內的風格」）

文章的 `chart` 區塊**不另外設計一套**，長相一律照 `docs/chart_library.md`（範例圖在 `docs/chart_library/`），程式端已經接好，撰寫時只要選對 `kind`：

| `kind` | 對應圖表庫 | 會長成什麼樣 |
|---|---|---|
| `bar`／`barline` 的長條 | **C 款直條** | 單一系列一個色（網站青藍 `--cat-1`）、上實下淡漸層、只圓頂端 3px；≤ 20 根每格 50% 寬（上限 48px）、更多根 ≤ 12px；日期類別自動補月／年分隔線（E 款） |
| `hbar`／`range` | **D 款橫條** | 同一系列一個色、左淡右實漸層、只圓長出去那一端；沒有直格線，全為正值時有淡底軌、有負值時畫零軸線；名稱在左完整顯示（手機自動換行，不截斷） |
| `line`／`barline` 的折線 | 網站折線 | 線寬 2、圓點；跟長條同圖時折線從琥珀起輪（個股頁「月營收＋YoY」同一組） |
| 以時間為橫軸的任何圖 | **E 時間軸格線** | 由網站共用層自動補，不必寫 |
| （甜甜圈） | A 款 | 尚未支援，見第 7 節 #4 |

- **顏色不要自己指定**：系列色依序是網站類別色 `--cat-1`（青藍）→ `--cat-2`（紫）→ `--cat-3`（琥珀）→ `--cat-4`（萊姆）；`signed` 時長條改紅漲綠跌。不要再期待「每列不同色」—— 那是 10-16 以前文章自己的調色盤（`--art-p*`），10-17 起只剩數字卡、關係圖、流程圖等說明圖區塊在用。
- **`highlight`／`marks` 的那根**換成琥珀（C 款「被選那根換強調色」）；`signed` 圖不能換色（紅綠有意義），改成 2px 外框。
- 滑過長條：該條 2px 外框、其他維持原色；提示框是網站同一款（掛在 body、不會被卡片切掉）。
- 數字標籤、軸字一律 12px、等寬字；這些都是網站共用層決定的，**撰寫時不要在 JSON 塞樣式欄位**（會被忽略）。

### 1-2 各類別的固定配方（2026-10-19 稽核：數據圖不足 7／8 篇，知識 3 篇全部 0 張）

先照配方把「必備圖」排好，再依題目加圖；配方裡的每一張都不能用 `kpi`、`table` 或文字代替 —— **有兩個以上同單位的數字，就畫成 `chart`**（例：CoWoS 月產能 11～14 萬→17～20 萬片＝`line`／`range`，不是 kpi）。

| 類別 | 鉤子圖（`ul` 後第一個區塊） | 核心對比 | 台股連結（本站資料，必備） | 其他必備 |
|---|---|---|---|---|
| 快訊 news | `chart line`：事件主角近 20～60 日走勢，`marks` 標事件日 | `chart hbar`：跟歷史／同業／財測比，本次 `highlight` | `chart hbar`：相關族群同期漲跌（`signed`）；或 `chart bar`：外資／投信買賣超 | 有發表會、法說會、記者會 → `video`（1-4） |
| 產業鏈 intro | `flow`：供應鏈圖（3～5 欄，節點帶 `codes`） | `chart hbar`：各環節規模或成本占比／毛利率 | `chart hbar`：鏈上各族群近 20 日漲跌（`signed`） | 主角產品的 `illus`（1-3）；**不列「代表公司」表** |
| 知識 know | `illus` style:2（依站內 3D／2.5D 重畫，1-3）或 `chart` | `chart hbar`：新舊世代／替代方案的**同單位規格**（頻寬 GB/s、功耗 pJ/bit、線寬 nm、產能萬片／月） | `chart hbar`：相關族群近 60 日漲跌，或 `chart barline`：相關族群月營收年增 | `chart bar`：市場規模逐年（研調兩來源，預估年 `marks`）；`video`（1-4） |

JSON 範本（顏色、字級一律不寫，網站共用層套圖表庫 C／D／E 款與 `--cat-*`、`--rise`／`--fall` 色票；寫了也會被忽略）：

```json
{"t":"chart","kind":"hbar","title":"〈一句結論：HBM4 每疊頻寬約 2 TB/s，是 DDR5 模組的 40 倍〉","unit":"GB/s",
 "x":["DDR5-6400 模組","GDDR7 單顆","HBM3E 一疊","HBM4 一疊"],"series":[{"name":"頻寬","type":"bar","data":[51.2,128,1200,2000]}],
 "highlight":[3],"note":"口徑：單一模組／單顆／單疊理論峰值","source":"JEDEC、美光，2025-04"}
{"t":"chart","kind":"hbar","signed":true,"title":"〈一句結論：HBM 族群 60 日漲 18%，領先記憶體其他段〉","unit":"%",
 "x":["…族群名…"],"series":[{"name":"近 60 日漲跌","type":"bar","data":[18.2]}],
 "note":"成交值加權，YYYY-MM-DD 至 YYYY-MM-DD 收盤","source":"本站整理自證交所，YYYY-MM-DD"}
{"t":"chart","kind":"bar","title":"〈一句結論：市場規模 3 年擴大 2.5 倍〉","unit":"億美元",
 "x":["2024","2025","2026","2027"],"series":[{"name":"市場規模","type":"bar","data":[0,0,0,0]}],
 "marks":[{"x":"2026","text":"預估"}],"note":"研調機構 A 與 B 的數字，取兩家都寫出的年份","source":"A，YYYY-MM；B，YYYY-MM"}
```

族群近 N 日漲跌與月營收年增：照第 3 節程式，`N = 60`（知識）或 `20`（產業鏈）；月營收用 `store.read("revenue_monthly")` 依 `loader.membership()` 合計後算年增。

### 1-3 產品架構圖取用四步（知識必做、產業鏈與新產品快訊有實體產品時做）

稽核：知識 3 篇都有剖面插圖，但網站現成的 3D（`hbm`、`switch_wireless`、`semiconductor`）一張都沒用，站內連結藏在文末摺疊區。**2026-10-19 起文章有 `scene` 區塊（需求 #11 已做）可以直接嵌站內 3D／2.5D**，照這四步：

1. **查圖**：`grep -n "<產品關鍵字>" docs/articles/diagram_inventory.md`，拿到圖 id、類型（3D／2.5D）、路由。3D 優先，其次 2.5D。
2. **嵌入**：放一塊 `scene`（欄位見 `production_guide.md`「`scene` 區塊」），`id` 就是 inventory 那一欄：
   ```json
   {"t": "scene", "kind": "3d", "id": "semiconductor", "title": "CoWoS-L：晶片與 HBM 並排在中介層上", "caption": "拖曳旋轉，點零件看名稱。"}
   ```
   2.5D 用 `"kind": "25d"`（例 `"id": "cowos"`、`"silicon_photonics"`、`"hbm_memory"`）。3D 與 2.5D 都有的產品可以各放一塊（3D 看結構、2.5D 看供應鏈），每篇最多 2 塊。
   inventory 沒有、只能重畫的（例 SSD／NAND）才走下面的「重畫」。
2-1. **重畫（選做；inventory 沒有圖時必做）**：用 `illus`（`"style": 2`、`kind:"custom"`）照該站內圖的**層次與零件名稱**重畫（零件名稱與站內圖一致，讀者點過去才對得起來）；零件 ≥ 6 個、mat ≥ 5 種（`illus_style.md` 2.1）。內建 kind 有 `cowos`、`rack` 的直接用，加 `"style": 2`。
3. **導流**：用了 `scene` 就不必另寫 `callout`（區塊下方自帶「在站內完整頁面看 ↗」）；只有重畫的 `illus` 才在下一個區塊放 `callout`：「想轉著看？本站有可旋轉的 3D 版：產業地圖 → 〈族群名〉 → 剖析圖（3D）」，文字裡不放網址（`callout` 不渲染連結）。
4. **連結**：`site_links` **第一個**放該圖的路由（例 `{"label":"HBM 3D 剖析圖","hash":"#industry/group/hbm"}`）。
inventory 沒有的產品（例 SSD／NAND）：照 inventory 第四節，用 `custom` 重畫或改 `steps`／`compare`，並在交件寫「站內無架構圖」。

### 1-4 影片搜尋兩步（快訊、知識都要找；最多 2 次 WebSearch，算在 10 次內）

稽核：8 篇 0 支影片，連特斯拉發表會、台積電法說會都沒附。

1. **第 1 次**：`<事件或產品英文名> <活動名> youtube`（例：`Tesla Roadster unveiling 2026 youtube`、`TSMC Q3 2026 earnings call youtube`、`HBM explained youtube`）。知識類用「`<產品> explained`」或「`<產品> 是什麼 影片`」。
2. **第 2 次**：換中文或換平台關鍵字（`<事件> 發表會 影片`、`<產品> 動畫 原理`）；兩次都出現**同一支**（相同 11 碼 id）或標題明確寫那場活動、片長 3～25 分鐘 → 採用。
3. 放在**核心對比圖之後**（不搶鉤子圖位置），`{"t":"video","provider":"youtube","id":"<11 碼>","title":"<一句話說看什麼>","source":"<上傳者>（非官方加「轉載，非官方」）","date":"YYYY-MM-DD"}`；排除條件照 `production_guide.md` 影片區塊。
4. 兩次都找不到 → 不放，交件寫「影片：搜 2 次未找到（關鍵字 A、B）」，不扣 A 分但 CEO 看得到。

## 2. 圖表發想清單（依題型挑，挑不到就從「讀者第一個會問什麼」反推）

可用區塊（只准用這些）：`chart` 的 `kind` = `bar`／`line`／`barline`（雙軸用 `series[i].axis:1`）／`hbar`／`range`（區間，`data:[[低,高]]`）；選填 `highlight:[索引]`、`marks:[{x,text}]`、`unit`、`y2unit`、最多 4 條 `series`。另有 `kpi`、`table`、`compare`、`flow`、`steps`、`stack`、`illus`（`style:2`）、`video`。

### 2-1 快訊（市場事件、總經、法說、營收）

| 題型 | 圖 | 區塊 | 需要的數據 | 去哪找 |
|---|---|---|---|---|
| 大跌／大漲「跟 2008（或 2000、2020、2022）比」 | 歷次最大跌幅 | `chart hbar`，本次 `highlight` | 各次高點→低點跌幅 % | WebSearch「費半 歷次 跌幅」＋第二來源；本次用 `intl_daily` 自己算 |
| 〃 | 跌了幾天、修復幾個月 | `chart hbar` 兩張或 `table` | 下跌天數、回到前高月數 | 媒體整理（經濟日報引 Bloomberg 有修復時間） |
| 〃 | 金融體系壓力對照 | `compare` 兩欄，每點都是數字 | VIX、失業率、高收益債利差、政策利率 | VIX：`intl_daily ^VIX`（2025-09 起）；失業率、利率：`macro`（2015 起）；2008 的值與信用利差：WebSearch FRED |
| 〃 | 同一起點的走勢路徑 | `chart line`，x＝「高點後第 N 天」，每次一條 `series`（≤ 4） | 每段的日收盤，換算成起點＝100 | 本次：`intl_daily`；歷史：資料湖沒有，需資料單位補（第 7 節）——補好前改用上一列的 `hbar` |
| 總經數字公布（CPI、非農、利率） | 近 12～24 期走勢＋本期 `marks` | `chart line` 或 `barline`（實際值柱＋預期線） | 每月數值、市場預期 | `macro`（CPILFESL、PAYEMS、UNRATE…）；預期值 WebSearch 兩來源 |
| 〃 | 降息／升息機率 | `chart bar` | FedWatch 各選項機率 | WebSearch（註明查詢日） |
| 法說會 | 營收、毛利率趨勢 | `chart barline`（營收柱＋毛利率線，`axis:1`） | 近 8 季營收、毛利率 | 公司法說簡報（WebSearch）＋ `financial_q` |
| 〃 | 財測 vs 實際 | `chart range`（財測區間）＋`marks` 標實際值 | 上季財測上下緣、實際值、本季新財測 | 法說新聞稿兩來源 |
| 〃 | 營收結構（製程、平台、地區） | `chart hbar`（占比 %） | 各項占比 | 法說簡報 |
| 月營收 | 月營收＋年增率 | `chart barline` | 近 13～24 個月 | `revenue_monthly`（不用上網） |
| 〃 | 同族群誰成長最快 | `chart hbar` | 族群成分股年增率 | `revenue_monthly` ＋ `loader.membership()` |
| 新產品／發表會 | 規格對照 | `table` 或 `compare` | 新舊代規格（製程、頻寬、功耗） | 原廠新聞稿＋媒體 |
| 〃 | 時間軸（發表→量產→出貨） | `steps`（`icon` 用 chip／factory／truck／clock） | 各里程碑日期 | 原廠、法說 |
| 〃 | 產品剖析 | `illus style:2` | 結構查證 | 照 `illus_style.md` |
| 〃 | 供應鏈誰受惠 | `flow`（節點帶 `codes`） | 環節、族群 | `supply_chain.yaml`／`groups.yaml` |
| 任何市場事件 | **台股各族群同期漲跌** | `chart hbar` | 族群漲跌 % | 本站資料（第 3 節範例） |
| 〃 | **外資／投信對族群買賣超** | `chart bar` 或 `hbar` | 法人買賣超（張） | `inst_daily` |
| 〃 | 融資變化（散戶情緒） | `chart bar` | 族群融資增減 | `margin_daily` |
| 〃 | 估值在歷史哪裡 | `chart range`（近 5 年本益比高低區間）＋`marks` 現值 | 本益比 | `valuation_daily` |

### 2-2 產業鏈／介紹（某產業、某技術、某公司）

| 題型 | 圖 | 區塊 | 數據與來源 |
|---|---|---|---|
| 這個產業有多大、長多快 | 市場規模逐年 | `chart bar`（`marks` 標預測年） | 研調機構數字（兩家都寫出來，對不上就用 `range`） |
| 上中下游是誰 | 產業鏈 | `flow`（3～5 欄） | `supply_chain.yaml`、法說 |
| 錢在哪一段 | 各環節毛利率比較 | `chart hbar` | 各公司財報毛利率（`financial_q` 或公告） |
| 台股這條鏈最近表現 | 鏈上族群近 20 日漲跌 | `chart hbar` | 本站資料 |
| 這個東西長什麼樣 | 剖析圖 | `illus style:2` | 照 `illus_style.md` |
| 技術新舊世代差在哪 | 規格對照 | `compare` 2～3 欄 | 原廠、技術文件 |

### 2-3 知識（名詞解釋、指標怎麼看）

| 題型 | 圖 | 區塊 | 數據與來源 |
|---|---|---|---|
| 這個指標怎麼算 | 計算步驟 | `steps` | 定義來源（官方說明） |
| 指標過去長怎樣 | 長期走勢＋高低點 `marks` | `chart line` | `macro`、`intl_daily`、`market_daily` |
| 高的時候、低的時候大盤怎樣 | 分組平均 | `chart bar` | 本站資料自己算，`note` 寫「歷史統計，不代表未來」 |
| A 跟 B 差在哪 | 對照卡 | `compare` | 官方定義 |
| 結構、製程 | 剖析圖／流程 | `illus`／`steps` | 結構查證 |

## 3. 可量化數據：怎麼找、怎麼驗

**先用本站資料，再上網。** 資料湖在 `data/`（雲端每天 commit，開工先 `git pull`）；`site/data/*.json` 是本機舊建置，**不要拿來當最新數字**。

| 資料表（`store.read`） | 內容 | 起始 |
|---|---|---|
| `price_daily` | 個股日收、成交值 | 深歷史 |
| `inst_daily` | 三大法人買賣超（`foreign_total`、`trust`、`dealer`，單位：股，÷1000＝張） | 2016 |
| `margin_daily` | 融資融券 | 有 |
| `revenue_monthly` | 月營收、月增、年增 | 有 |
| `valuation_daily` | 本益比、殖利率、淨值比 | 有 |
| `market_daily`／`index_daily` | 加權指數、類股指數 | 有 |
| `intl_daily` | `^SOX` `^GSPC` `^IXIC` `^VIX` `^TWII` `DX-Y.NYB` `TWD=X` | **2025-09 起** |
| `macro` | FRED：CPI、核心 CPI、PCE、非農、失業率、聯邦基金利率、10 年債、10Y-2Y | 2015 起 |
| 族群成分 | `pipeline.groups.loader.membership()`（code、group_id、group_name、chain） | — |

族群同期漲跌＋外資買賣超（**實測可跑**；站上族群頁用成交值加權，文章同口徑）。程式放 scratchpad，在 repo 根目錄用 `PYTHONPATH=. python3 <檔>` 跑：

```python
from pipeline.util import store
from pipeline.groups import loader
N = 6  # 近 N 個交易日
px = store.read("price_daily", years=[2026])[["date", "code", "close", "turnover"]]
days = sorted(px.date.unique())[-(N + 1):]
w = px[px.date.isin(days)]
c = w.pivot(index="date", columns="code", values="close"); ret = (c.iloc[-1] / c.iloc[0] - 1) * 100
tv = w[w.date.isin(days[1:])].groupby("code").turnover.sum()
m = loader.membership().assign(r=lambda d: d.code.map(ret), tv=lambda d: d.code.map(tv)).dropna()
grp = m.groupby("group_name").apply(lambda g: (g.r * g.tv).sum() / g.tv.sum()).round(2)
inst = store.read("inst_daily", years=[2026]); inst = inst[inst.date.isin(days[1:])].merge(loader.membership(), on="code")
fx = (inst.groupby("group_name").foreign_total.sum() / 1000).round(0)  # 張
print(days[0], "→", days[-1]); print(grp[grp.index.str.contains("晶圓|封裝|ASIC")]); print(fx[fx.index.isin(grp.index)].sort_values().head(8))
```

上網查的數字（WebSearch，只看得到摘要）：
1. **兩個獨立來源**對得上才畫（同一篇稿被轉載不算兩個）。對不上：用 `range` 畫區間或兩個都寫並標來源，不挑順眼的。
2. 每個數字寫清楚**單位、日期、口徑**：「費半（PHLX Semiconductor）收盤、2026-10-07→10-16、從近期高點起算」。
3. **比較要同一把尺**：同一個指數、同樣「高點→低點」、同樣頻率（月對月、季對季）。尺不同就不比，或 `note` 寫明。
4. 數字要確認**是誰的**（母子公司、合併或單一）；「中文名（英文名）」的對應一律另查。
5. 查不到：換關鍵字、換來源類型（官方／媒體或資料平台／同業網站）再查；總次數用完仍查不到，就**換一張查得到的圖**，不要寫「本文未查到」當結論。
6. 歷史統計一律加「歷史統計，不代表未來」；預測值（研調、財測）`marks` 標「預估」。
7. 交件時附「數字清單」：每個上圖的數字 → 來源 1、來源 2（或「本站資料表＋程式」）。

## 4. 標題與開頭鉤子（要流量，不准聳動不實）

社群研究結論（第 8 節）：讀者先看圖、再看數字、最後才看字；「跟歷史比」與「一張圖看懂」是財經媒體反覆使用的格式。

**標題公式（挑一個，≤ 26 字）**
| 公式 | 例子 |
|---|---|
| 數字＋對照 | 費半 6 天跌 10%：跟 2008 年差在哪 5 個數字 |
| 問題＋答案先給 | 這次是金融海嘯嗎？信用利差說還不是 |
| 一張圖看懂 | 一張圖看懂：晶圓代工第三季錢從哪裡來 |
| 反差 | 營收創新高，股價卻跌了 8%：法說會講了什麼 |
| 清單 | AI 伺服器 5 個零件，台股各由誰做 |
| 知識：一張圖＋倍數 | 一張圖看懂 HBM：頻寬是 DDR5 的 40 倍 |
| 知識：問題＋數字答案 | CPO 是什麼？每位元省電 70% 的光引擎 |
| 知識：痛點 | CoWoS 為什麼永遠不夠？產能兩年翻 1.5 倍 |

**知識類不准只寫「X 是什麼？」**（稽核：知識 3 篇標題都沒有數字，G 項全部 5 分）：要帶一個倍數、百分比或規模，數字要在鉤子圖或第一個核心對比圖裡看得到。

**一定要**：標題裡的數字在內文第一屏看得到、有來源；問句標題在三句話重點的第一條就給答案。
**不准**（`docs/launch_gap_legal_1009.md` 第三節）：「崩盤」「血洗」「末日」等誇大字眼（事實就是單日最大跌幅時寫數字，不寫形容詞）；「該上車」「進場時機」「低點到了」「必漲」「穩賺」「翻倍」；點名個股的「值得關注」「資金流入這檔」；「受惠」「概念股」；標題以族群或產業為主詞，公司名只在報導該公司自己公告的事實（月營收、法說會）時出現（法遵 2026-10-18 審 growth_plan_1018 時提出）；目標價、勝率、報酬率；「最準」「獨家」等無法證明的最高級。`stocks` 區塊只列「依本站族群分類的成分股」，`why` 寫它屬於哪個環節，不寫看好理由。

**開頭鉤子**：三句話重點第一條＝最驚人的那個數字＋時間範圍；緊接著就是鉤子圖。不寫「近日市場關注」這類空句。

## 5. 品質評分表（CEO 審稿用，滿分 100）

| 項目 | 分 | 給分標準 |
|---|---|---|
| A. 數據圖數量 | 15 | 達第 1 節下限 15；少 1 張 8；少 2 張以上 0 |
| B. 每張圖回答一個問題 | 10 | 標題是結論句、問題沒重複，每張 2 分（最多 10） |
| C. 鉤子圖在第一屏 | 5 | 三句話重點後第一個區塊就是圖或 kpi |
| D. 本站資料圖 | 10 | 至少 1 張用資料湖算的圖 10；沒有 0 |
| E. 量化對照 | 15 | 標題的問題有同口徑數字回答 15；只有文字對照 5；沒有 0 |
| F. 數字可信 | 15 | 每個數字有兩來源或本站資料、單位日期口徑齊 15；缺 1 個扣 5 |
| G. 標題與鉤子 | 10 | 符合第 4 節公式、數字在第一屏 10 |
| H. 可讀性 | 10 | 字數在上限內、段落 ≤ 120 字、每小節有視覺 10；每違反一項扣 3 |
| I. 畫面 | 10 | 1440／390 截圖無重疊、無空白圖、手機看得到數字 10 |

- **一票否決**（直接退件，不計分）：違反第 4 節「不准」任一條、數字沒有來源、圖表數值與來源不符、畫面有重疊。
- **≥ 75 分上架**；60～74 退一次（附扣分項）；< 60 退一次並要求換角度。
- 第二次仍 < 75：刪掉扣分的那幾張圖或段落後重算，≥ 70 就上架；否則該篇標 `failed`、寫原因，不跑第三輪。
- 評分寫進交件回報一行：「評分 82（A15 B8 C5 D10 E15 F10 G10 H6 I10）」。

### 5-1 交件自檢（撰寫 agent 交件前必跑；CEO 審稿也先跑一次，約 1 秒）

```bash
python3 - <全文.json> <<'EOF'
import json,sys;d=json.load(open(sys.argv[1]));B=d["blocks"];cat=d["cat"]
V={"chart","compare","flow","steps","stack","illus","video","kpi","table"};O={"compare","flow","steps","stack","illus","video"}
ch=sum(b["t"]=="chart" for b in B);ot=sum(b["t"] in O for b in B);need={"news":(3,0),"intro":(2,2),"know":(2,2)}[cat]
ul=next(i for i,b in enumerate(B) if b["t"]=="ul");first=B[ul+1]["t"] if ul+1<len(B) else "-"
sec,bad=None,[]
for b in B+[{"t":"h","text":"END"}]:
    if b["t"]=="h":
        if sec and not sec[1] and sec[0] not in("三句話重點","END"): bad.append(sec[0][:12])
        sec=[b.get("text",""),False]
    elif b["t"] in V|{"stocks"} and sec: sec[1]=True
longp=[len(b["text"]) for b in B if b["t"]=="p" and len(b["text"])>120]
words=sum(len(b.get("text","")) for b in B if b["t"] in("p","callout"))+sum(len(x) for b in B if b["t"]=="ul" for x in b["items"])
lim={"news":600,"intro":900,"know":900}[cat]
chk=[("數據圖",ch>=need[0],f"{ch}/{need[0]}"),("其他圖",ot>=need[1],f"{ot}/{need[1]}"),("合計4～6",4<=ch+ot<=6,ch+ot),
 ("鉤子圖緊接三句話",first in("chart","illus","flow","kpi"),first),("本站資料圖",any(b["t"]=="chart" and "本站" in b.get("source","") for b in B),""),
 ("影片",any(b["t"]=="video" for b in B),"沒有就要在交件寫搜過的關鍵字"),("小節都有視覺",not bad,bad),("段落≤120",not longp,longp),
 ("字數",words<=lim,f"{words}/{lim}"),("標題≤26",len(d["title"])<=26,len(d["title"])),("標題有數字",any(c.isdigit() for c in d["title"]),""),
 ("subtitle≤24",len(d.get("subtitle",""))<=24,len(d.get("subtitle",""))),("summary≤60",len(d.get("summary",""))<=60,len(d.get("summary",""))),
 ("groups≤3",len(d.get("groups",[]))<=3,len(d.get("groups",[]))),("tags≤4",len(d.get("tags",[]))<=4,len(d.get("tags",[])))]
if cat=="know": chk.append(("架構圖illus style2",any(b["t"]=="illus" and b.get("style")==2 for b in B),""))
if cat=="intro": chk.append(("供應鏈圖",any(b["t"] in("flow","stack") for b in B),""))
for n,ok,v in chk: print("✓" if ok else "✗",n,v)
EOF
```

- 任一 ✗（「影片」除外，影片 ✗ 要在交件寫搜過的關鍵字）→ 先補再交；`字數` 只算 `p`／`callout`／`ul`，圖表內文字不算。
- 這支只量「形」，A～I 的「質」（結論句、同一把尺、兩來源）仍由 CEO 照上表評。

## 6. 成本（與 `fast_path.md` 一致）

| 步驟 | 誰 | 模型 | token 上限 |
|---|---|---|---|
| 選題角度＋圖表企劃（列 4～6 張圖：問題／區塊／資料來源） | 撰寫 agent 第一步 | 便宜模型（sonnet） | 2 萬 |
| 本站數據（Python 讀資料湖） | 撰寫 agent | sonnet | 3 萬（程式算，不把整張表印進對話；只印結果） |
| 上網查證（WebSearch ≤ 10 次） | 撰寫 agent | sonnet | 6 萬 |
| 寫 JSON＋截 2 張圖＋自評分 | 撰寫 agent | sonnet | 6 萬 |
| 審稿（評分表＋2 張截圖＋數字清單） | CEO（排程對話） | 排程對話本身的模型（好模型值得花在這裡） | 5 萬 |
| 退件重做（最多 1 次） | 撰寫 agent | sonnet | 5 萬 |
| **合計** | | | **約 22～30 萬，上限 35 萬** |

省錢規矩：只讀這份與 `fast_path.md`；範本只讀一篇舊文章；資料湖用 Python 算完只印要畫的那幾個數字；截圖照舊 2 張；插圖只套現成積木。

## 7. 需要網頁／資料單位新增的（需求清單，撰寫 agent 不改程式）

| # | 需求 | 誰 | 理由 | 優先 |
|---|---|---|---|---|
| 1 | ✅ 2026-10-17 已做：`chart` 長條**正負上色**（`"signed": true`，別名 `sign` → 正紅負綠，台股慣例；格式見 production_guide.md 的 chart 欄位表） | 網頁 | 漲跌、買賣超圖現在正負同色，一眼看不出誰跌 | 高 |
| 2 | ✅ 2026-10-17 已做：`chart` **參考線與區間**（`refs:[{y,label}]`，hbar 用 x；`bands:[{from,to,label}]`；`text` 也收） | 網頁 | 「2008 年 VIX 高點在這」「升息期間」這類對照最常用 | 高 |
| 3 | **分享封面圖**：每篇自動產生 1200×630 圖卡（標題＋鉤子數字＋鉤子圖），寫進 `og:image` | 網頁 | 社群轉貼時第一眼只看到這張圖，直接決定點擊 | 高 |
| 4 | `chart kind:"donut"`（照圖表庫 A 款，用網站 `App.donut` 同一份規格；10-17 統一風格那批沒做，列為後續） | 網頁 | 營收結構、市占占比 | 中 |
| 5 | `heat` 熱力格（列＝族群、欄＝日期，紅綠深淺） | 網頁 | 「這幾天哪些族群一直跌」一張圖看完 | 中 |
| 6 | `timeline` 有日期刻度的時間軸（間距照實際日期） | 網頁 | `steps` 間距固定，看不出「三天內連發」 | 低 |
| 7 | 資料湖補長歷史：`^SOX` `^GSPC` `^VIX` 回補到 2000 年；FRED 加 `BAMLH0A0HYM2`（高收益債利差）、`VIXCLS` | 資料 | 「跟 2008 比」的路徑圖與信用利差目前只能靠上網查摘要 | 高 |
| 8 | `scripts/article_data.py`：一行指令輸出「族群 N 日漲跌／法人買賣超／營收年增」的 chart JSON | 資料 | 撰寫 agent 不必每篇重寫程式，省 token、口徑一致 | 中 |
| 9 | ✅ 2026-10-17 已做：文章圖表統一成網站圖表庫款式（C 直條／D 橫條／E 時間軸，見 1-1） | 網頁 | Andy：「圖表風格需要 Follow 我網頁內的風格」 | 高 |
| 10 | ✅ 2026-10-19 已做（分支 art-ui）：手機文章頁副標／族群／標籤／摘要收成一顆「導讀・相關族群」（預設收起、點了展開、記住），麵包屑收掉；原需求：手機（≤ 640）文章頁：`summary` 引言框與 `tags` 預設收起，或把 `ul` 後第一個視覺提到引言框前 | 網頁 | 2026-10-19 稽核：8 篇在 390 第一屏都看不到圖，頁首吃掉整屏（`quality_audit_1019.md`） | 高 |
| 11 | ✅ 2026-10-19 已做（分支 art-ui），區塊名定為 `scene`：`{"t":"scene","kind":"3d"|"25d","id":"…","title":"…","caption":"…"}`（用法見 1-3、production_guide.md）；原需求：`sitefig` 區塊：`{"t":"sitefig","kind":"3d"|"25d","id":"hbm","title":"…"}` 在文章內直接嵌站內 3D 場景（`three3d.js` `SCENES`）或題材 2.5D 圖（`themes3d.js`），可旋轉，手機給靜態圖＋「轉著看」鈕 | 網頁 | Andy 10-19「知識需要有該產品架構圖 2.5D 3D，可以從我網站內素材拿」；現在只能重畫＋導流（1-3） | 高 |
| 12 | Worker 機器路由加 `op:'get_body'`（`ARTICLE_PUT_KEY` 可用、只讀） | 網頁 | 品質稽核與重做要讀回已上架全文；10-19 稽核有 3 篇讀不到 | 中 |

## 8. 社群研究摘要（2026-10-17，WebSearch 10 次，只讀得到摘要）

1. **「跟歷史比」是財經媒體的固定格式，而且比的是同一把尺**：TVBS 整理台股自 1990 年至少 11 次股災、強調「看跌幅百分比不要看跌點」；經濟日報引 Bloomberg 比較修復時間（2008 約 77 個月、2020 約 4 個月）；商周轉載的股災回顧附多張圖。來源：news.tvbs.com.tw/money/3260284、money.udn.com/money/amp/story/5607/9358273、smart.businessweekly.com.tw/Reading/IndepArticle.aspx?ID=6018877。
2. **年輕投資人在 IG、Dcard、Threads，格式偏輪播圖卡與短句**：資策會 MIC 指 18～34 歲主力平台是 IG、Dcard、Threads；輪播貼文互動率略高於單張圖（SEJ 分析近 300 萬則：1.92% 對 1.74%，資料偏舊）；Threads 適合短句、對話式。來源：news.tvbs.com.tw/english/2477627、searchenginejournal.com/instagram-carousels/379311、vocus.cc/article/6923c2b2fd8978000176157a。
3. **「一張圖看懂＋豐儉由人」**：天下「一張圖看懂經濟」系列把單一指標濃縮成一張圖；數據新聞討論主張「一般讀者一眼看到大方向，有心的讀者挖得到細節」——對應本站「圖標題寫結論、滑過看數字」。另：金管會與投信投顧公會 2024 起收緊財經網紅推薦，文案必須守第 4 節。來源：cw.com.tw/author/6443、businesstoday.com.tw/article/category/80393/post/201702160034、finance.technews.tw/2024/05/22/influencer-marketing-etf/。
⚠ 沒查到台灣財經帳號的互動率實測數字；圖片優於純文字的業界統計方法不透明（Fanpage Karma 甚至發現無字乾淨圖互動較高），所以本手冊用「每張圖回答一個問題」而不是「圖越多越好」。
