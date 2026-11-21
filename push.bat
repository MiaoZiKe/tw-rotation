@echo off
title tw-rotation push
set "LOG=%~dp0push-log.txt"
echo Running... full log will be saved to push-log.txt
rem NOTE 2026-09-14: was  cmd /c ""...bat"" %*  which breaks the moment an
rem argument is passed -- cmd collapses the doubled quotes and reports
rem '"...\_push_core.bat"" "<msg>' is not recognized as an internal command.
rem `call` handles quoted arguments correctly and still propagates errorlevel.
rem (The commit message normally comes from COMMITMSG.txt anyway.)
call "%~dp0_push_core.bat" %* > "%LOG%" 2>&1
echo.
type "%LOG%"
echo.
echo ==========================================================
echo  Done. Full log: %LOG%
echo  If SUCCESS: wait for Actions, then open the site and Ctrl+F5.
echo  Press any key to close.
echo ==========================================================
pause >nul
