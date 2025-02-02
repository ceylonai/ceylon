import asyncio
import uuid
from typing import Dict, Callable

from ceylon.llm import PlayGround, LLMAgent
from ceylon.task.data import TaskMessage, TaskGroup, TaskStatus, TaskGroupGoal, GoalStatus


def group_tasks_completed(group_id: str) -> Callable:
    """Create a condition checker for a specific group"""

    def checker(task_groups: Dict[str, TaskGroup],
                completed_tasks: Dict[str, TaskMessage]) -> bool:
        print(f"Completed tasks: {completed_tasks}")
        if len(completed_tasks) == 5:
            return True
        return (group_id in task_groups and
                task_groups[group_id].status == TaskStatus.COMPLETED)

    return checker


async def main():
    playground = PlayGround()
    workers = [
        LLMAgent("worker1", "data_processor", max_concurrent_tasks=2),
        LLMAgent("worker2", "data_processor", max_concurrent_tasks=2),
        LLMAgent("worker3", "reporter", max_concurrent_tasks=3),
        LLMAgent("worker4", "system_admin", max_concurrent_tasks=2)
    ]

    # Create task groups with integrated goals
    data_group = PlayGround.create_task_group(
        name="Data Processing",
        description="Initial data processing tasks",
        subtasks=[
            TaskMessage(task_id=str(uuid.uuid4()), name="Process Raw Data",
                        description="Process raw data files",
                        duration=2, required_role="data_processor")
            for _ in range(2)
        ],
        goal=TaskGroupGoal(
            name="Complete Data Processing",
            description="Complete all data processing tasks",
            check_condition=group_tasks_completed(str(uuid.uuid4())),  # Will be updated with actual group ID
            success_message="Successfully completed all data processing!",
            failure_message="Failed to complete data processing tasks."
        ),
        priority=1
    )

    # Update the goal's check condition with the actual group ID
    data_group.goal.check_condition = group_tasks_completed(data_group.task_id)

    reporting_group = PlayGround.create_task_group(
        name="Report Generation",
        description="Generate reports from processed data",
        subtasks=[
            TaskMessage(task_id=str(uuid.uuid4()), name="Generate Report",
                        description="Create analysis report",
                        duration=3, required_role="reporter")
            for _ in range(2)
        ],
        goal=TaskGroupGoal(
            name="Complete Report Generation",
            description="Complete all reporting tasks",
            check_condition=group_tasks_completed(str(uuid.uuid4())),  # Will be updated with actual group ID
            success_message="Successfully completed all reports!",
            failure_message="Failed to complete report generation."
        ),
        depends_on=[data_group.task_id],
        priority=2
    )

    # Update the goal's check condition with the actual group ID
    reporting_group.goal.check_condition = group_tasks_completed(reporting_group.task_id)

    maintenance_group = PlayGround.create_task_group(
        name="System Maintenance",
        description="Regular system maintenance tasks",
        subtasks=[
            TaskMessage(task_id=str(uuid.uuid4()), name="Backup Data",
                        description="Backup processed data",
                        duration=2, required_role="system_admin")
            for _ in range(1)
        ],
        goal=TaskGroupGoal(
            name="Complete System Maintenance",
            description="Complete all maintenance tasks",
            check_condition=group_tasks_completed(str(uuid.uuid4())),  # Will be updated with actual group ID
            success_message="Successfully completed system maintenance!",
            failure_message="Failed to complete maintenance tasks."
        ),
        priority=3
    )

    # Update the goal's check condition with the actual group ID
    maintenance_group.goal.check_condition = group_tasks_completed(maintenance_group.task_id)

    async with playground.play(workers=workers) as active_playground:
        # Start task groups
        await active_playground.assign_task_groups([
            data_group,
            reporting_group,
            maintenance_group
        ])

        # Wait for completion
        while True:
            await asyncio.sleep(1)
            all_completed = all(group.status == TaskStatus.COMPLETED
                                for group in active_playground.task_groups.values())
            all_goals_achieved = all(group.goal and group.goal.status == GoalStatus.ACHIEVED
                                     for group in active_playground.task_groups.values())
            if all_completed and all_goals_achieved:
                break


if __name__ == "__main__":
    asyncio.run(main())
