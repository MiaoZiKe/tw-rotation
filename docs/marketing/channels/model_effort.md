# 各頻道子 agent 的模型與 effort 搭配（2026-11-20 Andy：「好 照這樣做 並且每個頻道都是」）

原則：要判斷的工作用強模型、高 effort；照步驟的工作用便宜模型、低 effort。派子 agent 時在 Agent 呼叫上明確帶 `model` 與 `effort`。

| 工作階段 | 模型 | effort |
|---|---|---|
| 選題、查證數字（兩個來源） | sonnet | medium |
| 寫腳本（鉤子、因果、念稿） | opus | medium |
| 素材規格（六面向逐鏡） | sonnet | medium |
| 配音、剪停頓、渲染、autofix、跑檢查 | sonnet | low |
| 輪播圖製作、caption、article | sonnet | medium |
| 最後審片、打分、看圖找問題（art-director／animation-director 等審查角色） | opus | high |
| 頻道主聊天室（派工、回報） | 不變 | — |

驗證：依模型特性與派工經驗訂的，尚未做同片對照。各頻道每支的 retro.md 記 Token 用量與品質變化，週檢討依結果調整本表。

**試行與隨時修正**（2026-11-20 Andy：「先試試看這樣的搭配，並且若在製作過程中發現有更好解方請提出並修改」）：本表是試行版。製作中發現更好的搭配（例：某階段 low 品質不夠、某階段 opus 沒必要），當下提出並直接改本表，在 retro.md 與回報裡寫「改了什麼、為什麼、證據」；不必等週檢討。
