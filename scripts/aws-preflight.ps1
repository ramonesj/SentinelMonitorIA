[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [string]$ExpectedAccountId = "952763303883",
    [string]$ExpectedUserArn = "arn:aws:iam::952763303883:user/ramonesj",
    [string]$Profile = "",
    [switch]$AllowDifferentPrincipal
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command is not available: $Name"
    }
}

function Invoke-AwsJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $awsArguments = @()
    if ($Profile) {
        $awsArguments += @("--profile", $Profile)
    }
    $awsArguments += $Arguments
    $result = & aws @awsArguments --output json
    if ($LASTEXITCODE -ne 0) {
        throw "AWS command failed: aws $($awsArguments -join ' ')"
    }
    return ($result | ConvertFrom-Json)
}

Require-Command -Name "aws"
Require-Command -Name "docker"
Require-Command -Name "git"

if ($Region -ne "us-east-1") {
    throw "The current modular templates are pinned to us-east-1; received region '$Region'."
}

Write-Host "SentinelMonitorIA AWS preflight" -ForegroundColor Cyan
Write-Host "Region:  $Region"
Write-Host "Profile: $(if ($Profile) { $Profile } else { 'AWS CLI default credential chain' })"
Write-Host ""

$identity = Invoke-AwsJson -Arguments @("sts", "get-caller-identity")
Write-Host "Account: $($identity.Account)"
Write-Host "Caller:  $($identity.Arn)"

if ($identity.Account -ne $ExpectedAccountId) {
    throw "Unexpected AWS account. Expected $ExpectedAccountId, received $($identity.Account)."
}

if (-not $AllowDifferentPrincipal -and $identity.Arn -ne $ExpectedUserArn) {
    throw "Unexpected caller. Expected $ExpectedUserArn, received $($identity.Arn). Use -AllowDifferentPrincipal only when intentionally using another deployment role."
}

$availabilityZones = Invoke-AwsJson -Arguments @(
    "ec2",
    "describe-availability-zones",
    "--region",
    $Region,
    "--filters",
    "Name=state,Values=available"
)
$zoneNames = @($availabilityZones.AvailabilityZones | ForEach-Object { $_.ZoneName })
$requiredZones = @("us-east-1a", "us-east-1b")
$missingZones = @($requiredZones | Where-Object { $_ -notin $zoneNames })
if ($missingZones.Count -gt 0) {
    throw "Required availability zones are not available: $($missingZones -join ', ')"
}
Write-Host "Availability zones: us-east-1a, us-east-1b available" -ForegroundColor Green

$userName = ($ExpectedUserArn -split "/")[-1]
$attachedPolicies = Invoke-AwsJson -Arguments @(
    "iam",
    "list-attached-user-policies",
    "--user-name",
    $userName
)
$hasAdministratorAccess = @($attachedPolicies.AttachedPolicies | Where-Object { $_.PolicyArn -eq "arn:aws:iam::aws:policy/AdministratorAccess" }).Count -gt 0
if ($hasAdministratorAccess) {
    Write-Host "AdministratorAccess: directly attached to $userName" -ForegroundColor Green
} else {
    Write-Warning "AdministratorAccess is not directly attached to $userName. It may be inherited from a group or replaced by another deployment role."
}

Write-Host ""
Write-Host "Preflight passed. No credentials were displayed." -ForegroundColor Green
Write-Host "Next checks remain: CloudFormation validation, Change Sets, quotas/budget review and deployment-specific smoke tests."