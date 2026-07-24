# SentinelMonitorIA System Check Script
# Verifica requisitos del sistema para desarrollo

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SentinelMonitorIA System Check      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check 1: Docker
Write-Host "1. Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Docker installed: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Docker not found or not in PATH" -ForegroundColor Red
        Write-Host "   Please install Docker Desktop from:" -ForegroundColor Yellow
        Write-Host "   https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ✗ Docker not found: $_" -ForegroundColor Red
}

Write-Host ""

# Check 2: Docker Compose
Write-Host "2. Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Docker Compose installed: $composeVersion" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Docker Compose not found" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Docker Compose not found: $_" -ForegroundColor Red
}

Write-Host ""

# Check 3: Python (optional)
Write-Host "3. Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Python installed: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "   ⚠ Python not found (optional for development)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠ Python not found (optional)" -ForegroundColor Yellow
}

Write-Host ""

# Check 4: Project structure
Write-Host "4. Checking project structure..." -ForegroundColor Yellow
$requiredDirs = @("agent", "backend", "frontend", "infra", "scripts")
$missingDirs = @()

foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Host "   ✓ Directory exists: $dir" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Missing directory: $dir" -ForegroundColor Red
        $missingDirs += $dir
    }
}

Write-Host ""

# Check 5: Backend requirements
Write-Host "5. Checking backend files..." -ForegroundColor Yellow
$backendFiles = @("docker-compose.yml", "Dockerfile", "requirements.txt")
foreach ($file in $backendFiles) {
    if (Test-Path "backend\$file") {
        Write-Host "   ✓ Backend file exists: $file" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Missing backend file: $file" -ForegroundColor Red
    }
}

Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "              SUMMARY                   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($missingDirs.Count -eq 0) {
    Write-Host "✓ Project structure is complete" -ForegroundColor Green
} else {
    Write-Host "⚠ Missing directories: $($missingDirs -join ', ')" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Install Docker Desktop if not installed" -ForegroundColor White
Write-Host "2. Run: cd backend" -ForegroundColor White
Write-Host "3. Run: docker-compose up -d" -ForegroundColor White
Write-Host "4. Test API at: http://localhost:8000" -ForegroundColor White
Write-Host ""

# Check Docker service
Write-Host "Checking Docker service status..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker service is running" -ForegroundColor Green
        Write-Host ""
        Write-Host "Ready to start SentinelMonitorIA!" -ForegroundColor Green
    } else {
        Write-Host "✗ Docker service is not running" -ForegroundColor Red
        Write-Host "Please start Docker Desktop application" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Cannot connect to Docker daemon" -ForegroundColor Red
    Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
}