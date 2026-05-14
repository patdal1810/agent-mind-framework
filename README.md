# AgentMind

AgentMind is a production ready infrastructure platform for AI agents.

AgentMind focuses on building the backend systems that autonomous AI agents need to operate safely and at scale.

---

# What is AgentMind?

AgentMind provides:

- Agent identity and authentication
- Agent memory storage and retrieval
- Tool discovery and execution
- Rate limiting
- Audit logging
- MCP (Model Context Protocol) support
- Agent permissions and access control
- Vector memory search using ChromaDB

Think of it like:

> Firebase + MCP + Memory + Tool Infrastructure for AI Agents.

---

# Features

## Agent Registration

Agents can register and receive API keys.

## API Key Authentication

Every request is authenticated using:

```http
X-Agent-Key
```

## Agent Memory

Agents can:

- Save memories
- Search memories semantically
- Retrieve context later

## Tool Registry

Agents can:

- Discover tools
- Run tools dynamically
- Check permissions

## Built-in Tools

Current tools:

- Calculator Tool
- Memory Search Tool
- Echo Tool

## MCP Support

AgentMind includes an MCP server so external AI systems can connect using the Model Context Protocol.

## Rate Limiting

Protects the infrastructure from abuse.

## Audit Logs

Tracks:

- Which agent executed actions
- Which tools were used
- Request/response data
- Errors and traces

---

# Tech Stack

## Backend

- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- ChromaDB
- MCP Python SDK

## Infrastructure

- Railway
- Docker
- Uvicorn

## AI Infrastructure

- Vector Memory Search
- MCP Protocol
- Tool Execution Runtime

---

# Architecture

```text
External Agent
      ↓
MCP Server
      ↓
AgentMind API
      ↓
Authentication Layer
      ↓
Permissions + Rate Limits
      ↓
Memory + Tools + Audit Logs
      ↓
PostgreSQL / Redis / ChromaDB
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/patdal1810/agent-mind-apps.git
cd agentmind
```

## Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file:

```env
APP_NAME=AgentMind
Others...
```

---

# Running PostgreSQL and Redis

## Start Docker Containers

```bash
docker compose up -d
```

## Verify Containers

```bash
docker ps
```

---

# Run the API

```bash
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

---

# Register an Agent

## Endpoint

```http
POST /v1/agents/register
```

## Request Body

```json
{
  "name": "Research Agent",
  "purpose": "An AI agent for testing",
  "invite_code": "AGENTMIND-BETA-001",
  "permissions": [
    "memory:read",
    "memory:write",
    "tools:calculator:run",
    "tools:echo:run"
  ]
}
```

---

# MCP Support

Run MCP Inspector:

```bash
mcp dev app/mcp_server.py
```

Set environment variables:

```bash
export AGENTMIND_API_URL="http://127.0.0.1:8000"
export AGENTMIND_API_KEY="YOUR_API_KEY"
```

Available MCP tools:

- save_memory
- search_memory
- list_tools
- run_tool

---

# Deployment

## Railway Deployment

Deploy:

- FastAPI service
- PostgreSQL service
- Redis service

Set Railway Variables:

```env
DATABASE_URL=...
REDIS_URL=...
PUBLIC_BASE_URL=https://your-app.up.railway.app
```

---

# Security Features

- API key hashing
- Invite-only registration
- Permission-based access control
- Rate limiting
- Audit logging
- MCP isolation layer

---

# Future Roadmap

Planned upgrades:

- OpenAI reasoning agents
- Autonomous tool selection
- Multi-agent collaboration
- Agent-to-agent communication
- pgvector support
- Billing and usage plans
- Hosted MCP endpoints
- Webhook events
- Agent observability dashboard
- Tool marketplace

---

# License

MIT License

---

# Author

Built by Patrick Olumba
