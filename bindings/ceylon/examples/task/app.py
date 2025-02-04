import asyncio
import uuid
from typing import Dict, Callable
from loguru import logger

from ceylon.task import TaskExecutionAgent, TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal, GoalStatus
from ceylon.task.manager import TaskManager


def create_goal_checker(required_tasks: int) -> Callable:
    """Creates a goal checker that completes when X tasks from a group are done"""
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


async def main():
    # Initialize playground and workers
    playground = TaskPlayGround()
    workers = [
        TaskExecutionAgent("worker1", "processor", max_concurrent_tasks=2),
        TaskExecutionAgent("worker2", "processor", max_concurrent_tasks=2),
    ]

    # Create task group with a clear goal
    processing_group = TaskManager.create_task_group(
        name="Data Processing",
        description="Process 10 data items, goal achieves at 5",
        subtasks=[
            TaskMessage(
                task_id=str(uuid.uuid4()),
                name=f"Process Data Item {i}",
                instructions=f"Processing task {i}",
                duration=1,
                required_role="processor",
                metadata={"item_number": i}
            )
            for i in range(10)
        ],
        goal=TaskGroupGoal(
            name="Partial Processing Complete",
            description="Complete at least 5 processing tasks",
            check_condition=create_goal_checker(required_tasks=5),
            success_message="Successfully completed minimum required tasks!",
            failure_message="Failed to complete minimum required tasks."
        ),
        priority=1
    )

    async with playground.play(workers=workers) as active_playground:
        active_playground: TaskPlayGround = active_playground
        await active_playground.assign_task_groups([processing_group])

        # Wait for goal achievement
        while True:
            await asyncio.sleep(1)
            current_group = active_playground.task_manager.task_groups[processing_group.task_id]

            # Print clear status updates
            logger.info(f"Group Status: {current_group.status}")
            if current_group.goal:
                logger.info(f"Goal Status: {current_group.goal.status}")

            if (current_group.goal and
                    current_group.goal.status == GoalStatus.ACHIEVED):
                logger.info("Goal achieved! System can stop while tasks continue.")
                break

        # Print completion statistics
        completed_tasks = active_playground.get_completed_tasks()
        logger.info(f"Completed Tasks: {len(completed_tasks)}")

        for task_id, output in completed_tasks.items():
            if output.completed:
                duration = output.end_time - output.start_time if output.end_time and output.start_time else None
                logger.info(f"Task {task_id} ({output.name}) - "
                            f"Duration: {duration:.2f}s - "
                            f"Metadata: {output.metadata}")
            else:
                logger.warning(f"Task {task_id} ({output.name}) failed: {output.error}")

        task_results = active_playground.get_task_results()
        logger.info(f"Task Results: {len(task_results)}")
        logger.info(task_results)


if __name__ == "__main__":
    asyncio.run(main())