<#
  台股資金輪動儀表板 — 一鍵設定

  設計原則：可以重複執行。每一步都先檢查現況，已經做好的就跳過，
  所以中途失敗或想補設定時，直接再跑一次就好。
#>

param(
  [switch]$ChangeToken,   # 強制重新輸入 FinMind token
  [switch]$NoBackfill,    # （保留相容）不觸發歷史回補
  [switch]$Backfill       # 強制觸發歷史回補（預設只在第一次安裝時觸發）
)

# 注意：這裡刻意用 Continue 而不是 Stop。
# PowerShell 5.1 會把 git/gh 寫到 stderr 的「提醒」也當成錯誤，
# 例如 "LF will be replaced by CRLF" 這種純警告會直接中斷整個腳本。
# 所以改成逐步檢查 $LASTEXITCODE，而不是靠例外。
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
Set-Location -LiteralPath $PSScriptRoot

function Say($msg)  { Write-Host "`n$msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Die($msg)  {
  Write-Host "`n[停止] $msg`n" -ForegroundColor Red
  Read-Host "按 Enter 關閉"
  exit 1
}
function Have($cmd) { $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue) }

# 執行外部指令並吞掉 stderr 的雜訊，只用結束代碼判斷成敗
function Run {
  param([string]$exe, [string[]]$cmdArgs, [switch]$Quiet)
  $out = & $exe @cmdArgs 2>&1
  $code = $LASTEXITCODE
  if (-not $Quiet -and $code -ne 0) {
    $text = ($out | Out-String).Trim()
    if ($text) { Write-Host "      $text" -ForegroundColor DarkGray }
  }
  return $code
}

function RefreshPath {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
              [Environment]::GetEnvironmentVariable("Path", "User")
}

Write-Host @"

  台股資金輪動儀表板 — 一鍵設定
  ================================
  這支腳本可以重複執行，做過的步驟會自動跳過。

"@ -ForegroundColor White

# ---------------------------------------------------------------- 1. 工具
Say "[1/8] 檢查需要的工具"

foreach ($t in @(
  @{cmd="python"; id="Python.Python.3.12"; name="Python"; url="https://www.python.org/downloads/"},
  @{cmd="git";    id="Git.Git";            name="Git";    url="https://git-scm.com/download/win"},
  @{cmd="gh";     id="GitHub.cli";         name="GitHub CLI"; url="https://cli.github.com"}
)) {
  if (-not (Have $t.cmd)) {
    if (Have winget) {
      Warn "找不到 $($t.name)，正在安裝…"
      winget install -e --id $t.id --accept-source-agreements --accept-package-agreements --silent | Out-Null
      RefreshPath
    }
    if (-not (Have $t.cmd)) { Die "找不到 $($t.name)。請到 $($t.url) 安裝後重跑這支腳本。" }
  }
  Ok $t.name
}

# ---------------------------------------------------------------- 2. GitHub 登入
Say "[2/8] GitHub 登入"
gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Warn "接下來會開瀏覽器讓你登入 GitHub，登入完回到這個視窗。"
  gh auth login --hostname github.com --git-protocol https --web --scopes "repo,workflow"
  gh auth status 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { Die "GitHub 登入沒有完成。" }
}
$me = (gh api user --jq .login 2>$null)
if (-not $me) { Die "拿不到 GitHub 帳號名稱，請確認 gh auth status 正常。" }
Ok "已登入：$me"

$repoName = "tw-rotation"
$slug = "$me/$repoName"

# ---------------------------------------------------------------- 3. FinMind token
Say "[3/8] FinMind token"
$hasSecret = $false
$secretList = (gh secret list --repo $slug 2>$null | Out-String)
if ($secretList -match "FINMIND_TOKEN") { $hasSecret = $true }

$finmind = ""
if ($hasSecret -and -not $ChangeToken) {
  # 已經存在 GitHub Secrets 裡了，不需要每次重貼
  Ok "FINMIND_TOKEN 已存在，直接沿用"
  Write-Host "     要換新的 token：用 update.bat -ChangeToken 或刪掉 repo 的 secret 再跑一次" -ForegroundColor DarkGray
} else {
  if (-not $hasSecret) {
    Write-Host "  到 https://finmindtrade.com 註冊並驗證 email，登入後複製 API token。"
    Write-Host "  直接按 Enter 可以跳過（之後重跑這支腳本再補即可）。"
  }
  Write-Host "  提示：貼上時不會顯示內容，這是正常的。" -ForegroundColor DarkGray
  $secure = Read-Host "  貼上 FinMind token" -AsSecureString
  $finmind = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}

# ---------------------------------------------------------------- 4. repo
Say "[4/8] 建立 / 確認 GitHub repo"

if (-not (Test-Path ".git")) {
  Run git @("init","-q") | Out-Null
  Run git @("branch","-M","main") | Out-Null
}

# 這個 repo 的檔案一律以原樣存放，不做換行轉換 ——
# 免得 git 一直發 CRLF 警告，也避免 .ps1 的 BOM/換行被改掉
Run git @("config","--local","core.autocrlf","false") | Out-Null
Run git @("config","--local","core.safecrlf","false") | Out-Null
Run git @("config","--local","user.name",$me) | Out-Null
Run git @("config","--local","user.email","$me@users.noreply.github.com") | Out-Null

gh repo view $slug 2>&1 | Out-Null
$repoExists = ($LASTEXITCODE -eq 0)
$firstInstall = -not $repoExists

if (-not $repoExists) {
  Run git @("add","-A") | Out-Null
  Run git @("commit","-q","-m","初始版本：台股資金輪動儀表板") -Quiet | Out-Null
  $code = Run gh @("repo","create",$repoName,"--public","--source=.","--remote=origin","--push")
  if ($code -ne 0) { Die "建立 repo 失敗，詳細訊息在上面。" }
  Ok "已建立 https://github.com/$slug"
} else {
  Ok "使用既有的 https://github.com/$slug"
  $remotes = (git remote 2>$null)
  if ($remotes -notcontains "origin") {
    Run git @("remote","add","origin","https://github.com/$slug.git") | Out-Null
  }

  # 同步策略（重要）：
  #   雲端 repo 是「資料」的權威 —— GitHub Actions 每天把 parquet commit 進去。
  #   本地只擁有「程式碼」。所以每次推送前：
  #     1. 抓下遠端，把本地分支對齊遠端頂端（index 也對齊）
  #     2. data/ 與 site/data/ 一律還原成遠端版本，本地過期的資料絕不蓋上去
  #     3. 只把程式碼的差異做成一個新 commit，快轉推送
  #   永遠不 force push —— 那會把雲端累積的歷史資料整個抹掉。
  $pushed = $false
  for ($try = 1; $try -le 4; $try++) {
    Run git @("fetch","origin","main") -Quiet | Out-Null
    Run git @("reset","--mixed","origin/main") -Quiet | Out-Null
    Run git @("checkout","origin/main","--","data") -Quiet | Out-Null
    Run git @("add","-A") | Out-Null
    $staged = (git diff --staged --name-only 2>$null | Measure-Object -Line).Lines
    if ($staged -eq 0) {
      Ok "程式碼與雲端一致，不需要推送"
      $pushed = $true
      break
    }
    Run git @("commit","-q","-m","更新程式碼") -Quiet | Out-Null
    $code = Run git @("push","origin","HEAD:main") -Quiet
    if ($code -eq 0) {
      Ok "程式碼已推送（$staged 個檔案變動）"
      $pushed = $true
      break
    }
    Warn "推送被拒（第 $try 次），雲端剛有新資料進來，重新對齊後再試…"
    Start-Sleep -Seconds ($try * 4)
  }
  if (-not $pushed) { Die "連續四次推送失敗。請等 Actions 跑完（沒有 In progress）後再重跑。" }
}

# ---------------------------------------------------------------- 5. Secrets
Say "[5/8] 設定 Secrets"
if ($finmind -and $finmind.Trim()) {
  $finmind.Trim() | gh secret set FINMIND_TOKEN --repo $slug 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { Ok "FINMIND_TOKEN 已寫入" } else { Warn "寫入失敗，等下可到 Settings → Secrets 手動新增" }
  $useFinmind = $true
} elseif ($hasSecret) {
  Ok "沿用既有的 FINMIND_TOKEN"
  $useFinmind = $true
} else {
  Warn "沒有 FinMind token —— 法人籌碼與歷史回補會停用"
  $useFinmind = $false
}

# ---------------------------------------------------------------- 6. 權限與 Pages
Say "[6/8] Actions 寫入權限與 GitHub Pages"

gh api -X PUT "repos/$slug/actions/permissions/workflow" `
  -f default_workflow_permissions=write -F can_approve_pull_request_reviews=false 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { Ok "Actions 可以回寫資料" }
else { Warn "設定失敗 —— 請手動到 Settings → Actions → General 勾 Read and write permissions" }

$pagesOk = $false
gh api -X POST "repos/$slug/pages" -f "build_type=workflow" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { $pagesOk = $true }
if (-not $pagesOk) {
  gh api -X PUT "repos/$slug/pages" -f "build_type=workflow" 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { $pagesOk = $true }
}
if ($pagesOk) { Ok "GitHub Pages 已開啟" }
else { Warn "自動開啟失敗 —— 請手動到 Settings → Pages → Source 選 GitHub Actions" }

# ---------------------------------------------------------------- 7. 抓取
Say "[7/8] 資料抓取"
Write-Host "  網站部署已獨立成「部署網站」工作流，程式碼一推上去 1-2 分鐘就上線，" -ForegroundColor DarkGray
Write-Host "  不用等資料抓完。這一步只負責資料。" -ForegroundColor DarkGray
Start-Sleep -Seconds 2
$active = (gh run list --repo $slug --workflow daily.yml --status in_progress --limit 1 --json databaseId 2>$null | Out-String)
$queued = (gh run list --repo $slug --workflow daily.yml --status queued --limit 1 --json databaseId 2>$null | Out-String)
if (($active -match "databaseId") -or ($queued -match "databaseId")) {
  Ok "每日管線已經有一輪在跑或排隊中，不重複觸發"
} else {
  gh workflow run "daily.yml" --repo $slug 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { Ok "每日管線已啟動（約 3-5 分鐘）" }
  else { Warn "自動觸發失敗 —— 到 Actions 頁面手動按 Run workflow" }
}

# ---------------------------------------------------------------- 8. 歷史回補
if ($useFinmind -and ($firstInstall -or $Backfill) -and -not $NoBackfill) {
  Say "[8/8] 觸發歷史回補"
  Write-Host "  補十年歷史，約一小時。它在雲端跑，你可以直接關掉這個視窗。"
  Start-Sleep -Seconds 5
  gh workflow run "backfill.yml" --repo $slug -f limit=400 -f start_date=2016-01-01 -f datasets=price+inst 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { Ok "歷史回補已啟動" }
  else { Warn "自動觸發失敗 —— 到 Actions → 歷史回補 手動按 Run workflow" }
} else {
  Say "[8/8] 略過歷史回補"
  Write-Host "  （只在第一次安裝時自動跑；要再補請用 backfill-financials.bat 或加 -Backfill）" -ForegroundColor DarkGray
}

# ---------------------------------------------------------------- 完成
$pagesUrl = "https://$($me.ToLower()).github.io/$repoName/"
Write-Host @"

  ================================================
  設定完成

  儀表板網址（3-5 分鐘後可以開）：
    $pagesUrl

  執行狀況：
    https://github.com/$slug/actions

  手機：用瀏覽器開網址 →
    iOS 分享 → 加入主畫面　/　Android 選單 → 加到主畫面

  之後每個交易日台北時間 18:30 自動更新，不用再碰它。
  ================================================

"@ -ForegroundColor White

# 桌面捷徑：之後要看儀表板直接點它，不用再跑這支腳本
# （用 .NET 直接寫檔，PowerShell 5.1 的 Set-Content 接 here-string 會出「資料流不可讀取」）
try {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $lnk = Join-Path $desktop "台股儀表板.url"
  $body = "[InternetShortcut]`r`nURL=$pagesUrl`r`nIconIndex=0`r`n"
  [System.IO.File]::WriteAllText($lnk, $body, [System.Text.Encoding]::ASCII)
  if ((Test-Path -LiteralPath $lnk) -and ((Get-Item -LiteralPath $lnk).Length -gt 0)) {
    Ok "桌面已建立捷徑「台股儀表板」"
  } else {
    Warn "桌面捷徑沒有寫成功（不影響使用，直接用上面的網址）"
  }
} catch {
  Warn "桌面捷徑建立失敗：$($_.Exception.Message)（不影響使用）"
}

$open = Read-Host "  現在開啟 Actions 頁面看跑的狀況嗎？(Y/n)"
if ($open -ne "n" -and $open -ne "N") {
  Start-Process "https://github.com/$slug/actions"
}
Read-Host "  按 Enter 關閉"
