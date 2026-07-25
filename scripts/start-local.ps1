# SentinelMonitorIA Local Development Starter
# Starts all services using Docker Compose.

param(
    [switch]$Build,
    [switch]$Logs,
    [switch]$Clean,
    [switch]$Frontend,
    [switch]$Intelligence
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "backend\docker-compose.yml"
$frontendComposeFile = Join-Path $projectRoot "backend\docker-compose.frontend.yml"
$intelligenceComposeFile = Join-Path $projectRoot "backend\docker-compose.redis-worker.yml"
$dockerUserBin = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin"

if ((Test-Path (Join-Path $dockerUserBin "docker.exe")) -and ($env:Path -notlike "*$dockerUserBin*")) {
    $env:Path = "$dockerUserBin;$env:Path"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SentinelMonitorIA Local Starter" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path $composeFile)) {
    Write-Host ("ERROR: No existe {0}" -f $composeFile) -ForegroundColor Red
    exit 1
}

if ($Frontend -and -not (Test-Path $frontendComposeFile)) {
    Write-Host ("ERROR: No existe {0}" -f $frontendComposeFile) -ForegroundColor Red
    exit 1
}

if ($Intelligence -and -not (Test-Path $intelligenceComposeFile)) {
    Write-Host ("ERROR: No existe {0}" -f $intelligenceComposeFile) -ForegroundColor Red
    exit 1
}

$dockerVersion = & docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker CLI no está disponible." -ForegroundColor Red
    exit 1
}

$null = & docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker Desktop no está ejecutándose." -ForegroundColor Red
    exit 1
}

$composeArgs = @("compose", "-f", $composeFile)
if ($Frontend) {
    $composeArgs += @("-f", $frontendComposeFile)
}
if ($Intelligence) {
    $composeArgs += @("-f", $intelligenceComposeFile)
}

if ($Clean) {
    Write-Host "Eliminando servicios y volúmenes locales..." -ForegroundColor Yellow
    & docker @composeArgs down -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "OK: recursos locales eliminados." -ForegroundColor Green
    exit 0
}

if ($Build) {
    if ($Intelligence) {
        Write-Host "Construyendo backend, telemetry worker, AI worker y notification worker..." -ForegroundColor Yellow
    } elseif ($Frontend) {
        Write-Host "Construyendo las imágenes del backend y frontend..." -ForegroundColor Yellow
    } else {
        Write-Host "Construyendo la imagen del backend..." -ForegroundColor Yellow
    }
    & docker @composeArgs build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: falló la construcción." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if ($Intelligence) {
    Write-Host "Iniciando PostgreSQL, Redis, backend, telemetry worker, AI worker y notification worker..." -ForegroundColor Yellow
} elseif ($Frontend) {
    Write-Host "Iniciando PostgreSQL, Redis, backend y frontend en Docker (LocalStack es opcional con el perfil aws)..." -ForegroundColor Yellow
} else {
    Write-Host "Iniciando PostgreSQL, Redis y backend (LocalStack es opcional con el perfil aws)..." -ForegroundColor Yellow
}
& docker @composeArgs up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: falló el arranque del stack." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "OK: servicios iniciados." -ForegroundColor Green
Write-Host "Esperando a que los servicios publiquen sus puertos..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$services = @(
    @{ Name = "PostgreSQL"; Port = 5432; Url = "localhost:5432" },
    @{ Name = "Redis"; Port = 6379; Url = "localhost:6379" },
    @{ Name = "Backend API"; Port = 8000; Url = "http://localhost:8000" },
    @{ Name = "Adminer"; Port = 8080; Url = "http://localhost:8080" },
    @{ Name = "Redis Commander"; Port = 8081; Url = "http://localhost:8081" }
)

if ($Frontend) {
    $services += @{ Name = "Frontend"; Port = 3000; Url = "http://localhost:3000" }
}

Write-Host ""
Write-Host "Estado de servicios:" -ForegroundColor Cyan
foreach ($service in $services) {
    $open = Test-NetConnection -ComputerName localhost -Port $service.Port -WarningAction SilentlyContinue
    if ($open.TcpTestSucceeded) {
        Write-Host ("  OK  {0}: {1}" -f $service.Name, $service.Url) -ForegroundColor Green
    } else {
        Write-Host ("  --  {0}: puerto {1} no responde todavía" -f $service.Name, $service.Port) -ForegroundColor Yellow
    }
}

if ($Logs) {
    Write-Host ""
    Write-Host "Mostrando logs. Usa Ctrl+C para salir del seguimiento." -ForegroundColor Yellow
    & docker @composeArgs logs -f
} else {
    Write-Host ""
    Write-Host "API:       http://localhost:8000" -ForegroundColor White
    Write-Host "Swagger:   http://localhost:8000/api/v1/docs" -ForegroundColor White
    Write-Host "Health:    http://localhost:8000/health" -ForegroundColor White
    if ($Frontend) {
        Write-Host "Frontend:  http://localhost:3000" -ForegroundColor White
    } else {
        Write-Host "Frontend:  ejecutar npm run dev en frontend o usar -Frontend" -ForegroundColor White
    }
    Write-Host "Adminer:   http://localhost:8080" -ForegroundColor White
    Write-Host "Redis UI:  http://localhost:8081" -ForegroundColor White
    Write-Host ""
    Write-Host "Ver logs:  docker compose -f backend\docker-compose.yml logs -f" -ForegroundColor White
    Write-Host "Detener:   docker compose -f backend\docker-compose.yml down" -ForegroundColor White
}