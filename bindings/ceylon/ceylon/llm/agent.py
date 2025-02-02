#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

from loguru import logger
from pydantic import BaseModel

from ceylon.llm.models import Model, ModelSettings, ModelMessage
from ceylon.llm.models.support.messages import MessageRole, TextPart
from ceylon.task.agent import TaskExecutionAgent
from ceylon.task.data import TaskMessage, TaskStatus


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

class LLMAgent(TaskExecutionAgent):
    """
    An agent that processes tasks using configurable LLM capabilities.
    Supports multiple LLM backends through the Model interface.
    """
    def __init__(
            self,
            name: str,
            llm_model: Model,
            config: LLMConfig,
            worker_role: str = "llm_processor",
            max_concurrent_tasks: int = 3
    ):
        super().__init__(
            name=name,
            worker_role=worker_role,
            max_concurrent_tasks=max_concurrent_tasks
        )
        self.llm_model = llm_model
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

    async def execute_task(self, task: TaskMessage) -> None:
        """
        Execute an LLM task with retry logic and error handling
        """
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Task: {task.name}")
            logger.info(f"Description: {task.description}")
            logger.info(f"{'='*80}\n")

            async with self.processing_lock:
                response = await self._execute_with_retry(task)

            if response:
                # Cache successful response
                self.response_cache[task.task_id] = response

                # Print the response
                logger.info("\nGenerated Content:")
                logger.info(f"{'-'*80}")
                logger.info(response.content)
                logger.info(f"{'-'*80}\n")

                # Update task with completion info
                task.completed = True
                task.end_time = datetime.now().timestamp()

                # Include response in task metadata
                if not task.metadata:
                    task.metadata = {}
                task.metadata['llm_response'] = response.content
                task.result = response.content
                task.metadata['response_timestamp'] = response.timestamp
                task.metadata.update(response.metadata)

                logger.info(f"{self.name}: Completed task {task.task_id}")

                # Remove from active tasks and broadcast completion
                del self.active_tasks[task.task_id]
                await self.broadcast_message(task)

                # Request new task
                await self.request_task("standard")
            else:
                raise Exception("Failed to get valid LLM response")

        except Exception as e:
            logger.error(f"Error executing LLM task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.metadata = task.metadata or {}
            task.metadata['error'] = str(e)
            await self.broadcast_message(task)

    async def _execute_with_retry(self, task: TaskMessage) -> Optional[LLMResponse]:
        """
        Execute LLM call with configured retry logic
        """
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                response = await self._call_llm(task)

                if response and response.content:
                    if await self.validate_response(response, task):
                        return response
                    else:
                        raise ValueError("Response validation failed")

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        if last_error:
            raise last_error
        return None

    async def _call_llm(self, task: TaskMessage) -> LLMResponse:
        """
        Make the actual LLM API call using the configured model
        """
        try:
            async with asyncio.timeout(self.config.timeout):
                # Construct messages for the model
                messages = [
                    ModelMessage(
                        role=MessageRole.SYSTEM,
                        parts=[TextPart(text=self.config.system_prompt)]
                    ),
                    ModelMessage(
                        role=MessageRole.USER,
                        parts=[TextPart(text=self._format_task_prompt(task))]
                    )
                ]

                # Make the model request
                response, usage = await self.llm_model.request(
                    messages=messages,
                    context=self.model_context
                )

                # Extract text from response parts
                response_text = ""
                for part in response.parts:
                    if hasattr(part, 'text'):
                        response_text += part.text

                return LLMResponse(
                    content=response_text,
                    metadata={
                        'task_id': task.task_id,
                        'usage': usage.__dict__,
                        'model_name': self.llm_model.model_name
                    }
                )

        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM call timed out after {self.config.timeout}s")
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")

    def _format_task_prompt(self, task: TaskMessage) -> str:
        """
        Format the task into a prompt for the LLM
        """
        prompt_parts = [
            f"Task: {task.name}",
            f"Description: {task.description}"
        ]

        # Add any task-specific metadata to prompt
        if task.metadata:
            for key, value in task.metadata.items():
                if key in ['type', 'topic', 'style', 'target_length']:
                    prompt_parts.append(f"{key.title()}: {value}")

        return "\n".join(prompt_parts)

    async def validate_response(self, response: LLMResponse, task: TaskMessage) -> bool:
        """
        Validate LLM response format and content
        Override this method to implement custom validation logic
        """
        if not response or not response.content:
            return False

        # Basic length validation
        if task.metadata and 'target_length' in task.metadata:
            target_length = task.metadata['target_length']
            actual_length = len(response.content.split())
            if actual_length < target_length * 0.5 or actual_length > target_length * 1.5:
                logger.warning(f"Response length {actual_length} words outside target range of {target_length}")
                return False

        # Add custom validation logic here
        return True

    async def close(self) -> None:
        """
        Clean up resources when agent is stopped
        """
        if self.llm_model:
            await self.llm_model.close()
        await super().close()