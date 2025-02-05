#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cache
from types import TracebackType
from typing import AsyncIterator, Optional, Sequence, Type, Callable

import httpx
from httpx import AsyncClient

from ceylon.llm.models.support.http import AsyncHTTPClient, cached_async_http_client
from ceylon.llm.models.support.messages import ModelMessage, ModelResponse, StreamedResponse
from ceylon.llm.models.support.settings import ModelSettings
from ceylon.llm.models.support.tools import ToolDefinition
from ceylon.llm.models.support.usage import Usage, UsageLimits
from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import TracebackType
from typing import AsyncIterator, Optional, Sequence, Type, Any
import re
import json

from ceylon.llm.models.support.http import AsyncHTTPClient, cached_async_http_client
from ceylon.llm.models.support.messages import (
    ModelMessage,
    ModelResponse,
    StreamedResponse,
    MessageRole,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    ModelMessagePart
)
from ceylon.llm.models.support.settings import ModelSettings
from ceylon.llm.models.support.tools import ToolDefinition
from ceylon.llm.models.support.usage import Usage, UsageLimits


@dataclass
class ModelContext:
    """Context for a specific model run"""
    settings: ModelSettings
    tools: Sequence[ToolDefinition]
    usage_limits: Optional[UsageLimits] = None


class Model(ABC):
    """Base class for all language model implementations with tool support"""

    # Regex pattern for extracting tool calls - can be overridden by subclasses
    TOOL_CALL_PATTERN = re.compile(
        r'<tool_call>(?P<tool_json>.*?)</tool_call>',
        re.DOTALL
    )

    def __init__(
            self,
            model_name: str,
            api_key: Optional[str] = None,
            http_client: Optional[AsyncHTTPClient] = None
    ):
        """Initialize the model.

        Args:
            model_name: Name/identifier of the model
            api_key: Optional API key for authentication
            http_client: Optional HTTP client for making requests
        """
        self.model_name = model_name
        self.api_key = api_key
        self.http_client = http_client or cached_async_http_client()

    async def __aenter__(self) -> "Model":
        """Async context manager entry"""
        return self

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType]
    ) -> None:
        """Async context manager exit"""
        await self.close()

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources used by the model"""
        if self.http_client:
            await self.http_client.close()

    @abstractmethod
    async def request(
            self,
            messages: Sequence[ModelMessage],
            context: ModelContext
    ) -> tuple[ModelResponse, Usage]:
        """Make a request to the model.

        Args:
            messages: Sequence of messages to send to the model
            context: Context containing settings and tools

        Returns:
            Tuple of (model response, usage statistics)
        """
        pass

    @abstractmethod
    async def request_stream(
            self,
            messages: Sequence[ModelMessage],
            context: ModelContext
    ) -> AsyncIterator[StreamedResponse]:
        """Make a streaming request to the model.

        Args:
            messages: Sequence of messages to send to the model
            context: Context containing settings and tools

        Returns:
            AsyncIterator yielding streamed response chunks
        """
        pass

    def create_context(
            self,
            settings: Optional[ModelSettings] = None,
            tools: Optional[Sequence[ToolDefinition]] = None,
            usage_limits: Optional[UsageLimits] = None
    ) -> ModelContext:
        """Create a context for model execution.

        Args:
            settings: Optional model settings
            tools: Optional sequence of tool definitions
            usage_limits: Optional usage limits

        Returns:
            ModelContext instance
        """
        return ModelContext(
            settings=settings or ModelSettings(),
            tools=tools or [],
            usage_limits=usage_limits
        )

    def _validate_messages(self, messages: Sequence[ModelMessage]) -> None:
        """Validate that the message sequence is valid.

        Args:
            messages: Sequence of messages to validate

        Raises:
            ValueError: If messages are invalid
        """
        if not messages:
            raise ValueError("Messages sequence cannot be empty")

    def _check_usage_limits(self, usage: Usage, limits: UsageLimits) -> None:
        """Check if usage is within specified limits.

        Args:
            usage: Current usage statistics
            limits: Usage limits to enforce

        Raises:
            UsageLimitExceeded: If any limit is exceeded
        """
        if limits.request_limit and usage.requests >= limits.request_limit:
            raise UsageLimitExceeded(
                f"Request limit {limits.request_limit} exceeded"
            )
        if limits.request_tokens_limit and usage.request_tokens >= limits.request_tokens_limit:
            raise UsageLimitExceeded(
                f"Request tokens limit {limits.request_tokens_limit} exceeded"
            )
        if limits.response_tokens_limit and usage.response_tokens >= limits.response_tokens_limit:
            raise UsageLimitExceeded(
                f"Response tokens limit {limits.response_tokens_limit} exceeded"
            )

    def _format_tool_descriptions(self, tools: Sequence[ToolDefinition]) -> str:
        """Format tool descriptions for system message.

        Args:
            tools: Sequence of tool definitions

        Returns:
            Formatted tool descriptions string
        """
        if not tools:
            return ""

        tool_descriptions = []
        for tool in tools:
            desc = f"- {tool.name}: {tool.description}\n"
            desc += f"  Parameters: {json.dumps(tool.parameters_json_schema)}"
            tool_descriptions.append(desc)

        return (
            "You have access to the following tools:\n\n"
            f"{chr(10).join(tool_descriptions)}\n\n"
            "To use a tool, respond with XML tags like this:\n"
            "<tool_call>{\"tool_name\": \"tool_name\", \"args\": {\"arg1\": \"value1\"}}</tool_call>\n"
            "Wait for the tool result before continuing."
        )

    def _parse_tool_call(self, match: re.Match) -> Optional[ToolCallPart]:
        """Parse a tool call match into a ToolCallPart.

        Args:
            match: Regex match object containing tool call JSON

        Returns:
            ToolCallPart if valid, None if invalid
        """
        try:
            tool_data = json.loads(match.group('tool_json'))
            if isinstance(tool_data, dict) and 'tool_name' in tool_data and 'args' in tool_data:
                return ToolCallPart(
                    tool_name=tool_data['tool_name'],
                    args=tool_data['args']
                )
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _parse_response(self, text: str) -> list[ModelMessagePart]:
        """Parse response text into message parts.

        Args:
            text: Raw response text from model

        Returns:
            List of ModelMessagePart objects
        """
        parts = []
        current_text = []
        last_end = 0

        # Find all tool calls in the response
        for match in self.TOOL_CALL_PATTERN.finditer(text):
            # Add any text before the tool call
            if match.start() > last_end:
                prefix_text = text[last_end:match.start()].strip()
                if prefix_text:
                    current_text.append(prefix_text)

            # Parse and add the tool call
            tool_call = self._parse_tool_call(match)
            if tool_call:
                # If we have accumulated text, add it first
                if current_text:
                    parts.append(TextPart(text=' '.join(current_text)))
                    current_text = []
                parts.append(tool_call)
            else:
                # If tool call parsing fails, treat it as regular text
                current_text.append(match.group(0))

            last_end = match.end()

        # Add any remaining text after the last tool call
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                current_text.append(remaining)

        # Add any accumulated text as final part
        if current_text:
            parts.append(TextPart(text=' '.join(current_text)))

        return parts


class UsageLimitExceeded(Exception):
    """Raised when usage limits are exceeded"""
    pass


@cache
def get_user_agent() -> str:
    """Get the user agent string for the HTTP client."""
    from ceylon import version

    return f'ceylon-ai/{version()}'


@cache
def cached_async_http_client(timeout: int = 600, connect: int = 5,
                             base_url: str = "http://localhost:11434") -> Callable[[], AsyncClient]:
    """Cached HTTPX async client so multiple agents and calls can share the same client.

    There are good reasons why in production you should use a `httpx.AsyncClient` as an async context manager as
    described in [encode/httpx#2026](https://github.com/encode/httpx/pull/2026), but when experimenting or showing
    examples, it's very useful not to, this allows multiple Agents to use a single client.

    The default timeouts match those of OpenAI,
    see <https://github.com/openai/openai-python/blob/v1.54.4/src/openai/_constants.py#L9>.
    """

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"User-Agent": get_user_agent()},
            timeout=timeout,
            base_url=base_url
        )

    return factory
