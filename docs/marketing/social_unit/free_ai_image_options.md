# 免費 AI 產圖方法比較（2026-10-28）

起因：OpenAI 產圖額度用完（429）。Andy 2026-10-28：「找出所有可以免費生成 AI 圖片的方法，並且每個都先生成，讓美編審核」。

試跑工作流：`.github/workflows/ai_image_trial.yml`（手動觸發），產出放在 `ai-image-trial` 分支的 `trial/<方法>/`（不進 main、不進公開網站）。
三個測試題：①明亮白天晶圓廠內部 ②明亮白天交易桌（螢幕只有抽象線圖）③明亮白天城市金融區街景；皆要求無文字、無標誌、無真實建築。

## 一、實測結果（GitHub Actions 上，2026-10-28 台北凌晨）

| 方法 | 結果 | 每張秒數 | 解析度 | 備註 |
|---|---|---|---|---|
| Pollinations（免金鑰） | 成功 3/3（第一輪第三張被限速 402，改 50 秒間隔重跑後全過） | 0.4～7 秒 | 686×858（要求 1080×1350 被降級） | **免金鑰版右下角有「pollinations.ai」浮水印**，加 `nologo=true` 無效；限 1 張／45 秒／IP。品質普通，人物細節差 |
| Cloudflare Workers AI（flux-1-schnell） | 失敗：401 驗證錯誤 | — | — | 現有 `CLOUDFLARE_API_TOKEN` 只有部署 Worker 權限，沒有 Workers AI 權限 |
| Cloudflare Workers AI（SDXL） | 失敗：401（同上） | — | — | 同上 |
| 本機開源 SD-Turbo（Actions CPU） | 成功 3/3 | 約 45 秒（含模型載入 21 秒另計） | 512×640 | 無浮水印、免金鑰；解析度低需放大，構圖還可以但細節粗 |

## 二、各方法總表

| 方法 | 免費額度 | 需要金鑰／Andy 要做什麼 | 商用授權 | 品質 | 本環境可用？ |
|---|---|---|---|---|---|
| Cloudflare Workers AI（flux-1-schnell、SDXL 等） | 每天 10,000 Neurons（UTC 00:00 重置），flux-1-schnell 約可產數百張 1024 圖 | 建一把有「Workers AI」權限的 API 權杖，存成 GitHub Secret（步驟見第三節 A） | FLUX.1-schnell 為 Apache-2.0，可商用 | 好（四方法中預期最佳） | 補權杖後可在 Actions 跑 |
| Google Gemini／Imagen（AI Studio） | 來源互相矛盾：有說 API 免費層圖片配額已歸零（2026-02），有說 Flash Image 每天可數百張；AI Studio 網頁版有免費額度 | 申請 AI Studio 金鑰存成 Secret（第三節 B）；可能需綁帳單 | 依 Google 條款，產出可商用，圖上帶 SynthID 隱形浮水印 | 很好 | 補金鑰後可試；免費配額不保證 |
| Hugging Face Inference Providers | 免費帳號每月約 0.10 美元額度（只夠幾張） | 申請 HF 權杖（第三節 C） | 依模型授權（FLUX.1-schnell 可商用；FLUX.1-dev 不可商用） | 好 | 補權杖後可試，量太少不適合日常 |
| Pollinations.ai | 免金鑰：1 張／45 秒／IP、帶浮水印；註冊金鑰可去浮水印 | 不用（免金鑰版）；要去浮水印需在 enter.pollinations.ai 註冊 | 官方條款查無明確商用聲明，**低信心** | 普通 | 已實測可用 |
| 開源模型本機跑（SD-Turbo，Actions CPU） | 無上限（Actions 分鐘數內，public repo 免費） | 不用 | SD-Turbo 為 Stability 社群授權，年營收 100 萬美元以下可商用 | 普通偏低，512 解析度 | 已實測可用 |
| Together AI | 2024 年的 FLUX.1-schnell 免費端點為限時 3 個月，2026 年查無仍存在的證據 | 需金鑰＋信用卡 | — | 好 | 未試（無確認的免費額度） |
| Replicate／Stability AI | 查無 2026 年確認的免費試用額度 | 需金鑰＋付費 | — | 好 | 未試 |
| Canva（本工作階段有連接器） | Canva 帳號內含 AI 產圖次數 | 不用另外申請 | 依 Canva 條款可商用 | 好 | 能產圖，但下載高解析原圖的網域被本容器擋，只拿到 161×200 預覽；需改在 Andy 電腦上下載 |
| Figma 產圖（generate_image） | 依 Figma 方案的 AI 點數 | 不用另外申請 | 依 Figma 條款 | 好 | 本次 Figma 連接器連線失敗（代理 403），未試 |
| Adobe Firefly | 網頁版免費帳號每月少量生成點數（約 25，有浮水印）；API 只開放企業 | 網頁手動操作，無法自動化 | 標榜商用安全 | 很好 | 無法程式呼叫 |

## 三、需要 Andy 申請的項目（不擋其他工作，可先不做；Pollinations 與本機開源已可用）

### A. Cloudflare Workers AI 權杖（建議第一優先，免費量最大）
1. 開 <https://dash.cloudflare.com/profile/api-tokens> → 按 **Create Token**（建立權杖）。
2. 在「Workers AI」那列範本按 **Use template**（使用範本）。沒看到就選最下面 **Create Custom Token**（自訂權杖）。
3. 欄位：

| 欄位 | 填什麼 |
|---|---|
| Token name（名稱） | `workers-ai-image` |
| Permissions（權限） | 左：`Account`、中：`Workers AI`、右：`Read`；再加一列 `Account`／`Workers AI`／`Edit` |
| Account Resources（帳戶範圍） | `Include` ＋ 你的帳號 |
| 其他（IP 篩選、TTL） | 不用動 |

4. 按 **Continue to summary**（繼續）→ **Create Token**（建立）→ 複製畫面上的權杖（只顯示一次）。
5. 開 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new>：Name 填 `CLOUDFLARE_AI_TOKEN`，Secret 貼上剛剛的權杖，按 **Add secret**（新增）。
6. 回我「Cloudflare AI 權杖加好了」，我改工作流讀這把權杖重跑。

### B. Google AI Studio 金鑰
1. 開 <https://aistudio.google.com/apikey> → 按 **Create API key**（建立金鑰）→ 選任一 Google Cloud 專案（沒有就讓它自動建）。
2. 複製金鑰 → 開 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new>：Name 填 `GEMINI_API_KEY`，Secret 貼上，按 **Add secret**。
3. 回我「Gemini 金鑰加好了」。（若之後顯示免費配額為 0，不要綁信用卡，告訴我即可。）

### C. Hugging Face 權杖（量很小，可最後做）
1. 開 <https://huggingface.co/settings/tokens/new?tokenType=fineGrained> → Token name 填 `image-trial`，勾 **Make calls to Inference Providers**（呼叫推論服務），其他不用動 → **Create token**。
2. 開 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new>：Name 填 `HF_TOKEN`，貼上，按 **Add secret**。

## 四、來源（WebSearch 摘要，未讀原文）
- Cloudflare Workers AI 價格：<https://developers.cloudflare.com/workers-ai/platform/pricing/>
- Hugging Face 免費額度：<https://huggingface.co/docs/inference-providers/pricing>
- Gemini 免費配額（第三方，互相矛盾，低信心）：<https://blog.laozhang.ai/en/posts/gemini-image-api-free-tier>、<https://tech-insider.org/how-to-use-nano-banana-pro-api-2026/>
- Pollinations 限速：實測回應「Free limit reached: 1 image every 45 seconds per IP」
- Together AI 免費 FLUX（2024 限時）：<https://together.ai/blog/flux-api-is-now-available-on-together-ai-new-pro-free-access-to-flux-schnell>
- Adobe Firefly 價格：<https://www.adobe.com/products/firefly/pricing-info.html>

## 五、美編審核（2026-10-28）

依 `ai_image_review.md` 十條逐張全解析度審。只有兩種方法有成品（Cloudflare flux／SDXL 因 401 無圖，不審）。灰階亮度為實測（0～255）。
通則：兩方法寬度都 < 1080，**第 7 條一律退回**；依 `ai_image_review.md` 第四節「任何一條退回＝整張退回」，6 張嚴格說都不得直接上線，下表同時列出「其他條是否過」供選型。

### 逐張判定（○通過　✕退回，編號對應十條）

| 圖 | 亮度 | 1 無字 | 2 無真實物 | 3 無畸形 | 4 明亮 | 5 色票 | 6 不擋標題 | 7 解析度 | 8 主題 | 9 版權 | 10 質感 | 結論 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Pollinations 晶圓廠 | 161 | ✕ 右下「pollinations.ai」浮水印 | ○ | ✕ 防塵衣人形臉部融化、左側設備穿插 | ○ | ○ 冷白藍 | ○ 主體居中偏上，下方地板空 | ✕ 686 寬 | ○ | ✕ 浮水印＝需交代來源與條款（商用聲明低信心） | ✕ 人影突兀 | 退回 |
| Pollinations 交易桌 | 90 | ✕ 浮水印 | ○ | ✕ 桌椅透視亂、失焦糊 | ✕ 偏暗 | ✕ 暗綠灰＋暖黃地板光斑 | ✕ 下半部高對比桌面 | ✕ | ○ | ✕ | ✕ | 退回 |
| Pollinations 金融區 | 99 | ✕ 浮水印 | ○ 虛構泛型 | ○ 大致合理，霧化嚴重 | ✕ 偏暗 | ○ 藍系但偏深 | ✕ 建築塞滿全幅，無留白 | ✕ | ○ | ✕ | ✕ 塑膠霧感、右側黑塊 | 退回 |
| SD-Turbo 晶圓廠 | 155 | ○ 目視無字（右側螢幕、牌面細碎，3 倍放大建議再確認） | ○ | ✕ 數位人物肢體變形、地面網格重複不自然 | ○ | ○ 白灰＋藍，有零星紅色 | ✕ 人物與細節鋪滿下半部 | ✕ 512 寬 | ○ | ○ 本機模型、無浮水印 | ✕ 紅藍小物雜 | 退回 |
| SD-Turbo 交易桌 | 138 | ○ | ○ | ○ 椅子、桌面大致自然 | ○ | ✕ 大面積綠藤＋青藍牆，偏卡通 | ✕ 下半部椅子地毯高對比 | ✕ | △ 與交易桌題意相近，但偏「綠化辦公室」 | ○ | ✕ 卡通插畫感 | 退回 |
| SD-Turbo 金融區 | 131 | ○ | ○ 泛型大樓 | ✕ 路人糊成色塊、窗格重複 | ○ | ○ 藍天藍玻璃 | ✕ 地面人群與大樓佔滿 | ✕ | ○ | ○ | ✕ 路面紅點人群雜 | 退回 |

### 放大／浮水印／用途

| 方法 | 放大到 1080×1350 可用？ | 浮水印能否裁掉 | 適合用途 |
|---|---|---|---|
| Pollinations | 686→1080 需放大 1.57 倍，圖本身已糊，再放大更軟；僅「晶圓廠」勉強看得過 | 浮水印約在右下 150×22 px，裁掉下緣約 3% 即可，但裁後尺寸更小、構圖微動；不建議以「裁掉」處理條款疑慮（商用聲明低信心） | 不建議用於封面；僅可當內頁小插圖（縮小到 ≤ 540 寬、裁掉浮水印、加遮罩）；暗圖（交易桌、金融區）不要用 |
| SD-Turbo（本機） | 512→1080 需放大 2.1 倍，細節會糊成油畫感；金融區放大後最耐看 | 無浮水印 | 封面背景不夠格（解析度、畫面太滿）；可當「大幅模糊＋白色漸層遮罩」的底圖，或內頁小插圖（≤ 400 寬）；需先用放大模型或加雜訊顆粒處理 |
| Cloudflare Workers AI | 未產出（401），不評分；預期 1024 級可用 | — | 待 Andy 補 Workers AI 權杖後重審 |

### 每方法總評與排名

1. **本機 SD-Turbo：第 1 名（相對最佳，但仍不直接過審）。** 亮度三張皆 ≥ 120、色調接近品牌亮冷色、無浮水印、授權單純。缺點是 512 解析度、人物畸形、畫面過滿。推薦：只當「模糊／漸層遮罩後的氣氛底圖」或內頁小插圖，且要求 prompt 去掉人物、減少雜物。
2. **Pollinations：第 2 名。** 兩張偏暗不合格，且免金鑰版有浮水印、版權聲明不明、限速 1 張／45 秒。僅晶圓廠一張亮度夠。不建議納入日常流程；若註冊金鑰去浮水印、取得 1080 以上，才重審。
3. **Cloudflare Workers AI：無成品，待補權杖。** 官方資料顯示免費量最大、FLUX 授權可商用，預期是最有機會達 1080 以上的方案，建議 Andy 先做第三節 A。

建議：目前三張都不上線；貼文背景仍以純色／漸層或比比素材庫為主。若要用 AI 圖，先補 Cloudflare 權杖，產 1080×1350、prompt 加「無人物、極簡、上緣主體、下方留白、明亮」後重審。
