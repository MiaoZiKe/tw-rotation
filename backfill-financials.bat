@echo off
setlocal
title TW Rotation Dashboard - Backfill financials
echo.
echo   Triggering financial statements backfill (revenue + income + balance sheet)...
echo   This runs in the cloud; you can close this window after it says OK.
echo.
gh workflow run backfill.yml -f limit=400 -f start_date=2016-01-01 -f datasets=revenue+financial+balance
if errorlevel 1 (
  echo   [!] Could not trigger. Open the Actions page and run it by hand:
  echo       workflow = backfill, datasets = revenue+financial+balance
) else (
  echo   [OK] Started. Check: https://github.com/MiaoZiKe/tw-rotation/actions
)
echo.
pause
endlocal
