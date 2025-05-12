"""
Content agent implementation for ChatDSJ Slack Bot.

This module provides the ContentAgent class that handles content extraction
and summarization from various sources such as web pages and YouTube videos.
"""
from typing import Dict, List, Optional

from langchain.tools import Tool

from agents.base_agent import BaseAgent
from services.content_service import ContentService
from utils.logging_config import configure_logging

logger = configure_logging()


class ContentAgent(BaseAgent):
    """
    Agent specialized in content extraction and summarization.
    
    This agent wraps the ContentService and provides tools for extracting
    and summarizing content from various sources.
    
    Attributes:
        content_service: The ContentService instance for content processing
    """

    def __init__(self, content_service: ContentService, verbose: bool = False) -> None:
        """
        Initialize a Content agent with the ContentService.
        
        Args:
            content_service: The ContentService instance for content processing
            verbose: Whether to enable verbose logging
        """
        self.content_service = content_service
        
        super().__init__(
            name="Content Processor",
            role="Content extraction and summarization specialist",
            goal="Extract and summarize content from various sources accurately and efficiently",
            verbose=verbose
        )

    def get_backstory(self) -> str:
        """
        Get the backstory for the Content agent.
        
        Returns:
            str: Specialized backstory for the Content agent
        """
        return (
            "You are the Content Processor, an expert in extracting and summarizing content "
            "from various sources including web pages, articles, and YouTube videos. You understand "
            "how to analyze and distill key information from complex content, providing users with "
            "concise, informative summaries that capture the most important points. Your expertise "
            "allows you to handle different content formats and adapt your summarization approach "
            "based on the source type and user preferences."
        )

    def get_tools(self) -> List[Tool]:
        """
        Get the tools available to the Content agent.
        
        Returns:
            List[Tool]: List of tools for content processing
        """
        return [
            Tool(
                name="extract_and_summarize",
                description="Extract content from a URL and generate a summary",
                func=self.extract_and_summarize
            ),
            Tool(
                name="determine_source_type",
                description="Determine the type of source from a URL",
                func=self.determine_source_type
            ),
            Tool(
                name="extract_urls_from_text",
                description="Extract URLs from text",
                func=self.extract_urls_from_text
            )
        ]

    def extract_and_summarize(
        self,
        url: str,
        max_length: int = 500,
        format: str = "markdown"
    ) -> Dict[str, any]:
        """
        Extract content from a URL and generate a summary.
        
        Args:
            url: The URL to extract content from
            max_length: Maximum length of the summary in words
            format: Output format ('markdown', 'text', or 'html')
            
        Returns:
            Dict: Summary information including title, summary text, source URL, etc.
        """
        return self.content_service.extract_and_summarize(url, max_length, format)

    def determine_source_type(self, url: str) -> str:
        """
        Determine the type of source from a URL.
        
        Args:
            url: The URL to analyze
            
        Returns:
            str: Source type ('webpage', 'youtube', 'github', etc.)
        """
        return self.content_service.get_source_type(url)

    def extract_urls_from_text(self, text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: The text to extract URLs from
            
        Returns:
            List[str]: List of extracted URLs
        """
        import re
        
        # Regular expression to match URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        
        # Find all URLs in the text
        urls = re.findall(url_pattern, text)
        
        # Deduplicate and validate
        unique_urls = []
        for url in urls:
            # Remove trailing punctuation that might have been included
            url = re.sub(r'[.,;:)]$', '', url)
            
            # Only include unique URLs
            if url not in unique_urls:
                unique_urls.append(url)
        
        return unique_urls