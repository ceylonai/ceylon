#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
# 
#
import asyncio

from loguru import logger
from ceylon import on, on_connect
from ceylon.base.playground import BasePlayGround, TaskOutput
from ceylon.task.data import TaskMessage, TaskRequest, TaskStatusUpdate, TaskStatus
from .manager import TaskManager


class TaskPlayGround(BasePlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.task_manager = TaskManager()

    @on(TaskMessage)
    async def handle_task_completion(self, task: TaskMessage, time: int):
        if task.completed and task.task_id in self.task_manager.tasks:
            # Record task completion
            logger.info(f"Task {task.task_id} completed by {task.assigned_to}")

            # Create task output record
            task_output = TaskOutput(
                task_id=task.task_id,
                name=task.name,
                completed=True,
                start_time=task.start_time,
                end_time=task.end_time,
                metadata=task.metadata if task.metadata else {}
            )
            self.add_completed_task(task.task_id, task_output)
            # Store task result if present
            if hasattr(task, 'result'):
                self.add_task_result(task.task_id, task.result)

            self._all_tasks_completed_events[task.task_id].set()
            # Broadcast status update
            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                group_id=task.group_id
            ))

            # Check if all groups are completed
            all_completed = await self.task_manager.handle_task_completion(task)
            if all_completed:
                logger.info("\nAll groups completed and goals achieved!")
                await self.finish()
                return

            # Activate dependent groups
            new_assignments = await self.task_manager.activate_ready_groups()
            for assignment in new_assignments:
                await self.broadcast_message(assignment)

    @on(TaskStatusUpdate)
    async def handle_task_status_update(self, update: TaskStatusUpdate, time: int):
        if update.status == TaskStatus.FAILED and update.task_id in self.task_manager.tasks:
            task = self.task_manager.tasks[update.task_id]
            # Record failed task
            task_output = TaskOutput(
                task_id=task.task_id,
                name=task.name,
                completed=False,
                start_time=task.start_time,
                end_time=task.end_time,
                error=update.message
            )
            self.add_completed_task(task.task_id, task_output)

    @on(TaskRequest)
    async def handle_task_request(self, request: TaskRequest, time: int):
        templates = self.task_manager.task_templates
        if request.role not in templates:
            logger.warning(f"No task templates for role {request.role}")
            return

        template = templates[request.role].get(request.task_type)
        if not template:
            logger.warning(f"No template for task type {request.task_type}")
            return

        new_task = template()
        new_task.assigned_to = request.requester
        self.task_manager.tasks[new_task.task_id] = new_task
        self.task_manager.worker_task_counts[request.requester] += 1

        await self.broadcast_message(new_task)
        logger.info(f"Task Manager: Created and assigned new task {new_task.task_id} to {request.requester}")

    @on_connect("*")
    async def handle_worker_connection(self, topic: str, agent: "AgentDetail"):
        self.task_manager.register_worker(agent.name, agent.role)

    async def assign_task_groups(self, groups):
        """Initialize and start processing multiple task groups"""
        assignments = await self.task_manager.assign_task_groups(groups)
        for assignment in assignments:
            await self.broadcast_message(assignment)
            self._all_tasks_completed_events[assignment.task_id] = asyncio.Event()

    async def print_all_statistics(self):
        """Print statistics for all task groups"""
        await self.task_manager.print_all_statistics()

        # Print task completion statistics
        completed_tasks = self.get_completed_tasks()
        successful = sum(1 for t in completed_tasks.values() if t.completed)
        failed = sum(1 for t in completed_tasks.values() if not t.completed)

        logger.info("\nTask Completion Statistics:")
        logger.info(f"Total Tasks: {len(completed_tasks)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")

        # Print task results if available
        task_results = self.get_task_results()
        if task_results:
            logger.info("\nTask Results Summary:")
            for task_id, result in task_results.items():
                logger.info(f"Task {task_id}: {result}")
