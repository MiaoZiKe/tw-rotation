# 3D 角色相關技能與工具調查（2026-11-13）

起因：Andy「繪圖不是你的專長，去看 GitHub 或網路上是不是有相關的 skill 可以使用」。
查證：WebSearch 12 組、GitHub 搜尋、實讀 GitHub 原始檔／PyPI／npm／Hugging Face。
連不到（未繞過）：meshy.ai、tripo3d.ai、quaternius.com、app.mesh2motion.org、mixamo.com、3d.hunyuan.tencent.com、itch.io —— 這些站的額度與條款只有搜尋摘要，信心低。

結論：有現成技能可裝，但沒有任何一個能一鍵把圖轉 3D 的靜態網格變成會走、有表情、手指會動的角色。

## Claude 技能
| 名稱 | 內容 | 授權 | 評估 |
|---|---|---|---|
| Anthropic 官方 skills | 19 個技能，沒有 3D 角色類 | Apache 2.0 | 不適用 |
| EL4CTEO/blender-skills | 28 個 Blender 技能：Rigify 綁骨、AI 網格權重、ARKit 形狀鍵、動作重定向、網頁匯出，可無頭執行 | MIT | 最對題；需先裝 bpy（428 MB，下載約 1 小時，尚未實裝） |
| cesartevisual/threejs-skills | 24 個 three.js 技能（材質、燈光、載入） | MIT | 可用於頭髮光澤、材質 |
| arjun988/blender-skills | 94 個技能，需 Blender MCP | MIT | 容器不能用 MCP |
| ahujasid/mcp-for-blender | 讓 Claude 操作開著的 Blender | MIT | 容器不能用，需 Andy 電腦上開 Blender |
| op7418/guizang-game-skill | 設定圖 → Tripo 帶骨角色 → three.js | AGPL-3.0 | 只參考做法，不併入程式碼 |

## 自動綁骨與動作
| 工具 | 重點 |
|---|---|
| Mesh2Motion（網頁，MIT／素材 CC0） | Andy 可上傳 glb、手動對骨架、選動作、匯出帶動作的 glb；有無手指骨未證實 |
| UniRig | 需 8 GB 以上顯示卡，線上版目前故障 |
| Rigify＋bpy | 容器可行性中等，未實跑 |
| Quaternius 通用動作庫 | CC0、120 多個動作、為重定向設計；容器連不到下載站 |
| KayKit 動作 | CC0；本機已有；作者自述套到別的角色可能不好看 |
| Mixamo | 動作可商用但不得把原始檔再散布；public repo 放 glb 有風險 |
| three r160 SkeletonUtils.retargetClip | 內建，需骨名對照表 |
| 腳掌鎖地 | 現成函式庫都停止維護，自寫雙骨解算 |

## 表情
沒有成熟開源工具能替任意頭部自動生成混合變形。建議沿用「貼圖臉＋立體眼球＋下巴／眼球骨頭」並精修。

## 圖轉 3D 直接拿成品（信心低，需 Andy 在官網確認條款）
Tripo、Meshy 可一次給貼圖＋骨架＋動作，但免費版多為非商用，付費約每月 20 美元。
混元開源版授權排除歐盟、英國、南韓（對外販售前要再確認）。

## 採用順序
1. 動作庫重定向＋自寫腳掌鎖地（我們做）
2. 表情：貼圖臉＋立體眼球精修（我們做）
3. 頭髮光澤（我們做）
4. 需要時再評估：Mesh2Motion（Andy 操作）、bpy＋Rigify（手指骨）、付費服務
