#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Set

from ceylon import on, on_connect
from ceylon.base.playground import BasePlayGround
from ceylon.llm.agent import LLMAgent


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskMessage:
    task_id: str
    name: str
    description: str
    duration: float
    required_role: str
    parent_id: Optional[str] = None
    group_id: Optional[str] = None  # Reference to TaskGroup
    subtask_ids: Set[str] = field(default_factory=set)
    assigned_to: Optional[str] = None
    completed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    max_concurrent: int = 3
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class TaskGroup:
    task_id: str
    name: str
    description: str
    subtasks: List[TaskMessage]
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # IDs of groups this group depends on
    required_by: List[str] = field(default_factory=list)  # IDs of groups that depend on this group
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1


@dataclass
class TaskRequest:
    requester: str
    role: str
    task_type: str
    priority: int = 1


@dataclass
class TaskStatusUpdate:
    task_id: str
    status: TaskStatus
    message: Optional[str] = None
    group_id: Optional[str] = None


class TaskWorkerAgent(LLMAgent):
    def __init__(self, name: str, worker_role: str, max_concurrent_tasks: int = 3):
        super().__init__(
            name=name,
            role=worker_role,
            system_prompt=f"You are a task execution agent specialized in {worker_role} tasks."
        )
        self.worker_role = worker_role
        self.active_tasks: Dict[str, TaskMessage] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.processing = False

    async def request_task(self, task_type: str, priority: int = 1):
        request = TaskRequest(
            requester=self.name,
            role=self.worker_role,
            task_type=task_type,
            priority=priority
        )
        await self.broadcast_message(request)
        print(f"{self.name}: Requested new {task_type} task")

    @on(TaskStatusUpdate)
    async def handle_status_update(self, update: TaskStatusUpdate, time: int):
        if update.task_id in self.active_tasks:
            print(f"{self.name}: Received status update for task {update.task_id}: {update.status}")
            if update.status == 'completed':
                self.active_tasks.pop(update.task_id, None)

    @on(TaskMessage)
    async def handle_task(self, task: TaskMessage, time: int):
        if task.assigned_to != self.name or task.required_role != self.worker_role:
            return

        await self.task_queue.put(task)
        if not self.processing:
            self.processing = True
            asyncio.create_task(self.process_task_queue())

    async def process_task_queue(self):
        while True:
            if len(self.active_tasks) >= self.max_concurrent_tasks:
                await asyncio.sleep(0.1)
                continue

            try:
                try:
                    task = self.task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    if not self.active_tasks:
                        self.processing = False
                        await self.request_task("standard")
                        break
                    await asyncio.sleep(0.1)
                    continue

                print(f"{self.name} ({self.worker_role}): Starting task {task.task_id} - {task.name}")
                task.start_time = datetime.now().timestamp()
                self.active_tasks[task.task_id] = task
                asyncio.create_task(self.execute_task(task))

            except Exception as e:
                print(f"Error processing task queue for {self.name}: {e}")
                await asyncio.sleep(1)

    async def execute_task(self, task: TaskMessage):
        try:
            await asyncio.sleep(task.duration)
            task.completed = True
            task.end_time = datetime.now().timestamp()
            del self.active_tasks[task.task_id]
            await self.broadcast_message(task)
            print(f"{self.name} ({self.worker_role}): Completed task {task.task_id} - {task.name}")
            await self.request_task("standard")

        except Exception as e:
            print(f"Error executing task {task.task_id}: {e}")
            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status="failed",
                message=str(e)
            ))


class PlayGround(BasePlayGround):
    def __init__(self, name="task_manager", port=8888):
        super().__init__(name=name, port=port)
        self.tasks: Dict[str, TaskMessage] = {}
        self.completed_tasks: Dict[str, TaskMessage] = {}
        self.task_groups: Dict[str, TaskGroup] = {}
        self.active_groups: Set[str] = set()
        self.completed_groups: Set[str] = set()
        self.workers_by_role: Dict[str, List[str]] = defaultdict(list)
        self.worker_task_counts: Dict[str, int] = defaultdict(int)
        self.task_templates = self._create_task_templates()

    def _create_task_templates(self):
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

    def create_top_task(self, name: str, description: str, subtasks: List[TaskMessage],
                        dependencies: Dict[str, List[str]] = None) -> TaskGroup:
        top_task_id = str(uuid.uuid4())

        # Link subtasks to parent
        for subtask in subtasks:
            subtask.parent_id = top_task_id

        return TaskGroup(
            task_id=top_task_id,
            name=name,
            description=description,
            subtasks=subtasks,
            dependencies=dependencies or {}
        )

    def check_top_task_completion(self, top_task: TaskGroup) -> bool:
        """Check if all subtasks in a top task are completed"""
        return all(
            task.task_id in self.completed_tasks
            for task in top_task.subtasks
        )

    @on(TaskRequest)
    async def handle_task_request(self, request: TaskRequest, time: int):
        if request.role not in self.task_templates:
            print(f"Warning: No task templates for role {request.role}")
            return

        template = self.task_templates[request.role].get(request.task_type)
        if not template:
            print(f"Warning: No template for task type {request.task_type}")
            return

        new_task = template()
        new_task.assigned_to = request.requester
        self.tasks[new_task.task_id] = new_task
        self.worker_task_counts[request.requester] += 1

        await self.broadcast_message(new_task)
        print(f"Task Manager: Created and assigned new task {new_task.task_id} to {request.requester}")

    @on_connect("*")
    async def handle_worker_connection(self, topic: str, agent: "AgentDetail"):
        self.workers_by_role[agent.role].append(agent.name)
        print(f"Task Manager: Worker {agent.name} connected with role {agent.role}")

    @on(TaskMessage)
    async def handle_task_completion(self, task: TaskMessage, time: int):
        if task.completed and task.task_id in self.tasks:
            self.completed_tasks[task.task_id] = task
            self.worker_task_counts[task.assigned_to] -= 1

            # Check if this task belongs to a top task
            if task.parent_id and task.parent_id in self.top_tasks:
                top_task = self.top_tasks[task.parent_id]
                if self.check_top_task_completion(top_task):
                    top_task.completed = True
                    print(f"\nTop Task '{top_task.name}' completed!")
                    await self.print_statistics(top_task)
                    await self.finish()

            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status="completed"
            ))

    async def print_statistics(self, top_task: Optional[TaskGroup] = None):
        if top_task:
            print(f"\nStatistics for Top Task: {top_task.name}")
        else:
            print("\nCurrent Statistics:")

        role_stats: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "total_duration": 0})
        tasks_to_analyze = top_task.subtasks if top_task else self.completed_tasks.values()

        for task in tasks_to_analyze:
            if task.task_id in self.completed_tasks:
                task = self.completed_tasks[task.task_id]
                duration = task.end_time - task.start_time
                role_stats[task.required_role]["count"] += 1
                role_stats[task.required_role]["total_duration"] += duration

        for role, stats in role_stats.items():
            avg_duration = stats["total_duration"] / stats["count"]
            print(f"Role: {role}")
            print(f"  Tasks Completed: {stats['count']}")
            print(f"  Average Duration: {avg_duration:.2f} seconds")

    async def assign_tasks(self, top_task: TaskGroup):
        """Assign tasks from a top task"""
        self.top_tasks[top_task.task_id] = top_task

        for task in top_task.subtasks:
            self.tasks[task.task_id] = task

        # Group tasks by role
        tasks_by_role = defaultdict(list)
        for task in top_task.subtasks:
            tasks_by_role[task.required_role].append(task)

        # Assign tasks based on dependencies and roles
        for role, role_tasks in tasks_by_role.items():
            available_workers = self.workers_by_role.get(role, [])
            if not available_workers:
                print(f"Warning: No workers available for role {role}")
                continue

            for task in role_tasks:
                worker_name = min(
                    available_workers,
                    key=lambda w: self.worker_task_counts[w]
                )
                task.assigned_to = worker_name
                self.worker_task_counts[worker_name] += 1
                await self.broadcast_message(task)

    @staticmethod
    def create_task_group(name: str, description: str, subtasks: List[TaskMessage],
                          dependencies: Dict[str, List[str]] = None,
                          depends_on: List[str] = None,
                          priority: int = 1) -> TaskGroup:
        group_id = str(uuid.uuid4())

        # Link subtasks to group
        for subtask in subtasks:
            subtask.group_id = group_id

        return TaskGroup(
            task_id=group_id,
            name=name,
            description=description,
            subtasks=subtasks,
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

    async def activate_ready_groups(self):
        """Activate groups whose dependencies are met"""
        for group_id, group in self.task_groups.items():
            if (group_id not in self.active_groups and
                    group_id not in self.completed_groups and
                    self.check_group_dependencies(group)):
                self.active_groups.add(group_id)
                print(f"\nActivating Task Group: {group.name}")
                # Assign tasks for this group
                await self.assign_group_tasks(group)

    async def assign_group_tasks(self, group: TaskGroup):
        """Assign tasks from a specific group"""
        tasks_by_role = defaultdict(list)
        for task in group.subtasks:
            if task.task_id not in self.completed_tasks:
                tasks_by_role[task.required_role].append(task)

        for role, role_tasks in tasks_by_role.items():
            available_workers = self.workers_by_role.get(role, [])
            if not available_workers:
                print(f"Warning: No workers available for role {role}")
                continue

            for task in role_tasks:
                worker_name = min(
                    available_workers,
                    key=lambda w: self.worker_task_counts[w]
                )
                task.assigned_to = worker_name
                task.status = TaskStatus.IN_PROGRESS
                self.worker_task_counts[worker_name] += 1
                await self.broadcast_message(task)

    @on(TaskMessage)
    async def handle_task_completion(self, task: TaskMessage, time: int):
        if task.completed and task.task_id in self.tasks:
            self.completed_tasks[task.task_id] = task
            self.worker_task_counts[task.assigned_to] -= 1

            # Update task group status
            if task.group_id in self.task_groups:
                group = self.task_groups[task.group_id]
                if self.check_group_completion(group):
                    group.status = TaskStatus.COMPLETED
                    self.active_groups.remove(group.id)
                    self.completed_groups.add(group.id)
                    print(f"\nTask Group '{group.name}' completed!")
                    await self.print_group_statistics(group)

                    # Activate dependent groups
                    await self.activate_ready_groups()

            # Check if all groups are completed
            if len(self.completed_groups) == len(self.task_groups):
                print("\nAll Task Groups completed!")
                await self.print_all_statistics()
                await self.finish()

            await self.broadcast_message(TaskStatusUpdate(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                group_id=task.group_id
            ))

    async def print_group_statistics(self, group: TaskGroup):
        print(f"\nStatistics for Task Group: {group.name}")
        await self._print_task_stats(group.subtasks)

    async def print_all_statistics(self):
        print("\nOverall Statistics:")
        for group in self.task_groups.values():
            print(f"\nGroup: {group.name}")
            print(f"Status: {group.status.value}")
            await self._print_task_stats(group.subtasks)

    async def _print_task_stats(self, tasks: List[TaskMessage]):
        role_stats = defaultdict(lambda: {"count": 0, "total_duration": 0})

        for task in tasks:
            if task.task_id in self.completed_tasks:
                completed_task = self.completed_tasks[task.task_id]
                duration = completed_task.end_time - completed_task.start_time
                role_stats[task.required_role]["count"] += 1
                role_stats[task.required_role]["total_duration"] += duration

        for role, stats in role_stats.items():
            avg_duration = stats["total_duration"] / stats["count"]
            print(f"Role: {role}")
            print(f"  Tasks Completed: {stats['count']}")
            print(f"  Average Duration: {avg_duration:.2f} seconds")

    async def assign_task_groups(self, groups: List[TaskGroup]):
        """Initialize and start processing multiple task groups"""
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
                await self.assign_group_tasks(group)


async def main():
    playground = PlayGround()
    workers = [
        TaskWorkerAgent("worker1", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker2", "data_processor", max_concurrent_tasks=2),
        TaskWorkerAgent("worker3", "reporter", max_concurrent_tasks=3),
        TaskWorkerAgent("worker4", "system_admin", max_concurrent_tasks=2)
    ]

    # Create multiple task groups with dependencies
    # Group 1: Data Processing
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

    # Group 2: Reporting (depends on Data Processing)
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

    # Group 3: System Maintenance (independent)
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

    # Start the playground with all task groups
    async with playground.play(workers=workers) as active_playground:
        await active_playground.assign_task_groups([
            data_group,
            reporting_group,
            maintenance_group
        ])

        # Wait for all groups to complete
        while len(active_playground.completed_groups) < 3:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
