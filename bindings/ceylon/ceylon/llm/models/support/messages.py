#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
# messages.py
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Union
from enum import Enum


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class TextPart:
    """Text content from the model"""
    text: str


@dataclass
class ToolCallPart:
    """Tool/function call from the model"""
    tool_name: str
    args: dict[str, Any]


@dataclass
class ToolReturnPart:
    """Result from a tool execution"""
    tool_name: str
    content: Any


@dataclass
class SystemPromptPart:
    """System instructions to the model"""
    content: str


@dataclass
class UserPromptPart:
    """User input to be processed"""
    content: str


@dataclass
class RetryPromptPart:
    """Request for the model to retry an operation"""
    tool_name: str
    content: str


ModelMessagePart = Union[
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    SystemPromptPart,
    UserPromptPart,
    RetryPromptPart
]


@dataclass
class ModelMessage:
    """A message in the conversation"""
    role: MessageRole
    parts: Sequence[ModelMessagePart]


@dataclass
class ModelResponse:
    """Response from the model"""
    parts: Sequence[ModelMessagePart]


@dataclass
class StreamedResponse:
    """Chunk of a streaming response"""
    delta: ModelMessagePart
    usage: Optional['Usage'] = None
