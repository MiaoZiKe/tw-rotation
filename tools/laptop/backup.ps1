# 每日備份（工作排程器每天台北 22:00 跑一次）。只從 GitHub 往筆電拉，不往外推任何東西。
# 做法：
#   1. 第一次：git clone --bare 整個 repo（含 data/ 資料湖的完整歷史）到 <備份根目錄>\repo.git
#   2. 之後每天：git fetch 把新的 commit 拉下來
#   3. 每天把當下所有分支與標籤另存一份到 refs/snapshots/<日期>/...（這就是「快照」）
#      → 即使 GitHub 上的歷史被覆寫或刪掉，筆電這份 14 天內的任何一天都還原得回來。
#      快照共用同一份物件，所以 14 份快照不會佔 14 倍空間。
#   4. 超過 14 天的快照刪掉，再 git gc 回收空間。
#   5. 會員資料：用憑證管理員裡的 tw-ops-backup（＝BACKUP_TOKEN）叫會員 Worker 的 /v1/admin/export，
#      存成 <備份根目錄>\members\members-YYYYMMDD.json，驗 sha256＋HMAC 簽章，保留 14 天。
#      這一步失敗（沒設權杖、Worker 連不上、簽章不對）會通知，但不讓 repo 備份算失敗。
#      ⚠ 這個檔案含會員 email：備份資料夾不要分享；Google Drive 同步的資料夾要維持「私人」。
. (Join-Path $PSScriptRoot 'common.ps1')
$cfg = Get-OpsConfig
$root = $cfg.backup_root
$repo = Join-Path $root 'repo.git'
$keepDays = 14
if ($cfg.keep_days) { $keepDays = [int]$cfg.keep_days }
New-Item -ItemType Directory -Force -Path $root | Out-Null

function Invoke-Git {
    # 刻意不用 param()：用了之後 -d 會被 PowerShell 當成自己的 -Debug 參數吃掉
    $GitArgs = [string[]]$args
    # PowerShell 5.1 會把 git 寫到 stderr 的進度訊息當成錯誤；這裡只看結束碼
    $ErrorActionPreference = 'Continue'
    $out = & git @GitArgs 2>&1 | ForEach-Object { [string]$_ }
    if ($LASTEXITCODE -ne 0) { throw ('git ' + ($GitArgs -join ' ') + ' 失敗：' + ($out | Out-String)) }
    return $out
}

# ---------------------------------------------------------------- 會員資料（/v1/admin/export）
function Backup-Members($cfg, [string]$root, [int]$keepDays) {
    $r = [TwCred]::Read('tw-ops-backup')
    if ($null -eq $r -or -not $r[1]) { Write-OpsLog '備份：憑證管理員裡沒有 tw-ops-backup（BACKUP_TOKEN），會員資料略過 —— 待辦，見 README 第 7 步'; return }
    $tok = $r[1].Trim()
    $api = 'https://tw-account.kcq01010909.workers.dev'
    if ($cfg.account_api) { $api = [string]$cfg.account_api }
    $dir = Join-Path $root 'members'
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $name = 'members-' + (Get-Date).ToString('yyyyMMdd') + '.json'
    $tmp = Join-Path $dir ($name + '.part')
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Method Post -Uri ($api.TrimEnd('/') + '/v1/admin/export') -Headers @{ Authorization = ('Bearer ' + $tok) } -OutFile $tmp -TimeoutSec 120
    # 驗簽：被簽的內容＝原文到 ,"sha256":" 之前再補一個 }（不重新序列化 JSON，位元組才對得上）
    $raw = [IO.File]::ReadAllText($tmp, (New-Object Text.UTF8Encoding($false)))
    $i = $raw.LastIndexOf(',"sha256":"')
    if ($i -lt 0) { Remove-Item $tmp -Force; throw '會員匯出檔格式不對（找不到 sha256）' }
    $m = [regex]::Match($raw.Substring($i), '^,"sha256":"([0-9a-f]{64})","sig":"([0-9a-f]*)"\}\s*$')
    if (-not $m.Success) { Remove-Item $tmp -Force; throw '會員匯出檔格式不對（sha256／sig 欄位）' }
    $bytes = [Text.Encoding]::UTF8.GetBytes($raw.Substring(0, $i) + '}')
    $sha = -join ([Security.Cryptography.SHA256]::Create().ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    $h = New-Object Security.Cryptography.HMACSHA256 (,[Text.Encoding]::UTF8.GetBytes($tok))
    $sig = -join ($h.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') })
    if ($sha -ne $m.Groups[1].Value -or $sig -ne $m.Groups[2].Value) { Remove-Item $tmp -Force; throw '會員匯出檔簽章驗不過（檔案被改過，或 Worker 的 BACKUP_TOKEN 跟筆電存的不一樣）' }
    Move-Item -Force $tmp (Join-Path $dir $name)
    $cut = (Get-Date).AddDays(-$keepDays).ToString('yyyyMMdd')
    Get-ChildItem $dir -Filter 'members-*.json' | Where-Object { $_.BaseName.Substring(8) -lt $cut } | Remove-Item -Force
    $kb = [math]::Round((Get-Item (Join-Path $dir $name)).Length / 1KB, 0)
    Write-OpsLog ('備份：會員資料 ' + $name + '（' + $kb + ' KB，簽章驗過）')
}

$ErrorActionPreference = 'Stop'
$started = Get-Date
try {
    if (-not (Test-Path $repo)) {
        Write-OpsLog ('備份：第一次，clone 到 ' + $repo + '（資料湖數百 MB，第一次會比較久）')
        Invoke-Git clone --bare $cfg.repo_url $repo | Out-Null
    }
    # 只抓分支與標籤；不用 --prune，GitHub 上被刪的分支在筆電這份保留
    Invoke-Git -C $repo fetch --tags origin '+refs/heads/*:refs/heads/*' | Out-Null

    $stamp = (Get-Date).ToString('yyyyMMdd')
    $refs = Invoke-Git -C $repo for-each-ref --format='%(objectname) %(refname)' refs/heads refs/tags
    foreach ($line in $refs) {
        $parts = ([string]$line).Split(' ')
        if ($parts.Count -lt 2) { continue }
        $name = $parts[1].Substring(5)   # 去掉開頭的 refs/
        Invoke-Git -C $repo update-ref ('refs/snapshots/' + $stamp + '/' + $name) $parts[0] | Out-Null
    }

    # 刪掉超過保留天數的快照
    $cut = (Get-Date).AddDays(-$keepDays).ToString('yyyyMMdd')
    $snaps = Invoke-Git -C $repo for-each-ref --format='%(refname)' refs/snapshots
    $removed = 0
    foreach ($r in $snaps) {
        $d = ([string]$r).Split('/')[2]
        if ($d -lt $cut) { Invoke-Git -C $repo update-ref -d ([string]$r) | Out-Null; $removed++ }
    }
    if ($removed -gt 0) { Invoke-Git -C $repo gc --prune=now --quiet | Out-Null }

    # 完整性檢查（只查連通性，幾十秒）
    Invoke-Git -C $repo fsck --connectivity-only --no-progress | Out-Null

    $head = (Invoke-Git -C $repo rev-parse --short refs/heads/main | Out-String).Trim()
    $sizeMB = [math]::Round(((Get-ChildItem $repo -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 0)
    $days = @(Invoke-Git -C $repo for-each-ref --format='%(refname)' 'refs/snapshots/*/heads/main').Count
    $min = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    $msg = ('備份完成：main=' + $head + '，快照 ' + $days + ' 天，佔 ' + $sizeMB + ' MB，耗時 ' + $min + ' 分鐘')
    Write-OpsLog $msg
    try { Backup-Members $cfg $root $keepDays } catch {
        $em = $_.Exception.Message
        Write-OpsLog ('備份：會員資料失敗：' + $em)
        Send-OpsNotice '會員資料備份失敗' ('會員資料備份失敗（repo 備份照常完成）：' + $em + "`r`n" + '紀錄檔：' + $script:LogPath) | Out-Null
    }
    $state = Get-OpsState
    $state | Add-Member -NotePropertyName last_backup -NotePropertyValue (@{ at = (Get-Date).ToString('o'); ok = $true; msg = $msg }) -Force
    if ($state.backup_alerted) { Send-OpsNotice '備份已恢復' $msg | Out-Null }
    $state | Add-Member -NotePropertyName backup_alerted -NotePropertyValue $false -Force
    Save-OpsState $state
    # 第二份異地備份：有放 rclone.exe 並設好 r2 遠端才跑（README「第二份異地備份」B）
    $rc = Join-Path $script:OpsDir 'rclone.exe'
    if (Test-Path $rc) {
        $ErrorActionPreference = 'Continue'
        & $rc sync $root 'r2:tw-backup' --fast-list 2>&1 | Out-Null
        $code = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($code -ne 0) { throw ('rclone 同步到 R2 失敗，結束碼 ' + $code) }
        Write-OpsLog '備份：已同步到 Cloudflare R2'
    }
    Write-Host $msg
} catch {
    $err = $_.Exception.Message
    Write-OpsLog ('備份失敗：' + $err)
    $state = Get-OpsState
    $state | Add-Member -NotePropertyName last_backup -NotePropertyValue (@{ at = (Get-Date).ToString('o'); ok = $false; msg = $err }) -Force
    $state | Add-Member -NotePropertyName backup_alerted -NotePropertyValue $true -Force
    Save-OpsState $state
    Send-OpsNotice '每日備份失敗' ('備份失敗：' + $err + "`r`n" + '紀錄檔：' + $script:LogPath) | Out-Null
    exit 1
}
