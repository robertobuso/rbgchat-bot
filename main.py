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
from services.openai_service import OpenAIService
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
openai_service = OpenAIService()
content_service = ContentService(openai_service)

# Initialize agents
slack_agent = SlackAgent(slack_service, verbose=settings.enable_crew_verbose)
memory_agent = MemoryAgent(notion_service, verbose=settings.enable_crew_verbose)
response_agent = ResponseAgent(openai_service, verbose=settings.enable_crew_verbose)
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


@app.on_event("startup")
async def startup_event():
    """
    Initialize services and connections on application startup.
    
    This function starts the Slack app in Socket Mode if available.
    """
    logger.info("Starting ChatDSJ Slack Bot")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")
    
    # Start Slack app in Socket Mode if available
    if slack_service.is_available() and slack_service.app_token:
        slack_service.start_socket_mode()
        logger.info("Slack bot started in socket mode.")
    else:
        logger.warning("Slack bot could not be started in socket mode.")


@app.get("/healthz")
async def health_check() -> Dict[str, any]:
    """
    Health check endpoint for monitoring and kubernetes probes.
    
    Returns:
        Dict[str, any]: Status of the application and its services
    """
    return {
        "status": "ok",
        "services": {
            "slack": slack_service.is_available(),
            "notion": notion_service.is_available(),
            "openai": openai_service.is_available(),
            "content": content_service.is_available()
        }
    }


@app.get("/metrics")
async def get_metrics() -> Dict[str, any]:
    """
    Get application metrics.
    
    Returns:
        Dict[str, any]: Application metrics
    """
    return metrics.get_summary()


@app.post("/metrics/reset")
async def reset_metrics() -> Dict[str, str]:
    """
    Reset application metrics.
    
    Returns:
        Dict[str, str]: Confirmation message
    """
    metrics.reset()
    return {"status": "ok", "message": "Metrics have been reset"}


@app.get("/test-openai")
async def test_openai() -> Dict[str, any]:
    """
    Test endpoint for the OpenAI service.
    
    This endpoint tests the OpenAI service by sending a simple completion request.
    
    Returns:
        Dict[str, any]: Result of the OpenAI test
    """
    if not openai_service.is_available():
        return {"status": "error", "message": "OpenAI client not initialized"}
    
    try:
        content, usage = openai_service.get_completion(
            prompt="Say hello world",
            conversation_history=[]
        )
        
        return {
            "status": "success",
            "response": content,
            "model": openai_service.model,
            "usage": usage
        }
    except Exception as e:
        logger.error(f"OpenAI API test error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/summarize")
async def summarize_url(request: Request) -> Dict[str, any]:
    """
    Summarize content from a URL.
    
    This endpoint extracts and summarizes content from a URL.
    
    Returns:
        Dict[str, any]: Summary result
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


@app.get("/api/todos")
async def get_todos(user_id: str, completed: Optional[bool] = None) -> Dict[str, any]:
    """
    Get todo items for a user.
    
    This endpoint retrieves todo items for a specific user.
    
    Args:
        user_id: Slack user ID
        completed: Filter by completed status
        
    Returns:
        Dict[str, any]: Todo items
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


@app.post("/api/todos")
async def add_todo(request: Request) -> Dict[str, any]:
    """
    Add a new todo item.
    
    This endpoint adds a new todo item for a user.
    
    Returns:
        Dict[str, any]: Created todo item
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


@app.patch("/api/todos/{todo_id}")
async def update_todo(todo_id: str, request: Request) -> Dict[str, any]:
    """
    Update a todo item.
    
    This endpoint updates a todo item.
    
    Args:
        todo_id: Todo item ID
        
    Returns:
        Dict[str, any]: Updated todo item
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


@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: str) -> Dict[str, any]:
    """
    Delete a todo item.
    
    This endpoint deletes a todo item.
    
    Args:
        todo_id: Todo item ID
        
    Returns:
        Dict[str, any]: Deletion result
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