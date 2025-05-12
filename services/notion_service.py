"""
Notion service for ChatDSJ Slack Bot.

This module provides a service for interacting with Notion's API,
managing user data, and retrieving information from Notion databases.
"""
from typing import Dict, List, Optional, Tuple, Any

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
        todo_db_id: ID of the TODO database in Notion
        summary_db_id: ID of the summary database in Notion
    """

    def __init__(self) -> None:
        """
        Initialize the Notion service with API token from settings.
        
        Sets up the Notion client and configures database IDs.
        """
        self.client: Optional[Client] = None
        self.user_db_id: Optional[str] = settings.notion_user_db_id
        
        # Initialize additional database IDs from settings
        self.todo_db_id: Optional[str] = getattr(settings, 'notion_todo_db_id', None)
        self.summary_db_id: Optional[str] = getattr(settings, 'notion_summary_db_id', None)
        
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

    def add_todo_item(self, slack_user_id: str, todo_text: str, due_date: Optional[str] = None, priority: str = "medium") -> Dict[str, Any]:
        """
        Add a todo item to the Notion database.
        
        Args:
            slack_user_id: Slack user ID
            todo_text: Text of the todo item
            due_date: Optional due date (ISO format)
            priority: Priority level (low, medium, high)
            
        Returns:
            Dict: Created todo item or error information
        """
        if not self.is_available() or not self.todo_db_id:
            logger.error("Notion client not initialized or todo database ID not set")
            return {"success": False, "error": "Notion todo integration not available"}
        
        try:
            # Validate priority
            valid_priorities = ["low", "medium", "high"]
            if priority not in valid_priorities:
                priority = "medium"
            
            # Prepare properties for the todo item
            properties = {
                "Text": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": todo_text}
                        }
                    ]
                },
                "UserId": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": slack_user_id}
                        }
                    ]
                },
                "Completed": {
                    "checkbox": False
                },
                "Priority": {
                    "select": {
                        "name": priority
                    }
                }
            }
            
            # Add due date if provided
            if due_date:
                properties["DueDate"] = {
                    "date": {
                        "start": due_date
                    }
                }
            
            # Create the todo item
            response = self.client.pages.create(
                parent={"database_id": self.todo_db_id},
                properties=properties
            )
            
            # Extract todo item details from response
            todo_id = response.get("id")
            
            logger.info(f"Created new todo item for user {slack_user_id}: {todo_text}")
            
            return {
                "success": True,
                "id": todo_id,
                "text": todo_text,
                "completed": False,
                "priority": priority,
                "due_date": due_date,
                "created_at": response.get("created_time")
            }
                
        except Exception as e:
            logger.error(f"Error adding todo item in Notion: {e}")
            return {"success": False, "error": str(e)}

    def get_todo_items(self, slack_user_id: str, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Get todo items for a user from the Notion database.
        
        Args:
            slack_user_id: Slack user ID
            completed: Filter by completed status (True, False, or None for all)
            
        Returns:
            List[Dict]: List of todo items
        """
        if not self.is_available() or not self.todo_db_id:
            logger.error("Notion client not initialized or todo database ID not set")
            return []
        
        try:
            # Prepare filter
            filter_params = {
                "and": [
                    {
                        "property": "UserId",
                        "rich_text": {
                            "equals": slack_user_id
                        }
                    }
                ]
            }
            
            # Add completed filter if specified
            if completed is not None:
                filter_params["and"].append({
                    "property": "Completed",
                    "checkbox": {
                        "equals": completed
                    }
                })
            
            # Query the database
            response = self.client.databases.query(
                database_id=self.todo_db_id,
                filter=filter_params,
                sorts=[
                    {
                        "property": "DueDate",
                        "direction": "ascending"
                    }
                ]
            )
            
            # Process results
            todo_items = []
            for page in response.get("results", []):
                properties = page.get("properties", {})
                
                # Extract text
                text = ""
                text_prop = properties.get("Text", {})
                if text_prop and text_prop.get("title"):
                    title_items = text_prop.get("title", [])
                    if title_items:
                        text = title_items[0].get("plain_text", "")
                
                # Extract completed status
                completed = properties.get("Completed", {}).get("checkbox", False)
                
                # Extract priority
                priority = "medium"
                priority_prop = properties.get("Priority", {}).get("select", {})
                if priority_prop:
                    priority = priority_prop.get("name", "medium")
                
                # Extract due date
                due_date = None
                due_date_prop = properties.get("DueDate", {}).get("date", {})
                if due_date_prop:
                    due_date = due_date_prop.get("start")
                
                # Extract completed date
                completed_at = None
                completed_at_prop = properties.get("CompletedAt", {}).get("date", {})
                if completed_at_prop:
                    completed_at = completed_at_prop.get("start")
                
                # Add to todo items list
                todo_items.append({
                    "id": page.get("id"),
                    "text": text,
                    "completed": completed,
                    "priority": priority,
                    "due_date": due_date,
                    "completed_at": completed_at,
                    "created_at": page.get("created_time")
                })
            
            logger.debug(f"Retrieved {len(todo_items)} todo items for user {slack_user_id}")
            return todo_items
            
        except Exception as e:
            logger.error(f"Error getting todo items from Notion: {e}")
            return []

    def update_todo_item(self, todo_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a todo item in the Notion database.
        
        Args:
            todo_id: ID of the todo item to update
            properties: Properties to update
            
        Returns:
            Dict: Updated todo item or error information
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return {"success": False, "error": "Notion integration not available"}
        
        try:
            # Prepare Notion properties
            notion_properties = {}
            
            # Handle text update
            if "text" in properties:
                notion_properties["Text"] = {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": properties["text"]}
                        }
                    ]
                }
            
            # Handle completed status update
            if "completed" in properties:
                notion_properties["Completed"] = {
                    "checkbox": properties["completed"]
                }
                
                # If marking as completed, update CompletedAt date
                if properties["completed"]:
                    import datetime
                    current_date = datetime.datetime.now().isoformat()
                    notion_properties["CompletedAt"] = {
                        "date": {
                            "start": current_date
                        }
                    }
                else:
                    # If marking as not completed, clear CompletedAt date
                    notion_properties["CompletedAt"] = {
                        "date": None
                    }
            
            # Handle priority update
            if "priority" in properties:
                valid_priorities = ["low", "medium", "high"]
                priority = properties["priority"]
                if priority not in valid_priorities:
                    priority = "medium"
                
                notion_properties["Priority"] = {
                    "select": {
                        "name": priority
                    }
                }
            
            # Handle due date update
            if "due_date" in properties:
                due_date = properties["due_date"]
                if due_date:
                    notion_properties["DueDate"] = {
                        "date": {
                            "start": due_date
                        }
                    }
                else:
                    notion_properties["DueDate"] = {
                        "date": None
                    }
            
            # Update the todo item
            response = self.client.pages.update(
                page_id=todo_id,
                properties=notion_properties
            )
            
            logger.info(f"Updated todo item: {todo_id}")
            
            # Return success response
            return {
                "success": True,
                "id": todo_id,
                "updated": list(properties.keys())
            }
                
        except Exception as e:
            logger.error(f"Error updating todo item in Notion: {e}")
            return {"success": False, "error": str(e)}

    def delete_todo_item(self, todo_id: str) -> Dict[str, Any]:
        """
        Delete a todo item from the Notion database.
        
        Args:
            todo_id: ID of the todo item to delete
            
        Returns:
            Dict: Success status and information
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return {"success": False, "error": "Notion integration not available"}
        
        try:
            # Delete the page (archive it in Notion)
            self.client.pages.update(
                page_id=todo_id,
                archived=True
            )
            
            logger.info(f"Deleted todo item: {todo_id}")
            
            return {
                "success": True,
                "id": todo_id,
                "message": "Todo item deleted successfully"
            }
                
        except Exception as e:
            logger.error(f"Error deleting todo item in Notion: {e}")
            return {"success": False, "error": str(e)}

    def save_content_summary(
        self,
        slack_user_id: str,
        title: str,
        summary: str,
        source_url: str,
        source_type: str = "webpage",
        tags: List[str] = []
    ) -> Dict[str, Any]:
        """
        Save a content summary to the Notion database.
        
        Args:
            slack_user_id: Slack user ID
            title: Title of the content
            summary: Summary text
            source_url: Source URL
            source_type: Type of source (webpage, youtube, etc.)
            tags: List of tags
            
        Returns:
            Dict: Created summary or error information
        """
        if not self.is_available() or not self.summary_db_id:
            logger.error("Notion client not initialized or summary database ID not set")
            return {"success": False, "error": "Notion summary integration not available"}
        
        try:
            # Prepare tags for Notion
            notion_tags = []
            for tag in tags:
                notion_tags.append({"name": tag})
            
            # Prepare properties for the summary
            properties = {
                "Title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": title}
                        }
                    ]
                },
                "UserId": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": slack_user_id}
                        }
                    ]
                },
                "SourceUrl": {
                    "url": source_url
                },
                "SourceType": {
                    "select": {
                        "name": source_type
                    }
                }
            }
            
            # Add tags if provided
            if tags:
                properties["Tags"] = {
                    "multi_select": notion_tags
                }
            
            # Create the summary page
            response = self.client.pages.create(
                parent={"database_id": self.summary_db_id},
                properties=properties
            )
            
            # Add the summary content as blocks
            summary_chunks = self._split_text_into_chunks(summary)
            blocks = []
            
            for chunk in summary_chunks:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": chunk}
                            }
                        ]
                    }
                })
            
            # Add blocks to the page
            self.client.blocks.children.append(
                block_id=response.get("id"),
                children=blocks
            )
            
            logger.info(f"Created new summary for user {slack_user_id}: {title}")
            
            return {
                "success": True,
                "id": response.get("id"),
                "title": title,
                "source_url": source_url,
                "source_type": source_type,
                "tags": tags,
                "created_at": response.get("created_time")
            }
                
        except Exception as e:
            logger.error(f"Error saving summary in Notion: {e}")
            return {"success": False, "error": str(e)}

    def get_summaries(self, slack_user_id: str, limit: int = 10, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get content summaries for a user from the Notion database.
        
        Args:
            slack_user_id: Slack user ID
            limit: Maximum number of summaries to retrieve
            tag: Optional tag to filter by
            
        Returns:
            List[Dict]: List of summaries
        """
        if not self.is_available() or not self.summary_db_id:
            logger.error("Notion client not initialized or summary database ID not set")
            return []
        
        try:
            # Prepare filter
            filter_params = {
                "and": [
                    {
                        "property": "UserId",
                        "rich_text": {
                            "equals": slack_user_id
                        }
                    }
                ]
            }
            
            # Add tag filter if specified
            if tag:
                filter_params["and"].append({
                    "property": "Tags",
                    "multi_select": {
                        "contains": tag
                    }
                })
            
            # Query the database
            response = self.client.databases.query(
                database_id=self.summary_db_id,
                filter=filter_params,
                sorts=[
                    {
                        "property": "Created",
                        "direction": "descending"
                    }
                ],
                page_size=limit
            )
            
            # Process results
            summaries = []
            for page in response.get("results", []):
                properties = page.get("properties", {})
                
                # Extract title
                title = ""
                title_prop = properties.get("Title", {})
                if title_prop and title_prop.get("title"):
                    title_items = title_prop.get("title", [])
                    if title_items:
                        title = title_items[0].get("plain_text", "")
                
                # Extract source URL
                source_url = properties.get("SourceUrl", {}).get("url", "")
                
                # Extract source type
                source_type = "webpage"
                source_type_prop = properties.get("SourceType", {}).get("select", {})
                if source_type_prop:
                    source_type = source_type_prop.get("name", "webpage")
                
                # Extract tags
                tags = []
                tags_prop = properties.get("Tags", {}).get("multi_select", [])
                for tag_item in tags_prop:
                    tag_name = tag_item.get("name")
                    if tag_name:
                        tags.append(tag_name)
                
                # Get summary content (limited to avoid large responses)
                summary_preview = self._get_page_preview(page.get("id"), max_blocks=3)
                
                # Add to summaries list
                summaries.append({
                    "id": page.get("id"),
                    "title": title,
                    "source_url": source_url,
                    "source_type": source_type,
                    "tags": tags,
                    "preview": summary_preview,
                    "created_at": page.get("created_time")
                })
            
            logger.debug(f"Retrieved {len(summaries)} summaries for user {slack_user_id}")
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting summaries from Notion: {e}")
            return []

    def get_summary(self, summary_id: str) -> Dict[str, Any]:
        """
        Get a specific summary from the Notion database.
        
        Args:
            summary_id: ID of the summary to retrieve
            
        Returns:
            Dict: Summary information or error
        """
        if not self.is_available():
            logger.error("Notion client not initialized")
            return {"success": False, "error": "Notion integration not available"}
        
        try:
            # Get the page properties
            page = self.client.pages.retrieve(page_id=summary_id)
            properties = page.get("properties", {})
            
            # Extract title
            title = ""
            title_prop = properties.get("Title", {})
            if title_prop and title_prop.get("title"):
                title_items = title_prop.get("title", [])
                if title_items:
                    title = title_items[0].get("plain_text", "")
            
            # Extract source URL
            source_url = properties.get("SourceUrl", {}).get("url", "")
            
            # Extract source type
            source_type = "webpage"
            source_type_prop = properties.get("SourceType", {}).get("select", {})
            if source_type_prop:
                source_type = source_type_prop.get("name", "webpage")
            
            # Extract tags
            tags = []
            tags_prop = properties.get("Tags", {}).get("multi_select", [])
            for tag_item in tags_prop:
                tag_name = tag_item.get("name")
                if tag_name:
                    tags.append(tag_name)
            
            # Get the full summary content
            content = self._get_page_content(summary_id)
            
            return {
                "success": True,
                "id": summary_id,
                "title": title,
                "content": content,
                "source_url": source_url,
                "source_type": source_type,
                "tags": tags,
                "created_at": page.get("created_time")
            }
                
        except Exception as e:
            logger.error(f"Error getting summary from Notion: {e}")
            return {"success": False, "error": str(e)}

    def _get_page_preview(self, page_id: str, max_blocks: int = 3) -> str:
        """
        Get a preview of a Notion page (first few blocks).
        
        Args:
            page_id: Notion page ID
            max_blocks: Maximum number of blocks to include
            
        Returns:
            str: Page preview text
        """
        try:
            # Get blocks
            response = self.client.blocks.children.list(block_id=page_id)
            blocks = response.get("results", [])[:max_blocks]
            
            # Extract text from blocks
            content = self._extract_text_from_blocks(blocks)
            
            # Add ellipsis if there are more blocks
            if response.get("has_more", False) or len(response.get("results", [])) > max_blocks:
                content += "\n..."
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting page preview from Notion: {e}")
            return "Unable to retrieve preview."

    def _get_page_content(self, page_id: str) -> str:
        """
        Get the full content of a Notion page.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            str: Page content text
        """
        try:
            # Get all blocks
            blocks = self._get_all_blocks(page_id)
            
            # Extract text from blocks
            content = self._extract_text_from_blocks(blocks)
            
            return content
            
        except Exception as e:
            logger.error(f"Error getting page content from Notion: {e}")
            return "Unable to retrieve content."

    def _split_text_into_chunks(self, text: str, max_length: int = 2000) -> List[str]:
        """
        Split text into chunks of maximum length.
        
        This is needed because Notion has a maximum length for rich_text in blocks.
        
        Args:
            text: Text to split
            max_length: Maximum length of each chunk
            
        Returns:
            List[str]: List of text chunks
        """
        if not text:
            return []
        
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        paragraphs = text.split("\n\n")
        
        current_chunk = ""
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max_length, start a new chunk
            if len(current_chunk) + len(paragraph) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks