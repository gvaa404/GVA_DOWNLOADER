@echo off
REM =====================================================================
REM  GVA Downloader v2.0 - Windows Installer
REM  Installs Python dependencies and prepares the application folder.
REM  Does NOT install Python or FFmpeg system-wide - see README.md.
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
    echo Make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Upgrading pip...
python -m pip install --upgrade pip

echo [2/3] Installing dependencies (yt-dlp, rich)...
python -m pip install -U yt-dlp rich

echo [3/3] Creating application folders...
python "%~dp0gva_downloader.py" --history >nul 2>nul

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo.
    echo [WARNING] FFmpeg was not found on PATH.
    echo Video merging, audio conversion, and thumbnail embedding need FFmpeg.
    echo Download it from https://ffmpeg.org/download.html and add its
    echo "bin" folder to your system PATH.
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
