"""
Todo agent implementation for ChatDSJ Slack Bot.

This module provides the TodoAgent class that handles todo management
operations using the Notion service.
"""
from typing import Dict, List, Optional, Any

from crewai.tools import Tool

from agents.base_agent import BaseAgent
from services.notion_service import NotionService
from utils.logging_config import configure_logging
from utils.text_processing import extract_todo_from_text

logger = configure_logging()


class TodoAgent(BaseAgent):
    """
    Agent specialized in todo management.
    
    This agent wraps the NotionService and provides tools for creating,
    retrieving, updating, and deleting todo items.
    
    Attributes:
        notion_service: The NotionService instance for API interactions
    """

    def __init__(self, notion_service: NotionService, verbose: bool = False) -> None:
        """
        Initialize a Todo agent with the NotionService.
        
        Args:
            notion_service: The NotionService instance for API interactions
            verbose: Whether to enable verbose logging
        """
        self.notion_service = notion_service
        
        super().__init__(
            name="Todo Manager",
            role="Task and todo management specialist",
            goal="Help users manage their tasks and todo items efficiently",
            verbose=verbose
        )

    def get_backstory(self) -> str:
        """
        Get the backstory for the Todo agent.
        
        Returns:
            str: Specialized backstory for the Todo agent
        """
        return (
            "You are the Todo Manager, an expert in helping users organize and manage "
            "their tasks and todo items. You understand how to create, track, and prioritize "
            "tasks, ensuring that users stay productive and focused on what matters most. "
            "Your expertise allows you to interpret natural language requests for task "
            "management, extract todo items from conversation, and provide users with "
            "clear summaries of their pending and completed tasks."
        )

    def get_tools(self) -> List[Tool]:
        """
        Get the tools available to the Todo agent.
        
        Returns:
            List[Tool]: List of tools for todo management
        """
        return [
            Tool(
                name="add_todo",
                description="Add a new todo item",
                func=self.add_todo
            ),
            Tool(
                name="get_todos",
                description="Get todo items for a user",
                func=self.get_todos
            ),
            Tool(
                name="update_todo",
                description="Update a todo item",
                func=self.update_todo
            ),
            Tool(
                name="delete_todo",
                description="Delete a todo item",
                func=self.delete_todo
            ),
            Tool(
                name="extract_todo_from_message",
                description="Extract a todo item from a message",
                func=self.extract_todo_from_message
            )
        ]

    def add_todo(
        self,
        slack_user_id: str,
        todo_text: str,
        due_date: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Add a new todo item.
        
        Args:
            slack_user_id: Slack user ID
            todo_text: Text of the todo item
            due_date: Optional due date (ISO format)
            priority: Priority level (low, medium, high)
            
        Returns:
            Dict: Created todo item information
        """
        return self.notion_service.add_todo_item(slack_user_id, todo_text, due_date, priority)

    def get_todos(
        self,
        slack_user_id: str,
        completed: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get todo items for a user.
        
        Args:
            slack_user_id: Slack user ID
            completed: Filter by completed status (True, False, or None for all)
            
        Returns:
            List[Dict]: List of todo items
        """
        return self.notion_service.get_todo_items(slack_user_id, completed)

    def update_todo(self, todo_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a todo item.
        
        Args:
            todo_id: ID of the todo item to update
            properties: Properties to update (text, completed, due_date, priority)
            
        Returns:
            Dict: Updated todo item information
        """
        return self.notion_service.update_todo_item(todo_id, properties)

    def delete_todo(self, todo_id: str) -> Dict[str, Any]:
        """
        Delete a todo item.
        
        Args:
            todo_id: ID of the todo item to delete
            
        Returns:
            Dict: Success status and information
        """
        return self.notion_service.delete_todo_item(todo_id)

    def extract_todo_from_message(self, message: str) -> Optional[str]:
        """
        Extract a todo item from a message.
        
        Args:
            message: Message text to extract todo from
            
        Returns:
            Optional[str]: Extracted todo text or None if not found
        """
        return extract_todo_from_text(message)

    def handle_todo_command(
        self,
        prompt_text: str,
        slack_user_id: str
    ) -> Dict[str, Any]:
        """
        Handle a todo command from a user.
        
        This method parses the prompt text to determine the todo operation
        and executes it accordingly.
        
        Args:
            prompt_text: Text of the user's message
            slack_user_id: Slack user ID
            
        Returns:
            Dict[str, Any]: Result of the todo operation
        """
        prompt_lower = prompt_text.lower()
        
        # Check for list/show todos
        if any(keyword in prompt_lower for keyword in ["list todos", "show todos", "my todos", "get todos"]):
            # Determine if we should show completed, incomplete, or all todos
            completed = None
            if "completed" in prompt_lower:
                completed = True
            elif "incomplete" in prompt_lower or "pending" in prompt_lower or "not done" in prompt_lower:
                completed = False
            
            # Get todos
            todos = self.get_todos(slack_user_id, completed)
            
            # Format response
            if not todos:
                return {
                    "success": True,
                    "message": "You don't have any todos" if completed is None else 
                              ("You don't have any completed todos" if completed else "You don't have any pending todos"),
                    "todos": []
                }
            
            # Create a formatted message
            status = "completed" if completed is True else "pending" if completed is False else ""
            status_msg = f" {status}" if status else ""
            
            return {
                "success": True,
                "message": f"Here are your{status_msg} todos:",
                "todos": todos
            }
        
        # Check for add/create todo
        elif any(keyword in prompt_lower for keyword in ["add todo", "create todo", "new todo"]):
            # Extract the todo text - everything after "add todo", "create todo", etc.
            for prefix in ["add todo", "create todo", "new todo"]:
                if prefix in prompt_lower:
                    todo_text = prompt_text[prompt_lower.index(prefix) + len(prefix):].strip()
                    break
            else:
                todo_text = extract_todo_from_text(prompt_text)
            
            if not todo_text:
                return {
                    "success": False,
                    "message": "I couldn't understand what todo you'd like to add. Please try again with something like 'add todo: finish the report'."
                }
            
            # Extract priority if specified
            priority = "medium"
            for priority_level in ["high", "medium", "low"]:
                if f"priority: {priority_level}" in prompt_lower or f"priority {priority_level}" in prompt_lower:
                    priority = priority_level
                    break
            
            # Extract due date if specified (this would need a more sophisticated date parser in a real implementation)
            due_date = None
            # Simple implementation for demonstration
            if "due" in prompt_lower:
                import re
                date_match = re.search(r'due(?:\s+on)?[:]?\s+(\d{4}-\d{2}-\d{2})', prompt_lower)
                if date_match:
                    due_date = date_match.group(1)
            
            # Add the todo
            result = self.add_todo(slack_user_id, todo_text, due_date, priority)
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": f"Added todo: {todo_text}",
                    "todo": result
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to add todo: {result.get('error', 'Unknown error')}",
                    "error": result.get("error")
                }
        
        # Check for complete/finish todo
        elif any(keyword in prompt_lower for keyword in ["complete todo", "finish todo", "mark todo", "done todo"]):
            # This would need to handle todo selection in a real implementation
            # For now, just return a message
            return {
                "success": False,
                "message": "To mark a todo as complete, please specify the todo number or exact text. For example: 'mark todo 3 as complete' or 'complete todo: finish the report'"
            }
        
        # Check for delete/remove todo
        elif any(keyword in prompt_lower for keyword in ["delete todo", "remove todo"]):
            # This would need to handle todo selection in a real implementation
            # For now, just return a message
            return {
                "success": False,
                "message": "To delete a todo, please specify the todo number or exact text. For example: 'delete todo 3' or 'remove todo: finish the report'"
            }
        
        # Check if this is just a todo to add without specific command
        else:
            todo_text = extract_todo_from_text(prompt_text)
            if todo_text:
                result = self.add_todo(slack_user_id, todo_text)
                
                if result.get("success"):
                    return {
                        "success": True,
                        "message": f"Added todo: {todo_text}",
                        "todo": result
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to add todo: {result.get('error', 'Unknown error')}",
                        "error": result.get("error")
                    }
            
            # Not a recognized todo command
            return {
                "success": False,
                "message": "I couldn't understand your todo request. Try 'add todo: [task]', 'list todos', 'complete todo [number]', or 'delete todo [number]'."
            }