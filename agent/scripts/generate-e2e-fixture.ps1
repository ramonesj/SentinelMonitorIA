[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\fixtures\e2e-telemetry.jsonl")
)

$ErrorActionPreference = "Stop"

$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = Split-Path -Parent $resolvedOutputPath
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

$runId = [Guid]::NewGuid().ToString("N")
$timestamp = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

$records = @(
    [ordered]@{
        kind = "metric"
        batch_id = "e2e_${runId}_metric"
        timestamp = $timestamp
        name = "e2e.vector.cpu.usage"
        value = 37.5
        metric_type = "gauge"
        labels = [ordered]@{ agent = "sentinel-e2e-vector-agent"; fixture = "jsonl" }
        unit = "percent"
        description = "Deterministic Vector E2E metric"
    },
    [ordered]@{
        kind = "log"
        batch_id = "e2e_${runId}_log"
        timestamp = $timestamp
        message = "SentinelMonitorIA Vector E2E log received"
        level = "info"
        service = "sentinel-agent"
        component = "vector-e2e"
        log_metadata = [ordered]@{ run_id = $runId; fixture = "jsonl" }
        parsed_fields = [ordered]@{ test_case = "telemetry-ingestion"; expected = "processed" }
    },
    [ordered]@{
        kind = "event"
        batch_id = "e2e_${runId}_event"
        timestamp = $timestamp
        event_type = "agent.e2e.completed"
        source = "sentinel-agent"
        summary = "SentinelMonitorIA Vector E2E event received"
        severity = "info"
        details = [ordered]@{ run_id = $runId; fixture = "jsonl"; expected = "processed" }
        correlation_id = "e2e-$runId"
    }
)

$lines = $records | ForEach-Object {
    $_ | ConvertTo-Json -Depth 10 -Compress
}

[System.IO.File]::WriteAllLines($resolvedOutputPath, $lines, $utf8NoBom)
Write-Output "Generated $($lines.Count) telemetry records at $resolvedOutputPath"
