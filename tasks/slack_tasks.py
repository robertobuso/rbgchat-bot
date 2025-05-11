"""
Slack tasks implementation for ChatDSJ Slack Bot.

This module provides the SlackTasks class that defines tasks related to
Slack interactions, such as processing mentions, fetching context, and
sending responses.
"""
from typing import Dict, List, Optional

from crewai import Task

from utils.logging_config import configure_logging

logger = configure_logging()


class SlackTasks:
    """
    Tasks related to Slack interactions.

    This class provides static methods that create Task objects for
    processing Slack mentions, fetching conversation context, and
    sending responses to Slack channels or threads.
    """

    @staticmethod
    def process_mention_task(agent) -> Task:
        """
        Create a task for processing a mention in Slack.

        This task handles the initial processing of a mention, including
        acknowledging receipt and preparing for response generation.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Process a mention in Slack. This involves acknowledging the mention, "
                "extracting the user's query, and preparing for response generation. "
                "You should send a typing indicator or acknowledgment message to let "
                "the user know their message is being processed."
            ),
            expected_output=(
                "A processed Slack mention with acknowledgment sent. The output should "
                "include the channel_id, user_id, message text (with mentions removed), "
                "thread_ts (if in a thread), and confirmation that an acknowledgment "
                "was sent to the user."
            ),
            agent=agent,
            async_execution=False
        )

    @staticmethod
    def fetch_context_task(agent) -> Task:
        """
        Create a task for fetching relevant conversation context.

        This task retrieves the conversation history from a channel or thread
        to provide context for response generation.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Fetch the relevant conversation context from Slack. This involves "
                "retrieving the conversation history from the channel or thread where "
                "the mention occurred. For thread mentions, fetch the entire thread. "
                "For channel mentions, fetch recent messages in the channel. Format "
                "the messages appropriately for context."
            ),
            expected_output=(
                "The relevant conversation history for context. This should include "
                "a list of formatted messages with user information, timestamps, and "
                "message content. The history should be ordered chronologically and "
                "include enough context for meaningful response generation."
            ),
            agent=agent,
            async_execution=False
        )

    @staticmethod
    def send_response_task(agent) -> Task:
        """
        Create a task for sending a response to Slack.

        This task handles sending the generated response to the appropriate
        Slack channel or thread.

        Args:
            agent: The agent that will execute this task

        Returns:
            Task: A CrewAI Task object
        """
        return Task(
            description=(
                "Send a response to a Slack channel or thread. This involves formatting "
                "the response appropriately for Slack, including any markdown or special "
                "formatting, and sending it to the correct channel or thread. If the original "
                "message was in a thread, the response should be sent to that thread. "
                "Otherwise, it should be sent to the channel."
            ),
            expected_output=(
                "A confirmation that the response was sent successfully to Slack. "
                "This should include the channel_id, thread_ts (if applicable), "
                "and the response text that was sent."
            ),
            agent=agent,
            async_execution=False
        )