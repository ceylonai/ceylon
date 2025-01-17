# agents.py
import asyncio
import json
from typing import List, Dict

import ceylon
from ceylon.base.agents import BaseMessageHandler, BaseProcessor, BaseEventHandler
from ceylon.ceylon.ceylon import uniffi_set_event_loop


class ChatMessageHandler(BaseMessageHandler):
    def __init__(self):
        self.messages: List[Dict] = []

    async def process_message(self, agent_id: str, message: dict, timestamp: int):
        formatted_msg = {
            "from": agent_id,
            "content": message,
            "time": timestamp,
        }
        self.messages.append(formatted_msg)
        print(f"Message from {agent_id}: {message}")


class ChatProcessor(BaseProcessor):
    async def process_data(self, input_data: dict):
        print(f"Processing input data: {input_data}")
        # Add your processing logic here
        await asyncio.sleep(0.1)  # Simulate some processing


class ChatEventHandler(BaseEventHandler):
    def __init__(self):
        self.connected_agents: Dict[str, ceylon.AgentDetail] = {}

    async def handle_agent_connected(self, topic: str, agent: ceylon.AgentDetail):
        self.connected_agents[agent.id] = agent
        print(f"Agent {agent.name} ({agent.id}) connected to topic {topic}")

    async def handle_agent_disconnected(self, topic: str, agent: ceylon.AgentDetail):
        if agent.id in self.connected_agents:
            del self.connected_agents[agent.id]
        print(f"Agent {agent.name} ({agent.id}) disconnected from topic {topic}")


class ChatAdminAgent:
    def __init__(self, name: str, port: int):
        self.config = ceylon.AdminAgentConfig(name=name, port=port)
        self.message_handler = ChatMessageHandler()
        self.processor = ChatProcessor()
        self.event_handler = ChatEventHandler()
        self.agent = ceylon.AdminAgent(
            self.config,
            self.message_handler,
            self.processor,
            self.event_handler
        )

    async def start(self, initial_data: dict, workers: List['ChatWorkerAgent']):
        uniffi_set_event_loop(asyncio.get_event_loop())
        try:
            worker_agents = [w.agent for w in workers]
            await self.agent.start(json.dumps(initial_data).encode('utf-8'), worker_agents)
        except Exception as e:
            print(f"Error starting admin agent: {e}")

    async def stop(self):
        await self.agent.stop()

    async def broadcast(self, message: dict):
        await self.agent.broadcast(json.dumps(message).encode('utf-8'))

    async def send_direct(self, peer_id: str, message: dict):
        await self.agent.send_direct(peer_id, json.dumps(message).encode('utf-8'))

    def get_connected_peers(self) -> List[ceylon.AgentDetail]:
        # TODO
        return self.agent.get_connected_peers()


class ChatWorkerAgent:
    def __init__(self, name: str, workspace_id: str, admin_peer: str, role: str, admin_port: int, admin_ip: str):
        self.config = ceylon.WorkerAgentConfig(
            name=name,
            work_space_id=workspace_id,
            admin_peer=admin_peer,
            role=role,
            admin_port=admin_port,
            admin_ip=admin_ip,
            conf_file=".ceylon_network"
        )
        self.message_handler = ChatMessageHandler()
        self.processor = ChatProcessor()
        self.event_handler = ChatEventHandler()
        self.agent = ceylon.WorkerAgent(
            self.config,
            self.message_handler,
            self.processor,
            self.event_handler
        )

    async def start(self, initial_data: dict):
        uniffi_set_event_loop(asyncio.get_event_loop())
        try:
            await self.agent.start(json.dumps(initial_data).encode('utf-8'))
        except Exception as e:
            print(f"Error starting worker agent: {e}")

    async def stop(self):
        await self.agent.stop()

    async def broadcast(self, message: dict):
        await self.agent.broadcast(json.dumps(message).encode('utf-8'))

    async def send_direct(self, peer_id: str, message: dict):
        await self.agent.send_direct(peer_id, json.dumps(message).encode('utf-8'))
