"""
Token counting utilities for LLM interactions.

This module provides functions to count tokens in text and messages,
and to ensure that message history stays within token limits.
"""
from typing import Dict, List, Optional, Union

import tiktoken

from config.settings import get_settings
from utils.logging_config import configure_logging

logger = configure_logging()
settings = get_settings()


def count_tokens(text: str, model: Optional[str] = None) -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
        model: The model to use for token counting (defaults to settings.openai_model)
        
    Returns:
        int: The number of tokens in the text
    """
    if model is None:
        model = settings.openai_model
    
    try:
        encoder = tiktoken.encoding_for_model(model)
        return len(encoder.encode(text))
    except KeyError:
        # Fallback to cl100k_base for newer models not yet in tiktoken
        logger.warning(f"Model {model} not found in tiktoken, using cl100k_base instead")
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text))


def count_messages_tokens(messages: List[Dict[str, str]], model: Optional[str] = None) -> int:
    """
    Count the number of tokens in a list of messages.
    
    This implements the token counting logic described in OpenAI's documentation:
    https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: The model to use for token counting (defaults to settings.openai_model)
        
    Returns:
        int: The total number of tokens in the messages
    """
    if model is None:
        model = settings.openai_model
    
    # Base tokens for the messages format
    tokens_per_message = 3
    tokens_per_name = 1
    
    # Count tokens
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += count_tokens(str(value), model)
            if key == "name":
                num_tokens += tokens_per_name
    
    # Every reply is primed with <|start|>assistant<|message|>
    num_tokens += 3
    
    return num_tokens


def ensure_messages_within_limit(
    messages: List[Dict[str, str]], 
    model: Optional[str] = None, 
    max_tokens: Optional[int] = None
) -> List[Dict[str, str]]:
    """
    Ensure that a list of messages stays within the token limit.
    
    This function preserves system messages and keeps as many recent messages
    as possible while staying under the token limit.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        model: The model to use for token counting (defaults to settings.openai_model)
        max_tokens: Maximum number of tokens allowed (defaults to settings.max_tokens_response)
        
    Returns:
        List[Dict[str, str]]: Trimmed list of messages
    """
    if model is None:
        model = settings.openai_model
    
    if max_tokens is None:
        max_tokens = settings.max_tokens_response
    
    # Separate system messages from other messages
    system_messages = [msg for msg in messages if msg["role"] == "system"]
    non_system_messages = [msg for msg in messages if msg["role"] != "system"]
    
    # Count tokens in system messages
    system_tokens = count_messages_tokens(system_messages, model)
    
    # Reserve tokens for system messages and some buffer
    available_tokens = max_tokens - system_tokens - 100  # 100 tokens buffer
    
    if available_tokens <= 0:
        logger.warning("System messages already exceed token limit")
        # Return only the first system message if we're over limit
        return [system_messages[0]] if system_messages else []
    
    # Start with most recent messages and work backwards
    result = system_messages.copy()
    current_tokens = system_tokens
    
    for message in reversed(non_system_messages):
        message_tokens = count_tokens(message["content"], model) + 4  # +4 for message overhead
        
        if current_tokens + message_tokens <= max_tokens:
            result.append(message)
            current_tokens += message_tokens
        else:
            break
    
    # Restore the original order (system messages first, then chronological)
    result = system_messages + [msg for msg in reversed(result[len(system_messages):])]
    
    if len(result) < len(messages):
        logger.info(f"Trimmed message history from {len(messages)} to {len(result)} messages to stay within token limit")
    
    return result