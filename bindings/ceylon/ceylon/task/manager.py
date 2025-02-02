#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import uuid
from collections import defaultdict
from typing import List, Optional, Dict, Set

from loguru import logger

from ceylon.task.data import TaskMessage, TaskGroup, TaskStatus, TaskGroupGoal


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TaskMessage] = {}
        self.completed_tasks: Dict[str, TaskMessage] = {}
        self.task_groups: Dict[str, TaskGroup] = {}
        self.active_groups: Set[str] = set()
        self.completed_groups: Set[str] = set()
        self.workers_by_role: Dict[str, List[str]] = defaultdict(list)
        self.worker_task_counts: Dict[str, int] = defaultdict(int)
        self.task_templates = self._create_task_templates()

    @staticmethod
    def create_task_group(
            name: str,
            description: str,
            subtasks: List[TaskMessage],
            goal: Optional[TaskGroupGoal] = None,
            dependencies: Dict[str, List[str]] = None,
            depends_on: List[str] = None,
            priority: int = 1
    ) -> TaskGroup:
        group_id = str(uuid.uuid4())

        # Link subtasks to group
        for subtask in subtasks:
            subtask.group_id = group_id

        return TaskGroup(
            task_id=group_id,
            name=name,
            description=description,
            subtasks=subtasks,
            goal=goal,
            dependencies=dependencies or {},
            depends_on=depends_on or [],
            priority=priority
        )

    def check_group_dependencies(self, group: TaskGroup) -> bool:
        """Check if all dependencies for a task group are met"""
        return all(
            dep_id in self.completed_groups
            for dep_id in group.depends_on
        )

    def check_group_completion(self, group: TaskGroup) -> bool:
        """Check if all subtasks in a group are completed"""
        return all(
            task.task_id in self.completed_tasks
            for task in group.subtasks
        )

    async def check_group_goals(self) -> bool:
        """Check if any group goals have been achieved"""
        goals_achieved = False
        for group in self.task_groups.values():
            if group.check_goal(self.task_groups, self.completed_tasks):
                goals_achieved = True
        return goals_achieved

    async def handle_task_completion(self, task: TaskMessage) -> bool:
        """Handle task completion and return whether all groups are completed"""
        if task.completed and task.task_id in self.tasks:
            self.completed_tasks[task.task_id] = task
            self.worker_task_counts[task.assigned_to] -= 1

            if task.group_id in self.task_groups:
                group = self.task_groups[task.group_id]
                if self.check_group_completion(group):
                    group.status = TaskStatus.COMPLETED
                    if group.id in self.active_groups:
                        self.active_groups.remove(group.id)
                    self.completed_groups.add(group.id)
                    await self._print_group_statistics(group)

                    if group.check_goal(self.task_groups, self.completed_tasks):
                        logger.debug(f"\nGoal achieved for group: {group.name}")
                        return len(self.completed_groups) == len(self.task_groups)
            return False

    def register_worker(self, worker_name: str, role: str):
        """Register a new worker with their role"""
        self.workers_by_role[role].append(worker_name)
        logger.debug(f"Task Manager: Worker {worker_name} registered with role {role}")

    async def assign_group_tasks(self, group: TaskGroup):
        """Assign tasks from a specific group"""
        tasks_by_role = defaultdict(list)
        for task in group.subtasks:
            if task.task_id not in self.completed_tasks:
                tasks_by_role[task.required_role].append(task)

        assignments = []
        for role, role_tasks in tasks_by_role.items():
            available_workers = self.workers_by_role.get(role, [])
            if not available_workers:
                logger.debug(f"Warning: No workers available for role {role}")
                continue

            for task in role_tasks:
                worker_name = min(
                    available_workers,
                    key=lambda w: self.worker_task_counts[w]
                )
                task.assigned_to = worker_name
                task.status = TaskStatus.IN_PROGRESS
                self.worker_task_counts[worker_name] += 1
                assignments.append(task)

        return assignments

    async def activate_ready_groups(self):
        """Activate groups whose dependencies are met and return new assignments"""
        new_assignments = []
        for group_id, group in self.task_groups.items():
            if (group_id not in self.active_groups and
                    group_id not in self.completed_groups and
                    self.check_group_dependencies(group)):
                self.active_groups.add(group_id)
                logger.debug(f"\nActivating Task Group: {group.name}")
                assignments = await self.assign_group_tasks(group)
                new_assignments.extend(assignments)
        return new_assignments

    async def assign_task_groups(self, groups: List[TaskGroup]):
        """Initialize and start processing multiple task groups"""
        all_assignments = []
        # Store all task groups
        for group in groups:
            self.task_groups[group.task_id] = group
            # Store all tasks
            for task in group.subtasks:
                self.tasks[task.task_id] = task

        # Activate groups with no dependencies
        for group in groups:
            if not group.depends_on:
                self.active_groups.add(group.task_id)
                assignments = await self.assign_group_tasks(group)
                all_assignments.extend(assignments)

        return all_assignments

    @staticmethod
    def _create_task_templates():
        return {
            "data_processor": {
                "standard": lambda: TaskMessage(
                    task_id=str(uuid.uuid4()),
                    name="Process Data Batch",
                    description="Process incoming data batch",
                    duration=2,
                    required_role="data_processor"
                ),
            },
            "reporter": {
                "standard": lambda: TaskMessage(
                    task_id=str(uuid.uuid4()),
                    name="Generate Report",
                    description="Generate periodic report",
                    duration=3,
                    required_role="reporter"
                ),
            },
            "system_admin": {
                "standard": lambda: TaskMessage(
                    task_id=str(uuid.uuid4()),
                    name="System Maintenance",
                    description="Perform system maintenance",
                    duration=2,
                    required_role="system_admin"
                ),
            }
        }

    async def _print_group_statistics(self, group: TaskGroup):
        """Print statistics for a specific task group"""
        logger.debug(f"\nStatistics for Task Group: {group.name}")
        await self._print_task_stats(group.subtasks)

    async def print_all_statistics(self):
        """Print statistics for all task groups"""
        logger.debug("\nOverall Statistics:")
        for group in self.task_groups.values():
            logger.debug(f"\nGroup: {group.name}")
            logger.debug(f"Status: {group.status.value}")
            await self._print_task_stats(group.subtasks)

    async def _print_task_stats(self, tasks: List[TaskMessage]):
        """Print statistics for a list of tasks"""
        role_stats = defaultdict(lambda: {"count": 0, "total_duration": 0})

        for task in tasks:
            if task.task_id in self.completed_tasks:
                completed_task = self.completed_tasks[task.task_id]
                duration = completed_task.end_time - completed_task.start_time
                role_stats[task.required_role]["count"] += 1
                role_stats[task.required_role]["total_duration"] += duration

        for role, stats in role_stats.items():
            avg_duration = stats["total_duration"] / stats["count"]
            logger.debug(f"Role: {role}")
            logger.debug(f"  Tasks Completed: {stats['count']}")
            logger.debug(f"  Average Duration: {avg_duration:.2f} seconds")
