@echo off
REM ============================================================
REM  AI Dataset Labeling Marketplace - One-Click Launcher
REM  Checks ports 8000 and 5173 first. If either is busy it
REM  stops with instructions and does NOT touch what is running.
REM ============================================================
setlocal ENABLEDELAYEDEXPANSION
set ROOT=%~dp0

echo ============================================
echo   AI Dataset Labeling Marketplace - Launcher
echo ============================================
echo.

REM --- 1. Port availability checks ---
set PORT_BUSY=0

netstat -ano > "%TEMP%\mkt_ports.txt" 2>nul
findstr /r /c:":8000 .*LISTENING" "%TEMP%\mkt_ports.txt" >nul 2>&1
if not errorlevel 1 (
  echo [BLOCKED] Port 8000 is already in use.
  echo            A backend is probably already running.
  echo            Open http://127.0.0.1:8000/docs in your browser
  echo            or close the old process then run this again.
  set PORT_BUSY=1
)
findstr /r /c:":5173 .*LISTENING" "%TEMP%\mkt_ports.txt" >nul 2>&1
if not errorlevel 1 (
  echo [BLOCKED] Port 5173 is already in use.
  echo            A frontend is probably already running.
  echo            Open http://127.0.0.1:5173 in your browser
  echo            or close the old process then run this again.
  set PORT_BUSY=1
)

if "!PORT_BUSY!"=="1" (
  echo.
  echo Nothing was started. Existing processes were not touched.
  pause
  exit /b 1
)
echo Ports 8000 and 5173 are free. Starting fresh.
echo.

REM --- 2. Apply database migrations (Postgres) ---
echo [1/3] Applying database migrations...
cd /d "%ROOT%"
python -m alembic upgrade head
if errorlevel 1 (
  echo ERROR: migrations failed. Check .env and the Python install.
  pause
  exit /b 1
)
echo       DB schema OK.
echo.

REM --- 3. Start backend + frontend, each in its own window ---
echo [2/3] Starting backend on http://127.0.0.1:8000 ...
start "Marketplace Backend" cmd /k "cd /d %ROOT% && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

if not exist "%ROOT%frontend\node_modules" (
  echo       Installing frontend dependencies (first run)...
  cd /d "%ROOT%frontend"
  call npm install
  cd /d "%ROOT%"
)

echo [3/3] Starting frontend on http://127.0.0.1:5173 ...
start "Marketplace Frontend" cmd /k "cd /d %ROOT%frontend && npm run dev"

REM --- 4. Wait, then open the site ---
echo.
echo Waiting for servers, then opening the browser...
timeout /t 8 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo.
echo All started. Keep the Backend and Frontend windows open.
echo   Site     : http://127.0.0.1:5173
echo   API docs : http://127.0.0.1:8000/docs
echo.
echo Tip: If the DB is empty, sign up an owner and a labeler first.
pause
endlocal