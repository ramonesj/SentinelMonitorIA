[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [string]$Profile = "",
    [string]$Phase = "",
    [switch]$IncludeAiNotifications
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$phaseRoot = Join-Path $root "infra\cloudformation\phases"
$basePhaseOrder = @(
    "00-vpc-network",
    "01-nat-instance",
    "02-security-groups",
    "03-iam",
    "04-ecr",
    "05-rds",
    "06-redis",
    "07-application-secrets",
    "08-cloudwatch",
    "09-alb",
    "10-ecs-cluster",
    "11-ecs-backend",
    "12-ecs-worker",
    "13-frontend-s3",
    "14-cloudfront"
)
$aiNotificationPhaseOrder = @(
    "19-ai-platform",
    "20-notification-platform",
    "21-ecs-ai-worker",
    "22-ecs-notification-worker"
)
$allPhaseOrder = @($basePhaseOrder + $aiNotificationPhaseOrder)
$selectedPhaseOrder = @($basePhaseOrder)
if ($IncludeAiNotifications) {
    $selectedPhaseOrder += $aiNotificationPhaseOrder
}

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI is not available."
}
if ($Region -ne "us-east-1") {
    throw "The current modular templates are pinned to us-east-1; received region '$Region'."
}

if ($Phase) {
    if ($Phase -notin $allPhaseOrder) {
        throw "Phase '$Phase' is not supported. Use a base phase 00-14 or an optional phase 19-22."
    }
    $selectedPhases = @($Phase)
} else {
    $selectedPhases = @($selectedPhaseOrder)
}

$awsPrefix = @()
if ($Profile) {
    $awsPrefix += @("--profile", $Profile)
}

foreach ($phaseName in $selectedPhases) {
    $templatePath = Join-Path $phaseRoot "$phaseName.yaml"
    if (-not (Test-Path $templatePath)) {
        throw "Template not found: $templatePath"
    }

    Write-Host "Validating $phaseName" -ForegroundColor Cyan
    & aws @awsPrefix cloudformation validate-template --region $Region --template-body "file://$templatePath" --output json | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "CloudFormation validation failed for $phaseName."
    }
}

Write-Host "CloudFormation validation completed for $($selectedPhases.Count) phase(s)." -ForegroundColor Green