from typing import Any

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    purpose: str | None = None
    permissions: list[str] = Field(default_factory=list)


class AgentCreateResponse(BaseModel):
    agent_id: int
    api_key: str
    message: str


class MemoryCreate(BaseModel):
    content: str


class MemorySearch(BaseModel):
    query: str
    limit: int = 5


class ToolRunRequest(BaseModel):
    input: dict[str, Any]


class StandardResponse(BaseModel):
    success: bool
    result: Any | None = None
    error: str | None = None
    trace_id: str
    latency_ms: int