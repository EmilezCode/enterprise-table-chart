param(
    [string]$Python = 'python',
    [string]$RuntimePython
)
$ErrorActionPreference = 'Stop'
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Program" }
}
if (!(Get-Command codex -ErrorAction SilentlyContinue)) { throw 'Install Codex CLI first.' }
# Only inspect connection shape. Never print, copy or modify personal credentials.
Invoke-Checked $Python @((Join-Path $PSScriptRoot 'setup_check.py'), 'connection')
$installRoot = Join-Path $env:LOCALAPPDATA 'EnterpriseTableChart'
New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
if (!$RuntimePython) {
    $venv = Join-Path $installRoot 'runtime'
    $RuntimePython = Join-Path $venv 'Scripts/python.exe'
    if (!(Test-Path -LiteralPath $RuntimePython)) { Invoke-Checked $Python @('-m', 'venv', $venv) }
    Invoke-Checked $RuntimePython @('-m', 'pip', 'install', '-r', (Join-Path $PSScriptRoot 'requirements.txt'))
}
Invoke-Checked $RuntimePython @((Join-Path $PSScriptRoot 'setup_check.py'), 'runtime')
$runtime = @{python=(Resolve-Path -LiteralPath $RuntimePython).Path}
[IO.File]::WriteAllText((Join-Path $installRoot 'runtime.json'), ($runtime | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
Invoke-Checked 'codex' @('plugin', 'marketplace', 'add', $PSScriptRoot, '--json')
Invoke-Checked 'codex' @('plugin', 'add', 'edp-render-proof@enterprise-table-chart', '--json')
Invoke-Checked 'codex' @('features', 'enable', 'enable_mcp_apps')
Write-Host 'Installed. Open Enterprise Table Chart in a new Codex chat. Existing older installations must be disabled manually to avoid duplicate entries.'
