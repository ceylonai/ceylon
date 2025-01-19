#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
import pickle
from typing import Any, Dict, List, Optional

from loguru import logger

from ceylon import AdminAgent, Processor, MessageHandler, EventHandler, AdminAgentConfig, WorkerAgent
from ceylon.ceylon.ceylon import uniffi_set_event_loop, AgentDetail, WorkerAgentConfig
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_CONF_FILE, DEFAULT_WORKSPACE_PORT, DEFAULT_WORKSPACE_IP, \
    DEFAULT_WORKSPACE_BUFFER_SIZE


class Admin(AdminAgent, Processor, MessageHandler, EventHandler):
    def __init__(self, name="admin", port=8888, buffer_size=DEFAULT_WORKSPACE_BUFFER_SIZE):
        self.return_response = None
        self.connected_agents: Dict[str, AgentDetail] = {}
        super().__init__(config=AdminAgentConfig(name=name, port=port, buffer_size=buffer_size),
                         processor=self,
                         on_message=self,
                         on_event=self)

    async def arun_admin(self, inputs: bytes, workers):
        uniffi_set_event_loop(asyncio.get_event_loop())
        await self.start(inputs, workers)
        return self.return_response

    def run_admin(self, inputs: bytes, workers):
        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            return event_loop.run_until_complete(self.arun_admin(inputs, workers))

        if event_loop.is_running():
            future = asyncio.ensure_future(self.arun_admin(inputs, workers), loop=event_loop)
            return event_loop.run_until_complete(future)
        else:
            return asyncio.run(self.arun_admin(inputs, workers))

    async def broadcast_data(self, message: Any):
        await self.broadcast(pickle.dumps(message))

    async def send_direct_data(self, peer_id: str, message: Any):
        await self.send_direct(peer_id, pickle.dumps(message))

    def get_connected_agents(self) -> List[AgentDetail]:
        return list(self.connected_agents.values())

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentDetail]:
        return self.connected_agents.get(agent_id)

    def get_agents_by_role(self, role: str) -> List[AgentDetail]:
        return [agent for agent in self.connected_agents.values() if agent.role == role]

    async def run(self, inputs: bytes):
        pass

    async def on_message(self, agent_id: str, data: bytes, time: int):
        pass

    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        self.connected_agents[agent.id] = agent
        logger.info(f"Agent connected: {agent.name} ({agent.id}) - Role: {agent.role}")

    async def on_agent_disconnected(self, topic: str, agent: AgentDetail):
        if agent.id in self.connected_agents:
            del self.connected_agents[agent.id]
            logger.info(f"Agent disconnected: {agent.name} ({agent.id})")


class Worker(WorkerAgent, Processor, MessageHandler, EventHandler):
    agent_type = "WORKER"

    def __init__(self, name="worker",
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 conf_file=DEFAULT_CONF_FILE,
                 admin_peer="",
                 admin_port=DEFAULT_WORKSPACE_PORT,
                 role="worker",
                 admin_ip=DEFAULT_WORKSPACE_IP,
                 buffer_size=DEFAULT_WORKSPACE_BUFFER_SIZE
                 ):
        super().__init__(config=WorkerAgentConfig(
            name=name,
            role=role,
            conf_file=conf_file,
            admin_peer=admin_peer,
            admin_port=admin_port,
            work_space_id=workspace_id,
            admin_ip=admin_ip,
            buffer_size=buffer_size
        ),
            processor=self,
            on_message=self,
            on_event=self)
        self.admin_id = admin_peer

    async def arun_worker(self, inputs: bytes):
        uniffi_set_event_loop(asyncio.get_event_loop())
        await self.start(inputs)

    def run_worker(self, inputs: bytes):
        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            return event_loop.run_until_complete(self.arun_worker(inputs))

        if event_loop.is_running():
            future = asyncio.ensure_future(self.arun_worker(inputs), loop=event_loop)
            return event_loop.run_until_complete(future)
        else:
            return asyncio.run(self.arun_worker(inputs))

    async def broadcast_data(self, message: Any):
        await self.broadcast(pickle.dumps(message))

    async def send_direct_data(self, peer_id: str, message: Any):
        await self.send_direct(peer_id, pickle.dumps(message))

    async def run(self, inputs: bytes):
        pass

    async def on_message(self, agent_id: str, data: bytes, time: int):
        pass

    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        pass
