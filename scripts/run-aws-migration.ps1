[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [ValidateSet("staging", "production")]
    [string]$EnvironmentName = "staging",
    [string]$ProjectName = "SentinelMonitorIA",
    [string]$Profile = "",
    [string]$Cluster = "",
    [string]$TaskDefinition = "",
    [string]$Subnet1 = "",
    [string]$Subnet2 = "",
    [string]$SecurityGroup = ""
)

$ErrorActionPreference = "Stop"

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

$awsPrefix = @()
if ($Profile) {
    $awsPrefix += @("--profile", $Profile)
}

if (-not $Cluster) {
    $Cluster = "sentinel-monitoria-$EnvironmentName"
}
if (-not $TaskDefinition) {
    $TaskDefinition = "sentinel-monitoria-$EnvironmentName-backend"
}
if (-not $Subnet1) {
    $Subnet1 = Get-ExportValue -ExportName "$ProjectName-$EnvironmentName-PrivateSubnet1Id"
}
if (-not $Subnet2) {
    $Subnet2 = Get-ExportValue -ExportName "$ProjectName-$EnvironmentName-PrivateSubnet2Id"
}
if (-not $SecurityGroup) {
    $SecurityGroup = Get-ExportValue -ExportName "$ProjectName-$EnvironmentName-BackendSecurityGroupId"
}

$networkConfiguration = "awsvpcConfiguration={subnets=[$Subnet1,$Subnet2],securityGroups=[$SecurityGroup],assignPublicIp=DISABLED}"
$overrides = @{
    containerOverrides = @(
        @{
            name = "backend"
            command = @("alembic", "upgrade", "head")
        }
    )
} | ConvertTo-Json -Compress

Write-Host "Running Alembic migration task" -ForegroundColor Cyan
Write-Host "Cluster:        $Cluster"
Write-Host "Task definition: $TaskDefinition"
Write-Host "Subnets:        $Subnet1, $Subnet2"
Write-Host "Security group: $SecurityGroup"

$runArguments = @(
    "ecs", "run-task",
    "--region", $Region,
    "--cluster", $Cluster,
    "--task-definition", $TaskDefinition,
    "--launch-type", "FARGATE",
    "--platform-version", "LATEST",
    "--network-configuration", $networkConfiguration,
    "--overrides", $overrides,
    "--query", "tasks[0].taskArn",
    "--output", "text"
)
$taskArn = (& aws @awsPrefix @runArguments).Trim()
if ($LASTEXITCODE -ne 0 -or -not $taskArn -or $taskArn -eq "None") {
    throw "Unable to start the ECS migration task."
}

Write-Host "Migration task: $taskArn"
& aws @awsPrefix ecs wait tasks-stopped --region $Region --cluster $Cluster --tasks $taskArn
if ($LASTEXITCODE -ne 0) {
    throw "Timed out while waiting for the migration task."
}

$describeArguments = @(
    "ecs", "describe-tasks",
    "--region", $Region,
    "--cluster", $Cluster,
    "--tasks", $taskArn,
    "--output", "json"
)
$task = (& aws @awsPrefix @describeArguments | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to describe the migration task."
}

$container = @($task.tasks[0].containers | Where-Object { $_.name -eq "backend" }) | Select-Object -First 1
$exitCode = $container.exitCode
if ($exitCode -ne 0) {
    Write-Error "Alembic migration failed with exit code $exitCode."
    Write-Error "Stopped reason: $($task.tasks[0].stoppedReason)"
    Write-Error "Container reason: $($container.reason)"
    exit 1
}

Write-Host "Alembic migration completed successfully." -ForegroundColor Green