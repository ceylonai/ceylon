#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
#
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Callable, Coroutine, Set


class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TaskResult:
    success: bool
    output: Any = None
    error: str = None


@dataclass
class Task:
    name: str
    processor: Callable[..., Coroutine] | str = None  # Updated to expect a coroutine
    input_data: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: TaskResult = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class TaskRequest:
    task_id: str
    task_type: str
    data: Any
    metadata: Dict[str, Any] = None


@dataclass
class TaskResponse:
    task_id: str
    result: Any
    status: str  # 'success' or 'error'
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
