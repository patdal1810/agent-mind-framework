from typing import Any

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    purpose: str | None = None
    invite_code: str
    capabilities: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class AgentCreateResponse(BaseModel):
    agent_id: int
    api_key: str
    message: str

class AgentDiscoverResponse(BaseModel):
    id: int
    name: str
    purpose: str | None = None
    capabilities: list[str] = Field(default_factory=list)


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

class AgentChatRequest(BaseModel):
    task: str
    save_result_to_memory: bool = False
    memory_search_limit: int = 5
    workflow_id: int | None = None

class AgentChatResponse(BaseModel):
    success: bool
    task: str
    response: str | None = None
    memories_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
    trace_id: str
    latency_ms: int

class AgentDelegateRequest(BaseModel):
    target_agent_id: int
    task: str
    memory_search_limit: int = 5
    save_result_to_memory: bool = False

class WorkflowCreateRequest(BaseModel):
    objective: str


class WorkflowResponse(BaseModel):
    id: int
    objective: str
    status: str

class ToolRegisterRequest(BaseModel):
    name: str
    description: str
    permission_required: str

    input_schema: dict[str, Any]

    validation_rules: dict[str, Any] | list[str] | None = None

    example_request: dict[str, Any] | None = None

    is_webhook: bool = False

    webhook_url: str | None = None

    webhook_method: str = "POST"

    webhook_headers: dict[str, Any] | None = None

    webhook_timeout_seconds: int = 30