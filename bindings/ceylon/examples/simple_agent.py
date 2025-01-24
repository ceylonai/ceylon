#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import pickle
import random

from ceylon import BaseAgent
from ceylon import PeerMode
from ceylon import enable_log

enable_log("INFO")


class AdminAgent(BaseAgent):

    async def on_agent_connected(self, topic: "str", agent: "AgentDetail"):
        logger.info(f"Agent connected: {agent.name} ({agent.id}) - Role: {agent.role}")

    async def on_message(self, agent_id: str, data: bytes, time: int):
        logger.info(f"Received message from {agent_id}: {data}")


class WorkerAgent(BaseAgent):
    async def on_agent_connected(self, topic: "str", agent: "AgentDetail"):
        logger.info(f"Worker connected: {agent.name} ({agent.id}) - Role: {agent.role}")

    async def run(self, inputs: bytes) -> None:
        logger.info(f"Worker started - {self.details().name} ({self.details().id})")
        while True:
            logger.info(f"Worker running - {self.details().name} ({self.details().id})")
            await self.broadcast_message({"type": "worker_status", "name": self.details().name, "messages_received": 1})
            await asyncio.sleep(1)


async def main():
    admin = AdminAgent(
        port=8855,
        mode=PeerMode.ADMIN,
        name="admin"
    )
    worker = WorkerAgent(
        name="worker",
        mode=PeerMode.CLIENT
    )
    await admin.start_agent(b"", [worker])


#
# if __name__ == '__main__':
#     asyncio.run(main())


import asyncio

from ceylon.base.agents import Admin, Worker
from loguru import logger


class AgentManager(Admin):

    def __init__(self):
        super().__init__(
            name="admin",
            port=7555
        )
        self.agent = None

    async def run(self, inputs: bytes):
        while True:
            logger.info("running")
            await self.broadcast_message({"type": "admin_status", "name": self.details().name, "messages_received": 1})
            await asyncio.sleep(random.randint(1, 10))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        logger.info(f"{self.details().name} Received message from {agent_id}: {pickle.loads(data)}")


class SupportAgent(Worker):

    async def run(self, inputs: bytes):
        while True:
            logger.info("running worker")
            await self.broadcast_message({"type": "worker_status", "name": self.details().name, "messages_received": 1})
            await asyncio.sleep(random.randint(1, 10))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        logger.info(f"{self.details().name} Received message from {agent_id}: {pickle.loads(data)}")


class ClarkAgent(Worker):

    async def run(self, inputs: bytes):
        while True:
            logger.info("running worker")
            await self.broadcast_message({"type": "worker_status", "name": self.details().name, "messages_received": 1})
            await asyncio.sleep(random.randint(1, 10))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        logger.info(f"{self.details().name} Received message from {agent_id}: {pickle.loads(data)}")


if __name__ == '__main__':
    asyncio.run(AgentManager().start_agent(b"", [
        SupportAgent(
            name="support",
            role="support"),
        SupportAgent(
            name="support2",
            role="support2"),
        ClarkAgent(
            name="ClarkAgent",
            role="ClarkAgent")

    ]))
