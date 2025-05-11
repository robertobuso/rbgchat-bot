"""
Notion service for ChatDSJ Slack Bot.

This module provides a service for interacting with Notion's API,
managing user data, and retrieving information from Notion databases.
"""
from typing import Dict, List, Optional, Tuple

from notion_client import Client

from config.settings import get_settings
from utils.logging_config import configure_logging
from utils.text_processing import extract_nickname_from_text

# Initialize logger and settings
logger = configure_logging()
settings = get_settings()


class NotionService:
    """
    Service for interacting with Notion's API.
    
    This class handles communication with Notion, manages user data,
    and provides functionality for storing and retrieving information.
    
    Attributes:
        client: Notion client instance
        user_db_id: ID of the user database in Notion
    """

    def __init__(self) -> None:
        """
        Initialize the Notion service with API token from settings.
        
        Sets up the Notion client and configures database IDs.
        """
        self.client: Optional[Client] = None
        self.user_db_id: Optional[str] = settings.notion_user_db_id
        
        # Initialize client if API token is available
        api_token = settings.notion_api_token.get_secret_value() if settings.notion_api_token else None
        if api_token and self.user_db_id:
            try:
                self.client = Client(auth=api_token)
                logger.info("Notion service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Notion client: {e}")
                self.client = None
        else:
            logger.warning("Notion API token or database ID not provided, service will not be available")

    def is_available(self) -> bool:
        """
        Check if the Notion service is available.
        
        Returns:
            bool: True if the client and database ID are initialized, False otherwise
        """
        return self.client is not None and self.user_db_id is not None

    def get_user_page_id(self, slack_user_id: str) -> Optional[str]:
        """
        Get the Notion page ID for a Slack user.
        
        Args:
            slack_user_id: Slack user ID to look up
            
        Returns:
            Optional[str]: Notion page ID if found, None otherwise
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return None
        
        try:
            # Query the database for the user
            response = self.client.databases.query(
                database_id=self.user_db_id,
                filter={
                    "property": "SlackUserID",
                    "rich_text": {
                        "equals": slack_user_id
                    }
                }
            )
            
            # Return the page ID if found
            if response["results"]:
                page_id = response["results"][0]["id"]
                logger.debug(f"Found Notion page for user {slack_user_id}: {page_id}")
                return page_id
            
            logger.debug(f"No Notion page found for user {slack_user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error querying Notion database: {e}")
            return None

    def get_user_page_properties(self, slack_user_id: str) -> Optional[Dict]:
        """
        Get the properties of a user's Notion page.
        
        Args:
            slack_user_id: Slack user ID to look up
            
        Returns:
            Optional[Dict]: Page properties if found, None otherwise
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return None
        
        # Get the page ID
        page_id = self.get_user_page_id(slack_user_id)
        if not page_id:
            return None
        
        try:
            # Retrieve the page
            page = self.client.pages.retrieve(page_id=page_id)
            
            # Extract and return properties
            properties = page.get("properties", {})
            logger.debug(f"Retrieved properties for user {slack_user_id}")
            return properties
            
        except Exception as e:
            logger.error(f"Error retrieving Notion page: {e}")
            return None

    def get_user_preferred_name(self, slack_user_id: str) -> Optional[str]:
        """
        Get the preferred name of a Slack user from Notion.
        
        Args:
            slack_user_id: Slack user ID to look up
            
        Returns:
            Optional[str]: Preferred name if found, None otherwise
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return None
        
        # Get the user properties
        properties = self.get_user_page_properties(slack_user_id)
        if not properties:
            return None
        
        try:
            # Extract preferred name from properties
            nickname_prop = properties.get("Nickname", {})
            if nickname_prop and nickname_prop.get("type") == "rich_text":
                rich_text = nickname_prop.get("rich_text", [])
                if rich_text:
                    nickname = rich_text[0].get("plain_text", "")
                    if nickname:
                        logger.debug(f"Found preferred name for user {slack_user_id}: {nickname}")
                        return nickname
            
            logger.debug(f"No preferred name found for user {slack_user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting preferred name: {e}")
            return None

    def get_user_page_content(self, slack_user_id: str) -> Optional[str]:
        """
        Get the content of a user's Notion page.
        
        Args:
            slack_user_id: Slack user ID to look up
            
        Returns:
            Optional[str]: Page content if found, None otherwise
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return None
        
        # Get the page ID
        page_id = self.get_user_page_id(slack_user_id)
        if not page_id:
            return None
        
        try:
            # Retrieve the page blocks
            blocks = self._get_all_blocks(page_id)
            
            # Extract and concatenate text content
            content = self._extract_text_from_blocks(blocks)
            
            logger.debug(f"Retrieved page content for user {slack_user_id}: {len(content)} chars")
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving Notion page content: {e}")
            return None

    def _get_all_blocks(self, page_id: str) -> List[Dict]:
        """
        Get all blocks from a Notion page, handling pagination.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            List[Dict]: List of block objects
        """
        blocks = []
        start_cursor = None
        
        while True:
            # Get a batch of blocks
            response = self.client.blocks.children.list(
                block_id=page_id,
                start_cursor=start_cursor
            )
            
            # Add blocks to the list
            blocks.extend(response.get("results", []))
            
            # Check if there are more blocks
            if response.get("has_more", False):
                start_cursor = response.get("next_cursor")
            else:
                break
        
        return blocks

    def _extract_text_from_blocks(self, blocks: List[Dict]) -> str:
        """
        Extract text content from Notion blocks.
        
        Args:
            blocks: List of Notion block objects
            
        Returns:
            str: Concatenated text content
        """
        content = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
                # Extract text from rich text array
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = " ".join([rt.get("plain_text", "") for rt in rich_text])
                
                if text:
                    # Add appropriate formatting based on block type
                    if block_type.startswith("heading"):
                        content.append(f"# {text}")
                    elif block_type == "bulleted_list_item":
                        content.append(f"• {text}")
                    elif block_type == "numbered_list_item":
                        content.append(f"- {text}")
                    else:
                        content.append(text)
            
            # Recursively process child blocks if present
            if block.get("has_children", False):
                try:
                    child_blocks = self._get_all_blocks(block.get("id"))
                    child_content = self._extract_text_from_blocks(child_blocks)
                    content.append(child_content)
                except Exception as e:
                    logger.error(f"Error processing child blocks: {e}")
        
        return "\n".join(content)

    def store_user_nickname(self, slack_user_id: str, nickname: str, slack_display_name: str) -> bool:
        """
        Store a user's nickname in Notion.
        
        Args:
            slack_user_id: Slack user ID
            nickname: Nickname to store
            slack_display_name: User's display name in Slack
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return False
        
        try:
            # Check if user already exists
            page_id = self.get_user_page_id(slack_user_id)
            
            if page_id:
                # Update existing page
                self.client.pages.update(
                    page_id=page_id,
                    properties={
                        "Nickname": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": nickname}
                                }
                            ]
                        }
                    }
                )
                logger.info(f"Updated nickname for user {slack_user_id}: {nickname}")
                return True
            else:
                # Create new page
                self.client.pages.create(
                    parent={"database_id": self.user_db_id},
                    properties={
                        "SlackUserID": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": slack_user_id}
                                }
                            ]
                        },
                        "SlackDisplayName": {
                            "title": [
                                {
                                    "type": "text",
                                    "text": {"content": slack_display_name}
                                }
                            ]
                        },
                        "Nickname": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": nickname}
                                }
                            ]
                        }
                    }
                )
                logger.info(f"Created new user page for {slack_user_id} with nickname: {nickname}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing nickname in Notion: {e}")
            return False

    def handle_nickname_command(self, prompt_text: str, slack_user_id: str, slack_display_name: str) -> Tuple[Optional[str], bool]:
        """
        Handle a nickname command from a user.
        
        Args:
            prompt_text: Text of the user's message
            slack_user_id: Slack user ID
            slack_display_name: User's display name in Slack
            
        Returns:
            Tuple[Optional[str], bool]: Confirmation message and success status
        """
        if not self.is_available():
            return "Sorry, the Notion integration is not available.", False
        
        # Extract nickname from text
        nickname = extract_nickname_from_text(prompt_text)
        
        if not nickname:
            return "I couldn't understand what nickname you'd like to use. Please try again with something like 'call me John'.", False
        
        # Store the nickname
        success = self.store_user_nickname(slack_user_id, nickname, slack_display_name)
        
        if success:
            return f"Got it! I'll call you {nickname} from now on.", True
        else:
            return "Sorry, I couldn't save your nickname. Please try again later.", False

    def add_todo_item(self, slack_user_id: str, todo_text: str) -> bool:
        """
        Add a todo item to a user's Notion page.
        
        This is a stub method for future implementation.
        
        Args:
            slack_user_id: Slack user ID
            todo_text: Text of the todo item
            
        Returns:
            bool: True if successful, False otherwise
        """
        # This is a stub for future implementation
        logger.info(f"Todo functionality not yet implemented: {slack_user_id}, {todo_text}")
        return False

    def get_page_content(self, page_id: str) -> Optional[str]:
        """
        Get the content of a Notion page by ID.
        
        This is a stub method for future implementation.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Optional[str]: Page content if found, None otherwise
        """
        # This is a stub for future implementation
        logger.info(f"Page content retrieval not yet implemented: {page_id}")
        return None