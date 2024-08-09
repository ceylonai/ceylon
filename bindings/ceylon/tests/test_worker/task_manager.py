# Distributed Task Management System

import asyncio
from typing import List
from pydantic.dataclasses import dataclass
from ceylon import Agent, CoreAdmin, on_message
from loguru import logger

from ceylon.ceylon import AgentDetail


# Data structures
@dataclass
class Task:
    id: int
    description: str
    difficulty: int  # 1-10 scale


@dataclass
class TaskAssignment:
    task: Task


@dataclass
class TaskResult:
    task_id: int
    worker: str
    success: bool


# Worker Agent
class WorkerAgent(Agent):
    def __init__(self, name: str, skill_level: int):
        self.name = name
        self.skill_level = skill_level
        super().__init__(name=name, workspace_id="task_management", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        logger.info(f"{self.name} received task: {data.task.description}")
        # Simulate task execution
        await asyncio.sleep(data.task.difficulty)
        success = self.skill_level >= data.task.difficulty
        await self.broadcast_data(TaskResult(task_id=data.task.id, worker=self.name, success=success))


# Task Manager
class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    workers: List[WorkerAgent] = []
    task_results: List[TaskResult] = []

    def __init__(self, tasks: List[Task], workers: List[WorkerAgent]):
        self.workers = workers
        self.tasks = tasks
        super().__init__(name="task_management", port=8000)

    async def on_agent_connected(self, topic: str, agent_id: AgentDetail):
        logger.info(f"Worker {agent_id} connected")
        if len(self.workers) == len(self.tasks):
            await self.assign_tasks()

    async def assign_tasks(self):
        for task, worker in zip(self.tasks, self.workers):
            await self.broadcast_data(TaskAssignment(task=task))

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        self.task_results.append(result)
        logger.info(
            f"Received result for task {result.task_id} from {result.worker}: {'Success' if result.success else 'Failure'}")
        if len(self.task_results) == len(self.tasks):
            await self.end_task_management()

    async def end_task_management(self):
        success_rate = sum(1 for result in self.task_results if result.success) / len(self.task_results)
        logger.info(f"All tasks completed. Success rate: {success_rate:.2%}")
        await self.stop()


# Main execution
if __name__ == '__main__':
    # Create tasks
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="Machine learning model training", difficulty=8),
    ]

    # Create workers
    workers = [
        WorkerAgent("Junior", skill_level=3),
        WorkerAgent("Intermediate", skill_level=6),
        WorkerAgent("Senior", skill_level=9),
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, workers)
    task_manager.run_admin(inputs=b"", workers=workers)
