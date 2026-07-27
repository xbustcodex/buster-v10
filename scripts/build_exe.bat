@echo off
setlocal EnableDelayedExpansion

title Buster AI OS Build

cd /d "%~dp0\.."

echo.
echo ==========================================
echo        Buster AI OS v11 Build
echo ==========================================
echo.

REM -------------------------------------------------------
REM Clean previous builds
REM -------------------------------------------------------

echo [1/6] Cleaning previous build...

if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist

echo Done.
echo.

REM -------------------------------------------------------
REM Create venv if missing
REM -------------------------------------------------------

echo [2/6] Checking virtual environment...

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

python -m pip install --upgrade pip

echo.

REM -------------------------------------------------------
REM Install dependencies
REM -------------------------------------------------------

echo [3/6] Installing requirements...

pip install -r requirements.txt
pip install pyinstaller

echo.

REM -------------------------------------------------------
REM Build executable
REM -------------------------------------------------------

echo [4/6] Building executable...

pyinstaller --noconfirm Buster.spec

if errorlevel 1 (
    echo.
    echo ==========================================
    echo BUILD FAILED
    echo ==========================================
    pause
    exit /b 1
)

echo.

REM -------------------------------------------------------
REM Verify build
REM -------------------------------------------------------

echo [5/6] Verifying executable...

if not exist dist\Buster\Buster.exe (
    echo.
    echo ERROR:
    echo Buster.exe was not created.
    pause
    exit /b 1
)

echo Build verified.
echo.

REM -------------------------------------------------------
REM Finished
REM -------------------------------------------------------

echo [6/6] Complete.

echo.
echo ==========================================
echo Build Successful
echo ==========================================
echo.

echo Executable:
echo.
echo dist\Buster\Buster.exe
echo.

pause