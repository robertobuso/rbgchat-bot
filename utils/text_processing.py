"""
Text processing utilities for ChatDSJ Slack Bot.

This module provides functions for extracting information from text
and formatting conversations for OpenAI API.
"""
import re
from typing import Dict, List, Optional, Tuple

from utils.logging_config import configure_logging

logger = configure_logging()


def extract_nickname_from_text(text: str) -> Optional[str]:
    """
    Extract a nickname from text using various patterns.
    
    This function tries different regex patterns to extract a nickname,
    such as "call me X", "my name is X", etc.
    
    Args:
        text: The text to extract a nickname from
        
    Returns:
        Optional[str]: The extracted nickname or None if not found
    """
    # List of regex patterns to try
    patterns = [
        r"(?:call\s+me|my\s+name\s+is|i\s+am|i'm)\s+([A-Za-z0-9_\-]+)",
        r"name[:\s]+([A-Za-z0-9_\-]+)",
        r"nickname[:\s]+([A-Za-z0-9_\-]+)",
    ]
    
    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nickname = match.group(1).strip()
            logger.debug(f"Extracted nickname: {nickname}")
            return nickname
    
    return None


def extract_todo_from_text(text: str) -> Optional[str]:
    """
    Extract a todo item from text.
    
    This function looks for patterns like "todo: X", "remember to X", etc.
    
    Args:
        text: The text to extract a todo from
        
    Returns:
        Optional[str]: The extracted todo or None if not found
    """
    # Patterns for todo extraction
    patterns = [
        r"todo:?\s+(.+)$",
        r"remember\s+to\s+(.+)$",
        r"don't\s+forget\s+to\s+(.+)$",
        r"note\s+to\s+self:?\s+(.+)$",
    ]
    
    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            todo = match.group(1).strip()
            logger.debug(f"Extracted todo: {todo}")
            return todo
    
    return None


def format_conversation_for_openai(
    messages: List[Dict[str, str]],
    user_display_names: Dict[str, str],
    bot_user_id: str
) -> List[Dict[str, str]]:
    """
    Format Slack conversation history for OpenAI API.
    
    This function converts Slack message format to OpenAI's expected format,
    replacing user IDs with display names and handling special message types.
    
    Args:
        messages: List of Slack messages
        user_display_names: Mapping of user IDs to display names
        bot_user_id: The bot's user ID
        
    Returns:
        List[Dict[str, str]]: Formatted messages for OpenAI API
    """
    formatted_messages = []
    
    for msg in messages:
        if "user" not in msg or "text" not in msg:
            continue
        
        user_id = msg["user"]
        text = msg["text"]
        
        # Skip empty messages
        if not text.strip():
            continue
        
        # Determine role based on user ID
        if user_id == bot_user_id:
            role = "assistant"
        else:
            role = "user"
            # Add user's name if available
            if user_id in user_display_names:
                text = f"{user_display_names[user_id]}: {text}"
        
        formatted_messages.append({
            "role": role,
            "content": text
        })
    
    logger.debug(f"Formatted {len(formatted_messages)} messages for OpenAI")
    return formatted_messages