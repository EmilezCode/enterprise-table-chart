$ErrorActionPreference = 'Stop'
# Explicit client update only. No scheduled task, background updater or credential copy.
$dirty = & git -C $PSScriptRoot status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Repository is unavailable.' }
if ($dirty) { throw 'Local changes found; preserve them before updating.' }
& git -C $PSScriptRoot pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Cannot fetch a fast-forward update. Check repository access.' }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Install.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Client update was not completed.' }
Write-Host 'Client files refreshed. Start a new chat or reload the plugin to load the updated bridge.'
