@echo off
setlocal EnableDelayedExpansion

title Buster AI OS Release Builder

cd /d "%~dp0\.."

set VERSION=11.0.0
set RELEASE=release

echo.
echo ======================================================
echo          Buster AI OS Release Builder
echo                 Version %VERSION%
echo ======================================================
echo.

::----------------------------------------------------------
:: Clean release folder
::----------------------------------------------------------

echo [1/8] Preparing release folder...

if exist %RELEASE% rmdir /S /Q %RELEASE%
mkdir %RELEASE%

echo.

::----------------------------------------------------------
:: Run tests
::----------------------------------------------------------

echo [2/8] Running test suite...

python -m pytest

if errorlevel 1 (
    echo.
    echo **************************************
    echo Tests failed.
    echo Release cancelled.
    echo **************************************
    pause
    exit /b 1
)

echo.

::----------------------------------------------------------
:: Build executable
::----------------------------------------------------------

echo [3/8] Building executable...

call scripts\build_exe.bat

if errorlevel 1 (
    echo.
    echo **************************************
    echo Build failed.
    echo **************************************
    pause
    exit /b 1
)

echo.

::----------------------------------------------------------
:: Create Portable folder
::----------------------------------------------------------

echo [4/8] Creating portable package...

mkdir "%RELEASE%\Buster-%VERSION%-Portable"

xcopy dist\Buster "%RELEASE%\Buster-%VERSION%-Portable\" /E /I /Y >nul

if exist README.md copy README.md "%RELEASE%\Buster-%VERSION%-Portable\" >nul
if exist LICENSE copy LICENSE "%RELEASE%\Buster-%VERSION%-Portable\" >nul
if exist version.json copy version.json "%RELEASE%\Buster-%VERSION%-Portable\" >nul

echo.

::----------------------------------------------------------
:: Compress ZIP (PowerShell)
::----------------------------------------------------------

echo [5/8] Compressing Portable ZIP...

powershell -NoLogo -NoProfile ^
Command "Compress-Archive -Force '%RELEASE%\Buster-%VERSION%-Portable\*' '%RELEASE%\Buster-%VERSION%-Portable.zip'"

echo.

::----------------------------------------------------------
:: Build installer (optional)
::----------------------------------------------------------

echo [6/8] Checking Inno Setup...

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist %ISCC% (
    echo Building installer...
    %ISCC% scripts\installer\Buster.iss
) else (
    echo.
    echo Inno Setup not installed.
    echo Skipping installer build.
)

echo.

::----------------------------------------------------------
:: Checksums
::----------------------------------------------------------

echo [7/8] Generating SHA256...

(
for %%F in ("%RELEASE%\*.zip" "%RELEASE%\*.exe") do (
    if exist "%%F" (
        certutil -hashfile "%%F" SHA256
        echo.
    )
)
) > "%RELEASE%\SHA256SUMS.txt"

echo.

::----------------------------------------------------------
:: Finish
::----------------------------------------------------------

echo [8/8] Finished.

(
echo ============================================
echo Buster AI OS Build
echo Version %VERSION%
echo %DATE% %TIME%
echo ============================================
echo.
echo Release folder:
echo %CD%\%RELEASE%
) > "%RELEASE%\build_log.txt"

echo.
echo ======================================================
echo BUILD SUCCESSFUL
echo ======================================================
echo.
echo Release folder:
echo.
echo %CD%\release
echo.
echo Contents:
echo.
dir "%RELEASE%"
echo.
pause