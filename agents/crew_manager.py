"""
Crew Manager for ChatDSJ Slack Bot.

This module implements the CrewAI orchestration layer that coordinates
the agents and tasks to handle user interactions. It manages the workflow
from receiving a Slack mention to delivering a response.
"""
from typing import Dict, Any, List, Optional, Tuple

from crewai import Crew
from loguru import logger

from config.settings import get_settings
from agents.slack_agent import SlackAgent
from agents.memory_agent import MemoryAgent
from agents.response_agent import ResponseAgent
from utils.text_processing import extract_nickname_from_text

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
        verbose: Whether to enable verbose logging
        crew: CrewAI Crew instance for agent coordination
    """

    def __init__(
        self,
        slack_agent: SlackAgent,
        memory_agent: MemoryAgent,
        response_agent: ResponseAgent
    ) -> None:
        """
        Initialize the Crew Manager with specialized agents.
        
        Args:
            slack_agent: Agent for Slack interactions
            memory_agent: Agent for user memory management
            response_agent: Agent for response generation
        """
        self.slack_agent = slack_agent
        self.memory_agent = memory_agent
        self.response_agent = response_agent
        self.verbose = settings.enable_crew_verbose
        
        # Initialize the crew
        self._initialize_crew()

    def _initialize_crew(self) -> None:
        """
        Initialize the CrewAI Crew with the specialized agents.
        
        This method creates a Crew instance with the slack, memory, and
        response agents, configuring it for sequential processing.
        """
        try:
            # Get agent instances
            agents = [
                self.slack_agent.get_agent(),
                self.memory_agent.get_agent(),
                self.response_agent.get_agent()
            ]
            
            # Filter out None values (in case any agent failed to initialize)
            agents = [agent for agent in agents if agent]
            
            # Create the crew
            self.crew = Crew(
                agents=agents,
                process=Crew.SEQUENTIAL,
                verbose=self.verbose
            )
            
            logger.info("Crew initialized with agents")
            
        except Exception as e:
            logger.error(f"Failed to initialize crew: {e}")
            self.crew = None

    def process_mention(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Slack mention event.
        
        This method handles the entire workflow from receiving a mention
        to delivering a response, including context gathering, nickname
        commands, and response generation.
        
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
        
        # Determine context type
        is_new_main_channel_question = not event.get("thread_ts")
        
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
        
        return response