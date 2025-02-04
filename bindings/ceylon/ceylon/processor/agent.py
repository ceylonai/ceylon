#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import dataclasses
import uuid
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict

from ceylon import Worker, on


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


@dataclass
class ProcessResponse:
    request_id: str
    result: Any
    status: ProcessState = ProcessState.PENDING  # 'success' or 'error'
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class ProcessWorker(Worker):
    def __init__(self, name: str, role: str):
        super().__init__(name=name, role=role)

    @on(ProcessRequest)
    async def handle_request(self, request: ProcessRequest, time: int):
        try:
            start_time = datetime.now()
            # Process the request (example implementation)
            try:
                result = await self._processor(request, time)
                status = ProcessState.SUCCESS
                error_message = None
            except Exception as e:
                result = None
                status = ProcessState.ERROR
                error_message = str(e)
            # Send response
            response = ProcessResponse(
                request_id=request.id,
                result=result,
                status=status,
                error_message=error_message,
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            await self.broadcast_message(response)

        except Exception as e:
            # Handle errors
            error_response = ProcessResponse(
                request_id=request.id,
                result=None,
                status="error",
                error_message=str(e)
            )
            await self.broadcast_message(error_response)

    @abstractmethod
    async def _processor(self, request: ProcessRequest, time: int):
        await self.handle_request(request, time)
