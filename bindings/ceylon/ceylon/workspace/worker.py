from ceylon.ceylon import WorkerAgent, WorkerAgentConfig, Processor, \
    MessageHandler


class Worker(WorkerAgent, Processor, MessageHandler):

    def __init__(self, name="admin", workspace_id="admin", admin_peer=None, admin_port=8888, role="worker"):
        super().__init__(config=WorkerAgentConfig(name=name,
                                                  role=role,
                                                  admin_peer=admin_peer,
                                                  admin_port=admin_port,
                                                  work_space_id=workspace_id), processor=self, on_message=self)

    async def run(self, inputs: "bytes"):
        pass

    def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        pass

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        pass
