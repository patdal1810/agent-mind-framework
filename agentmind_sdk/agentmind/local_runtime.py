import json
from typing import Any, Callable

from openai import OpenAI


class LocalTool:
    def __init__(
        self,
        name: str,
        description: str,
        function: Callable[[dict[str, Any]], dict[str, Any]],
        input_schema: dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.function = function
        self.input_schema = input_schema

    def to_openai_tool(self) -> dict[str, Any]:
        """
        Convert local Python tool into OpenAI tool schema.

        This lets the LLM know:
        - tool name
        - what it does
        - what input it expects
        """

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the developer's local Python function.
        """

        return self.function(input_data)


class LocalToolRuntime:
    """
    Lightweight runtime for developer-owned local tools.

    AgentMind backend still handles:
    - workflows
    - task history
    - memory
    - agent identity

    This local runtime handles:
    - custom developer tools
    - local business logic
    """

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4.1-mini",
    ):
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.tools: dict[str, LocalTool] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        function: Callable[[dict[str, Any]], dict[str, Any]],
        input_schema: dict[str, Any],
    ):
        """
        Register a developer-owned local tool.

        Example:
        runtime.register_tool(
            name="fraud_checker",
            description="Checks transaction fraud risk",
            function=fraud_checker,
            input_schema={...}
        )
        """

        self.tools[name] = LocalTool(
            name=name,
            description=description,
            function=function,
            input_schema=input_schema,
        )

    def run(
        self,
        task: str,
        system_prompt: str | None = None,
        max_tool_rounds: int = 5,
    ) -> dict[str, Any]:
        """
        Run a task using local developer tools.

        The model can call tools multiple times.

        Example:
        transaction_lookup -> fraud_checker -> final answer
        """

        tools = [
            tool.to_openai_tool()
            for tool in self.tools.values()
        ]

        messages = [
            {
                "role": "system",
                "content": system_prompt
                or (
                    "You are a local business-agent runtime. "
                    "Use available tools when needed. "
                    "Do not invent tool results. "
                    "If a tool is needed, call it."
                ),
            },
            {
                "role": "user",
                "content": task,
            },
        ]

        tool_calls_log = []

        for _ in range(max_tool_rounds):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            if not assistant_message.tool_calls:
                return {
                    "success": True,
                    "response": assistant_message.content or "",
                    "tool_calls": tool_calls_log,
                }

            messages.append(assistant_message)

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                raw_args = tool_call.function.arguments or "{}"

                try:
                    tool_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    tool_args = {}

                local_tool = self.tools.get(tool_name)

                if not local_tool:
                    tool_result = {
                        "error": f"Tool '{tool_name}' is not registered."
                    }
                    status = "failed"
                else:
                    try:
                        tool_result = local_tool.run(tool_args)
                        status = "success"
                    except Exception as error:
                        tool_result = {
                            "error": str(error)
                        }
                        status = "failed"

                tool_calls_log.append(
                    {
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "status": status,
                        "result": tool_result if status == "success" else None,
                        "error": tool_result.get("error") if status == "failed" else None,
                    }
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            {
                                "status": status,
                                "result": tool_result,
                            },
                            default=str,
                        ),
                    }
                )

        return {
            "success": False,
            "response": "Maximum local tool rounds reached.",
            "tool_calls": tool_calls_log,
        }