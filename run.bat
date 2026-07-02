@echo off
echo ========================================================
echo Starting Vector AI - Fintech and RegTech Backend Framework
echo ========================================================

REM Check if python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Check if venv directory exists, if not create it
if not exist venv (
    echo Creating virtual environment venv...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install/upgrade requirements
echo Installing/Updating dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

REM Start FastAPI application
echo Starting Uvicorn development server...
echo Access Swagger UI at http://127.0.0.1:8000/docs
echo Access Frontend at http://127.0.0.1:8000/
echo.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause
