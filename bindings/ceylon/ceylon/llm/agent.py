#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Sequence

from pydantic import BaseModel

from ceylon.llm.models import Model, ModelSettings, ModelMessage
from ceylon.llm.models.support.messages import (
    MessageRole,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    ModelMessagePart
)
from ceylon.llm.models.support.tools import ToolDefinition
from ceylon.processor.agent import ProcessWorker
from ceylon.processor.data import ProcessRequest


@dataclass
class LLMResponse:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class LLMConfig(BaseModel):
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000
    stop_sequences: list[str] = []
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    tools: Optional[Sequence[ToolDefinition]] = None
    parallel_tool_calls: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True


class LLMAgent(ProcessWorker):
    """
    An agent that processes tasks using configurable LLM capabilities.
    Supports multiple LLM backends through the Model interface.
    """

    def __init__(
            self,
            name: str,
            llm_model: Model,
            config: LLMConfig,
            role: str = "llm_processor",
            max_concurrent_tasks: int = 3
    ):
        super().__init__(
            name=name,
            role=role
        )
        self.llm_model: Model = llm_model
        self.config = config
        self.response_cache: Dict[str, LLMResponse] = {}
        self.processing_lock = asyncio.Lock()

        # Initialize model context with settings and tools
        self.model_context = self.llm_model.create_context(
            settings=ModelSettings(
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                parallel_tool_calls=config.parallel_tool_calls
            ),
            tools=config.tools or []
        )

    async def _process_tool_calls(
            self,
            message_parts: List[ModelMessagePart]
    ) -> List[ModelMessagePart]:
        """Process any tool calls in the message parts and return updated parts."""
        processed_parts = []

        for part in message_parts:
            if isinstance(part, ToolCallPart):
                try:
                    # Find the corresponding tool
                    tool = next(
                        (t for t in self.config.tools or []
                         if t.name == part.tool_name),
                        None
                    )

                    if tool:
                        # Execute the tool
                        result = await tool.function(**part.args)

                        # Add the tool return
                        processed_parts.append(
                            ToolReturnPart(
                                tool_name=part.tool_name,
                                content=result
                            )
                        )
                    else:
                        # Tool not found - add error message
                        processed_parts.append(
                            TextPart(
                                text=f"Error: Tool '{part.tool_name}' not found"
                            )
                        )
                except Exception as e:
                    # Handle tool execution error
                    processed_parts.append(
                        TextPart(
                            text=f"Error executing tool '{part.tool_name}': {str(e)}"
                        )
                    )
            else:
                processed_parts.append(part)

        return processed_parts

    async def _process_conversation(
            self,
            messages: List[ModelMessage]
    ) -> List[ModelMessage]:
        """Process a conversation, handling tool calls as needed."""
        processed_messages = []

        for message in messages:
            if message.role == MessageRole.ASSISTANT:
                # Process any tool calls in assistant messages
                processed_parts = await self._process_tool_calls(message.parts)
                processed_messages.append(
                    ModelMessage(
                        role=message.role,
                        parts=processed_parts
                    )
                )
            else:
                processed_messages.append(message)

        return processed_messages

    def _parse_request_data(self, data: Any) -> str:
        """Parse the request data into a string format."""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            return data.get("request", str(data))
        else:
            return str(data)

    async def _processor(self, request: ProcessRequest, time: int) -> tuple[str, Dict[str, Any]]:
        """Process a request using the LLM model."""
        # Initialize conversation with system prompt
        message_list = [
            ModelMessage(
                role=MessageRole.SYSTEM,
                parts=[TextPart(text=self.config.system_prompt)]
            )
        ]

        # Add user message
        user_text = self._parse_request_data(request.data)
        message_list.append(
            ModelMessage(
                role=MessageRole.USER,
                parts=[TextPart(text=user_text)]
            )
        )

        # Track the complete conversation
        complete_conversation = message_list.copy()
        final_response = None
        metadata = {}

        for attempt in range(self.config.retry_attempts):
            try:
                # Get model response
                response, usage = await self.llm_model.request(
                    message_list,
                    self.model_context
                )

                # Add model response to conversation
                assistant_message = ModelMessage(
                    role=MessageRole.ASSISTANT,
                    parts=response.parts
                )
                complete_conversation.append(assistant_message)

                # Process any tool calls
                complete_conversation = await self._process_conversation(
                    complete_conversation
                )

                # Extract final text response
                final_text_parts = [
                    part.text for part in response.parts
                    if isinstance(part, TextPart)
                ]
                final_response = " ".join(final_text_parts)

                # Update metadata
                metadata.update({
                    "usage": {
                        "requests": usage.requests,
                        "request_tokens": usage.request_tokens,
                        "response_tokens": usage.response_tokens,
                        "total_tokens": usage.total_tokens
                    },
                    "attempt": attempt + 1,
                    "tools_used": [
                        part.tool_name for part in response.parts
                        if isinstance(part, ToolCallPart)
                    ]
                })

                # If we got a response, break the retry loop
                if final_response:
                    break

            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    raise
                await asyncio.sleep(self.config.retry_delay)

        if not final_response:
            raise ValueError("No valid response generated")

        return final_response, metadata

    async def stop(self) -> None:
        if self.llm_model:
            await self.llm_model.close()
        await super().stop()