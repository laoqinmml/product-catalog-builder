# Export the merged catalogue HTML to an A4 PDF with headless Chrome.
# ASCII only on purpose (see render_pages.ps1 for the reason).
param(
  [Parameter(Mandatory = $true)][string]$Html,
  [Parameter(Mandatory = $true)][string]$Out,
  [string]$Chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Chrome)) {
  throw "Chrome not found: $Chrome"
}

$htmlPath = (Resolve-Path -LiteralPath $Html).Path
$uri = ([uri]$htmlPath).AbsoluteUri
$outPath = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
$outDir = Split-Path -Parent $outPath
if (-not (Test-Path -LiteralPath $outDir)) {
  New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}
if (Test-Path -LiteralPath $outPath) {
  Remove-Item -LiteralPath $outPath -Force
}

$pdfArgs = @(
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--no-default-browser-check",
  "--allow-file-access-from-files",
  "--no-pdf-header-footer",
  "--run-all-compositor-stages-before-draw",
  "--virtual-time-budget=60000",
  "--print-to-pdf=$outPath",
  $uri
)

& $Chrome @pdfArgs 2>&1 | Out-Null

if (-not (Test-Path -LiteralPath $outPath)) {
  throw "PDF not generated: $outPath"
}

$info = Get-Item -LiteralPath $outPath
Write-Output ("OK {0} ({1:N0} bytes)" -f $info.FullName, $info.Length)
