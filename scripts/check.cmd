@echo off
setlocal

cd /d "%~dp0\.."
set "PYTHONPATH=%CD%\src"

python -m compileall -q src tests scripts
if errorlevel 1 exit /b %errorlevel%

python -m competitive_intelligence validate
if errorlevel 1 exit /b %errorlevel%

python -m unittest discover -s tests -v
if errorlevel 1 exit /b %errorlevel%

endlocal
