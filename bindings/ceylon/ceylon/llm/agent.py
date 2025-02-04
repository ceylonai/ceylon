#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

from pydantic import BaseModel

from ceylon.llm.models import Model, ModelSettings, ModelMessage
from ceylon.llm.models.support.messages import MessageRole, TextPart
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

        # Initialize model context with settings
        self.model_context = self.llm_model.create_context(
            settings=ModelSettings(
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        )

    async def _processor(self, request: ProcessRequest, time: int):
        message_list = [
            ModelMessage(
                role=MessageRole.SYSTEM,
                parts=[
                    TextPart(text=self.config.system_prompt)
                ]
            ),
            ModelMessage(
                role=MessageRole.USER,
                parts=[
                    TextPart(text=request.data)
                ]
            )
        ]

        return await self.llm_model.request(message_list, self.model_context)

    async def stop(self) -> None:
        if self.llm_model:
            await self.llm_model.close()
        await super().stop()
