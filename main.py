#!/usr/bin/env python3
"""
ChatDSJ Slack Bot - Main Application Entry Point

This module initializes the FastAPI application and sets up the core services.
"""
import asyncio
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents.crew_manager import CrewManager
from agents.memory_agent import MemoryAgent
from agents.response_agent import ResponseAgent
from agents.slack_agent import SlackAgent
from agents.content_agent import ContentAgent
from agents.todo_agent import TodoAgent
from config.settings import get_settings
from services.content_service import ContentService
from services.notion_service import NotionService
from services.llm_service import LLMService  # Changed from OpenAIService
from services.slack_service import SlackService
from utils.logging_config import configure_logging
from utils.metrics import metrics

# Initialize logger
logger = configure_logging()

# Get settings
settings = get_settings()

# Initialize FastAPI app
app = FastAPI(
    title="ChatDSJ",
    description="A Slack bot using CrewAI architecture",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
slack_service = SlackService()
notion_service = NotionService()
llm_service = LLMService()  # Changed from OpenAIService
content_service = ContentService(llm_service)  # Pass the LLMService instead

# Initialize agents
slack_agent = SlackAgent(slack_service, verbose=settings.enable_crew_verbose)
memory_agent = MemoryAgent(notion_service, verbose=settings.enable_crew_verbose)
response_agent = ResponseAgent(llm_service, verbose=settings.enable_crew_verbose)  # Update to use LLMService
content_agent = ContentAgent(content_service, verbose=settings.enable_crew_verbose)
todo_agent = TodoAgent(notion_service, verbose=settings.enable_crew_verbose)

# Initialize crew manager
crew_manager = CrewManager(
    slack_agent=slack_agent,
    memory_agent=memory_agent,
    response_agent=response_agent,
    content_agent=content_agent,
    todo_agent=todo_agent
)


@slack_service.app.event("app_mention")
def handle_mention(event, say, client, logger):
    """
    Handle app_mention events from Slack.
    
    This function is called when the bot is mentioned in a Slack channel.
    It processes the mention using the crew manager and handles any errors.
    
    Args:
        event: The Slack event data
        say: Function to send a message to the channel
        client: Slack client instance
        logger: Logger instance
    """
    try:
        logger.info(f"Received mention: {event}")
        crew_manager.process_mention(event)
    except Exception as e:
        logger.error(f"Error processing mention: {e}", exc_info=True)
        say(
            text="I encountered an error while processing your request. Please try again later.",
            thread_ts=event.get("thread_ts", event.get("ts"))
        )


@slack_service.app.event("reaction_added")
def handle_reaction(event, logger):
    """
    Handle reaction_added events from Slack.
    
    This function is called when a reaction is added to a message.
    It tracks reactions to bot messages for analytics.
    
    Args:
        event: The Slack event data
        logger: Logger instance
    """
    # Extract event data
    item_user = event.get("item_user")
    item_ts = event.get("item", {}).get("ts")
    reaction = event.get("reaction")
    
    # Check if reaction was added to a bot message
    if item_user == slack_service.bot_user_id and item_ts:
        logger.info(f"Reaction {reaction} added to bot message {item_ts}")
        
        # Track reaction statistics (could be expanded in the future)
        # This is a placeholder for future analytics functionality


@slack_service.app.error
def handle_error(error, body, logger):
    """
    Handle errors from the Slack app.
    
    This function is called when an error occurs in the Slack app.
    It logs the error details for debugging.
    
    Args:
        error: The error that occurred
        body: The request body that caused the error
        logger: Logger instance
    """
    logger.error(f"Slack app error: {error}")
    logger.debug(f"Error body: {body}")


# Replace the on_event with lifespan context manager
@app.get("/", response_model=None)
async def root():
    """
    Root endpoint.
    
    Returns:
        Dict: Welcome message
    """
    return {"message": "Welcome to ChatDSJ API"}


# Replace the deprecated on_event handler with lifespan
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    """
    Lifespan context manager for FastAPI.
    
    This function is called when the application starts up and shuts down.
    It initializes services and connections on startup.
    
    Args:
        app: FastAPI application
    """
    # Startup
    logger.info("Starting ChatDSJ Slack Bot")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")
    
    # Start Slack app in Socket Mode if available
    if slack_service.is_available() and slack_service.app_token:
        slack_service.start_socket_mode()
        logger.info("Slack bot started in socket mode.")
    else:
        logger.warning("Slack bot could not be started in socket mode.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ChatDSJ Slack Bot")


@app.get("/healthz", response_model=None)
async def health_check():
    """
    Health check endpoint for monitoring and kubernetes probes.
    
    Returns:
        Dict: Status of the application and its services
    """
    return {
        "status": "ok",
        "services": {
            "slack": slack_service.is_available(),
            "notion": notion_service.is_available(),
            "openai": llm_service.is_available(),
            "content": content_service.is_available()
        }
    }


@app.get("/metrics", response_model=None)
async def get_metrics():
    """
    Get application metrics.
    
    Returns:
        Dict: Application metrics
    """
    return metrics.get_summary()


@app.post("/metrics/reset", response_model=None)
async def reset_metrics():
    """
    Reset application metrics.
    
    Returns:
        Dict: Confirmation message
    """
    metrics.reset()
    return {"status": "ok", "message": "Metrics have been reset"}


@app.get("/test-llm", response_model=None)  # Use response_model=None to avoid type errors
async def test_llm():
    """
    Test endpoint for the LLM service.
    
    This endpoint tests the LLM service by sending a simple completion request.
    
    Returns:
        Response with the result of the LLM test
    """
    if not llm_service.is_available():
        return {"status": "error", "message": "LLM client not initialized"}
    
    try:
        content, usage = llm_service.get_completion(
            prompt="Say hello world",
            conversation_history=[]
        )
        
        return {
            "status": "success",
            "response": content,
            "model": llm_service.model,
            "usage": usage
        }
    except Exception as e:
        logger.error(f"LLM API test error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/summarize", response_model=None)
async def summarize_url(request: Request):
    """
    Summarize content from a URL.
    
    This endpoint extracts and summarizes content from a URL.
    
    Returns:
        Dict: Summary result
    """
    try:
        # Parse JSON body
        data = await request.json()
        url = data.get("url")
        max_length = data.get("max_length", 500)
        format = data.get("format", "markdown")
        
        if not url:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "URL is required"}
            )
        
        if not content_service.is_available():
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Content service is not available"}
            )
        
        # Extract and summarize
        result = content_service.extract_and_summarize(url, max_length, format)
        
        return result
    except Exception as e:
        logger.error(f"Error summarizing URL: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.get("/api/todos", response_model=None)
async def get_todos(user_id: str, completed: Optional[bool] = None):
    """
    Get todo items for a user.
    
    This endpoint retrieves todo items for a specific user.
    
    Args:
        user_id: Slack user ID
        completed: Filter by completed status
        
    Returns:
        Dict: Todo items
    """
    try:
        if not notion_service.is_available() or not notion_service.todo_db_id:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Todo service is not available"}
            )
        
        # Get todos
        todos = notion_service.get_todo_items(user_id, completed)
        
        return {
            "status": "success",
            "todos": todos
        }
    except Exception as e:
        logger.error(f"Error getting todos: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.post("/api/todos", response_model=None)
async def add_todo(request: Request):
    """
    Add a new todo item.
    
    This endpoint adds a new todo item for a user.
    
    Returns:
        Dict: Created todo item
    """
    try:
        # Parse JSON body
        data = await request.json()
        user_id = data.get("user_id")
        text = data.get("text")
        due_date = data.get("due_date")
        priority = data.get("priority", "medium")
        
        if not user_id or not text:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "User ID and text are required"}
            )
        
        if not notion_service.is_available() or not notion_service.todo_db_id:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Todo service is not available"}
            )
        
        # Add todo
        result = notion_service.add_todo_item(user_id, text, due_date, priority)
        
        return result
    except Exception as e:
        logger.error(f"Error adding todo: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.patch("/api/todos/{todo_id}", response_model=None)
async def update_todo(todo_id: str, request: Request):
    """
    Update a todo item.
    
    This endpoint updates a todo item.
    
    Args:
        todo_id: Todo item ID
        
    Returns:
        Dict: Updated todo item
    """
    try:
        # Parse JSON body
        data = await request.json()
        
        if not notion_service.is_available():
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Todo service is not available"}
            )
        
        # Update todo
        result = notion_service.update_todo_item(todo_id, data)
        
        return result
    except Exception as e:
        logger.error(f"Error updating todo: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.delete("/api/todos/{todo_id}", response_model=None)
async def delete_todo(todo_id: str):
    """
    Delete a todo item.
    
    This endpoint deletes a todo item.
    
    Args:
        todo_id: Todo item ID
        
    Returns:
        Dict: Deletion result
    """
    try:
        if not notion_service.is_available():
            return JSONResponse(
                status_code=503,
                content={"status": "error", "message": "Todo service is not available"}
            )
        
        # Delete todo
        result = notion_service.delete_todo_item(todo_id)
        
        return result
    except Exception as e:
        logger.error(f"Error deleting todo: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.environment == "development",
    )