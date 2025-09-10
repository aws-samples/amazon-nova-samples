"""
Deployment configuration for Pipecat Voice AI Agent.

This module provides configuration management for different deployment environments.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeploymentConfig:
    """Configuration class for deployment settings."""

    # Environment settings
    environment: str = "development"
    log_level: str = "INFO"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 7860

    # AWS settings
    aws_region: str = "eu-north-1"

    # Daily.co settings
    daily_api_url: str = "https://api.daily.co/v1"

    # ECS specific settings
    max_bots_per_room: int = 1
    health_check_timeout: int = 30
    graceful_shutdown_timeout: int = 30

    # Resource limits and stability settings
    max_concurrent_rooms: int = 10
    bot_cleanup_interval: int = 300  # 5 minutes
    memory_cleanup_threshold: float = 0.8  # 80% memory usage

    # Health check settings
    health_check_interval: int = 30
    health_check_retries: int = 3

    # Performance tuning
    enable_request_pooling: bool = True
    max_request_pool_size: int = 100
    request_timeout: int = 30

    @classmethod
    def from_environment(cls) -> "DeploymentConfig":
        """Create configuration from environment variables."""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("FAST_API_PORT", "7860")),
            aws_region=os.getenv("AWS_REGION", "eu-north-1"),
            daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
            max_bots_per_room=int(os.getenv("MAX_BOTS_PER_ROOM", "1")),
            health_check_timeout=int(os.getenv("HEALTH_CHECK_TIMEOUT", "30")),
            graceful_shutdown_timeout=int(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT", "30")),
            max_concurrent_rooms=int(os.getenv("MAX_CONCURRENT_ROOMS", "10")),
            bot_cleanup_interval=int(os.getenv("BOT_CLEANUP_INTERVAL", "300")),
            memory_cleanup_threshold=float(
                os.getenv("MEMORY_CLEANUP_THRESHOLD", "0.8")
            ),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            health_check_retries=int(os.getenv("HEALTH_CHECK_RETRIES", "3")),
            enable_request_pooling=os.getenv("ENABLE_REQUEST_POOLING", "true").lower()
            == "true",
            max_request_pool_size=int(os.getenv("MAX_REQUEST_POOL_SIZE", "100")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global configuration instance
config = DeploymentConfig.from_environment()
