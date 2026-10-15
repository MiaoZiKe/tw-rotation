# 比比網頁互動第二版

原始分鏡與生成提示詞保留於各動作目錄的 `source_sheet.png`、`generation.json`；512 透明影格保留於 `frames/`。

輸出為 `anim-512.gif`、`anim-512.webp`、160 網頁用 `anim.gif`、`anim.webp`。`storyboard.json` 記錄逐格時間、原圖雜湊、共同畫布幾何與讀回驗證。`sheet_three_backgrounds.png` 用洋紅、深、淺背景檢查透明邊緣。

匯出使用所有格共同聯集裁切、單一比例、單一位移；不逐格重新對齊腳底，保留蹲下、跳起與落地的高度差。只排除切格邊界上面積小於主體 2% 的孤立碎片，不裁掉主體。

重新匯出：`python scripts/anim/bibi_web_v2_1015.py --keys <動作名>`。審核後加 `--runtime` 才複製到網站正式檔名。原始第一版資料夾不覆寫。

第二版拍照不再跳躍，快門對齊第 9 格驚訝反應，建議 1170 毫秒。轉圈素材 `spin_q` 為跑完一圈後的短暈眩收尾；跑圈軌跡由網站互動程式處理。


行為依據：
- https://www.torontohumanesociety.com/why-does-my-guinea-pig-popcorn/：短促跳躍、輕微扭身與連續爆發。
- https://vethelpdirect.com/vetblog/2021/06/01/why-does-my-guinea-pig-jump-what-is-popcorning/：四腳離地、扭身及短跑間穿插跳躍。

互動修正：紙飛機落地嗅聞、毛線不共用接球、橢圓跑一圈後暈眩、泡泡與葉子接觸時間對位。拍照快門1170ms。此為行為參考的卡通動畫，非逐格動物運動量測。
