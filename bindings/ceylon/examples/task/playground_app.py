#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import uuid
from typing import Dict, Callable, Optional, List
from loguru import logger

from ceylon.task import TaskExecutionAgent, TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal, GoalStatus
from ceylon.task.manager import TaskManager

class TaskProcessor:
    def __init__(self, num_workers: int = 2, tasks_per_worker: int = 2):
        self.playground = TaskPlayGround(name="task_processor")
        self.workers = [
            TaskExecutionAgent(
                f"worker{i}",
                "processor",
                max_concurrent_tasks=tasks_per_worker
            )
            for i in range(num_workers)
        ]

    def create_goal_checker(self, required_tasks: int) -> Callable:
        """Creates a goal checker that completes when X tasks are done"""
        def check_completion(task_groups: Dict[str, TaskGroup],
                             completed_tasks: Dict[str, TaskMessage]) -> bool:
            completed_group_tasks = sum(
                1 for task in completed_tasks.values()
                if hasattr(task, 'group_id') and
                task.group_id in task_groups
            )
            logger.info(f"Progress: {completed_group_tasks}/{required_tasks} tasks completed")
            return completed_group_tasks >= required_tasks

        return check_completion

    def create_processing_tasks(self, num_tasks: int) -> List[TaskMessage]:
        """Create a list of processing tasks"""
        return [
            TaskMessage(
                task_id=str(uuid.uuid4()),
                name=f"Process Data Item {i}",
                description=f"Processing task {i}",
                duration=1,
                required_role="processor",
                metadata={"item_number": i}
            )
            for i in range(num_tasks)
        ]

    def create_task_group(self, num_tasks: int, required_tasks: int) -> TaskGroup:
        """Create a task group with tasks and completion goal"""
        return TaskManager.create_task_group(
            name="Data Processing",
            description=f"Process {num_tasks} data items, goal achieves at {required_tasks}",
            subtasks=self.create_processing_tasks(num_tasks),
            goal=TaskGroupGoal(
                name="Partial Processing Complete",
                description=f"Complete at least {required_tasks} processing tasks",
                check_condition=self.create_goal_checker(required_tasks),
                success_message="Successfully completed minimum required tasks!",
                failure_message="Failed to complete minimum required tasks."
            ),
            priority=1
        )

    async def monitor_progress(self, active_playground: TaskPlayGround,
                               processing_group: TaskGroup) -> None:
        """Monitor task group progress until goal is achieved"""
        while True:
            await asyncio.sleep(1)
            current_group = active_playground.task_manager.task_groups[processing_group.task_id]

            # Print status updates
            logger.info(f"Group Status: {current_group.status}")
            if current_group.goal:
                logger.info(f"Goal Status: {current_group.goal.status}")

            if (current_group.goal and
                    current_group.goal.status == GoalStatus.ACHIEVED):
                logger.info("Goal achieved! System can stop while tasks continue.")
                break

    async def print_statistics(self, active_playground: TaskPlayGround) -> None:
        """Print completion statistics for all tasks"""
        completed_tasks = active_playground.get_completed_tasks()
        logger.info(f"\nCompleted Tasks: {len(completed_tasks)}")

        for task_id, output in completed_tasks.items():
            if output.completed:
                duration = (output.end_time - output.start_time
                            if output.end_time and output.start_time else None)
                logger.info(
                    f"Task {task_id} ({output.name}) - "
                    f"Duration: {duration:.2f}s - "
                    f"Metadata: {output.metadata}"
                )
            else:
                logger.warning(
                    f"Task {task_id} ({output.name}) failed: {output.error}"
                )

        task_results = active_playground.get_task_results()
        logger.info(f"\nTask Results: {len(task_results)}")
        logger.info(task_results)

    async def run(self, num_tasks: int = 10, required_tasks: int = 5) -> None:
        """Run the task processing system"""
        processing_group = self.create_task_group(num_tasks, required_tasks)

        async with self.playground.play(workers=self.workers) as active_playground:
            await active_playground.assign_task_groups([processing_group])

            # Monitor progress until goal is achieved
            await self.monitor_progress(active_playground, processing_group)

            # Print final statistics
            await self.print_statistics(active_playground)

async def main():
    # Initialize and run task processor
    processor = TaskProcessor(num_workers=2, tasks_per_worker=2)
    await processor.run(num_tasks=10, required_tasks=5)

if __name__ == "__main__":
    asyncio.run(main())