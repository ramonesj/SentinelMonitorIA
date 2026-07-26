[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [ValidateSet("staging", "production")]
    [string]$EnvironmentName = "staging",
    [string]$ImageTag = "v0.1.0",
    [string]$Profile = "",
    [string]$AccountId = "",
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backendContext = Join-Path $root "backend"
$dockerfile = Join-Path $backendContext "Dockerfile"

if (-not (Test-Path $dockerfile)) {
    throw "Backend Dockerfile not found: $dockerfile"
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is not available."
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI is not available."
}

$awsPrefix = @()
if ($Profile) {
    $awsPrefix += @("--profile", $Profile)
}

if (-not $AccountId) {
    $AccountId = (& aws @awsPrefix sts get-caller-identity --query Account --output text).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $AccountId) {
        throw "Unable to resolve the AWS account from the current credentials."
    }
}

$registry = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$backendRepository = "$registry/sentinel-monitoria/$EnvironmentName/backend"
$workerRepository = "$registry/sentinel-monitoria/$EnvironmentName/worker"
$backendImage = "$backendRepository`:$ImageTag"
$workerImage = "$workerRepository`:$ImageTag"

Write-Host "Target platform: linux/arm64"
Write-Host "Backend image:   $backendImage"
Write-Host "Worker image:    $workerImage"

if (-not $NoPush) {
    $password = & aws @awsPrefix ecr get-login-password --region $Region
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to obtain the ECR login password."
    }
    $password | & docker login --username AWS --password-stdin $registry
    if ($LASTEXITCODE -ne 0) {
        throw "Docker login to ECR failed."
    }
}

$buildArguments = @(
    "buildx", "build",
    "--platform", "linux/arm64",
    "--file", $dockerfile,
    "--tag", $backendImage,
    "--tag", $workerImage
)

if ($NoPush) {
    $buildArguments += "--load"
} else {
    $buildArguments += "--push"
}
$buildArguments += $backendContext

Write-Host "Building backend and worker images..." -ForegroundColor Cyan
& docker @buildArguments
if ($LASTEXITCODE -ne 0) {
    throw "ARM64 image build failed."
}

Write-Host "ECR image operation completed." -ForegroundColor Green
if (-not $NoPush) {
    Write-Host "Because ECR tags are immutable, use a new ImageTag for every rebuilt image." -ForegroundColor Yellow
}