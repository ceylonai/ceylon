#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from inspect import signature, Parameter
from typing import Callable, Dict, List

from ceylon.llm.models.support.tools import ToolDefinition


class ToolRegistry:
    """Registry to store and manage tool definitions."""

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, func: Callable) -> None:
        """Register a new tool with the registry."""
        # Generate JSON schema from function signature
        sig = signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param.kind == Parameter.VAR_POSITIONAL or param.kind == Parameter.VAR_KEYWORD:
                continue

            param_type = param.annotation if param.annotation != Parameter.empty else str
            properties[param_name] = {
                "type": self._get_json_type(param_type),
                "description": f"Parameter {param_name}"
            }

            if param.default == Parameter.empty:
                required.append(param_name)

        parameters_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }

        # Create tool definition
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters_json_schema=parameters_schema,
            function=func
        )

        self.tools[name] = tool_def

    def _get_json_type(self, python_type: type) -> str:
        """Convert Python type to JSON schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        return type_map.get(python_type, "string")

    def get_tools(self) -> List[ToolDefinition]:
        """Get all registered tools."""
        return list(self.tools.values())
