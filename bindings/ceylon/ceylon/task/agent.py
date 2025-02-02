#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TypeVar, Sequence, Dict

from loguru import logger
from pydantic import BaseModel

from ceylon import Worker, on
from ceylon.task.data import TaskMessage, TaskRequest, TaskStatusUpdate, TaskStatus

ResponseType = TypeVar("ResponseType")


class AgentRequest(BaseModel):
    input_data: str
    dependencies: Sequence[str]


# class LLMAgentConfig(BaseModel):
#     system_prompt: str | Sequence[str]
#     response_type: type[ResponseType] | None
#
#
# class LLMAgentBase(Worker):
#     def __init__(
#             self,
#             name: str,
#             role: str,
#             system_prompt: str | Sequence[str] = (),
#             response_type: type[ResponseType] = None
#     ):
#         super().__init__(name, role)
#         self.config = LLMAgentConfig(
#             system_prompt=system_prompt,
#             response_type=response_type
#         )


class TaskExecutionAgent(Worker):
    def __init__(self, name: str, worker_role: str, max_concurrent_tasks: int = 3):
        super().__init__(
            name=name,
            role=worker_role,
        )
        self.worker_role = worker_role
        self.active_tasks: Dict[str, TaskMessage] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.processing = False

    async def request_task(self, task_type: str, priority: int = 1):
        request = TaskRequest(
            requester=self.name,
            role=self.worker_role,
            task_type=task_type,
            priority=priority
        )
        await self.broadcast_message(request)
        logger.debug(f"{self.name}: Requested new {task_type} task")

    @on(TaskStatusUpdate)
    async def handle_status_update(self, update: TaskStatusUpdate, time: int):
        if update.task_id in self.active_tasks:
            logger.debug(f"{self.name}: Received status update for task {update.task_id}: {update.status}")
            if update.status == 'completed':
                self.active_tasks.pop(update.task_id, None)

    @on(TaskMessage)
    async def handle_task(self, task: TaskMessage, time: int):
        logger.debug(f"{self.name}: Received task {task.task_id} from {task.assigned_to}")
        if task.assigned_to != self.name or task.required_role != self.worker_role:
            return

        await self.task_queue.put(task)
        if not self.processing:
            self.processing = True
            asyncio.create_task(self.process_task_queue())

    async def process_task_queue(self):
        while True:
            if len(self.active_tasks) >= self.max_concurrent_tasks:
                await asyncio.sleep(0.1)
                continue

            try:
                try:
                    task = self.task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    if not self.active_tasks:
                        self.processing = False
                        await self.request_task("standard")
                        break
                    await asyncio.sleep(0.1)
                    continue

                logger.debug(f"{self.name} ({self.worker_role}): Starting task {task.task_id} - {task.name}")
                task.start_time = datetime.now().timestamp()
                self.active_tasks[task.task_id] = task
                asyncio.create_task(self.execute_task(task))

            except Exception as e:
                logger.debug(f"Error processing task queue for {self.name}: {e}")
                await asyncio.sleep(1)

    async def execute_task(self, task: TaskMessage):
        try:
            await asyncio.sleep(task.duration)
            task.completed = True
            task.end_time = datetime.now().timestamp()
            del self.active_tasks[task.task_id]
            await self.broadcast_message(task)
            logger.debug(f"{self.name} ({self.worker_role}): Completed task {task.task_id} - {task.name}")
            await self.request_task("standard")

        except Exception as e:
            logger.debug(f"Error executing task {task.task_id}: {e}")
            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                message=str(e)
            ))
