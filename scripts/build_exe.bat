@echo off
REM Build Standalone Executable for Ableton Hub
REM This script uses PyInstaller to create a standalone .exe file

echo Building Ableton Hub executable...
echo.

REM Change to project root (parent of scripts folder)
cd /d "%~dp0.."

REM Check for virtual environment Python
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo Using virtual environment Python: .venv\Scripts\python.exe
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo Using virtual environment Python: venv\Scripts\python.exe
) else (
    echo WARNING: Virtual environment not found!
    echo Looking for .venv\Scripts\python.exe or venv\Scripts\python.exe
    echo.
    echo Using system Python instead. This may cause issues if dependencies are missing.
    echo.
    set "PYTHON_EXE=python"
    pause
)

REM Check if PyInstaller is installed
"%PYTHON_EXE%" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    "%PYTHON_EXE%" -m pip install pyinstaller
)

REM Build the executable
"%PYTHON_EXE%" -m PyInstaller ^
    --name="Ableton Hub" ^
    --windowed ^
    --icon=resources/images/ableton-logo.png ^
    --add-data "resources;resources" ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=sqlalchemy ^
    --hidden-import=watchdog ^
    --hidden-import=zeroconf ^
    --hidden-import=sklearn ^
    --hidden-import=sklearn.cluster ^
    --hidden-import=sklearn.metrics ^
    --hidden-import=sklearn.preprocessing ^
    --hidden-import=numpy ^
    --hidden-import=librosa ^
    --hidden-import=soundfile ^
    --hidden-import=lxml ^
    --collect-all=PyQt6 ^
    src/main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo Build complete! Executable is in the 'dist' folder.
echo You can now double-click 'Ableton Hub.exe' to run the application.
echo.
pause
