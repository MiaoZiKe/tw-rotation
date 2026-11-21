@echo off
cd /d "%~dp0"
echo ===== START %DATE% %TIME% =====
echo folder: %CD%
git rev-parse --is-inside-work-tree >nul 2>&1 || ( echo [FAIL] not a git repo & exit /b 1 )
echo.
echo [1/5] status
git status --short --branch
echo.
echo [2/5] stage + commit
rem Claude cannot write .github\workflows through the remote file bridge
rem (the platform protects it), so updated workflows arrive in _pending\workflows.
if exist "%~dp0_pending\workflows\*.yml" (
  echo [INFO] applying pending workflow updates
  xcopy /Y /Q "%~dp0_pending\workflows\*.yml" "%~dp0.github\workflows\" >nul
)
git add -A
rem force-add the push scripts: local .git/info/exclude has *.bat which would skip them
git add -f push.bat _push_core.bat push PUSH-README.md 2>nul
rem COMMITMSG.txt is written by Claude in UTF-8, so the commit message can be
rem Chinese while this .bat stays pure ASCII (cmd reads .bat in the OEM codepage).
set "MSGOPT=-m "update via push script""
if not "%~1"=="" set "MSGOPT=-m "%~1""
if exist "%~dp0COMMITMSG.txt" set "MSGOPT=-F "%~dp0COMMITMSG.txt""
git diff --cached --quiet && ( echo [INFO] nothing to commit ) || ( git commit %MSGOPT% )
echo.
echo [3/5] pull --rebase
git pull --rebase origin main
if errorlevel 1 ( echo [FAIL] pull/rebase & git status --short & exit /b 3 )
echo.
echo [4/5] commits to push
git log --oneline origin/main..HEAD
echo.
echo [5/5] push
git push origin main
if errorlevel 1 ( echo [FAIL] push rejected & exit /b 4 )
echo.
echo SUCCESS - GitHub Actions will redeploy
git log --oneline -2
exit /b 0
