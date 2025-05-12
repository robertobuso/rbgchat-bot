"""
Slack service for ChatDSJ Slack Bot.

This module provides a service for interacting with Slack's API,
handling messages, events, and user information.
"""
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

from config.settings import get_settings
from utils.logging_config import configure_logging

# Initialize logger and settings
logger = configure_logging()
settings = get_settings()


class SlackService:
    """
    Service for interacting with Slack's API.
    
    This class handles communication with Slack, manages events,
    and provides functionality for sending and receiving messages.
    
    Attributes:
        app: Slack Bolt app instance
        client: Slack client from the Bolt app
        bot_user_id: Bot's user ID in Slack
        is_dummy: Whether this is a dummy instance (for testing/offline use)
        channel_data: Dictionary tracking channel statistics
        bot_message_ts: Dictionary tracking bot message timestamps
        user_info_cache: Cache of user information
    """

    def __init__(self) -> None:
        """
        Initialize the Slack service with credentials from settings.
        
        Sets up the Slack Bolt app, configures handlers, and initializes
        shared state for tracking messages and user information.
        """
        # Initialize credentials
        self.bot_token = settings.slack_bot_token.get_secret_value() if settings.slack_bot_token else None
        self.signing_secret = settings.slack_signing_secret.get_secret_value() if settings.slack_signing_secret else None
        self.app_token = settings.slack_app_token.get_secret_value() if settings.slack_app_token else None
        
        # Initialize shared state
        self.app: Optional[App] = None
        self.client = None
        self.bot_user_id: Optional[str] = None
        self.is_dummy: bool = False
        
        # Track channel data
        self.channel_data: Dict[str, Dict] = {}
        
        # Track bot message timestamps for threading
        self.bot_message_ts: Dict[str, str] = {}
        
        # Cache user info to reduce API calls
        self.user_info_cache: Dict[str, Dict] = {}
        
        # Initialize the app
        self._initialize_app()

    def _initialize_app(self) -> None:
        """
        Initialize the Slack Bolt app with credentials.
        
        If credentials are missing, creates a dummy app for testing.
        """
        if not all([self.bot_token, self.signing_secret, self.app_token]):
            logger.warning("Slack credentials missing, creating dummy app")
            self.app = App()
            self.client = self.app.client
            self.is_dummy = True
            self.bot_user_id = "DUMMY_BOT_ID"
            return
        
        try:
            # Initialize the app with credentials
            self.app = App(
                token=self.bot_token,
                signing_secret=self.signing_secret
            )
            
            self.client = self.app.client
            
            # Get bot user ID
            auth_response = self.client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            
            logger.info(f"Slack service initialized with bot ID: {self.bot_user_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Slack app: {e}")
            # Create dummy app as fallback
            self.app = App()
            self.client = self.app.client
            self.is_dummy = True
            self.bot_user_id = "DUMMY_BOT_ID"

    def is_available(self) -> bool:
        """
        Check if the Slack service is available.
        
        Returns:
            bool: True if the app is initialized and not a dummy, False otherwise
        """
        return self.app is not None and not self.is_dummy

    def register_mention_handler(self, handler: Callable) -> None:
        """
        Register a handler for app_mention events.
        
        Args:
            handler: Function to handle app_mention events
        """
        if not self.is_available():
            logger.warning("Cannot register mention handler: Slack app not available")
            return
        
        try:
            self.app.event("app_mention")(handler)
            logger.info("Registered app_mention handler")
        except Exception as e:
            logger.error(f"Failed to register mention handler: {e}")

    def register_reaction_handler(self, handler: Callable) -> None:
        """
        Register a handler for reaction_added events.
        
        Args:
            handler: Function to handle reaction_added events
        """
        if not self.is_available():
            logger.warning("Cannot register reaction handler: Slack app not available")
            return
        
        try:
            self.app.event("reaction_added")(handler)
            logger.info("Registered reaction_added handler")
        except Exception as e:
            logger.error(f"Failed to register reaction handler: {e}")

    def register_error_handler(self, handler: Callable) -> None:
        """
        Register a handler for error events.
        
        Args:
            handler: Function to handle error events
        """
        if not self.is_available():
            logger.warning("Cannot register error handler: Slack app not available")
            return
        
        try:
            self.app.error(handler)
            logger.info("Registered error handler")
        except Exception as e:
            logger.error(f"Failed to register error handler: {e}")

    def start_socket_mode(self) -> None:
        """
        Start the Slack app in Socket Mode in a separate thread.
        
        This allows the app to receive events without exposing a public endpoint.
        """
        if not self.is_available() or not self.app_token:
            logger.warning("Cannot start Socket Mode: Slack app not available or app token missing")
            return
        
        try:
            # Create handler
            handler = SocketModeHandler(self.app, self.app_token)
            
            # Start in a separate thread
            thread = threading.Thread(target=handler.start, daemon=True)
            thread.start()
            
            logger.info("Started Slack app in Socket Mode")
            
        except Exception as e:
            logger.error(f"Failed to start Socket Mode: {e}")

    def clean_prompt_text(self, text: str) -> str:
        """
        Clean the prompt text by removing bot mentions.
        
        Args:
            text: Raw message text
            
        Returns:
            str: Cleaned text without bot mentions
        """
        if not text:
            return ""
        
        # Remove bot mention
        if self.bot_user_id:
            text = re.sub(f"<@{self.bot_user_id}>", "", text)
        
        # Remove any other user mentions (optional)
        text = re.sub(r"<@[A-Z0-9]+>", "", text)
        
        # Clean up whitespace
        text = text.strip()
        
        return text

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
        if not self.is_available():
            logger.warning("Cannot send ephemeral message: Slack app not available")
            return False
        
        try:
            response = self.client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=text
            )
            
            return response["ok"]
            
        except SlackApiError as e:
            logger.error(f"Error sending ephemeral message: {e}")
            return False

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
        if not self.is_available():
            logger.warning("Cannot send message: Slack app not available")
            return {"ok": False, "error": "Slack app not available"}
        
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )
            
            # Track bot message timestamp
            if response["ok"] and "ts" in response:
                key = f"{channel_id}:{thread_ts if thread_ts else 'main'}"
                self.bot_message_ts[key] = response["ts"]
            
            return response
            
        except SlackApiError as e:
            logger.error(f"Error sending message: {e}")
            return {"ok": False, "error": str(e)}

    def get_user_info(self, user_id: str) -> Dict:
        """
        Get information about a Slack user.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            Dict: User information
        """
        if not self.is_available():
            logger.warning("Cannot get user info: Slack app not available")
            return {}
        
        # Check cache first
        if user_id in self.user_info_cache:
            return self.user_info_cache[user_id]
        
        try:
            response = self.client.users_info(user=user_id)
            
            if response["ok"]:
                # Cache the result
                self.user_info_cache[user_id] = response["user"]
                return response["user"]
            
            return {}
            
        except SlackApiError as e:
            logger.error(f"Error getting user info: {e}")
            return {}

    def get_user_display_name(self, user_id: str) -> str:
        """
        Get the display name of a Slack user.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            str: User's display name or a fallback
        """
        user_info = self.get_user_info(user_id)
        
        if not user_info:
            return f"User {user_id}"
        
        # Try to get the display name
        profile = user_info.get("profile", {})
        
        # Check different name fields in order of preference
        display_name = (
            profile.get("display_name")
            or profile.get("real_name")
            or user_info.get("name")
            or f"User {user_id}"
        )
        
        return display_name

    def fetch_channel_history(self, channel_id: str, limit: int = 100) -> List[Dict]:
        """
        Fetch message history from a Slack channel.
        
        Args:
            channel_id: Slack channel ID
            limit: Maximum number of messages to fetch
            
        Returns:
            List[Dict]: List of message objects
        """
        if not self.is_available():
            logger.warning("Cannot fetch channel history: Slack app not available")
            return []
        
        try:
            # Fetch messages with pagination if needed
            all_messages = []
            cursor = None
            
            while len(all_messages) < limit:
                # Determine how many messages to fetch in this request
                remaining = limit - len(all_messages)
                fetch_limit = min(remaining, 100)  # Slack API limit is 100 per request
                
                # Make the API call
                response = self.client.conversations_history(
                    channel=channel_id,
                    limit=fetch_limit,
                    cursor=cursor
                )
                
                if not response["ok"]:
                    break
                
                # Add messages to the list
                messages = response.get("messages", [])
                all_messages.extend(messages)
                
                # Check if there are more messages
                if response.get("has_more", False) and "response_metadata" in response:
                    cursor = response["response_metadata"].get("next_cursor")
                else:
                    break
            
            return all_messages[:limit]
            
        except SlackApiError as e:
            logger.error(f"Error fetching channel history: {e}")
            return []

    def fetch_thread_history(self, channel_id: str, thread_ts: str, limit: int = 100) -> List[Dict]:
        """
        Fetch message history from a Slack thread.
        
        Args:
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            limit: Maximum number of messages to fetch
            
        Returns:
            List[Dict]: List of message objects
        """
        if not self.is_available():
            logger.warning("Cannot fetch thread history: Slack app not available")
            return []
        
        try:
            # Fetch messages with pagination if needed
            all_messages = []
            cursor = None
            
            while len(all_messages) < limit:
                # Determine how many messages to fetch in this request
                remaining = limit - len(all_messages)
                fetch_limit = min(remaining, 100)  # Slack API limit is 100 per request
                
                # Make the API call
                response = self.client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts,
                    limit=fetch_limit,
                    cursor=cursor
                )
                
                if not response["ok"]:
                    break
                
                # Add messages to the list
                messages = response.get("messages", [])
                all_messages.extend(messages)
                
                # Check if there are more messages
                if response.get("has_more", False) and "response_metadata" in response:
                    cursor = response["response_metadata"].get("next_cursor")
                else:
                    break
            
            return all_messages[:limit]
            
        except SlackApiError as e:
            logger.error(f"Error fetching thread history: {e}")
            return []

    def update_channel_stats(self, channel_id: str, user_id: str, message_ts: str) -> None:
        """
        Update channel statistics with a new message.
        
        Args:
            channel_id: Slack channel ID
            user_id: Slack user ID who sent the message
            message_ts: Message timestamp
        """
        # Initialize channel data if not exists
        if channel_id not in self.channel_data:
            self.channel_data[channel_id] = {
                "message_count": 0,
                "user_count": set(),
                "last_activity": 0,
                "user_message_counts": {}
            }
        
        # Update statistics
        channel_stats = self.channel_data[channel_id]
        channel_stats["message_count"] += 1
        channel_stats["user_count"].add(user_id)
        channel_stats["last_activity"] = time.time()
        
        # Update user message count
        if user_id not in channel_stats["user_message_counts"]:
            channel_stats["user_message_counts"][user_id] = 0
        channel_stats["user_message_counts"][user_id] += 1

    def get_channel_stats(self, channel_id: str) -> Dict[str, Any]:
        """
        Get statistics for a Slack channel.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            Dict[str, Any]: Channel statistics
        """
        if channel_id not in self.channel_data:
            return {
                "message_count": 0,
                "user_count": 0,
                "last_activity": 0,
                "user_message_counts": {}
            }
        
        stats = self.channel_data[channel_id].copy()
        
        # Convert set to count for serialization
        stats["user_count"] = len(stats["user_count"])
        
        return stats