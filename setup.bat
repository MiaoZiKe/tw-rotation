@echo off
setlocal
title TW Rotation Dashboard - Setup
echo.
echo   Starting setup... (this window will stay open)
echo.

set "PS=powershell"
where pwsh >nul 2>nul && set "PS=pwsh"

"%PS%" -NoProfile -ExecutionPolicy Bypass -NoLogo -File "%~dp0setup.ps1"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo   [!] Setup exited with code %RC%
  echo       A log was written to:  %~dp0setup-log.txt
  echo       Send that file to Claude if you are stuck.
)
echo.
pause
endlocal
