import asyncio
import pickle

from ceylon.ceylon import AdminAgent, AdminAgentConfig, Processor, MessageHandler, uniffi_set_event_loop, EventHandler
from ceylon.workspace.runner import RunnerInput


class Admin(AdminAgent, Processor, MessageHandler, EventHandler):

    def __init__(self, name="admin", port=8888):
        print("Admin initialized")
        super().__init__(config=AdminAgentConfig(name=name, port=port), processor=self, on_message=self, on_event=self)

    async def run(self, inputs: "bytes"):
        pass

    #
    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"Admin on_message  {self.details().name}", agent_id, data, time)

    async def run_admin(self, inputs, workers):
        uniffi_set_event_loop(asyncio.get_event_loop())
        runner_input = RunnerInput(request=inputs, agents=[], network={})
        await self.start(pickle.dumps(runner_input), workers)

    #
    async def execute_task(self, input):
        pass

    async def on_agent_connected(self, topic: "str", agent_id: "str"):
        print("Agent connected", agent_id, topic)
