# 哩股哩股 LOGO 第五輪（2026-11-02，設計總監）

Andy 評語：「換其他風格我看看」。前四輪都是「扁平／漸層 App 圖示＋L」，本輪 8 種風格本身完全不同，每種 2 套配色（A＝陽光糖果主色、B＝反相或異色）。全部為 SVG 向量（`svg/`），文字一律轉成字型原始輪廓（不加粗、不變形，只做位移／旋轉），Playwright 輸出 PNG。不用吉祥物。AI 生圖未使用。

總覽：`overview.png`（8 種 × 2 配色 ＋ IG 110／40px 實際像素）、`overview_detail.png`（橫式 LOGO ＋ Threads 個人頁模擬）。

## 8 種方向
| 代號 | 風格 | 理念 | 字型（授權） |
|---|---|---|---|
| d1 | 純字標 | 小寫 ligu ligu，i 點換成大圓點（像太陽／資金落點）；兩個 ligu 顏色與點色互換＝輪動 | Fraunces Black（OFL） |
| d2 | 圓體可愛 | 四顆彈跳歪斜的糖果貼紙「哩股哩股」，上下錯落；圖示為大「哩」＋小「股」貼紙 | 粉圓 Huninn（OFL） |
| d3 | 單線 | 一筆畫：圓點（i）→ L 的豎線 → 彎進腳 → 流成上揚資金線；細線伴隨一條副流 | 無；橫式字用 Noto Sans TC Bold／Fraunces（OFL） |
| d4 | 復古徽章 | 雙環＋弧形字「LIGU LIGU」「哩股哩股」，中央旭日與三根上升柱（不是印章） | Fraunces Black、Noto Serif TC Black（OFL） |
| d5 | 黏土立體 | 三塊柔軟黏土甜甜圈切片，一塊被推出（熱點），中央一顆光澤球；漸層＋高光＋柔影模擬 | Noto Sans TC Black（OFL） |
| d6 | 霓虹科技 | 深底格線、發光 L 趨勢線＋霓虹環＋亮點；B 版用紅（台股漲）＋琥珀 | Inter ExtraBold、Noto Sans TC Bold（OFL） |
| d7 | 書法手寫 | 霞鶩文楷的「哩」，外圍一筆毛筆圓相（濃淡收筆），缺口露出一輪旭日 | 霞鶩文楷 LXGW WenKai TC（OFL） |
| d8 | 孟菲斯拼貼 | 藍色長方塊＋橘色圓頭塊拼成 L，散落圓環、鋸齒、三角、點陣；橫式 L-i-G-U 全由幾何塊組成 | Noto Sans TC Black（OFL） |

字型檔與授權文字在 `fonts/`；全部 SIL Open Font License 1.1，可商用。字型取得：`npm pack @fontsource/<名稱>`。

## 配色
A：底 #FFF7E8／墨藍 #1F2A44／橘 #E8590C／藍 #2B6BF3／紫 #7B4FE0／青 #0A8CA3（d1 d2 d3 d7 d8 d5 以此為底）。B：d1 d3 為藍底反白＋黃；d2 藍底黃粉；d4 橘底；d5 冷色（青粉黃＋藍球）；d6 深底紅黃；d7 墨藍底；d8 紫底。

## 檔案
`<代號>_<A|B>_icon512.png`（圓角方形）、`_ig400／_ig110／_ig40.png`（圓形，實際像素）、`_horizontal.png`（1200×400）；`svg/` 向量；`src/`：`python3 src/build.py [d1 d2…]` 產圖、`python3 src/overview.py` 產總覽。

## 40px 檢視
d1、d6、d7、d3 最清楚；d2、d5、d8 靠色塊辨識；d4 縮到 40px 只剩「圓章＋旭日」，字看不清（徽章的天性）。

## 推薦
1. **d7 書法手寫**：最有辨識度、東方韻味，40px 仍認得出（圓＋字＋紅日），和前四輪完全不同，也最不像一般金融 App。
2. **d1 純字標**：最容易延伸到全部文宣，40px 的「li」＋圓點好認，字標像 Dcard／Google 靠字本身。
3. d2 圓體可愛：最親和，適合 Threads／IG 社群個性；但與專業感有落差。
推薦頭像用 d7-A 或 d1-A，橫式用 d1 或 d7。
