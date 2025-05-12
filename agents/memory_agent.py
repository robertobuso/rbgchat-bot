"""
Memory agent implementation for ChatDSJ Slack Bot.

This module provides the MemoryAgent class that handles user memory
management through the Notion service.
"""
from typing import List, Optional, Tuple

from langchain.tools import Tool

from agents.base_agent import BaseAgent
from services.notion_service import NotionService
from utils.logging_config import configure_logging

logger = configure_logging()


class MemoryAgent(BaseAgent):
    """
    Agent specialized in user memory management.
    
    This agent wraps the NotionService and provides tools for retrieving
    and storing user-specific information in Notion.
    
    Attributes:
        notion_service: The NotionService instance for API interactions
    """

    def __init__(self, notion_service: NotionService, verbose: bool = False) -> None:
        """
        Initialize a Memory agent with the NotionService.
        
        Args:
            notion_service: The NotionService instance for API interactions
            verbose: Whether to enable verbose logging
        """
        self.notion_service = notion_service
        
        super().__init__(
            name="Memory Manager",
            role="User memory and context specialist",
            goal="Maintain and retrieve user-specific information to personalize interactions",
            verbose=verbose
        )

    def get_backstory(self) -> str:
        """
        Get the backstory for the Memory agent.
        
        Returns:
            str: Specialized backstory for the Memory agent
        """
        return (
            "You are the Memory Manager, an expert in maintaining and retrieving user-specific "
            "information. You have access to the Notion database where user preferences, "
            "conversation history, and personal details are stored. Your role is to ensure "
            "that interactions with users are personalized based on their history and preferences. "
            "You can retrieve user nicknames, store new information about users, and provide "
            "context that helps other agents deliver more personalized responses."
        )

    def get_tools(self) -> List[Tool]:
        """
        Get the tools available to the Memory agent.
        
        Returns:
            List[Tool]: List of tools for memory management
        """
        return [
            Tool(
                name="get_user_preferred_name",
                description="Get the preferred name of a Slack user from Notion",
                func=self.get_user_preferred_name
            ),
            Tool(
                name="get_user_page_content",
                description="Get the content of a user's Notion page",
                func=self.get_user_page_content
            ),
            Tool(
                name="handle_nickname_command",
                description="Handle a nickname command from a user",
                func=self.handle_nickname_command
            ),
            Tool(
                name="store_user_nickname",
                description="Store a user's nickname in Notion",
                func=self.store_user_nickname
            )
        ]

    def get_user_preferred_name(self, slack_user_id: str) -> Optional[str]:
        """
        Get the preferred name of a Slack user from Notion.
        
        Args:
            slack_user_id: Slack user ID to look up
            
        Returns:
            Optional[str]: Preferred name if found, None otherwise
        """
        return self.notion_service.get_user_preferred_name(slack_user_id)

    def get_user_page_content(self, slack_user_id: str) -> Optional[str]:
        """
        Get the content of a user's Notion page.
        
        Args:
            slack_user_id: Slack user ID to look up
            
        Returns:
            Optional[str]: Page content if found, None otherwise
        """
        return self.notion_service.get_user_page_content(slack_user_id)

    def handle_nickname_command(self, prompt_text: str, slack_user_id: str, slack_display_name: Optional[str] = None) -> Tuple[Optional[str], bool]:
        """
        Handle a nickname command from a user.
        
        Args:
            prompt_text: Text of the user's message
            slack_user_id: Slack user ID
            slack_display_name: User's display name in Slack
            
        Returns:
            Tuple[Optional[str], bool]: Confirmation message and success status
        """
        return self.notion_service.handle_nickname_command(prompt_text, slack_user_id, slack_display_name)

    def store_user_nickname(self, slack_user_id: str, nickname: str, slack_display_name: Optional[str] = None) -> bool:
        """
        Store a user's nickname in Notion.
        
        Args:
            slack_user_id: Slack user ID
            nickname: Nickname to store
            slack_display_name: User's display name in Slack
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.notion_service.store_user_nickname(slack_user_id, nickname, slack_display_name)