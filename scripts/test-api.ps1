# SentinelMonitorIA API smoke script
# Checks public API and development observability endpoints after startup.

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$results = @()

function Test-ApiEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Uri,
        [ValidateSet("Get", "Post")]
        [string]$Method = "Get",
        [string]$Body,
        [switch]$Optional
    )

    $status = 0
    try {
        $request = @{
            Uri = $Uri
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }

        if ($PSBoundParameters.ContainsKey("Body")) {
            $request.Body = $Body
            $request.ContentType = "application/json"
        }

        $response = Invoke-WebRequest @request
        $status = [int]$response.StatusCode
        if ($status -lt 200 -or $status -ge 400) {
            throw "HTTP $status"
        }

        $script:results += [pscustomobject]@{
            Name = $Name
            Passed = $true
            Optional = [bool]$Optional
        }
        Write-Host ("PASS {0}: HTTP {1}" -f $Name, $status) -ForegroundColor Green
    }
    catch {
        $message = if ($status -gt 0) { "HTTP $status" } else { "request failed" }
        $script:results += [pscustomobject]@{
            Name = $Name
            Passed = $false
            Optional = [bool]$Optional
        }
        if ($Optional) {
            Write-Host ("WARN {0}: {1}" -f $Name, $message) -ForegroundColor Yellow
        }
        else {
            Write-Host ("FAIL {0}: {1}" -f $Name, $message) -ForegroundColor Red
        }
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   SentinelMonitorIA API Smoke Checks   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ("Base URL: {0}" -f $BaseUrl)
Write-Host ""

Test-ApiEndpoint -Name "Backend root" -Uri "$BaseUrl/"
Test-ApiEndpoint -Name "Backend health" -Uri "$BaseUrl/health"
Test-ApiEndpoint -Name "API liveness" -Uri "$BaseUrl/api/v1/health/liveness"
Test-ApiEndpoint -Name "API readiness" -Uri "$BaseUrl/api/v1/health/readiness"
Test-ApiEndpoint -Name "Prometheus metrics" -Uri "$BaseUrl/metrics"

$testBody = "{}"
Test-ApiEndpoint -Name "Telemetry test" -Uri "$BaseUrl/api/v1/telemetry/test" -Method Post -Body $testBody
Test-ApiEndpoint -Name "Telemetry health" -Uri "$BaseUrl/api/v1/telemetry/health"
Test-ApiEndpoint -Name "Telemetry stats" -Uri "$BaseUrl/api/v1/telemetry/stats"
Test-ApiEndpoint -Name "OpenAPI docs" -Uri "$BaseUrl/api/v1/docs" -Optional

$requiredFailures = @($results | Where-Object { -not $_.Passed -and -not $_.Optional }).Count
$passed = @($results | Where-Object { $_.Passed }).Count
$optionalWarnings = @($results | Where-Object { -not $_.Passed -and $_.Optional }).Count

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host ("  Passed: {0}" -f $passed) -ForegroundColor Green
Write-Host ("  Required failures: {0}" -f $requiredFailures) -ForegroundColor $(if ($requiredFailures) { "Red" } else { "Green" })
Write-Host ("  Optional warnings: {0}" -f $optionalWarnings) -ForegroundColor Yellow
Write-Host ""

if ($requiredFailures -gt 0) {
    exit 1
}

Write-Host "API smoke checks passed." -ForegroundColor Green
