"""
Unit tests for SlackAgent implementation.

This module contains tests for the SlackAgent class and
its interaction with the SlackService.
"""
import unittest
from unittest.mock import MagicMock, patch

from agents.slack_agent import SlackAgent


class TestSlackAgent(unittest.TestCase):
    """Test cases for the SlackAgent class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock SlackService
        self.mock_slack_service = MagicMock()
        
        # Initialize the SlackAgent with the mock service
        self.agent = SlackAgent(self.mock_slack_service)

    def test_init(self):
        """Test SlackAgent initialization."""
        # Verify the agent is initialized with the correct attributes
        self.assertEqual(self.agent.slack_service, self.mock_slack_service)
        self.assertEqual(self.agent.name, "Slack Interface Specialist")
        self.assertEqual(self.agent.role, "Slack communication expert")
        self.assertIn("Handle all interactions", self.agent.goal)

    def test_get_tools(self):
        """Test tools registration."""
        # Get the tools
        tools = self.agent.get_tools()
        
        # Verify the expected tools are registered
        tool_names = [tool.name for tool in tools]
        self.assertIn("send_message", tool_names)
        self.assertIn("fetch_channel_history", tool_names)
        self.assertIn("fetch_thread_history", tool_names)
        self.assertIn("get_user_display_name", tool_names)
        self.assertIn("clean_prompt_text", tool_names)

    def test_send_message(self):
        """Test send_message method."""
        # Set up the mock return value
        expected_response = {"ok": True, "ts": "1234.5678"}
        self.mock_slack_service.send_message.return_value = expected_response
        
        # Call the method
        response = self.agent.send_message("C12345", "Hello, world!")
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.send_message.assert_called_once_with("C12345", "Hello, world!", None)
        
        # Verify the expected response was returned
        self.assertEqual(response, expected_response)

    def test_send_message_with_thread(self):
        """Test send_message method with thread_ts."""
        # Set up the mock return value
        expected_response = {"ok": True, "ts": "1234.5678"}
        self.mock_slack_service.send_message.return_value = expected_response
        
        # Call the method with thread_ts
        thread_ts = "1234.5678"
        response = self.agent.send_message("C12345", "Hello, world!", thread_ts)
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.send_message.assert_called_once_with("C12345", "Hello, world!", thread_ts)
        
        # Verify the expected response was returned
        self.assertEqual(response, expected_response)

    def test_send_ephemeral_message(self):
        """Test send_ephemeral_message method."""
        # Set up the mock return value
        self.mock_slack_service.send_ephemeral_message.return_value = True
        
        # Call the method
        result = self.agent.send_ephemeral_message("C12345", "U67890", "This is ephemeral")
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.send_ephemeral_message.assert_called_once_with(
            "C12345", "U67890", "This is ephemeral"
        )
        
        # Verify the expected result was returned
        self.assertTrue(result)

    def test_fetch_channel_history(self):
        """Test fetch_channel_history method."""
        # Set up the mock return value
        expected_messages = [{"type": "message", "text": "Hello"}, {"type": "message", "text": "World"}]
        self.mock_slack_service.fetch_channel_history.return_value = expected_messages
        
        # Call the method
        messages = self.agent.fetch_channel_history("C12345", 100)
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.fetch_channel_history.assert_called_once_with("C12345", 100)
        
        # Verify the expected messages were returned
        self.assertEqual(messages, expected_messages)

    def test_fetch_thread_history(self):
        """Test fetch_thread_history method."""
        # Set up the mock return value
        expected_messages = [{"type": "message", "text": "Thread start"}, {"type": "message", "text": "Reply"}]
        self.mock_slack_service.fetch_thread_history.return_value = expected_messages
        
        # Call the method
        messages = self.agent.fetch_thread_history("C12345", "1234.5678", 100)
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.fetch_thread_history.assert_called_once_with("C12345", "1234.5678", 100)
        
        # Verify the expected messages were returned
        self.assertEqual(messages, expected_messages)

    def test_get_user_display_name(self):
        """Test get_user_display_name method."""
        # Set up the mock return value
        expected_name = "John Doe"
        self.mock_slack_service.get_user_display_name.return_value = expected_name
        
        # Call the method
        name = self.agent.get_user_display_name("U12345")
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.get_user_display_name.assert_called_once_with("U12345")
        
        # Verify the expected name was returned
        self.assertEqual(name, expected_name)

    def test_clean_prompt_text(self):
        """Test clean_prompt_text method."""
        # Set up the mock return value
        expected_text = "Hello, world!"
        self.mock_slack_service.clean_prompt_text.return_value = expected_text
        
        # Call the method
        text = self.agent.clean_prompt_text("<@U12345> Hello, world!")
        
        # Verify the service method was called with the correct arguments
        self.mock_slack_service.clean_prompt_text.assert_called_once_with("<@U12345> Hello, world!")
        
        # Verify the expected text was returned
        self.assertEqual(text, expected_text)


if __name__ == "__main__":
    unittest.main()