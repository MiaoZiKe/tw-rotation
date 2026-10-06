# 移除兩個排程。加 -Purge 連設定檔、紀錄檔、憑證一起刪（備份資料夾不會動，要刪請自己刪）。
param([switch]$Purge)
foreach ($t in @('tw-ops 監控', 'tw-ops 每日備份')) {
    if (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $t -Confirm:$false
        Write-Host ('已移除排程：' + $t)
    } else { Write-Host ('沒有這個排程（略過）：' + $t) }
}
if ($Purge) {
    cmdkey /delete:tw-ops-gmail 2>$null | Out-Null
    cmdkey /delete:tw-ops-backup 2>$null | Out-Null
    $ops = Join-Path $env:LOCALAPPDATA 'tw-ops'
    if (Test-Path $ops) { Remove-Item -Recurse -Force $ops; Write-Host ('已刪除：' + $ops) }
}
Write-Host '完成。備份資料夾沒有刪除。'
