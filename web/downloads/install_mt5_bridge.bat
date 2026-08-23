@echo off
setlocal
cd /d "%~dp0"
title EBA Trader - MT5 Demo Bridge Installer

echo ===============================================
echo       EBA Trader - MT5 Demo Bridge Installer
echo ===============================================
echo.
echo This installs ONLY the local read-only Demo bridge.
echo It does NOT enable live trading or send your MT5 password to EBA.
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher ^(py^) was not found.
  echo Install Python 3.12 or newer from https://www.python.org/downloads/windows/
  echo During install, enable "Add Python to PATH".
  pause
  exit /b 1
)

echo [1/3] Updating pip...
py -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [2/3] Installing official MetaTrader5 Python package...
py -m pip install MetaTrader5
if errorlevel 1 goto :fail

echo [3/3] Downloading the EBA read-only MT5 bridge...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/enkhbat194/EBA-Trader/m18-fee-aware-execution-economics/bridge/mt5_demo_bridge.py' -OutFile '%~dp0mt5_demo_bridge.py'"
if errorlevel 1 goto :fail

echo.
echo ===============================================
echo SUCCESS
echo ===============================================
echo 1. Open MetaTrader 5 on this PC.
echo 2. Login to a DEMO account in MT5.
echo 3. Keep MT5 running.
echo 4. In EBA Trader: Settings ^> MetaTrader 5 ^> CREATE MT5 PAIR CODE.
echo 5. Copy the Windows command from EBA Trader.
echo 6. Open Command Prompt in this folder and paste that command.
echo.
echo Bridge file installed here:
echo %~dp0mt5_demo_bridge.py
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation failed.
echo Take a screenshot of this window and send it to ChatGPT.
pause
exit /b 1
