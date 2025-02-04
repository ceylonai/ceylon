#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
from typing import Dict

from loguru import logger

from ceylon import on
from ceylon.base.playground import BasePlayGround
from ceylon.processor.data import ProcessResponse, ProcessRequest, ProcessState


class ProcessPlayGround(BasePlayGround):
    def __init__(self, name="task_playground", port=8888):
        super().__init__(name=name, port=port)
        self.process_responses: Dict[str, ProcessResponse] = {}
        self.process_events: Dict[str, asyncio.Event] = {}
        self.process_progress: Dict[str, float] = {}

    @on(ProcessResponse)
    async def handle_process_response(self, response: ProcessResponse, time: int):
        """Handle task completion responses from workers"""
        logger.info(f"Received task response for {response.request_id}")
        self.process_responses[response.request_id] = response
        if response.request_id in self.process_events and (
                response.status != ProcessState.PENDING or response.status != ProcessState.PROCESSING):
            self.process_events[response.request_id].set()

    async def process_request(self, request: ProcessRequest, wait_for_completion=True) -> ProcessResponse or None:
        await self.broadcast_message(request)
        if wait_for_completion:
            event = asyncio.Event()
            self.process_events[request.id] = event
            await event.wait()
            # Cleanup
            self.process_events.pop(request.id)
            return self.process_responses[request.id]
