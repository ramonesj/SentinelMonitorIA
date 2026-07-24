# SentinelMonitorIA Docker Desktop status check
# Run from any directory: .\scripts\check-docker.ps1

$ErrorActionPreference = "Continue"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$testComposePath = Join-Path $scriptRoot "test-docker-compose.yml"

# Kiro/PowerShell sessions may have an old PATH after Docker Desktop installation.
# Add Docker Desktop's per-user CLI directory when it exists.
$dockerUserBin = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin"
if ((Test-Path (Join-Path $dockerUserBin "docker.exe")) -and ($env:Path -notlike "*$dockerUserBin*")) {
    $env:Path = "$dockerUserBin;$env:Path"
}

function Write-Section([string]$Message) {
    Write-Host ""
    Write-Host $Message -ForegroundColor Cyan
}

function Invoke-CommandCheck([string]$CommandName, [string[]]$Arguments) {
    $output = & $CommandName @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    return [PSCustomObject]@{
        Output = $output
        ExitCode = $exitCode
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Docker Desktop Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Section "1. Docker CLI"
$dockerVersion = Invoke-CommandCheck "docker" @("--version")
if ($dockerVersion.ExitCode -eq 0) {
    Write-Host ("   OK: {0}" -f ($dockerVersion.Output -join " ")) -ForegroundColor Green
} else {
    Write-Host "   ERROR: Docker CLI no está disponible en PATH." -ForegroundColor Red
    exit 1
}

Write-Section "2. Docker Compose"
$composeVersion = Invoke-CommandCheck "docker" @("compose", "version")
$composeCommand = "docker compose"
if ($composeVersion.ExitCode -eq 0) {
    Write-Host ("   OK: {0}" -f ($composeVersion.Output -join " ")) -ForegroundColor Green
} else {
    $legacyCompose = Invoke-CommandCheck "docker-compose" @("--version")
    if ($legacyCompose.ExitCode -eq 0) {
        $composeCommand = "docker-compose"
        Write-Host ("   OK: {0}" -f ($legacyCompose.Output -join " ")) -ForegroundColor Green
    } else {
        Write-Host "   ERROR: Docker Compose no está disponible." -ForegroundColor Red
        exit 1
    }
}

Write-Section "3. Docker daemon"
$dockerInfo = Invoke-CommandCheck "docker" @("info")
if ($dockerInfo.ExitCode -ne 0) {
    Write-Host "   ERROR: No se puede conectar con el daemon de Docker." -ForegroundColor Red
    Write-Host "   Abre Docker Desktop y espera a que indique Engine running." -ForegroundColor Yellow
    exit 1
}

Write-Host "   OK: Docker daemon está ejecutándose." -ForegroundColor Green
$serverVersion = (& docker info --format "{{.ServerVersion}}" 2>$null)
$containerCount = (& docker info --format "{{.Containers}}" 2>$null)
$imageCount = (& docker info --format "{{.Images}}" 2>$null)
Write-Host ("   Server version: {0}" -f $serverVersion) -ForegroundColor White
Write-Host ("   Containers: {0}" -f $containerCount) -ForegroundColor White
Write-Host ("   Images: {0}" -f $imageCount) -ForegroundColor White

Write-Section "4. Docker Compose smoke test"
$composeLines = @(
    "services:",
    "  test:",
    "    image: hello-world:latest"
)
$composeLines | Set-Content -Path $testComposePath -Encoding utf8

try {
    Write-Host "   Descargando/ejecutando hello-world; puede tardar la primera vez..." -ForegroundColor White
    if ($composeCommand -eq "docker compose") {
        & docker compose -f $testComposePath up --quiet-pull --no-color --abort-on-container-exit
    } else {
        & docker-compose -f $testComposePath up --quiet-pull --no-color --abort-on-container-exit
    }

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   OK: Docker Compose ejecutó el contenedor de prueba." -ForegroundColor Green
    } else {
        Write-Host "   ERROR: Docker Compose devolvió código $LASTEXITCODE." -ForegroundColor Red
        exit 1
    }
} finally {
    if ($composeCommand -eq "docker compose") {
        & docker compose -f $testComposePath down --remove-orphans 2>$null | Out-Null
    } else {
        & docker-compose -f $testComposePath down --remove-orphans 2>$null | Out-Null
    }
    Remove-Item -Path $testComposePath -Force -ErrorAction SilentlyContinue
}

Write-Section "5. WSL"
$wslStatus = Invoke-CommandCheck "wsl" @("--status")
if ($wslStatus.ExitCode -eq 0) {
    Write-Host "   OK: WSL está disponible." -ForegroundColor Green
} else {
    Write-Host "   AVISO: No se pudo verificar WSL; Docker puede seguir funcionando con otra configuración." -ForegroundColor Yellow
}

Write-Section "6. Resumen"
Write-Host "   DOCKER STATUS: READY" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso desde la raíz del proyecto:" -ForegroundColor Cyan
Write-Host '   .\scripts\start-local.ps1' -ForegroundColor White
Write-Host ""
Write-Host "Después, prueba la API con:" -ForegroundColor Cyan
Write-Host '   .\scripts\test-api.ps1' -ForegroundColor White
