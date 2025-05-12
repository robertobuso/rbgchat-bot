"""
Settings module for ChatDSJ Slack Bot.

This module defines the application settings using Pydantic for validation
and environment variable loading.
"""
from functools import lru_cache
from typing import Literal, Optional, Dict, Any

# Import directly from pydantic without requiring pydantic-settings
from pydantic import (
    BaseModel, 
    SecretStr, 
    field_validator,
    model_validator,
    ConfigDict
)


class Settings(BaseModel):
    """
    Application settings with environment variable loading and validation.
    
    Attributes:
        slack_bot_token: Slack bot user OAuth token
        slack_signing_secret: Slack signing secret for request verification
        slack_app_token: Slack app-level token for Socket Mode
        openai_api_key: OpenAI API key
        openai_model: OpenAI model to use for completions
        openai_system_prompt: Default system prompt for the assistant
        notion_api_token: Optional Notion API token
        notion_user_db_id: Optional Notion user database ID
        log_level: Logging level
        environment: Application environment
        max_tokens_response: Maximum tokens for AI responses
        max_message_history: Maximum messages to keep in conversation history
        enable_crew_verbose: Enable verbose logging for CrewAI
    """
    # Configuration using ConfigDict instead of class Config
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Enable environment variable loading
        populate_by_name=True,
    )
    
    # Slack Configuration
    slack_bot_token: SecretStr
    slack_signing_secret: SecretStr
    slack_app_token: SecretStr

    # OpenAI Configuration
    openai_api_key: SecretStr
    openai_model: str = "gpt-4o"
    openai_system_prompt: str = "You are ChatDSJ, a helpful AI assistant for the Slack workspace. You help users with their questions and tasks."

    # Notion Configuration
    notion_api_token: Optional[SecretStr] = None
    notion_user_db_id: Optional[str] = None

    # Application Configuration
    log_level: str = "INFO"
    environment: Literal["development", "testing", "production"] = "development"
    max_tokens_response: int = 1500
    max_message_history: int = 1000
    enable_crew_verbose: bool = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate that the log level is one of the standard logging levels.
        
        Args:
            v: The log level string to validate
            
        Returns:
            The validated log level string
            
        Raises:
            ValueError: If the log level is not valid
        """
        valid_levels = ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @model_validator(mode="before")
    @classmethod
    def load_from_env(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load values from environment variables.
        
        This is a custom validator that mimics the behavior of BaseSettings
        by loading values from environment variables.
        
        Args:
            data: The input data dictionary
            
        Returns:
            The updated data dictionary with values from environment variables
        """
        # If data is already populated (not empty), return it as is
        if data:
            return data
            
        # Import os here to avoid circular imports
        import os
        from dotenv import load_dotenv
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Create a dictionary with field names and their values from environment variables
        env_data = {}
        
        for field_name in cls.model_fields:
            # Convert field_name to uppercase for environment variables
            env_var_name = field_name.upper()
            if env_var_name in os.environ:
                env_data[field_name] = os.environ[env_var_name]
        
        return env_data


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()