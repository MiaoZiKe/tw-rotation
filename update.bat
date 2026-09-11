@echo off
setlocal
title TW Rotation Dashboard - Update
powershell -NoProfile -ExecutionPolicy Bypass -NoLogo -File "%~dp0setup.ps1" -NoBackfill %*
endlocal
