import asyncio
from typing import List, Mapping, Dict, Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel

from ceylon import Admin, UnifiedAgent, AgentDetail, on, on_connect, BaseAgent


class AgentConnectedStatus(BaseModel):
    agent: AgentDetail
    connected: bool

    class Config:
        arbitrary_types_allowed = True


class PlayGround(Admin):
    def __init__(self, name="playground", port=8888):
        super().__init__(name=name, port=port, role="playground")
        self.llm_agents: Dict[str, AgentConnectedStatus] = {}
        self._connected_event = None

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
            self._connected_event = None
            await self.stop()
