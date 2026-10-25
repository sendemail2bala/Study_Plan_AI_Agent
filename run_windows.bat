@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo Study Plan AI Agent - Windows setup
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found. Install Python 3.10+ and try again.
  pause
  exit /b 1
)
if not exist ".venv" (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection and Python version.
  pause
  exit /b 1
)
echo.
echo Starting Streamlit...
python -m streamlit run app.py
pause
