"""
OpenAI service for ChatDSJ Slack Bot.

This module provides a service for interacting with OpenAI's API,
handling completions, and tracking usage.
"""
import time
from typing import Dict, Optional, Tuple

from openai import OpenAI
from openai.types.chat import ChatCompletion

from config.settings import get_settings
from utils.logging_config import configure_logging
from utils.token_counter import count_messages_tokens, ensure_messages_within_limit

# Initialize logger and settings
logger = configure_logging()
settings = get_settings()


class OpenAIService:
    """
    Service for interacting with OpenAI's API.
    
    This class handles communication with OpenAI, manages token usage,
    and provides completion functionality for the bot.
    
    Attributes:
        client: OpenAI client instance
        model: Model to use for completions
        max_tokens: Maximum tokens for responses
        usage_stats: Dictionary tracking token usage and costs
    """

    def __init__(self) -> None:
        """
        Initialize the OpenAI service with API key from settings.
        
        Sets up the OpenAI client, configures model parameters,
        and initializes usage tracking.
        """
        self.client: Optional[OpenAI] = None
        self.model: str = settings.openai_model
        self.max_tokens: int = settings.max_tokens_response
        
        # Initialize usage tracking
        self.usage_stats: Dict = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
        }
        
        # Initialize client if API key is available
        api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI service initialized with model {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OpenAI API key not provided, service will not be available")

    def is_available(self) -> bool:
        """
        Check if the OpenAI service is available.
        
        Returns:
            bool: True if the client is initialized, False otherwise
        """
        return self.client is not None

    def get_completion(
        self,
        prompt: str,
        conversation_history: list,
        user_specific_context: Optional[str] = None,
        linked_notion_content: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Get a completion from OpenAI for the given prompt and context.
        
        Args:
            prompt: The user's current prompt
            conversation_history: Previous messages in the conversation
            user_specific_context: Optional user-specific context from Notion
            linked_notion_content: Optional content from linked Notion pages
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (will increase exponentially)
            
        Returns:
            Tuple[Optional[str], Optional[Dict]]: The completion text and usage statistics,
                                                 or (None, None) if the request fails
        """
        if not self.is_available():
            logger.error("OpenAI client not initialized")
            return None, None
        
        # Prepare system prompt with context
        system_prompt = settings.openai_system_prompt
        
        # Add user-specific context if available
        if user_specific_context:
            system_prompt += f"\n\nUser context: {user_specific_context}"
        
        # Add linked Notion content if available
        if linked_notion_content:
            system_prompt += f"\n\nRelevant information: {linked_notion_content}"
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Ensure messages are within token limit
        messages = ensure_messages_within_limit(
            messages, 
            model=self.model, 
            max_tokens=4096 - self.max_tokens  # Reserve space for completion
        )
        
        # Track request in usage stats
        self.usage_stats["requests_made"] += 1
        
        # Try to get completion with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.debug(f"Sending request to OpenAI (attempt {attempt + 1}/{max_retries})")
                
                response: ChatCompletion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{
                        "role": m["role"],
                        "content": m["content"]
                    } for m in messages],
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                )
                
                # Extract content and usage
                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                
                # Update usage tracking
                self._update_usage_tracking(usage)
                self.usage_stats["successful_requests"] += 1
                
                logger.debug(f"OpenAI response received: {len(content)} chars, {usage['total_tokens']} tokens")
                return content, usage
                
            except Exception as e:
                logger.error(f"Error getting completion from OpenAI: {e}")
                self.usage_stats["failed_requests"] += 1
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
        
        logger.error(f"Failed to get completion after {max_retries} attempts")
        return None, None

    def _update_usage_tracking(self, usage: Dict) -> None:
        """
        Update usage statistics with the latest request.
        
        Args:
            usage: Usage statistics from the OpenAI response
        """
        self.usage_stats["total_prompt_tokens"] += usage["prompt_tokens"]
        self.usage_stats["total_completion_tokens"] += usage["completion_tokens"]
        self.usage_stats["total_tokens"] += usage["total_tokens"]
        
        # Calculate and update cost
        cost = self._calculate_cost(usage)
        self.usage_stats["estimated_cost_usd"] += cost
        
        logger.debug(f"Updated usage stats: {self.usage_stats}")

    def _calculate_cost(self, usage: Dict) -> float:
        """
        Calculate the cost of a request based on token usage.
        
        Args:
            usage: Usage statistics from the OpenAI response
            
        Returns:
            float: Estimated cost in USD
        """
        # Pricing per 1K tokens (as of March 2023)
        # These rates should be updated if OpenAI changes their pricing
        pricing = {
            "gpt-4o": {"prompt": 0.01, "completion": 0.03},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-32k": {"prompt": 0.06, "completion": 0.12},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004},
        }
        
        # Default to gpt-3.5-turbo pricing if model not found
        model_pricing = pricing.get(self.model, pricing["gpt-3.5-turbo"])
        
        # Calculate cost
        prompt_cost = (usage["prompt_tokens"] / 1000) * model_pricing["prompt"]
        completion_cost = (usage["completion_tokens"] / 1000) * model_pricing["completion"]
        total_cost = prompt_cost + completion_cost
        
        return total_cost

    def get_usage_stats(self) -> Dict:
        """
        Get a copy of the current usage statistics.
        
        Returns:
            Dict: Copy of usage statistics
        """
        return self.usage_stats.copy()