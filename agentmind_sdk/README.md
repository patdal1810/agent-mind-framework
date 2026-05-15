# AgentMind Python SDK

Python SDK for AgentMind, an infrastructure platform for autonomous AI agents.

---

# Installation

## Install locally

```bash
pip install -e .
```

---

# Basic Usage

```python
from agentmind import AgentMindClient

client = AgentMindClient(
    base_url="https://your-agentmind-api.up.railway.app",
    api_key="agm_your_api_key"
)

response = client.chat("What is 45 * 12?")
print(response)
```

---

# Register an Agent

```python
from agentmind import AgentMindClient

client = AgentMindClient(
    base_url="https://your-agentmind-api.up.railway.app"
)

result = client.register_agent(
    name="Research Agent",
    purpose="Testing AgentMind",
    invite_code="AGENTMIND-BETA-001",
    permissions=[
        "memory:read",
        "memory:write",
        "tools:calculator:run",
        "tools:echo:run",
        "tools:quadratic_solver:run"
    ]
)

print(result["api_key"])
```

---

# Save Memory

```python
client.save_memory(
    "This agent prefers short technical answers."
)
```

---

# Search Memory

```python
client.search_memory(
    "answer style"
)
```

---

# List Available Tools

```python
client.list_tools()
```

---

# Get Tool Details

```python
client.get_tool("quadratic_solver")
```

---

# Run Tool Directly

```python
client.run_tool(
    "calculator",
    {
        "expression": "45 * 12"
    }
)
```

---

# Runtime Chat

```python
client.chat(
    task="Solve x^2 - 5x + 6 = 0",
    memory_search_limit=5,
    save_result_to_memory=False
)
```


---

# Features

- Agent authentication
- Memory storage
- Vector memory search
- Tool discovery
- Tool execution
- Autonomous runtime reasoning
- MCP-compatible architecture
- Structured validation
- Tool schema registry
- Railway deployment support

---

# Architecture

```text
Developer Agent
       ↓
AgentMind SDK
       ↓
AgentMind API
       ↓
Runtime + Memory + Tools
       ↓
PostgreSQL / Redis / ChromaDB
```

---

# Error Handling

The SDK includes:

- `AgentMindError`
- `AgentMindAuthError`
- `AgentMindAPIError`

Example:

```python
from agentmind import (
    AgentMindClient,
    AgentMindAPIError
)

try:
    client.chat("What is 45 * 12?")
except AgentMindAPIError as error:
    print(error)
```

---

# SDK Methods

| Method | Description |
|---|---|
| `get_manifest()` | Get platform manifest |
| `register_agent()` | Register new agent |
| `me()` | Get current agent |
| `save_memory()` | Save memory |
| `search_memory()` | Search memories |
| `list_tools()` | List all tools |
| `get_tool()` | Get one tool schema |
| `run_tool()` | Execute tool |
| `chat()` | Use autonomous runtime |

---

# Local Testing

```bash
python test_sdk.py
```

---

# Future Improvements

- Async SDK
- Streaming runtime responses
- Built-in retries
- Typed response models
- CLI support
- WebSocket support
- Hosted MCP integration

---

# Author

Built by Olumba Chidubem Patrick
