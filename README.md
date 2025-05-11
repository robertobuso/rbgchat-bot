[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🧠 Overview

**RBGChat Bot** is an AI-powered Slack bot built to enhance productivity and collaboration by integrating with Slack, Notion, and LLMs via a modular CrewAI architecture. It supports contextual responses, task tracking, summarization, and user memory — all running on a Python/FastAPI backend.

## ✨ Key Features

- **Slack Integration** — Responds to mentions in channels and threads.
- **Contextual AI Responses** — Uses OpenAI LLMs for accurate, personalized answers.
- **User Memory** — Stores user preferences, facts, and instructions in Notion.
- **Content Summarization** — Summarizes articles, documents, and YouTube videos.
- **Task Management** — Manages TODO lists via Notion integration.
- **Dynamic Prompts** — Uses editable prompts stored in Notion pages.
- **Intelligent Behavior Selection** — Automatically chooses actions based on user intent and system config.

## 🏗️ Architecture

RBGChat Bot follows a modular architecture with clean separation of concerns:

- **FastAPI** — Serves the REST API.
- **Slack Bolt** — Handles Slack event subscriptions and interactions.
- **CrewAI** — Manages agent/task orchestration.
- **LangChain** — Interfaces with LLMs (OpenAI, Claude, Gemini).
- **Notion API** — Stores user state, memory, and prompt content.
- **Redis** — Used for caching and coordination.

### High-Level Architecture Diagram

```mermaid
graph TD
    A[Slack] <--> B[Fly.io Load Balancer]
    B --> C[RBGChat Bot App Container]
    C --> D[Redis Cache]
    C --> E[Notion API]
    C --> F[LLM APIs]
    F --> G[OpenAI/GPT-4]
    F --> H[Anthropic/Claude]
    F --> I[Google/Gemini]
📁 Project Structure
bash
Copy
Edit
main.py                # FastAPI entry point

/config/
  settings.py          # Environment + secrets config

/utils/
  logging_config.py    # Structured logging setup
  token_counter.py     # Token usage tools
  text_processing.py   # Text utilities

/services/
  openai_service.py    # OpenAI integration
  notion_service.py    # Notion API client
  slack_service.py     # Slack event handler

/agents/
  base_agent.py        # Base CrewAI agent class
  slack_agent.py       # Slack-specific logic
  memory_agent.py      # Notion memory management
  response_agent.py    # OpenAI response generator
  crew_manager.py      # CrewAI orchestration

/tasks/
  slack_tasks.py       # Slack-specific tasks
  memory_tasks.py      # User memory tasks
  response_tasks.py    # Response generation tasks
⚙️ Setup
Prerequisites
Python 3.10+

Poetry

Fly.io CLI

Slack API credentials

Notion API token & DB ID

OpenAI API key

Installation
bash
Copy
Edit
# Clone the repo
git clone git@github.com:yourusername/rbgchat-bot.git
cd rbgchat-bot

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env
# Fill in your tokens in the .env file
Run Locally
bash
Copy
Edit
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Deploy to Fly.io
bash
Copy
Edit
# Install CLI (if not already)
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
💬 Usage
Invite the bot to your Slack workspace.

Add it to specific channels or threads.

Mention @RBGChat Bot and issue natural-language commands:

Ask questions

Summarize links

Manage TODOs

Retrieve memory/context

Customize behavior by editing the user’s Notion page.

🚀 API Endpoints
Slack Events
http
Copy
Edit
POST /slack/events
Handles mentions, messages, and interactions.

User Preferences
http
Copy
Edit
GET /users/me
PUT /users/me/preferences
Summaries
http
Copy
Edit
POST /summaries
GET /summaries
GET /summaries/{id}
Example request:

json
Copy
Edit
{
  "url": "https://example.com/article",
  "maxLength": 500,
  "format": "markdown"
}
TODOs
http
Copy
Edit
GET /todos
POST /todos
PATCH /todos/{id}
DELETE /todos/{id}
Example request:

json
Copy
Edit
{
  "text": "Finish project report",
  "dueDate": "2023-04-20T17:00:00Z",
  "priority": "high"
}
Health Check
http
Copy
Edit
GET /health
Returns API status.

🧪 Testing & Code Quality
Code Style: Follows PEP 8

Formatter: Black

Imports: isort

Type Checking: MyPy

Tests: Pytest for unit tests

🤝 Contributing
Fork the repo

Create a feature branch

Commit with clear messages

Submit a pull request with description

Ensure tests pass

📄 License
This project is licensed under the MIT License.