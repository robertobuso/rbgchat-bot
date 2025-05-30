"""
Response tasks implementation for ChatDSJ Slack Bot.

This module provides the ResponseTasks class that defines tasks related to
response generation, such as formatting conversation history and generating
responses using OpenAI.
"""
from typing import Dict, List, Optional

from crewai import Task

from utils.logging_config import configure_logging
from utils.token_counter import ensure_messages_within_limit

logger = configure_logging()


class ResponseTasks:
    """
    Tasks related to response generation.

    This class provides static methods that create Task objects for
    formatting conversation history and generating responses using OpenAI.
    """

    @staticmethod
    def format_history_task(agent) -> Task:
        """
        Create a task for formatting conversation history for OpenAI.

        This task prepares the conversation history in the format expected
        by the OpenAI API, ensuring it's within token limits.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Format the conversation history for OpenAI. This involves converting "
                "Slack message objects to the format expected by the OpenAI API. Replace "
                "user IDs with display names, handle special message types, and ensure "
                "the formatted history is within token limits. The system message should "
                "be preserved at the beginning of the conversation."
            ),
            expected_output=(
                "Properly formatted conversation history for OpenAI. This should be a list "
                "of message objects with 'role' and 'content' fields, where role is one of "
                "'system', 'user', or 'assistant'. The history should be ordered chronologically "
                "and within token limits for the specified OpenAI model."
            ),
            agent=agent,
            async_execution=False
        )

    @staticmethod
    def generate_response_task(agent) -> Task:
        """
        Create a task for generating a response using OpenAI.

        This task handles sending the formatted conversation history to
        OpenAI and retrieving a generated response.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Generate a response to a user's message using OpenAI. This involves "
                "sending the formatted conversation history, user-specific context, "
                "and the current query to the OpenAI API. The response should be "
                "contextually appropriate, helpful, and personalized based on the "
                "user's history and preferences. Handle any API errors gracefully "
                "and ensure the response is within reasonable length limits."
            ),
            expected_output=(
                "A response generated by OpenAI. This should be a string containing "
                "the assistant's response to the user's query, formatted appropriately "
                "for sending to Slack. The response should be contextually relevant, "
                "helpful, and personalized based on available user context."
            ),
            agent=agent,
            async_execution=False
        )