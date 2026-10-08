from typing import Callable, Any, Dict, Optional
from pydantic import BaseModel


class ToolMetadata(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    requires_approval: bool = False


class Tool:
    def __init__(self, metadata: ToolMetadata, func: Callable):
        self.metadata = metadata
        self.func = func

    def execute(self, **kwargs) -> Any:
        return self.func(**kwargs)


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, metadata: ToolMetadata, func: Callable):
        if not metadata.name.strip():
            raise ValueError("Tool name cannot be empty.")

        if not callable(func):
            raise TypeError("Tool function must be callable.")

        self.tools[metadata.name] = Tool(metadata, func)

    def get_tool(self, name: str) -> Optional[Tool]:
        if not isinstance(name, str):
            return None

        name = name.strip()

        if not name:
            return None

        return self.tools.get(name)

    def has_tool(self, name: str) -> bool:
        return self.get_tool(name) is not None

    def list_tools(self) -> list:
        return [
            tool.metadata.model_dump()
            for tool in self.tools.values()
        ]

    # ==========================================
    # TYPE VALIDATION
    # ==========================================

    def _validate_value_type(
        self,
        value: Any,
        expected_type: Any
    ) -> bool:

        if expected_type in ("float", float):
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        if expected_type in ("int", "integer", int):
            return isinstance(value, int) and not isinstance(value, bool)

        if expected_type in ("str", "string", str):
            return isinstance(value, str)

        if expected_type in ("bool", "boolean", bool):
            return isinstance(value, bool)

        # Unknown type definitions are not rejected here.
        return True

    # ==========================================
    # TOOL CALL VALIDATION
    # ==========================================

    def validate_tool_call(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> bool:

        tool = self.get_tool(name)

        # Tool must exist.
        if tool is None:
            return False

        # Arguments must be a dictionary.
        if not isinstance(arguments, dict):
            return False

        schema = tool.metadata.input_schema or {}

        # ------------------------------------------
        # SIMPLE PROJECT SCHEMA
        # Example:
        # {"a": "float", "b": "float"}
        # ------------------------------------------

        if (
            "properties" not in schema
            and "required" not in schema
        ):

            expected_arguments = set(schema.keys())
            supplied_arguments = set(arguments.keys())

            # Reject missing or unexpected arguments.
            if expected_arguments != supplied_arguments:
                return False

            # Validate argument types.
            for argument_name, expected_type in schema.items():

                if not self._validate_value_type(
                    arguments[argument_name],
                    expected_type
                ):
                    return False

            return True

        # ------------------------------------------
        # JSON-SCHEMA STYLE
        # ------------------------------------------

        properties = schema.get("properties", {})

        required = schema.get(
            "required",
            list(properties.keys())
        )

        # Required arguments must exist.
        for field in required:
            if field not in arguments:
                return False

        # No unexpected arguments.
        for argument_name in arguments:
            if argument_name not in properties:
                return False

        # Validate known argument types.
        for argument_name, value in arguments.items():

            property_schema = properties.get(
                argument_name,
                {}
            )

            expected_type = property_schema.get("type")

            if expected_type:
                if not self._validate_value_type(
                    value,
                    expected_type
                ):
                    return False

        return True


registry = ToolRegistry()