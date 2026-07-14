@echo off
setlocal
cd /d "%~dp0\.."
set MSG=%~1
if "%MSG%"=="" set MSG=Auto checkpoint after passing tests
python -m pytest
if errorlevel 1 exit /b 1
git rm -r --cached build dist >nul 2>&1
git add .
git reset HEAD build dist >nul 2>&1
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "%MSG%"
  git push
) else (
  echo Nothing to commit.
)
