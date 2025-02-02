#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from __future__ import annotations

import asyncio
from typing import List, Mapping, Dict, Optional, TypeVar, Sequence
from contextlib import asynccontextmanager
from pydantic import BaseModel

from ceylon import Admin, UnifiedAgent, AgentDetail, on, on_connect, BaseAgent, Worker


class AgentConnectedStatus(BaseModel):
    agent: AgentDetail
    connected: bool

    class Config:
        arbitrary_types_allowed = True


class BasePlayGround(Admin):
    def __init__(self, name="playground", port=8888):
        super().__init__(name=name, port=port, role="playground")
        self.llm_agents: Dict[str, AgentConnectedStatus] = {}
        self._connected_event = None
        self._stop_event = None

    async def finish(self) -> None:
        if self._stop_event:
            self._stop_event.set()

    @on_connect("*")
    async def on_llm_agent_connected(self, topic: str, agent: AgentDetail):
        self.llm_agents[agent.name] = AgentConnectedStatus(agent=agent, connected=True)
        if self._connected_event and all(status.connected for status in self.llm_agents.values()):
            self._connected_event.set()

    @asynccontextmanager
    async def play(self, workers: Optional[List[BaseAgent]] = None):
        """
        Async context manager for the playground that ensures all agents are connected before proceeding.
        
        Args:
            workers: Optional list of BaseAgent instances to start
            
        Yields:
            PlayGround: The playground instance with all agents connected
        """
        from asyncio import Event

        # Initialize connection event
        self._connected_event = Event()
        self._stop_event = Event()

        # Initialize agent statuses
        if workers:
            for agent in workers:
                self.llm_agents[agent.name] = AgentConnectedStatus(
                    agent=agent.details(),
                    connected=False
                )

        try:
            # Start the agent and wait for all connections
            asyncio.create_task(self.start_agent(workers=workers))
            await self._connected_event.wait()

            yield self

        finally:
            # Cleanup
            await self._stop_event.wait()
            self._connected_event = None
            self._stop_event = None
            await self.stop()
