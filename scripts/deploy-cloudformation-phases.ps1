[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [string]$ProjectName = "SentinelMonitorIA",
    [ValidateSet("staging", "production")]
    [string]$EnvironmentName = "staging",
    [string]$DeploymentDay = "2026-07-23",
    [string]$Profile = "",
    [string]$Phase = "",
    [string[]]$SkipPhase = @(),
    [string[]]$AdditionalParameterOverride = @(),
    [switch]$IncludeAiNotifications,
    [switch]$StopServices,
    [switch]$NoExecuteChangeSet
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$phaseRoot = Join-Path $root "infra\cloudformation\phases"
$matrixPath = Join-Path $phaseRoot "parameters.example.json"

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

function Convert-ParameterValue {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return "" }
    if ($Value -is [bool]) { return $Value.ToString().ToLowerInvariant() }
    return [string]$Value
}

function Get-PhaseParameterOverrides {
    param([Parameter(Mandatory = $true)][string]$PhaseName)

    $matrix = Get-Content -Raw -Path $matrixPath | ConvertFrom-Json
    $values = [ordered]@{
        ProjectName = $ProjectName
        EnvironmentName = $EnvironmentName
        DeploymentDay = $DeploymentDay
    }

    foreach ($property in $matrix.phaseOverrides.PSObject.Properties) {
        if ($property.Name -eq $PhaseName) {
            foreach ($override in $property.Value.PSObject.Properties) {
                $values[$override.Name] = Convert-ParameterValue -Value $override.Value
            }
        }
    }

    if ($StopServices -and $PhaseName -in @(
            "11-ecs-backend",
            "12-ecs-worker",
            "21-ecs-ai-worker",
            "22-ecs-notification-worker"
        )) {
        $values["DesiredCount"] = "0"
    }

    foreach ($override in $AdditionalParameterOverride) {
        if ($override -notmatch "^[^=]+=.*$") {
            throw "Invalid parameter override '$override'. Use ParameterName=Value."
        }
        $parts = $override -split "=", 2
        $values[$parts[0]] = $parts[1]
    }

    return @($values.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" })
}

if (-not (Test-Path $matrixPath)) {
    throw "Parameter matrix not found: $matrixPath"
}

if ($Phase) {
    if ($Phase -notin $allPhaseOrder) {
        throw "Phase '$Phase' is not supported. Use a base phase 00-14 or an optional phase 19-22."
    }
    $selectedPhases = @($Phase)
} else {
    $selectedPhases = @($selectedPhaseOrder | Where-Object { $_ -notin $SkipPhase })
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

    $stackName = "sentinel-monitoria-$phaseName-$EnvironmentName"
    $parameters = Get-PhaseParameterOverrides -PhaseName $phaseName
    $tags = @(
        "Project=$ProjectName",
        "Environment=$EnvironmentName",
        "DeploymentDay=$DeploymentDay",
        "ManagedBy=CloudFormation",
        "CostCenter=$ProjectName-$EnvironmentName"
    )

    $deployArguments = @(
        "cloudformation", "deploy",
        "--region", $Region,
        "--template-file", $templatePath,
        "--stack-name", $stackName,
        "--capabilities", "CAPABILITY_NAMED_IAM",
        "--no-fail-on-empty-changeset",
        "--parameter-overrides"
    ) + $parameters + @("--tags") + $tags

    if ($NoExecuteChangeSet) {
        $deployArguments += "--no-execute-changeset"
    }

    Write-Host "Deploying $phaseName -> $stackName" -ForegroundColor Cyan
    & aws @awsPrefix @deployArguments
    if ($LASTEXITCODE -ne 0) {
        throw "CloudFormation deployment failed for $phaseName."
    }

    if ($NoExecuteChangeSet) {
        Write-Host "Change Set created without execution for $phaseName. Stop after this phase for manual review." -ForegroundColor Yellow
        break
    }
}

Write-Host "CloudFormation phase command completed." -ForegroundColor Green
if ($StopServices) {
    Write-Host "ECS backend, telemetry worker, AI worker and notification worker were requested with DesiredCount=0. Run the migration before redeploying them with DesiredCount=1." -ForegroundColor Yellow
}