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
git add -A
rem force-add the push scripts: local .git/info/exclude has *.bat which would skip them
git add -f push.bat _push_core.bat push PUSH-README.md 2>nul
git diff --cached --quiet && ( echo [INFO] nothing to commit ) || (
  if "%~1"=="" ( git commit -m "update via push script" ) else ( git commit -m "%~1" )
)
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
