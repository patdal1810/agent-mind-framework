import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


AGENTMIND_API_URL = (
    os.getenv("AGENTMIND_API_URL", "http://127.0.0.1:8000")
    .strip()
    .replace("\n", "")
    .replace("\r", "")
    .rstrip("/")
)

AGENTMIND_API_KEY = (
    os.getenv("AGENTMIND_API_KEY", "")
    .strip()
    .replace("\n", "")
    .replace("\r", "")
)


mcp = FastMCP("AgentMind")


def get_headers() -> dict[str, str]:
    if not AGENTMIND_API_KEY:
        raise RuntimeError("AGENTMIND_API_KEY is missing")

    return {
        "X-Agent-Key": AGENTMIND_API_KEY,
    }


@mcp.tool()
async def save_memory(content: str) -> dict[str, Any]:
    """Save a memory for the current agent."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AGENTMIND_API_URL}/v1/memories",
            headers=get_headers(),
            json={"content": content},
            timeout=20,
        )

    response.raise_for_status()
    return response.json()


@mcp.tool()
async def search_memory(query: str, limit: int = 5) -> dict[str, Any]:
    """Search saved memories for the current agent."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AGENTMIND_API_URL}/v1/memories/search",
            headers=get_headers(),
            json={
                "query": query,
                "limit": limit,
            },
            timeout=20,
        )

    response.raise_for_status()
    return response.json()


@mcp.tool()
async def list_tools() -> dict[str, Any]:
    """List available AgentMind tools."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AGENTMIND_API_URL}/v1/tools",
            headers=get_headers(),
            timeout=20,
        )

    response.raise_for_status()
    return response.json()


@mcp.tool()
async def run_tool(tool_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """Run an AgentMind tool by name."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{AGENTMIND_API_URL}/v1/tools/{tool_name}/run",
            headers=get_headers(),
            json={"input": input_data},
            timeout=20,
        )

    response.raise_for_status()
    return response.json()


@mcp.resource("agentmind://manifest")
async def manifest() -> dict[str, Any]:
    """Return the AgentMind machine-readable manifest."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AGENTMIND_API_URL}/.well-known/agent.json",
            timeout=20,
        )

    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    mcp.run()