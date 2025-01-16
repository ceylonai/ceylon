import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


# Ceylon namespace implementation
class Ceylon:
    
    @staticmethod
    def version() -> str:
        return "1.0.0"

    @staticmethod
    def enable_log(level: str) -> None:
        # Implement logging configuration
        import logging
        logging.basicConfig(level=level.upper())

    @staticmethod
    def cprint(message: str) -> None:
        print(f"[Ceylon] {message}")

# Data classes for configuration
@dataclass
class AdminAgentConfig:
    name: str
    port: int

@dataclass
class WorkerAgentConfig:
    name: str
    conf_file: Optional[str]
    work_space_id: str
    admin_peer: str
    role: str
    admin_port: int
    admin_ip: str

    def __post_init__(self):
        self.conf_file = self.conf_file or ".ceylon_network"

@dataclass
class AgentDetail:
    name: str
    id: str
    role: str

# Abstract base classes for handlers
class MessageHandler(ABC):
    @abstractmethod
    async def on_message(self, agent_id: str, data: bytes, time: int) -> None:
        pass

class Processor(ABC):
    @abstractmethod
    async def run(self, inputs: bytes) -> None:
        pass

class EventHandler(ABC):
    @abstractmethod
    async def on_agent_connected(self, topic: str, agent: AgentDetail) -> None:
        pass

# Base Agent class with common functionality
class BaseAgent:
    def __init__(self, message_handler: MessageHandler, processor: Processor, event_handler: EventHandler):
        self.message_handler = message_handler
        self.processor = processor
        self.event_handler = event_handler
        self.running = False
        self._agent_detail = None

    async def _handle_message(self, agent_id: str, data: bytes):
        await self.message_handler.on_message(agent_id, data, int(time.time()))

    async def broadcast(self, message: bytes):
        raise NotImplementedError()

    def details(self) -> AgentDetail:
        return self._agent_detail

# AdminAgent implementation
class AdminAgent(BaseAgent):
    def __init__(self, config: AdminAgentConfig, message_handler: MessageHandler,
                 processor: Processor, event_handler: EventHandler):
        super().__init__(message_handler, processor, event_handler)
        self.config = config
        self._agent_detail = AgentDetail(
            name=config.name,
            id=f"admin_{config.name}_{config.port}",
            role="admin"
        )
        self.workers: List[WorkerAgent] = []

    async def start(self, inputs: bytes, workers: List['WorkerAgent']):
        if self.running:
            return

        self.workers = workers
        self.running = True

        # Process inputs
        await self.processor.run(inputs)

        # Start listening for messages
        await self._start_message_handler()

        Ceylon.cprint(f"AdminAgent {self.config.name} started on port {self.config.port}")

    async def stop(self):
        if not self.running:
            return

        self.running = False
        # Cleanup and stop message handling
        await self._cleanup()

        Ceylon.cprint(f"AdminAgent {self.config.name} stopped")

    async def broadcast(self, message: bytes):
        if not self.running:
            return

        # Broadcast message to all workers
        for worker in self.workers:
            try:
                await worker._handle_message(self._agent_detail.id, message)
            except Exception as e:
                Ceylon.cprint(f"Error broadcasting to worker {worker.details().id}: {e}")

    async def _start_message_handler(self):
        # Implementation for message handling setup
        pass

    async def _cleanup(self):
        # Cleanup resources
        pass

# WorkerAgent implementation
class WorkerAgent(BaseAgent):
    def __init__(self, config: WorkerAgentConfig, message_handler: MessageHandler,
                 processor: Processor, event_handler: EventHandler):
        super().__init__(message_handler, processor, event_handler)
        self.config = config
        self._agent_detail = AgentDetail(
            name=config.name,
            id=f"worker_{config.name}_{config.work_space_id}",
            role=config.role
        )
        self._admin_connection = None

    async def start(self, inputs: bytes):
        if self.running:
            return

        self.running = True

        # Connect to admin
        await self._connect_to_admin()

        # Process inputs
        await self.processor.run(inputs)

        # Start listening for messages
        await self._start_message_handler()

        Ceylon.cprint(f"WorkerAgent {self.config.name} started and connected to admin")

    async def stop(self):
        if not self.running:
            return

        self.running = False
        # Cleanup and stop message handling
        await self._cleanup()

        Ceylon.cprint(f"WorkerAgent {self.config.name} stopped")

    async def broadcast(self, message: bytes):
        if not self.running or not self._admin_connection:
            return

        # Send message to admin
        try:
            # Implementation for sending message to admin
            await self._send_to_admin(message)
        except Exception as e:
            Ceylon.cprint(f"Error broadcasting from worker {self._agent_detail.id}: {e}")

    async def _connect_to_admin(self):
        # Implementation for connecting to admin agent
        pass

    async def _start_message_handler(self):
        # Implementation for message handling setup
        pass

    async def _cleanup(self):
        # Cleanup resources
        pass

    async def _send_to_admin(self, message: bytes):
        # Implementation for sending message to admin
        pass

# Example implementation of handlers
class DefaultMessageHandler(MessageHandler):
    async def on_message(self, agent_id: str, data: bytes, time: int) -> None:
        Ceylon.cprint(f"Received message from {agent_id} at {time}: {data.decode()}")

class DefaultProcessor(Processor):
    async def run(self, inputs: bytes) -> None:
        Ceylon.cprint(f"Processing inputs: {inputs.decode()}")

class DefaultEventHandler(EventHandler):
    async def on_agent_connected(self, topic: str, agent: AgentDetail) -> None:
        Ceylon.cprint(f"Agent {agent.id} connected to topic {topic}")

# Example usage:
async def main():
    # Create handlers
    message_handler = DefaultMessageHandler()
    processor = DefaultProcessor()
    event_handler = DefaultEventHandler()

    # Create admin agent
    admin_config = AdminAgentConfig(name="admin1", port=8000)
    admin_agent = AdminAgent(admin_config, message_handler, processor, event_handler)

    # Create worker agents
    worker_configs = [
        WorkerAgentConfig(
            name="worker1",
            conf_file=None,
            work_space_id="ws1",
            admin_peer="admin1",
            role="worker",
            admin_port=8000,
            admin_ip="localhost"
        )
    ]

    workers = [
        WorkerAgent(config, message_handler, processor, event_handler)
        for config in worker_configs
    ]

    # Start agents
    await admin_agent.start(b"admin_inputs", workers)
    for worker in workers:
        await worker.start(b"worker_inputs")

    # Example broadcast
    await admin_agent.broadcast(b"Hello from admin!")
    await workers[0].broadcast(b"Hello from worker!")

    # Stop agents
    await admin_agent.stop()
    for worker in workers:
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main())