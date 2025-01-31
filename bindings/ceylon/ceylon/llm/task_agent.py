#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
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
    duration: float  # in seconds
    required_role: str  # Role required to execute this task
    assigned_to: Optional[str] = None
    completed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    max_concurrent: int = 3  # Maximum number of concurrent tasks per worker


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

    @on(TaskMessage)
    async def handle_task(self, task: TaskMessage, time: int):
        # Check both role and assignment
        if task.assigned_to != self.name or task.required_role != self.worker_role:
            return

        # Add task to queue
        await self.task_queue.put(task)

        # Start processing if not already running
        if not self.processing:
            self.processing = True
            asyncio.create_task(self.process_task_queue())

    async def process_task_queue(self):
        while True:
            # Check if we can take on more tasks
            if len(self.active_tasks) >= self.max_concurrent_tasks:
                await asyncio.sleep(0.1)
                continue

            try:
                # Get next task from queue (non-blocking)
                try:
                    task = self.task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    if not self.active_tasks:  # If no active tasks and queue empty, stop processing
                        self.processing = False
                        break
                    await asyncio.sleep(0.1)
                    continue

                # Start task execution
                print(f"{self.name} ({self.worker_role}): Starting task {task.task_id} - {task.name}")
                task.start_time = datetime.now().timestamp()
                self.active_tasks[task.task_id] = task

                # Create task execution coroutine
                asyncio.create_task(self.execute_task(task))

            except Exception as e:
                print(f"Error processing task queue for {self.name}: {e}")
                await asyncio.sleep(1)

    async def execute_task(self, task: TaskMessage):
        try:
            # Simulate task execution
            await asyncio.sleep(task.duration)

            # Update task status
            task.completed = True
            task.end_time = datetime.now().timestamp()

            # Remove from active tasks
            del self.active_tasks[task.task_id]

            # Report completion
            await self.broadcast_message(task)
            print(f"{self.name} ({self.worker_role}): Completed task {task.task_id} - {task.name}")

        except Exception as e:
            print(f"Error executing task {task.task_id}: {e}")
            # Could implement retry logic here if needed


class TaskManagerPlayground(PlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.tasks: Dict[str, TaskMessage] = {}
        self.completed_tasks: Dict[str, TaskMessage] = {}
        self.workers_by_role: Dict[str, List[str]] = defaultdict(list)
        self.worker_task_counts: Dict[str, int] = defaultdict(int)

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

            # Check if all tasks are completed
            if len(self.completed_tasks) == len(self.tasks):
                print("\nAll tasks completed! Summary:")
                role_stats: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "total_duration": 0})

                for completed_task in self.completed_tasks.values():
                    duration = completed_task.end_time - completed_task.start_time
                    print(f"Task {completed_task.task_id}: {completed_task.name}")
                    print(f"  Required Role: {completed_task.required_role}")
                    print(f"  Executed by: {completed_task.assigned_to}")
                    print(f"  Duration: {duration:.2f} seconds")

                    # Collect stats by role
                    role_stats[completed_task.required_role]["count"] += 1
                    role_stats[completed_task.required_role]["total_duration"] += duration

                print("\nRole-based Statistics:")
                for role, stats in role_stats.items():
                    avg_duration = stats["total_duration"] / stats["count"]
                    print(f"Role: {role}")
                    print(f"  Tasks Completed: {stats['count']}")
                    print(f"  Average Duration: {avg_duration:.2f} seconds")

                await self.finish()

    async def assign_tasks(self, tasks: List[TaskMessage]):
        # Store tasks in dictionary for easier tracking
        for task in tasks:
            self.tasks[task.task_id] = task

        # Group tasks by role
        tasks_by_role: Dict[str, List[TaskMessage]] = defaultdict(list)
        for task in tasks:
            tasks_by_role[task.required_role].append(task)

        # Assign tasks based on required roles
        for role, role_tasks in tasks_by_role.items():
            available_workers = self.workers_by_role.get(role, [])
            if not available_workers:
                print(f"Warning: No workers available for role {role}")
                continue

            # Assign tasks to workers in the role group
            for task in role_tasks:
                # Find worker with least assigned tasks
                worker_name = min(
                    available_workers,
                    key=lambda w: self.worker_task_counts[w]
                )

                task.assigned_to = worker_name
                self.worker_task_counts[worker_name] += 1
                await self.broadcast_message(task)
                print(f"Task Manager: Assigned task {task.task_id} to {worker_name} (role: {role})")


async def main():
    # Create playground and worker agents with specific roles
    playground = TaskManagerPlayground()
    workers = [
        TaskWorkerAgent("worker1", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker2", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker3", "reporter", max_concurrent_tasks=3),
        TaskWorkerAgent("worker4", "system_admin", max_concurrent_tasks=2)
    ]

    # Define tasks with required roles
    tasks = [
        TaskMessage(task_id="1", name="Process Raw Data 1", description="Process incoming data files",
                    duration=2, required_role="data_processor"),
        TaskMessage(task_id="2", name="Process Raw Data 2", description="Process incoming data files",
                    duration=3, required_role="data_processor"),
        TaskMessage(task_id="3", name="Process Analytics 1", description="Process analytics data",
                    duration=2, required_role="data_processor"),
        TaskMessage(task_id="4", name="Process Analytics 2", description="Process analytics data",
                    duration=3, required_role="data_processor"),
        TaskMessage(task_id="5", name="Generate Report 1", description="Create summary report",
                    duration=2, required_role="reporter"),
        TaskMessage(task_id="6", name="Generate Report 2", description="Create summary report",
                    duration=3, required_role="reporter"),
        TaskMessage(task_id="7", name="Backup Data 1", description="Backup processed data",
                    duration=2, required_role="system_admin"),
        TaskMessage(task_id="8", name="Backup Data 2", description="Backup processed data",
                    duration=2, required_role="system_admin"),
    ]

    # Start the playground and execute tasks
    async with playground.play(workers=workers) as active_playground:
        await active_playground.assign_tasks(tasks=tasks)


if __name__ == "__main__":
    asyncio.run(main())