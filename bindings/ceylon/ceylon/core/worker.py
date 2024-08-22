import asyncio
import pickle
from typing import Any

from ceylon.ceylon import WorkerAgent, WorkerAgentConfig, Processor, \
    MessageHandler, EventHandler

from ceylon.ceylon.ceylon import uniffi_set_event_loop
from ceylon.static_val import DEFAULT_WORKSPACE_PORT, DEFAULT_WORKSPACE_ID


class Worker(WorkerAgent, Processor, MessageHandler, EventHandler):
    agent_type = "WORKER"

    def __init__(self, name="admin", workspace_id=DEFAULT_WORKSPACE_ID, admin_peer="", admin_port=DEFAULT_WORKSPACE_PORT,
                 role="worker",
                 admin_ip="127.0.0.1"):
        super().__init__(config=WorkerAgentConfig(name=name,
                                                  role=role,
                                                  admin_peer=admin_peer,
                                                  admin_port=admin_port,
                                                  work_space_id=workspace_id, admin_ip=admin_ip), processor=self,
                         on_message=self, on_event=self)

    async def run(self, inputs: "bytes"):
        pass

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        pass

    def run_worker(self, inputs: bytes):
        import asyncio

        try:
            # Try to get the running event loop
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop, create a new one
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            return event_loop.run_until_complete(self.arun_worker(inputs))

        # If the loop is already running, schedule the coroutine in the running loop
        if event_loop.is_running():
            # Create a future to run the coroutine
            future = asyncio.ensure_future(self.arun_worker(inputs), loop=event_loop)
            return event_loop.run_until_complete(future)
        else:
            # If no loop is running, run the coroutine with asyncio.run()
            return asyncio.run(self.arun_worker(inputs))

    async def arun_worker(self, inputs: "bytes"):
        uniffi_set_event_loop(asyncio.get_event_loop())
        await self.start(inputs)

    async def on_agent_connected(self, topic: "str", agent: "AgentDetail"):
        pass

    async def broadcast_data(self, message: Any):
        await self.broadcast(pickle.dumps(message))
