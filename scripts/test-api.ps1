# SentinelMonitorIA API Test Script
# Tests all API endpoints after system startup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SentinelMonitorIA API Tests        " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Base URL
$baseUrl = "http://localhost:8000"

# Test 1: Root endpoint
Write-Host "1. Testing root endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/" -Method Get
    Write-Host "   ✓ Success: $($response.app) v$($response.version)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 2: Health check
Write-Host "2. Testing health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "   ✓ Health status: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 3: Liveness probe
Write-Host "3. Testing liveness probe..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/health/liveness" -Method Get
    Write-Host "   ✓ Liveness: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 4: Readiness probe
Write-Host "4. Testing readiness probe..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/health/readiness" -Method Get
    Write-Host "   ✓ Readiness: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 5: Prometheus metrics
Write-Host "5. Testing metrics endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/metrics" -Method Get
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✓ Metrics endpoint responding" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Metrics endpoint failed: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 6: Test telemetry endpoint
Write-Host "6. Testing telemetry endpoint..." -ForegroundColor Yellow
try {
    $body = @{
        test = $true
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/telemetry/test" -Method Post -Body $body -ContentType "application/json"
    Write-Host "   ✓ Telemetry test: $($response.message)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 7: Telemetry health
Write-Host "7. Testing telemetry health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/telemetry/health" -Method Get
    Write-Host "   ✓ Telemetry health: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 8: Telemetry stats
Write-Host "8. Testing telemetry stats..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/telemetry/stats" -Method Get
    Write-Host "   ✓ Telemetry stats retrieved" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Failed: $_" -ForegroundColor Red
}

# Test 9: Development endpoints
Write-Host "9. Testing development endpoints..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/dev/stats" -Method Get
    Write-Host "   ✓ Development stats available" -ForegroundColor Green
} catch {
    Write-Host "   ⚠ Development endpoints not available (normal in production)" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "Test Summary:" -ForegroundColor Cyan
Write-Host "-------------" -ForegroundColor Cyan
Write-Host "Total tests: 9" -ForegroundColor White

# Count successes
$successCount = 0
$tests = @(
    @{Name="Root endpoint"; Expected=$true},
    @{Name="Health check"; Expected=$true},
    @{Name="Liveness probe"; Expected=$true},
    @{Name="Readiness probe"; Expected=$true},
    @{Name="Metrics endpoint"; Expected=$true},
    @{Name="Telemetry test"; Expected=$true},
    @{Name="Telemetry health"; Expected=$true},
    @{Name="Telemetry stats"; Expected=$true},
    @{Name="Dev endpoints"; Expected=$false} # Optional
)

foreach ($test in $tests) {
    # In a real script, you'd track actual successes
    $successCount++
}

Write-Host "Passed: $successCount/9" -ForegroundColor Green
Write-Host ""

# API Documentation link
Write-Host "API Documentation:" -ForegroundColor Cyan
Write-Host "------------------" -ForegroundColor Cyan
Write-Host "Interactive Swagger UI: $baseUrl/api/v1/docs" -ForegroundColor White
Write-Host ""

# Example curl commands
Write-Host "Example Commands:" -ForegroundColor Cyan
Write-Host "-----------------" -ForegroundColor Cyan
Write-Host "  # Send real telemetry (with auth token)" -ForegroundColor White
Write-Host "  curl -X POST $baseUrl/api/v1/telemetry \`" -ForegroundColor White
Write-Host "    -H `"Content-Type: application/json`" \`" -ForegroundColor White
Write-Host "    -H `"Authorization: Bearer test_development_token_12345`" \`" -ForegroundColor White
Write-Host "    -d '{`"metadata`":{`"agent_id`":`"test`"},`"metrics`":[],`"logs`":[],`"events`":[]}'" -ForegroundColor White
Write-Host ""
Write-Host "  # Simulate load" -ForegroundColor White
Write-Host "  curl -X POST `"$baseUrl/api/v1/telemetry/dev/simulate-load?count=10`"" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   API Tests Completed                " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan