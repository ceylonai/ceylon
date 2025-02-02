#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
# 
#
from loguru import logger
from ceylon import on, on_connect
from ceylon.base.playground import BasePlayGround
from ceylon.task.data import TaskMessage, TaskRequest, TaskStatusUpdate, TaskStatus
from .manager import TaskManager


class TaskPlayGround(BasePlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.task_manager = TaskManager()

    @on(TaskMessage)
    async def handle_task_completion(self, task: TaskMessage, time: int):
        all_completed = await self.task_manager.handle_task_completion(task)

        if task.completed and task.task_id in self.task_manager.tasks:
            print(f"Task {task.task_id} completed by {task.assigned_to}")

            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                group_id=task.group_id
            ))

            # If all groups are completed, finish the playground
            if all_completed:
                logger.debug("\nAll groups completed and goals achieved!")
                await self.finish()
                return

            # Check for and activate any dependent groups
            new_assignments = await self.task_manager.activate_ready_groups()
            for assignment in new_assignments:
                await self.broadcast_message(assignment)

    @on(TaskRequest)
    async def handle_task_request(self, request: TaskRequest, time: int):
        templates = self.task_manager.task_templates
        if request.role not in templates:
            logger.debug(f"Warning: No task templates for role {request.role}")
            return

        template = templates[request.role].get(request.task_type)
        if not template:
            logger.debug(f"Warning: No template for task type {request.task_type}")
            return

        new_task = template()
        new_task.assigned_to = request.requester
        self.task_manager.tasks[new_task.task_id] = new_task
        self.task_manager.worker_task_counts[request.requester] += 1

        await self.broadcast_message(new_task)
        logger.debug(f"Task Manager: Created and assigned new task {new_task.task_id} to {request.requester}")

    @on_connect("*")
    async def handle_worker_connection(self, topic: str, agent: "AgentDetail"):
        self.task_manager.register_worker(agent.name, agent.role)

    async def assign_task_groups(self, groups):
        """Initialize and start processing multiple task groups"""
        assignments = await self.task_manager.assign_task_groups(groups)
        for assignment in assignments:
            await self.broadcast_message(assignment)

    async def print_all_statistics(self):
        """Print statistics for all task groups"""
        await self.task_manager.print_all_statistics()
