# llm_agent.py
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Set
from enum import Enum
import asyncio
from datetime import datetime
from loguru import logger

from ceylon import Worker, on
from ceylon.task import TaskExecutionAgent
from ceylon.task.data import TaskMessage, TaskStatus


class LLMTaskType(Enum):
    COMPLETION = "completion"
    CHAT = "chat"


@dataclass
class LLMTask(TaskMessage):
    """LLM-specific task with prompt and response handling"""
    # TaskMessage required fields
    task_id: str
    name: str
    description: str
    duration: float
    required_role: str = 'llm_agent'
    status: TaskStatus = TaskStatus.PENDING

    # LLM-specific fields
    task_type: LLMTaskType = LLMTaskType.COMPLETION
    system_prompt: str = ""
    input_data: Optional[str] = None
    output: Optional[str] = None
    temperature: float = 0.7


class LLMAgent(TaskExecutionAgent):
    def __init__(self,
                 name: str,
                 role: str,
                 agent_instructions: str):
        super().__init__(
            name=name,
            worker_role=role,
        )
        self.agent_instructions = agent_instructions
        self.active_tasks: Dict[str, LLMTask] = {}

    @on(LLMTask)
    async def handle_task(self, task: LLMTask, time: int):
        print( f"{self.name}: Received task {task.task_id} from {task.assigned_to}")
        if task.assigned_to != self.name:
            return

        try:
            logger.info(f"{self.name}: Starting task {task.task_id}")
            task.start_time = datetime.now().timestamp()

            # Build prompt
            prompt = self._create_prompt(task)

            # Simulate LLM processing
            await asyncio.sleep(task.duration)
            response = f"Processed task type {task.task_type.value}: {task.input_data}"

            # Update task
            task.output = response
            task.completed = True
            task.end_time = datetime.now().timestamp()
            task.status = TaskStatus.COMPLETED

            await self.broadcast_message(task)
            logger.info(f"{self.name}: Completed task {task.task_id}")

        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED

    def _create_prompt(self, task: LLMTask) -> str:
        return "\n".join([
            self.agent_instructions,
            task.system_prompt,
            f"Task: {task.description}",
            f"Input: {task.input_data}" if task.input_data else ""
        ])
