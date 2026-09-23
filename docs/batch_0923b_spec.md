# 批次 0923-B 規格書（Andy 2026-09-23 第二批，五件）

Andy 原話（逐字）：
> 連接器少了3D圖 請補上，另外幫我將設定改成右上角
> AI 伺服器機櫃與 GPU 運算托盤 2D請 Follow 其他族群風格更新
> 下方成分股欄位拿掉
> 圖四圖五 族群版面格式需要Follow AI 伺服器 那樣，點擊AI 伺服器進去就直接看到第一個族群的2D圖3D圖

依 DECISIONS #249（CLAUDE.md ★★★★★）：**一次全部做完再回報，中途不給看、不問**。

---

## 現況盤點（機器查出來的，不是印象）

`site/dg/*.js` 共 19 張族群層級剖析圖 ＋ `site/diagrams.js` 的 `mlcc`（族群層級）
與 `ai_server`（鏈層級），合計 21 個檔位。其中 **`scene:` 還是 `null` 的只剩三張**：

| 檔位 | 檔案 | 所屬鏈 | 中文名 |
|---|---|---|---|
| `ai_interconnect` | `site/dg/ai_interconnect.js:421` | `ai_server` | 高速連接器與互連 |
| `heavy_electric` | `site/dg/heavy_electric.js:555` | `infrastructure` | 重電：變壓器與 GIS |
| `petrochemical` | `site/dg/petrochemical.js:541` | `traditional` | 石化：輕油裂解 |

Andy 這次只點名連接器，但他 2026-09-23 早上已經下過
「**所有 2D 圖都要補上 3D 圖且風格一樣**」——
依 CLAUDE.md「他已經下過的指令不准再問一次」，**三張一起補**。

`site/three3d.js` 現有 18 個 SCENES（`ai_server` … `power_inductor`）。

---

## W1 — 補三個 3D 場景

### W1-1 `ai_interconnect`（高速連接器與互連）★ Andy 點名
場景要看得出「為什麼它叫高速連接器」，四件事缺一不可：
1. **屏蔽金屬籠（cage）** —— 高速連接器的識別特徵，為了擋 EMI 才存在。
2. **塑膠舌片＋舌片上的金手指** —— 差動對成對排列，看得出「對」不是「單根」。
3. **背面壓接針／貼片腳** —— 連到 PCB 的那一端。
4. **飛越纜線（flyover cable）** —— 從晶片旁的小連接器架空拉到籠架背面，繞開 PCB 損耗。

`site/three3d.js:2359` 已有現成的 `kind` 註解與幾何思路（高速連接器：籠 ＋ 舌片 ＋
金手指 ＋ 壓接針），直接沿用，不要另起一套。

### W1-2 `heavy_electric`（變壓器與 GIS）
油箱／鐵心／繞組／套管／散熱片；GIS 是金屬封閉的管狀匯流排。

### W1-3 `petrochemical`（輕油裂解）
裂解爐管、急冷塔、分餾塔群、球槽。旋轉對稱體多，靠**高度差與管線走向**做層次。

### 三張共同規格（不准放寬）
- 材質一律走 `FAMILY_PBR` 既有 token（`metal`/`alu`/`cu`/`pcb`/`cer`/`si`/`organic`/
  `emc`/`plastic`/`glass`），**不准寫死色碼**。
- 模組之間 CIE76 ΔE ≥ 25（`DG3D_DE_MIN`），關掉文字標籤也要分得出來。
- 預設收攏、游標移入才爆開（`expT` / `EXP_IN` / `EXP_OUT`，DECISIONS #246），跟既有 18 個一致。
- 每個零件的 `seg` 要對得上 `supply_chain.yaml` 的環節 id，`part` 要對得上 2D 圖的
  `data-part`（alias 機制見 SCENES 檔頭）。
- 補完把對應 `site/dg/<id>.js` 的 `scene: null` 改成 `scene: '<id>'`，
  **並把檔頭「不做真 3D」那段註解改掉**，寫明是 Andy 2026-09-23 要求補的。
- 深色／淺色兩種模式都要保留色彩（Andy 2026-09-23 第一批已經講過）。

---

## W2 — `ai_server` 鏈層級 2D 圖改成其他族群的風格

目標檔位：`site/diagrams.js` 的 `aiServer()`（「AI 伺服器：機櫃與運算托盤」）。
它是 2026-09-21 之前畫的，**還在用寫死色碼**，跟 `site/dg/*.js` 那 19 張的
`D.fx.glass／beam／beams／shadows／glowDefs／molecule` 共用材質介面對不起來。

要做的：
1. 寫死色碼全部換成 `--dg-*` token 與 `D.fx.*`，深淺兩模式都要成立。
2. 字級吃 `--dg-fs-min`（12px 基準），行距 16px；`labelRow`／`lrow3` 照新標準。
3. 版面左右調整，不浪費空白（Andy 2026-09-23 第一批原話）。
4. **既有互動一個都不准掉**：`data-seg` / `data-part` / 點零件亮同色 / 連 3D 的 alias。

---

## W3 — 三件前端行為

### W3-1 設定列改到右上角 ★ Andy 點名
`#dgTools`（`3D 立體`／`拖曳`／`配色`／`重設視角`／`動畫`／`收合圖` 那一排 pill）
目前由 `site/industry.js` 的 `placeDgTools()` 絕對定位在**圖的右下角**。
改成**圖的右上角**。

注意：`placeDgTools()` 現在算的是 `tools.style.bottom`，有 8px 死區與
`[300,1200,3000,5000]` 的補算。改成 `top` 之後那些節流邏輯照留，
不要因為換了一個方向就把防抖動的機制一起拿掉（那是 2026-09-23 量出 −25px 才補的）。

### W3-2 下方成分股欄位拿掉 ★ Andy 點名
`site/industry.js:747-749` 那張 `<div class="card">`（`#memberTitle` / `#memWide` /
`#mktSeg` / `#memberTable` / `#memberMore`）整塊移除，連同只服務它的程式碼：
`renderMembers()`、`COLS`、`sort`、`segTw`、`memWide` 的放寬／還原、`mktSeg` 的市場篩選、
`memberMore` 的展開更多、`A.onLive($('#memberTable'…))`。

⚠ 連帶要處理的：
- **`memWide`「放寬蓋住今日事件」是 Andy 2026-09-23 早上才要求加的**（`industry.js:988`）。
  成分股表拿掉之後它沒有服務對象了，一起移除，但**要把「換頁還原事件面板」那段收尾留著**，
  不然事件面板會卡在被蓋住的狀態。
- 說明文字裡「下方成分股同步篩選」這類句子（`industry.js:728`、`:111`）要改寫，
  不能留下指向不存在的東西的說明。
- `onGroup` / 環節晶片 / 關聯圖大圓點原本會「順手篩成分股」，那條副作用要拿掉，
  但**選取狀態本身（state.group / segFilter）要留著** —— 剖析圖與關聯圖還在用它。
- `scripts/_uitest.py` 裡驗 `#memberTable` 的斷言要一起改掉，不准留著假綠。

### W3-3 點進產業鏈直接看到第一張剖析圖 ★ Andy 點名
現在 `#industry/<chain>` 落在**族群總覽**分頁（DECISIONS #252）。
Andy 要的是「點擊 AI 伺服器進去就直接看到第一個族群的 2D 圖 3D 圖」。

改法：
- `#industry/<chain>` 的預設 `dgId` ＝ `DS.chainDefault(chain) || dgOpts[0]`
  （鏈層級有圖就那張，沒有就這條鏈成交值最大的那個族群圖）。
- 族群總覽**不刪**，改成自己的網址 `#industry/<chain>/overview`，
  分頁列位置維持第一個（它是總覽，位置不動），只是不再是 Default。
- `resolveDg()` 的 `gpDrilled`（在總覽上鑽進族群時不畫圖）那條要保留。
- `syncDgHash()` 要跟著改，不然 replaceState 會把網址寫回沒有 /dg/ 的形式。
- **DECISIONS #252 要補一條修正**，寫明是被 2026-09-23 第二批蓋掉的，不要讓兩條決策打架。

---

## 驗收（照 CLAUDE.md 的對照表挑段落，不跑整輪）

| 這批碰到什麼 | 要跑的段落 |
|---|---|
| `three3d.js` 三個新場景 | `批次24-半導體鏈3D`、`批次27-AI伺服器鏈3D`、`3D風格兩模式` |
| `diagrams.js` 的 aiServer | `產業`、`產業鏈導覽`、`新-產業與個股` |
| `industry.js` 三件 | `產業`、`族群頁`、`批次29-產業分頁`、`批次25-關聯圖`、`縮放掃描`、`手機` |

- **3D 相關段落一律 `--workers 1`**（平行跑會把 CPU 吃滿、工具列按鈕 6 秒點不到，整批假紅）。
- `_preview.py` 照跑（2 分鐘，抓文字重疊與多寬度溢出）。
- 只動 `site/**` 就可以跳過 pytest；`scripts/_uitest.py` 也在例外名單裡。
  用 `git diff --name-only` 判定，不准靠記憶。
