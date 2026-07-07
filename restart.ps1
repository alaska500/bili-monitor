param(
    [ValidateSet("web", "monitor")]
    [string]$Mode = "web",
    [string]$Config = "config.yaml",
    [string]$Host = "",
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$ConfigPath = if ([System.IO.Path]::IsPathRooted($Config)) { $Config } else { Join-Path $Root $Config }
$PidDir = Join-Path $Root "data"
$PidFile = Join-Path $PidDir "bili-monitor-$Mode.pid"

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @{
            Exe  = $python.Source
            Args = @()
        }
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @{
            Exe  = $py.Source
            Args = @("-3")
        }
    }

    throw "Python executable not found. Please make sure python or py is available in PATH."
}

function Test-BiliMonitorCommandLine {
    param(
        [string]$CommandLine,
        [string]$ModeName
    )

    if ([string]::IsNullOrWhiteSpace($CommandLine)) {
        return $false
    }

    return (
        ($CommandLine -like "*bili_monitor*") -or ($CommandLine -like "*bili-monitor*")
    ) -and (
        ($CommandLine -like "* $ModeName *") -or
        ($CommandLine -like "*`"$ModeName`"*") -or
        ($CommandLine -like "*'$ModeName'*") -or
        ($CommandLine -like "*$ModeName*")
    )
}

function Stop-BiliMonitorProcesses {
    param(
        [string]$ModeName,
        [string]$PidPath
    )

    $targets = @()

    if (Test-Path -LiteralPath $PidPath) {
        $pidText = (Get-Content -LiteralPath $PidPath -Raw).Trim()
        if ($pidText -match '^\d+$') {
            $pid = [int]$pidText
            $process = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $pid) -ErrorAction SilentlyContinue
            if ($process -and (Test-BiliMonitorCommandLine -CommandLine $process.CommandLine -ModeName $ModeName)) {
                $targets += $pid
            }
        }
    }

    $matched = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        Test-BiliMonitorCommandLine -CommandLine $_.CommandLine -ModeName $ModeName
    }

    foreach ($item in $matched) {
        if ($targets -notcontains $item.ProcessId) {
            $targets += $item.ProcessId
        }
    }

    foreach ($pid in $targets) {
        try {
            Stop-Process -Id $pid -Force
            Write-Host "Stopped process $pid"
        } catch {
            Write-Host ("Skip process {0}: {1}" -f $pid, $_.Exception.Message)
        }
    }

    if (Test-Path -LiteralPath $PidPath) {
        Remove-Item -LiteralPath $PidPath -Force
    }
}

function Start-BiliMonitorProcess {
    param(
        [string]$ModeName,
        [string]$ConfigFile,
        [string]$HostName,
        [int]$PortNumber,
        [string]$PidPath
    )

    if (-not (Test-Path -LiteralPath $PidDir)) {
        New-Item -ItemType Directory -Path $PidDir | Out-Null
    }

    $python = Get-PythonCommand
    $args = @()
    $args += $python.Args
    $args += @("-m", "bili_monitor", $ModeName, "-c", $ConfigFile)

    if (-not [string]::IsNullOrWhiteSpace($HostName)) {
        $args += @("--host", $HostName)
    }

    if ($PortNumber -gt 0) {
        $args += @("--port", "$PortNumber")
    }

    $process = Start-Process -FilePath $python.Exe -ArgumentList $args -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    Set-Content -LiteralPath $PidPath -Value $process.Id -Encoding ascii

    Start-Sleep -Seconds 2

    if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) {
        throw "Failed to start bili-monitor $ModeName."
    }

    Write-Host "Started bili-monitor $ModeName (PID $($process.Id))"
    Write-Host "Config: $ConfigFile"
}

try {
    Stop-BiliMonitorProcesses -ModeName $Mode -PidPath $PidFile
    Start-BiliMonitorProcess -ModeName $Mode -ConfigFile $ConfigPath -HostName $Host -PortNumber $Port -PidPath $PidFile
} catch {
    Write-Host ("Restart failed: {0}" -f $_.Exception.Message)
    exit 1
}
