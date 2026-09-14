@echo off
title tw-rotation push
set "LOG=%~dp0push-log.txt"
echo Running... full log will be saved to push-log.txt
cmd /c ""%~dp0_push_core.bat"" %* > "%LOG%" 2>&1
echo.
type "%LOG%"
echo.
echo ==========================================================
echo  Done. Full log: %LOG%
echo  If SUCCESS: wait for Actions, then open the site and Ctrl+F5.
echo  Press any key to close.
echo ==========================================================
pause >nul
