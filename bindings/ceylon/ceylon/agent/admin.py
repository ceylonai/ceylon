import enum
import time
from typing import List

from loguru import logger
from pydantic import BaseModel

from .common import AgentCommon
from ceylon.ceylon import AgentDetail
from ceylon.core.admin import Admin


class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    connected_timestamp: float


class AgentDetails(BaseModel):
    agents: List[AgentInfo] = []


class CoreAdmin(Admin, AgentCommon):
    def __init__(self, name, port, workers=None, server_mode=False):
        if workers is None:
            workers = []
        self.__server_mode = server_mode
        self.__workers = workers
        self.__connected_agents = []
        super().__init__(name, port)
        AgentCommon.__init__(self)

    async def run(self, inputs: "bytes"):
        logger.info((f"Admin on_run  {self.details().id}", inputs))
        pass

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        # remove agent list has the same id or name
        self.__connected_agents = [x for x in self.__connected_agents if x.id != agent.id]
        self.__connected_agents = [x for x in self.__connected_agents if x.name != agent.name]
        self.__connected_agents.append(
            AgentInfo(id=agent.id, name=agent.name, role=agent.role, connected_timestamp=time.time()))
        await self.broadcast_data(AgentDetails(agents=self.__connected_agents))

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        await self._on_message_handler(agent_id, data, time)
