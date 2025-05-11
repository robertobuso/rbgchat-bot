"""
Settings module for ChatDSJ Slack Bot.

This module defines the application settings using Pydantic for validation
and environment variable loading.
"""
from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseSettings, SecretStr, validator


class Settings(BaseSettings):
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

    @validator("log_level")
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

    class Config:
        """Pydantic configuration for Settings."""
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching.
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()