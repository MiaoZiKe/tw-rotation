# 素材盤點與本次檢查範圍

素材管理角色；盤點日期 2026-10-17（Asia/Taipei）。

- 已經 GitHub connector 實讀 `docs/anim/bibi_library/index.md`（SHA `8d947a7f18d0ee87f477acff5ebdabf3a782731e`）：67 組動作、表情、道具與互動，表列每組代表格、sprite、動態 WebP。此為現存索引記錄，沒有宣稱本次已逐格驗證。
- 已實讀 `docs/anim/bibi_basepose_1012/README.md`（SHA `be8598845815dad29f17b7865c7a973da6f759f5`）及 `png/` GitHub 目錄：31 張 PNG；README 另記奔跑 WebP、接觸表、自檢 JSON、分層重組腳本。README 內尺寸／面積／格數屬舊庫描述，不能當作本次實測結果。
- 遠端基礎姿勢包含正面、3/4、側面、趴、坐、躺、嗅地與奔跑。已以來源 URL＋Git SHA 登錄 `catalog_snapshot.json`，不搬移原檔、不下載整庫。
- 本機原有兩份 manifest：`bibi_chip_research_host`、`bibi_tilt_cream`。兩者都保留 `author_unverified` 及 review；前者風格待 Andy、後者權利未知。`scan` 對實際存在的檔案計算 alpha／尺寸／SHA-256。
- 歷史 `coins`、`growth`、`piggy` 與當前禁用金錢圖示規則有衝突，搜尋快照標 rejected，不刪原檔。其餘未知造型／權利者列 review，沒有自動升級 approved。
- `scripts/social/asset_catalog.py self-test` 已驗證：預設只選批准、待審預覽、拒用隔離、缺批准證據降級、中英同義詞及欄位篩選。

## 限制與待辦

本次素材系統盤點**未完整逐檔視覺檢查全庫**，未檢視遠端每格動畫、未測量遠端全部圖片 alpha／SHA-256；因此不宣稱全庫核完。主製作流程只下載本篇實際需要的少量素材並另行放大檢查。機器可讀 approved 數量為零時，搜尋預設回空陣列是正確門檻行為；請用 include-review 做候選比較，再留下人工確認紀錄。

科技物件可納同一 manifest 搜尋；本篇新建可編輯物件由設計流程登錄。未在本機或遠端清單證據中確認的 EUV、HBM、PCB、光纖等，不寫成已存在完整插畫庫。

## 本次新增共用素材

已登錄 8 個主持姿勢＋1 個曝光場景（author_unverified，父素材 bibi_clean），以及 3 個科技教學元件（codex_original，各附可編輯 SVG 與 PNG）。合計 12 件新資產、14 份本機 manifest；新增全為 review，動畫欄位 0／null，仍待 Andy 核可。pose_cells.json 保存固定格來源及裁切框；每件 manifest 保存 SHA-256、實際 PNG alpha 與尺寸。共用庫 INDEX、catalog.json、本篇 assets.json 及動畫庫 catalog.social.json 已建立明確版本交叉引用。

原始姿勢表已看總覽以標記可見動作表情；此步不是逐角色 200～400% 或每頁品管。曝光設備、光路元件均為教學示意，真實結構與光路應另查資料及人工審核。SVG 來源保留可編輯性，catalog 中 SVG 的 Pillow inspection_error 表示無法以點陣檢視器解析，不表示已驗透明度。

最終登錄增加六件 `tech_illustrated_*` 手繪科技PNG後，本篇共18件、全庫本機20份manifest。趴姿v002清理版已同步（v001因腳間碎片rejected退役）；新增PNG與SVG已統一重算SHA-256。角色／場景仍review，沒有Andy核可。科技PNG可獨立組合但無可改視角vector源；相關codex SVG為另一組獨立可編輯教學元件。
