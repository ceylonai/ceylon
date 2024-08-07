from loguru import logger

from .common import AgentCommon
from ceylon.ceylon import AgentDetail
from ceylon.core.admin import Admin


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
        self.__connected_agents.append(agent)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        await self._on_message_handler(agent_id, data, time)
