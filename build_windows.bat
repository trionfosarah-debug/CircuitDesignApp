@echo off
setlocal
cd /d "%~dp0"

echo [build] Preparing Windows build environment...
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python build_nuitka.py
if errorlevel 1 goto :error

echo.
echo Build complete: dist\CircuitDesignApp.exe
exit /b 0

:error
echo.
echo Build failed. Review the error above.
exit /b 1
