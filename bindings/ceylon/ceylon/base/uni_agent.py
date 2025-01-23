import asyncio
import pickle
from typing import Optional, List, Dict, Any

from loguru import logger

from ceylon import (
    MessageHandler, EventHandler, Processor,
    AgentDetail
)
from ceylon.ceylon import UnifiedAgent, PeerMode, UnifiedAgentConfig
from ceylon.ceylon.ceylon import uniffi_set_event_loop


class BaseAgent(UnifiedAgent, MessageHandler, EventHandler, Processor):
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
            config_path: Optional[str] = None
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

        # Initialize UnifiedAgent with self as handlers
        super().__init__(
            config=config,
            config_path=config_path,
            processor=self,
            on_message=self,
            on_event=self
        )

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

        self._handlers = {}
        self._run_handlers = {}
        self._connection_handlers = {}

    def add_handler(self, data_type, handler):
        if not hasattr(self, '_handlers'):
            self._handlers = {}
        self._handlers[data_type] = handler

    def add_run_handler(self, handler):
        if not hasattr(self, '_run_handlers'):
            self._run_handlers = {}
        self._run_handlers[f"{handler.__name__}"] = handler

    def add_connection_handler(self, topic, handler):
        if not hasattr(self, '_connection_handlers'):
            self._connection_handlers = {}
        self._connection_handlers[topic] = handler

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

    # MessageHandler interface implementation

    def on(self, data_type):
        def decorator(func):
            self.add_handler(data_type, func)
            return func

        return decorator

    def on_run(self):
        def decorator(func):
            self.add_run_handler(func)
            return func

        return decorator

    def on_connect(self, topic: str):
        def decorator(func):
            self.add_connection_handler(topic, func)
            return func

        return decorator

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            decoded_data = pickle.loads(data)
            data_type = type(decoded_data)

            if hasattr(self, '_handlers') and data_type in self._handlers:
                agent = self.get_agent_by_id(agent_id)
                await self._handlers[data_type](decoded_data, time, agent)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        try:
            if hasattr(self, '_connection_handlers'):
                # Handle wildcard first
                if '*' in self._connection_handlers:
                    await self._connection_handlers['*'](topic, agent)

                # Handle topic:role format
                for handler_pattern, handler in self._connection_handlers.items():
                    if handler_pattern == '*':
                        continue

                    if ':' in handler_pattern:
                        pattern_topic, pattern_role = handler_pattern.split(':')
                        if (pattern_topic == '*' or pattern_topic == topic) and \
                                (pattern_role == '*' or pattern_role == agent.role):
                            await handler(topic, agent)
                    elif handler_pattern == topic:
                        await handler(topic, agent)
        except Exception as e:
            logger.error(f"Error handling connection: {e}")

    async def run(self, inputs: bytes):
        try:
            decoded_input = pickle.loads(inputs) if inputs else None
            if hasattr(self, '_run_handlers'):
                all_runners = []
                for handler in self._run_handlers.values():
                    print(f"Running handler: {handler.__name__}")
                    await handler(decoded_input)
                    all_runners.append(asyncio.create_task(handler(decoded_input)))

                await asyncio.gather(*all_runners)
                # await self._handlers[data_type](decoded_input, 0, None)
        except Exception as e:
            logger.error(f"Error in run method: {e}")
