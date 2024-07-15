import asyncio

from ceylon.ceylon import AdminAgent, AdminAgentConfig, Processor, MessageHandler


class Admin(AdminAgent, Processor, MessageHandler):

    def __init__(self, name="admin", port=8888):
        super().__init__(config=AdminAgentConfig(name=name, port=port), processor=self, on_message=self)

    async def run(self, inputs: "bytes"):
        while True:
            await asyncio.sleep(1)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(agent_id, data, time)
