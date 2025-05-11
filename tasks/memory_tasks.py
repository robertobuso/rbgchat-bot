"""
Memory tasks implementation for ChatDSJ Slack Bot.

This module provides the MemoryTasks class that defines tasks related to
user memory operations, such as checking for nickname commands, storing
nicknames, and fetching user context from Notion.
"""
from typing import Dict, Optional, Tuple

from crewai import Task

from utils.logging_config import configure_logging
from utils.text_processing import extract_nickname_from_text

logger = configure_logging()


class MemoryTasks:
    """
    Tasks related to user memory operations.

    This class provides static methods that create Task objects for
    checking nickname commands, storing user nicknames, and fetching
    user-specific context from Notion.
    """

    @staticmethod
    def check_nickname_command_task(agent) -> Task:
        """
        Create a task for checking if a message contains a nickname command.

        This task analyzes the user's message to determine if it contains
        a request to set or change their nickname.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Check if a user's message contains a nickname command. This involves "
                "analyzing the text to identify patterns like 'call me X', 'my name is X', "
                "or explicit nickname commands. If a nickname command is detected, extract "
                "the requested nickname from the message."
            ),
            expected_output=(
                "A determination of whether a nickname command is present and the extracted "
                "nickname. The output should include a boolean indicating if a nickname command "
                "was detected, the extracted nickname (if any), and the user_id of the requester."
            ),
            agent=agent,
            async_execution=False
        )

    @staticmethod
    def store_nickname_task(agent) -> Task:
        """
        Create a task for storing a user's nickname in Notion.

        This task handles storing or updating a user's preferred nickname
        in their Notion page.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Store a user's nickname in their Notion page. This involves creating "
                "or updating the user's page in the Notion database with their preferred "
                "nickname. If the user doesn't have a page yet, create one. If they already "
                "have a page, update the nickname field. Ensure that the Slack user ID is "
                "properly linked to the Notion page for future reference."
            ),
            expected_output=(
                "A confirmation that the nickname was stored successfully in Notion. "
                "This should include the user_id, the stored nickname, a link to the "
                "Notion page (if available), and a status indicating success or failure."
            ),
            agent=agent,
            async_execution=False
        )

    @staticmethod
    def fetch_user_context_task(agent) -> Task:
        """
        Create a task for fetching user-specific context from Notion.

        This task retrieves user information and preferences from their
        Notion page to provide personalized context for responses.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Fetch user-specific context from Notion. This involves retrieving "
                "the user's page from the Notion database based on their Slack user ID. "
                "Extract relevant information such as their preferred name, previous "
                "interactions, preferences, and any other stored context that could help "
                "personalize the response. If the user doesn't have a Notion page yet, "
                "return basic information based on their Slack profile."
            ),
            expected_output=(
                "The user's context information from Notion. This should include their "
                "preferred name (or Slack display name if no preferred name is set), "
                "any stored preferences or information about previous interactions, "
                "and any other relevant context that could help personalize responses."
            ),
            agent=agent,
            async_execution=False
        )