import pickle

from loguru import logger

from ceylon import CoreAdmin, Agent
from ceylon.ceylon import AgentDetail


class ServerAdminAgent(CoreAdmin):

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        logger.info((f"ServerAdminAgent on_agent_connected {self.details().name}", agent.id, agent.name, agent.role))


class WorkerAgent1(Agent):

    async def run(self, inputs: "bytes"):
        logger.info((f"WorkerAgent1 on_run  {self.details().name}", inputs))


worker_1 = WorkerAgent1("worker_1", "server_admin", admin_port=8000)

server_admin = ServerAdminAgent("server_admin", 8000, workers=[worker_1])

# enable_log("info")
server_admin.run_admin(pickle.dumps({}), [worker_1])
