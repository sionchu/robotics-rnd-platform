[CmdletBinding()]
param(
    [ValidateSet('Preview', 'Install')]
    [string]$Mode = 'Preview',
    [switch]$WithVision,
    [switch]$InstallBuildTools
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Test-Python312 {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        'C:\Program Files\Python312\python.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    $python312 = Get-Command python3.12 -ErrorAction SilentlyContinue
    if ($python312) {
        return $python312.Source
    }
    return $null
}

function Test-BuildTools {
    $vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswhere)) {
        return $false
    }
    $path = & $vswhere -latest -products '*' -property installationPath
    return [bool]$path
}

function Install-WingetPackage {
    param(
        [string]$Id,
        [string]$Label
    )
    Write-Host "Installing baseline tool: $Label ($Id)"
    & winget install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget failed for $Id with exit code $LASTEXITCODE"
    }
}

$baseline = @(
    @{ Label = 'Git'; Command = 'git'; Id = 'Git.Git' },
    @{ Label = 'GitHub CLI'; Command = 'gh'; Id = 'GitHub.cli' },
    @{ Label = 'Windows Terminal'; Command = 'wt'; Id = 'Microsoft.WindowsTerminal' },
    @{ Label = 'VS Code'; Command = 'code'; Id = 'Microsoft.VisualStudioCode' },
    @{ Label = 'CMake'; Command = 'cmake'; Id = 'Kitware.CMake' },
    @{ Label = 'Ninja'; Command = 'ninja'; Id = 'Ninja-build.Ninja' }
)

Write-Host "Mode: $Mode"
Write-Host "Repository: $ProjectRoot"
Write-Host 'Baseline tools use winget only when absent.'
Write-Host 'CUDA Toolkit, Docker, Blender, OpenUSD packages, Isaac Sim, ROS, and vendor SDKs are optional and are not installed.'
Write-Host 'WSL is reported but no Windows feature or security policy is changed.'

$missing = [System.Collections.Generic.List[object]]::new()
foreach ($tool in $baseline) {
    if (Get-Command $tool.Command -ErrorAction SilentlyContinue) {
        Write-Host "PASS: $($tool.Label)"
    }
    else {
        Write-Host "MISSING: $($tool.Label)"
        $missing.Add($tool)
    }
}

$python312 = Test-Python312
if ($python312) {
    Write-Host "PASS: Python 3.12 at $python312"
}
else {
    Write-Host 'MISSING: Python 3.12'
    $missing.Add(@{ Label = 'Python 3.12'; Command = 'python3.12'; Id = 'Python.Python.3.12' })
}

if (Test-BuildTools) {
    Write-Host 'PASS: Visual Studio Build Tools/IDE'
}
elseif ($InstallBuildTools) {
    Write-Host 'MISSING: Visual Studio Build Tools'
    $missing.Add(@{ Label = 'Visual Studio 2022 Build Tools'; Command = 'vswhere'; Id = 'Microsoft.VisualStudio.2022.BuildTools' })
}
else {
    Write-Host 'WARN: Visual Studio Build Tools absent; use -InstallBuildTools to include the large baseline package.'
}

if (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host 'PASS: WSL command present'
}
else {
    Write-Host 'WARN: WSL absent; enable it deliberately using current Microsoft guidance.'
}

if ($Mode -eq 'Preview') {
    Write-Host "Preview complete. Missing auto-install candidates: $($missing.Count)"
    exit 0
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is required for baseline installation.'
}

foreach ($tool in $missing) {
    Install-WingetPackage -Id $tool.Id -Label $tool.Label
}

$python312 = Test-Python312
if (-not $python312) {
    throw 'Python 3.12 was not found after installation. Open a new shell and rerun the bootstrap.'
}

$venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python312 -m venv (Join-Path $ProjectRoot '.venv')
}
& $venvPython -m pip install --upgrade pip
$editable = if ($WithVision) { "$ProjectRoot[dev,vision]" } else { "$ProjectRoot[dev]" }
& $venvPython -m pip install -e $editable
& (Join-Path $ProjectRoot '.venv\Scripts\pre-commit.exe') install
Write-Host "Bootstrap complete. Activate with: $ProjectRoot\.venv\Scripts\Activate.ps1"
