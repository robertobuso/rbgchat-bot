"""
Crew Manager for ChatDSJ Slack Bot.

This module implements the CrewAI orchestration layer that coordinates
the agents and tasks to handle user interactions. It manages the workflow
from receiving a Slack mention to delivering a response.
"""
import re
from typing import Dict, Any, List, Optional, Tuple

from crewai import Crew
from loguru import logger

from config.settings import get_settings
from agents.slack_agent import SlackAgent
from agents.memory_agent import MemoryAgent
from agents.response_agent import ResponseAgent
from agents.content_agent import ContentAgent
from agents.todo_agent import TodoAgent
from utils.text_processing import extract_nickname_from_text
from utils.metrics import timed, metrics

# Initialize settings
settings = get_settings()


class CrewManager:
    """
    Manager for coordinating CrewAI agents and tasks.
    
    This class orchestrates the workflow for processing Slack mentions,
    handling nickname commands, managing conversation history, and
    generating responses.
    
    Attributes:
        slack_agent: Agent for Slack interactions
        memory_agent: Agent for user memory management
        response_agent: Agent for response generation
        content_agent: Agent for content extraction and summarization
        todo_agent: Agent for todo management
        verbose: Whether to enable verbose logging
        crew: CrewAI Crew instance for agent coordination
    """

    def __init__(
        self,
        slack_agent: SlackAgent,
        memory_agent: MemoryAgent,
        response_agent: ResponseAgent,
        content_agent: Optional[ContentAgent] = None,
        todo_agent: Optional[TodoAgent] = None
    ) -> None:
        """
        Initialize the Crew Manager with specialized agents.
        
        Args:
            slack_agent: Agent for Slack interactions
            memory_agent: Agent for user memory management
            response_agent: Agent for response generation
            content_agent: Optional agent for content processing
            todo_agent: Optional agent for todo management
        """
        self.slack_agent = slack_agent
        self.memory_agent = memory_agent
        self.response_agent = response_agent
        self.content_agent = content_agent
        self.todo_agent = todo_agent
        self.verbose = settings.enable_crew_verbose
        
        # Initialize the crew
        self._initialize_crew()

    def _initialize_crew(self) -> None:
        """
        Initialize the CrewAI Crew with the specialized agents.
        
        This method creates a Crew instance with all available agents,
        configuring it for sequential processing.
        """
        try:
            # Get agent instances
            agents = [
                self.slack_agent.get_agent(),
                self.memory_agent.get_agent(),
                self.response_agent.get_agent()
            ]
            
            # Add optional agents if available
            if self.content_agent:
                agents.append(self.content_agent.get_agent())
            
            if self.todo_agent:
                agents.append(self.todo_agent.get_agent())
            
            # Filter out None values (in case any agent failed to initialize)
            agents = [agent for agent in agents if agent]
            
            # Create the crew
            self.crew = Crew(
                agents=agents,
                process=Crew.SEQUENTIAL,
                verbose=self.verbose
            )
            
            logger.info(f"Crew initialized with {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize crew: {e}")
            self.crew = None

    @timed("process_mention")
    def process_mention(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Slack mention event.
        
        This method handles the entire workflow from receiving a mention
        to delivering a response, including context gathering, nickname
        commands, content processing, todo management, and response generation.
        
        Args:
            event: Slack event data containing the mention
            
        Returns:
            Dict[str, Any]: Response data including the sent message
        """
        # Extract key information from the event
        channel_id = event.get("channel")
        user_id = event.get("user")
        message_ts = event.get("ts")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts")
        
        # Clean prompt text
        prompt = self.slack_agent.clean_prompt_text(text)
        
        # Send acknowledgment
        self.slack_agent.send_ephemeral_message(
            channel_id, 
            user_id, 
            "I heard you! I'm working on a response... 🧠"
        )
        
        # Check for nickname command
        nickname_response, nickname_success = self.memory_agent.handle_nickname_command(
            prompt, 
            user_id, 
            self.slack_agent.get_user_display_name(user_id)
        )
        
        if nickname_response:
            # Handle nickname command
            response = self.slack_agent.send_message(channel_id, nickname_response, thread_ts)
            self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
            return response
        
        # Check for content processing command (summarization)
        if self.content_agent and self._is_content_processing_request(prompt):
            return self._handle_content_processing(prompt, channel_id, user_id, thread_ts, message_ts)
        
        # Check for todo management command
        if self.todo_agent and self._is_todo_management_request(prompt):
            return self._handle_todo_management(prompt, channel_id, user_id, thread_ts, message_ts)
        
        # Default to conversational response
        return self._handle_conversation(prompt, channel_id, user_id, thread_ts, message_ts, event)

    def _is_content_processing_request(self, prompt: str) -> bool:
        """
        Check if the prompt is requesting content processing.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            bool: True if content processing is requested, False otherwise
        """
        # Look for summarization keywords and URLs
        summarize_keywords = ["summarize", "summary", "tldr", "extract", "analyze"]
        has_url = re.search(r'https?://\S+', prompt) is not None
        
        return has_url and any(keyword in prompt.lower() for keyword in summarize_keywords)

    def _is_todo_management_request(self, prompt: str) -> bool:
        """
        Check if the prompt is requesting todo management.
        
        Args:
            prompt: The user's prompt
            
        Returns:
            bool: True if todo management is requested, False otherwise
        """
        # Look for todo keywords
        todo_keywords = ["todo", "task", "remind me", "add item", "list todos", "show todos", "my todos", "mark as done"]
        
        return any(keyword in prompt.lower() for keyword in todo_keywords)

    @timed("handle_content_processing")
    def _handle_content_processing(
        self,
        prompt: str,
        channel_id: str,
        user_id: str,
        thread_ts: Optional[str],
        message_ts: str
    ) -> Dict[str, Any]:
        """
        Handle content processing requests.
        
        Args:
            prompt: The user's prompt
            channel_id: Slack channel ID
            user_id: Slack user ID
            thread_ts: Optional thread timestamp
            message_ts: Message timestamp
            
        Returns:
            Dict[str, Any]: Response data
        """
        if not self.content_agent:
            response = self.slack_agent.send_message(
                channel_id,
                "I'm sorry, but content processing is not available at the moment.",
                thread_ts
            )
            self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
            return response
        
        # Extract URLs from the prompt
        urls = self.content_agent.extract_urls_from_text(prompt)
        
        if not urls:
            response = self.slack_agent.send_message(
                channel_id,
                "I couldn't find any URLs to process in your message. Please include a valid URL when asking for summarization.",
                thread_ts
            )
            self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
            return response
        
        # Process the first URL (for now, we'll just handle one at a time)
        url = urls[0]
        url_type = self.content_agent.determine_source_type(url)
        
        # Send a processing message
        self.slack_agent.send_message(
            channel_id,
            f"Processing {url_type} content from {url}...",
            thread_ts
        )
        
        # Extract and summarize the content
        summary_result = self.content_agent.extract_and_summarize(url)
        
        if not summary_result.get("success", False):
            error_message = summary_result.get("error", "Unknown error")
            response = self.slack_agent.send_message(
                channel_id,
                f"I'm sorry, but I couldn't process the content: {error_message}",
                thread_ts
            )
            self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
            return response
        
        # Format the summary
        title = summary_result.get("title", "Untitled")
        summary = summary_result.get("summary", "No summary generated")
        source_url = summary_result.get("sourceUrl", url)
        source_type = summary_result.get("sourceType", url_type)
        
        formatted_summary = f"*Summary of {title}*\n\n{summary}\n\n*Source:* {source_url}"
        
        # Send the summary
        response = self.slack_agent.send_message(channel_id, formatted_summary, thread_ts)
        
        # Store the summary in Notion if possible
        try:
            if self.memory_agent.notion_service.summary_db_id:
                self.memory_agent.notion_service.save_content_summary(
                    slack_user_id=user_id,
                    title=title,
                    summary=summary,
                    source_url=source_url,
                    source_type=source_type,
                    tags=summary_result.get("tags", [])
                )
        except Exception as e:
            logger.error(f"Failed to store summary in Notion: {e}")
        
        self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
        return response

    @timed("handle_todo_management")
    def _handle_todo_management(
        self,
        prompt: str,
        channel_id: str,
        user_id: str,
        thread_ts: Optional[str],
        message_ts: str
    ) -> Dict[str, Any]:
        """
        Handle todo management requests.
        
        Args:
            prompt: The user's prompt
            channel_id: Slack channel ID
            user_id: Slack user ID
            thread_ts: Optional thread timestamp
            message_ts: Message timestamp
            
        Returns:
            Dict[str, Any]: Response data
        """
        if not self.todo_agent:
            response = self.slack_agent.send_message(
                channel_id,
                "I'm sorry, but todo management is not available at the moment.",
                thread_ts
            )
            self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
            return response
        
        # Handle the todo command
        todo_result = self.todo_agent.handle_todo_command(prompt, user_id)
        
        if not todo_result.get("success", False):
            error_message = todo_result.get("message", "I couldn't process your todo request.")
            response = self.slack_agent.send_message(channel_id, error_message, thread_ts)
            self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
            return response
        
        # Format the response message
        message = todo_result.get("message", "Todo operation completed successfully.")
        
        # Add todo list if available
        todos = todo_result.get("todos", [])
        if todos:
            message += "\n\n"
            for i, todo in enumerate(todos, 1):
                status = "✅" if todo.get("completed", False) else "⬜"
                priority_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}
                priority = priority_map.get(todo.get("priority", "medium"), "")
                due_date = f" (Due: {todo.get('due_date')})" if todo.get("due_date") else ""
                message += f"{i}. {status} {priority} {todo.get('text', '')}{due_date}\n"
        
        # Send the response
        response = self.slack_agent.send_message(channel_id, message, thread_ts)
        self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
        return response

    @timed("handle_conversation")
    def _handle_conversation(
        self,
        prompt: str,
        channel_id: str,
        user_id: str,
        thread_ts: Optional[str],
        message_ts: str,
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle conversational interactions.
        
        Args:
            prompt: The user's prompt
            channel_id: Slack channel ID
            user_id: Slack user ID
            thread_ts: Optional thread timestamp
            message_ts: Message timestamp
            event: The original Slack event
            
        Returns:
            Dict[str, Any]: Response data
        """
        # Determine context type
        is_new_main_channel_question = not thread_ts
        
        # Fetch appropriate history
        if is_new_main_channel_question:
            # Check if asking about past history
            history_keywords = ["previous", "before", "earlier", "past", "history"]
            has_history_query = any(keyword in prompt.lower() for keyword in history_keywords)
            
            # Set limit based on query type
            limit = 1000 if has_history_query else 100
            channel_history = self.slack_agent.fetch_channel_history(channel_id, limit)
            thread_history = []
        else:
            # Thread context
            channel_history = self.slack_agent.fetch_channel_history(channel_id, limit=100)
            thread_history = self.slack_agent.fetch_thread_history(channel_id, thread_ts, limit=1000)
        
        # Merge histories and deduplicate
        all_messages = channel_history + thread_history
        merged_messages = []
        seen_ts = set()
        
        for msg in all_messages:
            ts = msg.get("ts")
            if ts and ts not in seen_ts:
                merged_messages.append(msg)
                seen_ts.add(ts)
        
        # Sort by timestamp
        merged_messages.sort(key=lambda x: float(x.get("ts", "0")))
        
        # Build user display names dictionary
        user_display_names = {}
        for msg in merged_messages:
            if "user" in msg and msg["user"] not in user_display_names:
                user_display_names[msg["user"]] = self.slack_agent.get_user_display_name(msg["user"])
        
        # Format history for OpenAI
        formatted_history = self.response_agent.format_conversation(
            merged_messages,
            user_display_names,
            self.slack_agent.slack_service.bot_user_id
        )
        
        # Get user context from Notion
        user_preferred_name = self.memory_agent.get_user_preferred_name(user_id)
        user_page_content = self.memory_agent.get_user_page_content(user_id)
        
        # Construct user context
        user_display_name = self.slack_agent.get_user_display_name(user_id)
        user_specific_context = f"You are talking to {user_preferred_name or user_display_name}."
        
        if user_page_content:
            user_specific_context += f" Here is some context about this user: {user_page_content}"
        
        # Generate response
        response_text = self.response_agent.generate_response(
            prompt=prompt,
            conversation_history=formatted_history,
            user_specific_context=user_specific_context
        )
        
        # Send response
        if response_text:
            response = self.slack_agent.send_message(channel_id, response_text, thread_ts)
        else:
            response = self.slack_agent.send_message(
                channel_id,
                "I'm sorry, I couldn't generate a response for that.",
                thread_ts
            )
        
        # Update stats
        self.slack_agent.slack_service.update_channel_stats(channel_id, user_id, message_ts)
        
        # Record metrics
        metrics.track_api_call("openai_completion")
        
        return response