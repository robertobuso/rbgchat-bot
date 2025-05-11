"""
Performance metrics utilities for ChatDSJ Slack Bot.

This module provides utilities for tracking and reporting
performance metrics and statistics across the application.
"""
import functools
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from loguru import logger

from utils.logging_config import configure_logging

# Initialize logger
logger = configure_logging()

# Type variable for generic function types
F = TypeVar('F', bound=Callable[..., Any])


class Metrics:
    """
    Class for tracking and reporting performance metrics.
    
    This class provides methods for tracking function execution times,
    API call counts, error rates, and other performance metrics.
    
    Attributes:
        _instance: Singleton instance
        execution_times: Dictionary of function execution times
        api_calls: Dictionary of API call counts by service
        errors: Dictionary of error counts by category
        last_reset: Timestamp of the last metrics reset
    """
    _instance = None
    
    def __new__(cls):
        """Create a singleton instance."""
        if cls._instance is None:
            cls._instance = super(Metrics, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self) -> None:
        """Initialize the metrics dictionaries."""
        self.execution_times: Dict[str, List[float]] = {}
        self.api_calls: Dict[str, int] = {}
        self.errors: Dict[str, int] = {}
        self.last_reset = datetime.now()
    
    def track_execution_time(self, category: str, time_ms: float) -> None:
        """
        Track function execution time.
        
        Args:
            category: Category or function name
            time_ms: Execution time in milliseconds
        """
        if category not in self.execution_times:
            self.execution_times[category] = []
        
        self.execution_times[category].append(time_ms)
        
        # Keep only the last 1000 measurements to prevent unbounded growth
        if len(self.execution_times[category]) > 1000:
            self.execution_times[category] = self.execution_times[category][-1000:]
    
    def track_api_call(self, service: str) -> None:
        """
        Track an API call to a service.
        
        Args:
            service: Name of the service called
        """
        self.api_calls[service] = self.api_calls.get(service, 0) + 1
    
    def track_error(self, category: str) -> None:
        """
        Track an error occurrence.
        
        Args:
            category: Error category or type
        """
        self.errors[category] = self.errors.get(category, 0) + 1
    
    def get_execution_stats(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution time statistics.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            Dict: Execution time statistics
        """
        import statistics
        
        result = {}
        
        if category:
            # Get stats for a specific category
            if category in self.execution_times and self.execution_times[category]:
                times = self.execution_times[category]
                result[category] = {
                    "count": len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "mean_ms": statistics.mean(times),
                    "median_ms": statistics.median(times),
                    "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else None,
                    "p99_ms": sorted(times)[int(len(times) * 0.99)] if len(times) >= 100 else None
                }
        else:
            # Get stats for all categories
            for cat, times in self.execution_times.items():
                if times:
                    result[cat] = {
                        "count": len(times),
                        "min_ms": min(times),
                        "max_ms": max(times),
                        "mean_ms": statistics.mean(times),
                        "median_ms": statistics.median(times),
                        "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else None,
                        "p99_ms": sorted(times)[int(len(times) * 0.99)] if len(times) >= 100 else None
                    }
        
        return result
    
    def get_api_call_stats(self) -> Dict[str, int]:
        """
        Get API call statistics.
        
        Returns:
            Dict: API call counts by service
        """
        return self.api_calls.copy()
    
    def get_error_stats(self) -> Dict[str, int]:
        """
        Get error statistics.
        
        Returns:
            Dict: Error counts by category
        """
        return self.errors.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all metrics.
        
        Returns:
            Dict: Summary of all metrics
        """
        now = datetime.now()
        time_since_reset = (now - self.last_reset).total_seconds()
        
        total_api_calls = sum(self.api_calls.values())
        total_errors = sum(self.errors.values())
        error_rate = total_errors / total_api_calls if total_api_calls > 0 else 0
        
        return {
            "time_since_reset_seconds": time_since_reset,
            "total_api_calls": total_api_calls,
            "total_errors": total_errors,
            "error_rate": error_rate,
            "api_calls_per_minute": (total_api_calls * 60) / time_since_reset if time_since_reset > 0 else 0,
            "execution_times": self.get_execution_stats(),
            "api_calls": self.get_api_call_stats(),
            "errors": self.get_error_stats()
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._initialize()
        logger.info("Metrics have been reset")


# Create a singleton instance
metrics = Metrics()


def timed(category: str) -> Callable[[F], F]:
    """
    Decorator to time function execution and record metrics.
    
    Args:
        category: Category name for this measurement
        
    Returns:
        Decorated function
        
    Example:
        @timed("database_query")
        def fetch_data():
            # Function execution time will be tracked
            return db.query.all()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000.0
                metrics.track_execution_time(category, execution_time_ms)
                
                if execution_time_ms > 1000:  # Log slow executions (>1s)
                    logger.warning(f"Slow execution: {category} took {execution_time_ms:.2f}ms")
        
        return cast(F, wrapper)
    
    return decorator


def track_api(service: str) -> Callable[[F], F]:
    """
    Decorator to track API calls to a service.
    
    Args:
        service: Name of the service being called
        
    Returns:
        Decorated function
        
    Example:
        @track_api("slack_api")
        def send_message():
            # API call will be tracked
            return slack_client.chat_postMessage(...)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                metrics.track_api_call(service)
                return func(*args, **kwargs)
            except Exception as e:
                metrics.track_error(f"{service}_{e.__class__.__name__}")
                raise
        
        return cast(F, wrapper)
    
    return decorator


def track_error(category: str) -> Callable[[F], F]:
    """
    Decorator to track errors in a function.
    
    Args:
        category: Error category
        
    Returns:
        Decorated function
        
    Example:
        @track_error("database_error")
        def fetch_data():
            # Errors will be tracked under "database_error" category
            return db.query.all()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                metrics.track_error(category)
                raise
        
        return cast(F, wrapper)
    
    return decorator