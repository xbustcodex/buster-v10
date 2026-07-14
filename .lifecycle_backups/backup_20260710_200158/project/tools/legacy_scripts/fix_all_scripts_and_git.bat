@echo off
setlocal

cd /d "%~dp0"

mkdir scripts 2>nul

echo Updating .gitignore...
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *.pyo
echo.
echo # Virtual env
echo .venv/
echo venv/
echo.
echo # PyInstaller / builds
echo build/
echo dist/
echo.
echo # Large binaries
echo *.exe
echo *.dll
echo *.pyd
echo *.pkg
echo *.pyz
echo.
echo # Logs
echo *.log
echo.
echo # IDE / OS
echo .vscode/
echo .idea/
echo Thumbs.db
echo Desktop.ini
) > .gitignore

echo Updating scripts\build_exe.bat...
(
echo @echo off
echo setlocal
echo cd /d "%%~dp0\.."
echo if not exist .venv python -m venv .venv
echo call .venv\Scripts\activate
echo python -m pip install --upgrade pip
echo pip install pyinstaller
echo if exist requirements.txt pip install -r requirements.txt
echo if exist build rmdir /s /q build
echo if exist dist rmdir /s /q dist
echo python -m PyInstaller Buster.spec
echo if errorlevel 1 exit /b 1
echo echo Build complete: dist\Buster\Buster.exe
) > scripts\build_exe.bat

echo Updating scripts\test_push.bat...
(
echo @echo off
echo setlocal
echo cd /d "%%~dp0\.."
echo set MSG=%%~1
echo if "%%MSG%%"=="" set MSG=Auto checkpoint after passing tests
echo python -m pytest
echo if errorlevel 1 exit /b 1
echo git rm -r --cached build dist ^>nul 2^>^&1
echo git add .
echo git reset HEAD build dist ^>nul 2^>^&1
echo git diff --cached --quiet
echo if errorlevel 1 ^(
echo   git commit -m "%%MSG%%"
echo   git push
echo ^) else ^(
echo   echo Nothing to commit.
echo ^)
) > scripts\test_push.bat

echo Updating scripts\release.bat...
(
echo @echo off
echo setlocal
echo cd /d "%%~dp0\.."
echo call scripts\build_exe.bat
echo if errorlevel 1 exit /b 1
echo call scripts\test_push.bat "Release source update"
) > scripts\release.bat

echo Updating scripts\build.bat...
(
echo @echo off
echo cd /d "%%~dp0\.."
echo python -m pytest
) > scripts\build.bat

echo Updating scripts\benchmark.bat...
(
echo @echo off
echo cd /d "%%~dp0\.."
echo python -m pytest --durations=20
) > scripts\benchmark.bat

echo Removing build/dist from git index...
git rm -r --cached build dist 2>nul

echo Done.
echo Now run:
echo git add .gitignore scripts
echo git commit -m "Fix scripts and ignore build artifacts"
pause