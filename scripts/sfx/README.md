## 十三、運作音效（2026/11/27 Andy：「以後產出所有內容，Claude 這邊都需要在影片上配對應運作上的音效」）

只做後製、不重渲畫面。三支檔：`scripts/three/sfx-synth.py`（通用合成器，吃 cue 表 JSON，不依賴專案檔，別的頻道可單獨用）、`scripts/three/sfx-ops.py`（科技片轉接層，從 storyboard／script／model 自動排 cue 表）、`scripts/three/add-sfx.sh`（混進成片）。依賴只有 python3＋numpy＋ffmpeg；全部程式合成、固定 seed、不用外部音檔。

**流程：雲端渲染完 → 抓成片 → `add-sfx.sh` → 交件**（`make-tech.sh` 先不改）：

```bash
bash scripts/three/add-sfx.sh --tech <slug> out/<slug>.mp4 out/<slug>-sfx.mp4          # 科技片：自動排
bash scripts/three/add-sfx.sh <in.mp4> <cues.json 或 sfx.wav> <out.mp4> [--end 片尾卡秒]   # 通用（其他頻道）
```

混音規則：旁白講話時 sfx 自動壓低 −8 dB；sfx 比旁白低約 10 dB（講話時約 18 dB、整體約 17 dB）；整條 loudnorm 回 −16 LUFS，再接 −4 dBFS 限幅（吃掉 AAC 過衝，成片峰值 ≤ −1 dBFS）；影像串流 copy；片尾卡之後沒有運作音效。成品旁產出 `out/<slug>/sfx-cues.json`（每個音效的時間、類型、來源）與 `sfx-table.json`（cue 表）。

| 聲音 | 對應的動作 |
|---|---|
| motor 低頻嗡聲（隨轉速） | `rotate` 動作（轉軸、輥輪、轉盤），`cut` 刀片 |
| servo 伺服 whir | motion：`pick-place`、`arm-transfer`、`arm-reach`、`scan` |
| hiss 濾波白噪＋開閥／關閥 click | `flow` 顏色 argonC、名稱含 gas／spray／air／cool（氣流、吹淨、噴氣） |
| liquid 粉紅噪＋水滴 | `flow` 顏色 waterD、cuBright（液體噴灑與流動） |
| plasma 電流嗡＋細微劈啪 | plasma 層的 `flow`、`pulse` plasmaC（電漿、高壓） |
| sputter 細碎撞擊 | hitL 層的 `flow`、`pulse` hitC（原子被打出） |
| heat 低頻爐火聲 | `pulse` hotC／moltenC |
| chips 碎屑點擊 | `flow` chipFlake |
| clunk＋slide 金屬撞擊與滑軌 | `explode`／`assemble`／`reexplode`、`shift` 有位移、`press-bond`、`stack-up`（同時動的多層合成一聲） |
| valve 氣動 click | 氣流開關、`press-bond` 壓下放開、`pick-place` 吸附破真空 |
| whoosh 很輕的氣流掃過 | `props.shot` 鏡頭大移動（超過 `SHOT_MIN`；硬切不加） |
| 不加 | 標籤出現、字卡、overlay、reveal、片尾卡 |

生活類（給沒有 3D 模型的頻道，只能手寫 cue 表）：`footstep` 腳步、`door` 開關門、`cup` 杯子、`keyboard` 打字、`pageturn` 翻書、`rain` 雨聲。加新種類：在 `sfx-synth.py` 寫 `fn(dur, **params)` 再 `register("名字", fn, 預設dB)`。cue 表格式：`[{"t": 3.2, "dur": 1.5, "kind": "rain", "gain": 0, "pan": 0.5, "params": {}}]`，格式說明在 `sfx-synth.py` 檔頭。
