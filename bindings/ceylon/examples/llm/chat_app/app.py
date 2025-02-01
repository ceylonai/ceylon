import asyncio
import uuid
from typing import List, Dict, Callable

from ceylon.llm.playground import PlayGround, TaskWorkerAgent
from ceylon.task.data import TaskMessage, TaskGroupGoal, TaskGroup, TaskStatus


def specific_groups_completed(group_ids: List[str]) -> Callable:
    """Create a condition checker for specific groups"""

    def checker(task_groups: Dict[str, TaskGroup],
                completed_tasks: Dict[str, TaskMessage]) -> bool:
        print(len(task_groups))
        return all(
            group_id in task_groups
            and task_groups[group_id].status == TaskStatus.COMPLETED
            for group_id in group_ids
        )

    return checker


async def main():
    playground = PlayGround()
    workers = [
        TaskWorkerAgent("worker1", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker2", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker3", "reporter", max_concurrent_tasks=3),
        TaskWorkerAgent("worker4", "system_admin", max_concurrent_tasks=2)
    ]

    # Create task groups (as before)
    data_group = playground.create_task_group(
        name="Data Processing",
        description="Initial data processing tasks",
        subtasks=[
            TaskMessage(task_id=str(uuid.uuid4()), name="Process Raw Data",
                        description="Process raw data files",
                        duration=2, required_role="data_processor")
            for _ in range(2)
        ],
        priority=1
    )

    reporting_group = playground.create_task_group(
        name="Report Generation",
        description="Generate reports from processed data",
        subtasks=[
            TaskMessage(task_id=str(uuid.uuid4()), name="Generate Report",
                        description="Create analysis report",
                        duration=3, required_role="reporter")
            for _ in range(2)
        ],
        depends_on=[data_group.task_id],
        priority=2
    )

    maintenance_group = playground.create_task_group(
        name="System Maintenance",
        description="Regular system maintenance tasks",
        subtasks=[
            TaskMessage(task_id=str(uuid.uuid4()), name="Backup Data",
                        description="Backup processed data",
                        duration=2, required_role="system_admin")
            for _ in range(1)
        ],
        priority=3
    )

    # Define goals
    final_goal = TaskGroupGoal(
        name="Complete Processing and Reporting",
        description="Complete data processing and report generation",
        check_condition=specific_groups_completed([data_group.task_id, reporting_group.task_id]),
        success_message="Successfully completed data processing and report generation!",
        failure_message="Failed to complete processing and reporting tasks.",
        dependent_groups=[data_group.task_id, reporting_group.task_id]
    )

    async with playground.play(workers=workers) as active_playground:
        # Add goals
        await active_playground.add_goal("final_goal", final_goal)

        # Start task groups
        await active_playground.assign_task_groups([
            data_group,
            reporting_group,
            maintenance_group
        ])

        # Wait for completion or goal achievement
        while not await active_playground.check_goals():
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
