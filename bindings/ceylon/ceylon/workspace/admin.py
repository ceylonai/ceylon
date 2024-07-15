import asyncio

from ceylon.ceylon import AdminAgent, AdminAgentConfig, Processor, MessageHandler, uniffi_set_event_loop


class Admin(AdminAgent, Processor, MessageHandler):

    def __init__(self, name="admin", port=8888):
        print("Admin initialized")
        super().__init__(config=AdminAgentConfig(name=name, port=port), processor=self, on_message=self)

    async def run(self, inputs: "bytes"):
        print("Admin running")
        # while True:
        #     await self.broadcast(pickle.dumps({
        #         "hello": "world from admin"
        #     }))
        #     await asyncio.sleep(1)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(agent_id, data, time)

    async def run_admin(self, inputs, workers):
        uniffi_set_event_loop(asyncio.get_event_loop())
        await self.start(inputs, workers)

#
