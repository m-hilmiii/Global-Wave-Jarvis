<#
.SYNOPSIS
    JARVIS AI Operating System - PowerShell Launcher & Daemon Manager
.DESCRIPTION
    Controls the local JARVIS FastAPI server, background execution, desktop shortcut, and Windows startup.
.EXAMPLE
    .\scripts\start_jarvis.ps1 -Status
    .\scripts\start_jarvis.ps1 -Background
    .\scripts\start_jarvis.ps1 -Stop
    .\scripts\start_jarvis.ps1 -Shortcut
    .\scripts\start_jarvis.ps1 -Startup
#>

[CmdletBinding()]
param(
    [switch]$Background,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Restart,
    [switch]$Shortcut,
    [switch]$Startup,
    [switch]$UninstallStartup
)

$WorkspaceRoot = Split-Path -Parent $PSScriptRoot
Set-Location $WorkspaceRoot

$PythonExe = "C:\Users\unalm\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

if ($Stop) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" stop
}
elseif ($Status) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" status
}
elseif ($Restart) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" restart
}
elseif ($Shortcut) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" shortcut
}
elseif ($Startup) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" startup-install
}
elseif ($UninstallStartup) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" startup-uninstall
}
elseif ($Background) {
    & $PythonExe "$WorkspaceRoot\scripts\jarvis_daemon.py" start
}
else {
    # Default: launch interactive or foreground
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "   🧠 JARVIS AI OPERATING SYSTEM - SAYIN HILMI" -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    & $PythonExe "$WorkspaceRoot\run_global_wave.py"
}
