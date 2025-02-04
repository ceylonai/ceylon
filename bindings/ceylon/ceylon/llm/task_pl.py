from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import asyncio
import uuid

from loguru import logger
from ceylon import on, on_connect, Worker, AgentDetail

from .base_playground import BasePlayGround
from .manager import TaskManager, TaskMessage, TaskGroup, TaskStatus


@dataclass
class TaskRequest:
    task_id: str
    task_type: str
    instructions: str
    required_role: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResponse:
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None
    runtime_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgressUpdate:
    task_id: str
    progress: float  # 0.0 to 1.0
    status: TaskStatus
    message: Optional[str] = None


class TaskWorker(Worker):
    def __init__(self, name: str, role: str):
        super().__init__(name=name, role=role)
        self.active_task: Optional[TaskMessage] = None

    @on(TaskRequest)
    async def handle_task_request(self, request: TaskRequest, time: int):
        try:
            if self.active_task:
                # Already processing a task
                return

            logger.info(f"Worker {self.name} received task: {request.task_id}")

            # Process task (simulated work)
            self.active_task = TaskMessage(
                task_id=request.task_id,
                name=f"Task-{request.task_id[:8]}",
                instructions=request.instructions,
                required_role=request.required_role
            )

            # Send progress updates
            await self.broadcast_message(TaskProgressUpdate(
                task_id=request.task_id,
                progress=0.0,
                status=TaskStatus.IN_PROGRESS,
                message="Starting task"
            ))

            # Simulate work
            await asyncio.sleep(2)

            # Send completion
            response = TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                result={"processed": True},
                runtime_stats={
                    "duration": 2.0,
                    "memory_used": "100MB"
                }
            )
            await self.broadcast_message(response)
            self.active_task = None

        except Exception as e:
            logger.error(f"Error processing task {request.task_id}: {e}")
            await self.broadcast_message(TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            ))
            self.active_task = None


class TaskPlayGround(BasePlayGround):
    def __init__(self, name="task_playground", port=8888):
        super().__init__(name=name, port=port)
        self.task_manager = TaskManager()
        self.task_responses: Dict[str, TaskResponse] = {}
        self.task_events: Dict[str, asyncio.Event] = {}
        self.task_progress: Dict[str, float] = {}

    @on(TaskResponse)
    async def handle_task_response(self, response: TaskResponse, time: int):
        """Handle task completion responses from workers"""
        logger.info(f"Received task response for {response.task_id}: {response.status}")

        self.task_responses[response.task_id] = response
        if response.task_id in self.task_events:
            self.task_events[response.task_id].set()

        if response.status == TaskStatus.COMPLETED:
            task = self.task_manager.tasks.get(response.task_id)
            if task:
                task.completed = True
                all_completed = await self.task_manager.handle_task_completion(task)
                if all_completed:
                    logger.info("All tasks completed")
                    await self.finish()

    @on(TaskProgressUpdate)
    async def handle_progress_update(self, update: TaskProgressUpdate, time: int):
        """Handle task progress updates"""
        self.task_progress[update.task_id] = update.progress
        logger.debug(f"Task {update.task_id} progress: {update.progress:.1%}")

    @on_connect("*")
    async def handle_worker_connection(self, topic: str, agent: AgentDetail):
        """Register new workers with the task manager"""
        self.task_manager.register_worker(agent.name, agent.role)
        await super().on_llm_agent_connected(topic, agent)

    async def submit_task(self, task_type: str, instructions: str, role: str,
                          metadata: Optional[Dict[str, Any]] = None) -> TaskResponse:
        """Submit a task and wait for its completion"""
        task_id = str(uuid.uuid4())
        request = TaskRequest(
            task_id=task_id,
            task_type=task_type,
            instructions=instructions,
            required_role=role,
            metadata=metadata or {}
        )

        # Setup completion event
        self.task_events[task_id] = asyncio.Event()

        # Send request
        await self.broadcast_message(request)

        try:
            # Wait for completion
            await asyncio.wait_for(self.task_events[task_id].wait(), timeout=30.0)
            return self.task_responses[task_id]
        except asyncio.TimeoutError:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error_message="Task timed out"
            )
        finally:
            # Cleanup
            self.task_events.pop(task_id, None)

    def get_task_progress(self, task_id: str) -> float:
        """Get current progress for a task"""
        return self.task_progress.get(task_id, 0.0)

    async def close(self):
        """Clean shutdown of playground"""
        # Cancel any pending tasks
        for task_id, event in self.task_events.items():
            event.set()

        # Clear state
        self.task_responses.clear()
        self.task_events.clear()
        self.task_progress.clear()

        await self.force_close()
