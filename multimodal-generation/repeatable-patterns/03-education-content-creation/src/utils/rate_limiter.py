"""
Rate Limiter Utility

Flexible rate limiting system for API requests with optimization features
and frontend integration capabilities.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Advanced rate limiter with optimization features for API requests.
    Designed for notebook use and frontend integration.
    """
    
    def __init__(self, default_limit: int = 30, skip_final_delays: bool = True):
        """
        Initialize rate limiter.
        
        Args:
            default_limit: Default rate limit in seconds
            skip_final_delays: Whether to skip delays for final requests
        """
        self.last_request_times: Dict[str, datetime] = {}
        self.rate_limits: Dict[str, int] = {
            'nova-premier': 5,   # 5 seconds between requests
            'nova-pro': 30,      # 30 seconds between requests  
            'nova-canvas': 30,   # 30 seconds between requests
            'default': default_limit
        }
        self.skip_final_delays = skip_final_delays
        self.current_topic = 0
        self.total_topics = 0
        self.session_stats = {
            'total_waits': 0,
            'total_wait_time': 0,
            'requests_made': 0,
            'delays_skipped': 0
        }
    
    def set_topic_info(self, current: int, total: int) -> None:
        """
        Set current topic information for optimization.
        
        Args:
            current: Current topic number
            total: Total number of topics
        """
        self.current_topic = current
        self.total_topics = total
    
    def wait_if_needed(self, service: str, is_final_request: bool = False) -> Dict[str, Any]:
        """
        Wait if needed to respect rate limits.
        
        Args:
            service: Service name (nova-premier, nova-pro, nova-canvas)
            is_final_request: Whether this is the final request
            
        Returns:
            Dict with wait information
        """
        current_time = datetime.now()
        service_key = service.lower()
        
        # Get rate limit for this service
        rate_limit = self.rate_limits.get(service_key, self.rate_limits['default'])
        
        # Skip rate limiting for final requests if enabled
        if (self.skip_final_delays and is_final_request and 
            self.current_topic >= self.total_topics):
            print(f"   ⚡ Skipping final rate limit for {service} (optimization)")
            self.last_request_times[service_key] = current_time
            self.session_stats['delays_skipped'] += 1
            return {
                'waited': False,
                'wait_time': 0,
                'reason': 'final_request_optimization',
                'service': service
            }
        
        wait_info = {
            'waited': False,
            'wait_time': 0,
            'reason': 'no_wait_needed',
            'service': service
        }
        
        if service_key in self.last_request_times:
            time_since_last = (current_time - self.last_request_times[service_key]).total_seconds()
            
            if time_since_last < rate_limit:
                wait_time = rate_limit - time_since_last
                
                # Show appropriate message
                if is_final_request:
                    print(f"   ⏱️ Final rate limiting: Waiting {wait_time:.1f}s for {service}")
                else:
                    print(f"   ⏱️ Rate limiting: Waiting {wait_time:.1f}s for {service}")
                
                time.sleep(wait_time)
                
                # Update stats
                self.session_stats['total_waits'] += 1
                self.session_stats['total_wait_time'] += wait_time
                
                wait_info.update({
                    'waited': True,
                    'wait_time': wait_time,
                    'reason': 'rate_limit_enforced'
                })
        
        # Update last request time
        self.last_request_times[service_key] = datetime.now()
        self.session_stats['requests_made'] += 1
        
        print(f"   ✅ Rate limit OK for {service}")
        return wait_info
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.
        
        Returns:
            Dict with session statistics
        """
        return {
            **self.session_stats,
            'services_tracked': list(self.last_request_times.keys()),
            'rate_limits': self.rate_limits.copy(),
            'average_wait_time': (
                self.session_stats['total_wait_time'] / self.session_stats['total_waits']
                if self.session_stats['total_waits'] > 0 else 0
            )
        }
    
    def reset_stats(self) -> None:
        """Reset session statistics."""
        self.session_stats = {
            'total_waits': 0,
            'total_wait_time': 0,
            'requests_made': 0,
            'delays_skipped': 0
        }
        print("🔄 Rate limiter statistics reset")
    
    def set_rate_limit(self, service: str, limit: int) -> None:
        """
        Set custom rate limit for a service.
        
        Args:
            service: Service name
            limit: Rate limit in seconds
        """
        self.rate_limits[service.lower()] = limit
        print(f"⚙️ Rate limit for {service} set to {limit} seconds")
    
    def get_next_available_time(self, service: str) -> Optional[datetime]:
        """
        Get the next time a request can be made for a service.
        
        Args:
            service: Service name
            
        Returns:
            Next available time or None if available now
        """
        service_key = service.lower()
        
        if service_key not in self.last_request_times:
            return None
        
        rate_limit = self.rate_limits.get(service_key, self.rate_limits['default'])
        next_time = self.last_request_times[service_key] + timedelta(seconds=rate_limit)
        
        if datetime.now() >= next_time:
            return None
        
        return next_time


class NovaRateLimiter(RateLimiter):
    """
    Specialized rate limiter for Nova models with optimized settings.
    """
    
    def __init__(self):
        super().__init__(default_limit=30, skip_final_delays=True)
        print("✅ Nova Rate Limiter initialized")
        print("   • Nova Premier: 5 seconds between requests")
        print("   • Nova Pro: 30 seconds between requests")
        print("   • Nova Canvas: 30 seconds between requests")
        print("   • Optimized to skip final delays when possible")


# Global rate limiter instance
_global_rate_limiter: Optional[NovaRateLimiter] = None


def setup_rate_limiting() -> NovaRateLimiter:
    """
    Set up Nova rate limiting with a single function call.
    
    Returns:
        NovaRateLimiter: Configured rate limiter instance
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        _global_rate_limiter = NovaRateLimiter()
    
    return _global_rate_limiter


def get_rate_limiter() -> NovaRateLimiter:
    """
    Get the global rate limiter instance.
    
    Returns:
        NovaRateLimiter: The global rate limiter
    """
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        return setup_rate_limiting()
    
    return _global_rate_limiter


def wait_for_service(service: str, is_final: bool = False) -> Dict[str, Any]:
    """
    Quick function to wait for a service.
    
    Args:
        service: Service name
        is_final: Whether this is the final request
        
    Returns:
        Dict with wait information
    """
    limiter = get_rate_limiter()
    return limiter.wait_if_needed(service, is_final)


def set_topic_progress(current: int, total: int) -> None:
    """
    Set current topic progress for optimization.
    
    Args:
        current: Current topic number
        total: Total topics
    """
    limiter = get_rate_limiter()
    limiter.set_topic_info(current, total)


def get_rate_stats() -> Dict[str, Any]:
    """
    Get rate limiting statistics.
    
    Returns:
        Dict with statistics
    """
    limiter = get_rate_limiter()
    return limiter.get_stats()


class RateLimiterTracker:
    """
    Class-based interface for rate limiting (similar to TokenTracker pattern).
    """
    
    @classmethod
    def setup(cls) -> NovaRateLimiter:
        """Set up rate limiting."""
        return setup_rate_limiting()
    
    @classmethod
    def wait(cls, service: str, is_final: bool = False) -> Dict[str, Any]:
        """Wait for service if needed."""
        return wait_for_service(service, is_final)
    
    @classmethod
    def set_progress(cls, current: int, total: int) -> None:
        """Set topic progress."""
        set_topic_progress(current, total)
    
    @classmethod
    def stats(cls) -> Dict[str, Any]:
        """Get statistics."""
        return get_rate_stats()
    
    @classmethod
    def reset(cls) -> None:
        """Reset statistics."""
        limiter = get_rate_limiter()
        limiter.reset_stats()


# Convenience functions for specific Nova models
def wait_for_premier(is_final: bool = False) -> Dict[str, Any]:
    """Wait for Nova Premier if needed."""
    return wait_for_service('nova-premier', is_final)


def wait_for_pro(is_final: bool = False) -> Dict[str, Any]:
    """Wait for Nova Pro if needed."""
    return wait_for_service('nova-pro', is_final)


def wait_for_canvas(is_final: bool = False) -> Dict[str, Any]:
    """Wait for Nova Canvas if needed."""
    return wait_for_service('nova-canvas', is_final)


# Quick setup function for notebook cells
def quick_rate_setup():
    """
    Ultra-simple setup function for notebook cells.
    
    Returns:
        tuple: (rate_limiter, wait_function, stats_function)
    """
    limiter = setup_rate_limiting()
    return limiter, wait_for_service, get_rate_stats
