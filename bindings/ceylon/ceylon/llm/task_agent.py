#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from dataclasses import dataclass
from typing import List, Optional
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
    assigned_to: Optional[str] = None
    completed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class TaskWorkerAgent(LLMAgent):
    def __init__(self, name: str):
        super().__init__(
            name=name,
            role="task_worker",
            system_prompt="You are a task execution agent."
        )
        self.current_task: Optional[TaskMessage] = None

    @on(TaskMessage)
    async def handle_task(self, task: TaskMessage, time: int):
        if task.assigned_to != self.name:
            return

        print(f"{self.name}: Starting task {task.task_id} - {task.name}")
        self.current_task = task
        self.current_task.start_time = datetime.now().timestamp()

        # Simulate task execution
        await asyncio.sleep(task.duration)

        self.current_task.completed = True
        self.current_task.end_time = datetime.now().timestamp()

        # Report completion
        await self.broadcast_message(self.current_task)
        print(f"{self.name}: Completed task {task.task_id} - {task.name}")


class TaskManagerPlayground(PlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.tasks: List[TaskMessage] = []
        self.completed_tasks: List[TaskMessage] = []

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
                    print(f"  Executed by: {completed_task.assigned_to}")
                    print(f"  Duration: {duration:.2f} seconds")
                await self.finish()

    async def assign_tasks(self, tasks: List[TaskMessage], worker_names: List[str]):
        self.tasks = tasks

        # Simple round-robin task assignment
        for i, task in enumerate(tasks):
            worker_name = worker_names[i % len(worker_names)]
            task.assigned_to = worker_name
            await self.broadcast_message(task)
            print(f"Task Manager: Assigned task {task.task_id} to {worker_name}")


async def main():
    # Create playground and worker agents
    playground = TaskManagerPlayground()
    worker1 = TaskWorkerAgent("worker1")
    worker2 = TaskWorkerAgent("worker2")
    workers = [worker1, worker2]

    # Define some tasks
    tasks = [
        TaskMessage(task_id="1", name="Process Data", description="Process incoming data", duration=2),
        TaskMessage(task_id="2", name="Generate Report", description="Create summary report", duration=3),
        TaskMessage(task_id="3", name="Send Notifications", description="Notify stakeholders", duration=1),
        TaskMessage(task_id="4", name="Backup Data", description="Backup processed data", duration=2),
    ]

    # Start the playground and execute tasks
    async with playground.play(workers=workers) as active_playground:
        await active_playground.assign_tasks(
            tasks=tasks,
            worker_names=[worker.name for worker in workers]
        )


if __name__ == "__main__":
    asyncio.run(main())
