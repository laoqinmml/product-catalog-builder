# Drop the previous derived print assets so assets-print never keeps stale files.
# This file is ASCII only on purpose: Windows PowerShell 5.1 reads a .ps1
# without a BOM as ANSI, so Chinese literals here would be mangled.
param(
  [Parameter(Mandatory = $true)][string]$Root
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$target = Join-Path $rootPath "assets-print"

if (-not (Test-Path -LiteralPath $target)) {
  Write-Output "nothing to remove"
  exit 0
}

$resolved = (Resolve-Path -LiteralPath $target).Path
if (-not $resolved.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "refusing to delete outside root: $resolved"
}

Remove-Item -LiteralPath $resolved -Recurse -Force
Write-Output "removed $resolved"
