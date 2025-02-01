#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from typing import Callable, List, Dict, Optional

from loguru import logger

from ceylon.task.data import TaskGroup, TaskMessage, TaskStatus, TaskGroupGoal, GoalStatus


class GoalChecker:
    def __init__(self):
        self.goals: Dict[str, TaskGroupGoal] = {}

    def add_goal(self, goal_id: str, goal: TaskGroupGoal):
        self.goals[goal_id] = goal

    async def check_goals(self, task_groups: Dict[str, TaskGroup],
                          completed_tasks: Dict[str, TaskMessage]) -> Optional[str]:
        """
        Check all goals and return the ID of any achieved final goal
        Returns None if no final goal is achieved
        """
        achieved_final_goal = None

        for goal_id, goal in self.goals.items():
            if goal.status != GoalStatus.ACHIEVED:
                # Check if dependent groups are completed
                if goal.dependent_groups:
                    if not all(group_id in task_groups and
                               task_groups[group_id].status == TaskStatus.COMPLETED
                               for group_id in goal.dependent_groups):
                        continue

                # Check goal condition
                if goal.check_condition(task_groups, completed_tasks):
                    goal.status = GoalStatus.ACHIEVED
                    logger.info(f"\nGoal Achieved: {goal.name}")
                    logger.info(goal.success_message)
                    achieved_final_goal = goal_id

        return achieved_final_goal


class PlayGroundExtension:
    def __init__(self, playground):
        self.playground = playground
        self.goal_checker = GoalChecker()

    def add_task_goal(self, goal_id: str, goal: TaskGroupGoal):
        """Add a new goal to the system"""
        self.goal_checker.add_goal(goal_id, goal)

    async def check_task_goals(self) -> bool:
        """
        Check if any final goals have been achieved
        Returns True if a final goal is achieved
        """
        achieved_goal = await self.goal_checker.check_goals(
            self.playground.task_groups,
            self.playground.completed_tasks
        )
        return achieved_goal is not None


# Example goal conditions
def all_groups_completed(task_groups: Dict[str, TaskGroup],
                         completed_tasks: Dict[str, TaskMessage]) -> bool:
    """Check if all task groups are completed"""
    return all(group.status == TaskStatus.COMPLETED
               for group in task_groups.values())


def specific_groups_completed(group_ids: List[str]) -> Callable:
    """Create a condition checker for specific groups"""

    def checker(task_groups: Dict[str, TaskGroup],
                completed_tasks: Dict[str, TaskMessage]) -> bool:
        return all(
            group_id in task_groups
            and task_groups[group_id].status == TaskStatus.COMPLETED
            for group_id in group_ids
        )

    return checker
