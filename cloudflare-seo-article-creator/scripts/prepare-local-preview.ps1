#Requires -Version 5.1

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{0,119}$')]
    [string]$ArticleId,
    [ValidatePattern('^[a-zA-Z0-9-]{1,80}$')]
    [string]$RunId = ([guid]::NewGuid().ToString('N')),
    [string]$WorkRoot,
    [string]$TemporaryRoot,
    [string]$PreviewRoot,
    [switch]$InitializeOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# WindowsとmacOSで保存先・コピー・正本保持の実装を共有する。
$python = Get-Command python3, python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $python) {
    throw 'Python 3.9以上が必要です。自動インストールは行いません。'
}
$scriptPath = Join-Path $PSScriptRoot 'prepare-local-preview.py'
$pythonArgs = @($scriptPath, '--project-root', $ProjectRoot, '--article-id', $ArticleId, '--run-id', $RunId)
if (-not [string]::IsNullOrWhiteSpace($WorkRoot)) { $pythonArgs += @('--work-root', $WorkRoot) }
if (-not [string]::IsNullOrWhiteSpace($TemporaryRoot)) { $pythonArgs += @('--temporary-root', $TemporaryRoot) }
if (-not [string]::IsNullOrWhiteSpace($PreviewRoot)) { $pythonArgs += @('--preview-root', $PreviewRoot) }
if ($InitializeOnly) { $pythonArgs += '--initialize-only' }
& $python.Source @pythonArgs
if ($LASTEXITCODE -ne 0) {
    throw '一時プレビューの準備に失敗しました。出力した BLOCKED の理由を確認してください。'
}
