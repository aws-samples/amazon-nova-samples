# CloudWatch Logs Insights Queries

This document contains useful CloudWatch Logs Insights queries for monitoring and troubleshooting the Pipecat ECS deployment.

## Basic Queries

### All Logs from Last Hour

```
fields @timestamp, level, message, service.name
| filter @timestamp > @timestamp - 1h
| sort @timestamp desc
```

### Error Logs Only

```
fields @timestamp, level, message, error.type, error.details
| filter level = "ERROR"
| sort @timestamp desc
```

### Performance Metrics

```
fields @timestamp, message, duration_ms, function
| filter ispresent(duration_ms)
| stats avg(duration_ms), max(duration_ms), min(duration_ms) by function
| sort avg desc
```

## Health Check Monitoring

### Health Check Failures

```
fields @timestamp, message, request_id, error
| filter message like /health check failed/
| sort @timestamp desc
```

### Health Check Response Times

```
fields @timestamp, duration_ms, request_id
| filter message like /health_check/
| stats avg(duration_ms), max(duration_ms), count() by bin(5m)
```

## Bot Lifecycle Monitoring

### Bot Process Events

```
fields @timestamp, lifecycle_event, bot_pid, room_url
| filter ispresent(lifecycle_event)
| sort @timestamp desc
```

### Bot Startup Failures

```
fields @timestamp, message, error.type, error.details, room_url
| filter error.type like /BOT_STARTUP_FAILED/
| sort @timestamp desc
```

### Active Bot Count Over Time

```
fields @timestamp, active_bots
| filter ispresent(active_bots)
| stats max(active_bots) by bin(5m)
| sort @timestamp desc
```

## Request Monitoring

### HTTP Request Patterns

```
fields @timestamp, http_method, http_path, request_id, client_ip
| filter ispresent(http_method)
| stats count() by http_method, http_path
| sort count desc
```

### Slow Requests

```
fields @timestamp, message, duration_ms, request_id, http_path
| filter duration_ms > 1000
| sort duration_ms desc
```

### Request Volume by Endpoint

```
fields @timestamp, http_path
| filter ispresent(http_path)
| stats count() by http_path, bin(5m)
| sort @timestamp desc
```

## Error Analysis

### Error Types and Frequency

```
fields @timestamp, error.type, error.details
| filter ispresent(error.type)
| stats count() by error.type
| sort count desc
```

### Room Creation Failures

```
fields @timestamp, message, error.details, request_id
| filter error.type like /ROOM_CREATION_FAILED/ or error.type like /TOKEN_GENERATION_FAILED/
| sort @timestamp desc
```

### AWS Service Errors

```
fields @timestamp, message, error.type, error.details
| filter error.details like /AWS/ or error.details like /Bedrock/ or error.details like /SecretManager/
| sort @timestamp desc
```

## Performance Analysis

### Function Performance Summary

```
fields @timestamp, function, duration_ms
| filter ispresent(duration_ms)
| stats avg(duration_ms) as avg_duration, max(duration_ms) as max_duration, count() as call_count by function
| sort avg_duration desc
```

### Response Time Percentiles

```
fields @timestamp, duration_ms
| filter ispresent(duration_ms)
| stats pct(duration_ms, 50) as p50, pct(duration_ms, 90) as p90, pct(duration_ms, 95) as p95, pct(duration_ms, 99) as p99 by bin(5m)
| sort @timestamp desc
```

## Service Health Monitoring

### Service Startup Events

```
fields @timestamp, message
| filter message like /Starting Pipecat Voice AI Agent server/
| sort @timestamp desc
```

### Cleanup Events

```
fields @timestamp, message, terminated_count, killed_count, error_count
| filter message like /Cleanup completed/
| sort @timestamp desc
```

### Environment Configuration Issues

```
fields @timestamp, message, missing_vars
| filter ispresent(missing_vars)
| sort @timestamp desc
```

## Daily.co Integration Monitoring

### Daily Room Operations

```
fields @timestamp, message, room_url, request_id
| filter message like /Daily room/ or message like /Room created/
| sort @timestamp desc
```

### Daily API Errors

```
fields @timestamp, message, error.details
| filter message like /Daily/ and level = "ERROR"
| sort @timestamp desc
```

## Custom Metrics Extraction

### Extract Bot Metrics for CloudWatch Custom Metrics

```
fields @timestamp, active_bots, total_bot_processes
| filter ispresent(active_bots)
| stats max(active_bots) as max_active_bots, max(total_bot_processes) as max_total_processes by bin(1m)
```

### Extract Response Time Metrics

```
fields @timestamp, duration_ms, function
| filter ispresent(duration_ms)
| stats avg(duration_ms) as avg_response_time by function, bin(1m)
```

## Troubleshooting Queries

### Find Correlated Errors by Request ID

```
fields @timestamp, message, request_id, level
| filter request_id = "YOUR_REQUEST_ID_HERE"
| sort @timestamp asc
```

### Find All Events for a Specific Bot

```
fields @timestamp, message, bot_pid, lifecycle_event
| filter bot_pid = YOUR_BOT_PID_HERE
| sort @timestamp asc
```

### Memory and Resource Issues

```
fields @timestamp, message
| filter message like /memory/ or message like /resource/ or message like /limit/
| sort @timestamp desc
```

## Usage Instructions

1. Go to CloudWatch Logs Insights in the AWS Console
2. Select the log group: `/ecs/pipecat-voice-agent-{environment}/application`
3. Copy and paste any of the above queries
4. Adjust the time range as needed
5. Click "Run query"

## Creating CloudWatch Alarms from Queries

You can create CloudWatch alarms based on these queries by:

1. Running the query in CloudWatch Logs Insights
2. Clicking "Add to dashboard" or "Create alarm"
3. Setting appropriate thresholds and notification targets

## Automated Monitoring

The `monitoring.py` script can be used to continuously monitor service health and automatically log issues to CloudWatch.

```bash
# Run continuous monitoring
python monitoring.py --url http://your-alb-dns-name --interval 30

# Single health check
python monitoring.py --url http://your-alb-dns-name --single-check
```
