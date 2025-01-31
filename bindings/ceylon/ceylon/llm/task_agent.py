#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

from ceylon.llm.playground import PlayGround
from ceylon.llm.agent import LLMAgent
from ceylon import on, on_connect


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


class TaskWorkerAgent(LLMAgent):
    def __init__(self, name: str, worker_role: str):
        super().__init__(
            name=name,
            role=worker_role,  # Use the specific worker role
            system_prompt=f"You are a task execution agent specialized in {worker_role} tasks."
        )
        self.worker_role = worker_role
        self.current_task: Optional[TaskMessage] = None

    @on(TaskMessage)
    async def handle_task(self, task: TaskMessage, time: int):
        # Check both role and assignment
        if task.assigned_to != self.name or task.required_role != self.worker_role:
            return

        print(f"{self.name} ({self.worker_role}): Starting task {task.task_id} - {task.name}")
        self.current_task = task
        self.current_task.start_time = datetime.now().timestamp()

        # Simulate task execution
        await asyncio.sleep(task.duration)

        self.current_task.completed = True
        self.current_task.end_time = datetime.now().timestamp()

        # Report completion
        await self.broadcast_message(self.current_task)
        print(f"{self.name} ({self.worker_role}): Completed task {task.task_id} - {task.name}")


class TaskManagerPlayground(PlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.tasks: List[TaskMessage] = []
        self.completed_tasks: List[TaskMessage] = []
        self.workers_by_role: Dict[str, List[str]] = {}  # Role -> List of worker names

    @on_connect("*")
    async def handle_worker_connection(self, topic: str, agent: "AgentDetail"):
        # Track workers by their roles
        if agent.role not in self.workers_by_role:
            self.workers_by_role[agent.role] = []
        self.workers_by_role[agent.role].append(agent.name)
        print(f"Task Manager: Worker {agent.name} connected with role {agent.role}")

    @on(TaskMessage)
    async def handle_task_completion(self, task: TaskMessage, time: int):
        if task.completed:
            self.completed_tasks.append(task)
            print(f"Task Manager: Received completion for task {task.task_id}")

            # Check if all tasks are completed
            if len(self.completed_tasks) == len(self.tasks):
                print("\nAll tasks completed! Summary:")
                for completed_task in self.completed_tasks:
                    duration = completed_task.end_time - completed_task.start_time
                    print(f"Task {completed_task.task_id}: {completed_task.name}")
                    print(f"  Required Role: {completed_task.required_role}")
                    print(f"  Executed by: {completed_task.assigned_to}")
                    print(f"  Duration: {duration:.2f} seconds")
                await self.finish()

    async def assign_tasks(self, tasks: List[TaskMessage]):
        self.tasks = tasks

        # Assign tasks based on required roles
        for task in tasks:
            available_workers = self.workers_by_role.get(task.required_role, [])
            if not available_workers:
                print(f"Warning: No workers available for role {task.required_role} (Task {task.task_id})")
                continue

            # Round-robin within the role group
            worker_index = len([t for t in self.tasks if t.required_role == task.required_role]) % len(available_workers)
            worker_name = available_workers[worker_index]
            task.assigned_to = worker_name

            await self.broadcast_message(task)
            print(f"Task Manager: Assigned task {task.task_id} to {worker_name} (role: {task.required_role})")


async def main():
    # Create playground and worker agents with specific roles
    playground = TaskManagerPlayground()
    workers = [
        TaskWorkerAgent("worker1", "data_processor"),
        TaskWorkerAgent("worker2", "data_processor"),
        TaskWorkerAgent("worker3", "reporter"),
        TaskWorkerAgent("worker4", "system_admin")
    ]

    # Define tasks with required roles
    tasks = [
        TaskMessage(task_id="1", name="Process Raw Data", description="Process incoming data files",
                    duration=2, required_role="data_processor"),
        TaskMessage(task_id="2", name="Process Analytics", description="Process analytics data",
                    duration=3, required_role="data_processor"),
        TaskMessage(task_id="3", name="Generate Report", description="Create summary report",
                    duration=2, required_role="reporter"),
        TaskMessage(task_id="4", name="Backup Data", description="Backup processed data",
                    duration=2, required_role="system_admin"),
    ]

    # Start the playground and execute tasks
    async with playground.play(workers=workers) as active_playground:
        await active_playground.assign_tasks(tasks=tasks)


if __name__ == "__main__":
    asyncio.run(main())