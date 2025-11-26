# Observability in Amazon Nova Act

## Overview
Observability is crucial for understanding, debugging, and optimizing automation workflows. Nova Act provides built-in logging, tracing, and session recording capabilities to monitor automations and diagnose issues.

## Learning Objectives
- Understand the importance of monitoring automation workflows
- Access and interpret Nova Act execution logs
- Use built-in tracing functionality to visualize workflow execution
- Record and analyze session videos
- Apply debugging techniques to resolve issues
- Integrate custom logging with Nova Act

## Prerequisites
**⚠️ Complete the centralized setup first!**
- Complete setup in `../00-setup/`
- Completion of previous tutorials (01-03)
- Basic understanding of Python logging

## Why Observability Matters
- **Debugging** - Understand why automations fail
- **Performance Optimization** - Identify bottlenecks
- **Monitoring** - Ensure automations run as expected
- **Compliance** - Maintain audit trails
- **Learning** - Understand AI agent decision-making
- **Troubleshooting** - Quickly diagnose issues

## Nova Act Observability Features

### 1. Automatic Logging
Nova Act automatically logs all actions at INFO level or above to console.

### 2. Debug Logging
Enable detailed debug information:
```bash
export NOVA_ACT_LOG_LEVEL=10  # DEBUG level
```

### 3. HTML Trace Files
Self-contained HTML files with:
- Screenshots of each step
- Actions taken by Nova Act
- AI decision-making process
- Timing information
- Error details

### 4. Session Video Recording
Record entire browser sessions as WebM videos for visual debugging.

### 5. S3 Integration
Store session data in Amazon S3 for long-term retention with automatic upload.

## Tutorial Script

### Observability (`1_observability.py`)
Comprehensive demonstration of all observability features including:
- Basic and debug logging
- HTML trace generation
- Video recording
- Error debugging techniques
- Custom logging integration

## Debugging Workflow
1. **Enable Debug Logging** - Set `NOVA_ACT_LOG_LEVEL=10`
2. **Review Console Logs** - Look for errors and unexpected behavior
3. **Examine Trace Files** - View HTML traces in browser
4. **Watch Session Video** - Identify UI timing issues
5. **Iterate and Fix** - Adjust based on findings

## Best Practices

### Production Deployments
- Always set `logs_directory` for persistent storage
- Use appropriate log levels (INFO for production, DEBUG for development)
- Implement log rotation for large trace files
- Store logs securely with S3 integration

### Development
- Enable debug logging for detailed troubleshooting
- Record videos for complex workflows
- Review trace files regularly to understand Nova Act behavior
- Add custom logging for workflow milestones

### Monitoring
- Track success/failure rates and execution times
- Set up alerts for failed automations
- Regular review of error patterns
- Optimize workflows based on trace analysis

## Common Debugging Scenarios

### Action Fails Silently
- Enable debug logging
- Review trace screenshots
- Check element detection
- Verify page load completion

### Intermittent Failures
- Record video to see timing issues
- Add explicit waits
- Check for dynamic content
- Review network timing

### Unexpected Behavior
- Review trace screenshots
- Check prompt clarity
- Verify page structure
- Add more specific instructions

## Quick Start
```bash
# Activate environment
source ../00-setup/venv/bin/activate

# Run observability tutorial
python 1_observability.py
```

## Log Levels
- **DEBUG (10)** - Development, detailed troubleshooting
- **INFO (20)** - Production, general monitoring (default)
- **WARNING (30)** - Potential issues
- **ERROR (40)** - Failures, exceptions
- **CRITICAL (50)** - System failures

## Next Steps
- Review generated trace files and videos
- Practice debugging with intentional failures
- Integrate observability into production workflows
- Set up S3 storage for long-term retention
- Implement monitoring and alerting
