import asyncio
from typing import List, Dict, Any

from pydantic.dataclasses import dataclass
from pydantic.v1 import BaseModel

from ceylon import Agent, CoreAdmin, on_message
from loguru import logger


class Task(BaseModel):
    id: int
    description: str
    difficulty: int  # 1-10 scale
    dependencies: List[int]  # List of task IDs this task depends on


class SubTask(BaseModel):
    task: Task
    assigned_worker: str


class TaskAssignment(BaseModel):
    subtask: SubTask


@dataclass
class TaskResult:
    task_id: int
    worker: str
    success: bool


class WorkerAgent(Agent):
    def __init__(self, name: str, skill_level: int):
        self.name = name
        self.skill_level = skill_level
        super().__init__(name=name, workspace_id="advanced_task_management", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        logger.info(f"{self.name} received task: {data.subtask.task.description}")
        # Simulate task execution
        await asyncio.sleep(data.subtask.task.difficulty)
        success = self.skill_level >= data.subtask.task.difficulty
        await self.broadcast_data(TaskResult(task_id=data.subtask.task.id, worker=self.name, success=success))


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    workers: List[WorkerAgent] = []
    task_results: Dict[int, TaskResult] = {}
    pending_tasks: Dict[int, Any] = {}
    completed_tasks: List[int] = []

    def __init__(self, tasks: List[Task], workers: List[WorkerAgent]):
        self.tasks = tasks
        self.workers = workers
        self.pending_tasks = {task.id: SubTask(task=task, assigned_worker="") for task in tasks}
        super().__init__(name="advanced_task_management", port=8000)

    async def on_agent_connected(self, topic: str, agent_id: str):
        logger.info(f"Worker {agent_id} connected")
        # if len(self.workers) == len(self.tasks):
        await self.assign_tasks()

    async def assign_tasks(self):
        for task_id, subtask in self.pending_tasks.items():
            if all(dep in self.completed_tasks for dep in subtask.task.dependencies):
                available_worker = next((w for w in self.workers if w.skill_level >= subtask.task.difficulty), None)
                if available_worker:
                    subtask.assigned_worker = available_worker.name
                    await self.broadcast_data(TaskAssignment(subtask=subtask))
                    logger.info(f"Assigned task {task_id} to {available_worker.name}")

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        self.task_results[result.task_id] = result
        self.completed_tasks.append(result.task_id)
        logger.info(
            f"Received result for task {result.task_id} from {result.worker}: {'Success' if result.success else 'Failure'}")

        # Remove the completed task from pending tasks
        print("self.pending_tasks[result.task_id]", result.task_id, result.task_id in self.pending_tasks)
        if result.task_id in self.pending_tasks:
            print("del self.pending_tasks[result.task_id]", result.task_id)
            del self.pending_tasks[result.task_id]
        # print(self.pending_tasks)
        # for idx, task in self.pending_tasks:
        #     if task.task_id == result.task_id:
        #         del self.pending_tasks[idx]

        # Check if we can assign more tasks
        await self.assign_tasks()

        if not self.pending_tasks:
            await self.end_task_management()

    async def end_task_management(self):
        success_rate = sum(1 for result in self.task_results.values() if result.success) / len(self.task_results)
        logger.info(f"All tasks completed. Success rate: {success_rate:.2%}")
        await self.stop()


if __name__ == '__main__':
    # Create tasks with dependencies
    tasks = [
        Task(id=1, description="Data preparation", difficulty=2, dependencies=[]),
        Task(id=2, description="Feature engineering", difficulty=5, dependencies=[1]),
        Task(id=3, description="Model training", difficulty=8, dependencies=[2]),
        Task(id=4, description="Model evaluation", difficulty=6, dependencies=[3]),
        Task(id=5, description="Report generation", difficulty=4, dependencies=[4]),
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
