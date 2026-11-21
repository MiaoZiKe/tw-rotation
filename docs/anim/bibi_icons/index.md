# 比比互動小圈圖示（11 個）

- 用途：網頁版客服鈕「比比」互動選單的小圈圖示；每個 96×96 透明 PNG、手繪風粗描邊（#1A0907）、奶油白圓底，與比比同風格。
- 製作：`python scripts/anim/bibi_interact_g1.py --out <scratchpad>/bibi_g --repo-out docs/anim --icons`（`scripts/anim/bibi_icons_g1.py`）。
- 圓底外是透明；不加陰影，深淺主題都可直接用。

| 預覽 | 檔名 | 圖示 | 對應互動 |
|---|---|---|---|
| <img src="hand.png" width="48"> | `hand.png` | 手 | 摸摸頭 |
| <img src="grass.png" width="48"> | `grass.png` | 牧草 | 吃草 |
| <img src="ball.png" width="48"> | `ball.png` | 球 | 玩球 |
| <img src="spin.png" width="48"> | `spin.png` | 旋轉箭頭 | 轉圈圈 |
| <img src="highfive.png" width="48"> | `highfive.png` | 擊掌手 | 擊掌 |
| <img src="music.png" width="48"> | `music.png` | 音符 | 聽音樂 |
| <img src="heart.png" width="48"> | `heart.png` | 愛心 | 比心 |
| <img src="moon.png" width="48"> | `moon.png` | 月亮 | 晚安 |
| <img src="camera.png" width="48"> | `camera.png` | 相機 | 拍照 |
| <img src="chat.png" width="48"> | `chat.png` | 對話泡泡 | 聊天 |
| <img src="hammer.png" width="48"> | `hammer.png` | 玩具嗶嗶槌 | 敲一下（bibi_hit → bibi_cry） |

- `hammer.png`（10-11 晚新增）：`python scripts/anim/bibi_moves_v2.py --out <scratchpad>/bibi_v2 --repo-out docs/anim --only hit` 會一起重畫（`make_hammer_icon`）。
