# 比比動畫用：OpenAI 產圖 MCP 伺服器，一鍵安裝（Windows PowerShell）
# 做的事：下載伺服器程式 → 建 Python 3.12 虛擬環境 → 安裝套件 → 詢問金鑰（不會顯示、不會存進專案）→ 註冊到 Claude Code
$ErrorActionPreference = "Stop"
$dir  = Join-Path $HOME "mcp-openai-image"
$base = "https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/scripts/anim/mcp_openai_image"

Write-Host "1/5 建立資料夾 $dir"
New-Item -ItemType Directory -Force $dir | Out-Null

Write-Host "2/5 下載伺服器程式"
foreach ($f in @("openai_image_mcp.py", "requirements.txt")) {
    Invoke-WebRequest -Uri "$base/$f" -OutFile (Join-Path $dir $f) -UseBasicParsing
}

Write-Host "3/5 建立 Python 3.12 虛擬環境並安裝套件（約 1～2 分鐘）"
py -3.12 -m venv (Join-Path $dir ".venv")
$py = Join-Path $dir ".venv\Scripts\python.exe"
& $py -m pip install --upgrade pip -q
& $py -m pip install -r (Join-Path $dir "requirements.txt") -q
& $py -c "import sys; sys.path.insert(0, r'$dir'); import openai_image_mcp as m; print('伺服器程式載入成功')"

Write-Host "4/5 貼上你的 OpenAI API Key（輸入時畫面不會顯示任何字，貼上後按 Enter）"
$sec   = Read-Host "OpenAI API Key" -AsSecureString
$bstr  = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$key   = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
if (-not $key) { throw "沒有輸入金鑰" }

Write-Host "5/5 註冊到 Claude Code"
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { throw "找不到 claude 指令，請先安裝 Claude Code" }
claude mcp remove openai-image --scope user 2>$null
claude mcp add --transport stdio --scope user --env "OPENAI_API_KEY=$key" openai-image -- $py (Join-Path $dir "openai_image_mcp.py")
$key = $null

Write-Host ""
Write-Host "完成。請重開 Claude Code，輸入 /mcp 應該會看到 openai-image 已連線，有 5 個工具。"
