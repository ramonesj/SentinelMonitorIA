#!/bin/bash
# LocalStack initialization script
# Creates SQS queues and S3 buckets for development

echo "Initializing LocalStack for SentinelMonitorIA..."

# Wait for LocalStack to be ready
until awslocal sqs list-queues --endpoint-url=http://localhost:4566 > /dev/null 2>&1; do
  echo "Waiting for LocalStack to be ready..."
  sleep 2
done

# Create SQS queues
echo "Creating SQS queues..."

# Telemetry queue
awslocal sqs create-queue --queue-name sentinel-telemetry --endpoint-url=http://localhost:4566
echo "Created queue: sentinel-telemetry"

# Alerts queue
awslocal sqs create-queue --queue-name sentinel-alerts --endpoint-url=http://localhost:4566
echo "Created queue: sentinel-alerts"

# Dead letter queue
awslocal sqs create-queue --queue-name sentinel-dlq --endpoint-url=http://localhost:4566
echo "Created queue: sentinel-dlq"

# Create S3 buckets
echo "Creating S3 buckets..."

# Telemetry bucket
awslocal s3 mb s3://sentinelmonitoria-telemetry --endpoint-url=http://localhost:4566
echo "Created bucket: sentinelmonitoria-telemetry"

# Logs bucket
awslocal s3 mb s3://sentinelmonitoria-logs --endpoint-url=http://localhost:4566
echo "Created bucket: sentinelmonitoria-logs"

# Backups bucket
awslocal s3 mb s3://sentinelmonitoria-backups --endpoint-url=http://localhost:4566
echo "Created bucket: sentinelmonitoria-backups"

echo "LocalStack initialization completed!"