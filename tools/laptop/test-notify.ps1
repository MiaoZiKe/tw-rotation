# 手動測試一次通知：會照設定檔把桌面通知、Gmail、ntfy 各送一次「測試」訊息，並印出哪幾個成功。
. (Join-Path $PSScriptRoot 'common.ps1')
$done = Send-OpsNotice '測試通知' ('這是一則測試。收到代表通知設定正確。時間：' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
if ($done.Count -eq 0) { Write-Host '沒有任何一個通知管道成功，請看紀錄檔：' $script:LogPath -ForegroundColor Red; exit 1 }
Write-Host ('已送出：' + ($done -join '、')) -ForegroundColor Green
