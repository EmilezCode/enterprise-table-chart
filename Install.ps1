$ErrorActionPreference = 'Stop'
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Program" }
}
if (!(Get-Command codex -ErrorAction SilentlyContinue)) { throw 'Install Codex CLI first.' }
# Capture in memory only: this JSON can contain this user's existing credentials.
$connectionJson = & codex mcp get enterprise_data_remote --json
if ($LASTEXITCODE -ne 0) { throw 'Configure your own authorized enterprise_data_remote first.' }
$connection = $connectionJson | ConvertFrom-Json
$transport = $connection.transport
$address = $null
if (!$connection.enabled -or $transport.type -ne 'streamable_http' -or
    ![Uri]::TryCreate($transport.url, [UriKind]::Absolute, [ref]$address) -or
    $address.Scheme -ne 'https' -or $address.UserInfo -or $address.Query -or $address.Fragment) {
    throw 'An enabled, authorized HTTPS enterprise_data_remote connection is required.'
}
if (!$transport.http_headers -or @($transport.http_headers.PSObject.Properties).Count -eq 0) {
    throw 'This installer requires your own http_headers authorization. OAuth-only migration needs separate setup.'
}
$headers = @{}
foreach ($item in $transport.http_headers.PSObject.Properties) { $headers[$item.Name] = $item.Value }
$headers['X-EDP-Client'] = 'table-chart-plugin'
$installRoot = Join-Path $env:LOCALAPPDATA 'EnterpriseTableChart/remote-marketplace'
$plugin = Join-Path $installRoot 'plugins/edp-render-proof'
New-Item -ItemType Directory -Force -Path (Join-Path $plugin '.codex-plugin') | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'plugins/edp-render-proof/.codex-plugin/plugin.json') -Destination (Join-Path $plugin '.codex-plugin/plugin.json') -Force
# Native HTTP configuration stays local, outside the public Git repository.
$remote = @{type='http'; url=$transport.url; http_headers=$headers}
$mcp = @{mcpServers=@{edp_render_proof=$remote}}
[IO.File]::WriteAllText((Join-Path $plugin '.mcp.json'), ($mcp | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
$catalogRoot = Join-Path $installRoot '.agents/plugins'
New-Item -ItemType Directory -Force -Path $catalogRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '.agents/plugins/marketplace.json') -Destination (Join-Path $catalogRoot 'marketplace.json') -Force
Invoke-Checked 'codex' @('plugin','marketplace','add',$installRoot,'--json')
Invoke-Checked 'codex' @('plugin','add','edp-render-proof@enterprise-table-chart','--json')
Invoke-Checked 'codex' @('features','enable','enable_mcp_apps')
# Migrate only the known old table-chart entry; preserve all other user settings.
$codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
$configFile = Join-Path $codexRoot 'config.toml'
$body = [IO.File]::ReadAllText($configFile)
$pattern = '(?ms)(^\[plugins\."edp-render-proof@edp-ui-proof-local"\]\r?\n)(.*?)(?=^\[|\z)'
$updated = [regex]::Replace($body, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{
    param($match)
    $match.Groups[1].Value + [regex]::Replace($match.Groups[2].Value, '(?m)^enabled[ \t]*=[ \t]*true[ \t]*\r?$', 'enabled = false')
})
if ($updated -ne $body) { [IO.File]::WriteAllText($configFile, $updated, [Text.UTF8Encoding]::new($false)) }
Write-Host 'Installed native remote HTTP plugin. No Python bridge is used. The known 1.x local entry is disabled; its files and old cards are retained. Reload the plugin or start a new chat.'
