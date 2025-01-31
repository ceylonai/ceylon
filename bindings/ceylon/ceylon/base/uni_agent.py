import asyncio
import pickle
from typing import Optional, List, Dict, Any

from loguru import logger

from ceylon import (
    MessageHandler, EventHandler, Processor,
    AgentDetail
)
from ceylon.base.support import AgentCommon
from ceylon.ceylon import UnifiedAgent, PeerMode, UnifiedAgentConfig
from ceylon.ceylon.ceylon import uniffi_set_event_loop


class BaseAgentData(AgentDetail):

    @property
    def get_extra_data(self):
        if self.extra_data is None:
            return None
        return pickle.loads(self.extra_data)


class BaseAgent(UnifiedAgent, MessageHandler, EventHandler, Processor, AgentCommon):
    """
    Extended UnifiedAgent with additional functionality and built-in message/event handling.
    Inherits directly from UnifiedAgent and implements required handler interfaces.
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
            config_path: Optional[str] = None,
            extra_data: Optional[Any] = None
    ):
        # Create configuration
        config = UnifiedAgentConfig(
            name=name,
            mode=mode,
            role=role,
            port=port,
            buffer_size=buffer_size,
            work_space_id=workspace_id,
            admin_peer=admin_peer,
            admin_ip=admin_ip
        )

        _extra_data = None
        if extra_data is not None:
            _extra_data = pickle.dumps(extra_data)

        # Initialize UnifiedAgent with self as handlers
        super().__init__(
            config=config,
            config_path=config_path,
            processor=self,
            on_message=self,
            on_event=self,
            extra_data=_extra_data
        )
        AgentCommon.__init__(self)
        # super(AgentCommon, self).__init__()
        # Store initialization parameters
        self.name = name
        self.mode = mode
        self.role = role
        self.port = port
        self.admin_peer = admin_peer
        self.admin_ip = admin_ip
        self.workspace_id = workspace_id
        self.buffer_size = buffer_size

        # Initialize agent storage
        self.connected_agents: Dict[str, AgentDetail] = {}
        self._message_handlers: List[callable] = []
        self._event_handlers: List[callable] = []

    async def start_agent(self, inputs: bytes = b"", workers: Optional[List[UnifiedAgent]] = None) -> None:
        uniffi_set_event_loop(asyncio.get_event_loop())
        """
        Start the agent. Wrapper around the base start() method for clarity.
        """
        logger.info(f"Starting {self.name} agent in {self.mode.name} mode")
        await self.start(inputs, workers)

    async def broadcast_message(self, message: Any) -> None:
        """
        Broadcast a message to all connected agents with automatic serialization.
        """
        try:
            if not isinstance(message, bytes):
                message = pickle.dumps(message)
            await self.broadcast(message)
            # logger.debug(f"Broadcast message sent: {message}")
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")

    async def send_message(self, peer_id: str, message: Any) -> None:
        """
        Send a direct message to a specific peer with automatic serialization.
        """
        try:
            if not isinstance(message, bytes):
                message = pickle.dumps(message)
            await self.send_direct(peer_id, message)
        except Exception as e:
            logger.error(f"Error sending direct message: {e}")

    # def get_connected_agents(self) -> List[AgentDetail]:
    #     """Get list of all connected agents"""
    #     return list(self.connected_agents.values())

    def get_agent_by_id(self, agent_id: str) -> Optional[AgentDetail]:
        """Get agent details by ID"""
        return self.connected_agents.get(agent_id)

    async def on_message(self, agent: BaseAgentData, data: "bytes", time: "int"):
        await self.common_on_message(agent, data, time)

    async def on_agent_connected(self, topic: "str", agent: BaseAgentData):
        await self.common_on_agent_connected(topic, agent)

    async def run(self, inputs: "bytes"):
        await self.common_on_run(inputs)

    # MessageHandler interface implementation
