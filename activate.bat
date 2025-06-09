@echo off
REM Activation script for RTSP Camera Streaming Application virtual environment

echo 🎥 RTSP Camera Streaming - Activating Virtual Environment

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found!
    echo    Run: python setup_env.py
    exit /b 1
)

REM Check if we're already in a virtual environment
if defined VIRTUAL_ENV (
    echo ⚠️  Already in virtual environment: %VIRTUAL_ENV%
    echo    Deactivate first with: deactivate
) else (
    echo ✅ Activating virtual environment...
    call venv\Scripts\activate.bat
    echo 🚀 Virtual environment activated!
    echo    Python: %VIRTUAL_ENV%\Scripts\python.exe
    echo    To deactivate: deactivate
)