from pydantic import ValidationError

from .exceptions import ConfigurationError

def validate_app_config(func):
    """
    A decorator that handles environment variable validation errors thrown by Pydantic Settings and formats
    them into a user-friendly display.

    This decorator catches ValidationError exceptions and transforms them into a formatted error message
    with a consistent visual style. It specifically handles two types of environment variable errors:
    - Missing required environment variables
    - Invalid environment variable names

    Args:
        func: The function to be decorated

    Returns:
        wrapper: The decorated function that includes error handling

    Raises:
        ConfigurationError: A formatted error message with a 60-character wide display showing:
            - A border of asterisks
            - A centered "Environment Configuration Error" title
            - One or more error messages describing the specific environment variable issues
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            errors = e.errors()
            error_messages = []
            
            for error in errors:
                if error["type"] == "missing":
                    error_messages.append(f"Missing required environment variable: {error['loc'][0]}")
                elif error["type"] == "extra_forbidden":
                    error_messages.append(f"Invalid environment variable name: {str(error['loc'][0]).upper()}")
            
            width = 60
            border = "*" * width
            title = "Environment Configuration Error"
            
            formatted_message = (
                "\n"
                f"{border}\n"
                f"* {title.center(width-4)} *\n"
                f"{border}\n"
                + "\n".join(f"* {msg:<{width-4}} *" for msg in error_messages) + "\n"
                f"{border}\n"
            )
            
            raise ConfigurationError(formatted_message)
            
    return wrapper