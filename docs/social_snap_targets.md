# 自動截圖目標清單（site/snap.js）

> Andy 2026-10-20：「熱力圖都需要具備即時功能，他也是需要截圖發布的內容」。
> 每個目標都有 `data-snap="<名稱>"`（各頁重畫後自動補回），並提供 `window.TwSnapReady(名稱)`（true＝畫完、即時資料若適用已套上）與 `window.TwSnapList()`（目前 DOM 裡有哪些）。

| 名稱 | 路由 | 截的範圍 | 有即時？ |
|---|---|---|---|
| `heat-overview` | `#overview` | 資金熱力圖整張卡 | 有（HL，站主／管理員） |
| `heat-ovtheme` | `#overview` | 熱門題材熱力圖整張卡 | 有（成分股即時；顏色依熱度，選「平均漲跌」才隨即時變色） |
| `heat-industry` | `#heatmap/industry` | 「整個台股一次看」整張卡 | 有 |
| `heat-theme` | `#heatmap/theme` | 題材資金熱力整張卡 | 有 |
| `rot-wheel` | `#flow/rotation` | 資金輪盤整張卡（含右邊族群資金排行） | 有（卡上「即時」鈕，RLV） |
| `rotation-wheel` | `#flow/rotation` | 輪盤圖本體（不含標題列與控制項） | 同上 |
| `rotation-rank` | `#flow/rotation` | 族群資金排行長條圖本體 | 同上（輪盤即時時排行同步重算，x 軸標「・即時」） |
| `rot-wheel-mini` | `#overview` | 迷你資金輪盤卡 | 總覽摘要卡的即時 |
| `flow-tree` | `#flow/sankey` | 資金分流樹整張卡（含右側資金流向排名） | 有（SKL） |
| `sankey-tree` | `#flow/sankey` | 分流樹圖本體 | 同上 |
| `flow-tree-ov` | `#overview` | 昨日資金分流樹卡 | 否（昨日） |
| `market-streak` | `#market/streak` | 法人連續買賣超整張卡 | 否（日資料） |
| `heat-season` | `#season` | 月度報酬熱力 | 否（歷史） |

## 就緒判斷
- `TwSnapReady(名稱)`：目標在畫面上、有畫好的 canvas／svg（或清單列）、沒有 `.isempty`，且所在卡片的 `data-snap-live` 不是 `pending`。
- `data-snap-live`：`pending`（即時開著、盤中、還沒輪完一圈，約 20～40 秒）／`live`（已套上）／`close`（收盤資料，含盤後與訪客）／`err`（抓不到或等超過 60 秒，截到什麼就是什麼）。
- 即時只給**站主或管理員**登入的瀏覽器（livegate.js）。截圖程式要拍即時版，需用管理員身分登入；未登入一律是 `close`。
- 熱力圖的「即時」鈕（標題旁，預設開）；資金輪盤與資金分流樹的「即時」鈕要截圖程式自己點（`#rotLiveBtn`、`#sankeyLiveBtn`），點完等 `TwSnapReady`。
- 非盤中（09:00–13:35 以外）顯示最後收盤。
