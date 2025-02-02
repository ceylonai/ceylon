import json
from typing import Any, AsyncIterator, Optional, Sequence

import httpx

from ceylon.llm.models import Model, ModelContext
from ceylon.llm.models.support.messages import (
    MessageRole,
    ModelMessage,
    ModelResponse,
    StreamedResponse,
    TextPart,
    ToolCallPart
)
from ceylon.llm.models.support.usage import Usage


class OllamaModel(Model):
    """Implementation of the Model class for Ollama API"""

    def __init__(
            self,
            model_name: str,
            base_url: str = "http://localhost:11434",
            timeout: float = 60.0,
            **kwargs: Any
    ):
        """Initialize the Ollama model.
        
        Args:
            model_name: Name of the Ollama model to use
            base_url: Base URL for the Ollama API
            timeout: Request timeout in seconds
        """
        super().__init__(model_name, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout
        )

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()

    def _format_messages(self, messages: Sequence[ModelMessage]) -> str:
        """Format messages for Ollama API.

        Ollama's generate endpoint expects a prompt string, so we format
        the messages into a conversation format.
        """
        formatted_parts = []

        for message in messages:
            if message.role == MessageRole.SYSTEM:
                formatted_parts.append(f"System: {self._get_text_content(message)}")
            elif message.role == MessageRole.USER:
                formatted_parts.append(f"User: {self._get_text_content(message)}")
            elif message.role == MessageRole.ASSISTANT:
                formatted_parts.append(f"Assistant: {self._get_text_content(message)}")
            elif message.role == MessageRole.TOOL:
                # Include tool name in response if available
                tool_name = self._get_tool_name(message)
                formatted_parts.append(f"Tool ({tool_name}): {self._get_text_content(message)}")

        # Add a final Assistant: prompt to indicate it's the model's turn
        formatted_parts.append("Assistant:")

        return "\n\n".join(formatted_parts)

    def _get_text_content(self, message: ModelMessage) -> str:
        """Extract text content from message parts"""
        parts = []
        for part in message.parts:
            if isinstance(part, TextPart):
                parts.append(part.text)
        return " ".join(parts)

    def _get_tool_name(self, message: ModelMessage) -> str:
        """Get tool name from message if present"""
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                return part.tool_name
        return "unknown"

    def _prepare_request_data(self, messages: Sequence[ModelMessage], context: ModelContext, stream: bool = False) -> dict[str, Any]:
        """Prepare the request data for Ollama API"""
        data = {
            "model": self.model_name,
            "prompt": self._format_messages(messages),
            "stream": stream
        }

        # Add model settings
        if context.settings:
            options = {}
            if context.settings.temperature is not None:
                options["temperature"] = context.settings.temperature
            if context.settings.top_p is not None:
                options["top_p"] = context.settings.top_p
            if context.settings.max_tokens is not None:
                options["num_predict"] = context.settings.max_tokens
            if options:
                data["options"] = options

        return data

    async def request(
            self,
            messages: Sequence[ModelMessage],
            context: ModelContext
    ) -> tuple[ModelResponse, Usage]:
        """Make a request to the Ollama API.

        Args:
            messages: Sequence of messages to send
            context: Context containing settings

        Returns:
            Tuple of (model response, usage statistics)
        """
        self._validate_messages(messages)

        data = self._prepare_request_data(messages, context, stream=False)

        # Make request
        response = await self.client.post(
            "/api/generate",
            json=data
        )
        response.raise_for_status()
        result = response.json()

        # Extract response and usage
        response_text = result.get("response", "")
        usage = Usage(
            request_tokens=result.get("prompt_eval_count", 0),
            response_tokens=result.get("eval_count", 0),
            total_tokens=(
                    result.get("prompt_eval_count", 0) +
                    result.get("eval_count", 0)
            ),
            requests=1
        )

        return ModelResponse(parts=[TextPart(text=response_text)]), usage

    async def request_stream(
            self,
            messages: Sequence[ModelMessage],
            context: ModelContext
    ) -> AsyncIterator[StreamedResponse]:
        """Make a streaming request to the Ollama API.

        Args:
            messages: Sequence of messages to send
            context: Context containing settings

        Yields:
            StreamedResponse objects containing response chunks
        """
        self._validate_messages(messages)

        data = self._prepare_request_data(messages, context, stream=True)

        # Make streaming request
        async with self.client.stream(
                "POST",
                "/api/generate",
                json=data
        ) as response:
            response.raise_for_status()

            # Track usage across chunks
            total_usage = Usage(requests=1)

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract chunk text and update usage
                if "response" in chunk:
                    # Update usage stats
                    chunk_usage = Usage(
                        request_tokens=chunk.get("prompt_eval_count", 0),
                        response_tokens=chunk.get("eval_count", 0),
                        total_tokens=(
                                chunk.get("prompt_eval_count", 0) +
                                chunk.get("eval_count", 0)
                        )
                    )
                    total_usage.add(chunk_usage)

                    # Yield response chunk
                    yield StreamedResponse(
                        delta=TextPart(text=chunk["response"]),
                        usage=chunk_usage
                    )

                # Handle done message
                if chunk.get("done", False):
                    break

    @classmethod
    async def list_models(cls, base_url: str = "http://localhost:11434") -> list[dict[str, Any]]:
        """List available Ollama models.

        Args:
            base_url: Base URL for the Ollama API

        Returns:
            List of model information dictionaries
        """
        async with httpx.AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])