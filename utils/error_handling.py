"""
Error handling utilities for ChatDSJ Slack Bot.

This module provides error handling functions and decorators
to ensure consistent error management across the application.
"""
import functools
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from loguru import logger

# Type variable for generic function types
F = TypeVar('F', bound=Callable[..., Any])


def safe_execute(default_return: Any = None) -> Callable[[F], F]:
    """
    Decorator to safely execute a function and catch any exceptions.
    
    Args:
        default_return: The default value to return if an exception occurs
        
    Returns:
        A decorator function
    
    Example:
        @safe_execute(default_return=[])
        def get_items():
            # If this raises an exception, it will return [] instead
            return db.query.all()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.debug(f"Exception details: {traceback.format_exc()}")
                return default_return
        return cast(F, wrapper)
    return decorator


def handle_api_error(
    func: Callable[[Any], Dict],
    error_msg: str = "An error occurred while processing your request."
) -> Callable[[Any], Dict]:
    """
    Decorator to handle API errors and return consistent error responses.
    
    Args:
        func: The function to decorate
        error_msg: The default error message to return
        
    Returns:
        A decorated function
        
    Example:
        @handle_api_error
        def get_user_data(user_id):
            # If this raises an exception, it will return a formatted error response
            return api.get_user(user_id)
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Dict:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}")
            logger.debug(f"Exception details: {traceback.format_exc()}")
            return {
                "success": False,
                "error": str(e),
                "message": error_msg
            }
    return wrapper


def format_exception(e: Exception) -> Dict[str, str]:
    """
    Format an exception into a standardized dictionary.
    
    Args:
        e: The exception to format
        
    Returns:
        Dict: Formatted exception details
    """
    return {
        "error_type": e.__class__.__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }


def get_error_message(e: Exception, default_message: str = "An error occurred.") -> str:
    """
    Get a user-friendly error message from an exception.
    
    Args:
        e: The exception
        default_message: Default message to use if the exception message is empty
        
    Returns:
        str: User-friendly error message
    """
    error_msg = str(e) if str(e) else default_message
    
    # Map common exceptions to more user-friendly messages
    error_map = {
        "ConnectionError": "Failed to connect to the service. Please check your network connection.",
        "TimeoutError": "The request timed out. Please try again later.",
        "PermissionError": "You don't have permission to perform this action.",
        "FileNotFoundError": "The requested file could not be found.",
        "ValidationError": "The provided data is invalid.",
        "SlackApiError": "An error occurred while communicating with Slack."
    }
    
    return error_map.get(e.__class__.__name__, error_msg)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable[[F], F]:
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay for each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        A decorator function
        
    Example:
        @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        def connect_to_api():
            # This will be retried up to 3 times with exponential backoff
            return api.connect()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import time
            
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(f"Attempt {attempt} failed, retrying in {current_delay:.2f}s: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    
    return decorator