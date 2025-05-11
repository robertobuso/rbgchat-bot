"""
Content service for ChatDSJ Slack Bot.

This module provides a service for extracting and summarizing
content from various sources, including web pages and YouTube videos.
"""
import re
import time
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config.settings import get_settings
from services.openai_service import OpenAIService
from utils.logging_config import configure_logging

# Initialize logger and settings
logger = configure_logging()
settings = get_settings()


class ContentService:
    """
    Service for extracting and summarizing content from various sources.
    
    This class handles website content extraction, summarization,
    and content processing for different types of URLs.
    
    Attributes:
        openai_service: OpenAI service for text summarization
        user_agent: User agent string for HTTP requests
        source_parsers: Dictionary of source-specific parser functions
    """

    def __init__(self, openai_service: Optional[OpenAIService] = None) -> None:
        """
        Initialize the Content service with OpenAI service for summarization.
        
        Args:
            openai_service: Optional OpenAI service instance for summarization
        """
        self.openai_service = openai_service
        self.user_agent = "Mozilla/5.0 (compatible; ChatDSJBot/1.0; +https://chatdsj.com)"
        
        # Register source-specific parsers
        self.source_parsers = {
            "youtube.com": self._parse_youtube,
            "youtu.be": self._parse_youtube,
            "github.com": self._parse_github,
            "medium.com": self._parse_medium,
            "default": self._parse_generic_webpage
        }
        
        logger.info("Content service initialized")

    def is_available(self) -> bool:
        """
        Check if the Content service is available for summarization.
        
        Returns:
            bool: True if the service can summarize content, False otherwise
        """
        return self.openai_service is not None and self.openai_service.is_available()

    def extract_and_summarize(
        self,
        url: str,
        max_length: int = 500,
        format: str = "markdown"
    ) -> Dict[str, any]:
        """
        Extract content from a URL and generate a summary.
        
        Args:
            url: The URL to extract content from
            max_length: Maximum length of the summary in words
            format: Output format ('markdown', 'text', or 'html')
            
        Returns:
            Dict: Summary information including title, summary text, source URL, etc.
        """
        try:
            # Validate and normalize the URL
            normalized_url = self._normalize_url(url)
            if not normalized_url:
                return {
                    "success": False,
                    "error": "Invalid URL format",
                    "url": url
                }
            
            # Extract content from the URL
            content, title, metadata = self._extract_content(normalized_url)
            
            if not content:
                return {
                    "success": False,
                    "error": "Failed to extract content from URL",
                    "url": normalized_url
                }
            
            # Generate a summary if OpenAI service is available
            if self.is_available():
                summary = self._generate_summary(content, title, max_length, format)
            else:
                # Fallback to a simple extraction-based summary
                summary = self._extract_based_summary(content, max_length)
            
            # Return the summary information
            return {
                "success": True,
                "title": title,
                "summary": summary,
                "sourceUrl": normalized_url,
                "sourceType": metadata.get("type", "webpage"),
                "wordCount": len(content.split()),
                "readingTime": len(content.split()) // 200,  # Approx. 200 WPM reading speed
                "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tags": metadata.get("tags", [])
            }
            
        except Exception as e:
            logger.error(f"Error extracting and summarizing content: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    def _normalize_url(self, url: str) -> Optional[str]:
        """
        Normalize a URL to ensure it has a scheme and is properly formatted.
        
        Args:
            url: The URL to normalize
            
        Returns:
            Optional[str]: Normalized URL or None if invalid
        """
        if not url:
            return None
        
        # Add https:// if no scheme is present
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            # Parse the URL to validate it
            parsed = urlparse(url)
            if not parsed.netloc:
                return None
            
            return url
        except Exception:
            return None

    def _extract_content(self, url: str) -> Tuple[str, str, Dict]:
        """
        Extract content from a URL using the appropriate parser.
        
        Args:
            url: The URL to extract content from
            
        Returns:
            Tuple[str, str, Dict]: Content text, title, and metadata
        """
        # Parse the URL to determine the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace("www.", "")
        
        # Select the appropriate parser based on the domain
        parser = self.source_parsers.get(domain)
        if not parser:
            # Find a matching domain (e.g., medium.com for subdomain.medium.com)
            for known_domain, known_parser in self.source_parsers.items():
                if known_domain in domain:
                    parser = known_parser
                    break
            else:
                # Use the default parser if no match is found
                parser = self.source_parsers["default"]
        
        # Parse the content
        return parser(url)

    def _parse_generic_webpage(self, url: str) -> Tuple[str, str, Dict]:
        """
        Parse a generic webpage to extract content.
        
        Args:
            url: The URL to extract content from
            
        Returns:
            Tuple[str, str, Dict]: Content text, title, and metadata
        """
        try:
            # Fetch the webpage
            response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the title
            title = soup.title.string if soup.title else ""
            title = title.strip() if title else "Untitled"
            
            # Extract metadata
            metadata = {
                "type": "webpage",
                "tags": []
            }
            
            # Extract meta description
            description_tag = soup.find("meta", attrs={"name": "description"})
            if description_tag and "content" in description_tag.attrs:
                metadata["description"] = description_tag["content"]
            
            # Extract meta keywords
            keywords_tag = soup.find("meta", attrs={"name": "keywords"})
            if keywords_tag and "content" in keywords_tag.attrs:
                keywords = keywords_tag["content"].split(",")
                metadata["tags"] = [k.strip() for k in keywords if k.strip()]
            
            # Extract main content
            # This is a simple heuristic approach - more advanced content extraction may be needed
            content = []
            
            # Try to find main content container
            main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main|article"))
            
            # If a main content area is found, extract text from it
            if main_content:
                # Remove script and style elements
                for script in main_content(["script", "style", "nav", "header", "footer"]):
                    script.extract()
                
                # Get text from paragraphs
                paragraphs = main_content.find_all("p")
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 50:  # Skip very short paragraphs
                        content.append(text)
            else:
                # Fallback to all paragraphs if no main content area is found
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.extract()
                
                paragraphs = soup.find_all("p")
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and len(text) > 50:  # Skip very short paragraphs
                        content.append(text)
            
            # Combine the content
            content_text = "\n\n".join(content)
            
            return content_text, title, metadata
            
        except Exception as e:
            logger.error(f"Error parsing generic webpage: {e}")
            return "", "Failed to Parse", {"type": "webpage", "tags": []}

    def _parse_youtube(self, url: str) -> Tuple[str, str, Dict]:
        """
        Parse a YouTube video page to extract content.
        
        This implementation provides a stub - in a real implementation,
        you would use the YouTube API or yt-dlp to extract transcripts.
        
        Args:
            url: The YouTube URL to extract content from
            
        Returns:
            Tuple[str, str, Dict]: Content text, title, and metadata
        """
        # Note: In a real implementation, use the YouTube API or yt-dlp to extract transcripts
        # This is a simplified placeholder
        
        try:
            # Fetch the webpage
            response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the title
            title = soup.title.string if soup.title else ""
            title = title.strip() if title else "Untitled YouTube Video"
            
            # Remove " - YouTube" from the title if present
            if title.endswith(" - YouTube"):
                title = title[:-10]
            
            # Extract metadata
            metadata = {
                "type": "youtube",
                "tags": ["video"]
            }
            
            # In a real implementation, extract more metadata like video length, channel, etc.
            
            # Since we can't easily get the transcript, use the video description
            description = ""
            desc_elem = soup.find("meta", {"name": "description"})
            if desc_elem and "content" in desc_elem.attrs:
                description = desc_elem["content"]
            
            content = f"YouTube Video: {title}\n\nDescription: {description}\n\n" + \
                      "Note: For a complete summary, a transcript would be needed."
            
            return content, title, metadata
            
        except Exception as e:
            logger.error(f"Error parsing YouTube video: {e}")
            return "", "Failed to Parse YouTube Video", {"type": "youtube", "tags": ["video"]}

    def _parse_github(self, url: str) -> Tuple[str, str, Dict]:
        """
        Parse a GitHub page to extract content.
        
        Args:
            url: The GitHub URL to extract content from
            
        Returns:
            Tuple[str, str, Dict]: Content text, title, and metadata
        """
        try:
            # Fetch the webpage
            response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the title
            title = soup.title.string if soup.title else ""
            title = title.strip() if title else "Untitled GitHub Repository"
            
            # Remove " · GitHub" from the title if present
            if " · GitHub" in title:
                title = title.split(" · GitHub")[0]
            
            # Extract metadata
            metadata = {
                "type": "github",
                "tags": ["code", "repository"]
            }
            
            # Check if it's a repository page
            repository_content = []
            
            # Get the README content if available
            readme = soup.find("article", class_="markdown-body")
            if readme:
                # Remove script and style elements
                for script in readme(["script", "style"]):
                    script.extract()
                
                # Get text content
                readme_text = readme.get_text("\n\n").strip()
                repository_content.append(f"README:\n{readme_text}")
            
            # Get repository description if available
            description = soup.find("p", {"class": "f4"})
            if description:
                desc_text = description.get_text().strip()
                if desc_text:
                    repository_content.insert(0, f"Description: {desc_text}")
            
            # Get repository statistics if available
            stats = []
            stat_items = soup.find_all("a", {"class": "Link--muted"})
            for item in stat_items:
                stat_text = item.get_text().strip()
                if stat_text:
                    stats.append(stat_text)
            
            if stats:
                repository_content.append(f"Stats: {', '.join(stats)}")
            
            # Combine the content
            content_text = "\n\n".join(repository_content)
            
            # If no repository content was found, fallback to generic parsing
            if not content_text:
                return self._parse_generic_webpage(url)
            
            return content_text, title, metadata
            
        except Exception as e:
            logger.error(f"Error parsing GitHub page: {e}")
            return "", "Failed to Parse GitHub Page", {"type": "github", "tags": ["code"]}

    def _parse_medium(self, url: str) -> Tuple[str, str, Dict]:
        """
        Parse a Medium article to extract content.
        
        Args:
            url: The Medium URL to extract content from
            
        Returns:
            Tuple[str, str, Dict]: Content text, title, and metadata
        """
        try:
            # Fetch the webpage
            response = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract the title
            title = soup.find("h1")
            title_text = title.get_text().strip() if title else "Untitled Medium Article"
            
            # Extract metadata
            metadata = {
                "type": "medium",
                "tags": ["article"]
            }
            
            # Extract author information
            author = soup.find("a", {"rel": "author"})
            if author:
                metadata["author"] = author.get_text().strip()
            
            # Extract tags
            tags = []
            tag_elements = soup.find_all("a", {"rel": "tag"})
            for tag in tag_elements:
                tag_text = tag.get_text().strip()
                if tag_text:
                    tags.append(tag_text)
            
            if tags:
                metadata["tags"] = tags
            
            # Extract article content
            content = []
            
            # Try to find article content
            article = soup.find("article")
            if article:
                # Remove script, style, and other non-content elements
                for elem in article(["script", "style", "nav", "header", "footer"]):
                    elem.extract()
                
                # Get text from paragraphs
                paragraphs = article.find_all("p")
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text:
                        content.append(text)
            else:
                # Fallback to generic parsing if article element not found
                return self._parse_generic_webpage(url)
            
            # Combine the content
            content_text = "\n\n".join(content)
            
            return content_text, title_text, metadata
            
        except Exception as e:
            logger.error(f"Error parsing Medium article: {e}")
            return "", "Failed to Parse Medium Article", {"type": "medium", "tags": ["article"]}

    def _generate_summary(
        self,
        content: str,
        title: str,
        max_length: int = 500,
        format: str = "markdown"
    ) -> str:
        """
        Generate a summary of the content using OpenAI.
        
        Args:
            content: The content to summarize
            title: The title of the content
            max_length: Maximum length of the summary in words
            format: Output format ('markdown', 'text', or 'html')
            
        Returns:
            str: The generated summary
        """
        if not self.is_available() or not self.openai_service:
            return self._extract_based_summary(content, max_length)
        
        try:
            # Prepare the prompt for summarization
            prompt = f"""Please summarize the following {title} in approximately {max_length} words.
            Focus on the key points, main arguments, and important conclusions.
            
            Output the summary in {format} format.
            
            Content to summarize:
            {content[:15000]}  # Limit content to avoid token limits
            """
            
            # Generate the summary
            summary, _ = self.openai_service.get_completion(
                prompt=prompt,
                conversation_history=[],
                max_retries=2
            )
            
            return summary or self._extract_based_summary(content, max_length)
            
        except Exception as e:
            logger.error(f"Error generating summary with OpenAI: {e}")
            return self._extract_based_summary(content, max_length)

    def _extract_based_summary(self, content: str, max_length: int = 500) -> str:
        """
        Generate a summary using extraction-based techniques.
        
        This is a fallback method when OpenAI summarization is not available.
        
        Args:
            content: The content to summarize
            max_length: Maximum length of the summary in words
            
        Returns:
            str: The generated extraction-based summary
        """
        try:
            # Split into sentences
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            # Simple heuristic: take the first sentence and a few from the body
            if not sentences:
                return "No content available to summarize."
            
            # Take the first sentence as the introduction
            introduction = sentences[0] if sentences else ""
            
            # Take some sentences from the middle for the body
            body_sentences = []
            if len(sentences) > 5:
                # Take every nth sentence to get a good distribution
                n = max(1, len(sentences) // 10)
                body_sentences = [sentences[i] for i in range(1, len(sentences) - 1, n)][:5]
            else:
                body_sentences = sentences[1:-1]
            
            # Take the last sentence as the conclusion
            conclusion = sentences[-1] if len(sentences) > 1 else ""
            
            # Combine the summary parts
            summary_sentences = [introduction] + body_sentences
            if conclusion and conclusion not in summary_sentences:
                summary_sentences.append(conclusion)
            
            # Join the sentences and limit to max_length words
            summary = " ".join(summary_sentences)
            words = summary.split()
            if len(words) > max_length:
                summary = " ".join(words[:max_length]) + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating extraction-based summary: {e}")
            # Very simple fallback: just take the first portion of the content
            words = content.split()
            return " ".join(words[:max_length]) + "..." if len(words) > max_length else content

    def get_source_type(self, url: str) -> str:
        """
        Determine the type of source from a URL.
        
        Args:
            url: The URL to analyze
            
        Returns:
            str: Source type ('webpage', 'youtube', 'github', etc.)
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            
            # Check for known domains
            if domain in self.source_parsers:
                if domain in ["youtube.com", "youtu.be"]:
                    return "youtube"
                elif domain == "github.com":
                    return "github"
                elif domain == "medium.com" or domain.endswith(".medium.com"):
                    return "medium"
            
            # Check for common file extensions
            path = parsed_url.path.lower()
            if path.endswith(".pdf"):
                return "pdf"
            elif path.endswith((".jpg", ".jpeg", ".png", ".gif")):
                return "image"
            elif path.endswith((".mp4", ".avi", ".mov", ".wmv")):
                return "video"
            
            # Default to webpage
            return "webpage"
            
        except Exception:
            return "webpage"