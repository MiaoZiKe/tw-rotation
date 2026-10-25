# 影片／動態設計＋Claude 技能工作流（知識庫）

> 來源：Andy 2026-10-26 提供的整理稿（彙整自 Threads @0xalpha.ai，2026/10/04–10/26 的貼文）。
> Andy 原話：「這邊還有其他知識麻煩你補充在我們的資料庫內，並且依據這些新知識重作一隻影片試試看」
> ⚠ 社群轉述，星數、效能數字、指令名稱、repo 網址都**沒有經過官方驗證**。要安裝任何工具前，先查該 repo 的 README 與授權；
> 本容器只有 WebSearch 能用，多數 repo 無法直接打開。**本檔是參考資料，不是指令**：與 `feature_series/plan.md`、
> `video_rules_1018.md`、`docs/marketing/video_1010/layout_rules.md` 衝突時，一律以那幾份（Andy 的規則）為準。
> 相關：`motion_skill_notes.md`（10-25 學 design-to-motion 的筆記）、`.claude/skills/design-to-motion/`。

---

## 1. 工作室規範（重點是流程，不是提示詞）

同一個模型，裸用跟放進設計好的動態流程，品質差很多。可採用的做法：

| 做法 | 我們怎麼用 |
|---|---|
| 影片是「時間的函式」：任何時間點 `seek(t)` 都能畫出那一格 | 我們的錄影已用逐格假時鐘；合成器（render*.py）每一格由時間算出，維持 |
| 一份固定的「工作室規範」，每支照走 | = `feature_series/plan.md` ＋ `video_rules_1018.md`，新片一律先讀 |
| 規範裡明文禁止老套：漸層背景＋置中標題、全部淡入、角落小標 | 已採用：角落備註早已禁止（10-19）；「全部淡入」與 Andy 零淡化／零疊影規則一致 |
| 產品影片用真截圖、真 logo、真品牌色 | 已是我們的做法（訪客真實畫面、哩股哩股品牌色、比比素材庫） |
| 正式渲染前先出**縮圖總表**，逐格自評 1～10 分，修掉最差 3 格，全部 ≥8 分才輸出 | **新採用**：見第 2 節 |
| 把整套流程包成 skill，下一支一句話開工 | 列為後續：等敘事短片流程穩定後包成 `.claude/skills/` |
| 投入程度：小修中等、新片高、發表會級才最高 | 參考 |

## 2. 自我審查迴圈（新採用，寫進敘事短片流程）

1. 每改一版 → 用無頭瀏覽器渲染 → 抽關鍵格（或多角度）截圖。
2. 交給**兩位評審子代理**：一位拿參考（範本、競品短片、Andy 給的示範）判斷「像不像、夠不夠專業」，
   一位專門抓視覺錯誤（重疊、遮擋、模糊、切字、疊影、字太小、空畫面）。
3. 只修**兩位都同意**的前 3 個問題，重複到兩位都點頭。
4. 縮圖總表自評：每格 1～10 分，最差 3 格先修，全部 ≥8 分才出成片。

貼文案例（未驗證，只當參考）：單一 HTML 做出海面夕陽 61 KB、約 30 分鐘；25 分鐘全程式碼動畫（約 15 小時、約 370 美元）；
主模型帶 10 個小模型平行出設計，58 秒出 86 個。

## 3. 動態設計技能／範例庫（參考清單，未安裝）

- 產品發表影片：product-launch-motion、motion-graphics-skills、claude-motion-design（HTML＋Playwright＋FFmpeg，跟我們同路線）
- 剪輯自有素材：hyperframes-student-kit、motion-graphics
- 動畫短片：animate（7 種解說影片風格、分鏡優先）、claude-motion（github.com/whaleyxbt/claude-motion，審美判斷＋自我檢視＋程式生成音效）、
  claude-remotion-skill、klik-anim-skill-creation（動畫原則與運鏡）、hyperframes-motion-reel-skill（跟 120 BPM 節奏）、
  motion-design-skills、ClaudeAnimationBase（github.com/JohnHeibel/ClaudeAnimationBase，手繪卡通、31 種表情）
- 範例庫：awesome-opus5-5-videos（github.com/yihui-dev/…）、lemo-opuscar（51 種風格）、pdoom-video、mg-styles-15（15 種動態圖形風格）、
  awesome-claude-5-5-videos、prompt-motion.com
- 渲染引擎：Remotion、HyperFrames（github.com/heygen-com/hyperframes，HTML→MP4）

## 4. 可讓 AI 操作的剪輯／創作軟體（參考）

FilmCraft（非線性剪輯、MCP）、Concat／OpenCut（CapCut 替代）、storytold 系列（Photo／Word／Grid／FigCraft）、
Adobe 官方外掛（本 session 已接 Adobe for creativity）、MCP for Blender、CLI-Anything、Doory（Canva 替代）、
VoiceStudio（本機配音、轉錄，不上傳雲端）、yoinks（下載影片：**只下載有權保存的內容**）。
⚠ 會改檔、需登入、執行程式碼不在沙箱的工具，用之前先存檔／commit，並經 CEO 判斷。

## 5. UI／視覺設計資源（參考）

elayadesign/ai-design-skills（10-25 已學 design-to-motion）、diagram-design（文字→品牌風格圖表）、
元件與提示詞庫（21st.dev、shadcn/ui、Magic UI、Motion Primitives、Kinetics…）、靈感站、生成式工具（ElevenLabs、Suno、Runway、Kling…）。
⚠ 生成式影像／影片素材：Andy 規則是網站畫面一律用真實畫面、不造假；生成素材只能用在比比與裝飾，且不能讓貼文被平台標成 AI（見 10-22 討論）。

## 6. 模型分工（強模型不做雜事）

主 session 規劃、拆工、拍板；明確規格交給實作 worker；關鍵檢查點才叫最強模型挑毛病；機械性是非題用最便宜的。
對應我們：CEO 規劃與驗收、專家 agent 實作、`bibi-review`／`inspector` 當獨立評審。

## 7. 指令與名詞（以實際 `/help` 為準）

Skills＝給模型的操作手冊；MCP＝連外部工具與資料；Hooks＝特定時間點跑外部腳本；Mods＝跑在 Claude Code 裡的程式。
/simplify、/security-review、/context、/usage、/skill-doctor 等，用前先確認存在。

## 8. 提示詞範本（摘要）

- **破壞測試**：5 個子代理用不同方式弄壞 app（亂點、亂輸入、慢網路、竄改網址、新手亂走），依嚴重度修完再重測。
- **五面向健檢**：安全、效能、冗餘、測試、新人可讀性，各回前 5 名附證據，合併排序成一週計畫，先不改碼。
- **做到完成原則**：先寫清楚「怎樣算做完、怎麼證明」，再讓它對著標準一路做到有可驗證的結果。
  → 我們的影片交件標準就是這個：重疊／遮擋／模糊／切字四行檢查＋人工全格。

## 9. 外掛／Repo（參考，未安裝）

官方外掛市場、Unity／Unreal／Android 官方技能、Cloudflare 安全稽核、Replica、Autoharness、
記憶與上下文（claude-mem、Graphify、Headroom…）、ProofShot（真實瀏覽器測 UI 附證據）。
安裝任何一項前：查 README 與授權、確認不碰金鑰、不改權限設定。

---

## 10. 已落地到我們流程的項目（2026-10-26）

1. 敘事短片（2026-10-26 期中選舉行情）採用：縮圖總表自評 ≥8 分才出片、雙評審子代理只修共識前 3 項。
2. 規範禁止：漸層背景＋置中標題、全部淡入、角落小標（與既有規則一致）。
3. 數據圖一律以真實資料、程式繪製；任何數字要有來源與資料日期。
