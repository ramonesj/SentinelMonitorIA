# SentinelMonitorIA executive manual PDF builder
# Converts the self-contained HTML source to PDF with Google Chrome headless.

[CmdletBinding()]
param(
    [string]$ChromePath,
    [string]$InputHtml = "docs\manual\SentinelMonitorIA-Manual-Ejecutivo.html",
    [string]$OutputPdf = "docs\manual\SentinelMonitorIA-Manual-Ejecutivo.pdf"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

function Get-AbsoluteProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $projectRoot $Path))
}

function Find-Chrome {
    $candidates = @(
        (Join-Path ${env:ProgramFiles} "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:ProgramW6432 "Google\Chrome\Application\chrome.exe")
    )

    foreach ($candidate in ($candidates | Where-Object { $_ -and $_.Trim() -ne "" } | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $command = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    return $null
}

if (-not $ChromePath) {
    $ChromePath = Find-Chrome
} elseif (-not (Test-Path -LiteralPath $ChromePath -PathType Leaf)) {
    throw "No existe el ejecutable Chrome indicado: $ChromePath"
} else {
    $ChromePath = (Resolve-Path -LiteralPath $ChromePath).Path
}

if (-not $ChromePath) {
    throw "No se encontró Google Chrome. Usa -ChromePath con la ruta completa a chrome.exe."
}

$inputPath = Get-AbsoluteProjectPath -Path $InputHtml
$outputPath = Get-AbsoluteProjectPath -Path $OutputPdf

if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "No existe la fuente HTML: $inputPath"
}

$outputDirectory = Split-Path -Parent $outputPath
if (-not (Test-Path -LiteralPath $outputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
}

$inputUri = [System.Uri]::new($inputPath).AbsoluteUri
$tempProfile = Join-Path ([System.IO.Path]::GetTempPath()) ("sentinelmonitoria-chrome-" + [Guid]::NewGuid().ToString("N"))

if (Test-Path -LiteralPath $outputPath -PathType Leaf) {
    Remove-Item -LiteralPath $outputPath -Force
}

$chromeArguments = @(
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--allow-file-access-from-files",
    "--no-pdf-header-footer",
    "--user-data-dir=$tempProfile",
    "--print-to-pdf=$outputPath",
    $inputUri
)

Write-Host "SentinelMonitorIA · Generador de manual PDF" -ForegroundColor Cyan
Write-Host ("Chrome: {0}" -f $ChromePath)
Write-Host ("HTML:   {0}" -f $inputPath)
Write-Host ("PDF:    {0}" -f $outputPath)

$chromeExitCode = $null
try {
    $chromeOutput = & $ChromePath @chromeArguments 2>&1
    $chromeExitCode = $LASTEXITCODE

    # Chrome puede devolver el control antes de terminar la escritura del PDF.
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while (-not (Test-Path -LiteralPath $outputPath -PathType Leaf) -and [DateTime]::UtcNow -lt $deadline) {
        Start-Sleep -Milliseconds 500
    }
} finally {
    if (Test-Path -LiteralPath $tempProfile) {
        Remove-Item -LiteralPath $tempProfile -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($chromeExitCode -ne 0) {
    Write-Host ("Aviso: Chrome informó código de salida {0}; se validará el artefacto generado." -f $chromeExitCode) -ForegroundColor Yellow
}

if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
    throw "Chrome no generó el PDF esperado: $outputPath"
}

$outputFile = Get-Item -LiteralPath $outputPath
if ($outputFile.Length -lt 10000) {
    throw "El PDF generado parece incompleto: $($outputFile.Length) bytes."
}

$headerBytes = [System.IO.File]::ReadAllBytes($outputPath)[0..4]
$header = [System.Text.Encoding]::ASCII.GetString($headerBytes)
if ($header -ne "%PDF-") {
    throw "El archivo generado no tiene una cabecera PDF válida: '$header'"
}

Write-Host ("OK: PDF generado y validado ({0:N0} bytes)." -f $outputFile.Length) -ForegroundColor Green
