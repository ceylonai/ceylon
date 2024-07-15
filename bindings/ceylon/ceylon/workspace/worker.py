import asyncio
import pickle

from ceylon.ceylon import AdminAgent, AdminAgentConfig, enable_log, WorkerAgent, WorkerAgentConfig


class Worker(WorkerAgent):

    def __init__(self, name="admin", workspace_id="admin", admin_peer=None, admin_port=8888):
        super().__init__(config=WorkerAgentConfig(name=name,
                                                  admin_peer=admin_peer,
                                                  admin_port=admin_port,
                                                  work_space_id=workspace_id))
