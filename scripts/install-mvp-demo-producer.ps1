[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,
    [string]$ApiEndpoint = "http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com",
    [string]$InstanceId = "i-0c56b84145cd08d22",
    [string]$Region = "us-east-1",
    [string]$Profile = "sentinel-monitoria"
)

$ErrorActionPreference = "Stop"
if (-not $ApiKey.Trim()) {
    throw "ApiKey cannot be empty."
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    throw "AWS CLI is not available."
}

$producerPath = Join-Path $PSScriptRoot "mvp-demo-producer.py"
if (-not (Test-Path $producerPath)) {
    throw "Producer script not found: $producerPath"
}

function ConvertTo-GzipBase64 {
    param([Parameter(Mandatory = $true)][string]$Path)

    $inputBytes = [IO.File]::ReadAllBytes($Path)
    $memoryStream = New-Object IO.MemoryStream
    try {
        $gzipStream = New-Object IO.Compression.GzipStream($memoryStream, [IO.Compression.CompressionMode]::Compress)
        try {
            $gzipStream.Write($inputBytes, 0, $inputBytes.Length)
        } finally {
            $gzipStream.Dispose()
        }
        return [Convert]::ToBase64String($memoryStream.ToArray())
    } finally {
        $memoryStream.Dispose()
    }
}

function ConvertTo-Base64 {
    param([Parameter(Mandatory = $true)][string]$Text)
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Text))
}

function Invoke-RemoteSsm {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Commands
    )

    $request = [ordered]@{
        DocumentName = "AWS-RunShellScript"
        InstanceIds = @($InstanceId)
        Parameters = @{ commands = $Commands }
        Comment = $Name
        TimeoutSeconds = 120
    }
    $requestJson = $request | ConvertTo-Json -Depth 6 -Compress
    $inputPath = [IO.Path]::GetTempFileName()
    $commandId = $null
    try {
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($inputPath, $requestJson, $utf8NoBom)
        $commandId = (& aws ssm send-command `
            --cli-input-json "file://$inputPath" `
            --region $Region `
            --profile $Profile `
            --query "Command.CommandId" `
            --output text).Trim()
    } finally {
        Remove-Item $inputPath -Force -ErrorAction SilentlyContinue
    }

    if ($LASTEXITCODE -ne 0 -or -not $commandId -or $commandId -eq "None") {
        throw "SSM send-command failed for $Name"
    }

    $status = "Pending"
    $invocation = $null
    do {
        Start-Sleep -Seconds 2
        $invocation = aws ssm get-command-invocation `
            --command-id $commandId `
            --instance-id $InstanceId `
            --region $Region `
            --profile $Profile `
            --query "{Status:Status,ResponseCode:ResponseCode,StandardOutputContent:StandardOutputContent}" `
            --output json | ConvertFrom-Json
        $status = [string]$invocation.Status
    } while ($status -in @("Pending", "InProgress", "Delayed"))

    Write-Host "$Name status=$status command_id=$commandId response_code=$($invocation.ResponseCode)" -ForegroundColor Cyan
    if ($invocation.StandardOutputContent) {
        Write-Host $invocation.StandardOutputContent
    }
    if ($status -ne "Success") {
        throw "SSM command failed for $Name with status $status"
    }
}

$producerB64 = ConvertTo-GzipBase64 -Path $producerPath
$envContent = @"
SENTINEL_API_ENDPOINT=$ApiEndpoint
SENTINEL_API_KEY=$ApiKey
SENTINEL_AGENT_ID=ec2-test-redes-synthetic
SENTINEL_HOSTNAME=test-redes
SENTINEL_AGENT_VERSION=mvp-demo-producer/1.0
SENTINEL_LOG_LEVEL=INFO
"@
$envB64 = ConvertTo-Base64 -Text ($envContent.Trim() + "`n")

$producerUnit = @'
[Unit]
Description=SentinelMonitorIA controlled synthetic telemetry producer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=sentinel-demo
Group=sentinel-demo
WorkingDirectory=/opt/sentinel-mvp
EnvironmentFile=/etc/sentinel-mvp/producer.env
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -u /opt/sentinel-mvp/mvp-demo-producer.py
Restart=always
RestartSec=30
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
ProtectKernelLogs=yes
RestrictSUIDSGID=yes
LockPersonality=yes
MemoryMax=128M
CPUQuota=5%
TasksMax=32
LimitNOFILE=1024
UMask=0077
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sentinel-mvp-demo-producer

[Install]
WantedBy=multi-user.target
'@
$producerUnitB64 = ConvertTo-Base64 -Text $producerUnit

$smokeUnit = @'
[Unit]
Description=SentinelMonitorIA synthetic incident smoke test
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=sentinel-demo
Group=sentinel-demo
WorkingDirectory=/opt/sentinel-mvp
EnvironmentFile=/etc/sentinel-mvp/producer.env
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -u /opt/sentinel-mvp/mvp-demo-producer.py --once --mode incident
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
ProtectKernelLogs=yes
RestrictSUIDSGID=yes
LockPersonality=yes
MemoryMax=128M
CPUQuota=5%
TasksMax=32
LimitNOFILE=1024
UMask=0077
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sentinel-mvp-demo-smoke
'@
$smokeUnitB64 = ConvertTo-Base64 -Text $smokeUnit

Invoke-RemoteSsm -Name "Install synthetic producer files" -Commands @(
    "set -eu",
    "if ! getent passwd sentinel-demo >/dev/null 2>&1; then useradd --system --home-dir /opt/sentinel-mvp --shell /sbin/nologin sentinel-demo; fi",
    "install -d -o sentinel-demo -g sentinel-demo -m 0750 /opt/sentinel-mvp",
    "printf '%s' '$producerB64' | base64 --decode | gzip --decompress | tee /opt/sentinel-mvp/mvp-demo-producer.py >/dev/null",
    "chown sentinel-demo:sentinel-demo /opt/sentinel-mvp/mvp-demo-producer.py",
    "chmod 0750 /opt/sentinel-mvp/mvp-demo-producer.py",
    "python3 --version",
    "sha256sum /opt/sentinel-mvp/mvp-demo-producer.py"
)

Invoke-RemoteSsm -Name "Configure synthetic producer service" -Commands @(
    "set -eu",
    "install -d -o root -g root -m 0750 /etc/sentinel-mvp",
    "printf '%s' '$envB64' | base64 --decode | tee /etc/sentinel-mvp/producer.env >/dev/null",
    "chown root:root /etc/sentinel-mvp/producer.env",
    "chmod 0600 /etc/sentinel-mvp/producer.env",
    "printf '%s' '$producerUnitB64' | base64 --decode | tee /etc/systemd/system/sentinel-mvp-demo-producer.service >/dev/null",
    "printf '%s' '$smokeUnitB64' | base64 --decode | tee /etc/systemd/system/sentinel-mvp-demo-smoke.service >/dev/null",
    "chmod 0644 /etc/systemd/system/sentinel-mvp-demo-producer.service /etc/systemd/system/sentinel-mvp-demo-smoke.service",
    "systemctl daemon-reload",
    "systemctl enable sentinel-mvp-demo-producer.service",
    "systemctl restart sentinel-mvp-demo-producer.service",
    "systemctl is-enabled sentinel-mvp-demo-producer.service",
    "systemctl is-active sentinel-mvp-demo-producer.service",
    "stat -c 'env_mode=%a env_owner=%U:%G' /etc/sentinel-mvp/producer.env"
)

Invoke-RemoteSsm -Name "Run synthetic incident smoke test" -Commands @(
    "set -eu",
    "systemctl start sentinel-mvp-demo-smoke.service",
    "systemctl show sentinel-mvp-demo-smoke.service --property=ExecMainCode --property=ExecMainStatus --value",
    "journalctl -u sentinel-mvp-demo-smoke.service -n 20 --no-pager -o cat",
    "systemctl is-active sentinel-mvp-demo-producer.service",
    "journalctl -u sentinel-mvp-demo-producer.service -n 20 --no-pager -o cat",
    "rm -f /etc/systemd/system/sentinel-mvp-demo-smoke.service",
    "systemctl daemon-reload"
)

Write-Host "Synthetic producer installed on $InstanceId; API key was not printed or persisted locally." -ForegroundColor Green
