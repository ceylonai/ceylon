import asyncio

from ceylon.ceylon import AdminAgent, AdminAgentConfig, Processor, MessageHandler, EventHandler
from ceylon.ceylon.ceylon import uniffi_set_event_loop


class Admin(AdminAgent, Processor, MessageHandler, EventHandler):

    def __init__(self, name="admin", port=8888):
        self.return_response = None
        super().__init__(config=AdminAgentConfig(name=name, port=port), processor=self, on_message=self, on_event=self)

    async def run(self, inputs: "bytes"):
        pass

    #
    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        pass

    def run_admin(self, inputs: "bytes", workers):
        import asyncio
        return asyncio.run(self.arun_admin(inputs, workers))

    async def arun_admin(self, inputs: "bytes", workers):
        uniffi_set_event_loop(asyncio.get_event_loop())
        await self.start(inputs, workers)
        return self.return_response

        #

    async def execute_task(self, input):
        pass

    async def on_agent_connected(self, topic: "str", agent_id: "str"):
        pass
