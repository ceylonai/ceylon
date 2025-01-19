#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
import pickle
from dataclasses import dataclass
from typing import List

from loguru import logger
from ceylon.base.agents import Admin, Worker
from ceylon.static_val import DEFAULT_WORKSPACE_ID

# Data Structures
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
class WorkerAgent(Worker):
    def __init__(self, name: str, skill_level: int,
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_peer="",
                 admin_port=8000):
        self.name = name
        self.skill_level = skill_level
        self.has_task = False
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            admin_port=admin_port
        )
        logger.info(f"Worker {name} initialized with skill level {skill_level}")

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            message = pickle.loads(data)

            if isinstance(message, TaskAssignment) and not self.has_task:
                logger.info(f"{self.name} received task: {message.task.description}")
                self.has_task = True

                # Simulate task execution
                await asyncio.sleep(message.task.difficulty)
                success = self.skill_level >= message.task.difficulty

                result = TaskResult(task_id=message.task.id, worker=self.name, success=success)
                # Use broadcast instead of direct message
                await self.broadcast(pickle.dumps(result))
                logger.info(f"{self.name} completed task {message.task.id} with success={success}")

        except Exception as e:
            logger.error(f"Error processing message in worker: {e}")

    async def run(self, inputs: bytes):
        logger.info(f"Worker {self.name} started")
        while True:
            await asyncio.sleep(0.1)

# Task Manager
class TaskManager(Admin):
    def __init__(self, tasks: List[Task], expected_workers: int,
                 name="task_manager", port=8000):
        super().__init__(name=name, port=port)
        self.tasks = tasks
        self.expected_workers = expected_workers
        self.task_results = []
        self.tasks_assigned = False
        logger.info(f"Task Manager initialized with {len(tasks)} tasks")

    async def on_agent_connected(self, topic: str, agent_id: str):
        await super().on_agent_connected(topic, agent_id)
        connected_count = len(self.get_connected_agents())
        logger.info(f"Worker connected. {connected_count}/{self.expected_workers} workers connected.")

        if connected_count == self.expected_workers and not self.tasks_assigned:
            logger.info("All workers connected. Starting task distribution.")
            await self.assign_tasks()

    async def assign_tasks(self):
        if self.tasks_assigned:
            return

        self.tasks_assigned = True
        connected_workers = self.get_connected_agents()

        for task, worker in zip(self.tasks, connected_workers):
            assignment = TaskAssignment(task=task)
            # Broadcast the task assignment
            await self.broadcast(pickle.dumps(assignment))
            logger.info(f"Assigned task {task.id} to worker {worker.name}")

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            message = pickle.loads(data)
            if isinstance(message, TaskResult):
                self.task_results.append(message)
                logger.info(
                    f"Received result for task {message.task_id} from {message.worker}: "
                    f"{'Success' if message.success else 'Failure'}"
                )

                if len(self.task_results) == len(self.tasks):
                    await self.end_task_management()

        except Exception as e:
            logger.error(f"Error processing message in manager: {e}")

    async def end_task_management(self):
        success_rate = sum(1 for result in self.task_results if result.success) / len(self.task_results)
        logger.info(f"All tasks completed. Success rate: {success_rate:.2%}")

        # Print detailed results
        logger.info("\nDetailed Results:")
        for result in self.task_results:
            status = "✓" if result.success else "✗"
            logger.info(f"Task {result.task_id} - Worker: {result.worker} - Status: {status}")

        await self.stop()

    async def run(self, inputs: bytes):
        logger.info("Task Manager started")
        while True:
            if len(self.task_results) == len(self.tasks):
                break
            await asyncio.sleep(0.1)

async def main():
    # Create tasks
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="Machine learning model training", difficulty=8),
    ]

    # Create task manager
    task_manager = TaskManager(tasks, expected_workers=3)
    admin_details = task_manager.details()

    # Create workers with proper admin_peer
    workers = [
        WorkerAgent("Junior", skill_level=3, admin_peer=admin_details.id),
        WorkerAgent("Intermediate", skill_level=6, admin_peer=admin_details.id),
        WorkerAgent("Senior", skill_level=9, admin_peer=admin_details.id),
    ]

    try:
        logger.info("Starting task management system...")
        await task_manager.arun_admin(b"", workers)
    except KeyboardInterrupt:
        logger.info("Shutting down task management system...")
    finally:
        pass

if __name__ == "__main__":
    logger.info("Initializing task management system...")
    asyncio.run(main())