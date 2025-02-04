#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
#
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


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
