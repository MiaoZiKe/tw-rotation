# AI Office 角色建模腳本（Blender Python）

把角色「參數檔」變成一份**一體成形的網格＋骨架＋蒙皮權重＋形態鍵＋AO 頂點色＋臉貼片**，輸出成 GLB，網站執行期再用 `GLTFLoader` 載入（`site/office/char/mochi.js`）。
GLB 是成品，**擁有者與網站都不需要 Blender**；只有重新產出模型的人才需要照下面裝一次環境。

## 一鍵重現

```bash
# 1. 建一個虛擬環境（不要放進 repo；bpy 約 1.1 GB）。bpy 5.3 需要 Python 3.13
python3.13 -m venv /tmp/bpyenv
/tmp/bpyenv/bin/pip install bpy==5.3.0 scikit-image

# 2. 產出（約 12 秒）：參數檔名、輸出資料夾
/tmp/bpyenv/bin/python tools/ai_office_char/build_char.py params_mochi site/office/char/models
#   只出某幾級：--lod 0,1
```

產出 `site/office/char/models/mochi_lod0.glb`（近）、`mochi_lod1.glb`（中）、`mochi_lod2.glb`（遠）與 `mochi.json`（錨點、骨頭、形態鍵名、臉貼片範圍）。
`mochi.json` 裡的座標已換成網站座標（Y 向上、臉朝 +Z）。

## 做法（為什麼是這樣）

| 步驟 | 內容 | 為什麼 |
|---|---|---|
| 1 距離場 | `sdf.py`：身體橢球＋耳／手臂／腿／尾橢球，用**平滑最小值**聯集（每個部件有自己的圓角半徑 `k`），腳底壓平 | 四肢是從身體「捏出來」的凸起，根部自然內凹，沒有接縫、尖角 |
| 2 取表面 | scikit-image Marching Cubes（0.8 cm 格）→ Blender 合併重複點 → 體素重網格 | MC 在剛好落在格點的地方會產生零長度邊，直接丟給 QuadriFlow 會失敗，要先合併＋重網格清成流形 |
| 3 重拓撲 | `QuadriFlow`（對稱）→ 目標四邊形數（LOD0 2500／LOD1 900／LOD2 300） | 乾淨的四邊形、邊流向、均勻面積 |
| 4 貼回距離場 | 每個頂點沿距離場梯度投影回等值面 | 重拓撲後輪廓回到解析曲面 |
| 5 AO | 解析 SDF 環境遮蔽（沿法線取 4 個距離）→ `COLOR_0` | 不用烘焙、可重現；耳根、肢根、腹下自然變暗 |
| 6 蒙皮 | 程序化權重：肢體鏈影響範圍＋根部漸入＋軀幹 Z 漸層，平滑 3 次，每點最多 4 骨 | 內凹過渡區跟著身體動，不會被肢體整塊拖走；臉區整片跟著頭骨 |
| 7 形態鍵 | `squash／stretch／land／plump／breath／cheek.L／cheek.R`，全是「位置與法線的純函式」 | 三個 LOD 的形態鍵自動一致，不用逐級手作 |
| 8 臉貼片 | 從本體複製「臉前方」那片面，沿法線外推 1.2 mm，前視平面 UV，同樣的權重與形態鍵 | 貼圖（腮紅、鼻、嘴、眉、淚）**貼合曲面並跟著變形** |
| 9 匯出 | `export_scene.gltf`，不壓縮（bpy pip 版沒有 Draco／meshopt），形態鍵只存位置、稀疏 | vendor 沒有解碼器；靠面數控制大小 |

## 重用到其他物種

1. 複製 `params_mochi.py` → `params_<物種>.py`，改 `BODY`、`PARTS`（橢球清單）、`BONES`、`LIMBS`、`FACE`、`LODS`。
2. `python build_char.py params_<物種> <輸出資料夾>`。
3. 網站端 `MochiChar` 以 `mochi.json` 的 `anchors／bones／decal` 組裝；眼睛、嘴型是共用的（`facerig.js`），換物種只需要換錨點。

骨頭名稱規則：`root pelvis spine head tail tail.tip ear.L ear.R ear.tip.L ear.tip.R arm.L arm.R hand.L hand.R leg.L leg.R foot.L foot.R`（L ＝ 模型 +X）。
注意：`GLTFLoader` 會把節點名稱裡的「.」拿掉（`foot.L` → `footL`），`mochi.js` 用 `mochi.json` 還原成原名。

## 檔案

- `params_mochi.py`　糰糰參數（比例、部件、骨架、蒙皮範圍、臉、LOD）
- `sdf.py`　距離場、梯度投影、解析 AO
- `build_char.py`　Blender 腳本（上表 2～9）
