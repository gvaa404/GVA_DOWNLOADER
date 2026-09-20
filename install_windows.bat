@echo off
setlocal
title GVA Downloader Installer

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/gvaa404/GVA_DOWNLOADER/main/install_windows.ps1' -OutFile ([System.IO.Path]::Combine($env:TEMP,'gva-install.ps1')); & powershell.exe -NoProfile -ExecutionPolicy Bypass -File ([System.IO.Path]::Combine($env:TEMP,'gva-install.ps1')) } catch { Write-Host $_ -ForegroundColor Red; exit 1 }"

if errorlevel 1 (
    echo.
    echo GVA Downloader installation failed.
    pause
    exit /b 1
)

echo.
echo GVA Downloader installation finished.
pause
endlocal
