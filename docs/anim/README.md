# 動畫設計單位：從分鏡到上線的整套流程

> 2026-10-09 Andy：「幫我將 LOGO GIF 圖設計成立動畫設計單位，之後會需要請相關人員製作動畫以及 GIF 圖片，
> CEO 幫我找相關人員，並且將上述從給你分鏡圖片到你合成 GIF 以及去背整套流程寫個系統先儲存」。

## 1. 人員
| 角色 | 定義檔 | 管什麼 |
|---|---|---|
| 動畫導演 | `.claude/agents/animation-director.md` | 企劃、分鏡表、規格、審片（三種底逐格看） |
| 動態設計師 | `.claude/agents/motion-designer.md` | 素材整理、去背、合成 GIF／WebP、接上網站 |
| 協作 | `canvas-motion-engineer`（Canvas 動效、宣傳影片）、`art-director`（配色與風格把關）、`marketing-strategist`（行銷用途的文案） | |

CEO 派工順序：Andy 給需求（＋圖）→ 動畫導演寫分鏡與規格 → 動態設計師製作 → 動畫導演審片 → 推上線 → 回報附檢查圖。

## 2. 分鏡表範本（`docs/anim/<名稱>/storyboard.md`）
```
名稱：mascot-wave（天竺鼠揮手）
用途：總覽歡迎卡｜顯示 64px｜輸出 128px｜循環｜透明背景｜≤ 80KB
| 格 | 動作 | 表情 | 停留 ms | 備註 |
| 1 | 站好 | 張嘴笑 | 400 | 循環起點 |
| 2 | 右手舉起 | 笑 | 120 | 動作線 2 條 |
| 3 | 手到最高 | 瞇眼笑 | 120 | |
| 4 | 手放下一半 | 笑 | 120 | |
| 5 | 回到站好 | 張嘴笑 | 400 | 接回格 1 |
```

## 3. 素材放哪
- 原檔（Andy 給的 GIF／圖／影片）：`site/brand/src/`，**永遠保留**，日後重做都從這裡開始。
- 分鏡圖：`docs/anim/<名稱>/frames/`，檔名排序就是播放順序（01.png、02.png…）。
- 成品：`site/brand/<名稱>-<尺寸>.gif／.webp／.png`。

## 4. 一條龍指令
```
python scripts/anim/gif_pipeline.py run --in site/brand/src/support_anim_1009.gif --out site/brand/sup-anim --sizes 128
python scripts/anim/gif_pipeline.py run --in docs/anim/mascot-wave/frames/ --out site/brand/mascot-wave --sizes 128 --durations 400,120,120,120,400
python scripts/anim/gif_pipeline.py check --in site/brand/sup-anim-128.gif     # 只出檢查圖
```
輸出：GIF（每格透明）、動態 WebP（半透明邊緣、通常更小）、第一格 PNG、`_check/` 檢查圖（洋紅／深／淺三排）。
輸入可以是 GIF、動態 WebP、MP4（要 `pip install imageio-ffmpeg`）、或分鏡圖資料夾。純色綠幕用 `--bg-color 00ff00`。

## 5. 2026-10-09 客服鈕 GIF 踩過的坑（腳本已內建防呆）
| # | 症狀 | 根因 | 腳本怎麼防 |
|---|---|---|---|
| 1 | 有幾格背景還在 | 存 GIF 時只有第一格帶透明色 | 用 RGBA 逐格存，存完讀回檢查每格四角 |
| 2 | 跳起來那兩格整隻被挖空 | 先裁切再去背，頭頂碰到裁切邊，灌水從邊緣灌進身體 | 一律在原圖上去背，最後才依「所有格聯集框」裁切 |
| 3 | 灌水從描邊細縫漏進身體 | 毛邊、動態模糊讓描邊有縫 | 描邊先往外擴 2px 補縫；本體太小自動加大半徑重試，並警告 |
| 4 | 地上有淡色影子 | 影子跟背景相連但不是同色 | 亮度 > 150 且跟背景相連一起吃掉（要保留用 `--keep-shadow`） |
| 5 | 淺色主題看起來像有背景 | 網站那邊加了 CSS drop-shadow | 規定：成品與網站端都**不加陰影／外框** |

## 6. 審片清單（動畫導演）
- [ ] 洋紅排沒有任何米色／灰色殘留
- [ ] 每一格身體完整（耳朵、腳、動作線都在）
- [ ] 深色、淺色主題下沒有白邊、沒有陰影
- [ ] 節奏照分鏡，循環接得起來
- [ ] 檔案大小在規格內（網站用 ≤ 80KB）
- [ ] 網站實際截圖（深＋淺）看過，跟 Andy 的範本並排一致

## 7. 可選工具
這個環境另外接了 Adobe（Firefly／Express：去背、生成、動畫）與 Canva、Figma 的連線，Andy 想用 AI 生分鏡圖時可以走那邊，
生出來的圖一樣放 `docs/anim/<名稱>/frames/` 再進第 4 節的流程（用之前先跟 Andy 確認帳號與授權）。
