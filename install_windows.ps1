$ErrorActionPreference = "Stop"

$AppName = "GVA Downloader"
$AppVersion = "2.1"
$RepoZip = "https://github.com/gvaa404/GVA_DOWNLOADER/archive/refs/heads/main.zip"
$InstallDir = Join-Path $env:LOCALAPPDATA "GVA-Downloader"
$BinDir = Join-Path $InstallDir "bin"
$VenvDir = Join-Path $InstallDir "venv"
$Launcher = Join-Path $BinDir "gvad.cmd"
$TempDir = Join-Path $env:TEMP ("gva-install-" + [guid]::NewGuid().ToString())

function Step($Text) { Write-Host $Text -ForegroundColor Cyan }
function OK($Text) { Write-Host ("[OK] " + $Text) -ForegroundColor Green }
function Fail($Text) { Write-Host ("[ERROR] " + $Text) -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "============================================"
Write-Host "   GVA Downloader v$AppVersion"
Write-Host "       One-Click Windows Installer"
Write-Host "============================================"
Write-Host ""

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
try {
    Step "[1/5] Checking required Windows tools..."

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "Windows App Installer / winget was not found. Install App Installer from Microsoft Store, then run this installer again."
    }

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Step "Installing Python 3.12..."
        winget install --id Python.Python.3.12 -e --scope user --accept-source-agreements --accept-package-agreements --silent
    }

    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Step "Installing FFmpeg..."
        winget install --id Gyan.FFmpeg -e --scope user --accept-source-agreements --accept-package-agreements --silent
    }

    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $python) {
        $py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
        if (Test-Path $py) { $python = $py }
    }
    if (-not $python) { Fail "Python installation completed but python.exe was not found." }

    OK "Python and FFmpeg are ready"

    Step "[2/5] Downloading GVA Downloader..."
    Invoke-WebRequest -Uri $RepoZip -OutFile (Join-Path $TempDir "repo.zip")
    Expand-Archive -Path (Join-Path $TempDir "repo.zip") -DestinationPath $TempDir -Force

    $repoDir = Get-ChildItem -Path $TempDir -Directory | Where-Object { $_.Name -like "GVA_DOWNLOADER-*" } | Select-Object -First 1
    if (-not $repoDir) { Fail "Downloaded GVA repository could not be located." }

    $source = Get-ChildItem -Path (Join-Path $repoDir.FullName "src") -Filter "gva_downloader*.py" -File |
        Sort-Object Name | Select-Object -Last 1
    if (-not $source) { Fail "No GVA Downloader Python source was found." }

    $requirements = Join-Path $repoDir.FullName "requirements.txt"
    if (-not (Test-Path $requirements)) { Fail "requirements.txt was not found." }

    Step "[3/5] Installing GVA..."
    New-Item -ItemType Directory -Force -Path $InstallDir, $BinDir | Out-Null
    Copy-Item $source.FullName (Join-Path $InstallDir "gva_downloader.py") -Force
    Copy-Item $requirements (Join-Path $InstallDir "requirements.txt") -Force

    $imgDir = Join-Path $repoDir.FullName "img"
    if (Test-Path $imgDir) {
        Remove-Item (Join-Path $InstallDir "img") -Recurse -Force -ErrorAction SilentlyContinue
        Copy-Item $imgDir (Join-Path $InstallDir "img") -Recurse -Force
    }

    if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
        & $python -m venv $VenvDir
    }

    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    & $venvPython -m pip install --upgrade pip | Out-Null
    & $venvPython -m pip install -r (Join-Path $InstallDir "requirements.txt") | Out-Null
    OK "GVA and Python dependencies installed"

    Step "[4/5] Creating 'gvad' command..."
    @"
@echo off
setlocal
set "INSTALL_DIR=$InstallDir"
set "VENV_DIR=$VenvDir"
set "APP_VERSION=$AppVersion"

if "%~1"=="--version" (
  echo GVA Downloader v%APP_VERSION%
  exit /b 0
)
if "%~1"=="-v" (
  echo GVA Downloader v%APP_VERSION%
  exit /b 0
)
if "%~1"=="--help" (
  echo GVA Downloader v%APP_VERSION%
  echo.
  echo   gvad                 Start GVA Downloader
  echo   gvad --version       Show version
  echo   gvad --help          Show help
  echo   gvad --uninstall     Uninstall GVA Downloader
  exit /b 0
)
if "%~1"=="-h" (
  echo GVA Downloader v%APP_VERSION%
  echo.
  echo   gvad                 Start GVA Downloader
  echo   gvad --version       Show version
  echo   gvad --help          Show help
  echo   gvad --uninstall     Uninstall GVA Downloader
  exit /b 0
)
if "%~1"=="--uninstall" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$i=[Environment]::ExpandEnvironmentVariables('%INSTALL_DIR%'); $p=Join-Path $env:USERPROFILE 'GVA-Downloads'; $d=Join-Path $i 'downloads'; if(Test-Path $d){if(Test-Path $p){Write-Host 'GVA-Downloads already exists. Uninstall cancelled.' -ForegroundColor Red; exit 1}; Move-Item $d $p}; Remove-Item $i -Recurse -Force; Write-Host 'GVA Downloader successfully uninstalled.' -ForegroundColor Green"
  exit /b %errorlevel%
)

"%VENV_DIR%\Scripts\python.exe" "%INSTALL_DIR%\gva_downloader.py" %*
endlocal
"@ | Set-Content -Path $Launcher -Encoding ASCII

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (($userPath -split ';') -contains $BinDir)) {
        [Environment]::SetEnvironmentVariable("Path", (($userPath.TrimEnd(';') + ";" + $BinDir).Trim(';')), "User")
    }
    $env:Path = "$BinDir;$env:Path"
    OK "Command installed: gvad"

    Step "[5/5] Verifying installation..."
    $version = & $Launcher --version
    if ($version -ne "GVA Downloader v$AppVersion") { Fail "GVA version verification failed." }
    OK "Installation verified"

    Write-Host ""
    Write-Host "============================================"
    Write-Host "   GVA Downloader v$AppVersion Ready"
    Write-Host "============================================"
    Write-Host ""
    Write-Host "Start:       gvad"
    Write-Host "Version:     gvad --version"
    Write-Host "Help:        gvad --help"
    Write-Host "Uninstall:   gvad --uninstall"
    Write-Host ""
    Write-Host "Open a new PowerShell/CMD window before using 'gvad' there." -ForegroundColor Yellow
}
finally {
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
