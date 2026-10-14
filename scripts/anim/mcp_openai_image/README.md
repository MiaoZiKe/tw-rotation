# OpenAI 產圖 MCP 伺服器（給本機 Claude Code 用）

讓 Claude Code 能直接呼叫 OpenAI 產圖，並依「角色參考圖」一格一格產生 12 格分鏡、合成透明 GIF／WebP。
金鑰只放在你本機（Claude Code 的設定），**不進 repo、不貼進聊天室**。

## 五個工具
| 工具 | 做什麼 |
|---|---|
| `generate_image` | 文字產圖，可要求透明背景 |
| `edit_image_from_reference` | 依一張或多張參考圖改圖（角色造型要一致時用，預設高保真） |
| `generate_frames_from_reference` | 依同一張角色參考圖，逐格產生 12 格關鍵影格；中斷後再叫一次會跳過已完成的格 |
| `make_gif_from_frames` | 影格合成透明 GIF，並同時輸出動態 WebP（網頁用 WebP 較好） |
| `make_contact_sheet` | 影格排成帶格號的總覽圖，給人逐格檢查 |

## 安裝（Windows，只做一次）
1. 開 PowerShell（一般權限就可以），貼上這兩行：
```
Invoke-WebRequest https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/scripts/anim/mcp_openai_image/setup.ps1 -OutFile $HOME\setup-openai-mcp.ps1
powershell -ExecutionPolicy Bypass -File $HOME\setup-openai-mcp.ps1
```
2. 照畫面指示貼上 OpenAI API Key（輸入時不會顯示，這是正常的）。
3. 重開 Claude Code，輸入 `/mcp`，看到 `openai-image` 是 connected、5 個工具就成功了。

## 使用
對 Claude Code 說：
- 「用 openai-image 的 edit_image_from_reference，以 C:\路徑\default_idle.png 當參考，產生比比側面跑步，存成 run_01.png」
- 「用 generate_frames_from_reference，參考圖是 …，12 格分別是…，透明背景，存到 …」
- 「用 make_gif_from_frames 把這 12 張合成 GIF，每格 80 毫秒」

## 在雲端 session 直接用（不需要本機 Claude Code）
Andy 的日常是用雲端 session，本機沒有 `claude` 指令。這種情況下不用註冊 MCP，雲端的 Claude 直接 import 同一支程式呼叫即可：
1. 環境設定（claude.ai/code 輸入框上方的雲端圖示 → 環境旁的齒輪）。Pro／Max 方案優先用 **Network secrets**：Add secret，Allowed websites 填 `api.openai.com`，Custom headers 的 Name 填 `Authorization`、Prefix 填 `Bearer`、Value 貼金鑰，按 Connect；金鑰不進 VM，Claude 呼叫時設 `OPENAI_API_KEY=proxy-injected` 當佔位即可。沒有這一區的方案：Network access 選 Custom 加 `api.openai.com`，並把 `OPENAI_API_KEY=金鑰` 放環境變數。金鑰一律不貼進聊天室。
2. 新開一個 session，Claude 用 `python3 -c "import sys; sys.path.insert(0,'scripts/anim/mcp_openai_image'); import openai_image_mcp as m; ..."` 呼叫 `m.generate_image(...)`、`m.edit_image_from_reference(...)`、`m.generate_frames_from_reference(...)`、`m.make_gif_from_frames(...)`。
3. 產出放 repo 內的 `docs/anim/…`，審過才 commit（金鑰永遠不進 repo）。

## 注意
- OpenAI API 是另外計費，跟 ChatGPT Plus 無關；帳號要有可用額度，不然會回 `insufficient_quota`。
- `size` 只支援 `1024x1024`、`1536x1024`、`1024x1536`、`auto`（不支援 2048x2048）；要更高解析度請產圖後另外放大。
- 換模型：設環境變數 `OPENAI_IMAGE_MODEL`（預設 `gpt-image-1`）。
- 產出預設放 `~/openai-image-outputs`，也可以每次指定 `output_dir`。
- 這個伺服器只能在「你自己電腦上的 Claude Code」使用；雲端 session 的網路擋住 api.openai.com，叫不到。
- 套件版本：`mcp` 2.x 把 `FastMCP` 改名成 `MCPServer`，程式兩種都支援，不用擔心。
