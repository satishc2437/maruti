<#
.SYNOPSIS
Deploys this Copilot payload into a target repository's .github/ tree.

.PARAMETER Target
Path to the target repo. Defaults to the current directory.
#>
param(
    [string]$Target = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -PathType Container $Target)) {
    Write-Error "Target directory does not exist: $Target"
    exit 1
}

$installed = 0
foreach ($sub in @('agents', 'prompts')) {
    $source = Join-Path $ScriptDir $sub
    if (Test-Path -PathType Container $source) {
        $dest = Join-Path $Target ".github\$sub"
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Recurse -Force "$source\*" $dest
        $installed++
        Write-Host "Installed $sub/ into $dest"
    }
}

if ($installed -eq 0) {
    Write-Error "Nothing to install (payload is empty)."
    exit 1
}
