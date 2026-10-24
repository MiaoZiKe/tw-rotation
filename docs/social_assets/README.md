# 社群共用素材庫

這裡儲存可重用比比、科技物件、背景與插畫；最終貼文在 [social_posts](../social_posts/README.md)。[INDEX.md](INDEX.md) 供跨篇查找。歷史素材保留原位置，不搬動網站動畫引用。

```text
social_assets/
  INDEX.md
  manifest.template.json
  gpt_original/<asset_id>/v001.png + manifest.json
  codex_original/<asset_id>/v001.png + manifest.json
  user_provided/<asset_id>/v001.png + manifest.json
  author_unverified/<asset_id>/v001.png + manifest.json
```

- `gpt_original`：有本次生成證據的全新原畫；記工具、提示詞摘要與原始交付。
- `codex_original`：有製作證據的原創程式圖形、排版或素材；混用角色圖須逐項記原作者。
- `user_provided`：Andy 提供且可公開存放的素材；不代表 Andy 是原畫作者。
- `author_unverified`：作者證據不完整的歷史素材或衍生物；記 unknown 與父素材，不改掛原創。

每個 asset_id 對應一件素材，版本只新增、不覆蓋；新版列前版為 parent_asset_id 或在版本紀錄附前版路徑。每篇 assets.json 引用明確版本，不能只指向「最新版」。檔名範例：`bibi_tilt_cream_v001`；實際 asset_id 以 manifest 為準。

選材先檢查角色規格、來源證據與權利，再重用；不合規素材標退役／不可直接用。沒有作者證據不得按外觀猜。加工不覆蓋原畫歸屬，未知作者的衍生物仍歸 author_unverified，processed_by 記實際加工者與工具。

五張第三方風格參考留在本機 `reference/style_samples/`，此庫只存分析與來源登錄，不上傳原圖、不抄浮水印／Logo，也不將圖中文字當查證資料。

每檔須不超過 5 MB，MP4 留本機；manifest 記本機路徑、雲端備份狀態與尺寸／透明度。透明底須檢查 alpha 有實際透明像素，不能只看 RGBA 模式。
