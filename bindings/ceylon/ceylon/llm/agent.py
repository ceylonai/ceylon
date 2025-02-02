import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel

from loguru import logger
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
    stop_sequences: List[str] = []
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0

    class Config:
        arbitrary_types_allowed = True

class LLMAgent(TaskExecutionAgent):
    """
    An agent that processes tasks using LLM capabilities.
    Extends TaskExecutionAgent with LLM-specific processing.
    """
    def __init__(
            self,
            name: str,
            config: LLMConfig,
            worker_role: str = "llm_processor",
            max_concurrent_tasks: int = 3
    ):
        super().__init__(
            name=name,
            worker_role=worker_role,
            max_concurrent_tasks=max_concurrent_tasks
        )
        self.config = config
        self.response_cache: Dict[str, LLMResponse] = {}
        self.processing_lock = asyncio.Lock()

    async def execute_task(self, task: TaskMessage) -> None:
        """
        Execute an LLM task with retry logic and error handling
        """
        try:
            logger.info(f"{self.name}: Starting LLM task {task.task_id}")

            # Prepare context and execute with retries
            async with self.processing_lock:
                response = await self._execute_with_retry(task)

            if response:
                # Cache successful response
                self.response_cache[task.task_id] = response

                # Update task with completion info
                task.completed = True
                task.end_time = datetime.now().timestamp()

                # Include response in task metadata
                if not hasattr(task, 'metadata'):
                    task.metadata = {}
                task.metadata['llm_response'] = response.content
                task.metadata['response_timestamp'] = response.timestamp

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
                # Simulate LLM call - replace with actual LLM integration
                await asyncio.sleep(task.duration)
                response = await self._call_llm(task)

                if response and response.content:
                    return response

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
        Make the actual LLM API call
        Replace this with your LLM integration (e.g. OpenAI, Anthropic, etc.)
        """
        try:
            async with asyncio.timeout(self.config.timeout):
                # Construct prompt with system prompt and task details
                prompt = f"{self.config.system_prompt}\n\nTask: {task.description}"

                # Simulate LLM response - replace with actual API call
                response_text = f"Simulated LLM response for task {task.task_id}"

                return LLMResponse(
                    content=response_text,
                    metadata={
                        'task_id': task.task_id,
                        'prompt_tokens': len(prompt),
                        'completion_tokens': len(response_text)
                    }
                )

        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM call timed out after {self.config.timeout}s")
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")

    async def validate_response(self, response: LLMResponse) -> bool:
        """
        Validate LLM response format and content
        Override this method to implement custom validation logic
        """
        if not response or not response.content:
            return False

        # Add custom validation logic here
        return True