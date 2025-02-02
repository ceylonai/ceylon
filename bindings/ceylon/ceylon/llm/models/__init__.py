#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import TracebackType
from typing import AsyncIterator, Optional, Sequence, Type

from ceylon.llm.models.support.http import AsyncHTTPClient, cached_async_http_client
from ceylon.llm.models.support.messages import ModelMessage, ModelResponse, StreamedResponse
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
    """Base class for all language model implementations"""

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
        if limits.total_tokens and usage.total_tokens >= limits.total_tokens:
            raise UsageLimitExceeded(
                f"Total token limit {limits.total_tokens} exceeded"
            )


class UsageLimitExceeded(Exception):
    """Raised when usage limits are exceeded"""
    pass
