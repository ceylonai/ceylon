#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
# tools.py
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional


@dataclass
class ToolDefinition:
    """Definition of a tool/function that can be called by the model"""
    name: str
    description: str
    parameters_json_schema: dict[str, Any]
    function: Callable[..., Coroutine[Any, Any, Any]]
    outer_typed_dict_key: Optional[str] = None
