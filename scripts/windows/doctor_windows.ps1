[CmdletBinding()]
param(
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$script:Findings = [System.Collections.Generic.List[object]]::new()
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ProjectPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

function Add-Finding {
    param(
        [ValidateSet('PASS', 'WARN', 'MISSING', 'UNSUPPORTED', 'UNKNOWN')]
        [string]$Status,
        [string]$Component,
        [string]$Detail
    )
    $script:Findings.Add([pscustomobject]@{
        Status = $Status
        Component = $Component
        Detail = $Detail
    })
}

function Get-CommandVersion {
    param(
        [string]$Name,
        [string[]]$Arguments
    )
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command -and $Name -eq 'ninja') {
        $packageRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
        $ninjaFallback = Get-ChildItem -LiteralPath $packageRoot -Recurse -Filter 'ninja.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($ninjaFallback) {
            $command = [pscustomobject]@{ Source = $ninjaFallback.FullName }
        }
    }
    if (-not $command) {
        Add-Finding -Status 'MISSING' -Component $Name -Detail 'command not found'
        return
    }
    try {
        $detail = (& $command.Source @Arguments 2>&1 | Select-Object -First 1).ToString().Trim()
        Add-Finding -Status 'PASS' -Component $Name -Detail $detail
    }
    catch {
        Add-Finding -Status 'WARN' -Component $Name -Detail $_.Exception.Message
    }
}

$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$computer = Get-CimInstance Win32_ComputerSystem
Add-Finding -Status 'PASS' -Component 'Windows' -Detail "$($os.Caption), version $($os.Version), build $($os.BuildNumber)"
Add-Finding -Status 'PASS' -Component 'CPU' -Detail "$($cpu.Name), $($cpu.NumberOfCores) cores / $($cpu.NumberOfLogicalProcessors) logical"
$ramGiB = [math]::Round($computer.TotalPhysicalMemory / 1GB, 2)
Add-Finding -Status 'PASS' -Component 'RAM' -Detail "$ramGiB GiB"

$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    $gpuLine = (& $nvidia.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>&1 | Select-Object -First 1).ToString().Trim()
    if ($gpuLine -and $gpuLine -match '^[^,]+,\s*[0-9]+,\s*[^,]+$') {
        $gpuParts = $gpuLine -split ',\s*'
        Add-Finding -Status 'PASS' -Component 'GPU' -Detail $gpuParts[0]
        if ($gpuParts.Count -ge 3) {
            Add-Finding -Status 'WARN' -Component 'VRAM' -Detail "$($gpuParts[1]) MiB; below Isaac Sim 6.0 official 16 GB minimum"
            Add-Finding -Status 'PASS' -Component 'NVIDIA driver' -Detail $gpuParts[2]
        }
        $smiHeader = (& $nvidia.Source 2>&1 | Select-Object -First 3) -join ' '
        if ($smiHeader -match 'CUDA Version:\s*([0-9.]+)') {
            Add-Finding -Status 'PASS' -Component 'Driver CUDA ceiling' -Detail $Matches[1]
        }
    }
    else {
        Add-Finding -Status 'WARN' -Component 'GPU' -Detail $gpuLine
    }
}
else {
    Add-Finding -Status 'MISSING' -Component 'NVIDIA' -Detail 'nvidia-smi not found'
}

Get-CommandVersion -Name 'git' -Arguments @('--version')
Get-CommandVersion -Name 'gh' -Arguments @('--version')
Get-CommandVersion -Name 'code' -Arguments @('--version')
Get-CommandVersion -Name 'cmake' -Arguments @('--version')
Get-CommandVersion -Name 'ninja' -Arguments @('--version')
Get-CommandVersion -Name 'python' -Arguments @('--version')
if (Test-Path -LiteralPath $ProjectPython) {
    $projectPythonVersion = (& $ProjectPython --version 2>&1 | Select-Object -First 1).ToString().Trim()
    Add-Finding -Status 'PASS' -Component 'Project Python' -Detail $projectPythonVersion
}
else {
    Add-Finding -Status 'MISSING' -Component 'Project Python' -Detail 'repository .venv not found'
}
Get-CommandVersion -Name 'pwsh' -Arguments @('--version')
Get-CommandVersion -Name 'docker' -Arguments @('--version')
Get-CommandVersion -Name 'blender' -Arguments @('--version')
Get-CommandVersion -Name 'usdview' -Arguments @('--help')
Get-CommandVersion -Name 'usdcat' -Arguments @('--help')
Get-CommandVersion -Name 'nvcc' -Arguments @('--version')

$vswhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
if (Test-Path -LiteralPath $vswhere) {
    $vsPath = (& $vswhere -latest -products '*' -property installationPath 2>&1 | Select-Object -First 1).ToString().Trim()
    $vsVersion = (& $vswhere -latest -products '*' -property catalog_productDisplayVersion 2>&1 | Select-Object -First 1).ToString().Trim()
    Add-Finding -Status 'PASS' -Component 'Visual Studio' -Detail "$vsVersion at $vsPath"
}
else {
    Add-Finding -Status 'MISSING' -Component 'Visual Studio' -Detail 'Build Tools/IDE not found'
}

$wsl = Get-Command wsl -ErrorAction SilentlyContinue
if ($wsl) {
    $distroOutput = & $wsl.Source -l -q 2>$null
    $distroNames = @($distroOutput | ForEach-Object { ($_.ToString() -replace "`0", '').Trim() } | Where-Object { $_ })
    if ($distroNames.Count -gt 0) {
        Add-Finding -Status 'PASS' -Component 'WSL2' -Detail ("distributions: " + ($distroNames -join ', '))
    }
    else {
        Add-Finding -Status 'WARN' -Component 'WSL2' -Detail 'command present; no distribution listed'
    }
}
else {
    Add-Finding -Status 'MISSING' -Component 'WSL2' -Detail 'wsl command not found'
}

$isaacRoot = 'C:\isaacsim'
if (Test-Path -LiteralPath (Join-Path $isaacRoot 'isaac-sim.bat')) {
    $isaacVersionPath = Join-Path $isaacRoot 'VERSION'
    $isaacVersion = if (Test-Path -LiteralPath $isaacVersionPath) {
        (Get-Content -LiteralPath $isaacVersionPath -Raw).Trim()
    }
    else {
        'version file absent'
    }
    Add-Finding -Status 'WARN' -Component 'Isaac Sim' -Detail "$isaacVersion installed; RTX 4070 Ti 12 GB is below the 6.0 official minimum"
}
else {
    Add-Finding -Status 'MISSING' -Component 'Isaac Sim' -Detail 'local distribution not found'
}

if (Test-Path -LiteralPath $ProjectPython) {
    try {
        $torchDetail = (& $ProjectPython -c "import torch; print(f'torch={torch.__version__} cuda={torch.cuda.is_available()} runtime={torch.version.cuda}')" 2>&1 | Select-Object -First 1).ToString().Trim()
        if ($torchDetail -match 'cuda=True') {
            Add-Finding -Status 'PASS' -Component 'PyTorch CUDA' -Detail $torchDetail
        }
        else {
            Add-Finding -Status 'WARN' -Component 'PyTorch CUDA' -Detail $torchDetail
        }
    }
    catch {
        Add-Finding -Status 'MISSING' -Component 'PyTorch CUDA' -Detail $_.Exception.Message
    }
}

Get-Volume | Where-Object DriveLetter | Sort-Object DriveLetter | ForEach-Object {
    $sizeGiB = [math]::Round($_.Size / 1GB, 1)
    $freeGiB = [math]::Round($_.SizeRemaining / 1GB, 1)
    Add-Finding -Status 'PASS' -Component "Drive $($_.DriveLetter):" -Detail "$freeGiB GiB free of $sizeGiB GiB"
}

$script:Findings | Format-Table -AutoSize

if ($OutputPath) {
    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
    $parent = Split-Path -Parent $resolvedOutput
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [pscustomobject]@{
        generated_at = [DateTimeOffset]::UtcNow.ToString('o')
        machine_role = 'windows-desktop'
        findings = $script:Findings
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resolvedOutput -Encoding utf8
    Write-Host "Local report: $resolvedOutput"
}
