"""Utility functions for logging and performance monitoring."""
import datetime
import time
import inspect
from src.core.config import DEBUG


def debug_print(message: str) -> None:
    """Print debug message with timestamp and function name."""
    if not DEBUG:
        return
    
    stack = inspect.stack()
    func_name = stack[1].function
    
    # Skip wrapper functions
    if func_name in ('time_it', 'time_it_async'):
        func_name = stack[2].function
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"{timestamp} {func_name} {message}")


def time_it(label: str, func):
    """Time synchronous function execution."""
    start = time.perf_counter()
    result = func()
    elapsed = time.perf_counter() - start
    debug_print(f"Execution time for {label}: {elapsed:.4f}s")
    return result


async def time_it_async(label: str, func):
    """Time asynchronous function execution."""
    start = time.perf_counter()
    result = await func()
    elapsed = time.perf_counter() - start
    debug_print(f"Execution time for {label}: {elapsed:.4f}s")
    return result
