#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
import pickle
from dataclasses import dataclass
from typing import List
from ceylon import BaseAgent, DEFAULT_WORKSPACE_ID, PeerMode, on, on_run, on_connect, AgentDetail


@dataclass
class Task:
    id: int
    description: str
    difficulty: int


@dataclass
class TaskAssignment:
    task: Task


@dataclass
class TaskResult:
    task_id: int
    worker: str
    success: bool


class WorkerAgent(BaseAgent):
    def __init__(self, name: str, skill_level: int,
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_peer=""):
        self.name = name
        self.skill_level = skill_level
        self.has_task = False
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            mode=PeerMode.CLIENT
        )

    @on(TaskAssignment)
    async def handle_task(self, data: TaskAssignment, time: int,  agent: AgentDetail):
        print(f"Task {data.task.id} assigned to {self.name}")
        if self.has_task:
            return

        self.has_task = True
        await asyncio.sleep(data.task.difficulty)
        success = self.skill_level >= data.task.difficulty

        result = TaskResult(
            task_id=data.task.id,
            worker=self.name,
            success=success
        )
        await self.broadcast(pickle.dumps(result))

    @on_run()
    async def handle_run(self, inputs: bytes):
        while True:
            await asyncio.sleep(0.1)


class TaskManager(BaseAgent):
    def __init__(self, tasks: List[Task], expected_workers: int,
                 name="task_manager", port=8000):
        super().__init__(
            name=name,
            port=port,
            mode=PeerMode.ADMIN,
            role="task_manager"
        )
        self.tasks = tasks
        self.expected_workers = expected_workers
        self.task_results = []
        self.tasks_assigned = False

    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        connected_count = len(await self.get_connected_agents())
        print(f"Worker connected: {agent.name} ({agent.name}) - Role: {agent.role} ({topic})")
        print(f"Connected workers: {connected_count} of {self.expected_workers} expected {self.tasks_assigned}")
        if connected_count == self.expected_workers and not self.tasks_assigned:
            print("All workers connected")
            await self.assign_tasks()

    @on(TaskResult)
    async def handle_result(self, data: TaskResult, time: int, agent: AgentDetail):
        self.task_results.append(data)
        if len(self.task_results) == len(self.tasks):
            print("All tasks completed")
            for result in self.task_results:
                print(f"Task {result.task_id} assigned to {result.worker} - {'Success' if result.success else 'Failure'}")
            await self.end_task_management()

    async def assign_tasks(self):
        if self.tasks_assigned:
            return

        self.tasks_assigned = True
        connected_workers = await self.get_connected_agents()
        for task, worker in zip(self.tasks, connected_workers):
            print(f"Assigning task {task.id} to {worker.name}")
            await self.broadcast(pickle.dumps(TaskAssignment(task=task)))

    async def end_task_management(self):
        success_rate = sum(1 for r in self.task_results if r.success) / len(self.task_results)
        print(f"Success rate: {success_rate:.2%}")
        await self.stop()

    @on_run()
    async def handle_run(self, inputs: bytes):
        while True:
            if len(self.task_results) == len(self.tasks):
                break
            await asyncio.sleep(0.1)


async def main():
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="ML model training", difficulty=8),
    ]

    task_manager = TaskManager(tasks, expected_workers=3)
    admin_details = task_manager.details()

    workers = [
        WorkerAgent("Junior", skill_level=3, admin_peer=admin_details.id),
        WorkerAgent("Intermediate", skill_level=6, admin_peer=admin_details.id),
        WorkerAgent("Senior", skill_level=9, admin_peer=admin_details.id),
        WorkerAgent("Senior2", skill_level=8, admin_peer=admin_details.id),
    ]

    await task_manager.start_agent(b"", workers)


if __name__ == "__main__":
    asyncio.run(main())
