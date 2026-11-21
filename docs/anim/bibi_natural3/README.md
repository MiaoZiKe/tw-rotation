# 比比自然互動第三輪

正式程式素材版本 `1016natural3`。品牌參考原圖已保存為 `approved_master.png`；各組原始16格透明圖為 `<key>/source_sheet.png`，實際生成提示詞與缺陷記錄為 `generation.json`。

| 動作 | key | 反應總長 | 接觸或事件 |
|---|---|---:|---|
| 啃葉 | leaf_bite | 1200ms | 第6來源格300ms閉口，重播9/10咀嚼 |
| 泡泡受驚 | bubble_react | 1000ms | 第6格200ms鼻碰，縮頭瞇眼後找尋 |
| 紙飛機 | plane_react | 1200ms | 第6格200ms鼻碰，回縮再低頭嗅 |
| 毛線側跌 | yarn_tumble | 2600ms | 600ms開始傾、940ms側腹著地、2140ms身體鬆線、2480ms回復 |

匯出器 `scripts/anim/bibi_natural3.py` 重用既有gif_pipeline，不生圖、不重畫角色。執行 `python scripts/anim/bibi_natural3.py --revision natural3`，各組由 `export_settings.json` 定義共同取樣窗、時序及人工量點，輸出 `export_natural3/`：16張512透明PNG、512 GIF／WebP、160 WebP、三底接觸表、storyboard與逐播放格engine_tracks。

全格採共同裁切縮放保留位移。嘴鼻從實際影格放大量測，body為人工近似橢圓；不是由全身外框猜嘴。泡泡／紙飛機因前探超出格界，採共同擴展取樣窗及主體連通區分離，保留完整耳鼻腳；清理游離動作線、來源鮮洋紅碎邊，原圖不改。幾何及逐格量點都在設定與storyboard中。

毛線播放第4時間段改hold第3來源格，避免原第4格纏線突然消失；原16 PNG保留，總長不變。WebP自動把相鄰相同格合併，因此毛線15個編碼格對應16時間段，非漏時間。原畫負責身上纏線，網頁只補連球尾線，不重疊另一套身體環。

四檔160 WebP皆80KB內，格式、透明角落、實際解碼總時長已驗。32項測試與獨立三底／實際160／逐格對應審核通過；瀏覽器動態與正式部署狀態見 `../bibi_unit/review.md` 與 `../bibi_unit/README.md`，不能用靜態或測試冒充已上線。
