#requires -Version 5.1
<#
    GTA V Legacy builder - PowerShell wrapper.

    Installs nothing. See README.md for the requirements.
    All arguments are forwarded to buildiso.py, e.g.:

        .\build.ps1 --help
        .\build.ps1 --output "GTA V Legacy.iso" -v
#>
$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    Write-Error "Python 3 was not found on PATH. Install it from https://www.python.org/downloads/"
    exit 1
}

& $python.Source (Join-Path $PSScriptRoot "buildiso.py") @args
exit $LASTEXITCODE
