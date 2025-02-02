#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
import uuid
from typing import Dict, Callable

from ceylon.task import TaskExecutionAgent, TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal, GoalStatus


def create_goal_checker(required_tasks: int) -> Callable:
    """Creates a goal checker that completes when X tasks from a group are done"""

    def check_completion(task_groups: Dict[str, TaskGroup],
                         completed_tasks: Dict[str, TaskMessage]) -> bool:
        # Count completed tasks that belong to this group
        completed_group_tasks = sum(
            1 for task in completed_tasks.values()
            if hasattr(task, 'group_id') and
            task.group_id in task_groups
        )
        print(f"Progress: {completed_group_tasks}/{required_tasks} tasks completed")
        return completed_group_tasks >= required_tasks

    return check_completion


async def main():
    playground = TaskPlayGround()
    workers = [
        TaskExecutionAgent("worker1", "processor", max_concurrent_tasks=2),
        TaskExecutionAgent("worker2", "processor", max_concurrent_tasks=2),
    ]

    # Create a task group with a clear goal: complete 5 tasks
    processing_group = TaskPlayGround.create_task_group(
        name="Data Processing",
        description="Process 10 data items, goal achieves at 5",
        subtasks=[
            TaskMessage(
                task_id=str(uuid.uuid4()),
                name=f"Process Data Item {i}",
                description=f"Processing task {i}",
                duration=1,
                required_role="processor"
            )
            for i in range(10)  # Create 10 tasks
        ],
        goal=TaskGroupGoal(
            name="Partial Processing Complete",
            description="Complete at least 5 processing tasks",
            check_condition=create_goal_checker(required_tasks=5),  # Goal achieves at 5 tasks
            success_message="Successfully completed minimum required tasks!",
            failure_message="Failed to complete minimum required tasks."
        ),
        priority=1
    )

    async with playground.play(workers=workers) as active_playground:
        await active_playground.assign_task_groups([processing_group])

        # Wait for goal achievement
        while True:
            await asyncio.sleep(1)
            current_group = active_playground.task_groups[processing_group.task_id]

            # Print clear status updates
            print(f"\nGroup Status: {current_group.status}")
            if current_group.goal:
                print(f"Goal Status: {current_group.goal.status}")

            if (current_group.goal and
                    current_group.goal.status == GoalStatus.ACHIEVED):
                print("\nGoal achieved! System can stop while tasks continue.")
                break


if __name__ == "__main__":
    asyncio.run(main())

