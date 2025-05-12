"""
Slack agent implementation for ChatDSJ Slack Bot.

This module provides the SlackAgent class that handles interactions
with the Slack API and manages message sending and retrieval.
"""
from typing import Any, Dict, List, Optional

from crewai import Agent
from langchain.tools import Tool

from agents.base_agent import BaseAgent
from services.slack_service import SlackService
from utils.logging_config import configure_logging

logger = configure_logging()


class SlackAgent(BaseAgent):
    """
    Agent specialized in Slack interactions.
    
    This agent wraps the SlackService and provides tools for sending messages,
    retrieving conversation history, and managing user information.
    
    Attributes:
        slack_service: The SlackService instance for API interactions
    """

    def __init__(self, slack_service: SlackService, verbose: bool = False) -> None:
        """
        Initialize a Slack agent with the SlackService.
        
        Args:
            slack_service: The SlackService instance for API interactions
            verbose: Whether to enable verbose logging
        """
        self.slack_service = slack_service
        
        super().__init__(
            name="Slack Interface Specialist",
            role="Slack communication expert",
            goal="Handle all interactions with the Slack platform efficiently and reliably",
            verbose=verbose
        )

    def get_backstory(self) -> str:
        """
        Get the backstory for the Slack agent.
        
        Returns:
            str: Specialized backstory for the Slack agent
        """
        return (
            "You are the Slack Interface Specialist, an expert in managing communications "
            "between users and the ChatDSJ system through Slack. You understand Slack's "
            "message formats, threading, and user information structures. Your expertise "
            "allows you to retrieve conversation history, format messages appropriately, "
            "and ensure that all communications with users are delivered correctly. You "
            "are the bridge between the Slack platform and the rest of the ChatDSJ system."
        )

    def get_tools(self) -> List[Tool]:
        """
        Get the tools available to the Slack agent.
        
        Returns:
            List[Tool]: List of tools for Slack interactions
        """
        return [
            Tool(
                name="send_message",
                description="Send a message to a Slack channel or thread",
                func=self.send_message
            ),
            Tool(
                name="send_ephemeral_message",
                description="Send an ephemeral message visible only to a specific user",
                func=self.send_ephemeral_message
            ),
            Tool(
                name="fetch_channel_history",
                description="Fetch message history from a Slack channel",
                func=self.fetch_channel_history
            ),
            Tool(
                name="fetch_thread_history",
                description="Fetch message history from a Slack thread",
                func=self.fetch_thread_history
            ),
            Tool(
                name="get_user_display_name",
                description="Get the display name of a Slack user",
                func=self.get_user_display_name
            ),
            Tool(
                name="clean_prompt_text",
                description="Clean the prompt text by removing bot mentions",
                func=self.clean_prompt_text
            )
        ]

    def send_message(self, channel_id: str, text: str, thread_ts: Optional[str] = None) -> Dict:
        """
        Send a message to a Slack channel or thread.
        
        Args:
            channel_id: Slack channel ID
            text: Message text
            thread_ts: Optional thread timestamp to reply in a thread
            
        Returns:
            Dict: Response from the Slack API
        """
        return self.slack_service.send_message(channel_id, text, thread_ts)

    def send_ephemeral_message(self, channel_id: str, user_id: str, text: str) -> bool:
        """
        Send an ephemeral message visible only to a specific user.
        
        Args:
            channel_id: Slack channel ID
            user_id: Slack user ID who will see the message
            text: Message text
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.slack_service.send_ephemeral_message(channel_id, user_id, text)

    def fetch_channel_history(self, channel_id: str, limit: int = 1000) -> List[Dict]:
        """
        Fetch message history from a Slack channel.
        
        Args:
            channel_id: Slack channel ID
            limit: Maximum number of messages to fetch
            
        Returns:
            List[Dict]: List of message objects
        """
        return self.slack_service.fetch_channel_history(channel_id, limit)

    def fetch_thread_history(self, channel_id: str, thread_ts: str, limit: int = 1000) -> List[Dict]:
        """
        Fetch message history from a Slack thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            limit: Maximum number of messages to fetch
            
        Returns:
            List[Dict]: List of message objects
        """
        return self.slack_service.fetch_thread_history(channel_id, thread_ts, limit)

    def get_user_display_name(self, user_id: str) -> str:
        """
        Get the display name of a Slack user.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            str: User's display name or a fallback
        """
        return self.slack_service.get_user_display_name(user_id)

    def clean_prompt_text(self, text: str) -> str:
        """
        Clean the prompt text by removing bot mentions.
        
        Args:
            text: Raw message text
            
        Returns:
            str: Cleaned text without bot mentions
        """
        return self.slack_service.clean_prompt_text(text)