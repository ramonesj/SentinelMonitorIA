# SentinelMonitorIA local smoke checks
# Read-only checks for backend, frontend and public observability endpoints.

param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [switch]$RequireFrontend
)

$ErrorActionPreference = "Stop"
$failures = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Uri,
        [switch]$Optional
    )

    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
            throw "HTTP $($response.StatusCode)"
        }
        Write-Host ("PASS  {0}: HTTP {1}" -f $Name, [int]$response.StatusCode) -ForegroundColor Green
        return
    } catch {
        if ($Optional) {
            Write-Host ("WARN  {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Yellow
        } else {
            $script:failures++
            Write-Host ("FAIL  {0}: {1}" -f $Name, $_.Exception.Message) -ForegroundColor Red
        }
    }
}

Write-Host "SentinelMonitorIA local smoke checks" -ForegroundColor Cyan
Write-Host "Backend:  $BackendUrl"
Write-Host "Frontend: $FrontendUrl"
Write-Host ""

Test-Endpoint -Name "Backend root" -Uri "$BackendUrl/"
Test-Endpoint -Name "Backend health" -Uri "$BackendUrl/health"
Test-Endpoint -Name "API liveness" -Uri "$BackendUrl/api/v1/health/liveness"
Test-Endpoint -Name "API readiness" -Uri "$BackendUrl/api/v1/health/readiness"
Test-Endpoint -Name "Prometheus metrics" -Uri "$BackendUrl/metrics"
Test-Endpoint -Name "Telemetry health" -Uri "$BackendUrl/api/v1/telemetry/health"
Test-Endpoint -Name "Telemetry stats" -Uri "$BackendUrl/api/v1/telemetry/stats"

if ($RequireFrontend) {
    Test-Endpoint -Name "Frontend" -Uri "$FrontendUrl/"
} else {
    Test-Endpoint -Name "Frontend (optional)" -Uri "$FrontendUrl/" -Optional
}

Write-Host ""
if ($failures -gt 0) {
    Write-Host ("Smoke checks failed: {0}" -f $failures) -ForegroundColor Red
    exit 1
}

Write-Host "Smoke checks passed." -ForegroundColor Green
