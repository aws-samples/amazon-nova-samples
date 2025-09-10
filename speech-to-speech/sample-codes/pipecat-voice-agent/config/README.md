# Configuration

This directory contains application configuration files.

## Files

- `deployment_config.py` - Main deployment configuration including environment settings, resource limits, and AWS service configurations

## Usage

The deployment configuration is imported by the main application:

```python
from config.deployment_config import config
```

## Configuration Structure

The deployment config typically includes:

- Environment-specific settings (development/production)
- Resource limits and constraints
- AWS service configurations
- Application-specific parameters

## Notes

- Configuration files should not contain sensitive information like API keys
- Use environment variables for secrets and sensitive data
- Different environments can have different configuration values
