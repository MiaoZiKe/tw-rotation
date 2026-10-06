# 監控（工作排程器每 5 分鐘跑一次）。只讀不寫，不對外提供任何服務。
# 檢查四件事：① 正式站首頁 ② 版號 meta（tw:build）③ 會員 Worker 的 /health ④ 每日管線 last_run.json 有沒有太久沒更新
# 同一項連續失敗 2 次才通知；之後同一個問題不再重複通知（每 6 小時提醒一次還沒好）；恢復時通知一次。
param([switch]$Once)
. (Join-Path $PSScriptRoot 'common.ps1')
$cfg = Get-OpsConfig
$state = Get-OpsState
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Get-Url([string]$url) {
    $h = @{ 'User-Agent' = 'tw-ops-monitor'; 'Cache-Control' = 'no-cache' }
    return Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 30 -Headers $h
}

$results = [ordered]@{}

# ① ② 首頁與版號
try {
    $r = Get-Url ($cfg.site_url + '?_=' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
    $results['site'] = @{ ok = ($r.StatusCode -eq 200); msg = ('HTTP ' + $r.StatusCode) }
    $m = [regex]::Match($r.Content, 'name="tw:build"\s+content="([^"]*)"')
    if ($m.Success -and $m.Groups[1].Value -and -not $m.Groups[1].Value.StartsWith('dev')) {
        $results['build'] = @{ ok = $true; msg = $m.Groups[1].Value }
    } else {
        $results['build'] = @{ ok = $false; msg = '首頁沒有版號 meta（tw:build），或還是 dev：可能部署壞了' }
    }
} catch {
    # 首頁打不開時版號一定也讀不到：只報首頁這一項，避免同一件事寄兩封
    $results['site'] = @{ ok = $false; msg = $_.Exception.Message }
}

# ③ 會員 Worker
if ($cfg.account_api) {
    try {
        $r = Get-Url ($cfg.account_api.TrimEnd('/') + '/health')
        $j = $r.Content | ConvertFrom-Json
        $results['account'] = @{ ok = ($j.ok -eq $true); msg = ('ok=' + $j.ok + ' configured=' + $j.configured) }
    } catch { $results['account'] = @{ ok = $false; msg = $_.Exception.Message } }
}

# ④ 每日管線：last_run.json 的 finished_at
# 週末不跑管線：週六、週日、週一允許 74 小時；其他日子 26 小時。國定假日會誤報一次（README 有寫）。
try {
    $r = Get-Url $cfg.last_run_url
    $j = $r.Content | ConvertFrom-Json
    $fin = [DateTimeOffset]::Parse($j.finished_at)
    $ageH = ([DateTimeOffset]::UtcNow - $fin).TotalHours
    $tpe = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromHours(8))
    $limit = 26
    if (@('Saturday', 'Sunday', 'Monday') -contains $tpe.DayOfWeek.ToString()) { $limit = 74 }
    $ok = $ageH -le $limit
    $msg = ('最後成功 ' + $fin.ToOffset([TimeSpan]::FromHours(8)).ToString('MM-dd HH:mm') + '（台北），距今 ' + [math]::Round($ageH, 1) + ' 小時，上限 ' + $limit + ' 小時')
    if ($j.errors -and $j.errors.Count -gt 0) { $msg += '；最近一輪有 ' + $j.errors.Count + ' 個步驟錯誤' }
    $results['pipeline'] = @{ ok = $ok; msg = $msg }
} catch { $results['pipeline'] = @{ ok = $false; msg = ('讀不到 last_run.json：' + $_.Exception.Message) } }

$names = @{ site = '正式站首頁'; build = '網站版號'; account = '會員 Worker'; pipeline = '每日資料管線' }
$now = Get-Date
foreach ($k in $results.Keys) {
    $res = $results[$k]
    $s = $state.$k
    if ($null -eq $s) { $s = [pscustomobject]@{ fails = 0; alerted = $false; last_alert = '' }; $state | Add-Member -NotePropertyName $k -NotePropertyValue $s -Force }
    if ($res.ok) {
        if ($s.alerted) {
            Send-OpsNotice ('已恢復：' + $names[$k]) ($names[$k] + ' 恢復正常。' + "`r`n" + $res.msg) | Out-Null
        }
        $s.fails = 0; $s.alerted = $false; $s.last_alert = ''
    } else {
        $s.fails = [int]$s.fails + 1
        $remind = $false
        if ($s.alerted -and $s.last_alert) { $remind = (($now - [datetime]$s.last_alert).TotalHours -ge 6) }
        if (($s.fails -ge 2 -and -not $s.alerted) -or $remind) {
            $prefix = '異常'
            if ($remind) { $prefix = '仍未恢復' }
            Send-OpsNotice ($prefix + '：' + $names[$k]) ($names[$k] + ' 連續 ' + $s.fails + ' 次檢查失敗。' + "`r`n" + $res.msg + "`r`n" + '網站：' + $cfg.site_url) | Out-Null
            $s.alerted = $true; $s.last_alert = $now.ToString('o')
        }
    }
    Write-OpsLog ('監控 ' + $k + ' ' + ($(if ($res.ok) { 'OK' } else { '失敗' })) + ' ' + $res.msg)
}
$state | Add-Member -NotePropertyName last_check -NotePropertyValue $now.ToString('o') -Force
Save-OpsState $state
if ($Once) { $results.GetEnumerator() | ForEach-Object { Write-Host ($_.Key + '：' + ($(if ($_.Value.ok) { 'OK' } else { '失敗' })) + '  ' + $_.Value.msg) } }
