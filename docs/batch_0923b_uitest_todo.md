# 批次 0923-B：`scripts/_uitest.py` 待改清單

由 CEO 在所有 agent 交件後**統一**改（`_uitest.py` 由產業頁那一路持有，
其餘 agent 一律不准碰，所以建議都彙整到這裡）。
⚠ 這些不是「可以之後再說」的 —— 不改就是**假綠或假紅**，兩種都比紅燈危險。

## 一、W5 半導體五張（畫布寬 980 → 660）

Andy 指定的新風格把畫布從 980 收到 660，下面全是**寫死 980** 的斷言，不改一定紅：

1. `_b14b_typo()` 的 `ok(f"{lab} 圖以原尺寸顯示（native 980…）", z["svgW"] >= 970)`
   → 改成 `>= 650`。影響 `t_b21_foundry` / `t_b21_silicon_wafer` / `t_b21_hbm` /
   `t_b14b_wbg`，每張 6 個組合。
2. `t_b14b_wbg` 的
   `_b14b_gutter(pg, "第三代", [[480,500,16,62,548],[480,500,16,564,774],[480,500,16,924,1064]])`
   → 那三條「溝」是 980 兩大框的產物，新版沒有。整條拿掉（欄與欄的分離現在由
   `.dgv2` 的 grid 保證），或換成新座標（SiC 30–230 ｜ GaN 306–598，溝 240–300，y 126–316）。
3. `t_b21_cowos` ⑨ 的 `ok("⑨ 寬度仍然是 980", h0["w"] == 980)`、
   ⑧ 的 `ty["svgW"] >= 960`、以及「畫出畫布（viewBox 980）」那句文案 → 三處都換成 660。
4. `t_b21_cowos` ② 的
   `ok("併入①：掛標籤的每一列都有真的 data-seg", all(bool(x) for x in got["segsOfTagRows"]))`
   → v2 的 `externalize()` 會把 `data-seg` 從 SVG 的 `g.lrow.ext` **搬到 HTML 卡片**
   （`diagrams.js` 既有行為，AI 伺服器那三張也一樣），所以 `g.dataset.seg` 會是 undefined。
   改成量 `.dgc[data-seg]`。同段的 `nTag >= 9` 與「標籤蓋得到五種環節」**保留**
   （`text.tag` 還在 `g.lrow` 裡）。

對應段落：`批次21-晶圓代工`、`批次21-矽晶圓`、`批次21-HBM`、`批次21-CoWoS去重`、
`批次14b-第三代半導體`，外加 `產業`、`族群頁`、`批次24-半導體鏈3D`（**`--workers 1`**）。

## 二、W6／W7 資金流向（新增 20 條，舊斷言要清）

**要清掉的舊斷言**（DOM 已經不存在，留著必紅）：
`#rotBoard`、`#rotCycle`、`.rotfilter .gchip`、`.rotfilter .seg.rotchain`、
`.linkrow.gchips[data-for="sankey"]` 以及桑基那排的 `.gchip`。

**要新增的**（建議開一段 `批次30-兩層下拉與象限卡`；agent 的腳本可直接抄，
路徑見下方「現成腳本」）：

W6 資金輪動下拉（1～6）
1. `.rotfilter[data-rf="flow"] .rotdd` == 2 且 `.rotfilter .gchip` == 0
2. 點第一層 `.ddbtn` → `aria-expanded` false→true；面板在 **390px** 下 left ≥ 0 且 right ≤ 390
3. 選「半導體」→ 第二層自動打開，`.ddlist .ddopt.chk` 數量 **< 全部族群數**
4. 連勾兩個 → ① 第二層仍開著 ② `#rotClock` scatter `data.length` 變 2
   ③ 按鈕含「已選 2 個」 ④ `localStorage['tw.rot.filter']` 的 groups 長度 == 2
5. Esc → `aria-expanded` 回 false；點「清除」→ scatter 點數回到 N
6. 開 `#rotZoomBtn` → 放大視窗也有 2 個 `.rotdd`，在裡面勾一個 → **卡片那排摘要跟著變**
   （共用狀態，最容易退化的一條）

W7 象限卡（7～13）
7. `#rotBoard`、`#rotCycle` 都不存在；`#rotMove` 存在非空且 top ≥ `#rotClockWrap` 的 top
8. `#rotClock .rotquads .rq` == 4，四顆 computed color 互異，四顆都在 `#rotClock` 矩形內
   （**390 要驗**，位置是用像素算的）
9. 點一顆 → `#stagePanel` hidden→visible，`li[data-gid]` 筆數 == 該卡 `em` 的數字
10. 面板與 `#rankFlowWrap` 幾何**不重疊**
11. 點第二顆 → `.rq.on` 只 1 顆、`#stagePanel[data-k]` 換人；再點同一顆 → 收合
12. 點面板裡的族群列 → `#rankPanel` hidden→visible（驗走既有展開路徑）
13. 拖 `#rotBack` 到 10 天前，300ms 後四顆卡的數字改變（驗跟著「看哪一天」走）

桑基下拉（14～20，選擇器 `ROW = '.ddrow[data-for="sankey"]'`）
14. `ROW .rotdd` == 2 且 `.linkrow.gchips[data-for="sankey"] .gchip` == 0
15. 點 `ROW .rotdd[data-dd="chain"] .ddbtn` → `aria-expanded` true；390 下面板不溢出
16. 選一條鏈 → 第二層自動開，`.ddlist .ddopt.one.row` < 全部族群數；
    **`input[type=checkbox]` == 0**（驗這邊是單選）
17. 點一個族群 → ① `#sankeyPanel` hidden→visible ② 第二層 `aria-expanded` 回 false
    ③ 按鈕含該族群名
18. **（≥800px 才驗）** 樹節點總數變多且結構簽章改變；390 跳過並註明
    「窄版三層樹本來就不畫葉節點」
19. **`#rotClock` scatter 點數選前選後相同**（驗沒有被併進 `ROT`，這條最容易退化）
20. 點 `ROW .dd-clear` → 結構簽章回到最初、`#sankeyPanel` 收回 hidden

## 三、W3 產業頁十件（等該路交件後依實際改動補）

至少會動到：
- `#memberTable` / `#memberTitle` / `#memWide` / `#mktSeg` / `#memberMore`（成分股整塊移除）
- `#dgMenu` / `.dgcard`（圖別選單移除）
- 產業鏈標題那排 `pill`（`157 檔` / `今日` / `本益比中位`）與 `A.L.back()`
- `#industry/<chain>` 的落點改成第一張剖析圖（**測試網址要用完整的 `/dg/` 路由**）
- 分頁標籤只剩族群名（斷言若比對完整圖名會紅）
- `#dgTools` 從右下改右上（位置斷言）
- 族群總覽的長條圖／圓餅圖改版（甜甜圈、其他併塊、中心數字）
- 切主題時剖析圖配色跟著切（**新增**，要量畫布真實顏色，不是驗按鈕文字）

## 四、現成腳本（可直接抄進 `_uitest.py`）

- `scratchpad/w67.py` —— 資金輪動下拉＋象限卡，三寬度
- `scratchpad/w6zoom.py` —— 放大視窗共用狀態
- `scratchpad/w6sankey.py` —— 桑基下拉，三寬度
- W4／W5 各自的量測腳本（見那兩路的回報）

## 五、測試技巧（踩過的坑，別再踩一次）

- `#flow` / `#industry` 頁用 `pg.click()` 點靠上方的按鈕會被**吸頂的 `.topbar` 攔截**逾時，
  改用 JS 派發的 `element.click()` 就穩定。
  （同類問題的另一種解法是 HANDOFF 裡「3D 容器改走滑鼠座標」。）
- **3D 相關段落一律 `--workers 1`** —— 平行跑會把 CPU 吃滿、工具列 6 秒點不到，整批假紅。
- `scripts/_show.py` 每次跑會先清空 `docs/_show/`，多個 agent 同時跑會互相洗掉截圖。
