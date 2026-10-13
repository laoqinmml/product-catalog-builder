param(
  # Pass the catalogue root from the caller. This file is ASCII only on purpose:
  # Windows PowerShell 5.1 reads a .ps1 without a BOM as ANSI, so Chinese
  # literals here would be mangled into broken paths.
  [Parameter(Mandatory=$true)][string]$Root,
  [string[]]$Only = @(),
  [string]$Browser,
  [string]$OutDir
)

# Render pages/*.html to the output folder with headless Edge.
# render.cjs needs playwright, which is usually not installed, so Edge is used.

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -LiteralPath $Root).Path

$edgeCandidates = @(
  "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
  "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)
$edge = $edgeCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $edge) { $edge = $Browser }
if (-not $edge) {
  throw "no browser found: install Edge or pass -Browser <chrome-or-edge.exe>"
}

$pagesDir = Join-Path $rootPath "pages"
if (-not (Test-Path -LiteralPath $pagesDir)) { throw "pages folder not found: $pagesDir" }

if (-not $OutDir) { $OutDir = Join-Path $rootPath ([char]0x8F93 + [char]0x51FA) }
$outDir = $OutDir
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

# Browsers cache file:// images. Without a fresh profile a replaced asset
# keeps rendering as the old picture, so the profile is rebuilt every run.
$profile = Join-Path $rootPath "tmp\edge-profile-render"
if (Test-Path -LiteralPath $profile) { Remove-Item -LiteralPath $profile -Recurse -Force }
New-Item -ItemType Directory -Path $profile -Force | Out-Null

$files = Get-ChildItem -LiteralPath $pagesDir -Filter *.html -File | Sort-Object Name
if ($Only.Count -gt 0) { $files = $files | Where-Object { $Only -contains $_.Name } }

$ok = 0
foreach ($file in $files) {
  $target = (Join-Path $pagesDir $file.Name) -replace '\\', '/'
  $url = "file:///" + [uri]::EscapeUriString($target)
  $out = Join-Path $outDir ([System.IO.Path]::ChangeExtension($file.Name, ".png"))
  & $edge --headless=new --no-sandbox --disable-gpu --hide-scrollbars `
    --force-device-scale-factor=2 --window-size=794,1123 `
    --user-data-dir=$profile --screenshot=$out $url 2>&1 | Out-Null
  if (Test-Path -LiteralPath $out) { $ok++; Write-Output "OK  $($file.Name)" }
  else { Write-Output "FAIL $($file.Name)" }
}
Write-Output "rendered $ok / $($files.Count)"
