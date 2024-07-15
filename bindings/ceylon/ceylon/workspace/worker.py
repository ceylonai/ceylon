import asyncio
import pickle

from ceylon.ceylon import AdminAgent, AdminAgentConfig, enable_log, WorkerAgent, WorkerAgentConfig, Processor, \
    MessageHandler


class Worker(WorkerAgent, Processor, MessageHandler):

    def __init__(self, name="admin", workspace_id="admin", admin_peer=None, admin_port=8888):
        super().__init__(config=WorkerAgentConfig(name=name,
                                                  admin_peer=admin_peer,
                                                  admin_port=admin_port,
                                                  work_space_id=workspace_id), processor=self, on_message=self)

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(1)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(agent_id, data, time)
