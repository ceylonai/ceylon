#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio

from loguru import logger

from ceylon import enable_log
from ceylon.base.uni_agent import BaseAgent
from ceylon.ceylon import PeerMode

# enable_log("INFO")


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


if __name__ == '__main__':
    asyncio.run(main())
