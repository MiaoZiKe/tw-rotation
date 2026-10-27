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
