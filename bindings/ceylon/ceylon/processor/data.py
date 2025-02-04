#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import dataclasses
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Dict


class ProcessState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class ProcessRequest:
    task_type: str
    data: Any
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Optional[Dict[str, Any]] = None
    dependency_data: Optional[Dict[str, Any]] = None


@dataclass
class ProcessResponse:
    request_id: str
    result: Any
    status: ProcessState = ProcessState.PENDING  # 'success' or 'error'
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
