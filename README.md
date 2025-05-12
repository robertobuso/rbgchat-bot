# ChatDSJ Bot — AI-Powered Slack Bot with CrewAI Architecture

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🧠 Overview

**ChatDSJ Bot** is an AI-powered Slack bot designed to enhance productivity and collaboration by integrating Slack, Notion, and large language models using a modular CrewAI architecture. It provides contextual responses, task tracking, content summarization, and memory management — all backed by a Python/FastAPI backend.

## ✨ Key Features

- **Slack Integration** — Responds to mentions in channels and threads  
- **Contextual AI Responses** — Uses OpenAI for accurate, personalized answers  
- **User Memory** — Stores preferences and instructions in Notion  
- **Content Summarization** — Summarizes articles and YouTube videos  
- **Task Management** — Tracks TODOs via Notion  
- **Dynamic Prompts** — Editable prompts stored in Notion  
- **Behavior Selection** — Chooses actions based on user intent and config  

## 🏗️ Architecture

ChatDSJ Bot follows a modular structure with clear separation of concerns:

- **FastAPI** — REST API server  
- **Slack Bolt** — Slack events and message handling  
- **CrewAI** — Orchestrates agents and tasks  
- **LangChain** — Interfaces with OpenAI, Claude, Gemini  
- **Notion API** — Persistent storage and memory  
- **Redis** — Caching and coordination  

## 📐 High-Level Architecture Diagram

```mermaid
- **FastAPI** — REST API server  
- **Slack Bolt** — Slack events and message handling  
- **CrewAI** — Orchestrates agents and tasks  
- **LangChain** — Interfaces with OpenAI, Claude, Gemini  
- **Notion API** — Persistent storage and memory  
- **Redis** — Caching and coordination  
```

## 📁 Project Structure

```
main.py                # FastAPI entry point

/config/
  settings.py          # Environment and secrets config

/utils/
  logging_config.py    # Structured logging
  token_counter.py     # Token usage tools
  text_processing.py   # Text utilities

/services/
  openai_service.py    # Handles OpenAI integration
  notion_service.py    # Notion API client
  slack_service.py     # Slack event logic

/agents/
  base_agent.py        # Base CrewAI agent
  slack_agent.py       # Slack interaction logic
  memory_agent.py      # User memory via Notion
  response_agent.py    # Generates responses
  crew_manager.py      # Agent orchestration

/tasks/
  slack_tasks.py       # Slack-related tasks
  memory_tasks.py      # Memory-related tasks
  response_tasks.py    # LLM response tasks
```

## ⚙️ Setup

### Prerequisites

- Python 3.10+  
- Poetry  
- Fly.io CLI  
- Slack Bot Token, App Token, and Signing Secret  
- Notion API token and database ID  
- OpenAI API key  

### Installation

```
# Clone the repo
git clone git@github.com:yourusername/chatdsj-bot.git
cd chatdsj-bot

# Install dependencies
poetry install

# Copy env template
cp .env.example .env

# Fill in your API keys and secrets in the .env file
```

### Run Locally

```
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Deploy to Fly.io

```
# Install Fly.io CLI if needed
# https://fly.io/docs/flyctl/install/

# Deploy
fly deploy

# Set environment secrets
flyctl secrets set SLACK_BOT_TOKEN="..." \
                  SLACK_SIGNING_SECRET="..." \
                  SLACK_APP_TOKEN="..." \
                  OPENAI_API_KEY="..." \
                  NOTION_API_TOKEN="..." \
                  NOTION_USER_DB_ID="..."
```

## 💬 Usage

- Invite the bot to your Slack workspace  
- Add it to channels or threads  
- Mention `@ChatDSJ` to interact  
- Use natural language to:
  - Ask questions  
  - Summarize articles  
  - Manage TODOs  
  - Retrieve user memory  
- Customize by editing content and instructions in each user's Notion page  

## 🚀 API Endpoints

### Slack Events

- `POST /slack/events` — Handles incoming Slack events  

### User Preferences

- `GET /users/me` — Retrieve user info  
- `PUT /users/me/preferences` — Update preferences  

### Summaries

- `POST /summaries` — Generate summary from a URL  
- `GET /summaries` — List summaries  
- `GET /summaries/{id}` — Get a specific summary  

### TODOs

- `GET /todos` — List TODOs  
- `POST /todos` — Create TODO  
- `PATCH /todos/{id}` — Update TODO  
- `DELETE /todos/{id}` — Delete TODO  

### Health Check

- `GET /health` — Returns status info  

## 🧪 Testing & Code Quality

- Style: PEP 8  
- Formatter: Black  
- Import Sorter: isort  
- Type Checking: MyPy  
- Testing Framework: Pytest  

## 🤝 Contributing

- Fork the repo  
- Create a feature branch  
- Write clear commit messages  
- Submit a PR with description  
- Make sure all tests pass  

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).