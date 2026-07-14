@echo off
if "%1"=="" (
 echo Usage: new_feature_branch.bat feature-name
 exit /b 1
)

git checkout main
git pull
git checkout -b feature/%1
