@echo off
setlocal
REM =====================================================================
REM  GVA Downloader v2.0 - Windows Installer
REM  Installs Python dependencies and prepares the application folder.
REM =====================================================================

echo.
echo ============================================
echo   GVA Downloader v2.0 - Windows Setup
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure "Add python.exe to PATH" is enabled.
    pause
    exit /b 1
)

echo [1/4] Checking Python...
python --version

echo [2/4] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo [3/4] Installing GVA Downloader dependencies...
python -m pip install -U -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

echo [4/4] Preparing application folders...
python "%~dp0gva_downloader.py" --history >nul 2>nul

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo [WARNING] FFmpeg was not found on PATH.
    echo FFmpeg is needed for video merging, audio conversion,
    echo thumbnail embedding, and related post-processing.
    echo Download FFmpeg from https://ffmpeg.org/download.html
    echo and add its "bin" folder to the system PATH.
) else (
    echo FFmpeg detected.
)

echo.
echo ============================================
echo   Setup complete!
echo   Run GVA Downloader with:
echo       python gva_downloader.py
echo ============================================
pause
endlocal
