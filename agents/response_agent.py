"""
Response agent implementation for ChatDSJ Slack Bot.

This module provides the ResponseAgent class that handles generating
responses to user queries using the OpenAI service.
"""
from typing import Dict, List, Optional

from langchain.tools import Tool

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from utils.logging_config import configure_logging
from utils.text_processing import format_conversation_for_openai

logger = configure_logging()


class ResponseAgent(BaseAgent):
    """
    Agent specialized in generating responses to user queries.
    
    This agent wraps the LLMService and provides tools for generating
    appropriate responses based on conversation context.
    
    Attributes:
        openai_service: The LLMService instance for API interactions
    """

    def __init__(self, openai_service: LLMService, verbose: bool = False) -> None:
        """
        Initialize a Response agent with the LLMService.
        
        Args:
            openai_service: The LLMService instance for API interactions
            verbose: Whether to enable verbose logging
        """
        self.openai_service = openai_service
        
        super().__init__(
            name="Response Generator",
            role="AI conversation specialist",
            goal="Generate helpful, accurate, and contextually appropriate responses to user queries",
            verbose=verbose
        )

    def get_backstory(self) -> str:
        """
        Get the backstory for the Response agent.
        
        Returns:
            str: Specialized backstory for the Response agent
        """
        return (
            "You are the Response Generator, an expert in crafting helpful and contextually "
            "appropriate responses to user queries. You understand how to interpret user "
            "messages, consider conversation history, and incorporate user-specific context "
            "to generate personalized and relevant responses. Your expertise in natural "
            "language processing allows you to maintain coherent conversations across "
            "multiple interactions and provide accurate information to users."
        )

    def get_tools(self) -> List[Tool]:
        """
        Get the tools available to the Response agent.
        
        Returns:
            List[Tool]: List of tools for response generation
        """
        return [
            Tool(
                name="generate_response",
                description="Generate a response to a user query using OpenAI",
                func=self.generate_response
            ),
            Tool(
                name="format_conversation",
                description="Format Slack conversation history for OpenAI API",
                func=self.format_conversation
            )
        ]

    def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict]] = None,
        user_specific_context: Optional[str] = None,
        linked_notion_content: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a response to a user query using OpenAI.
        
        Args:
            prompt: The user's current prompt
            conversation_history: Previous messages in the conversation
            user_specific_context: Optional user-specific context from Notion
            linked_notion_content: Optional content from linked Notion pages
            
        Returns:
            Optional[str]: The generated response or None if generation fails
        """
        response, _ = self.openai_service.get_completion(
            prompt=prompt,
            conversation_history=conversation_history or [],
            user_specific_context=user_specific_context,
            linked_notion_content=linked_notion_content
        )
        return response

    def format_conversation(
        self,
        messages: List[Dict],
        user_display_names: Dict[str, str],
        bot_user_id: str
    ) -> List[Dict[str, str]]:
        """
        Format Slack conversation history for OpenAI API.
        
        Args:
            messages: List of Slack messages
            user_display_names: Mapping of user IDs to display names
            bot_user_id: The bot's user ID
            
        Returns:
            List[Dict[str, str]]: Formatted messages for OpenAI API
        """
        return format_conversation_for_openai(messages, user_display_names, bot_user_id)