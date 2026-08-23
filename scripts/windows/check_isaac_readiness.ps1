[CmdletBinding()]
param(
    [string]$IsaacRoot = 'C:\isaacsim',
    [string]$OutputPath,
    [switch]$RunCompatibilityChecker,
    [int]$CompatibilityTimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$report = [ordered]@{
    generated_at = [DateTimeOffset]::UtcNow.ToString('o')
    machine_role = 'windows-desktop'
    official_minimum = [ordered]@{
        product = 'Isaac Sim 6.0 x86_64'
        gpu = 'GeForce RTX 4080'
        vram_gb = 16
        requirements_url = 'https://docs.isaacsim.omniverse.nvidia.com/6.0.0/installation/requirements.html'
    }
    os = $null
    gpu = $null
    installed = $false
    isaac_version = $null
    compatibility_checker = $null
    compatibility_run = 'NOT_REQUESTED'
    compatibility_exit_code = $null
    assessment = 'UNKNOWN'
}

$os = Get-CimInstance Win32_OperatingSystem
$report.os = "$($os.Caption), version $($os.Version), build $($os.BuildNumber)"

$nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidia) {
    $line = (& $nvidia.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>&1 | Select-Object -First 1).ToString().Trim()
    if ($line -and $line -match '^[^,]+,\s*[0-9]+,\s*[^,]+$') {
        $parts = $line -split ',\s*'
        $report.gpu = [ordered]@{
            name = $parts[0]
            vram_mib = [int]$parts[1]
            driver = $parts[2]
        }
    }
}

$launcher = Join-Path $IsaacRoot 'isaac-sim.bat'
$checker = Join-Path $IsaacRoot 'isaac-sim.compatibility_check.bat'
$versionPath = Join-Path $IsaacRoot 'VERSION'
$report.installed = Test-Path -LiteralPath $launcher
$report.compatibility_checker = if (Test-Path -LiteralPath $checker) { $checker } else { $null }
if (Test-Path -LiteralPath $versionPath) {
    $report.isaac_version = (Get-Content -LiteralPath $versionPath -Raw).Trim()
}

if ($report.gpu -and $report.gpu.vram_mib -lt (16 * 1024)) {
    $report.assessment = 'BELOW_OFFICIAL_MINIMUM'
}
elseif ($report.gpu) {
    $report.assessment = 'MEETS_DOCUMENTED_VRAM_FLOOR'
}
else {
    $report.assessment = 'GPU_NOT_DETECTED'
}

if ($RunCompatibilityChecker) {
    if (-not $report.compatibility_checker) {
        $report.compatibility_run = 'CHECKER_MISSING'
    }
    else {
        $argument = '/d /c ""{0}""' -f $checker
        $process = Start-Process -FilePath 'cmd.exe' -ArgumentList $argument -PassThru
        $completed = $process.WaitForExit($CompatibilityTimeoutSeconds * 1000)
        if ($completed) {
            $report.compatibility_run = 'COMPLETED'
            $report.compatibility_exit_code = $process.ExitCode
        }
        else {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            $report.compatibility_run = 'TIMED_OUT'
        }
    }
}

$reportObject = [pscustomobject]$report
$reportObject | Format-List

if ($OutputPath) {
    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
    $parent = Split-Path -Parent $resolvedOutput
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $reportObject | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resolvedOutput -Encoding utf8
    Write-Host "Local report: $resolvedOutput"
}

if ($report.assessment -eq 'GPU_NOT_DETECTED') {
    exit 2
}
exit 0
