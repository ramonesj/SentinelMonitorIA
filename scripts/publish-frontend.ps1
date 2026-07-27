[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [ValidateSet("staging", "production")]
    [string]$EnvironmentName = "staging",
    [string]$ProjectName = "SentinelMonitorIA",
    [string]$Profile = "",
    [string]$ApiBaseUrl = "",
    [ValidateSet("rules", "lex_bedrock")]
    [string]$ChatProvider = "rules",
    [string]$BucketName = "",
    [string]$WebsiteUrl = "",
    [switch]$SkipBuild,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $root "frontend"
$distRoot = Join-Path $frontendRoot "dist"

function Get-ExportValue {
    param([Parameter(Mandatory = $true)][string]$ExportName)

    $arguments = @()
    if ($Profile) {
        $arguments += @("--profile", $Profile)
    }
    $arguments += @(
        "cloudformation", "list-exports",
        "--region", $Region,
        "--query", "Exports[?Name=='$ExportName'].Value | [0]",
        "--output", "text"
    )
    $value = (& aws @arguments).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $value -or $value -eq "None") {
        throw "CloudFormation export not found: $ExportName"
    }
    return $value
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI is not available."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is not available."
}
if (-not (Test-Path $frontendRoot)) {
    throw "Frontend directory not found: $frontendRoot"
}

$awsPrefix = @()
if ($Profile) {
    $awsPrefix += @("--profile", $Profile)
}

if (-not $BucketName) {
    $BucketName = Get-ExportValue -ExportName "$ProjectName-$EnvironmentName-FrontendBucketName"
}
$null = & aws @awsPrefix s3api get-bucket-website --bucket $BucketName --region $Region 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "S3 bucket '$BucketName' is not configured as a Website bucket. Pass -BucketName for the approved public S3 Website bucket."
}
if (-not $ApiBaseUrl) {
    $albDnsName = Get-ExportValue -ExportName "$ProjectName-$EnvironmentName-LoadBalancerDnsName"
    $ApiBaseUrl = "http://$($albDnsName -replace '^https?://', '')"
}
$ApiBaseUrl = $ApiBaseUrl.TrimEnd("/")
if ($ApiBaseUrl -notmatch '^https?://') {
    throw "ApiBaseUrl must start with http:// or https://"
}
if (-not $WebsiteUrl) {
    $WebsiteUrl = "http://$BucketName.s3-website-$Region.amazonaws.com"
}

if (-not $SkipBuild) {
    $previousApiBaseUrl = $env:VITE_API_BASE_URL
    $previousChatProvider = $env:VITE_CHAT_PROVIDER
    $locationPushed = $false
    try {
        $env:VITE_API_BASE_URL = $ApiBaseUrl
        $env:VITE_CHAT_PROVIDER = $ChatProvider
        Push-Location $frontendRoot
        $locationPushed = $true
        Write-Host "Building frontend with VITE_API_BASE_URL=$ApiBaseUrl and VITE_CHAT_PROVIDER=$ChatProvider" -ForegroundColor Cyan
        & npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed."
        }
    } finally {
        if ($locationPushed) {
            Pop-Location
        }
        $env:VITE_API_BASE_URL = $previousApiBaseUrl
        $env:VITE_CHAT_PROVIDER = $previousChatProvider
    }
}

if (-not (Test-Path (Join-Path $distRoot "index.html"))) {
    throw "frontend/dist/index.html was not found. Build the frontend or remove -SkipBuild only when dist already exists."
}

$s3Arguments = @(
    "s3", "sync",
    $distRoot,
    "s3://$BucketName",
    "--region", $Region,
    "--delete",
    "--only-show-errors"
)
if ($DryRun) {
    $s3Arguments += "--dryrun"
}

Write-Host "Publishing frontend to s3://$BucketName" -ForegroundColor Cyan
& aws @awsPrefix @s3Arguments
if ($LASTEXITCODE -ne 0) {
    throw "S3 frontend publication failed."
}

Write-Host "Frontend publication completed." -ForegroundColor Green
Write-Host "Public URL: $WebsiteUrl"
Write-Host "API base URL: $ApiBaseUrl"
Write-Host "Chat provider label: $ChatProvider"
