#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
#
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Set, List, Dict, Callable


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
    id : str = field(default_factory=lambda: str(uuid.uuid4()))
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


class GoalStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"


@dataclass
class TaskGroupGoal:
    name: str
    description: str
    check_condition: Callable[[Dict[str, TaskGroup], Dict[str, TaskMessage]], bool]
    success_message: str
    failure_message: str
    status: GoalStatus = GoalStatus.NOT_STARTED
    dependent_groups: List[str] = None  # List of group IDs this goal depends on
