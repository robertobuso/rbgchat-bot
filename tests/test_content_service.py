"""
Unit tests for ContentService implementation.

This module contains tests for the ContentService class and its
content extraction and summarization functionality.
"""
import unittest
from unittest.mock import MagicMock, patch

from services.content_service import ContentService
from services.openai_service import OpenAIService


class TestContentService(unittest.TestCase):
    """Test cases for the ContentService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock OpenAIService
        self.mock_openai_service = MagicMock(spec=OpenAIService)
        self.mock_openai_service.is_available.return_value = True
        self.mock_openai_service.get_completion.return_value = ("This is a summary", {"prompt_tokens": 100, "completion_tokens": 50})
        
        # Initialize the ContentService with the mock service
        self.content_service = ContentService(self.mock_openai_service)

    def test_init(self):
        """Test ContentService initialization."""
        # Verify the service is initialized with the correct attributes
        self.assertEqual(self.content_service.openai_service, self.mock_openai_service)
        self.assertIn("Mozilla", self.content_service.user_agent)
        self.assertIn("youtube.com", self.content_service.source_parsers)
        self.assertIn("github.com", self.content_service.source_parsers)
        self.assertIn("default", self.content_service.source_parsers)

    def test_is_available(self):
        """Test is_available method."""
        # Test with available OpenAI service
        self.assertTrue(self.content_service.is_available())
        
        # Test with unavailable OpenAI service
        self.mock_openai_service.is_available.return_value = False
        self.assertFalse(self.content_service.is_available())
        
        # Test with no OpenAI service
        content_service = ContentService(None)
        self.assertFalse(content_service.is_available())

    def test_normalize_url(self):
        """Test _normalize_url method."""
        # Test with valid URL with scheme
        url = "https://example.com"
        normalized = self.content_service._normalize_url(url)
        self.assertEqual(normalized, url)
        
        # Test with valid URL without scheme
        url = "example.com"
        normalized = self.content_service._normalize_url(url)
        self.assertEqual(normalized, "https://" + url)
        
        # Test with invalid URL
        url = "not a url"
        normalized = self.content_service._normalize_url(url)
        self.assertIsNone(normalized)
        
        # Test with empty URL
        url = ""
        normalized = self.content_service._normalize_url(url)
        self.assertIsNone(normalized)

    @patch('requests.get')
    def test_extract_content_generic_webpage(self, mock_get):
        """Test _parse_generic_webpage method."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
                <meta name="keywords" content="test, page, keywords">
            </head>
            <body>
                <main>
                    <p>This is a test paragraph with enough text to be included in the content extraction process for testing purposes.</p>
                    <p>This is another paragraph that should be included due to its length which exceeds the minimum threshold set in the method.</p>
                </main>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        content, title, metadata = self.content_service._parse_generic_webpage("https://example.com")
        
        # Verify the HTTP request was made with the correct arguments
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["User-Agent"], self.content_service.user_agent)
        
        # Verify the expected content, title, and metadata were extracted
        self.assertIn("test paragraph", content)
        self.assertIn("another paragraph", content)
        self.assertEqual(title, "Test Page")
        self.assertEqual(metadata["type"], "webpage")
        self.assertIn("test", metadata["tags"])
        self.assertIn("page", metadata["tags"])
        self.assertIn("keywords", metadata["tags"])

    @patch('requests.get')
    def test_extract_content_youtube(self, mock_get):
        """Test _parse_youtube method."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <title>Test YouTube Video - YouTube</title>
                <meta name="description" content="This is a test YouTube video description.">
            </head>
            <body>
                <div>Video content</div>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        content, title, metadata = self.content_service._parse_youtube("https://youtube.com/watch?v=12345")
        
        # Verify the HTTP request was made with the correct arguments
        mock_get.assert_called_once()
        
        # Verify the expected content, title, and metadata were extracted
        self.assertIn("Test YouTube Video", title)
        self.assertNotIn("- YouTube", title)
        self.assertEqual(metadata["type"], "youtube")
        self.assertIn("video", metadata["tags"])
        self.assertIn("Description:", content)
        self.assertIn("test YouTube video description", content)

    @patch('requests.get')
    def test_extract_content_github(self, mock_get):
        """Test _parse_github method."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <title>test-repo · GitHub</title>
            </head>
            <body>
                <p class="f4">Test repository description</p>
                <article class="markdown-body">
                    <h1>Test Repository</h1>
                    <p>This is a test repository README content.</p>
                </article>
                <a class="Link--muted">100 stars</a>
                <a class="Link--muted">50 forks</a>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the method
        content, title, metadata = self.content_service._parse_github("https://github.com/test/test-repo")
        
        # Verify the HTTP request was made with the correct arguments
        mock_get.assert_called_once()
        
        # Verify the expected content, title, and metadata were extracted
        self.assertEqual(title, "test-repo")
        self.assertEqual(metadata["type"], "github")
        self.assertIn("repository", metadata["tags"])
        self.assertIn("Test repository description", content)
        self.assertIn("Test Repository", content)
        self.assertIn("test repository README content", content)

    @patch('requests.get')
    def test_extract_and_summarize(self, mock_get):
        """Test extract_and_summarize method."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <title>Test Page</title>
            </head>
            <body>
                <main>
                    <p>This is a test paragraph with enough text to be included in the content extraction process for testing purposes.</p>
                    <p>This is another paragraph that should be included due to its length which exceeds the minimum threshold set in the method.</p>
                </main>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock the OpenAI response
        self.mock_openai_service.get_completion.return_value = ("This is a summary of the test page.", {"prompt_tokens": 100, "completion_tokens": 50})
        
        # Call the method
        result = self.content_service.extract_and_summarize("https://example.com", 500, "markdown")
        
        # Verify the summary was generated
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Test Page")
        self.assertEqual(result["summary"], "This is a summary of the test page.")
        self.assertEqual(result["sourceUrl"], "https://example.com")
        self.assertEqual(result["sourceType"], "webpage")
        
        # Verify OpenAI was called for summarization
        self.mock_openai_service.get_completion.assert_called_once()

    @patch('requests.get')
    def test_extract_and_summarize_fallback(self, mock_get):
        """Test extract_and_summarize method with fallback summarization."""
        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <title>Test Page</title>
            </head>
            <body>
                <main>
                    <p>This is a test paragraph with enough text to be included in the content extraction process for testing purposes.</p>
                    <p>This is another paragraph that should be included due to its length which exceeds the minimum threshold set in the method.</p>
                </main>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Create a ContentService with no OpenAI service
        content_service = ContentService(None)
        
        # Call the method
        result = content_service.extract_and_summarize("https://example.com", 500, "markdown")
        
        # Verify the fallback summary was generated
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Test Page")
        self.assertIn("test paragraph", result["summary"])
        self.assertEqual(result["sourceUrl"], "https://example.com")
        self.assertEqual(result["sourceType"], "webpage")

    def test_get_source_type(self):
        """Test get_source_type method."""
        # Test YouTube URLs
        self.assertEqual(self.content_service.get_source_type("https://youtube.com/watch?v=12345"), "youtube")
        self.assertEqual(self.content_service.get_source_type("https://youtu.be/12345"), "youtube")
        
        # Test GitHub URLs
        self.assertEqual(self.content_service.get_source_type("https://github.com/user/repo"), "github")
        
        # Test Medium URLs
        self.assertEqual(self.content_service.get_source_type("https://medium.com/@user/article"), "medium")
        self.assertEqual(self.content_service.get_source_type("https://user.medium.com/article"), "medium")
        
        # Test file types
        self.assertEqual(self.content_service.get_source_type("https://example.com/document.pdf"), "pdf")
        self.assertEqual(self.content_service.get_source_type("https://example.com/image.jpg"), "image")
        self.assertEqual(self.content_service.get_source_type("https://example.com/video.mp4"), "video")
        
        # Test default
        self.assertEqual(self.content_service.get_source_type("https://example.com"), "webpage")
        self.assertEqual(self.content_service.get_source_type("https://unknown-site.com/page"), "webpage")


if __name__ == "__main__":
    unittest.main()