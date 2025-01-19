#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
import pickle

from loguru import logger

from ceylon import AgentDetail
from ceylon.base.agents import Admin, Worker
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_CONF_FILE, DEFAULT_WORKSPACE_PORT, DEFAULT_WORKSPACE_IP


class NetworkManager(Admin):
    def __init__(self, name="admin", port=8888):
        super().__init__(name=name, port=port)
        self.return_response = None

    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        await super().on_agent_connected(topic, agent)
        logger.info(f"Network Manager: New agent connected - {agent.name} ({agent.id})")

        # Send welcome message to the new agent
        welcome_msg = {
            "type": "welcome",
            "from": self.details().name,
            "to": agent.id,
            "message": f"Welcome {agent.name}!"
        }
        await self.send_direct_data(agent.id, welcome_msg)

        # Broadcast new agent arrival
        broadcast_msg = {
            "type": "system",
            "message": f"New agent joined: {agent.name}"
        }
        await self.broadcast_data(broadcast_msg)

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            message = pickle.loads(data)
            logger.info(f"Network Manager received message from {agent_id}: {message}")

            # Echo back to sender
            response = {
                "type": "echo",
                "original_message": message,
                "from_admin": True,
                "to": agent_id
            }
            await self.send_direct_data(agent_id, response)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def run(self, inputs: bytes):
        logger.info(f"Network Manager started - {self.details().name} ({self.details().id})")
        while True:
            connected_agents = self.get_connected_agents()
            if connected_agents:
                status_msg = {
                    "type": "status",
                    "connected_agents": len(connected_agents)
                }
                await self.broadcast_data(status_msg)
            await asyncio.sleep(30)


class WorkingAgent(Worker):
    def __init__(self, name="worker",
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 conf_file=DEFAULT_CONF_FILE,
                 admin_peer="",
                 admin_port=DEFAULT_WORKSPACE_PORT,
                 role="worker",
                 admin_ip=DEFAULT_WORKSPACE_IP):
        super().__init__(name=name,
                         workspace_id=workspace_id,
                         conf_file=conf_file,
                         admin_peer=admin_peer,
                         admin_port=admin_port,
                         role=role,
                         admin_ip=admin_ip)
        self.message_count = 0

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            message = pickle.loads(data)
            logger.info(f"Worker {self.details().name}:{self.details().id} received message from {agent_id}: {message}")

            # Respond to direct messages
            if isinstance(message, dict) and message.get('type') == 'welcome':
                response = {
                    "type": "greeting",
                    "from": self.details().name,
                    "to": agent_id,
                    "message": f"Thanks for the welcome! From {self.details().name}"
                }
                await self.send_direct_data(agent_id, response)

            self.message_count += 1

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        logger.info(f"Worker {self.details().name}: New agent connected - {agent.name} ({agent.id})")

        # Send greeting to new agent
        greeting = {
            "type": "greeting",
            "from": self.details().name,
            "to": agent.id,
            "message": f"Hello {agent.name}!"
        }
        await self.send_direct_data(agent.id, greeting)

    async def run(self, inputs: bytes):
        logger.info(f"Worker started - {self.details().name} ({self.details().id})")
        while True:
            status = {
                "type": "worker_status",
                "name": self.details().name,
                "messages_received": self.message_count
            }
            await self.broadcast_data(status)
            await asyncio.sleep(60)


async def main():
    # Create network manager (admin)
    network_manager = NetworkManager()

    # Create worker agents
    worker_names = ["Alice", "Bob", "Charlie"]
    workers = []

    admin_details = network_manager.details()

    for name in worker_names:
        worker = WorkingAgent(
            name=name,
            admin_peer=admin_details.id
        )
        workers.append(worker)

    try:
        # Start the network
        await network_manager.arun_admin(b"", workers)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Cleanup code here if needed
        pass


if __name__ == "__main__":
    logger.info("Starting network test...")
    asyncio.run(main())
