@echo off
setlocal
cd /d "%~dp0\.."
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install pyinstaller
if exist requirements.txt pip install -r requirements.txt
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller Buster.spec
if errorlevel 1 exit /b 1
echo Build complete: dist\Buster\Buster.exe
