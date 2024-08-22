import pickle

from loguru import logger

from ceylon import Agent
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT


class AgentMonitor(Agent):

    def __init__(self, name="monitor",
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_port=DEFAULT_WORKSPACE_PORT,
                 admin_peer="",
                 role="worker"):
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_port=admin_port,
            admin_peer=admin_peer,
            role=role if role else name
        )

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        logger.info((agent_id, data, time))
