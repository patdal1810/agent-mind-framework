from typing import Any

import requests


class AgentMindError(Exception):
    """Base error for AgentMind SDK."""


class AgentMindAuthError(AgentMindError):
    """Raised when authentication fails."""


class AgentMindAPIError(AgentMindError):
    """Raised when the AgentMind API returns an error."""


class AgentMindClient:
    """
    Python SDK client for AgentMind.

    This class wraps the AgentMind REST API so agents and developers
    can call memory, tools, and runtime endpoints easily.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["X-Agent-Key"] = self.api_key

        return headers

    def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> dict[str, Any]:
        if auth_required and not self.api_key:
            raise AgentMindAuthError("API key is required for this request.")

        url = f"{self.base_url}{path}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=json_data,
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise AgentMindAPIError(f"Request failed: {str(error)}") from error

        if response.status_code == 401:
            raise AgentMindAuthError("Invalid or missing AgentMind API key.")

        if response.status_code >= 400:
            try:
                error_body = response.json()
            except ValueError:
                error_body = response.text

            raise AgentMindAPIError(
                f"AgentMind API error {response.status_code}: {error_body}"
            )

        try:
            return response.json()
        except ValueError as error:
            raise AgentMindAPIError("Invalid JSON response from AgentMind API.") from error

    def get_manifest(self) -> dict[str, Any]:
        """
        Get AgentMind machine-readable manifest.

        This does not require an API key.
        """
        return self._request(
            method="GET",
            path="/.well-known/agent.json",
            auth_required=False,
        )

    def register_agent(
        self,
        name: str,
        purpose: str,
        invite_code: str,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Register a new agent.

        This returns an API key. Store it safely.
        """
        payload = {
            "name": name,
            "purpose": purpose,
            "invite_code": invite_code,
            "permissions": permissions or [],
        }

        return self._request(
            method="POST",
            path="/v1/agents/register",
            json_data=payload,
            auth_required=False,
        )

    def me(self) -> dict[str, Any]:
        """
        Get the current authenticated agent profile.
        """
        return self._request(
            method="GET",
            path="/v1/agents/me",
        )

    def save_memory(self, content: str) -> dict[str, Any]:
        """
        Save a memory for the current agent.
        """
        return self._request(
            method="POST",
            path="/v1/memories",
            json_data={"content": content},
        )

    def search_memory(
        self,
        query: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Search stored memories for the current agent.
        """
        return self._request(
            method="POST",
            path="/v1/memories/search",
            json_data={
                "query": query,
                "limit": limit,
            },
        )

    def list_tools(self) -> dict[str, Any]:
        """
        List available tools with schemas, validation rules, and examples.
        """
        return self._request(
            method="GET",
            path="/v1/tools",
        )

    def get_tool(self, tool_name: str) -> dict[str, Any]:
        """
        Get details for one tool.
        """
        return self._request(
            method="GET",
            path=f"/v1/tools/{tool_name}",
        )

    def run_tool(
        self,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Run a specific AgentMind tool.
        """
        return self._request(
            method="POST",
            path=f"/v1/tools/{tool_name}/run",
            json_data={"input": input_data},
        )

    def chat(
        self,
        task: str,
        memory_search_limit: int = 5,
        save_result_to_memory: bool = False,
    ) -> dict[str, Any]:
        """
        Send a task to AgentMind Runtime.

        AgentMind will:
        - search memory
        - reason
        - choose tools when needed
        - return structured output
        """
        return self._request(
            method="POST",
            path="/v1/agent/chat",
            json_data={
                "task": task,
                "memory_search_limit": memory_search_limit,
                "save_result_to_memory": save_result_to_memory,
            },
        )
    
    
def health_check(self) -> dict[str, Any]:
    """
    Check if the AgentMind API is reachable.
    """
    try:
        manifest = self.get_manifest()

        return {
            "success": True,
            "message": "AgentMind API is reachable.",
            "manifest": manifest,
        }

    except Exception as error:
        return {
            "success": False,
            "message": "Could not reach AgentMind API.",
            "error": str(error),
            "base_url": self.base_url,
        }