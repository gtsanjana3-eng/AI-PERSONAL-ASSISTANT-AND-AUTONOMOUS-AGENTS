import httpx
import json
from typing import Dict, Any, Optional

from backend.config import settings
from backend.tools.registry import registry


def _build_system_prompt() -> str:
    tools_info = []

    for name, tool in registry.tools.items():
        tools_info.append({
            "name": name,
            "description": tool.metadata.description,
            "input_schema": tool.metadata.input_schema,
            "requires_approval": tool.metadata.requires_approval
        })

    return f"""You are an AI task planner.

Analyze the user's request and create a safe, step-by-step task plan.

Available tools:
{json.dumps(tools_info, indent=2)}

IMPORTANT SAFETY RULES:

1. You may ONLY use tools from the Available tools list.
2. NEVER invent a new tool.
3. NEVER execute tools yourself.
4. Only create a plan describing which registered tools should be used.
5. Tool arguments MUST match the tool's input schema.
6. Do not include unexpected tool arguments.
7. If no tool is needed, use tool_name null and tool_args {{}}.
8. Do not output Python code, shell commands, or arbitrary executable code.
9. Do not output markdown.

You MUST output ONLY valid JSON in exactly this structure:

{{
    "intent": "Short description of user intent",
    "tasks": [
        {{
            "id": 1,
            "description": "Step description",
            "tool_name": "name_of_registered_tool_or_null",
            "tool_args": {{"arg1": "value"}}
        }}
    ]
}}

Do NOT output markdown formatting such as ```json.
"""


def _validate_plan(plan_data: Any) -> bool:
    """
    Validate the complete plan returned by the LLM
    before allowing it into the orchestrator.
    """

    if not isinstance(plan_data, dict):
        return False

    # ------------------------------------------
    # Validate top-level structure
    # ------------------------------------------

    if "intent" not in plan_data:
        return False

    if "tasks" not in plan_data:
        return False

    if not isinstance(plan_data["intent"], str):
        return False

    if not isinstance(plan_data["tasks"], list):
        return False

    # ------------------------------------------
    # Validate every task
    # ------------------------------------------

    for task in plan_data["tasks"]:

        if not isinstance(task, dict):
            return False

        # Required task fields
        if "id" not in task:
            return False

        if "description" not in task:
            return False

        if "tool_name" not in task:
            return False

        if "tool_args" not in task:
            return False

        # Validate field types
        if not isinstance(task["id"], int):
            return False

        if not isinstance(task["description"], str):
            return False

        if not isinstance(task["tool_args"], dict):
            return False

        tool_name = task["tool_name"]

        # --------------------------------------
        # No tool requested
        # --------------------------------------

        if tool_name is None:

            if task["tool_args"]:
                return False

            continue

        # --------------------------------------
        # Tool MUST exist
        # --------------------------------------

        if not isinstance(tool_name, str):
            return False

        tool = registry.get_tool(tool_name)

        if tool is None:
            return False

        # --------------------------------------
        # Validate tool arguments
        # --------------------------------------

        if not registry.validate_tool_call(
            tool_name,
            task["tool_args"]
        ):
            return False

    return True


def call_llm_planner(
    user_input: str
) -> Optional[Dict[str, Any]]:

    if not settings.LLM_API_KEY:
        return None

    url = (
        f"{settings.LLM_BASE_URL.rstrip('/')}"
        "/chat/completions"
    )

    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": _build_system_prompt()
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        "response_format": {
            "type": "json_object"
        }
    }

    try:

        with httpx.Client(timeout=10.0) as client:

            response = client.post(
                url,
                headers=headers,
                json=payload
            )

            response.raise_for_status()

            data = response.json()

            content = (
                data["choices"][0]["message"]["content"]
            )

            plan_data = json.loads(content)

            # Final security validation
            if not _validate_plan(plan_data):
                return None

            return plan_data

    except Exception:
        return None