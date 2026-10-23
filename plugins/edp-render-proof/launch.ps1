$ErrorActionPreference = 'Stop'
$runtimeFile = Join-Path $env:LOCALAPPDATA 'EnterpriseTableChart/runtime.json'
if (!(Test-Path -LiteralPath $runtimeFile)) { throw 'Run Install.ps1 from the enterprise-table-chart repository first.' }
$runtime = Get-Content -LiteralPath $runtimeFile -Raw -Encoding UTF8 | ConvertFrom-Json
if (!(Test-Path -LiteralPath $runtime.python)) { throw 'Plugin Python runtime is missing. Run Install.ps1 again.' }
& $runtime.python -X utf8 -u (Join-Path $PSScriptRoot 'fixed_server.py')
exit $LASTEXITCODE
