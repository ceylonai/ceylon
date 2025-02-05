import json
from typing import Any, AsyncIterator, Optional, Sequence

import httpx

from ceylon.llm.models import Model, ModelContext, cached_async_http_client
from ceylon.llm.models.support.messages import (
    MessageRole,
    ModelMessage,
    ModelResponse,
    StreamedResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart
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
        self.client = cached_async_http_client(timeout=self.timeout, base_url=self.base_url)

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client().aclose()

    def _format_messages(self, messages: Sequence[ModelMessage], context: ModelContext) -> str:
        """Format messages for Ollama API.

        Args:
            messages: Messages to format
            context: Context containing tools and settings

        Returns:
            Formatted prompt string
        """
        formatted_parts = []

        # Add tool definitions if available
        if context.tools:
            formatted_parts.append(f"System: {self._format_tool_descriptions(context.tools)}")

        # Format conversation history
        for message in messages:
            prefix = {
                MessageRole.SYSTEM: "System",
                MessageRole.USER: "User",
                MessageRole.ASSISTANT: "Assistant",
                MessageRole.TOOL: "Tool"
            }.get(message.role, "Unknown")

            content = []
            for part in message.parts:
                if isinstance(part, TextPart):
                    content.append(part.text)
                elif isinstance(part, ToolCallPart):
                    tool_call = {
                        "tool_name": part.tool_name,
                        "args": part.args
                    }
                    content.append(
                        f"<tool_call>{json.dumps(tool_call)}</tool_call>"
                    )
                elif isinstance(part, ToolReturnPart):
                    content.append(
                        f"Result from {part.tool_name}: {json.dumps(part.content)}"
                    )

            formatted_parts.append(f"{prefix}: {' '.join(content)}")

        # Add final prompt for assistant
        formatted_parts.append("Assistant:")

        return "\n\n".join(formatted_parts)

    def _prepare_request_data(
            self,
            messages: Sequence[ModelMessage],
            context: ModelContext,
            stream: bool = False
    ) -> dict[str, Any]:
        """Prepare the request data for Ollama API"""
        data = {
            "model": self.model_name,
            "prompt": self._format_messages(messages, context),
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
            context: Context containing settings and tools

        Returns:
            Tuple of (model response, usage statistics)
        """
        self._validate_messages(messages)

        data = self._prepare_request_data(messages, context, stream=False)

        # Make request
        response = await self.client().post(
            "/api/generate",
            json=data
        )
        response.raise_for_status()
        result = response.json()

        # Parse response and create usage stats
        response_text = result.get("response", "")
        response_parts = self._parse_response(response_text)

        usage = Usage(
            request_tokens=result.get("prompt_eval_count", 0),
            response_tokens=result.get("eval_count", 0),
            total_tokens=(
                    result.get("prompt_eval_count", 0) +
                    result.get("eval_count", 0)
            ),
            requests=1
        )

        return ModelResponse(parts=response_parts), usage

    async def request_stream(
            self,
            messages: Sequence[ModelMessage],
            context: ModelContext
    ) -> AsyncIterator[StreamedResponse]:
        """Make a streaming request to the Ollama API.

        Args:
            messages: Sequence of messages to send
            context: Context containing settings and tools

        Yields:
            StreamedResponse objects containing response chunks
        """
        self._validate_messages(messages)

        data = self._prepare_request_data(messages, context, stream=True)

        # Track state across chunks
        current_text = []
        total_usage = Usage(requests=1)

        async with self.client().stream(
                "POST",
                "/api/generate",
                json=data
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "response" in chunk:
                    chunk_text = chunk["response"]
                    current_text.append(chunk_text)

                    # Try to parse complete tool calls
                    accumulated_text = ''.join(current_text)
                    for match in self.TOOL_CALL_PATTERN.finditer(accumulated_text):
                        tool_call = self._parse_tool_call(match)
                        if tool_call:
                            # Yield any text before the tool call
                            prefix = accumulated_text[:match.start()].strip()
                            if prefix:
                                yield StreamedResponse(
                                    delta=TextPart(text=prefix),
                                    usage=None
                                )

                            # Yield the tool call
                            yield StreamedResponse(
                                delta=tool_call,
                                usage=None
                            )

                            # Keep any remaining text
                            current_text = [accumulated_text[match.end():]]
                            break
                    else:
                        # If no tool call found and we've accumulated enough text
                        if len(accumulated_text) > 100:
                            yield StreamedResponse(
                                delta=TextPart(text=accumulated_text),
                                usage=None
                            )
                            current_text = []

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

                if chunk.get("done", False):
                    # Yield any remaining text
                    remaining_text = ''.join(current_text).strip()
                    if remaining_text:
                        yield StreamedResponse(
                            delta=TextPart(text=remaining_text),
                            usage=total_usage
                        )
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