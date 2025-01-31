#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

from ceylon import on, on_connect
from ceylon.llm.agent import LLMAgent
from ceylon.llm.playground import PlayGround


@dataclass
class TaskMessage:
    task_id: str
    name: str
    description: str
    duration: float
    required_role: str
    assigned_to: Optional[str] = None
    completed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    max_concurrent: int = 3


@dataclass
class TaskRequest:
    requester: str
    role: str
    task_type: str
    priority: int = 1


@dataclass
class TaskStatusUpdate:
    task_id: str
    status: str  # 'requested', 'assigned', 'completed', 'failed'
    message: Optional[str] = None


class TaskWorkerAgent(LLMAgent):
    def __init__(self, name: str, worker_role: str, max_concurrent_tasks: int = 3):
        super().__init__(
            name=name,
            role=worker_role,
            system_prompt=f"You are a task execution agent specialized in {worker_role} tasks."
        )
        self.worker_role = worker_role
        self.active_tasks: Dict[str, TaskMessage] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.processing = False

    async def request_task(self, task_type: str, priority: int = 1):
        """Request a new task from the task manager"""
        request = TaskRequest(
            requester=self.name,
            role=self.worker_role,
            task_type=task_type,
            priority=priority
        )
        await self.broadcast_message(request)
        print(f"{self.name}: Requested new {task_type} task")

    @on(TaskStatusUpdate)
    async def handle_status_update(self, update: TaskStatusUpdate, time: int):
        """Handle task status updates"""
        if update.task_id in self.active_tasks:
            print(f"{self.name}: Received status update for task {update.task_id}: {update.status}")
            if update.status == 'completed':
                self.active_tasks.pop(update.task_id, None)

    @on(TaskMessage)
    async def handle_task(self, task: TaskMessage, time: int):
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
                        # Request new task when queue is empty
                        await self.request_task("standard")
                        break
                    await asyncio.sleep(0.1)
                    continue

                print(f"{self.name} ({self.worker_role}): Starting task {task.task_id} - {task.name}")
                task.start_time = datetime.now().timestamp()
                self.active_tasks[task.task_id] = task
                asyncio.create_task(self.execute_task(task))

            except Exception as e:
                print(f"Error processing task queue for {self.name}: {e}")
                await asyncio.sleep(1)

    async def execute_task(self, task: TaskMessage):
        try:
            await asyncio.sleep(task.duration)
            task.completed = True
            task.end_time = datetime.now().timestamp()
            del self.active_tasks[task.task_id]
            await self.broadcast_message(task)
            print(f"{self.name} ({self.worker_role}): Completed task {task.task_id} - {task.name}")

            # Request new task after completion
            await self.request_task("standard")

        except Exception as e:
            print(f"Error executing task {task.task_id}: {e}")
            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status="failed",
                message=str(e)
            ))


class TaskManagerPlayground(PlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.tasks: Dict[str, TaskMessage] = {}
        self.completed_tasks: Dict[str, TaskMessage] = {}
        self.workers_by_role: Dict[str, List[str]] = defaultdict(list)
        self.worker_task_counts: Dict[str, int] = defaultdict(int)
        self.task_templates: Dict[str, Dict] = {
            "data_processor": {
                "standard": lambda: TaskMessage(
                    task_id=str(uuid.uuid4()),
                    name="Process Data Batch",
                    description="Process incoming data batch",
                    duration=2,
                    required_role="data_processor"
                ),
            },
            "reporter": {
                "standard": lambda: TaskMessage(
                    task_id=str(uuid.uuid4()),
                    name="Generate Report",
                    description="Generate periodic report",
                    duration=3,
                    required_role="reporter"
                ),
            },
            "system_admin": {
                "standard": lambda: TaskMessage(
                    task_id=str(uuid.uuid4()),
                    name="System Maintenance",
                    description="Perform system maintenance",
                    duration=2,
                    required_role="system_admin"
                ),
            }
        }

    @on(TaskRequest)
    async def handle_task_request(self, request: TaskRequest, time: int):
        """Handle dynamic task requests from workers"""
        if request.role not in self.task_templates:
            print(f"Warning: No task templates for role {request.role}")
            return

        template = self.task_templates[request.role].get(request.task_type)
        if not template:
            print(f"Warning: No template for task type {request.task_type}")
            return

        new_task = template()
        new_task.assigned_to = request.requester
        self.tasks[new_task.task_id] = new_task
        self.worker_task_counts[request.requester] += 1

        await self.broadcast_message(new_task)
        print(f"Task Manager: Created and assigned new task {new_task.task_id} to {request.requester}")

    @on_connect("*")
    async def handle_worker_connection(self, topic: str, agent: "AgentDetail"):
        self.workers_by_role[agent.role].append(agent.name)
        print(f"Task Manager: Worker {agent.name} connected with role {agent.role}")

    @on(TaskMessage)
    async def handle_task_completion(self, task: TaskMessage, time: int):
        if task.completed and task.task_id in self.tasks:
            self.completed_tasks[task.task_id] = task
            self.worker_task_counts[task.assigned_to] -= 1
            print(f"Task Manager: Received completion for task {task.task_id}")

            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status="completed"
            ))

            await self.print_statistics()

    async def print_statistics(self):
        print("\nCurrent Statistics:")
        role_stats: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "total_duration": 0})

        for task in self.completed_tasks.values():
            duration = task.end_time - task.start_time
            role_stats[task.required_role]["count"] += 1
            role_stats[task.required_role]["total_duration"] += duration

        for role, stats in role_stats.items():
            avg_duration = stats["total_duration"] / stats["count"]
            print(f"Role: {role}")
            print(f"  Tasks Completed: {stats['count']}")
            print(f"  Average Duration: {avg_duration:.2f} seconds")

    async def assign_tasks(self, initial_tasks: List[TaskMessage]):
        """Assign initial batch of tasks"""
        for task in initial_tasks:
            self.tasks[task.task_id] = task

        tasks_by_role = defaultdict(list)
        for task in initial_tasks:
            tasks_by_role[task.required_role].append(task)

        for role, role_tasks in tasks_by_role.items():
            available_workers = self.workers_by_role.get(role, [])
            if not available_workers:
                print(f"Warning: No workers available for role {role}")
                continue

            for task in role_tasks:
                worker_name = min(
                    available_workers,
                    key=lambda w: self.worker_task_counts[w]
                )
                task.assigned_to = worker_name
                self.worker_task_counts[worker_name] += 1
                await self.broadcast_message(task)


async def main():
    # Create playground and worker agents
    playground = TaskManagerPlayground()
    workers = [
        TaskWorkerAgent("worker1", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker2", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker3", "reporter", max_concurrent_tasks=3),
        TaskWorkerAgent("worker4", "system_admin", max_concurrent_tasks=2)
    ]

    # Initial tasks
    initial_tasks = [
        TaskMessage(task_id="1", name="Initial Data Processing",
                    description="Process initial data batch",
                    duration=2, required_role="data_processor"),
        TaskMessage(task_id="2", name="Initial Report",
                    description="Generate initial report",
                    duration=3, required_role="reporter"),
    ]

    # Start the playground with initial tasks
    async with playground.play(workers=workers) as active_playground:
        await active_playground.assign_tasks(initial_tasks)

        # Let the system run for a while to demonstrate dynamic task creation
        await asyncio.sleep(20)
        await active_playground.finish()


if __name__ == "__main__":
    asyncio.run(main())