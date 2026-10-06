# 一鍵安裝：把腳本複製到 %LOCALAPPDATA%\tw-ops，寫設定檔（不含密碼），在工作排程器建兩個排程。
#   tw-ops 監控：每 5 分鐘
#   tw-ops 每日備份：每天 22:00（筆電時區請設台北）
# 不需要系統管理員權限：排程用目前登入的使用者、「只有登入時才執行」。
param(
    [string]$GmailTo = '',          # 收通知的信箱（留空＝不寄信）
    [string]$NtfyTopic = '',        # ntfy.sh 的主題名稱（留空＝不推手機）
    [string]$BackupRoot = '',       # 備份位置（留空＝有 D 槽用 D:\tw-backup，否則用 使用者資料夾\tw-backup）
    [switch]$NoDesktop              # 不要桌面通知
)
$ErrorActionPreference = 'Stop'
$ops = Join-Path $env:LOCALAPPDATA 'tw-ops'
New-Item -ItemType Directory -Force -Path $ops | Out-Null

# 1. 檢查 git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host '找不到 git。請先安裝 Git for Windows（https://git-scm.com/download/win），裝完重開 PowerShell 再跑一次。' -ForegroundColor Red
    exit 1
}

# 2. 複製腳本
foreach ($f in @('common.ps1', 'monitor.ps1', 'backup.ps1', 'test-notify.ps1', 'uninstall.ps1')) {
    Copy-Item -Force (Join-Path $PSScriptRoot $f) (Join-Path $ops $f)
}

# 3. 備份位置
if (-not $BackupRoot) {
    if (Test-Path 'D:\') { $BackupRoot = 'D:\tw-backup' } else { $BackupRoot = Join-Path $env:USERPROFILE 'tw-backup' }
}

# 4. 設定檔（只有網址與信箱，沒有任何密碼）。重跑 install 會保留舊設定裡沒被參數覆蓋的值。
$cfgPath = Join-Path $ops 'config.json'
$old = $null
if (Test-Path $cfgPath) { $old = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json }
if (-not $GmailTo -and $old) { $GmailTo = $old.gmail_to }
if (-not $NtfyTopic -and $old) { $NtfyTopic = $old.ntfy_topic }
$cfg = [ordered]@{
    site_url       = 'https://miaozike.github.io/tw-rotation/'
    account_api    = 'https://tw-account.kcq01010909.workers.dev'
    last_run_url   = 'https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/data/_state/last_run.json'
    repo_url       = 'https://github.com/MiaoZiKe/tw-rotation.git'
    backup_root    = $BackupRoot
    keep_days      = 14
    gmail_to       = $GmailTo
    ntfy_topic     = $NtfyTopic
    notify_desktop = (-not $NoDesktop)
}
$cfg | ConvertTo-Json | Set-Content -Path $cfgPath -Encoding UTF8

# 5. 工作排程器
$ps = (Get-Command powershell.exe).Source
$user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$monArgs = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $ops 'monitor.ps1') + '"'
$monTrig = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName 'tw-ops 監控' -Action (New-ScheduledTaskAction -Execute $ps -Argument $monArgs) -Trigger $monTrig -Principal $principal -Settings $settings -Force | Out-Null

$bakArgs = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $ops 'backup.ps1') + '"'
$bakTrig = New-ScheduledTaskTrigger -Daily -At '22:00'
Register-ScheduledTask -TaskName 'tw-ops 每日備份' -Action (New-ScheduledTaskAction -Execute $ps -Argument $bakArgs) -Trigger $bakTrig -Principal $principal -Settings $settings -Force | Out-Null

# 6. 提醒：Gmail 密碼存在憑證管理員，不存在任何檔案
. (Join-Path $ops 'common.ps1')
Write-Host ''
Write-Host '安裝完成。' -ForegroundColor Green
Write-Host ('  腳本與設定：' + $ops)
Write-Host ('  備份位置：  ' + $BackupRoot)
Write-Host '  排程：tw-ops 監控（每 5 分鐘）、tw-ops 每日備份（每天 22:00）'
if ($GmailTo -and $null -eq (Get-GmailCredential)) {
    Write-Host ''
    Write-Host '還差一步：把 Gmail 應用程式密碼存進 Windows 憑證管理員（照 README 第 3 步）：' -ForegroundColor Yellow
    Write-Host '  cmdkey /generic:tw-ops-gmail /user:你的Gmail地址 /pass'
}
$tz = (Get-TimeZone).Id
if ($tz -ne 'Taipei Standard Time') { Write-Host ('注意：這台電腦的時區是 ' + $tz + '，備份會在當地 22:00 跑，不是台北 22:00。') -ForegroundColor Yellow }
Write-Host ''
Write-Host '下一步：執行一次監控看結果 →  powershell -ExecutionPolicy Bypass -File "' -NoNewline
Write-Host ((Join-Path $ops 'monitor.ps1') + '" -Once')
