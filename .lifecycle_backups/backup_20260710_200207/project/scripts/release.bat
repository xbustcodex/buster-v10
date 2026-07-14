@echo off
setlocal
cd /d "%~dp0\.."
call scripts\build_exe.bat
if errorlevel 1 exit /b 1
call scripts\test_push.bat "Release source update"
