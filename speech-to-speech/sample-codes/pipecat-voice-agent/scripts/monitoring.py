#!/usr/bin/env python3
"""
Monitoring utilities for Pipecat ECS deployment.

This module provides utilities for monitoring the health and performance
of the Pipecat voice agent service running in ECS.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from logger_config import logger, log_performance, log_error


class ServiceMonitor:
    """Monitor for Pipecat service health and performance."""

    def __init__(self, service_url: str, check_interval: int = 30):
        """Initialize the service monitor.

        Args:
            service_url: Base URL of the service to monitor
            check_interval: Interval between health checks in seconds
        """
        self.service_url = service_url.rstrip("/")
        self.check_interval = check_interval
        self.session: Optional[aiohttp.ClientSession] = None
        self.health_history: List[Dict] = []
        self.performance_history: List[Dict] = []

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def check_health(self) -> Dict:
        """Perform a health check on the service.

        Returns:
            Dict containing health check results
        """
        start_time = time.time()

        try:
            async with self.session.get(
                f"{self.service_url}/health", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                duration_ms = (time.time() - start_time) * 1000

                health_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status_code": response.status,
                    "response_time_ms": duration_ms,
                    "healthy": response.status == 200,
                }

                if response.status == 200:
                    try:
                        body = await response.json()
                        health_data["details"] = body
                        health_data["service_status"] = body.get("status", "unknown")
                        health_data["active_bots"] = body.get("checks", {}).get(
                            "active_bots", 0
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse health response: {e}")
                        health_data["parse_error"] = str(e)
                else:
                    health_data["error"] = f"HTTP {response.status}"
                    try:
                        error_body = await response.text()
                        health_data["error_details"] = error_body
                    except:
                        pass

                self.health_history.append(health_data)

                # Keep only last 100 health checks
                if len(self.health_history) > 100:
                    self.health_history = self.health_history[-100:]

                if health_data["healthy"]:
                    logger.bind(
                        response_time_ms=duration_ms,
                        active_bots=health_data.get("active_bots", 0),
                    ).info("Health check passed")
                else:
                    logger.bind(
                        status_code=response.status,
                        response_time_ms=duration_ms,
                        error=health_data.get("error"),
                    ).warning("Health check failed")

                return health_data

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            health_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "healthy": False,
                "error": "timeout",
                "response_time_ms": duration_ms,
            }
            self.health_history.append(health_data)
            log_error(
                Exception("Health check timeout"),
                "HEALTH_CHECK_TIMEOUT",
                response_time_ms=duration_ms,
            )
            return health_data

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            health_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "healthy": False,
                "error": str(e),
                "response_time_ms": duration_ms,
            }
            self.health_history.append(health_data)
            log_error(e, "HEALTH_CHECK_ERROR", response_time_ms=duration_ms)
            return health_data

    async def check_readiness(self) -> Dict:
        """Perform a readiness check on the service.

        Returns:
            Dict containing readiness check results
        """
        start_time = time.time()

        try:
            async with self.session.get(
                f"{self.service_url}/ready", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                duration_ms = (time.time() - start_time) * 1000

                readiness_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "status_code": response.status,
                    "response_time_ms": duration_ms,
                    "ready": response.status == 200,
                }

                if response.status == 200:
                    try:
                        body = await response.json()
                        readiness_data["details"] = body
                    except Exception as e:
                        logger.warning(f"Failed to parse readiness response: {e}")

                return readiness_data

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "ready": False,
                "error": str(e),
                "response_time_ms": duration_ms,
            }

    def get_health_summary(self, minutes: int = 10) -> Dict:
        """Get a summary of health checks over the specified time period.

        Args:
            minutes: Number of minutes to look back

        Returns:
            Dict containing health summary
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        recent_checks = [
            check
            for check in self.health_history
            if datetime.fromisoformat(check["timestamp"]) > cutoff_time
        ]

        if not recent_checks:
            return {
                "period_minutes": minutes,
                "total_checks": 0,
                "healthy_checks": 0,
                "unhealthy_checks": 0,
                "success_rate": 0.0,
                "avg_response_time_ms": 0.0,
            }

        healthy_checks = sum(
            1 for check in recent_checks if check.get("healthy", False)
        )
        total_checks = len(recent_checks)

        response_times = [
            check["response_time_ms"]
            for check in recent_checks
            if "response_time_ms" in check
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        return {
            "period_minutes": minutes,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "unhealthy_checks": total_checks - healthy_checks,
            "success_rate": (
                (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
            ),
            "avg_response_time_ms": avg_response_time,
            "min_response_time_ms": min(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
        }

    async def run_continuous_monitoring(self):
        """Run continuous monitoring of the service."""
        logger.info(f"Starting continuous monitoring of {self.service_url}")

        while True:
            try:
                # Perform health check
                health_result = await self.check_health()

                # Log summary every 10 checks
                if len(self.health_history) % 10 == 0:
                    summary = self.get_health_summary(10)
                    logger.bind(
                        success_rate=summary["success_rate"],
                        avg_response_time_ms=summary["avg_response_time_ms"],
                        total_checks=summary["total_checks"],
                    ).info("Health monitoring summary (last 10 minutes)")

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                log_error(e, "MONITORING_ERROR")
                await asyncio.sleep(self.check_interval)


async def main():
    """Main function for running the monitoring script."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Monitor Pipecat service health")
    parser.add_argument(
        "--url",
        default=os.getenv("SERVICE_URL", "http://localhost:7860"),
        help="Service URL to monitor",
    )
    parser.add_argument(
        "--interval", type=int, default=30, help="Check interval in seconds"
    )
    parser.add_argument(
        "--single-check",
        action="store_true",
        help="Perform a single health check and exit",
    )

    args = parser.parse_args()

    async with ServiceMonitor(args.url, args.interval) as monitor:
        if args.single_check:
            # Single health check
            health = await monitor.check_health()
            readiness = await monitor.check_readiness()

            print(
                json.dumps(
                    {
                        "health": health,
                        "readiness": readiness,
                    },
                    indent=2,
                )
            )
        else:
            # Continuous monitoring
            await monitor.run_continuous_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
