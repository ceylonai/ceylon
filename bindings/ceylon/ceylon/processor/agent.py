#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

from abc import abstractmethod
from datetime import datetime

from ceylon import Worker, on
from ceylon.processor.data import ProcessResponse, ProcessRequest, ProcessState


class ProcessWorker(Worker):
    def __init__(self, name: str, role: str):
        super().__init__(name=name, role=role)

    @on(ProcessRequest)
    async def handle_request(self, request: ProcessRequest, time: int):
        try:
            if request.task_type != self.details().role:
                return
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
                status=ProcessState.ERROR,
                error_message=str(e)
            )
            await self.broadcast_message(error_response)

    @abstractmethod
    async def _processor(self, request: ProcessRequest, time: int):
        await self.handle_request(request, time)
