#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import pickle
from typing import Optional, List, Dict, Any

from loguru import logger
from mkdocs.commands.new import config_text

from ceylon import Processor, MessageHandler, EventHandler, AgentDetail
from ceylon.ceylon import PeerMode, UnifiedAgent, UnifiedAgentConfig
from ceylon.ceylon.ceylon import uniffi_set_event_loop


class UnifiedAgentHandler(Processor, MessageHandler, EventHandler):
    """
    A unified handler for different agent types in Ceylon framework.
    Supports both admin and worker agent modes.
    """

    def __init__(
            self,
            name: str,
            mode: PeerMode,
            role: str = "default",
            port: Optional[int] = None,
            admin_peer: Optional[str] = None,
            admin_ip: Optional[str] = None,
            workspace_id: str = "default",
            buffer_size: int = 1024,
            config_path: Optional[str] = None
    ):
        self.name = name
        self.mode = mode
        self.role = role
        self.port = port
        self.admin_peer = admin_peer
        self.admin_ip = admin_ip
        self.workspace_id = workspace_id
        self.buffer_size = buffer_size
        self.config_path = config_path

        # Initialize storage for connected agents
        self.connected_agents: Dict[str, AgentDetail] = {}
        self.agent: Optional[UnifiedAgent] = None

        # Create appropriate agent configuration
        if self.mode == PeerMode.ADMIN:
            self._setup_admin_agent()
        else:
            self._setup_worker_agent()

    def _setup_admin_agent(self) -> None:
        """Setup agent in admin mode"""
        config = UnifiedAgentConfig(
            name=self.name,
            port=self.port or 8888,
            buffer_size=self.buffer_size,
            mode=PeerMode.ADMIN,
            role=self.role,
            work_space_id=self.name if self.workspace_id is None else self.workspace_id,
            admin_peer=None,
            admin_ip=self.admin_ip or "127.0.0.1",
        )

        self.agent = UnifiedAgent(
            config=config,
            config_path=None,
            processor=self,
            on_message=self,
            on_event=self
        )

    def _setup_worker_agent(self) -> None:
        """Setup agent in worker mode"""
        config = UnifiedAgentConfig(
            name=self.name,
            mode=PeerMode.CLIENT,
            role=self.role,
            port=None,
            buffer_size=self.buffer_size,
            work_space_id=None,
            admin_peer=None,
            admin_ip=None,
        )
        self.agent = UnifiedAgent(
            config=config,
            config_path=None,
            processor=self,
            on_message=self,
            on_event=self
        )

    async def start(self, inputs: bytes = b"", workers: Optional[List[UnifiedAgent]] = None) -> None:

        uniffi_set_event_loop(asyncio.get_event_loop())
        """Start the agent"""
        if not self.agent:
            raise RuntimeError("Agent not initialized")

        logger.info(f"Starting {self.name} agent in {self.mode.name} mode")
        await self.agent.start(inputs, workers)

    async def stop(self) -> None:
        """Stop the agent"""
        if not self.agent:
            raise RuntimeError("Agent not initialized")

        logger.info(f"Stopping {self.name} agent")
        await self.agent.stop()

    async def broadcast(self, message: Any) -> None:
        """Broadcast a message to all connected agents"""
        if not self.agent:
            raise RuntimeError("Agent not initialized")

        message_bytes = pickle.dumps(message)
        await self.agent.broadcast(message_bytes)

    async def send_direct(self, peer_id: str, message: Any) -> None:
        """Send a message directly to a specific peer"""
        if not self.agent:
            raise RuntimeError("Agent not initialized")

        message_bytes = pickle.dumps(message)
        await self.agent.send_direct(peer_id, message_bytes)

    def get_agent_details(self) -> AgentDetail:
        """Get details about the current agent"""
        if not self.agent:
            raise RuntimeError("Agent not initialized")

        return self.agent.details()

    def get_connected_agents(self) -> List[AgentDetail]:
        """Get list of all connected agents"""
        return list(self.connected_agents.values())

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentDetail]:
        """Get agent details by ID"""
        return self.connected_agents.get(agent_id)

    def get_agents_by_role(self, role: str) -> List[AgentDetail]:
        """Get all agents with a specific role"""
        return [
            agent for agent in self.connected_agents.values()
            if agent.role == role
        ]

    # Processor interface implementation
    async def run(self, inputs: bytes) -> None:
        """Process incoming data"""
        try:
            data = pickle.loads(inputs)
            logger.debug(f"Processing data: {data}")
            # Implement your processing logic here
        except Exception as e:
            logger.error(f"Error processing data: {e}")

    # MessageHandler interface implementation
    async def on_message(self, agent_id: str, data: bytes, time: int) -> None:
        """Handle incoming messages"""
        try:
            message = pickle.loads(data)
            logger.debug(f"Received message from {agent_id}: {message}")
            # Implement your message handling logic here
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    # EventHandler interface implementation
    async def on_agent_connected(self, topic: str, agent: AgentDetail) -> None:
        """Handle agent connection events"""
        self.connected_agents[agent.id] = agent
        logger.info(f"Agent connected: {agent.name} ({agent.id}) - Role: {agent.role}")
