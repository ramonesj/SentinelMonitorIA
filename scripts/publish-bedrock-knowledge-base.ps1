[CmdletBinding()]
param(
    [string]$Region = "us-east-1",
    [string]$ProjectName = "SentinelMonitorIA",
    [ValidateSet("staging", "production")]
    [string]$EnvironmentName = "staging",
    [string]$Profile = "",
    [string]$CorpusPath = "",
    [string]$BucketName = "",
    [string]$KnowledgeBaseId = "",
    [string]$DataSourceId = "",
    [switch]$StartIngestion,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($CorpusPath)) {
    $CorpusPath = Join-Path $root "docs\knowledge-base"
}

if (-not $DryRun -and -not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI is not available."
}

if (-not (Test-Path -LiteralPath $CorpusPath -PathType Container)) {
    throw "Corpus directory not found: $CorpusPath"
}
$corpusRoot = (Resolve-Path -LiteralPath $CorpusPath).Path.TrimEnd('\', '/')

$awsPrefix = @()
if ($Profile) {
    $awsPrefix += @("--profile", $Profile)
}

function Invoke-AwsCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & aws @($awsPrefix + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed: aws $($Arguments -join ' ')"
    }
}

function Invoke-AwsJson {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $raw = & aws @($awsPrefix + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed: aws $($Arguments -join ' ')"
    }
    if (-not $raw) {
        throw "AWS CLI returned an empty JSON response: aws $($Arguments -join ' ')"
    }
    return (($raw -join [Environment]::NewLine) | ConvertFrom-Json)
}

function Get-CloudFormationExportValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExportName
    )

    $document = Invoke-AwsJson -Arguments @(
        "cloudformation", "list-exports", "--region", $Region, "--output", "json"
    )
    $matches = @($document.Exports | Where-Object { $_.Name -eq $ExportName })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one CloudFormation export '$ExportName'; found $($matches.Count). Deploy phase 19 first or pass the resource ID explicitly."
    }
    return [string]$matches[0].Value
}

if ($DryRun) {
    if ([string]::IsNullOrWhiteSpace($BucketName)) {
        $BucketName = "<source-bucket>"
    }
    if ([string]::IsNullOrWhiteSpace($KnowledgeBaseId)) {
        $KnowledgeBaseId = "<knowledge-base-id>"
    }
    if ([string]::IsNullOrWhiteSpace($DataSourceId)) {
        $DataSourceId = "<data-source-id>"
    }
} else {
    if ([string]::IsNullOrWhiteSpace($BucketName)) {
        $BucketName = Get-CloudFormationExportValue -ExportName "$ProjectName-$EnvironmentName-AiLogArchiveBucketName"
    }
    if ([string]::IsNullOrWhiteSpace($KnowledgeBaseId)) {
        $KnowledgeBaseId = Get-CloudFormationExportValue -ExportName "$ProjectName-$EnvironmentName-AiKnowledgeBaseId"
    }
    if ([string]::IsNullOrWhiteSpace($DataSourceId)) {
        $DataSourceId = Get-CloudFormationExportValue -ExportName "$ProjectName-$EnvironmentName-AiKnowledgeBaseDataSourceId"
    }
}

$allowedExtensions = @(".md", ".txt", ".json", ".html", ".htm")
$excludedPathPattern = '(?i)(^|[\\/])(\.env($|[.])|.*(secret|credential|access.?key|private.?key).*)'
$credentialPattern = '(?i)(bearer\s+[A-Za-z0-9._-]{20,}|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b|(password|secret|token|api[_ -]?key|access[_ -]?key|private[_ -]?key)\s*[:=]\s*[^\s,]+|\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b)'
$files = @(
    Get-ChildItem -LiteralPath $corpusRoot -File -Recurse |
        Where-Object {
            ($allowedExtensions -contains $_.Extension.ToLowerInvariant()) -and
            ($_.FullName -notmatch $excludedPathPattern)
        }
)

if ($files.Count -eq 0) {
    throw "No supported redacted documents found under $corpusRoot. Allowed extensions: $($allowedExtensions -join ', ')"
}

$potentialCredentialFiles = @()
foreach ($file in $files) {
    $content = [System.IO.File]::ReadAllText($file.FullName)
    if ($content -match $credentialPattern) {
        $potentialCredentialFiles += $file.FullName
    }
}
if ($potentialCredentialFiles.Count -gt 0) {
    throw "Potential credential-shaped content detected; redact these files before publishing: $($potentialCredentialFiles -join ', ')"
}

Write-Host "Publishing $($files.Count) document(s) to s3://$BucketName/knowledge-base/" -ForegroundColor Cyan
foreach ($file in $files) {
    $relativePath = ($file.FullName.Substring($corpusRoot.Length) -replace '^[\\/]+', '') -replace '\\', '/'
    $destination = "s3://$BucketName/knowledge-base/$relativePath"
    if ($DryRun) {
        Write-Host "[DRY RUN] $($file.FullName) -> $destination" -ForegroundColor Yellow
        continue
    }

    Invoke-AwsCommand -Arguments @(
        "s3", "cp", $file.FullName, $destination,
        "--region", $Region,
        "--only-show-errors"
    )
}

if ($StartIngestion) {
    if ($DryRun) {
        Write-Host "[DRY RUN] Would start ingestion for Knowledge Base $KnowledgeBaseId and data source $DataSourceId." -ForegroundColor Yellow
    } else {
        $job = Invoke-AwsJson -Arguments @(
            "bedrock-agent", "start-ingestion-job",
            "--knowledge-base-id", $KnowledgeBaseId,
            "--data-source-id", $DataSourceId,
            "--region", $Region,
            "--output", "json"
        )
        $jobId = $job.ingestionJob.ingestionJobId
        Write-Host "Started Bedrock ingestion job: $jobId" -ForegroundColor Green
    }
} else {
    if ($DryRun) {
        Write-Host "Dry run completed. No files were uploaded; use the real command after reviewing the corpus." -ForegroundColor Yellow
    } else {
        Write-Host "Upload completed. Start ingestion later with -StartIngestion after reviewing the uploaded corpus." -ForegroundColor Green
    }
}

Write-Host "KnowledgeBaseId: $KnowledgeBaseId" -ForegroundColor DarkGray
Write-Host "DataSourceId: $DataSourceId" -ForegroundColor DarkGray
Write-Host "Only the knowledge-base/ S3 prefix is included by the CloudFormation data source; Bedrock writes embeddings to the S3 Vectors index during ingestion." -ForegroundColor DarkGray
