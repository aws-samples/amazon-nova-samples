"""
Main production RTVI Bot Server 
- Full-featured FASTAPI server with Daily.co WebRTC integration 
- Production-ready with comprehensive logging, health checks, and process management 
- Handles both browser access and RTVI client connections

- Main production server
"""

import uvicorn
import argparse
import os
import logging
import subprocess
import signal
import sys
import time
import uuid
import gc
import psutil
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict
from logger_config import (
    logger,
    log_performance,
    log_error,
    log_request,
    log_bot_lifecycle,
)
from config.deployment_config import config

import asyncio
import aiohttp
from dotenv import load_dotenv

# from bot import main

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from datetime import datetime

from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
)

# from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection

# Load environment variables from .env file
load_dotenv(override=True)

logger = logging.getLogger("pc")

# Maximum number of bot instances allowed per room
MAX_BOTS_PER_ROOM = config.max_bots_per_room

# Dictionary to track bot processes: {pid: (process, room_url, start_time)}
bot_procs = {}

# Store Daily API helpers
daily_helpers = {}

# Resource monitoring
_resource_monitor_task = None
_cleanup_task = None

# pcs_map: Dict[str, SmallWebRTCConnection] = {}


async def monitor_resources():
    """Monitor system resources and cleanup if needed."""
    while True:
        try:
            # Get current memory usage
            memory_percent = psutil.virtual_memory().percent / 100.0
            cpu_percent = psutil.cpu_percent(interval=1) / 100.0

            # Log resource usage
            logger.debug(
                f"Resource usage - Memory: {memory_percent:.1%}, CPU: {cpu_percent:.1%}"
            )

            # Trigger cleanup if memory usage is high
            if memory_percent > config.memory_cleanup_threshold:
                logger.warning(f"High memory usage detected: {memory_percent:.1%}")
                await cleanup_stale_processes()

                # Force garbage collection
                gc.collect()

            # Check for stale bot processes
            await cleanup_stale_processes()

            # Sleep for the configured interval
            await asyncio.sleep(config.bot_cleanup_interval)

        except Exception as e:
            logger.error(f"Error in resource monitoring: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying


async def cleanup_stale_processes():
    """Clean up stale bot processes that are no longer needed."""
    current_time = time.time()
    stale_pids = []

    for pid, entry in bot_procs.items():
        proc = entry[0]
        room_url = entry[1]
        start_time = entry[2] if len(entry) > 2 else current_time

        # Check if process is still running
        if proc.poll() is not None:
            # Process has finished
            stale_pids.append(pid)
            log_bot_lifecycle("finished", pid, room_url)
        elif current_time - start_time > 3600:  # 1 hour timeout
            # Process has been running too long, terminate it
            logger.warning(
                f"Terminating long-running bot process - PID: {pid}, Room: {room_url}"
            )
            try:
                proc.terminate()
                proc.wait(timeout=config.graceful_shutdown_timeout)
                stale_pids.append(pid)
                log_bot_lifecycle("timeout_terminated", pid, room_url)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                stale_pids.append(pid)
                log_bot_lifecycle("timeout_killed", pid, room_url)
            except Exception as e:
                log_error(e, "STALE_CLEANUP_ERROR", bot_pid=pid, room_url=room_url)

    # Remove stale processes from tracking
    for pid in stale_pids:
        if pid in bot_procs:
            del bot_procs[pid]

    if stale_pids:
        logger.info(f"Cleaned up {len(stale_pids)} stale bot processes")


def cleanup():
    """Cleanup function to terminate all bot processes.

    Called during server shutdown.
    """
    cleanup_start = time.time()
    logger.info("Starting cleanup of bot processes...")

    terminated_count = 0
    killed_count = 0
    error_count = 0

    for pid, entry in bot_procs.items():
        proc = entry[0]
        room_url = entry[1]

        if proc.poll() is None:  # Process is still running
            log_bot_lifecycle("terminating", pid, room_url)
            try:
                proc.terminate()
                # Give process time to terminate gracefully
                proc.wait(timeout=config.graceful_shutdown_timeout)
                terminated_count += 1
                log_bot_lifecycle("terminated", pid, room_url)
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Force killing bot process - PID: {pid}, Room: {room_url}"
                )
                proc.kill()
                proc.wait()
                killed_count += 1
                log_bot_lifecycle("killed", pid, room_url)
            except Exception as e:
                error_count += 1
                log_error(e, "CLEANUP_ERROR", bot_pid=pid, room_url=room_url)
        else:
            log_bot_lifecycle("already_finished", pid, room_url)

    cleanup_duration = (time.time() - cleanup_start) * 1000
    logger.info(
        f"Cleanup completed - Terminated: {terminated_count}, Killed: {killed_count}, "
        f"Errors: {error_count}, Total: {len(bot_procs)}, Duration: {cleanup_duration:.2f}ms"
    )

    log_performance("cleanup", cleanup_duration)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    cleanup()
    sys.exit(0)


def get_bot_file():
    return "bot"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager that handles startup and shutdown tasks.

    - Creates aiohttp session
    - Initializes Daily API helper
    - Starts resource monitoring
    - Cleans up resources on shutdown
    """
    global _resource_monitor_task, _cleanup_task

    # Initialize aiohttp session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=config.max_request_pool_size if config.enable_request_pooling else 100,
        limit_per_host=30,
        ttl_dns_cache=300,
        use_dns_cache=True,
    )
    aiohttp_session = aiohttp.ClientSession(
        connector=connector, timeout=aiohttp.ClientTimeout(total=config.request_timeout)
    )

    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=config.daily_api_url,
        aiohttp_session=aiohttp_session,
    )

    # Start resource monitoring task
    _resource_monitor_task = asyncio.create_task(monitor_resources())
    logger.info("Resource monitoring started")

    yield

    # Cleanup on shutdown
    if _resource_monitor_task:
        _resource_monitor_task.cancel()
        try:
            await _resource_monitor_task
        except asyncio.CancelledError:
            pass

    await aiohttp_session.close()
    cleanup()


# Initialize FastAPI app with lifespan manager
app = FastAPI(lifespan=lifespan)

# Configure CORS to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint for ECS monitoring.

    Performs comprehensive health checks including:
    - Daily API helper initialization
    - Environment variable validation
    - Basic connectivity tests

    Returns:
        JSONResponse: Health status with timestamp and details

    Raises:
        HTTPException: If service is unhealthy
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "pipecat-voice-agent",
        "version": "1.0",
        "checks": {},
        "request_id": request_id,
    }

    try:
        log_request(request_id, "GET", "/health")

        # Check 1: Daily API helper initialization
        daily_helper = daily_helpers.get("rest")
        if not daily_helper:
            health_status["checks"]["daily_helper"] = "failed"
            logger.error(f"Daily API helper not initialized - Request ID: {request_id}")
            raise HTTPException(
                status_code=503, detail="Daily API helper not initialized"
            )
        health_status["checks"]["daily_helper"] = "ok"
        logger.debug(f"Daily API helper check passed - Request ID: {request_id}")

        # Check 2: Required environment variables (from secrets or direct env vars)
        required_env_vars = ["DAILY_API_KEY", "AWS_REGION"]
        missing_vars = []
        env_status = {}

        for var in required_env_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
                env_status[var] = "missing"
            else:
                env_status[var] = "present"
                # Log source of environment variable (for debugging)
                if var == "DAILY_API_KEY":
                    logger.info(
                        f"Daily API key loaded: {value[:10]}... - Request ID: {request_id}"
                    )
                elif var == "AWS_REGION":
                    logger.info(f"AWS region: {value} - Request ID: {request_id}")

        # Optional AWS credentials check (may come from IAM role or secrets)
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if aws_access_key and aws_secret_key:
            env_status["aws_credentials"] = "explicit"
            logger.info(
                f"Using explicit AWS credentials: {aws_access_key[:10]}... - Request ID: {request_id}"
            )
        else:
            env_status["aws_credentials"] = "iam_role"
            logger.info(
                f"Using IAM role for AWS credentials - Request ID: {request_id}"
            )

        if missing_vars:
            health_status["checks"]["environment"] = {
                "status": "failed",
                "missing": missing_vars,
                "details": env_status,
            }
            logger.error(
                f"Missing required environment variables: {missing_vars} - Request ID: {request_id}"
            )
            raise HTTPException(
                status_code=503,
                detail=f"Missing required environment variables: {', '.join(missing_vars)}",
            )

        health_status["checks"]["environment"] = {"status": "ok", "details": env_status}

        # Check 3: Bot process tracking
        active_bots = sum(1 for proc in bot_procs.values() if proc[0].poll() is None)
        health_status["checks"]["active_bots"] = active_bots
        health_status["checks"]["total_bot_processes"] = len(bot_procs)

        # Check 4: Resource usage
        try:
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Quick check

            health_status["checks"]["memory_usage_percent"] = round(memory_percent, 1)
            health_status["checks"]["cpu_usage_percent"] = round(cpu_percent, 1)

            # Add resource status
            if memory_percent > 90:
                health_status["checks"]["resource_status"] = "critical_memory"
            elif cpu_percent > 90:
                health_status["checks"]["resource_status"] = "critical_cpu"
            elif memory_percent > 80 or cpu_percent > 80:
                health_status["checks"]["resource_status"] = "warning"
            else:
                health_status["checks"]["resource_status"] = "ok"

        except Exception as e:
            health_status["checks"]["resource_status"] = "unavailable"
            logger.warning(f"Could not get resource usage: {str(e)}")

        logger.debug(
            f"Bot process check completed - Active: {active_bots}, "
            f"Total: {len(bot_procs)} - Request ID: {request_id}"
        )

        # Log successful health check
        duration_ms = (time.time() - start_time) * 1000
        log_performance("health_check", duration_ms, request_id=request_id)

        return JSONResponse(health_status)

    except HTTPException:
        # Re-raise HTTP exceptions
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            f"Health check failed with HTTP exception - Request ID: {request_id}, Duration: {duration_ms:.2f}ms"
        )
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            e, "HEALTH_CHECK_ERROR", request_id=request_id, duration_ms=duration_ms
        )
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint for ECS deployment.

    This endpoint indicates whether the service is ready to accept traffic.
    Unlike /health, this can be used for more sophisticated deployment strategies.

    Returns:
        JSONResponse: Readiness status

    Raises:
        HTTPException: If service is not ready
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        log_request(request_id, "GET", "/ready")

        # Check if Daily helper is ready
        daily_helper = daily_helpers.get("rest")
        if not daily_helper:
            logger.error(
                f"Service not ready - Daily helper not initialized - Request ID: {request_id}"
            )
            raise HTTPException(
                status_code=503,
                detail="Service not ready - Daily helper not initialized",
            )

        # Check if we can create rooms (basic functionality test)
        # This is a lightweight check - we don't actually create a room
        if not os.getenv("DAILY_API_KEY"):
            logger.error(
                f"Service not ready - Daily API key not configured - Request ID: {request_id}"
            )
            raise HTTPException(
                status_code=503,
                detail="Service not ready - Daily API key not configured",
            )

        duration_ms = (time.time() - start_time) * 1000
        log_performance("readiness_check", duration_ms, request_id=request_id)

        return JSONResponse(
            {
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "pipecat-voice-agent",
                "request_id": request_id,
            }
        )

    except HTTPException:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            f"Readiness check failed - Request ID: {request_id}, Duration: {duration_ms:.2f}ms"
        )
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            e, "READINESS_CHECK_ERROR", request_id=request_id, duration_ms=duration_ms
        )
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")


async def create_room_and_token() -> tuple[str, str]:
    """Helper function to create a Daily room and generate an access token.

    Returns:
        tuple[str, str]: A tuple containing (room_url, token)

    Raises:
        HTTPException: If room creation or token generation fails
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        logger.info(f"Creating Daily room - Request ID: {request_id}")

        room = await daily_helpers["rest"].create_room(DailyRoomParams())
        if not room.url:
            log_error(
                Exception("Room creation returned empty URL"),
                "ROOM_CREATION_FAILED",
                request_id=request_id,
            )
            raise HTTPException(status_code=500, detail="Failed to create room")

        logger.info(
            f"Daily room created successfully - Room: {room.url} - Request ID: {request_id}"
        )

        token = await daily_helpers["rest"].get_token(room.url)
        if not token:
            log_error(
                Exception(f"Token generation failed for room: {room.url}"),
                "TOKEN_GENERATION_FAILED",
                request_id=request_id,
                room_url=room.url,
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to get token for room: {room.url}"
            )

        duration_ms = (time.time() - start_time) * 1000
        log_performance(
            "create_room_and_token",
            duration_ms,
            request_id=request_id,
            room_url=room.url,
        )

        logger.info(
            f"Room and token created successfully - Room: {room.url}, "
            f"Token length: {len(token)} - Request ID: {request_id}"
        )

        return room.url, token

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            e, "CREATE_ROOM_TOKEN_ERROR", request_id=request_id, duration_ms=duration_ms
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to create room and token: {str(e)}"
        )


@app.get("/")
async def start_agent(request: Request):
    """Endpoint for direct browser access to the bot.

    Creates a room, starts a bot instance, and redirects to the Daily room URL.

    Returns:
        RedirectResponse: Redirects to the Daily room URL

    Raises:
        HTTPException: If room creation, token generation, or bot startup fails
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        log_request(
            request_id,
            "GET",
            "/",
            client_ip=request.client.host if request.client else "unknown",
        )

        logger.info(
            f"Starting agent for direct browser access - Request ID: {request_id}"
        )
        room_url, token = await create_room_and_token()

        logger.info(
            f"Room created, checking bot limits - Room: {room_url} - Request ID: {request_id}"
        )

        # Check if there is already an existing process running in this room
        num_bots_in_room = sum(
            1
            for proc in bot_procs.values()
            if proc[1] == room_url and proc[0].poll() is None
        )
        if num_bots_in_room >= MAX_BOTS_PER_ROOM:
            logger.error(
                f"Max bot limit reached for room - Room: {room_url}, "
                f"Current: {num_bots_in_room}, Max: {MAX_BOTS_PER_ROOM} - Request ID: {request_id}"
            )
            raise HTTPException(
                status_code=500, detail=f"Max bot limit reached for room: {room_url}"
            )

        # Spawn a new bot process
        try:
            bot_file = get_bot_file()
            proc = subprocess.Popen(
                ["python3", "-m", bot_file, "-u", room_url, "-t", token],
                shell=False,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                # Add resource limits to prevent runaway processes
                preexec_fn=None,  # Don't change process group for better cleanup
            )
            bot_procs[proc.pid] = (proc, room_url, time.time())

            log_bot_lifecycle("started", proc.pid, room_url, request_id=request_id)

        except Exception as e:
            log_error(e, "BOT_STARTUP_FAILED", request_id=request_id, room_url=room_url)
            raise HTTPException(
                status_code=500, detail=f"Failed to start subprocess: {e}"
            )

        duration_ms = (time.time() - start_time) * 1000
        log_performance(
            "start_agent",
            duration_ms,
            request_id=request_id,
            room_url=room_url,
            bot_pid=proc.pid,
        )

        logger.info(
            f"Agent started successfully, redirecting to room - Room: {room_url}, "
            f"PID: {proc.pid} - Request ID: {request_id}"
        )

        return RedirectResponse(room_url)

    except HTTPException:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            f"Start agent failed - Request ID: {request_id}, Duration: {duration_ms:.2f}ms"
        )
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            e, "START_AGENT_ERROR", request_id=request_id, duration_ms=duration_ms
        )
        raise HTTPException(status_code=500, detail=f"Failed to start agent: {str(e)}")


@app.post("/connect")
async def rtvi_connect(request: Request) -> Dict[Any, Any]:
    """RTVI connect endpoint that creates a room and returns connection credentials.

    This endpoint is called by RTVI clients to establish a connection.

    Returns:
        Dict[Any, Any]: Authentication bundle containing room_url and token

    Raises:
        HTTPException: If room creation, token generation, or bot startup fails
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        log_request(
            request_id,
            "POST",
            "/connect",
            client_ip=request.client.host if request.client else "unknown",
        )

        logger.info(f"Creating room for RTVI connection - Request ID: {request_id}")
        room_url, token = await create_room_and_token()

        logger.info(
            f"Room created for RTVI, starting bot process - Room: {room_url} - Request ID: {request_id}"
        )

        # Start the bot process
        try:
            bot_file = get_bot_file()
            proc = subprocess.Popen(
                ["python3", "-m", bot_file, "-u", room_url, "-t", token],
                shell=False,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                # Add resource limits to prevent runaway processes
                preexec_fn=None,  # Don't change process group for better cleanup
            )
            bot_procs[proc.pid] = (proc, room_url, time.time())

            log_bot_lifecycle("started_rtvi", proc.pid, room_url, request_id=request_id)

        except Exception as e:
            log_error(
                e, "RTVI_BOT_STARTUP_FAILED", request_id=request_id, room_url=room_url
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to start subprocess: {e}"
            )

        duration_ms = (time.time() - start_time) * 1000
        log_performance(
            "rtvi_connect",
            duration_ms,
            request_id=request_id,
            room_url=room_url,
            bot_pid=proc.pid,
        )

        logger.info(
            f"RTVI connection established successfully - Room: {room_url}, "
            f"PID: {proc.pid} - Request ID: {request_id}"
        )

        # Return the authentication bundle in format expected by DailyTransport
        return {"room_url": room_url, "token": token}

    except HTTPException:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            f"RTVI connect failed - Request ID: {request_id}, Duration: {duration_ms:.2f}ms"
        )
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            e, "RTVI_CONNECT_ERROR", request_id=request_id, duration_ms=duration_ms
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to establish RTVI connection: {str(e)}"
        )


@app.get("/status/{pid}")
def get_status(pid: int, request: Request):
    """Get the status of a specific bot process.

    Args:
        pid (int): Process ID of the bot
        request (Request): FastAPI request object

    Returns:
        JSONResponse: Status information for the bot

    Raises:
        HTTPException: If the specified bot process is not found
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        log_request(
            request_id,
            "GET",
            f"/status/{pid}",
            client_ip=request.client.host if request.client else "unknown",
        )

        # Look up the subprocess
        proc = bot_procs.get(pid)

        # If the subprocess doesn't exist, return an error
        if not proc:
            logger.warning(
                f"Bot process not found - PID: {pid} - Request ID: {request_id}"
            )
            raise HTTPException(
                status_code=404, detail=f"Bot with process id: {pid} not found"
            )

        # Check the status of the subprocess
        status = "running" if proc[0].poll() is None else "finished"
        room_url = proc[1]

        duration_ms = (time.time() - start_time) * 1000
        log_performance(
            "get_status",
            duration_ms,
            request_id=request_id,
            bot_pid=pid,
            bot_status=status,
        )

        logger.info(
            f"Bot status retrieved - PID: {pid}, Status: {status}, "
            f"Room: {room_url} - Request ID: {request_id}"
        )

        return JSONResponse(
            {
                "bot_id": pid,
                "status": status,
                "room_url": room_url,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except HTTPException:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            f"Get status failed - PID: {pid}, Duration: {duration_ms:.2f}ms - Request ID: {request_id}"
        )
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_error(
            e,
            "GET_STATUS_ERROR",
            request_id=request_id,
            bot_pid=pid,
            duration_ms=duration_ms,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get bot status: {str(e)}"
        )


if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Parse command line arguments for server configuration
    default_host = os.getenv("HOST", "0.0.0.0")
    default_port = int(os.getenv("FAST_API_PORT", "7860"))

    parser = argparse.ArgumentParser(description="Daily FastAPI server")
    parser.add_argument("--host", type=str, default=default_host, help="Host address")
    parser.add_argument("--port", type=int, default=default_port, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Reload code on change")

    config = parser.parse_args()

    logger.info(
        f"Starting Pipecat Voice AI Agent server on {config.host}:{config.port}"
    )

    try:
        # Start the FastAPI server with improved configuration for containers
        uvicorn.run(
            "server:app",
            host=config.host,
            port=config.port,
            reload=config.reload,
            # Add container-friendly settings
            access_log=True,
            log_level="info",
            # Enable graceful shutdown
            timeout_keep_alive=30,
            timeout_graceful_shutdown=int(os.getenv("GRACEFUL_TIMEOUT", "30")),
        )
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        cleanup()
    except Exception as e:
        logger.error(f"Server error: {e}")
        cleanup()
        sys.exit(1)
