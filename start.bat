@echo off
rem Double-click to start OCR Search Engine and open it in the browser.
rem Closing this window stops the server.
cd /d "%~dp0"
title OCR Search Engine
set URL=https://127.0.0.1:8000/

rem Already running? Just open the page.
curl -sk %URL%api/health >nul 2>&1 && (start "" %URL% & exit /b 0)

if not exist .venv\Scripts\python.exe (
    echo First run: creating the Python environment and installing packages...
    py -3 -m venv .venv || goto :failed
    .venv\Scripts\python -m pip install -r requirements.txt || goto :failed
)

rem Open the browser once the server has had a few seconds to start.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 4; Start-Process '%URL%'"
.venv\Scripts\python app\main.py
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo OCR Search Engine could not start. See the messages above.
pause
exit /b 1
