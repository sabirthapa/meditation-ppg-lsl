# Convenience launcher for the meditation PPG LSL recorder.
# Activates UTF-8 console output and runs any project script in the venv.
#
# Examples:
#   .\run.ps1 scripts\test_imports.py
#   .\run.ps1 scripts\run_laptop_recorder.py --config configs\laptop_01_test.json --duration 60
#   .\run.ps1 scripts\scan_bands.py

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Error "Virtual environment not found at $venvPy. Re-run setup."
    exit 1
}

$env:PYTHONUTF8 = "1"
# Make `import src...` work on any fresh clone without extra setup
# (the venv is recreated per machine, so we can't rely on a .pth file).
$env:PYTHONPATH = $root
Set-Location $root
& $venvPy @args
exit $LASTEXITCODE
