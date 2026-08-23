@echo off
setlocal
echo ==========================================
echo EBA Trader - MT5 Demo Bridge Installer
echo ==========================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher ^(py^) was not found.
  echo Install Python 3.12+ from python.org, then run this file again.
  pause
  exit /b 1
)

py -m pip install --upgrade pip
if errorlevel 1 goto :fail
py -m pip install MetaTrader5
if errorlevel 1 goto :fail

echo.
echo SUCCESS: MetaTrader5 Python package is installed.
echo Keep MetaTrader 5 terminal open and logged into a DEMO account.
echo Then use the pairing command shown inside EBA Trader Settings.
pause
exit /b 0

:fail
echo.
echo Installation failed. Copy the error above and send it to ChatGPT.
pause
exit /b 1
