"""Utility functions for logging and performance monitoring."""
import logging
import time

logger = logging.getLogger("sonic")


def debug_print(message: str) -> None:
    """Log a debug message. Replaces the old print-based approach."""
    logger.debug(message)


def time_it(label: str, func):
    """Time synchronous function execution."""
    start = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - start
    logger.debug("Execution time for %s: %.4fs", label, elapsed)
    return result


async def time_it_async(label: str, func):
    """Time asynchronous function execution."""
    start = time.perf_counter()
    result = await func()
    elapsed = time.perf_counter() - start
    logger.debug("Execution time for %s: %.4fs", label, elapsed)
    return result
