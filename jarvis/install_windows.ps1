# Jarvis installer for Windows. Run from this folder:
#   Right-click > "Run with PowerShell"   (or: powershell -ExecutionPolicy Bypass -File install_windows.ps1)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# Stop any running copy first. Windows will not let us touch files that a live
# process has open, and Jarvis usually IS running when you reinstall it.
Write-Host "Stopping any running copy of Jarvis..." -ForegroundColor Cyan
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*main.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 3

# -- Find a Python that Jarvis's dependencies actually support --------------
# 3.13+ has no prebuilt wheels yet for faster-whisper / webrtcvad, so we pin 3.12/3.11.
$WANTED = @("3.12", "3.11")
$pyExe = $null
$pyArgs = @()

function Test-Python($exe, $argList) {
    try {
        $v = & $exe @argList -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $WANTED -contains $v.Trim()) { return $v.Trim() }
    } catch { }
    return $null
}

$hasPy = [bool](Get-Command py -ErrorAction SilentlyContinue)

# 1. Already-installed 3.12 or 3.11 via the Python Install Manager / launcher
if ($hasPy) {
    foreach ($v in $WANTED) {
        if (Test-Python "py" @("-V:$v")) { $pyExe = "py"; $pyArgs = @("-V:$v"); break }
    }
}

# 2. A bare `python` on PATH that happens to be the right version
if (-not $pyExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    if (Test-Python "python" @()) { $pyExe = "python"; $pyArgs = @() }
}

# 3. Nothing suitable - let the install manager fetch 3.12 for us
if (-not $pyExe -and $hasPy) {
    Write-Host "Installing Python 3.12 (needed by the speech libraries)..." -ForegroundColor Cyan
    & py install 3.12
    if (Test-Python "py" @("-V:3.12")) { $pyExe = "py"; $pyArgs = @("-V:3.12") }
}

if (-not $pyExe) {
    Write-Host "No usable Python found. Install Python 3.12 from python.org (tick 'Add python.exe to PATH') and run this again." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python: $pyExe $pyArgs" -ForegroundColor Green

# -- Ollama (the local AI engine) -------------------------------------------
$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue) -and -not (Test-Path $ollamaExe)) {
    Write-Host "Installing Ollama..." -ForegroundColor Cyan
    winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
}

# -- Virtual environment + dependencies -------------------------------------
# Reuse a working environment rather than rebuilding it - faster, and it avoids
# the "file is in use" failure that deleting a live .venv causes.
if (Test-Path ".\.venv\Scripts\python.exe") {
    Write-Host "Reusing the existing environment..." -ForegroundColor Cyan
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    if (Test-Path ".venv") {
        try { Remove-Item ".venv" -Recurse -Force -ErrorAction Stop }
        catch {
            Write-Host "Could not clear the old environment - something is still using it." -ForegroundColor Red
            Write-Host "Close any Jarvis windows, then run this again." -ForegroundColor Red
            exit 1
        }
    }
    & $pyExe @pyArgs -m venv .venv
}
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment was not created. Stopping." -ForegroundColor Red
    exit 1
}
$venvPy = ".\.venv\Scripts\python.exe"

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "A dependency failed to install. Send the red text above to Claude." -ForegroundColor Red
    exit 1
}

Write-Host "Downloading models (one time, several GB)..." -ForegroundColor Cyan
& $venvPy setup_models.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Model download failed. Check your internet connection and run this script again." -ForegroundColor Red
    exit 1
}

# -- Shortcuts --------------------------------------------------------------
Write-Host "Creating the Jarvis app shortcuts..." -ForegroundColor Cyan
& $venvPy make_icon.py
$icon = "$here\jarvis.ico"

$ws = New-Object -ComObject WScript.Shell

function New-JarvisShortcut($path, $description) {
    $s = $ws.CreateShortcut($path)
    $s.TargetPath = "$here\.venv\Scripts\pythonw.exe"
    $s.Arguments = "`"$here\main.py`""
    $s.WorkingDirectory = $here
    $s.Description = $description
    if (Test-Path $icon) { $s.IconLocation = $icon }
    $s.Save()
}

# Starts with Windows
New-JarvisShortcut ([Environment]::GetFolderPath('Startup') + "\Jarvis.lnk") "Jarvis voice assistant"

# On the Desktop
New-JarvisShortcut ([Environment]::GetFolderPath('Desktop') + "\Jarvis.lnk") "Open Jarvis"

# In the Start menu, so typing "Jarvis" in Start finds it like any installed app
$programs = [Environment]::GetFolderPath('Programs')
New-Item -ItemType Directory -Force -Path $programs | Out-Null
New-JarvisShortcut "$programs\Jarvis.lnk" "Jarvis voice assistant"

Write-Host "Jarvis is now on your Desktop and in your Start menu." -ForegroundColor Cyan

# Stop any copy left running by an earlier install, so this one can take over
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*main.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

Start-Process "$here\.venv\Scripts\pythonw.exe" -ArgumentList "`"$here\main.py`"" -WorkingDirectory $here
Write-Host ""
Write-Host "Done. Jarvis is running and will start every time you log in." -ForegroundColor Green
Write-Host "The floating mic panel is now on screen. Click the mic, or press Win+Alt+J." -ForegroundColor Green
Write-Host "The gear on the panel opens Settings, where you can change how it behaves." -ForegroundColor Green
